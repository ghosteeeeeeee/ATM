# Position Sizing Extensions Spec

**Date**: 2026-08-08
**Status**: Approved — ready for implementation
**Priority**: High

## Current State

Implemented:
- Kelly criterion (quarter-Kelly, disabled until 50+ trades)
- Signal quality scoring (Sharpe >1, PF >1.5, WR >50%)
- Regime detection (mean-reversion vs momentum)
- HL API equity query

Constants:
- `KELLY_FRACTION = 0.25`
- `KELLY_MIN_POSITION_USDT = 11.0` (HL minimum)
- `KELLY_MAX_POSITION_USDT = 20.0`
- `KELLY_MAX_POSITION_PCT = 0.05`

## Proposed Extensions

### Phase 1: Quick Wins (This Week)

#### 1. Signal Weighting by Quality Score
**What**: Weight position size by signal quality grade
**Why**: Higher-quality signals deserve more capital
**Where**: `position_manager.py`

```python
def get_signal_weight(grade: str) -> float:
    weights = {'A': 1.5, 'B': 1.2, 'C': 1.0, 'D': 0.8, 'F': 0.5}
    return weights.get(grade, 1.0)

# Usage
quality = score_signal(signal)
weight = get_signal_weight(quality['grade'])
size = base_size * weight
```

**Risk**: Low — multiplicative adjustment only
**Impact**: Medium — better signals get more capital

#### 2. Drawdown-Responsive Sizing
**What**: Reduce position size during drawdowns
**Why**: Protect capital during losing streaks
**Where**: `position_manager.py`

```python
def get_drawdown_multiplier(equity: float, peak_equity: float) -> float:
    drawdown = (peak_equity - equity) / peak_equity if peak_equity > 0 else 0
    if drawdown > 0.10:  # 10% drawdown
        return 0.25  # Cut to quarter
    elif drawdown > 0.05:  # 5% drawdown
        return 0.50  # Cut to half
    return 1.0

# Usage
peak = get_peak_equity()
multiplier = get_drawdown_multiplier(current_equity, peak)
size = base_size * multiplier
```

**Risk**: Medium — may reduce sizing too aggressively
**Impact**: High — prevents blowups during losing streaks

#### 3. Portfolio Heat Limit
**What**: Limit total risk across all open positions
**Why**: Prevents correlation blowup
**Where**: `position_manager.py`

```python
def calculate_portfolio_heat(positions: list) -> float:
    """Total risk = sum of (size * stop_distance) for all positions."""
    total_risk = 0
    for pos in positions:
        stop_distance = abs(pos['entry'] - pos['stop_loss']) / pos['entry']
        total_risk += pos['size'] * stop_distance
    return total_risk

MAX_PORTFOLIO_HEAT = 0.15  # Max 15% total risk

def can_open_position(new_risk: float, current_heat: float) -> bool:
    return (current_heat + new_risk) <= MAX_PORTFOLIO_HEAT
```

**Risk**: Medium — may block legitimate trades
**Impact**: High — prevents overconcentration

#### 4. Conservative Mode Toggle
**What**: Manual override to reduce all sizing by 50%
**Why**: Human control during uncertainty periods
**Where**: `hermes_constants.py`, `position_manager.py`

```python
# hermes_constants.py
CONSERVATIVE_MODE_ENABLED = False
CONSERVATIVE_MODE_MULTIPLIER = 0.5

# position_manager.py
def apply_conservative_mode(size: float) -> float:
    if CONSERVATIVE_MODE_ENABLED:
        return size * CONSERVATIVE_MODE_MULTIPLIER
    return size
```

**Risk**: Low — manual toggle only
**Impact**: High — instant human override capability

### Phase 2: Next 2 Weeks

#### 5. Correlation Matrix
**What**: Check if new signal is redundant with existing
**Why**: Avoid correlated signals that don't diversify
**Where**: `signal_validator.py`

```python
def check_correlation(new_signal_returns, existing_signals, threshold=0.7):
    for name, returns in existing_signals.items():
        corr = np.corrcoef(new_signal_returns, returns)[0, 1]
        if abs(corr) > threshold:
            return False, f"Correlated with {name}: {corr:.2f}"
    return True, "OK"
```

**Risk**: Low — check only
**Impact**: Medium — better diversification

#### 6. Walk-Forward Validation Pipeline
**What**: Auto-disable signals that fail walk-forward test
**Why**: Prevents overfit signals from trading live
**Where**: `signal_auditor.py`

