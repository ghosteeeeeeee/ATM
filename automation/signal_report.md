# === Signal Performance Report ===
**Period:** Last 6h | 24h  
**Generated:** 2026-09-18 11:30 UTC

## KILLED (executed):
None — no new kills this cycle.

## Previous kills verified:
- **open-skies+** — Already killed 2026-09-17 (11T/8d, 36.4% WR, -$0.73). All regime blocks confirmed. Trades in 24h window are pre-kill entries that just closed. In NEVER_REENABLE_FLAGS.
- **open-skies-** — Already killed 2026-09-17 (SHORT not applicable). In NEVER_REENABLE_FLAGS.
- **pullback-entry+** — Already killed 2026-09-10 (CEO, 0% WR). In NEVER_REENABLE_FLAGS.

## BOOSTED (executed):
None — no boost candidates met all criteria.

## REGIME GATES (verified):
| Signal | EXTREME | NORMAL | HIGH | Status |
|--------|---------|--------|------|--------|
| pullback-entry- | 1.0x ✅ | 0.0x ✅ BLOCKED | 0.5x ✅ PENALIZED | Correct |
| volume-breakout-long+ | 1.0x (default) | 1.0x (default) | 0.0x BLOCKED | Correct |

## LOSERS (watch list):
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| open-skies+ | LONG | 0% | -$0.61 | 4 | KILLED — pre-kill entries closing |
| pullback-entry- | SHORT | 20% | -$0.59 | 5 | WATCH — gate working, recent variance |

## WINNERS:
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| volume-breakout-long+ | LONG | 75% | +$0.34 | 8 | 100% WR in EXTREME |
| doji-bottom-long | LONG | 100% | +$0.13 | 1 | Insufficient sample |
| r2-trend-long8 | LONG | 100% | +$0.12 | 1 | Insufficient sample |
| warrior-sr-confirm+ | LONG | 100% | +$0.04 | 1 | Insufficient sample |
| mover+ | LONG | 100% | +$0.03 | 1 | Insufficient sample |
| grind-breakout+ | LONG | 100% | +$0.01 | 1 | Insufficient sample |

## 24h COMPOSITE:
- **Total trades:** 24
- **Total PnL:** +$0.09 (slightly positive)
- **Overall WR:** ~38% (most losses are small ATR SL hits)

## ISSUES:
- **Low volume (Sept 17):** Only 6 trades created vs normal 25-53/day. One-day dip, recovered next day.
- **No signal inversions detected.**
- **pullback-entry- NORMAL losses:** AIXBT (-$0.14) and ALT (-$0.15) entered NORMAL regime despite 0.0x gate. Likely entered before gate deployment (Sept 17). Monitor next cycle.

## SYSTEM HEALTH:
- ✅ Pipeline running (last trade created 10 min ago)
- ✅ 1 open position
- ✅ No lock file stuck
- ✅ All kill flags verified False in hermes_constants.py
