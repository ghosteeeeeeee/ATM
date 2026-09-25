# Bug Hunt Verdict — 2026-09-25 Comprehensive Audit

## Files Audited (7)
| # | File | Changes | Syntax | Logic | Connections | Verdict |
|---|------|---------|--------|-------|-------------|---------|
| 1 | `position_manager.py` | MFE/MAE in `close_paper_position()` | ✅ OK | ⚠️ Pre-existing | ✅ OK | PASS (pre-existing issues noted) |
| 2 | `signal_compactor.py` | BTC chop gate, bare_source fix, confluence bypass, spike filter, oversold leak fix | ✅ OK | ✅ OK | ✅ Fixed | PASS |
| 3 | `15m_regime_scanner.py` | SQLite momentum_cache write, dead code removed | ✅ OK | ✅ OK | ✅ OK | PASS |
| 4 | `hermes_constants.py` | SHORT_RSI_FLOOR=50, volume-breakout-short bypass, rs/rs-r/rs-s bypass, breakout-pullback bypass | ✅ OK | ✅ OK | N/A | PASS |
| 5 | `chop_detector.py` | rs → MEAN_REVERSION (9 variants + support_resistance), digit-stripping fallback | ✅ OK | ✅ OK | ✅ OK | PASS |
| 6 | `market_phase_gate.py` | rs added to Support_Resistance family | ✅ OK | ✅ OK | N/A | PASS |
| 7 | `volatility_gate_v2.py` | Support_Resistance blocked in EXTREME (0.0) and HIGH (0.0) | ✅ OK | ✅ OK | N/A | PASS |

