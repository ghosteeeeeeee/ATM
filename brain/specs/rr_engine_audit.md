# Independent Audit: Risk-Reward Engine Spec

**Auditor:** Independent Review (subagent)
**Date:** 2026-08-26
**Files Reviewed:** 13 source files, 1 spec document

---

## Overall Verdict

**APPROVE WITH CHANGES** — The concept is sound and the architecture is right for the system, but the spec has several implementation bugs, data-source mismatches, and logical gaps that would cause failures or wrong behavior at runtime if implemented as-is.

---

## Strengths

1. **Right problem, right approach.** The current `rr_gate()` is genuinely weak — SL is purely ATR-based (no structural context), TP is a naive nearest-swing capped at 2.5%, and there's no liquidity awareness. The proposed multi-source S/R map with regime-adjusted thresholds is the correct upgrade path.

2. **Drop-in integration (Option A) is the right call.** Upgrading `rr_gate()` internally while keeping the same return signature means zero changes to any signal file. This is exactly how the system should evolve — one gate file changes, everything benefits.

3. **Shadow mode is well-designed.** The three-flag approach (`RR_ENGINE_ENABLED`, `RR_ENGINE_SHADOW`, `RR_ENGINE_FORCE`) mirrors the proven `monte_carlo_gate_oracle()` pattern. Starting in shadow mode, collecting data, then switching to enforcement is the right rollout strategy.

4. **Fail-open philosophy is maintained.** The spec explicitly says `RR_ENGINE_FAIL_OPEN = True` and the integration code catches all exceptions with `return True, 0, 0, 999`. This matches the existing gate pattern — critical.

5. **Composite scoring with grade bands.** The 0-100 scoring with A/B/C/D/F grades maps cleanly to the existing `SIGNAL_QUALITY_MIN_GRADE = 'C'` constant. This is not accidental — the spec was written with the system's existing quality framework in mind.

6. **No new API calls.** All data sources already exist (atr_cache.json, candles.db, liquidation_clusters.json). Zero new API calls means zero new rate-limit risk.

---

## Weaknesses / Gaps

### Critical (will break at runtime)

**W1: Python constant name contains Chinese characters — syntax error.**
Line 453 of the spec: `RR_ENGINE_SL_STRUCTURAL缓冲 = 0.002` — the constant name contains `缓冲` (Chinese for "buffer"). Python will reject this. Must be renamed to `RR_ENGINE_SL_STRUCTURAL_BUFFER = 0.002`.

**W2: ATR cache stores dollar ATR, spec expects ATR%.**
`atr_cache.py` stores `{token: {atr: <dollar_value>, ts: <unix>}}` — e.g., `atr: 45.23` for ETH. But the spec's `compute_vol_width()` reads `atr_cache.json` expecting `atr_pct`. The existing `entry_gates.py::_get_cached_atr()` tries `entry.get('atr_pct', entry.get('atr')` — which falls back to the raw dollar ATR. If `atr_pct` is missing (it is — only `atr` is stored), the code gets a raw dollar value (e.g., 45.23) and treats it as a percentage. This would classify everything as EXTREME regime and break R:R calculations.

**Fix:** Either:
- (a) Have `compute_vol_width()` convert dollar ATR to ATR% using `atr_dollar / price * 100`, OR
- (b) Add `atr_pct` to atr_cache.json when writing it, OR
- (c) Read from `volatility_gate.get_atr_pct()` which correctly computes ATR% from candles.

The spec mentions "fallback to candles computation" but doesn't implement the conversion. This must be explicit.

**W3: `signal_type` parameter missing from `_compute_score()`.**
The scoring function uses `signal_type` in `_regime_alignment_pts(regime, signal_type)` but:
- `signal_type` is not a parameter of `_compute_score()`
- `signal_type` IS a parameter of the top-level `evaluate_rr()` but isn't passed down
- The function signature on line 312 is `_compute_score(rr_ratio, vol_width, liquidity, sr_map)` — no `signal_type`

This will cause a `NameError` at runtime.

### Significant (wrong behavior or suboptimal design)

**W4: BB_STDDEV mismatch with existing implementations.**
The spec proposes `RR_ENGINE_BB_STDDEV = 2.0`. But `range_finder.py` uses `BB_STDDEV = 1.8` and `bb_bounce.py` also uses `BB_STDDEV = 1.8`. Using 2.0 in the engine means the engine's BB width calculation will produce different values than the signals that actually use BB. This is inconsistent and will lead to wrong squeeze detection. Use 1.8 to match the existing system.

