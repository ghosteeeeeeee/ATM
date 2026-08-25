# Coin Tracker System Specification

## Version: 2.0
## Date: 2026-08-25
## Status: Active

---

## 1. Executive Summary

The Coin Tracker is a per-coin intelligence system that collects, scores, and predicts market movements using 20 factors. It plugs into the Hermes trading system to improve signal quality, entry timing, and exit management.

**Core Value:** Predict moves BEFORE they happen using weather, liquidation, contrarian signals, and technical analysis.

---

## 2. System Architecture

### 2.1 Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         EXTERNAL DATA SOURCES                               │
├─────────────────────────────────────────────────────────────────────────────┤
│  hl_cache.json     │  candles.db      │  weather_station.json              │
│  (prices, meta)    │  (multi-TF)      │  (tide, sea, wind)                │
│                    │                   │  liquidation_clusters.json        │
│                    │                   │  (stop hunts, cascades)           │
└─────────┬──────────┴─────────┬─────────┴──────────────┬────────────────────┘
          │                    │                        │
          ▼                    ▼                        ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           COIN TRACKER                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│  coin_tracker.py — Main collector (runs every 5 min)                       │
│  coin_tracker_score.py — 20-factor scoring engine                          │
│  coin_tracker_schema.py — Database schema                                  │
│  coin_tracker_analysis.py — Wyckoff, Elliott Wave, S/R, Trend, Vol Profile│
└─────────┬──────────────────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         COIN TRACKER.DB                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│  agg_scores — Per-coin composite scores (health, composite, predictive)   │
│  coin_{TOKEN} — Per-coin event history (price, indicators, scores)        │
│  _coin_registry — Coin metadata (health, leverage, decimals)              │
└─────────┬──────────────────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                      TRADING SYSTEM INTEGRATION                             │
├─────────────────────────────────────────────────────────────────────────────┤
│  signal_gen ──▶ signal_compactor ──▶ context_gate ──▶ position_manager     │
│       │               │                  │                  │              │
│       ▼               ▼                  ▼                  ▼              │
│  coin_tracker_hot  confluence        rule-based         dynamic SL/TP     │
│  (20 factors)      scoring           validation          R:R-based        │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Coin Tracker Components

### 3.1 Main Collector (`coin_tracker.py`)

**Purpose:** Collect and score all coins every 5 minutes.

**Input:**
- `hl_cache.json` — prices, metadata
- `candles.db` — 5m, 1h, 4h candles
- `weather_station.json` — tide, sea state, wind
- `liquidation_clusters.json` — stop hunts, cascades
- `token_speeds` table — price acceleration

**Output:**
- `coin_tracker.db` — per-coin scores and events

**Process:**
1. Read all coins from hl_cache
2. For each coin:
   - Compute 20 factor scores
   - Calculate composite score
   - Calculate predictive score
   - Determine health (hot/warm/cold)
   - Store in database
3. Compute health distribution
4. Detect contrarian signals
5. Generate predictive alerts

### 3.2 Scoring Engine (`coin_tracker_score.py`)

**20 Scoring Factors:**

| # | Factor | Weight | Description |
|---|--------|--------|-------------|
| 1 | momentum | 14% | Price momentum (EMA, RSI) |
| 2 | volume | 6% | Volume analysis |
| 3 | volatility | 5% | ATR-based volatility |
| 4 | spread | 5% | Bid-ask spread quality |
| 5 | signals | 3% | Signal count and confidence |
| 6 | regime | 3% | Market regime (bull/bear/neutral) |
| 7 | wyckoff | 12% | Wyckoff phase analysis |
| 8 | ewave | 6% | Elliott Wave count |
| 9 | trend | 5% | Trend quality score |
| 10 | setup | 4% | Setup type (long/short) |
| 11 | clustering | 3% | Signal clustering |
| 12 | recency | 4% | Data freshness |
| 13 | liquidation | 5% | Liquidation proximity |
| 14 | tide | 4% | Market flow alignment |
| 15 | sea_state | 3% | Market health |
| 16 | wind | 3% | Momentum alignment |
| 17 | token_regime | 2% | Historical performance |
| 18 | contrarian | 5% | Health distribution |
| 19 | macd_div | 4% | MACD divergence |
| 20 | rr | 4% | Risk/reward ratio |

