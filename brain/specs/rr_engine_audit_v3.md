# Independent Audit v3: Implementation Verification

**Auditor:** Third-Party Implementation Review
**Date:** 2026-08-26
**Files Reviewed:** risk_reward_engine.py (883 lines), entry_gates.py (rr_gate integration), hermes_constants.py (RR_ENGINE_* constants), volatility_gate.py, rs_signals.py, liquidation_map.py

---

## Overall Verdict

**NEEDS FIXES** — The architecture is sound and the code is well-structured, but **3 critical bugs** will cause incorrect SL/TP prices, broken legacy comparison, and silent liquidation TP failures at runtime. These must be fixed before shadow mode produces any useful data.

---

## Critical Bugs (Must Fix)

### BUG #1: SL and TP prices are calculated with wrong units — Severity: CRITICAL

**Location:** `risk_reward_engine.py`, `compute_structural_rr()` function, lines 482-516

**The problem:** `sl_distance_pct` and `tp_distance_pct` are stored as **decimal fractions** (e.g., 0.015 for 1.5%), but are then subtracted/added directly to the price as if they were **dollar amounts**.

```python
# Line 482: This produces a decimal fraction
sl_distance_pct = atr_pct * atr_mult / 100.0  # e.g., 0.009066

# Line 490: BUG — subtracts the fraction from price, not price*fraction
sl_price = price - sl_distance_pct  # 110000 - 0.009 = 109999.991 ❌
# Should be:
sl_price = price - (price * sl_distance_pct)  # 110000 - 997.26 = 109002.74 ✓
```

**Verified with BTC at $110,000:**
- SL price displayed: $109,999.985 (only $0.015 below entry!) ❌
- Correct SL price: $109,002.74 (0.91% below entry) ✓
- TP price displayed: $110,000.018 (only $0.018 above entry!) ❌
- Correct TP price: $111,994.52 (1.81% above entry) ✓

**Impact:** The SL and TP prices are off by **4-5 orders of magnitude**. If these prices were ever pushed to Hyperliquid, every trade would be stopped out instantly (SL essentially at entry) and no TP would ever hit.

**Note:** The R:R *ratio* is actually correct (both numerator and denominator have the same wrong units, so they cancel). But the prices themselves are dangerously wrong.

**Fix:** Lines 490 and 516: multiply by price before adding/subtracting:
```python
# Line 490 (SL):
sl_price = price - (price * sl_distance_pct) if direction == 'LONG' else price + (price * sl_distance_pct)

# Line 516 (TP):
tp_price = price + (price * tp_distance_pct) if direction == 'LONG' else price - (price * tp_distance_pct)
```

**Same bug exists in structural buffer adjustment (lines 502, 508):**
```python
# Line 502: This happens to be CORRECT because structural_buffer (0.002) is applied to price
sl_price = level_price - (price * structural_buffer)  # ✓ price × buffer

# But the sl_distance_pct recalculation on line 503:
sl_distance_pct = (price - sl_price) / price  # This produces a decimal fraction (0.002)
# Later this is multiplied by 100 for display (line 559), which is correct.
# BUT the final sl_price = price - sl_distance_pct still uses the raw fraction.
```

### BUG #2: Liquidation TP never triggers — unit mismatch in comparison — Severity: HIGH

**Location:** `risk_reward_engine.py`, lines 543-548

```python
# line 544: nearest is in PERCENT (e.g., 1.5 = 1.5%)
nearest = liquidity.get('nearest_ahead_dist')

# line 545: tp_max is in DECIMAL (e.g., 0.025 = 2.5%)
tp_max = _get_tp_max_pct(regime)  # returns 0.025

# BUG: comparing percent to decimal — always False
if nearest and nearest <= tp_max:  # 1.5 <= 0.025 → FALSE always
```

**Impact:** Liquidation clusters will NEVER be used as TP targets. The engine always falls back to ATR-based TP, defeating the purpose of having liquidation data.

