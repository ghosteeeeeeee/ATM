# Continuum Engine — From Events to States

**Created:** 2026-09-04 00:30 UTC
**Status:** Spec — architecture design
**Priority:** HIGH — replaces event-based signals with state-based continuum

---

## The Shift

**Current system:** Signal fires → event → trade entry/exit
**New system:** States accumulate → compound → trigger trades when thresholds met

The continuum engine tracks BTC (and later alts) as a **living state machine**. Instead of waiting for a signal to fire, we watch states evolve in real-time. When enough states align, we enter. When states degrade, we exit. No events — just a continuous flow of state changes.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    CONTINUUM ENGINE                          │
│                                                              │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐   │
│  │  State        │    │  State       │    │  Compound    │   │
│  │  Tracker      │───▶│  Machine     │───▶│  Scorer      │   │
│  │  (30s tick)   │    │  (entry/exit)│    │  (0-100)     │   │
│  └──────────────┘    └──────────────┘    └──────────────┘   │
│         │                   │                   │            │
│         ▼                   ▼                   ▼            │
│  ┌──────────────────────────────────────────────────────┐   │
│  │              SQLite State Table                       │   │
│  │  (persistent, queryable, survives restarts)          │   │
│  └──────────────────────────────────────────────────────┘   │
│         │                                                    │
│         ▼                                                    │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐   │
│  │  Entry        │    │  Exit        │    │  Position    │   │
│  │  Signal       │    │  Signal      │    │  Sizer       │   │
│  └──────────────┘    └──────────────┘    └──────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

---

## State Dimensions

Each state dimension tracks a specific aspect of BTC's position in the continuum.

### Core States (6 dimensions)

| # | State | Values | Hysteresis | Description |
|---|-------|--------|------------|-------------|
| 1 | **EMA300_POSITION** | ABOVE / BELOW / AT | 5 candles ON / 3 candles OFF | Price relative to EMA300 (1m) |
| 2 | **EMA300_DURATION** | counter (minutes) | resets on flip | Consecutive minutes above/below EMA300 |
| 3 | **ZSCORE_TIER** | STRONG_NEG / NEG / NEUTRAL / POS / STRONG_POS | 3 candles ON / 5 candles OFF | Z-score level (z = (price - 20h_mean) / 20h_std) |
| 4 | **VOLUME_REGIME** | LOW / NORMAL / HIGH / PARABOLIC | 5 candles ON / 3 candles OFF | Volume vs 1hr rolling average |
| 5 | **VELOCITY** | FALLING / SLOW / RISING / FAST | 3 candles ON / 3 candles OFF | Price velocity (5m change %) |
| 6 | **ACCELERATION** | NEGATIVE / FLAT / POSITIVE | 3 candles ON / 3 candles OFF | Rate of change of velocity |

### Extended States (from coin_tracker insights)

| # | State | Values | Description |
|---|-------|--------|-------------|
| 7 | **WYCKOFF_PHASE** | ACCUMULATION / MARKUP / DISTRIBUTION / MARKDOWN / UNKNOWN | Wyckoff market structure |
| 8 | **EWAVE_COUNT** | W1 / W2 / W3 / W4 / W5 / CA / CB / CC / UNKNOWN | Elliott wave position |
| 9 | **TREND_QUALITY** | STRONG_UP / UP / WEAK / DOWN / STRONG_DOWN | Multi-EMA alignment score |
| 10 | **MARKET_PHASE** | CALM / STORMY / RECOVERY / DECLINING | Overall market regime |

### Multi-Timeframe States (fractal)

Each core state is computed across **4 timeframes**: 1m, 5m, 15m, 1h

```
BTC continuum state at any moment:
├── 1m states:  [EMA300:ABOVE, DURATION:45, ZSCORE:POS, VOLUME:HIGH, VEL:RISING, ACCEL:POS]
├── 5m states:  [EMA300:ABOVE, DURATION:9,  ZSCORE:POS, VOLUME:NORMAL, VEL:RISING, ACCEL:FLAT]
├── 15m states: [EMA300:ABOVE, DURATION:3,  ZSCORE:NEUTRAL, VOLUME:NORMAL, VEL:SLOW, ACCEL:POS]
└── 1h states:  [EMA300:BELOW, DURATION:0, ZSCORE:NEG, VOLUME:LOW, VEL:FALLING, ACCEL:NEG]
```

