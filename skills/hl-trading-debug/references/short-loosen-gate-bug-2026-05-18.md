# SHORT Trailing Gate Loosen Bug (2026-05-18)

## Bug

Trailing SL gate for SHORT does not block LOOSENING when `current_on_wrong_side=True`. The gate fires `needs_sl=True` unconditionally for wrong-side cases, even when `new_sl > current_sl` (SL would widen).

## Location

`tpsl_utils.py` lines 430-445:

```python
elif direction == 'SHORT':
    if current_sl > 0:
        current_on_wrong_side = (current_sl > current_price)  # PATCHED ✓
        if new_sl < current_sl:
            result['needs_sl'] = True          # tighten ✓
        elif current_on_wrong_side:
            result['needs_sl'] = True          # ← BUG: no tighten check!
            result['_force_write'] = True      # ← allows widening
        else:
            new_sl = current_sl; needs_sl = False
```

## Worked Example: TRB SHORT

```
entry=16.894, current=16.904, db_sl=16.993125
new_sl = 16.944682   (computed from lowest=16.894 × 1.003)

current_on_wrong_side = (16.993 > 16.904) = True  (SL is in loss zone)
new_sl < current_sl   → 16.945 < 16.993 = False    (would LOOSEN, not tighten)

→ Gate goes to elif current_on_wrong_side:
→ needs_sl=True, _force_write=True
→ new_sl=16.944682 written to DB (wider than 16.993 — WRONG direction)
```

## Correct Behavior

In the `elif current_on_wrong_side:` branch for SHORT, we should only force-write when the new SL would actually TIGHTEN (`new_sl < current_sl`). If `new_sl > current_sl`, the SL would widen — this should be blocked, not forced.

## Fix

```python
elif current_on_wrong_side:
    if new_sl < current_sl:
        result['needs_sl'] = True
        result['_force_write'] = True
    else:
        new_sl = current_sl
        result['needs_sl'] = False
```

## Status

**NOT YET FIXED** — confirmed 2026-05-18.

## Verification

```python
# Test that gate blocks loosening
trades = [
    ('TRB',   'SHORT', 16.894, 16.904, 16.993125, 16.453125, 16.894, 16.894),
]
for token, direction, entry, current, db_sl, db_tp, high, low in trades:
    r = tpsl_utils.compute_atr_sl_tp(...)
    tighten = r['new_sl'] < db_sl
    print(f'{token}: new_sl={r["new_sl"]:.6f} db_sl={db_sl:.6f} tighten={tighten} needs_sl={r.get("needs_sl")}')
    # Expected: tighten=False, needs_sl=False (gate should block)
```

## Related

- `references/tpsl-trailing-gate-bugs-2026-05-18.md` — 3 bugs fixed (pass→needs_sl=True ×2, SHORT wrong_side inverted)
- `references/short-wrong-side-comparison-bug-2026-05-18.md` — the wrong-side inversion bug