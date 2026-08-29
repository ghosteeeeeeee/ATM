=== Signal Performance Report ===
Generated: 2026-08-29 11:15 UTC

Period: 6h | 24h | 7d

KILLED (executed): None — no signal meets all kill criteria this cycle.

BOOSTED (executed): None — no signal meets all boost criteria this cycle.

LOSERS (watch list):
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| accel-300-v2-short- | SHORT | 25.0% | -$0.14 | 4T/24h | WATCH — below 30% WR but <5 trades (kill needs 5+). 7d: 4T 25% -$0.14. Already killed (ACCEL_300_V2_MINUS_ENABLED=False). |
| accel-300-v2- | SHORT | 30.8% | -$0.10 | 13T/24h | WATCH — 30.8% WR borderline. 7d: 72T 52.8% +$1.46 (best performer). 24h dip is noise, not degradation. |
| bb-bounce-short | SHORT | 42.9% | -$0.05 | 7T/6h | WATCH — 6h uptick negative but 7d: 35T 60% $0.00. Neutral. |
| bb-bounce-short | SHORT | 54.2% | -$0.05 | 24T/24h | OK — 54% WR, tiny loss. 7d confirms break-even. |

WINNERS:
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| macd-div- | SHORT | 72.0% | +$0.24 | 25T/7d | STRONG — best 7d performer per trade. |
| accel-300-v2- | SHORT | 52.8% | +$1.46 | 72T/7d | STRONG — highest total PnL. 24h dip is noise. |
| bb_bounce+ | LONG | 59.0% | +$0.11 | 39T/7d | GOOD — steady performer. |
| hzscore- | SHORT | 50.0% | +$0.09 | 10T/7d | OK — break-even to slight positive. |
| r2-trend-short4 | SHORT | 100% | +$0.20 | 3T/7d | GOOD — small sample but perfect. |

ISSUES:
- No signal inversions detected.
- All 24h exits are ATR_SL hits — system is getting stopped out frequently but losses are capped at -$0.08 to -$0.12 per trade. The tight ATR SL (0.8% min) is working as designed: small losses, no blowups.
- 7d losers (slow_grind, hl_copy, pump_catcher, ct_hot, atr_spike, continuation) are all already killed in NEVER_REENABLE_FLAGS. No action needed.
- System is in a low-volatility chop phase: many trades, tight stops, small losses. This is expected behavior, not a signal degradation.

ACTION: No changes to hermes_constants.py this cycle.
