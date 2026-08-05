# Trailing Gate `needs_sl` — When it blocks a valid tighten (2026-05-17)

## The Problem

`compute_atr_sl_tp` returns `needs_sl=False` for VVV SHORT even though the computed SL (14.611) would significantly tighten the position (current DB SL=14.772, computed=14.611, gap=+1.6%).

The trailing gate logic in `tpsl_utils.py`:
- SHORT: `new_sl < current_sl` → allow tighten; `new_sl >= current_sl` → block (`needs_sl=False`)
- VVV case: computed 14.611 < current 14.772 → gate SHOULD allow, but `needs_sl=False`

## Possible Root Cause

The `needs_sl` flag is set to False when the new SL would LOOSEN the position. But in `compute_atr_sl_tp`, the function also sets `needs_sl=False` under other conditions:

1. `current_sl <= 0` (no existing SL) — the function sets `needs_sl=True` explicitly
2. Phase = `NEW_TRADE` — `needs_sl=True`
3. In the trailing gate block, when `new_sl >= current_sl` (SHORT) — `needs_sl=False`

But wait — VVV's `new_sl=14.611 < current_sl=14.772`, so it should NOT be blocked by the trailing gate. Yet `needs_sl=False`.

**Hypothesis**: The function may be returning `needs_sl=False` because `eff_sl_pct = ATR_SL_MIN_ACCEL = 0.70%` (floor binding) but the anchor `ref_price` used is `lowest_price=14.51`. Since `lowest_price < current_price (14.605)`, the computed `new_sl = 14.51 × 1.007 = 14.616` is very close to `current_sl = 14.772`. The gate might be comparing the WRONG values.

Need to trace the exact line-by-line execution to find where `needs_sl=False` is set.

## Diagnostic

```python
import sys
sys.path.insert(0, '/root/.hermes/scripts')
from tpsl_utils import compute_atr_sl_tp

# Add debug print to compute_atr_sl_tp temporarily
result = compute_atr_sl_tp(
    token='VVV', direction='SHORT',
    entry_price=14.576, current_price=14.605,
    highest_price=14.643, lowest_price=14.51,
    pnl_pct=-0.002, current_sl=14.772310, current_tp=14.190150,
    momentum_stats=None, speed_percentile=50.0
)
print(f"needs_sl={result['needs_sl']}, new_sl={result['new_sl']:.6f}, eff_sl_pct={result['eff_sl_pct']*100:.2f}%")
print(f"state={result['state']}, k={result['k']}, atr_pct={result['atr_pct']*100:.3f}%")
print(f"ref_price used: {result.get('ref_price', 'N/A')}")
```

## The Fix

If the gate is blocking a valid tighten (computed SL significantly better than current SL), the fix is to add a minimum delta override:

```python
# In tpsl_utils trailing gate — if computed SL is meaningfully tighter, allow regardless
MIN_SL_IMPROVE_PCT = 0.005  # 0.5% minimum improvement threshold

if direction == 'SHORT':
    if current_sl > 0:
        tighten_amt = (current_sl - new_sl) / current_sl
        if new_sl < current_sl or tighten_amt >= MIN_SL_IMPROVE_PCT:
            pass  # tighten or meaningful improvement
        else:
            new_sl = current_sl
            result['needs_sl'] = False
```

Or: always set `needs_sl=True` when `new_sl < current_sl` regardless of other conditions.

## References

- `references/vvv-0g-sl-wrong-atr-managed-false-2026-05-17.md` — VVV/0G full investigation
- `references/trailing-gate-needs-sl-debug-2026-05-17.md` — this document