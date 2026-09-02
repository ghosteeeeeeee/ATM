# Independent Verdict: accel_300_v3_long

**Auditor:** Independent auditor (own conclusions, no priming)
**Date:** 2026-09-01
**Files reviewed:** v3 signal, v2 signal, hermes_constants.py, signals/__init__.py, signal_schema.py, signal_compactor.py, volatility_gate.py
**DB queried:** signals_hermes_runtime.db (signal_outcomes table)

---

## Claim 1: v3 fixes the "local-top entry problem" of v2

**Verdict: PARTIAL — Thesis is sound, but unproven in live data**

**Evidence:**
- v2 long has 24 trades: 10 wins (41.7% WR), 14 losses, avg PnL **-$0.0156/trade**, total **-$0.37**
- v2 losses cluster around -0.8% to -1.1% (stop-loss hits), wins vary from +0.08% to +3.12%
- v2 enters when gap is ACCELERATING (widening), which catches spikes at local tops
- v3 requires: gap narrowed from peak (pullback happened) → gap re-expanding (bounce confirmed)
- v2 long is now DISABLED (`ACCEL_300_V2_LONG_ENABLED = False`), v3 is ENABLED — v3 replaces v2
- **Critical:** v3 has 0 trades in the database — no live validation yet
- The design change from "enter on acceleration" to "enter on pullback bounce" is logically sound for avoiding local tops
- **Risk:** Pullback detection depends on `GAP_PEAK_WINDOW=20` bars. If the peak is older than 20 bars, the pullback won't be detected, and the signal won't fire (potentially missing trades)

**Confidence: MEDIUM** — Design is sound but zero live evidence

---

## Claim 2: v3 has 20 tunable constants in hermes_constants.py

**Verdict: PARTIAL — 22 total, not 20**

**Evidence:**
- Counted all `ACCEL_300_V3_LONG_*` constants in hermes_constants.py: **22 total**
- 18 are imported and used directly in the signal's detection logic + scanner
- 3 are confidence calibration (CONF_BASE=72, CONF_FLOOR=60, CONF_CAP=88) — used in scanner, not imported by the signal file itself (hardcoded as 72/60/88 at lines 527-530)
- 1 is ENABLED toggle (not a "tunable" parameter)
- **Issue:** The confidence constants (CONF_BASE, CONF_FLOOR, CONF_CAP) exist in hermes_constants.py but are **NOT imported or used** by the signal. The signal hardcodes `72`, `60`, and `88` directly (lines 527-530). This violates the "no hardcoded constants" convention and means changing the constants in hermes_constants.py would have NO effect on the signal.

**Confidence: HIGH** — Counted and verified; the unused confidence constants are a real issue

---

## Claim 3: v3 is registered as a fast signal

**Verdict: AGREE**

**Evidence:**
- `signals/__init__.py` line 170: `{'name': 'accel_300_v3_long', 'enabled': ACCEL_300_V3_LONG_ENABLED, 'run': _accel_300_v3_long_run}`
- `_SLOW_SIGNALS = {'macd_divergence', 'signal_confluence', 'ichimoku_cloud'}` — v3 is NOT in this set
- Verified via `get_fast_signals()`: `accel_300_v3_long` is present in the 16 fast signals
- v3 scans every 1 minute via signals_runner

**Confidence: HIGH**

---

## Claim 4: v3 passes all syntax checks

**Verdict: AGREE**

**Evidence:**
- `ast.parse()` of the full v3 source: PASS
- `import signals.accel_300_v3_long as m`: PASS — imports without error
- All 18 imported constants from hermes_constants resolve correctly
- `detect_accel_300_v3_long` callable: YES
- `scan_accel_300_v3_long_signals` callable: YES
- `run` entry point: YES

**Confidence: HIGH**

---

## Claim 5: bug_hunter found and fixed a NameError in is_component_disabled()

**Verdict: PARTIAL — The v3 NameError was fixed, but a DIFFERENT NameError was introduced/left unfixed**

**Evidence:**
- Git diff confirms `ACCEL_300_V3_LONG_ENABLED` was added to the import block in `is_component_disabled()` (line 2137) and to the function body (lines 2336-2337). This fix is correct.
- **UNFIXED BUG:** `ACCEL_300_V2_LONG_5M_ENABLED` is used at lines 2333-2334 but is **NOT imported** in the function's import block (lines 2083-2138). This causes a **NameError** when calling `is_component_disabled('accel-300-v2-long-5m+')`:
  ```
  NameError: name 'ACCEL_300_V2_LONG_5M_ENABLED' is not defined
  ```
