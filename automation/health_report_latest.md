# Health Report — 2026-10-07 23:49 UTC

## PIPELINE: WARN
- Status: running (192 rc=0 cycles in 30min, 0 tracebacks)
- Signals (1h): 52 generated, 0 approved (hotset empty — compaction filtering)
- Trades: 1 open (CRV LONG +5.38%), 13 closed today
- Position manager: clean, ATR trailing active on CRV

## MARKET
- Regime: LONG_BIAS (75 LONG / 1 SHORT / 48 NEUTRAL)
- Speed: 128/241 tokens (53%) >= 50th percentile
- Signal strength: CAUTION (10.45)

## SYSTEM
- Critical timers: 3/3 active (price-collector, 1m-candle, pipeline) — all firing ≤75s
- Disk: 86% used (95G/118G, 17G free) ⚠️
- Prices: 87 tokens, fresh (~51s)
- 1m candles: 105 in last 5min, flowing
- Services: pipeline OK, hl-sync-guardian OK, hl-copy OK, brain-api OK

## AUTO-FIXES APPLIED
- None required — pipeline healthy, timers active, no crashes, no DB locks

## ALERTS
1. **DISK 86%** (WARN, recurring) — DB hogs: coin_tracker 3.3G, candles 2.6G, mtf_macd_tuner 1.6G, session_brain 1.1G. No logs >7d to clean. Needs DB retention plan.
2. **better-coder broken** (WARN) — `dispatcher.dispatcher` module missing (empty dir). Service crashes every run. Not auto-fixed.
3. **Phantom trade** (WARN) — GRASS SHORT -0.0015% (atr_trail_hit).
4. **Hotset empty** (INFO) — 52 signals/hour, 0 survived compaction. Aggressive filtering active.
