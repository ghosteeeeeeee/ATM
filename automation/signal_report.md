=== Signal Performance Report ===
Generated: 2026-09-22 ~09:30 UTC

## 6h Performance (minimum 2 trades)
| Signal | Dir | Trades | WR | PnL |
|--------|-----|--------|-----|-----|
| pump-chain+ | LONG | 3 | 0.0% | -$0.76 |
| pump-chain- | SHORT | 2 | 100.0% | +$0.25 |

## 24h Performance (minimum 3 trades)
| Signal | Dir | Trades | WR | PnL |
|--------|-----|--------|-----|-----|
| pump-chain+ | LONG | 13 | 15.4% | -$1.51 |
| pump-chain- | SHORT | 6 | 33.3% | -$0.38 |

## KILLED (executed)
| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| pump-chain+ | LONG | 15.4% | -$1.51 | 13 (24h) | PUMP_FLOW_PLUS_ENABLED=False, PUMP_CHAIN_V4_ENABLED=False. Added to NEVER_REENABLE_FLAGS. |

### Kill rationale
- WR < 30% (15.4%) with 13 trades (24h) ✓
- Net PnL < -$0.10 (-$1.51) ✓
- Active > 24h (since Sep 10, 12 days) ✓
- ALL regimes lose: EXTREME 20%WR -$1.21, HIGH 0%WR -$0.30
- Lifetime: 80T 41.3%WR +$0.95 — edge existed but collapsed recently

## BOOSTED (executed)
None — no signal meets boost criteria (WR>55%, 5+ trades, PnL>+$0.05)

## LOSERS (watch list)
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| pump-chain- | SHORT | 33.3% | -$0.38 | 6 (24h) | WATCH — lifetime 57.4%WR +$0.24. EXTREME regime only (33.3%WR). Small 24h loss, not yet kill-worthy. |

## WINNERS
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| pump-chain- | SHORT (lifetime) | 57.4% | +$0.24 | 61 | Healthy long-term. 24h dip but no action needed. |

## Other 24h Trades (not meeting min-sample threshold)
- btc-pump-rider+ LONG: 1T, -$0.09
- pullback-entry- SHORT: 1T, -$0.29
- accel-300- SHORT: 2T, +$0.30 (positive)
- mover+ LONG: 2T, -$0.24
- doji-bottom-long LONG: 2T, -$0.19

## ISSUES
- No signal inversions detected
- pump-chain+ LONG has been bleeding for days — dead hours filter (0-5,23 UTC) and RSI blocks (35-75) already in place but insufficient. Full kill warranted.
- pump-flow-minus already killed same day (0%WR -$0.63 24h) — pump-flow family is fully dead now.
