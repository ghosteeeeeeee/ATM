# Stop-Loss & Exit Rules Config

> Source of truth: `position_manager.py` constants (lines 60-98)
> Docker target: `/app/ATM/config/stoploss.md`

---

## Exit Strategy Overview

| Exit | Trigger | Timeout | Status | Notes |
|---|---|---|---|---|
| **Cut Loser** | pnl ≤ -2.0% | immediate | **DISABLED** | Guardian handles emergency exits; cut_loser commented out to avoid races (lines 1583-87) |
| **Hard SL** | price hits SL price | at entry | active | 3% default (`SL_PCT`), 1% min (`SL_PCT_MIN`) |
| **Trailing SL** | pnl ≥ +1% | locks in profit | active | 0.3% buffer → 0.2% floor; tightens with volume confirmation |
| **Cascade Flip** | loss -0.25% armed, -0.35/-0.50% fire | speed-armed | active | Reverses losing position into opposite direction |
| **Wave Turn** | z>1.5 + accel reverses | immediate | active | Closes before stale checks |
| **Stale Winner** | pnl ≥ +1% + stalled | 30 min | active | Closed if speed < 33rd percentile + vel < 0.2% for 30+ min |
| **Stale Loser** | pnl ≤ -1% + stalled | 30 min | active | Closed if speed < 33rd percentile + vel < 0.2% for 30+ min |

---

## Hard Stop-Loss (Entry-Time SL)

Set at trade entry based on entry price + `SL_PCT`.

```
LONG:  stop_loss = entry × (1 - SL_PCT)   # e.g. entry $100 → SL $97
SHORT: stop_loss = entry × (1 + SL_PCT)
```

| Constant | Value | Location |
|---|---|---|
| `SL_PCT` | 3% | position_manager.py:61 |
| `SL_PCT_MIN` | 1% minimum | position_manager.py:62 |
| `CUT_LOSER_PNL` | -2.0% (disabled) | position_manager.py:60 |

---

## Trailing Stop-Loss

Engages when `pnl_pct >= +1%` (`TRAILING_START_PCT_DEFAULT`). Once active, it is the **ONLY** exit — `cut_loser` is disabled during trailing.

### Activation

```
TRAILING_START_PCT_DEFAULT = 0.01   # +1% profit to activate
```

### Buffer (distance from profit peak)

| Phase | Buffer | When |
|---|---|---|
| Phase 1 (initial) | 0.30% (`TRAILING_BUFFER_PCT_DEFAULT`) | First activation |
| Phase 2 (tightened) | 0.20% (`TRAILING_PHASE2_BUFFER_DEFAULT`) | Profit continues to grow |
| Volume confirmed | 0.35% (`TRAILING_VOL_CONF_BUFFER`) | 24h MA volume confirms direction |
| Volume weak | 0.25% (`TRAILING_VOL_NO_CONF_BUFFER`) | Volume below 24h MA |

```
trailing_SL = profit_peak - buffer
LONG:  trailing_SL = profit_peak × (1 - buffer)
SHORT: trailing_SL = profit_peak × (1 + buffer)
```

| Constant | Value | Location |
|---|---|---|
| `TRAILING_START_PCT_DEFAULT` | 1% | position_manager.py:67 |
| `TRAILING_BUFFER_PCT_DEFAULT` | 0.3% | position_manager.py:68 |
| `TRAILING_PHASE2_BUFFER_DEFAULT` | 0.2% | position_manager.py:69 |
| `TRAILING_VOL_CONF_BUFFER` | 0.35% | position_manager.py:73 |
| `TRAILING_VOL_NO_CONF_BUFFER` | 0.25% | position_manager.py:74 |
| `TRAILING_VOL_LOOKBACK` | 24 candles | position_manager.py:75 |
| `TRAILING_TIGHTEN` | True | position_manager.py:76 |
| `TRAILING_DATA_FILE` | `/var/www/hermes/data/trailing_stops.json` | position_manager.py:77 |

---

## Cascade Flip

Speed-armed reversal. Closes losing position AND enters opposite direction when conditions are met.

### State Machine

```
pnl > -0.25%                    → NOT ARMED (no action)
-0.50% < pnl <= -0.25%          → ARMED (speed check, wait)
pnl <= -0.50% (pctl 50-80)      → FLIP TRIGGERED
pnl <= -0.35% (pctl > 80)       → FAST FLIP (high momentum)
```

