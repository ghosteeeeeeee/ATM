# Guardian Closing Markers — signal_compactor Integration

## The Feature

`hl-sync-guardian.py` writes `guardian-closing-markers.json` to mark tokens it is actively closing.
`signal_compactor.py` reads it (line ~108) to exclude those tokens from new signal execution —
defense-in-depth when PostgreSQL hasn't been updated yet (orphan case).

## File Format

Written by guardian as:
```json
{"tokens": {"ZK": {"started": "2026-05-04 21:34:12", "trade_id": 123, "pid": 9876}}, "saved_at": "..."}
```

## Bug Caught (2026-05-18)

The file was `[]` (a JSON list, not a dict). `signal_compactor.py` line ~108 did:
```python
guardian_closing = {k.lower() for k in data.get('tokens', {})}
```
Calling `.get()` on a list → `'list' object has no attribute 'get'` — warning fires but is non-fatal
(signal_compactor catches it, falls through, continues with empty `guardian_closing`).

## Fix Applied

Added type guard in `signal_compactor.py`:
```python
if not isinstance(data, dict):
    log(f"[WARN] Guardian closing markers file is corrupt (type={type(data).__name__}) — skipping", 'WARN')
    guardian_closing = set()
else:
    guardian_closing = {k.lower() for k in data.get('tokens', {})}
```

## Root Cause

`guardian-closing-markers.json` was written as a bare list `[]` instead of `{"tokens": {}}`.
Likely written by an older version of guardian, or a botched write. Current guardian code
writes a dict structure correctly (see `hl-sync-guardian.py` line ~387 `json.dump({'tokens': markers, ...})`).

## Status

Fix committed to `signal_compactor.py`. No data loss — guardian closing protection was
defense-in-depth only, PostgreSQL open-position query remains the primary defense.