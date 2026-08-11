# Signal Entry Timing Improvements — Book-Informed Plan

**Created:** 2026-08-11
**Source:** Cross-referenced 15 trading books against 20 active Hermes signals
**Goal:** Better trade entry timing using evidence-based strategies from trading literature

---

## Source Books

| # | Book | Key Entry Concept |
|---|------|-------------------|
| 1 | Sadowski — 9 Advanced Strategies | MA crossover, Heikin-Ashi, RSI divergence, Bollinger touch + trend |
| 2 | CFI — Complete Guide to Trading | Fundamental+technical alignment, confirmed breakouts with volume |
| 3 | Heitkoetter — Day Trading | Confirmed range breakout, avoid first 30 min, 2:1 R:R min |
| 4 | Warrior Trading — Day Trading Beginners | Confirmed pattern at S/R, wait for candle close, limit orders |
| 5 | Carli — Power of Divergence | CCI divergence at extremes + trendline break confirmation |
| 6 | Trader Tom — First Trading Manual | Candlestick patterns at key levels, pullback entries in trends |
| 7 | Ozenbas — Liquidity Markets | Narrow spread, order book S/R, limit orders in illiquid |
| 8 | Woods — Price Action | Context + Pattern + Confluence, pin bar at S/R, inside bar |
| 9 | Porwal — 10 Profitable Strategies | Inside Bar, Doji, Engulfing, Trendline Breakout, ADX+EMA |
| 10 | Smith — Short Swing Trading | SST methodology, pattern completion + volume |
| 11 | Larry Swing — Swing Trading | Master Plan signal, daily close confirmation, trade above 50 MA |
| 12 | Cardoza — System Development | Backtested edge, ATR trailing, Monte Carlo expectancy |
| 13 | Aziz & Baehr — Trading Psychology | Pre-defined rules only, break after 3 losses |
| 14 | Bennet — Trading Volatility | IV rank entries, volatility mean reversion, straddle/strangle |
| 15 | Wyckoff — Day Trader's Bible | Accumulation/distribution, spring/test, volume absorption |

---

## Current Signal Inventory (Active)

| Signal | Entry Method | Has Volume | Has R:R | Has Trend Filter | Has Candle Close |
|--------|-------------|-----------|---------|-----------------|-----------------|
| hzscore | MTF z-score agreement | No | No | Regime | No |
| bb_bounce | BB band touch + RSI + 1H EMA | No | No | 1H EMA20/50 | No |
| bb_bounce_short | BB touch + RSI + regime | Optional | No | 1H EMA20/50 | No |
| return_exhaustion | Percentile extreme + momentum div | No | No | 1H return | No |
| return_exhaustion_short | Tighter percentile + regime | Optional | No | Regime | No |
| range_breakout | BB squeeze + retest + bounce | No | No | 1H trend | No |
| momentum_leaderboard | Top movers + confluence | No | No | 5m trend | No |
| continuation | Re-entry after profitable close | No | No | 1H trend | No |
| engulfing | Tight range + big move + volume | **Yes** (1.5x) | No | No | No |
| macd_1m | Tuned MACD crossover | No | No | No | No |
| phase_accel | Momentum phase transition | No | No | Phase state | No |
| fast_momentum | 5m z-score acceleration | No | No | No | No |
| mtf_macd | 1H z-score + MTF histogram | No | No | MTF alignment | No |
| vortex_break | VI crossover + ADX>20 + EMA | No | No | EMA20 | No |
| momentum | Composite score (z+vel+phase+regime+RSI+MACD) | No | No | Regime | No |
| tl_break_short | Diagonal trendline break | No | No | Linear regression | No |
| counter_flip | MTF alignment flip vs open pos | No | No | MTF MACD | No |
| rs | Swing S/R bounce | No | No | 5m regime | No |
| ma_100_cross_long | 100 MA cross on 1m | No | No | No | No |
| ma_100_cross_short | 100 MA cross on 1m | No | No | No | No |

---

## TIER 1 — Universal Fixes (apply to ALL signals)

### 1. R:R Pre-Check Gate

**Problem:** 9/15 books require min 2:1 R:R before entry. Zero of our 20 signals compute R:R before emitting. Signals fire blindly and rely on ATR-based SL/TP downstream.

**Book Evidence:**
- Porwal: "Min R:R = 1:2" across all strategies
- Heitkoetter: "2:1 R:R minimum, trail stop at 1:1 after profit"
- Woods: "Target: nearest S/R level (highest probability)"
- Trader Tom: "1:2 min R:R, ATR-based sizing"