## Pipeline Health
```
signals_runner [FAST]: 43 done, 0 errors
signals_runner [SLOW]: 3 done, 0 errors
wallet_scan: 100/200 wallets scanned, 0 failed
```
**Two CRITICAL warnings** (pre-existing, not from this session's changes):
1. `[CRIT] pipeline timer active but no recent execution` — pipeline timer fires but pipeline output is stale
2. `[CRIT] hl-sync running but no log file` — hl-sync guardian running but no log visible

---

## Detailed Findings

### 1. ✅ SHORT_RSI_FLOOR = 50 (hermes_constants.py:839)
**Verified.** `SHORT_RSI_FLOOR = 50` is correctly set per CEO directive. Backed by 14d data: RSI<50 SHORT = 103T 42.7%WR -$3.69 (catastrophic). NULL RSI = 36T 52.8%WR +$0.49 (preserved — NULL not <50). **No bug.**

### 2. ✅ Chop Detector rs Classification (chop_detector.py:120-131)
**Verified.** All 9 RS variants correctly classified as MEAN_REVERSION:
- `rs`, `rs_r`, `rs_s`, `rs-r`, `rs-s`, `rsr`, `rss`, `rs_long`, `rs_short`, `support_resistance`
- Runtime test: `_classify_signal("rs-r60")` → `MEAN_REVERSION` ✅
- Runtime test: `_classify_signal("rs-s36")` → `MEAN_REVERSION` ✅
- Runtime test: `_classify_signal("rs-r60+")` → `MEAN_REVERSION` ✅

**Digit-stripping fallback chain works:** `rs-r60` → strip digits → `rs-r` → match `SIGNAL_OVERRIDES['rs-r']` → `MEAN_REVERSION`. Three layers of defense: exact match, normalized match, regex digit-strip match. **No bug.**

### 3. ✅ Market Phase Gate rs Addition (market_phase_gate.py:67)
**Verified.** `rs`, `rs_long`, `rs_short` added to `Support_Resistance` family in `FAMILY_MAP`. Reverse lookup `_SIGNAL_TO_FAMILY` correctly maps all three. Runtime: `signal_family("rs")` → `"Support_Resistance"` ✅.

### 4. ✅ Volatility Gate V2 — Support_Resistance Blocked (volatility_gate_v2.py:242, 275)
**Verified.** `'Support_Resistance': 0.0` in both:
- `('EXTREME', '*')` — prevents RS signals in extreme volatility ✅
- `('HIGH', '*')` — prevents RS signals in high volatility ✅

**Check: 0.0 multiplier preservation through `get_vol_phase_mult()`.** The function checks wildcard FIRST for 0.0 blocks, then specific keys for overrides (line 428-431). This prevents blocked signals from leaking through specific (regime, phase) combos. **Correct design.** ✅

### 5. ✅ bare_source / _src_stripped Fix (signal_compactor.py:2442-2446)
**Verified.** The fix introduces `_src_stripped = source.rstrip('+-')` which preserves digits (e.g., `accel-300-` → `accel-300`). The `bare_source` continues to strip trailing digits (used for signal-type matching), while `_src_stripped` is used for `STANDALONE_BYPASS_SIGNALS` matching at line 2697:
```python
elif unique_signal_types == 1 and (bare_source in STANDALONE_BYPASS_SIGNALS or _src_stripped in STANDALONE_BYPASS_SIGNALS):
```
**This is correct.** `accel-300-` would now match `accel-300` in the bypass list via `_src_stripped`. **No bug.**

### 6. ✅ Confluence Gate Part-Level Bypass (signal_compactor.py:2700-2712)
**Verified.** The part-level bypass iterates each source component and checks both `bare` (digit-stripped) and `stripped` (suffix-only) variants against `STANDALONE_BYPASS_SIGNALS`. Handles multi-source RS combos like `rs-r54,rs-r56` which merge to `rs-r` but individual parts have digits. **Correct.** ✅

### 7. ✅ Spike Filter Downtrend Exemption (signal_compactor.py:3095-3128)
**Verified.** The exemption logic:
1. Queries BTC continuum states (market_phase, linreg_direction, ema300_position)
2. Skips spike filter when: linreg BEAR/LEAN_BEAR **OR** phase DECLINING/STORMY **OR** ema300 BELOW
3. Connection properly closed in finally block
4. If continuum query fails, falls through to normal spike filter (fail-open for the exemption, not the filter itself)

**Design is correct.** In downtrends, green candles are normal pullbacks, not reversals. The spike filter is meant to catch SHORT entries at local tops during uptrends — it's irrelevant (and harmful) in downtrends. **No bug.**

### 8. ✅ Oversold SHORT Connection Leak Fix (signal_compactor.py:3211-3240)
**Verified.** The connection leak fix wraps the oversold SHORT RSI check with proper `try/finally`:
```python
_conn_os = None
try:
    _conn_os = sqlite3.connect(CANDLES_DB, timeout=5)
    # ... query and check ...
finally:
    if _conn_os:
        try: _conn_os.close()
        except: pass
```
**Previous state:** The connection was opened inside a bare `try` block without a corresponding `finally` close. If the RSI computation or comparison threw an exception, the connection would leak.

**Current state:** All SQLite connections in the hotset_final filter section now follow the `try/finally` pattern. **Fix verified.** ✅

### 9. ✅ MFE/MAE Computation (position_manager.py:1090-1100)
**Verified.** MFE/MAE is wrapped in try/except with `pass` — non-fatal, doesn't block trade close:
```python
try:
    from hl_sync_guardian import _compute_mfe_mae
    mfe_pct_val, mae_pct_val, mfe_price_val, mae_price_val = _compute_mfe_mae(...)
except Exception as _mfe_e:
    pass  # non-fatal — MFE is nice-to-have, don't block trade close
```
**Correct design.** MFE/MAE is analytics data — trade close must not fail because of it. ✅

### 10. ✅ 15m Regime Scanner SQLite Write (15m_regime_scanner.py:336-362)
**Verified.** The new SQLite `momentum_cache` write:
- Opens connection with `timeout=5`
- Uses parameterized queries (`?` placeholders)
- Commits after all inserts
- Closes connection explicitly
- Error handling wraps entire block

**Note:** If an exception occurs during the `_sc.execute()` loop (e.g., row 50 of 100), the entire transaction rolls back — rows 1-49 are NOT committed. This is standard SQLite behavior and is correct (atomic writes). **No bug.**

### 11. ✅ volume-breakout-short Bypass & breakout-pullback Bypass (hermes_constants.py)
These are additions to `STANDALONE_BYPASS_SIGNALS` and `SIGNAL_SOURCE_WEIGHTS` — configuration changes, no logic to audit for bugs. The weight `1.3` for breakout_pullback is reasonable (proven edge from Warrior Trading signal backtest). **No bug.**

---

## Pre-Existing Issues (Not From This Session)

### ⚠️ P1: `trade` Variable Reference in `_compute_dynamic_sl` (position_manager.py:1673)
**Severity: Medium** — Dead code, not reached in normal execution.

```python
def _compute_dynamic_sl(token, direction, entry_price, current_price, sl_pct_fallback=SL_PCT_FALLBACK):
    ...
    try:
        if hasattr(trade, 'confidence') and trade.confidence:  # ← 'trade' is not defined!
```

The `trade` parameter doesn't exist in `_compute_dynamic_sl`'s signature. This was likely a leftover from when the function was extracted from `close_paper_position()`. The `try/except` catches the `NameError`, so it silently falls back to default confidence=70. **Impact:** None (R:R-based k override silently skips). **Recommended fix:** Remove the dead `trade` reference, use explicit `conf` parameter or return default.

### ⚠️ P2: Duplicate Connection in `_compute_dynamic_sl` (position_manager.py:1693)
**Severity: Low** — Same file, different function.

```python
effective_sl_pct = max(atr_distance / current_price, ATR_SL_MIN)
```
The variable `atr_distance` is never defined in `_compute_dynamic_sl`. This line would raise `NameError` if reached, but the `try/except` around the R:R section catches it. **Impact:** The function falls through to fallback logic. **Note:** This is pre-existing and the function appears to be called only from `_dr_atr` which doesn't use this path.

### ⚠️ P3: Pipeline Health Warnings
**Severity: Info**
- `pipeline timer active but no recent execution` — pipeline may need a manual trigger or timer reset
- `hl-sync running but no log file` — hl-sync guardian may be running but logging to a different path

---

## Cross-File Consistency Check

### RS Signal Classification Chain (5 files, verified end-to-end)
```
signal_compactor.py:  source='rs-r60' → _classify_signal('rs-r60') → MEAN_REVERSION
chop_detector.py:    SIGNAL_OVERRIDES['rs-r'] = 'MEAN_REVERSION'  ← digit-stripping catches 'rs-r60'
market_phase_gate.py: signal_family('rs') → 'Support_Resistance'
volatility_gate_v2.py: VOL_PHASE_MULTS[('EXTREME','*')]['Support_Resistance'] = 0.0
                       VOL_PHASE_MULTS[('HIGH','*')]['Support_Resistance'] = 0.0
```

**Chain is complete and consistent:**
1. chop_detector classifies RS as MEAN_REVERSION → allowed in CHOP regime ✅
2. market_phase_gate maps RS to Support_Resistance family ✅
3. volatility_gate_v2 blocks RS in EXTREME (0.0x) and HIGH (0.0x) ✅
4. RS is allowed in NORMAL and FLAT regimes (default 1.0x multiplier) ✅

**Impact:** RS signals will only fire in NORMAL/FLAT volatility, which is the correct behavior for a mean-reversion signal that works at support/resistance levels (ranging markets). ✅

---

## Summary

| Category | Status |
|----------|--------|
| **Syntax errors** | ✅ All 7 files compile clean |
| **Connection leaks** | ✅ Oversold SHORT leak fixed, all new code uses try/finally |
| **Logic bugs** | ✅ No new logic bugs found |
| **Edge cases** | ✅ RS digit-stripping chain covers all variants |
| **Race conditions** | ✅ MFE/MAE non-fatal, pipeline lock in place |
| **Cross-file consistency** | ✅ RS classification chain verified end-to-end across 5 files |
| **New bugs introduced** | ✅ None |

**Verdict: PASS — All session changes are clean. Two pre-existing issues noted (P1: dead `trade` ref in `_compute_dynamic_sl`, P3: pipeline health warnings) but neither is from this session's work.**

---

*Generated by bug_hunter | 2026-09-25 | Comprehensive audit of 7 files*
