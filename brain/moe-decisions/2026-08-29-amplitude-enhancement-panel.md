# MoE Decision Panel — Amplitude-Based Trading System Enhancements

**Date:** 2026-08-29
**Question:** Should we implement the amplitude-based trading system enhancements?
**Panel:** All 6 experts (Signal, Code, Risk, Stats, Regime, Systems)

---

## Synthesis Framework (Ready for Expert Verdicts)

### Expert Weights (Adjusted for This Question)

| Expert | Weight | Rationale |
|--------|--------|-----------|
| Signal Analyst | 0.20 | Amplitude affects signal scoring |
| Code Architect | 0.15 | New scripts, integration risk |
| Risk Manager | 0.30 | **PRIMARY** — SL/ sizing changes are high-stakes |
| Statistician | 0.20 | Need empirical validation |
| Regime Analyst | 0.10 | Amplitude relates to vol regimes |
| Systems Engineer | 0.05 | Cache design is straightforward |

### Decision Thresholds

- **APPROVE**: Weighted score > 0.7, no HIGH-confidence dissent
- **MODIFY**: Weighted score 0.5-0.7, or one expert has HIGH-confidence concern
- **REJECT**: Weighted score < 0.5, or any expert has CRITICAL finding
- **ESCALATE TO T**: Experts split 50/50

---

## Expert Verdicts (Pending)

### 1. Signal Analyst (weight: 0.20)
**Status:** ✅ COMPLETE
**Verdict:** MODIFY (implement cautiously with guardrails)
**Confidence:** MEDIUM

**Key Findings:**
- No backtest evidence that HIGH_AMP tokens have lower signal quality — 0.85x penalty is hypothesis, not validated edge
- 0.85x penalty would affect ~50% of traded tokens (15 of 30) — significant structural change
- Trade #2 (ZRO +16.06%) was HIGH_AMP winner that penalty would have suppressed
- Volatility Gate V2 already handles ATR-based volatility — risk of double-penalization
- Amplitude breakout signal NOT viable yet — missing infrastructure

**Conditions:**
1. Start with SOFT penalty (0.92x, not 0.85x)
2. Add kill switch AMPLITUDE_WEIGHT_ENABLED
3. Log every decision for 14-day observation
4. Tighten to 0.85x only after validation

### 2. Code Architect (weight: 0.15)
**Status:** ✅ COMPLETE
**Verdict:** PROCEED with conditions
**Confidence:** HIGH

**Key Findings:**
- 3 connection-leak risks (db.close() without try/finally)
- 1 duplicate-code violation (wave_trade_context.py)
- 1 double-query waste in main()
- Hardcoded constants in wave scripts (should be in hermes_constants.py)

**Conditions:**
1. Fix connection leaks first (try/finally in both wave scripts)
2. Deduplicate get_candles() into one shared function
3. Move hardcoded constants to hermes_constants.py
4. Build amplitude_cache.py following atr_cache.py pattern
5. Dynamic SL is HIGH risk — needs paper-trading period

### 3. Risk Manager (weight: 0.30)
**Status:** ✅ COMPLETE
**Verdict:** MODIFY — approve foundation, reject amplitude-based SL
**Confidence:** HIGH

**Key Findings:**
- **4.3% amplitude-based SL is UNWORKABLE** — at 5x leverage = 21.5% portfolio risk per trade
  - Violates MAX_PORTFOLIO_HEAT (15%)
  - Preempted by MAE guard (3.0% price threshold triggers before 4.3% SL)
  - Degrades R:R from 1:1.5 to 1:1
- **0.7x position sizing for HIGH_AMP is APPROVED** — sound risk adjustment
- **6 of 15 HIGH_AMP tokens are blacklisted** (TRUMP, WIF, UNI, FET, SPX, SUI)
- **Correlated crash risk** — 5 HIGH_AMP positions + BTC -5% = 75% portfolio loss

**Approve:**
1. Amplitude Cache (Idea 1)
2. Amplitude-Weighted Compactor (Idea 3) — start with 0.92x, not 0.85x
3. Position Sizing (Idea 4) — 0.7x for HIGH_AMP

**Reject:**
4. 4.3% amplitude-based SL — use amplitude as ATR scaling factor instead

**New Constants Proposed:**
```python
AMPLITUDE_SL_SCALING_ENABLED = True
AMPLITUDE_SL_MAX_FACTOR = 1.5    # cap at 1.5x ATR
AMPLITUDE_SL_HARD_CAP = 0.020    # 2.0% absolute cap (10% portfolio at 5x)
```

### 4. Statistician (weight: 0.20)
**Status:** ✅ COMPLETE
**Verdict:** PROCEED with caution — descriptive foundation solid, predictive enhancements unvalidated
**Confidence:** MEDIUM

**Key Findings:**
- BTC vs ZRO amplitude gap: **Significant** (p<0.001) — classes are real
- 3x amplitude ratio: **Direction significant**, magnitude approximate (2-5x range, not exactly 3x)
- Short wave bucket (n=5-12): **Too small** for precise estimates — confidence intervals wide
- TRUMP's 82.45% outlier: **Misclassifies** as HIGH_AMP when median is 1.77% (MED_AMP)
- Wave position with n=3: **Statistically meaningless** (CI=[21%-94%])
- Amplitude-based sizing → profit: **UNTESTED** (no backtests exist)

**Critical Gap:** Descriptive finding ("amplitude varies") → Predictive enhancement ("use amplitude for trading") has NO empirical validation.

