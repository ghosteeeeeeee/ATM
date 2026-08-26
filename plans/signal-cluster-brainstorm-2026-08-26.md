# Signal Cluster Data → Trading System Integration Brainstorm

**Date:** 2026-08-26
**Goal:** Every trade should be a winner
**Source Data:** 30-day signal cluster analysis (69,990 signals, 63 types, 21 families)

---

## Executive Summary

The signal cluster analysis revealed **predictable market phase cycles** and **measurable lead-lag relationships** between signal families. This document brainstormes how to weaponize these patterns to improve winrate and prediction accuracy across the entire trading system.

The core insight: **signals are not independent events — they follow a market lifecycle**. If we know which phase we're in, we know which signals to trust, which to ignore, and what's coming next.

---

## 1. Market Phase Gate (The Biggest Edge)

### The Problem
Currently, every signal is evaluated independently. A `bb_bounce` gets the same treatment whether the market is trending, ranging, or in exhaustion. But the analysis shows:
- **Bollinger bounces win in Range-Bound phases** (r=+0.738 with Range)
- **Bollinger bounces lose in Trend phases** (r=-0.386 with Trendline)
- **Trendline breaks win in Trend Building phases** but fail in Range phases

### The Solution: `market_phase_gate.py`

A new filter layer that runs **before** signal compaction. It detects the current market phase from the last 3-5 days of signal composition, then applies phase-specific multipliers:

```python
# Phase detection (run daily or on each compaction)
phase = detect_market_phase()  # returns: 'trend_building', 'explosion', 'range', 'defensive', etc.

# Phase-specific signal multipliers
PHASE_SIGNAL_WEIGHTS = {
    'trend_building': {
        'Accelerate': 1.3,   # boost — these are early warnings
        'Momentum': 1.2,     # boost — building breakout
        'Squeeze': 1.2,      # boost — compression detected
        'Bollinger': 0.7,    # penalty — don't fade trends
        'Exhaustion': 0.5,   # penalty — move hasn't happened yet
    },
    'explosion': {
        'ZScore': 0.8,       # penalty — the event is NOW, not entry
        'Hot_Set': 1.0,      # neutral — concurrent with event
        'Mover': 1.2,        # boost — ride the momentum
        'R2': 1.3,           # boost — trend strength confirmed
    },
    'range': {
        'Bollinger': 1.4,    # boost — mean reversion works
        'Range': 1.3,        # boost — range signals are accurate
        'Trendline': 0.6,    # penalty — false breakouts in range
        'Momentum': 0.7,     # penalty — momentum fades in range
    },
    'defensive': {
        'HL_Copy': 1.3,      # boost — follow the smart money
        'Support/Resistance': 1.2,  # boost — key levels matter
        'Exhaustion': 1.1,   # slight boost — moves are tired
        'Momentum': 0.6,     # penalty — choppy market kills momentum
    },
}
```

### Integration Point
In `signal_compactor.py`, after scoring each signal, multiply the score by the phase weight:

```python
phase_weight = PHASE_SIGNAL_WEIGHTS.get(current_phase, {}).get(family, 1.0)
final_score = base_score * phase_weight
```

### Expected Impact
- **+5-10% WR improvement** by avoiding wrong-phase signals
- Reduces noise in the hot-set (fewer signals to evaluate)
- Creates a "meta-filter" that compounds with existing filters

---

## 2. Hebbian V2: Signal Family Correlations

### The Problem
The existing Hebbian engine (`hebbian_engine.py`) tracks token-token and token-signal associations. But it doesn't track **signal family correlations** — which families co-occur on winning trades.

### The Solution: Add `family_chains` table to `correlations.db`

```sql
CREATE TABLE family_chains (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    family_a TEXT NOT NULL,      -- e.g., 'Accelerate'
    family_b TEXT NOT NULL,      -- e.g., 'Momentum'
    direction TEXT,              -- LONG/SHORT
    
    -- Counts
    co_wins INTEGER DEFAULT 0,  -- both families fired, trade won
    co_losses INTEGER DEFAULT 0,
    total_co INTEGER DEFAULT 0,
    
    -- Derived
    win_rate REAL DEFAULT 0.0,
    lift REAL DEFAULT 0.0,       -- vs base rate
    confidence REAL DEFAULT 0.0,
    avg_pnl REAL DEFAULT 0.0,
    
    -- Temporal
    half_life_weight REAL DEFAULT 1.0,
    last_seen TIMESTAMP,
    
    UNIQUE(family_a, family_b, direction)
);
```

