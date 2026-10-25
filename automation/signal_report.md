# Signal Performance Report
**Generated:** 2026-10-25 03:32 UTC | **Period:** Last 6h | 24h

## Summary
Very quiet cycle: 4 trades in 6h, 10 trades in 24h. No signal meets kill criteria (5+ trades, WR<30%, PnL<-$0.10) or boost criteria (5+ trades, WR>55%, PnL>$0.05). **No kills, no boosts executed.** 24h total: +$0.82, 80% WR (8/10).

---

## KILLED (executed):
| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| — | — | — | — | — | none — no candidates |

## BOOSTED (executed):
| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| — | — | — | — | — | none — no candidates (no signal has 5+ trades in 24h) |

## LOSERS (watch list):
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| bb-bounce-v2-long+ | LONG | 0.0% (6h) | -0.01 | 1 (6h) | WATCH — single tiny loser, below kill threshold |

## WINNERS:
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| volume-buildup- | SHORT | 50.0% | +0.19 | 2 (24h) | ENABLED — best 24h PnL |
| pump-chain+ | LONG | 100.0% | +0.06 | 2 (24h) | ENABLED |
| ai-trader-pending | mixed | 100.0% | +0.16 | 2 (24h) | ENABLED (manual/pending) |
| hl_copy_trader | LONG | 100.0% | +0.16 | 1 (6h) | ENABLED (copy trader) |
| continuum+ | LONG | 100.0% | +0.12 | 1 (24h) | ENABLED |
| bb-squeeze+ | LONG | 100.0% | +0.04 | 1 (6h) | ENABLED |

## ISSUES:
- **No current inversions (24h).** 46 all-time hits are `tl_break_long`/`tl_break_short` from the old FLIP mechanism, disabled 2026-08-01 (`scripts/decider_run.py:1444`) — last inversion closed 2026-08-01, matching the fix date exactly. Historical/resolved, no action needed.
- **Sample sizes below thresholds everywhere** — max 2 trades per signal in 24h. Kill/boost rules untestable this cycle; next run may have actionable data.
- Prior report (03:31 UTC) listed "3,313 all-time trades"; DB actually has 6,009 closed. Old report used a narrower scope — numbers re-verified fresh this run.
- 2 open positions (both LONG, no inversion risk): `continuum+`, `r2v2-long3`.

---

*Report auto-generated. Next report: ~6h from now.*

---

## PARAM CHANGE LOG (last 7 days)

| Date | Commit | Change |
|------|--------|--------|
| 2026-10-24 | f96aa8a | brain_auditor: AUDIT RUN #122 — LONG_RSI_SWEET_SPOT_BOOST 10... |
| 2026-10-24 | c10b227 | scripts: UNCLOG-2 — 4 CEO-approved flips (consult 20261024T1... |
| 2026-10-24 | 186ff1c | watchdog: 14:20 UTC cycle — BTC broke EMA300 pin DOWN (knife... |
| 2026-10-24 | 9482523 | logs: hourly analysis 2026-10-24 12:28 — no change, quiet ho... |
| 2026-10-24 | 7553d4e | brain_auditor: AUDIT RUN #114 (2026-10-24) — entry_regime_4h... |
| 2026-10-23 | c4edf08 | exit-system: breakeven lock for CEO trades — SL→entry at +0.... |
| 2026-10-23 | 10d6898 | Daily trading system update (2026-10-23) |
| 2026-10-22 | 2d78f19 | Daily trading system update (2026-10-22) |
| 2026-10-22 | 24225f3 | brain_auditor: AUDIT RUN #69 — BTC-regime habitat map verifi... |
| 2026-10-22 | 0747cdd | scripts: wire shadow_signals_runner into pipeline with shado... |

*Changes to `scripts/hermes_constants.py`. Use `git show <commit>` for details.*
