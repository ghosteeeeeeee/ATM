# Amplitude & Wave Period Trading System — Enhanced Brainstorm

**Created:** 2026-08-29
**Status:** Deep analysis complete, ready for implementation
**Key Insight:** Long waves (8h+) have ~3x higher amplitude than short waves (<2h). This is the most important finding.

---

## Executive Summary

After analyzing 30 tokens across 720 1-hour candles each, we discovered:

1. **Amplitude is the key differentiator** — not frequency (all tokens are MEDIUM_FREQ_TREND)
2. **Long waves have 3x higher amplitude** than short waves — this predicts profit potential
3. **BTC/ETH are LOW_AMP** (1.0-1.1%), most alts are MED/HIGH_AMP (1.5-4.5%)
4. **Wave position alone doesn't predict outcomes** — but combined with amplitude, it's powerful

---

## Part 1: Token Classification (Corrected)

### Amplitude Classes (30 tokens)

| Class | Count | Tokens | Avg Amp Range |
|-------|-------|--------|---------------|
| **LOW_AMP** (<1.5%) | 2 | BTC, ETH | 1.0-1.1% |
| **MED_AMP** (1.5-2.5%) | 13 | SOL, LINK, HYPE, DOGE, AAVE, ONDO, POPCAT, KAS, XRP, AVAX, DOT, DYDX, FIL | 1.5-2.5% |
| **HIGH_AMP** (>2.5%) | 15 | ENA, WIF, ZRO, TRUMP, CRV, WLD, TURBO, SPX, SUI, NEAR, INJ, FET, UNI, LDO, ARB | 2.5-4.5% |

### Amplitude Percentiles (Key Data)

| Token | Avg | P50 | P75 | P90 | P95 | Max | Class |
|-------|-----|-----|-----|-----|-----|-----|-------|
| BTC | 1.02% | 0.64% | 1.21% | 1.94% | 2.81% | 14.62% | LOW |
| ETH | 1.14% | 0.76% | 1.20% | 2.21% | 3.01% | 19.83% | LOW |
| SOL | 1.56% | 1.04% | 1.86% | 3.41% | 4.92% | 12.80% | MED |
| ZRO | 4.28% | 3.13% | 5.35% | 8.24% | 11.89% | 24.88% | HIGH |
| TRUMP | 4.01% | 1.77% | 3.94% | 7.86% | 11.02% | 82.45% | HIGH |
| WIF | 4.36% | 2.48% | 5.80% | 9.25% | 14.02% | 27.90% | HIGH |

**How to read:**
- **P50 (Median):** Typical swing size (50% of waves are smaller)
- **P75:** Above-average swing (25% of waves are bigger)
- **P90:** Bad day swing (10% of waves are bigger)
- **P95:** Worst-case typical swing (5% of waves are bigger)
- **Max:** Historical worst case

---

## Part 2: Period Distributions (New Finding)

### Period Buckets by Token

| Token | <2h | 2-4h | 4-8h | 8-16h | 16h+ | Avg Period | CV |
|-------|-----|------|------|-------|------|------------|-----|
| BTC | 5% | 36% | 47% | 10% | 2% | 16.5h | 8.87 |
| ETH | 6% | 32% | 44% | 17% | 0% | 4.9h | 0.63 |
| SOL | 5% | 38% | 43% | 14% | 1% | 16.6h | 8.83 |
| ZRO | 6% | 28% | 40% | 25% | 1% | 7.7h | 2.66 |
| TRUMP | 7% | 29% | 45% | 18% | 1% | 18.9h | 7.69 |
| WIF | 1% | 28% | 31% | 32% | 8% | 30.0h | 6.90 |
| ENA | 1% | 30% | 47% | 21% | 1% | 8.1h | 2.91 |
| SPX | 5% | 34% | 42% | 19% | 0% | 5.0h | 0.57 |
| POPCAT | 8% | 32% | 52% | 8% | 0% | 4.4h | 0.56 |
| LINK | 7% | 27% | 50% | 15% | 1% | 5.7h | 1.35 |

**Key observations:**
- **ETH/SPX/POPCAT** have tight distributions (CV < 1.0) — consistent wave timing
- **BTC/SOL/DOGE** have high CV (8.0+) — often due to data gaps, not actual chaos
- **ZRO/ENA** have moderate CV (2.5-3.0) — somewhat predictable

