=== Signal Performance Report ===
Date: 2026-08-31 23:10 UTC | Period: Last 6h / 24h

## 24h Summary
- Trades closed: 48 | PnL: -$0.39 | WR: 39.6%
- 7d: 376 trades | PnL: -$1.47 | WR: 49.2%

## KILLED (executed today)
| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| macd-div- | SHORT | 20% | -$0.35 | 5 | KILLED — NEVER_REENABLE (signal_reporter 2026-08-31) |

## KILL CANDIDATES
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| (none) | — | — | — | — | No signals meet kill criteria (WR<30%, 5+ trades, PnL<-$0.10) |

## BOOST CANDIDATES
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| (none) | — | — | — | — | No signals meet boost criteria (WR>55%, 5+ trades, consistent) |

## LOSERS (watch list)
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| ichimoku- | SHORT | 40.0% | -$0.26 | 20 | Monitor — high volume, small losses |
| confluence- | SHORT | 40.0% | -$0.23 | 5 | Borderline — at trade threshold |
| macd-div- | SHORT | 50.0% | -$0.17 | 6 | Already killed as standalone |
| accel-300-v2-long | LONG | 25.0% | -$0.21 | 8 | Watch — but combo version profitable |

## WINNERS
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| bb-bounce-long+ | LONG | 57.1% | +$0.05 | 7 | Healthy |
| accel-300-v2-long | LONG | 36.4% | +$0.07 | 11 | Positive despite low WR (good R:R) |
| accel-300-v2-long,volume-breakout-long+ | LONG | 100% | +$0.38 | 2 | Confluence boost working |

## ISSUES
- No direction inversions found
- SHORT signals (ichimoku-, confluence-) are generating most volume but losing small amounts
- System overall slightly negative (-$0.39/24h) — within noise range
- MACD divergence already killed today — no further action needed

## Action Taken
- Killed `macd-div-` SHORT via NEVER_REENABLE_FLAGS (signal_reporter 2026-08-31)
- No additional kills or boosts warranted — all signals within normal range