**Fractal rule:** Small timeframes inform big timeframes. Big timeframes validate small timeframes.
- If 1m says "wave starting" but 1h says "trend unchanged" → the 1m signal is noise
- If 1m says "wave starting" and 1h says "trend shifting" → high conviction

---

## State Machine: Entry Logic

### LONG Entry Sequence

```
STATE 1: EMA300_CROSS
  └─ Trigger: price > EMA300 for 5+ consecutive 1m candles
  └─ Effect: EMA300_POSITION = ABOVE, EMA300_DURATION starts counting

STATE 2: CONFIRMED_ABOVE
  └─ Trigger: EMA300_DURATION >= 60 minutes (1h)
  └─ Effect: Entry state machine advances to phase 2
  └─ Anti-fake-out: filters the 2-5 minute false crosses

STATE 3: ZSCORE_RISING
  └─ Trigger: ZSCORE_TIER moving from NEG toward POS
  └─ Specifically: z was < -0.5 and is now > -0.5 and rising
  └─ Effect: Momentum confirmed, wave has direction

STATE 4: VOLUME_BUILDING
  └─ Trigger: VOLUME_REGIME = HIGH or PARABOLIC
  └─ Specifically: 5min volume > 1.5x of 1hr average
  └─ Effect: Wave has energy, confirmed breakout

ENTRY SIGNAL: States 1+2+3 must be TRUE
  └─ State 4 is BONUS: adds to confidence/position size
  └─ Multi-timeframe bonus: if 5m/15m also confirm → higher confidence
```

### SHORT Entry Sequence (mirror)

```
STATE 1: EMA300_CROSS_BELOW
  └─ Trigger: price < EMA300 for 5+ consecutive 1m candles

STATE 2: CONFIRMED_BELOW
  └─ Trigger: EMA300_DURATION >= 60 minutes below

STATE 3: ZSCORE_FALLING
  └─ Trigger: ZSCORE_TIER moving from POS toward NEG

STATE 4: VOLUME_BUILDING
  └─ Trigger: VOLUME_REGIME = HIGH or PARABOLIC

ENTRY: States 1+2+3 TRUE, State 4 bonus
```

---

## Compound Scorer (0-100)

The scorer runs every 30 seconds, computing a continuous score from the current state.

### Scoring Weights

```python
STATE_WEIGHTS = {
    # Core states
    'ema300_position':     0.15,   # Above/below EMA300
    'ema300_duration':     0.10,   # How long (longer = stronger trend)
    'zscore_tier':         0.15,   # Z-score level
    'volume_regime':       0.12,   # Volume confirmation
    'velocity':            0.10,   # Price velocity
    'acceleration':        0.08,   # Momentum of momentum
    
    # Extended states
    'wyckoff_phase':       0.08,   # Market structure
    'ewave_count':         0.06,   # Wave position
    'trend_quality':       0.08,   # Multi-EMA alignment
    'market_phase':        0.08,   # Overall regime
}
# Total: 1.00
```

### Score Computation

```python
def compute_state_score(states, timeframe='1m'):
    """
    Compute 0-100 score from current states.
    
    Each state dimension contributes to the score based on:
    - Its current value (e.g., ABOVE_EMA300 = +15 points)
    - Its weight (e.g., ema300_position = 0.15)
    - Multi-timeframe alignment bonus
    """
    score = 50.0  # Start neutral
    
    # EMA300 position
    if states['ema300_position'] == 'ABOVE':
        score += 15 * STATE_WEIGHTS['ema300_position'] * 100
    elif states['ema300_position'] == 'BELOW':
        score -= 15 * STATE_WEIGHTS['ema300_position'] * 100
    
    # EMA300 duration (logarithmic scaling)
    duration = states['ema300_duration']
    if duration > 0:
        duration_score = min(10, math.log2(duration + 1))  # 0-10 points
        score += duration_score * STATE_WEIGHTS['ema300_duration'] * 10
    
    # Z-score tier
    zscore_map = {
        'STRONG_NEG': -15, 'NEG': -5, 'NEUTRAL': 0,
        'POS': 5, 'STRONG_POS': 15
    }
    score += zscore_map.get(states['zscore_tier'], 0) * STATE_WEIGHTS['zscore_tier'] * 10
    
    # Volume regime
    volume_map = {
        'LOW': -10, 'NORMAL': 0, 'HIGH': 10, 'PARABOLIC': 20
    }
    score += volume_map.get(states['volume_regime'], 0) * STATE_WEIGHTS['volume_regime']
    
    # Velocity
    velocity_map = {
        'FALLING': -10, 'SLOW': 0, 'RISING': 10, 'FAST': 15
    }
    score += velocity_map.get(states['velocity'], 0) * STATE_WEIGHTS['velocity']
    
    # Acceleration
    accel_map = {
        'NEGATIVE': -8, 'FLAT': 0, 'POSITIVE': 8
    }
    score += accel_map.get(states['acceleration'], 0) * STATE_WEIGHTS['acceleration']
    
    # Multi-timeframe alignment bonus
    # If 5m/15m/1h states agree with 1m → bonus
    alignment_bonus = compute_tf_alignment(states)
    score += alignment_bonus
    
    return max(0, min(100, score))
```