**Total: 100%**

### 3.3 Health Classification

| Health | Composite | Description |
|--------|-----------|-------------|
| hot | ≥ 63 | Strong setup, ready to trade |
| warm | 50-62 | Moderate setup, monitor |
| cold | < 50 | Weak setup, avoid |

### 3.4 Predictive Score

Combines all factors into a single 0-100 score:
- Composite (55%)
- Tide (10%)
- Liquidation (10%)
- Sea state (5%)
- Wind (5%)
- Token regime (5%)
- Stop hunt prediction (5%)
- Contrarian (5%)

---

## 4. Signal Generation

### 4.1 Coin Tracker Hot Signal (`coin_tracker_hot.py`)

**Entry Criteria:**
1. Health = hot (or warm with filters)
2. Composite ≥ 63 (LONG) or 55 (SHORT)
3. Extension filters pass (z_score, BB, speed, accel)
4. Cooldown expired (10 minutes)

**Extension Filters:**

| Direction | Filter | Threshold | Purpose |
|-----------|--------|-----------|---------|
| LONG | z_score | > -0.5 | Avoid falling knives |
| LONG | bb_position | > 0.4 | Avoid lower band entries |
| SHORT | z_score | < -0.5 | Avoid shorting oversold |
| SHORT | bb_position | < 0.6 | Avoid upper band entries |

**Signal Types:**
- `coin_tracker_hot_long` (ct-hot+)
- `coin_tracker_hot_short` (ct-hot-)

### 4.2 Signal Flow

```
coin_tracker_hot.py
    │
    ├─▶ Checks: health, composite, extension filters, cooldown
    │
    ├─▶ add_signal() → signals_hermes_runtime.db
    │
    ▼
signal_compactor.py
    │
    ├─▶ Groups by token+direction
    ├─▶ Checks confluence (≥2 sources)
    ├─▶ Weights confidence by health/composite
    │
    ▼
hotset.json → decider_run.py
    │
    ├─▶ context_gate: validates entry
    ├─▶ entry_gates: checks ATR/TP/SL
    │
    ▼
position_manager.py
    │
    ├─▶ Opens position
    ├─▶ Sets dynamic SL/TP
    │
    ▼
Hyperliquid API
```

---

## 5. Integration Points

### 5.1 Context Gate Integration

**File:** `decider_run.py:790`

**Current:** Uses speed, z_score, momentum from speed_tracker
**Proposed:** Add coin_tracker data

```python
def rule_based_context_gate(token, direction, source, sig):
    # ... existing logic ...
    
    # NEW: Coin tracker data
    coin_data = get_coin_tracker_data(token)
    if coin_data:
        composite = coin_data.get('composite', 50)
        predictive = coin_data.get('predictive_score', 50)
        health = coin_data.get('health', 'warm')
        
        # Block if composite too low
        if composite < 50:
            return ('SKIP', f'composite {composite:.0f} < 50')
        
        # Boost confidence if predictive score high
        if predictive > 70:
            confidence *= 1.1
        
        # Block if health is cold
        if health == 'cold':
            return ('SKIP', f'health=cold')
```

### 5.2 Signal Compactor Integration

**File:** `signal_compactor.py:846`

**Current:** Groups signals, checks confluence
**Proposed:** Weight confidence by health/composite

```python
def run_compaction(dry=False, verbose=False, purge_executed=False):
    # ... existing logic ...
    
    # NEW: Weight signals by coin_tracker health
    for signal in signals:
        coin_data = get_coin_tracker_data(signal['token'])
        if coin_data:
            health = coin_data.get('health', 'warm')
            composite = coin_data.get('composite', 50)
            
            # Adjust confidence based on health
            if health == 'hot':
                signal['confidence'] *= 1.2
            elif health == 'cold':
                signal['confidence'] *= 0.8
            
            # Adjust based on composite
            if composite > 70:
                signal['confidence'] *= 1.1
            elif composite < 50:
                signal['confidence'] *= 0.9
```

