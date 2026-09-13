# INDEPENDENT AUDIT VERDICT — ZEN SHORT Loss & Proposed Combined Filter

**Auditor:** Independent auditor (fresh eyes, no priming)
**Date:** 2026-09-13 ~18:00 UTC
**Files read from scratch:** rr_structural.py, hermes_constants.py (lines 3135-3165), risk_reward_engine.py
**Data verified:** PostgreSQL (brain DB), candles.db, signals_hermes_runtime.db, git history

---

## Claim 1: ZEN SHORT lost because momentum was rising and speed was dead (7.5 percentile)

**Verdict: AGREE**
**Confidence: HIGH**

**Evidence:**
- PostgreSQL `_signal_metadata` confirms: `momentum_state=rising`, `speed_percentile=7.5`, `bb_position=0.420`, `rsi_14=41.79`, `price_acceleration=-0.0046`
- Entry: $6.3206, Exit: $6.4098 (atr_sl_hit), PnL: -7.06%
- Price moved UP 1.41% against the SHORT position
- The signal fired a SHORT while price was accelerating UPWARD (rising momentum, dead speed = grinding higher with no pullback)
- Metadata also shows `is_stale=True`, `btc_regime=TRANSITIONING`

**Root cause analysis:** Shorting a token with rising momentum and near-zero speed is fighting the tape. Speed=7.5 means ZEN was moving slower than 92.5% of tokens — a slow grind upward. Rising momentum confirms the direction was UP. This was a structural misfire: good R:R on paper but wrong market dynamics.

---

## Claim 2: Combined filter (bb<0.1 OR speed<20 OR mom=rising) saves all 3 SHORT losses with 0 wins cost

**Verdict: PARTIAL — misses INJ (-6.52%)**
**Confidence: HIGH**

**Evidence — all 7 rr-struct- SHORT trades:**

| Token | PnL | bb_position | speed | mom | bb<0.1 | spd<20 | mom=r | ANY | Correct? |
|-------|-----|------------|-------|-----|--------|--------|-------|-----|----------|
| ZEN | -7.06% | 0.420 | 7.5 | rising | — | BLOCK | BLOCK | BLOCK | ✅ Caught |
| LINK | -5.15% | -0.086 | 57.1 | falling | BLOCK | — | — | BLOCK | ✅ Caught |
| BANANA | -3.14% | -0.006 | 29.8 | falling | BLOCK | — | — | BLOCK | ✅ Caught |
| **INJ** | **-6.52%** | **0.385** | **77.6** | **flat** | **—** | **—** | **—** | **—** | **❌ MISSED** |
| LDO | +2.81% | 0.511 | 46.0 | flat | — | — | — | — | ✅ Passes |
| AIXBT | +1.36% | 0.371 | 75.8 | flat | — | — | — | — | ✅ Passes |
| MNT | +5.58% | 0.316 | 37.0 | flat | — | — | — | — | ✅ Passes |

**What the filter catches:**
- 3 losses saved: ZEN (-7.06%) + LINK (-5.15%) + BANANA (-3.14%) = **-15.35% saved**
- 0 wins lost ✅ (no winning SHORT has bb<0.1, speed<20, or mom=rising)

**What it MISSES:**
- **INJ SHORT (-6.52%)**: bb=0.385, speed=77.6, mom=flat — none of the 3 filters trigger
- INJ is the 2nd largest loss and would NOT be caught

**Why INJ was missed:** INJ had a flat momentum state and normal speed/bb. It should have been caught by the **existing accel filter** (accel=0.0044 > 0 = price going UP → should block SHORT). However, there was a bug in the accel calculation that used percentage ROC instead of absolute price delta, which caused false negatives in uptrends. This bug was fixed on 2026-09-13 04:56 UTC — AFTER INJ opened (2026-09-12 13:33 UTC).

---

## Claim 3: bb_position is available via `short_result['vol_width']['bb_position']` — zero cost

**Verdict: AGREE**
**Confidence: HIGH**

**Evidence:**
- `risk_reward_engine.py` line 348-355: `compute_vol_width()` returns dict with `bb_position` key
- `evaluate_rr()` line 767: returns `{'vol_width': vol_width, ...}`
- In `rr_structural.py` detect(), `short_result['vol_width']` is already accessed (line 224-225)
- Adding `short_result['vol_width']['bb_position']` costs **zero additional computation** — it's already computed inside `evaluate_rr()`

**Verification:** Running `evaluate_rr('ZEN', 'SHORT', 6.3206)` confirms vol_width contains `bb_position=1.289` (current price is above upper BB; at trade entry time the metadata shows 0.420).

**Note on bb_position semantics:**
- bb_position = 0 → price at lower Bollinger Band
- bb_position = 0.5 → price at middle band (SMA)
- bb_position = 1 → price at upper band
- bb_position < 0 → price below lower band (extreme oversold)
- bb_position > 1 → price above upper band (extreme overbought)
- LINK bb=-0.086 and BANANA bb=-0.006 both have price BELOW the lower BB, making SHORT entries very risky (shorting oversold = catching falling knife in reverse)

---

