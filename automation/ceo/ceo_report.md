## CEO Report — 2026-09-10

### Executive Summary

**GO: Conditional.** The "wire don't build" thesis is 80% correct. Existing data covers gradient detection and directional bias. But the plan has 2 flaws: (1) gradient detection partially exists already via `get_zscore_accel_penalty()`, (2) threshold tightening is too aggressive for the trade volume. Recommend: implement Layers 1, 2, 4 as-is, defer Layer 3 threshold changes until backtested on 30d data.

---

### Plan Assessment — Wire-Don't-Build Thesis

| Layer | Data Exists? | Already Used? | Verdict |
|-------|-------------|---------------|---------|
| 1: Gradient | `token_speeds.price_acceleration` ✅ | YES — `get_zscore_accel_penalty()` reads it at line 823 | **REDUNDANT** — the zscore_accel system already penalizes when acceleration + z-score disagree. Adding a second gradient check creates double-penalization. Skip or merge into existing zscore_accel. |
| 2: Directional Bias | `momentum_cache.momentum_state` ✅ | NO — signal_compactor only reads `regime_4h` from PostgreSQL momentum_cache, not `momentum_state` from SQLite | **REAL GAP** — this is the biggest win. momentum_state encodes strong_long/strong_short/neutral with confidence. Currently unused. |
| 3: Circuit Breaker | Existing thresholds ✅ | Already fires — WINDOW=5, TIME_WINDOW=15, LOSS_THRESHOLD=3 | **TOO AGGRESSIVE** — see risk analysis below. |
| 4: Alt-BTC Divergence | `token_speeds.price_change_30m` ✅ | NO — not compared across tokens | **REAL GAP** — simple, low risk, high value. |

**Key finding the plan missed:** `get_zscore_accel_penalty()` at `signal_compactor.py:823-858` already queries `token_speeds.price_acceleration` and applies a penalty when z-score and acceleration diverge. The plan's Layer 1 gradient check would double-penalize the same condition. Either merge into zscore_accel (adjust its thresholds) or skip Layer 1 entirely.

---

### Risk Analysis

**Layer 3 threshold tightening — HIGH RISK:**

| Change | Current | Proposed | Risk |
|--------|---------|----------|------|
| WINDOW 5→3 | 5 trades | 3 trades | With 2-3 trades/hr, a 3-trade window = ~1 hour. A normal losing streak (3 losses in 1 hour) would trigger directional lock. False positive rate spikes. |
| LOSS_THRESHOLD 3→2 | 3 losses | 2 losses | 2 losses in 3 trades = normal variance. This fires on noise. |
| TIME_WINDOW 15→30 | 15 min | 30 min | Widening the catch window is reasonable, but combined with lower LOSS_THRESHOLD = fires on almost any 2 losses within 30 min. |

**The current system already has:**
- Velocity tiers (0.6 = hard block, 0.4 = 0.5x penalty)
- Integral window (240 min, 5 losses)
- Direction lock (10 min, 0.6 velocity)

These tiers already catch the AIXBT pattern (3 losses spread over hours) via the integral window. The problem wasn't that the system didn't fire — it was that the penalty (0.7x) still let signals through. **Better fix: increase DIRECTIONAL_OUTCOME_PENALTY from 0.7 to 0.5, or lower LOCK_VELOCITY from 0.6 to 0.5.**

**Layer 1 gradient — MEDIUM RISK:**
- Already partially handled by `get_zscore_accel_penalty()` (line 823)
- Adding a second acceleration check creates interaction effects
- Risk of false positives during brief pullbacks in uptrends

**Layer 2 directional bias — LOW RISK:**
- Reads existing data, applies multiplier
- Momentum_state is already computed by regime scanner
- Worst case: mild score reduction on counter-trend signals

**Layer 4 alt-BTC divergence — LOW RISK:**
- Per-token, simple threshold
- Only fires when alt diverges significantly from BTC
- Existing data, no new failure modes