### 5.3 Entry Gates Integration

**File:** `entry_gates.py`

**Current:** Validates entries based on various criteria
**Proposed:** Add predictive score and R:R filters

```python
def validate_entry(token, direction, source, confidence):
    # ... existing logic ...
    
    # NEW: Coin tracker predictive score filter
    coin_data = get_coin_tracker_data(token)
    if coin_data:
        predictive = coin_data.get('predictive_score', 50)
        rr_data = coin_data.get('rr_data')
        
        # Block if predictive score too low
        if predictive < 50:
            return False, f'predictive {predictive:.0f} < 50'
        
        # Block if R:R too low
        if rr_data and rr_data.get('rr_ratio', 0) < 1.5:
            return False, f'R:R {rr_data["rr_ratio"]:.2f} < 1.5'
```

### 5.4 Position Manager Integration

**File:** `position_manager.py`

**Current:** Uses fixed SL/TP or simple ATR-based
**Proposed:** Use coin_tracker R:R for dynamic SL/TP

```python
def _compute_dynamic_sl(token, direction, entry_price, ...):
    # ... existing logic ...
    
    # NEW: Use coin_tracker R:R for SL
    coin_data = get_coin_tracker_data(token)
    if coin_data:
        rr_data = coin_data.get('rr_data')
        if rr_data:
            sl = rr_data.get('stop_loss')
            if sl and ((direction == 'LONG' and sl < entry_price) or 
                       (direction == 'SHORT' and sl > entry_price)):
                return sl
    
    # Fallback to existing logic
    return existing_sl

def _compute_dynamic_tp(token, direction, entry_price, ...):
    # ... existing logic ...
    
    # NEW: Use coin_tracker R:R for TP
    coin_data = get_coin_tracker_data(token)
    if coin_data:
        rr_data = coin_data.get('rr_data')
        if rr_data:
            tp = rr_data.get('take_profit')
            if tp and ((direction == 'LONG' and tp > entry_price) or 
                       (direction == 'SHORT' and tp < entry_price)):
                return tp
    
    # Fallback to existing logic
    return existing_tp
```

---

## 6. Database Schema

### 6.1 agg_scores Table

```sql
CREATE TABLE agg_scores (
    symbol TEXT PRIMARY KEY,
    ts INTEGER,
    health TEXT,
    composite REAL,
    predictive_score REAL,
    -- Technical factors
    momentum REAL,
    volume REAL,
    volatility REAL,
    spread REAL,
    signals REAL,
    regime REAL,
    wyckoff_phase TEXT,
    ewave_count INTEGER,
    trend_quality REAL,
    setup_score REAL,
    setup_type TEXT,
    clustering_bullish REAL,
    clustering_bearish REAL,
    recency REAL,
    -- Weather factors
    tide REAL,
    sea_state REAL,
    wind REAL,
    token_regime REAL,
    -- Liquidation
    liquidation REAL
);
```

### 6.2 coin_{TOKEN} Tables

```sql
CREATE TABLE coin_{TOKEN} (
    id INTEGER PRIMARY KEY,
    ts INTEGER,
    event_type TEXT,
    price REAL,
    spread_bps REAL,
    vol_1h REAL,
    vol_24h REAL,
    rsi_14 REAL,
    macd_hist REAL,
    ema_9 REAL,
    ema_20 REAL,
    ema_50 REAL,
    atr_14 REAL,
    health TEXT,
    health_score REAL,
    signal_type TEXT,
    signal_confidence REAL,
    regime TEXT,
    wyckoff_phase TEXT,
    ewave_count INTEGER,
    trend_quality REAL,
    trend_direction TEXT,
    setup_score REAL,
    setup_type TEXT,
    clustering_bullish REAL,
    clustering_bearish REAL,
    recency REAL,
    liquidation REAL,
    tide REAL,
    sea_state REAL,
    wind REAL,
    token_regime REAL,
    predictive_score REAL
);
```

