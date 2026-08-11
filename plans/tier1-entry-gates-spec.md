# Tier 1 Entry Gate Utilities — Spec

**Created:** 2026-08-11
**Status:** Ready for implementation
**File:** `scripts/entry_gates.py`

---

## Overview

Four shared utility functions that every signal calls before emitting via `add_signal()`.
Each gate returns `True` (pass) or `False` (block). Signals opt-in by calling the gate
after their logic fires but before `add_signal()`.

All gates are fail-open: if data is missing or an exception occurs, the gate passes.
This prevents utility bugs from killing the entire signal pipeline.

---

## Gate 1: R:R Pre-Check

**Purpose:** Suppress signals where the reward-to-risk ratio is below threshold.

**Signature:**
```python
def rr_gate(token: str, direction: str, price: float, candles_5m: list = None) -> tuple:
    """
    Returns (pass: bool, sl: float, tp: float, rr: float)
    - pass=True means signal should emit
    - pass=False means signal should be suppressed
    - sl/tp are the computed stop-loss and take-profit prices
    - rr is the ratio (reward / risk)
    """
```

**Logic:**
1. Fetch ATR from `atr_cache.json` (reuse existing `_get_cached_atr()` pattern)
2. If ATR unavailable, use `ATR_PCT_FALLBACK = 3%` from hermes_constants
3. SL distance = `ATR_SL_MIN` (1.2%) from hermes_constants — conservative floor
4. TP distance = nearest S/R level if available, else `ATR_TP_MIN` (0.8%)
5. To find nearest S/R: query `rs.py` levels or scan recent swing highs/lows from candles_5m
6. R:R = TP distance / SL distance
7. If `rr < MIN_RR_RATIO` (2.0 from books), return `(False, 0, 0, rr)`
8. Otherwise return `(True, sl_price, tp_price, rr)`

**Constants (add to hermes_constants.py):**
```python
ENTRY_RR_MIN_RATIO = 2.0     # minimum R:R to allow entry (9/15 books)
ENTRY_RR_SL_ATR_MULT = 1.0   # SL = 1.0 × ATR
ENTRY_RR_USE_S_R = True      # prefer nearest S/R as TP target
```

**Data sources:**
- ATR: `atr_cache.json` (existing)
- S/R levels: `rs.py` swing detection (reuse `detect_swings()` logic) or candles_5m recent highs/lows

**Books:** Porwal (all), Heitkoetter (2:1), Woods (nearest S/R), Trader Tom (1:2)

---

## Gate 2: Volume Confirmation

**Purpose:** Require above-average volume on the signal candle.

**Signature:**
```python
def volume_gate(candles: list, min_ratio: float = 1.2, lookback: int = 20) -> bool:
    """
    Returns True if current candle volume >= min_ratio × average volume.
    Fail-open: returns True if volume data is missing or insufficient.
    """
```

**Logic:**
1. Extract volume from last `lookback` candles
2. Filter out zero-volume candles
3. Compute average volume (excluding current candle)
4. Compare current candle volume to average
5. Return `current_vol >= avg_vol * min_ratio`
6. Fail-open: if < 20 candles or all zero volume → return True

**Constants:**
```python
ENTRY_VOLUME_MIN_RATIO = 1.2   # current vol must be 1.2× average (10/15 books)
ENTRY_VOLUME_LOOKBACK = 20     # candles for average
```

**Second function (Wyckoff continuation):**
```python
def volume_dryup_gate(candles: list, lookback: int = 5) -> bool:
    """
    Returns True if volume is declining (good for continuation signals).
    Wyckoff: volume drying on pullback = bullish continuation.
    """
```

**Books:** Porwal (all strategies), Wyckoff (absorption), Woods (trend volume), Carli (divergence confirmation)

---

## Gate 3: Candle Close Confirmation

**Purpose:** Only use the last confirmed (closed) candle, not the one still forming.

**Signature:**
```python
def candle_close_gate(candles: list, timeframe_seconds: int = 60) -> list:
    """
    Returns candles[:-1] if the last candle is still forming.
    Returns candles unchanged if the last candle is confirmed closed.
    Fail-open: returns original candles on error.
    """
```

**Logic:**
1. Check age of last candle (timestamp vs now)
2. If `age < timeframe_seconds` → candle still forming → skip it
3. Return `candles[:-1]` (use only confirmed closes)
4. Fail-open: on error, return original candles

**Also available as boolean check:**
```python
def is_candle_closed(candle: dict, timeframe_seconds: int = 60) -> bool:
    """Returns True if candle is old enough to be confirmed closed."""
```

**Constants:**
```python
ENTRY_CANDLE_CLOSE_ENABLED = True      # master switch
ENTRY_CANDLE_CLOSE_BUFFER_SEC = 10     # extra seconds to wait after close
```

**Books:** Carli ("wait for candle close"), Porwal ("must wait for close"), Warrior Trading ("wait for candle close"), Woods ("wait for candle close")

---

## Gate 4: Session Timing

**Purpose:** Suppress signals during low-quality time windows.

**Signature:**
```python
def session_timing_gate() -> bool:
    """
    Returns True if current time is a good session to trade.
    Returns False if we should skip (choppy/low-liquidity window).
    Fail-open: returns True on error.
    """
```

**Logic:**
1. Get current UTC time
2. Sunday 00:00–06:00 UTC → False (crypto low liquidity)
3. All other times → True
4. Fail-open: on error, return True

**Constants:**
```python
ENTRY_SESSION_FILTER_ENABLED = True      # master switch
ENTRY_SESSION_BLOCK_SUNDAY_HOURS = (0, 6)  # block Sunday 00:00-06:00 UTC
```

**Books:** Heitkoetter ("avoid first 30 min"), Warrior Trading ("avoid first 30 min"), Ozenbas ("avoid first/last 30 min"), Trader Tom ("avoid first 30 min")

---

## Integration Pattern

Each signal calls gates after detection, before `add_signal()`:

```python
# In scan_*_signals(), after detecting signal:
from entry_gates import rr_gate, volume_gate, candle_close_gate, session_timing_gate

# Gate 1: Session timing
if not session_timing_gate():
    continue

# Gate 2: Candle close (use only confirmed closes for detection)
candles = candle_close_gate(raw_candles, timeframe_seconds=60)

# Gate 3: Volume
if not volume_gate(candles, min_ratio=ENTRY_VOLUME_MIN_RATIO):
    continue

# Gate 4: R:R (needs price + direction + token)
rr_pass, sl, tp, rr = rr_gate(token, direction, price)
if not rr_pass:
    continue

# All gates passed — emit signal
add_signal(...)
```

---

## File Location

New file: `/root/.hermes/scripts/entry_gates.py`

All imports from existing code:
- `from paths import *`
- `from hermes_constants import ATR_SL_MIN, ATR_TP_MIN, ATR_PCT_FALLBACK`
- ATR cache: `json.load(open(ATR_CACHE_FILE))`

---

## Testing

Each gate has a `__main__` block for manual testing:

```bash
python3 scripts/entry_gates.py rr ETH LONG 3500
python3 scripts/entry_gates.py volume ETH
python3 scripts/entry_gates.py close ETH 60
python3 scripts/entry_gates.py session
```

---

## Implementation Order

1. **candle_close_gate** — simplest, no data deps, trivial
2. **session_timing_gate** — datetime only, trivial
3. **volume_gate** — needs candle volume data, straightforward
4. **rr_gate** — most complex, needs ATR + S/R, build last
