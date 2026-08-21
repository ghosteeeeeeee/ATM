# Signal Performance Report
Generated: 2026-08-21 17:30 UTC | Period: 6h + 24h

## 24h Totals
35 trades | 54.3% WR | +$0.24 PnL (breakeven)

## 6h Performance
| Signal | Dir | Trades | WR | PnL |
|--------|-----|--------|-----|-----|
| ct-hot+ | LONG | 12 | 41.7% | -$1.02 |
| hl_copy_trader | LONG | 10 | 50.0% | -$0.28 |

## 24h Performance (3+ trades)
| Signal | Dir | Trades | WR | PnL |
|--------|-----|--------|-----|-----|
| ct-hot+ | LONG | 14 | 42.9% | -$0.71 |
| hl_copy_trader | LONG | 16 | 62.5% | +$0.71 |

## KILLED (executed)
None — no signals meet kill criteria (WR <30% with 5+ trades).

## BOOSTED (executed)
None — no signals meet boost criteria (WR >55% with 5+ trades AND PnL >$0.05).
hl_copy_trader (62.5% WR, +$0.71) is close but only has 16 trades in24h — borderline.

## LOSERS (watch list)
| Signal | Dir | Trades | WR | PnL | Status |
|--------|-----|--------|-----|-----|--------|
| ct-hot+ | LONG | 14 | 42.9% | -$0.71 | Already DISABLED (flag=False since 17:00 today). 0W-7L in last 3h before disable. All 14 trades are pre-disable. |

## WINNERS
| Signal | Dir | Trades | WR | PnL | Status |
|--------|-----|--------|-----|-----|--------|
| hl_copy_trader | LONG | 16 | 62.5% | +$0.71 | Active. Best performer. HYPE LONG (6T, 66.7%, +$0.45) and BTC LONG (3T, 66.7%, +$0.23) driving gains. |

## ISSUES
- **ct-hot+ still firing pre-disable:** 14 trades created today before 17:00 UTC disable. COIN_TRACKER_HOT_PLUS_ENABLED is now False — no new trades will fire.
- **Low trade volume:** Only 2 signals produced 3+ trades in 24h. System is signal-starved.
- **No inversions detected.**
