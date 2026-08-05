# accel-300 LOOKBACK + STALE_BARS Calibration Bug (Jun 2026)

## What Happened

T was tweaking `ACCEL_300_LOOKBACK` in hermes_constants (set to 250) but the signal was ignoring it — had hardcoded `LOOKBACK = 30` locally. Only2 of 8+ ACCEL_300 constants were actually imported and used.

After patching the import, the new LOOKBACK=250 caused 0 signals:

| Setting | Value | Effect |
|---|---|---|
| ACCEL_300_LOOKBACK | 250 | Detection starts at bar 550 |
| ACCEL_300_STALE_BARS | 25 | Stale gate blocks bars_since > 25 |
| PURR cross_bar | 441 | bars_since = 550-441 = 109 to 698-441 = 257 |
| Result | ALL 34 growth-passing bars blocked | bars_since min=109, all > 25 |

At original `LOOKBACK=30`: detection starts at bar 330, same cross → bars_since = 330-441 = -111 (cross is in the "future" relative to bar330, but bars 451, 453, 459, 461, 462 pass with bars_since=10-21, all < 25).

## Root Cause

The cross_bar (where price crossed the EMA300) is fixed by the price history. When LOOKBACK changes:
- Detection start = PERIOD (300) + LOOKBACK
- bars_since = detection_start - cross_bar

With LOOKBACK=250: detection starts at 550, cross at 441 → bars_since = 109-257 (all > 25, all blocked)
With LOOKBACK=30: detection starts at 330, cross at 441 → bars_since = -111 to 257 (bars451+ pass with bars_since=10-21, within stale=25)

## The Fix Pattern

When changing `ACCEL_300_LOOKBACK`, always check if `ACCEL_300_STALE_BARS` needs updating:

```python
# bars_since for the shortest-passing bar:
bars_since_min = (PERIOD + LOOKBACK) - cross_bar  # cross_bar is ~441 for PURR

# STALE_BARS must be >= bars_since_min to not block the closest cross
# With LOOKBACK=250: bars_since_min ≈ 109 → STALE_BARS needs to be ≥ 109
# With LOOKBACK=30: bars_since_min ≈10 → STALE_BARS=25 works fine
```

## Also: Regime slope for single-row price_history

Most tokens (149/230) have only 1 row in price_history. Regime slope from1 row = 0.0000. Threshold `ACCEL_300_REGIME_SLOPE_PCT=0.003` means slope< -0.30%/bar for SHORT. PURR at -0.0647%/bar is > -0.30%, so blocked. All 81 fresh tokens blocked at 0.003.

## Diagnostic One-Liner

```bash
cd /root/.hermes/scripts && PYTHONPATH=/root/.hermes/scripts python3 - <<'EOF'
import sys; sys.path.insert(0, '.'); from signals.accel_300 import _get_1m_prices
prices = _get_1m_prices('PURR', lookback=700)
newest = prices[-1]['timestamp']; cross_bar = 441
detection_start = 300 + 250  # PERIOD + ACCEL_300_LOOKBACK
bars_since = detection_start - cross_bar
print(f"Detection start bar: {detection_start}, cross_bar: {cross_bar}, bars_since: {bars_since}")
print(f"STALE_BARS=25 blocks: {bars_since > 25}")
EOF
```

## Key Lesson

Constants in hermes_constants are **useless** if the signal doesn't import and use them. Always verify with `grep -n "ACCEL_300" signals/accel_300.py` that the constant you changed is actually referenced in the signal's code — not just that it exists in the constants file.
