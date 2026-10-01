# Health Report — 2026-10-01 20:47 UTC

## Pipeline
- **Status:** OK — active, last cycle 20:45:26 completed rc=0
- **Signals (1h):** 70 generated
- **Trades:** 1 open (BTC LONG, in profit), 0 closed today
- **Errors (30m):** 0 Tracebacks, 0 crashes
- **Hotset:** empty (no signals survived compaction) — not a failure, just quiet market

## Market
- **Regime:** LONG_BIAS — 3 LONG / 0 SHORT / 113 NEUTRAL (116 tokens, 20:45)
- **Speed:** 128/241 tokens ≥ 50th percentile (~53%)
- **Prices:** fresh — prices.json written 20:47:05, token_speeds 162/241 updated <5min, 48 stale (tolerable)

## System
- **Timers:** core pipeline timers firing <1min (pipeline, price-collector, signal-compactor, hl-sync-guardian, watchdog)
- **Services:** hermes-pipeline.service active, hermes-hl-sync-guardian.service active
- **Disk:** 86% used (17G free) — WARN threshold 85%
- **Journal:** vacuumed, freed 87.3MB (now 17M)

## Top Disk Consumers
| Size | File |
|------|------|
| 3.3G | coin_tracker.db |
| 2.3G | candles.db |
| 1.3G | mtf_macd_tuner.db |
| 895M | signals_hermes.db |
| 835M | session_brain.db |

## Auto-Fixes Applied
- journalctl vacuum — freed 87.3MB
- Log gzip scan — nothing >7d to compress (logs already small)

## Alerts
- **WARN:** disk 86% — consumers are DBs, not logs. Suggest retention/vacuum plan for coin_tracker.db + mtf_macd_tuner.db
- **WARN:** 5 timers never fired / inactive: hl-copy (since Aug 15), regime-24h-check, regime-transition-check, gate2-circuit-breaker, ma-cross-5m-tuner. atr-sl-updater is known ghost (guardian owns ATR SL)
- **INFO:** no pipeline restart needed; kill switch state unchanged
