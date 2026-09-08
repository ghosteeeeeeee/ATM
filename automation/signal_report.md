=== Signal Performance Report ===
Generated: 2026-09-08 11:10 UTC | 43 trades in 24h | Total PnL: +$0.69 | WR: 60.5%

KILLED (executed):
| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| (none) | — | — | — | — | No signals meet all 3 kill criteria |

BOOST CANDIDATES:
| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| pump-chain+ | LONG | 81.3% | +$0.51 | 16 | STRONG — consistent volume + high WR |
| open-skies+ | LONG | 66.7% | +$1.23 | 3 | STRONG — highest PnL/trade, low sample |

LOSERS (watch list):
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| sma20-dip+ | LONG | 47.1% | -$0.42 | 17 | WATCH — active ~7h, too early to kill. WR below 50% but no kill criteria met. |
| ema300-dip-short | SHORT | 55.6% | -$0.45 | 9 | WATCH — good WR but losses larger than wins. Active ~18h. |
| bb-bounce-v2-long+ | LONG | 53.8% | -$0.18 | 13 | WATCH — thin negative, profit zone. |

WINNERS:
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| pump-chain+ | LONG | 81.3% | +$0.51 | 16 | STRONG |
| open-skies+ | LONG | 66.7% | +$1.23 | 3 | STRONG |
| r2-trend-short3 | SHORT | 100% | +$0.10 | 2 | PERFECT (low count) |
| r2v2-long3 | LONG | 100% | +$0.09 | 1 | PERFECT (1 trade) |

ISSUES:
- No direction inversions detected
- No signals meet all 3 kill criteria (WR<30%, PnL<-$0.10, active>24h)
- sma20-dip+ — high volume (17 trades) but negative. 8 cut-loser-CL-T1 exits. Losses small individually ($0.09-$0.24) but accumulate. Needs >24h data before kill decision.
- ema300-dip-short — decent WR (55.6%) but -$0.45 net. Large losses on MNT (-$0.22) and SYRUP (-$0.20) offset wins.
- cut-loser-CL-T1 is dominant loss exit — stop-loss entries may be too tight or entries chasing.
- ema300-dip-short protected test window evaluates after 2026-09-09 05:00 UTC.
