# accel-300 Debug Findings — ME, ASTER, Instant Close Investigation (2026-05-14)

## Summary

User investigated ME SHORT and ASTER LONG positions that seemed to close instantly. The work yielded:

1. **Condition 2 signed-gap bug** — `abs(gap_now)` stripped sign from gap, allowing SHORT to fire on coins ABOVE EMA
2. **Stale signal bug** — `detect_accel_300` returned at first valid historical bar without re-checking current bar state
3. **Close reason taxonomy** — `atr_sl_hit` = position_manager, `guardian_sl` = guardian self-close, `HL_SL_CLOSED` = HL native SL
4. **3-way close reason field** — `close_reason`, `exit_reason`, and `guardian_closed` boolean distinguish which system closed a trade

---

## Bug 1: Condition 2 Signed-Gap Bug

**File:** `/root/.hermes/scripts/signals/accel_300.py`, line ~225

**Symptom:** SHORT signals firing on coins ABOVE EMA (catching falling knives). For CHIP at bar 374, `gap_now=+0.25%` (ABOVE EMA), but `abs(0.25) = 0.25 >= 0.20` → passed. SHORT fired on wrong direction.

**Root cause:** `abs(gap_now) < min_gap` made the comparison direction-agnostic. For SHORT, a positive gap (above EMA) would pass since `abs(+0.25) = 0.25`. For LONG, the same bug made it reject small negative gaps.

**Fix:** Direction-specific signed comparisons:
```python
# BEFORE (BUG — direction-agnostic abs)
if abs(gap_now) < min_gap:
    return None

# AFTER (direction-specific signed)
if direction == 'LONG':
    if gap_now < min_gap:   # negative or too-small positive gap
        return None
elif direction == 'SHORT':
    if gap_now > -min_gap:   # positive gap (above EMA = not SHORT-eligible)
        return None
```

---

## Bug 2: Stale Signal — No Current-Bar Recheck

**File:** `/root/.hermes/scripts/signals/accel_300.py`, FINAL_VERIFY block

**Symptom:** COMP SHORT returned a signal at bar 361, but the current bar (708) was above EMA. Signal was stale by ~347 bars.

**Root cause:** `detect_accel_300` loops backward from `n-2` and returns immediately when it finds a valid crossing bar. It never re-verifies the current bar state after the loop completes.

**Fix:** Added FINAL_VERIFY block before return:
```python
# Re-verify current bar state (prevents stale signals from returning)
if current_bar_idx >= 2:
    cur_gap = (closes[current_bar_idx] - ema300[current_bar_idx]) / ema300[current_bar_idx] * 100
    cur_direction = 'LONG' if cur_gap > 0 else 'SHORT'
    if cur_direction != direction:
        return None  # market flipped since signal bar — reject
    if direction == 'LONG' and cur_gap < MIN_GAP_PCT_LONG:
        return None
    if direction == 'SHORT' and cur_gap > -MIN_GAP_PCT_SHORT:
        return None
```

Also added regime filter (linear regression on last 50 closes):
```python
import statistics, sqlite3
# ... after FINAL_VERIFY, before return ...
if len(recent_closes) >= 10:
    try:
        n = len(recent_closes)
        mean_x = sum(range(n)) / n
        mean_y = sum(recent_closes) / n
        cov = sum((i - mean_x) * (recent_closes[i] - mean_y) for i in range(n)) / n
        var = sum((i - mean_x) ** 2 for i in range(n)) / n
        slope = cov / var if var != 0 else 0
        if slope < 0 and direction == 'LONG':
            return None
        if slope > 0 and direction == 'SHORT':
            return None
    except:
        pass  # best-effort — errors pass through
```

---

## Close Reason Taxonomy

When debugging why positions close, THREE fields distinguish the closer:

| `close_reason` | `exit_reason` | `guardian_closed` | Who closed it |
|----------------|---------------|-----------------|---------------|
| `atr_sl_hit` | `atr_sl_hit` | `f` | position_manager — SL hit on ATR-based stop |
| `atr_tp_hit` | `atr_tp_hit` | `f` | position_manager — TP hit on ATR-based target |
| `guardian_sl` | `guardian_sl` | `t` | guardian — HL self-close SL breach |
| `guardian_tp` | `guardian_tp` | `t` | guardian — HL self-close TP breach |
| `HL_SL_CLOSED` | `HL_SL_CLOSED` | `t` | Hyperliquid native SL |
| `profit-monster` | `profit-monster` | `f` | position_manager — trailing TP hit |
| `cascade_flip` | `cascade_flip` | `f` | cascade_flip system |

