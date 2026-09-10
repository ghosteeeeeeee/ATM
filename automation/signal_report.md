=== Signal Performance Report ===
Period: 2026-09-10 ~14:30 UTC | Window: 6h / 24h
Total: 14 trades (6h, +$1.75) | 42 trades (24h, +$3.97, 64.3% WR)

KILLED (executed):
| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| (none) | — | — | — | — | No kill candidates. All signals with 3+ trades are profitable. |

BOOST CANDIDATES (watch):
| Signal | Dir | WR | PnL | Trades | Notes |
|--------|-----|-----|-----|--------|-------|
| pump-chain- | SHORT | 90.0% | +$1.27 | 10 | DOMINANT — 90% WR, smallest loss -$0.14. Reliable across 24h. |
| pullback-entry- | SHORT | 76.5% | +$2.16 | 17 | TOP PnL — highest absolute profit, 17 trades. Already boosted. |

LOSERS (watch list):
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| pullback-entry+ | LONG | 0.0% | -$0.23 | 2 | 0% WR but only 2T — in NEVER_REENABLE_FLAGS already |
| open-skies+ | LONG | 0.0% | -$0.23 | 1 | Single trade, too early to judge |
| pump-chain-,r2-trend-short4 | SHORT | 0.0% | -$0.18 | 1 | Combo signal, single trade |
| accel-300-v4-short- | SHORT | 50.0% | +$0.18 | 2 | Breakeven — watch for edge decay |

WINNERS:
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| pullback-entry- | SHORT | 76.5% | +$2.16 | 17 | TOP PERFORMER — highest PnL |
| pump-chain- | SHORT | 90.0% | +$1.27 | 10 | BEST WR — 90% with meaningful volume |
| pump-chain+ | LONG | 50.0% | +$0.45 | 2 | Early but profitable |
| mover- | SHORT | 75.0% | +$0.07 | 4 | Small sample, profitable |
| accel-300-v4-short- | SHORT | 50.0% | +$0.18 | 2 | Breakeven |

7d WATCH LIST (signals losing over 7d):
| Signal | Dir | Trades | WR | PnL | Status |
|--------|-----|--------|-----|-----|--------|
| ema300_dip_short | SHORT | 24 | 41.7% | -$1.48 | DISABLED (EMA300_DIP_SHORT_ENABLED=False) |
| ema300_dip | LONG | 35 | 60.0% | -$1.01 | ENABLED — 60% WR but still net negative (tight TP/SL) |
| slow_grind | LONG | 15 | 40.0% | -$0.80 | DISABLED (NEVER_REENABLE) |
| sma20_dip | LONG | 19 | 42.1% | -$0.73 | DISABLED (SMA20_DIP_PLUS_ENABLED=False) |
| coiled_spring | LONG | 21 | 42.9% | -$0.65 | ENABLED — regime-filtered |
| pullback-entry+ | LONG | 6 | 16.7% | -$0.57 | NEVER_REENABLE — 16.7% WR |
| accel_300_v3_long | LONG | 9 | 44.4% | -$0.54 | ENABLED — re-enabled with EXTREME block |

ISSUES:
- No signal inversions detected
- No kill candidates in 24h window (all signals with 3+ trades are positive)
- ema300_dip LONG has 60% WR but -$1.01 PnL over 7d — possible R:R sizing issue (wins are small, losses are larger)
- ema300_dip_short is the worst 7d performer (-$1.48) but is already correctly disabled
- Total 24h system PnL: +$3.97 across 42 trades — healthy positive edge
