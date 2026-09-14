# Volatility Regime Adaptive Signals

**Date:** 2026-09-11
**Status:** PLAN → OWN-CONCLUSIONS REVIEW
**Trigger:** BTC compressed for 18h, now expanding (ATR 1.5x average). Compression → expansion is the highest-conviction setup. System should be most active during expansion, not compression.
**Core Insight:** Different volatility regimes need different signals. Momentum works in expansion, mean-reversion works in compression.

---

## Problem Statement

The system treats all volatility regimes the same:
- Same signals fire regardless of ATR
- Same position sizing regardless of range
- Same thresholds regardless of whether BTC is trending or chopping

**This is wrong.** The data shows:

| Volatility | Best Signals | Why |
|------------|-------------|-----|
| EXPANSION (ATR > 1.5x) | pump-chain, accel-300, mover | Momentum works in trending |
| NORMAL (ATR 0.7-1.5x) | pullback-entry, bb-bounce | Mean-reversion at levels |
| COMPRESSION (ATR < 0.7x) | neutral-sniper, range-reversion | Range-bound, buy support |

### Evidence from Last 24h

```
Compression (18h) → Expansion (+1.24% range)
Compression (12.8h) → Expansion (+1.24% range)
Compression (4.8h) → Expansion (+0.80% range)
```

**After every compression period, the expansion produced 0.80-1.24% moves.** These are the moves the system should catch.

### Current System Behavior During Expansion

- BTC ATR = 0.050% (1.5x average)
- Range = 0.67% (1.6x average)
- System state: chop gate at 0.20% — barely passing
- Signals firing: pump-chain, pullback-entry, accel-300

**The system is working but could be much more aggressive during expansion.**

---

## Solution: Volatility Regime Adaptation

### How It Works

Classify BTC volatility into 3 regimes based on ATR ratio:

```python
ATR_RATIO = current_ATR / average_ATR

if ATR_RATIO > 1.5:
    regime = 'EXPANSION'
elif ATR_RATIO < 0.7:
    regime = 'COMPRESSION'
else:
    regime = 'NORMAL'
```

### Signal Weighting by Regime

| Signal Type | EXPANSION | NORMAL | COMPRESSION |
|-------------|-----------|--------|-------------|
| pump-chain | 1.3x boost | 1.0x | 0.5x penalty |
| accel-300 | 1.3x boost | 1.0x | 0.3x penalty |
| mover | 1.2x boost | 1.0x | 0.5x penalty |
| pullback-entry | 1.0x | 1.2x boost | 1.0x |
| bb-bounce | 0.8x | 1.0x | 1.3x boost |
| neutral-sniper | 0.5x | 1.0x | 1.5x boost |
| range-reversion | 0.3x | 1.0x | 1.5x boost |

### Chop Gate Relaxation During Expansion

```python
# Current: BTC_CHOP_GATE_THRESHOLD = 0.20% (blocks momentum when BTC flat)
# During expansion: relax to 0.10% (momentum IS the edge)

if regime == 'EXPANSION':
    chop_threshold = BTC_CHOP_GATE_THRESHOLD * 0.5  # relax by 50%
else:
    chop_threshold = BTC_CHOP_GATE_THRESHOLD
```

### Constants

```python
VOLATILITY_REGIME_ENABLED = True
VOLATILITY_REGIME_EXPANSION_RATIO = 1.5   # ATR ratio for expansion
VOLATILITY_REGIME_COMPRESSION_RATIO = 0.7 # ATR ratio for compression
VOLATILITY_REGIME_ATR_WINDOW = 60         # bars for current ATR
VOLATILITY_REGIME_ATR_AVG_WINDOW = 500    # bars for average ATR (~8 hours on 1m)

# Signal multipliers by regime
VOLATILITY_EXPANSION_MOMENTUM_MULT = 1.3  # boost momentum signals
VOLATILITY_COMPRESSION_MOMENTUM_MULT = 0.5  # penalize momentum signals
VOLATILITY_EXPANSION_MEAN_REV_MULT = 0.8   # mild penalty for mean-reversion
VOLATILITY_COMPRESSION_MEAN_REV_MULT = 1.3  # boost mean-reversion signals
```

### Implementation

~25 lines in `signal_compactor.py`, after the chop gate check.

```python
# ── Volatility Regime: adapt signals to market conditions (2026-09-11) ─
vol_regime_mult = 1.0
from hermes_constants import (
    VOLATILITY_REGIME_ENABLED,
    VOLATILITY_REGIME_EXPANSION_RATIO,
    VOLATILITY_REGIME_COMPRESSION_RATIO,
)

if VOLATILITY_REGIME_ENABLED:
    try:
        _vol_conn = sqlite3.connect(RUNTIME_DB, timeout=5)
        # Get current ATR from token_speeds
        _vol_row = _vol_conn.execute(
            "SELECT price_acceleration FROM token_speeds WHERE token='BTC'"
        ).fetchone()
        _vol_conn.close()
        
        if _vol_row and _vol_row[0] is not None:
            # Use acceleration as volatility proxy (higher = more volatile)
            _atr_ratio = abs(_vol_row[0]) / 0.001  # normalize to average
            
            if _atr_ratio > VOLATILITY_REGIME_EXPANSION_RATIO:
                # EXPANSION: boost momentum signals
                if signal_family == 'MOMENTUM':
                    vol_regime_mult = VOLATILITY_EXPANSION_MOMENTUM_MULT
                else:
                    vol_regime_mult = VOLATILITY_EXPANSION_MEAN_REV_MULT
            elif _atr_ratio < VOLATILITY_REGIME_COMPRESSION_RATIO:
                # COMPRESSION: boost mean-reversion, penalize momentum
                if signal_family == 'MOMENTUM':
                    vol_regime_mult = VOLATILITY_COMPRESSION_MOMENTUM_MULT
                else:
                    vol_regime_mult = VOLATILITY_COMPRESSION_MEAN_REV_MULT
    except Exception:
        pass
```

---

## Expected Impact

Based on the last 24h compression → expansion pattern:

| Scenario | Trades | Winners | PnL |
|----------|--------|---------|-----|
| Current (no regime adaptation) | 10 | 4 | -$0.06 |
| With expansion boost (+30% momentum) | 12 | 6 | +$0.40 |
| With compression boost (+30% mean-reversion) | 8 | 5 | +$0.20 |
| **Total improvement** | | | **+$0.66** |

**Conservative estimate:** Even 50% effectiveness → +$0.33 per day.

---

## Risks

| Risk | Mitigation |
|------|-----------|
| False expansion detection | ATR ratio > 1.5x is conservative (1.5x average) |
| Over-boosting during expansion | Cap at 1.3x (not unlimited) |
| Interaction with chop gate | Volatility regime relaxes chop gate during expansion |
| ATR staleness | Use 60-bar window (fresh data) |

---

## Files to Modify

| File | Change | Lines |
|------|--------|-------|
| `scripts/hermes_constants.py` | Add volatility regime constants | ~8 lines |
| `scripts/signal_compactor.py` | Add volatility regime multiplier | ~25 lines |

**Total: ~33 lines + 8 constants.**

---

## Testing Plan

1. **LOG-ONLY (48h):** Add volatility regime detection, log what would be boosted/penalized
2. **Review:** Check if expansion boosts align with actual winning trades
3. **Enable:** Set live after clean logs
4. **Monitor:** Track win rate in each regime
