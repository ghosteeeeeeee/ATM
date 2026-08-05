# TP/SL Ratio Diagnostic — Session 2026-05-15

## The Pattern

When a trade's TP and SL are computed from different ATR values, the TP/SL ratio will be wrong. Canonical ratio:
```
TP_pct / SL_pct = ATR_TP_K_MULT = 1.25
```

If ratio ≠ 1.25, the TP and SL were computed from different sources.

## Diagnostic One-Liner

```python
import json
for t in json.load(open('/var/www/hermes/data/trades.json'))['open']:
    sl_pct = abs(t['sl'] - t['entry']) / t['entry']
    tp_pct = abs(t['entry'] - t['tp']) / t['entry']
    ratio = tp_pct / sl_pct if sl_pct > 0 else 0
    if abs(ratio - 1.25) > 0.2:
        print(f"{t['coin']:8} SL={sl_pct*100:.2f}% TP={tp_pct*100:.2f}% ratio={ratio:.2f}x ⚠️")
    else:
        print(f"{t['coin']:8} SL={sl_pct*100:.2f}% TP={tp_pct*100:.2f}% ratio={ratio:.2f}x")
```

## What It Found

ZK SHORT: SL=0.70%, TP=3.75%, ratio=5.4x — **should be 1.25x**.

## Root Cause Implied by Ratio

| Ratio | What it means |
|-------|--------------|
| ~1.25 | TP and SL from same ATR computation — healthy |
| ~2-3x | TP computed from a different (larger) ATR than SL |
| ~0.5x | TP computed from a different (smaller) ATR than SL |
| Very large | SL floor-bound (MIN) + TP ATR-based — ratio driven by MIN_SL vs ATR_tp |

For ZK: SL=0.70% = ATR (floor-bound at ATR_SL_MIN_INIT=0.50%), TP=3.75% implies ATR=3.75%/1.25=3.0%. Two different ATRs used.

## Fix

When `lowest_price = 0` in DB for a SHORT, use `_entry` as ref_price for BOTH SL and TP computation. The `_entry` anchor (line 1650-1651) applies to SL but not TP (line 1655). Fix: extend the `_entry` anchor to TP as well when `lowest_price=0`.

## Verification After Fix

```python
# All trades should have TP/SL ratio within 0.1 of 1.25
import json
for t in json.load(open('/var/www/hermes/data/trades.json'))['open']:
    if t['direction'] == 'SHORT':
        sl_pct = (t['sl'] - t['entry']) / t['entry']
        tp_pct = (t['entry'] - t['tp']) / t['entry']
    else:
        sl_pct = (t['entry'] - t['sl']) / t['entry']
        tp_pct = (t['tp'] - t['entry']) / t['entry']
    ratio = tp_pct / sl_pct if sl_pct > 0 else 0
    assert abs(ratio - 1.25) < 0.2, f"{t['coin']} ratio={ratio:.2f}x — BUG"
```