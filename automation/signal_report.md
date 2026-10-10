=== Signal Performance Report ===
Period: Last 6h | 24h

KILLED (executed):
| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| (none) | | | | | volume-breakout-long+ already regime-blocked in HIGH |

BOOSTED (executed):
| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| (none) | | | | | no signal met boost criteria (WR>55%, 5+ trades, PnL>$0.05) |

LOSERS (watch list):
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| volume-breakout-long+ | LONG | 22.2% | -$0.67 | 9 | HIGH regime already blocked (30d: 25% WR -$0.69 HIGH vs 72% +$3.56 EXTREME) |
| hmacd_mtf-- | SHORT | 33.3% | -$0.07 | 3 | Small sample, watch |
| bb-bounce-v2-long+ | LONG | 40.0% | -$0.04 | 5 | Small sample, watch |

WINNERS:
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| ai-trader+ | LONG | 100% | +$0.16 | 4 | Consistent across tokens, boost candidate if sample grows |

ISSUES:
- No direction inversions found (0 in 24h)
- volume-breakout-long+ 24h bleed is HIGH-regime specific; NORMAL/EXTREME are profitable (67%/72% WR). Regime gate already blocks HIGH — no action needed.
- ai-trader+ 100% WR but only 4 trades (< 5 trade boost threshold). Monitor for next cycle.
