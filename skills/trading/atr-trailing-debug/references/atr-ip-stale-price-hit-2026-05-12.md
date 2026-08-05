# IP atr_sl_hit Anomaly — 2026-05-12 03:40

## The Trade
- Trade ID: 9308 (IP LONG, 3x leverage, $50)
- Entry: $0.5565 | Exit: $0.556580 | Close reason: `atr_sl_hit`
- Source: `accel-300+,hhh-long4`, conf=98.00

## The Paradox
For a LONG: `atr_sl_hit` fires when `current_price <= stop_loss`.

All computed SL variants are below exit price:

| SL scenario | Computed SL | Exit ($0.556580) vs SL |
|-------------|-------------|------------------------|
| ACCEL_FAST k=0.0375 + MIN_SL=0.50% | $0.555387 | +0.21% above |
| New trade INIT floor 0.50% | $0.555387 | +0.21% above |
| ATR_K_INITIAL×ATR (k=1.0, base) | $0.555511 | +0.19% above |
| MIN_SL floor 0.20% | $0.555387 | +0.21% above |

Exit is above every computed SL. `atr_sl_hit` should NOT have fired.

## Root Cause: Stale `current_price` in Hit Detection

`check_atr_tp_sl_hits()` reads `pos.get('current_price')` from the **in-memory position dict**, not a live HL price fetch.

In the 03:40 cycle:
1. `check_atr_tp_sl_hits()` ran with stale `current_price` (could be 0 or previous cycle's value)
2. That stale price was below the stored SL → `atr_sl_hit` triggered
3. `mirror_close()` was called with the **actual HL fill price** $0.556580 (correct)
4. The logged exit price reflects the real HL execution; the trigger was based on stale dict price

**The HL fill is correct. The trigger was wrong.** The position_manager processed the close with the correct exit price, but the close was initiated by a false signal from the stale dict.

## Verification Steps

```bash
# Check IP position's current_price in the position_manager cycle
# Look at the 03:40 log entries around check_atr_tp_sl_hits:
python3 -c "
log = '/root/.hermes/logs/pipeline.log'
with open(log, 'rb') as f:
    f.seek(-800000, 2)
    tail = f.read().decode('utf-8', errors='replace')
for l in tail.split('\n'):
    if '03:40' in l and ('IP' in l or 'current_price' in l or 'atr_sl_hit' in l):
        print(l)
"
```

## Fix Direction

**Option A (best)**: In `check_and_manage_positions()`, call `refresh_current_prices()` BEFORE `check_atr_tp_sl_hits()` so the in-memory dict has fresh prices at detection time.

**Option B**: Make `check_atr_tp_sl_hits()` accept a `prices` dict parameter passed in from the caller (which already has fresh prices), instead of reading from `pos.get('current_price')`.

**Option C**: Have `check_atr_tp_sl_hits()` fetch live price directly from HL for each token, bypassing the in-memory dict entirely.

## Lesson

The `atr_cache` itself is NOT stuck or stale. The issue is the **order of operations**: hit detection reads from a dict whose `current_price` was set in a previous cycle. This is an execution-order bug, not an ATR cache bug.

**ATR cache is fine.** The bug is in position_manager's hit-detection → price-freshness sequencing.