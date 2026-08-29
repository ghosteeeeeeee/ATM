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

## Part 5: Critical Corrections (From Independent Audit)

### ❌ Wave Position Prediction Does NOT Work

The brainstorm claimed "SHORT near peak = good entry." **This is contradicted by data:**

| Trade | Wave Position | Claimed Score | Actual PnL |
|-------|---------------|---------------|------------|
| 1 (LOST) | post_peak_declining | 85/100 (GOOD) | **-4.22%** |
| 2 (WON) | near_trough | 15/100 (BAD) | **+16.06%** |
| 3 (WON) | near_peak | 85/100 (GOOD) | **+1.11%** |

**Conclusion:** Wave position scoring is unreliable with 3-trade sample size. Do NOT implement Idea 2 (Wave-Position Entry Filter) until we have 50+ trades per token.

### ⚠️ Leverage Must Be in All SL/TP Calculations

The brainstorm calculates SL as price% but ignores leverage. At 5x leverage:
- 4.28% price SL = **21.4% portfolio loss**
- 1.5% price SL = **7.5% portfolio loss**

**Every SL suggestion must show:** price%, portfolio% (at current leverage), and max acceptable loss.

### ⚠️ Amplitude is Non-Stationary

ZRO amplitude varied within 30 days:
- Q1 (25th percentile): 2.87%
- Median: 3.13%
- Q3 (75th percentile): 5.35%
- Ratio Q3/Q1: 1.86x

**The "average" is misleading.** Use rolling windows (last 100 waves), not 30-day averages.

---

## Part 6: Enhancement Ideas (Ranked by Impact)

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

#### 11. Amplitude Regime Detection (Rolling Windows)
**What:** Use rolling 100-wave windows instead of 30-day averages.
**Why:** Amplitude is non-stationary — ZRO varied 2.87% to 6.45% within 30 days.
**Implementation:**
```python
def get_rolling_amplitude(token, window=100):
    """Compute amplitude from last 100 waves, not 30-day average."""
    periods = get_recent_wave_periods(token, count=window)
    amplitudes = [abs(p['amplitude_pct']) for p in periods]
    return {
        'current': amplitudes[-1] if amplitudes else 0,
        'rolling_avg': np.mean(amplitudes) if amplitudes else 0,
        'rolling_p75': np.percentile(amplitudes, 75) if amplitudes else 0,
        'expanding': len(amplitudes) > 10 and np.mean(amplitudes[-10:]) > np.mean(amplitudes[-20:-10]),
    }
```

#### 12. Leverage-Aware Stop Loss (CRITICAL MISSING)
**What:** Express all SL in both price% and portfolio% terms.
**Why:** 4.28% price SL at 5x leverage = 21.4% portfolio loss. Never ignore leverage.
**Implementation:**
```python
def leverage_aware_sl(token, direction, entry_price, leverage):
    amp = get_avg_amplitude(token)
    price_sl_pct = amp / 100  # e.g., 4.28%
    portfolio_sl_pct = price_sl_pct * leverage  # e.g., 21.4%
    
    # Cap at max acceptable portfolio loss
    MAX_PORTFOLIO_LOSS = 0.05  # 5%
    if portfolio_sl_pct > MAX_PORTFOLIO_LOSS:
        price_sl_pct = MAX_PORTFOLIO_LOSS / leverage
        portfolio_sl_pct = MAX_PORTFOLIO_LOSS
    
    return {
        'price_sl_pct': price_sl_pct,
        'portfolio_sl_pct': portfolio_sl_pct,
        'sl_price': entry_price * (1 + price_sl_pct) if direction == 'SHORT' else entry_price * (1 - price_sl_pct),
        'max_loss_usdt': POSITION_SIZE * portfolio_sl_pct
    }
```

