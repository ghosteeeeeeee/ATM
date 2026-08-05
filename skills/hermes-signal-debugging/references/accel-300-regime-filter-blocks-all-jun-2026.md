# accel-300 Regime Filter Bug — June 62026

## Symptom
Live runs of `accel_300.py` produce 0 signals despite:
- Market is clearly trending (many tokens in downtrends)
- Multiple tokens have valid EMA300 crosses in recent bars
- 155 accel-300 SHORT trades were placed historically with WR51.6%

## Root Cause
The regime filter at `accel_300.py` lines 390–419 computes slope from `price_history` (last 20 bars) and blocks SHORT when `slope_pct >= -ACCEL_300_REGIME_SLOPE_PCT`.

With `ACCEL_300_REGIME_SLOPE_PCT = 0.008`:
- Threshold for SHORT: `slope_pct < -0.008` (market must be meaningfully bearish)
- **27 out of 30 sampled tokens have slope >= -0.008** (near-zero or positive)
- ALL SHORT signals are blocked as NEUTRAL market

Key insight: the regime filter was NOT in the original commit (`de86b7c` May 132026). The 155 historical SHORT trades were placed WITHOUT it. It was added later and is blocking signals that previously worked.

## Diagnostic Script
```python
import sqlite3, statistics
from hermes_constants import ACCEL_300_REGIME_SLOPE_PCT

conn = sqlite3.connect('/root/.hermes/data/signals_hermes.db', timeout=10)
tokens = [r[0] for r in conn.execute("SELECT DISTINCT token FROM price_history LIMIT 30").fetchall()]
for tok in tokens:
    rows = conn.execute("SELECT price FROM price_history WHERE token=? ORDER BY timestamp DESC LIMIT 20", (tok,)).fetchall()
    if len(rows) < 10: continue
    closes_20 = [r[0] for r in reversed(rows)]
    n_r = len(closes_20)
    mean_x = (n_r - 1) / 2.0
    mean_y = statistics.mean(closes_20)
    cov = sum((i - mean_x) * (closes_20[i] - mean_y) for i in range(n_r))
    var_x = sum((i - mean_x) ** 2 for i in range(n_r))
    slope = cov / var_x if var_x > 0 else 0
    slope_pct = slope / mean_y if mean_y > 0 else 0
    blocked = slope_pct >= -ACCEL_300_REGIME_SLOPE_PCT
    print(f"{tok}: slope={slope_pct*100:.4f}%/bar SHORT {'BLOCKED' if blocked else 'PASSES'}")
conn.close()
```

## Fix Options

### Option A: Raise threshold (quickest fix)
Set `ACCEL_300_REGIME_SLOPE_PCT = 0.002` in `hermes_constants.py`. This flips the blocking threshold to only block SHORT when market is STRONGLY bullish (slope > +0.002). Tokens with flat or slightly negative slopes pass.

### Option B: Remove regime filter entirely
The filter was added post-hoc and wasn't in the code when155 successful trades were placed. Consider removing lines 390–419 from `accel_300.py`.

### Option C: Flip the logic
Only block SHORT when `slope_pct > +0.015` (strong uptrend), not when `slope_pct >= -0.008`. This was the original intent — block counter-regime, not all slightly-bullish-to-neutral markets.

## Tokens Affected
Even top performers (ZK 67% WR, LINK, STBL, ME) would be blocked by the regime filter today. Their slopes are all >= -0.008.

## Relevant Code
`accel_300.py` lines 390–419:
```python
# Regime filter: suppress counter-regime signals
try:
    conn = sqlite3.connect('/root/.hermes/data/signals_hermes.db', timeout=10)
    rows = conn.execute(
        "SELECT price FROM price_history WHERE token=? ORDER BY timestamp DESC LIMIT 20",
        (token.upper(),)
    ).fetchall()
    conn.close()
    if len(rows) >= 10:
        closes_20 = [r[0] for r in reversed(rows)]
        n = len(closes_20)
        mean_x = (n - 1) / 2.0
        mean_y = statistics.mean(closes_20)
        cov = sum((i - mean_x) * (closes_20[i] - mean_y) for i in range(n))
        var_x = sum((i - mean_x) ** 2 for i in range(n))
        if var_x > 0:
            slope = cov / var_x
            slope_pct = slope / mean_y if mean_y > 0 else 0
            # Block LONG in down/sideways markets
            if slope_pct <= ACCEL_300_REGIME_SLOPE_PCT and direction == 'LONG':
                return None
            # Block SHORT in up/sideways markets
            if slope_pct >= -ACCEL_300_REGIME_SLOPE_PCT and direction == 'SHORT':
                return None
except Exception:
    pass
```

## Lessons
1. Regime filter was added AFTER successful trading — it's a regression, not an improvement
2. `ACCEL_300_REGIME_SLOPE_PCT = 0.008` is too tight — blocks almost everything
3. Original intent (block counter-regime) is correct, but implementation is inverted — it blocks nearly all SHORTs because most markets are near-neutral
4. Always verify new filters against historical trade data before deploying
