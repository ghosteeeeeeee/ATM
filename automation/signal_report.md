# Signal Performance Report
**Generated:** 2026-08-23 23:30 UTC | **Period:** Last 6h + 24h

## KILLED (executed)
| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| (none) | — | — | — | — | No kill candidates — all losers have <5 trades or WR >30% |

## BOOSTED (executed)
| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| (none) | — | — | — | — | No boost candidates — no signal meets all 3 criteria (WR>55%, PnL>$0.05, 5+ trades) |

## LOSERS (watch list)
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| hzscore- | SHORT | 42.9% | -$0.21 | 7 | WATCH — re-enabled 08-22, -$0.03/trade avg. Below kill threshold (WR>30%) |
| macd-div+ | LONG | 0.0% | -$0.36 | 2 | LOW VOL — too few trades to act |
| ct-hot- | SHORT | 0.0% | -$0.15 | 2 | LOW VOL — too few trades to act |

## WINNERS
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| hl_copy_trader | LONG | 40.0% | +$0.42 | 20 | ACTIVE — highest volume, net positive despite sub-50% WR |
| ct-hot+ | LONG | 53.3% | +$0.18 | 15 | ACTIVE — solid WR, consistent earner |

## 6h Detail (for reference)
| Signal | Dir | WR | PnL | Trades |
|--------|-----|-----|-----|--------|
| hl_copy_trader | LONG | 50.0% | +$0.32 | 2 |
| ct-hot+ | LONG | 55.6% | +$0.10 | 9 |
| hzscore- | SHORT | 0.0% | -$0.05 | 2 |
| macd-div+ | LONG | 0.0% | -$0.36 | 2 |

## ISSUES
- No signal inversions found (no LONG signals executing SHORT or vice versa)
- hzscore- re-enabled 2 days ago for signal starvation — currently losing but within tolerance. Re-evaluate in 24h if trend continues.
- Low trade volume overall — signal starvation may be affecting sample sizes.

## Actions Taken
- No flags changed this cycle (no kill candidates met criteria)
- Next review: 6h