### Confluence Requirements (for flip to fire)

- Opposite signal in `PENDING/WAIT/APPROVED/SKIPPED` state
- Confidence ≥ 60%
- Created within last 30 minutes
- At least 1 distinct signal type agreeing

### Post-Flip Trailing

After a flip, trailing activates tighter than normal:

```
TRAILING_POST_FLIP_PCT = 0.5%  # 0.5% activation + 0.5% buffer
```

| Constant | Value | Location |
|---|---|---|
| `CASCADE_FLIP_ARM_LOSS` | -0.25% | position_manager.py:89 |
| `CASCADE_FLIP_TRIGGER_LOSS` | -0.50% (pctl 50-80) | position_manager.py:90 |
| `CASCADE_FLIP_HF_TRIGGER_LOSS` | -0.35% (pctl > 80) | position_manager.py:91 |
| `CASCADE_FLIP_MIN_CONF` | 60% | position_manager.py:92 |
| `CASCADE_FLIP_MAX_AGE_M` | 30 min | position_manager.py:93 |
| `CASCADE_FLIP_MIN_TYPES` | 1 | position_manager.py:94 |
| `CASCADE_FLIP_MAX` | 3 per token | position_manager.py:95 |
| `CASCADE_FLIP_POST_TRAIL_PCT` | 0.5% | position_manager.py:96 |

---

## Wave Turn Exit

Z-score extreme + acceleration flipping direction. Fires BEFORE stale checks.

```
LONG:  z_score > +1.5 AND acceleration < 0  → close LONG
SHORT: z_score < -1.5 AND acceleration > 0  → close SHORT
```

Only fires when trailing is NOT active.

---

## Stale Winner / Loser

Speed-stall detection. Only fires when trailing is NOT active.

| Type | PnL Condition | Speed Condition | Time |
|---|---|---|---|
| Stale Winner | ≥ +1% (`STALE_WINNER_MIN_PROFIT`) | pctl < 33 AND vel < 0.2% (`STALE_VELOCITY_THRESHOLD`) | 30+ min (`STALE_WINNER_TIMEOUT_MINUTES`) |
| Stale Loser | ≤ -1% (`STALE_LOSER_MAX_LOSS`) | pctl < 33 AND vel < 0.2% | 30+ min (`STALE_LOSER_TIMEOUT_MINUTES`) |

> ⚠️ Bug: Config comment says 15 min for losers (line 32) but code uses 30 min (line 337).

| Constant | Value | Location |
|---|---|---|
| `STALE_WINNER_TIMEOUT_MINUTES` | 15 min | position_manager.py:32 |
| `STALE_LOSER_TIMEOUT_MINUTES` | 30 min | position_manager.py:33 |
| `STALE_WINNER_MIN_PROFIT` | +1% | position_manager.py:34 |
| `STALE_LOSER_MAX_LOSS` | -1% | position_manager.py:35 |
| `STALE_VELOCITY_THRESHOLD` | 0.2% | position_manager.py:37 |
| `SPEED_STALL_THRESHOLD` | 33 (pctl) | position_manager.py:324 |

---

## Exit Priority Order

```
1. Wave Turn          (immediate — highest conviction)
2. Trailing SL       (once active, ONLY exit — cut_loser disabled)
3. Cascade Flip      (speed-armed reversal, before cut_loser)
4. Stale Winner/Loser (speed-stall, fires alongside trailing)
5. Cut Loser          DISABLED — guardian handles emergency
```

---

## Guardian vs Position Manager

- **Guardian** (`hl-sync-guardian.py`): Live HL execution, orphan recovery, PnL sync
- **Position Manager** (`position_manager.py`): Paper/computed exits, trailing SL calc, cascade flips

Cut_loser is disabled in position_manager to prevent races — guardian is the authoritative emergency handler.

---

## Runtime File Paths

| File | Purpose |
|---|---|
| `/var/www/hermes/data/trailing_stops.json` | Active trailing SL state |
| `/var/www/hermes/data/flip_counts.json` | Cascade flip counts per token |
| `/var/www/hermes/data/volume_cache.json` | 24h volume MA cache |
