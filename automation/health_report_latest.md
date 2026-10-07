# Hermes Health Report — 2026-10-07 05:50 UTC

## Status: OK (WARN: disk 85%)

PIPELINE:
- Status: active (cycle #232066)
- Signals (1h): 77 generated
- Trades: 1 open (IMX LONG -0.15%), 3 closed today (+1.11 USDT, 2 wins)
- Errors: 0 Tracebacks/CRASH in 30min window
- position_manager: rc=0
- Phantom trades (atr_sl_hit <0.01%): 0 today
- Hotset: empty (COOL_OFF, 67% coins hot — expected under current regime)

MARKET:
- Regime: LONG_BIAS 72 / SHORT 2 / NEUTRAL 49 (123 tokens, 5m)
- coin_tracker: STORMY, COOL_OFF strength 54
- Speeds: 178 fresh / 90 tokens >= 50th percentile
- Predictive: MOMENTUM_SURGE wind gust 0.32 vs sustained 0.09

SYSTEM:
- Timers: 3/3 active — price-collector (50s), pipeline (28s), 1m-candle (3m)
- Services: pipeline + hl-sync-guardian active
- Disk: 85% used (18G free of 118G) — WARN, recurring
- Prices: fresh — collector ran 50s ago, 87 prices, candle_seed 10/10
- DB locks: normal concurrent access (price-collector, 1m-candle, trades-api) — not stuck
- OpenMemory MCP: functional (with Accept header)

AUTO-FIXES APPLIED:
- None required — no crashes, no stuck locks, no missed critical timers
- Log compression skipped (nothing >7d old)
- Failed aux services (better-coder, bug-hunter, git-release) not restarted — root-cause fixes required, restart-only is a bandaids (per prior decision)

ALERTS:
- WARN: Disk 85% (recurring since Oct 1). Largest: coin_tracker.db 3.3G, candles.db 2.6G, mtf_macd_tuner.db 1.4G, session_brain.db 1.0G, signals_hermes.db 949M. CEO DB-pruning decision still open.
- WARN: 3 non-trading systemd services failed (better-coder exit 1, bug-hunter exit 1 by design, git-release exit 1). Auxiliary only.
- INFO: safety filters working as designed — RSI hard-floor blocks, BTC-CRASH momentum blocks, loss cooldowns.

SIDE FINDINGS:
1. signals table 26,121 rows — unbounded growth despite signal-purge timer (recurring). signal_history still empty — purge may target wrong table.
2. decisions table stale since 2026-04-13 — dead table, compactor logs to journal only.
3. coin_tracker_data.json lives at /var/www/html/ (not data/) — path quirk, not missing.
4. Empty legacy prices.db files at /root/.hermes/data/prices.db and scripts/data/prices.db — unused; real price_history is in signals_hermes.db static DB (13M rows).
5. BTC-CRASH / RSI-hard-floor blocks firing correctly — not errors.
