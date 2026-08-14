# Signal Performance Report
**Generated:** 2026-08-15 | **Period:** Last 6h + 24h + 7d

## KILLED (executed)

| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| wave_catcher+ | LONG | 33.3% | -$0.34 | 6 (24h) | KILLED — added NEVER_REENABLE |
| mover+ | LONG | 28.6% | -$0.15 | 7 (24h) | KILLED — added NEVER_REENABLE |
| range_breakout+ | LONG | 25.0% | -$0.41 | 8 (7d) | KILLED — added NEVER_REENABLE |

## BOOSTED (executed)

| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| r2-trend-long2 | LONG | 61.5% | +$0.17 | 13 (24h) | WATCH — consistent winner |
| wave_catcher+ | SHORT | 42.9% | +$0.15 | 7 (24h) | KEEP — net positive |

## LOSERS (watch list)

| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| hzscore- | SHORT | 53.1% | -$0.21 | 32 (7d) | inverted R:R — avg_win $0.053 vs avg_loss $0.073 |
| range_breakout_short | SHORT | 33.3% | -$0.11 | 3 (24h) | borderline — needs more trades |
| r2-trend-long3 | LONG | 66.7% | -$0.12 | 9 (7d) | high WR but negative PnL — wins too small |
| r2-trend-long1 | LONG | 57.1% | -$0.02 | 7 (7d) | near breakeven |
| continuation+ | LONG | 66.7% | +$0.01 | 3 (24h) | small sample, needs data |

## WINNERS

| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| r2-trend-long2 | LONG | 61.5% | +$0.17 | 13 (24h) | best performing active signal |
| r2-trend-long0 | LONG | 66.7% | +$0.07 | 3 (24h) | small sample |
| wave_catcher+ | SHORT | 42.9% | +$0.15 | 7 (24h) | net positive despite low WR |
| bb-bounce-short,hzscore- | SHORT | 61.1% | +$0.14 | 18 (7d) | confluence combo winner |

## ISSUES
- **No signal inversions found** — all trades match expected direction
- **hzscore- SHORT** has53.1% WR but negative PnL ($0.053 avg win vs $0.073 avg loss) — inverted R:R
- **r2-trend-long3** has66.7% WR but -$0.12 PnL — wins are small, losses are large

## 6h Performance
Only 3 signals had 2+ trades: mover+ LONG (0% WR, -$0.11), r2-trend-long3 (50%, -$0.05), r2-trend-long2 (66.7%, +$0.01)

## Changes Made
- `WAVE_CATCHER_PLUS_ENABLED = False` + NEVER_REENABLE
- `MOMENTUM_LEADERBOARD_PLUS_ENABLED = False` + NEVER_REENABLE
- `RANGE_BREAKOUT_PLUS_ENABLED = False` + NEVER_REENABLE