#### 13. Amplitude Mean-Reversion Strategy
**What:** Trade amplitude expansion/compression cycles.
**Why:** After high-amplitude periods, amplitude tends to compress (vol mean-reversion).
**Implementation:**
```python
def amplitude_mean_reversion_signal(token):
    rolling = get_rolling_amplitude(token)
    
    if rolling['current'] > rolling['rolling_p75'] * 1.5:
        # Amplitude expansion — expect compression
        return {'signal': True, 'type': 'vol_selling', 'confidence': 70}
    
    if rolling['current'] < rolling['rolling_avg'] * 0.5:
        # Amplitude compression — expect expansion
        return {'signal': True, 'type': 'vol_buying', 'confidence': 60}
    
    return {'signal': False}
```

#### 14. Multi-Timeframe Amplitude Analysis
**What:** Run amplitude analysis on 1h, 4h, and daily candles.
**Why:** 1h may be noisy; 4h/daily may be more stable and actionable.
**Implementation:**
```python
def multi_tf_amplitude(token):
    """Compare amplitude across timeframes."""
    amp_1h = get_avg_amplitude(token, '1h')
    amp_4h = get_avg_amplitude(token, '4h')
    amp_1d = get_avg_amplitude(token, '1d')
    
    # If 4h amp > 1h amp significantly, the 4h trend is stronger
    tf_alignment = 'aligned' if amp_4h > amp_1h * 0.8 else 'divergent'
    
    return {'1h': amp_1h, '4h': amp_4h, '1d': amp_1d, 'alignment': tf_alignment}
```

#### 15. Time-of-Day Amplitude Effects
**What:** Check if amplitude varies by hour of day.
**Why:** Some tokens may be more volatile during specific sessions (Asian, US, etc.).
**Implementation:**
```python
def hourly_amplitude_profile(token):
    """Compute average amplitude by hour of day."""
    candles = get_candles(token, '1h', 2880)  # 4 months
    extrema = find_peaks_troughs(...)
    
    hourly_amps = defaultdict(list)
    for p in periods:
        hour = p['from_time'].hour
        hourly_amps[hour].append(abs(p['amplitude_pct']))
    
    return {h: np.mean(a) for h, a in sorted(hourly_amps.items())}
```

#### 16. Amplitude Clustering (Volatility Regimes)
**What:** Detect when amplitude enters a new regime (high/low vol cluster).
**Why:** Amplitude regimes persist for days/weeks. Trade differently in each regime.
**Implementation:**
```python
def detect_amplitude_regime(token):
    rolling = get_rolling_amplitude(token, window=100)
    historical_avg = get_historical_avg_amplitude(token)
    
    if rolling['rolling_avg'] > historical_avg * 1.3:
        return 'high_vol_regime'
    elif rolling['rolling_avg'] < historical_avg * 0.7:
        return 'low_vol_regime'
    else:
        return 'normal_regime'
```

#### 17. Partial Exits Based on Amplitude
**What:** Take 50% profit at 0.5x amplitude, trail the rest.
**Why:** Captures more of the wave while limiting downside.
**Implementation:**
```python
def amplitude_partial_exit(token, direction, entry_price, position_size):
    amp = get_avg_amplitude(token)
    
    # First target: 0.5x amplitude
    tp1 = entry_price * (1 + amp * 0.5 / 100) if direction == 'LONG' else entry_price * (1 - amp * 0.5 / 100)
    
    # Second target: full amplitude (trail after TP1 hit)
    tp2 = entry_price * (1 + amp / 100) if direction == 'LONG' else entry_price * (1 - amp / 100)
    
    return {
        'tp1': tp1, 'tp1_size': position_size * 0.5,
        'tp2': tp2, 'tp2_size': position_size * 0.5,
        'trail_start': tp1
    }
```

#### 18. Amplitude-Winrate Correlation Backtest
**What:** Test whether HIGH_AMP tokens actually have lower win rates.
**Why:** No evidence exists. High amplitude = bigger wins when trades work.
**Implementation:** Run backtest comparing win rates across amplitude classes.

---

## Part 7: Implementation Roadmap (Revised After Audit)

### Phase 0: Critical Fixes (Do First)
1. ✅ Bug fix (extrema detection) — DONE
2. ✅ Data gap filtering — DONE
3. Fix duplicate code in `wave_trade_context.py` (import from wave_period_detector)
4. Add zero-amplitude wave filtering
5. Filter TRUMP 82.45% outlier before computing stats

