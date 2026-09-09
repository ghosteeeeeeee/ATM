# RR Engine Exit System — Spec

**Author:** CEO (Hermes Trading System)
**Date:** 2026-09-08
**Status:** SPEC
**Type:** Structural exit management using existing RR engine

---

## 1. Core Concept

The RR engine already knows the structural levels at entry. Use the SAME engine to manage exits by re-evaluating periodically during the trade.

**No separate exit logic needed.** The engine IS the exit manager.

---

## 2. How It Works

### At Entry (already exists)
```
evaluate_rr(token, direction, price) →
  SL: below nearest support
  TP: at next resistance
  R:R: ratio
  sr_map: all structural levels
  liquidity: cluster positions
```

### During Trade (new)
```
Every 5 minutes:
  evaluate_rr(token, direction, current_price) →
    Compare current price to structural levels
    If near resistance → take profit
    If support broken → cut loss
    If support moved up → trail SL
    If liquidation cluster ahead → prepare exit
```

---

## 3. Exit Rules

### Rule 1: TP at Resistance
```python
# When price is within 0.3% of a resistance level → take profit
for level in sr_map:
    if level['type'] == 'resistance':
        dist = abs(level['price'] - current_price) / current_price
        if dist < 0.003:  # within 0.3%
            EXIT = 'RESISTANCE_TP'
```

**Why:** Resistance = rejection zone. Price often reverses at these levels.

### Rule 2: SL at Support Break
```python
# When price breaks below nearest support → cut loss
for level in sr_map:
    if level['type'] == 'support':
        if current_price < level['price']:
            EXIT = 'SUPPORT_BREAK'
```

**Why:** Support = structural floor. If it breaks, the setup is invalidated.

### Rule 3: Trail SL to Support
```python
# As price rises, move SL to the next support level above previous SL
new_support = find_nearest_support(current_price, direction='below')
if new_support > current_sl:
    SL = new_support
```

**Why:** Support levels are where price bounces. Trailing to support protects profits while giving the trade room to breathe.

### Rule 4: Exit Before Liquidation Cluster
```python
# When price approaches a liquidation cluster → exit before cascade
for cluster in liquidation_clusters:
    dist = abs(cluster['price'] - current_price) / current_price
    if dist < 0.005:  # within 0.5%
        EXIT = 'LIQUIDATION_ZONE'
```

**Why:** Liquidation clusters = forced selling/buying zones. Price often cascades through these.

### Rule 5: Structural R:R Deterioration
```python
# Re-evaluate R:R — if it's deteriorating, exit
new_rr = evaluate_rr(token, direction, current_price)
if new_rr['rr_ratio'] < 1.0:  # R:R below 1:1
    EXIT = 'RR_DETERIORATION'
```

**Why:** If the trade's R:R has deteriorated (e.g., resistance appeared above, support broke below), the setup is no longer valid.

---

## 4. Exit Priority

When multiple exit signals fire simultaneously:

| Priority | Exit Type | Rationale |
|----------|-----------|-----------|
| 1 | SUPPORT_BREAK | Structural floor broken — must exit |
| 2 | LIQUIDATION_ZONE | Cascade imminent — exit before forced selling |
| 3 | RR_DETERIORATION | Setup no longer valid |
| 4 | RESISTANCE_TP | Take profit at structural ceiling |
| 5 | TRAIL_SUPPORT | Trail SL to next support |

---

## 5. Re-evaluation Frequency

| Regime | Frequency | Rationale |
|--------|-----------|-----------|
| FLAT | Every 10 min | Low volatility, less urgent |
| NORMAL | Every 5 min | Standard monitoring |
| HIGH | Every 3 min | Fast moves need faster response |
| EXTREME | Every 1 min | Cascade risk is high |

---

## 6. Integration with Existing Systems

### With Profit Monster
- Profit Monster handles quick profit-taking (Tier 1/2)
- RR engine handles structural exits (resistance, support breaks)
- They work together: PM catches quick profits, RR engine catches structural exits

### With Cut Loser
- Cut Loser handles time-based and loss-based exits
- RR engine handles structural exits (support breaks, R:R deterioration)
- They work together: CL catches quick losses, RR engine catches structural failures

### With ATR SL/TP
- ATR SL/TP is the fallback when structural levels are unclear
- RR engine overrides ATR when structural levels are present
- They work together: ATR handles the "no structure" case, RR engine handles the "structure present" case

---

## 7. Pseudo-code

