# Signal Performance Report

Period: Last 6h | 24h (as of 2026-10-18 02:14 UTC)

Market is very quiet — only 4 closed trades in 24h, 3 in 6h. No signal meets kill or boost thresholds this cycle. No direction inversions found.

## KILLED (executed):
None — no signal met kill criteria (WR <30% with 5+ trades, 24h).

## BOOSTED (executed):
None — no signal met boost criteria (WR >55% with 5+ trades, 24h).

## LOSERS (watch list) — 72h context:
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| doji-bottom-long | LONG | 45.5% | -$0.51 | 11 | WATCH — HIGH regime only (9T 33%WR -$0.59). Kill if 24h sample grows and stays <50% WR |
| pump-chain- | SHORT | 0.0% | -$0.49 | 8 | WATCH — 72h bleed but 24h only 1 trade. EXTREME regime 10T 20%WR -$0.01 (72h). Already has HIGH_BLOCK=True |
| ai-trader+ | LONG | 44.4% | -$0.42 | 9 | WATCH — EXTREME 6T 33%WR -$0.38 / HIGH 3T 67% -$0.04 |
| bb-bounce-v2-long+ | LONG | 33.3% | -$0.27 | 6 | WATCH — EXTREME only (4T 25%WR -$0.29). Below 50% WR all regimes |

## WINNERS — 6h:
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| pump-chain-,pump-chain-v6- | SHORT | 100% | +$0.47 | 1 | OK |
| pump-chain+ | LONG | 100% | +$0.02 | 1 | OK |

## ISSUES:
- Very low trade volume (4 closed trades / 24h) — signal sample too small for statistical kills. Do not act on 72h patterns without 24h confirmation (survivorship/variance lesson).
- No inversions detected in last 24h.
