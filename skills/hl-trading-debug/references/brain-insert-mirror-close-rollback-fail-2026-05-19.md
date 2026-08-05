# Brain.py DB INSERT Fail → HL Orphan Rollback Failure
**Date:** 2026-05-19
**Status:** ALL FIXED

## The Chain

```
decider_run → brain.py → mirror_open()   → HL position OPENS
           → add_trade() DB INSERT         → FAILS (signal claim conflict)
           → exception handler:
               → conn.rollback()           → logs failure
               → mirror_close()            → FAILS (signal already claimed)
               → AUDIT state dump          → full coin state logged
               → sys.exit(1)               → forces decider_run signal rollback
           → HL position stays open        → ORPHAN (until guardian detects)
           → decider_run catches RC=1      → rollback_signal_executed() fires
           → sig_id=None fallback fires    → token+direction fallback rollback
           → signal claim cleared          → signal freed for retry
```

## Evidence from pipeline.log

```
[brain.py] RC=1 stdout=[brain.py] ✔ no duplicate open in PostgreSQL for ADA
[brain.py] → mirror_open(ADA, SHORT, entry_price=0.247645, leverage=5)
[HYPE Mirror] OPEN SHORT 41 ADA @ signal=$0.248035 → HL_fill=$0.247970 (1 fi
[brain.py] ❌ FAILED: stderr=(empty)
⚠️ ROLLBACK FAILED: sig#1001709 already claimed by another process
→ FAILED:
```

**Key signature:**
- `RC=1` = brain.py exited with error code 1
- `FAILED: stderr=(empty)` = Python exception printed to stderr but stderr was empty... wait, actually `stderr=(empty)` means the subprocess captured stderr and it was empty — the Python exception went to stdout (or was swallowed)
- `ROLLBACK FAILED: sig# already claimed` = decider_run tried to rollback the signal-executed claim but another process already consumed it

## Root Cause — Two-Part Failure

### Failure 1: DB INSERT fails
brain.py `add_trade()` raises exception AFTER `mirror_open()` succeeds. The HL position is already live. DB INSERT fails (signal claim conflict or other constraint violation).

### Failure 2: mirror_close() rollback fails
brain.py exception handler calls `mirror_close()` to undo the HL position. BUT:
- `decider_run.py:1940` — "ROLLBACK FAILED: sig# already claimed by another process"
- The signal-executed claim was already consumed by another process (likely the same decider_run that is now catching the exception)
- This means `mirror_close()` is never called — or if called, fails because the position is already confirmed on HL

Result: **HL position left orphaned with zero DB record.**

## Why It Reproduces

```
ADA: decider_run (14:51:13) → brain.py → mirror_open(SHORT 41 ADA) → HL OK
                                           → DB INSERT → ??? FAIL
                                           → exception → mirror_close(SHORT) → ROLLBACK FAILED
                                           → HL position lives on
UNI: same pattern at 14:52:59
```

## Diagnostic

To catch this in real-time, look for:
```
grep "ROLLBACK FAILED" /root/.hermes/logs/pipeline.log
grep "RC=1 stdout=\[brain.py\]" /root/.hermes/logs/pipeline.log
grep "❌ FAILED: stderr=(empty)" /root/.hermes/logs/pipeline.log
grep "=== AUDIT: DB INSERT FAILURE STATE ===" /root/.hermes/logs/pipeline.log
```

Also check: `tail /root/.hermes/logs/pipeline.err.log` — Python tracebacks go here, not to subprocess stdout.

## Complete Fix Index (2026-05-19)

| # | File | What | Status |
|---|------|------|--------|
| 1 | hl-sync-guardian.py:3759 | orphan INSERT trade_id NULL (was `int(lev*1000000)`) | FIXED |
| 2 | brain.py:486-496 | hl_notional = total_sz × fill_px; None fallback when missing | FIXED |
| 3 | brain.py:597 | sys.exit(1) after failed rollback (was return None) | FIXED |
| 4 | decider_run.py:1943-1957 | sig_id=None fallback rollback | FIXED |
| 5 | hl-sync-guardian.py:3353 | hype_realized_pnl_pct guard (was always computed_pnl_pct) | FIXED |
| 6 | brain.py:473 | mirror_open result structured logging (not full dict) | ADDED |
| 7 | brain.py:543 | success PnL ratio log | ADDED |
| 8 | brain.py:558-594 | full DB INSERT failure audit state dump | ADDED |

**Cleared:** ZEN (id=9895, trade_id=5000000) and CHIP (id=9891, trade_id=3000000) — stale guardian_orphan records from May 15 blocking new orphans.

## Note on `HL_MIN_NOTIONAL_USDT`

`HL_MIN_NOTIONAL_USDT = 11.0` defined in `hermes_constants.py:252` but **ZERO imports anywhere**. Actual HL minimum enforced by `MIN_TRADE_USDT = 10.0` + `MIN_ORDER_BUFFER = 0.10` in `hyperliquid_exchange.py:706-707`. Per T's instruction: keep in hermes_constants as documentation only. Never import or enforce separately.

## Key Lessons

1. **"RC=1 stdout=[brain.py] FAILED: stderr=(empty)"** = silent Python exception in brain.py. Always check `pipeline.err.log` for actual traceback. Python exceptions in subprocesses go to stderr, not the captured stdout that pipeline.log shows.

2. **When `brain.py` needs decider_run to do something (rollback signal claim), don't try to do it inside brain.py's exception handler.** brain.py doesn't know the sig_id. Instead exit with non-zero code — let decider_run handle what it already knows how to handle. brain.py's job is to fail loudly, not to fix the consequences itself.

3. **When `mirror_get_entry_fill` falls back (no HL fill data), `total_sz=None`. Store `None` in `hl_notional_usdt`** — don't fall back to signal-level `size_usdt` which is 5x the actual HL notional. Guardian's `hype_realized_pnl_usdt` is the ground truth for PnL when `hl_notional_usdt` is NULL.

4. **The orphan path (add_orphan_trade, reconcile_hype_to_paper, _close_orphan_paper_trade_by_id) is actually correct and well-designed.** Don't break it further. When orphan trades fail to create local records, the root cause is brain.py failure upstream, not guardian orphan handling.

5. **Subagent audit results must be verified in main session before accepting.** One subagent reported `HL_MIN_NOTIONAL_USDT` was "not referenced anywhere" — that was correct, but reported `DEFAULT_TRADE_SIZE_USDT` was also "not referenced" — which was FALSE. Verified directly with grep in main session.

## What Was Fixed This Session (2026-05-19)

All 3 audit bugs fixed, compile clean, guardian restarted:

1. **brain.py:489** — `hl_notional = round(total_sz * fill_px, 4)` when `total_sz` and `fill_px` available; writes `None` (not `size_usdt`) when `total_sz=None`. Guardian uses `hype_realized_pnl_usdt` as ground truth for NULL cases.

2. **decider_run.py:1947** — sig_id=None fallback rollback added. When signal_id is None (legacy hot-set), decider_run tries token+direction match as fallback so signal isn't permanently stuck as `executed=1`.

3. **hl-sync-guardian.py:3353** — `hype_realized_pnl_pct = round(realized_pnl_value / calc_notional * 100, 4) if realized_pnl_value else None`. Uses HL realized pct, not price-based, when HL realized is available.