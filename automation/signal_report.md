=== Signal Performance Report ===
Generated: 2026-08-24 | Period: 6h + 24h

## KILLED (executed): None
No signals met strict kill thresholds (WR<30%, 5+ trades, PnL<-$0.10, 24h active).

## DEAD (already killed, residual trades in window):
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| macd-div+ | LONG | 20.0% | -$0.55 | 5 | KILLED 2026-08-23 (pre-kill trades) |
| hzscore- | SHORT | 28.6% | -$0.04 | 7 | KILLED + NEVER_REENABLE (pre-kill trades) |

## BOOSTED (executed):
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| bb_bounce+ | LONG | 80.0% | +$0.32 | 5 | Weight 1.35 — maintained |
| tl_break_short | SHORT | 83.3% | +$0.11 | 6 | Weight 1.2 — maintained |

## WINNERS:
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| bb_bounce+ | LONG | 80.0% | +$0.32 | 5 | Strong, weight already boosted |
| tl_break_short | SHORT | 83.3% | +$0.11 | 6 | Strong, weight already boosted |
| ct-hot+ | LONG | 48.0% | +$0.23 | 25 | Profitable, high volume, weight 1.0 |

## WATCH LIST (no kill yet):
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| ct-hot- | SHORT | 0.0% | -$0.15 | 2 | Low volume, monitor |
| hl_copy_trader | LONG | 33.3% | -$0.07 | 3 | Below threshold, weight already 0.3 |

## LOSERS (no action needed):
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| hl_copy_trader | LONG | 33.3% | -$0.07 | 3 | Watch, below kill threshold |

## ISSUES:
- Composite signals appearing: `ct-hot-,tl_break_short,tl_break_short` (2T, 0% WR, -$0.23) — multi-signal combo with poor performance
- `macd-div+` trades still in 24h window despite kill — likely pre-kill closures
- No signal inversions detected