### Score Thresholds

| Score | Action | Position Size |
|-------|--------|---------------|
| 0-30 | No trade | 0% |
| 30-40 | Watch only | 0% |
| 40-50 | Small position (early entry) | 25% |
| 50-70 | Normal position | 50% |
| 70-85 | Full position | 75% |
| 85-100 | Maximum conviction | 100% |

**Hysteresis:** Entry when score crosses above 30. Exit when score drops below 20. This prevents whipsaws.

---

## Tiered Exit System

### Tier 1: Tighten Stop (Single State Degradation)

Any single state degrades → move stop to breakeven or tighter trailing.

Examples:
- Volume drops from HIGH → NORMAL → tighten stop
- Velocity drops from RISING → SLOW → tighten stop
- Z-score drops from STRONG_POS → POS → tighten stop

### Tier 2: Reduce Position (Compound Degradation)

2+ states degrade simultaneously → close 50% of position.

Examples:
- Volume drops AND velocity drops → close half
- Z-score drops AND acceleration turns negative → close half

### Tier 3: Full Exit (Entry State Machine Breaks)

The entry state machine itself breaks → close remaining position.

Examples:
- Price drops below EMA300 for 30+ minutes → full exit (LONG)
- Z-score drops below -1.5 → full exit (LONG)
- Score drops below 20 → full exit

### Exit State Machine (LONG example)

```
ENTRY: States 1+2+3 TRUE → score > 30 → ENTER LONG

TIER 1: Any single state degrades
  └─ Action: Move stop to breakeven
  └─ Example: Volume: HIGH → NORMAL

TIER 2: 2+ states degrade within 5 minutes
  └─ Action: Close 50% position
  └─ Example: Volume: HIGH → NORMAL + Velocity: RISING → SLOW

TIER 3: Entry state machine breaks
  └─ Action: Close remaining position
  └─ Example: EMA300_DURATION resets to 0 (price below EMA300 for 3+ candles)
  └─ OR: Score drops below 20
  └─ OR: ZSCORE_TIER drops to STRONG_NEG
```

---

## Fractal Multi-Timeframe Logic

### The Bidirectional Flow

```
SMALL SCALE (1m, 5m)          BIG SCALE (15m, 1h)
     │                              │
     │  ── informs ──▶              │
     │                              │
     │  ◀── validates ──            │
     │                              │
```

### Rules

1. **Small → Big:** When 1m states change, they influence 5m states (and 5m influences 15m, etc.)
   - If 1m EMA300 crosses above and holds for 60 min → 5m EMA300 position may flip to ABOVE

2. **Big → Small validation:** When small TF states change, check big TF for confirmation
   - If 1m says "wave starting" but 1h trend is still DOWN → reduce confidence
   - If 1m says "wave starting" and 1h trend is shifting UP → full confidence

3. **Noise filtering:** Small TF states that don't persist long enough to influence big TFs are noise
   - 1m EMA300 cross that lasts 5 minutes → doesn't affect 5m state → noise
   - 1m EMA300 cross that lasts 60+ minutes → affects 5m state → signal

4. **Scale matching:** The same pattern appears at every scale
   - BTC wave on 1m (hours) = same structure as BTC wave on 1h (weeks)
   - The continuum engine should detect the same states at every timeframe

---

## SQLite State Table

