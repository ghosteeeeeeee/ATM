# Signal Performance Report

Period: Last 6h | 24h
Generated: 2026-10-21 ~20:40 UTC

KILLED (executed):
| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| — | — | — | — | — | none met kill criteria |

BOOSTED (executed):
| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| — | — | — | — | — | none met boost criteria |

LOSERS (watch list):
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| pump-chain+ | LONG | 0.0% | -$0.32 | 6 (24h) | EXTREME habitat still +$1.99/30d (22W/59T) — 24h is variance window. HIGH already blocked (c9092aea 2026-10-21 03:37), NORMAL already 0.0 in vol gate. Monitor: if EXTREME 7d stays 0% WR, revisit. |
| r2v2-long3 | LONG | 40.0% | -$0.15 | 5 (24h) | Small bleed, no regime win — tuning candidate if persists 24h. |
| continuation+ | LONG | 50.0% | -$0.18 | 4 (24h) | 50% WR but negative PnL — exit quality issue, not entry. Watch. |
| bb-bounce-v2-long+ | LONG | 33.3% | -$0.23 | 3 (6h) | 24h still positive (62.5% +$0.03). 6h window noise. EXTREME already blocked in vol gate. |

WINNERS:
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| bb-bounce-v2-long+ | LONG | 62.5% | +$0.03 | 8 (24h) | Healthy but thin PnL — no boost (needs >$0.05). |
| continuum-trend+ | LONG | 66.7% | +$0.05 | 3 (24h) | Small n, consistent. No boost (needs 5+ trades). |
| pump-chain-,pump-chain-v6- | SHORT | 30.0% | +$0.28 | 10 (7d) | EXTREME combo pocket profitable since Oct 16 gate (+$0.31, 4W/10T). Leave alone. |

ISSUES:
- **Low trade volume**: only 5 signal+direction cells hit n>=3 in 24h. Thin data makes kill decisions high-variance — correct to hold fire this cycle.
- **pump-chain- EXTREME bare gate working**: bare 'pump-chain-' SHORT last opened EXTREME trade Oct 16 14:04 (before 0.0 gate commit 3dabb044 14:44). Combo 'pump-chain-,pump-chain-v6-' still trades EXTREME — intentional (v6 has own validated gates; combo EXTREME +$0.31 since Oct 16).
- **Inversions**: 0 found in 24h. Clean.
- **pump-chain+ HIGH leak closed**: 2 HIGH trades opened 01:03-01:04 UTC today, before HIGH block commit c9092aea at 03:37. No HIGH trades since. Block effective.
