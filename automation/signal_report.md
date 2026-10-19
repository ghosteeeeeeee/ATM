# Signal Performance Report
**Generated:** 2026-10-19 03:32 UTC | **Period:** Last 6h + 24h

## Summary
Very quiet period: **13 closed trades in 24h** (3 in 6h), net **-$0.32**. No signal+direction pair reached the 5-trade threshold, so **no kills or boosts executed**. No inversions.

---

## KILLED (executed):
| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| — | — | — | — | — | none (no candidates met criteria) |

## BOOSTED (executed):
| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| — | — | — | — | — | none (no candidates met criteria) |

## LOSERS (watch list):
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| bb-bounce-v2-long+ | LONG | 0.0% | -$0.18 | 2 (24h) / 16 (7d, 31.3%, -$0.61) | watch — 24h sample too small to kill; 7d persistent bleed |
| hl_copy_trader | LONG+SHORT | 0.0% | -$0.11 | 2 (24h) | watch |
| pump-chain- | SHORT | 21.9% | -$0.55 | 32 (7d) | watch — large 7d bleed, only 1 trade in 24h |
| doji-bottom-long | LONG | 31.3% | -$0.97 | 16 (7d) | watch — worst 7d PnL, 0 trades in 24h |
| ai-trader+ | LONG | 31.3% | -$0.68 | 16 (7d) | watch — 1 win in 24h |
| hmacd_mtf- | LONG | 20.0% | -$0.33 | 5 (7d) | watch |

## WINNERS:
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| continuum-trend+ | LONG | 100% | +$0.03 | 1 (24h) | healthy |
| ai-trader+ | LONG | 100% | +$0.05 | 1 (24h) | healthy |
| ai-trader-manual | LONG | 100% | +$0.05 | 1 (24h) | healthy |
| pump-chain-,pump-chain-v6- | SHORT | 100% | +$0.07 | 1 (24h) | healthy |
| volume-buildup- | SHORT | 77.8% | +$0.35 | 9 (7d) | healthy |

---

## ISSUES:
- **`close_time` is naive UTC in brain DB** — comparing with timezone-aware Python datetimes silently returns 0 rows (psycopg2 sends aware params as timestamptz). Query scripts must strip tzinfo (`datetime.now(timezone.utc).replace(tzinfo=None)`) or the 6h/24h windows look empty. Flag for pipeline query hygiene.
- Volume very low this period (13 trades/24h) — kill/boost thresholds unreachable. Next runs should watch 7d losers above if 24h volume stays sparse; if bb-bounce-v2-long+ / doji-bottom-long / pump-chain- SHORT continue bleeding, consider regime-gated blocks (check `volatility_regime` win rates before any blanket kill).
- 2 open trades at report time.
