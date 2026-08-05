# Stale Signals Persist Through Regime Reversal — VERIFIED BUG (2026-05-13)

## Bug Summary
**Status:** VERIFIED — architectural flaw, not a one-off
**Location:** signal_compactor.py + decider_run.py
**Claim:** "Old signals from hours earlier still execute after price regime has completely reversed"

## What the claim gets wrong
Signals **cannot** persist for hours — staleness caps them at 5 minutes from `entry_origin_ts`.

## What the claim gets right
Counter-regime signals survive regime flips and can execute before staleness expires.

## Live Validation (2026-05-13 18:35)
IMX SHORT was open at 0.18697 (entered 18:29:07, ~5.6 min old) while candles.db 1m regression showed **LONG_BIAS** (conf=17). Trade signal was accel-300-,rs-r688 (2-source, conf=79.9). This is the exact bug scenario: SHORT executing against LONG_BIAS regime.

Other open trades at time of check:
| Token | Dir | Entry | Age | Signal | Regime |
|-------|-----|-------|-----|--------|--------|
| IMX | SHORT | 0.18697 | 5.6min | accel-300-,rs-r688 | LONG_BIAS |
| COMP | LONG | 22.928 | 21.6min | accel-300+,rs-s64 | LONG_BIAS |
| BLUR | LONG | 0.02603 | 56.5min | accel-300+,rs-s478 | LONG_BIAS |

## Root Cause Analysis

### 1. signal_compactor.py — staleness is the only exit timer
- `staleness_mult = max(0.0, 1.0 - (age_m * 0.2))` → 0 at 5 min
- `_filter_safe_prev_hotset()` only checks: staleness + confluence + WR
- **No regime check in preserve path**
- No HOTSET_TTL constant — staleness IS the TTL

### 2. signal_compactor.py — reg_mult is a score multiplier, not a filter
```python
# Lines 253-266
if (regime == 'LONG_BIAS' and direction == 'LONG') or \
   (regime == 'SHORT_BIAS' and direction == 'SHORT'):
    reg_mult = 1.50   # aligned: boost
elif (regime == 'LONG_BIAS' and direction == 'SHORT') or \
     (regime == 'SHORT_BIAS' and direction == 'LONG'):
    reg_mult = 0.50   # counter-regime: suppress, NOT block
```
Counter-regime signals are demoted in score but **not removed**.

### 3. decider_run.py — max 30pt penalty, not a hard block
```python
penalty = min(int(_regime_conf * 0.4), 30)  # max 30 pt
effective_penalty = max(penalty - escalation, 0)
confidence -= effective_penalty
```
A base-conf=85 signal: 85 - 30 = **55** — still executable.

## Failure Scenario
1. T=0: LONG_BIAS regime → LONG signal (conf=88) enters hot-set, `reg_mult=1.5x`
2. T=2min: Regime flips to SHORT_BIAS
3. T=2min: Preservation pass — signal passes staleness (age=2min, staleness=0.6)
4. T=2-5min: Signal in hot-set, now counter-regime
5. T=4min: decider_run: 88 - 30 = 58. If MIN_EXEC_CONFIDENCE ≤ 58 → **executes LONG into SHORT_BIAS**

## Pitfall: DB Navigation
- `signals_hermes.db` — **NOT** the signals DB. Contains: price_history, latest_prices, regime_log, ohlcv_1m, _meta. No signals table.
- `signals_hermes_runtime.db` — correct signals DB (signals table with decision, combo_key, hot_cycle_count, survival_rounds)
- `candles.db` — candle data for all timeframes — used for regime regression
- PostgreSQL `brain.trades` — live open trades (token, direction, entry_price, created_at, regime=None for recent trades)

Query open trades:
```python
import psycopg2
conn = psycopg2.connect(host='/var/run/postgresql', database='brain', user='postgres', timeout=5)
cur = conn.cursor()
cur.execute("SELECT token, direction, entry_price, created_at::text FROM trades WHERE status='open'")
```

Query regime from candles.db (same logic as signal_compactor.get_regime_1m):
```python
import sqlite3, statistics
conn = sqlite3.connect('/root/.hermes/data/candles.db')
rows = conn.execute("SELECT close FROM candles_1m WHERE token=? ORDER BY ts DESC LIMIT 50", (token,)).fetchall()
closes = [r[0] for r in reversed(rows)]
# regression → LONG_BIAS/SHORT_BIAS/NEUTRAL
```

## Fix Direction
`_filter_safe_prev_hotset()` needs a regime alignment filter in signal_compactor.py:
```python
# After staleness check, before returning filtered.append():
regime, regime_conf = get_regime_1m(tok)
if regime_conf > 60:
    if (regime == 'SHORT_BIAS' and direction == 'LONG') or \
       (regime == 'LONG_BIAS' and direction == 'SHORT'):
        continue  # counter-regime — don't preserve
```

Also consider: add regime penalty to `_score_signal()` so counter-regime signals score below threshold entirely, not just survive by score margin.

## Key File References
| File | Lines | Role |
|------|-------|------|
| signal_compactor.py | 248-251 | staleness formula |
| signal_compactor.py | 253-266 | reg_mult scoring (not filter) |
| signal_compactor.py | 1396-1411 | preserve path — no regime check |
| signal_compactor.py | 113-151 | get_regime_1m() |
| decider_run.py | 1125-1174 | regime penalty (not block) |
| hl-sync-guardian.py | 1731-1910 | _check_stale_rotation — trade-level only, not signal-level |
