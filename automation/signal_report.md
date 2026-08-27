=== Signal Performance Report ===
Period: 2026-08-27 ~04:00 UTC | Last 6h + 24h

KILLED (executed):
None — no signals meet strict kill criteria (WR<30%, 5+ trades, >24h active, PnL<-$0.10)

BOOSTED (executed):
| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| macd-div- | SHORT | 75.0% | +$0.23 | 4 | Watch — positive, needs more data |

TUNE CANDIDATES (next review):
| Signal | Dir | WR | PnL | Trades | Active | Status |
|--------|-----|-----|-----|--------|--------|--------|
| slow-grind- | SHORT | 33.3% | -$0.64 | 12 | ~7h | Below 24h threshold — monitor |
| pump-catcher+ | LONG | 33.3% | -$0.39 | 21 | ~21h | Approaching 24h — will kill if no improvement |
| bb_bounce+ | LONG | 16.7% | -$0.29 | 6 | — | Already killed (BB_BOUNCE_PLUS_ENABLED=False) |

WINNERS:
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| macd-div- | SHORT | 75.0% | +$0.23 | 4 | Healthy — needs more data |
| r2-trend-long3 | LONG | 50.0% | +$0.09 | 2 | Small sample |
| cascade-reverse-v2-mtf_alignment+cascade_active | SHORT | 33.3% | +$0.19 | 3 | Positive despite low WR |

ISSUES:
- No signal inversions found
- pump-catcher+ approaching kill threshold — 21 trades at 33.3% WR, will re-evaluate at next 6h report
- slow-grind- needs more time to reach statistical significance (>24h active)
