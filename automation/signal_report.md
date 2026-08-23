=== Signal Performance Report ===
Period: 2026-08-23 ~12:00 UTC | 6h + 24h

**24h Total:** 36 trades, -$0.23 PnL

## KILLED (executed):
None — no signals meet kill criteria (WR<30% AND PnL<-$0.10 AND >5 trades).

## BOOSTED (executed):
None — no signals meet boost criteria (WR>55% AND PnL>$0.05 AND 5+ trades AND consistent across tokens).

## LOSERS (watch list):
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| hzscore- | SHORT | 60% | -$0.16 | 5 | R:R problem: losses 7x avg win |
| ct-hot- | SHORT | 0% | -$0.15 | 2 | Too few trades to judge |

**hzscore- analysis:** High WR (60%) but 2 ATR SL hits (-$0.14, -$0.15) wipe out 3 profit-monster exits (+$0.06, +$0.05, +$0.02). Re-enabled Aug 22 by T for signal starvation — keep watching but no action yet.

## WINNERS:
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| hl_copy_trader | LONG | 38.9% | +$0.10 | 18 | Below WR threshold, net positive |
| ct-hot+ | LONG | 50% | +$0.08 | 6 | Marginal |

## INVERSIONS:
None found.

## ISSUES:
- Total PnL negative (-$0.23) despite 36 trades — system generating trades but edge is thin
- hzscore- R:R imbalance: wins small, losses big (ATR SL too wide or exits too tight)
- No clear kill or boost candidates — signal quality is mediocre across the board
