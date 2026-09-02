# Signal Performance Report
**Generated:** 2026-09-01 23:10 UTC | **Period:** Last 6h + 24h

## Overall Stats
- **Total trades (all time):** 4,412 | **Date range:** 2026-07-29 → 2026-09-01
- **Trades last 6h:** 11 | **Trades last 24h:** 58

---

## WINNERS (WR > 55%, PnL > 0)

| Signal | Dir | 6h T | 6h WR | 6h PnL | 24h T | 24h WR | 24h PnL | Status |
|--------|-----|------|-------|--------|-------|--------|---------|--------|
| bb-bounce-short | SHORT | — | — | — | 5 | 80.0% | +0.01 | ENABLED |

---

## LOSERS / KILL CANDIDATES

None that meet kill criteria (WR < 30% AND 5+ trades AND PnL < -$0.10).

`accel-300-v2-long` was killed earlier today (commit 977e87c). Still showing 2 trades in 6h (50% WR, +$0.10) — likely in-flight trades at disable time. 24h: 13T, 30.8% WR, -$0.53.

---

## MARGINAL / WATCH LIST

| Signal | Dir | 24h T | 24h WR | 24h PnL | Avg PnL/T | Status | Note |
|--------|-----|-------|--------|---------|-----------|--------|------|
| bb-bounce-long+ | LONG | 24 | 58.3% | -0.22 | -0.009 | ENABLED | Good WR but losses > wins. R:R tuning needed. |
| r2-trend-long3 | LONG | 2 | 50.0% | -0.06 | -0.03 | ENABLED | Only 2 trades, needs more data. |

---

## SIGNAL INVERSIONS (24h)

**No inversions found.** All signals respect their direction labels.

---

## RECOMMENDATIONS

1. **[WATCH] bb-bounce-long+** — 58.3% WR with 24 trades but -$0.22 PnL. Wins are small, losses are larger. Consider widening take-profit or tightening stop-loss to improve R:R ratio. Do NOT kill — WR is healthy.
2. **[KEEP] bb-bounce-short** — 80% WR, small positive PnL. Only 5 trades — needs more volume to confirm.
3. **[NO ACTION] accel-300-v2-long** — Already killed. Monitor that disable persists.

---

*Report auto-generated. Next report: ~6h from now.*