### What It Learns
From the cluster analysis, we know:
- `Accelerate → Momentum` has r=+0.720 correlation (2-day lag)
- `Squeeze → Trendline` has r=+0.799 correlation (2-day lag)
- `ZScore → Bollinger` has r=+0.727 correlation (2-day lag)

But the Hebbian engine would learn **actual win rates** for these sequences:
- "When Accelerate fires on a coin, and Momentum fires 1-2 days later on that same coin, what's the win rate?"
- "When Squeeze fires, should we pre-position for Trendline breaks?"

### Integration Point
In `decider_run.py`, after the context gate checks, add a Hebbian family correlation check:

```python
from correlation_engine import CorrelationEngine
engine = CorrelationEngine()

# Check if this signal's family has good predictive history
family = signal_family(signal_type)
rec = engine.should_trade_family(family, token, direction)

if rec['recommendation'] == 'AVOID':
    penalty = HEBBIAN_FAMILY_PENALTY  # e.g., 0.5x score multiplier
elif rec['recommendation'] == 'TRADE':
    boost = HEBBIAN_FAMILY_BOOST  # e.g., 1.2x score multiplier
```

### Expected Impact
- **+3-5% WR** from avoiding bad family combinations
- Learns which signal families work together for specific tokens
- Self-improving: as more trades close, the correlations get sharper

---

## 3. Confluence Scorer (Multi-Family Agreement)

### The Problem
Currently, `signal_compactor.py` uses `CONFLUENCE_REQUIRED` — it requires multiple signals to agree. But it doesn't weight **which families** are agreeing. From the analysis:
- `bb_bounce + support_resistance + coin_tracker_hot` = 444 co-occurrences (strong setup)
- `bb_bounce + r2_trend_long + support_resistance` = 160 co-occurrences (strong setup)
- Random 3 signals = much weaker setup

### The Solution: `confluence_scorer.py`

A new module that scores confluence based on **family diversity** and **known strong combos**:

```python
# Known strong confluence combos (from cluster analysis)
STRONG_CONFLUENCES = [
    {'families': ['Bollinger', 'Support/Resistance', 'Mover'], 'bonus': 15, 'min_families': 2},
    {'families': ['R2', 'Support/Resistance', 'Bollinger'], 'bonus': 12, 'min_families': 2},
    {'families': ['Exhaustion', 'Support/Resistance'], 'bonus': 10, 'min_families': 2},
    {'families': ['Trendline', 'Squeeze'], 'bonus': 8, 'min_families': 2},  # "powder keg"
]

# Known weak combos (avoid)
WEAK_CONFLUENCES = [
    {'families': ['Trendline', 'Bollinger'], 'penalty': -20, 'reason': 'trending vs mean-reverting'},
    {'families': ['Squeeze', 'HL_Copy'], 'penalty': -15, 'reason': 'compression vs defensive'},
]

def score_confluence(signal_families: list[str]) -> int:
    """Return bonus/penalty points based on family combo."""
    score = 0
    families_set = set(signal_families)
    
    for combo in STRONG_CONFLUENCES:
        overlap = families_set.intersection(set(combo['families']))
        if len(overlap) >= combo['min_families']:
            score += combo['bonus']
    
    for combo in WEAK_CONFLUENCES:
        overlap = families_set.intersection(set(combo['families']))
        if len(overlap) >= 2:
            score += combo['penalty']
    
    return score
```

### Integration Point
In `signal_compactor.py`, after computing the base confluence score, add the family-based bonus:

```python
family_bonus = score_confluence([signal_family(s) for s in signals])
final_score += family_bonus
```

### Expected Impact
- **+5-8% WR** on confluence setups
- Rewards multi-family agreement (stronger signals)
- Penalizes contradictory family combos (noise)

