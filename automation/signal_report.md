=== Signal Performance Report ===
Period: 2026-08-17 10:30 UTC | Last 6h: 9 trades, -$0.21 | Last 24h: 38 trades, +$0.48

## KILLED (executed):
| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| range_breakout_short | SHORT | 46.4% | -$0.21 | 28 (7d) | KILLED — re-enabled test failed. Last 2 trades ATR SL hits. Added to NEVER_REENABLE. |

## BOOSTED: None
No signals meet boost criteria (WR >55%, 5+ trades, PnL > $0.05, consistent across tokens).

## LOSERS (watch list):
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| r2-trend-long3 | LONG | 33.3% | -$0.11 | 6 (24h) | WATCH — overall 55.6% WR (18T), 24h slump may be noise |
| bb_bounce+ | LONG | 0.0% | -$0.04 | 2 (24h) | WATCH — overall 58.3% WR (24T), not enough 24h trades |

## WINNERS:
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| bb_bounce+,hl_copy_trader | LONG | 100.0% | +$0.26 | 2 (24h) | Good |
| hzscore-,tl_break_short | SHORT | 100.0% | +$0.10 | 1 (24h) | Combo fired before kill — hzscore dead now |
| ct-hot+,rs-s53 | LONG | 100.0% | +$0.09 | 1 (24h) | ct-hot killed, combos may still fire from compactor |
| r2-trend-long2 | LONG | 64.7% | +$0.19 | 17 (7d) | Best r2_trend variant |
| stop_hunt_reversal_long+ | LONG | 66.7% | +$0.03 | 3 (24h) | Consistent |

## ISSUES:
- No direction inversions detected
- hzscore- killed Aug 17 — last trades were Aug 16, kill working
- ct-hot killed Aug 17 — combos (ct-hot+,rs-s46, ct-hot+,rs-s53) still appearing in 24h from compactor (trades opened before kill)
- range_breakout_short RE-KILLED — was re-enabled Aug 16 for testing, test failed (2/2 ATR SL hits in 6h)

## SYSTEM TOTALS:
- 24h: 38 trades, +$0.48 PnL (positive but slim)
- 6h: 9 trades, -$0.21 PnL (small negative)
- No critical bugs found
