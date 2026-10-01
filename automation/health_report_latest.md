=== Health Report ===
Time: 2026-10-01 01:48 UTC

PIPELINE: OK
- Status: running (last cycle 01:45:34, all steps rc=0)
- Signals (1h): 60 generated
- Trades: 3 open (JUP/HBAR/ALGO SHORT pump-chain), 1 closed today (MNT LONG win +0.0129 USDT)
- Errors: 0 real (Traceback/CRASH none in last 30m)
- Hotset: empty — no signals survived compaction; decider skipped (no signal >50% conf)

MARKET:
- Regime: LONG_BIAS — 3 LONG / 0 SHORT / 113 NEUTRAL (116 scanned)
- Speed: 53.1% tokens >= 50th percentile (128/241)

SYSTEM:
- Timers: core hermes-pipeline/price-collector/signal-compactor/watchdog/hl-sync all active
- Disk: 86% used — WARN (DBs, not logs)
- Prices: 86 tokens, updated 54s ago — fresh
- Services: hermes-pipeline + hermes-hl-sync-guardian active
- Load: 5.69 / 5.01 / 4.74 (elevated but pipeline completing)

AUTO-FIXES APPLIED:
- journalctl vacuum (freed 0B)
- candles.db WAL checkpoint attempted (busy — DB under active use)
- scanned for idle large logs >7d / >1h — none safe to gzip

ALERTS:
- Disk 86% — main consumers are SQLite DBs (~9.3G+ across 5 files). No auto-vacuum applied (destructive). Needs CEO decision: archive/prune coin_tracker, candles, mtf_macd_tuner, session_brain history.
- Regime check timers OnBootSec-only (not OnCalendar) — won't fire until reboot.
- hermes-atr-sl-updater.timer missing.
- decisions table last write 2026-04-13 — likely dead path post-signal_compactor migration.