---

## 4. Signal Lifecycle Filters (Early/Late Indicator Awareness)

### The Problem
From the analysis:
- **Accelerate/Momentum are EARLY** — they fire 2-3 days before the big move
- **ZScore is CONCURRENT** — it fires DURING the event
- **Exhaustion/Stop_Hunt are LAGGING** — they fire AFTER the move

Currently, all signals are treated equally. But:
- Taking an Accelerate signal on day 1 and expecting profit on day 1 = wrong expectation
- Taking an Exhaustion signal expecting continuation = wrong direction
- Taking a ZScore signal expecting further move = entering at the top

### The Solution: `signal_lifecycle_filter.py`

Tag each signal with its lifecycle role and adjust expectations:

```python
SIGNAL_LIFECYCLE = {
    # EARLY: Expect 1-3 day delay before profit
    'accel_300_long': 'early', 'accel_300_short': 'early',
    'inverse_accel_300_long': 'early', 'inverse_accel_300_short': 'early',
    'momentum': 'early', 'fast_momentum': 'early', 'velocity': 'early',
    'squeeze_cross': 'early', 'bollinger_squeeze_long': 'early',
    
    # CONCURRENT: Expect immediate move
    'zscore_rising_long': 'concurrent', 'zscore_rising_short': 'concurrent',
    'r2_trend_long': 'concurrent', 'r2_trend_short': 'concurrent',
    'hot-set': 'concurrent',
    
    # LAGGING: Expect reversal or exhaustion
    'return_exhaustion_long': 'lagging', 'return_exhaustion_short': 'lagging',
    'spike_exhaustion_short': 'lagging',
    'stop_hunt_reversal_long': 'lagging',
}

# Lifecycle-specific trade parameters
LIFECYCLE_PARAMS = {
    'early': {
        'sl_mult': 1.5,      # wider SL (needs room to develop)
        'tp_mult': 2.0,      # bigger TP (bigger move expected)
        'hold_time': '3-5 days',
        'entry_scale': 'scale in over 2-3 entries',
    },
    'concurrent': {
        'sl_mult': 1.0,      # normal SL
        'tp_mult': 1.5,      # normal TP
        'hold_time': '1-2 days',
        'entry_scale': 'single entry',
    },
    'lagging': {
        'sl_mult': 0.8,      # tight SL (move is tired)
        'tp_mult': 0.8,      # smaller TP (limited upside)
        'hold_time': 'hours to 1 day',
        'entry_scale': 'single entry, quick exit',
    },
}
```

### Integration Point
In `decider_run.py`, when computing SL/TP, use lifecycle-aware parameters:

```python
lifecycle = SIGNAL_LIFECYCLE.get(signal_type, 'concurrent')
params = LIFECYCLE_PARAMS[lifecycle]

sl_distance = base_sl * params['sl_mult']
tp_distance = base_tp * params['tp_mult']
```

### Expected Impact
- **+3-5% WR** from appropriate position sizing
- Early signals get wider stops (fewer stop-outs)
- Lagging signals get tighter stops (catch reversals faster)

---

## 5. Phase-Aware Auto-Approval/Rejection

### The Problem
The Hebbian gate has `HEBBIAN_AUTO_APPROVE_WR` and `HEBBIAN_AUTO_REJECT_WR` thresholds. But these are static. The analysis shows that signal effectiveness varies by market phase.

### The Solution: Dynamic thresholds based on current phase

```python
PHASE_AUTO_THRESHOLDS = {
    'trend_building': {
        'auto_approve_wr': 65,    # higher bar — wait for strong signals
        'auto_reject_wr': 35,     # reject weak signals
    },
    'explosion': {
        'auto_approve_wr': 55,    # lower bar — ride the momentum
        'auto_reject_wr': 30,
    },
    'range': {
        'auto_approve_wr': 60,    # medium bar — mean reversion is reliable
        'auto_reject_wr': 40,
    },
    'defensive': {
        'auto_approve_wr': 70,    # highest bar — be very selective
        'auto_reject_wr': 45,
    },
}
```

### Integration Point
In `decider_run.py`, the Hebbian gate section:

