=== Signal Performance Report ===
Period: 2026-09-28 05:09 UTC | 7d window (Sep 21-28)

## KILLED (executed this run)

| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| pump-chain+ (V5) | LONG | 20.0% | -$1.26 | 15 | KILLED — PUMP_CHAIN_V5_ENABLED=False, added to NEVER_REENABLE_FLAGS |

Regime breakdown: EXTREME 25%WR -$0.96 (12T), HIGH 0%WR -$0.30 (3T). ALL regimes lose.

## PREVIOUSLY KILLED (still enforced)

| Signal | Dir | WR | PnL | Trades | Killed |
|--------|-----|-----|-----|--------|--------|
| pullback-entry- | SHORT | 0.0% | -$1.69 | 7 | Sep 22 — PULLBACK_ENTRY_MINUS_ENABLED=False |
| mover+ | LONG | 25.0% | -$1.19 | 8 | Sep 24 — MOVER_PLUS_ENABLED=False |
| pump-chain- | SHORT | 45.5% | -$0.93 | 33 | Sep 25 — PUMP_CHAIN_V5_SHORT_ENABLED=False |
| accel-300-breakout | SHORT | 28.6% | -$0.12 | 7 | Sep 23 — ACCEL_300_BREAKOUT_ENABLED=False |

## BOOSTED (executed this run)

None — no signals met boost criteria (WR>55%, 5+ trades, positive PnL) in 7d.

## LOSERS (watch list)

| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| doji-bottom-long | LONG | 33.3% | -$0.20 | 3 | Low volume, monitor |
| bb-bounce-v2-long+ | LONG | 42.9% | -$0.18 | 14 | Marginal, EXTREME regime noise |
| accel-300+,rs_s | LONG | 37.8% | -$2.91 | 275 | All-time chronic loser, combo signal |

## WINNERS

| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| volume-breakout-long+ | LONG | 66.7% | $0.79 | 3 | Strong but low volume |
| continuum-osc+ | LONG | 75.0% | -$0.05 | 4 | High WR, slightly negative PnL |
| r2_trend_long | LONG | 62.2% | $0.59 | 127 | Consistent all-time winner |

## 24h Summary

Only 5 trades closed in last 24h (quiet market):
- rs-s30,rs-s33 LONG: -$0.02
- rs-s111 LONG: -$0.12
- rs-r66,rs-r74 SHORT: -$0.03
- mover- SHORT: -$0.04
- rs-s94 LONG: -$0.07

## ISSUES

- **No signal inversions detected** — all signals match expected directions.
- **pump-chain+ LONG V5 was still firing** despite 20% WR — killed this run. V5 was enabled Sep 22 as a "48h test" that ran for 6 days.
- **pullback-entry- flag bug resolved** — trades stopped after PULLBACK_ENTRY_MINUS_ENABLED=False on Sep 22. The flag is working correctly (no post-disable trades).

## Flag Changes This Run

```
scripts/hermes_constants.py:
  Line 3613: PUMP_CHAIN_V5_ENABLED = False  (was True)
  Line 1761: Added 'PUMP_CHAIN_V5_ENABLED' to NEVER_REENABLE_FLAGS
```
