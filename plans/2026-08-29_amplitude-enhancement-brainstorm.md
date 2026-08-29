# Amplitude-Based Trading System Enhancements — Brainstorm

**Date:** 2026-08-29
**Context:** Wave period analysis revealed amplitude is the key differentiator between tokens, not frequency. All major tokens are MEDIUM_FREQ_TREND, but amplitude varies from 1.0% (BTC) to 4.4% (ZRO).

---

## Core Insight

**Amplitude predicts how much a token will swing per wave.** This is directly useful for:
- Setting stop losses that don't get hunted
- Taking profits before the wave reverses
- Sizing positions inversely to volatility
- Filtering signals during high-amplitude regimes

---

## Idea 1: Amplitude-Based Dynamic Stop Loss (HIGH PRIORITY)

**Problem:** Current ATR-based stops use a fixed multiplier. HIGH_AMP tokens like ZRO (4.28% avg swing) need wider stops than BTC (1.02% avg swing).

**Solution:** Use amplitude percentile data to set stops.

```python
# In hermes_constants.py
AMPLITUDE_STOP.MULTIPLIERS = {
    'LOW_AMP':  1.5,   # BTC, ETH: 1.5x avg amplitude
    'MED_AMP':  1.25,  # SOL, LINK: 1.25x avg amplitude  
    'HIGH_AMP': 1.0,   # ZRO, TRUMP: 1.0x avg amplitude (already wide)
    'CHAOTIC':  0.75,  # WIF: tighter relative to amplitude
}

# Stop = entry_price * (avg_amplitude_pct/100 * multiplier)
# Example: ZRO SHORT at $1.066, avg_amp=4.28%, mult=1.0
#   SL = 1.066 * (0.0428 * 1.0) = 1.066 * 0.0428 = $0.0456 → SL at $1.1116
```

**Data we have:**
| Token | Avg Amp | P95 Amp | Suggested SL |
|-------|---------|---------|--------------|
| BTC | 1.02% | 2.81% | 1.5% (1.5x avg) |
| ETH | 1.14% | 3.01% | 1.7% (1.5x avg) |
| SOL | 1.56% | 4.92% | 2.0% (1.25x avg) |
| ZRO | 4.28% | 11.89% | 4.3% (1.0x avg) |
| TRUMP | 4.01% | 11.02% | 4.0% (1.0x avg) |

**Benefit:** ZRO trade wouldn't have been stopped out at -4.22% if SL was set at 4.3% instead of the ATR-based value.

---

## Idea 2: Wave-Position Entry Filter (MEDIUM PRIORITY)

**Problem:** Entries at the wrong wave position (SHORT near trough, LONG near peak) get stopped out.

**Solution:** Score entry quality based on where we are in the current wave.

```python
def score_wave_position(token, direction, lookback=720):
    """
    Score 0-100 based on wave position.
    
    100 = perfect entry (SHORT at peak, LONG at trough)
    0 = terrible entry (SHORT at trough, LONG at peak)
    """
    extrema = get_recent_extrema(token, lookback)
    last_extremum = extrema[-1]
    
    if direction == 'SHORT':
        if last_extremum['type'] == 'peak':
            return 90  # Great — we're near a peak
        elif last_extremum['type'] == 'trough':
            return 10  # Bad — we're near a trough
    
    if direction == 'LONG':
        if last_extremum['type'] == 'trough':
            return 90  # Great — we're near a trough
        elif last_extremum['type'] == 'peak':
            return 10  # Bad — we're near a peak
    
    return 50  # Neutral — unclear position
```

**Integration:** Multiply signal confidence by wave_position_score/100.

**Benefit:** The losing ZRO SHORT at $1.066 would have been filtered (entered near trough = low score).

---

## Idea 3: Amplitude-Weighted Signal Compactor (HIGH PRIORITY)

**Problem:** Signal compactor treats all tokens equally. A signal on BTC (LOW_AMP) is different from a signal on ZRO (HIGH_AMP).

**Solution:** Add amplitude multiplier to compactor scoring.

```python
# In signal_compactor.py, add to scoring:
AMPLITUDE_COMPACTOR_MULT = {
    'LOW_AMP':  1.1,   # Boost: stable tokens, signals are reliable
    'MED_AMP':  1.0,   # Neutral
    'HIGH_AMP': 0.85,  # Penalty: volatile tokens, signals less reliable
    'CHAOTIC':  0.7,   # Heavy penalty: unpredictable
}

# In score calculation:
amp_class = get_amplitude_class(token)  # From wave cache
amp_mult = AMPLITUDE_COMPACTOR_MULT.get(amp_class, 1.0)
final_score = base_score * amp_mult
```

**Benefit:** HIGH_AMP tokens like ZRO get naturally deprioritized in hotset unless their signal is exceptionally strong.

---

## Idea 4: Amplitude Cache (Foundation for All Ideas)

**Problem:** Wave analysis is expensive (needs 720 candles + extrema detection). Can't run it on every signal.

