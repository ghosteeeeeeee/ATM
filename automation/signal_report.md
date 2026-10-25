# Signal Performance Report
**Generated:** 2026-10-25 21:34 UTC | **Period:** Last 6h + 24h

**Volume context:** 6h = 5 closed trades (-$0.09), 24h = 16 closed trades (+$0.27), 72h = 46 (+$0.86). Low sample sizes this cycle.

---

## KILLED (executed):

| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| — | — | — | — | — | No kills — no signal met all kill criteria (WR<30% AND PnL<-$0.10 AND 5+ trades, 24h) |

## BOOSTED (executed):

| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| — | — | — | — | — | No boosts — no signal met all boost criteria (WR>55% AND PnL>$0.05 AND 5+ trades, 24h) |

## LOSERS (watch list):

| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| bb-bounce-v2-long+ | LONG | 20.0% | -$0.02 | 5 (24h) | WATCH — fails kill bar (PnL -$0.02 > -$0.10). 72h: 14.3% WR, -$0.27. All-time regime split: FLAT 100% (4T), HIGH 55.6% (18T), NORMAL 45.7% (46T), EXTREME 46.2% (13T) — wins in FLAT/HIGH, so blanket kill inappropriate per regime check. Matches audit #138 finding (kill bars fail on 30d/14d/7d). Next cycle: kill if 24h PnL drops below -$0.10 |
| r2v2-long3 | LONG | 50.0% | -$0.01 | 2 (24h) | WATCH — sample too small |
| hl_copy_trader | LONG | 50.0% | +$0.07 | 2 (24h) | WATCH — 6h -$0.09 (atr_sl_hit), monitor |

## WINNERS:

| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| pump-chain+ | LONG | 100.0% | +$0.05 | 1 (24h) | OK — below sample threshold |
| continuum+ | LONG | 100.0% | +$0.08 | 1 (24h) | OK — below sample threshold |
| volume-buildup- | SHORT | 100.0% | +$0.08 | 2 (24h) | OK — 72h: 64.3% WR, +$0.23 (14T). Below 5T boost bar, recheck next cycle |
| bb-squeeze+ | LONG | 66.7% | +$0.02 | 3 (24h) | OK — 72h: 66.7% WR, +$0.12 (6T). Below 5T 24h boost bar, recheck next cycle |

## ISSUES:

- **No direction inversions** in last 24h — signal/direction labels consistent.
- **Low trade volume** (16 closed trades/24h) — most signals below sample thresholds; conclusions this cycle are necessarily tentative.
- **bb-bounce-v2-long+** remains the primary watch item: 3 consecutive sub-30% WR days but PnL losses are tiny (trail_arm_timeout exits mostly breakeven/small). Do NOT blanket-kill — regime data shows FLAT/HIGH winners; regime-based blocking only if it degrades further.
- No kill/boost actions executed this cycle — no git commits, no hermes_constants.py edits.

---
*Report auto-generated. Next report: ~6h from now.*

---

## PARAM CHANGE LOG (last 7 days)

| Date | Commit | Change |
|------|--------|--------|
| 2026-10-25 | f6a7ed8 | brain_auditor: audit run #138 — escalation #17 closed as sup... |
| 2026-10-25 | f86261f | brain_auditor: #134 addendum — watchdog 06:44 P1 rejected-wi... |
| 2026-10-24 | f96aa8a | brain_auditor: AUDIT RUN #122 — LONG_RSI_SWEET_SPOT_BOOST 10... |
| 2026-10-24 | c10b227 | scripts: UNCLOG-2 — 4 CEO-approved flips (consult 20261024T1... |
| 2026-10-24 | 186ff1c | watchdog: 14:20 UTC cycle — BTC broke EMA300 pin DOWN (knife... |
| 2026-10-24 | 9482523 | logs: hourly analysis 2026-10-24 12:28 — no change, quiet ho... |
| 2026-10-24 | 7553d4e | brain_auditor: AUDIT RUN #114 (2026-10-24) — entry_regime_4h... |
| 2026-10-23 | c4edf08 | exit-system: breakeven lock for CEO trades — SL→entry at +0.... |
| 2026-10-23 | 10d6898 | Daily trading system update (2026-10-23) |
| 2026-10-22 | 2d78f19 | Daily trading system update (2026-10-22) |

*Changes to `scripts/hermes_constants.py`. Use `git show <commit>` for details.*