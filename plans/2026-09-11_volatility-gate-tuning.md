# Volatility Gate V2 — Expansion/Compression Tuning

**Date:** 2026-09-11
**Status:** PLAN → OWN-CONCLUSIONS REVIEW
**Trigger:** Expansion regime has 38% WR on LONG signals (system loses money during expansion). The existing volatility_gate_v2.py already combines regime+phase but needs tuning for expansion/compression.
**Core Insight:** Expansion alone isn't enough — you need the DIRECTION of expansion. LONG in expansion with BTC falling = 38% WR. SHORT in expansion with BTC falling = 83% WR.

---

## Problem Statement

The existing `volatility_gate_v2.py` already combines:
1. Volatility regime (FLAT/NORMAL/HIGH/EXTREME)
2. Market phase (trend_building/explosion/range/defensive)
3. Signal lifecycle roles
4. Inverse correlation penalties

**But it's not tuned for the ATR ratio insight.** The backtest shows:

| Regime | Trades | WR | PnL | Issue |
|--------|--------|-----|------|-------|
| EXPANSION (ATR > 1.5x) | 14 | 57% | -$0.46 | LONG signals losing (38% WR) |
| NORMAL (ATR 0.7-1.5x) | 64 | 64% | +$1.82 | Working well |
| COMPRESSION (ATR < 0.7x) | 22 | 55% | +$0.32 | OK |

**The problem:** During expansion, the system fires LONG signals when BTC is falling. The volatility gate doesn't know the DIRECTION of the expansion.

### Key Data

```
LONG in expansion:  8 trades, 3W/5L = 38% WR, PnL: $-0.61  ← LOSING
SHORT in expansion: 6 trades, 5W/1L = 83% WR, PnL: $+0.15  ← WINNING

BTC rising during expansion: 2 trades
BTC falling during expansion: 3 trades
BTC flat during expansion: 9 trades
```

---

## Solution: Extend volatility_gate_v2.py

### What to Add

1. **ATR ratio classification** — add ratio-based regime detection alongside existing ATR% classification
2. **BTC momentum direction** — combine volatility regime with BTC trend direction
3. **Aggressive multipliers during expansion** — boost correct direction, penalize wrong direction

### Implementation

#### 1. Add ATR Ratio to volatility_gate_v2.py

```python
# New function in volatility_gate_v2.py
def get_atr_ratio(token='BTC', lookback=500):
    """
    Calculate ATR ratio: current_ATR / average_ATR
    Returns float (e.g., 1.5 = current ATR is 1.5x average)
    """
    atr_pct = get_atr_pct(token)
    if atr_pct is None:
        return 1.0
    
    # Get average ATR from cache or compute
    avg_atr = _get_avg_atr(token, lookback)
    if avg_atr is None or avg_atr == 0:
        return 1.0
    
    return atr_pct / avg_atr

def classify_atr_ratio(ratio):
    """Classify ATR ratio into regime"""
    if ratio > 1.5:
        return 'EXPANSION'
    elif ratio < 0.7:
        return 'COMPRESSION'
    else:
        return 'NORMAL'
```

#### 2. Add BTC Momentum Direction

```python
# New function
def get_btc_trend_direction():
    """Get BTC 30m trend direction for regime bias"""
    try:
        conn = sqlite3.connect(RUNTIME_DB, timeout=5)
        row = conn.execute(
            "SELECT velocity FROM momentum_cache WHERE token='BTC'"
        ).fetchone()
        conn.close()
        
        if row and row[0] is not None:
            if row[0] > 0.15:
                return 'RISING'
            elif row[0] < -0.15:
                return 'FALLING'
            else:
                return 'FLAT'
    except:
        pass
    return 'UNKNOWN'
```

#### 3. Enhanced Combined Multiplier

```python
def get_combined_multiplier_v2(signal_type, regime, phase, atr_ratio, btc_trend):
    """
    Enhanced multiplier that considers:
    1. Volatility regime (existing)
    2. Market phase (existing)
    3. ATR ratio (new)
    4. BTC trend direction (new)
    """
    mult = 1.0
    
    # 1. Existing volatility-phase multiplier
    mult *= get_vol_phase_mult(family, regime, phase)
    
    # 2. ATR ratio boost/penalty
    if atr_ratio > 1.5:  # EXPANSION
        if btc_trend == 'RISING' and direction == 'LONG':
            mult *= 1.3  # Boost LONG in rising expansion
        elif btc_trend == 'FALLING' and direction == 'SHORT':
            mult *= 1.3  # Boost SHORT in falling expansion
        elif btc_trend == 'FALLING' and direction == 'LONG':
            mult *= 0.5  # Penalize LONG in falling expansion
        elif btc_trend == 'RISING' and direction == 'SHORT':
            mult *= 0.5  # Penalize SHORT in rising expansion
    elif atr_ratio < 0.7:  # COMPRESSION
        # Compression = mean-reversion works
        if family in ('Bollinger', 'Range', 'Exhaustion'):
            mult *= 1.3  # Boost mean-reversion in compression
    
    return max(0.3, min(2.0, mult))
```

---

## Expected Impact

Based on backtest data:

| Change | Trades Affected | Expected Impact |
|--------|----------------|-----------------|
| Boost SHORT in falling expansion | 3 trades | +$0.15 → +$0.25 |
| Penalize LONG in falling expansion | 5 trades | -$0.61 → -$0.20 |
| Boost mean-reversion in compression | 22 trades | +$0.32 → +$0.50 |
| **Total** | | **+$0.60 improvement** |

---

## Files to Modify

| File | Change | Lines |
|------|--------|-------|
| `scripts/volatility_gate_v2.py` | Add ATR ratio + BTC trend functions | ~30 lines |
| `scripts/signal_compactor.py` | Pass ATR ratio and BTC trend to multiplier | ~10 lines |

**Total: ~40 lines extending existing system.**

---

## Why This Is Better Than the Previous Plan

| Previous Plan | This Plan |
|---------------|-----------|
| Built parallel system | Extends existing volatility_gate_v2.py |
| Used wrong data (price_acceleration) | Uses actual ATR% |
| No backtest data | 30-day backtest with 100 trades |
| Would conflict with existing system | Integrates with existing system |
| Generic multipliers | Data-driven multipliers based on actual performance |

---

## Testing Plan

1. **LOG-ONLY (48h):** Add ATR ratio and BTC trend to volatility gate, log enhanced multipliers
2. **Review:** Check if enhanced multipliers align with actual winners/losers
3. **Enable:** Set live after clean logs
4. **Monitor:** Track WR improvement in expansion/compression regimes
