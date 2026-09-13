# SKEPTICAL AUDIT VERDICT
**Auditor:** Deep Skeptic  
**Date:** 2026-09-13 18:11 UTC  
**Subject:** Proposed SHORT filters for rr_structural.py  
**Data source:** PostgreSQL (brain), verified via live queries

---

## VERDICT SUMMARY

| # | Claim | Verdict | Skepticism |
|---|-------|---------|------------|
| 1 | bb_position < 0.1 saves LINK (-5.15%) and BANANA (-3.14%) | **PARTIAL** | HIGH |
| 2 | speed_percentile < 20 saves ZEN (-7.06%) | **PARTIAL** | HIGH |
| 3 | momentum_state = rising saves ZEN (-7.06%) | **PARTIAL** | HIGH |
| 4 | Combined filter saves -15.35% with 0 wins cost | **AGREE (the 3 trades) / DISAGREE (the claim)** | CRITICAL |
| 5 | Existing accel filter (now fixed) catches INJ-type losses | **PARTIAL** | HIGH |
| 6 | Existing RSI filter catches BANANA-type losses | **DISAGREE** | CRITICAL |
| 7 | Filters are complementary and don't overlap | **DISAGREE** | CRITICAL |

**OVERALL VERDICT: DO NOT DEPLOY AS CLAIMED.** The individual filter observations are correct for the 3 specific trades, but the aggregate claims are dangerously misleading.

---

## CLAIM 1: "bb_position < 0.1 filter for SHORT would save LINK (-5.15%) and BANANA (-3.14%)"

**Verdict: PARTIAL** — The specific trades match, but the claim is cherry-picked.

**Evidence:**
- ✅ LINK ID=15322: bb_position = **-0.086** (< 0.1 ✓) — pnl = -5.15%
- ✅ BANANA ID=15275: bb_position = **-0.0063** (< 0.1 ✓) — pnl = -3.14%

**Gotchas:**
1. **bb_position < 0.1 catches 136 out of 493 SHORT trades (27.6%).** This is NOT a surgical filter — it's a chainsaw. Over a quarter of all SHORTs would be blocked.
2. **Of those 136 trades, 52 are WINNERS (38.2%).** Filtering them out would cost +230.68% in lost PnL.
3. **bb_position is computed from a z-score based on 20-bar window** (signal_schema.py:464), NOT from Bollinger Bands directly. The variable name is misleading.
4. **bb_position is stored in `_signal_metadata` but the filter doesn't exist yet.** The claim is about a proposed filter, not an existing one.
5. **The metadata value is computed at signal creation time by `_enrich_indicators()`.** If the filter were added to `rr_structural.py` (detection time), the bb_position could be DIFFERENT because:
   - `_enrich_indicators` uses `get_price_history(token, 60)` — 60min of 1m data
   - rr_structural would need a separate computation
   - Data may change between detection and metadata capture

---

## CLAIM 2: "speed_percentile < 20 filter for SHORT would save ZEN (-7.06%)"

**Verdict: PARTIAL** — The trade matches, but the filter has catastrophic false positives.

**Evidence:**
- ✅ ZEN ID=15324: speed_percentile = **7.5** (< 20 ✓) — pnl = -7.06%

**Gotchas:**
1. **speed_percentile < 20 catches 77 out of 493 SHORT trades (15.6%).**
2. **Of those 77 trades, 39 are WINNERS (50.6%).** The filter has a coin-flip false positive rate.
3. **🔴 CRITICAL: 109 tradeable tokens have NO speed data in token_speeds.** If the filter is applied to signal metadata (where speed_percentile comes from token_speeds), these tokens will have `speed_percentile = None`, causing:
   - If coded as `if m.get('speed_percentile') is not None and m.get('speed_percentile') < 20:` → **FAIL OPEN** (trade goes through even with no speed data)
   - If coded as `if m.get('speed_percentile') < 20:` → **TypeError crash**
   - Either way: 53% of tradeable tokens bypass this filter entirely.
4. **speed_percentile in metadata comes from `token_speeds` table** (signal_schema.py:499), which is written by `speed_tracker.py` approximately once per minute. It's a PERCENTAGE ranking across all tokens, NOT an absolute velocity measure. A token can have speed_percentile=20 and still be moving fast — it just means 80% of tokens are moving faster.
5. **The speed_percentile at metadata capture time ≠ what it would be at detection time** if the filter were added to rr_structural.py. Speed updates every ~1 minute.

