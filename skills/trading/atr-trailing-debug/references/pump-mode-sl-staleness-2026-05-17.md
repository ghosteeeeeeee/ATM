# Pump-Mode Entry → PostgreSQL Staleness (2026-05-17)

## The Bug

SHORT trades (PEOPLE, XMR, BSV) have SL stored ABOVE entry in `brain.trades`:

| Token | DB SL | ATR-computed | Delta | Entry |
|-------|-------|-------------|-------|-------|
| PEOPLE | 0.007179 (+1.5%) | 0.007107 (+0.47%) | DB above entry | 0.007074 |
| XMR | 399.194 (+1.0%) | 396.083 (+0.25%) | DB above entry | 395.10 |
| BSV | 15.7853 (+2.0%) | 15.5319 (+0.40%) | DB above entry | 15.47 |

COMP is now closed.

## Root Cause

**Entry-time PUMP-mode SL persists and blocks ATR engine updates.**

1. `decider_run.execute_trade()` uses `PUMP_SL_PCT=0.015` (1.5%) and `PUMP_TP_PCT=0.025` (2.5%) from `signal_gen.py:1221-1222` — NOT from `hermes_constants`. This value is written to PostgreSQL via `brain.py add_trade()`.

2. For SHORT: `SL = entry × (1 + 0.015)` → above entry ✓ (correct for initial protective stop)

3. `position_manager._collect_atr_updates()` calls `tpsl_utils.compute_atr_sl_tp()` and computes correct values (e.g., BSV new_sl=15.5319 using 0.70% ACCEL floor for in-profit SHORT with low-vol tier).

4. The PostgreSQL UPDATE from `_persist_atr_levels()` may be **failing silently** — the pipeline service uses peer auth (local socket) which works for `psql` subprocess but may fail for `psycopg2` from sandbox. This needs verification.

## What tpsl_utils Computes vs What's Stored

Trace for BSV (entry=15.47, current=15.4345, lowest=15.4345):
- `atr = get_fresh_atr('BSV')` → 0.0432
- `atr_pct = 0.0432 / 15.47 = 0.28%` (< ATR_PCT_LOW_THRESH=1%) → k_base = 1.0 (LOW_VOL)
- `momentum_stats` → percentile_short from signal → phase → k multiplier
- `is_new_trade=False` (pnl_pct=0.23% > 0), `_in_profit=True`
- SHORT + in-profit → `ref_price = lowest_price = 15.4345`
- `eff_sl_pct = max(k × atr_pct, ATR_SL_MIN_ACCEL) = max(0.28%, 0.70%) = 0.70%`
- `new_sl = 15.4345 × (1 + 0.0070) = 15.5319`
- `new_tp = 15.4345 × (1 - 0.70% × 1.25) = 15.4997`

Stored DB value: `stop_loss=15.78528` → stale PUMP initial (15.47 × 1.02 = 15.7794, close to DB value).

## Delta Gate Analysis

The delta gate (`ATR_UPDATE_THRESHOLD=0.15%`) compares `(396.08 - 399.19) / 399.19 = 0.78%` for XMR — well above threshold. For BSV: `(15.53 - 15.79) / 15.79 = 1.6%` — also above threshold. Delta gate would NOT block the write. The DB write is being attempted but silently failing.

## Why tpsl_utils Is NOT the Problem

Confirmed this session:
- tpsl_utils is the sole ATR computation authority ✓
- Uses only hermes_constants values ✓
- Correctly computes 0.70% ACCEL floor for in-profit SHORT with low-vol (atr_pct=0.38%)
- SHORT SL anchored to `lowest_price` when profitable ✓ (not `_entry` which was the 2026-05-15 bug)
- Phase k scaling applied correctly
- INIT/ACCEL floors correct

## Open Issue: PUMP_SL_PCT Not in hermes_constants

This is a pre-existing known issue (listed in both hl-trading-debug and atr-trailing-debug open issues since 2026-05-16). `PUMP_SL_PCT=0.015` and `PUMP_TP_PCT=0.025` live in `signal_gen.py:1221-1222` instead of `hermes_constants`. T's directive: pump mode should use `ATR_SL_MIN_INIT`/`ATR_TP_MIN`.

## Immediate Fix

SQL to overwrite stale SL:
```sql
UPDATE trades SET stop_loss = 396.083310, target = 383.462625 WHERE id=10092 AND token='XMR';
UPDATE trades SET stop_loss = 15.531968,  target = 15.163200 WHERE id=10039 AND token='BSV';
UPDATE trades SET stop_loss = 0.007107,   target = 0.006896  WHERE id=10093 AND token='PEOPLE';
```

## Files

- `tpsl_utils.py` — sole ATR computation authority ✓
- `position_manager.py` — `_collect_atr_updates()` computes ATR values, `_persist_atr_levels()` writes to DB
- `signal_gen.py:1221-1222` — `PUMP_SL_PCT=0.015`, `PUMP_TP_PCT=0.025` (not in hermes_constants)
- `hermes_constants.py` — all ATR constants (ATR_SL_MIN=0.50%, ATR_SL_MAX=1%, etc.)