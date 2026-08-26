=== Signal Performance Report ===
Period: 2026-08-26 ~12:00 UTC | Last 6h + 24h

KILLED (executed):
| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| bb_bounce+ | LONG | 12.5% | -$0.55 | 8 | KILLED — WR<30%, PnL<-$0.10, 5+ trades. Added to NEVER_REENABLE_FLAGS. |

BOOSTED (executed):
| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| (none) | — | — | — | — | No signals meet all boost criteria (WR>55%, 5+ trades, PnL>$0.05) |

LOSERS (watch list):
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| continuation- | SHORT | 0.0% | -$0.37 | 3 | WATCH — 0% WR but only 3 trades (below 5 threshold). Monitor next 6h. |
| slow-grind- | SHORT | 37.5% | -$0.34 | 8 | Already killed by CEO 2026-08-26. Confirmed in NEVER_REENABLE_FLAGS. |
| pump-catcher+ | LONG | 50.0% | -$0.04 | 4 | BORDERLINE — break-even PnL, needs more data. |

WINNERS:
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| cascade-reverse-v2-mtf_alignment+cascade_active | SHORT | 66.7% | +$0.48 | 3 | Good but <5 trades, can't boost yet. |
| macd-div- | SHORT | 100.0% | +$0.21 | 3 | Perfect but <5 trades, watch for consistency. |
| bb-bounce-short | SHORT | 100.0% | +$0.07 | 3 | Perfect but <5 trades. |
| r2-trend-short4 | SHORT | 100.0% | +$0.15 | 2 | Perfect, too few trades. |

ISSUES:
- No direction inversions detected (clean).
- continuation- SHORT at 0% WR needs monitoring — if next 6h has more losses, kill.
