=== Signal Performance Report ===
Generated: 2026-09-17 11:15 UTC

Period: Last 6h | 24h

KILLED (executed):
| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| (none) | - | - | - | - | - |

BLOCKED (regime):
| Signal | Dir | Regime | Reason |
|--------|-----|--------|--------|
| Pullback_Entry | SHORT | NORMAL | 0/3 (0%) -$0.37 in 24h. All-time 48.3% WR -$0.03. Set multiplier 0.0 in volatility_gate_v2.py |

BOOSTED (executed):
| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| (none) | - | - | - | - | - |

LOSERS (watch list):
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| pullback-entry- | SHORT | 30.8% | -$0.16 | 13 | NORMAL blocked. EXTREME 3/3 +$0.60, HIGH 1/7 -$0.39. |
| volume-breakout-long+ | LONG | 0.0% | -$0.10 | 3 | Below kill threshold (5+ trades). Watch. |
| open-skies+ | LONG | 50.0% | -$0.03 | 2 (6h) | Marginal. 6h only. |

WINNERS:
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| open-skies+ | LONG | 50.0% | +$0.11 | 6 (24h) | Healthy. No action. |

ISSUES:
- pullback-entry- HIGH regime: 1/7 (14.3%) in 24h vs 52.9% all-time. Bad 24h run, not structural. Left at 0.7x multiplier.
- volume-breakout-long+: 0% WR but only 3 trades. Below kill threshold. Monitor.
- No signal inversions detected (24h).

DECISIONS MADE:
- pullback-entry- NORMAL regime blocked (0.0x multiplier in volatility_gate_v2.py)
- No blanket kills — EXTREME regime is 66.7% WR all-time for pullback-entry-
- No boosts — no signal meets 55% WR threshold with sufficient trades
