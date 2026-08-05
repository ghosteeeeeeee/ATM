# Stale Marker Cleanup Order Bug — 2026-05-20

## Symptom
`[OPEN-POS-FILTER] Guardian closing markers active: ['ada', 'mon', 'strk', 'tia']` persisting across all signal_compactor cycles, even though no positions are open in PostgreSQL or HL.

## Root Cause
In `sync()` at line 3524-3528, stale marker cleanup ran **before** `hl_pos` was fetched (before Step 1):

```python
# Line 3518-3530 — WRONG ORDER
try:
    stale_markers = _load_closing_markers()
    for tok in list(stale_markers.keys()):
        if tok not in hl_pos:   # <-- hl_pos was {} at this point!
            log(f'[STALE-MARKER] {tok} no longer in HL — clearing closing marker')
            _clear_closing_marker(tok)
except Exception:
    pass

log(f'── Sync cycle ──')

# Step 1: Get HL positions (retry on rate-limit → empty dict)
hl_pos = {}
for attempt in range(4):
    try:
        hl_pos = get_open_hype_positions_curl()
        if hl_pos:
            break
        ...
    except Exception as e:
        ...
if not hl_pos:
    log('HL still returning empty — skipping this cycle')
    return   # <-- Orphan close never reached!
```

When HL was rate-limited and returned `{}`, the stale marker cleanup saw `hl_pos = {}` and concluded ALL markers were stale (token not in empty set = True). All markers cleared. Then the cycle skipped because HL was empty. Orphan close never ran. Next cycle: same thing → markers keep reappearing.

## The Fix
Move stale marker cleanup to AFTER `hl_pos` is populated (after Step 1, around line 3563):

```python
# Step 1: Get HL positions (retry on rate-limit → empty dict)
hl_pos = {}
for attempt in range(4):
    ...

if not hl_pos:
    log('HL still returning empty — skipping this cycle')
    return

# Stale marker cleanup — AFTER hl_pos is populated (not before).
# When HL was rate-limited and returned {}, all markers were incorrectly cleared
# as stale before the orphan close could run, causing the closing marker bug.
try:
    stale_markers = _load_closing_markers()
    for tok in list(stale_markers.keys()):
        if tok not in hl_pos:
            log(f'  [STALE-MARKER] {tok} no longer in HL — clearing closing marker')
            _clear_closing_marker(tok)
except Exception:
    pass
```

Now when HL is rate-limited, no cleanup runs (markers preserved). When HL returns real positions, cleanup only clears markers for tokens truly gone from HL.

## Files Modified
- `hl-sync-guardian.py`: stale marker cleanup moved from line ~3518 to line ~3563 (after Step 1)

## Verification
- `cat /root/.hermes/data/guardian-closing-markers.json` → FILE GONE after fix (no stale markers)
- Marker file deleted manually: `rm -f /root/.hermes/data/guardian-closing-markers.json`
- Guardian running: `pgrep -f hl-sync-guardian.py`