**W5: Swing detection window inconsistency.**
The spec proposes `SR_LOOKBACK_CANDLES = 300` and `window=5` for swing detection. But:
- `entry_gates.py` uses `n=3` (7-bar window)
- `rs_signals.py` uses `RS_LEVEL_LOOKBACK = 20` (40-bar window)
- `momentum_leaderboard.py` uses `window=5` (11-bar window)
- `coin_tracker_analysis.py` uses `left=5, right=5` (11-bar window)

None of these match `window=5` for the N-bar detection with 300 candles lookback. The spec should specify which existing implementation to match. Given the S/R signal (rs_signals.py) is the most battle-tested, using `window=20` from that implementation (or at least documenting the discrepancy) would be better.

**W6: EXTREME regime R:R of 2.0 seems wrong.**
The regime table says EXTREME (>1.5% ATR) needs R:R ≥ 2.0. But the existing `volatility_gate.py` says EXTREME should "skip entirely" or only trade "continuation" signals. Requiring 2.0 R:R in EXTREME is too lenient — EXTREME markets have wild price swings that make R:R unreliable. The spec should either:
- Block entirely in EXTREME (like volatility_gate does), OR
- Set a much higher R:R threshold (3.0+) to compensate for the noise

**W7: S/R clustering uses ATR in inconsistent units.**
`SR_CLUSTER_ATR = 1.0` means "merge levels within 1.0 × ATR". But ATR can be in dollars or percent depending on context. The merge function `_cluster_levels()` takes `atr_pct` as parameter, so this seems correct (% units). But the SL placement logic says "extend SL 0.2% beyond structural level" which is a fixed %, not ATR-scaled. This mixing of ATR-relative and absolute % thresholds needs clarification.

**W8: Missing `signal_type` pass-through to regime alignment scoring.**
The scoring formula includes "Vol alignment (20 points)" that checks regime+signal compatibility. But `rr_gate()` in `entry_gates.py` doesn't receive `signal_type` — it gets `(token, direction, price, candles_5m)`. The spec's `evaluate_rr()` adds `signal_type` parameter, but the integration code on line 403 doesn't pass it: `result = evaluate_rr(token, direction, price, candles_5m=candles_5m)`. The `signal_type` is lost, so vol alignment scoring will always fail/return 0.

**Fix:** Either:
- (a) Add `signal_type` to `rr_gate()` signature (minor API change), OR
- (b) Make vol alignment scoring not depend on signal_type (use only regime + direction)

### Minor (polish issues)

**W9: Cache TTL of 5 min for S/R map is too long for order book data.**
Order book walls can change in seconds. 5-minute-old order book S/R data is stale. The S/R map should separate candle S/R (5 min TTL is fine) from order book S/R (30-60 sec TTL or re-read from file each call). Alternatively, just accept that the liquidation_clusters.json file is updated every 5 minutes and this is a known limitation.

**W10: `SR_MIN_TOUCHES = 3` is much lower than `RS_MIN_TOUCHES = 30`.**
The spec uses 3 minimum touches for a valid S/R level. But the actual RS signal uses 30. This means the engine will consider many more levels as "valid" compared to what the RS signal actually trades on. This dilutes the S/R map with weak levels. I'd recommend `SR_MIN_TOUCHES = 10` as a middle ground, or at least document why 3 is chosen.

**W11: Scoring formula `rr_pts = min(40, rr_ratio * 13)` has odd scaling.**
R:R of 1.0 = 13 pts, 2.0 = 26 pts, 3.0 = 39 pts, 3.08 = 40 pts (capped). The 13x multiplier means a tiny improvement from 3.0 to 3.1 earns 1 point, but going from 1.0 to 2.0 earns 13 points. This is fine in principle (diminishing returns) but the slope is too steep in the 1-2 range. Consider `min(40, rr_ratio * 12 + 4)` to give a floor of 4 pts even for R:R < 1.

**W12: The spec mentions `_regime_alignment_pts(regime, signal_type)` but never defines its logic.**
The only description is: "FLAT regime + mean-reversion signal = 20pts, NORMAL + trend signal = 20pts, Mismatch = 0pts." But:
- Which signals are "mean-reversion"? (bb_bounce, range_finder, hzscore?)
- Which are "trend"? (pump-catcher, r2-trend, continuation?)
- What about regime-agnostic signals like liq-hunt, confluence?
- What about the multi-signal compound types like `bb_bounce+,range_finder+`?

