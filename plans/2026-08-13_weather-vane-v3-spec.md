# Weather Vane v3 — Predictive Methods Deep Dive

**Date:** 2026-08-13
**Status:** PROPOSED — awaiting CEO review
**Goal:** Give the Weather Vane PREDICTIVE powers — detect regime shifts BEFORE losses happen

---

## Current Weather Vane (v2) — Reactive Only

The v2 weather vane is purely reactive: it watches losses accumulate, then suppresses. By the time it fires, the damage is done. We need leading indicators that detect the weather changing BEFORE the storm hits.

---

## Proposed Predictive Methods

### Method 1: Per-Token Consecutive Loss Counter

**Concept:** Track consecutive losses per token (not per direction). If a token has 3+ consecutive losses, something is wrong with that token's setup — suppress ALL signals for it.

**Why it's predictive:** A token that just lost 3 times in a row is likely in a choppy or adverse regime. The NEXT signal for that token is likely to lose too.

**Implementation:**
```python
def get_consecutive_losses(token: str, direction: str) -> int:
    """Count consecutive losses for this token+direction."""
    # Query signal_outcomes ORDER BY created_at DESC
    # Count losses from most recent until first win
    # Return count

# In _score_signal():
consec = get_consecutive_losses(token, direction)
if consec >= 3:
    dir_outcome_mult = min(dir_outcome_mult, 0.6)  # strong penalty
elif consec >= 2:
    dir_outcome_mult = min(dir_outcome_mult, 0.8)  # mild penalty
```

**Params:**
```python
CONSEC_LOSS_ENABLED = True
CONSEC_LOSS_THRESHOLD_HARD = 3    # 3+ consecutive → 0.6x penalty
CONSEC_LOSS_THRESHOLD_MILD = 2    # 2 consecutive → 0.8x penalty
```

**Backtest plan:** Query signal_outcomes for consecutive loss streaks, check if 3+ streaks predict future losses.

---

### Method 2: Volume Spike Detection

**Concept:** Unusual volume spikes often precede price reversals. If a token's volume spikes 3x+ above its 24h average, a move is coming.

**Why it's predictive:** Volume spikes indicate institutional activity or accumulation/distribution. The direction of the spike predicts the next move.

**Implementation:**
```python
def check_volume_spike(token: str) -> str:
    """Check if token has a volume spike. Returns 'BULLISH_SPIKE', 'BEARISH_SPIKE', or None."""
    # Query candles_1h volume for last 24h
    # Compute avg volume per hour
    # Compare current hour to avg
    # If >3x avg: check if price closed up (bullish spike) or down (bearish spike)

# In _score_signal():
spike = check_volume_spike(token)
if spike == 'BULLISH_SPIKE' and direction == 'SHORT':
    dir_outcome_mult = min(dir_outcome_mult, 0.7)  # bullish spike = bad for SHORT
elif spike == 'BEARISH_SPIKE' and direction == 'LONG':
    dir_outcome_mult = min(dir_outcome_mult, 0.7)  # bearish spike = bad for LONG
```

**Params:**
```python
VOLUME_SPIKE_ENABLED = True
VOLUME_SPIKE_THRESHOLD = 3.0    # 3x average volume = spike
VOLUME_SPIKE_PENALTY = 0.7
```

---

### Method 3: Volatility Expansion

**Concept:** Periods of low volatility (tight BB, low ATR) are followed by explosive moves. Detect compression → expect expansion → suppress signals during expansion.

**Why it's predictive:** Volatility is mean-reverting. After compression comes expansion. Entering during expansion = chasing.

**Implementation:**
```python
def check_volatility_expansion(token: str) -> bool:
    """Check if ATR expanded 2x+ from recent average."""
    # Get ATR(14) from candles_1h
    # Compare to 24h average ATR
    # If current > 2x avg: expansion detected

# In _score_signal():
if check_volatility_expansion(token):
    dir_outcome_mult = min(dir_outcome_mult, 0.75)  # volatility = uncertainty
```

**Params:**
```python
VOL_EXPANSION_ENABLED = True
VOL_EXPANSION_THRESHOLD = 2.0    # 2x ATR expansion
VOL_EXPANSION_PENALTY = 0.75
```

---

### Method 4: Time-of-Day Pattern

**Concept:** Certain hours consistently produce worse trades. Suppress signals during historically bad hours.

**Why it's predictive:** Market microstructure creates predictable patterns. Low-liquidity hours (3-5 AM) have wider spreads and more noise.

**Implementation:**
```python
def get_time_penalty() -> float:
    """Return penalty based on current hour's historical performance."""
    hour = datetime.now().hour
    # Look up historical WR for this hour
    # If WR < 45%: return 0.8x penalty
    # If WR > 55%: return 1.0x (no penalty)
```

**Params:**
```python
TIME_PATTERN_ENABLED = True
TIME_PATTERN_BAD_WR = 45        # hours with WR below this get penalized
TIME_PATTERN_PENALTY = 0.8
```

---

### Method 5: Entry Price vs Recent Range

