# RS Signal Bugs — Close-Only Data Pitfalls (2026-05-08)

## Files in scope
- Canonical: `/root/.hermes/scripts/signals/rs.py` (576 lines)
- Deprecated: `/root/.hermes/scripts/rs_signals.py` (552 lines) — NOT in pipeline
- Runner: `/root/.hermes/scripts/run_rs_signals.py` (152 lines) — NOT in pipeline

## Canonical path
```
run_pipeline.py → signals_runner.py → signals/__init__.py → signals/rs.py
```

## Key discovery: price_history is close-only

`_get_candles_1m()` (line 489):
```python
return [{'open': r[1], 'high': r[1], 'low': r[1], 'close': r[1]} for r in rows]
```
Every candle has `open == high == low == close`. This is the root cause of multiple
broken functions that assumed real OHLCV candles.

## Bug 1: `_level_recently_broken` — always returned False

**Original logic** (broken):
```python
for c in recent:
    opened = c['open']    # == close (close-only synthesis)
    closed = c['close']   # == open
    if opened < level < closed:  # impossible — open == close
        return True
```
**Fix**: Compare successive candle closes for level crossing:
```python
for i in range(1, len(recent)):
    prev_close = recent[i - 1]['close']
    curr_close = recent[i]['close']
    if prev_close < level < curr_close: return True  # resistance broken
    if prev_close > level > curr_close: return True  # support broken
```

## Bug 2: `_bounce_confirmation` — lookback guard off-by-one

**Wrong guard** (added during fix, caused test failures):
```python
if len(candles) < lookback + 1:  # rejects exactly lookback candles
    return False
```
**Correct guard**:
```python
if len(candles) < lookback:  # loop checks i+1 < len(recent) for safety
    return False
```
The loop safely handles the last candle via `if i + 1 < len(recent)`, so we only
need `len(candles) >= lookback`.

With `lookback=6`: 6 candles → `recent = candles[-6:]` (6 elements) →
`range(1, 6)` → i=1..5. `i=5` (last candle): `i+1=6 < 6` is False → loop body
skipped → no OOB. Correct.

## Bug 3: `high_touch` unused variable

```python
high_touch = abs(c['high'] - level)  # computed but never used
low_touch  = abs(c['low']  - level)   # only this was used
```
Removed `high_touch`. Also removed unused `window` parameter.

## Testing pattern: synthetic vs real data

Always test with both:
```python
# Synthetic close-only candles (reproduces the production bug)
candles = [{'close': 100}, {'close': 101}, {'close': 102.5}]
r = _level_recently_broken(candles, 101.5, lookback=3)
assert r == True  # cross up through 101.5

# Real data smoke test
candles = _get_candles_1m('BTC')
atr = _atr(candles)
sig = detect_rs_signal('BTC', candles, candles[-1]['close'])
```

## Python bytecode caching bug

Running `python3 -c "from signals.rs import ..."` after patching the `.py` file
can still load stale `.pyc` bytecode from `__pycache__/rs.cpython-312.pyc`.

**Fix**: Clear all pycache before testing:
```bash
find /root/.hermes/scripts/signals -name "__pycache__" -type d -exec rm -rf {} +
find /root/.hermes/scripts/signals -name "*.pyc" -delete
```

Also: `python3 -B` (disable .pyc writing) or `importlib.reload()` to force re-import.

## Verification commands

```bash
# Syntax check
python3 -m py_compile signals/rs.py

# Unit tests
python3 -c "
from signals.rs import _level_recently_broken, _bounce_confirmation

# _level_recently_broken: cross up
r = _level_recently_broken([{'close':100},{'close':101},{'close':102.5}], 101.5, lookback=3)
assert r == True, f'cross up: got {r}'

# _level_recently_broken: cross down
r = _level_recently_broken([{'close':103},{'close':102},{'close':101}], 101.5, lookback=3)
assert r == True

# _bounce_confirmation: LONG bounce
c = [{'close':100}]*2 + [{'close':99.9}, {'close':100.1}] + [{'close':100.2}]
r = _bounce_confirmation(c, 100.0, 'LONG', atr_value=1.0)
assert r == True

# Real data smoke test
from signals.rs import detect_rs_signal, _get_candles_1m
candles = _get_candles_1m('BTC')
price = candles[-1]['close']
sig = detect_rs_signal('BTC', candles, price)
print(f'BTC signal: {sig}')
"

# Live smoke test (30s timeout)
timeout 30 python3 -c "
from signals.rs import detect_rs_signal, _get_candles_1m, _atr, _find_swing_highs_lows, RS_LEVEL_LOOKBACK
token = 'BTC'
candles = _get_candles_1m(token)
print(f'Got {len(candles)} candles, ATR={_atr(candles):.4f}')
h, l = _find_swing_highs_lows(candles, RS_LEVEL_LOOKBACK)
print(f'Swing highs: {len(h)}, lows: {len(l)}')
sig = detect_rs_signal(token, candles, candles[-1]['close'])
print(f'Signal: {sig}')
"
```

## Other divergences: signals/rs.py vs rs_signals.py

| Feature | signals/rs.py (canonical) | rs_signals.py (deprecated) |
|---------|--------------------------|---------------------------|
| ATR band filter | Removed (deprecated) | Active (rejects 0.3–0.6 ATR) |
| `_level_recently_broken` | Close-cross logic | Wick-cross logic (broken) |
| `_bounce_confirmation` | ATR-normalized thresholds | Fixed 0.20% threshold |
| `_build_level_touches` | ATR-normalized | Fixed 0.15% |
| `signaled_tokens` return | `list[str]` | `list[str]` (correct) |
| RS_ENABLED check | Yes (line 499) | No |

Deprecated `rs_signals.py` is NOT in the live pipeline. Only `signals/rs.py` matters.
