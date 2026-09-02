# R:R Engine Bug Hunt Report

**Date:** 2026-09-02
**Files analyzed:**
- `scripts/risk_reward_engine.py` (963 lines, NEW)
- `scripts/entry_gates.py` lines 115-182 (rr_gate upgrade)
- `scripts/signal_compactor.py` lines 741-1031 (_score_signal, RR integration)
- `scripts/hermes_constants.py` lines 2384-2443 (RR_ENGINE_* constants)

---

## CRITICAL Bugs

### Bug #1: Fail-Open Results Get 1.30x Confidence BOOST (Wrong Direction)
- **File:** `scripts/risk_reward_engine.py` lines 923-957
- **What:** When `evaluate_rr()` hits an exception with `RR_ENGINE_FAIL_OPEN=True`, it returns `{'pass': True, 'rr_ratio': 999, 'score': 0, 'grade': 'A'}`. The `rr_confidence_multiplier()` receives this result and evaluates:
  - `grade == 'F'`? No → skip
  - `rr < 1.0`? No (999) → skip
  - `result['pass'] == False`? No (True) → skip
  - `rr >= 4.0 and grade == 'A'`? **YES** → returns `mult=1.30`
- **Impact:** WRONG BEHAVIOR — every time the engine fails to load data (missing candles, DB errors, import failures), the signal gets a **130% confidence boost** instead of neutral (1.0). This is the exact opposite of fail-open intent. The engine failing should not make trades MORE confident.
- **Severity:** CRITICAL — directly inflates scores for signals where the engine couldn't assess risk, potentially pushing bad trades through the hotset.
- **Fix:** Add a fail-open check before the graded multiplier logic:
  ```python
  # Detect fail-open result (rr=999 with score=0 is the fail-open signature)
  if rr >= 999 and score == 0:
      return 1.0, f"RR FAIL-OPEN: engine could not evaluate (no data)"
  ```
  Or better: have `evaluate_rr()` set a flag like `'fail_open': True` in its result dict.

### Bug #2: Dead `else: parser.print_help()` at Module Level
- **File:** `scripts/risk_reward_engine.py` lines 962-963
- **What:** The `rr_confidence_multiplier()` function ends with:
  ```python
  except Exception as e:
      return 1.0, f"RR ENGINE ERROR (fail-open): {e}"
  else:
      parser.print_help()
  ```
  This `else` is attached to the function's `try/except`. The `try` block always returns (either normal path or hard-block returns), so the `else` is dead code. However, `parser` is only defined in `__main__` scope (line 805). If this `else` ever executed (e.g., future code refactor removes a return), it would crash with `NameError: name 'parser' is not defined`.
- **Impact:** DEAD CODE that would crash if ever reached. Copy-paste residue from the CLI block.
- **Severity:** HIGH — latent crash. Currently harmless but will bite during any refactor that touches the try block's return paths.
- **Fix:** Delete lines 962-963 entirely.

---

## HIGH Severity Bugs

### Bug #3: SQLite Connection Leak in signal_compactor.py (No finally Block)
- **File:** `scripts/signal_compactor.py` lines 998-1015
- **What:** The RR engine integration opens a SQLite connection to get the latest price:
  ```python
  _rr_conn = _sq3.connect(..., timeout=5)
  _rr_cur = _rr_conn.cursor()
  _rr_cur.execute(...)
  _rr_row = _rr_cur.fetchone()
  _rr_cur.close(); _rr_conn.close()
  ```
  If `execute()` or `fetchone()` throws, the `close()` calls on line 1011 are never reached. The outer `except Exception: pass` on line 1014 swallows the error but does NOT close the connection.
- **Impact:** CONNECTION LEAK — each failure leaks one SQLite connection. Since `_score_signal()` runs for every signal in every compaction cycle (every few minutes), repeated failures accumulate leaked connections. SQLite connections hold file locks, and under Python's GC this eventually causes `"database is locked"` errors in other parts of the pipeline.
- **Severity:** HIGH — known pattern that has caused pipeline failures before (per AGENTS.md: "SQLite leaks = database locked").
- **Fix:** Wrap in `finally`:
  ```python
  _rr_conn = None
  try:
      _rr_conn = _sq3.connect(..., timeout=5)
      _rr_cur = _rr_conn.cursor()
      _rr_cur.execute(...)
      _rr_row = _rr_cur.fetchone()
      if _rr_row:
          _rr_price = _rr_row[0]
  except Exception:
      pass
  finally:
      if _rr_conn:
          _rr_conn.close()
  ```

