# Bounce Gate Bug — June 14, 2026

## The Bug
Structural control-flow bug in rs.py support and resistance sections.

**Before fix (Jun 14 2026):**
```python
if not bounces:
    nearest_support = None   # ← hard gate: blocks everything below when bounces=False
else:
    if broken and price > level:
        broken = False
        bounces = True
        # Falls through
    if broken:
        ...  # BROKEN PATH — unreachable when bounces=False
    else:
        ...  # BOUNCE PATH
```

`if broken:` was nested inside `else: bounces`, making it unreachable when `bounces=False`. The `RS_BROKEN_SHORT_ENABLED=False` killswitch only worked when `bounces=True`.

**After fix:**
```python
# Reclassify first
if broken and price > level:
    broken = False
    bounces = True

if broken:
    ...  # BROKEN PATH — fires independently of bounce status
elif bounces:
    ...  # BOUNCE PATH — gated by bounce confirmation
```

## Why It Matters
- Pre-868add3: broken check ran independently → broken-path signals fired
- Post-868add3: bounce gate added → broken-path silently blocked
- `RS_BROKEN_SHORT_ENABLED` and `RS_BROKEN_RESISTANCE_LONG_ENABLED` were already `True` in constants, but the code path was unreachable
- The fix restores broken-path signals that existed before the refactor

## Both Sections Affected
- Support LONG path: lines ~622-680
- Resistance SHORT path: lines ~695-760

## Detection Pattern
When `RS_BROKEN_*_ENABLED` flags are set correctly but broken-level signals never appear in output — check the control flow, not the flag values.
