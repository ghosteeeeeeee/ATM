# Plan: Weather Station Integration into Coin Tracker

## Date: 2026-08-23

## Goal

Make coin_tracker "SMART" by integrating weather station data and liquidation clusters to predict moves BEFORE they happen, not just react.

## Current State

### Weather Station (NOT used in scoring)
- **Tide:** Market flow balance (long vs short signals)
- **Waves:** Signal intensity over time
- **Wind:** Momentum, velocity, acceleration distribution
- **Sea State:** Overall health from outcomes (WR, PnL)
- **Tokens:** Reef (good), Sandbar (neutral), Deep (bad) classification

### Liquidation Clusters (7% weight in scoring)
- **Proximity:** Distance to liquidation clusters
- **Stop Hunt Detection:** Active stop hunts = explosive moves
- **Cluster Size:** Bigger clusters = more energy

### Coin Tracker Scoring (13 factors)
```
momentum: 14%, volume: 10%, volatility: 7%, spread: 7%
signals: 4%, regime: 4%, wyckoff: 14%, ewave: 9%
trend: 7%, setup: 8%, clustering: 4%, recency: 5%
liquidation: 7%
```

## Integration Plan

### Phase 1: Weather Factors in Scoring (Week 1)

#### 1.1 Tide Score (Market Flow)
```python
def score_tide(token_data, weather_data):
    """
    Score based on market flow alignment.
    
    Logic:
    - If tide is BULLISH (>55% long) and token is LONG → boost
    - If tide is BEARISH (>55% short) and token is SHORT → boost
    - If tide contradicts direction → penalty
    
    Weight: 5% (new)
    """
    tide_24h = weather_data.get('tide', {}).get('24h', {})
    long_pct = tide_24h.get('long_pct', 50)
    short_pct = tide_24h.get('short_pct', 50)
    
    # Determine tide direction
    if long_pct > 55:
        tide_dir = 'BULLISH'
    elif short_pct > 55:
        tide_dir = 'BEARISH'
    else:
        tide_dir = 'NEUTRAL'
    
    # Align with token direction
    token_dir = token_data.get('setup_type') or token_data.get('trend_direction')
    
    if tide_dir == token_dir:
        return 80 + (abs(long_pct - 50) / 50) * 20  # 80-100
    elif tide_dir == 'NEUTRAL':
        return 50  # Neutral
    else:
        return 30 - (abs(long_pct - 50) / 50) * 20  # 10-30
```

#### 1.2 Sea State Score (Market Health)
```python
def score_sea_state(weather_data):
    """
    Score based on overall market health.
    
    Logic:
    - High WR (>55%) → market is healthy → boost all signals
    - Low WR (<45%) → market is sick → penalize all signals
    - Negative PnL → caution mode
    
    Weight: 3% (new)
    """
    sea = weather_data.get('sea_state', {})
    wr = sea.get('winrate', 50)
    pnl = sea.get('total_pnl', 0)
    
    if wr > 55 and pnl > 0:
        return 80 + (wr - 55) * 2  # 80-100
    elif wr > 50:
        return 60 + (wr - 50) * 4  # 60-80
    elif wr > 45:
        return 40 + (wr - 45) * 4  # 40-60
    else:
        return 20 + (wr - 30) * 1.33  # 20-40
```

#### 1.3 Wind Score (Momentum Alignment)
```python
def score_wind(token_data, weather_data):
    """
    Score based on momentum alignment with market.
    
    Logic:
    - If market avg_velocity > 0 and token accelerating → boost
    - If market avg_velocity < 0 and token decelerating → boost
    - Mismatch → penalty
    
    Weight: 3% (new)
    """
    wind = weather_data.get('wind', {})
    market_vel = wind.get('avg_velocity', 0)
    market_accel = wind.get('avg_accel', 0)
    
    token_accel = token_data.get('price_acceleration') or 0
    
    # Alignment check
    if market_vel > 0 and token_accel > 0:
        return 80  # Both accelerating up
    elif market_vel < 0 and token_accel < 0:
        return 80  # Both accelerating down
    elif abs(market_vel) < 0.001:
        return 50  # Market flat
    else:
        return 30  # Mismatch
```

#### 1.4 Token Regime Score (Historical Performance)
```python
def score_token_regime(token, weather_data):
    """
    Score based on token's historical regime classification.
    
    Logic:
    - Reef tokens (WR >55%, PnL >$0.1) → boost
    - Deep tokens (WR <35%, PnL <-$0.5) → penalty
    - Sandbar → neutral
    
    Weight: 2% (new)
    """
    tokens = weather_data.get('tokens', {})
    
    for regime_type in ['reef', 'sandbar', 'deep']:
        for t in tokens.get(regime_type, []):
            if t['token'] == token:
                if regime_type == 'reef':
                    return 80 + min(20, t.get('winrate', 50) - 55)
                elif regime_type == 'deep':
                    return 20 + max(0, t.get('winrate', 35) - 20)
                else:
                    return 50
    
    return 50  # Unknown = neutral
```

