# Surfing.md Gap Closure — Plan

## Goal

Close the gap between `surfing.md` (the trading philosophy) and the live Hermes implementation. Prioritize highest-impact items that improve signal quality and reduce false entries.

---

## Gap Analysis Summary

| Status | Count |
|--------|-------|
| ✅ Fully implemented | 13 |
| ⚠️ Partially done | 4 |
| ❌ Not implemented | 5 |

---

## Priority 1 — High Impact, Low Risk

### 1. Use `wave_phase` + `funding_rate` in signal decisions

**What:** The `wave_phase` field is written to `token_speeds` DB but never used in signal scoring or filtering. Funding rates are fetched by `candle_predictor.py` but not used in trade decisions.

**Why:** `wave_phase` encodes whether a token is "building", "cresting", "collapsing", or "range-bound" — exactly what surfing.md's wave quality filter describes. Funding rate is the "wind direction" that tells you if a wave has tailwind or headwind.

**Files likely to change:**
- `signal_gen.py` — add `wave_phase` and `funding_rate` to LONG/SHORT signal scoring
- `ai_decider.py` — add `wave_phase` and `funding_rate` to prompt context so LLM decider can use it

**Approach:**
1. In `signal_gen.py`, fetch `wave_phase` from `speed_tracker.get_token_speed(token)` alongside speed data
2. Fetch funding rate from `candle_predictor.py`'s `fetch_hl_market_data()` or directly from HL API
3. In LONG signal scoring: penalize tokens with `wave_phase == "collapsing"` or `wave_phase == "range-bound"`
4. In SHORT signal scoring: penalize tokens with `wave_phase == "building"` or `wave_phase == "range-bound"`
5. Add funding rate as a multiplier: LONG with negative funding rate (tailwind) gets +5% score boost; SHORT with positive funding rate gets +5%

**Risks:** Adding too many filters could reduce position frequency. Start with mild penalties (5-10%), not hard blocks.

---

### 2. Hard-block counter-trend traps instead of penalizing

**What:** `_check_counter_trend_trap()` currently penalizes confidence by 10-20pts. Surfing.md says it should be a hard block.

**Why:** NIL trade (surfing.md) shows counter-trend traps are high-probability failures. A penalty lets strong signals through anyway — but the problem is the signal fired in a range, not just low confidence.

**Files likely to change:**
- `decider_run.py` — `_check_counter_trend_trap()` and its call sites (lines ~980, ~1445)

**Approach:**
1. Change penalty logic to hard-block when: `is_stale AND |z_score| < 1.0` (near mean) AND direction contradicts regime
2. Keep penalty for edge cases where z-score is extreme but speed is picking up (potential wave turn in progress)
3. Add test: replay NIL token's Apr 2 signal — should now block

**Risks:** Could block legitimate reversals at extreme z-scores. Keep the `|z_score| < 1.0` near-mean condition to only block range-bound counter-trend traps.

---

## Priority 2 — Medium Impact, Medium Effort

### 3. Add regime STRONG/WEAK axis to signal decisions

**What:** Regime is currently binary LONG/SHORT. Surfing.md wants a STRONG/WEAK confidence axis that gates whether z-score extremes are used as entries vs exits.

**Why:** 0G trade (surfing.md) — z=-1.179 at bottom of range was treated as entry signal, but regime was weak/ranging, so z-score should have triggered an EXIT, not an entry.

**Files likely to change:**
- `4h_regime_scanner.py` — compute regime confidence/strength score
- `signal_gen.py` — use regime strength in z-score interpretation
- `ai_decider.py` — add regime strength to prompt context

**Approach:**
1. In `4h_regime_scanner.py`, add `regime_strength` score (0-100) based on:
   - Consistency of 4h candle directions (all green vs mixed)
   - BTC/ETH regime alignment across timeframes
   - Funding rate direction
2. In `signal_gen.py`:
   - If `regime_strength < 40` (weak regime): treat z-score extremes as **exit signals only**, not entry triggers
   - If `regime_strength >= 60` (strong regime): z-score extremes confirm trend entries
3. In AI decider prompt: tell LLM that weak regimes = mean reversion, strong regimes = trend continuation

**Risks:** Regime strength calculation needs historical validation. Start simple (e.g., % of last 20 4h candles in same direction) before adding complexity.

---

### 4. `speed_percentile >= 80 → +15% score boost` (not just threshold boost)

**What:** Currently speed>=80 tokens get 5% easier entry threshold. Surfing.md describes a 15% score boost applied to the confidence number itself.

**Why:** Surfing.md says "+15% score boost" — threshold reduction is a different mechanism. A score boost propagates through to hot-set ranking; a threshold reduction only affects the final gate.

**Files likely to change:**
- `signal_gen.py` — apply multiplicative boost to signal confidence when `speed_percentile >= 80`
- `decider_run.py` — already has 20% boost (verify it's working as described)

**Approach:**
1. In `signal_gen.py`, after computing `score`, before writing to DB:
   ```python
   if speed_pctl >= 80:
       score = min(score * 1.15, 100)
   ```
2. Update `surfing.md` entry to match: current implementation uses 5% threshold reduction, not 15% score boost. Decide which is correct and update one.

**Risks:** Score inflation. Cap at 100% to prevent overflow.

---

## Priority 3 — Lower Impact / More Research Needed

### 5. Wave-of-interest filter (top 50 tokens)

**What:** Instead of processing all 536 tokens, focus on top 50 that are: (a) in regime direction, (b) speed_percentile > 50, (c) not is_stale.

**Why:** Reduces compute, focuses on actionable waves.

**Risks:** Could miss slow-building setups. Not urgent — current pipeline handles 536 tokens without obvious bottleneck.

---

### 6. Position-in-wave detection

**What:** Detect if we're early/mid/late in a wave to adjust position sizing.

**Risks:** Hard to implement reliably. Needs research. Lower priority than 1-4.

---

## Files To Change (Summary)

| Priority | File | Change |
|----------|------|--------|
| P1 | `signal_gen.py` | Add wave_phase + funding_rate to scoring; add 15% score boost for speed>=80 |
| P1 | `decider_run.py` | Hard-block counter-trend traps |
| P2 | `4h_regime_scanner.py` | Add regime_strength calculation |
| P2 | `ai_decider.py` | Add wave_phase + funding_rate + regime_strength to prompt context |
| P3 | `signal_gen.py` | Optional: wave-of-interest filter for universe reduction |

## Validation

1. Replay NIL token Apr 2 20:11 signal — should now block (P1 #2)
2. Replay 0G trade Mar 22 — should now flag as weak-regime exit, not entry (P2 #3)
3. Check that existing hot-set scores show ~15% boost for speed>=80 tokens (P2 #4)
4. Monitor pipeline log for `wave_phase` and `funding_rate` appearing in signal context (P1 #1)

## Open Questions

1. Is the 15% score boost (surfing.md) correct, or should it stay as 5% threshold reduction?
2. What `wave_phase` values are actually being written by `speed_tracker.py`? Need to check live data.
3. Should regime_strength use a rolling window or fixed lookback? Rolling is more adaptive but noisier.
