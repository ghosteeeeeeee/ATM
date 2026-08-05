# RS Signal Fix — add_signal Missing source/confidence Args

## When (2026-05-14)

RS signal (range_sitter) completely silent. signal_compactor log showed 0 signals emitted despite RS having clear setups on chart.

## Root Cause

`rs.py` calls `add_signal()` with only 6 positional args:
```python
sid = add_signal(token, direction, signal_type, value, price, exchange)
```

But `signal_schema.add_signal()` signature requires:
```python
add_signal(token, direction, signal_type, source, confidence, value, price, exchange, ...)
```

The `source` (e.g. 'rs-s82') and `confidence` (0-100) were being passed as `value` and `price`. The schema then rejected the row silently — no exception, just a None return and no signal added.

## Fix Applied (rs.py lines ~667-671)

```python
# BEFORE (broken):
sid = add_signal(token, direction, 'range_sitter', value, price, 'hyperliquid')

# AFTER (fixed):
sid = add_signal(
    token=token,
    direction=direction,
    signal_type='range_sitter',
    source='rs-s82',
    confidence=75,
    value=value,
    price=price,
    exchange='hyperliquid',
)
```

## Verification

```bash
cd /root/.hermes/scripts
python3 -c "from signals.rs import run; n=run(); print(f'RS signals: {n}')"
# Should emit signals for tokens in range (RS_LEVEL=0.82)
```

## Pattern: Keyword Args Are Safer

When calling `add_signal()`, always use keyword args. The schema has 15+ parameters and relies on position for the first 6 then keywords — mixing styles causes silent failures.

```python
# Always use keyword args for add_signal
sid = add_signal(
    token=token,
    direction=direction,
    signal_type=signal_type,
    source=source,          # <-- often missed
    confidence=confidence,  # <-- often missed
    value=value,
    price=price,
    exchange=exchange,
)
```

## Related Signals with Same Pattern

Any signal that calls `add_signal()` directly is a potential candidate for this bug. Check:
- `signals/rs.py`
- `signals/accel_300.py`
- `signals/hzscore.py`
- `signals/momentum.py`