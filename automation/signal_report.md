# Signal Performance Report
**Generated:** 2026-10-08 ~11:15 UTC | **Period:** Last 6h + 24h (+48h context)

## Trade Volume
- **6h:** 0 closed trades
- **24h:** 7 closed trades
- **48h:** 19 closed trades
- System is very quiet — below thresholds for kills/boosts.

---

## KILLED (executed):

| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| — | — | — | — | — | None this cycle |

---

## BOOSTED (executed):

| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| — | — | — | — | — | None this cycle |

---

## LOSERS (watch list):

| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| pump-chain- | SHORT | 0.0% | -0.22 | 3 (24h) | WATCH — under 5-trade kill threshold; 48h: 30% WR, +0.72 over 10 trades → not a kill candidate |

---

## WINNERS:

| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| pump-chain+ | LONG | 66.7% | +0.95 | 3 (24h) | Active, positive. 48h: 40% WR, +0.74 over 5 trades. Below boost thresholds (needs 5+ trades / 24h). |

---

## ISSUES:
- No signal inversions in last 24h (0 direction mismatches found).
- Trade volume is unusually low (0 in 6h, 7 in 24h) — not a signal-quality issue, just quiet market.
- No `*_ENABLED` flags changed. No regime gates modified. No git commit needed (no code changes).
- pump-chain- SHORT is the only potential concern but fails all kill criteria: 24h has only 3 trades (< 5), and 48h is net positive (+$0.72). Keep monitoring.

## Kill Criteria Check (24h):
- WR < 30% + 5+ trades + PnL < -$0.10 + active > 24h → **No signal met ALL criteria**
- Boost criteria: WR > 55% + 5+ trades + PnL > $0.05 → **No signal met ALL criteria**