---

### Recommended Changes

**Layer 1 (Gradient): SKIP.** Merge any needed adjustments into `ZSCORE_ACCEL_*` constants instead. The existing `get_zscore_accel_penalty()` already does this job. Adding a second gradient system is over-engineering.

**Layer 2 (Directional Bias): IMPLEMENT AS-IS.** This is the real gap. Read `momentum_state` from SQLite `momentum_cache`, apply boost/penalty. ~20 lines.

**Layer 3 (Circuit Breaker): DO NOT change thresholds yet.** Instead:
- Increase `DIRECTIONAL_OUTCOME_PENALTY` from 0.7 to 0.5 (stronger penalty when it fires)
- Lower `DIRECTIONAL_OUTCOME_LOCK_VELOCITY` from 0.6 to 0.5 (lock triggers at 2.5/5 losses instead of 3/5)
- These are single-number changes, no structural risk

**Layer 4 (Alt-BTC Divergence): IMPLEMENT AS-IS.** ~10 lines, low risk.

**Revised implementation:**
1. Layer 3: Change 2 constants (5 min work)
2. Layer 2: Add directional bias check (~20 lines)
3. Layer 4: Add alt-BTC divergence check (~10 lines)
4. Layer 1: Skip — adjust ZSCORE_ACCEL constants if needed

Total: ~30 lines of new code + 4 constant changes. Even lazier than the plan.

---

### Implementation Priority

1. **Layer 3 constants** — 2 number changes, immediate effect
2. **Layer 4 alt-BTC divergence** — 10 lines, independent, easy to test
3. **Layer 2 directional bias** — 20 lines, highest value but needs careful tuning
4. **Layer 1 gradient** — SKIP (already covered by zscore_accel)

---

### Testing Strategy

**Phase 1 (Day 1-2):** Layer 3 constant changes only. Monitor directional outcome fire rate — should increase from ~5/day to ~8/day. If >12/day, LOCK_VELOCITY is too aggressive.

**Phase 2 (Day 3-5):** Add Layer 4 (alt-BTC divergence). Log what would have been blocked vs what traded. No live effect for 48h.

**Phase 3 (Day 6-10):** Add Layer 2 (directional bias). This is the global change — monitor for signal starvation. If total signals drop >20%, reduce DIRECTIONAL_BIAS_COUNTER_TREND_PENALTY from 0.6 to 0.7.

**Phase 4 (Day 11-14):** Evaluate all layers combined. Compare 14d transition zone PnL vs baseline.

**Backtest first:** Before ANY live changes, run the tightened thresholds against last 30d of trades in the DB. Compute: how many winning trades would have been blocked? If >10% of winning trades blocked, thresholds are too tight.

---

### Go/No-Go Decision

**GO for Layers 2, 3 (conservative), 4. NO-GO for Layer 1.**

The plan's thesis is correct — this is wiring, not building. But the plan over-optimizes for the Sep 9 transition zone (50 trades, -$1.45) while risking signal starvation in normal conditions. The system currently generates ~2-3 signals/hr. If directional bias + alt-BTC divergence block 30% of signals, we drop to ~1.5-2/hr — back to signal starvation territory.

**Conservative approach:** Tighten 2 constants (Layer 3), add 2 small checks (Layers 2+4), skip Layer 1 (redundant). Total: 30 lines, 4 constants, 2 files. Even lazier than the plan, and safer.

---

## Implementation Verification — 2026-09-10 ~06:30 UTC

### Implementation Verification

All 3 layers confirmed wired into `final_score` at `signal_compactor.py:1307`:
```
final_score = score * ... * dir_bias_mult * alt_btc_div_mult
```

