"""Self-correcting loop: find bugs via AppTest + fix + verify.

Usage:
  python scripts/self_correct.py              # one pass, no push
  python scripts/self_correct.py --loop 3     # up to 3 auto-fix iterations
  python scripts/self_correct.py --push       # commit & push if fixed

Loop:
  1. Observe  — run AppTest on every page, collect exceptions + Streamlit Cloud log hints
  2. Diagnose — regex the traceback to file:line + error type
  3. Fix      — apply deterministic patch for known patterns; fall back to LLM hint
  4. Verify   — re-run AppTest; if green, commit

Designed to run locally and in CI (.github/workflows/self-correct.yml).
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PAGES = ["app.py", "pages/1_Macro_Analysis.py", "pages/2_Sectoral_Analysis.py", "pages/3_Micro_Analysis.py", "pages/4_Guide.py"]

# Known error -> fix mapping (deterministic, no LLM needed)
FIXES = {
    "KeyError: '_label'": "mirror _label to full df in src/micro_tab.py",
    "cannot import name 'market_verdict'": "check src/analytics.py exports market_verdict; ensure HIST_DIR files exist",
    "cannot import name": "verify export exists in src/analytics.py and is committed/pushed",
    "get_loc.*_label": "add df['_label'] alias in micro_tab",
    "SyntaxError: f-string expression part cannot include a backslash": "extract emoji vars before f-string in micro_tab",
    "UnicodeEncodeError": "avoid cp1252 print of emoji; write utf-8 file instead",
}

def run_tests(pages=None) -> list[dict]:
    pages = pages or DEFAULT_PAGES
    try:
        from streamlit.testing.v1 import AppTest
    except Exception as e:
        return [{"page": "*", "ok": False, "error": f"AppTest import failed: {e}", "trace": traceback.format_exc()}]
    failures = []
    for p in pages:
        fp = ROOT / p
        if not fp.exists():
            failures.append({"page": p, "ok": False, "error": f"File not found: {fp}", "trace": ""})
            continue
        try:
            at = AppTest.from_file(str(fp), default_timeout=120)
            at.run()
            if at.exception:
                err = "\n".join(str(e) for e in at.exception)
                failures.append({"page": p, "ok": False, "error": err[:2000], "trace": err})
            else:
                # also exercise a stock select on micro to catch _label bugs
                if p == "pages/3_Micro_Analysis.py" and at.selectbox:
                    try:
                        opts = at.selectbox[0].options
                        if len(opts) > 1:
                            at.selectbox[0].set_value(opts[1]).run()
                            if at.exception:
                                err = "\n".join(str(e) for e in at.exception)
                                failures.append({"page": p + " [select]", "ok": False, "error": err[:2000], "trace": err})
                    except Exception as e:
                        failures.append({"page": p + " [select]", "ok": False, "error": str(e)[:2000], "trace": traceback.format_exc()})
        except Exception as e:
            failures.append({"page": p, "ok": False, "error": str(e)[:2000], "trace": traceback.format_exc()})
    return failures


def diagnose(failures: list[dict]) -> list[dict]:
    diags = []
    for f in failures:
        err = f["error"]
        hint = "unknown"
        for pat, fix in FIXES.items():
            if re.search(pat, err, re.IGNORECASE):
                hint = fix
                break
        # extract file:line
        m = re.search(r'File "([^"]+)", line (\d+)', f["trace"] or err)
        loc = f"{m.group(1)}:{m.group(2)}" if m else f["page"]
        diags.append({**f, "hint": hint, "loc": loc})
    return diags


def apply_deterministic_fix(diag: dict) -> bool:
    """Apply a known deterministic fix. Returns True if a file was patched."""
    err = diag["error"]
    # Example: _label KeyError -> ensure micro_tab mirrors _label
    if "_label" in err and "KeyError" in err:
        fp = ROOT / "src/micro_tab.py"
        txt = fp.read_text(encoding="utf-8")
        if 'df["_label"] = df[label_col]' not in txt:
            txt = txt.replace(
                'df_valid["_label"] = df_valid[label_col].astype(str) + " (" + df_valid[symbol_col].astype(str) + ")"',
                'df["_label"] = df[label_col].astype(str) + " (" + df[symbol_col].astype(str) + ")"\n    df_valid["_label"] = df_valid[label_col].astype(str) + " (" + df_valid[symbol_col].astype(str) + ")"',
            )
            fp.write_text(txt, encoding="utf-8")
            print(f"  patched {fp} for _label")
            return True
    if "f-string expression part cannot include a backslash" in err:
        print("  hint: extract emoji to variable before f-string (see src/micro_tab.py:310)")
        return False
    return False


def git_commit_push(msg: str) -> bool:
    try:
        subprocess.check_call(["git", "add", "-A"], cwd=ROOT)
        status = subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True)
        if not status.strip():
            print("  no changes to commit")
            return False
        subprocess.check_call(["git", "commit", "-m", msg], cwd=ROOT)
        subprocess.check_call(["git", "push"], cwd=ROOT)
        print(f"  pushed: {msg}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"  git failed: {e}")
        return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--loop", type=int, default=1, help="max auto-fix iterations")
    ap.add_argument("--push", action="store_true", help="commit & push if fixed")
    ap.add_argument("--pages", nargs="*", default=None)
    args = ap.parse_args()

    for i in range(max(1, args.loop)):
        print(f"\n=== pass {i+1}/{args.loop} — observing ===")
        failures = run_tests(args.pages)
        if not failures:
            print("[OK] All pages green - no bug found.")
            return 0
        print(f"❌ {len(failures)} failure(s):")
        diags = diagnose(failures)
        for d in diags:
            print(f"  - {d['page']} @ {d['loc']}: {d['error'][:180]}")
            print(f"    hint: {d['hint']}")
        if i == args.loop - 1:
            print("\nNo more iterations — not auto-fixing in this pass.")
            return 1
        print("\n--- attempting deterministic fixes ---")
        fixed_any = False
        for d in diags:
            if apply_deterministic_fix(d):
                fixed_any = True
        if not fixed_any:
            print("  no deterministic fix matched — needs LLM or manual patch.")
            print("  Tip: pipe the error into your LLM fixer or run: opencode --prompt \"fix the AppTest failure in <file>\"")
            return 1
        print("  re-verifying after patch...")
        failures2 = run_tests(args.pages)
        if not failures2:
            print("✅ Fixed and verified green.")
            if args.push:
                git_commit_push(f"auto-fix: {diags[0]['hint']} ({diags[0]['loc']})")
            return 0
        print(f"  still failing ({len(failures2)}), looping...")
    return 1


if __name__ == "__main__":
    sys.exit(main())