```python
phase = get_current_phase()  # cached, computed daily
thresholds = PHASE_AUTO_THRESHOLDS.get(phase, {'auto_approve_wr': 60, 'auto_reject_wr': 40})

if signal_wr >= thresholds['auto_approve_wr'] and min_n >= HEBBIAN_AUTO_MIN_N:
    decision = 'APPROVE'  # strong signal in favorable phase
elif signal_wr <= thresholds['auto_reject_wr'] and min_n >= HEBBIAN_AUTO_MIN_N:
    decision = 'REJECT'   # weak signal in unfavorable phase
```

### Expected Impact
- **+2-4% WR** from phase-appropriate thresholds
- More trades in favorable phases, fewer in unfavorable
- Self-adjusting: as phase detection improves, thresholds adapt

---

## 6. Predictive Signal Sequencing (The "What's Next" Engine)

### The Problem
From the analysis, we know:
- ZScore flood → Pattern signals in +1 day (r=0.905)
- Wave → R2 in +3 days (r=0.904)
- Squeeze → Trendline in +2 days (r=0.799)

But the system doesn't use this to **prepare** for upcoming signals.

### The Solution: `signal预言er.py` (Signal Forecaster)

A module that tracks which families spiked recently and predicts what's coming:

```python
# Lead-lag rules from cluster analysis
LEAD_LAG_RULES = [
    {'leader': 'ZScore', 'follower': 'Pattern', 'lag_days': 1, 'corr': 0.905},
    {'leader': 'Wave', 'follower': 'R2', 'lag_days': 3, 'corr': 0.904},
    {'leader': 'Momentum', 'follower': 'Pattern', 'lag_days': 2, 'corr': 0.902},
    {'leader': 'ZScore', 'follower': 'Exhaustion', 'lag_days': 3, 'corr': 0.864},
    {'leader': 'Stop_Hunt', 'follower': 'HL_Copy', 'lag_days': 2, 'corr': 0.861},
    {'leader': 'Squeeze', 'follower': 'Trendline', 'lag_days': 2, 'corr': 0.799},
    {'leader': 'ZScore', 'follower': 'Bollinger', 'lag_days': 2, 'corr': 0.727},
    {'leader': 'Accelerate', 'follower': 'Momentum', 'lag_days': 2, 'corr': 0.720},
    {'leader': 'Trendline', 'follower': 'Accelerate', 'lag_days': 2, 'corr': 0.710},
]

def predict_upcoming_families(recent_families: dict[str, int], lookback_days: int = 3) -> list[dict]:
    """Given recent family activity, predict what's coming."""
    predictions = []
    
    for rule in LEAD_LAG_RULES:
        leader_count = recent_families.get(rule['leader'], 0)
        if leader_count > 0:
            predictions.append({
                'predicted_family': rule['follower'],
                'expected_in_days': rule['lag_days'],
                'correlation': rule['corr'],
                'confidence': min(1.0, leader_count / 100) * rule['corr'],
                'leader': rule['leader'],
            })
    
    return sorted(predictions, key=lambda x: -x['confidence'])
```

### How to Use It

1. **Pre-positioning**: If ZScore flooded yesterday, prepare for Pattern signals tomorrow. Pre-scan coins for pattern setups.

2. **Phase transition warnings**: If Squeeze dominated for 2 days, expect Trendline breaks in 2 days. Tighten stops on existing positions.

3. **Exhaustion alerts**: If ZScore flooded 3 days ago, expect Exhaustion signals tomorrow. Take profit on existing positions.

### Integration Point
New systemd timer: `hermes-signal-forecaster.timer` (runs every 6 hours)

```python
# In signal_forecaster.py
predictions = predict_upcoming_families(get_recent_family_counts())
if predictions:
    # Write to /var/www/hermes/data/signal_predictions.json
    # Dashboard shows "Expected next: Bollinger (in 2 days, 73% confidence)"
    write_predictions(predictions)
    
    # Boost confidence for signals that match predictions
    for sig in pending_signals:
        sig_family = signal_family(sig['signal_type'])
        for pred in predictions:
            if sig_family == pred['predicted_family']:
                sig['confidence'] += pred['confidence'] * 5  # boost up to 5 points
```

