# ONDO SHORT Failure — Signal Conflict + RS Weakness Analysis (2026-05-21)

## What happened
ONDO SHORT @ $0.39830 (rs-r495 + zscore-pump-, conf=84.5%) stopped out via atr_sl_hit 20 min later.

## Root causes

### 1. Signal conflict — zscore-pump- then zscore-pump+ in same session
Timeline:
- 14:50:10 SHORT rs-r440 conf=62.9 (entry signal)
- 15:03:12 SHORT rs-r696 conf=65.5 (another SHORT, lower conf)
- 15:17:03 LONG rs-s6264,zscore-pump+ conf=75.7 z=2.547 ← CONTRADICTION
- 15:19:04 LONG rs-s3923,zscore-pump+ conf=80.7 z=2.491 ← CONTRADICTION

Price went UP after SHORT entry. The zscore-pump+ LONG signals fired 27 and 29 min after
entry, both at higher confidence (75.7, 80.7) than the SHORT entry conf (62.9).

### 2. Ancient RS level
rs-r495 had ~495 total touches but probably <10 in recent 200 candles. Ancient
institutional level, not relevant to current price action.

### 3. Four-loss pattern replicated across STRK, MORPHO, TIA, ONDO
All four losing shorts showed the same pattern:
- zscore-pump- SHORT fired first
- zscore-pump+ LONG fired 13-33 min later at equal or higher confidence
- Price moved against SHORT position

Winning shorts (ADA, AAVE, ANIME, BSV, CHIP): zero contradicting zscore LONG signals.

## Key data
- 37 closed trades: 25 shorts (12 losing, 13 winning), 12 longs (9 winning, 3 losing)
- RS touch count is the single best predictor of trade quality
- 0-100 touches: 22% win rate, -0.39% avg PnL
- 500-1500 touches: 75% win rate, +0.44% avg PnL
- 1500+ touches: 50% win rate, +0.99% avg PnL

## Six recommended fixes
1. **Signal conflict cache** — maintain token→last_zscore_direction+timestamp, suppress
   if opposite fired within 30 min and has weaker z-score
2. **RSI confirmation** — require RSI(14) > 60 for SHORT, < 40 for LONG zscore entries
3. **RS momentum qualifier** — penalize counter-trend RS entries where z-score and
   direction conflict
4. **Frustrated level detector** — 15+ touches in last 50 candles with no commitment
   through → 15-25% confidence penalty
5. **Cross-signal structural strength** — when combining rs-r + zscore-pump-, require
   20+ recent touches or apply 10pt confidence penalty
6. **Decider weighted scoring** — structural vs momentum signals scored separately,
   both must clear threshold