# Signal Performance Report
**Generated:** 2026-10-22 09:33 UTC | **Period:** Last 6h + 24h

## Volume
- **6h:** 1 closed trade | PnL +$0.11
- **24h:** 29 closed trades | PnL -$0.55

---

## KILLED (executed)

| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| — | — | — | — | — | None met kill criteria |

No signal has WR < 30% with 5+ trades AND PnL < -$0.10 (24h).

---

## BOOSTED (executed)

| Signal | Dir | WR | PnL | Trades | Action |
|--------|-----|-----|-----|--------|--------|
| — | — | — | — | — | None met boost criteria |

bb-bounce-v2-long+ has 57.1% WR (7 trades) but PnL is -$0.05 — fails the PnL > $0.05 gate.

---

## LOSERS (watch list)

| Signal | Dir | 24h WR | 24h PnL | Trades | Status |
|--------|-----|--------|---------|--------|--------|
| continuation+ | LONG | 50.0% | -$0.18 | 4 | WATCH — needs 5+ trades to judge |
| pump-chain+ | LONG | 0.0% | -$0.16 | 2 | WATCH — HIGH regime already blocked |
| r2v2-long3 | LONG | 50.0% | -$0.14 | 4 | WATCH — needs 5+ trades to judge |
| r2v2-long4 | LONG | 0.0% | -$0.12 | 2 | WATCH — sample too small |
| bb-bounce-v2-long+ | LONG | 57.1% | -$0.05 | 7 | WATCH — winning WR, small net loss |

---

## WINNERS

| Signal | Dir | 24h WR | 24h PnL | Trades | Status |
|--------|-----|--------|---------|--------|--------|
| warrior-sr-confirm+ | LONG | 100.0% | +$0.11 | 1 | OK |
| ai-trader-pending | SHORT | 100.0% | +$0.11 | 1 | OK (manual) |
| r2v2-long7 | LONG | 100.0% | +$0.04 | 1 | OK |
| continuum-trend+ | LONG | 50.0% | +$0.01 | 2 | OK |

---

## ISSUES
- No direction inversions found (24h).
- Low trade volume: 6h window had only 1 closed trade — no signal qualified for 6h analysis (HAVING COUNT >= 2 returned empty).
- 6h winners/losers indeterminate this cycle.

---

*Report auto-generated from brain DB. Next report: ~6h from now.*

---

## PARAM CHANGE LOG (last 7 days)

| Date | Commit | Change |
|------|--------|--------|
| 2026-10-22 | 2d78f19 | Daily trading system update (2026-10-22) |
| 2026-10-22 | 24225f3 | brain_auditor: AUDIT RUN #69 — BTC-regime habitat map verifi... |
| 2026-10-22 | 0747cdd | scripts: wire shadow_signals_runner into pipeline with shado... |
| 2026-10-21 | 0c57042 | plans: spec v2 autonomous BTC loop — CEO answers baked in: B... |
| 2026-10-21 | c625517 | skills+data: add §12 no-edge default (CEO directive — arm th... |
| 2026-10-21 | 6fee8ef | scripts: shadow-registry + shadow-bypass system (T directive... |
| 2026-10-21 | 1630544 | Daily trading system update (2026-10-21) |
| 2026-10-21 | c9092ae | signals: block pump-chain+ LONG in HIGH regime — 37%WR $-0.4... |
| 2026-10-20 | 06e7bd3 | fix: ichimoku bypass — bug_hunter FAIL fixes (CRITICAL + HIG... |
| 2026-10-20 | a1b8095 | signals: ichimoku LONG standalone bypass (CEO regime-conditi... |

*Changes to `scripts/hermes_constants.py`. Use `git show <commit>` for details.*
