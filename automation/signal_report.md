=== Signal Performance Report ===
Generated: 2026-09-22 05:10 UTC

KILLED (executed):
| Signal | Dir | WR | PnL | Trades 24h | Action |
|--------|-----|-----|-----|------------|--------|
| pump-chain- | SHORT | 0% | -$0.63 | 4 | KILLED — set PUMP_FLOW_MINUS_ENABLED=False. Already in NEVER_REENABLE_FLAGS. 0% WR EXTREME (7d). |

BOOSTED (executed):
| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| (none) | — | — | — | — | — |

LOSERS (watch list):
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| pump-chain+ | LONG | 25% | -$0.50 | 12 | WATCH — 24h bad stretch but 7d still profitable (+$1.99, 44.2% WR). EXTREME regime strong (46.9% WR). |
| pullback-entry- | SHORT | 49.1% | -$0.32 | 53 | WATCH — HIGH profitable (52% WR +$0.50), NORMAL losing. Gate already blocks NORMAL. |
| mover+ | LONG | 62.5% | -$0.17 | 8 | WATCH — 7d breakeven, EXTREME was -1T noise. |
| doji-bottom-long | LONG | 60% | +$0.09 | 5 | OK — small sample, slightly positive. |

WINNERS:
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| volume-breakout-long+ | LONG | 68.8% | +$1.41 | 16 | STRONG — consistent edge across 7d. |
| grind-trend+ | LONG | 50% | +$0.24 | 18 | STEADY — break-even WR, positive PnL. |

ISSUES:
- No direction inversions detected.
- pump-chain- SHORT was re-enabled 2026-09-21 after key mismatch bug fix — but still 0% WR. All 4 trades in EXTREME regime hit ATR SL or dead money exit. Signal fires on pump detections but SHORT direction gets stopped out on momentum. This is structural — pump-chain SHORT may not have edge in current market regime.
- pump-chain+ LONG24h loss streak (25% WR) is within normal variance. 7d performance remains positive across EXTREME (+$1.28) and HIGH (+$0.47). Do NOT kill.
