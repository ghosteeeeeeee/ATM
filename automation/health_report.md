# Health Report — 2026-10-08 00:50 UTC

```
=== Health Report ===
Time: 2026-10-08 00:50 UTC

PIPELINE: OK
- Status: running (last LIVE run 00:46:51 rc=0)
- Signals (1h): 86
- Trades: 1 open (CRV LONG +9.07%), 0 closed today
- Errors: 0 pipeline Tracebacks

MARKET:
- Regime: 47 LONG / 15 SHORT / 60 NEUTRAL (LONG_BIAS)
- Speed: 128/241 tokens >= 50th percentile (avg 48.6)

SYSTEM:
- Timers: 3/3 active (price-collector, 1m-candle, pipeline)
- Disk: 85% used (118G, 17G free) — journal vacuum freed 181M
- Prices: fresh (~2min age)

AUTO-FIXES APPLIED:
- Fixed trade_watchdog.py NameError (watchdog_mode undefined) — service was crash-looping
- journalctl --vacuum-size=80M — freed 181M

ALERTS:
- Disk still WARN at 85% — DB prune CEO decision open (goal <80% Oct 14)
- Failed non-critical units unchanged (better-coder, bug-hunter, git-release, brain-auditor)
- signals_hermes_runtime.db unbounded; decisions table dead (recurring)
```
