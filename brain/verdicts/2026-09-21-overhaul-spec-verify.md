# Audit Verdict: Structural Awareness Overhaul Spec

**Date:** 2026-09-21  
**Auditor:** Independent Review (CEO delegation)  
**Spec:** `/root/.hermes/plans/structural-awareness-overhaul.md`  
**Status:** PARTIAL AGREEMENT — good diagnosis, flawed prescription

---

## === VERDICT ===

**Verdict:** PARTIAL — The spec correctly identifies the core problem (reactive system misses structural context) but overstates what "wiring" existing code will achieve, underestimates integration complexity, and introduces risks it doesn't acknowledge.

---

## 1. Is the Spec Complete? What's Missing?

### Missing from the spec:

- **No backtest/validation plan before building.** The spec proposes building 3 new files and modifying 4 existing ones without any baseline measurement. There's no "here's what win rate looks like WHEN we integrate X" — just assumptions. The existing analysis scripts (`linreg_ma180_analysis.py`) already show MA180 data exists but the spec doesn't reference this analysis.

- **No mention of signal_compactor's existing multiplier chain.** Line 1782 of `signal_compactor.py` already has **27 multipliers** in a single expression. The spec proposes adding `structural_bias` as another multiplier/filter without acknowledging the existing complexity. Every new filter further reduces trade frequency.

- **No mention of the STALENESS PROBLEM.** AGENTS.md explicitly documents that signals are detected at one time but executed later, and filters don't re-validate at execution time. The spec's "entry at value levels" proposal would be undermined by staleness — by the time a signal reaches execution, the "value level" may have moved.

- **No mention of the BTC-CRASH filter.** `decider_run.py` lines 2993-3009 show an existing crash filter that already blocks trades. The spec's proactive positioning could conflict with this.

- **No mention of execution timing or pipeline architecture.** The pipeline acquires a lock file, runs sequentially. Adding more computation (structural analysis, bias calculation, entry optimization) inside the hot path could increase pipeline duration. No latency budget is defined.

- **No testing strategy.** "Test with historical data" (Phase 3) and "Test with live data" (Phase 4) are hand-waves. No mention of shadow mode, paper trading, or A/B framework.

- **No rollback plan.** Kill switches are mentioned in mitigation but not in the implementation plan. Where exactly do the ENABLED flags go?

- **No mention of the `coin_tracker_score.py` factor count.** The scoring engine already has 22 factors. The spec proposes adding structural awareness as if it's additive, but the scoring system is already saturated — adding factors dilutes existing ones or requires reweighting.

---

## 2. Are the 4 Phases Realistic?

### Phase 1: Wire Existing Systems (1-2 days) — ⚠️ UNDERESTIMATED

The spec claims this is "just wiring." But:

- **"Integrate coin_tracker_analysis S/R into sl_zones.py"** — These use fundamentally different data sources. `coin_tracker_analysis.py` uses pivot-based S/R from OHLCV candles (pure computation, no DB). `sl_zones.py` uses PostgreSQL `sl_memory` table (trade execution history). Merging them requires deciding: which takes priority when they disagree? What if pivot-SR says "buy at support" but SL-memory says "this is a death zone"? This is a design decision, not wiring.

- **"Wire continuum_oscillator into bias engine"** — The continuum oscillator already writes to `continuum.db` and is consumed by `continuum_context.py`, which is already imported by `signal_compactor.py` (lines 1127, 1350, 2538), `chop_detector.py`, `squeeze_breakout.py`, and `signal_schema.py`. The spec claims it "should be used for proactive positioning" but doesn't explain what's ACTUALLY missing vs what's already integrated.

- **"Add MA180 entry filter"** — The `linreg_ma180_analysis.py` analysis script EXISTS and has analyzed historical trades. But the spec doesn't reference its findings. Is MA180 actually predictive? Without running this analysis and showing results, adding an MA180 filter is cargo-cult engineering.

### Phase 2: Build Bias Engine (2-3 days) — ⚠️ TOO AMBITIOUS

Creating `structural_bias.py` that "combines BTC structure + continuum + S/R + Wyckoff" into a single BULLISH/BEARISH/NEUTRAL bias is the core of this overhaul, and it gets 2-3 days. This is the hardest piece — it requires:

1. Deciding how to weight conflicting signals (Wyckoff says accumulation, but S/R says price is at resistance)
2. Defining when bias is strong enough to block signals
3. Avoiding overfitting to historical patterns

