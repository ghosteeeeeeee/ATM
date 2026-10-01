=== Health Report ===
Time: 2026-10-01 15:48 UTC

PIPELINE: OK
- Status: running (active since 15:46:02, triggered by hermes-pipeline.timer)
- Cycle health: 191 rc=0 steps in 30min; 0 Traceback/CRASH/FATAL
- Signals (1h): 107 generated | 30m: 62
- Decider: hotset EMPTY — no signals survived compaction (none ≥50% conf)
- Trades: 2 open (ETH LONG -0.19%, BTC LONG +0.32%), 21 closed today (7W / 33.3% WR / -0.84 USDT)
- Errors: 0 real pipeline errors (1 false-positive "CRASH" line = BTC-CRASH-OVERRIDE informational)

MARKET:
- Regime: NEUTRAL — 1 LONG_BIAS (ACE) / 1 SHORT_BIAS (AERO) / 114 NEUTRAL (116 scanned)
- Speed: 53.1% tokens >= 50th percentile (128/241)

SYSTEM:
- Services: hermes-pipeline active; hermes-hl-sync-guardian active (15h)
- Timers: hermes-pipeline.timer active (every 1min); core hermes timers firing (watchdog, signal-compactor, price-collector, coin-tracker, regime scanners)
- Disk: 86% used — WARN (DB growth, not logs)
- Prices: 86 tokens, updated 55s ago — fresh
- token_speeds: 241 tokens, 88 stale (36.5%)
- Kill switch: LIVE enabled (hermes_constants + /var/www/hermes/data/hype_live_trading.json)
- Load: 7.96 / 6.94 / 6.54 (elevated; pipeline still completing)

AUTO-FIXES APPLIED:
- None this cycle — pipeline healthy, timers firing, prices fresh, no logs >7d to gzip, no crash/restart warranted

ALERTS:
- Disk 86% — consumers are SQLite DBs (~9.2G+). No safe auto-vacuum (destructive). Needs CEO decision: archive/prune coin_tracker, candles, mtf_macd_tuner, session_brain history.
- Hotset EMPTY — 107 signals/hr generated, 0 approved by compactor. No new trades until signals clear. Market NEUTRAL.
- hermes-wasp.service exit 1 every cycle — code-owner fix.
- hermes-better-coder.service ModuleNotFoundError: dispatcher.dispatcher — code-owner fix.
- hermes-price-collector intermittent candle-aggregation "database is locked" — latest run succeeded; lock path needs code-owner fix.
- decisions table dead since 2026-04-13 — expected after signal_compactor migration.
