=== Signal Performance Report ===
Period: 2026-08-28 23:08 UTC — Last 6h | 24h

KILLED (executed):
None — no signals meet kill criteria (WR < 30% with 5+ trades AND PnL < -$0.10 over 24h).

BOOSTED (executed):
| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| bb-bounce-short | SHORT | 81.8% | +$0.20 | 11 | Already boosted (compactor weight 1.5x) |

LOSERS (watch list):
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| accel-300-v2- | SHORT | 33.3% | $0.00 | 12 (6h) | Flat in last 6h; 24h WR 53.2% +$1.41 — not a kill |

WINNERS:
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| accel-300-v2- | SHORT | 53.2% | +$1.41 | 62 (24h) | Volume workhorse, steady profit |
| bb-bounce-short | SHORT | 81.8% | +$0.20 | 11 (24h) | High WR, consistent across tokens |

ISSUES:
- No signal inversions detected.
- `accel-300-v2-` had 0% WR on 5 tokens in last 6h (ZEN, CC, HYPE, PUMP, YGG) — each -$.09. Likely noise, not a kill signal yet. Monitor.
- Combined signal names (e.g. `accel-300-v2-,rs-r156`) show scattered 1-trade losses — these are compactor combos, not standalone signal failures.
