"""Assumption constants driving Macro verdicts. Edit here; every page follows.

These are judgment inputs, not data. They are kept in one place so the
Market Verdict math stays transparent and easy to challenge.
"""

# India 10Y G-Sec yield (%). No reliable free API feed exists, so this is
# updated manually. Check https://www.rbi.org.in before major reviews.
RISK_FREE_RATE = 7.1

# Required equity return (%) used by the Market Verdict: the return an
# investor demands from smallcaps for their risk.
REQUIRED_RETURN = 15.0

# Long-run inflation anchor (%). Nominal growth is shown as real growth by
# subtracting this, e.g. "+14% sales" reads as "~9% real".
INFLATION = 5.0

# Equity risk premium (%) over the risk-free rate. Context for how demanding
# the required return is relative to bonds.
EQUITY_PREMIUM = 4.0
