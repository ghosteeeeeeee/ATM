# Signal Performance Report
**Generated:** 2026-10-27 (run) | **Period:** Last 6h + 24h

## KILLED (executed):
| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| — | — | — | — | — | None met kill criteria (24h) |

## BOOSTED (executed):
| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| — | — | — | — | — | None met boost criteria (bb-squeeze+ failed multi-token: 5T all hyperliquid; also DEPRIORITIZED 2026-10-10 on 14d zero-edge data) |

## LOSERS (watch list):
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| bb-bounce-v2-long+ | LONG | 33.3% (7d) | -0.36 (7d) | 18 (7d) / 1 (24h) | WATCH — chronic 7d loser, 24h volume too low to kill |
| continuation+ | LONG | 50.0% | -0.16 | 2 | WATCH — 24h sample too small |
| volume-buildup- | SHORT | 66.7% | -0.07 | 3 | WATCH — WR fine, slight negative PnL (R:R) |
| pump-chain+ | LONG | 47.4% (7d) | -0.41 (7d) | 19 (7d) / 3 (24h) | WATCH — 7d chronic, but 24h at 100% WR +0.28 (recovering) |

## WINNERS:
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| bb-squeeze+ | LONG | 60.0% | +0.37 | 5 | KEEP — single token, no boost (multi-token rule) |
| pump-chain+ | LONG | 100.0% | +0.28 | 3 | KEEP |
| warrior-sr-confirm+ | LONG | 100.0% | +0.06 | 2 | KEEP |
| continuum-osc+ | LONG | 100.0% | +0.02 | 1 | KEEP |

## 6h Performance:
| Signal | Dir | Trades | WR | PnL |
|--------|-----|--------|-----|-----|
| bb-squeeze+ | LONG | 2 | 100.0% | +0.38 |

## ISSUES:
- No signal inversions in 24h (long/short name vs direction check clean).
- Low trade volume overall: 20 closed trades in 24h, 2 in 6h — sample sizes below action thresholds.
- Note: ad-hoc "name/direction mismatch" query using `signal LIKE '%-%'` produces false positives on hyphenated names (bb-bounce-v2-long+); authoritative check is long/short substring only — that returned zero.

---
*No kills, no boosts this cycle. Next report: ~6h.*
