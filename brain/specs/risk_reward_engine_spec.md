# Risk-Reward Engine Spec (v2 — post-audit)

**Author:** CEO (Hermes Trading System)
**Date:** 2026-08-26
**Status:** REVISED — incorporates fixes from 2 independent audits
**Type:** Gate/Filter (upgrades `entry_gates.py::rr_gate`)

---

## Changelog (v2)

Fixed from audits:
1. **ATR unit bug** → use `volatility_gate.get_atr_pct()` (computes from candles, handles conversion correctly)
2. **Chinese constant name** → `RR_ENGINE_SL_STRUCTURAL_BUFFER`
3. **`signal_type` parameter** → added to `_compute_score()` signature, optional in `rr_gate()`
4. **Reuse existing S/R code** → import from `rs_signals.py` and `liquidation_map.py`, don't reimplement
5. **Regime alignment** → use `volatility_gate.REGIME_SIGNALS` lookup, not a new classification
6. **Per-component fallbacks** → each data source has explicit availability handling
7. **Added `compare_with_legacy()`** → shadow mode logs delta vs old rr_gate

---

## 1. Problem

Current `rr_gate()` in `entry_gates.py`:
- SL = ATR × 1.0 (fixed)
- TP = nearest swing high/low from 5m candles, capped at 2.5%
- R:R must be ≥ 2.0

Misses: liquidity clusters (magnets/cascades), order book walls, volatility width context, structural strength (touch count).

## 2. Solution: `risk_reward_engine.py`

Composite R:R evaluator that enriches the ATR-based gate with:
1. Multi-source S/R map (candle swings + order book + liquidation clusters)
2. Volatility width normalization (ATR% + Bollinger Band width)
3. Liquidity proximity scoring (clusters = targets or risks)
4. Structural R:R (reward measured to nearest wall, not arbitrary TP)

## 3. Data Sources (all existing)

| Source | File | Updated By |
|--------|------|-----------|
| ATR% | `volatility_gate.get_atr_pct()` | computes from `candles.db` |
| Candles (5m, 1h) | `candles.db` | `price_collector.py` |
| Liquidation clusters + composite S/R | `liquidation_clusters.json` | `liquidation_map.py` |
| Candle S/R (swing detection) | computed from `candles_5m` | reuse `rs_signals._find_swing_highs_lows()` |
| Bollinger Bands | computed from `candles_5m` on-the-fly | N/A |

## 4. Core Function

```python
def evaluate_rr(token, direction, price, candles_5m=None, signal_type=None):
    """Structural R:R evaluation.
    
    Returns dict with: pass, rr_ratio, sl_price, tp_price, score, grade, 
    block_reason, notes, sr_map, vol_width, liquidity, legacy_rr.
    """
```

## 5. Components

### 5.1 S/R Map
- Candle S/R: reuse `rs_signals._find_swing_highs_lows()` + `_cluster_levels()`
- Order book + liquidation S/R: read `liquidation_clusters.json → support_resistance` (already merged by `liquidation_map.py`)
- Also call `liquidation_map.get_sr_levels(coin)` for clean API access
- Merge all sources, sort by proximity to price
- Cluster nearby levels within ATR distance

### 5.2 Volatility Width
- ATR%: use `volatility_gate.get_atr_pct(token)` — handles dollar→percent conversion correctly
- ATR regime: use `volatility_gate.classify_volatility(atr_pct)`
- BB width: compute from last 20 candles in `candles_5m` (period=20, stddev=1.8 to match existing signals)
- BB squeeze: width < 0.04 (4%)
- Energy score: blend of ATR percentile and BB width

### 5.3 Liquidity Proximity
- Read from `liquidation_clusters.json → liquidation_clusters` key
- For LONG: clusters above = TP magnets, clusters below = cascade risk
- For SHORT: clusters below = TP magnets, clusters above = cascade risk
- `magnet_score`: how close nearest cluster is in trade direction
- `cascade_risk`: how close and large nearest cluster is against trade direction

### 5.4 Structural R:R
- SL: ATR × mult (from hermes_constants), extended beyond nearby structural level if needed
- TP: nearest S/R in trade direction, fallback to ATR-based TP
- Cap: regime-adjusted max (2.5% NORMAL, 3.0% FLAT, 2.0% HIGH/EXTREME)

### 5.5 Scoring (3 components for v1)
- R:R quality (50 pts) — higher R:R = more points
- Liquidity flow (25 pts) — trading toward clusters = bonus
- S/R clarity (25 pts) — clear structural target = bonus
- Grade: A (80+), B (65-79), C (50-64), D (35-49), F (<35)

## 6. Regime-Adjusted R:R Minimums

| Regime | Min R:R | Rationale |
|--------|---------|-----------|
| FLAT | 2.5 | Low energy, need bigger reward |
| NORMAL | 2.0 | Standard (matches existing rr_gate) |
| HIGH | 1.5 | Volatile, wider SL, accept lower ratio |
| EXTREME | 2.0 | Only specific signals trade here (11+ allowed by volatility_gate) |

## 7. Integration

Drop-in replacement for `rr_gate()` in `entry_gates.py`. Same return signature.
Shadow mode: `RR_ENGINE_SHADOW = True` → log verdicts but always pass.

## 8. Shadow Mode

```python
RR_ENGINE_ENABLED = True
RR_ENGINE_SHADOW = True   # log only, don't block
RR_ENGINE_FORCE = False    # switch to True after validation
```

Collect 7 days of data: blocked signals WR vs allowed signals WR.
Enforce only if blocked WR < 40%.

## 9. Constants

All in `hermes_constants.py`:
- `RR_ENGINE_ENABLED`, `RR_ENGINE_SHADOW`, `RR_ENGINE_FORCE`, `RR_ENGINE_FAIL_OPEN`
- `RR_ENGINE_MIN_RATIO_FLAT = 2.5`, `_NORMAL = 2.0`, `_HIGH = 1.5`, `_EXTREME = 2.0`
- `RR_ENGINE_SL_ATR_MULT = 1.0`, `RR_ENGINE_SL_STRUCTURAL_BUFFER = 0.002`
- `RR_ENGINE_TP_MIN_PCT = 0.005`, `RR_ENGINE_TP_MAX_PCT = 0.03`, `RR_ENGINE_TP_ATR_MULT = 2.0`
- `RR_ENGINE_SR_CLUSTER_ATR = 1.0`, `RR_ENGINE_SR_LOOKBACK = 300`, `RR_ENGINE_SR_MIN_TOUCHES = 3`
- `RR_ENGINE_LIQ_MAX_DIST = 2.0`, `RR_ENGINE_LIQ_MAGNET_BONUS = 10`, `RR_ENGINE_LIQ_FIGHT_PENALTY = -10`
- `RR_ENGINE_MIN_SCORE = 50`
- `RR_ENGINE_BB_PERIOD = 20`, `RR_ENGINE_BB_STDDEV = 1.8`, `RR_ENGINE_BB_SQUEEZE = 0.04`
- `RR_ENGINE_CACHE_TTL = 300`

## 10. File Changes

| File | Change |
|------|--------|
| `scripts/risk_reward_engine.py` | **NEW** — core engine |
| `scripts/entry_gates.py` | Upgrade `rr_gate()` to use engine |
| `scripts/hermes_constants.py` | Add `RR_ENGINE_*` constants |
| `brain/specs/risk_reward_engine_spec.md` | This file |
