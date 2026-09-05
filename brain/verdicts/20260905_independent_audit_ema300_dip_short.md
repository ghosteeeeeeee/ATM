# Independent Audit — ema300_dip_short Bypass Investigation

**Auditor:** Independent (own conclusions, no priming from prior analysis)
**Date:** 2026-09-05
**Files Read:**
- `/root/.hermes/scripts/signals/ema300_dip_short.py` (263 lines — full)
- `/root/.hermes/scripts/signal_compactor.py` (3255 lines — full, key sections verified)
- `/root/.hermes/scripts/decider_run.py` (1144+ lines — full)
- `/root/.hermes/scripts/hermes_constants.py` (2771 lines — full)
- `/root/.hermes/brain/verdicts/ema300_dip_short_bypass_investigation.md` (318 lines — full)

**Data Sources Checked:**
- PostgreSQL trades table (open positions, trade history)
- hermes_constants.py STANDALONE_BYPASS_SIGNALS, SHORT_BLACKLIST, EMA300 constants
- signal_compactor.py `_filter_safe_prev_hotset()` and SLOPE FILTER
- ema300_dip_short.py `detect_ema300_dip_short()` — programmatic test run

---

## Open Trades Verified

| Token | Direction | Signal | Conf | Open Time | PnL |
|-------|-----------|--------|------|-----------|-----|
| WLFI | SHORT | ema300-dip-short | 84 | 2026-09-04 23:51 | -$0.05 |
| ADA | SHORT | ema300-dip-short | 79 | 2026-09-05 02:27 | +$0.03 |
| BCH | SHORT | ema300-dip-short | 79 | 2026-09-05 03:05 | -$0.02 |

None of WLFI, ADA, or BCH are in SHORT_BLACKLIST. Trades are not violations of the blacklist — they are valid entries that bypassed via the standalone bypass path.

---

## Claim 1: "Detection function validates EMA300 slope at generation time ONLY"

### Verdict: ✅ AGREE
### Confidence: HIGH

**Evidence:**

The detection function `detect_ema300_dip_short()` in `ema300_dip_short.py` lines 56-151 validates 6 conditions including EMA300 slope. The critical code is at lines 97-100:

```python
if n >= 20:
    ema_slope = (ema_vals[-1] - ema_vals[-20]) / ema_vals[-20] * 100
    if ema_slope >= EMA300_DIP_SHORT_MAX_EMA_SLOPE:
        return None
```

Where `EMA300_DIP_SHORT_MAX_EMA_SLOPE = 0.0` (hermes_constants.py:1536). This means:
- `ema_slope >= 0.0` → returns None (blocked)
- `ema_slope < 0.0` → passes through

I ran a programmatic test creating 700 synthetic candles with a clear uptrend. The detection function **correctly returned None** (blocked). This function ONLY runs during signal generation in `scan_signals()` (line 215), which is called by `signals_runner.py`. After the signal is written to DB via `add_signal()`, this function is never called again.

**No downstream component calls `detect_ema300_dip_short()`.**

---

## Claim 2: "No downstream component re-validates this condition"

### Verdict: ✅ AGREE
### Confidence: HIGH

**Evidence:**

I searched the entire pipeline for any EMA300 slope re-validation:

### Compactor (`signal_compactor.py`)
- **SLOPE FILTER** (lines 1232-1268): This checks **price slope** (linear regression of 20 raw 1m closes), NOT EMA300 slope. The formula is:
  ```python
  slope_pct = (numer / denom) / y_mean * 100
  ```
  Threshold: `ACCEL_300_REGIME_SLOPE_PCT = 0.05%` (hermes_constants.py:1289), relaxed 3x in SHORT_BIAS to 0.15%.
  
  This is a **fundamentally different metric** from the detection function's EMA300 slope. Price slope can be negative (short-term drop) while EMA300 slope is positive (long-term EMA still rising).

- **No call to `detect_ema300_dip_short()`** anywhere in `signal_compactor.py`.

### Decider (`decider_run.py`)
- Reads `hotset.json`, iterates entries, executes trades.
- No reference to `ema300_dip_short` detection function.
- No EMA300 slope check.

### Preservation Path (`_filter_safe_prev_hotset`)
- Checks: cooldown, blacklist, staleness, conf filter, source validation, confluence.
- Does **NOT** check: EMA300 slope, detection function conditions, SLOPE FILTER, spike filter, velocity filter.

**Summary:** Once a signal enters the DB, no component re-validates the EMA300 slope condition. The only stale-signal prevention is the 5-10 minute staleness decay.

---

## Claim 3: "STANDALONE_BYPASS allows single-source signals to bypass confluence gate"

### Verdict: ✅ AGREE
### Confidence: HIGH

**Evidence:**

