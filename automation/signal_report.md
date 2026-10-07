# Signal Performance Report

Period: Last 6h | 24h
Generated: 2026-10-07 23:09 UTC

## 6h Performance (HAVING >= 2)
| Signal | Dir | Trades | WR | PnL |
|--------|-----|--------|-----|-----|
| pump-chain+ | LONG | 2 | 50.0% | +$0.01 |

## 24h Performance (HAVING >= 3)
| Signal | Dir | Trades | WR | PnL |
|--------|-----|--------|-----|-----|
| pump-chain- | SHORT | 8 | 25.0% | +$0.76 |
| pump-chain+ | LONG | 4 | 25.0% | -$0.20 |
| pump-chain-v5 | LONG | 1 | 0.0% | -$0.06 |

Only pump-chain family traded in the last 24h (13 closed trades total).

## KILLED (executed)
| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| — | — | — | — | — | none |

No kill candidates met ALL criteria (WR<30% AND 5+ trades AND PnL<-$0.10 AND active>24h).

## BOOSTED (executed)
| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| — | — | — | — | — | none |

No boost candidates met ALL criteria (WR>55% AND PnL>$0.05 AND 5+ trades).

## LOSERS (watch list)
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| pump-chain+ | LONG | 25.0% | -$0.20 | 4 | WATCH — 1 trade short of kill threshold (need 5). 3/4 exits hard_max_loss, avg loser ~$0.09. All-time regimes: EXTREME 48.4%WR +$2.07 (edge), HIGH 37.9%WR -$0.04 (noise), NORMAL 20%WR -$0.35 (5T only). HIGH_BLOCK=False. 48h EXTREME 3T 0%WR -$0.27 — short-window noise vs 62T all-time +$2.07. Do NOT kill: EXTREME edge is real and PUMP_FLOW_PLUS_ENABLED was CEO re-enabled 2026-10-07. |
| pump-chain-v5 | LONG | 0.0% | -$0.06 | 1 | WATCH — re-enabled 2026-10-07 CEO (68.3% all-time bare form). Single trade insufficient. |

## WINNERS
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| pump-chain- | SHORT | 25.0% | +$0.76 | 8 | PROFITABLE low-WR profile — winners ~$0.53-0.61 (atr_trail/trail_sl) vs losers ~$0.03-0.12 (hard_max_loss). R:R carries PnL despite 25% WR. All-time regimes: NORMAL 64.3%WR +$0.22 (edge), HIGH 42.9%WR -$0.48 (bleed), EXTREME 50.0%WR -$0.07 (breakeven). HIGH_BLOCK already True. EXTREME block False (CEO reverted — "every dump is a SHORT"). DEFENSES ACTIVE: SHORT_HIGH_BLOCK=True, SHORT_RSI_MIN=45, CUT_LOSER_PNL. No action. |

## Regime Checks (kill-candidate due diligence)
- pump-chain+ : NO regime >=55% WR. EXTREME is the only profitable regime (+$2.07/62T). Blanket kill not warranted (also fails 5+ trade count).
- pump-chain- : NORMAL 64.3% WR (14T) >=55% → regime-route, not kill. Already routed: HIGH_BLOCK=True. 24h net POSITIVE anyway.

## Inversions
None. GOAT LONG 24h was signal `pump-chain-v5` (LONG signal, correct direction). All-time pump-chain direction/sign mismatch count: 0.

## Exit Pattern Notes (24h)
- pump-chain+ : 3 hard_max_loss (-$0.27) + 1 pump_exit_dead_money (+$0.07). No trail winners — stops firing before momentum.
- pump-chain- : 5 hard stops (-$0.38) vs 2 trail winners (+$1.14). Classic asymmetric R:R — winners need trail room, losers are cut small. Working as designed.

## ISSUES
- Low trade volume system-wide: only 13 closed trades / 24h across 3 signals. Quiet regime or slot starvation — not a signal-quality problem.
- pump-chain+ NORMAL regime 20% WR / -$0.35 on 5 all-time trades — sample too small to gate, but if NORMAL continues bleeding, consider NORMAL block (mirrors SHORT_HIGH_BLOCK pattern).
- pump-chain+ 24h losers all hard_max_loss with tight stops (~1.3%): verify pump_exit is actually managing trail for LONG or if RR engine is overriding.

## Actions Taken
NONE. No kills, no boosts, no flag changes, no vol-gate edits. Criteria not met. Report-only cycle.
