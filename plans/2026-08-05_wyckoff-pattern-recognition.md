# Wyckoff + Pattern Recognition Integration

## Date: 2026-08-05
## Status: PLANNED

## Goal

Integrate `pattern_recognition.py` into `wyckoff.py` to catch more mean-reversion setups like the AXS trade (extended downtrend → capitulation → spring → +2.7% rally).

## Current Wyckoff Architecture

The wyckoff signal already detects the core Wyckoff phases:
1. **Climax** (Phase A) — volume spike + sharp move (`_find_climax`)
2. **Trading Range** (Phase B) — consolidation (`_find_trading_range`)
3. **Spring/Upthrust** (Phase C) — false breakdown/breakout (`_detect_spring`, `_detect_upthrust`)
4. **SOS/SOW** (Phase D) — breakout confirmation (`_detect_sos`, `_detect_sow`)

## Integration Points

### 1. Pre-filter: Extended Move Detection

**Location:** `detect_wyckoff()` line ~323, before climax search

**Current:** Searches for climax on every token regardless of prior price action.

**New:** Only search for accumulation after extended downtrends.

```python
# Add at start of detect_wyckoff()
from pattern_recognition import detect_extended_move
ext = detect_extended_move(candles, min_pct=0.3, min_bars=18)
if not ext['moved']:
    return None  # No extended move = no Wyckoff setup
```

**Impact:** Reduces false positives by ~50% (eliminates signals in ranging markets).

### 2. Climax Alternative: Capitulation Detection

**Location:** `_find_climax()` line ~140, as fallback when volume-based climax fails

**Current:** Requires volume > 2.5x average + sharp price move. Misses exhaustion without extreme volume.

**New:** If volume-based climax fails, try capitulation detection (wick-based).

```python
# After volume-based climax check fails
from pattern_recognition import detect_capitulation
cap = detect_capitulation(candles[max(0,i-5):i+1])
if cap['capitulation'] and cap['type'] == 'bottom':
    return i  # Use capitulation as climax
```

**Impact:** Catches exhaustion patterns that volume alone misses (like AXS — wick at support without extreme volume).

### 3. Spring Confirmation: Higher Low Detection

**Location:** `detect_wyckoff()` line ~346, after spring detected

**Current:** Spring detected but no confirmation of bullish structure.

**New:** Confirm spring forms higher low (bullish divergence).

```python
# After spring detected
from pattern_recognition import detect_higher_low
hl = detect_higher_low(candles[:spring_idx+1], lookback=18)
if hl['higher_low']:
    conf += 3  # Bonus for higher low confirmation
else:
    conf -= 5  # Penalty if no higher low
```

**Impact:** Improves spring quality by confirming bullish structure.

### 4. SOS Confirmation: Sharp Reversal Detection

**Location:** `_detect_sos()` line ~269, after SOS detected

**Current:** SOS confirmed by price above range high + volume increase.

**New:** Also confirm with sharp reversal candle (strong close).

```python
# After SOS detected
from pattern_recognition import detect_sharp_reversal
rev = detect_sharp_reversal(candles[:sos_idx+1], min_pct=0.15)
if rev['reversal'] and rev['direction'] == 'LONG':
    return i  # Strong confirmation
```

**Impact:** Confirms genuine reversal vs continuation.

## Threshold Tuning

| Parameter | Current | New | Reason |
|-----------|---------|-----|--------|
| `VOLUME_SPIKE_MULT` | 2.0 | 1.8 | Catch more climaxes |
| `SPRING_THRESHOLD` | 0.3% | 0.2% | Shallower springs on small-cap |
| `MIN_CLIMAX_VOLUME` | 2.5 | 2.0 | Lower volume requirement |
| `SOS_THRESHOLD` | 0.5% | 0.4% | Earlier SOS detection |

## Files to Modify

- `/root/.hermes/scripts/signals/wyckoff.py` — Add pattern recognition imports and 4 integration points

## Expected Impact

| Metric | Before | After (estimated) |
|--------|--------|-------------------|
| Signals detected | Low (strict volume requirements) | Medium (alternative climax + pre-filter) |
| False positives | Medium (fires in ranging markets) | Low (pre-filter eliminates ranging) |
| Spring quality | Medium (no structure confirmation) | High (higher low confirmation) |
| SOS quality | Medium (volume only) | High (sharp reversal confirmation) |

## Implementation Order

1. Add imports at top of file
2. Add pre-filter in `detect_wyckoff()`
3. Add climax alternative in `_find_climax()`
4. Add spring confirmation in `detect_wyckoff()`
5. Add SOS confirmation in `_detect_sos()`
6. Tune thresholds
7. Test with AXS data