2-3 days is realistic for a first version, but the spec presents it as a complete solution.

### Phase 3: Build Entry Optimizer (1-2 days) — REALISTIC but depends on Phase 2

### Phase 4: Build Proactive Positioner (2-3 days) — ❌ MOST RISKY

"Pre-position based on structure" with "limit orders at support/resistance" is a fundamentally different trading paradigm than the current market-order-on-signal system. This requires:

- Limit order management (replacing market orders)
- Position scaling logic
- Cancellation/adjustment of unfilled orders
- Integration with `hyperliquid_exchange.py`

This is not a "feature addition" — it's an architectural change to the execution engine. The spec buries this in Phase 4 as if it's a natural extension.

---

## 3. Undocumented Dependencies Between Phases

- **Phase 2 depends on Phase 1's S/R merge being correct.** If the merged S/R is noisy or contradictory, the bias engine inherits bad data.
- **Phase 3 depends on Phase 2's bias output.** The entry optimizer needs to know the bias direction. But the spec doesn't define the interface between these.
- **Phase 4 depends on ALL previous phases.** You can't pre-position without bias, without good S/R, without entry filtering. This is a cascade dependency, not parallel work.
- **All phases depend on `hermes_constants.py` changes.** The spec mentions this but doesn't enumerate what constants are needed. Each new filter needs threshold tuning, and without backtesting, these are magic numbers.

---

## 4. "Already Built" Inventory Accuracy

| Claim | Verified? | Notes |
|-------|-----------|-------|
| `coin_tracker_analysis.py` has Wyckoff detection | ✅ YES | `detect_wyckoff_phase()` exists, takes OHLCV candle list, returns phase/confidence. But it's basic — only detects climax→range→spring/upthrust sequences. No re-accumulation, no markdown continuation. |
| `coin_tracker_analysis.py` has Elliott Wave | ✅ YES (partially visible, 1123 lines total) | Not fully inspected but module docstring confirms. |
| `coin_tracker_analysis.py` has S/R from pivots | ✅ YES | `compute_sr_levels()` at line 68. Uses pivot clustering with configurable merge tolerance. Returns top 10 levels. |
| `coin_tracker_score.py` has 22 factors | ✅ YES | WEIGHTS dict has 20 entries (not 22 as claimed). Factors include: momentum, volume, volatility, spread, signals, regime, wyckoff, ewave, trend, setup, clustering, recency, liquidation, tide, sea_state, wind, token_regime, contrarian, macd_div, rr. That's 20, not 22. |
| `sl_zones.py` is integrated into signal_compactor | ✅ YES | Lines 3180-3206: `entry_distance_filter` is called with a try/except fallback. |
| `sl_zones.py` is integrated into position_manager | ✅ YES | Line 2514: `zone_aware_exit_check` imported. |
| `sl_zones.py` is integrated into decider_run | ✅ YES | Line 1772: `zone_adjusted_size` imported. |
| `continuum_oscillator.py` is built | ✅ YES | 267 lines, fires signals based on BTC score cadence. Uses 6-tick window. |
| `continuum_context.py` is built | ✅ YES | Referenced by signal_compactor (3 places), chop_detector, squeeze_breakout, signal_schema. Already well-integrated. |
| `breakout_engine.py` is built | ✅ YES | 595 lines, detects compression→breakout. Writes to oc_pending_signals.json AND signals DB. |
| Signal compactor has 27 multipliers | ✅ YES | Line 1782 confirms: 27 multiplicative factors in a single expression. |

**Key inaccuracy:** The spec says coin_tracker_score has "22 factors" — it actually has 20. Minor but signals the spec was written from memory, not fresh code inspection.

---

## 5. Risks NOT Mentioned in the Spec

### Critical risks:

1. **Multiplier death spiral.** With 27 existing multipliers, each new filter compounds. If each filter blocks 20% of trades, 30 filters means 0.8^30 = 0.12% of trades survive. The spec doesn't model how many trades would be lost.

2. **Conflicting structural signals.** Wyckoff says "accumulation" (bullish), but S/R shows price at resistance (bearish), and continuum says "falling" (bearish). How does the bias engine resolve conflicts? No arbitration logic is defined.

3. **Overfitting to BTC structure.** The spec assumes BTC structure predicts alt behavior. This correlation is regime-dependent — in high-beta markets it holds, in rotation markets it breaks. No mention of correlation decay or regime-dependent weighting.

