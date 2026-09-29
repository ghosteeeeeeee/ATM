## Error Alerts — 2026-09-29 03:47 UTC

### CRITICAL (1)
- **CRITICAL** (continuous): `position_manager: FAILED` — `[FATAL] Guardian already running — exiting` every pipeline run. Root cause: race condition between position_manager step and hl-sync-guardian service. Position_manager exits rc=1 but guardian handles SL/TP updates and position closes. Non-functional but noisy. Fix: either remove position_manager from pipeline (guardian covers it) or add lock-check before TPSL computation.

### WARN (3)
- **WARN** (1): `hermes-coding-mcp.service` crash-looping (activating auto-restart). Needs investigation.
- **WARN** (1): 10 services in failed/dead state — 5m-candle, away-detector, better-coder, brain-auditor, bug-hunter, ceo, git-release, mtf-macd-tuner, trade-watchdog, trading-checklist.
- **WARN** (1): Hotset empty — no signals survived compaction. 67 signals generated but 0 passed confidence threshold.

### AUTO-FIXES APPLIED
- Cleaned /tmp/*.so (2.5GB node-compile-cache files >3 days old)
- Trimmed pipeline.log from 77MB to ~15MB (last 5000 lines)
- Compressed old log files (>3 days)
- Disk: 86% → 83% (3GB reclaimed)

## Error Alerts — 2026-09-29 05:58 UTC
- **REPEATED** (10x): `Sep N N:N:N python3[TOK]: TS   position_manager: TOK in N.2s (rc=N)`
- **REPEATED** (6x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING — BTC_LEVEL`
- **REPEATED** (5x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK level: -N.N% from high, +N.N% from low — blocking TOK entries`
- **NEW** (1x): `Sep N N:N:N python3[TOK]: TS   TS   🚨 [TOK-TOK] TOK TOK BLOCKED — WARNING: TOK level: +N.N% from high, +N.N% from low — blocking TOK entries`
