# Signal Performance Report
**Generated:** 2026-10-16 14:13 UTC | **Period:** Last 6h + 24h

## Overall Stats
- **Total trades (all time):** 3,161 | **WR:** 51.1% | **PnL:** -99.36%
- **Date range:** 2026-07-29 → 2026-10-16

---

## WINNERS (WR > 55%, PnL > 0)

| Signal | Dir | 6h T | 6h WR | 6h PnL | 24h T | 24h WR | 24h PnL | Status |
|--------|-----|------|-------|--------|-------|--------|---------|--------|
| ai-trader+ | LONG | 3 | 66.7% | -0.10 | 5 | 60.0% | +0.82 | ❓ |

---

## LOSERS (WR < 30%, PnL < -2%)

| Signal | Dir | 6h T | 6h WR | 6h PnL | 24h T | 24h WR | 24h PnL | Status | Rec |
|--------|-----|------|-------|--------|-------|--------|---------|--------|-----|
| pump-chain- | SHORT | 3 | 0.0% | -1.31 | 6 | 0.0% | -3.10 | ❓ | **DISABLE** |
| bb-bounce-v2-long+ | LONG | 4 | 25.0% | -1.67 | 5 | 20.0% | -3.01 | ❓ | **DISABLE** |

---

## MARGINAL (30-50% WR)

| Signal | Dir | 24h T | 24h WR | 24h PnL | Status | Note |
|--------|-----|-------|--------|---------|--------|------|
| bb-squeeze+ | LONG | 2 | 50.0% | -0.31 | ENABLED | Needs more data |
| hl_copy_trader | LONG | 2 | 50.0% | -0.01 | ❓ | Needs more data |
| pump-chain+ | LONG | 7 | 42.9% | +9.51 | ❓ | Borderline |

---

## DISABLED BUT GOOD (candidates for re-enabling)

None found. Top performers are already enabled.

---

## SIGNAL INVERSIONS (24h)

**No inversions found.** All signals respect their direction labels.

---

## RECOMMENDATIONS

1. **[DISABLE] pump-chain- SHORT** — WR=0.0%, PnL=-3.10% over 6 trades (24h).
2. **[DISABLE] bb-bounce-v2-long+ LONG** — WR=20.0%, PnL=-3.01% over 5 trades (24h).
3. **[WATCH] bb-squeeze+ LONG** — WR=50.0%, PnL=-0.31% over 2 trades. Monitor next cycle.
4. **[WATCH] hl_copy_trader LONG** — WR=50.0%, PnL=-0.01% over 2 trades. Monitor next cycle.
5. **[WATCH] pump-chain+ LONG** — WR=42.9%, PnL=+9.51% over 7 trades. Monitor next cycle.
6. **[KEEP] 1 winning combos** — ai-trader+. LONG side dominant.

---

*Report auto-generated. Next report: ~6h from now.*

---

## PARAM CHANGE LOG (last 7 days)

| Date | Commit | Change |
|------|--------|--------|
| 2026-10-16 | b16d030 | signals: brain_auditor captain run — pump-chain- SHORT dead-... |
| 2026-10-16 | 9bdda8d | Daily trading system update (2026-10-16) |
| 2026-10-16 | 86dce93 | signals: SHORT mid-band death band block (45-55, non-pump-ch... |
| 2026-10-15 | 6d2bfc9 | brain_auditor: Captain run 2026-10-15 18:30 — kill hmacd_mtf... |
| 2026-10-15 | 262603a | config: hard_max_loss -3.00% → -4.00% account PnL |
| 2026-10-15 | 6c9f043 | brain_auditor: KILL volume-breakout-short- (0/3 all-time 0%W... |
| 2026-10-15 | 0bc76eb | brain_auditor: captain audit 2026-10-15 14:50 — kill LONG-SH... |
| 2026-10-14 | 796c745 | brain_auditor: re-enable doji-bottom (EXTREME gated) + LONG-... |
| 2026-10-14 | b51cae0 | signals: kill volume-buildup+ LONG — 3T 0W last hour all har... |
| 2026-10-14 | 20fcff5 | Daily trading system update (2026-10-14) |

*Changes to `scripts/hermes_constants.py`. Use `git show <commit>` for details.*