## Claim 4: Speed and momentum need new candle computation functions

**Verdict: DISAGREE — existing data is sufficient**
**Confidence: HIGH**

**Evidence for speed_percentile:**
- `token_speeds` table in `signals_hermes_runtime.db` already has `speed_percentile` per token
- `signal_schema.py` line 493-499 already queries it in `get_signal_enrichment()`
- To access from `detect()`: one SQLite query to `signals_hermes_runtime.db` → `token_speeds.speed_percentile WHERE token = ?`
- The file already imports `sqlite3` and has `_CANDLES_DB` — adding a `RUNTIME_DB` constant and one query is trivial
- **Cost: 1 SQL query (~1ms)**

**Evidence for momentum_state:**
- Computed from 5-bar velocity of close prices: `(prices[-1] - prices[-6]) / prices[-6] * 100`
- If velocity > 0.1% → "rising", < -0.1% → "falling", else "flat"
- `detect()` already calls `_get_rsi()` which fetches 100 1m candle closes from candles.db
- The same close data can compute momentum_state — just needs velocity of last 6 closes
- **Cost: reuse existing data, ~5 lines of code**

**Neither requires new candle computation functions.** Speed is a pre-computed ranking, momentum_state is a trivial velocity calculation from data already fetched.

---

## BONUS FINDING: Existing filters should have caught BANANA and INJ

### BANANA (RSI=10.53 — extreme oversold)
**The existing RSI filter (RR_STRUCTURAL_RSI_MIN=30) should have blocked this SHORT.**

- BANANA opened: 2026-09-11 22:37 UTC
- RSI filter added to rr_structural.py: 2026-09-12 01:11 UTC
- **BANANA was traded BEFORE the RSI filter existed in the code**
- RSI=10.53 is extreme oversold — shorting this is suicidal. The filter was correctly designed but came too late.

### INJ (accel=+0.0044 — price going UP)
**The existing accel filter (RR_STRUCTURAL_BLOCK_ACCEL=True) should have blocked this SHORT.**

- INJ opened: 2026-09-12 13:33 UTC
- Accel filter bug fix: 2026-09-13 04:56 UTC
- **The accel filter existed but had a bug**: it used percentage ROC instead of absolute price delta. In an uptrend, percentage ROC shows negative values even when price is rising (because the base is higher). This false negative let INJ through.
- The fix (commit f787fae4) changed to absolute price deltas and fixed the row guard off-by-one.

---

## SIDE FINDING: Proposed filters would block some winning LONG trades if applied broadly

If the proposed SHORT filters were accidentally applied to LONG signals too:

| LONG Trade | PnL | Would be blocked by |
|------------|-----|---------------------|
| INJ LONG | +5.47% | mom=rising |
| NEO LONG | +30.98% | mom=rising |
| NEAR LONG | +0.27% | mom=rising |
| IMX LONG | +0.61% | mom=rising |
| BABY LONG | +4.46% | speed=18.0 < 20 |
| WLD LONG | -5.75% | speed=15.5 < 20 |

**6 trades affected (5 winners, 1 loser).** The filters MUST be direction-gated to SHORT only. The proposed implementation in `rr_structural.py` detect() naturally does this since it checks `short_ok` vs `long_ok` separately, so this is safe as implemented.

---

## SUMMARY TABLE

| # | Claim | Verdict | Confidence |
|---|-------|---------|------------|
| 1 | ZEN lost due to rising momentum + dead speed | **AGREE** | HIGH |
| 2 | Combined filter saves all 3 losses, 0 wins cost | **PARTIAL** — misses INJ (-6.52%) | HIGH |
| 3 | bb_position available from vol_width at zero cost | **AGREE** | HIGH |
| 4 | Speed/momentum need new computation functions | **DISAGREE** — existing data sufficient | HIGH |

## RECOMMENDATIONS

1. **Add bb_position < 0.1 filter** for SHORT — zero cost, catches LINK and BANANA-type setups. Implement in detect() using `short_result['vol_width']['bb_position']`.

2. **Add speed_percentile < 20 filter** for SHORT — 1 SQL query to token_speeds. Catches ZEN-type setups (dead speed = grinding against trade direction).

3. **Add momentum_state filter** for SHORT (rising = block) — ~5 lines using existing candle data. Catches ZEN-type setups.

4. **To catch INJ too:** The existing accel filter (block SHORT when accel > 0) should work now that the bug is fixed. Verify by checking if any future SHORT trades with accel > 0 still get through. If not, the existing accel filter is sufficient for INJ-type losses.

5. **Verify BANANA is now protected:** The RSI<30 filter was added after BANANA. All future SHORT entries with RSI<30 should be blocked. Run a backtest to confirm.

6. **DO NOT apply these filters to LONG signals** — they would incorrectly block winners (NEO +30.98%, INJ +5.47%, etc.).

---

*Auditor's note: The INJ miss is the most important finding here. The proposed "saves ALL SHORT losses" claim is overstated — it saves 3 of 4 losses (75%). The 4th loss (INJ -6.52%) needs the existing accel filter (now fixed) to catch it. The total saved is -15.35% (not the full -21.87% including INJ).*
