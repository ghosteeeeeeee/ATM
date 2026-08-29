=== Signal Performance Report ===
Generated: 2026-08-29 (6h cycle)

## 24h Summary
Total: 59 trades | 55.9% WR | +$1.12 PnL
Open positions: 5

## TOP PERFORMERS (24h)
| Signal | Dir | Trades | WR | PnL | Avg PnL |
|--------|-----|--------|-----|-----|---------|
| accel-300-v2- | SHORT | 31 | 58.1% | +$1.35 | +$0.044 |
| bb-bounce-short | SHORT | 18 | 61.1% | +$0.12 | +$0.007 |
| macd-div- | SHORT | 2 | 50.0% | +$0.01 | +$0.005 |

## 72h Extended View (5+ trades)
| Signal | Dir | Trades | WR | PnL | Avg PnL | Status |
|--------|-----|--------|-----|-----|---------|--------|
| accel-300-v2- | SHORT | 72 | 52.8% | +$1.46 | +$0.020 | Winner |
| macd-div- | SHORT | 9 | 77.8% | +$0.44 | +$0.049 | Winner |
| bb-bounce-short | SHORT | 25 | 60.0% | -$0.02 | -$0.001 | Breakeven |
| slow-grind- | SHORT | 11 | 36.4% | -$0.51 | -$0.046 | DISABLED |
| pump-catcher+ | LONG | 20 | 35.0% | -$0.22 | -$0.011 | DISABLED |
| atr-spike+ | LONG | 7 | 28.6% | -$0.15 | -$0.021 | DISABLED |

## KILLS EXECUTED
None this cycle. All known losers already disabled:
- slow-grind-: SLOW_GRIND_SHORT_ENABLED = False
- pump-catcher+: PUMP_CATCHER_ENABLED = False (all variants)
- atr-spike+: ATR_SPIKE_ENABLED = False (all variants)

## WATCH LIST
| Signal | Dir | Trades | WR | PnL | Note |
|--------|-----|--------|-----|-----|------|
| bb-bounce+ | LONG | 4 (72h) | 0% | -$0.62 | BB_BOUNCE_LONG_ENABLED = True. Only 4 trades, doesn't meet kill threshold (5+). Monitor. |
| accel-300-v2-short- | SHORT | 2 (24h) | 0% | -$0.19 | Too few trades to judge. |

## ISSUES
- No direction inversions detected
- bb_bounce+ (LONG) has 0% WR but only 4 trades in 72h — below kill threshold
- All top volume going SHORT (accel-300-v2- and bb-bounce-short dominate)

## ACTIONS
- No signals killed this cycle
- No boosts applied — current winners already at max enabled state
- Recommend monitoring bb_bounce+ LONG; kill if reaches 5+ trades with < 30% WR
