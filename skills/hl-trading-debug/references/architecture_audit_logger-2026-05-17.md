# Audit Trail System — architecture_audit_logger (2026-05-17)

## Why It Exists

When the ATOM phantom re-entry happened (2026-05-17), we could not determine:
- Whether the 09:36 position was ever in the DB
- Whether the DB INSERT actually failed or silently succeeded
- What sequence of events led to the combined -$0.1725 loss

The system had no audit trail. Every component (brain.py, position_manager, hl-sync-guardian) logged to different places with different formats and different field names. Correlating events required manually reading three log files simultaneously.

**The audit.log is the single source of truth for the full trade lifecycle.**

## Architecture

**File:** `/var/www/hermes/data/audit.log` — JSON-Lines, append-only, one JSON object per line.

**Module:** `/root/.hermes/scripts/audit_logger.py`

**Every function is idempotent and crash-safe** — any audit call failure is caught and swallowed so audit logging never blocks trading. This is intentional: a crash in audit would be catastrophic.

## Event Types

| Event | Source | When |
|-------|--------|------|
| `TRADE_OPEN_ATTEMPT` | brain.py add_trade() | Before any HL/DB call — logs token, direction, signal, entry_price, amount_usdt |
| `TRADE_OPEN_SUCCESS` | brain.py add_trade() | DB INSERT succeeds, HL confirmed — logs trade_id, hl_entry_price |
| `TRADE_OPEN_FAILED` | brain.py add_trade() | DB INSERT fails — logs reason, hl_position_left_open flag |
| `TRADE_CLOSE` | position_manager + guardian | On any close — logs entry_price, exit_price, pnl_usdt, pnl_pct, hype_realized, is_loss |
| `TRADE_ORPHAN_DETECTED` | hl-sync-guardian orphan guard | Guardian finds HL position with no DB record |
| `LOSS_COOLDOWN_SET` | position_manager + guardian | set_loss_cooldown() called — logs streak, hours, reason |

Every record carries: `ts` (ISO8601 UTC), `phase`, `run_id`, `pid`, `token`, `direction`

## Phase Context

`audit_logger.set_phase('pipeline'|'guardian'|'position_manager', run_id)` is called at the top of each script's main() to tag all subsequent events with the originating phase.

## Files Instrumented

| File | Events Added |
|------|-------------|
| `brain.py` | TRADE_OPEN_ATTEMPT (before HL/DB), TRADE_OPEN_SUCCESS (after INSERT), TRADE_OPEN_FAILED (rollback failed path) |
| `position_manager.py` | TRADE_CLOSE (close_paper_position), LOSS_COOLDOWN_SET (set_loss_cooldown) |
| `hl-sync-guardian.py` | TRADE_CLOSE (_close_paper_trade_db), TRADE_ORPHAN_DETECTED (orphan guard), LOSS_COOLDOWN_SET (_record_loss_cooldown) |

## Diagnostic Commands

```bash
# All ATOM events
grep '"ATOM"' /var/www/hermes/data/audit.log | python3 -c "
import sys, json
for line in sys.stdin:
    d = json.loads(line)
    print(f\"[{d['ts']}] [{d['event']}] loss={d.get('pnl_usdt','?')} cooldown={d.get('streak','?')}\")

# All loss cooldown events
grep 'LOSS_COOLDOWN_SET' /var/www/hermes/data/audit.log | python3 -c "
import sys, json
for line in sys.stdin:
    d = json.loads(line)
    print(f\"[{d['ts']}] {d['token']} {d['direction']} streak={d['streak']} hours={d['hours']} reason={d['reason']}\")

# All orphan detections
grep 'TRADE_ORPHAN_DETECTED' /var/www/hermes/data/audit.log

# All sentinel alerts (guard failures)
grep 'SENTINEL_ALERT' /var/www/hermes/data/audit.log

# Failed opens with HL position left open (critical)
grep 'TRADE_OPEN_FAILED' /var/www/hermes/data/audit.log | python3 -c "
import sys, json
for line in sys.stdin:
    d = json.loads(line)
    if d.get('hl_position_left_open'):
        print(f\"[{d['ts']}] ⚠️ {d['token']} {d['direction']} — HL POSITION LEFT OPEN\")
"
```

## Critical Pattern: Sentinel Must ACT Not Just Alert

During ATOM debug (2026-05-17), we found the sentinel in `close_paper_position()` detected `hype_realized_pnl_usdt < 0` but only printed an ALERT — never called `set_loss_cooldown()`. The cooldown was still missed.

**Rule:** Any sentinel that detects a guard failure must ALSO act to fix it. Alerting without acting is a half-measure that gives the appearance of detection without the protection.

This applies to:
- Loss detection sentinel in close_paper_position() — must call set_loss_cooldown()
- Orphan detection in guardian — must call _record_loss_cooldown()
- Corrupted data detected in _load_closing_markers() — must log + reset + alert

## Critical Pattern: Corrupted Data Silently Resets

`_load_closing_markers()` returned `data.get('tokens', {})` on whatever `json.load()` returned. If the file was written as a raw list `[]` instead of `{"tokens": {...}}`, the dict call on a list raises `'list' object has no attribute 'get'` — but the function catches this and returns `{}`, silently losing all closing markers.

**Rule:** Any JSON file load must validate the structure before returning it. At minimum:
```python
data = json.load(f)
if not isinstance(data, dict):
    log('CORRUPTED file — resetting', 'WARN')
    return {}
tokens = data.get('tokens', {})
if not isinstance(tokens, dict):
    log('CORRUPTED tokens — resetting', 'WARN')
    return {}
```

## Key Lesson: HL History is Ground Truth

When T says a position was open at time T and guardian logs say it wasn't:
1. Do NOT dismiss T's HL history as wrong
2. Exhaust every system explanation before disagreeing
3. If analysis doesn't fit T's data, update the analysis — don't defend the wrong answer

The ATOM case: initial analysis said "sub-60s position" but T said it was open for hours. We investigated further and found that the position existed on HL before the guardian started tracking it (guardian first_seen = 10:05:26), meaning the 09:36 position appeared and disappeared in the ~60s window between guardian sync cycles. The hours-long hold was real — it just wasn't visible to the guardian because it was brief and fell in the sync gap.

**HL history is ground truth. Always.**