### Phase 2: Liquidation Cluster Enhancement (Week 2)

#### 2.1 Stop Hunt Prediction
```python
def predict_stop_hunt(token_data, liq_data, weather_data):
    """
    Predict imminent stop hunts using liquidation clusters.
    
    Logic:
    - Cluster within 0.5% + bearish tide → SHORT signal
    - Cluster within 0.5% + bullish tide → LONG signal
    - Cluster size > $500M → high confidence
    
    Weight: Add to existing liquidation score
    """
    clusters = liq_data.get('_coin_clusters', [])
    tide = weather_data.get('tide', {}).get('24h', {})
    
    if not clusters:
        return None
    
    nearest = min(clusters, key=lambda c: abs(c.get('distance_pct', 100)))
    distance = abs(nearest.get('distance_pct', 100))
    
    if distance > 0.5:
        return None  # Too far
    
    # Determine direction based on cluster side
    if nearest.get('side') == 'long':
        # Long liquidations below = support, price likely to bounce
        direction = 'LONG'
    else:
        # Short liquidations above = resistance, price likely to drop
        direction = 'SHORT'
    
    # Confidence based on distance and size
    confidence = 70
    if distance < 0.25:
        confidence += 15
    if nearest.get('total_notional_usd', 0) > 500_000_000:
        confidence += 10
    
    return {
        'direction': direction,
        'confidence': min(95, confidence),
        'cluster_distance': distance,
        'cluster_size': nearest.get('total_notional_usd'),
    }
```

#### 2.2 Cascade Prediction
```python
def predict_cascade(token_data, liq_data, weather_data):
    """
    Predict liquidation cascades.
    
    Logic:
    - Multiple clusters within 1% → cascade risk
    - High volatility + clusters → accelerated cascade
    - Low volume + clusters → delayed cascade
    
    Weight: Add to liquidation score
    """
    clusters = liq_data.get('_coin_clusters', [])
    
    close_clusters = [c for c in clusters if abs(c.get('distance_pct', 100)) < 1.0]
    
    if len(close_clusters) < 2:
        return None  # Need multiple clusters for cascade
    
    # Calculate cascade probability
    total_size = sum(c.get('total_notional_usd', 0) for c in close_clusters)
    avg_distance = sum(abs(c.get('distance_pct', 100)) for c in close_clusters) / len(close_clusters)
    
    # Higher probability with more clusters and closer distance
    probability = min(90, 40 + len(close_clusters) * 10 + (1 - avg_distance) * 20)
    
    return {
        'probability': probability,
        'cluster_count': len(close_clusters),
        'total_size': total_size,
        'avg_distance': avg_distance,
    }
```

### Phase 3: Predictive Scoring (Week 3)

#### 3.1 Predictive Composite Score
```python
def compute_predictive_score(token_data, weather_data, liq_data):
    """
    Compute predictive score that combines:
    - Current technical state (existing 13 factors)
    - Weather alignment (new 4 factors)
    - Liquidation setup (enhanced)
    - Predictive signals (new)
    
    Returns: 0-100 predictive score
    """
    # Existing score (from current system)
    current_score = compute_current_score(token_data)
    
    # Weather alignment
    tide_score = score_tide(token_data, weather_data)
    sea_score = score_sea_state(weather_data)
    wind_score = score_wind(token_data, weather_data)
    regime_score = score_token_regime(token_data['symbol'], weather_data)
    
    # Liquidation setup
    liq_setup = score_liquidation(token_data['price'], liq_data)
    
    # Predictive signals
    stop_hunt = predict_stop_hunt(token_data, liq_data, weather_data)
    cascade = predict_cascade(token_data, liq_data, weather_data)
    
    # Weighted combination
    predictive_score = (
        current_score * 0.60 +           # Existing technical factors
        tide_score * 0.10 +              # Market flow alignment
        sea_score * 0.05 +               # Market health
        wind_score * 0.05 +              # Momentum alignment
        regime_score * 0.05 +            # Historical performance
        liq_setup * 0.10 +               # Liquidation proximity
        (80 if stop_hunt else 50) * 0.05 # Stop hunt prediction
    )
    
    return {
        'predictive_score': round(predictive_score, 1),
        'components': {
            'current': current_score,
            'tide': tide_score,
            'sea': sea_score,
            'wind': wind_score,
            'regime': regime_score,
            'liquidation': liq_setup,
            'stop_hunt': stop_hunt,
            'cascade': cascade,
        },
        'signals': {
            'stop_hunt_imminent': stop_hunt is not None,
            'cascade_risk': cascade is not None and cascade['probability'] > 60,
            'tide_aligned': tide_score > 70,
            'market_healthy': sea_score > 60,
        }
    }
```

