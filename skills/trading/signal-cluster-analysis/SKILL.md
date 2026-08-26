---
name: signal-cluster-analysis
description: Analyze signal generation patterns, temporal clusters, and sequential relationships across signal families. Detects market phase transitions, lead-lag correlations, co-signal confluence zones, and signal lifecycle patterns (early/concurrent/late indicators).
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [signals, analysis, patterns, clusters, cascade, market-regime, confluence]
    related_skills: [signal-backtest, signal-quality-tuner, signal-combo-analyzer]
triggers:
  - analyze signal clusters
  - signal patterns over time
  - which signals fire together
  - signal sequential patterns
  - market phase detection from signals
  - signal lifecycle analysis
  - signal confluence zones
  - lead lag signal relationships
  - signal family correlations
---

# Signal Cluster Analysis

## What This Skill Does

Analyzes the Hermes signal database (`signals_hermes_runtime.db`) to find **temporal patterns** in signal generation. Answers questions like:

- Which signal types cluster together in time?
- Does signal family A appearing predict family B appearing later?
- Which signals are early warnings vs lagging confirmations?
- What "market phase" is the system in based on signal composition?
- Which coins have the most signal confluence (multiple families firing)?

## Quick Start

```bash
cd /root/.hermes/scripts
python3 analyze_signal_clusters.py      # Full analysis (daily dominance, waves, sequential patterns, co-signals, regime transitions, correlations, time-of-day, confidence)
python3 analyze_signal_cascades.py      # Deep dive (market phases, signal lifecycle, transition matrix, confluence zones)
```

Both scripts read from `signals_hermes_runtime.db` (last 30 days) and print to stdout. No arguments needed.

## Key Concepts

### Signal Families

Signals are grouped into **families** — related signal types that share market logic:

| Family | Signals | Market Meaning |
|--------|---------|----------------|
| Accelerate | accel_300_long/short, inverse_accel_300 | Price acceleration (early warning) |
| Bollinger | bb_bounce, bb_bounce_short, bollinger_squeeze | Mean reversion |
| Momentum | momentum, fast_momentum, velocity, phase_accel | Directional momentum |
| ZScore | zscore_rising_long/short, hzscore, mtp_zscore | Statistical extremes |
| Trendline | tl_break_long/short, vortex_break_long/short | Trend breakouts |
| Squeeze | squeeze_cross, bollinger_squeeze, atr_compression | Volatility compression |
| R2 | r2_trend_long/short, r2_rev | R-squared trend strength |
| HL_Copy | hl_copy_plus, hl_copy_minus | Copy-trading signals |
| Support/Resistance | support_resistance | Key price levels |
| Mover | coin_tracker_hot_long/short, mover_long/short | Hot coin detection |
| Exhaustion | return_exhaustion_long/short, spike_exhaustion | Move exhaustion |
| Hot_Set | hot-set | Multi-signal confluence |

### Market Phase Cycle

The 30-day analysis reveals a **repeatable market cycle**:

```
Squeeze/Trendline (compression) 
  → Momentum (breakout building)
    → ZScore Surge (the event itself)
      → Bollinger (mean reversion)
        → Exhaustion (move tired)
          → Range (oscillation)
            → S/R + HL_Copy (defensive)
              → back to Trendline (new cycle)
```

### Lead-Lag Correlations

Signal families have **predictive relationships** with measurable time lags:

| Leading Signal | → Follows | Days Later | Correlation |
|---------------|-----------|------------|-------------|
| ZScore | Pattern | +1d | +0.905 |
| Wave | R2 | +3d | +0.904 |
| Momentum | Pattern | +2d | +0.902 |
| ZScore | Exhaustion | +3d | +0.864 |
| Stop_Hunt | HL_Copy | +2d | +0.861 |
| Squeeze | Trendline | +2d | +0.799 |
| ZScore | Bollinger | +2d | +0.727 |
| Accelerate | Momentum | +2d | +0.720 |
| Trendline | Accelerate | +2d | +0.710 |

**Inverse relationships** (never active together):
- Trendline ↔ Bollinger (r=-0.386) — trending vs mean-reverting
- Squeeze ↔ HL_Copy (r=-0.266) — compression vs copy-trading

### Signal Lifecycle Roles

| Role | Families | When They Appear |
|------|----------|-----------------|
| 🟢 **EARLY** | Accelerate, Momentum, Trendline | 2-3 days BEFORE big moves |
| 🟡 **CONCURRENT** | ZScore, R2, Hot_Set | DURING the event |
| 🔵 **LAGGING** | Exhaustion, Stop_Hunt, Pattern | AFTER the move completes |

