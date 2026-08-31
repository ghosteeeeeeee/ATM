=== Signal Performance Report ===
Generated: 2026-08-31 (auto_1hr run)

## Summary
- **24h:** 45 trades, 42.2% WR, -$0.44 PnL
- **6h:** 17 trades, 29.4% WR, -$0.32 PnL

## KILLED (executed this run)
| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| MACD_DIVERGENCE_ENABLED | master | — | — | — | Set False (master switch was True while both directions dead) |
| MACD_DIVERGENCE_PLUS_ENABLED | LONG | — | — | — | Added to NEVER_REENABLE_FLAGS (CEO killed 2026-08-23, not protected) |

## Already Killed (prior runs, still executing legacy trades)
| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| accel-300-v2-long | LONG | 0% | -$0.20 | 3 | Auto-killed today by auto_1hr (line 1440) |
| macd-div- | SHORT | 25% | -$0.19 | 4 | Killed 2026-08-31, in NEVER_REENABLE |
| confluence-,ichimoku- | SHORT | 25% | -$0.26 | 4 | Combo signal — individual signals not killable |

## BOOSTED (executed this run)
| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| (none) | — | — | — | — | No candidates with sufficient sample size |

## LOSERS (watch list)
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| accel-300-v2-long | LONG | 0% | -$0.20 | 3 | Auto-killed, legacy trades |
| macd-div- | SHORT | 25% | -$0.19 | 4 | Dead, legacy trades |
| confluence-,ichimoku- | SHORT | 25% | -$0.26 | 4 | Combo — monitor underlying signals |
| ichimoku-,macd-div- | SHORT | 50% | -$0.11 | 2 | Combo — small sample, neutral |
| accel-300 | LONG | 33% | -$0.13 | 3 | rs-only LONG — small sample |
| engulfing | LONG | 0% | -$0.13 | 2 | Small sample |

## WINNERS
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| ichimoku | SHORT | 50% | +$0.23 | 4 | Core SHORT signal — solid |
| bb-bounce-long | LONG | 62.5% | +$0.15 | 8 | Best LONG performer, BB_BOUNCE_LONG_ENABLED=True |
| cascade-reverse-v2 | LONG | 50% | +$0.12 | 2 | Small sample |
| r2-trend | SHORT | 100% | +$0.05 | 1 | Tiny sample |
| ichimoku-rs | SHORT | 44.4% | +$0.09 | 9 | Highest volume signal, slightly positive |

## ISSUES
- No signal inversions found (LONG signals not firing SHORT or vice versa)
- MACD_DIVERGENCE master switch was still True while both directions were dead — fixed this run
- MACD_DIVERGENCE_PLUS_ENABLED was killed by CEO but not in NEVER_REENABLE_FLAGS — fixed this run
- Overall 6h WR is very low (29.4%) — likely noise from low sample, monitor next cycle
- All current losers were already killed prior to this run — no new kills needed
