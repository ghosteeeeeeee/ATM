# Plan: Phase Acceleration Tuner (ATR-Normalized)

## Goal
Build a tuner that runs every 5 minutes on 1m candles, scans all HL tokens, and tunes `detect_phase()` thresholds per token using ATR-normalized scoring.

## ATR-Normalized Scoring

This mirrors the existing ATR TP/SL system:
```
atr_pct = atr / entry_price
k = _atr_multiplier(atr_pct)   # 0.25 to 2.0 based on volatility regime
sl_pct = k * atr_pct
tp_pct = 2 * k * atr_pct
```

For each phase-accel transition (accelerating phase enter):
- Entry at candle close when phase transitions to 'accelerating'
- Simulate SL = `k × atr_pct`, TP = `2k × atr_pct`
- **Score = ATR multiple** = (PnL%) / atr_pct — how many ATRs the move captured
- **Win = 1+ ATR**, Loss = < 1 ATR

This is volatility-normalized — a 3% move in a low-volatility token scores the same as 8% in a high-vol one.

## Current System

**Hardcoded thresholds** (signal_gen.py lines 147-152):
```
PHASE_BUILDING     = 60
PHASE_ACCELERATING = 75   # ← primary tune target
PHASE_EXHAUSTION   = 88
PHASE_EXTREME      = 95
velocity floor     = 0.05
```

**Existing:** `detect_phase()`, `get_momentum_stats()`, `_run_phase_accel_signals()`

## Proposed Architecture

```
systemd timer (every 5 min)
  └── phase_accel_tuner.py
        ├── Fetch 1m candles for all HL tokens (7-day lookback)
        ├── Compute ATR(14) per token from candles.db
        ├── Sweep BUILDING ∈ {55,58,60,62,65} × ACCEL ∈ {68,72,75,78,80,85}
        ├── For each combo: simulate trades at each ACCEL transition
        │     Entry = candle close when phase enters ACCEL
        │     SL = k × atr_pct, TP = 2k × atr_pct
        │     Score = mean(atr_multiples) across all trades
        ├── Write best thresholds → phase_accel_tuner.db
        └── Update phase_cache (current phase per token, updated every 5 min)

signal_gen.py
  └── _run_phase_accel_signals()
        └── Reads tuned thresholds from phase_accel_tuner.db
        └── detect_phase() called with per-token threshold overrides
```

## DB Schema — `phase_accel_tuner.db`

```sql
CREATE TABLE per_token_thresholds (
    token          TEXT PRIMARY KEY,
    phase_building REAL,       -- e.g. 60
    phase_accel    REAL,       -- e.g. 75
    phase_exhaust  REAL,       -- e.g. 88
    phase_extreme  REAL,       -- e.g. 95
    vel_floor      REAL,       -- e.g. 0.05
    score          REAL,       -- mean ATR multiple (higher = better)
    n_trades       INTEGER,
    winrate        REAL,
    avg_win_atr    REAL,       -- avg win in ATR units
    avg_loss_atr   REAL,       -- avg loss in ATR units
    updated_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE phase_cache (
    token      TEXT PRIMARY KEY,
    phase      TEXT,          -- 'quiet'|'building'|'accelerating'|'exhaustion'|'extreme'
    percentile REAL,
    velocity   REAL,
    atr_pct    REAL,          -- current atr_pct
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## Step-by-Step Plan

### Step 1: Create `phase_accel_tuner.py`

**File:** `/root/.hermes/scripts/phase_accel_tuner.py`

Core sweep logic:
```python
def compute_atr(closes, highs, lows, period=14):
    # Standard ATR from 1m candles

def _atr_multiplier(atr_pct):
    if atr_pct >= 0.10: return 2.0
    elif atr_pct >= 0.05: return 1.5
    elif atr_pct >= 0.02: return 1.0
    elif atr_pct >= 0.01: return 0.5
    else: return 0.25