```python
def validate_signal(signal: str, trades: list) -> bool:
    results = walk_forward_test(trades)
    if not results['robust']:
        log(f"Signal {signal} failed walk-forward: {results['overfitting_pct']}")
        return False
    if results['avg_test_sharpe'] < 0.5:
        log(f"Signal {signal} test Sharpe too low: {results['avg_test_sharpe']}")
        return False
    return True
```

**Risk**: Low — validation only
**Impact**: Medium — prevents overfit signals

#### 7. Adaptive Kelly Fraction
**What**: Increase/decrease Kelly based on recent performance
**Why**: Scale with demonstrated edge
**Where**: `position_sizing.py`

```python
def get_adaptive_kelly_fraction(recent_sharpe: float) -> float:
    if recent_sharpe > 2.0:
        return 0.35  # Strong edge
    elif recent_sharpe > 1.5:
        return 0.30  # Good edge
    elif recent_sharpe > 1.0:
        return 0.25  # Base (quarter-Kelly)
    elif recent_sharpe > 0.5:
        return 0.15  # Weak edge
    else:
        return 0.05  # Minimal
```

**Risk**: Medium — dynamic adjustment
**Impact**: Medium — better capital allocation

### Phase 3: Month 2

#### 8. Signal Decay Detection (HIGH PRIORITY)
**What**: Detect when signals stop working
**Why**: Catch regime changes
**Where**: `hebbian_learner.py`

```python
def detect_signal_decay(signal: str, lookback=50) -> bool:
    rolling_wr = calculate_rolling_win_rate(signal, lookback)
    original_wr = get_historical_wr(signal)
    if rolling_wr < original_wr * 0.85:  # 15% decay
        return True
    return False
```

**Risk**: Low — detection only
**Impact**: High — prevents trading dead signals

#### 9. Volatility-Normalized Sizing (MEDIUM PRIORITY)
**What**: Size inversely proportional to volatility
**Why**: Equal risk per trade
**Where**: `position_manager.py`

```python
def volatility_adjusted_size(base_size: float, atr_pct: float, target_vol=2.0):
    adjustment = target_vol / atr_pct if atr_pct > 0 else 1.0
    return base_size * min(adjustment, 2.0)  # Cap at 2x
```

**Risk**: Medium — dynamic adjustment
**Impact**: Medium — better risk normalization

#### 10. Session-Based Sizing (LOW PRIORITY)
**What**: More capital during high-liquidity sessions
**Why**: Better fills, less slippage
**Where**: `position_manager.py`

```python
def get_session_multiplier() -> float:
    hour = datetime.utcnow().hour
    if 8 <= hour <= 16:  # US/EU
        return 1.2
    elif 0 <= hour <= 8:  # Asia
        return 0.8
    return 1.0
```

**Risk**: Low — timing adjustment
**Impact**: Low — crypto is 24/7, weak correlation

## Implementation Order

| Phase | Items | Timeline | Risk |
|-------|-------|----------|------|
| Phase 1 | #1, #2, #3, #4 | This week | Low-Medium |
| Phase 2 | #5, #6, #7 | Next 2 weeks | Low-Medium |
| Phase 3 | #8, #9, #10 | Month 2 | Medium |

## Testing Plan

1. **Unit tests**: Each function tested with known inputs
2. **Paper trading**: Run Phase 1 for 1 week before live
3. **A/B test**: Compare sizing with/without extensions
4. **Monitor**: Watch for overfitting or regime sensitivity

## Implementation Cautions (from CEO)

1. Signal Weighting must use quality grades from hebbian_learner (already produces A-F)
2. Drawdown-Responsive needs equity tracking — verify `equity_history` table exists or add peak_equity tracking
3. Portfolio Heat needs open positions data — check if positions table is populated
4. Conservative Mode must override all other sizing logic (Kelly, quality weighting, etc.)

## CEO Decisions (2026-08-08)

| Question | Decision |
|----------|----------|
| Phase 1 items | All four — Signal Weighting → Drawdown-Responsive → Portfolio Heat → Conservative Mode |
| Circuit breaker | 10% — keep current (`KELLY_DRAWDOWN_CIRCUIT_BREAKER = 0.10`) |
| Kelly trades | 50 — keep current, variance too high for 30 |
| Conservative mode | Yes — `CONSERVATIVE_MODE_ENABLED = False` + 0.5x multiplier |
| Phase 2 reorder | Correlation Matrix before Walk-Forward (simpler first) |
| Phase 3 priority | Signal Decay (HIGH) > Volatility-Normalized (MEDIUM) > Session-Based (LOW) |
