# RR Engine — 3-Fix Verification Report

**Date:** 2026-10-12
**Verifier:** bug_hunter
**Code verified:** `/root/.hermes/scripts/risk_reward_engine.py` (mtime Oct 12 20:49), `/root/.hermes/scripts/hermes_constants.py` (mtime Oct 12 20:42)
**Method:** Live execution of all 7 tests against current code + live price DB, plus direct code inspection. All numbers below come from actual runs — nothing from memory.

---

## Verdict Summary

| # | Check | Verdict |
|---|-------|---------|
| 1 | Fix 1: Dead token skip (code) | ✅ PASS |
| 2 | Test 1: Imports | ✅ PASS |
| 3 | Test 2: Dead token skip (AI16Z / #1710 / BLAST) | ✅ PASS |
| 4 | Fix 2: ATR-aware SL floor (code) | ✅ PASS (with 1 spec deviation — see notes) |
| 5 | Test 3: Low-ATR SL < 1.30% (TRX / PAXG / BNB / BTC) | ✅ PASS |
| 6 | Fix 3: Grade F threshold = 28 (code) | ✅ PASS |
| 7 | Test 4: BTC LONG grade D not F | ✅ PASS |
| 8 | Test 5: EXTREME tokens R:R ≥ 1.5 | ⚠️ PARTIAL (2/3 pass; GRASS = 1.10) |
| 9 | Test 6: Full kill count | ✅ PASS (8% of real tokens killed) |
| 10 | Test 7: Direction correctness | ✅ PASS |

**Overall: 3 fixes verified working. One partial finding (GRASS R:R 1.10 via structural TP) — not a regression, expected code behavior, not a hard kill.**

---

## Fix 1: Dead token skip — ✅ PASS

**Code (risk_reward_engine.py:753-760):**
```python
if abs(atr_pct - 0.75) < 0.01:
    sr_check = build_sr_map(token_upper, price, candles_5m, atr_pct)
    if len(sr_check) == 0:
        return _result(True, 999, 0, 0, 0, 'A', None,
                     f'no market data for {token_upper} (fail-open)')
```
`_result` signature is `_result(passed, rr, sl, tp, score, grade, reason, notes)` (line 850) → returns `pass=True, rr=999, score=0, grade='A'` exactly as specified.

**Test 2 output:**
```
AI16Z:  pass=True rr=999 score=0 grade=A | OK
#1710:  pass=True rr=999 score=0 grade=A | OK
BLAST:  pass=True rr=999 score=0 grade=A | OK
```
All three dead tokens return fail-open with the exact expected values. `block_reason` is None.

**Confirmed downstream:** `rr_confidence_multiplier` (line 1013) detects `rr >= 999` and returns `1.0` (neutral, no boost, no block) — dead tokens cannot be killed or boosted. Verified in Test 6: 166 dead direction-evaluations skipped entirely.

---

## Fix 2: ATR-aware SL floor — ✅ PASS

**Code — pre-loop floor (lines 523-527):**
```python
sl_floor = getattr(hc, 'ATR_SL_MIN', 0.015)
atr_based_sl = atr_pct * 1.5 / 100.0  # 1.5× ATR as the effective floor
sl_distance_pct = max(sl_distance_pct, min(sl_floor, atr_based_sl))
```
⚠️ **Spec deviation (benign):** pre-loop floor uses **1.5× ATR**, not the 2.0× stated in the fix description. Stricter than spec — floor never wider than 1.5× ATR before the structural loop. Not a bug, but the fix description and code disagree.

**Code — post-loop clamp (lines 559-569):** matches spec exactly:
```python
sl_floor = getattr(hc, 'ATR_SL_MIN', 0.015)
atr_based_floor = atr_pct * 2.0 / 100.0  # 2× ATR as the cap on the floor
effective_floor = min(sl_floor, atr_based_floor)
if sl_distance_pct < effective_floor:
    sl_distance_pct = effective_floor
```

**Old fixed floor confirmed:** `hermes_constants.py:684` → `ATR_SL_MIN = 0.013` (1.30%).

**Test 3 output:**
```
TRX:  ATR=0.12% SL=0.25% R:R=2.03 grade=D   (SL ≈ 2× ATR, was 1.30% before fix)
PAXG: ATR=0.21% SL=0.42% R:R=1.20 grade=D   (SL = exactly 2× ATR)
BNB:  ATR=0.45% SL=0.90% R:R=1.00 grade=D   (SL = exactly 2× ATR)
BTC:  ATR=0.51% SL=1.01% R:R=1.04 grade=D   (SL ≈ 2× ATR, structural extension)
```
TRX and PAXG (the two tokens named in the verification criteria) both have SL far below 1.30%. ✅ The 1.30% fixed floor no longer traps low-ATR tokens.

---

## Fix 3: Grade F threshold lowered to 28 — ✅ PASS

**Code:**
- `hermes_constants.py:3887`: `RR_ENGINE_BLOCK_SCORE = 28  # hard block below this (grade F) — lowered from 35 (2026-10-12)`
- `risk_reward_engine.py:707`: `block_score = getattr(hc, 'RR_ENGINE_BLOCK_SCORE', 28)` — `_compute_score()` correctly uses the constant; grade D assigned for `score >= block_score`.

**Test 4 output:**
```
BTC LONG: score=34.0 grade=D (should be D, not F)
```
**Note:** live score is 34.0, not the 30.4 cited in the fix description (live S/R data has shifted since the fix was written — BTC now has 17 S/R levels vs whatever existed at fix time). **This actually strengthens the verification:** 34.0 < old threshold 35, so with current data BTC LONG would STILL be Grade F → `rr_confidence_multiplier` hard block (`grade == 'F'` → 0.0×, line 1017). The new threshold of 28 is what prevents this false kill right now. PASS with evidence the fix matters.

---

## Test 5: EXTREME tokens — ⚠️ PARTIAL (2/3)

```
INJ:   ATR=2.4% R:R=1.50 SL=2.36% TP=3.55% grade=D   (TP via ATR — capped at ATR×1.5)
SAND:  ATR=2.0% R:R=1.50 SL=2.02% TP=3.04% grade=D   (TP via ATR — capped at ATR×1.5)
GRASS: ATR=3.4% R:R=1.10 SL=1.92% TP=2.12% grade=D   (TP via CANDLE — structural level)
```

- **INJ ✅ / SAND ✅** — R:R exactly 1.50. The ATR-scaled TP cap (`_get_tp_max_pct`, line 474: `TP_cap = max(regime_cap, ATR × 1.5)`) works as designed: EXTREME regime base cap 2.0% is superseded by ATR×1.5 (3.54% / 3.03%), and SL = 1× ATR, giving R:R = 1.5 by construction.
- **GRASS ❌ (1.10 vs expected ≥ 1.5)** — root cause identified: GRASS's TP came from a **CANDLE S/R level** at 2.12%, not the ATR fallback. Structural TP selection (lines 582-601) overrides the ATR-based TP and does not enforce any minimum R:R. SL was also structurally extended to 1.92%. Net: R:R = 1.10. **The ATR-scaled TP cap only guarantees R:R ≥ 1.5 when TP is ATR-derived** — it does not protect against nearby structural targets.
- **Impact assessment:** NOT a hard kill. GRASS is grade D, shadow-logged only (`RR_ENGINE_SHADOW=True`, constants line 3848 — blocks are logged, `passed` forced True at line 817), and `rr_confidence_multiplier` returns 0.70× (poor penalty), not 0.0. No false kill. Expected behavior of the current design, but the test's stated expectation (R:R ≥ 1.5 for all EXTREME tokens) is not met for structural-TP cases.

---

## Test 6: Full kill count — ✅ PASS

```
Dead tokens skipped: 166
Real tokens: 368
Killed: 30 (8% of real)
```
166 dead direction-evaluations were short-circuited by Fix 1 (83 tokens × 2 directions, from 534 total price entries). Of 368 real evaluations, only 30 (8%) get multiplier 0.0. Kills come from `rr_confidence_multiplier`: grade F, R:R < 0.70 hard block, or `pass=False`. For context: shadow mode means `evaluate_rr` itself never blocks — the ~30 hard kills via the multiplier are the real production gate, and 8% is a healthy kill rate (the pre-fix false-kill pattern was killing legit low-ATR setups like BTC/TRX/PAXG).

---

## Test 7: Direction correctness — ✅ PASS

```
LONG SL < entry: True
LONG TP > entry: True
SHORT SL > entry: True
SHORT TP < entry: True
```
(BTC LONG: SL=82159.21 / TP=83870.76; BTC SHORT: SL=83840.79 / TP=81755.00 — both correct relative to $83,000 entry.)

---

## Sideways Finds (see something, say something)

1. **[LOW-MED] Dead-token detection is coupled to a fallback quirk.** `compute_vol_width` (lines 344-350): when `get_atr_pct()` returns None, it computes `ATR_PCT_FALLBACK(0.03) × 100 = 3.0%`, then clamps to `0.75%` because `3.0 > 1.5`. The dead-token check probes for this magic 0.75 value. If anyone changes `ATR_PCT_FALLBACK` to ≤ 0.015 (so ×100 ≤ 1.5), the clamp won't trigger, dead tokens get a real-looking ATR (e.g. 1.0%), and the dead-token skip silently disables. **Suggested fix:** detect deadness directly (`get_atr_pct(token) is None` + 0 S/R levels) instead of probing for 0.75. Works fine today — fragility, not a bug.
2. **[LOW] Fix description vs code desync:** pre-loop SL floor uses 1.5× ATR (line 526), post-loop clamp uses 2.0× ATR (line 562). The two floors are inconsistent with each other and with the fix description (which says 2.0× for both). Benign — the post-loop clamp is the binding one — but worth aligning doc + code.
3. **[LOW] Comment/value mismatch:** `hermes_constants.py:766` — `ATR_PCT_FALLBACK = 0.03  # 2% assumed ATR` — value converts to 3%, comment says 2%.
4. **[INFO] Misclassification risk is fail-open:** a live token with genuine ATR ≈ 0.75% ± 0.01 AND zero S/R levels would be mislabeled dead → returns pass=True (fail-open). Safe direction; negligible impact.

---

## Conclusion

All three fixes are present in code and behave as specified when executed:

- **Fix 1** returns exact fail-open values for dead tokens and downstream multiplier treats them as neutral.
- **Fix 2** removes the 1.30% SL floor trap for low-ATR tokens (TRX SL 0.25%, PAXG SL 0.42%).
- **Fix 3** keeps BTC LONG at grade D with current live data (score 34.0 — under the old 35 threshold it would still be falsely killed today).

The one unmet expectation (GRASS R:R 1.10) is explained, reproducible, and not a false kill — structural TP selection intentionally overrides the ATR cap. No regressions found. No fixes shipped by this verification — read-only audit plus this report.