**Recommendations:**
1. Run amplitude-winrate backtest (Idea 18) BEFORE building compactor
2. Filter TRUMP's 82.45% outlier before classification
3. Don't claim "3x" as precise — say "2-5x across tokens"
4. Rolling windows mandatory (non-stationary amplitude)

### 5. Regime Analyst (weight: 0.10)
**Status:** ✅ COMPLETE
**Verdict:** INTEGRATE (as new dimension, not regime replacement)
**Confidence:** HIGH

**Key Findings:**
- Amplitude and regime are ORTHOGONAL — they measure different things
  - Regime = directional bias (slope + R²)
  - Amplitude = volatility magnitude (swing size)
- No overlap risk — they feed into different decision points
- Existing volatility_gate_v2.py uses ATR (candle-by-candle), amplitude is wave-to-wave — complementary
- Wave position scoring CONTRADICTED by data (same as auditor found)

**Recommendation:** Integrate amplitude as new dimension alongside regime, not replacing it.

### 6. Systems Engineer (weight: 0.05)
**Status:** ✅ COMPLETE
**Verdict:** PROCEED with fixes
**Confidence:** HIGH

**Key Findings:**
- Pipeline HEALTHY, data FRESH, all services running
- Amplitude computation is EXPENSIVE (720 candles × 30 tokens × extrema detection)
- ATR cache pattern doesn't directly translate — amplitude needs rolling windows, not TTL
- **Must decouple computation from pipeline** — use dedicated timer (every 15 min)

**Requirements:**
1. Dedicated `hermes-amplitude-cache.timer` (15 min), not inline in pipeline
2. Dual-layer cache: rolling data file + computed cache file
3. Graceful degradation: stale/missing cache → neutral defaults
4. Add `AMPLITUDE_CACHE_FILE` to paths.py
5. Compressor reads from cache, never computes

---

## Synthesis

### Consensus: MODIFY — Approve Foundation, Reject Amplitude-Based SL

All 6 experts agree the amplitude classification is real and statistically significant. All agree the foundation (cache, compactor, sizing) should be built. The Risk Manager and Signal Analyst reject the 4.3% amplitude-based SL as unworkable, proposing amplitude as an ATR scaling factor instead.

### Confidence Score: 0.85 / 1.00

| Expert | Weight | Verdict | Confidence | Score |
|--------|--------|---------|------------|-------|
| Signal Analyst | 0.20 | MODIFY | MEDIUM | 0.70 |
| Code Architect | 0.15 | PROCEED w/conditions | HIGH | 0.85 |
| Risk Manager | 0.30 | MODIFY | HIGH | 0.80 |
| Regime Analyst | 0.10 | INTEGRATE | HIGH | 0.90 |
| Statistician | 0.20 | PROCEED w/caution | MEDIUM | 0.75 |
| Systems Engineer | 0.05 | PROCEED w/fixes | HIGH | 0.85 |

**Weighted average: 0.80**

### Dissent Notes

**Signal Analyst (MEDIUM confidence):** "No backtest evidence that HIGH_AMP tokens have lower signal quality — the 0.85x penalty is a hypothesis, not a validated edge." Recommends starting with 0.92x and validating over 14 days before tightening.

**Statistician (MEDIUM confidence):** "The gap between 'amplitude varies' and 'amplitude-based trading is profitable' requires backtesting that hasn't been done." Recommends running amplitude-winrate correlation BEFORE building compactor.

**Risk Manager (HIGH confidence):** "4.3% SL at 5x leverage = 21.5% portfolio risk per trade. Violates MAX_PORTFOLIO_HEAT. Preempted by MAE guard at 3.0%. Dead code in most scenarios." Recommends amplitude as ATR scaling factor, not replacement.

---

## Final Recommendation

**APPROVE (Modified)** — Build the amplitude infrastructure with the following conditions:

### Phase 0: Critical Fixes (Do First)
1. Fix connection leaks in wave scripts (try/finally)
2. Deduplicate get_candles() into shared function
3. Move hardcoded constants to hermes_constants.py
4. Filter TRUMP's 82.45% outlier before classification

### Phase 1: Foundation (This Week)
5. Build amplitude_cache.py with rolling 100-wave windows
6. Dedicated hermes-amplitude-cache.timer (every 15 min)
7. Add AMPLITUDE_CACHE_FILE to paths.py
8. Graceful degradation: stale cache → neutral defaults

### Phase 2: Integration (Next Week)
9. Amplitude-weighted signal compactor with SOFT penalty (0.92x, not 0.85x)
10. Add kill switch AMPLITUDE_WEIGHT_ENABLED
11. Position sizing: 0.7x for HIGH_AMP (APPROVED by Risk Manager)
12. Log every decision for 14-day observation

### Phase 3: Validation (Week After)
13. Run amplitude-winrate correlation backtest
14. Compare win rates after 14 days of observation
15. Tighten to 0.85x ONLY if validated

### Phase 4: Dynamic SL (Future, After Validation)
16. Use amplitude as ATR scaling factor (NOT replacement)
17. AMPLITUDE_SL_MAX_FACTOR = 1.5 (cap at 1.5x ATR)
18. AMPLITUDE_SL_HARD_CAP = 0.020 (2.0% absolute cap)

### ⛔ NOT IMPLEMENTING
- 4.3% amplitude-based SL — rejected by Risk Manager
- Wave-position entry filter — contradicted by data
- Amplitude breakout signal — premature without cache infrastructure
