# Signal Performance Report

Period: Last 6h | 24h — Generated 2026-10-14

## KILLED (executed):
None this cycle.

## BOOSTED (executed):
None this cycle.

## LOSERS (watch list):

| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| pump-chain+ | LONG | 12.5% | -$0.34 | 8 | EXTREME bleed (4T 0%WR -$0.27). All-time EXTREME +$3.27 / 45.9% WR — bad window, not structural. HIGH/NORMAL already dampened 0.5x. Monitor; kill only if EXTREME all-time turns negative. |
| pump-chain- | SHORT | 21.1% | -$0.27 | 19 | EXTREME bleed (18T 22.2%WR -$0.24). NORMAL all-time 69.2%WR +$0.50 — keep. HIGH already blocked. Losses are small ATR_SL hits (-$0.01 to -$0.13), not catastrophic. CEO re-enabled EXTREME 2026-10-08. Monitor 7d. |
| bb-bounce-v2-long+ | LONG | 40.0% | -$0.09 | 5 | Hyphen form weak. Underscore form (bb_bounce_v2_long) all-time HIGH 77.1%WR +$0.89, NORMAL 76.0%WR +$0.87. Same signal, different DB naming. Not a kill. |
| volume-buildup+ | LONG | 0.0% | -$0.26 | 3 | ALREADY KILLED — VOLUME_BUILDUP_PLUS_ENABLED=False (auto_1hr 2026-10-14 09:15). 24h losses are pre-kill. Done. |

## WINNERS:

| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| volume-buildup- | SHORT | 100% | +$0.16 | 2 (6h) | Below boost threshold (need 5+). VOLUME_BUILDUP_MINUS_ENABLED=True. Monitor for boost next cycle. |
| r2v2-long3 | LONG | 66.7% | +$0.01 | 3 | PnL too small ($0.01 < $0.05 boost threshold). All-time only 5T. Watch. |

## ISSUES:
- No signal inversions found (24h).
- pump-chain+ and pump-chain- both bleeding in EXTREME this 24h window. All-time EXTREME data still supports pump-chain+ LONG (+$3.27). pump-chain- SHORT NORMAL habitat intact (69.2% WR). No structural failures detected.
- No regime qualifies for new blocking: pump-chain+ EXTREME all-time 45.9% WR (profitable), pump-chain- NORMAL 69.2% WR (above 55% threshold).