**Implementation:**
```python
# Shared utility in signal_schema.py or new entry_utils.py
def check_rr(price, atr, direction, s уровни=None):
    """
    Compute R:R before emitting signal.
    SL = ATR-based (existing ATR_SL_MIN/MAX from hermes_constants)
    TP = nearest S/R level or ATR-based TP
    Returns (rr_ratio, sl_price, tp_price) or None if below threshold
    """
    sl_distance = atr * ATR_SL_MULT  # from hermes_constants
    tp_distance = atr * ATR_TP_MULT
    
    if s уровни:
        # Use nearest S/R as target (Woods: "nearest S/R = highest probability")
        tp_distance = min(abs(price - s уровни), tp_distance)
    
    rr = tp_distance / sl_distance
    if rr < MIN_RR_RATIO:  # 2.0 from books
        return None
    
    sl = price - sl_distance if direction == 'long' else price + sl_distance
    tp = price + tp_distance if direction == 'long' else price - tp_distance
    return (rr, sl, tp)
```

**Priority:** CRITICAL — affects all signals
**Effort:** Small — one utility function, call from each signal

---

### 2. Volume Confirmation Utility

**Problem:** 10/15 books treat volume confirmation as mandatory. Only `engulfing` has it. 7/8 key signals lack volume gates.

**Book Evidence:**
- Porwal: "Volume spike on signal day" for all strategies
- Wyckoff: "Volume with no price progress = absorption (reversal imminent)"
- Woods: "Volume increases in trend direction, dries up against it"
- Carli: "Volume confirmation required for divergence"

**Implementation:**
```python
# Shared utility
def check_volume(candles, min_ratio=1.2):
    """
    Require current volume > min_ratio × average volume.
    Returns True if volume confirms, False otherwise.
    """
    if len(candles) < 20:
        return True  # not enough data, don't block
    avg_vol = np.mean([c['volume'] for c in candles[-20:]])
    current_vol = candles[-1]['volume']
    return current_vol >= avg_vol * min_ratio

def check_volume_dryup(candles, lookback=5):
    """
    Wyckoff: volume drying up on pullback = bullish continuation.
    Returns True if volume is declining (good for continuation signals).
    """
    recent = [c['volume'] for c in candles[-lookback:]]
    return all(recent[i] <= recent[i-1] for i in range(1, len(recent)))
```

**Priority:** CRITICAL — second biggest quality uplift
**Effort:** Small — one utility, signals opt-in

---

### 3. Candle Close Confirmation Gate

**Problem:** 6/15 books say "wait for candle close, not just wick." Most signals use live price (wick-based) rather than confirmed close.

**Book Evidence:**
- Carli: "Conservative: wait for candle close beyond trendline"
- Porwal: "Must wait for close to avoid fake breakouts"
- Woods: "Wait for candle close, not just wick"
- Warrior Trading: "Wait for candle close, limit orders only"

**Implementation:**
```python
def is_candle_closed(candle, max_age_seconds=60):
    """
    Check if candle is actually closed (not still forming).
    Returns True if candle is closed and safe to use for entry.
    """
    candle_time = candle['timestamp']
    now = time.time()
    return (now - candle_time) >= max_age_seconds

def require_closed_candle(candles, tf_seconds):
    """
    Use only the last CLOSED candle (not the current forming one).
    Returns candles[:-1] (exclude current forming candle).
    """
    return candles[:-1] if len(candles) > 1 else candles
```

**Priority:** HIGH — prevents fakeout entries
**Effort:** Trivial — one check per signal

---

### 4. Session Timing Filter

**Problem:** 5/15 books say avoid first 30 min of session (choppy). No signals filter by time of day.

**Book Evidence:**
- Heitkoetter: "Avoid first 30 min of session"
- Warrior Trading: "Start with 10-20 shares, avoid first 30 min"
- Ozenbas: "Avoid first/last 30 min"
- Trader Tom: "Avoid first 30 min (choppy)"

**Implementation:**
```python
def is_good_session_time():
    """
    Filter out low-quality trading windows.
    For crypto: avoid Sunday 00:00-06:00 UTC (low liquidity)
    For any: avoid first 30 min after major session open.
    """
    now = datetime.utcnow()
    # Sunday early morning = low liquidity
    if now.weekday() == 6 and now.hour < 6:
        return False
    return True
```

**Priority:** MEDIUM — quality filter
**Effort:** Trivial — one check

---

## TIER 2 — Signal-Specific Improvements

### 5. return_exhaustion + Divergence at S/R (Carli Framework)

**Problem:** Fires on percentile extremes anywhere, not at key S/R levels. No trendline break confirmation. Pure momentum divergence without structure.

**Carli's Rules (from book):**
1. Divergence must form in extreme zones (CCI below -150 or above +150)
2. Second price peak must have Fibonacci extension of 1.13-1.618 of last retracement
3. Divergence alone ≠ signal — need trendline break confirmation
4. Min 2 bars between divergence points

