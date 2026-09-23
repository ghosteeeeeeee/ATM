# Health Report — 2026-09-23 19:45 UTC

## PIPELINE: OK
- Status: running (cycle #212809)
- Last complete: 19:43:42 (33s CPU)
- Signals (1h): 42 generated (all SHORT biased)
- Trades today: 27 closed, -0.38 USDT PnL, 48.1% winrate
- Open trades: 0
- Errors: 1 transient signal_compactor failure (19:31, self-healed)

## MARKET: NEUTRAL
- Regime: 2 LONG bias / 0 SHORT bias / 118 NEUTRAL
- Speed: 126 tokens >= 50th percentile
- Hotset: EMPTY (0 tokens survived compaction)
- Signals filtered: RR-engine blocking (grade=F), spike filter (RSI<30)

## SYSTEM: OK
- Services: pipeline=active, hl-sync-guardian=active
- Timers: 19 active, all firing on schedule
- Disk: 84% used (freed 1.1G via journal vacuum)
- DB sizes: coin_tracker=2.7G, candles=2.1G, signals=817M

## AUTO-FIXES APPLIED
- Vacuumed journal logs: freed 1.1G (85% → 84%)

## ALERTS
- **WARN**: Disk at 84% — coin_tracker.db (2.7G) and candles.db (2.1G) are the biggest consumers. Consider pruning if disk pressure continues.
- **WARN**: Hotset empty for multiple cycles — market is very quiet (NEUTRAL regime). No trade opportunities passing filters.
