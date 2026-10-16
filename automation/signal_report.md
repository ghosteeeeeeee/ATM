# Signal Performance Report

Period: Last 6h | 24h
Generated: 2026-10-16 20:15 UTC

## KILLED (executed):
| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| (none) | | | | | No new kills |

All kill candidates from this window were already regime-blocked by earlier
signal_reporter runs today (committed 14:44 UTC, pipeline restarted 20:15 UTC,
blocks verified live via gate unit check):

- **pump-chain- SHORT** — EXTREME 0.0 block live (8T 0% WR, -$0.49/24h, all EXTREME).
  NORMAL 1.2 boost kept (14d 64% WR +$0.48 habitat). HIGH hard-blocked via
  PUMP_CHAIN_SHORT_HIGH_BLOCK_ENABLED. Signal alive, correctly routed.
- **bb-bounce-v2-long+ LONG** — EXTREME 0.0 block live (24h EXTREME 3T all losers).
  NORMAL +$0.55 / FLAT 100% WR kept.
- **doji-bottom-long LONG** — removed from EXTREME REGIME_SIGNALS (3T 0% WR falling knife).
  HIGH 57% / NORMAL 60% kept.

## BOOSTED (executed):
| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| (none) | | | | | No boost candidates |

Closest: ai-trader+ LONG 60% WR but $0.00 PnL (5T). volume-buildup- SHORT 75% WR
but -$0.03 (4T, one big loser). Neither meets WR>55% + 5T + PnL>$0.05.

## LOSERS (watch list):
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| doji-bottom-long | LONG | 45.5% | -$0.51 | 11 | Regime-correct post-block. Loss = exit quality: atr_sl_hit 3T -$0.45 + hard_max_loss -$0.10 vs profit-trail 6T +$0.17. SL too wide for entry, not a regime problem. |
| bb-bounce-v2-long+ | LONG | 33.3% | -$0.27 | 6 | EXTREME blocked. 30d NORMAL 52.2% +$0.55, HIGH 56.3% -$0.07. 24h loss predates block. |
| volume-buildup- | SHORT | 75.0% | -$0.03 | 4 | One loser wipes 3 winners. 30d NORMAL-only 87.5% +$0.38. Small-n, watch. |
| pump-chain- | SHORT | 0.0% | -$0.49 | 8 | All EXTREME, blocked. Trades closed 01:58–14:28, before 14:44 commit. Post-block verdict in next report. |

## WINNERS:
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| ai-trader+ | LONG | 60.0% | $0.00 | 5 | Breakeven. Active. |
| pump-chain+ | LONG | 33.3% | +$0.41 | 3 | Positive PnL, low WR (2/3 losers, 1 big winner). EXTREME habitat. |
| volume-buildup- | SHORT | 75.0% | -$0.03 | 4 | See watch list — high WR, negative PnL. |

## ISSUES:
- **None.** Zero direction inversions in 24h. No new bugs found.
- ai-trader-manual (3T 33.3% LONG, 2T 0% SHORT, -$0.10 combined) — manual overrides, not signal-gated. Not actionable by signal_reporter.
- Gate verification: pump-chain- EXTREME=0.0, NORMAL=1.2, bb-bounce-v2-long+ EXTREME=0.0, doji-bottom-long EXTREME=removed. All confirmed via `_get_signal_type_mult` live check.