### Phase 4: Smart Signal Generation (Week 4)

#### 4.1 Predictive Signal Filter
```python
def predictive_filter(token_data, weather_data, liq_data):
    """
    Filter signals based on predictive analysis.
    
    Logic:
    - High predictive score (>70) → allow
    - Stop hunt imminent → boost confidence
    - Cascade risk → reduce position size
    - Market unhealthy → reduce confidence
    
    Returns: (allow_signal, confidence_adjustment, reason)
    """
    predictive = compute_predictive_score(token_data, weather_data, liq_data)
    score = predictive['predictive_score']
    signals = predictive['signals']
    
    if score < 50:
        return False, 0, f"Low predictive score ({score})"
    
    confidence_adj = 0
    reasons = []
    
    if signals['stop_hunt_imminent']:
        confidence_adj += 10
        reasons.append("Stop hunt imminent")
    
    if signals['cascade_risk']:
        confidence_adj -= 5
        reasons.append("Cascade risk — reduce size")
    
    if signals['tide_aligned']:
        confidence_adj += 5
        reasons.append("Tide aligned")
    
    if signals['market_healthy']:
        confidence_adj += 5
        reasons.append("Market healthy")
    else:
        confidence_adj -= 5
        reasons.append("Market unhealthy")
    
    return True, confidence_adj, ', '.join(reasons)
```

#### 4.2 Smart Entry Timing
```python
def optimal_entry_timing(token_data, weather_data, liq_data):
    """
    Determine optimal entry timing based on:
    - Liquidation cluster proximity
    - Tide direction
    - Wind momentum
    
    Returns: entry timing recommendation
    """
    clusters = liq_data.get('_coin_clusters', [])
    tide = weather_data.get('tide', {}).get('24h', {})
    wind = weather_data.get('wind', {})
    
    recommendations = []
    
    # Check liquidation proximity
    if clusters:
        nearest = min(clusters, key=lambda c: abs(c.get('distance_pct', 100)))
        if abs(nearest.get('distance_pct', 100)) < 0.5:
            recommendations.append("ENTER NOW — liquidation cluster within 0.5%")
        elif abs(nearest.get('distance_pct', 100)) < 1.0:
            recommendations.append("ENTER SOON — cluster within 1%")
    
    # Check tide alignment
    long_pct = tide.get('long_pct', 50)
    if long_pct > 60:
        recommendations.append("BULLISH TIDE — favor LONG entries")
    elif long_pct < 40:
        recommendations.append("BEARISH TIDE — favor SHORT entries")
    
    # Check wind momentum
    if wind.get('avg_velocity', 0) > 0.01:
        recommendations.append("STRONG MOMENTUM — ride the wave")
    elif wind.get('avg_velocity', 0) < -0.01:
        recommendations.append("WEAK MOMENTUM — wait for reversal")
    
    return recommendations
```

## New Ideas for Integration

### Idea 1: Weather-Based Regime Detection
```python
def detect_market_regime(weather_data):
    """
    Detect market regime from weather data.
    
    Regimes:
    - CALM: Low volatility, neutral tide, healthy sea
    - STORMY: High volatility, extreme tide, unhealthy sea
    - RECOVERY: Improving sea state, rising tide
    - DECLINING: Worsening sea state, falling tide
    
    Use regime to adjust all signal weights.
    """
    sea = weather_data.get('sea_state', {})
    tide = weather_data.get('tide', {}).get('24h', {})
    wind = weather_data.get('wind', {})
    
    # Calculate regime indicators
    wr = sea.get('winrate', 50)
    long_pct = tide.get('long_pct', 50)
    volatility = wind.get('gusts', 0) / wind.get('sustained', 1) if wind.get('sustained', 0) > 0 else 1
    
    if wr > 55 and abs(long_pct - 50) < 10 and volatility < 1.5:
        return 'CALM'
    elif wr < 45 or abs(long_pct - 50) > 20 or volatility > 2.0:
        return 'STORMY'
    elif wr > 50 and long_pct > 55:
        return 'RECOVERY'
    elif wr < 50 and long_pct < 45:
        return 'DECLINING'
    else:
        return 'NEUTRAL'
```