---

## Part 3: The Big Discovery — Amplitude-Period Relationship

### Long Waves Have 3x Higher Amplitude

| Token | <2h Amp | 8-16h Amp | Ratio | Implication |
|-------|---------|-----------|-------|-------------|
| BTC | 0.53% | 1.77% | 3.3x | Long BTC waves = big moves |
| ETH | 0.50% | 1.78% | 3.6x | Same pattern |
| SOL | 0.70% | 2.23% | 3.2x | Same pattern |
| ZRO | 2.15% | 7.57% | 3.5x | Long ZRO waves = massive moves |
| TRUMP | 2.31% | 9.49% | 4.1x | TRUMP has highest ratio |
| SPX | 1.94% | 5.38% | 2.8x | More stable but still 3x |
| LINK | 0.93% | 3.45% | 3.7x | Same pattern |
| DOGE | 1.17% | 3.16% | 2.7x | Same pattern |

**Average ratio: 3.36x**

### What This Means

```
Short waves (<2h): Small moves (0.5-2.0%), frequent, good for scalping
Long waves (8h+):  Big moves (2.0-9.0%), rare, good for swing trading

If you can predict wave length, you can:
1. Size positions appropriately (bigger for longer waves)
2. Set stops appropriately (wider for longer waves)
3. Set targets appropriately (further for longer waves)
4. Time entries to catch long waves (the big money)
```

---

## Part 4: Trade Post-Mortem — ZRO Analysis

### The 3 ZRO Trades

| Trade | Entry | Exit | PnL | Wave Position | Would Wave Filter Have Helped? |
|-------|-------|------|-----|---------------|-------------------------------|
| 1 (LOST) | $1.066 | $1.075 | -4.22% | NEAR_PEAK (85/100) | No — position was good, stop was too tight |
| 2 (WON) | $1.127 | $1.091 | +16.06% | NEAR_TROUGH (15/100) | No — bad position but big winner |
| 3 (WON) | $1.173 | $1.170 | +1.11% | NEAR_PEAK (85/100) | No — good position, small win |

### Key Finding: Wave Position Alone Doesn't Predict Outcomes

The losing trade (Trade 1) had a GOOD wave position (NEAR_PEAK for SHORT). The winning trade (Trade 2) had a BAD wave position (NEAR_TROUGH for SHORT).

**Why?** Because amplitude matters more than position. Trade 2 caught a long wave (7+ hour decline) with high amplitude, while Trade 1 got stopped out during a short wave oscillation.

### What Would Have Saved Trade 1?

**Wider stop loss based on amplitude:**
- Current SL: ~0.84% (hit at $1.075)
- Amplitude-based SL: 4.28% (would be at $1.1116)
- With wider SL, trade would have survived and potentially hit TP

---

## Part 5: Enhancement Ideas (Ranked by Impact)

### 🔴 Tier 1: High Impact, Build First

#### 1. Amplitude Cache (Foundation)
**What:** Pre-compute amplitude class and percentiles per token, cache for 1 hour.
**Why:** All other enhancements need this data.
**Files:** `scripts/amplitude_cache.py` (new)
**Data to cache:**
```json
{
  "ZRO": {
    "amp_class": "HIGH_AMP",
    "avg_amp": 4.276,
    "p50_amp": 3.131,
    "p75_amp": 5.350,
    "p90_amp": 8.243,
    "p95_amp": 11.892,
    "max_amp": 24.882,
    "avg_period": 7.72,
    "period_cv": 2.66,
    "last_update": 1787972400
  }
}
```

#### 2. Dynamic Stop Loss Based on Amplitude
**What:** Set SL = entry_price × (avg_amp% × multiplier)
**Why:** ZRO trade would have survived with 4.3% SL instead of 0.84%
**Implementation:**
```python
def get_dynamic_sl(token, direction, entry_price):
    amp = get_avg_amplitude(token)  # From cache
    multiplier = get_sl_multiplier(token)  # 1.0x for HIGH_AMP, 1.5x for LOW_AMP
    sl_pct = amp * multiplier / 100
    
    if direction == 'LONG':
        return entry_price * (1 - sl_pct)
    else:
        return entry_price * (1 + sl_pct)
```

