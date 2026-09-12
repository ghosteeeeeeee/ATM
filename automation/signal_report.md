# Signal Performance Report
**Generated:** 2026-09-12 15:30 UTC | **Period:** Last 6h + 24h

## Overall Stats (24h)
- **Total trades:** 24 | **WR:** 54.2% | **Net PnL:** -0.28 USDT
- **Active signals:** 14 unique signal+direction combos

---

## WINNERS (WR > 55%, PnL > 0)

| Signal | Dir | 6h T | 6h WR | 6h PnL | 24h T | 24h WR | 24h PnL | Status |
|--------|-----|------|-------|--------|-------|--------|---------|--------|
| rr-struct+ | LONG | 2 | 50.0% | -0.12 | 5 | 80.0% | +0.02 | ✅ KEEP |
| pump-chain- | SHORT | — | — | — | 9 | 66.7% | -0.10 | ⚠️ WATCH |
| mover- | SHORT | — | — | — | 2 | 100% | +0.20 | ✅ KEEP |
| mover+ | LONG | — | — | — | 1 | 100% | +0.31 | ✅ KEEP |

---

## LOSERS (Kill candidates: WR < 30%, 5+ trades, PnL < -$0.10)

**None meet all kill criteria.**

| Signal | Dir | 24h T | 24h WR | 24h PnL | Regime Issue | Action |
|--------|-----|-------|--------|---------|--------------|--------|
| pullback-entry- | SHORT | 4 | 25.0% | -0.28 | Fails in NORMAL (42.9% WR) | TUNE — block NORMAL |
| rr-struct- | SHORT | 3 | 33.3% | -0.25 | Only HIGH regime (33.3% WR) | WATCH — too few trades |

---

## MARGINAL (30-50% WR or negative PnL with decent WR)

| Signal | Dir | 24h T | 24h WR | 24h PnL | Status | Note |
|--------|-----|-------|--------|---------|--------|------|
| trend_purity+ | LONG | 8 | 50.0% | -0.15 | ENABLED | Active < 24h, needs more data |
| pump-chain- | SHORT | 9 | 66.7% | -0.10 | ENABLED | Good WR but small net loss |

---

## REGIME ANALYSIS (key findings)

**pullback-entry- SHORT** — Works in volatile markets, fails in calm:
- EXTREME: 77.8% WR (9 trades) ✅
- HIGH: 64.7% WR (17 trades) ✅
- NORMAL: 42.9% WR (7 trades) ❌ → **Block NORMAL regime**

**pump-chain- SHORT** — Consistent across regimes:
- EXTREME: 62.5% WR (24 trades) ✅
- HIGH: 61.5% WR (13 trades) ✅
- NORMAL: 66.7% WR (3 trades) ✅

**rr-struct- SHORT** — Only HIGH regime, underperforming:
- HIGH: 33.3% WR (3 trades) ❌

---

## SIGNAL INVERSIONS (24h)

**No inversions found.** All signals respect their direction labels.

---

## RECOMMENDATIONS

1. **[TUNE] pullback-entry- SHORT** — Add NORMAL regime block in volatility_gate_v2.py. Signal works in EXTREME/HIGH but loses in NORMAL. 4 trades is below kill threshold but regime pattern is clear.
2. **[WATCH] rr-struct- SHORT** — 33.3% WR over 3 trades. All in HIGH regime. Monitor next cycle — if WR stays <40% with 5+ trades, kill.
3. **[WATCH] trend_purity+ LONG** — 50% WR, -$0.15 PnL over 8 trades. Active < 24h. Needs more data before acting.
4. **[KEEP] rr-struct+ LONG** — 80% WR, +$0.02 PnL. Small sample (5 trades) but solid.

---

*Report auto-generated. Next report: ~6h from now.*

---

## PARAM CHANGE LOG (last 7 days)

| Date | Commit | Change |
|------|--------|--------|
| 2026-09-12 | 194dbbb | CEO: Verified profitable — 24h 42T 66.7% WR |
| 2026-09-12 | b91d353 | bug-hunter: fix 3 medium + 1 low in trend_purity |
| 2026-09-12 | 195214e | Brain RAG System: session_brain.py, brain auditor, dashboard |
| 2026-09-12 | d0c64cd | config: volume_breakout to volatility gate + standalone bypass |
| 2026-09-12 | 1391a81 | config: trend_purity uses RR engine + ATR SL (not PM Trail) |
| 2026-09-12 | 1ca70cc | config: trend_purity uses pm_trail + atr_sl (default, not rr_engine) |
| 2026-09-12 | e486894 | config: pump-chain uses BOTH pm_trail + rr_engine (tightest stop) |
| 2026-09-12 | 4375531 | fix: add pump_chain underscore variants to PROFIT_MONSTER_BY_SIGNAL |
| 2026-09-12 | 8e54f00 | config: trend_purity signals use RR engine exits |
| 2026-09-12 | 5bf77ff | Config: Add pm_trail exit system for trend_purity signals |

*Changes to `scripts/hermes_constants.py`. Use `git show <commit>` for details.*
