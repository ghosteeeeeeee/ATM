## CEO Report — 2026-08-26 ~22:00 UTC — Signal Regime Memory Spec Review

### VERDICT: APPROVE with condition — backbone signal FIRST

**The spec is good. The timing is wrong.** Regime memory is a Phase 2 improvement, not a Phase 1 crisis fix.

### Verified Numbers (DB, not reports)
| Metric | Value |
|--------|-------|
| 24h | 52T, -$0.32, 48.1% WR |
| 7d | 343T, -$5.06, 48.4% WR |
| Open trades | 4 |
| ATR_SL/48h | 35 hits, -$4.75 (65% of losses) |
| Backbone signals | **ZERO** |
| Active LONG signal | pump-catcher+ only (7T/7d 28.6% WR -$0.41) |

### Spec Assessment

**What's right:**
- Phase 0 (persist regime at entry) is the critical path — correct priority
- Cold-start blending with REGIME_SIGNALS priors is sound
- SQLite over JSON is the right call (concurrency, atomicity)
- `dormant` state is elegant — nearly unreachable `deprecated` is the right design
- Shadow mode with 2-week validation before activation
- Kill system coordination protocol addresses real complexity

**What's wrong:**
1. **Wrong priority.** System has ZERO backbone signals. Regime memory doesn't help if we have no signals to remember. Build backbone signal FIRST, regime memory SECOND.
2. **The bb_bounce example is misleading.** Spec says bb_bounce was "killed for regime mismatch." Reality: 8T/24h 12.5% WR -$0.55 on LOW-LIQUIDITY tokens (WLFI, BLUR, AR, CRV). Today's loss was token quality, not regime. bb_bounce 7d is still 61.5% WR +$0.37 — it was killed on a bad day, not a regime problem.
3. **Dormant resurrection assumes signals exist to resurrect.** Most killed signals (wave_catcher, accel-300, movers, slow-grind) were killed for structural reasons (inverted R:R, 0% WR), not regime mismatch. Only bb_bounce + hl_copy_trader were arguably killed prematurely.
4. **4+ day build time** during a signal starvation crisis is a misallocation.

### Decision

**APPROVE the spec — build it AFTER backbone signal.**

Sequence:
1. **NOW:** Build new backbone signal (delegated to signal_analyst, already in progress)
2. **Day 2-3:** Implement Phase 0 (persist regime at entry) — 1 day, low risk
3. **Day 3-5:** Phase 1-2 (tracker + rotator integration) — 2 days
4. **Day 5-7:** Phase 3-4 (kill system + lifecycle) — 2 days
5. **Day 7+:** Shadow mode for 2 weeks

### Risk Assessment

**Building regime memory NOW:** HIGH RISK. 4+ days of engineering time while system has zero signals. Signal starvation = zero trades = zero PnL. Every day without a backbone signal is a day of lost opportunity.

**Building regime memory AFTER backbone:** LOW RISK. System regains signal flow, we have real data to work with, regime memory becomes an optimization rather than a rescue.

**Not building regime memory at all:** MEDIUM RISK. We'll keep killing signals on bad days and missing them on good days. The problem is real but not urgent relative to signal starvation.

### One Strategic Concern the Spec Misses

The spec focuses on **signal-level** regime memory but ignores **token-level** regime memory. Some tokens behave differently in the same regime. A token in Wyckoff accumulation might fire LONG signals regardless of overall market regime. The spec's "token-specific regime affinity" is listed as v2/out-of-scope, but it's actually the higher-ROI feature — we already have coin_tracker data for this.

**Recommendation:** After v1 ships, immediately scope a v2 that adds token×regime tracking using existing coin_tracker.db data.

### What Changed

Nothing yet. Spec approved, pending backbone signal completion.

### Next Actions

1. **Monitor backbone signal development** — signal_analyst delegation active
2. **If backbone signal ships:** begin Phase 0 (regime persistence)
3. **If backbone signal stalls:** redirect engineering to signal development, defer regime memory
4. **Monitor ATR_SL** — 35 hits/48h -$4.75 remains dominant loss

---

## CEO Report — 2026-08-27 ~01:10 UTC

### Diagnosis
NEUTRAL relax fix from yesterday (Aug 26) passed signals through the confluence gate but the final guard (Step 11) blocked them — missing the same NEUTRAL relax exception. Pipeline confirmed: 5 signals approved at gate, only 1 reached hotset. System has ZERO backbone signals. ct-hot+ legacy 80T/7d -$5.07 aging out today.

### Verified Numbers
| Metric | Value | Trend |
|--------|-------|-------|
| 24h | 61T, -$0.15, 44.3% WR | Flat (was -$0.45 yesterday) |
| 7d | 351T, -$4.55, 47.9% WR | Improving (was -$5.06) |
| Today Aug 27 | 5T, +$0.33, 40% WR | Early, positive |
| Open trades | 2 SHORT | Near breakeven |
| ATR_SL/48h | 37 hits, -$4.57 | Dominant loss (65%) |
| ct-hot+ legacy | 80T/7d, -$5.07 | Aging out today |
| Coin tracker | 69/109 accumulation | Bullish |

### Fix Applied
**signal_compactor.py final guard** — Added NEUTRAL relax check (lines 1971-1977). When CONFLUENCE_NEUTRAL_RELAX=True and 4h regime is NEUTRAL, single-type signals now pass the final guard instead of being blocked. This was the second half of yesterday's NEUTRAL relax fix (first half: confluence gate check at line 1404).

### Root Cause
Yesterday's fix addressed the confluence gate (Step 2) but not the final guard (Step 11). The final guard was designed as a safety net against single-source signals slipping through, but it didn't account for NEUTRAL relax — a legitimate exception to the 2-type confluence requirement.

### Active Signal Performance (7d)
| Signal | Trades | PnL | WR | Status |
|--------|--------|-----|-----|--------|
| cascade-reverse-v2 SHORT | 5 | +$0.39 | 40% | Active, emerging winner |
| macd-div- SHORT | 17 | +$0.06 | 70.6% | Active, best WR |
| r2-trend-long3 LONG | 8 | +$0.24 | 50% | Active |
| pump-catcher+ LONG | 15 | -$0.25 | 33.3% | Active, ATR_SL 11 hits |
| hzscore- SHORT | 10 | +$0.09 | 50% | Active, marginal |

### Next Actions
1. **Monitor hotset population** after NEUTRAL relax final guard fix — next pipeline cycle
2. **ct-hot+ age-out** should complete today — system projected net positive after
3. **Build backbone signal** — still delegated to signal_analyst (LONG, volume+momentum)
4. **Monitor disk** — 83%, approaching 85% cleanup threshold
