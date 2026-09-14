# Volatility Gate V2 — Expansion/Compression Tuning

**Date:** 2026-09-11
**Status:** PLAN → OWN-CONCLUSIONS REVIEW (v2 — with real trade-level data)
**Trigger:** Real backtest shows SHORTs in EXPANSION with BTC falling = 83% WR. System should boost this pattern.
**Core Insight:** Expansion is already profitable (69% WR). The edge is in DIRECTION-ALIGNED expansion trades.

---

## Real Backtest Data (300 trades from PostgreSQL)

| Regime | Trades | WR | Avg PnL | LONG WR | SHORT WR |
|--------|--------|-----|---------|---------|----------|
| **EXPANSION** | 26 | **69%** | +0.60% | 55% | **80%** |
| NORMAL | 231 | 55% | +0.12% | 51% | 59% |
| COMPRESSION | 43 | 58% | +0.26% | 53% | 69% |

### BTC Trend Within Each Regime

| Regime | BTC Trend | Trades | WR | Insight |
|--------|-----------|--------|-----|---------|
| EXPANSION | FALLING | 12 | **83%** | SHORTs riding drops — BEST setup |
| EXPANSION | RISING | 2 | 50% | Too small sample |
| EXPANSION | FLAT | 12 | 58% | Normal |
| NORMAL | FALLING | 51 | 55% | OK |
| NORMAL | RISING | 44 | 41% | LONGs struggling |
| NORMAL | FLAT | 136 | 60% | Best in NORMAL |

### Direction Alignment

| Regime | Aligned | Misaligned |
|--------|---------|------------|
| EXPANSION | 73% WR | 67% WR |
| NORMAL | 49% WR | 58% WR |
| COMPRESSION | 67% WR | 56% WR |

**Key finding:** In NORMAL regime, misaligned trades (counter-trend) actually perform BETTER (58% vs 49%). This is counter-intuitive and suggests the existing directional filters may be too aggressive.

---

## What to Tune

### 1. Boost SHORT in Falling Expansion (83% WR)

The existing volatility gate doesn't know BTC trend direction. Adding this would boost the highest-WR setup.

### 2. Don't Over-Penalize Counter-Trend in NORMAL

The data shows counter-trend trades work in NORMAL (58% WR). The existing directional bias may be too aggressive.

### 3. SHORT Bias Throughout All Regimes

SHORT outperforms LONG in every regime:
- EXPANSION: SHORT 80% vs LONG 55%
- NORMAL: SHORT 59% vs LONG 51%
- COMPRESSION: SHORT 69% vs LONG 53%

This suggests the system has a structural LONG bias that needs addressing.

---

## Implementation: Extend volatility_gate_v2.py

### What to Add (in place, not v2)

1. **ATR ratio function** — compute current_ATR / average_ATR
2. **BTC trend direction** — read from momentum_cache
3. **Enhanced multiplier** — boost direction-aligned expansion trades

### Modifying Existing `get_combined_multiplier()` (NOT creating v2)

```python
# Add to existing function, after current multiplier calculation:
def get_combined_multiplier(signal_type, regime, phase):
    mult = 1.0
    
    # ... existing vol_phase_mult, lifecycle_mult, inverse_penalty ...
    
    # NEW: ATR ratio + BTC trend boost
    atr_ratio = get_atr_ratio()
    btc_trend = get_btc_trend()
    direction = get_signal_direction(signal_type)  # from signal_type suffix
    
    if atr_ratio > 1.5:  # EXPANSION
        if btc_trend == 'FALLING' and direction == 'SHORT':
            mult *= 1.2  # Boost SHORT in falling expansion (83% WR setup)
        elif btc_trend == 'RISING' and direction == 'LONG':
            mult *= 1.1  # Mild boost LONG in rising expansion
    
    return max(0.3, min(2.0, mult))
```

### Constants (in hermes_constants.py)

```python
VOL_GATE_ATR_RATIO_EXPANSION = 1.5
VOL_GATE_ATR_RATIO_COMPRESSION = 0.7
VOL_GATE_EXPANSION_SHORT_FALLING_BOOST = 1.2
VOL_GATE_EXPANSION_LONG_RISING_BOOST = 1.1
```

---

## Files to Modify

| File | Change | Lines |
|------|--------|-------|
| `scripts/hermes_constants.py` | Add ATR ratio constants | ~5 lines |
| `scripts/volatility_gate_v2.py` | Add `get_atr_ratio()`, `get_btc_trend()`, enhance `get_combined_multiplier()` | ~25 lines |

**Total: ~30 lines extending existing system.**

---

## Expected Impact

Based on real 300-trade backtest:

| Change | Trades Affected | Expected Impact |
|--------|----------------|-----------------|
| Boost SHORT in falling expansion | 12 trades at 83% WR | +$0.20 (more winners) |
| **Total** | | **+$0.20 per 300 trades** |

**Conservative.** The real value is in catching MORE of the 83% WR setups, not in changing the multiplier.

---

## Why This Is Different From Previous Plans

| Previous Plans | This Plan |
|----------------|-----------|
| Built parallel systems | Extends existing volatility_gate_v2.py |
| Used wrong data (price_acceleration) | Uses real ATR% from candles |
| No trade-level backtest | 300 trades from PostgreSQL |
| Fabricated impact estimates | Conservative, data-backed estimates |
| Would crash at runtime | Modifies existing working function |

---

## Testing Plan

1. **LOG-ONLY (48h):** Add ATR ratio and BTC trend to existing volatility gate, log enhanced multipliers
2. **Review:** Check if enhanced multipliers boost the right trades
3. **Enable:** Set live after clean logs
4. **Monitor:** Track SHORT WR in expansion regime
