# Signal Performance Report

Period: Last 6h | 24h (as of 2026-10-23 03:33 UTC)

## KILLED (executed)
| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| — | — | — | — | — | None qualified |

## BOOSTED (executed)
| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| — | — | — | — | — | None qualified |

## LOSERS (watch list)

24h (all under kill threshold — max 2 trades per signal+direction):
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| ai-trader-pending | SHORT | 50.0% | +0.08 | 2 | watch |

7d context (NOT kill-eligible under 24h criteria, but bleeding):
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| pump-chain+ | LONG | 6.7% | -1.29 | 15 | WATCH — no trades 48h; stale/HIGH-regime/BTC guards likely gating it already |
| ai-trader+ | LONG | 38.5% | -0.67 | 13 | watch |
| doji-bottom-long | LONG | 40.0% | -0.53 | 10 | watch |
| pump-chain- | SHORT | 0.0% | -0.47 | 8 | watch — RSI floor reverted to 45 on 2026-10-21 |
| bb-bounce-v2-long+ | LONG | 50.0% | -0.45 | 20 | watch — WR ok, exit/R:R drag |

## WINNERS
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| warrior-sr-confirm- | SHORT | 100.0% | +0.15 | 2 | healthy (under 5T boost bar) |
| bb-squeeze+ | LONG | 100.0% | +0.12 | 1 | healthy |
| volume-buildup- | SHORT | 100.0% | +0.08 | 1 | healthy |
| ai-trader-pending | SHORT | 50.0% | +0.08 | 2 | healthy |

24h net (all closed): **6 trades, +$0.43, 83.3% WR (5W/1L)**

## ISSUES
- **No signal met kill criteria this window** (needs 5+ trades, WR<30%, PnL<-$0.10 in 24h). No boost candidates either (needs 5+ trades; max was 2). Nothing executed.
- **Zero direction inversions** in 24h — no bug.
- **Low execution volume**: 800 signals generated in 24h → only 6 closed trades (0.75%). Pipeline alive and firing (last signal 03:33 UTC); likely gate filtering, but worth watching if closes stay near zero next window.
- 6h window had 0 closed trades meeting HAVING >=2 (3 single-trade closes happened).