**Solution:** Pre-compute and cache amplitude data per token.

```python
# New file: scripts/amplitude_cache.py
# Structure: {token: {avg_amp, p95_amp, amp_class, avg_period, last_update}}

AMPLITUDE_CACHE_TTL = 3600  # 1 hour (amplitude changes slowly)

def get_amplitude_class(token: str) -> str:
    """Get cached amplitude class for a token."""
    cache = load_amplitude_cache()
    if token in cache and not is_stale(cache[token]):
        return cache[token]['amp_class']
    return 'MED_AMP'  # Default if not cached

def get_avg_amplitude(token: str) -> float:
    """Get cached average amplitude for a token."""
    cache = load_amplitude_cache()
    if token in cache and not is_stale(cache[token]):
        return cache[token]['avg_amp']
    return 2.0  # Default if not cached
```

**Integration points:** Signal compactor, SL setting, position sizing, context gate.

---

## Idea 5: Wave-Frequency Change Detector (MEDIUM PRIORITY)

**Problem:** We can detect when wave frequency changes, but don't use it.

**Solution:** Use frequency acceleration/deceleration as a regime signal.

```python
def detect_wave_regime_change(token, lookback=720):
    """
    Detect if wave frequency is changing.
    
    Returns:
        'accelerating' — waves getting faster (expect breakout)
        'decelerating' — waves getting slower (expect consolidation)
        'stable' — no significant change
    """
    # Compare recent 10 periods vs previous 10 periods
    recent_avg = avg of last 10 wave periods
    historical_avg = avg of previous 10 wave periods
    
    change_pct = (recent_avg - historical_avg) / historical_avg * 100
    
    if change_pct < -20:
        return 'accelerating'  # Waves 20%+ faster
    elif change_pct > 20:
        return 'decelerating'  # Waves 20%+ slower
    else:
        return 'stable'
```

**Trading use:**
- `accelerating` → Tighten stops, expect volatility expansion
- `decelerating` → Widen stops, expect range contraction
- `stable` → Normal operations

---

## Idea 6: Amplitude-Based Take Profit (MEDIUM PRIORITY)

**Problem:** Fixed TP:SL ratios (like 2:1) don't account for token amplitude. ZRO might need 3:1 while BTC needs 1.5:1.

**Solution:** Set TP based on historical wave amplitude.

```python
def calculate_dynamic_tp(token, direction, entry_price):
    """
    Set TP at the expected next wave extreme.
    
    Uses average amplitude to estimate where the next
    peak/trough will be.
    """
    avg_amp = get_avg_amplitude(token)  # From amplitude cache
    
    # TP = entry ± avg_amplitude (expect one full wave)
    if direction == 'LONG':
        return entry_price * (1 + avg_amp/100)
    else:
        return entry_price * (1 - avg_amp/100)
```

**Example:** ZRO SHORT at $1.066, avg_amp=4.28%
- TP = 1.066 * (1 - 0.0428) = $1.020 (take 4.3% profit)

---

## Idea 7: Context Gate — Wave State Integration (LOW PRIORITY)

**Problem:** Context gate doesn't know about wave state.

**Solution:** Add wave state as a context factor.

```python
def get_wave_context(token):
    """
    Returns wave context for the context gate.
    
    Factors:
    - amplitude_class: LOW/MED/HIGH/CHAOTIC
    - wave_regime: accelerating/decelerating/stable
    - position_in_wave: near_peak/near_trough/mid_wave
    """
    amp_class = get_amplitude_class(token)
    regime = detect_wave_regime_change(token)
    position = get_wave_position(token)
    
    # Context gate scoring
    score = 0
    if amp_class == 'LOW_AMP': score += 2
    elif amp_class == 'MED_AMP': score += 1
    elif amp_class == 'HIGH_AMP': score -= 1
    elif amp_class == 'CHAOTIC': score -= 3
    
    if regime == 'stable': score += 1
    elif regime == 'accelerating': score += 0  # Neutral — could go either way
    elif regime == 'decelerating': score -= 1
    
    return score  # Added to context gate total
```

---

## Idea 8: Amplitude Breakout Strategy (NEW — HIGH PRIORITY)

**Problem:** Current signals are all trend-following. No signal for amplitude expansion.

**Solution:** New signal that fires when amplitude expands beyond historical norm.

```python
def amplitude_breakout_signal(token, lookback=720):
    """
    Fire when current amplitude exceeds P95 historical amplitude.
    
    Logic: When a token starts making bigger swings than usual,
    it's often breaking out of a range or entering a new regime.
    """
    candles = get_candles(token, '1h', lookback)
    extrema = find_peaks_troughs(closes, window=3)
    periods = calculate_wave_periods(extrema, timestamps)
    
    recent_amp = abs(periods[-1]['amplitude_pct'])
    p95_amp = np.percentile([abs(p['amplitude_pct']) for p in periods[:-1]], 95)
    
    if recent_amp > p95_amp:
        # Amplitude breakout — direction based on recent price action
        direction = 'LONG' if closes[-1] > closes[-3] else 'SHORT'
        confidence = min(90, 50 + (recent_amp - p95_amp) / p95_amp * 100)
        return {'signal': True, 'direction': direction, 'confidence': confidence}
    
    return {'signal': False}
```

