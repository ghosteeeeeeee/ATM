# Health Report — 2026-10-06 07:48 UTC

```
=== Health Report ===
Time: 2026-10-06 07:48 UTC

PIPELINE: OK
- Status: running (cycle #230792, signal_analyst PASS GOAT LONG, breakout_engine running)
- Signals (1h): 76 generated
- Trades: 0 open (signal_outcomes), 1 paper (HL LTC reconciled), 6 closed today
- Errors: 0 Traceback/CRASH in 30m

MARKET:
- Regime: LONG_BIAS (33 LONG / 12 SHORT / 75 NEUTRAL) — shifted from SHORT_BIAS at 06:48
- Speed: 50.3% tokens >= 50th percentile (89/177)

SYSTEM:
- Timers: 4/4 critical active (pipeline 58s ago, price-collector 1m59s, 1m-candle 1m12s, hl-sync-guardian active)
- Disk: 84% used (up from 83% at 06:48; growth in DBs not logs)
- Prices: 85 tokens collected at 07:46:58 (fresh)
- candles.db: held by 2 normal concurrent writers — NOT a stuck lock

AUTO-FIXES APPLIED:
- None needed — system healthy

ALERTS:
- WARN: Disk 84% approaching 85% threshold. Logs 225M total, nothing >7d to compress. Growth is in DBs (coin_tracker 3.4G, candles 2.6G, mtf_macd_tuner 1.1G). Monitor; clean DBs if >85%.
- INFO: Today 0% WR on 6 closed trades (bb-squeeze+ LONG 2x, trend-ride+ LONG 4x) — trading performance, not system fault. Tiny sample.
- INFO: hermes-hl-sync-guardian.timer last fired 02:50 UTC (~5h ago) — recurring non-trading-path note from prior report. Service is active.
- INFO: Legacy `decisions` table in signals_hermes_runtime.db stale since Apr 13 — live decision flow uses `signals.decision` + decision-log. Dead table, not on path.
- INFO: price_signals.db is 0 bytes, unreferenced by scripts — dead file.
- INFO: Dead/disabled units unchanged: hl-copy, ma-cross-5m-tuner, regime-24h-check, regime-transition-check, atr-sl-updater — non-trading path.
- INFO: Prior get_sl_multiplier_v2() keyword error (02:59) — no recurrence in current logs. Resolved.
```
