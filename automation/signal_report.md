# Signal Performance Report
**Generated:** 2026-09-23 17:08 UTC | **Period:** Last 6h + 24h

## Overall Stats
- **24h:** 23 trades | WR: 39.1% | PnL: -$1.15
- **6h:** 3 trades | WR: 33.3% | PnL: -$0.08
- **All-time:** 5,280 closed trades

---

## KILLED (executed)

None. No signals meet kill criteria (5+ trades, WR<30%, net PnL<-$0.10 in 24h).

---

## BOOSTED (executed)

None. No signals meet boost criteria (5+ trades, WR>55%, PnL>$0.05 in 24h). Quiet 24h window.

---

## LOSERS (watch list)

| Signal | Dir | 24h T | 24h WR | 24h PnL | Lifetime T | Lifetime WR | Lifetime PnL | Status |
|--------|-----|-------|--------|---------|------------|-------------|--------------|--------|
| pullback-entry- | SHORT | 3 | 0.0% | -$0.59 | 119 | 52.1% | +$0.35 | WATCH — bad 24h in EXTREME, overall profitable |
| mover+ | LONG | 3 | 33.3% | -$0.34 | 18 | 66.7% | -$0.24 | WATCH — high WR but bad R:R (avg loss > avg win) |
| bb-bounce-v2-long+ | LONG | 9 | 44.4% | -$0.10 | 14 | 42.9% | -$0.55 | WATCH — persistent underperformer |
| accel-300-breakout | SHORT | 2 | 50.0% | -$0.05 | — | — | — | WATCH — needs more data |

---

## WINNERS

| Signal | Dir | 24h T | 24h WR | 24h PnL | Status |
|--------|-----|-------|--------|---------|--------|
| volume-breakout-long+ | LONG | 2 | 50.0% | +$0.05 | Small sample |
| bb-bounce-v2-long+,rs-s39 | LONG | 1 | 100% | +$0.04 | Combo, needs data |
| continuum-osc+ | LONG | 1 | 100% | +$0.01 | Single trade |

---

## SIGNAL INVERSIONS (24h)

**No inversions found.** All signals respect their direction labels.

---

## REGIME ANALYSIS (kill candidates)

- **pullback-entry SHORT** — 24h losses all in EXTREME regime (ATR SL hits). Lifetime: EXTREME 53.3% WR +$0.33, HIGH 53.2% +$0.39, NORMAL 44.1% -$0.79. Signal is regime-dependent; NORMAL is the drag.
- **mover+ LONG** — 24h: EXTREME 0% WR -$0.22, HIGH 50% -$0.12. Lifetime EXTREME: 57.1% WR but -$0.48 (bad R:R). HIGH: 66.7% +$0.09. EXTREME regime is the problem.
- **bb-bounce-v2-long+ LONG** — 24h: HIGH 50% -$0.07, EXTREME 100% +$0.04. Lifetime EXTREME: 66.7% -$0.20 (bad R:R). HIGH: 50% -$0.06. Marginal everywhere.

---

## RECOMMENDATIONS

1. **[NO ACTION]** — 24h is too quiet (23 trades) to justify kills. All losers have <5 trades in the window.
2. **[WATCH] mover+ LONG** — High WR (66.7% lifetime) but negative PnL. EXTREME regime losses are larger than HIGH wins. Consider blocking EXTREME regime via `volatility_gate_v2.py` if next cycle confirms.
3. **[WATCH] bb-bounce-v2-long+ LONG** — Persistent small loser. 42.9% lifetime WR, -$0.55. Needs 20+ more trades before kill decision.
4. **[WATCH] pullback-entry SHORT** — Good signal overall. The 24h EXTREME losses are noise (3 trades). No action needed.

---

*Report auto-generated. Next report: ~6h from now.*

---

## PARAM CHANGE LOG (last 7 days)

| Date | Commit | Change |
|------|--------|--------|
| 2026-09-23 | 2f756ed | Signals: Complete pump_chain_v5_short following add-signal c... |
| 2026-09-23 | e61cd1f | Fix: add accel-30 to STANDALONE_BYPASS_SIGNALS |
| 2026-09-23 | b50be86 | fix: add return-exhaustion-short (hyphen) to bypass list — w... |
| 2026-09-23 | 2f23e0a | signals: add pullback-entry- SHORT dead hours 0,1,10,11 |
| 2026-09-23 | f52bb96 | fix: RR_ENGINE_CONF_HARD_BLOCK_RR 0.95→0.70 — allow lower R:... |
| 2026-09-23 | 6b66d7c | fix: SHORT_RSI_FLOOR 50→40 — 50 blocked SHORT in downtrends,... |
| 2026-09-23 | a668cbf | brain_auditor: 12:00 UTC audit — no config change, 3 creativ... |
| 2026-09-23 | cec7ef3 | brain_auditor: LONG_RSI_FLOOR=30 added (Sep 23 ~08:00 UTC) |
| 2026-09-23 | 393ad43 | brain_auditor: SHORT_RSI_FLOOR 35→50 + audit report |
| 2026-09-23 | d339ea7 | CEO: Fix dead hours bug + correct dead hours configs |

*Changes to `scripts/hermes_constants.py`. Use `git show <commit>` for details.*