**Concept:** If entry price is at the extreme of the recent range (top for LONG, bottom for SHORT), the trade is chasing. Suppress signals at extremes.

**Why it's predictive:** Buying at the top or selling at the bottom = chasing. Mean reversion is more likely.

**Implementation:**
```python
def check_price_extreme(token: str, direction: str, price: float) -> bool:
    """Check if price is at extreme of recent range."""
    # Get 24h high/low from candles_1h
    # Compute position: (price - low) / (high - low)
    # If LONG and position > 0.90: price near top → chasing
    # If SHORT and position < 0.10: price near bottom → chasing

# In _score_signal():
if check_price_extreme(token, direction, price):
    dir_outcome_mult = min(dir_outcome_mult, 0.75)
```

**Params:**
```python
PRICE_EXTREME_ENABLED = True
PRICE_EXTREME_THRESHOLD = 0.90   # 90th percentile = extreme
PRICE_EXTREME_PENALTY = 0.75
```

---

### Method 6: Multi-Token Correlation Break

**Concept:** When correlated tokens diverge, the market is shifting. Track correlation between token pairs — when it drops, suppress signals.

**Why it's predictive:** Correlated assets moving together = stable market. Divergence = regime change.

**Implementation:**
```python
def check_correlation_break(token: str) -> bool:
    """Check if token's correlation with its peers dropped."""
    # Define peer groups (e.g., SOL ecosystem: SOL, RAY, JTO)
    # Compute 24h price correlation
    # If correlation dropped below 0.5: divergence detected

# In _score_signal():
if check_correlation_break(token):
    dir_outcome_mult = min(dir_outcome_mult, 0.8)
```

**Params:**
```python
CORRELATION_BREAK_ENABLED = True
CORRELATION_BREAK_THRESHOLD = 0.5
CORRELATION_BREAK_PENALTY = 0.8
```

---

### Method 7: Regime Scanner Alignment

**Concept:** If the 4h regime scanner says LONG_BIAS but the Weather Vane sees SHORT losses, there's a conflict. Trust the real-time data.

**Why it's predictive:** The regime scanner is lagging. When it disagrees with real-time outcomes, the real-time data is usually right.

**Implementation:**
```python
def check_regime_conflict(token: str, direction: str) -> bool:
    """Check if regime scanner contradicts recent outcomes."""
    # Get regime from regime_4h.json
    # Get recent outcomes for this direction
    # If regime says LONG_BIAS but SHORT is losing: conflict

# In _score_signal():
if check_regime_conflict(token, direction):
    dir_outcome_mult = min(dir_outcome_mult, 0.7)
```

**Params:**
```python
REGIME_CONFLICT_ENABLED = True
REGIME_CONFLICT_PENALTY = 0.7
```

---

### Method 8: Spread/Tightness Monitor

**Concept:** Wide bid-ask spreads indicate illiquidity or uncertainty. Signals fired during wide spreads get worse fills.

**Why it's predictive:** Wide spreads = market makers uncertain = incoming move.

**Implementation:** Requires real-time spread data (not currently tracked). Defer until data source available.

**Params:** N/A (deferred)

---

## Priority Ranking

| # | Method | Predictive Power | Complexity | Data Available | Priority |
|---|--------|-----------------|------------|----------------|----------|
| 1 | Consecutive losses | High | Low | ✅ signal_outcomes | **NOW** |
| 5 | Price extremes | Medium | Low | ✅ candles_1h | **NOW** |
| 2 | Volume spikes | Medium | Low | ✅ candles_1h | **NOW** |
| 4 | Time-of-day | Low-Medium | Low | ✅ trade outcomes | **NOW** |
| 3 | Volatility expansion | Medium | Low | ✅ candles_1h | NEXT |
| 7 | Regime conflict | Medium | Low | ✅ regime_4h.json | NEXT |
| 6 | Correlation break | Medium | Medium | ✅ price history | LATER |
| 8 | Spread monitor | High | High | ❌ needs data | DEFERRED |

---

## Recommended Implementation Order

1. **Consecutive losses** (#1) — most direct, highest impact
2. **Price extremes** (#5) — simple, catches chasing
3. **Volume spikes** (#2) — catches institutional activity
4. **Time-of-day** (#4) — catches low-liquidity hours

Methods 5-8 can be added later as data sources become available.

---

## Integration Approach

All methods feed into the same `_score_signal()` function as the existing Weather Vane:

```python
# Layer 0: Structure shift (LONG only, per 14-day backtest)
# Layer 1: Consecutive losses (per-token)
# Layer 2: Price extremes (per-token)
# Layer 3: Volume spikes (per-token)
# Layer 4: Time-of-day (market-wide)
# Layer 5: Loss cluster (existing v2)

# Minimum penalty wins — any layer can trigger suppression
```

---

## Files to Modify

| File | Change |
|------|--------|
| `scripts/hermes_constants.py` | Add all new params |
| `scripts/signal_compactor.py` | Add helper functions + integrate into `_score_signal()` |
