=== Signal Performance Report ===
Period: Last 6h | 24h (generated 2026-10-10 17:14 UTC)

KILLED (executed):
| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| (none) | | | | | No signal met kill criteria (WR<30% + 5T + PnL<-$0.10) |

BOOSTED (executed):
| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| (none) | | | | | No signal met boost criteria (WR>55% + 5T) |

LOSERS (watch list):
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| volume-breakout-long+ | LONG | 33.3% | -$0.23 | 9 | HIGH regime block went live 15:42 UTC (mult=0.0 verified); NORMAL also blocked; EXTREME kept (all-time 72% WR +$3.70). Today's HIGH losses (AIXBT/WCT/BLUR/BABY -$0.73) all opened BEFORE block. Monitor next cycle — block should stop HIGH bleed. |
| hmacd_mtf-- | SHORT | 33.3% | -$0.07 | 3 | n=3 too small to act. All-time EXTREME: 4T 25% -$0.21. Watch. |
| bb-bounce-v2-long+ | LONG | 33.3% | -$0.05 | 3 | n=3 too small. All-time: NORMAL 17T 52.9% +$0.32, HIGH 18T 55.6% -$0.06, FLAT 4T 100% +$0.17. Mixed, no regime action. Watch. |

WINNERS:
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| ai-trader+ | LONG | 100% | +$0.16 | 4 | 4T (1 below boost threshold). Consistent across 4 tokens (CRV/GRASS/NEAR/SYRP all green). Boost if 5T next cycle. |
| pump-chain- | SHORT | 50.0% | +$0.30 | 2 | Small sample, positive. NORMAL SHORT habitat already boosted (1.2x). No action. |
| pump-chain+ | LONG | 100% | +$0.17 | 1 | Single trade. No action. |

ISSUES:
- volume-breakout-long+ HIGH block (Volume family 0.0, volatility_gate_v2.py:307) was added 15:42 UTC today but 6 HIGH trades opened between 02:09-08:51 today (before edit). Pipeline restarted 17:13 — block is now live (verified: get_combined_multiplier returns 0.0 for HIGH). Expect HIGH bleed to stop next cycle. EXTREME habitat untouched (mult=1.0).
- No direction inversions found in 24h (checked long-signal/SHORT and short-signal/LONG mismatches — zero).
- STANDALONE_BYPASS_SIGNALS: not checked this cycle — no evidence of bypass-caused anomalies in trade data.
