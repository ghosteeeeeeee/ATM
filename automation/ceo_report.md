# CEO Report — 2026-08-06

## System Status
- **Timers**: All active (pipeline, hl-sync-guardian, price-collector, etc.)
- **Live Trading**: ACTIVE (kill switch true, trailing tightened)
- **24h Signal Outcomes**: 159 trades

## 24h Performance (by signal)
| Signal | Trades | WR | PnL |
|--------|--------|-----|-----|
| tl_break_long | 14 | 100% | +$1.81 |
| vel-hermes- | 46 | 43.5% | +$0.47 |
| zscore-rising+ | 8 | 62.5% | +$0.23 |
| zscore-rising- | 31 | 54.8% | +$0.22 |
| tl_break_short | 5 | 80% | +$0.22 |
| decider | 9 | 11.1% | -$0.18 |
| bb_bounce | 16 | 62.5% | -$0.15 |

## CEO DECISIONS

### URGENT: Dead Signal Leak Still Active
- **decider** (9 trades/24h, 11.1% WR) and **bb_bounce** (16 trades/24h) still firing
- Both in NEVER_REENABLE_FLAGS but still generating signals
- **DELEGATE to bug_hunter**: Find root cause in signal registration/batch pipeline. Previous investigation found stale batch data but leak persists.

### Monitor Active
- **tl_break_long**: 100% WR, 14 trades — continue monitoring, protected
- **vel-hermes-**: 46 trades, 43.5% WR — largest volume but marginal
- **zscore confluence**: 8+31 trades, 62.5%/54.8% WR — consistent
- **hzscore+confluence**: 5 trades today, 100% WR

### No Parameter Changes
- System net profitable, signals running stable
- Live trailing: activation 0.30%, distance 0.70%

## Open Positions
- 586 positions tracked in hl_copy
- Total unrealized PnL: $12.6M (includes all traders)
