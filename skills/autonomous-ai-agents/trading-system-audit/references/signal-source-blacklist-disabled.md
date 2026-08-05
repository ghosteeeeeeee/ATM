# SIGNAL_SOURCE_BLACKLIST — Critical Bug Reference

## The Bug (2026-05-08)

**File:** `hermes_constants.py` lines 87-101

```python
SIGNAL_SOURCE_BLACKLIST = {
    # ALL ENTRIES COMMENTED OUT 2026-05-05
    # Comment claims: "Redundant with Layer 2 kill-switches in signal_schema.py add_signal()"
```

`signal_schema.add_signal()` checks `source in SIGNAL_SOURCE_BLACKLIST`, but since the set is `{}` (empty), nothing is ever blocked. All the sources that should be blocked flow freely to the hot-set.

## Why It Was Missed

- Prior audits timed out (600s worker limits) before reaching `hermes_constants.py`
- The comment "Redundant with Layer 2" was taken at face value
- `signal_schema.py:add_signal()` does check the blacklist, but it does nothing when the set is empty

## Sources That Should Be Blocked

Based on comment at hermes_constants.py:101-130:
- `pct-hermes-` — catches falling knives (short at bottom of range)
- `pct-hermes+` — catches topping (long at top of range)
- `vel-hermes-` — inverted velocity signal
- `vel-hermes+` — inverted velocity signal
- `hzscore+`, `hzscore-`, `hzscore` — solo hzscore without confluence
- `pattern_scanner` — historically catastrophic win rate

## Verification Command

```bash
grep -A 50 "SIGNAL_SOURCE_BLACKLIST" /root/.hermes/scripts/hermes_constants.py | head -20
# Should show active set members, not all-commented
```

## Fix Required

Restore active set members in `SIGNAL_SOURCE_BLACKLIST = {}`. The comment claims redundancy with `signal_schema.py` but that protection is only as good as the set itself.
