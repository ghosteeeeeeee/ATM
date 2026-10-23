# Signal Performance Report
**Generated:** 2026-10-23 15:32 UTC | **Period:** Last 6h + 24h

## Totals
- **6h:** 10 closed trades | PnL: -$0.58
- **24h:** 19 closed trades | PnL: -$0.36

---

## KILLED (executed)

| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| — | — | — | — | — | None met kill criteria (WR<30%, n>=5, PnL<-$0.10) |

---

## BOOSTED (executed)

| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| — | — | — | — | — | None met boost criteria (WR>55%, n>=5) |

---

## LOSERS (watch list)

| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| volume-buildup- | SHORT | 42.9% | -$0.32 | 7 (24h) | WATCH — active since 2026-10-12, all regimes 50% WR (NORMAL n=16, EXTREME n=4); no regime >=55%, but WR above 30% kill bar. Re-check next cycle. |
| bb-bounce-v2-long+ | LONG | 0.0% | -$0.25 | 2 (24h) | WATCH — below trade-count threshold |

---

## WINNERS

| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| warrior-sr-confirm- | SHORT | 100.0% | +$0.24 | 3 (24h) | Enabled — n<5, no boost yet |
| bb-squeeze+ | LONG | 66.7% | +$0.10 | 3 (24h) | Enabled — n<5, no boost yet |

---

## ISSUES

- No signal met kill or boost thresholds this cycle — trade volume is low (19 in 24h).
- No signal inversions found (0 direction mismatches in 24h).

---

## PARAM CHANGE LOG (last 7 days)

| Date | Commit | Change |
|------|--------|--------|
| 2026-10-23 | c4edf08 | exit-system: breakeven lock for CEO trades — SL→entry at +0.... |
| 2026-10-23 | 10d6898 | Daily trading system update (2026-10-23) |
| 2026-10-22 | 2d78f19 | Daily trading system update (2026-10-22) |
| 2026-10-22 | 24225f3 | brain_auditor: AUDIT RUN #69 — BTC-regime habitat map verifi... |
| 2026-10-22 | 0747cdd | scripts: wire shadow_signals_runner into pipeline with shado... |
| 2026-10-21 | 0c57042 | plans: spec v2 autonomous BTC loop — CEO answers baked in: B... |
| 2026-10-21 | c625517 | skills+data: add §12 no-edge default (CEO directive — arm th... |
| 2026-10-21 | 6fee8ef | scripts: shadow-registry + shadow-bypass system (T directive... |
| 2026-10-21 | 1630544 | Daily trading system update (2026-10-21) |
| 2026-10-21 | c9092ae | signals: block pump-chain+ LONG in HIGH regime — 37%WR $-0.4... |

*Changes to `scripts/hermes_constants.py`. Use `git show <commit>` for details.*
