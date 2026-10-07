# Hermes Health Report — 2026-10-07 09:48 UTC

## Status: OK (WARN: disk 85%)

PIPELINE:
- Status: completed LIVE run 09:46:42 (oneshot — inactive between runs is normal)
- Signals (1h): 132 generated (pump-chain 73, volume_breakout_short 20, oversold_bounce_long 18, continuum_score_long 8, ichimoku_short 6)
- Trades: 0 open, 6 closed today (+0.64 USDT). Pipeline portfolio line: 11 closed / +41.74% (cumulative metric)
- Errors: 0 Tracebacks / CRASH / FATAL in 30min window
- position_manager: rc=0 (0 open / 0 closed / 0 adjusted)
- Phantom trades (|pnl|<0.01%): 0 in 24h
- FOGO SHORT rejected at RSI hard floor 36.6 < 45 — filter working correctly, signal intentionally not rolled back

MARKET:
- Regime: SHORT_BIAS 100 / LONG 3 / NEUTRAL 21 (124 tokens, 5m)
- Speeds: 128 / 241 tokens >= 50th percentile
- Live trading: ON (kill switch both gates true)
- Top speed: ACE 100.0, BLZ 100.0, HEMI 99.4

SYSTEM:
- Timers: 3/3 active — price-collector (last 09:46:03), 1m-candle (last 09:46:22), pipeline (fired 09:47)
- Services: hl-sync-guardian active; pipeline oneshot completed cleanly
- Disk: 85% used (18G free of 118G) — WARN, recurring since Oct 1
- Prices: fresh — candles_1m BTC 09:46, ETH 09:40, collector candle_seed 10/10
- DB locks: normal concurrent access (collector + 1m-candle on candles.db) — not stuck
- Logs: 272M total, nothing >7 days old to gzip

AUTO-FIXES APPLIED:
- None required — no crashes, no stuck locks, no missed critical timers
- Log compression skipped (no .log files older than 7 days)
- DB prune not attempted — CEO DB-retention decision still open (kanban target <80% by Oct 14)

ALERTS:
- WARN: Disk 85% (recurring). Largest: coin_tracker.db 3.3G, candles.db 2.6G (17.1M rows, 10.4M >30d), mtf_macd_tuner.db 1.4G, session_brain.db 1.0G, signals_hermes.db 951M
- INFO: safety filters healthy — RSI hard-floor, BTC-CRASH momentum blocks, signal non-rollback on failed exec
- INFO: 1491 "error|fail" journal matches in 24h — all intentional filter blocks, zero system crashes

SIDE FINDINGS:
1. signals_hermes_runtime.db unbounded (92MB, purge only removes executed>1h) — recurring
2. decisions table dead since 2026-04-13 — recurring, compactor logs to journal only
3. tokens table last_update stale (Aug 24) for 7 active rows — live pricing uses candles_1m/price_history, not this table