```sql
CREATE TABLE continuum_states (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    token TEXT NOT NULL,                     -- 'BTC'
    timeframe TEXT NOT NULL,                 -- '1m', '5m', '15m', '1h'
    ts INTEGER NOT NULL,                     -- Unix timestamp
    
    -- Core states
    ema300_position TEXT,                    -- 'ABOVE', 'BELOW', 'AT'
    ema300_duration INTEGER,                 -- Minutes above/below
    zscore_tier TEXT,                        -- 'STRONG_NEG', 'NEG', 'NEUTRAL', 'POS', 'STRONG_POS'
    zscore_value REAL,                       -- Actual z-score value
    volume_regime TEXT,                      -- 'LOW', 'NORMAL', 'HIGH', 'PARABOLIC'
    velocity TEXT,                           -- 'FALLING', 'SLOW', 'RISING', 'FAST'
    velocity_value REAL,                     -- Actual velocity %
    acceleration TEXT,                       -- 'NEGATIVE', 'FLAT', 'POSITIVE'
    acceleration_value REAL,                 -- Actual acceleration %
    
    -- Extended states
    wyckoff_phase TEXT,                      -- 'ACCUMULATION', 'MARKUP', etc.
    ewave_count TEXT,                        -- 'W1', 'W2', etc.
    trend_quality TEXT,                      -- 'STRONG_UP', 'UP', etc.
    market_phase TEXT,                       -- 'CALM', 'STORMY', etc.
    
    -- Compound score
    state_score REAL,                        -- 0-100 compound score
    
    -- Entry/exit tracking
    entry_state TEXT,                        -- Current entry state machine phase
    position_side TEXT,                      -- 'LONG', 'SHORT', 'NONE'
    position_size_pct REAL,                  -- 0-100% of max position
    
    -- Metadata
    updated_at INTEGER DEFAULT (strftime('%s', 'now')),
    
    UNIQUE(token, timeframe, ts)
);

CREATE INDEX idx_continuum_token_ts ON continuum_states(token, ts);
CREATE INDEX idx_continuum_tf_ts ON continuum_states(timeframe, ts);
```

---

## Implementation Plan

### Phase 1: Core State Tracker
**File:** `scripts/continuum_engine.py`

- Read BTC prices from `hl_cache.json` (allmids() every 30s)
- Compute EMA300, z-score, volume, velocity, acceleration
- Track state transitions with hysteresis
- Write states to SQLite every 30 seconds
- Compute compound score

### Phase 2: Entry State Machine
**File:** `scripts/continuum_entry.py`

- Implement the 4-state entry sequence
- Track entry state machine progression
- Emit entry signals when states align
- Integrate with signal_compactor.py (or replace it for BTC)

### Phase 3: Exit Manager
**File:** `scripts/continuum_exit.py`

- Monitor state degradation
- Implement tiered exit system
- Tighten stops on single state change
- Reduce position on compound degradation
- Full exit on entry state machine break

### Phase 4: Multi-Timeframe Fractal
**File:** `scripts/continuum_fractal.py`

- Compute states across 1m/5m/15m/1h
- Implement bidirectional influence
- Noise filtering (small TF must persist to affect big TF)
- Scale matching (same pattern at every timeframe)

### Phase 5: Integration
- Wire into `decider_run.py` for trade execution
- Add continuum states to dashboard
- Backtest on historical BTC 1m data
- Paper trade test

---

## Comparison to Current System

| Aspect | Current System | Continuum Engine |
|--------|---------------|------------------|
| **Signal type** | Event-based (fires once) | State-based (continuous) |
| **Entry timing** | After signal fires | When states align |
| **Exit timing** | Fixed rules (trailing stop, etc.) | State degradation (tiered) |
| **Multi-timeframe** | Separate signals per TF | Fractal bidirectional |
| **Position sizing** | Fixed or rule-based | Score-based (0-100) |
| **Noise filtering** | Confidence threshold | State hysteresis + duration |
| **State awareness** | None (each signal is independent) | Full (knows where it is in continuum) |
| **Restart behavior** | Loses state | Persists in SQLite |

---

## Expected Improvements

1. **Better entries:** State machine ensures we enter when the trend is confirmed, not at the first cross
2. **Better exits:** Tiered system gets out when states degrade, not when a fixed stop is hit
3. **Less noise:** Hysteresis prevents whipsaws from 1-candle dips
4. **Position awareness:** Always know where BTC is in the wave continuum
5. **Scalable:** Same architecture works for alts later (fractal multi-asset)

---

## Next Steps

1. [ ] Build `continuum_engine.py` — core state tracker
2. [ ] Build state transition logic with hysteresis
3. [ ] Implement compound scorer
4. [ ] Build entry state machine
5. [ ] Build tiered exit system
6. [ ] Add SQLite state table
7. [ ] Backtest on Sep 3 BTC data (known wave pattern)
8. [ ] Paper trade test
9. [ ] Integrate with decider_run.py
10. [ ] Update surfing.md with continuum philosophy
