# signals/rs.py price=0 bug (2026-06-03)

## Bug Summary
All RS signals from `signals/rs.py` had `price=0` in the signals DB because `price` parameter was not passed to `add_signal()`.

Result: 52 pending LONGs with price=0 were rejected by the compactor price gate before reaching hot-set. SHORTs had a few with valid prices (5/59) that made it through.

## Root Cause
In `signals/rs.py` line ~774, the `add_signal()` call omits the `price` parameter:

```python
# BROKEN — signals/rs.py (the signals/ dir version)
sid = add_signal(
    token=token.upper(),
    direction=sig['direction'],
    signal_type=RS_SIGNAL_TYPE,
    source=sig['source'],
    confidence=sig['confidence'],
    # ← price=MISSING here
)

# CORRECT — rs_signals.py (top-level script version, line ~509)
sid = add_signal(
    token=token.upper(),
    direction=sig['direction'],
    signal_type=RS_SIGNAL_TYPE,
    source=sig['source'],
    confidence=sig['confidence'],
    value=sig['value'],
    price=price,   # ← present
    ...
)
```

Both files use the same `signal_schema.add_signal()`. The schema correctly writes `price` to the DB column. The bug is purely the missing argument in signals/rs.py.

## Detection
Check signals.json pending entries — if all RS LONGs have price=0 while SHORTs have varied prices, look at which rs.py file is being called. The signals/rs.py (signals/ subdir) is imported by signals_runner.py as `_rs_run`. The top-level rs_signals.py is imported by signal_gen.py directly.

## Fix
Add `price=price,` to the add_signal call in signals/rs.py at line ~774.

## Related
- Two near-identical RS signal implementations exist: signals/rs.py (signals/ package) and rs_signals.py (top-level script). The top-level one is correct; the signals/ package one is broken.
- Compactor price gate: rejects signals with price <= 0 before hot-set entry (lines ~338, ~409-414 in signal_compactor.py).