**Benefit:** Could catch the big TRUMP moves (82% max amplitude) or ZRO breakouts.

---

## Idea 9: Amplitude-Adjusted Position Sizing (HIGH PRIORITY)

**Problem:** Kelly criterion uses win rate and avg win/loss, but doesn't account for amplitude.

**Solution:** Reduce position size for HIGH_AMP tokens to normalize risk.

```python
def amplitude_adjusted_size(base_size, token):
    """
    Adjust position size based on amplitude class.
    
    Goal: Equal dollar-risk across all tokens.
    HIGH_AMP tokens get smaller positions.
    """
    amp_class = get_amplitude_class(token)
    
    adjustments = {
        'LOW_AMP':  1.0,   # Full size (BTC, ETH)
        'MED_AMP':  0.9,   # 10% reduction (SOL, LINK)
        'HIGH_AMP': 0.7,   # 30% reduction (ZRO, TRUMP)
        'CHAOTIC':  0.5,   # 50% reduction (WIF)
    }
    
    return base_size * adjustments.get(amp_class, 1.0)
```

**Example:** $100 base size
- BTC: $100 (LOW_AMP)
- SOL: $90 (MED_AMP)
- ZRO: $70 (HIGH_AMP)
- WIF: $50 (CHAOTIC)

---

## Idea 10: Wave Correlation Across Tokens (EXPERIMENTAL)

**Problem:** Tokens move together sometimes, but we don't track wave correlation.

**Solution:** Detect when multiple tokens have synchronized waves.

```python
def detect_wave_sync(tokens):
    """
    Detect if multiple tokens are in-phase (synced waves) or out-of-phase.
    
    In-phase: All tokens trending same direction → high conviction
    Out-of-phase: Tokens diverging → low conviction, reduce size
    """
    wave_positions = {}
    for token in tokens:
        extrema = get_recent_extrema(token)
        wave_positions[token] = extrema[-1]['type']  # 'peak' or 'trough'
    
    peaks = sum(1 for v in wave_positions.values() if v == 'peak')
    troughs = sum(1 for v in wave_positions.values() if v == 'trough')
    
    sync_ratio = max(peaks, troughs) / len(tokens)
    
    if sync_ratio > 0.7:
        return 'in_phase'  # High conviction
    elif sync_ratio < 0.4:
        return 'out_of_phase'  # Low conviction
    else:
        return 'mixed'
```

**Benefit:** When BTC, ETH, SOL are all at peaks together, SHORT signals across alts have higher conviction.

---

## Priority Ranking

| Priority | Idea | Impact | Effort | Status |
|----------|------|--------|--------|--------|
| **1** | Amplitude Cache (Idea 4) | Foundation | Low | Ready to build |
| **2** | Dynamic Stop Loss (Idea 1) | HIGH | Medium | Ready to build |
| **3** | Amplitude-Weighted Compactor (Idea 3) | HIGH | Low | Ready to build |
| **4** | Position Sizing (Idea 9) | HIGH | Low | Ready to build |
| **5** | Wave-Position Entry Filter (Idea 2) | MEDIUM | Medium | Needs validation |
| **6** | Dynamic Take Profit (Idea 6) | MEDIUM | Medium | Needs backtest |
| **7** | Frequency Change Detector (Idea 5) | MEDIUM | Low | Ready to build |
| **8** | Amplitude Breakout Signal (Idea 8) | HIGH | High | Needs backtest |
| **9** | Context Gate Integration (Idea 7) | LOW | Low | Ready to build |
| **10** | Wave Correlation (Idea 10) | LOW | High | Experimental |

---

## Implementation Roadmap

### Phase 1: Foundation (This Week)
1. Build amplitude cache (`scripts/amplitude_cache.py`)
2. Integrate with signal compactor (Idea 3)
3. Add amplitude-based position sizing (Idea 9)

### Phase 2: Stops & Targets (Next Week)
4. Dynamic stop loss based on amplitude (Idea 1)
5. Dynamic take profit based on amplitude (Idea 6)
6. Wave-position entry filter (Idea 2)

### Phase 3: New Signals (Week After)
7. Amplitude breakout signal (Idea 8)
8. Frequency change detector (Idea 5)
9. Context gate integration (Idea 7)

### Phase 4: Advanced (Future)
10. Wave correlation across tokens (Idea 10)

---

## Open Questions

1. **How often should amplitude cache update?** Hourly? Daily? On significant price change?
2. **Should amplitude class be static or dynamic?** A token might shift from MED_AMP to HIGH_AMP during volatile periods.
3. **Backtest needed:** Which ideas actually improve win rate? All need validation.
4. **Interaction with existing ATR:** How does amplitude relate to ATR? Should they be combined or is one sufficient?
