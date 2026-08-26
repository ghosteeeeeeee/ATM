=== Signal Performance Report ===
Period: Last 6h | 24h | Generated: 2026-08-26 ~23:10 UTC

KILLED (executed):
| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| bb_bounce+ | LONG | 16.7% | -$0.29 | 6 (24h) | BB_BOUNCE_ENABLED=False + NEVER_REENABLE. Trades bypass BB_BOUNCE_PLUS_ENABLED check. |

BOOSTED (executed):
| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| (none) | - | - | - | - | No candidates meet 5+ trade threshold |

LOSERS (watch list):
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| slow-grind- | SHORT | 36.4% | -$0.62 | 11 (24h) | ALREADY KILLED — flag=False, NEVER_REENABLE. Bypass suspected. |
| pump-catcher+ | LONG | 40.0% | -$0.38 | 10 (24h) | Watch — new signal (today), may need tuning |

WINNERS:
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| bb-bounce-short | SHORT | 100% | +$0.07 | 3 | Small sample, keep watching |
| macd-div- | SHORT | 75% | +$0.20 | 4 | Strong, small sample |
| cascade-reverse-v2... | SHORT | 66.7% | +$0.48 | 3 | Strong, small sample |

ISSUES:
- CRITICAL: bb_bounce+ trades bypass BB_BOUNCE_PLUS_ENABLED=False check. Root cause: bb_bounce.py sets signal_type='bb_bounce' (bare) but source='bb_bounce+'. The signal_schema.py check for _comp=='bb_bounce' only checks BB_BOUNCE_ENABLED (was True). Fixed by setting BB_BOUNCE_ENABLED=False.
- slow-grind- trades still appearing despite SLOW_GRIND_SHORT_ENABLED=False. May be pre-disable trades in 24h window, or bypass bug similar to bb_bounce.
- No signal inversions detected (24h).
