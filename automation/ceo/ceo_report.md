## CEO Report — 2026-09-11 (Plan Review: Chop Regime Signal Gating)

### Diagnosis

4 consecutive losses (SAND SHORT -7%, BCH SHORT -5.5%, APT LONG -6%, ENA SHORT -5.7%) — all entered when BTC 30m momentum was flat (-0.5% to +0.5%). Momentum signals firing into chop via STANDALONE_BYPASS, chop detector voting system lets them through (BTC votes CHOP but other votes override to TREND).

Verified: 24h 43T 65.1% WR +$2.70. 7d 318T 57.9% WR +$1.47. System is profitable overall — these 4 losses are -$0.60 total, not structural.

### Plan Assessment

**CONDITIONAL GO — Layers A + revised B. SKIP C. DEFER D.**

**Layer A (BTC hard gate):** Threshold 0.15% is correct (matches validated CHOP_DETECTOR_BTC_MOM_THRESHOLD). But plan overstates impact: only catches 2/4 named losses (BCH SHORT, APT LONG). SAND SHORT and ENA SHORT are pullback-entry — classified MEAN_REVERSION by chop_detector, not touched by momentum gate.

**Layer B (regime-aware neutral block):** Critical gap — plan modifies signal classification but misses that STANDALONE_BYPASS signals BYPASS the neutral block entirely (signal_compactor.py:1807/1815). pump-chain, pullback-entry are in STANDALONE_BYPASS. Classification change is cosmetic. **Fix: gate the STANDALONE_BYPASS condition itself with BTC momentum check, not just signal family.**

**Layer C (continuum oscillator):** Skip. 20 lines + DB reads for marginal precision on top of 4 existing voters. Revisit after A+B validated.

**Layer D (RS enable):** Defer. RS source weight 0.4 is intentional suppression (underperformed). Don't unblock until RS signal re-engineered.

### Risk Analysis

- **High:** Layer B as written doesn't fix the STANDALONE_BYPASS gap — momentum signals still bypass neutral block
- **Medium:** 0.15% BTC gate may block valid pullback entries during brief dips in strong trends (mitigated: strong trends have BTC >0.3%)
- **Medium:** Mean-reversion signals may lose in true NEUTRAL (low vol, no oscillation) — test LOG-ONLY first

### Fix Applied

**Recommended implementation:**
1. Layer A: BTC hard gate in `_score_signal()` before chop detector (~10 lines)
2. Layer B (revised): Add `abs(btc_30m) >= 0.15%` check to STANDALONE_BYPASS bypass condition in neutral block (~5 lines)
3. LOG_ONLY flag for 48h testing before live enable
4. Remove Layer C and D from this change

**Total: ~15 lines + 2 constants + LOG_ONLY flag.**

### Verification

- After 48h LOG-ONLY: verify no false positives (valid momentum entries blocked)
- After live enable: monitor signal volume for >20% drop
- Track mean-reversion signal WR in NEUTRAL (target: >50% at 10+ trades)
- Re-run trade analysis after 7 days to measure impact
