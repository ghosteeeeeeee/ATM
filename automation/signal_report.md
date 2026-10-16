=== Signal Performance Report ===
Period: Last 6h | 24h
Generated: 2026-10-16 ~06:00 UTC

Totals: 6h = 8 trades, -$0.32 | 24h = 22 trades, +$0.43

KILLED (executed):
| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| (none) | | | | | No signal met kill criteria (needs WR<30%, 5+ trades, PnL<-$0.10) |

BOOSTED (executed):
| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| (none) | | | | | No signal met boost criteria (needs WR>55%, 5+ trades) |

LOSERS (watch list):
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| pump-chain- | SHORT | 0.0% | -$0.20 | 3 (24h) | WATCH — below 5-trade kill threshold; 7d: 27.6% WR, +$0.04 (n=29). All-time regime: NORMAL 64.3% WR (+$0.48), EXTREME 44.8% (-$0.25), HIGH 46.2% (-$0.42). Not a blanket kill; NORMAL regime edge intact. |

WINNERS:
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| pump-chain+ | LONG | 42.9% | +$0.95 | 7 (24h) | Positive PnL, largest 24h contributor; WR below 55% boost bar. 7d: 34.4% WR, +$0.85 (n=32). |
| ai-trader+ | LONG | 50.0% | +$0.01 | 2 (24h) | Small sample, breakeven |
| hl_copy_trader | LONG | 50.0% | +$0.01 | 2 (24h) | Small sample, breakeven |

ISSUES:
- No direction inversions detected in 24h (0 mismatches).
- Signal volume is low (22 closed trades in 24h) — insufficient data for most kill/boost decisions this cycle.
- pump-chain- SHORT 3 straight SL hits in 6h (atr_sl_hit) but 7d PnL still slightly positive; recheck next cycle if 5+ 24h trades accumulate.