This function needs a complete implementation spec, not just two examples.

---

## Specific Findings

### Finding 1: ATR Unit Mismatch Will Cause Wrong Regime Classification
**Severity: CRITICAL**

`atr_cache.json` stores raw ATR dollar values (e.g., `{"ETH": {"atr": 45.23, "ts": ...}}`). The spec's `compute_vol_width()` tries to read `atr_pct` from this cache. Since `atr_pct` doesn't exist in the file, it falls back to `atr` (raw 45.23). Then `classify_volatility(45.23)` returns `EXTREME` (anything > 1.5%). Every single token would be classified as EXTREME, making the engine useless.

**Evidence:** `entry_gates.py` line 62: `return entry.get('atr_pct', entry.get('atr'))` — same bug exists today, but the current `rr_gate()` doesn't classify regime so it's dormant. The new engine would activate this bug.

### Finding 2: Liquidation Cluster Direction Semantics Are Confusing
**Severity: MEDIUM**

The spec says: "For LONG: clusters above price = potential TP magnets, clusters below = SL risk." But `liquidation_hunt.py` (the existing signal) treats clusters CONTRARIANLY — "If longs are about to get liquidated (price dropping toward their liq levels), we go LONG." This is the opposite interpretation.

The engine needs to clearly decide: are clusters targets to trade TOWARD (magnet theory) or levels to trade AGAINST (contrarian cascade theory)? Both theories have merit, but they produce opposite R:R adjustments. The spec should pick one and document the thesis.

My recommendation: **use clusters as targets (TP magnets) for R:R calculation, but flag when a cluster is close to SL as cascade risk.** The contrarian thesis is for signal generation (liq-hunt), not for R:R assessment.

### Finding 3: No Handling of Missing/Partial Data
**Severity: MEDIUM**

The spec says "fail-open" but doesn't specify per-component fallback:
- What if liquidation_clusters.json is stale (15+ min old)?
- What if candles_5m has < 30 candles (swing detection needs 2× window)?
- What if atr_cache.json is missing the token?
- What if order book data is unavailable for the token?

Each component should have explicit fallback behavior: "If data unavailable, exclude this source from the S/R map (don't block the signal)." The merge function should work with 1/3 or 2/3 sources.

### Finding 4: TP Cap of 3.0% May Be Too Tight
**Severity: LOW-MEDIUM**

The spec caps TP at `RR_ENGINE_TP_MAX_PCT = 0.03` (3.0%). But `ATR_TP_MAX = 0.02` (2.0%) is the existing cap. If structural S/R is at 3.5% away, the engine would ignore it and fall back to ATR-based TP. For BTC with 0.8% ATR, 2× ATR = 1.6% TP, which is fine. But for low-ATR tokens (FLAT regime), structural levels at 2-3% are realistic and shouldn't be capped. The 3.0% cap is reasonable but should be regime-adjusted: 2.5% for NORMAL, 3.5% for FLAT.

### Finding 5: Existing S/R Implementations Would Be Duplicated
**Severity: LOW**

The spec proposes a new `_sr_map.py` for S/R detection. But `rs_signals.py` already has:
- Swing high/low detection (rolling window)
- ATR-normalized clustering
- Touch counting with recency weighting
- Bounce confirmation

The engine should import from `rs_signals.py` or refactor the common S/R logic into a shared utility rather than reimplementing it. This avoids drift between the signal's S/R levels and the engine's S/R levels.

### Finding 6: `entry_gates.py` Signature Change Breaks API
**Severity: LOW**

The spec adds `signal_type` to `evaluate_rr()` but the `rr_gate()` wrapper doesn't pass it through. To pass it through, `rr_gate()` needs a new parameter. All callers of `rr_gate()` (in every signal file) would need to be updated — or `signal_type` needs to be inferred from context. Since the goal is a drop-in replacement, `signal_type` should either:
- Be inferred (default to None, skip vol alignment scoring), or
- Be added as an optional parameter with default None

### Finding 7: Regime-Adjusted R:R Thresholds May Cause Signal Starvation
**Severity: LOW-MEDIUM**

