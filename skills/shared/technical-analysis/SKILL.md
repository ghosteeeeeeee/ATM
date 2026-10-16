---
name: technical-analysis
description: Use when analyzing any crypto trade setup. Covers RSI, MACD, support/resistance, trendlines, EMAs, volume, and pattern recognition. Triggers on "analyze", "what do you see", "check the chart", "TA", "technical analysis".
---

# Technical Analysis Skill

Standard analysis framework used for all manual trade decisions. Combines multiple indicators with pattern recognition and contrarian checks.

## Analysis Checklist

Run through these in order for every setup:

### 1. EMA Structure (Trend Direction)
```python
# Calculate EMAs on 5m candles
ema50 = EMA(closes, 50)    # Short-term trend
ema100 = EMA(closes, 100)  # Medium-term trend
ema180 = EMA(closes, 180)  # Long-term trend / key support-resistance
ema300 = EMA(closes, 300)  # Macro trend (used by continuum)
```

**Interpretation:**
- Price ABOVE all EMAs = bullish structure
- Price BELOW all EMAs = bearish structure
- EMAs converging = consolidation / squeeze
- EMAs fanning out = trending
- EMA180 is key dynamic S/R — bounces often happen here

### 2. MACD (8, 50, 12) — Momentum
```python
ema8 = EMA(closes, 8)
ema50 = EMA(closes, 50)
macd_line = ema8 - ema50
signal_line = EMA(macd_line, 12)
histogram = macd_line - signal_line
```

**Interpretation:**
- MACD above signal = bullish momentum
- MACD below signal = bearish momentum
- Crossover = momentum shift (entry signal)
- Histogram rising = momentum building
- Histogram falling = momentum fading
- **Divergence:** Price makes higher high, MACD makes lower high = bearish divergence (and vice versa)

**Divergence is the strongest MACD signal.** It means momentum is fading even though price hasn't turned yet.

### 3. RSI (14) — Overbought/Oversold
```python
gains, losses = price_changes
rsi = 100 - (100 / (1 + avg_gain/avg_loss))
```

**Bands (from hermes_constants):**
- LONG: 20-75 (sweet spot 45-60)
- SHORT: 35-65 (sweet spot 45-60)
- RSI < 30 = oversold (bounce zone)
- RSI > 70 = overbought (dump zone)
- RSI 50 = neutral

**Entry rules:**
- LONG at RSI 45-60 (mid-band sweet spot)
- SHORT at RSI 45-60
- NEVER long at RSI > 70 (overbought chase)
- NEVER short at RSI < 35 (oversold falling knife)

### 4. Support/Resistance — Swing Points
```python
# Find swing highs (local maxima)
swing_highs = find_local_maxima(highs, lookback=3)

# Find swing lows (local minima)  
swing_lows = find_local_minima(lows, lookback=3)
```

**How to identify levels:**
- Multiple touches = STRONG level (3+ touches)
- Single touch = WEAK level
- Level tested and held = confirmed support/resistance
- Level broken = flips role (support becomes resistance, vice versa)

**Key levels to mark:**
- Swing highs/lows (last 20-40 bars)
- EMA50/100/180 (dynamic S/R)
- Round numbers ($80,000, $82,000)
- Previous day high/low
- Session open/close

### 5. Trendlines
```python
# Connect swing lows for uptrend line
# Connect swing highs for downtrend line
# More touches = stronger trendline
```

**How to draw:**
- Uptrend: connect 2+ rising swing lows
- Downtrend: connect 2+ falling swing highs
- Steeper trendline = more fragile (breaks easily)
- Shallower trendline = more robust

**Breakout/breakdown:**
- Price breaks above downtrend line = bullish signal
- Price breaks below uptrend line = bearish signal
- Wait for candle CLOSE beyond trendline (not just wick)

### 6. Volume — Confirmation
```python
avg_volume = mean(volume[-20:])
current_ratio = volume[-1] / avg_volume
```

**Interpretation:**
- Volume surge on breakout = confirmed (real move)
- Volume surge on breakdown = confirmed (real move)
- Volume DECLINING on rally = weak (likely fakeout)
- Volume DECLINING on dump = weak (likely bounce)
- **Volume spike on dip = buying (bullish)**
- **Volume spike on rally = selling (bearish)**

### 7. Pattern Recognition

**Bear Flag:**
- Flagpole: sharp decline (5+ bars)
- Flag: tight consolidation, slight upward drift
- Entry: short on break below flag low
- Target: flagpole height projected down

**Bull Flag:**
- Flagpole: sharp rally
- Flag: tight consolidation, slight downward drift
- Entry: long on break above flag high
- Target: flagpole height projected up

**Double Top:**
- Two peaks at similar price
- Second peak with lower volume = bearish
- Entry: short on break below neckline

**Double Bottom:**
- Two troughs at similar price
- Second trough with higher volume = bullish
- Entry: long on break above neckline

**Fakeout:**
- Price breaks key level then reverses
- Usually on low volume
- Stop hunt before real move

### 8. Contrarian Check (see contrarian-analysis skill)
- Is the setup too obvious?
- Where are stop loss clusters?
- What would a short seller see?
- What is the opposite setup?

## Analysis Template

```markdown
## [COIN] [DIRECTION] Analysis — [DATE TIME]

### Current State
- Price: $X
- RSI: X
- MACD: X vs Signal: X → BULLISH/BEARISH
- EMA50: $X (+X%)
- EMA100: $X (+X%)
- EMA180: $X (+X%)

### Support/Resistance
- Resistance: $X, $X, $X
- Support: $X, $X, $X

### Trend
- EMA structure: [bullish/bearish/mixed]
- Trendline: [direction, strength]
- Pattern: [flag/divergence/none]

### Volume
- Current: X (Xx average)
- Trend: [rising/falling/normal]

### Divergence Check
- MACD divergence: [yes/no, type]
- Volume divergence: [yes/no]

### Contrarian Score
- [HIGH/MEDIUM/LOW] risk
- [reasons]

### Verdict
- [ENTRY/WAIT/SKIP]
- [reasoning]
```

## Entry Rules

1. **Always check RSI first** — if outside 40-65, don't enter
2. **MACD must confirm** — crossover or divergence in your favor
3. **Volume must support** — breakout needs volume, divergence needs decline
4. **S/R must be clear** — know where your SL and TP are before entry
5. **Contrarian check** — if setup is too obvious, skip or size down
6. **Run precheck** — `ai_trader_precheck.py COIN DIRECTION` for gate verification

## Exit Rules

1. **SL below support (LONG) / above resistance (SHORT)** — not arbitrary %
2. **TP at next S/R level** — not arbitrary %
3. **Trail after +2%** — lock breakeven
4. **Cut if MACD crosses against you** — momentum shift = exit
5. **Cut if volume dries up on breakout** — fakeout likely

## Date
Created 2026-10-16 based on repeated analysis of BTC, GRASS, AVAX, and other manual trades.