---

## 7. Constants and Thresholds

### 7.1 Signal Generation Thresholds

| Constant | Value | Description |
|----------|-------|-------------|
| COIN_TRACKER_HOT_MIN_COMPOSITE | 63 | LONG composite threshold |
| COIN_TRACKER_HOT_MIN_COMPOSITE_SHORT | 55 | SHORT composite threshold |
| COIN_TRACKER_HOT_COOLDOWN_HOURS | 0.167 | 10-minute cooldown |
| COIN_TRACKER_HOT_CLUSTER_MIN | 1.0 | Minimum cluster count |
| COIN_TRACKER_HOT_RECENCY_MIN | 0.35 | Minimum recency weight |

### 7.2 Extension Filters

| Constant | Value | Description |
|----------|-------|-------------|
| COIN_TRACKER_HOT_MIN_ZSCORE_LONG | -0.5 | LONG z-score minimum |
| COIN_TRACKER_HOT_MAX_ZSCORE_SHORT | -0.5 | SHORT z-score maximum |
| COIN_TRACKER_HOT_MIN_BB_LONG | 0.4 | LONG BB position minimum |
| COIN_TRACKER_HOT_MAX_BB_SHORT | 0.6 | SHORT BB position maximum |
| COIN_TRACKER_HOT_MIN_SPEED_PCT | 20 | Speed percentile minimum |
| COIN_TRACKER_HOT_MAX_SPEED_PCT | 95 | Speed percentile maximum |
| COIN_TRACKER_HOT_MIN_ACCEL | -0.01 | Price acceleration minimum |

---

## 8. Monitoring and Alerts

### 8.1 Predictive Alerts

| Alert | Severity | Trigger |
|-------|----------|---------|
| STOP_HUNT | HIGH | Cluster within 0.5% |
| CASCADE_RISK | HIGH | Multiple clusters within 1% |
| TIDE_SHIFT | MEDIUM | Tide imbalance >20% |
| MOMENTUM_SURGE | MEDIUM | Wind gusts >2x sustained |
| REGIME_CHANGE | LOW | Sea state shifting |

### 8.2 Market Regime Detection

| Regime | Conditions | Action |
|--------|------------|--------|
| CALM | Low vol, neutral tide, healthy | Normal trading |
| STORMY | High vol, extreme tide, unhealthy | Reduce exposure |
| RECOVERY | Improving sea, rising tide | Accumulate |
| DECLINING | Worsening sea, falling tide | Defensive |

---

## 9. Performance Metrics

| Metric | Current | Target |
|--------|---------|--------|
| Signal win rate | 35% | 50%+ |
| R:R ratio | 1.3 | 2.0+ |
| Predictive accuracy | Unknown | 70%+ |
| Contrarian accuracy | Unknown | 60%+ |

---

## 10. Implementation Roadmap

### Phase 1: Context Gate Integration (Week 1)
- [ ] Add coin_tracker data retrieval
- [ ] Integrate composite score
- [ ] Add predictive score boost
- [ ] Test with historical data

### Phase 2: Signal Compactor Integration (Week 2)
- [ ] Add health-based confidence weighting
- [ ] Add composite-based confidence weighting
- [ ] Test signal quality improvement

### Phase 3: Entry Gates Integration (Week 3)
- [ ] Add predictive score filter
- [ ] Add R:R filter
- [ ] Test entry quality improvement

### Phase 4: Position Manager Integration (Week 4)
- [ ] Integrate R:R for dynamic SL/TP
- [ ] Test exit quality improvement

---

## 11. Risk Mitigation

1. **Backtest extensively** before deploying
2. **Paper trade** for 1 week
3. **Monitor performance** daily
4. **Have rollback plan** ready
5. **Start with small position sizes** until confident

---

## 12. Open Questions

1. Should we add coin_tracker to the hotset.json for dashboard visibility?
2. How to handle stale coin_tracker data?
3. Should we add coin_tracker alerts to the notification system?
4. What's the optimal weight for each factor?
5. How to validate predictive accuracy over time?
