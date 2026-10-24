# Signal Performance Report
**Generated:** 2026-10-24 22:15 UTC | **Period:** Last 6h + 24h

## Overall Stats (24h)
- **Closed trades:** 11 | **Net PnL:** +$1.06
- **Inversions:** 0

---

## KILLED (executed)

None — no signal met kill criteria (no WR < 30% with 5+ trades and negative PnL).

---

## BOOSTED (executed)

None — no signal met boost criteria (only one signal with 5+ trades, already performing; no weight change made without stronger signal).

---

## LOSERS (watch list)

| Signal | Dir | 24h T | 24h WR | 24h PnL | Status |
|--------|-----|-------|--------|---------|--------|
| ai-trader-pending | SHORT | 2 | 50.0% | -$0.04 | WATCH — below min sample, manual/pending flow |

---

## WINNERS

| Signal | Dir | 6h T | 6h WR | 6h PnL | 24h T | 24h WR | 24h PnL | Status |
|--------|-----|------|-------|--------|-------|--------|---------|--------|
| volume-buildup- | SHORT | — | — | — | 5 | 80.0% | +$0.51 | ENABLED — consistent top performer |

Other positive 24h singles (n<3, informational): pump-chain- SHORT (+$0.34, 100%), continuum+ LONG (+$0.12, 100%), ai-trader-pending LONG (+$0.12, 100%), pump-chain+ LONG (+$0.01, 100%).

---

## ISSUES

- Very low trade volume in the last 24h (11 closed trades) — nothing actionable at this sample size. Next 6h run should re-check; kill/boost thresholds need 5–10+ trades per signal.
- No direction inversions detected. No critical bugs found.