### Key diagnostic query
```sql
SELECT token, direction, entry_price, stop_loss, exit_price, pnl_pct,
       open_time, close_time,
       EXTRACT(EPOCH FROM (close_time - open_time)) as dur_sec,
       close_reason, guardian_closed, highest_price, lowest_price
FROM trades
WHERE open_time >= '2026-05-14'
ORDER BY open_time;
```

### What ME's 3.1s close actually means

ME SHORT: `close_reason=atr_sl_hit`, `guardian_closed=f` — **position_manager closed it**, not guardian. The `lowest_price=0.1` confirms price went well below the SL of 0.1007 — the SL genuinely fired. This is NOT an orphan or bug — it's a legitimate short-term loss.

The real question for ME SHORT: why did price immediately move against the position within 3 seconds? Either:
1. Entry timing was bad (chose the exact top)
2. Signal was stale when emitted
3. Price data delay between signal generation and execution

---

## PostgreSQL vs brain.db

On this system, use `psql -U postgres -d brain` (NOT `hermes` — that DB doesn't exist).

```bash
psql -U postgres -d brain -c "SELECT table_name FROM information_schema.tables WHERE table_schema='public';"
# Key tables: trades, loss_cooldowns, signal_cooldowns, tpsl_self_close, hyperliquid_trades

# Get recent trades
psql -U postgres -d brain -c "
SELECT token, direction, entry_price, exit_price, pnl_pct, stop_loss,
       open_time, close_time,
       EXTRACT(EPOCH FROM (close_time - open_time)) as dur_sec,
       close_reason, guardian_closed, highest_price, lowest_price
FROM trades
WHERE open_time >= '2026-05-14'
ORDER BY open_time;
"

# Check tpsl_self_close for guardian self-close records
psql -U postgres -d brain -c "SELECT * FROM tpsl_self_close ORDER BY updated_at DESC LIMIT 10;"

# Check loss_cooldowns
psql -U postgres -d brain -c "SELECT * FROM loss_cooldowns ORDER BY expires DESC LIMIT 20;"
```

---

## Other Bugs Fixed in This Session

| Bug | Location | Fix |
|-----|----------|-----|
| PERSISTENCE_BARS=2 hardcoded | accel_300.py line 67 | Imported `ACCEL_300_PERSISTENCE_BARS=3` from hermes_constants |
| gap_at_cross return guard | accel_300.py line ~260 | Fixed: `round(gap_at_cross, 4) if gap_at_cross is not None else None` |
| gap_bonus threshold 0.05 | accel_300.py | Changed to `MIN_GAP_GROWTH_PCT` (0.03) for consistency |
| gap_then-gapspeed confusion | accel_300.py | SHORT: `gap_then - gap_now` (positive = accelerating downward) |
| Stale comment | accel_300.py | Updated "MIN_GAP_PCT" → "MIN_GAP_PCT_LONG / MIN_GAP_PCT_SHORT" |

---

## accel-300 Signal Flow for Investigation

When debugging a signal, trace through these files:

1. **Signal emit** → `accel_300.py` `detect_accel_300()` — check FINAL_VERIFY, gap sign, regime filter
2. **DB write** → `signal_schema.py` `add_signal()` — confirms written to signals_hermes_runtime.db
3. **Compaction** → `signal_compactor.py` — routes to hot-set, checks cooldowns
4. **Execution** → `decider_run.py` — converts hot-set entry to HL order
5. **Position open** → `brain.py` `add_trade()` + `mirror_open()` — creates brain.trades record
6. **Monitoring** → `position_manager.py` `check_atr_tp_sl_hits()` — watches for SL/TP hits (not called from signal_compactor — runs independently)
7. **Guardian backup** → `hl-sync-guardian.py` `check_self_close()` — secondary SL/TP monitor for UNPROTECTABLE_COINS

The separation between position_manager (primary SL/TP monitor) and guardian (backup self-close) is key — they operate independently.