### Expected Impact
- **+3-5% WR** from anticipating upcoming phases
- Reduces surprise losses from phase transitions
- Creates a "weather forecast" for signals

---

## 7. Token-Specific Signal Effectiveness (From Hebbian V2)

### The Problem
The cluster analysis shows family-level patterns, but the Hebbian V2 spec already proposes `signal_effectiveness` per token+signal. This is the missing piece: **not all signals work for all tokens**.

### The Solution: Per-Token Signal Scoring

From the Hebbian V2 spec, `signal_effectiveness` table tracks:
```
token + signal + direction → win_rate, confidence, avg_pnl
```

### New Idea: Signal Family Preference per Token

```sql
CREATE TABLE token_family_preference (
    token TEXT NOT NULL,
    family TEXT NOT NULL,
    direction TEXT,
    
    trades INTEGER DEFAULT 0,
    wins INTEGER DEFAULT 0,
    win_rate REAL DEFAULT 0.0,
    avg_pnl REAL DEFAULT 0.0,
    confidence REAL DEFAULT 0.0,
    
    UNIQUE(token, family, direction)
);
```

What it learns:
- "SOL prefers Bollinger bounces (65% WR) but hates Momentum signals (40% WR)"
- "BTC prefers Trendline breaks (70% WR) but ZScore signals underperform (48% WR)"

### Integration Point
In `signal_compactor.py`, after scoring a signal, look up the token's family preference:

```python
family_pref = get_token_family_preference(token, family, direction)
if family_pref and family_pref['confidence'] > 0.6:
    if family_pref['win_rate'] > 60:
        boost = (family_pref['win_rate'] - 50) / 10  # +1 to +5 points
        final_score += boost
    elif family_pref['win_rate'] < 45:
        penalty = (50 - family_pref['win_rate']) / 10  # -1 to -5 points
        final_score -= penalty
```

### Expected Impact
- **+5-8% WR** by personalizing signals per token
- Learns which signals work for which coins
- Self-improving: as trades close, preferences sharpen

---

## 8. Confluence Zone Detector (Real-Time)

### The Problem
The analysis identified specific days where 3+ families spiked simultaneously = best trade setups. But this is computed retrospectively.

### The Solution: Real-time confluence zone detection

```python
def detect_confluence_zone(daily_signals: dict) -> dict | None:
    """Check if today is a confluence zone (3+ families >1σ above mean)."""
    family_counts = count_families(daily_signals)
    total = sum(family_counts.values())
    
    spiking = []
    for family, count in family_counts.items():
        # Get 7-day rolling mean and std for this family
        mean, std = get_family_rolling_stats(family)
        pct = count / max(total, 1) * 100
        if pct > mean + std:
            spiking.append(family)
    
    if len(spiking) >= 3:
        return {
            'is_confluence': True,
            'families': spiking,
            'strength': len(spiking),  # 3 = good, 4 = great, 5 = exceptional
        }
    return None
```

### Integration Point
When a confluence zone is detected:
1. **Boost all signals** in the hot-set by 10-20% (multiple families agreeing)
2. **Increase position size** (higher conviction)
3. **Write to dashboard** for human awareness

### Expected Impact
- **+5-10% WR** on confluence days
- Concentrates capital on highest-probability setups
- Avoids over-trading during low-confluence periods

---

## 9. Inverse Correlation Guard

### The Problem
The analysis shows strong inverse correlations:
- Trendline ↔ Bollinger (r=-0.386)
- Trendline ↔ HL_Copy (r=-0.374)
- Squeeze ↔ HL_Copy (r=-0.266)

When one family dominates, the other should be **penalized or blocked**.

### The Solution: Inverse correlation filter