**Calibrated multipliers:**
| Amp Class | Avg Amp | SL Multiplier | Effective SL |
|-----------|---------|---------------|--------------|
| LOW_AMP | 1.0% | 1.5x | 1.5% |
| MED_AMP | 2.0% | 1.25x | 2.5% |
| HIGH_AMP | 4.0% | 1.0x | 4.0% |
| CHAOTIC | 4.4% | 0.75x | 3.3% |

#### 3. Amplitude-Weighted Signal Compactor
**What:** Multiply signal confidence by amplitude class multiplier.
**Why:** HIGH_AMP tokens need stronger signals to justify the volatility.
**Implementation:**
```python
AMPLITUDE_COMPACTOR_MULT = {
    'LOW_AMP': 1.10,   # Boost: stable, signals reliable
    'MED_AMP': 1.00,   # Neutral
    'HIGH_AMP': 0.85,  # Penalty: volatile, signals less reliable
    'CHAOTIC': 0.70,   # Heavy penalty
}
```

#### 4. Amplitude-Adjusted Position Sizing
**What:** Reduce position size for HIGH_AMP tokens to normalize risk.
**Why:** Equal dollar-risk across all tokens.
**Implementation:**
```python
def amplitude_adjusted_size(base_size, token):
    amp_class = get_amplitude_class(token)
    adjustments = {
        'LOW_AMP': 1.0,    # Full size (BTC, ETH)
        'MED_AMP': 0.9,    # 10% reduction
        'HIGH_AMP': 0.7,   # 30% reduction
        'CHAOTIC': 0.5,    # 50% reduction
    }
    return base_size * adjustments.get(amp_class, 1.0)
```

### 🟡 Tier 2: Medium Impact, Build Next

#### 5. Wave-Period Aware Stop Loss
**What:** Adjust SL based on expected wave length, not just amplitude.
**Why:** Long waves need wider stops to avoid getting shaken out.
**Implementation:**
```python
def wave_period_adjusted_sl(token, entry_price, expected_wave_hours):
    base_amp = get_avg_amplitude(token)
    
    # Longer waves need wider stops
    if expected_wave_hours >= 8:
        sl_mult = 1.5  # Wide stop for long waves
    elif expected_wave_hours >= 4:
        sl_mult = 1.25  # Standard
    else:
        sl_mult = 1.0  # Tight for short waves
    
    sl_pct = base_amp * sl_mult / 100
    return entry_price * (1 + sl_pct)  # For SHORT
```

#### 6. Dynamic Take Profit Based on Amplitude
**What:** Set TP at the expected next wave extreme.
**Why:** Take profit before the wave reverses.
**Implementation:**
```python
def get_dynamic_tp(token, direction, entry_price):
    avg_amp = get_avg_amplitude(token)
    
    if direction == 'LONG':
        return entry_price * (1 + avg_amp/100)
    else:
        return entry_price * (1 - avg_amp/100)
```

#### 7. Amplitude Breakout Signal (New Signal Type)
**What:** Fire when current amplitude exceeds P95 historical amplitude.
**Why:** Amplitude expansion often precedes breakouts.
**Implementation:**
```python
def amplitude_breakout_signal(token):
    recent_amp = get_current_wave_amplitude(token)
    p95_amp = get_p95_amplitude(token)  # From cache
    
    if recent_amp > p95_amp:
        # Amplitude breakout
        direction = 'LONG' if price_action_bullish else 'SHORT'
        confidence = min(90, 50 + (recent_amp - p95_amp) / p95_amp * 100)
        return {'signal': True, 'direction': direction, 'confidence': confidence}
    
    return {'signal': False}
```

#### 8. Frequency Change Detector
**What:** Detect when wave frequency accelerates/decelerates.
**Why:** Frequency changes often precede regime changes.
**Implementation:**
```python
def detect_frequency_change(token):
    recent_periods = get_recent_wave_periods(token, count=10)
    historical_periods = get_historical_wave_periods(token, count=10)
    
    recent_avg = np.mean(recent_periods)
    hist_avg = np.mean(historical_periods)
    
    change_pct = (recent_avg - hist_avg) / hist_avg * 100
    
    if change_pct < -20:
        return 'accelerating'  # Expect breakout
    elif change_pct > 20:
        return 'decelerating'  # Expect consolidation
    else:
        return 'stable'
```

