# TPSL Trailing Gate Bugs — ALL RESOLVED 2026-05-18

## Bugs Fixed

Four bugs in `tpsl_utils.py` trailing gate (lines 413–443):

| Bug | Line | Before | After | Impact |
|-----|------|--------|-------|--------|
| LONG tighten blocked | 416 | `pass` (needs_sl=None→falsy) | `result['needs_sl'] = True` | LONG SLs couldn't tighten upward |
| SHORT tighten blocked | 435 | `pass` (needs_sl=None→falsy) | `result['needs_sl'] = True` | SHORT SLs couldn't tighten downward |
| SHORT wrong-side inverted | 432 | `current_sl < current_price` | `current_sl > current_price` | WRONG_SIDE force-write never fired for SHORT |
| SHORT force_write LOOSEN | 436-443 | force_write fires regardless of tighten/loosen direction | `if new_sl < current_sl:` guard added | force_write now only fires on TIGHTEN; LOOSEN blocked |

**ALL 4 RESOLVED 2026-05-18.**

## Bug 4 Detail: SHORT force_write LOOSEN

The wrong_side branch (lines 436-443) fired `force_write=True` even when `new_sl > current_sl` (loosening). This would write a wider SL to DB — directly into loss territory.

**Before fix (BUG):**
```python
elif current_on_wrong_side:
    result['needs_sl'] = True          # ← no tighten check!
    result['_force_write'] = True      # ← allows widening SL
```

**After fix:**
```python
elif current_on_wrong_side:
    if new_sl < current_sl:            # only when TIGHTENING
        result['needs_sl'] = True
        result['_force_write'] = True
    else:
        new_sl = current_sl
        result['needs_sl'] = False     # block the looser SL
```

## Worked Examples

**MERL SHORT (tighten case):**
```
current_sl=0.029268, new_sl=0.029265
new_sl < current_sl → True (tightening)
→ needs_sl=True, force_write=False ✓
```

**TRB SHORT (loosen case — OLD BUG):**
```
current_sl=16.993, new_sl=16.945
new_sl < current_sl → False (loosening)
→ needs_sl=False (blocked) ✓
```

## Why Bug 4 Was the Last Fix

Bugs 1-3 were blockers that prevented ANY tightening. Bug 4 only manifests after bugs 1-3 are fixed — once tightening flows through, the loosen case can be observed. The `.pyc` bytecode cache was also found to be loading old unpatched code, compounding all four bugs.

## Files Modified

- `/root/.hermes/scripts/tpsl_utils.py` — 4 patches applied (lines 416, 432, 435, 436-443)
- `/root/.hermes/scripts/__pycache__/tpsl_utils.cpython-312.pyc` — deleted and regenerated

## Key Lesson

HL is the source of truth. When T says a position was open at time T and guardian logs say it wasn't, investigate WHY — 60s sync gap, brief sub-60s position, corrupted closing markers, DB INSERT failure. Never dismiss T's HL history as wrong. Also: **always clear bytecode cache after patching Python modules**, or `sys.modules` will serve stale `.pyc` files instead of the patched `.py` source.

## Related

- `references/short-loosen-gate-bug-2026-05-18.md` — Bug 4 detail doc
- `references/short-wrong-side-comparison-bug-2026-05-18.md` — Bug 3 detail doc