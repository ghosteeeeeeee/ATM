=== Signal Performance Report ===
Period: 2026-09-19 ~15:00 UTC (Last 6h / 24h)

System: 11T 63.6% WR $0.80 (6h) | 40T 62.5% WR $2.47 (24h) — healthy

KILLED (executed this cycle):
None. grind-trend- already killed 2026-09-19 (20% WR, -$0.38, no winning regime).

BOOSTED (executed this cycle):
None. No signal meets all boost criteria (5+ trades, 55%+ WR, positive PnL, multi-token).

WINNERS (24h):
| Signal            | Dir  | WR     | PnL   | Trades | Status          |
|-------------------|------|--------|-------|--------|-----------------|
| pump-chain+       | LONG | 64.7%  | $1.68 | 17     | Active — top performer |
| grind-trend+      | LONG | 83.3%  | $0.47 | 6      | Active — best WR |
| pullback-entry-   | SHORT| 62.5%  | $0.28 | 8      | Active          |
| doji-bottom-long  | LONG | 100%   | $0.30 | 1      | Watch (low vol) |
| volume-breakout-long+ | LONG | 100% | $0.08 | 1    | Watch (low vol) |
| warrior-sr-confirm+ | LONG | 100% | $0.09 | 1     | Watch (low vol) |

LOSERS (24h):
| Signal         | Dir  | WR    | PnL    | Trades | Status                         |
|----------------|------|-------|--------|--------|--------------------------------|
| grind-trend-   | SHORT| 20%   | -$0.38 | 5      | KILLED (already disabled)      |
| mover+         | LONG | 0%    | -$0.05 | 1      | Watch (low volume, not actionable yet) |

REGIME NOTES:
- grind-trend- SHORT: NORMAL regime = 12.5% WR (8T, -$0.33), HIGH = 33.3% WR (3T, -$0.16). All regimes negative → blanket kill correct.
- grind-trend+ LONG: 83.3% WR — only LONG direction is profitable. MINUS already killed.

ISSUES:
- None. No direction inversions found. No bugs detected.
- grind-trend- trades still appearing (5 in 24h) despite GRIND_TREND_MINUS_ENABLED=False on line 2036. These are from before the kill took effect (all from today before ~15:00 UTC). New trades should not fire.
