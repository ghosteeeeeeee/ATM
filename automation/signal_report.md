# Signal Performance Report
**Generated:** 2026-10-19 22:05 UTC | **Period:** Last 6h + 24h

## Overall Stats
- **Total trades (all time, closed):** 5,911 | **WR:** 45.3% | **PnL:** -15.05
- **Date range:** 2026-05-20 → 2026-10-19
- **Closed trades in window:** 6h: 1 | 24h: 17 (low activity period)

---

## KILLED (executed)

| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| — | — | — | — | — | None — no signal met kill criteria |

## BOOSTED (executed)

| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| — | — | — | — | — | None — no signal met boost criteria (5+ trades, WR>55%, PnL>$0.05) |

## LOSERS (watch list)

| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| ai-trader+ | LONG | 25.0% | -0.17 | 4 | Watch — below 5-trade kill threshold; manual channel, not blanket-killable. All-time EXTREME regime: 25% WR, -0.81 (HIGH regime: 75% WR, +0.11). EXTREME LONG conf-demote already in SHADOW since 2026-10-18 (commit feaf3f1) |
| bb-bounce-v2-long+ | LONG | 75.0% | -0.14 | 4 | Watch — R:R asymmetry, not a WR problem. 3 winners = +0.12 total; one stale_exit loss = -0.26. All-time regimes all 46-56% WR, ~breakeven. Not killable |

## WINNERS

| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| continuum-trend+ | LONG | 100% | +0.04 | 2 | Promising but under-sampled (need 5+ trades to boost) |
| r2v2-long3 | LONG | 100% | +0.05 | 1 | Single trade, no action |
| ai-trader-manual | LONG | 100% | +0.05 | 1 | Single trade, no action |

## ISSUES

- **No inversions found** (24h). All direction labels match signal names.
- **6h window has only 1 closed trade** — no 6h signal stats possible this run.
- **ai-trader+ EXTREME-long bleed continues** (-0.81 all-time in EXTREME). Shadow conf-demote deployed 2026-10-18; keep collecting counterfactual data, do not force-enforce without CEO approval.
- **bb-bounce-v2-long+ stale_exit risk:** single -0.26 stale_exit erased 3 winners. Worth a look at stale-exit threshold for this family, but no config change this run (sample too small).

---

*Report auto-generated. Next report: ~6h from now.*

---

## PARAM CHANGE LOG (last 7 days)

| Date | Commit | Change |
|------|--------|--------|
| 2026-10-19 | 8d26e2e | risk: CEO verdict — lift size reduce 30→50%, disable ai-trad... |
| 2026-10-19 | 96ad7b6 | Daily trading system update (2026-10-19) |
| 2026-10-18 | 4e0ab75 | brain_auditor: audit run 2026-10-18 23:44 — comment hygiene,... |
| 2026-10-18 | feaf3f1 | signals: ai-trader+ EXTREME LONG conf-demote SHADOW (brain_a... |
| 2026-10-18 | f635705 | brain_auditor: Captain audit run Oct 18 14:50 — 0 config cha... |
| 2026-10-18 | 9b2c95f | brain_auditor: Audit run Oct 18 10:35 — soak #13, 0 config c... |
| 2026-10-18 | 836de28 | brain_auditor: Captain audit Oct 18 06:40 — soak #11, 0 conf... |
| 2026-10-17 | 209c5ae | brain_auditor: trail-arm-timeout candle OOS (all 4 cohorts) ... |
| 2026-10-17 | b01d329 | brain_auditor: captain run Oct 17 06:45 — 0 changes, verify+... |
| 2026-10-17 | 75b2af2 | brain_auditor: REGIME_CONF_EXTREME_MULT 1.15→0.85 — stale Se... |

*Changes to `scripts/hermes_constants.py`. Use `git show <commit>` for details.*
