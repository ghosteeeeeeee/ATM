# Trading Book Action Items Spec

**Source**: Top 5 trading books ranked by actionability
**Date**: 2026-08-08
**Status**: Draft

## Quick Wins (implement now, no book reading needed)

### 1. Half-Kelly Position Sizing
**What**: Replace fixed $11 with optimal-f per signal
**Formula**: `0.5 * (win_rate - (1-win_rate) * avg_loss / avg_win)`
**Where**: `position_manager.py`, `hermes_constants.py`
**Effort**: small
**Priority**: HIGH

```python
# Add to hermes_constants.py
KELLY_FRACTION = 0.5  # Half-Kelly for safety

# Add to position_manager.py
def calculate_kelly_size(win_rate, avg_win, avg_loss, equity):
    kelly = win_rate - (1 - win_rate) * (avg_loss / avg_win)
    return equity * KELLY_FRACTION * kelly
```

### 2. Walk-Forward Testing
**What**: Replace single train/test split with rolling windows
**Where**: `signal_auditor.py`, `backtest_*.py`
**Effort**: medium
**Priority**: HIGH

```python
# Rolling 80/20 windows
def walk_forward_test(data, window_size=0.8, step=0.1):
    results = []
    for start in range(0, 1 - window_size, step):
        train = data[start:start + window_size]
        test = data[start + window_size:start + window_size + 0.2]
        results.append(backtest(train, test))
    return average_results(results)
```

### 3. Correlation Check Before Adding Signals
**What**: Before adding new signal, check >0.7 correlation with existing
**Where**: `signals/__init__.py`, new `signal_validator.py`
**Effort**: small
**Priority**: MEDIUM

```python
def check_signal_correlation(new_signal, existing_signals):
    for sig in existing_signals:
        corr = pearsonr(new_signal.returns, sig.returns)
        if abs(corr) > 0.7:
            return False, f"Too correlated with {sig.name}: {corr:.2f}"
    return True, "OK"
```

### 4. Liquidity-Adjusted Position Sizing
**What**: Reduce size when 24h volume < threshold
**Where**: `position_manager.py`
**Effort**: small
**Priority**: MEDIUM

```python
def liquidity_adjusted_size(base_size, volume_24h, min_volume=100000):
    if volume_24h < min_volume:
        return base_size * (volume_24h / min_volume)
    return base_size
```

---

## Medium-Term (require book reading)

### 5. Signal Quality Scoring (Chan)
**What**: Score signals by Sharpe ratio and profit factor
**Thresholds**: Sharpe > 1.0, Profit Factor > 1.5
**Where**: `signal_compactor.py`, `signal_auditor.py`
**Effort**: medium

### 6. Meta-Labeling (López de Prado)
**What**: Predict whether signal will succeed given current conditions
**Where**: `signal_compactor.py`
**Effort**: large

### 7. Regime Detection (Chan)
**What**: Detect mean-reversion vs momentum regimes
**Where**: `counter_flip.py`, `squeeze_cross.py`
**Effort**: medium

### 8. Alpha Decay Detection (Narang)
**What**: Detect when signals are dying
**Where**: `hebbian_learner.py`, `signal_auditor.py`
**Effort**: medium

---

## Long-Term (full book implementation)

### 9. Forecast Combination (Carver)
**What**: How to combine 40+ signals without correlation blowup
**Where**: `signal_compactor.py`
**Effort**: large

### 10. Optimal Execution (Cartea)
**What**: Market impact models for larger trades
**Where**: `position_manager.py`, `hyperliquid_exchange.py`
**Effort**: large

---

## Implementation Order

| Phase | Items | Timeline |
|-------|-------|----------|
| Phase 1 | #1, #2, #3, #4 | This week |
| Phase 2 | #5, #6, #7 | Next 2 weeks |
| Phase 3 | #8, #9, #10 | Month 2 |

---

## Book Ingestion Plan

| Book | How to Get | Skill Name |
|------|------------|------------|
| Algorithmic Trading — Chan | Buy PDF or find summary | book_chan |
| Advances in Financial ML — López de Prado | Buy PDF or find summary | book_delprado |
| Math of Money Management — Vince | Buy PDF or find summary | book_vince |
| Systematic Trading — Carver | Buy PDF or find summary | book_carver |
| Trading and Exchanges — Harris | Buy PDF or find summary | book_harris |
