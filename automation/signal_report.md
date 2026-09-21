# Signal Performance Report
**Generated:** 2026-09-21 17:09 UTC | **Period:** Last 6h + 24h

## Overall Stats
- **Total trades (all time):** 5,231
- **Date range:** 2026-05-20 → 2026-09-21
- **7d closed trades:** 193

---

## 6h Performance (1+ trades)

| Signal | Dir | Trades | WR | PnL |
|--------|-----|--------|-----|-----|
| mover+ | LONG | 1 | 100.0% | +$0.13 |
| pump-chain+ | LONG | 3 | 33.3% | -$0.07 |
| doji-bottom-long | LONG | 2 | 50.0% | -$0.19 |

## 24h Performance (2+ trades)

| Signal | Dir | Trades | WR | PnL |
|--------|-----|--------|-----|-----|
| pump-chain+ | LONG | 14 | 50.0% | +$1.17 |
| volume-breakout-long+ | LONG | 2 | 50.0% | +$0.57 |
| doji-bottom-long | LONG | 3 | 33.3% | -$0.34 |

---

## KILLED (executed): None

No signal meets kill criteria (WR <30% with 5+ trades, net PnL < -$0.10 over 24h, active >24h).

---

## BOOSTED (executed): None

No signal meets all boost criteria (WR >55% with 5+ trades, consistent across tokens). pump-chain+ is the closest at 50% WR / 14 trades — borderline, needs WR bump.

---

## LOSERS (watch list)

| Signal | Dir | Trades | WR | PnL | Status | Notes |
|--------|-----|--------|-----|-----|--------|-------|
| doji-bottom-long | LONG | 3 | 33.3% | -$0.34 | WATCH | Lifetime: 66.7% WR (6 trades, +$0.40). 24h noise — too few trades to kill. NORMAL regime is 0% WR (1 trade). |
| pullback-entry- | SHORT | 1 | 0% | -$0.17 | NO ACTION | Lifetime: 55.4% WR (112 trades, +$2.04). 1 trade = noise. |
| bb-bounce-v3-long+ | LONG | 1 | 0% | -$0.02 | NO ACTION | Brand new signal (first seen today). No data. |
| r2-trend-short3 | SHORT | 1 | 0% | -$0.02 | NO ACTION | 4 lifetime trades. Minimal activity. |

---

## WINNERS

| Signal | Dir | Trades | WR | PnL | Status | Notes |
|--------|-----|--------|-----|-----|--------|-------|
| pump-chain+ | LONG | 14 | 50.0% | +$1.17 | ACTIVE | Spread across 12 tokens. Winners: ADA (+0.52), JUP (+0.47), CASHCAT (+0.43), ETC (+0.30), AIXBT (+0.09), ACE (+0.06). Losers: HEMI (-0.28), CAKE (-0.18), ALGO (-0.15). |
| volume-breakout-long+ | LONG | 2 | 50.0% | +$0.57 | ACTIVE | FIL (+0.74), HYPER (-0.17). Too few trades to call. |
| mover+ | LONG | 1 | 100% | +$0.13 | ACTIVE | 1 trade. No verdict yet. |
| accel-300-breakout,rs-r64,rs-r66 | SHORT | 1 | 100% | +$0.17 | ACTIVE | 1 trade. Combo signal, no verdict. |
| continuum- | SHORT | 1 | 100% | +$0.02 | ACTIVE | 1 trade. No verdict. |

---

## SIGNAL INVERSIONS (24h)

**None found.** All signals respect their direction labels.

---

## ISSUES

- **doji-bottom-long NORMAL regime:** 0% WR (1 trade) vs 50% WR in HIGH (2 trades). Too few trades for regime-based blocking. Monitor next cycle — if NORMAL continues losing, add regime gate.
- **pump-chain+ spread:** Performing well across tokens but some losers (HEMI, CAKE, ALGO). These are coin-specific, not signal-level — no action needed unless a token consistently loses.

---

## PARAM CHANGE LOG (last 7 days)

| Date | Commit | Change |
|------|--------|--------|
| 2026-09-21 | 8f7d401 | config: squeeze_breakout cooldown 4h → 20min |
| 2026-09-21 | 4f77803 | fix: squeeze_breakout — move all magic numbers to hermes_constants |
| 2026-09-21 | 1ec8df2 | feat: squeeze_breakout signal — consolidation breakout catcher |
| 2026-09-21 | 874094c | Oscillator Matrix: shadow mode implementation |
| 2026-09-21 | 8b63f41 | Fix: BTC_LEVEL constants — remove dead code, add tunable params |
| 2026-09-21 | ac16c94 | brain_auditor: UNIVERSAL_MAX_HOLD_MINUTES=480 safety net |
| 2026-09-21 | ba0c034 | config: CONF_FILTER_MAX 89→92 (conservative) |
| 2026-09-21 | 8c09684 | fix: ride_it_exit no-op replace + pump_exit datetime bug |
| 2026-09-21 | ba7a244 | config: raise CONF_FILTER_MAX from 89 to 96 |
| 2026-09-21 | 039a3fe | config: add continuum-osc and volume-breakout to PM Trail by default |

*Changes to `scripts/hermes_constants.py`. Use `git show <commit>` for details.*

---
*Report generated 2026-09-21 17:09 UTC. Next report: ~6h.*
