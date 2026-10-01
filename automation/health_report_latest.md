=== Health Report ===
Time: 2026-10-01 16:47 UTC

PIPELINE: OK
- Status: running (last cycle 16:45:39, all steps rc=0)
- Signals (1h): 54 generated
- Trades: 2 open (BTC LONG, ETH LONG), 21 closed today
- Today PnL: -$0.84 USDT | WR 33.3% (7W/21)
- Errors: 0 real (grep hits were coin_tracker "0 errors")

MARKET:
- Regime: 2 LONG_BIAS (ZRO, PUMP) / 0 SHORT / 114 NEUTRAL — overall NEUTRAL
- Speed: 50.3% tokens >= 50th percentile (81/161)
- Hotset: empty — 5 signals pending top-10, 0 survived compaction (confidence <50%)

SYSTEM:
- Timers: ~50+ hermes timers active and firing on schedule
- Disk: 86% used (118G, 17G free) — WARN
- Prices: fresh (token_speeds.updated_at = 16:46 UTC)
- Guardian: active | Pipeline: active | Key timers (price-collector, 1m-candle, signal-compactor, trade-watchdog, watchdog): all active
- Journal: vacuumed, freed 84MB

DB DISK BREAKDOWN (growth root cause):
- coin_tracker.db 3.3G
- candles.db 2.3G (+961M WAL)
- mtf_macd_tuner.db 1.3G
- signals_hermes.db 893M
- session_brain.db 835M

AUTO-FIXES APPLIED:
- journalctl --vacuum-size=50M → freed 84MB archived journals
- systemctl daemon-reload → cleared stale hermes-atr-sl-updater.timer ghost reference (unit file does not exist; ATR SL managed locally by guardian via DB — not a functional gap)

ALERTS:
- WARN: Disk 86% — DB growth not logs (no .log files >7d). Needs CEO pruning decision for coin_tracker.db / candles.db / mtf_macd_tuner.db. Recurring since 2026-10-01 15:48.
- WARN: hermes-atr-sl-updater.timer unit file missing (not-found). Inert ghost entry — SL/TP path healthy via guardian. Delete stale reference or recreate unit if local ATR updater desired.
- INFO: Hotset empty — signal starvation continues (54 sig/hr raw, 0 pass confidence gate). Same as 15:48 report.
- INFO: 53/241 token_speeds is_stale=1 but updated_at fresh — flag means "no recent price move", not data staleness.
- INFO: Today red day (-$0.84, 33.3% WR) — within normal variance, no kill triggers.
