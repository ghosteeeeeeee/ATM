# Loss Cooldown Missed — ATOM Phantom Re-Entry (2026-05-17)

**Situation:** ATOM SHORT opened on HL at 09:36:07 (entry=2.0716), closed at 10:04:58 (exit=2.1042, loss=-$0.16). No DB record. No cooldown. Pipeline immediately fired another ATOM SHORT at 10:05:26 (entry=2.1051), closed at 10:07:05 (loss=-$0.02). Only the second trade recorded in DB.

**Combined HL loss:** `hype_realized_pnl_usdt = -0.1725` on DB id=10077 — HL calculated both closes as a single realized loss.

---

## Root Cause (Definitive — from Guardian Logs)

Guardian checked HL every 60 seconds from 09:30 through 10:04:
```
09:36:19  HL:5, DB:5 — ATOM NOT on HL, NOT in DB
09:37-10:04  Every sync: HL:5, DB:5 — ATOM never present
10:04:23  HL:5, DB:5 — ATOM still not present
10:04:24-10:05:24  [~60s window: position briefly appears on HL and closes]
10:05:24  HL:4, DB:5 — ATOM gone from HL, still in DB as "Missing"
10:05:26  Guardian LIVE-MISS handler opens new SHORT at 2.1051 (id=10077)
```

**The 09:36:07 timestamp in the user's HL history is NOT in any guardian log.** The position never existed in the system's view at 09:36. The guardian `first_seen` for ATOM in `guardian-missing-tracking.json` is `10:05:26` — this is when the guardian first detected ATOM as a missing position.

**What happened:** A phantom DB record (from an earlier signal_compactor signal that was never properly executed on HL) combined with a brief HL position that appeared and disappeared between two guardian sync cycles (~60 second window). When guardian saw "DB says open, HL says closed", it treated this as a LIVE-MISS and opened a new position, marking the phantom record as "executed." This created a new position that had no connection to the original 09:36 trade the user saw.

The `guardian-closing-markers.json` cross-check added to `signal_compactor._get_open_tokens()` is the fix: tokens in closing markers are now treated as "open" even if PostgreSQL has a phantom record, preventing the LIVE-MISS handler from creating spurious new trades.

---

## Three Bugs Found

### Bug 1 — `close_paper_position()`: reason string has no %, is_loss never fires

`close_paper_position()` at line ~930:
- Calls with `reason='atr_sl_hit'` (no PnL% pattern)
- Regex `re.search(r'([+-]\d+\.\d+)%', reason)` finds nothing
- `pnl_usdt_val` stays 0 → `is_loss = (0 < 0) = False`
- `set_loss_cooldown()` never called
- `hype_realized_pnl_usdt = -0.1725` proves real HL loss existed but was invisible to cooldown logic

**Fix A (applied):** Added DB fallback after regex block — when reason has no PnL%, query `hype_realized_pnl_usdt` from the trade row and use it to set `pnl_usdt_val`.

**Fix E (applied):** Sentinel in `else` branch: when `is_loss=False` but `hype_realized_pnl_usdt < 0`, print alert so the missed cooldown is visible in logs.

### Bug 2 — STALE_ROTATION path: no `_record_loss_cooldown` call

`hl-sync-guardian._check_stale_rotation()` line ~1938: direct DB UPDATE, no cooldown call. HARD-SL and CUT_LOSER both had it, STALE_ROTATION didn't.

**Fix B (applied):** Added `_record_loss_cooldown(token, direction_upper)` inside `if pnl_pct < 0:` after the STALE_ROTATION UPDATE.

### Bug 3 (Critical) — Pipeline gap: phantom DB record + brief HL position

`signal_compactor._get_open_tokens()` only checked PostgreSQL. A phantom record in PostgreSQL (signal consumed but never executed on HL) caused `guardian-closing-markers.json` to be added as a secondary authority.

**Fix F (applied):** `_get_open_tokens()` now cross-checks `guardian-closing-markers.json` — tokens in closing markers are treated as "open" even if PostgreSQL has no record.

---

## Fixes Applied (Summary)

| Fix | File | Lines | What |
|-----|------|--------|------|
| A | position_manager.py | ~940-958 | DB fallback to `hype_realized_pnl_usdt` when reason has no % |
| B | hl-sync-guardian.py | ~1953-1958 | STALE_ROTATION `_record_loss_cooldown` call |
| C | position_manager.py | ~966-978 | Sentinel alert for hidden loss when is_loss=False |
| D | position_manager.py + guardian | ~2814-2818, ~262-264 | Verify-after-write in set_loss_cooldown |
| E | position_manager.py | ~959-964 | Debug trace before/after set_loss_cooldown |
| F | signal_compactor.py | ~76-120 | `_get_open_tokens()` checks guardian-closing-markers.json |

---

## Debug Traces to Look For

When a loss cooldown is missed, grep for these in the logs:

```
[Position Manager] close_paper_position trade_id=X reason='atr_sl_hit' pnl_usdt_val=0.0 is_loss=False
[Position Manager] ⚠️  ALERT: is_loss=False but hype_realized_pnl_usdt=-X < 0 — cooldown may be missed!
[Guardian] ⚠️  ALERT: final_pnl_usdt=0 but hype_pnl_usdt=-X < 0 — cooldown may be missed!
[Guardian] _record_loss_cooldown(ATOM, SHORT): entry before write = {'expires': ..., 'reason': 'loss'}
[Position Manager] DEBUG: loss_cooldowns.json verify after write = {'expires': ..., 'reason': 'loss'}
```

---

## Diagnostic Commands

```bash
# Check loss_cooldowns for a token
cat /root/.hermes/data/loss_cooldowns.json | python3 -m json.tool | grep -A5 -B1 ATOM

# Find trades with hidden loss (hype_realized < 0 but pnl_usdt >= 0)
psql -h 10.60.68.154 -p 5432 -U postgres -d brain -c \
  "SELECT id, token, pnl_usdt, hype_realized_pnl_usdt, close_reason FROM trades \
   WHERE hype_realized_pnl_usdt < 0 AND pnl_usdt >= 0 AND close_time >= NOW() - INTERVAL '7 days';"

# Check guardian orphan tracking
cat /root/.hermes/data/guardian-missing-tracking.json
cat /root/.hermes/data/guardian-closing-markers.json
```

---

## Architecture Notes

**Cooldown write path:** Both `position_manager.set_loss_cooldown()` (reason='loss') and `hl-sync-guardian._record_loss_cooldown()` (reason='guardian') write to the SAME `loss_cooldowns.json` file. Guardian skips if pipeline already wrote (reason='loss'). Pipeline uses `_load_cooldowns()` + `_save_cooldowns()` via FileLock.

**Guardian orphan close path (lines 3636-3678):** When no DB record exists for an orphan HL position, guardian inserts a minimal `guardian_orphan` record, then calls `_close_orphan_paper_trade_by_id()`. This path has `_record_loss_cooldown()` and `_save_closing_marker()` — closing marker cleared only if `close_ok` (DB update succeeded).