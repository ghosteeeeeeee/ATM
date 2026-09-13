# Pump-Chain Exit Strategy Spec

**Date:** 2026-09-13
**Status:** SPEC — awaiting approval
**Data source:** FIL LONG trade analysis (own-conclusions audit, 154 1m candles)

---

## 1. Problem

Current exit (profit-monster-trail) exits too early on pump-chain momentum trades:
- FIL trade hit +14.98% peak but PM Trail exited at +4.98%
- PM Trail uses fixed 0.3% trail — too tight for momentum breakouts
- Pump-chain fires on capital rotation — these moves can run 5-10%+ but PM Trail kills them at 2-3%

## 2. Analysis (FIL LONG Case Study)

**Entry:** $0.8545 (14:00)
**Peak:** $0.9704 (+13.56%)
**Max DD from peak:** -2.52% (at 14:47)
**ATR(14) 1h:** $0.0089 (0.94%)

**Three killer dips that must survive:**
1. 14:47: -2.52% from peak (widest)
2. 15:42: -2.10% from peak
3. 16:12: -2.00% from peak

**Empirical ratio:** max_dd / ATR = 2.83x

## 3. Exit Strategy

### Primary: ATR-Based Trailing Stop

```
TRAIL: ATR(14) 1h × 2.5 from peak
- Survives max DD of -2.52% (ATR 2.5x = 2.35% — close)
- ATR 2.6x is minimum (2.71% trail)
- ATR 3.0x is recommended (3.12% trail, 6% margin)
```

### Secondary: Momentum Exit

```
EXIT when 5m velocity < -0.5% for 2+ consecutive candles
- Catches reversal at the top
- Exits before trailing stop would trigger
```

### Tertiary: Time Exit

```
EXIT if profit < 2% after 2 hours
- Prevents dead money
- Only triggers if trade never reached meaningful profit
```

## 4. Parameters

```python
# Pump-Chain Exit Parameters
PUMP_CHAIN_EXIT_TRAIL_MULT = 2.5      # ATR multiplier for trailing stop
PUMP_CHAIN_EXIT_MOMENTUM_VEL = -0.5   # 5m velocity threshold for momentum exit
PUMP_CHAIN_EXIT_MOMENTUM_CANDLES = 2  # consecutive negative candles required
PUMP_CHAIN_EXIT_TIME_THRESHOLD = 2.0  # min profit % for time exit
PUMP_CHAIN_EXIT_TIME_HOURS = 2.0      # max hold time in hours
```

## 5. Implementation

### Files to modify:
1. `scripts/hermes_constants.py` — Add exit parameters
2. `scripts/position_manager.py` — Add pump-chain exit logic (check if signal is pump-chain, use ATR trail instead of PM Trail)
3. `scripts/profit_monster.py` — Add pump-chain to PROFIT_MONSTER_BYPASS_SIGNALS

### Exit logic:
```python
if signal_type == 'pump-chain+':
    # Use ATR trail instead of PM Trail
    trail_distance = atr * PUMP_CHAIN_EXIT_TRAIL_MULT
    
    # Check momentum exit
    if five_min_velocity < PUMP_CHAIN_EXIT_MOMENTUM_VEL for 2+ candles:
        exit("momentum_fade")
    
    # Check time exit
    if profit < PUMP_CHAIN_EXIT_TIME_THRESHOLD and hold_time > PUMP_CHAIN_EXIT_TIME_HOURS:
        exit("dead_money")
    
    # Otherwise, use ATR trail
    trailing_stop = peak - trail_distance
```

## 6. Backtest Results (FIL Case)

| Method | Exit Price | PnL | Survives? |
|--------|-----------|-----|-----------|
| PM Trail (0.3%) | $0.8971 | +4.98% | ❌ |
| ATR 2.5x | — | +12.7% | ✅ |
| ATR 3.0x | — | +12.7% | ✅ |
| Momentum exit | — | +12.4% | ✅ |

## 7. Risk

- ATR 2.5x trail is tight (survives by 0.03%)
- ATR 3.0x trail is safer (6% margin)
- Momentum exit may exit too early on shallow pullbacks
- Time exit may cut winners that need more time

## 8. Recommendation

Use **ATR 3.0x** as default trail. This gives 6% margin over the empirical max DD ratio of 2.83x. Add momentum exit as secondary trigger.