---

## CLAIM 3: "momentum_state = rising filter for SHORT would save ZEN (-7.06%)"

**Verdict: PARTIAL** — The trade matches, but the filter catches too many winners.

**Evidence:**
- ✅ ZEN ID=15324: momentum_state = **rising** (✓) — pnl = -7.06%

**Gotchas:**
1. **momentum_state = rising catches 80 out of 493 SHORT trades (16.2%).**
2. **Of those 80 trades, 38 are WINNERS (47.5%).** Almost half are false positives.
3. **momentum_state is computed from a 5-bar velocity** (signal_schema.py:489):
   ```python
   vel = (prices[-1] - prices[-6]) / prices[-6] * 100
   momentum_state = 'rising' if vel > 0.1 else 'falling' if vel < -0.1 else 'flat'
   ```
   This is a 5-minute velocity from 1m candles. `vel > 0.1%` is an extremely low threshold — almost any uptick triggers "rising."
4. **🔴 "Zero cost" claim is FALSE if the filter is added to rr_structural.py.** The closes used for momentum_state come from `get_price_history(token, 60)` (60min window), while rr_structural's `_get_rsi()` fetches 100 closes from candles_1m with a separate query. These are different queries. Adding momentum_state to rr_structural would require either:
   - A NEW database query (not zero cost)
   - Refactoring `_get_rsi()` to return closes (code change)
   - **However**, if the filter is added to `signal_compactor.py` instead (checking metadata), then yes, it's zero additional cost because the metadata already has momentum_state.
5. **momentum_state is NOT from token_speeds.** It's computed independently in `_enrich_indicators()`. This is a different computation from the "momentum" in speed_tracker.

---

## CLAIM 4: "Combined filter saves -15.35% with 0 wins cost"

**Verdict: DISAGREE** — The -15.35% figure is correct for 3 trades, but the "0 wins cost" claim is **demonstrably false**.

