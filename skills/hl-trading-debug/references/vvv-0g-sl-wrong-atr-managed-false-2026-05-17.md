# VVV + 0G SL Investigation — 2026-05-17

## The Problem

Two open trades (VVV SHORT, 0G SHORT) have SL values significantly wider than what `tpsl_utils.compute_atr_sl_tp` computes:

| Token | Dir | DB SL | Computed SL | Gap | atr_managed |
|-------|-----|-------|-------------|-----|-------------|
| VVV | SHORT | 14.772310 | 14.611570 | **+1.6% too wide** | **False** |
| 0G | SHORT | 0.503663 | 0.498918 | **+0.95% too wide** | **False** |
| STRK | LONG | 0.041950 | 0.041950 | ✓ match | True |
| ZEN | LONG | 5.936698 | 5.936698 | ✓ match | True |
| MOVE | LONG | 0.017191 | 0.017192 | ✓ match | True |

## Root Cause

**`atr_managed = False`** in PostgreSQL for VVV and 0G. This means `_persist_atr_levels` was never called for these trades — the SL was set at open time and never updated by position_manager's ATR engine.

STRK/ZEN/MOVE have `atr_managed = True` — correct SL values, properly managed by the ATR trailing system.

## The `atr_managed` Flag

`_persist_atr_levels` sets `atr_managed = TRUE` on every successful UPDATE:
```python
cur.execute("""
    UPDATE trades
    SET stop_loss = %s, target = %s, atr_managed = TRUE
    WHERE id = %s AND status = 'open'
""", (new_sl, new_tp, trade_id))
```

If `atr_managed = FALSE`, either:
1. The trade was never processed by `_collect_atr_updates` (e.g., excluded by a filter)
2. The UPDATE failed silently
3. The SL was written at entry time by a different path (signal, brain.py Step 5, etc.)

## Diagnostic Query

```python
import psycopg2
conn = psycopg2.connect(host='/var/run/postgresql', database='brain', user='postgres', password='Brain123')
cur = conn.cursor()
cur.execute("SELECT token, direction, entry_price, stop_loss, target, highest_price, lowest_price, atr_managed FROM trades WHERE status='open' AND token IN ('VVV','0G')")
for row in cur.fetchall():
    print(row)
conn.close()
```

## VVV SL Anatomy

Actual: `14.772310 = current_price (14.605) + ATR (0.167)`
Computed: `14.611570` (current_price × (1 + 0.70%) using ACCEL floor with ATR%=1.15%)

The actual VVV SL exactly equals `current_price + ATR` — a formula that does NOT exist in `tpsl_utils.compute_atr_sl_tp`. Most likely: the SL was set at entry by the signal that opened the trade, and position_manager never overwrote it.

## 0G SL Anatomy

Actual: `0.503663 ≈ entry × 1.0153` (+1.53% from entry)
Computed: `0.498918` (= entry × (1 + 0.70%))

The 1.53% distance matches `SL_PCT_FALLBACK = 0.015 (1.5%)` from hermes_constants. This suggests the SL was set at entry time from a signal or brain.py default, not from the ATR engine.

## Fix

For VVV: `UPDATE trades SET stop_loss=14.611570 WHERE token='VVV' AND status='open'`
For 0G: `UPDATE trades SET stop_loss=0.498918 WHERE token='0G' AND status='open'`

Then verify with:
```python
from tpsl_utils import compute_atr_sl_tp
# VVV SHORT
result = compute_atr_sl_tp(token='VVV', direction='SHORT', entry_price=14.576, current_price=14.605,
    highest_price=14.643, lowest_price=14.51, pnl_pct=-0.002, current_sl=14.772310, current_tp=14.190150,
    momentum_stats=None, speed_percentile=50.0)
print(f"VVV: computed_SL={result['new_sl']:.6f}, eff_sl={result['eff_sl_pct']*100:.2f}%")

# 0G SHORT
result = compute_atr_sl_tp(token='0G', direction='SHORT', entry_price=0.49609, current_price=0.4955,
    highest_price=0.496245, lowest_price=0.49545, pnl_pct=0.0011, current_sl=0.503663, current_tp=0.483814,
    momentum_stats=None, speed_percentile=50.0)
print(f"0G: computed_SL={result['new_sl']:.6f}, eff_sl={result['eff_sl_pct']*100:.2f}%")
```

## Prevention

When a new trade arrives:
1. Check if `atr_managed = FALSE` immediately after opening
2. If FALSE after 1 cycle of position_manager, force-run `_collect_atr_updates` for that token
3. The `needs_sl` field from `compute_atr_sl_tp` should be True if the trailing gate would accept a tighten — if it's False but the gap is large, investigate why