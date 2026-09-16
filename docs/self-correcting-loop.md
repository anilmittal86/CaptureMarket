# Self-Correcting Loop

**Goal:** the agent finds the bug and fixes it without you watching — then proves it’s green.

## How it works (Observe → Diagnose → Fix → Verify)

```
push / schedule / Cloud log ──▶ Observe ──▶ Diagnose ──▶ Fix ──▶ Verify ──▶ push if green
                                 ▲                               │
                                 └─────────── loop (max 3) ──────┘
```

1. **Observe** — `scripts/self_correct.py` runs `AppTest.from_file` on `app.py` + every `pages/*.py` (including a `selectbox` interaction on Micro to catch `_label`/`PEG` bugs). Also re-usable for a Streamlit Cloud log snippet you paste.
2. **Diagnose** — regex extracts `File "...", line N` + error type (`KeyError`, `ImportError`, `SyntaxError`, `UnicodeEncodeError`). Maps to a hint via `FIXES` dict (e.g., `_label KeyError → mirror _label to full df`).
3. **Fix** — first tries a **deterministic patch** (no LLM, no API key, <1s). If no pattern matches, it prints `needs LLM` and exits — you (or `opencode --prompt`) pipe the log to an LLM for a patch.
4. **Verify** — re-runs the same `AppTest` suite. Only if green does it `git commit --push`.

## Running it

```bash
# local, one pass, no push — what CI does on every push
python scripts/self_correct.py

# up to 3 auto-fix iterations, commit & push if fixed
python scripts/self_correct.py --loop 3 --push

# watch mode (dev): re-run on file change
pip install watchdog
watchmedo shell-command --patterns="*.py" --recursive --command="python scripts/self_correct.py"
```

## CI

`.github/workflows/self-correct.yml` runs the same script on:

- every `push` to `main` and every PR
- every 6 hours (catches NSE/yfinance drift + Cloud image drift)
- manual `workflow_dispatch`

If the loop finds a failure with a deterministic fix, it pushes the fix to the branch. If it needs an LLM, it comments on the PR with the hint.

## Extending to LLM auto-fix

Add an `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` secret and a second step:

```yaml
- name: LLM fix
  if: steps.observe.outputs.exit_code != '0'
  run: opencode --prompt "Fix the AppTest failure. Log: $(cat self_correct.log)" --apply
```

The deterministic layer stays as a fast, free guardrail; the LLM layer handles novel tracebacks.

## What it already catches (from your history)

- `KeyError: '_label'` in `src/micro_tab.py:154` — mirrored `_label` to full `df`
- `ImportError: cannot import name 'market_verdict'` — stale Cloud vs `origin/main` (`git fetch` check)
- `SyntaxError: f-string backslash` — emoji extracted before f-string
- `UnicodeEncodeError: cp1252` — write utf-8 file instead of `print`

Add new `FIXES` entries as you hit new error classes.

## Streamlit Cloud log → loop

If Cloud shows a redacted traceback, click `Manage app → Logs`, copy the full `File "...", line ...` block, save as `cloud.log`, and run:

```bash
python scripts/self_correct.py --pages pages/3_Micro_Analysis.py  # targeted
# or paste cloud.log into: opencode --prompt "fix this: $(cat cloud.log)"
```

The loop is the same — only the observer input changes.