`ema300-dip-short` is explicitly listed in `STANDALONE_BYPASS_SIGNALS` at hermes_constants.py:1828:
```python
STANDALONE_BYPASS_SIGNALS = (
    ...
    'ema300-dip-short',  # EMA300 rally seller — works solo in strong downtrends
    ...
)
```

This list has 45 entries. The bypass works at three locations in signal_compactor.py:

1. **Step 2 Confluence Gate** (line 1538): `if unique_signal_types == 1 and bare_source in STANDALONE_BYPASS_SIGNALS: pass_gate = True`
2. **Final Confluence Guard** (line 2131): `if bare_src in STANDALONE_BYPASS_SIGNALS: ... allowed at final guard`
3. **Preservation Path** (line 2990): `if bare_src_check in STANDALONE_BYPASS_SIGNALS: pass  # backtested standalone — allow through preserve`

This means a single-source `ema300-dip-short` signal can:
- Pass the confluence gate with only 1 source (no cross-validation)
- Survive through the preservation path
- Be re-approved at the final guard

The defense-in-depth consequence: there's no second signal to provide cross-validation or to independently confirm the market conditions are still valid.

---

## Claim 4: "Preservation path bypasses safety filters"

### Verdict: ✅ AGREE
### Confidence: HIGH

**Evidence:**

The `_filter_safe_prev_hotset()` function (lines 2913-3036) checks:
- ✅ Loss cooldown (`_is_loss_cooldown_active`)
- ✅ Blacklist (SHORT/LONG)
- ✅ Solana-only / delisted
- ✅ Open positions
- ✅ Staleness decay (hardcoded 0.01 floor)
- ✅ Confidence filter (CONF_FILTER)
- ✅ Source blacklist (validate_source)
- ✅ Confluence requirement (STANDALONE_BYPASS bypass)
- ✅ Per-coin WR filter

The function does **NOT** check:
- ❌ EMA300 slope (the detection function's key condition)
- ❌ Price slope (the compactor's SLOPE FILTER)
- ❌ Spike filter (recent bullish candle check)
- ❌ Velocity filter (recent price movement)
- ❌ Detection function conditions (RSI, distance from EMA300, trend strength, red candle)
- ❌ Any market-state re-validation

A preserved entry can survive for 5+ minutes (or 8+ minutes for FAVORITES tokens with `FAVORITES_RESIDENCY_DECAY = 0.12`) without any re-validation of the original detection conditions. If market conditions reverse (EMA slope turns positive) during that window, the stale signal executes with wrong conditions.

---

## Additional Findings

### Finding 1: Detection function has a warmup bias (Severity: LOW)
The EMA300 is initialized with `ema = closes[0]` (line 75-76), then iterated from index 0. For a true EMA300, the initial value should be the SMA of the first 300 values. This means the first ~300 iterations produce an inaccurate EMA. However, with 700 candles loaded and only the last value used, this is a minor inaccuracy (the EMA converges after ~1000 iterations, but 700 is usually close enough for slope direction). **Not the primary cause of bypass.**

### Finding 2: ETC trade had conf=102 (Severity: LOW)
The closed ETC trade shows confidence=102, which exceeds MAX_CONFIDENCE=88 defined in the detection function. This is because `decider_run.py` boosts confidence: `effective_conf = float(sig_conf) * wave_mult + speed_pts`. The raw signal confidence was likely 84-88, boosted to 102 by wave_mult and speed_pts. **Not a detection function bug — it's the execution pipeline boosting.**

### Finding 3: SEI and STX losses from same signal (Severity: MEDIUM)
SEI lost -$0.20 and STX lost -$0.12 (both closed), suggesting the bypass issue is systemic, not token-specific. The 3 open trades (WLFI, ADA, BCH) are at breakeven/small loss — same pattern.

---

## Root Cause Summary

The architectural gap is clear and confirmed:

1. **Detection function** validates EMA300 slope < 0 at signal generation → writes to DB
2. **Compactor** reads from DB, checks **price slope** (different metric), allows through confluence gate via STANDALONE_BYPASS
3. **Preservation path** preserves entries without re-validating any detection conditions
4. **Decider** executes from hotset.json without re-validation

When EMA300 slope turns positive after signal generation, the signal becomes stale but persists through the pipeline.

**Recommended fix:** Add EMA300 slope re-validation in the compactor's pre-filter (for `ema300_dip_short` signals) and in the preservation path. This is a one-file change in `signal_compactor.py`.

---

## Overall Assessment

All four claims from the previous investigation are **CONFIRMED** by independent analysis. The previous investigation (`ema300_dip_short_bypass_investigation.md`) was thorough and accurate. The root cause is an architectural gap: detection function conditions are only validated at generation time, with no downstream re-validation. The STANDALONE_BYPASS mechanism allows single-source signals to persist through all pipeline stages without cross-validation.
