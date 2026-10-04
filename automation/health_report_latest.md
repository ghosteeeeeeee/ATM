=== Health Report ===
Time: 2026-10-04 12:48 UTC

PIPELINE: OK
- Status: running (timer-triggered every 1min, last LIVE cycle 12:46:46 rc=0)
- Signals (1h): 87 generated (signals table)
- Trades: 3 open, 34 closed today (brain trades source of truth)
- PnL: -7.73% today | +86.80% last 7d (212 closed)
- Errors: 0 Traceback/CRASH/exception in 30 min
- Position manager: rc=0 every cycle

MARKET:
- Regime: SHORT_BIAS — 14 LONG / 26 SHORT / 77 NEUTRAL (regime_5m.json ts 12:45)
- Speed: 53.5% tokens >= 50th percentile (129/241)

SYSTEM:
- Timers: core active (pipeline 1m, price-collector 30s, signal-compactor 1m, pump-hunter, 1m-candle, watchdog, 15m-regime, 4h-regime)
- Services: hermes-pipeline active, hermes-hl-sync-guardian active (long-running daemon since 2026-10-03)
- Disk: 80% used (under 85% threshold)
- Prices: fresh (regime 1.4m, candles 1.3m, coin_tracker 0.2m)
- Phantom trades: 0
- Hot signals top: SYRUP hmacd_mtf SHORT 85.2, WCT doji_bottom_long 80.0, ADA bb_bounce_v2_long 77.0

AUTO-FIXES APPLIED:
- none — pipeline healthy, no restarts or cleanups forced

ALERTS:
- WARN: hermes-price-collector crash-loops on candles.db "database is locked" during candle agg (known; systemd auto-restarts; prices still collected; needs PRAGMA busy_timeout + serialize vs _aggregate_1m)
- WARN: dead timer refs — atr-sl-updater.timer not-found; regime-24h-check + regime-transition-check enabled but inactive (OnBootSec-only by design)
- WARN: signal_outcomes partial (17 closed today) vs portfolio 34 — brain trades table is source of truth
- INFO: decisions table stale (latest 2026-04-13) — unused post-signal_compactor migration
- INFO: today PnL -7.73% — performance, not system health; 7d still +86.80%
