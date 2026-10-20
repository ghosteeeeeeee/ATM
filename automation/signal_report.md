=== Signal Performance Report ===
Period: Last 6h | 24h

KILLED (executed):
| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| (none) | - | - | - | - | No candidates |

BOOSTED (executed):
| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| (none) | - | - | - | - | No candidates |

LOSERS (watch list):
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| ai-trader+ | LONG | 25.0% | -$0.17 | 4 | Watch — only 4 trades, needs 5+ for kill; wins in HIGH (77.8%) and FLAT (60%) regimes |
| bb-bounce-v2-long+ | LONG | 60.0% | -$0.18 | 5 | Watch — high WR but avg loss > avg win; wins in HIGH (56.5%) and FLAT (100%) regimes |

WINNERS:
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| (none with 5+ trades, PnL > $0.05, WR > 55%) | | | | | |

ISSUES:
- No direction inversions found in last 24h.
- 6h window: zero closed trades with 2+ per signal+direction — quiet period.
- Both 24h losers have profitable regimes (HIGH/FLAT) — regime-block losing regimes rather than blanket kill if they worsen. Next run: escalate ai-trader+ if it crosses 5 trades with WR still <30%.
