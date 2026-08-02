# Plan: Fix DB/HL Sync — Stop ai-decider.timer Pollution

## Bug Summary

The `signals_hermes_runtime.db` (SQLite) and Hyperliquid are out of sync because `ai_decider.py`
is still running via systemd timer, creating phantom SKIPPED entries that corrupt the signal lifecycle.

---

## ROOT CAUSE

**`ai-decider.timer`** — systemd timer that fires every 10 minutes and runs `ai_decider.py`.

`ai_decider.py` contains `update_open_positions_skipped()` (line ~1037) which:
1. Queries **PostgreSQL** `brain.trades` for open positions per server
2. For every token with an open position → `UPDATE signals SET executed=1, decision='SKIPPED'`
3. Does **NOT** increment `compact_rounds`
4. Runs every 10 minutes, creating duplicate SKIPPED entries

This races against:
- `signal_compactor` (every 5 min via pipeline) — approves new signals
- `decider_run` (every 1 min via pipeline) — tries to execute APPROVED signals

**Evidence:**
- 26 SUI LONG SKIPPED entries (one per 10-min ai_decider run since 20:30)
- 4 each of VINE/MOODENG/STX SKIPPED entries
- `ai-decider.timer` confirmed active in `systemctl list-timers`
- Pipeline log shows "ai_decider] Token budget exceeded" entries interleaved with signal_compactor

---

## Current State

| Source | Count |
|--------|-------|
| SKIPPED (phantom, from ai_decider) | 38 |
| EXECUTED (real trades) | 8 |
| APPROVED (live signal_compactor) | 17 |
| PENDING | 10 |

HL actual positions: BTC, ETH, LTC, ME, SUI, TON, PENDLE, ASTER, SEI (9 in brain.trades + SEI in HL but not brain → phantom)

---

## Files Changed by This Fix

### 1. `/etc/systemd/system/ai-decider.timer` — DISABLE
```
systemctl stop ai-decider.timer
systemctl disable ai-decider.timer
```
**Done** — timer stopped at 21:05 UTC.

### 2. `/etc/systemd/system/ai-decider.service` — DISABLE
```
systemctl stop ai-decider.service
systemctl disable ai-decider.service
```

### 3. `signals_hermes_runtime.db` — CLEANUP

Archive then delete phantom SKIPPED entries:
```sql
-- Archive before delete
CREATE TABLE signals_archive_20260416_210600 AS
SELECT * FROM signals WHERE decision = 'SKIPPED';

-- Delete all SKIPPED (phantom pollution from ai_decider)
DELETE FROM signals WHERE decision = 'SKIPPED';
```

Verify EXECUTED entries are real (HBAR, SUI from pattern_micro_flag) — keep those.

### 4. `signal_compactor.py` — ALREADY DONE
- Created as standalone deterministic compactor (replaces `_do_compaction_llm`)
- Runs every 5 min via `run_pipeline.py` `STEPS_EVERY_5M`
- Sole approval authority — writes `decision='APPROVED'` only
- DB fallback for speed data fixed (uses `token_speeds` table when `speed_cache.json` missing)

### 5. `decider_run.py` — ALREADY DONE
- `_run_hot_set()` patched to READ-ONLY (returns 0, no APPROVED writes)
- Removed orphaned `try:` block that was causing `executed=1` with wrong decision values

---

## Verification Steps

1. **Timer stopped**: `systemctl status ai-decider.timer` → inactive
2. **No ai_decider runs**: `grep "ai_decider" logs/pipeline.log | tail -5` → only signal_compactor
3. **SKIPPED cleaned**: `SELECT COUNT(*) FROM signals WHERE decision='SKIPPED'` → 0
4. **EXECUTED preserved**: `SELECT * FROM signals WHERE decision='EXECUTED'` → 8 real trades
5. **APPROVED signals**: `signal_compactor` will regenerate clean APPROVED on next 5-min tick
6. **HL sync**: `hl-sync-guardian` properly records closes to `signal_outcomes`
7. **Brain trades match HL**: Compare `brain.trades` open vs `get_open_hype_positions_curl()`

---

## Secondary Issues Found (Not Primary Bug)

### guardian-closed-set.json empty
`guardian-closed-set.json` is `[]` — guardian thinks nothing was ever closed.
This prevents proper "already closed" detection. Investigate `sync_pnl_from_hype()` and `_record_trade_outcome()`.

### SEI phantom position
HL has SEI SHORT but brain.trades has no SEI entry.
Should be in brain.trades but is missing — `mirror_open` may have failed.

### ENS in signal_outcomes vs EXECUTED
ENS appears as LOSS at 14:42 in `signal_outcomes` but also as EXECUTED at 20:44.
These are different trade cycles — not a bug, just ENS reopened after loss.

---

## Risk / Tradeoffs

- **Risk**: Disabling ai-decider.timer means `ai_decider.py` never runs → hot-set compaction
  relies 100% on `signal_compactor.py`. Currently verified working.
- **Mitigation**: Monitor pipeline log for `signal_compactor` entries every 5 min.
- **Cleanup**: SKIPPED entries when deleted are archived to `signals_archive_20260416_210600`.
- **No data loss**: All real EXECUTED trades are preserved. APPROVED will regenerate.

---

## Open Questions

1. Should `ai_decider.py` be deleted entirely or kept as reference?
2. Should `signal_compactor` also handle the `update_open_positions_skipped` logic
   (skip tokens with open positions in brain.trades)?
3. Why does `guardian-closed-set.json` stay empty — does guardian ever write to it?
4. SEI phantom — should `hl-sync-guardian` auto-reconcile HL positions not in brain.trades?
