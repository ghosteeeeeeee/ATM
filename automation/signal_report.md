=== Signal Performance Report ===
Period: 2026-09-23 ~17:08 UTC | Last 6h + 24h

## KILLED (executed):
| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| accel-300-breakout | SHORT | 28.6% | -$0.12 | 7 | ACCEL_300_BREAKOUT_ENABLED=False. ALL trades EXTREME. In NEVER_REENABLE (was incorrectly re-enabled 2026-08-12). |

## BLOCKED (regime):
| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| mover+ | LONG | 33.3% | -$0.34 | 3 | Mover EXTREME multiplier 1.2→0.0x. EXTREME drags: 4/7 wins but -$0.48 lifetime. HIGH/NORMAL still profitable. |

## BOOSTED: None

## WINNERS:
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| pump-chain- | SHORT | 62.5% | +$0.33 | 8 | Active, performing well |

## LOSERS (watch list):
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| mover+ | LONG | 33.3% | -$0.34 | 3 | EXTREME blocked. Watch HIGH/EXTREME split. |
| bb-bounce-v2-long+ | LONG | 50.0% | $0.00 | 8 | Breakeven — no action needed |

## ISSUES:
- accel-300-breakout was in NEVER_REENABLE list (line 1653) but ACCEL_300_BREAKOUT_ENABLED was True. Flag now correctly False.
- accel-300-breakout not in FAMILY_MAP — had no regime filtering, bypassed volatility_gate_v2 entirely.
- No direction inversions detected.