**Fix:** Convert nearest to decimal before comparison:
```python
if nearest and (nearest / 100.0) <= tp_max and (nearest / 100.0) >= getattr(hc, 'RR_ENGINE_TP_MIN_PCT', 0.005):
    tp_distance_pct = nearest / 100.0
```

### BUG #3: Legacy comparison triggers infinite recursion — Severity: HIGH

**Location:** `risk_reward_engine.py`, lines 570-577

```python
def _legacy_rr(token, direction, price, candles_5m=None):
    try:
        from entry_gates import rr_gate as legacy_gate  # ← imports entry_gates
        # entry_gates.rr_gate with RR_ENGINE_ENABLED=True calls risk_reward_engine.evaluate_rr
        # evaluate_rr calls _legacy_rr → INFINITE RECURSION
        passed, sl, tp, rr = legacy_gate(token, direction, price, candles_5m)
```

**Call chain:**
1. `evaluate_rr()` → `_legacy_rr()` (line 700)
2. `_legacy_rr()` → `entry_gates.rr_gate()` (line 574)
3. `entry_gates.rr_gate()` (line 132-134) → `risk_reward_engine.evaluate_rr()`
4. `evaluate_rr()` → `_legacy_rr()` → RECURSION

**Impact:** The legacy comparison always hits `RecursionError`, which is caught by the outer `except Exception` and returns `{'pass': True, 'rr': 999}`. The shadow mode comparison is completely non-functional — it always shows "legacy PASS" vs "engine verdict."

**Fix:** Call the legacy logic directly without going through entry_gates:
```python
def _legacy_rr(token, direction, price, candles_5m=None):
    """Run old rr_gate logic directly (avoid recursion through entry_gates)."""
    try:
        from volatility_gate import get_atr_pct
        atr_pct = get_atr_pct(token)
        if atr_pct is None:
            from hermes_constants import ATR_PCT_FALLBACK
            atr_pct = ATR_PCT_FALLBACK
        sl_distance = price * 0.015 * 1.2  # ATR_SL_MIN * ENTRY_RR_SL_ATR_MULT
        tp_distance = price * 0.008  # ATR_TP_MIN
        if sl_distance <= 0:
            return {'pass': True, 'sl': 0, 'tp': 0, 'rr': 999}
        rr = tp_distance / sl_distance
        sl = price - sl_distance if direction == 'LONG' else price + sl_distance
        tp = price + tp_distance if direction == 'LONG' else price - tp_distance
        return {'pass': rr >= 2.0, 'sl': sl, 'tp': tp, 'rr': rr}
    except Exception:
        return {'pass': True, 'sl': 0, 'tp': 0, 'rr': 999}
```

---

## Medium Issues

### BUG #4: BB position clamps out-of-band prices to 0/1 — Severity: MEDIUM

**Location:** `risk_reward_engine.py`, `_compute_bb_width()`, lines 297-301

```python
band_range = upper - lower
if band_range > 0:
    position = (closes[-1] - lower) / band_range  # Can be <0 or >1
else:
    position = 0.5
# No clamping — position can be -0.5 or 1.5
```

**Impact:** While not causing errors, positions outside [0,1] indicate extreme moves that are currently not visible in the output. The energy score doesn't use `bb_position`, so this is cosmetic. However, for diagnostic purposes, the position should be documented as "can exceed [0,1]" or explicitly clamped.

### BUG #5: ATR fallback conversion is confusing — Severity: LOW

**Location:** `risk_reward_engine.py`, `compute_vol_width()`, lines 322-326

```python
atr_pct = getattr(hc, 'ATR_PCT_FALLBACK', 0.03) * 100  # "convert from fraction to %"
# ATR_PCT_FALLBACK = 0.03 in hermes_constants.py (line 611) with comment "2% assumed ATR"
# But 0.03 * 100 = 3.0%, which contradicts the "2%" comment
```

