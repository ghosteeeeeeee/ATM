# Signal Performance Report
**Generated:** 2026-09-20 19:15 UTC | **Period:** Last 6h + 24h

## Overall Stats
- **Total trades (all time):** 5,198 | **WR:** 45.7% | **PnL:** -$8.55

---

## WINNERS (WR > 55%, PnL > 0)

| Signal | Dir | 6h T | 6h WR | 6h PnL | 24h T | 24h WR | 24h PnL | Status |
|--------|-----|------|-------|--------|-------|--------|---------|--------|
| pump-chain+ | LONG | 3 | 66.7% | +0.01 | 18 | 61.1% | +0.69 | ENABLED |
| pullback-entry- | SHORT | 2 | 50.0% | -0.05 | 9 | 66.7% | +0.38 | ENABLED |
| grind-trend+ | LONG | 0 | — | — | 3 | 100.0% | +0.42 | ENABLED |

---

## LOSERS (WR < 30%, PnL < -$0.10)

None found.

---

## MARGINAL (30-50% WR, negative PnL)

| Signal | Dir | 24h T | 24h WR | 24h PnL | Regime | Note |
|--------|-----|-------|--------|---------|--------|------|
| grind-trend- | SHORT | 3 | 33.3% | -0.20 | HIGH: 33.3% (3T), NORMAL: 0% (2T) | Gated NORMAL. Losing HIGH too — only 1 day of data. Watchlist. |

---

## DISABLED BUT GOOD (candidates for re-enabling)

None found. Top performers are already enabled.

---

## SIGNAL INVERSIONS (24h)

None found.

---

## KILLED (executed this period)

None. No signals met kill criteria (WR<30% with 5+ trades, PnL<-$0.10, active>24h).

---

## BOOSTED (executed this period)

None. No signals met boost criteria (WR>55% with 5+ trades, PnL>$0.05, consistent across tokens).

---

## ACTIONS TAKEN

- **No kills.** grind-trend- SHORT (33.3% WR, -$0.20) only has 3 trades — below 5-trade kill threshold. Already gated in NORMAL regime via volatility_gate_v2.py. Losing in HIGH too but too few trades for blanket kill.
- **No boosts.** pump-chain+ LONG is the standout (18T, 61.1%, +$0.69) but already performing well — no config changes needed.
- **No inversions.** Clean.

---

## WATCHLIST

| Signal | Dir | Trend | Action if degrades |
|--------|-----|-------|--------------------|
| grind-trend- | SHORT | 33.3% WR, -$0.20 (24h). Only 1 day of data (9/19). Already gated NORMAL. | Add HIGH gate if 5+ trades with <40% WR |
