# Signal Performance Report
**Generated:** 2026-10-29 14:45 UTC | **Period:** Last 6h + 24h

## Overall Stats
- **Total trades (all time):** 3,413 | **WR:** 50.9% | **PnL:** -100.79%
- **Date range:** 2026-07-29 → 2026-10-29

---

## WINNERS (WR > 55%, PnL > 0)

| Signal | Dir | 6h T | 6h WR | 6h PnL | 24h T | 24h WR | 24h PnL | Status |
|--------|-----|------|-------|--------|-------|--------|---------|--------|
| bb-squeeze+ | LONG | — | —% | — | 7 | 100.0% | +2.04 | ENABLED |

---

## LOSERS (WR < 30%, PnL < -2%)

None found.

---

## MARGINAL (30-50% WR)

| Signal | Dir | 24h T | 24h WR | 24h PnL | Status | Note |
|--------|-----|-------|--------|---------|--------|------|
| volume-buildup- | SHORT | 3 | 33.3% | -1.87 | ENABLED | Needs more data |

---

## DISABLED BUT GOOD (candidates for re-enabling)

None found. Top performers are already enabled.

---

## SIGNAL INVERSIONS (24h)

**No inversions found.** All signals respect their direction labels.

---

## RECOMMENDATIONS

1. **[WATCH] volume-buildup- SHORT** — WR=33.3%, PnL=-1.87% over 3 trades. Monitor next cycle.
2. **[KEEP] 1 winning combos** — bb-squeeze+. LONG side dominant.

---

*Report auto-generated. Next report: ~6h from now.*

---

## PARAM CHANGE LOG (last 7 days)

| Date | Commit | Change |
|------|--------|--------|
| 2026-10-29 | bcf2406 | harden LLM model resolver (bug_hunter SHIP-WITH-FIXES findin... |
| 2026-10-29 | a0989ec | llm: centralize model to ONE place — opencode config (mimo-v... |
| 2026-10-29 | 2ef737d | scripts: 'where are the shorts' round (CEO consult 20261029T... |
| 2026-10-27 | 14ddb5c | ctx-gate: deterministic rules conversion IN SHADOW (CEO 2026... |
| 2026-10-27 | 3d43a36 | watchdog: gate LLM agent on open_count (CEO 2026-10-27 item ... |
| 2026-10-27 | f96a1e2 | fix: BUG-068 — brain_auditor #188 inverted CHASE_RATIO_SHADO... |
| 2026-10-27 | 56bd9e8 | brain_auditor: Audit run #188 — CHASE_RATIO reverted on its ... |
| 2026-10-27 | f1d8ca0 | scripts: SHADOW-RECKONING review-fix round (329547e5) — 7 ME... |
| 2026-10-27 | 98e9dc9 | scripts: SHADOW-RECKONING round (CEO consult 20261027T024741... |
| 2026-10-26 | c7da007 | brain_auditor: audit run #157 — daily-commit guard fixed (po... |

*Changes to `scripts/hermes_constants.py`. Use `git show <commit>` for details.*