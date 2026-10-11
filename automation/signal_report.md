# Signal Performance Report

Generated: 2026-10-11 06:40 UTC
Period: Last 6h | 24h (21 closed trades in 24h, 2 in 6h — low activity)

KILLED (executed):
| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| — | — | — | — | — | none — no signal met kill criteria in 24h |

BOOSTED (executed):
| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| — | — | — | — | — | none — top winners (ai-trader+, doji-bottom-long) had only 4 trades each, below 5-trade boost threshold |

LOSERS (watch list):
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| volume-breakout-long+ | LONG | 0% | -$0.23 | 2 (24h) | WATCH: 7d = 12 trades, 25% WR, -$0.73. No winning regime (EXTREME 20%/-0.15, HIGH 37.5%/-0.46). 24h count too low to kill by rule — next run, kill if 5+ trades accumulate or add regime gate |
| r2v2-long3/4/8 | LONG | 0% | -$0.26 | 3 (24h) | WATCH: r2v2 EXTREME regime 7d = 0% WR n=3. Noise-level volume |
| hmacd_mtf-+ | LONG | 0% | -$0.02 | 1 (24h) | WATCH: 7d EXTREME 25% WR n=4, -$0.21 |
| bb-squeeze+ | LONG | — | — | 0 (24h) | WATCH: 7d = 22 trades, 59.1% WR but -$0.55 PnL (R:R problem). HIGH regime -0.53. No 24h activity |
| bb-bounce-v3-long+ | LONG | — | — | 0 (24h) | WATCH: 7d NORMAL 42.9% WR, -$0.42 |
| mtf-regime-trend- | SHORT | — | — | 0 (24h) | WATCH: 7d 40% WR, -$0.42 |

WINNERS:
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| doji-bottom-long | LONG | 75% | +$0.35 | 4 (24h) | Healthy — one more trade qualifies for boost next run |
| ai-trader+ | LONG | 75% | +$0.07 | 4 (24h) | Healthy — one more trade qualifies for boost next run |
| pump-chain+,pump-chain-v6+ | LONG | 33.3% | +$0.39 | 3 (24h) | Profitable but WR low; pump-chain+ 7d = 52.9% WR +$1.32 |

ISSUES:
- Direction inversions (24h): 0 — clean
- Open trades: 0
- Low trade volume (21 closes/24h) — insufficient data for most kill/boost rules; decisions deferred to next 6h run
- bb-squeeze+ is a structural R:R problem on 7d (high WR, negative PnL) — candidate for TP/SL review, not a kill