### Idea 2: Liquidation Heatmap
```python
def generate_liquidation_heatmap(liq_data, price_range):
    """
    Generate heatmap of liquidation clusters.
    
    Shows where stops are clustered, helping predict:
    - Support/resistance levels
    - Potential cascade zones
    - Optimal entry/exit points
    """
    clusters = liq_data.get('liquidation_clusters', {})
    
    heatmap = {}
    for coin, coin_clusters in clusters.items():
        heatmap[coin] = {
            'long_stops': [],  # Support levels
            'short_stops': [],  # Resistance levels
            'cascade_zones': [],  # Areas with multiple clusters
        }
        
        for cluster in coin_clusters:
            price = cluster.get('price')
            side = cluster.get('side')
            size = cluster.get('total_notional_usd', 0)
            
            if side == 'long':
                heatmap[coin]['long_stops'].append({
                    'price': price,
                    'size': size,
                    'distance_pct': cluster.get('distance_pct'),
                })
            else:
                heatmap[coin]['short_stops'].append({
                    'price': price,
                    'size': size,
                    'distance_pct': cluster.get('distance_pct'),
                })
        
        # Find cascade zones (clusters within 0.5% of each other)
        all_stops = heatmap[coin]['long_stops'] + heatmap[coin]['short_stops']
        all_stops.sort(key=lambda x: x['price'])
        
        for i in range(len(all_stops) - 1):
            if abs(all_stops[i]['price'] - all_stops[i+1]['price']) / all_stops[i]['price'] < 0.005:
                heatmap[coin]['cascade_zones'].append({
                    'price_range': (all_stops[i]['price'], all_stops[i+1]['price']),
                    'total_size': all_stops[i]['size'] + all_stops[i+1]['size'],
                })
    
    return heatmap
```

### Idea 3: Predictive Alert System
```python
def generate_predictive_alerts(token_data, weather_data, liq_data):
    """
    Generate predictive alerts for high-probability setups.
    
    Alert Types:
    - STOP_HUNT: Liquidation cluster within 0.5%
    - CASCADE_RISK: Multiple clusters within 1%
    - TIDE_SHIFT: Tide changing direction
    - MOMENTUM_SURGE: Wind velocity spiking
    - REGIME_CHANGE: Sea state shifting
    """
    alerts = []
    
    # Stop hunt alert
    clusters = liq_data.get('_coin_clusters', [])
    if clusters:
        nearest = min(clusters, key=lambda c: abs(c.get('distance_pct', 100)))
        if abs(nearest.get('distance_pct', 100)) < 0.5:
            alerts.append({
                'type': 'STOP_HUNT',
                'severity': 'HIGH',
                'message': f"Liquidation cluster {nearest.get('distance_pct', 0):.2f}% away",
                'action': 'ENTER NOW',
            })
    
    # Tide shift alert
    tide = weather_data.get('tide', {})
    if tide.get('24h', {}).get('imbalance', 0) > 0.2:
        direction = 'BULLISH' if tide['24h']['long_pct'] > 55 else 'BEARISH'
        alerts.append({
            'type': 'TIDE_SHIFT',
            'severity': 'MEDIUM',
            'message': f"Strong {direction} tide ({tide['24h']['long_pct']:.0f}% long)",
            'action': f'Favor {direction} entries',
        })
    
    # Momentum surge alert
    wind = weather_data.get('wind', {})
    if wind.get('gusts', 0) > wind.get('sustained', 1) * 2:
        alerts.append({
            'type': 'MOMENTUM_SURGE',
            'severity': 'MEDIUM',
            'message': f"Wind gusts {wind['gusts']:.4f} vs sustained {wind['sustained']:.4f}",
            'action': 'Expect volatile moves',
        })
    
    return alerts
```

## Implementation Timeline

### Week 1: Core Weather Integration
- [ ] Add tide score to coin_tracker_score.py
- [ ] Add sea state score
- [ ] Add wind score
- [ ] Add token regime score
- [ ] Update WEIGHTS dictionary
- [ ] Test with historical data

### Week 2: Liquidation Enhancement
- [ ] Enhance stop hunt prediction
- [ ] Add cascade prediction
- [ ] Improve liquidation scoring
- [ ] Test with live liquidation data

### Week 3: Predictive Scoring
- [ ] Implement predictive composite score
- [ ] Add predictive signal filter
- [ ] Add optimal entry timing
- [ ] Backtest predictive accuracy

### Week 4: Smart Alerts
- [ ] Implement predictive alert system
- [ ] Add liquidation heatmap
- [ ] Add market regime detection
- [ ] Deploy to production

## Success Metrics

| Metric | Current | Target |
|--------|---------|--------|
| Signal win rate | 35% | 50%+ |
| Predictive accuracy | N/A | 70%+ |
| Stop hunt prediction | N/A | 80%+ |
| Cascade prediction | N/A | 60%+ |

## Risk Mitigation

1. **Backtest extensively** before deploying
2. **Paper trade** the new system for 1 week
3. **Monitor performance** daily
4. **Have rollback plan** ready

## Open Questions

1. What's the optimal weight for weather factors?
2. How to handle stale weather data?
3. Should we add weather to the coin_tracker dashboard?
4. How to alert users of predictive signals?
