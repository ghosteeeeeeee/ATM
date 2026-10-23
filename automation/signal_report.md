# Signal Performance Report
**Generated:** 2026-10-23 21:35 UTC | **Period:** Last 6h + 24h

## Summary
- **Trades closed:** 2 (6h) | 19 (24h) — low flow, pipeline healthy (LIVE, 1 open position)
- **Kills executed:** 0 — no signal met kill criteria this cycle
- **Boosts executed:** 0 — no signal met boost criteria (5+ trades)
- **Inversions:** 0

---

## KILLED (executed)

None — no signal met all three kill criteria (WR<30%, 5+ trades, PnL<-$0.10, active>24h).

---

## BOOSTED (executed)

None — closest candidates fell short on trade count.

---

## LOSERS (watch list)

| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| volume-buildup- | SHORT | 42.9% | -$0.36 | 7 (24h) | WATCH — 7d: 44.4% WR, -$0.31, 9T. Regimes (7d): EXTREME 50% (n=4), NORMAL 25% (n=4). No regime ≥55% WR, but 24h WR ≥30% → no kill per rules. Bleeding small losses consistently — revisit if 24h WR drops below 35%. |
| bb-bounce-v2-long+ | LONG | 0.0% | -$0.25 | 2 (24h) | WATCH — only 2T (kill needs 5+). 7d: 17T, 47.1% WR, -$0.58. Both 24h losses via hard_max_loss/hard_sl. Not a kill, not a boost. |
| pump-chain+ | LONG | 0.0% | -$0.07 | 1 (24h) | WATCH — sample too small. HIGH-regime block already shipped 2026-10-21. |
| ai-trader-pending | SHORT/LONG | 0.0% | -$0.05 | 2 (24h) | Manual/pending orders — outside signal governance. |

## WINNERS

| Signal | Dir | WR | PnL | Trades | Status |
|--------|-----|-----|-----|--------|--------|
| warrior-sr-confirm- | SHORT | 100.0% | +$0.16 | 2 (24h) | ENABLED — below 5T boost threshold; single-token (hyperliquid). Re-check next cycle. |
| bb-squeeze+ | LONG | 66.7% | +$0.10 | 3 (24h) | ENABLED — below 5T boost threshold; single-token (hyperliquid). Re-check next cycle. |
| r2v2-long4 | LONG | 100.0% | +$0.01 | 1 (24h) | ENABLED — sample too small. |

---

## SIGNAL INVERSIONS (24h)

**No inversions found.** All signals respect their direction labels.

---

## ISSUES

- **Low trade throughput:** only 2 closes in the last 6h (19 in 24h). Pipeline is running normally (LIVE, sync clean) — likely just quiet flow, but watch the next cycle for a stall.
- **`[hotset] fallback DB query returned 0 tokens`** in pipeline.log — hotset fallback returns empty; low severity, worth a look if hotset dashboard shows blank.
- **Boost candidates concentrated on one token:** both near-boost winners (warrior-sr-confirm-, bb-squeeze+) are hyperliquid-only — not yet "consistent across multiple tokens."

---

## RECOMMENDATIONS

1. **[WATCH] volume-buildup- SHORT** — persistent small bleed (7d -$0.31). Monitor WR; if 24h WR <30% with 5+ trades next cycle, kill.
2. **[NO ACTION] bb-bounce-v2-long+** — 2T insufficient. Accumulate more data.
3. **[RE-CHECK] warrior-sr-confirm- / bb-squeeze+** — promote to boost if either hits 5T with WR>55% next cycle.

---

*Report auto-generated. Next report: ~6h from now.*

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