Current system produces ~20-30 signals/day. FLAT regime needs R:R ≥ 3.0 — this is very high. If 50% of tokens are in FLAT regime (common per the spec's own data: "102/104 tokens flat"), then half the tokens would need 3.0 R:R to pass. Combined with the existing volume, session, hebbian, and regime gates, this could starve the system. The 3.0 threshold should be validated against historical R:R distributions before enforcement.

---

## Recommended Changes

### Priority 1 (Must fix before implementation)

1. **Fix ATR unit handling.** Convert dollar ATR to ATR% in `compute_vol_width()` using `atr_dollar / price * 100`. Or better: use `volatility_gate.get_atr_pct(token)` which already does this correctly.

2. **Fix constant name.** Rename `RR_ENGINE_SL_STRUCTURAL缓冲` → `RR_ENGINE_SL_STRUCTURAL_BUFFER`.

3. **Fix `signal_type` pass-through.** Either add it to `rr_gate()` signature (optional param, default None) or remove vol-alignment-by-signal-type from scoring (simpler, recommended for v1).

4. **Match BB_STDDEV to existing implementations.** Use 1.8, not 2.0.

### Priority 2 (Should fix before implementation)

5. **Define `_regime_alignment_pts()` fully.** Map signal types to categories (mean-reversion / trend / momentum / structural) with an explicit lookup table.

6. **Add per-component data availability handling.** If liquidation data is stale or missing, exclude it from the S/R map rather than using empty/bad data.

7. **Clarify cluster direction semantics.** Document whether clusters are used as TP magnets (recommended) or contrarian signals, and handle both cases explicitly in the scoring.

8. **Lower EXTREME regime threshold or block entirely.** R:R ≥ 2.0 in EXTREME is too lenient. Either block (consistent with volatility_gate.py) or require 3.0+.

### Priority 3 (Nice to have)

9. **Share S/R detection code with `rs_signals.py`.** Extract common swing detection and clustering into a utility to avoid duplication.

10. **Reduce `SR_MIN_TOUCHES` from 30 (RS) to a middle ground like 8-10.** Three touches is too few for structural significance.

11. **Regime-adjust the TP max cap.** 2.5% for NORMAL, 3.5% for FLAT.

12. **Document R:R distribution before setting FLAT threshold.** Run 7-day backtest to see what % of signals actually achieve 3.0+ R:R. If <10%, the threshold is effectively "no FLAT trades."

---

## What I Would Do Differently

**1. Don't build a new S/R module — extend `rs_signals.py`.**
The S/R detection in `rs_signals.py` is already battle-tested with the right parameters (window=20, ATR-normalized clustering, touch counting). Building a new `_sr_map.py` duplicates this logic and creates drift risk. Instead, add a `get_sr_map(token, price, ...)` function to `rs_signals.py` that returns the merged multi-source S/R map. The RR engine calls this function.

**2. Make the scoring formula simpler for v1.**
The 4-component scoring (R:R quality 40 + vol alignment 20 + liquidity flow 20 + S/R clarity 20) is elegant but requires all four components to work perfectly. For v1, I'd simplify to:
- R:R quality (50 points) — the core value proposition
- Liquidity bonus (20 points) — the novel addition
- S/R clarity (20 points) — are there clear targets?
- Vol penalty (10 points) — subtract for mismatched regime
This is 3 working components instead of 4 potentially broken ones. Add vol alignment scoring in v2 after backtesting shows the engine works.

**3. Use `volatility_gate.get_atr_pct()` as the single source for ATR%.**
Don't read atr_cache.json directly. The `volatility_gate.get_atr_pct()` function already handles the dollar-to-percent conversion correctly, computes from 1h candles, and has fallback logic. Reuse it.

**4. Start with stricter thresholds, relax later.**
For initial shadow mode, I'd set `RR_ENGINE_MIN_RATIO_NORMAL = 2.5` (not 2.0). The current system already has a 2.0 floor. If we're replacing it with a "smarter" engine, it should be MORE selective, not equally selective. Tighten first, loosen after data shows which signals are actually good.

**5. Add a `compare_with_legacy()` function.**
The shadow mode should log not just "what would this engine have blocked" but also "how does this differ from what the legacy rr_gate blocked." This delta analysis is critical for understanding whether the engine is actually adding value or just being different.

**6. Make cascade_risk bidirectional.**
The spec treats cascade_risk as purely negative (SL risk). But cascades also create opportunity — a cascade below price provides exit liquidity for LONG TP. The engine should score cascades in BOTH directions: cascade_risk (negative for SL side) AND cascade_opportunity (positive for TP side). This is the key insight from the liquidation_hunt signal that the spec partially misses.
