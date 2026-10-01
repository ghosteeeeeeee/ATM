# Health Report — 2026-10-01 23:47 UTC

```
=== Health Report ===
Time: 2026-10-01 23:47 UTC

PIPELINE: OK
- Status: running (active, 1min timer, 0 Tracebacks/30min)
- Signals (1h): 67 generated / 0 approved (hotset empty)
- Trades: 1 open (SUSHI LONG 1/6), 23 closed today, 39.1% WR, -0.73 USDT
- Errors: 0 pipeline errors; 1 transient candles.db lock in price_collector
- Phantom atr_sl_hit <0.01%: 0

MARKET:
- Regime: NEUTRAL (115 neutral / 2 long_bias / 0 short_bias) regime_5m.json 23:45Z
- Speed: 124/241 tokens >=50th pct (fresh); 99 stale
- Tokens: 86 prices collected; candles_1m age ~60s

SYSTEM:
- Timers: core firing <1min (pipeline, signal-compactor, price-collector, watchdog, coin-tracker)
- Disk: 86% used (96G/118G, 16G free) WARN
- Prices: fresh
- Failed units (non-critical): better-coder, bug-hunter, ceo, git-release, mtf-macd-tuner, trading-checklist, upgrade-implementer, weather-station-api

AUTO-FIXES APPLIED:
- None required (pipeline healthy; disk nothing safe to clean; timers firing)

ALERTS:
- Disk 86% — CEO DB-pruning decision open
- Hotset empty — 67 sig/hr, 0 approved (gate/market, not crash)
- price_collector "database is locked" on candle agg (concurrent 1m-candle)
- better-coder: ModuleNotFoundError dispatcher.dispatcher
- bug-hunter FAILs: hardcoded passwords, dead signal_gen imports