**Evidence:**
- ✅ LINK (-5.15%) + BANANA (-3.14%) + ZEN (-7.06%) = -15.35% ✓
- ❌ The combined filter catches **261 out of 493 SHORT trades (52.9%)**
- ❌ **145 of those are WINNERS** — not zero
- ❌ Total wins lost: **+412.42%** in PnL
- ❌ Total losses saved: **-514.85%** in PnL
- ❌ **NET IMPACT: -102.43%** (you'd LOSE more than you save)

**The "0 wins cost" appears to come from ONLY checking those 3 specific trades, not the actual filter behavior.**

**Top 10 winning trades that would be killed by this filter:**
| Token | PnL | Caught By |
|-------|-----|-----------|
| ONDO | +18.66% | mom |
| SEI | +15.79% | mom |
| ADA | +14.12% | mom |
| INJ | +12.49% | bb |
| WLD | +10.12% | bb |
| DYDX | +9.78% | bb |
| CHIP | +9.40% | speed+mom |
| DOGE | +9.34% | speed |
| ETC | +8.49% | bb |
| PUMP | +7.81% | bb |

**Zero intersection:** The proposed "combined filter" has **0 trades** where all three conditions (bb<0.1 AND speed<20 AND mom=rising) are true simultaneously. This means:
- The filters never actually fire together
- The "combined" filter is really just the union (OR) of three independent filters
- Each individual filter has terrible precision

---

## CLAIM 5: "Existing accel filter (now fixed) catches INJ-type losses"

**Verdict: PARTIAL** — The accel filter exists and the code fix is real, but the claim is misleading.

**Evidence:**
- ✅ The code in rr_structural.py (lines 125-129) does use absolute delta:
  ```python
  first_half_delta = closes[mid] - closes[0]
  second_half_delta = closes[-1] - closes[mid]
  return second_half_delta - first_half_delta
  ```
- ✅ INJ ID=15295 has `price_acceleration = 0.0044` (> 0) in metadata — would be caught IF the filter used this value.
- ✅ INJ ID=15261 has `price_acceleration = 0.009` (> 0) in metadata — would be caught.

**Gotchas:**
1. **🔴 The accel value in metadata (from token_speeds) is a DIFFERENT COMPUTATION from rr_structural's `_compute_price_acceleration()`:**
   - **token_speeds** (speed_tracker.py:294-301): `accel = (vel_5m - vel_15m) / span` — difference of PERCENTAGE velocities
   - **rr_structural** (_compute_price_acceleration, lines 125-129): `second_half_delta - first_half_delta` — difference of ABSOLUTE price deltas
   - These can give OPPOSITE signs for the same price action.
2. **INJ ID=15295 STILL FIRED as rr-struct- despite accel=0.0044 in metadata.** This proves the two computations diverged at detection time. The rr_structural accel was ≤ 0, so the filter didn't block it. The metadata accel (from token_speeds) was 0.0044, but it wasn't checked.
3. **The accel filter in rr_structural uses `_compute_price_acceleration(token)` which opens a SEPARATE SQLite connection to candles.db.** This is an additional DB query, not free.
4. **The existing accel filter catches 221 trades (44.8% of all SHORTs).** Of those, 122 are winners (55.2%). The filter has a negative net impact: saves -407.01% but costs +317.46%.
5. **"Now fixed" — the absolute delta fix is real but only applies to rr_structural._compute_price_acceleration().** The metadata `price_acceleration` (from speed_tracker) still uses percentage velocity. Anyone analyzing trades via metadata accel values would get misleading results.

---

## CLAIM 6: "Existing RSI filter catches BANANA-type losses"

**Verdict: DISAGREE** — The RSI filter did NOT catch BANANA. The metadata value is misleading.

**Evidence:**
- ❌ BANANA ID=15275: **The rr-struct- SHORT signal FIRED** despite having rsi_14=10.53 in metadata.
- ❌ This PROVES the existing RSI filter (RR_STRUCTURAL_RSI_MIN = 30) did NOT catch this trade.
- ❌ If the filter had caught it, the signal would never have been created.

**Root cause — RSI computation discrepancy:**
1. **rr_structural._get_rsi()** (lines 80-100): Fetches 100 closes from `candles_1m WHERE is_closed = 1`. Computes standard RSI.
2. **signal_schema._enrich_indicators()** (lines 466-473): Fetches 50 closes from `_get_closes_from_candles_1m()` which does **NOT** filter by `is_closed = 1`. Computes RSI differently.
3. **At detection time, rr_structural's RSI was ≥ 30** (otherwise the signal would have been blocked).
4. **At metadata capture time, the enriched RSI was 10.53** (different computation, possibly including unclosed candle).
5. **You CANNOT use metadata `rsi_14` to verify whether the rr_structural RSI filter would have caught a trade.** They are different values from different computations.

**Gotchas:**
1. The rr_structural RSI filter DOES exist and has `RR_STRUCTURAL_RSI_MIN = 30`. It works correctly — for its own computation.
2. But BANANA's RSI was apparently ≥ 30 at detection time, meaning the market conditions were different 50-100 candles earlier.
3. **This is a timing issue:** the RSI could change significantly between when the 1m candle closes and when the metadata is captured.
4. **The existing RSI filter has caught ZERO rr-struct- SHORT trades in 30 days of data** (confirmed by query). This means either:
   - No rr-struct- SHORT has had RSI < 30 at detection time, OR
   - The RSI values are consistently ≥ 30 at detection time but drop later

---

## CLAIM 7: "These filters are complementary and don't overlap"

**Verdict: DISAGREE** — The filters overlap massively with each other AND with existing filters.

**Evidence:**
- **New filters overlap with EXISTING filters (accel + RSI):**
  - bb_position<0.1: 64/136 overlap with existing filters (47%)
  - speed_percentile<20: 37/77 overlap with existing filters (48%)
  - momentum_state=rising: 32/80 overlap with existing filters (40%)
  - Total overlap: **123 trades** caught by both new AND existing filters

- **New filters overlap with EACH OTHER:**
  - bb ∩ speed: catches same trades for tokens that are both oversold and slow
  - bb ∩ mom: catches trades where price is at bottom but rising (contradictory signal)
  - speed ∩ mom: catches slow tokens that are rising
  - All three: **ZERO trades** (the filters never all trigger simultaneously)

- **The "complementary" claim is FALSE** because:
  1. 123 trades are double-counted (caught by both new and existing)
  2. Only 138 trades are truly new catches (not caught by existing)
  3. Of those 138 new catches, many are big winners (ADA +14.12%, ONDO +18.66%, SEI +15.79%)
  4. The filters are not independent — they all correlate with "price at low point in recent history"

---

## ADDITIONAL TECHNICAL FINDINGS

### Finding A: TWO Different Acceleration Computations
| Metric | Source | Formula | Used By |
|--------|--------|---------|---------|
| `price_acceleration` (metadata) | token_speeds / speed_tracker.py | `(vel_5m - vel_15m) / span` (% velocity difference) | signal_compactor (metadata) |
| `_compute_price_acceleration()` | rr_structural.py | `second_half_delta - first_half_delta` (absolute price delta of delta) | rr_structural filter |

These can give OPPOSITE signs. Anyone analyzing trades via metadata accel would reach wrong conclusions about whether the rr_structural filter would have caught them.

### Finding B: RSI Computation Discrepancy
| Metric | Source | Candles | is_closed filter |
|--------|--------|---------|------------------|
| RSI (filter) | rr_structural._get_rsi() | 100 | YES (is_closed=1) |
| rsi_14 (metadata) | signal_schema._enrich_indicators() | 50 | NO |

These can differ by 20+ RSI points on the same token at the same time. The metadata rsi_14 is NOT reliable for verifying rr_structural's RSI filter behavior.

### Finding C: Fail-Open for Missing Speed Data
**109 tradeable tokens** (53% of all tradeable tokens) have NO data in `token_speeds`. A `speed_percentile < 20` filter would:
- **Fail open** if properly coded with None check → trades pass through anyway
- **Crash** if coded without None check → TypeError

### Finding D: The Momentum State Threshold is Too Low
```python
vel = (prices[-1] - prices[-6]) / prices[-6] * 100
momentum_state = 'rising' if vel > 0.1 else 'falling' if vel < -0.1 else 'flat'
```
A 0.1% threshold over 5 minutes means ANY tiny uptick triggers "rising." This explains why 16.2% of ALL SHORTs have `momentum_state = rising` — it's barely above noise.

### Finding E: The Existing Accel Filter is Net Negative
The accel filter (`price_accel > 0` blocks SHORT) catches 221 trades but:
- 122 wins (cost +317.46%)
- 99 losses (save -407.01%)
- **Net: -89.55%** (you'd be better off without this filter)

This filter was described as "catching INJ-type losses" but it actually catches MORE winners than losers.

---

## RECOMMENDATIONS

1. **DO NOT deploy the combined filter as claimed.** The "0 wins cost" claim is false. The filter catches 145 winners.

2. **If deploying individual filters, use signal_compactor.py, not rr_structural.py.** The metadata already has bb_position, speed_percentile, and momentum_state. Adding filters to rr_structural would require new DB queries.

3. **Fix the speed_percentile filter to handle missing data.** With 109 tradeable tokens missing speed data, the filter must explicitly handle None values.

4. **Raise the momentum_state threshold.** 0.1% over 5 minutes is noise. Consider 0.5% or higher.

5. **Standardize RSI computation.** The rr_structural RSI and metadata rsi_14 use different data windows and filters. This makes trade analysis unreliable.

6. **Standardize acceleration computation.** token_speeds and rr_structural use fundamentally different formulas. Pick one and use it consistently.

7. **Re-evaluate the existing accel filter.** It has a negative net impact. Consider whether the "percentage ROC vs absolute delta fix" actually improved it, or if the filter itself is fundamentally flawed.

8. **If you want to filter oversold SHORTs, use rsi_14 < 20 (not < 30).** The current rr_structural RSI_MIN=30 catches nothing. A lower threshold like 20 would catch extreme cases like BANANA (rsi_14=10.53) without excessive false positives.

---

## DATA SUMMARY

| Filter | Trades Caught | Wins Lost | Losses Saved | Net Impact |
|--------|--------------|-----------|--------------|------------|
| bb_position < 0.1 | 136/493 (27.6%) | +230.68% | -241.76% | -11.08% |
| speed_percentile < 20 | 77/493 (15.6%) | +99.62% | -146.59% | -46.97% |
| momentum_state = rising | 80/493 (16.2%) | +124.90% | -194.39% | -69.49% |
| Combined (OR) | 261/493 (52.9%) | +412.42% | -514.85% | -102.43% |
| Existing accel (accel>0) | 221/493 (44.8%) | +317.46% | -407.01% | -89.55% |
| Existing RSI (RSI<30) | 0/493 (0%) | 0% | 0% | 0% |

*All PnL values in percentage points. Net Impact = Losses Saved + Wins Lost.*