# For each token, each threshold combo:
trades = []
for i in range(warmup, len(candles)-1):
    pct, vel = compute_percentile_velocity(...)
    phase = detect_phase(pct, vel, building, accel, exhaustion, extreme)
    prev_phase = phases[i-1]
    if phase == 'accelerating' and prev_phase != 'accelerating':
        entry = candles[i+1]['close']
        atr = compute_atr(...)
        atr_pct = atr / entry
        k = _atr_multiplier(atr_pct)
        sl = entry * (1 - k * atr_pct)
        tp = entry * (1 + 2 * k * atr_pct)
        # Walk forward: find when SL/TP hit
        # Record: won (touched tp first), lost (touched sl first), or open
        pnl_atr = pnl_pct / atr_pct
        trades.append(pnl_atr)

score = mean([t['pnl_atr'] for t in trades])
winrate = wins / len(trades)
```

Grid: BUILDING ∈ {55, 58, 60, 62, 65} × ACCEL ∈ {68, 72, 75, 78, 80, 85}
→ 30 combos per token per run

Fallback: if < 5 trades for a combo, skip (insufficient data)

### Step 2: Create systemd timer (every 5 min)

**Service:** `/etc/systemd/system/phase-accel-tuner.service`
**Timer:** `/etc/systemd/system/phase-accel-tuner.timer`

```ini
[Timer]
OnBootSec=30
OnUnitActiveSec=5min
AccuracySec=1s

[Install]
WantedBy=timers.target
```

### Step 3: Wire into signal_gen.py

In `_run_phase_accel_signals()`:
```python
def _get_tuned_thresholds(token):
    row = query_db("SELECT * FROM per_token_thresholds WHERE token=?", (token,))
    if row:
        return {'building': row.phase_building, 'accel': row.phase_accel, ...}
    return None  # fallback to globals

def _run_phase_accel_signals(prices_dict):
    for token in ...:
        tuned = _get_tuned_thresholds(token)
        if tuned:
            phase = detect_phase(pct, vel,
                                  building=tuned['building'],
                                  accel=tuned['accel'],
                                  exhaustion=tuned['phase_exhaust'],
                                  extreme=tuned['phase_extreme'])
        else:
            phase = detect_phase(pct, vel)  # global defaults
        # ... rest unchanged
```

### Step 4: Read phase_cache for current phase (fast path)

For tokens already tuned, `_run_phase_accel_signals` can read from `phase_cache` instead of recomputing `get_momentum_stats()`:
- Skip recompute if `phase_cache` updated < 2 min ago
- Fall back to live compute if cache stale or missing

## Files to Create
- `/root/.hermes/scripts/phase_accel_tuner.py`
- `/etc/systemd/system/phase-accel-tuner.service`
- `/etc/systemd/system/phase-accel-tuner.timer`
- `/root/.hermes/data/phase_accel_tuner.db` (auto-created by script)

## Files to Modify
- `/root/.hermes/scripts/signal_gen.py`
  - `detect_phase()`: add optional threshold params
  - `_run_phase_accel_signals()`: read tuned thresholds from DB

## Validation
1. `python3 phase_accel_tuner.py` standalone → verify `phase_accel_tuner.db` populated
2. `systemctl status phase-accel-tuner.timer` → verify timer active
3. Check `phase_cache` table: `SELECT token, phase, atr_pct FROM phase_cache`
4. Before/after comparison: run `_run_phase_accel_signals` with and without tuned params on same candles

## Risks & Tradeoffs
- **Timer overlap**: Set `TimeoutStartSec=300` in service to prevent stacking
- **Cold token problem**: New tokens or tokens with < 5 ATR trades → fall back to globals
- **Phase cache staleness**: `price_age_minutes()` guard already in `_run_phase_accel_signals()` — handles stale HL data
- **DB contention**: signal_gen reads phase_accel_tuner.db every minute → use READ COMMITTED, brief locks (SQLite handles fine at this volume)
