# Hermes Health Report
Time: 2026-10-06 09:47 UTC

## PIPELINE: OK
- Status: running LIVE, cycle #230912 (09:47:23)
- Position Manager: Open 0 | Closed 0 (this cycle)
- signals_runner: rc=0 (22.9s)
- breakout_engine: rc=0, 0 signals
- Signals (1h): 95 generated
- Trades: 0 open, 7 closed today
  - bb-squeeze+ LONG 2x: -$0.25
  - pump-chain- SHORT 1x: -$0.25
  - trend-ride+ LONG 4x: -$0.34
- Errors (30m): 1 non-fatal CTX-GATE LLM timeout (CRV @ 09:38, 35s) — pipeline continued via BTC-CRASH-OVERRIDE
- Tracebacks/CRASH: 0

## MARKET
- Regime: SHORT_BIAS — 11 LONG / 50 SHORT / 62 NEUTRAL (123 tokens scanned 09:45)
- Speed: 53.1% tokens >= 50th percentile (128/241)
- Prices: 84 tokens, prices.json updated 09:46:56 (~1min old, fresh)
- Coin tracker: STORMY, 10 hot / 73 warm / 3 cold, 0 errors

## SYSTEM
- Core timers: ALL ACTIVE
  - hermes-pipeline.timer: 30s ago
  - hermes-price-collector.timer: 1m44s ago
  - hermes-1m-candle.timer: 1m35s ago
  - hermes-hl-sync-guardian.timer: 6h ago (active, expected cadence)
- Disk: 84% used (19G free / 118G) — 1pt below 85% WARN
- DB sizes: coin_tracker 3.3G, candles 2.5G, mtf_macd_tuner 1.1G, session_brain 1.0G, signals_hermes 938M
- candles.db locks: 3 normal concurrent writers (pipeline/price-collector/1m-candle) — NOT stuck
- Phantom trades (atr_sl_hit <0.01% PnL): 0
- Dead units (recurring, non-trading path): atr-sl-updater (inactive), hl-copy, ma-cross-5m-tuner, regime-24h-check, regime-transition-check

## AUTO-FIXES APPLIED
- None required. System healthy.

## ALERTS
- **WARN**: Disk 84% — approaching threshold. Growth is DBs (coin_tracker, candles, mtf_macd_tuner), not logs. If crosses 85%: run DB retention on tuner/tracker DBs.
- **INFO**: CTX-GATE LLM timeout (CRV LONG @ 09:38) — non-fatal, trade allowed via crash-override. No recurrence in last 9m.
- **NOTE**: hermes-atr-sl-updater.timer inactive — not on critical trading path; no auto-restart.
- **NOTE**: hermes-hl-sync-guardian last fired 02:50 UTC (~7h) — verify expected cadence if guardian should run more often.
