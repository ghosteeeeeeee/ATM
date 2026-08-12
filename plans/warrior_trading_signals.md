# Warrior Trading Signal Enhancements

## Status: PLANNED
## Created: 2026-08-11

## Overview
Signal ideas derived from Warrior Trading's day trading methodology, mapped to gaps in Hermes system.

---

## Priority 1: Quick Wins

### 1. Time-of-Day Filter
- **File**: `scripts/signals_runner.py` (modify existing)
- **Concept**: Avoid first 30 minutes of trading session (high volatility, fakeouts)
- **Logic**: Skip signal generation during UTC 00:00-00:30
- **Effort**: 10 lines

### 2. Volume-Price Divergence
- **File**: `scripts/signals/vol_price_divergence.py` (new)
- **Concept**: Price making new highs/lows but volume declining = reversal signal
- **Direction**: LONG (bullish divergence), SHORT (bearish divergence)
- **Confirmation**: Require 3+ declining volume bars while price extends
- **Effort**: ~150 lines

### 3. Hammer/Shooting Star at S/R
- **File**: `scripts/signals/hammer_reversal.py` (new)
- **Concept**: Classic reversal candles at key support/resistance
- **Logic**: Detect hammer (bullish) or shooting star (bearish) near S/R zones
- **Confirmation**: Volume spike on the pattern candle
- **Effort**: ~120 lines

---

## Priority 2: Pattern Enhancements

### 4. Morning/Evening Star
- **File**: `scripts/signals/morning_star.py` (new)
- **Concept**: Three-candle reversal pattern (strong confirmation)
- **Logic**: Doji/small body in middle, large candle before and after
- **Effort**: ~100 lines

### 5. Doji Breakout
- **File**: `scripts/signals/doji_breakout.py` (new)
- **Concept**: Indecision candle followed by directional breakout
- **Logic**: Doji → next candle closes above/below doji range
- **Effort**: ~80 lines

### 6. Flag/Pennant Breakout
- **File**: `scripts/signals/flag_breakout.py` (new)
- **Concept**: Consolidation after strong move → continuation
- **Logic**: Detect tight range after >2% move, enter on breakout
- **Effort**: ~150 lines

---

## Priority 3: System Enhancements

### 7. ATR Trailing Stops
- **File**: `scripts/position_manager.py` (modify existing)
- **Concept**: Dynamic trailing stops based on ATR, not fixed %
- **Logic**: Trail at 2x ATR from entry, tighten to 1.5x after 1:1
- **Effort**: ~50 lines

### 8. Scale-In Logic
- **File**: `scripts/position_manager.py` (modify existing)
- **Concept**: Add to winning positions at predefined levels
- **Logic**: Add 50% at +1%, 25% at +2% (max 3 adds)
- **Effort**: ~80 lines

### 9. Daily Loss Limit
- **File**: `scripts/position_manager.py` (modify existing)
- **Concept**: Stop trading after X% daily drawdown
- **Logic**: Track daily P&L, halt new trades if drawdown > 2%
- **Effort**: ~40 lines

---

## Priority 4: Advanced Patterns

### 10. Wedge Reversal
- **File**: `scripts/signals/wedge_reversal.py` (new)
- **Concept**: Rising/falling wedge = reversal pattern
- **Effort**: ~200 lines

### 11. Triangle Breakout
- **File**: `scripts/signals/triangle_breakout.py` (new)
- **Concept**: Ascending/descending/symmetrical triangle
- **Effort**: ~200 lines

### 12. Event Filter
- **File**: `scripts/event_filter.py` (new)
- **Concept**: Avoid trading during major crypto events (hard forks, upgrades)
- **Integration**: Calendar API or static list
- **Effort**: ~100 lines

---

## Signal Architecture (Reference)

All new signals must follow:
```
scripts/signals/<name>.py
├── run(prices_dict=None) → int  # Entry point
├── scan_<name>_signals(prices_dict) → int
├── detect_<pattern>(...) → dict or None
└── CLI test in __main__
```

Register in:
- `scripts/signals/__init__.py` (import + registry entry)
- `scripts/hermes_constants.py` (ENABLED flags)

---

## Testing Strategy

1. Backtest each signal on 20-day historical data
2. Verify win rate > 45% and positive avg PNL
3. Check for false signals in choppy markets
4. Confirm cooldown/cooldown interactions

---

## Notes

- Warrior Trading edge = avoiding mistakes, not complex strategies
- Focus on confirmation over prediction
- Volume confirms price moves
- Time filters reduce noise significantly
