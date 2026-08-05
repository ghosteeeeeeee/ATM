# Guardian Closing Marker Corruption (2026-05-17)

## Symptom

Guardian log shows repeated:
```
[WARN]   [_save_closing_marker] FAILED for {token}: 'list' object has no attribute 'get'
```

All closing markers are silently lost. Tokens that should be blocked by `guardian-closing-markers.json` can re-enter.

## Root Cause

`_load_closing_markers()` reads `guardian-closing-markers.json` and returns `data.get('tokens', {})`.

If the file was ever written as a raw list `[]` instead of `{"tokens": {...}}`:
1. `json.load()` returns a list `[]`
2. `data.get('tokens', {})` on a list → `AttributeError: 'list' object has no attribute 'get'`
3. Exception caught → returns `{}` (empty dict)
4. All closing markers silently lost

The write path (`_save_closing_marker`) was correct — it wrote `{'tokens': markers, ...}` — but corruption could occur if:
- A prior version of the code wrote the wrong structure
- Manual edit corrupted the file
- A race condition wrote an incomplete structure

## Fix Applied

`hl-sync-guardian.py` `_load_closing_markers()` now validates structure:

```python
def _load_closing_markers() -> dict:
    """Load the current closing markers dict. Defensive: validates structure."""
    try:
        with open(_GUARDIAN_CLOSING_FILE) as f:
            data = json.load(f)
        if not isinstance(data, dict):
            log(f'  [_load_closing_markers] CORRUPTED file (type={type(data).__name__}) — resetting', 'WARN')
            return {}
        tokens = data.get('tokens', {})
        if not isinstance(tokens, dict):
            log(f'  [_load_closing_markers] CORRUPTED tokens (type={type(tokens).__name__}) — resetting', 'WARN')
            return {}
        return tokens
    except (FileNotFoundError, json.JSONDecodeError):
        return {}
```

Now if file is corrupted, it logs a WARN and resets to `{}`. The `_save_closing_marker` write path remains unchanged — it will rewrite the correct structure next time a marker is saved.

## Verification

```bash
# Check current state of closing markers
cat /root/.hermes/data/guardian-closing-markers.json | python3 -m json.tool

# Should be {"tokens": {...}} not [...]
# If it's [], the fix auto-resets it on next guardian run

# Check for the corruption warning in guardian logs
grep "_load_closing_markers.*CORRUPTED" /root/.hermes/logs/sync-guardian.log
```