### Bug #4: Hardcoded Multiplier Constants (Constants Exist But Are Never Used)
- **File:** `scripts/risk_reward_engine.py` lines 940-955
- **What:** `rr_confidence_multiplier()` hardcodes all multiplier values:
  ```python
  if rr >= 4.0 and grade == 'A':
      mult = 1.30
  elif rr >= 3.0 and grade in ('A', 'B'):
      mult = 1.15
  elif rr >= 2.0:
      mult = 1.00
  elif rr >= 1.5:
      mult = 0.85
  else:
      mult = 0.70
  ```
  Meanwhile, `hermes_constants.py` defines 10 `RR_ENGINE_CONF_*` constants (lines 2436-2443) that are NEVER referenced:
  - `RR_ENGINE_CONF_HARD_BLOCK_RR = 1.0`
  - `RR_ENGINE_CONF_BOOST_MULT = 1.30`
  - `RR_ENGINE_CONF_STRONG_MULT = 1.15`
  - `RR_ENGINE_CONF_NEUTRAL_MULT = 1.00`
  - `RR_ENGINE_CONF_MEDIOCRE_MULT = 0.85`
  - `RR_ENGINE_CONF_POOR_MULT = 0.70`
- **Impact:** WRONG BEHAVIOR on config change — anyone modifying these constants (as directed by the "No hardcoded constants" rule in AGENTS.md) will think they've changed the behavior, but the code ignores them entirely. The constants are dead code.
- **Severity:** HIGH — violates the project's own coding standard. Any tuning attempt will silently fail.
- **Fix:** Replace hardcoded values with constant lookups:
  ```python
  if rr >= getattr(hc, 'RR_ENGINE_CONF_BOOST_THRESHOLD_RR', 4.0) and grade == 'A':
      mult = getattr(hc, 'RR_ENGINE_CONF_BOOST_MULT', 1.30)
  ```

### Bug #5: Hard Block Threshold Constants Also Unused
- **File:** `scripts/risk_reward_engine.py` lines 931-938
- **What:** Same issue as Bug #4 but for the hard block thresholds:
  ```python
  if grade == 'F':
      return 0.0, f"..."
  if rr < 1.0:
      return 0.0, f"..."
  if not result['pass'] and result.get('block_reason', '').startswith('Score'):
      return 0.0, f"..."
  ```
  Constants `RR_ENGINE_CONF_HARD_BLOCK_RR = 1.0` and `RR_ENGINE_CONF_HARD_BLOCK_SCORE = 35` are defined but never referenced. The hard-block RR threshold (1.0) and score threshold (35) are hardcoded.
- **Impact:** Same as Bug #4 — tuning constants has no effect.
- **Severity:** HIGH — duplicates Bug #4 in scope.
- **Fix:** Use the constants: `if rr < getattr(hc, 'RR_ENGINE_CONF_HARD_BLOCK_RR', 1.0):`

---

## MEDIUM Severity Bugs

### Bug #6: Swing Detection Window Mismatch (Silent Empty Results)
- **File:** `scripts/risk_reward_engine.py` lines 113 vs 119
- **What:** `_build_candle_sr()` checks `len(candles_5m) < 30` before proceeding, but calls `_find_swing_highs_lows(use_candles, window=20)` which requires `n >= window * 2 + 1 = 41` candles. If there are 30-40 candles, the function passes the guard check but the swing detection returns empty (no crash, just no S/R levels). No logging or warning.
- **Impact:** EDGE CASE — for newer tokens or tokens with sparse candle data, the S/R map silently returns empty, causing the score to lose 25 pts (S/R clarity = 0). This could cause borderline signals to fail the min_score gate when they shouldn't.
- **Severity:** MEDIUM — silent quality degradation for data-sparse tokens.
- **Fix:** Change the guard to `len(candles_5m) < 41` or `len(candles_5m) < (window * 2 + 1)` using the actual window parameter.

