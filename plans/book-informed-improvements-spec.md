# Hermes Trading System — Book-Informed Improvements Spec

**Date**: 2026-08-08
**Status**: Ready for implementation
**Source**: Top trading books + Kelly criterion research

---

## Phase 1: Quick Wins (This Week)

### 1. Half-Kelly Position Sizing
**Source**: Kelly criterion (Wikipedia), Ralph Vince — Mathematics of Money Management

**Current state**: Fixed $11 per trade
**Problem**: Doesn't scale with edge or bankroll

**Formula** (from Wikipedia):
```
f* = p/l - q/g

Where:
- f* = fraction of bankroll to bet
- p = probability of winning (win_rate)
- q = probability of losing (1 - win_rate)
- g = gain on win (avg_win_pct / 100)
- l = loss on loss (avg_loss_pct / 100)
```

**Half-Kelly** (safer, 50% of full Kelly):
```
kelly_size = 0.5 * (win_rate - (1 - win_rate) * (avg_loss / avg_win))
position_size = bankroll * kelly_size
```

**Implementation**:
- File: `position_manager.py`
- Add `calculate_kelly_size()` function
- Query last 100 trades per signal for win_rate, avg_win, avg_loss
- Cap at max position size

**Test**: Backtest with last 30 days of trades

---

### 2. Walk-Forward Testing
**Source**: Ernest Chan — Algorithmic Trading

**Current state**: Single train/test split
**Problem**: Overfitting to specific time period

**Implementation**:
```python
def walk_forward_test(data, window=0.8, step=0.1):
    results = []
    for start in range(0, 1 - window, step):
        train_end = start + window
        test_end = min(train_end + 0.2, 1.0)
        train = data[start:train_end]
        test = data[train_end:test_end]
        results.append(backtest(train, test))
    return average_results(results)
```

**Where**: `signal_auditor.py`, new `backtest_utils.py`

---

### 3. Correlation Check Before Adding Signals
**Source**: López de Prado — Advances in Financial ML

**Current state**: No correlation check
**Problem**: Redundant signals waste capital

**Implementation**:
```python
def check_signal_correlation(new_signal_returns, existing_signals):
    for name, returns in existing_signals.items():
        corr = np.corrcoef(new_signal_returns, returns)[0, 1]
        if abs(corr) > 0.7:
            return False, f"Too correlated with {name}: {corr:.2f}"
    return True, "OK"
```

**Where**: `signals/__init__.py`, new `signal_validator.py`

---

### 4. Liquidity-Adjusted Position Sizing
**Source**: Larry Harris — Trading and Exchanges

**Current state**: Same size regardless of liquidity
**Problem**: Slippage on illiquid tokens

**Implementation**:
```python
def liquidity_adjusted_size(base_size, volume_24h, min_volume=100000):
    if volume_24h < min_volume:
        return base_size * (volume_24h / min_volume)
    return base_size
```

**Where**: `position_manager.py`

---

## Phase 2: Signal Quality (Next 2 Weeks)

### 5. Signal Quality Scoring
**Source**: Ernest Chan — Algorithmic Trading

**Thresholds**:
- Sharpe Ratio > 1.0
- Profit Factor > 1.5
- Win Rate > 55% (for mean-reversion)
- Min 30 trades for statistical significance

**Where**: `signal_compactor.py`, `signal_auditor.py`

---

### 6. Meta-Labeling
**Source**: López de Prado — Advances in Financial ML

**Concept**: Instead of predicting direction, predict whether signal will succeed given current conditions

**Implementation**:
- Train classifier on (signal + market_features) → success/failure
- Only trade when classifier confidence > 70%

**Where**: `signal_compactor.py`

---

### 7. Regime Detection
**Source**: Ernest Chan — Algorithmic Trading

**Concept**: Detect mean-reversion vs momentum regimes

**Implementation**:
- Use ADF test for stationarity
- ADF p-value < 0.05 → mean-reversion regime
- ADF p-value > 0.10 → momentum regime

**Where**: `counter_flip.py`, `squeeze_cross.py`

---

## Phase 3: Advanced (Month 2)

### 8. Alpha Decay Detection
**Source**: Rishi Narang — Inside the Black Box

**Concept**: Detect when signals are dying

**Implementation**:
- Track rolling 30-day Sharpe ratio
- Alert when Sharpe drops below 0.5
- Auto-disable signals with persistent decay

**Where**: `hebbian_learner.py`, `signal_auditor.py`

---

### 9. Forecast Combination
**Source**: Robert Carver — Systematic Trading

**Concept**: How to combine 40+ signals without correlation blowup

**Implementation**:
- Equal weight baseline (rarely loses)
- Inverse-volatility weighting (often wins)
- Risk budget allocation

**Where**: `signal_compactor.py`

---

### 10. Market Impact Models
**Source**: Cartea, Jaimungal — Algorithmic and High-Frequency Trading

**Concept**: Estimate slippage on larger trades

**Implementation**:
- Impact = k * sqrt(size / ADV)
- Reduce position size when impact > 0.1%

**Where**: `position_manager.py`, `hyperliquid_exchange.py`

---

## Implementation Order

| Phase | Items | Timeline | Effort |
|-------|-------|----------|--------|
| Phase 1 | #1, #2, #3, #4 | This week | Small |
| Phase 2 | #5, #6, #7 | Next 2 weeks | Medium |
| Phase 3 | #8, #9, #10 | Month 2 | Large |

---

## Testing Plan

### Unit Tests
- Kelly sizing: verify formula against known values
- Walk-forward: verify rolling windows
- Correlation: verify against known correlated signals

### Integration Tests
- Backtest each improvement against last 30 days
- Compare Sharpe ratio before/after
- Verify no regression in existing signals

### Paper Trading
- Run Phase 1 improvements on paper for 1 week
- Monitor win rate, PnL, position sizes
- Go live only if improvement confirmed

---

## Book References

1. **Algorithmic Trading** — Ernest Chan (2013)
   - ISBN: 978-1118460146
   - Focus: Mean reversion, momentum, regime detection

2. **Advances in Financial Machine Learning** — Marcos López de Prado (2018)
   - ISBN: 978-1119482086
   - Focus: Meta-labeling, triple-barrier, feature importance

3. **The Mathematics of Money Management** — Ralph Vince (1992)
   - ISBN: 978-0471547389
   - Focus: Position sizing, optimal f, Kelly criterion

4. **Systematic Trading** — Robert Carver (2015)
   - ISBN: 978-0995029309
   - Focus: Portfolio construction, forecast combination

5. **Trading and Exchanges** — Larry Harris (2003)
   - ISBN: 978-0195158984
   - Focus: Market microstructure, liquidity, order flow