- This is a **pre-existing bug** (existed before the v3 commit), NOT introduced by v3
- The v3 fix correctly added the import for `ACCEL_300_V3_LONG_ENABLED` but did NOT fix the missing `ACCEL_300_V2_LONG_5M_ENABLED` import
- **Impact:** `is_component_disabled()` crashes for 5m variant components. However, `add_signal()` handles this separately via local imports, so signals still work. The crash only affects `is_component_disabled()` callers (like signal_compactor's preserved-entry guard).

**Confidence: HIGH** — Reproduced the NameError; confirmed pre-existing

---

## Additional Findings

### BUG: NameError in is_component_disabled() for accel-300-v2-long-5m
- **Severity: MEDIUM** — Pre-existing bug, not introduced by v3
- `ACCEL_300_V2_LONG_5M_ENABLED` is missing from the import block at line 2083-2138
- Any call to `is_component_disabled('accel-300-v2-long-5m+')` crashes with NameError
- Fix: Add `ACCEL_300_V2_LONG_5M_ENABLED` to the import block

### ISSUE: Unused variable `price_epsilon`
- Line 326: `price_epsilon = max(abs(closes[latest_idx]) * 1e-12, 1e-12)` — defined but never used
- v2 uses this variable (line 349: `if price_velocity <= -price_epsilon`), but v3 doesn't
- v3 uses `if price_velocity <= 0` instead
- **Severity: LOW** — Dead code, no functional impact

### ISSUE: Hardcoded magic numbers in signal file
- Lines 400, 408: `-0.15` gap velocity threshold — hardcoded, not in hermes_constants.py
- Line 322: `velocity_window = 5` — hardcoded local variable, not a constant
- Line 337: `6` in green_count loop range — hardcoded
- Lines 520-530: Confidence calculation uses hardcoded `20`, `15`, `10`, `5`, `8`, `45`, `65`, `88`, `72`, `60`
- **Note:** v2 has the same `-0.15` issue (lines 396-397, 405). This is inherited, not new.
- **Severity: MEDIUM** — Violates project convention: "All thresholds, periods, and tunable parameters MUST go in hermes_constants.py"

### ISSUE: Unused confidence constants
- `ACCEL_300_V3_LONG_CONF_BASE = 72`, `CONF_FLOOR = 60`, `CONF_CAP = 88` exist in hermes_constants.py
- The signal hardcodes these same values (lines 527-530) instead of importing them
- Changing the constants in hermes_constants.py would have NO effect
- **Severity: MEDIUM** — False sense of tunability

### ISSUE: None price handling
- `detect_accel_300_v3_long` crashes with `TypeError` if any price is None (line 271)
- v2 has the same issue — neither handles None gracefully
- **Note:** The `_get_1m_prices` function filters from DB, so None prices should never arrive in practice
- **Severity: LOW** — Defensive coding issue, not a practical bug

### VERIFICATION: Integration points all correct
- `signal_compactor.py`: Source weight key `('accel_300_v3_long', 'accel-300-v3-long+')` matches v3's SOURCE constant ✓
- `signal_schema.py` Layer 2: Correctly checks `ACCEL_300_V3_LONG_ENABLED` for `accel-300-v3-long+`, `-`, and bare variants ✓
- `is_component_disabled()`: Handles v3 components correctly ✓
- `volatility_gate.py`: v3 is in NORMAL, HIGH, EXTREME regimes (not FLAT) — appropriate for pullback entries ✓
- `hermes_constants.py` PROFIT_MONSTER_BYPASS: v3 included (manages via ATR SL, not PM Trail) ✓
- `hermes_constants.py` STANDALONE_BYPASS: v3 included (works solo) ✓
- Registry: v3 is registered and enabled ✓

### DATA ANALYSIS: v2 long trade outcomes
| Metric | Value |
|--------|-------|
| Total trades | 24 |
| Wins | 10 (41.7%) |
| Losses | 14 (58.3%) |
| Avg PnL | -$0.0156/trade |
| Total PnL | -$0.37 |
| Worst loss | NOT: -1.62% |
| Best win | CRV: +3.12% |
| Loss pattern | Consistent -0.8% to -1.1% (stop-loss hits) |
| Win pattern | Variable +0.08% to +3.12% |

The v2 data confirms the local-top problem: losses are uniform (stop-loss triggered after entering at spike peak), while wins are variable (only succeed when trend continues after entry). v3's pullback requirement is designed to address exactly this pattern.

---

## Summary Table

| # | Claim | Verdict | Confidence |
|---|-------|---------|------------|
| 1 | v3 fixes local-top entry problem | **PARTIAL** (sound thesis, zero live evidence) | MEDIUM |
| 2 | 20 tunable constants | **PARTIAL** (22 total, 3 unused/confidence not wired) | HIGH |
| 3 | Registered as fast signal | **AGREE** | HIGH |
| 4 | Passes syntax checks | **AGREE** | HIGH |
| 5 | bug_hunter fixed NameError | **PARTIAL** (v3 NameError fixed, different 5m NameError unfixed) | HIGH |

## Action Items

1. **FIX:** Add `ACCEL_300_V2_LONG_5M_ENABLED` to the import block in `is_component_disabled()` (line ~2083-2138)
2. **FIX:** Wire up confidence constants (CONF_BASE, CONF_FLOOR, CONF_CAP) — either import and use them in the signal, or remove them from hermes_constants.py
3. **FIX:** Move hardcoded `-0.15` gap velocity thresholds to hermes_constants.py
4. **CLEANUP:** Remove unused `price_epsilon` variable (line 326)
5. **CLEANUP:** Move `velocity_window = 5` to a constant in hermes_constants.py
6. **MONITOR:** v3 has zero live trades — monitor first 20+ trades before drawing performance conclusions
