# Signal Performance Report
**Generated:** 2026-10-06 23:10 UTC | **Period:** Last 6h + 24h

## Overall Stats (24h)
- **Total closed trades:** 13
- **Trades by signal:**
  - trend-ride+ LONG: 5T, 20.0% WR, -$0.33
  - pump-chain- SHORT: 3T, 33.3% WR, -$0.29
  - bb-squeeze+ LONG: 2T, 0.0% WR, -$0.25
  - oversold-bounce+ LONG: 2T, 100% WR, +$0.24
  - mover+ LONG: 1T, 100% WR, +$0.10

---

## KILLED (executed):
| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| trend-ride+ | LONG | 20.0% | -$0.33 | 5 | **DISABLED** — TREND_RIDE_LONG_ENABLED=False, TREND_RIDE_LONG_PLUS_ENABLED=False |

**Kill rationale:** Meets all criteria — WR 20% < 30%, 5 trades, PnL -$0.33 < -$0.10, age 25.4h > 24h. Regime breakdown: EXTREME 50% WR -$0.11 (2T), HIGH 33.3% WR -$0.01 (3T), NORMAL 50% WR -$0.06 (2T). No regime ≥55% WR → blanket kill appropriate. Backtest cited EXTREME 99T 58.6% +$5.69 edge did not materialize live (only 7 total live trades, all negative).

---

## BOOSTED (executed):
| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| — | — | — | — | — | None qualified (need 5+ trades, WR>55%, PnL>$0.05) |

---

## LOSERS (watch list):
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| pump-chain- | SHORT | 33.3% | -$0.29 | 3 | WATCH — all-time 127T 52.8% WR -$0.76. NORMAL regime 72.7% WR (11T). Not enough 24h volume to kill. HIGH regime already re-allowed by CEO 2026-10-06. |
| bb-squeeze+ | LONG | 0.0% | -$0.25 | 2 | WATCH — all-time 69T 60.9% WR -$0.05. Only 2 trades in 24h. EXTREME block already active. |

---

## WINNERS:
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| oversold-bounce+ | LONG | 100% | +$0.24 | 2 | Healthy — below boost threshold (needs 5+ trades) |
| mover+ | LONG | 100% | +$0.10 | 1 | Healthy — below boost threshold |

---

## SIGNAL INVERSIONS (24h)
**No inversions found.** All signals respect their direction labels.

---

## ISSUES
- None. No inversions, no bugs detected this cycle.
- Low trade volume (13 trades/24h) — most signals under-sampled for statistical action.
