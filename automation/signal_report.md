# Signal Performance Report

Period: 2026-10-21 ~03:00 UTC | Last 6h + 24h | brain DB queried directly (not trusted reports)

## KILLED (executed)
| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| (none) | | | | | No signal met full kill criteria (all-regime losers). pump-chain+ EXTREME pocket +$3.89 all-time kept. |

## TUNED (executed)
| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| pump-chain+ | LONG | 0% (24h) | -$0.55 | 6 | `PUMP_CHAIN_LONG_HIGH_BLOCK_ENABLED` False→**True**. HIGH regime all-time 38T 37%WR -$0.48 + 24h HIGH 3T 0W -$0.43. EXTREME 100T +$3.89 kept open. |

## BOOSTED (executed)
| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| (none) | | | | | No 24h candidate cleared boost bar (WR>55% + n>=5 + PnL>$0.05). |

## LOSERS (watch list)
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| pump-chain-,pump-chain-v6- | SHORT | 16.7% | -$0.19 | 6 | Watch. Meets surface kill bar but CEO reverted EXTREME SHORT block 2026-10-07 ("every dump is a SHORT"); HIGH block already on; only -$0.19 in 24h — noise window. Revisit if 7d EXTREME stays <40% WR. |
| r2v2-long3 | LONG | 33.3% | -$0.07 | 7d: 5T 60% +$0.02 EXTREME | Below kill thresholds (n=3). Historical EXTREME edge intact. |

## WINNERS
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| pump-chain+ | LONG | 43% | +$3.89 | 100 (all-time EXTREME) | Edge regime — now fully routed to EXTREME via HIGH block. |
| pump-chain- | SHORT | 60% | +$0.43 | 15 (all-time NORMAL) | Keep; EXTREME 43%WR -$0.54 is the bleed pocket (blocked by floors, not kill). |

## ISSUES
- **Inversions (24h):** none found — no long-named signals closed SHORT or vice versa.
- **Anomaly:** 5 of 6 pump-chain+ LONG losses exited via `trail_arm_timeout` / `hard_max_loss` in a low-BTC-drift window — execution-side, not signal-side. HIGH block removes the worst of these.
- **Pump-chain+ 24h was 0% WR across both its regimes (EXTREME -$0.12, HIGH -$0.43)** — small n (6T); treated as HIGH-regime bleed + noise, not an all-regime kill.
