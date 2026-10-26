# Signal Performance Report
**Generated:** 2026-10-26 09:33 UTC | **Period:** Last 6h + 24h

## 6h Performance
| Signal | Dir | Trades | WR | PnL |
|--------|-----|--------|-----|-----|
| pump-chain+ | LONG | 2 | 100.0% | +0.05 |

## 24h Performance
| Signal | Dir | Trades | WR | PnL |
|--------|-----|--------|-----|-----|
| bb-bounce-v2-long+ | LONG | 5 | 20.0% | -0.05 |
| volume-buildup- | SHORT | 4 | 100.0% | +0.12 |

---

## KILLED (executed):
None — no signal met all three kill criteria (WR<30% + 5 trades, PnL<-$0.10, active >24h).

## BOOSTED (executed):
None — no signal met all three boost criteria (WR>55% + 5 trades, PnL>$0.05, multi-token).

## LOSERS (watch list):
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| bb-bounce-v2-long+ | LONG | 20.0% | -0.05 | 5 | WATCH — fails PnL threshold (-0.05 > -0.10); regime check: NORMAL only, 20% WR. Kill if PnL drops below -0.10 next cycle |
| hl_copy_trader | LONG | 0.0% | -0.09 | 1 | WATCH — n too small |
| hh-hl-,warrior-sr-confirm- | SHORT | 0.0% | -0.09 | 1 | WATCH — n too small |
| continuum-trend+ | LONG | 0.0% | -0.08 | 1 | WATCH — n too small |

## WINNERS:
| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| volume-buildup- | SHORT | 100.0% | +0.12 | 4 | WATCH for boost — 1 short of 5-trade threshold |
| pump-chain+ | LONG | 100.0% | +0.05 | 2 (6h) | ENABLED |
| r2v2-long3 | LONG | 100.0% | +0.09 | 1 | ENABLED |
| continuum-osc- | SHORT | 100.0% | +0.01 | 1 | ENABLED |

## ISSUES:
- **No inversions found** (0 direction mismatches in 24h).
- Low trade volume overall (11 closed trades/24h) — most signals below statistical thresholds; no actions taken this cycle.

---

*Report auto-generated. Next report: ~6h from now.*

---

## PARAM CHANGE LOG (last 7 days)

| Date | Commit | Change |
|------|--------|--------|
| 2026-10-26 | c7da007 | brain_auditor: audit run #157 — daily-commit guard fixed (po... |
| 2026-10-25 | f6a7ed8 | brain_auditor: audit run #138 — escalation #17 closed as sup... |
| 2026-10-25 | f86261f | brain_auditor: #134 addendum — watchdog 06:44 P1 rejected-wi... |
| 2026-10-24 | f96aa8a | brain_auditor: AUDIT RUN #122 — LONG_RSI_SWEET_SPOT_BOOST 10... |
| 2026-10-24 | c10b227 | scripts: UNCLOG-2 — 4 CEO-approved flips (consult 20261024T1... |
| 2026-10-24 | 186ff1c | watchdog: 14:20 UTC cycle — BTC broke EMA300 pin DOWN (knife... |
| 2026-10-24 | 9482523 | logs: hourly analysis 2026-10-24 12:28 — no change, quiet ho... |
| 2026-10-24 | 7553d4e | brain_auditor: AUDIT RUN #114 (2026-10-24) — entry_regime_4h... |
| 2026-10-23 | c4edf08 | exit-system: breakeven lock for CEO trades — SL→entry at +0.... |
| 2026-10-23 | 10d6898 | Daily trading system update (2026-10-23) |

*Changes to `scripts/hermes_constants.py`. Use `git show <commit>` for details.*