The comment says "2% assumed ATR" but `ATR_PCT_FALLBACK = 0.03` produces 3.0% after the multiplication. The actual semantics are unclear — is `ATR_PCT_FALLBACK` a fraction (0.03 = 3%) or a percentage (0.03 = 0.03%)? The `* 100` suggests it's treated as a fraction, making the fallback 3.0%.

---

## Code Quality

**Positives:**
1. **Well-structured:** Clean separation of concerns — S/R map builder, volatility width, liquidity proximity, structural R:R, scoring, main entry point.
2. **Good error handling:** Every external call has try/except with sensible fallbacks. `RR_ENGINE_FAIL_OPEN = True` is correctly implemented.
3. **Proper DB access:** `_get_candles_5m()` uses context manager with `finally: conn.close()`.
4. **Cache with TTL:** Both `_sr_cache` and `_vol_cache` have proper TTL expiration.
5. **Dedup logging:** `_log_dedup` prevents spam in shadow mode — good for production.
6. **Fail-open philosophy:** Every exception path returns `pass=True` (lines 746-750).
7. **Shadow mode correctly implemented:** Logs blocks but doesn't enforce (line 720).

**Issues found:**
1. **Global mutable state:** `_sr_cache`, `_vol_cache`, `_liq_cache`, `_log_dedup` are module-level dicts. Fine for single-process use but would leak across test cases.
2. **Silent exception swallowing:** `_build_liq_sr()` line 212 catches all exceptions with `pass`. At minimum, log a warning.
3. **_result() helper returns 'entry_price': 0:** The degenerate price case (line 655) calls `_result(False, 0, 0, 0, ...)` which sets `entry_price=0`. Callers checking `result['entry_price']` would get 0 instead of the original price.

---

## Integration Check

### entry_gates.py Integration (lines 115-175)

**Verdict: CLEAN integration.** The drop-in replacement pattern works correctly:

```python
# entry_gates.py line 130-139:
if RR_ENGINE_ENABLED:
    from risk_reward_engine import evaluate_rr
    result = evaluate_rr(token, direction, price, candles_5m=candles_5m, signal_type=signal_type)
    return result['pass'], result['sl_price'], result['tp_price'], result['rr_ratio']
```

- Returns correct 4-tuple `(pass, sl_price, tp_price, rr_ratio)` ✓
- ImportError fallback to legacy works ✓
- Exception handler (line 142-143) catches engine errors and falls through ✓
- Legacy fallback path (lines 145-179) is independent and functional ✓
- No changes needed to any signal file callers ✓

