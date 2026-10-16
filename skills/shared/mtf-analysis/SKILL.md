---
name: mtf-analysis
description: Use when analyzing any crypto trade setup across multiple timeframes. Combines 1m/5m/15m/1h/4h analysis with continuum oscillator for full market picture. Triggers on "multi-timeframe", "MTF", "zoom out", "bigger picture", "timeframe analysis".
---

# Multi-Timeframe Analysis Skill

Zoom in and out across timeframes to see the full picture before entering a trade. A trade that looks good on 5m might be terrible on 1h.

## Timeframe Hierarchy

| TF | Role | Weight | What It Tells You |
|----|------|--------|-------------------|
| **1m** | Execution | 10% | Entry timing, micro-momentum |
| **5m** | Setup | 20% | Short-term trend, bounce/dip |
| **15m** | Confirmation | 25% | Swing structure, RSI bands |
| **1h** | Direction | 25% | Macro trend, key levels |
| **4h** | Regime | 20% | Market regime, long-term bias |

**The rule:** Higher timeframes override lower timeframes. A 5m bullish signal in a 4h bearish trend is a bounce, not a reversal.

## Analysis Process

### Step 1: Run analysis on each timeframe
```python
# For each TF, calculate:
- RSI 14
- MACD 8,50,12 (line, signal, histogram)
- EMA50, EMA100
- Volume ratio (current vs 20-bar average)
- MACD crossover status
- Histogram trend (rising/falling)
```

### Step 2: Read the continuum oscillator
```bash
cat /var/www/hermes/data/continuum_data.json
```
Key fields:
- `ema300_position` — ABOVE/BELOW/AT (macro trend)
- `zscore_tier` — STRONG_POS/NEUTRAL/STRONG_NEG
- `velocity_state` — RISING/SLOW/FALLING
- `acceleration_state` — POSITIVE/NEGATIVE
- `trend_quality` — STRONG_UP/STRONG_DOWN
- `linreg_direction` — LEAN_BULL/LEAN_BEAR/FLAT
- `market_phase` — ACCUMULATION/DISTRIBUTION/RECOVERY/DECLINING

### Step 3: Build the timeframe matrix

| TF | RSI | MACD | Signal | Trend | Notes |
|----|-----|------|--------|-------|-------|
| 1m | X | BULL/BEAR | Rising/Falling | | |
| 5m | X | BULL/BEAR | Rising/Falling | | |
| 15m | X | BULL/BEAR | Rising/Falling | | |
| 1h | X | BULL/BEAR | Rising/Falling | | |
| 4h | X | BULL/BEAR | Rising/Falling | | |

### Step 4: Count alignment
- How many TFs are bullish? Bearish?
- Are higher TFs (1h, 4h) aligned with lower TFs (1m, 5m)?
- Is there divergence between TFs?

## Interpretation Rules

### All Timeframes Aligned (5/5)
**Strongest signal.** Enter with confidence.
- All bearish = strong SHORT
- All bullish = strong LONG

### Higher TFs Bearish, Lower TFs Bullish (bounce)
**The bounce pattern.** Lower TFs show a bounce in a bearish trend.
- SHORT setup: wait for bounce to exhaust (1m RSI drops, histogram falls)
- LONG setup: risky — fighting the higher TF trend
- **This is the most common chop pattern**

### Higher TFs Bullish, Lower TFs Bearish (dip)
**The dip pattern.** Lower TFs show a dip in a bullish trend.
- LONG setup: wait for dip to exhaust (1m RSI rises, histogram rises)
- SHORT setup: risky — fighting the higher TF trend

### Mixed Signals (2-3/5 aligned)
**Skip or size down.** No clear edge.

## Entry Rules

1. **1h and 4h must align with your direction** — if they don't, skip
2. **15m should confirm** — RSI in your favor, MACD supporting
3. **5m is your timing** — enter when 5m aligns with 15m/1h
4. **1m is your trigger** — enter on 1m confirmation (crossover, rejection candle)
5. **Continuum must not contradict** — if continuum is STRONG_DOWN, don't fight it with LONGs

## Example: BTC SHORT (2026-10-16)

| TF | RSI | MACD | Signal | Trend |
|----|-----|------|--------|-------|
| 1m | 28.6 | BEAR | Falling | Bearish |
| 5m | 52.5 | BULL | Rising | Bounce |
| 15m | 24.1 | BEAR | Falling | Bearish |
| 1h | 35.5 | BEAR | Falling | Bearish |
| 4h | 36.0 | BEAR | Falling | Bearish |

**Continuum:** EMA300 BELOW, STRONG_DOWN, LEAN_BEAR

**Alignment: 4/5 bearish.** Only 5m bullish (the bounce).

**Verdict:** SHORT aligned with 15m/1h/4h + continuum. 5m bounce is the risk, but 1m already rolling over (RSI 28.6, histogram falling).

**Entry timing:** 1m showing bounce exhaustion = enter SHORT.

## Contrarian Integration

After MTF analysis, run contrarian checks:
- Is the MTF alignment TOO obvious?
- Where are stop clusters on each TF?
- What would the opposite trade look like?

**The best trades have:**
- 4/5 TFs aligned ✅
- 1 TF conflicting (the risk) ⚠️
- Contrarian view weaker than your view ✅

## Common Patterns

### The Fakeout
- 5m breaks above resistance on volume
- 15m, 1h, 4h all bearish
- 1m shows rejection candle
- **Result:** 5m breakout fails, price dumps

### The Absorption
- Price hits support on 1h
- 5m shows strong bounce
- 15m RSI recovering from oversold
- **Result:** Bounce continues to next resistance

### The Continuation
- All TFs aligned in one direction
- Continuum confirms
- Volume supporting
- **Result:** Strong move in trend direction

## Volume Confirmation

| TF | Volume Signal | Meaning |
|----|--------------|---------|
| 1m spike | Entry trigger | Smart money entering |
| 5m above avg | Setup confirmed | Real move, not fake |
| 15m above avg | Trend confirmed | Institutional interest |
| 1h above avg | Regime shift | Major move starting |

**Low volume on higher TFs = weak trend, likely chop**

## Date
Created 2026-10-16 based on BTC multi-timeframe analysis during chop trading session.