### 🟢 Tier 3: Lower Impact, Build Later

#### 9. Context Gate — Wave State Integration
**What:** Add wave state as a context factor in the context gate.
**Why:** Wave state provides additional information for decision making.

#### 10. Wave Correlation Across Tokens
**What:** Detect when multiple tokens have synchronized waves.
**Why:** In-phase tokens = higher conviction signals.

---

## Part 6: Implementation Roadmap

### Phase 1: Foundation (This Week)
1. ✅ Bug fix (extrema detection) — DONE
2. ✅ Data gap filtering — DONE
3. Build amplitude cache (`scripts/amplitude_cache.py`)
4. Integrate with signal compactor (Idea 3)
5. Add amplitude-based position sizing (Idea 4)

### Phase 2: Stops & Targets (Next Week)
6. Dynamic stop loss based on amplitude (Idea 2)
7. Wave-period adjusted stop loss (Idea 5)
8. Dynamic take profit based on amplitude (Idea 6)

### Phase 3: New Signals (Week After)
9. Amplitude breakout signal (Idea 7)
10. Frequency change detector (Idea 8)
11. Context gate integration (Idea 9)

### Phase 4: Advanced (Future)
12. Wave correlation across tokens (Idea 10)

---

## Part 7: Key Data Tables for Implementation

### Table 1: Amplitude Class Thresholds
| Class | Avg Amp Range | Token Count | Examples |
|-------|---------------|-------------|----------|
| LOW_AMP | <1.5% | 2 | BTC, ETH |
| MED_AMP | 1.5-2.5% | 13 | SOL, LINK, DOGE |
| HIGH_AMP | >2.5% | 15 | ZRO, TRUMP, WIF |

### Table 2: Amplitude Percentiles (for dynamic SL/TP)
| Token | P50 | P75 | P90 | P95 | Suggested SL (1.0x avg) |
|-------|-----|-----|-----|-----|-------------------------|
| BTC | 0.64% | 1.21% | 1.94% | 2.81% | 1.0% |
| ETH | 0.76% | 1.20% | 2.21% | 3.01% | 1.1% |
| SOL | 1.04% | 1.86% | 3.41% | 4.92% | 1.6% |
| ZRO | 3.13% | 5.35% | 8.24% | 11.89% | 4.3% |
| TRUMP | 1.77% | 3.94% | 7.86% | 11.02% | 4.0% |
| WIF | 2.48% | 5.80% | 9.25% | 14.02% | 4.4% |

### Table 3: Period-Amplitude Relationship (for wave-period aware stops)
| Token | <2h Amp | 8-16h Amp | Ratio | Implication |
|-------|---------|-----------|-------|-------------|
| BTC | 0.53% | 1.77% | 3.3x | Long waves = 3x bigger moves |
| ZRO | 2.15% | 7.57% | 3.5x | Long ZRO waves = massive |
| TRUMP | 2.31% | 9.49% | 4.1x | Highest ratio |

---

## Part 8: Open Questions for Further Research

1. **How often should amplitude cache update?** Hourly seems right for 1h candles.
2. **Should amplitude class be static or dynamic?** A token might shift during volatile periods.
3. **How to predict wave length BEFORE entry?** Can we estimate if the next wave will be short or long?
4. **Interaction with ATR:** How does amplitude relate to ATR? Should they be combined?
5. **Backtest needed:** Which ideas actually improve win rate? All need validation.

---

## Appendix: Raw Data

### Full Token List (30 tokens analyzed)
BTC, ETH, SOL, LINK, ARB, ZRO, TRUMP, WIF, HYPE, DOGE, SUI, AAVE, ONDO, WLD, TURBO, POPCAT, SPX, KAS, XRP, FET, AVAX, DOT, NEAR, UNI, INJ, FIL, CRV, DYDX, ENA, LDO

### Analysis Parameters
- Timeframe: 1h
- Lookback: 720 candles (30 days)
- Extrema window: 3 (strict > / < after bug fix)
- Data gap filter: 48 hours
