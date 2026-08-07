# Momentum Leaderboard Signal — Spec

**Date:** 2026-08-07
**Status:** Spec — not yet implemented

## Concept

Build our own "top movers" leaderboard from local candle data. Rank tokens by move size across timeframes, then decide direction — ride continuation or fade overextension.

## Data Sources (zero new API calls)

| Source | What | Already populated? |
|--------|------|--------------------|
| `candles.db` → `candles_5m` | 5-min OHLCV | Yes (~167 tokens) |
| `candles.db` → `candles_15m` | 15-min OHLCV | Yes (~212 tokens) |
| `candles.db` → `candles_1h` | 1-hour OHLCV | Yes (~212 tokens) |
| `speed_cache.json` | velocity/accel/percentile | Yes (from speed_tracker) |

## Algorithm

### Step 1 — Compute returns per token

```python
ret_5m  = (close[-1] - close[-6]) / close[-6]   # last 5 × 5m candles
ret_15m = (close[-1] - close[-5]) / close[-5]   # last 5 × 15m candles
ret_1h  = (close[-1] - close[-5]) / close[-5]   # last 5 × 1h candles
move_score = abs(ret_1h) * 0.5 + abs(ret_15m) * 0.3 + abs(ret_5m) * 0.2
```

### Step 2 — Rank

Rank all tokens by `move_score`, take top N (default 10).

### Step 3 — Direction decision per top mover

| Condition | Direction | Logic |
|-----------|-----------|-------|
| `ret_1h` big positive AND `ret_5m` still positive | **LONG** | Momentum continuation — trend intact |
| `ret_1h` big positive BUT `ret_5m` negative + speed > 70th pctl | **SHORT** | Overextended, fading the blow-off |
| `ret_1h` big negative AND `ret_5m` still negative | **SHORT** | Momentum continuation — breakdown intact |
| `ret_1h` big negative BUT `ret_5m` positive + speed > 70th pctl | **LONG** | Oversold bounce — rubber band snap-back |

### Step 4 — Confidence scaling

```
base = 75
+5 if 15m and 1h agree on direction (confluence)
+5 if speed percentile > 80 (elite mover)
-10 if overextended (abs(ret_5m) > 3.0%)
capped at 88
```

## Guards

- Blacklists: `SHORT_BLACKLIST` / `LONG_BLACKLIST` (enforced by `add_signal`)
- Stale data: skip if latest candle > 15 min old
- Overextended: skip if `abs(ret_5m) > 3.0%` (too risky to enter)
- Open positions: skip tokens already held
- Cooldown: 30 min per token+direction
- Min move threshold: `move_score > 1.0%` (filter noise)
- Delisted: skip

## Files to Create/Modify

| File | Action | Purpose |
|------|--------|---------|
| `scripts/signals/momentum_leaderboard.py` | **CREATE** | Signal logic |
| `scripts/hermes_constants.py` | **EDIT** | Add flags + params |
| `scripts/signals/__init__.py` | **EDIT** | Import + registry entry |

## Constants (in `hermes_constants.py`)

```python
# ── Momentum Leaderboard Signal ─────────────────────────────────────────────
MOMENTUM_LEADERBOARD_ENABLED = False          # master switch
MOMENTUM_LEADERBOARD_PLUS_ENABLED = True      # LONG direction
MOMENTUM_LEADERBOARD_MINUS_ENABLED = True     # SHORT direction
MOMENTUM_LEADERBOARD_TOP_N = 10               # top movers to evaluate
MOMENTUM_LEADERBOARD_MOVE_MIN = 1.0           # min move_score % to emit
MOMENTUM_LEADERBOARD_COOLDOWN_MIN = 30        # per token+direction
MOMENTUM_LEADERBOARD_RET_WINDOWS = (6, 5, 5)  # candles for 5m/15m/1h
```

## Signal Types & Sources

| Direction | signal_type | source |
|-----------|-------------|--------|
| LONG | `mover_long` | `mover+` |
| SHORT | `mover_short` | `mover-` |

## Registry Entry

```python
{'name': 'momentum_leaderboard', 'enabled': 'MOMENTUM_LEADERBOARD_ENABLED', 'run': _momentum_leaderboard_run},
```

## Per-Direction Enforcement (in `scan_leaderboard_signals`)

```python
if direction == 'LONG' and not MOMENTUM_LEADERBOARD_PLUS_ENABLED:
    continue
if direction == 'SHORT' and not MOMENTUM_LEADERBOARD_MINUS_ENABLED:
    continue
```