**Proposed Fix:**
- Add S/R proximity check (reuse `rs.py` levels)
- Require price structure break (trendline or swing) after divergence forms
- Add candle pattern confirmation (pin bar, engulfing at extreme)
- Add volume divergence (declining volume on move = exhaustion)

**Priority:** HIGH — return_exhaustion is a key signal
**Effort:** Medium — needs S/R data feed + structure break detection

---

### 6. rs.py + Candle Patterns at Levels

**Problem:** Our S/R signal detects bounces but doesn't check what candle pattern formed at the bounce. Books say candle pattern at S/R = highest probability entry.

**Book Evidence:**
- Woods: "Pin bar at support = bullish → buy above pin bar high"
- Porwal: "Engulfing at support → buy above pattern"
- Porwal: "Doji at overbought/oversold → entry on break of doji"

**Proposed Fix:**
```python
# After detecting bounce from S/R in rs.py, check candle pattern:
def detect_candle_pattern(candle, prev_candle):
    """Detect high-probability patterns at S/R levels."""
    body = abs(candle['close'] - candle['open'])
    upper_wick = candle['high'] - max(candle['open'], candle['close'])
    lower_wick = min(candle['open'], candle['close']) - candle['low']
    total_range = candle['high'] - candle['low']
    
    if total_range == 0:
        return None
    
    # Pin bar: long wick (>2/3 of range), small body (<1/3)
    if lower_wick > total_range * 0.66 and body < total_range * 0.33:
        return 'bullish_pin_bar'
    if upper_wick > total_range * 0.66 and body < total_range * 0.33:
        return 'bearish_pin_bar'
    
    # Engulfing: body > previous body, opposite direction
    prev_body = abs(prev_candle['close'] - prev_candle['open'])
    if body > prev_body:
        if prev_candle['close'] < prev_candle['open'] and candle['close'] > candle['open']:
            return 'bullish_engulfing'
        if prev_candle['close'] > prev_candle['open'] and candle['close'] < candle['open']:
            return 'bearish_engulfing'
    
    # Doji: very small body (<10% of range)
    if body < total_range * 0.10:
        return 'doji'
    
    return None
```

**Priority:** HIGH — rs.py is our structural signal
**Effort:** Medium — needs candle pattern detection + integration

---

### 7. engulfing.py Fixes

**Problem:** No S/R proximity, no trend alignment, no proper body-vs-body engulfing check.

**Proposed Fixes:**
- Add S/R proximity gate (reuse `rs.py` levels)
- Add trend alignment filter (check 1H EMA20/50)
- Fix engulfing detection: current body must > previous body (not just move %)
- Add candle close confirmation

**Priority:** MEDIUM
**Effort:** Small

---

### 8. vortex_break.py Fixes

**Problem:** No volume, fires on stale crossovers (5-bar window), no retest confirmation.

**Book Evidence (Porwal ADX-EMA):**
- ADX > 20 and < 50 (strong but not exhausted)
- Entry on pullback to EMA(14), not on crossover itself
- Volume spike on signal day

**Proposed Fixes:**
- Tighten crossover window from 5 bars to 1 bar (fresh crossover only)
- Add volume gate
- Require retest of breakout level before entry
- Add ADX upper bound (< 50 to avoid exhausted trends)

**Priority:** MEDIUM
**Effort:** Small

---

### 9. bb_bounce.py Fixes

**Problem:** No volume, no multi-touch at band.

**Proposed Fixes:**
- Add volume gate
- Require 2+ band touches (strengthen signal)
- Add candle close confirmation

**Priority:** MEDIUM
**Effort:** Small

---

### 10. range_breakout.py Fixes

**Problem:** No volume (data issue), fixed retest %, no clean close check.

**Proposed Fixes:**
- ATR-adaptive retest percentage (not fixed 0.2%)
- Require clean close above band (not wick)
- Note: volume data issue needs investigation (97% zeros in candles_5m)

**Priority:** LOW
**Effort:** Small (except volume data fix)

---

### 11. continuation.py — Volume Dryup on Pullback

**Problem:** No volume analysis for continuation quality.

**Wyckoff Rule:** "Volume drying up on pullback in uptrend = bullish continuation"

**Proposed Fix:**
- Add volume dryup check: declining volume during pullback = stronger continuation signal
- Volume surging on decline = forced liquidation (avoid)

**Priority:** MEDIUM
**Effort:** Small

---

### 12. hzscore.py — Session Timing + Price Action

**Problem:** No session timing, no price action confirmation at z-score extremes.

**Proposed Fixes:**
- Add session timing filter (avoid Sunday early morning)
- Require candle pattern confirmation at z-score extreme (optional boost)

