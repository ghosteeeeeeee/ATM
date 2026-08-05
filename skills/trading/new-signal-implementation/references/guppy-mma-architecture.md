# Guppy MMA — Standalone Signal Architecture (PATH C)

Created: 2026-05-04
Status: Plan complete, not yet built

## Architecture Decision

**PATH C selected** — guppy MMA is fully standalone (pump_hunter pattern).

**Why guppy cannot use hot-set (PATH A):**
- Guardian manages ATR TP/SL exits for hot-set positions
- Guppy wants fast-group-flip exit: price closes below fast group low = exit
- Two independent exit systems would fight over the same position
- Guardian's `mirror_close` + live HL TP/SL orders = ghost orders, double-close risk
- Single-source signals blocked at hot-set compaction (conf-1s rule)

**Pattern confirmed:** pump_hunter, zscore_pump, atr_compression_signals are all standalone for the same reason.

---

## Three-Layer Kill Switch Design

| Switch | Location | Controls |
|--------|----------|----------|
| `LIVE_TRADING_ENABLED` | hermes_constants.py | Guardian + ALL `mirror_*` calls globally |
| `GUPPY_LIVE` env var | run_guppy_signals.py + hyperliquid_exchange.py | Only guppy's mirror_open/mirror_close |
| `GUPPY_ENABLED` | hermes_constants.py | Guppy scanner + signal generation |

**Key behavior:**
- `GUPPY_LIVE=1` + `LIVE_TRADING_ENABLED=False` → guppy places real trades (others blocked)
- `GUPPY_LIVE=0`/unset → guppy dry-runs
- `GUPPY_ENABLED=False` → scanner doesn't run at all

**Implementation in hyperliquid_exchange.py:**
```python
# In mirror_open() and mirror_close():
if not is_live_trading_enabled():
    if os.environ.get('GUPPY_LIVE', '').lower() in ('1', 'true', 'yes'):
        pass  # bypass global kill for guppy
    else:
        return {"success": False, "message": "Live trading disabled"}
```

---

## Guardian Integration — CRITICAL

Guardian has TWO separate exclusion lists. Both MUST be updated:

### 1. position_manager.py (4 places)
```python
AND (signal IS NULL OR signal NOT IN ('pump_hunter', 'zscore_pump', 'guppy'))
```

### 2. hl-sync-guardian.py (3+ places)
```python
# Lines ~607, ~634, ~1054:
signal NOT IN ('pump_hunter')  →  signal NOT IN ('pump_hunter', 'guppy')
```

### ⚠️ Pre-existing Bug
`position_manager.py` excludes BOTH `pump_hunter` AND `zscore_pump`.
`hl-sync-guardian.py` excludes ONLY `pump_hunter` — `zscore_pump` is NOT excluded.

This means zscore_pump positions could trigger guardian orphan handling. When adding guppy, also fix zscore_pump in guardian for consistency.

### How Guardian Skips Standalone Positions

Guardian hard-stop query:
```sql
WHERE status='open' AND exchange='Hyperliquid'
  AND stop_loss IS NOT NULL AND stop_loss > 0
  AND (atr_managed IS NULL OR atr_managed = FALSE)
```

Standalone signals: `signal='guppy'`, `atr_managed=FALSE` (default), `stop_loss=NULL` (never set).
Since `stop_loss IS NOT NULL` is FALSE, guardian never evaluates these positions.

---

## Exit Logic: Fast-Group-Flip

Guppy's exit is the REVERSE of its entry signal:
- LONG entry: fast group crosses above slow group
- LONG exit: price closes below fast group low point
- SHORT entry: fast group crosses below slow group
- SHORT exit: price closes above fast group high point

NOT guardian's ATR system. Standalone signal reads local `candles_1m` SQLite DB for price data — no HL API calls for price.

---

## Guppy EMA Groups

```
FAST_GROUP = [3, 5, 8, 10, 12, 15]
SLOW_GROUP = [30, 35, 40, 45, 50, 60]
```

- Squeeze: fast group within 0.3% of slow group
- Entry: fast group crosses slow group (LONG = above, SHORT = below)
- Squeeze breakout confirmation: whichever group breaks first determines direction
- Min separation: fast group 0.5% away from slow at entry

---

## Signal Naming

| | LONG | SHORT |
|---|---|---|
| Signal type | `guppy_long` | `guppy_short` |
| Source tag | `guppy+` | `guppy-` |
| brain DB signal | `guppy` | `guppy` |
| Exit reason | `guppy_fast_flip` | `guppy_fast_flip` |

---

## Files to Create

| File | Purpose |
|------|---------|
| `/root/.hermes/scripts/guppy_signals.py` | Pure detection engine, zero HL deps |
| `/root/.hermes/scripts/run_guppy_signals.py` | Runner: --scan/--monitor/--status/--close ALL |
| `/var/www/hermes/data/guppy_positions.json` | Position tracker (lives at HERMES_DATA) |
| `/var/www/hermes/guppy.html` | Dashboard (nginx served at /guppy) |
| `/root/.hermes/scripts/backtest_guppy.py` | Historical validation |
| `/etc/systemd/system/hermes-guppy.service` | oneshot service |
| `/etc/systemd/system/hermes-guppy.timer` | `OnCalendar=*:0/1` |

---

## Monitor Frequency — OPEN

Should `--monitor` run every 60s (same as --scan) or more frequently (15s)?
Guppy's fast-group flip exit is time-sensitive. Options:
1. Same timer as --scan (60s) — simpler
2. Separate 15s timer for --monitor — faster reaction but more complexity
3. Embed exit check in --scan run (bar-by-bar check of current price)

---

## Brain DB Integration

On position open (mirrors pump_hunter):
```python
def _create_brain_record(token, direction, signal_dict, size, entry_price):
    cur.execute("""
        INSERT INTO trades (..., signal, ...)
        SELECT ..., 'guppy', ...
        WHERE NOT EXISTS (
            SELECT 1 FROM trades WHERE token=%s AND server='Hermes' AND status='open'
        )
        RETURNING id
    """, (...))
```

On position close:
```python
def _close_brain_record(token, reason, pnl_pct):
    cur.execute("""
        UPDATE trades SET status='closed', close_time=NOW(),
            exit_price=%s, pnl_pct=%s, close_reason=%s
        WHERE token=%s AND server='Hermes' AND status='open' AND signal='guppy'
    """, (...))
```

---

## Key Files for Reference

- `/root/.hermes/scripts/pump_hunter.py` — pure standalone, tracker JSON, no brain DB
- `/root/.hermes/scripts/zscore_pump_hunter.py` — standalone but writes to brain DB
- `/root/.hermes/scripts/hyperliquid_exchange.py` — mirror_open/mirror_close (needs GUPPY_LIVE bypass)
- `/root/.hermes/scripts/position_manager.py` — exclusion list (needs 'guppy' + fix 'zscore_pump')
- `/root/.hermes/scripts/hl-sync-guardian.py` — orphan recovery (needs 'guppy' + fix 'zscore_pump')
