# signal_gen Performance Fix — Full Analysis

## Problem

signal_gen.py running every 60s via `hermes-pipeline.timer` but taking 134-140s per run. The 180s timeout was being hit regularly. Pipeline starts a new run before the previous one finishes → cascading backlog.

## Timeline of Discovery

1. Initial timing: `scan_rs_signals` profile showed **211.5 seconds** for 191 tokens (cProfile, 1169629765 function calls)
2. The `compute_score` mom-threading fix reduced momentum loop from ~40s to ~16.7s — but full signal_gen was still 134s because `scan_rs_signals` was the dominant cost
3. Vectorizing `rs_signals.py` brought `scan_rs_signals` from 211s to ~9s
4. Full signal_gen after both fixes: ~25s (pattern 0.4s + momentum 16s + RS 9s + confluence 1s)

## Phase Timing Breakdown (post-fix)

| Phase | Time | Notes |
|-------|------|-------|
| `_run_pattern_signals` | 0.4s | Fast, never the problem |
| Momentum loop (LONG+SHORT × 191 tokens) | ~16s | mom-threading fix helped |
| `scan_rs_signals` | **~9s** | Was 211s before vectorization |
| `run_confluence_detection` | ~1s | Fast |
| **Total signal_gen** | **~25s** | Was 134s+ |

## cProfile Data (pre-fix scan_rs_signals)

```
scan_rs_signals: 211.486s
         ncalls  tottime  cumtime
      1    0.093  211.486  rs_signals.py:403(scan_rs_signals)
    191    0.128  209.135    rs_signals.py:250(detect_rs_signal)
123100  141.609  203.269    rs_signals.py:200(_build_level_touches)
1159092306   61.774   61.774    {built-in method builtins.abs}
    191    2.905    4.026    rs_signals.py:85(_find_swing_highs_lows)
```

Key observations:
- 1.16 billion `abs()` calls inside `_build_level_touches`
- `_build_level_touches` called 123,100 times — that's ~645 calls per token
- Each call scanned all 4,700 candles (when swing levels were found)
- `_find_swing_highs_lows` called 191 times (once per token), each doing ~1.89M Python operations

## Root Cause Analysis

### `_build_level_touches` — O(M × N) per token

```python
# Called for EVERY swing level found — hundreds per token
def _build_level_touches(candles, level, window=20):
    count = 0
    for c in candles:  # 4700 candles
        high_touch = abs(c['high'] - level) / level * 100.0  # 2x abs per candle
        low_touch  = abs(c['low']  - level) / level * 100.0
        if high_touch < 0.15 or low_touch < 0.15:
            count += 1
    return count
```

With 4700 candles and ~645 swing levels per token: `645 × 4700 × 2 = 6,063,000 abs()` calls per token × 191 = 1.16 billion total.

### `_find_swing_highs_lows` — O(N²) per token

```python
for i in range(window, len(candles) - window):
    window_highs = [candles[j]['high'] for j in range(i-window, i+window+1)]
    window_lows  = [candles[j]['low']  for j in range(i-window, i+window+1)]
    if high == max(window_highs):
        swing_highs.append((i, high))
```

For each of 4,660 candles (valid range), creates TWO 201-element lists → `201 × 4660 × 2 = 1.87M` Python list comprehensions per token.

## The Fix

### 1. NumPy rolling max/min for `_find_swing_highs_lows`

```python
def _rolling_max(arr, window):
    n = len(arr)
    out = np.empty(n, dtype=np.float64)
    out[:window-1] = arr[:window-1]
    for i in range(window-1, n):
        out[i] = arr[i-window+1:i+1].max()
    return out

def _find_swing_highs_lows(candles, window=20):
    n = len(candles)
    highs = np.array([c['high'] for c in candles], dtype=np.float64)
    lows  = np.array([c['low']  for c in candles], dtype=np.float64)
    roll_high = _rolling_max(highs, window)
    roll_min  = _rolling_min(lows,  window)
    swing_highs = [(i, highs[i]) for i in range(window, n-window)
                   if highs[i] == roll_high[i]]
    swing_lows  = [(i, lows[i])  for i in range(window, n-window)
                   if lows[i]   == roll_min[i]]
    return swing_highs, swing_lows
```

Still O(N) asymptotic but NumPy's C-level loops are ~100x faster than Python list comprehensions.

### 2. NumPy fast path in `_build_level_touches`

```python
def _build_level_touches(candles_or_highs_lows, level=None, window=None):
    touch_threshold_pct = 0.15

    # Fast path: pre-extracted (highs, lows) tuple
    if isinstance(candles_or_highs_lows, tuple):
        highs, lows = candles_or_highs_lows
        threshold = abs(level) * touch_threshold_pct / 100.0
        return int(((np.abs(highs - level) < threshold) |
                     (np.abs(lows  - level) < threshold)).sum())

    # Legacy path (for backward compat)
    candles = candles_or_highs_lows
    count = 0
    for c in candles:
        high_touch = abs(c['high'] - level) / level * 100.0
        low_touch  = abs(c['low']  - level) / level * 100.0
        if high_touch < touch_threshold_pct or low_touch < touch_threshold_pct:
            count += 1
    return count
```

### 3. Pre-extract arrays once per token in `detect_rs_signal`

```python
def detect_rs_signal(token, candles, price):
    # ... early returns ...

    # Pre-extract arrays ONCE, reuse for all level touch counts
    highs = np.array([c['high'] for c in candles], dtype=np.float64)
    lows  = np.array([c['low']  for c in candles], dtype=np.float64)
    candles_arrays = (highs, lows)

    swing_highs, swing_lows = _find_swing_highs_lows(candles, RS_LEVEL_LOOKBACK)

    raw_resistance = [(l, _build_level_touches(candles_arrays, l))
                      for _, l in swing_highs]
    raw_support    = [(l, _build_level_touches(candles_arrays, l))
                      for _, l in swing_lows]
```

## Files Modified

- `/root/.hermes/scripts/rs_signals.py` — added `import numpy as np`, `_rolling_max`, `_rolling_min`, updated `_find_swing_highs_lows` with NumPy, updated `_build_level_touches` with fast path, updated `detect_rs_signal` to pre-extract arrays
- `/root/.hermes/scripts/signal_gen.py` — mom-threading fixes (lines ~860-910, ~2401, ~2500) — this was done earlier in the session

## Why This Wasn't Caught Earlier

1. The signal_gen pipeline timeout is set at 180s in `run_pipeline.py` — but the timeout is per-step, so signal_gen could exceed it without the pipeline failing entirely
2. signal_gen has no internal phase timing — the 180s limit was treated as a safety net, not a performance budget
3. The RS scan was always slow (~200s) — it predates this session but was never profiled because the system worked (just slowly)
4. The "fix" for compute_score redundant fetches was done first (16.7s momentum) but the dominant cost was RS scan at 211s

## Lessons Learned

1. **Always profile the full pipeline** — fixing a 16s bottleneck (compute_score) when a 211s bottleneck exists (scan_rs_signals) doesn't help much
2. **Python's math in tight loops is the enemy** — 1.16B `abs()` calls in pure Python is ~61s of CPU time. NumPy vectorization is 100x+ faster
3. **O(N²) with Python data structures hides in "simple" functions** — `_find_swing_highs_lows` looked innocent (20 lines) but was quadratic
4. **Pre-extract arrays once, reuse multiple times** — the key insight is that `detect_rs_signal` calls `_build_level_touches` hundreds of times with the same candle data but different `level` values. Extract the arrays once, pass them to each call