**Priority:** LOW
**Effort:** Trivial

---

## TIER 3 — Missing Signals (New)

### 13. Inside Bar Breakout (Porwal, Woods)

**Entry Rules:**
1. Inside bar: high and low within prior candle's range
2. Entry on candle close below mother bar low (short) or above mother bar high (long)
3. Higher timeframe trend direction must align
4. Volume confirmation on breakout
5. Prior trend must exist

**Targets:** T1: 1× mother range, T2: 1.5×, T3: 2×
**Stop:** Above/below mother candle. Min R:R = 1:2.

**Priority:** HIGH — strong edge per Porwal
**Effort:** Medium — new signal file

---

### 14. Doji at Extremes (Porwal)

**Entry Rules:**
1. Doji at market extreme (top or bottom)
2. RSI/Stochastic confirms overbought/oversold
3. Entry when high or low of Doji breaks
4. Gap up after Doji at bottom = strong bullish confirmation

**Priority:** MEDIUM
**Effort:** Small — pattern detection

---

### 15. Pin Bar at S/R (Woods)

**Entry Rules:**
1. Long lower tail at support = bullish pin bar → buy above pin bar high
2. Long upper tail at resistance = bearish pin bar → sell below pin bar low
3. Must be at a key S/R level, not in no-man's-land

**Priority:** MEDIUM — overlaps with rs.py improvement (#6)
**Effort:** Small — integrate into rs.py

---

### 16. Morning/Evening Star (Woods)

**Entry Rules:**
1. 3-bar reversal at major S/R
2. Morning Star: bearish candle + small body candle + bullish candle
3. Buy above Morning Star, sell below Evening Star
4. Volume should increase on 3rd candle

**Priority:** LOW
**Effort:** Medium — 3-candle pattern detection

---

### 17. Wyckoff Spring (Wyckoff)

**Entry Rules:**
1. After accumulation phase, price tests support level
2. "Spring" = price briefly dips below support then reverses sharply
3. Volume spike on reversal confirms spring
4. Entry on reversal above support
5. Stop below spring low

**Priority:** MEDIUM — our wyckoff.py is disabled (0% WR), but concept is sound
**Effort:** Medium — needs accumulation phase detection

---

## Implementation Order

| Phase | What | Effort | Impact |
|-------|------|--------|--------|
| **1** | R:R pre-check utility | Small | Critical — all signals benefit |
| **2** | Volume confirmation utility | Small | Critical — 10/15 books mandate |
| **3** | Candle close gate | Trivial | High — prevents fakeouts |
| **4** | Session timing filter | Trivial | Medium — avoids chop |
| **5** | rs.py + candle patterns | Medium | High — best structural signal |
| **6** | return_exhaustion + S/R + divergence | Medium | High — key signal improvement |
| **7** | engulfing.py fixes | Small | Medium |
| **8** | vortex_break fixes | Small | Medium |
| **9** | bb_bounce fixes | Small | Medium |
| **10** | Inside Bar Breakout (new) | Medium | High — new edge |
| **11** | continuation + volume dryup | Small | Medium |
| **12** | range_breakout fixes | Small | Low |
| **13** | Doji at extremes (new) | Small | Medium |
| **14** | Wyckoff Spring (new) | Medium | Medium |
| **15** | Morning/Evening Star (new) | Medium | Low |
| **16** | hzscore session timing | Trivial | Low |

---

## Universal Entry Rules (Summary from All Books)

| Rule | Books Citing | Status |
|------|-------------|--------|
| Min R:R = 1:2 before entry | 9/15 | **MISSING** |
| Volume confirmation on entry | 10/15 | **MISSING** (1/20 signals) |
| Wait for candle close | 6/15 | **MISSING** |
| Trade with higher timeframe trend | 8/15 | Partial (some signals) |
| Stop at pattern's logical extreme | All | ATR-based (acceptable) |
| Use trailing stops | All | **YES** (trailing system exists) |
| Avoid first 30 min of session | 5/15 | **MISSING** |
| Divergence alone ≠ signal (need confirmation) | Carli | **MISSING** |
| Candle pattern at S/R = high probability | Woods, Porwal | **MISSING** |
| Volume drying on pullback = continuation | Wyckoff | **MISSING** |

---

## Notes

- Full books are in `/root/.hermes/books/` for reference
- Signal files are in `/root/.hermes/scripts/signals/`
- Signal runner: `/root/.hermes/scripts/signals_runner.py`
- Signal compactor: `/root/.hermes/scripts/signal_compactor.py`
- Constants: `/root/.hermes/scripts/hermes_constants.py`
- Paths: `/root/.hermes/scripts/paths.py`