### Co-Signal Patterns

Most common signal pairs firing on the **same coin** within a day:

| Signal A | Signal B | Count | Meaning |
|---------|---------|-------|---------|
| bb_bounce_short | support_resistance | 444 | Bounce at S/R levels |
| bb_bounce_short | coin_tracker_hot_long | 280 | Mean reversion on movers |
| coin_tracker_hot_long | support_resistance | 255 | Hot coins at key levels |
| r2_trend_long | support_resistance | 201 | Trend at S/R |
| bb_bounce_short | r2_trend_long | 160 | Confluence zone setup |

## Usage Patterns

### 1. Detect Current Market Phase

```bash
cd /root/.hermes/scripts
python3 analyze_signal_cascades.py | grep -A 50 "MARKET PHASE ANALYSIS"
```

Look at the last 3-5 days of phase output. If Trendline/Accelerate dominate → expect breakout. If HL_Copy/S/R dominate → defensive mode.

### 2. Find What's Coming Next

```bash
python3 analyze_signal_clusters.py | grep -A 30 "SEQUENTIAL PATTERN"
```

Check the leading families. If Accelerate spiked 2 days ago, expect Momentum today. If ZScore spiked, expect Bollinger in 2 days.

### 3. Identify Best Confluence Setups

```bash
python3 analyze_signal_cascades.py | grep -A 20 "CONFLUENCE ZONES"
```

Days with 3+ families spiking = highest-probability trade setups.

### 4. Check Confidence Levels by Family

```bash
python3 analyze_signal_clusters.py | grep -A 20 "CONFIDENCE PATTERNS"
```

Use high-confidence families (Mover 84.9%, HL_Copy 83.9%) for entries. Use low-confidence (ZScore 65.3%) for confirmation only.

## Extending the Analysis

### Custom Time Window

Edit the SQL in either script:
```python
# Change from 30 days to 14 days:
WHERE created_at >= date('now', '-14 days')

# Or specific date range:
WHERE created_at BETWEEN '2026-08-01' AND '2026-08-26'
```

### Adding New Signal Families

Edit the `signal_family()` function in both scripts:
```python
families = {
    'MyNewFamily': ['my_new_signal_1', 'my_new_signal_2'],
    # ... existing families
}
```

### Export to JSON

Both scripts can be modified to output JSON instead of print statements. The data structures are plain Python dicts/lists.

## Architecture

```
scripts/analyze_signal_clusters.py
    ├── get_signal_data()           → reads signals_hermes_runtime.db
    ├── group_by_day()              → daily signal counts
    ├── analyze_daily_dominance()   → which families dominate each day
    ├── analyze_signal_waves()      → spike-and-fade detection (>2x avg)
    ├── analyze_sequential_patterns() → lead-lag correlations
    ├── analyze_co_signal_patterns()  → same-coin signal pairs
    ├── analyze_market_regime_signals() → regime transitions
    ├── analyze_time_of_day_patterns()  → hourly distributions
    └── analyze_confidence_trends()     → confidence by family

scripts/analyze_signal_cascades.py
    ├── get_daily_family_data()     → normalized daily family counts
    ├── analyze_market_phases()     → phase classification per day
    ├── analyze_signal_lifecycle()  → early/concurrent/late roles
    ├── analyze_transition_matrix() → what follows what
    └── analyze_confluence_opportunities() → multi-family spike days
```

## Data Requirements

- **Database:** `/root/.hermes/data/signals_hermes_runtime.db`
- **Table:** `signals` (columns: signal_type, token, direction, confidence, created_at, decision, z_score, momentum_state, price)
- **Minimum data:** 7 days of signals for basic analysis, 30+ days for reliable correlations

## Related Skills

- **signal-backtest** — Backtest individual signals against historical data
- **signal-quality-tuner** — Optimize signal parameters for win rate
- **signal-combo-analyzer** — Find best multi-signal combinations
- **trade-analysis** — Analyze actual trade outcomes

## References

- `plans/signal-cluster-analysis-2026-08-26.md` — Full 30-day analysis report
- `scripts/analyze_signal_clusters.py` — Cluster analysis script
- `scripts/analyze_signal_cascades.py` — Cascade analysis script
- `scripts/signals/` — Individual signal implementations
- `scripts/hermes_constants.py` — Signal thresholds and parameters