### Phase 1: Foundation (This Week)
6. Build amplitude cache with ROLLING WINDOWS (not TTL) — Idea 11
7. Add leverage-aware SL to all calculations — Idea 12
8. Integrate amplitude with signal compactor — Idea 3
9. Add amplitude-based position sizing — Idea 4

### Phase 2: Stops & Targets (Next Week)
10. Dynamic stop loss based on rolling amplitude — Idea 2 (revised)
11. Dynamic take profit with partial exits — Idea 17
12. Amplitude regime detection — Idea 16

### Phase 3: New Signals (Week After)
13. Amplitude breakout signal — Idea 7
14. Frequency change detector — Idea 8
15. Multi-timeframe amplitude — Idea 14
16. Amplitude-winrate correlation backtest — Idea 18

### Phase 4: Advanced (Future)
17. Time-of-day amplitude effects — Idea 15
18. Amplitude mean-reversion strategy — Idea 13
19. Wave correlation across tokens — Idea 10
20. Context gate integration — Idea 9

### ⛔ NOT IMPLEMENTING (Until 50+ trades validated)
- Wave-position entry filter (Idea 2) — contradicted by data
- Wave-position scoring logic — needs fundamental rethinking

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

## Part 9: Priority Table (Revised After Audit)

| Priority | Idea | Impact | Effort | Status | Audit Finding |
|----------|------|--------|--------|--------|---------------|
| **1** | Amplitude Cache (rolling) | Foundation | Low | Ready | Use rolling windows, not TTL |
| **2** | Leverage-Aware SL | CRITICAL | Low | Ready | Auditor: "single biggest risk factor" |
| **3** | Amplitude-Weighted Compactor | HIGH | Low | Ready | Verified correct |
| **4** | Position Sizing | HIGH | Low | Ready | Multipliers need backtest |
| **5** | Dynamic SL (rolling amp) | HIGH | Medium | Ready | Non-stationary — use rolling |
| **6** | Partial Exits | MEDIUM | Medium | Ready | New idea from auditor |
| **7** | Amplitude Regime Detection | MEDIUM | Medium | Ready | New idea from auditor |
| **8** | Multi-TF Amplitude | MEDIUM | Medium | Ready | New idea from auditor |
| **9** | Amplitude Breakout Signal | HIGH | High | Needs backtest | — |
| **10** | Frequency Change Detector | MEDIUM | Low | Ready | — |
| ⛔ | Wave-Position Entry Filter | — | — | BLOCKED | Contradicted by data |
| ⛔ | Wave-Position Scoring | — | — | BLOCKED | Needs rethinking |

---

## Part 10: Open Questions for Further Research

1. **How to handle non-stationary amplitude?** Rolling windows vs regime detection vs adaptive?
2. **What's the right max portfolio loss per trade?** 2%? 5%? Depends on account size?
3. **Should amplitude cache use waves or candles?** Waves = semantic, candles = simpler.
4. **Interaction with ATR:** How does amplitude relate to ATR? Should they be combined?
5. **Backtest needed:** Which ideas actually improve win rate? Run amplitude-winrate correlation first.
6. **How often to update rolling amplitude?** Every new wave? Every 10 waves? Daily?
7. **Should we pause trading during amplitude spikes?** Or just reduce size?
8. **Time-of-day effects:** Do some tokens have higher amplitude during specific hours?

---

## Appendix: Raw Data

### Full Token List (30 tokens analyzed)
BTC, ETH, SOL, LINK, ARB, ZRO, TRUMP, WIF, HYPE, DOGE, SUI, AAVE, ONDO, WLD, TURBO, POPCAT, SPX, KAS, XRP, FET, AVAX, DOT, NEAR, UNI, INJ, FIL, CRV, DYDX, ENA, LDO

### Analysis Parameters
- Timeframe: 1h
- Lookback: 720 candles (30 days)
- Extrema window: 3 (strict > / < after bug fix)
- Data gap filter: 48 hours
