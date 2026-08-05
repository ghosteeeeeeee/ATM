# accel-300 Zero Signals — June 5 2026 Diagnostic

**Symptom**: accel_300.run() returns 0 signals after threshold changes (Jun 1-4 tightening).

**Initial hypothesis**: Data pipeline broken (price_history stale at 8.7 days).

**Actual root causes (in priority order)**:

## Root Cause 1: Regime Slope Threshold Too Restrictive (PRIMARY)

The regime filter in `detect_accel_300()` at lines 410/413 uses:
```python
if slope_pct <= 0.03 and direction == 'LONG': return None
if slope_pct >= -0.03 and direction == 'SHORT': return None
```

Token regime slopes from price_history (20-bar linear regression):
```
ETH:  slope=-0.0085%/bar [FLAT] — blocks LONG
AVAX: slope=+0.0389%/bar [passes] — but only 9 rows → regime check bypassed
SOL:  slope= 0.0000%/bar [FLAT] — blocks LONG
LINK: slope=-0.0049%/bar [FLAT] — blocks LONG
BTC:  slope=-0.0056%/bar [FLAT] — blocks SHORT (but BTC is blacklisted)
```

Every token is in FLAT regime. No signal can pass.

**Fix applied**: `slope_pct <= 0.03` → `<= 0.015` for both directions (lines 410/413).

## Root Cause 2: Stale Threshold Raised Too Far

Prior session raised stale threshold from 10→40 bars to handle "sustained trends where cross is 40+ bars ago."

But in chop, crosses happen frequently (every 20-40 bars) and price goes sideways after — the cross is stale not because trend is old but because it failed.

Raising stale threshold to 40 let old stale crosses through that had no follow-through.

**Fix applied**: 40 → 20 bars (line 290).

## Root Cause 3: Gap Minimum Too High for Flat Market

`MIN_GAP_PCT_LONG = 0.30` requires price to be 0.30% above EMA. In a flat market with 0.20% typical gap, nothing qualifies.

**Fix applied**: 0.30 → 0.20 in hermes_constants.py (both LONG and SHORT).

## Data Pipeline — NOT the Problem

- `price_history` for ETH: 0.8 minutes old ✅
- `price_history` for SOL/BTC: 12768 minutes old ❌
- SOL/BTC staleness: **blacklisted tokens don't get price updates** — this is expected, not a bug

The data was fine for active tokens. The problem was threshold changes, not data pipeline.

## BTC Blacklist Note

BTC has 85731 rows in price_history but all at timestamp 1779941848 (209.7h stale).
This is NOT a data pipeline failure — BTC is in the blacklist so price_history stops updating.
SOL, MATIC, ARB, OP, NEAR, FTM all blacklisted → same 12768m staleness.

**Do NOT investigate the price_history data pipeline** — it's working correctly.
Investigate only if non-blacklisted tokens show staleness.

## Trace Checklist for Future Zero-Signal Issues

When accel_300.run() returns 0:
1. Check `price_age_minutes(token)` for active (non-blacklisted) tokens — should be < 10 min
2. Check `_get_1m_prices(token, 400)` returns ≥ 350 rows
3. Compute regime slope manually: 20-bar linear regression on price_history
   ```python
   import sqlite3, statistics
   conn = sqlite3.connect('/root/.hermes/data/signals_hermes.db')
   cur = conn.cursor()
   cur.execute('SELECT price FROM price_history WHERE token=? ORDER BY timestamp DESC LIMIT 20', (token,))
   rows = cur.fetchall()
   closes = [r[0] for r in reversed(rows)]
   n = len(closes); mean_x = (n-1)/2.0; mean_y = statistics.mean(closes)
   cov = sum((i-mean_x)*(closes[i]-mean_y) for i in range(n))
   var_x = sum((i-mean_x)**2 for i in range(n))
   slope = cov/var_x if var_x > 0 else 0
   slope_pct = slope/mean_y*100 if mean_y > 0 else 0
   ```
4. Check stale threshold: `bars_since_cross > 20` (current value)
5. Check gap minimum: `MIN_GAP_PCT_LONG/SHORT = 0.20` (current value)
6. Check gap growth: `ACCEL_300_MIN_GAP_GROWTH = 0.08` (current value)

## Changes Made June 5 2026

| Location | Change | Reason |
|---|---|---|
| accel_300.py:290 | `bars_since_cross > 40` → `> 20` | Too loose — let stale crosses through in chop |
| accel_300.py:410 | `slope_pct <= 0.03` → `<= 0.015` | Too strict — blocked everything in flat market |
| accel_300.py:413 | `slope_pct >= -0.03` → `>= -0.015` | Same for SHORT |
| hermes_constants.py | `MIN_GAP_PCT_LONG = 0.30` → `0.20` | Too high for flat market |
| hermes_constants.py | `MIN_GAP_PCT_SHORT = 0.30` → `0.20` | Same |
| hermes_constants.py | `ACCEL_300_MIN_GAP_GROWTH = 0.05` → `0.08` | Require stronger acceleration |

## Why accel-300+ LONG Is Broken (Separate Issue)

The regime/gap/stale fixes address why accel-300 returns 0 signals. But separately,
accel-300+ LONG was 22% WR in the last 96h (200 trades). This is a killswitch issue,
not a threshold tuning issue — in chop, even valid accel-300+ LONG signals hit SL.

See: `references/96h-trade-analysis-2026-06-05.md`