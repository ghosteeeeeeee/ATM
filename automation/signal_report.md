=== Signal Performance Report ===
Period: Last 6h | 24h
Generated: 2026-09-09

KILLED (executed):
None — no signals met kill criteria (WR < 30%, 5+ trades, active > 24h)

BOOSTED (executed):
None — no clear winners above 55% WR with 5+ trades

LOSERS (watch list — tune candidates):
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| sma20_dip | LONG | 35.7% | -$0.90 | 14 | Tune: WR < 40% with 10+ trades. SMA20_DIP_PLUS already killed 2026-09-08 |
| ema300_dip_short | SHORT | 36.4% | -$0.78 | 11 | Tune: WR < 40% with 10+ trades. Under test protection until 2026-09-09 05:00 UTC |
| bb_bounce_v2_long | LONG | 33.3% | -$0.54 | 6 | Watch: WR < 40%, only 6 trades (below 10 threshold) |
| r2_trend_short | SHORT | 33.3% | -$0.13 | 3 | Watch: only 3 trades, too early to judge |
| pump_chain | LONG | 42.9% | -$0.97 | 14 | Watch: WR borderline, highest PnL loss in absolute terms |

WINNERS:
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| mover | SHORT | 100% | +$0.04 | 2 | N/A — 2 trades only |
| open_skies | LONG | 50% | +$0.01 | 2 | N/A — 2 trades only |

ISSUES:
- No signal inversions detected (24h)
- No signals meet strict kill criteria (WR < 30% + 5+ trades + active > 24h)
- `sma20_dip LONG` is the strongest tune candidate: 14 trades, 35.7% WR, -$0.90 PnL
- `ema300_dip_short SHORT` protected until 2026-09-09 05:00 UTC — cannot kill before then
- 6h volume is low (3 signal combos with 2+ trades) — limited data for action