```python
INVERSE_FAMILIES = {
    'Trendline': ['Bollinger', 'HL_Copy'],
    'Bollinger': ['Trendline'],
    'Squeeze': ['HL_Copy'],
    'HL_Copy': ['Trendline', 'Squeeze'],
    'Momentum': ['Exhaustion'],  # momentum wins when exhaustion loses
}

def inverse_penalty(signal_family: str, dominant_families: list[str]) -> float:
    """Return penalty multiplier if this family contradicts the dominant families."""
    for dom in dominant_families:
        if dom in INVERSE_FAMILIES and signal_family in INVERSE_FAMILIES[dom]:
            return 0.5  # 50% penalty — contradicting the market
    return 1.0  # no penalty
```

### Integration Point
In `signal_compactor.py`, after phase detection:

```python
dominant_families = get_dominant_families(lookback_days=3)
for signal in hotset:
    family = signal_family(signal['signal_type'])
    penalty = inverse_penalty(family, dominant_families)
    signal['score'] *= penalty
```

### Expected Impact
- **+3-5% WR** by avoiding contradictory signals
- Filters out noise from regime transitions
- Creates cleaner hot-set

---

## 10. Signal Family Rotation Tracker

### The Problem
The analysis shows families "rotate" — Trendline dominates, then Squeeze, then Momentum, etc. But the system doesn't track this rotation.

### The Solution: Rotation tracker

```python
class FamilyRotationTracker:
    """Track which families are active and predict rotation."""
    
    def __init__(self):
        self.rotation_history = []  # [(date, dominant_family)]
    
    def record_day(self, date: str, dominant_family: str):
        self.rotation_history.append((date, dominant_family))
    
    def detect_cycle(self) -> dict:
        """Find repeating patterns in family rotation."""
        # Look for sequences like: Trendline → Squeeze → Momentum → ZScore → Bollinger
        # If we see "Trendline → Squeeze" twice, predict "Momentum" next
        
        if len(self.rotation_history) < 10:
            return {'status': 'insufficient_data'}
        
        recent = [f for _, f in self.rotation_history[-10:]]
        
        # Find all 2-family sequences
        sequences = {}
        for i in range(len(recent) - 1):
            seq = f"{recent[i]}→{recent[i+1]}"
            sequences[seq] = sequences.get(seq, 0) + 1
        
        # Most common recent sequence → predict next
        most_common = max(sequences.items(), key=lambda x: x[1])
        
        return {
            'last_transition': most_common[0],
            'count': most_common[1],
            'prediction': self._predict_next(most_common[0]),
        }
```

### Expected Impact
- **+2-3% WR** from anticipating phase transitions
- Creates a "market clock" that tracks where we are in the cycle
- Long-term: learns the market's natural rhythm

---

## 11. New Signal Ideas Based on Cluster Patterns

### Signal 1: `phase_breakout`
**Concept:** Fires when a phase transition is detected (e.g., Trendline → Squeeze → Momentum means breakout imminent).

**Logic:**
- Detect Squeeze family dominance (2+ days)
- Wait for Accelerate or Momentum to appear
- Fire signal with "breakout imminent" tag

**Expected WR:** 65-70% (based on Squeeze→Trendline r=0.799)

### Signal 2: `exhaustion_reversal`
**Concept:** Fires when Exhaustion signals appear after a ZScore surge.

**Logic:**
- ZScore family spiked 2-3 days ago (r=0.864 for ZScore→Exhaustion)
- Exhaustion signals now appearing
- Fire reversal signal

**Expected WR:** 60-65% (based on ZScore→Exhaustion correlation)

### Signal 3: `confluence_hunter`
**Concept:** Fires when 3+ families spike on the same coin simultaneously.

**Logic:**
- Track per-coin family counts
- When 3+ families fire on same coin within 1 day
- Fire "high confluence" signal

**Expected WR:** 70-75% (from confluence zone analysis)

### Signal 4: `regime_filter_signal`
**Concept:** A meta-signal that adjusts all other signals based on current regime.

**Logic:**
- Compute current phase from last 3-5 days of family composition
- Apply phase-specific multipliers to all pending signals
- Not a new signal per se, but a filter layer

### Signal 5: `family_momentum`
**Concept:** Fires when a family's activity is accelerating (3-day rolling average increasing).

**Logic:**
- Track 3-day rolling average of each family's signal count
- When a family's 3-day average is >2x its 7-day average
- Fire "family accelerating" signal for that family

