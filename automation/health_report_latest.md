# Health Report — 2026-10-05 09:47 UTC

## Pipeline: OK
- Status: **active** (hermes-pipeline.service), LIVE cycle every 1m, all steps rc=0
- Position manager: healthy — 3/6 open slots, rc=0 every cycle, 1 ATR adjust in last cycle
- Signals (1h): **110** in `signals` table
- Trades: **3 open** | **35 closed today** | PnL **-13.07%**
  - Open: SAND SHORT -0.65% (mtf-regime-trend-), ETH LONG +0.01% (bb-bounce-v2-long+), HBAR SHORT +0.60% (pump-chain-)
  - Closed page (200 rolling): 55.5% WR (111/200), +1.13 USDT
- Errors in 30m: **0** Traceback/CRASH in pipeline (position_manager rc=0 all cycles)

## Market
- Regime: **SHORT_BIAS** (3 LONG / 67 SHORT / 47 NEUTRAL, 117 tokens, ts 09:45)
- Macro gate: LONG=REDUCE, SHORT=FULL (wr=65%)
- Speed: **52.7%** tokens ≥ 50th percentile (127/241)

## System
- Core timers: **all 3 active** — price-collector (last 09:43:38→next ~09:46), 1m-candle (09:43:49), pipeline (09:46:00)
- Services: pipeline **active**, hl-sync-guardian **active**
- Disk: **82%** used (91G/118G, 21G free) — under 85% threshold
- Prices: trades.json 0.1min, signals.json 0.9min, coin_tracker_data.json 09:46 (~1min, at /var/www/html/ by design)
- Coins collected: 85 prices most cycles (one zero-price cycle at 09:43:38, recovered next run)
- Phantom atr_sl_hit (<0.01% PnL, 24h): **0**

## Auto-fixes applied
- **None required.** No crashes, no stuck timers, prices fresh, disk under threshold. Recurring candles.db lock contention is write contention (pipeline + 1m-candle + price-collector write concurrently) — not a stuck lock; stopping services would not fix it and risks the timer path (same call as 06:49 report). Code-level fix still pending: serialize candle writers / raise busy_timeout beyond 30–60s.

## Alerts
- **WARN** (recurring): `hermes-price-collector.service` — 46 lock-related events in last 60m (`database is locked` / `database table is locked` on candles.db). Aggregation (5m/15m/1h/4h) + wal_checkpoint + `_store_candles` + seeder all contend. Services self-recover; raw prices still collected. One cycle collected 0 prices (09:43:38) — recovered. **Root-cause fix still pending in code, not systemd.**
- **WARN** (known): `signals` table has 22,174 rows total — cleanup needed, not a runtime failure.
- **INFO**: `signal_outcomes` open=0 vs portfolio open=3 — outcomes table partial; portfolio source of truth = position_manager + trades.json (per AGENTS.md).
- **INFO**: `systemctl list-timers hermes-*` glob returns 0 (systemd glob quirk); explicit unit names confirm all timers healthy.
- **INFO**: hotset.json empty this cycle — no signals survived compaction / none above 50% confidence to execute. Not an error.
- **INFO**: today PnL -13.07% is trading performance, not system health.
