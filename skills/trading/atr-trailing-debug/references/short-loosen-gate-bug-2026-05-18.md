# SHORT Trailing Gate Loosen Bug — FIXED 2026-05-18

## Bug

Trailing SL gate for SHORT did not block LOOSENING when `current_on_wrong_side=True`. The gate fired `needs_sl=True` unconditionally for wrong-side cases, even when `new_sl > current_sl` (SL would widen into loss territory).

## Location

`tpsl_utils.py` lines 430-445 (pre-fix):

```python
elif current_on_wrong_side:
    result['needs_sl'] = True          # ← BUG: no tighten check!
    result['_force_write'] = True      # ← allows widening SL
```

## Worked Example: TRB SHORT

```
entry=16.894, current=16.904, db_sl=16.993
new_sl = 16.944682   (computed from lowest=16.894 × 1.003)

current_on_wrong_side = (16.993 > 16.904) = True  (SL in loss zone)
new_sl < current_sl   → 16.945 < 16.993 = False    (LOOSEN, not tighten)

→ elif current_on_wrong_side: fires
→ needs_sl=True, _force_write=True
→ new_sl=16.944682 written to DB (wider than 16.993 — WRONG)
```

## Fix Applied 2026-05-18

`tpsl_utils.py` lines 436-443:

```python
elif current_on_wrong_side:
    if new_sl < current_sl:           # only when TIGHTENING
        result['needs_sl'] = True
        result['_force_write'] = True
    else:
        new_sl = current_sl
        result['needs_sl'] = False    # block the looser SL
```

Now `force_write=True` only fires when `new_sl < current_sl` (tightening). If `new_sl >= current_sl`, the SL write is blocked entirely.

## Verification

MERL SHORT (TIGHTEN case):
- new_sl=0.029265 < current_sl=0.029268 → `needs_sl=True`, `force_write=False` ✓

TRB SHORT (LOOSEN case — OLD BUG):
- new_sl=16.945 > current_sl=16.993 → blocked → `needs_sl=False` ✓

## Related

- Pattern 12 in SKILL.md — SHORT trailing gate wrong-side INVERTED (RESOLVED 2026-05-18)
- `references/tpsl-trailing-gate-bugs-2026-05-18.md` — 3 other bugs fixed same session (pass→needs_sl=True ×2, SHORT wrong_side inverted)