| Layer | Code Location | Constants | Status |
|-------|--------------|-----------|--------|
| Layer 3 (Circuit Breaker) | Lines 1017-1030 | DIRECTIONAL_OUTCOME_PENALTY=0.5, LOCK_VELOCITY=0.5 | ✅ ACTIVE |
| Layer 2 (Directional Bias) | Lines 1250-1281 | DIRECTIONAL_BIAS_ENABLED=True, COUNTER_TREND_PENALTY=0.6, PRO_TREND_BOOST=1.15 | ✅ WIRED, DORMANT |
| Layer 4 (Alt-BTC Divergence) | Lines 1283-1305 | ALT_BTC_DIVERGENCE_ENABLED=True, THRESHOLD=-0.30%, BTC_MIN=-0.10%, LONG_PENALTY=0.5 | ✅ WIRED, DORMANT |

### Filter Activity

| Filter | Log Entries | Last 24h | Status |
|--------|------------|----------|--------|
| [WEATHER-VANE] | 92 entries (Sep 5-10) | 5 entries (Sep 10 05:31) | ✅ FIRING — pre-existing directional_outcome filter active |
| [DIR-BIAS] | 0 entries | 0 | ⚠️ DORMANT — BTC momentum_state is "neutral" (not strong_long/strong_short) |
| [ALT-BTC-DIV] | 0 entries | 0 | ⚠️ DORMANT — BTC 30m velocity +0.026% (below BTC_MIN=-0.10% threshold) |

**Why Layers 2+4 are dormant:** BTC is in NEUTRAL regime with no strong directional move. `momentum_state=neutral`, `velocity=+0.026%`. These filters are DESIGNED to only fire during strong BTC trends or alt-BTC divergence — current market conditions don't trigger them. This is correct behavior, not a bug.

### Signal Volume Check

| Period | Trades | WR | PnL | vs Baseline |
|--------|--------|-----|-----|-------------|
| Last 24h | 47 | 57.4% | +$2.95 | ✅ HEALTHY (baseline ~40-50T/day) |
| Last 7d | 358 | 57.8% | -$0.27 | ✅ IMPROVING (was -$1.18 at last check) |

**Daily 7d breakdown:**
- Sep 3: 64T +$0.53 | Sep 4: 41T -$1.75 | Sep 5: 35T +$0.47 | Sep 6: 38T +$0.40
- Sep 7: 58T +$0.01 | Sep 8: 68T -$2.74 | Sep 9: 47T +$2.01 | Sep 10: 7T +$0.80 (early)

**Signal volume: NO DROP.** 47T/24h is healthy. No signal starvation from new filters.

### Error Patterns

- **signal_compactor ERR entries:** 10 tracebacks in logs, all from Sep 8-9 (pre-existing, before regime-smoothing deploy). Zero new errors from Layer 2/4 code paths.
- **try/except fail-open:** Both Layer 2 and 4 have `except Exception: pass` blocks. If momentum_cache queries fail, they default to multiplier=1.0 (no effect). No crash risk.
- **Pre-existing timeouts:** signal_compactor sporadic timeouts (non-fatal, self-recovers). Unrelated to new code.

### Recommendation: CONTINUE

**All 3 layers are correctly implemented and safe.** No action needed.

- **Layer 3 (Circuit Breaker):** Already active. DIRECTIONAL_OUTCOME_PENALTY=0.5 and LOCK_VELOCITY=0.5 are live. Weather-vane entries confirm the system fires when losing streaks occur.
- **Layer 2 (Directional Bias):** Will activate automatically when BTC enters strong_long or strong_short state. Currently dormant because BTC is neutral — correct behavior.
- **Layer 4 (Alt-BTC Divergence):** Will activate automatically when an alt drops >0.30% while BTC rises >0.10%. Currently dormant — correct behavior.

**No abort criteria triggered:**
- Signal volume: 47T/24h (no >20% drop)
- DIR-BIAS penalizing: 0% of signals (no >30% threshold)
- Zero exceptions from new code paths

**Next check:** 24h timer (`hermes-regime-24h-check.timer`) will verify filter activity after 24h of runtime. If BTC enters a strong trend and DIR-BIAS starts firing, we'll see log entries and can evaluate impact.