### Bug #7: Dead Variables `_liq_cache` and `_liq_cache_ts`
- **File:** `scripts/risk_reward_engine.py` lines 57-58
- **What:** Two module-level variables are declared but never read or written anywhere:
  ```python
  _liq_cache = None  # global liquidation data (refreshed per call)
  _liq_cache_ts = 0
  ```
- **Impact:** COSMETIC — dead code. Suggests the author intended to cache liquidation data globally but never implemented it.
- **Severity:** LOW (cosmetic, but the comment "refreshed per call" is misleading since it's never refreshed at all).
- **Fix:** Delete lines 57-58 or implement the intended caching.

### Bug #8: Dead Variable `atr_pct` in `_legacy_rr()`
- **File:** `scripts/risk_reward_engine.py` lines 578-580
- **What:** `atr_pct` is computed but never used:
  ```python
  atr_pct = get_atr_pct(token)
  if atr_pct is None:
      atr_pct = getattr(hc, 'ATR_PCT_FALLBACK', 0.03) * 100
  # atr_pct is never referenced after this point
  ```
  The legacy R:R calculation uses `ATR_SL_MIN` and `ATR_TP_MIN` directly, not `atr_pct`.
- **Impact:** COSMETIC — dead code. The function also makes a wasted DB call to `get_atr_pct()`.
- **Severity:** LOW — unnecessary DB query per call.
- **Fix:** Remove the `atr_pct` computation.

### Bug #9: Dead Import `_build_level_touches`
- **File:** `scripts/risk_reward_engine.py` line 42
- **What:** `_build_level_touches` is imported from `rs_signals` but never called anywhere in the file.
- **Impact:** COSMETIC — unused import.
- **Severity:** LOW.
- **Fix:** Remove from import statement.

### Bug #10: Dead Import `evaluate_rr` in signal_compactor.py
- **File:** `scripts/signal_compactor.py` line 995
- **What:** `evaluate_rr` is imported alongside `rr_confidence_multiplier` but only `rr_confidence_multiplier` is used in signal_compactor.
- **Impact:** COSMETIC — unused import.
- **Severity:** LOW.
- **Fix:** Remove `evaluate_rr` from the import.

### Bug #11: `_compute_score` S/R Clarity Not Direction-Aware
- **File:** `scripts/risk_reward_engine.py` lines 625-636
- **What:** The S/R clarity scoring checks the nearest level by absolute `distance_pct` regardless of direction:
  ```python
  nearest_dist = sr_map[0].get('distance_pct', 999)
  if 0.3 < nearest_dist < 2.0:
      score += 25
  ```
  But `sr_map` is sorted by absolute proximity, so `sr_map[0]` could be a support level for a LONG trade (which is irrelevant for the TP target). The 25 pts would be awarded for having a nearby support, when what matters for a LONG is having a nearby resistance (TP target).
- **Impact:** WRONG BEHAVIOR — score could be inflated by irrelevant S/R levels in the opposite direction.
- **Severity:** MEDIUM — could push borderline signals through the min_score gate.
- **Fix:** Filter `sr_map` by trade direction before scoring:
  ```python
  direction_levels = [l for l in sr_map if (direction == 'LONG' and l['type'] == 'resistance') or (direction == 'SHORT' and l['type'] == 'support')]
  if direction_levels:
      nearest_dist = direction_levels[0].get('distance_pct', 999)
  ```

---

## LOW Severity / Edge Cases

### Bug #12: `compute_liquidity_proximity` and `compute_structural_rr` Are Case-Sensitive on Direction
- **File:** `scripts/risk_reward_engine.py` lines 389, 490, 499, 516, 525, 533
- **What:** These functions compare `direction == 'LONG'` without uppercasing. The main entry point `evaluate_rr()` uppercases direction (line 676), so the primary path is safe. But if someone calls these functions directly with lowercase direction (e.g., `'long'`), all LONG trades would be treated as SHORT (falling into the `else` branch).
- **Impact:** EDGE CASE — safe through the primary path but fragile for direct callers.
- **Severity:** LOW.
- **Fix:** Add `direction = direction.upper()` at the top of each function, or document the uppercase requirement.

### Bug #13: `_build_liq_sr` Silently Swallows All Exceptions
- **File:** `scripts/risk_reward_engine.py` lines 212-213
- **What:** The liquidation cluster loading is wrapped in a bare `except Exception: pass`, hiding any data format issues, missing keys, or type errors.
- **Impact:** EDGE CASE — if the liquidation data format changes (e.g., `price` field becomes a string), errors would be silently swallowed and the function would return partial/empty results with no logging.
- **Severity:** LOW.
- **Fix:** Add logging: `except Exception as e: _log(f"WARN: liq SR failed for {token}: {e}")`

### Bug #14: Unbounded Module-Level Cache Growth
- **File:** `scripts/risk_reward_engine.py` lines 55-56
- **What:** `_sr_cache` and `_vol_cache` dicts grow without bound. Tokens are added but never evicted (entries expire by TTL check, but the dict entries remain forever).
- **Impact:** EDGE CASE — for the current ~25 tradeable tokens, this is negligible. But in a hypothetical scenario with hundreds of tokens, it would be a slow memory leak.
- **Severity:** LOW — bounded by token universe size.
- **Fix:** Optional: add periodic eviction or use `functools.lru_cache`.

### Bug #15: `ATR_PCT_FALLBACK` Documentation Says "2%" But Value Is 0.03 (3%)
- **File:** `scripts/hermes_constants.py` line 674
- **What:** Comment says `# 2% assumed ATR` but value is `0.03` which converts to 3% in usage. Furthermore, the effective fallback in `compute_vol_width` is 0.75% (capped), making both the comment and the intermediate value misleading.
- **Impact:** COSMETIC — documentation mismatch. Could confuse future tuning.
- **Severity:** LOW.
- **Fix:** Update comment to reflect actual behavior: `# 0.75% effective ATR fallback (capped in compute_vol_width)`

### Bug #16: Inconsistent Score/Grade in Fail-Open Result
- **File:** `scripts/risk_reward_engine.py` line 766
- **What:** `_result(True, 999, 0, 0, 0, 'A', None, f'fail-open: {e}')` returns `score=0` with `grade='A'`. Grade A requires score >= 80 per the grading scale.
- **Impact:** COSMETIC — downstream code checking `score` vs `grade` consistency would be confused. Notes string says "fail-open" which clarifies intent.
- **Severity:** LOW.
- **Fix:** Use consistent values: `score=100, grade='A'` for fail-open, or add a separate `'fail_open': True` flag.

---

## Performance Issues

### Issue #17: Redundant SQLite Connection for Price Fetch in signal_compactor
- **File:** `scripts/signal_compactor.py` lines 998-1011
- **What:** `_score_signal()` opens a brand new SQLite connection to `candles.db` just to get the latest close price for the RR engine. But `run_compaction()` already has the signal data which likely includes price information, or could batch-query prices for all tokens at once.
- **Impact:** PERFORMANCE — one extra DB connection per signal per compaction cycle. With 10+ signals per cycle, that's 10+ separate DB connections for the same table.
- **Severity:** LOW.
- **Fix:** Batch-query all needed prices once before the scoring loop.

---

## Summary

| Severity | Count | Key Issues |
|----------|-------|------------|
| CRITICAL | 2 | Fail-open gets 1.30x boost; Dead `parser.print_help()` crash |
| HIGH | 3 | Connection leak; Hardcoded constants ignore hermes_constants |
| MEDIUM | 3 | Window mismatch; Direction-unaware S/R scoring; Dead variables |
| LOW | 7 | Case sensitivity; Exception swallowing; Cache growth; Doc mismatch |

**Top 3 priorities to fix:**
1. **Bug #1** (CRITICAL): Fail-open → 1.30x boost — directly inflates scores on engine failures
2. **Bug #2** (CRITICAL): Dead `else: parser.print_help()` — latent NameError crash
3. **Bug #3** (HIGH): SQLite connection leak in signal_compactor — pipeline stability risk

---

*Bug hunt performed by: bug_hunter subagent*
*Methodology: Full read of all 4 changed files, cross-referenced with dependency modules (rs_signals.py, liquidation_map.py, volatility_gate.py, hermes_constants.py)*