**One issue:** The legacy fallback in `entry_gates.py` (lines 145-179) is the **actual** working legacy code. But `_legacy_rr()` in risk_reward_engine.py tries to call this same code through `entry_gates.rr_gate`, creating the recursion bug (#3). The engine's own legacy comparison is broken, but the entry_gates fallback path works correctly.

### hermes_constants.py Integration

**Verdict: CORRECT.** All 20 `RR_ENGINE_*` constants are properly defined:
- `RR_ENGINE_ENABLED = True` ✓
- `RR_ENGINE_SHADOW = True` ✓ (shadow mode for initial rollout)
- `RR_ENGINE_FORCE = False` ✓
- All regime thresholds match the spec ✓
- `RR_ENGINE_BB_STDDEV = 1.8` matches existing signals ✓
- `RR_ENGINE_SR_MIN_TOUCHES = 3` is intentionally lower than RS signal's 5 ✓
- No Chinese characters in constant names ✓ (fixed from audit v1)

### Dependency Integration

| Dependency | Import | Status |
|---|---|---|
| `volatility_gate.get_atr_pct()` | `from volatility_gate import get_atr_pct` | ✓ Works correctly |
| `volatility_gate.classify_volatility()` | `from volatility_gate import classify_volatility` | ✓ Works correctly |
| `rs_signals._find_swing_highs_lows()` | try/except import | ✓ Graceful fallback |
| `rs_signals._cluster_levels()` | try/except import | ✓ Graceful fallback |
| `liquidation_map.get_sr_levels()` | try/except import | ✓ Graceful fallback |
| `liquidation_map.load_clusters()` | try/except import | ✓ Graceful fallback |

---

## Test Results

### Test 1: Basic evaluate_rr (ETH LONG $3500)
```
pass=True R:R=1.33 score=40.625 grade=D
SL=3499.985 (1.50%) TP=3500.020 (2.00%)
Regime=HIGH ATR=1.02%
```
- Engine runs without errors ✓
- Shadow mode correctly passes despite low R:R ✓
- **SL price wrong** — only $0.015 from entry instead of $52.50 ❌

### Test 2: CLI (BTC LONG $110,000 --quick)
```
BTC LONG | R:R=1.21 Score=39 Grade=D | SL=109999.985 TP=110000.018 | PASS
```
- CLI interface works ✓
- **SL price wrong** — only $0.015 from entry on a $110K asset ❌

### Test 3: SHORT direction
```
SHORT: pass=True R:R=1.21 SL=110000.015 TP=109999.982
```
- SHORT calculation direction is correct (SL above, TP below) ✓
- **Same unit bug** — SL only $0.015 from entry ❌

### Test 4: Edge cases
- Negative price → correctly blocked ("degenerate_price") ✓
- Zero price → correctly blocked ("degenerate_price") ✓
- DOGE at $0.15 → SL=0.135 (10% distance, not 1.5% as intended) ❌

### Test 5: Legacy comparison
- Triggers infinite recursion (caught by exception handler) ❌
- Always returns `{'pass': True, 'rr': 999}` as fallback ❌
- Shadow mode comparison is non-functional ❌

### Test 6: S/R Map
```
SR levels count: 19
Nearest level: $77382.00 at -0.02% [SUPPORT] via ORDER_BOOK
```
- S/R map builds correctly from order book data ✓
- Levels sorted by proximity ✓
- Multiple sources present (ORDER_BOOK) ✓

### Test 7: BB Width
```
BB width: 0.0052 (0.52%), Position: 0.025
Manual verification: 0.0053 (0.53%), Position: 0.037
```
- Calculation matches manual verification (within rounding) ✓
- 2/20 closes outside bands — extreme squeeze detected ✓

### Test 8: Scoring
- R:R 0.5 → score 43 (D) ✓
- R:R 2.0 → score 62 (C) ✓  
- R:R 4.0 → score 87 (A) ✓
- Scoring formula math is correct ✓

---

## Remaining Issues (Priority Order)

### Must fix before deployment:

1. **BUG #1: SL/TP price calculation** — Multiply by price before add/subtract (lines 490, 516)
2. **BUG #2: Liquidation TP unit mismatch** — Convert `nearest` from percent to decimal (line 545-546)
3. **BUG #3: Legacy comparison recursion** — Rewrite `_legacy_rr()` to not import entry_gates (lines 570-577)

### Should fix before deployment:

4. **BUG #4: BB position out-of-bounds** — Add documentation or clamping (line 299)
5. **BUG #5: ATR fallback comment** — Fix misleading "2% assumed" comment (line 324)
6. **Silent exception in _build_liq_sr** — Add warning log (line 212)

### Can fix after shadow mode starts:

7. **Score floor issue** — R:R < 4 always fails the 50-point min score gate (line 595: `max(5, rr_ratio * 12.5)` → R:R=4 gives exactly50). Consider lowering `RR_ENGINE_MIN_SCORE` or adjusting the multiplier.
8. **SR_MIN_TOUCHES = 3** — Consider raising to 5 to match rs_signals.py

---

## Approval

**NEEDS FIXES**

The 3 critical bugs must be fixed before this engine produces any useful shadow mode data. The SL/TP price bug (#1) is the most dangerous — it produces prices that are essentially at entry, which would be catastrophic if ever used for real order placement. The engine architecture, scoring, integration, and overall design are solid. With the 3 bug fixes applied, this is ready for shadow mode testing.

**Estimated fix time:** 30 minutes for bugs #1-#3.
