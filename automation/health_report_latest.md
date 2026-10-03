=== Health Report ===
Time: 2026-10-03 01:47 UTC

PIPELINE: OK
- Status: running (timer-triggered, last run completed 01:45:40 LIVE)
- Signals (1h): 61 in signals table
- Trades: 3 open, 49 closed today (+28.79% PnL)
- Errors: 0 in last 30 min
- Regime: NEUTRAL (116 neutral / 1 LONG_BIAS PUMP / 0 SHORT)
- Speed: 129/241 tokens >= 50th percentile (53.5%)

SYSTEM:
- Timers: active (pipeline every 1min, price-collector every 30s, signal-compactor every 1min, hl-sync-guardian every 5min)
- Services: hl-sync-guardian active; pipeline oneshot completes cleanly
- Disk: 89% used (after journal vacuum from 90%)
- Prices: fresh (trades.json + signals.json written 01:45)
- Hotset: empty [] — expected under full NEUTRAL regime

AUTO-FIXES APPLIED:
- journalctl --vacuum-size=100M: freed 170M archived journals (disk 90%→89%)
- No logs >7d to compress (all active)
- No pipeline restart needed (healthy, completed run)

ALERTS:
- WARN disk 89% — candles.db-wal 5.1G locked by price_collector; DB-retention decision open for CEO
- WARN 5 failed non-critical services: bug-hunter (hardcoded passwords + dead imports to defunct signal_gen), mtf-macd-tuner (PrecomputedMACD.warmup AttributeError), trading-checklist (0 approved signals), git-release, better-coder — none on live trading path
