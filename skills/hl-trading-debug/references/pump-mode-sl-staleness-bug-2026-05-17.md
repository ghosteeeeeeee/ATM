# Pump Mode SL/TP Staleness Bug — RESOLVED 2026-05-17

## Root Cause

Two compounding issues:

1. **`position_manager.py` exclusion filter was wrong** — `get_open_positions()`, `get_position_count()`, and `is_position_open()` all had `signal NOT IN ('pump_hunter', 'zscore_pump')` — blocking BOTH `pump_hunter` AND `zscore_pump` signals from ATR management. Only `pump_hunter` (standalone executor) should have been excluded.

2. **`decider_run.py` writes pump-mode fallback SL/TP on entry** — For `zscore-pump` signals, decider_run uses hardcoded 1.5%/2.5% SL/TP (from `signal_gen.PUMP_SL_PCT/PUMP_TP_PCT`) written to brain DB. PM was supposed to override within 1 cycle, but the exclusion filter prevented PM from ever seeing these trades.

## Fix Applied (2026-05-17)

**`position_manager.py` exclusion filter** — removed `zscore_pump` from 3 locations:
- `get_open_positions()` line 258: `('pump_hunter', 'zscore_pump')` → `('pump_hunter')`
- `get_position_count()` line 282: `('pump_hunter', 'zscore_pump')` → `('pump_hunter')`
- `is_position_open()` line 306: `('pump_hunter', 'zscore_pump')` → `('pump_hunter')`

Filter now reads: `AND (signal IS NULL OR signal NOT IN ('pump_hunter'))` — only `pump_hunter` (standalone executor with its own HL order placement) is excluded from PM ATR management.

**Docstrings corrected** — all 3 functions had stale docstrings saying "excludes pump_hunter and zscore_pump" — corrected to "excludes pump_hunter signal only".

**DB reset for stale trades** — trades that had been running with stale SL/TP needed their `stop_loss/target` zeroed so PM could write fresh ATR values without trailing gate interference:
```sql
UPDATE trades SET stop_loss=0, target=0, atr_managed=FALSE
WHERE token IN ('AVAX','MON') AND status='open';
```

## Key Findings

### Initial SL/TP source is correct
`decider_run.py` → `brain.py add_trade()` → PostgreSQL `trades` table. Decider_run pump-mode writes 1.5%/2.5% SL/TP as fallback. PM overrides within 1 cycle. **This is the designed behavior, not a bug.** New `zscore-pump` trades will ALWAYS have `atr_managed=FALSE` on entry — PM picks them up on the next cycle.

### `trades.json` is a read-only display layer
`update-trades-json.py` reads from PostgreSQL and writes `trades.json`. If `trades.json` shows wrong SL/TP, the bug is in the DB write path (PM or brain.py), never in the JSON sync. Always check PostgreSQL first:
```bash
psql -h /var/run/postgresql -U postgres -d brain -c \
  "SELECT token, direction, stop_loss, target, atr_managed, signal, open_time \
   FROM trades WHERE status='open' ORDER BY open_time;"
```

### Trailing gate behavior
`tpsl_utils.compute_atr_sl_tp()` trailing gate: SHORT new_sl must be `< current_sl` (tighten), LONG new_sl must be `> current_sl` (tighten). If a stale SL is already tighter than the new ATR value, the trailing gate blocks the update — PM can't fix stale values without the DB reset above.

Reset to 0 → PM writes fresh ATR values → trailing gate activates normally from that point.

### `signals/zscore_pump.py` is signal-only
Not a standalone executor. Feeds pipeline via `signal_compactor` → `decider_run` → `brain.py`. Does NOT bypass PM ATR management. Left untouched.

### `pump_hunter.py` still active
`pump_hunter.py` is a separate standalone executor at `/root/.hermes/scripts/pump_hunter.py` with hardcoded SL=1.5%, TP=2.5%. PM correctly excludes its trades via the `pump_hunter` filter. Still active — user to decide if it should be removed.

## Verification

Current open positions (all ATR-managed):
```
token | direction | stop_loss  | target    | atr_managed | signal
------+----------+-----------+-----------+-------------+------------------
AVAX  | SHORT    | 9.28957500 | 9.13275000 | t           | rs-r202,rs-r63,zscore-pump-
MON   | SHORT    | 0.02805099 | 0.02757744 | t           | rs-r330,zscore-pump-
SNX   | LONG     | 0.31185165 | 0.31719050 | t           | rs-s35,zscore-pump+
XRP   | SHORT    | 1.42886600 | 1.37255600 | f           | rs-r303,zscore-pump-  ← PM next cycle
STBL  | SHORT    | 0.03238400 | 0.03110700 | f           | rs-r102,zscore-pump-  ← PM next cycle
```

STBL/XRP have `atr_managed=FALSE` — PM will compute and write ATR values on next cycle. No action needed unless immediate fix required (use the DB reset SQL above).