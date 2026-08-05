# Self-Learning System — Full Spec

## 1. Overview

**Purpose:** Automatically detect signal decay and adjust parameters to maintain profitability.

**Core Principle:** Scientific method — change ONE variable at a time, measure impact, iterate.

**Architecture:**
```
signal_outcomes → self_learner → hermes_constants.py → signal_analyst → better signals
```

## 2. Goal Definition

**Success Metrics:**

| Metric | Target | Minimum | Critical |
|--------|--------|---------|----------|
| Win Rate | > 45% | > 35% | < 25% |
| PnL (7d) | > +$1.00 | > $0 | < -$2.00 |
| Trades/day | 5-15 | 3 | < 1 |
| Consecutive losses | < 3 | < 5 | > 8 |

**Failure Triggers:**

| Condition | Action |
|-----------|--------|
| WR < 25% for 10+ trades | Emergency: disable signal |
| WR < 35% for 15+ trades | Tighten filters |
| WR > 60% for 20+ trades | Loosen filters |
| 5+ consecutive losses | Pause signal, human review |
| PnL < -$2.00 in 7d | Reduce position sizing |

## 3. Parameter Tuning Rules

**What can be adjusted:**

| Parameter | Current | Tighten (+5%) | Loosen (-5%) | Range |
|-----------|---------|---------------|--------------|-------|
| RSI_OVERSOLD | 40 | 42 | 38 | [30, 50] |
| RSI_OVERBOUGHT | 60 | 63 | 57 | [50, 70] |
| BB_TOUCH_PCT | 0.20 | 0.21 | 0.19 | [0.10, 0.30] |
| BOUNCE_MIN_PCT | 0.05 | 0.0525 | 0.0475 | [0.02, 0.10] |
| TREND_FILTER_NEUTRAL_PCT | 0.1 | 0.105 | 0.095 | [0.05, 0.20] |
| SPEED_MIN_THRESHOLD | 30 | 32 | 28 | [20, 40] |

**Adjustment logic:**
```python
def adjust_parameter(param_name, current_value, direction):
    config = PARAM_CONFIG[param_name]
    step = config['step']
    min_val = config['min']
    max_val = config['max']
    
    if direction == 'tighten':
        new_value = current_value * (1 + step)
    else:
        new_value = current_value * (1 - step)
    
    new_value = max(min_val, min(max_val, new_value))
    if new_value == current_value:
        return None
    return new_value
```

## 4. Performance Analysis

**Rolling window:** Last 30 trades per signal type

**Metrics computed:**
- Win rate (wins / total)
- Average win size
- Average loss size
- Profit factor (gross wins / gross losses)
- Max drawdown
- Sharpe ratio (simplified)

**Decay detection:**
```python
def detect_decay(trades):
    if len(trades) < 10:
        return False
    half = len(trades) // 2
    first_wr = calculate_wr(trades[:half])
    second_wr = calculate_wr(trades[half:])
    return first_wr - second_wr > 0.15
```

## 5. Scientific Method Implementation

**Rule:** Change ONE parameter at a time.

```python
last_change = load_last_change()
if last_change and trades_since(last_change) < 15:
    return  # Wait for more data

param = find_weakest_param(signal_type)
adjust_param(param, direction)
log_change(param, old_value, new_value, reason)
```

## 6. Logging & Audit

**Every change logged to:**
- `automation/self_learning_log.json`
- Format: `{timestamp, signal_type, param, old_value, new_value, reason, wr_before, wr_after}`

**Daily summary:**
- Total adjustments made
- Parameters changed
- Impact on WR (before/after)

## 7. Safety Rails

| Constraint | Value | Rationale |
|------------|-------|-----------|
| Max adjustments/day | 3 | Prevent over-fitting |
| Min trades between changes | 15 | Need data to judge |
| Parameter range limits | Defined per param | Prevent extreme values |
| Human override | CEO can lock params | Prevent unwanted changes |
| Emergency stop | WR < 25% | Disable signal entirely |

## 8. Integration

**Pipeline flow:**
```
signal_outcomes → self_learner (daily) → hermes_constants.py → signals
```

**Systemd timer:**
```
hermes-self-learner.timer — daily at 06:00 UTC
```

## 9. Monitoring

**Dashboard metrics:**
- Parameters changed this week
- WR trend (improving/declining)
- Adjustment impact (WR before/after)
- Active signal health scores

## 10. Rollout Plan (2-Day Timeline)

| Phase | Time | Action |
|-------|------|--------|
| 1. Build | Day 1 AM | Create self_learner.py, integrate into pipeline |
| 2. Shadow | Day 1 PM - Day 2 AM | Log only, validate logic |
| 3. Limited | Day 2 AM | Allow 1 adjustment/day, monitor |
| 4. Full | Day 2 PM | Allow 3 adjustments/day, fully online |

**Day 1:**
- 06:00-12:00: Build self_learner.py
- 12:00-18:00: Integrate into pipeline, test
- 18:00-00:00: Shadow mode, validate logging

**Day 2:**
- 00:00-06:00: Monitor shadow results
- 06:00-12:00: Enable limited mode (1 adjustment/day)
- 12:00-18:00: Monitor, verify adjustments work
- 18:00+: Full mode (3 adjustments/day)
