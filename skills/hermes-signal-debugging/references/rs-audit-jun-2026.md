# rs.py Audit — June 14, 2026

## Bugs Found & Fixed

### Bug 1: `cand_signal` NameError at line 753 (HIGH)
**Symptom:** `NameError: name 'cand_signal' is not defined` when resistance path hits bounce gate or hard cap.
**Root cause:** `cand_signal` was only defined inside `else: bounces` block but used at line 753 outside that block.
**Fix:** Added `cand_signal = None` initialization before the bounces gate (line 699).
**File:** `/root/.hermes/scripts/signals/rs.py`

### Bug 2: Bounce detection scale mismatch (HIGH)
**Symptom:** `next_close > c['close'] * 1.00025` compared next candle to the TOUCHING candle's close, not to the level itself. A candle 0.2% away from level (touch_thresh) could confirm bounce with only 0.025% follow-through (8:1 scale mismatch).
**Fix:** Changed to `next_close > level * 1.00025` (LONG) and `level * 0.99975` (SHORT).
**File:** `/root/.hermes/scripts/signals/rs.py` lines 290, 301

### Bug 3: Bounce HARD GATE blocked broken-level path (HIGH)
**Symptom:** Broken-level signals never fired regardless of `RS_BROKEN_SHORT_ENABLED` / `RS_BROKEN_RESISTANCE_LONG_ENABLED` settings.
**Root cause:** Pre-868add3: broken check ran independently. Post-868add3: bounce gate (`if not bounces: nearest_support = None`) ran BEFORE the broken-path check, making it unreachable when `bounces=False`. The broken path was nested inside the `else: bounces` block.
**Fix (Jun 14 2026):** Restructured BOTH support and resistance sections so broken-path check runs BEFORE bounce gate:
```
# BEFORE (broken path unreachable when bounces=False):
if not bounces:
    nearest_support = None
else:
    if broken: ...       ← never reached when bounces=False
    else: ...            ← only reachable with bounces=True

# AFTER (broken path fires independently):
if broken: ...           ← fires regardless of bounces
elif bounces: ...        ← normal bounce path still gated by bounce confirmation
```
**Files:** `/root/.hermes/scripts/signals/rs.py` lines 622–680 (support) and 695–760 (resistance)

### Bug 4: Outdated comment on recency formula (LOW)
**Symptom:** Line 27 comment: `recency_score = recent + K×ancient`. Actual code (line 414): `recency_score = recency_touches × K + ancient_touches` with K=3.0.
**Fix:** Update line 27 comment to match actual formula. Code is correct (K=3.0 gives recent 3× weight over ancient — intended behavior).

---

## Verified Working (June 14, 2026)

### 1m price_history confirmed for ALL calculations
```
price_history (signals_hermes.db)
  → _get_candles_1m() synthesizes ohlcv (open=high=low=close=price)
  → detect_rs_signal(candles, price)
      → _atr()              ← from input candles
      → _find_swing_highs_lows() ← from input candles
      → _build_level_touches()   ← from input candles (fast NumPy path)
      → _bounce_confirmation()    ← from input candles
      → _level_recently_broken() ← from input candles
```
No candles, ohlcv_1m, or external API calls used anywhere in detection chain.

### Bounce detection verified
- LONG: candle within 0.2×ATR of level, next candle closes above `level*1.00025` → True
- SHORT: candle within 0.2×ATR, next candle closes below `level*0.99975` → True
- Verified with concrete traces on AAVE/AVAX real data.
- `lookback=6` candles minimum, `RS_BOUNCE_THRESH_ATR=1.0`

### Broken level handling verified
- Support broken: `prev_close > level > curr_close` AND follow-through candle also below → True
- Support bounce (NOT broken): cross then immediate reversal → False
- Resistance broken: `prev_close < level < curr_close` AND follow-through candle also above → True
- Both require 2 confirming candles beyond crossing candle (single cross = bounce, not break)

---

## Design Limitations (Not Bugs)

1. **Bounce nearly impossible on close-only + tight ATR tokens**: For low-ATR tokens (AVAX 0.031%, AAVE 0.018%), touch_thresh is 0.004-0.006% of price. Close-only candles (open=high=low=close) rarely hit such tight thresholds. This is a data quality limitation, not a code defect.

2. **`_get_clustered_recency` heuristic**: When clustering averages multiple raw levels, recency lookup finds the closest raw level by price — not a cluster member. Better than guaranteed miss from exact-key lookup. Acceptable.

3. **Legacy `_build_level_touches` path dead code**: Lines 417-428 never reached (all callers pass `candles_arrays` tuple). Can be removed in cleanup.

4. **`cand_signal` redundant assignment at line 719**: When killswitch fires, both the early `cand_signal = None` (line 719) and the later assignment in `else` block (line 748) set the same variable. No functional issue.

---

## Key Constants (June 2026)
- `RS_BOUNCE_THRESH_ATR = 1.0` — touch threshold multiplier
- `RS_BOUNCE_LOOKBACK = 6` — candles checked for bounce confirmation
- `RS_PROXIMITY_K = 0.70` — fire if price within 0.70 ATR of level
- `RS_MIN_TOUCHES = 5` — minimum touches for valid level
- `RS_TOUCH_HARD_CAP = 120` — block signals above this touch count
- `RS_BROKEN_SHORT_ENABLED = True` (effectively disabled)
- `RS_BROKEN_RESISTANCE_LONG_ENABLED = True` (effectively disabled)
- `RS_LEVEL_BROKEN_LOOKBACK = 200` — ~8hrs on 1m candles
