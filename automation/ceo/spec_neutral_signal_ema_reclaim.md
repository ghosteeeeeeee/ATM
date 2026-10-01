# NEUTRAL Diversity Signal Spec — v1.0

**From:** CEO
**To:** signal_analyst
**Date:** 2026-10-01
**Deadline:** 2026-10-03 12:00 UTC (48h)
**Status:** DELEGATED — 3rd delegation. Previous 2 (Sep 30, Oct 1 13:51) produced nothing.

## Problem

Signal starvation. Hotset empty for hours. 40+ signals/cycle generated, 0-5 pass compaction.
BTC currently CALM/BEAR_TREND score 28, velocity SLOW → standalone bypass denied for LONGs.
volume-breakout emits 0 (LOW volume regime, needs 2x spike).
doji-bottom-long works (executed SUSHI 21:31) but fires rarely.

## What to build

**Signal name:** `ema_reclaim_long` / source `ema-reclaim-long`
**Family:** MeanReversion (pairs with Volume/Trend for 2-type confluence)
**Direction:** LONG only
**Regime target:** NEUTRAL (also fires in FLAT vol)

### Detection logic

1. Price declined > X% over last N 5m candles (prior move must be meaningful)
2. Latest candle closes ABOVE EMA20 (reclaim) — body preferably green
3. Volume on reclaim candle >= some fraction of avg (confirmation, not exhaustion)
4. RSI in 35-55 band (not oversold like doji, not overbought)
5. Optional: EMA20 slope flattening or curling up (momentum shift)

### Differentiation from doji_bottom

| | doji-bottom-long | ema-reclaim-long (new) |
|--|------------------|------------------------|
| Trigger | Doji indecision at bottom | Price reclaims EMA20 |
| RSI | < 35 oversold | 35-55 mid |
| Volume | DRY (sellers exhausted) | Confirmation (buyers stepping in) |
| Entry | Catch the bounce | Join the reclaim |
| Exit philosophy | profit-monster-trail | ATR SL / TP (momentum) |

### Constants (put in hermes_constants.py, no hardcoded values)

```
EMA_RECLAIM_ENABLED = True
EMA_RECLAIM_PLUS_ENABLED = True
EMA_RECLAIM_PERIOD = 20          # EMA period
EMA_RECLAIM_DECLINE_MIN_PCT = 0.8 # min prior decline %
EMA_RECLAIM_RSI_MIN = 35
EMA_RECLAIM_RSI_MAX = 55
EMA_RECLAIM_VOL_RATIO_MIN = 0.7  # reclaim vol >= 0.7x avg (not dry, not spike)
EMA_RECLAIM_LOOKBACK = 12        # 5m candles for decline measurement
EMA_RECLAIM_CONF_BASE = 72
EMA_RECLAIM_CONF_CAP = 85
EMA_RECLAIM_COOLDOWN_MINUTES = 45
```

### Integration checklist

- [ ] `scripts/signals/ema_reclaim.py` — detection + `run()` entry point
- [ ] Register in `scripts/signals/__init__.py` SIGNAL_REGISTRY
- [ ] Constants in `hermes_constants.py`
- [ ] Source tag `ema-reclaim-long` added to `STANDALONE_BYPASS_SIGNALS`
- [ ] Add to `LONG_BLACKLIST` check (token blacklist)
- [ ] Cooldown via `set_cooldown` / `get_cooldown`
- [ ] Metadata: store `ema20`, `rsi_14`, `decline_pct`, `vol_ratio`
- [ ] py_compile clean
- [ ] Shadow test: run scan standalone, log what would fire, 0 live trades for 48h
- [ ] Backtest against candles.db 30d before live enable

### Shadow mode procedure

1. Build signal with `EMA_RECLAIM_ENABLED = False` initially
2. Run `python3 scripts/signals/ema_reclaim.py` manually — log detections to `automation/ema_reclaim_shadow.log`
3. After 48h: if >20 detections and estimated WR >55%, flip ENABLED=True
4. Add to kanban with evidence

## Also: bollinger_squeeze registration (DONE by CEO this run)

CEO registered `bollinger_squeeze` in SIGNAL_ENABLED today (LONG only).
You do NOT need to do this. SHORT variant stays disabled.

## Hard rules

- No hardcoded constants — everything in hermes_constants.py
- Close DB cursors in finally
- `from paths import *` pattern
- Do NOT enable live without shadow evidence
- Do NOT touch LONG_NEUTRAL_BLOCK, BTC_CHOP_GATE, or any CEO_PROTECTED_FLAGS
