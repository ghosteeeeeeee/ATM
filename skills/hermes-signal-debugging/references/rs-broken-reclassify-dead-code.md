# rs.py broken-level reclassification — dead code bug

## The Bug (rs.py lines 554-562 and 618-625)

### Pattern: reclassify placed INSIDE the `if broken:` block

**Wrong (current code):**
```python
if broken:
    # Was the level broken but price recovered?
    if price > level:          # ← unreachable when broken=True AND price<level simultaneously
        broken = False
        bounces = True

    if broken:                  # ← always True here; reclassify above has no effect
        # fire signal and return
```

**Correct (intended logic):**
```python
if broken:
    # Reclassify BEFORE deciding signal direction
    if price > level:
        broken = False
        bounces = True
        # fall through to normal bounce signal path
    else:
        # fire broken-signal and return

if not broken:
    # normal bounce path — now reachable after reclassify
```

### Why the current code is dead

`broken=True` means `_level_recently_broken` returned True. For a support level this means price crossed BELOW it. For a resistance level it means price crossed ABOVE it.

- Support broken (`broken=True`): price is BELOW level. Check `if price > level` can NEVER be true. Dead.
- Resistance broken (`broken=True`): price is ABOVE level. Check `if price < level` can NEVER be true. Dead.

The reclassify was clearly intended to handle pullback/reclaim scenarios but the placement makes it unreachable.

## rs-s-broken and rs-r-broken signal map

| Level type | Price condition | `broken` flag | Signal direction |
|---|---|---|---|
| Support | price < level (below broken support) | True | SHORT (fires and returns) |
| Support | price > level (price reclaimed) | reclassify False | falls through → bounce LONG |
| Resistance | price > level (above broken resistance) | True | LONG (fires and returns) |
| Resistance | price < level (price fell back below) | reclassify False | falls through → rejection SHORT |

The bottom-right cell (resistance broken but price fell back = should fire SHORT) is BROKEN because the reclassify can never fire for resistance.

## Execution evidence (2026-06-03)

- `rs-s-broken` SHORTs in executed: 10, all fired correctly as SHORT
- `rs-r-broken` LONGs in executed: 0 (correct — no resistance levels were broken while price was above them in this dataset)
- `rs-r-broken SHORT`: 0 in pending/executed — the broken-returns-below path can never fire
- `rs-s-broken LONG`: 0 in pending/executed — the broken-returns-above path can never fire

## Fix approach

Move the price-context check OUTSIDE the `if broken:` block so the reclassify can redirect to the normal path:

```python
# Check if broken level was reclassified
if broken and price > level:     # support: broken but price recovered
    broken = False
    bounces = True
elif broken and price < level:    # resistance: broken but price fell back
    broken = False
    # don't set bounces — want rejection SHORT, not bounce LONG

if broken:
    # fire broken-level signal (SHORT for support, LONG for resistance)
    ...
else:
    # fire normal signal using reclassified bounces flag
    ...
```

Then the normal path (lines 588-607 and 651-673) will be reached with the correct bounces flag set.