**Expected WR:** 55-60% (early warning system)

---

## 12. Dashboard Enhancements

### New Dashboard: Signal Phase Monitor

```
/var/www/hermes/data/signal_phase.json

{
  "current_phase": "range",
  "phase_since": "2026-08-25",
  "phase_days": 2,
  "dominant_families": ["Bollinger", "Support/Resistance", "HL_Copy"],
  "predicted_next_phase": "defensive",
  "expected_in_days": 2,
  "active_confluences": [
    {"coin": "SOL", "families": ["Bollinger", "R2", "S/R"], "strength": 3}
  ],
  "family_trends": {
    "Bollinger": {"trend": "rising", "3d_avg": 15.2, "7d_avg": 12.1},
    "Trendline": {"trend": "falling", "3d_avg": 3.1, "7d_avg": 8.4}
  },
  "lead_lag_alerts": [
    {"leader": "ZScore", "fired": "2026-08-23", "predicted": "Bollinger", "expected": "2026-08-25", "confidence": 0.73}
  ]
}
```

### New Dashboard Panel: Confluence Zones

Show real-time confluence detection:
- Which coins have 3+ families firing
- Historical win rate of each confluence combo
- Current phase and predicted next phase

---

## 13. Implementation Priority

| Priority | Idea | Complexity | Expected Impact | Dependencies |
|----------|------|------------|-----------------|--------------|
| **P0** | Market Phase Gate (#1) | Medium | +5-10% WR | Phase detection logic |
| **P0** | Confluence Scorer (#3) | Low | +5-8% WR | Family definitions |
| **P1** | Signal Lifecycle Filters (#4) | Low | +3-5% WR | Family definitions |
| **P1** | Inverse Correlation Guard (#9) | Low | +3-5% WR | Correlation data |
| **P2** | Hebbian V2 Family Correlations (#2) | High | +3-5% WR | Correlation engine |
| **P2** | Predictive Signal Sequencing (#6) | Medium | +3-5% WR | Lead-lag data |
| **P2** | Token-Specific Preferences (#7) | Medium | +5-8% WR | Trade history |
| **P3** | Confluence Zone Detector (#8) | Medium | +5-10% WR | Real-time stats |
| **P3** | Family Rotation Tracker (#10) | Low | +2-3% WR | Historical data |
| **P3** | New Signals (#11) | High | Variable | Phase detection |

### Cumulative Expected Impact

If all P0+P1 items are implemented:
- **Phase Gate:** +5-10% WR
- **Confluence Scorer:** +5-8% WR
- **Lifecycle Filters:** +3-5% WR
- **Inverse Guard:** +3-5% WR
- **Total: +16-28% WR improvement** (compounding, not additive)

Current WR estimate: ~52-55% (based on ZScore confidence of 65.3% and Mover confidence of 84.9%)
**Target WR: 68-75%** (with compounding effects)

---

## 14. Risk Considerations

| Risk | Mitigation |
|------|-----------|
| Phase detection is laggy (3-5 day lookback) | Use rolling window, not fixed lookback |
| Confluence scorer could overfit to historical data | Use Bayesian confidence, require min_n=5 |
| Lifecycle filters assume past patterns hold | Decay old patterns, weight recent data |
| Too many filters = signal starvation | Monitor daily trade count, must stay >5/day |
| Phase transitions are unpredictable | Use lead-lag rules, not hard predictions |
| Token preferences need trade history | Start with phase-level, add token-level gradually |

---

## 15. Next Steps

1. **Implement Market Phase Gate** (P0) — Highest impact, medium complexity
2. **Implement Confluence Scorer** (P0) — High impact, low complexity
3. **Add lifecycle roles to all signals** (P1) — Low complexity, high value
4. **Build inverse correlation filter** (P1) — Low complexity, high value
5. **Extend Hebbian V2 with family correlations** (P2) — High complexity, high value
6. **Build signal forecaster** (P2) — Medium complexity, high value
7. **Backtest all changes on 30-day data** — Validate before deploying

---

*Brainstorm generated 2026-08-26. Source: Signal cluster analysis (69,990 signals, 30 days).*
