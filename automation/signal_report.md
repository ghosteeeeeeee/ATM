# Signal Performance Report
**Generated:** 2026-10-04 (verified via brain DB live query)
**Period:** Last 6h + 24h

## Verified Numbers (queried live, not from prior reports)

### 24h (closed trades, HAVING >= 3)
| Signal | Dir | Trades | WR | PnL |
|--------|-----|--------|-----|-----|
| bb-bounce-v3-long+ | LONG | 6 | 50.0% | -$0.05 |
| bb-squeeze+ | LONG | 19 | 68.4% | +$0.37 |

### 6h (closed trades, HAVING >= 2)
| Signal | Dir | Trades | WR | PnL |
|--------|-----|--------|-----|-----|
| bb-squeeze+ | LONG | 8 | 50.0% | -$0.19 |

### Single-trade losers (24h, too thin to act on)
| Signal | Dir | Trades | WR | PnL |
|--------|-----|--------|-----|-----|
| pump-chain- | SHORT | 1 | 0% | -$0.24 |
| volume-breakout-long+ | LONG | 1 | 0% | -$0.11 |
| bb-squeeze+,rs-s102,rs-s114 | LONG | 1 | 0% | -$0.11 |
| continuation+ | LONG | 1 | 0% | -$0.02 |

## KILLED (executed)
None. No signal meets kill criteria (WR < 30% AND PnL < -$0.10 AND 5+ trades 24h).

## BOOSTED (executed)
None new. bb-squeeze+ already boosted to 1.2x on 2026-10-03 23:13 (signal_compactor.py). Auto-tuned combo_weights.json has it at 1.14. EXTREME regime already blocked (0.0x in volatility_gate_v2.py, BB_SQUEEZE_LONG_EXTREME_BLOCK_ENABLED=True). 6h dip (-$0.19, 50% WR) is short-term noise — 7d still 47T 61.7% +$0.50 across 31 tokens.

## LOSERS (watch list)
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| bb-bounce-v3-long+ | LONG | 50.0% | -$0.05 | 6 (24h) | WATCH — does NOT meet kill criteria. 7d: 12T 58.3% +$0.09. Regime: HIGH 60% WR +$0.08, NORMAL 50% -$0.01 (break-even, not losing). Signal active since 2026-09-21. Not a kill, not a boost. Monitor next cycle. |
| pump-chain- | SHORT | 0% | -$0.24 | 1 (24h) | WATCH — single trade, too thin. Signal has 123 total trades since 2026-09-09. |
| volume-breakout-long+ | LONG | 0% | -$0.11 | 1 (24h) | WATCH — single trade, too thin. |

## WINNERS
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| bb-squeeze+ | LONG | 68.4% | +$0.37 | 19 (24h) | ACTIVE + ALREADY BOOSTED. Multi-token consistent: SYRUP 3T/100%/+$0.38, BLUR 2T/100%/+$0.49, ALT 2T/100%/+$0.06. 7d: 47T 61.7% +$0.50 / 31 tokens. EXTREME regime blocked (50% WR -$0.15). HIGH 65.4% +$0.38, NORMAL 66.7% +$0.27 kept. No action needed. |

## Regime Breakdown (full history, HAVING >= 3)

### bb-bounce-v3-long+
| Regime | Trades | Wins | WR | PnL |
|--------|--------|------|-----|-----|
| HIGH | 5 | 3 | 60.0% | +$0.08 |
| NORMAL | 8 | 4 | 50.0% | -$0.01 |

No regime < 50% WR. HIGH wins (60% >= 55% threshold). NORMAL is break-even. No regime block warranted — signal overall not in kill territory.

### bb-squeeze+
| Regime | Trades | Wins | WR | PnL |
|--------|--------|------|-----|-----|
| EXTREME | 12 | 6 | 50.0% | -$0.15 |
| HIGH | 26 | 17 | 65.4% | +$0.38 |
| NORMAL | 9 | 6 | 66.7% | +$0.27 |

EXTREME losing — already blocked via volatility_gate_v2.py 0.0x multiplier (line 328) and BB_SQUEEZE_LONG_EXTREME_BLOCK_ENABLED=True. HIGH/NORMAL winning, correctly kept enabled.

## ISSUES
- **No inversions found** (24h): zero trades where signal name says long but direction=SHORT or vice versa.
- **Thin sample overall**: only 2 signals have >= 3 closed trades in 24h. Pipeline may be undertrading or many signals blocked by gates. Not necessarily a bug — could be regime/filters doing their job.
- **bb-squeeze+ 6h cool-off**: 8T 50% WR -$0.19 in last 6h. 3 hard_max_loss exits (CHIP/USELESS/AIXBT ~-1.0% each) + 1 atr_sl_hit (PURR). 24h and 7d still firmly positive. Not actionable — normal variance for a 68% WR signal.
- **bb-bounce-v3-long+ NORMAL regime at 50%**: break-even, not losing. No action per regime-blocking rules (need < 50% WR to block; HIGH 60% wins so blanket kill inappropriate anyway).

## Actions Taken This Cycle
1. Queried brain DB directly for 6h/24h numbers (did not trust prior report).
2. Checked regime breakdown before any kill consideration.
3. Checked inversions — clean.
4. Verified bb-squeeze+ already boosted + EXTREME-blocked (no double-boost).
5. No kills executed — no signal met criteria.
6. No boosts executed — only boost candidate already boosted.
7. No code changes to hermes_constants.py, volatility_gate_v2.py, or signal_compactor.py.

## Recommendation for Next Cycle
- Monitor bb-bounce-v3-long+ — if 24h WR drops below 30% with 5+ trades AND PnL < -$0.10, re-evaluate. Currently 50% WR -$0.05, far from kill threshold.
- Watch pump-chain- — 1 trade -$0.24 this cycle but 123 total trades historically. Needs more 24h data before any action.
- No OpenMemory store performed (task instruction: skip all OpenMemory calls).