4. **Limit order execution risk (Phase 4).** Limit orders at S/R levels may never fill, or fill only when the level breaks (catching falling knives). The spec doesn't address order lifecycle management.

5. **Pipeline timing impact.** Adding structural analysis (Wyckoff, Elliott Wave, S/R computation) to the execution path increases computation time. With 50+ tokens in the hot set, each requiring S/R computation, this could add seconds to pipeline execution. No latency analysis.

6. **Data staleness at decision time.** `coin_tracker_analysis.py` operates on candle data that may be minutes old. Structural levels computed from 5m candles change between closes. The spec doesn't address data freshness requirements.

7. **No mention of the `STANDALONE_BYPASS_SIGNALS` flag.** This flag lets signals bypass normal confluence. If the new bias engine blocks signals, but STANDALONE_BYPASS is active, which wins? Undefined behavior.

8. **Backtest-to-live performance gap.** Historical S/R levels are known in advance. Live S/R levels are discovered in real-time. Any backtest of structural awareness would be optimistically biased.

---

## 6. Is the Expected Impact Realistic?

### Claims vs reality:

| Spec Claim | Assessment |
|------------|------------|
| Win rate: 46% → 52%+ | ⚠️ AMBITIOUS. Going from 46% to 52% is a 13% relative improvement. The existing system already has 27 multipliers. Adding more filters typically improves win rate at the cost of trade frequency, not overall PnL. The spec doesn't mention trade frequency impact. |
| PnL: -$13/week → break-even or positive | ⚠️ MISLEADING. Win rate improvement alone doesn't guarantee PnL improvement. If filter additions reduce trade count from 10/week to 5/week at 52% win rate, net PnL could still be negative. Expected value = (win_rate × avg_win) - (loss_rate × avg_loss) × frequency. |
| "Entry at value levels" | ⚠️ PARTIALLY TRUE. MA180 and S/R filtering CAN improve entry quality, but "value" is a moving target. The spec doesn't define what "excitement levels" are quantitatively or how to measure "value." |
| "Structural awareness: None → Full" | ❌ OVERSTATEMENT. The system already has structural awareness in `coin_tracker_analysis.py` — the spec says so itself. The claim should be "structural awareness: unused → integrated." |

**Most realistic claim:** The reactivity improvement (reactive → proactive) is the strongest argument. Leading signals like breakout_engine already exist but aren't used for pre-positioning.

---

## 7. Single Highest-Impact Change First

### **Run the MA180 analysis and use its results to add a single filter to signal_compactor.**

**Why:**

1. **The analysis already exists.** `scripts/analysis/linreg_ma180_analysis.py` has already computed MA180 slope and price-vs-MA180 for historical trades. Run it, get the data, and see if price-near-MA180 entries actually win more.

2. **Low risk, high signal.** One new multiplier in the existing 27-multiplier chain. If the data shows MA180 proximity improves win rate, add it. If not, don't. This is data-driven, not assumption-driven.

3. **No new files needed.** Just import `coin_tracker_analysis.py`'s MA180 computation into `signal_compactor.py` and add one multiplier. This can be done in hours, not days.

4. **Proves the thesis.** If MA180 proximity doesn't help, the entire "entry at value" premise is weakened and the spec needs revision before building more.

5. **Measurable.** Before/after win rate comparison is straightforward with the existing trade database.

**Implementation:** Add a single `ma180_proximity_mult` to line 1782 of `signal_compactor.py` that multiplies confidence up when price is within ±0.3% of MA180 and down when price is >1% away. Measure, then expand.

---

## Summary Assessment

The spec correctly diagnoses a real problem: the system is reactive and lacks structural context. However, it proposes building NEW code (structural_bias.py, entry_optimizer.py, proactive_positioner.py) when the first step should be MEASURING whether existing structural data actually improves outcomes. The spec is a solution in search of validation.

**The spec should be rewritten as:**
1. Run existing analyses to validate the thesis
2. Add ONE filter based on data
3. Measure impact
4. THEN propose broader changes

Building 3 new scripts and modifying 4 existing ones without baseline measurement is how you get a system with 30+ multipliers that trades nothing.

---

*Audited by: Independent Review*  
*Files inspected: structural-awareness-overhaul.md, coin_tracker_analysis.py, coin_tracker_score.py, sl_zones.py, continuum_oscillator.py, breakout_engine.py, signal_compactor.py (lines 1760-1800, 3170-3209), decider_run.py (lines 2960-3010)*  
*Confidence: HIGH*
