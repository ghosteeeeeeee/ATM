# Signal Performance Report
**Generated:** 2026-09-13 23:30 UTC | **Period:** Last 6h + 24h

## Overall Stats
- **24h trades:** 35 | **24h PnL:** -$0.16 (flat)
- **6h trades:** 6 | **6h PnL:** -$0.72

---

## WINNERS (WR > 55%, PnL > 0)

| Signal | Dir | 6h T | 6h WR | 6h PnL | 24h T | 24h WR | 24h PnL | Status |
|--------|-----|------|-------|--------|-------|--------|---------|--------|
| rr-struct+ | LONG | 3 | 66.7% | -0.21 | 9 | 66.7% | +0.52 | ENABLED |
| pump-chain+ | LONG | — | —% | — | 5 | 80.0% | +0.39 | ENABLED |
| pullback-entry- | SHORT | 1 | 0.0% | -0.21 | 9 | 55.6% | +0.13 | ENABLED |

---

## LOSERS (WR < 30%, PnL < -$0.10, 5+ trades)

**None meet kill criteria.** Two watch-list signals have <5 trades (below threshold).

---

## WATCH LIST (below kill threshold but losing)

| Signal | Dir | 24h T | 24h WR | 24h PnL | Regime Blocks | Note |
|--------|-----|-------|--------|---------|---------------|------|
| trend_purity+ | LONG | 3 | 0.0% | -0.75 | HIGH=0.0x, EXTREME=0.15x | 0% WR but only 3 trades. Already regime-blocked. |
| rr-struct- | SHORT | 3 | 33.3% | -0.22 | HIGH=0.0x | 33% WR, 3 trades. Wins in NORMAL (67% WR). Already regime-blocked. |

---

## MARGINAL (30-55% WR)

None. All signals outside winners are <5 trades.

---

## SIGNAL INVERSIONS (24h)

**No inversions found.** All signals respect their direction labels.

---

## RECOMMENDATIONS

1. **[NO ACTION]** — No signals meet kill criteria (5+ trades, <30% WR, >24h active, PnL < -$0.10).
2. **[KEEP]** — 3 winning combos: rr-struct+, pump-chain+, pullback-entry-. LONG side dominant.
3. **[WATCH]** — trend_purity+ on watch. If next cycle adds 2+ more losing trades, consider blanket kill. Already regime-blocked in HIGH (0.0x) and EXTREME (0.15x).
4. **[WATCH]** — rr-struct- marginal. Wins in NORMAL (67% WR), blocked in HIGH. Needs more data to decide.

---

*Report auto-generated. Next report: ~6h from now.*

---

## PARAM CHANGE LOG (last 7 days)

| Date | Commit | Change |
|------|--------|--------|
| 2026-09-13 | 197e731 | fix: update stale comments in oversold_bounce constants header |
| 2026-09-13 | 3b1f9d3 | CEO: verified + monitoring 2026-09-13 ~22:35 UTC |
| 2026-09-13 | 2535c08 | signals: tighten oversold_bounce to golden zone — every trade a winner |
| 2026-09-13 | 27e4d64 | tune: lower HIGH regime R:R minimum from 1.5x to 1.3x |
| 2026-09-13 | 9352d43 | signals: add oversold_bounce — mean reversion LONG at extreme oversold |
| 2026-09-13 | a913481 | config: add open-skies+ to standalone bypass + BTC chop exemption |
| 2026-09-13 | dfb37d9 | trading: fix bug-hunter findings — partial matching for exit configs |
| 2026-09-13 | 273f00a | trading: mover signals use pump-exit for exit management |
| 2026-09-13 | b2ec796 | config: add mover_long to STANDALONE_BYPASS_SIGNALS (85.7% WR) |
| 2026-09-13 | 7f75b31 | config: pump-chain standalone bypass + BTC chop exemption |

*Changes to `scripts/hermes_constants.py`. Use `git show <commit>` for details.*
