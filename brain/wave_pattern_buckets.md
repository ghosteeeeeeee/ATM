# Wave Pattern Classification System

## 5 Wave Pattern Buckets

Based on analysis of 20 tokens across 720 1-hour candles each.

---

### 1. HIGH_FREQ_OSCILLATOR (6 tokens)
**Examples:** ZRO, ARB, HYPE, WLD, TURBO, FET

**Characteristics:**
- Dominant period: **1-2 hours** (70%+ of all waves)
- Average amplitude: **Low** (<1%)
- High coefficient of variation (CV > 1.0)
- Fast, noisy oscillations

**What it looks like:**
```
Period histogram:
  1-2h: ████████████████████████████ (70-80%)
  2-4h: ███ (5-10%)
  4-8h: ████ (10-15%)
  8h+:  ██ (3-6%)
```

**Trading implications:**
- ❌ **AVOID** trend-following (too much noise)
- ✅ **USE** mean-reversion strategies
- ✅ **USE** tight stops (1-2% max)
- ✅ **USE** lower timeframes (15m or 5m)
- ⚠️ High frequency of whipsaws

---

### 2. MEDIUM_FREQ_TREND (10 tokens)
**Examples:** BTC, ETH, SOL, TRUMP, DOGE, SUI, AAVE, POPCAT, SPX, KAS

**Characteristics:**
- Dominant period: **4-8 hours** (60%+ of all waves)
- Average amplitude: **Low to High** (varies by token)
- Lower CV (0.5-1.0 for best cases)
- Rideable trends with clear swings

**What it looks like:**
```
Period histogram:
  1-2h: ██ (5-15%)
  2-4h: ████████████████ (30-40%)
  4-8h: ██████████████████████ (40-50%)
  8h+:  ████ (10-20%)
```

**Trading implications:**
- ✅ **BEST** for swing trading
- ✅ **USE** trend-following strategies
- ✅ **USE** MACD wave rider (existing system)
- ✅ **USE** wider stops (2-4%)
- ✅ **USE** 1h or 4h timeframes
- 🎯 **IDEAL** for the accel-300-v2 signal

---

### 3. BIMODAL (2 tokens)
**Examples:** LINK, ONDO

**Characteristics:**
- Two dominant periods: **1-2h AND 4-8h** (each 35-45%)
- Regime-dependent behavior
- Switches between fast chop and slow trends

**What it looks like:**
```
Period histogram:
  1-2h: ████████████████████ (40-45%)
  2-4h: ████████ (15-20%)
  4-8h: ████████████████████ (30-45%)
  8h+:  ████ (10-15%)
```

**Trading implications:**
- ⚠️ **COMPLEX** — requires regime detection
- ✅ **USE** adaptive strategies
- ✅ **SWITCH** between fast/slow modes
- ⚠️ **AVOID** during regime transitions
- 🎯 **BEST** when regime is clearly identified

---

### 4. CHAOTIC (1 token)
**Examples:** WIF

**Characteristics:**
- No dominant period
- Very high CV (>1.5)
- Unpredictable wave lengths
- High amplitude swings

**What it looks like:**
```
Period histogram:
  1-2h: ████████████ (30-35%)
  2-4h: ████████████ (30-35%)
  4-8h: █████████ (20-25%)
  8h+:  █████ (10-15%)
```

**Trading implications:**
- ❌ **AVOID** systematic strategies
- ⚠️ **REDUCE** position size
- ✅ **USE** wider stops (4%+)
- ✅ **USE** higher timeframes only
- 🎯 **BEST** for discretionary trading

---

### 5. TRANSITIONAL (1 token)
**Examples:** XRP

**Characteristics:**
- Flat distribution across all periods
- No clear dominant frequency
- Often in between pattern states
- Low amplitude

**What it looks like:**
```
Period histogram:
  1-2h: ████████████ (30-35%)
  2-4h: ██████████ (25-30%)
  4-8h: ████████████ (30-35%)
  8h+:  ████ (10-15%)
```

**Trading implications:**
- ⚠️ **WAIT** for pattern to emerge
- ❌ **AVOID** forcing trades
- ✅ **USE** smaller position sizes
- 🎯 **BEST** when transitioning to MEDIUM_FREQ_TREND

---

## Amplitude Classes

| Class | Avg Amplitude | Tokens | Strategy |
|-------|---------------|--------|----------|
| **LOW_AMP** | <1.5% | BTC, ETH, LINK, ARB, ZRO, HYPE, ONDO, WLD, TURBO, XRP, FET | Tighter targets, more trades |
| **MED_AMP** | 1.5-2.5% | SOL, WIF, DOGE, AAVE, POPCAT, KAS | Standard targets |
| **HIGH_AMP** | >2.5% | TRUMP, SUI, SPX | Wider targets, fewer trades |

---

## Cross-Classification Matrix

| Pattern | LOW_AMP | MED_AMP | HIGH_AMP |
|---------|---------|---------|----------|
| **HIGH_FREQ_OSCILLATOR** | ARB, ZRO, HYPE, WLD, TURBO, FET | — | — |
| **MEDIUM_FREQ_TREND** | BTC, ETH | SOL, DOGE, AAVE, POPCAT, KAS | TRUMP, SUI, SPX |
| **BIMODAL** | LINK, ONDO | — | — |
| **CHAOTIC** | — | WIF | — |
| **TRANSITIONAL** | XRP | — | — |

---

## Key Insights

1. **Most tokens are MEDIUM_FREQ_TREND** (50%) — the sweet spot for swing trading
2. **HIGH_FREQ_OSCILLATOR** tokens (30%) are noise machines — avoid or mean-revert
3. **Amplitude correlates with pattern** — high-amp tokens tend to be MEDIUM_FREQ
4. **ZRO is a HIGH_FREQ_OSCILLATOR** — explains the choppy trades
5. **BTC/ETH are clean MEDIUM_FREQ_TREND** — ideal for the existing wave rider system

---

## Recommended Actions by Bucket

### For MEDIUM_FREQ_TREND tokens:
- Run accel-300-v2 signals as-is
- Use 1h/4h timeframes
- Standard position sizing

### For HIGH_FREQ_OSCILLATOR tokens:
- **Disable** trend-following signals
- **Enable** mean-reversion signals
- Use 15m timeframe
- Reduce position size by 50%

### For BIMODAL tokens:
- Add regime detection layer
- Switch strategies based on dominant period
- Use adaptive position sizing

### For CHAOTIC/TRANSITIONAL tokens:
- **Reduce exposure** significantly
- Use wider stops
- Wait for pattern to stabilize