```python
def manage_exit(token, direction, entry_price, entry_sl, entry_tp, trade_data):
    """Manage exit using RR engine structural analysis.
    
    Called every N minutes during an open trade.
    """
    current_price = get_current_price(token)
    
    # Re-evaluate RR engine
    result = evaluate_rr(token, direction, current_price)
    sr_map = result['sr_map']
    liquidity = result['liquidity']
    
    # Rule 1: TP at resistance
    for level in sr_map:
        if level['type'] == 'resistance':
            dist = abs(level['price'] - current_price) / current_price
            if dist < 0.003:  # within 0.3%
                return 'TAKE_PROFIT', current_price, 'resistance_tp'
    
    # Rule 2: SL at support break
    for level in sr_map:
        if level['type'] == 'support':
            if direction == 'LONG' and current_price < level['price']:
                return 'CUT_LOSS', current_price, 'support_break'
            if direction == 'SHORT' and current_price > level['price']:
                return 'CUT_LOSS', current_price, 'support_break'
    
    # Rule 3: Trail SL to support
    new_sl = find_trail_sl(sr_map, direction, current_sl)
    if new_sl != current_sl:
        UPDATE_SL = new_sl
    
    # Rule 4: Exit before liquidation cluster
    for cluster in liquidity.get('clusters', []):
        dist = abs(cluster['price'] - current_price) / current_price
        if dist < 0.005:
            return 'EXIT', current_price, 'liquidation_zone'
    
    # Rule 5: R:R deterioration
    if result['rr_ratio'] < 1.0:
        return 'EXIT', current_price, 'rr_deterioration'
    
    # No exit signal — hold
    return 'HOLD', current_price, None
```

---

## 8. Constants

```python
# RR Engine Exit System
RR_EXIT_ENABLED = True
RR_EXIT_FREQUENCY_FLAT = 600       # 10 min
RR_EXIT_FREQUENCY_NORMAL = 300     # 5 min
RR_EXIT_FREQUENCY_HIGH = 180       # 3 min
RR_EXIT_FREQUENCY_EXTREME = 60     # 1 min

# Exit thresholds
RR_EXIT_RESISTANCE_DIST = 0.003    # within 0.3% of resistance = TP
RR_EXIT_SUPPORT_BREAK缓冲 = 0.001   # 0.1% below support = break
RR_EXIT_LIQUIDATION_DIST = 0.005   # within 0.5% of cluster = exit
RR_EXIT_RR_MIN = 1.0              # R:R below 1:1 = deterioration

# Trail logic
RR_EXIT_TRAIL_ENABLED = True
RR_EXIT_TRAIL_BUFFER = 0.002      # 0.2% below support for SL
```

---

## 9. Example: DOT Sep 8

```
Entry: $1.095
SR Map:
  Support: $1.080 (3 touches)
  Resistance: $1.150 (2 touches)
  Liquidation cluster: $1.200

Exit evaluation at each 5-min interval:

14:40  price=$1.095  → HOLD (just entered)
14:45  price=$1.098  → HOLD (price rising)
14:50  price=$1.102  → HOLD (price rising)
...
15:12  price=$1.150  → TAKE_PROFIT (hit resistance at $1.150, +5.0%)

OR if resistance breaks:
15:12  price=$1.152  → Resistance broken, new support = $1.150
15:15  price=$1.160  → HOLD (price above new support)
15:20  price=$1.180  → HOLD (price rising)
...
15:45  price=$1.200  → EXIT (liquidation cluster at $1.200, +9.6%)
```

---

## 10. Advantages Over Fixed Exits

| | Fixed Exit | RR Engine Exit |
|---|---|---|
| TP target | Arbitrary ($0.15, 2%) | Nearest resistance |
| SL placement | Fixed (1.5% ATR) | Below support level |
| Trail logic | Fixed % from peak | Trail to next support |
| Cascade awareness | None | Exit before liquidation zones |
| Volatility adaptation | None | Adjusts frequency to regime |
| R:R monitoring | None | Exits if R:R deteriorates |

---

## 11. Backtest Plan

1. Run existing pullback entry signals (790 signals, 54% WR)
2. Apply RR engine exits instead of fixed 4h exit
3. Compare: win rate, avg return, max drawdown
4. Validate: does the engine correctly identify resistance/support exits?

---

## 12. File Changes

| File | Change |
|------|--------|
| `scripts/risk_reward_engine.py` | Add `manage_exit()` function |
| `scripts/hermes_constants.py` | Add `RR_EXIT_*` constants |
| `scripts/position_manager.py` | Call `manage_exit()` periodically |

No new files needed — extends existing engine.
