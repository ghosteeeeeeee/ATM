# Signal Spec: `continuation` V2 — Smart Re-entry After Profitable Close

## Concept

After a trade closes in profit, assess the current trend state to decide:
1. **Re-enter SAME direction** (momentum alive, trend strong = catch next wave)
2. **Re-enter OPPOSITE direction** (move exhausted, overextended = fade the exhaustion)
3. **Skip** (no clear edge = stay out)

**V1 failed** (40% WR, killed Aug 16) because it only fired same-direction with a 5-min window.
**V2 adds**: extended window, trend analysis, exhaustion detection, smart direction.

## Trigger

Trade closes with `pnl_pct >= CONTINUATION_MIN_PNL` (default: +0.3%).
Window: `CONTINUATION_WINDOW_SEC` seconds after close (default: 1800s = 30 min).

## Detection Flow

```
Trade closes (profit-monster, T1, trail)
  → Is close_reason in CONTINUATION_TRIGGER_REASONS?
  → Is pnl_pct >= CONTINUATION_MIN_PNL?
  → Is close_time within CONTINUATION_WINDOW_SEC of now?
  → Analyze trend state (EMA gap, slope, velocity, RSI, z-score)
  → Smart direction decision:
      If exhausted (overextended + velocity dying) → REVERSE direction
      If trend alive (slope/velocity positive) → SAME direction
      If unclear → SKIP
  → Pullback guard: skip if price reversed >1% since close
  → Wave penalty: diminishing confidence after wave 2+
  → Fire signal with decided direction
```

## Trend Analysis (1m candles)

| Metric | What it measures | How |
|--------|-----------------|-----|
| `gap_pct` | Price vs EMA50 | Positive = above EMA, negative = below |
| `slope` | Trend direction/strength | 20-bar linear regression slope, % per bar |
| `velocity` | Recent momentum | 10-bar rate of change, % per bar |
| `ret_5m` | 5m context | 10-bar return on 5m candles |
| `slope_5m` | 5m trend | 10-bar slope on 5m candles |

## Exhaustion Detection

| Condition | LONG exhaustion | SHORT exhaustion |
|-----------|----------------|-----------------|
| RSI (1h) | > 75 | < 25 |
| Z-score (1h) | > 2.0 | < -2.0 |
| Gap + velocity | Gap > 1.5% AND velocity < 0 | Gap < -1.5% AND velocity > 0 |

When exhaustion detected → fire OPPOSITE direction (fade the move).

## Trend Alive Detection

| Condition | LONG alive | SHORT alive |
|-----------|-----------|------------|
| Slope (1m) | > 0.01%/bar | < -0.01%/bar |
| Velocity (1m) | > 0.005%/bar | < -0.005%/bar |
| 5m context | slope_5m > 0 AND ret_5m > 0 | slope_5m < 0 AND ret_5m < 0 |

When trend alive → fire SAME direction (ride the wave).

## Parameters (hermes_constants.py)

```python
# ── Continuation V2 ────────────────────────────────────────────────────
CONTINUATION_ENABLED = True
CONTINUATION_PLUS_ENABLED = True          # re-enter LONG
CONTINUATION_MINUS_ENABLED = True         # re-enter SHORT
CONTINUATION_MIN_PNL = 0.3                # % — minimum PnL to trigger
CONTINUATION_WINDOW_SEC = 1800            # 30 min (was 5 min in V1)

# Trend analysis
CONTINUATION_EMA_PERIOD = 50              # EMA for gap calc
CONTINUATION_SLOPE_PERIOD = 20            # bars for slope
CONTINUATION_VELOCITY_PERIOD = 10         # bars for velocity
CONTINUATION_GAP_THRESHOLD = 0.3          # % gap threshold
CONTINUATION_SLOPE_THRESHOLD = 0.01       # % per bar
CONTINUATION_VELOCITY_THRESHOLD = 0.005   # % per bar

# Exhaustion detection
CONTINUATION_EXHAUST_RSI_LONG = 75
CONTINUATION_EXHAUST_RSI_SHORT = 25
CONTINUATION_EXHAUST_ZSCORE = 2.0
CONTINUATION_EXHAUST_GAP_PCT = 1.5

# Wave control
CONTINUATION_WAVE_COOLDOWN_SEC = 7200     # 2 hour window for wave counting
CONTINUATION_WAVE_MAX = 3                 # max waves per token

# Confidence
CONTINUATION_CONF_BASE = 80
CONTINUATION_CONF_FLOOR = 65
CONTINUATION_CONF_CAP = 90
CONTINUATION_CONF_EXHAUST_BONUS = 5       # +5 for exhaustion fades
CONTINUATION_CONF_TREND_BONUS = 4         # +4 for strong trends
CONTINUATION_CONF_WAVE_PENALTY = 5        # -5 per wave beyond wave 1
CONTINUATION_COOLDOWN_MIN = 60
```

## Source Strings

| Direction | Source | signal_type |
|-----------|--------|-------------|
| LONG | `continuation+` | `continuation_long` |
| SHORT | `continuation-` | `continuation_short` |

## What V2 Changed from V1

| Aspect | V1 (killed) | V2 |
|--------|-------------|-----|
| Window | 5 min (300s) | 30 min (1800s) |
| Direction | Same only | Smart (same or reverse) |
| Intelligence | RSI/zscore thresholds | EMA gap + slope + velocity + exhaustion |
| Exhaustion | None | RSI > 75 / z > 2.0 / gap > 1.5% + velocity dying |
| Wave control | None | Penalty after wave 2+ |
| Compactor | continuation- standalone blocked | Block removed (V2 is smart) |

## What It Does NOT Do

- Does NOT fire on losses (only profit exits)
- Does NOT fire if price reversed >1% since close
- Does NOT fire if trend state is unclear (no edge)
- Does NOT fire if wave count exceeded (diminishing returns)

## Data Sources

- **Trade close events**: PostgreSQL `trades` table
- **Price action**: candles.db (1m, 5m, 1h)
- **Wave counting**: signals_hermes_runtime.db (recent signals)

## Pipeline Integration

- **Speed**: Fast signal (single-token poll per recent close)
- **Layer 1**: Kill-switches, blacklists, cooldown (standard)
- **Layer 2**: `add_signal()` enforcement (unchanged — same source strings)
- **Layer 3**: `signal_compactor` scoring (continuation- standalone block removed)
