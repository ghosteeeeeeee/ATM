# Hermes Health Report
Time: 2026-10-06 12:48 UTC

## PIPELINE: OK
- Status: running LIVE, cycle #231091+ (12:46-12:48)
- Steps (30m): signal_analyst rc=0, breakout_engine rc=0, signals_runner rc=0, decider_run rc=0, position_manager rc=0, hermes-trades-api rc=0
- Signals (1h): 147 generated
- Trades: 0 open, 7 closed today
  - bb-squeeze+ LONG 2x: -$0.25
  - pump-chain- SHORT 1x: -$0.25
  - trend-ride+ LONG 4x: -$0.34
  - 0% WR tiny sample — trading perf, not system fault
- Errors (30m): 0 Traceback/CRASH. BTC-CRASH filter correctly blocking DOT LONGs (BTC 30m mom -0.15%) — working as designed given SHORT_BIAS market
- Phantom trades (atr_sl_hit <0.01%): 0

## MARKET
- Regime: SHORT_BIAS — 16 LONG / 41 SHORT / 65 NEUTRAL (122 tokens scanned 12:45)
- Speed: 53.1% tokens >= 50th percentile (128/241)
- Prices: 85 tokens, prices.json updated 12:47:14 UTC (~1min old, fresh)
- Coin tracker: STORMY, 64 hot / 21 warm / 1 cold, 74% hot → COOL_OFF signal (reduce exposure)

## SYSTEM
- Core timers: ALL ACTIVE (verified 12:48)
  - hermes-pipeline.timer: 2s ago
  - hermes-price-collector.timer: 57s ago
  - hermes-1m-candle.timer: 39s ago
  - hermes-hl-sync-guardian.timer: last fired 02:50 UTC (9h ago) — service itself active running since Oct 4; recurring cadence note
- Disk: 84% used (19G free / 118G) — 1pt below 85% WARN
- candles.db locks: 3 normal concurrent writers (pipeline/price-collector/1m-candle) — NOT stuck
- DB sizes: candles 2.5G + WAL 14M; coin_tracker/mtf_macd_tuner still largest (from prior checks)
- Logs: nothing >7d to compress; largest is pipeline.log 77M

## AUTO-FIXES APPLIED
- None required. System healthy. No services stopped, no timers disturbed.

## ALERTS
- **WARN**: Disk 84% — approaching 85% threshold. Growth is DBs not logs. Next step if crosses: DB retention on coin_tracker / mtf_macd_tuner.
- **NOTE** (recurring, non-trading): hl-sync-guardian.timer last fired 02:50 UTC (~9h). Service active (running). Verify expected cadence.
- **NOTE** (market context, not system): BTC 30m momentum -0.15% blocking LONG entries; 74% coins hot → COOL_OFF. Filters working correctly.
