# Bug Hunter: grind-breakout-v2 Verification

## Verdict: SAFE

No HIGH-severity issues. No SQL injection, no connection leaks, no division-by-zero, no off-by-one errors. All 23 synthetic edge-case tests + live-data run passed. One MEDIUM logic quirk (MACD histogram comparison is mathematically degenerate) affects only a +2 confidence bonus, never a filter. Ship it; optionally clean up the MEDIUM/LOW items later.

## Issues Found

### MEDIUM — MACD "histogram rising" check is degenerate (bonus-only impact)
`_get_macd_hist` computes `hist_prev = macd_line[-2] - signal_line` using the **final** signal-line value instead of the signal value at the previous bar. Therefore `hist_now > hist_prev` ⟺ `macd_line[-1] > macd_line[-2]` — the signal line cancels exactly. The check that claims "MACD histogram rising" is actually "MACD line rising". Verified numerically: `hist_now - hist_prev == macd_line[-1] - macd_line[-2]` to 1e-12 on a 50-close test series.
- **Impact:** limited to `GRIND_BREAKOUT_V2_CONF_MACD_BONUS` (+2 confidence). It is NOT a hard filter (correctly bonus-only per spec), so no signal is wrongly blocked or allowed because of this.
- **Fix (optional):** track the signal EMA incrementally so `hist_prev` uses the signal value as of bar `-2`.

### LOW — Nonstandard MACD EMA seeding (related to above)
Each MACD point is computed from an independently seeded EMA over `closes[max(0,i-35):i]` rather than one continuous EMA chain. Values are an approximation of standard MACD. Acceptable for a bonus; do not treat these as canonical MACD values if reused elsewhere.

### LOW — Hardcoded constants in confidence section (repo convention violation)
`grind_breakout_v2.py` lines 285/287/291 hardcode `3.0`, `2.5` (volume-ratio bonus thresholds) and `0.01` (accel bonus threshold). AGENTS.md says all tunable parameters must live in `hermes_constants.py`. Also the constant comment says "+5 if volume > 3x average" but the code also grants a half bonus (5//2=2) at ≥2.5x — comment/doc mismatch.
- **Fix:** add `GRIND_BREAKOUT_V2_CONF_VOL_TIER1/2` and `GRIND_BREAKOUT_V2_CONF_ACCEL_TIER` constants.

### LOW — Compression volume check uses an avg that includes the surge bar
`vol_avg = sum(vols[-20:])/20` includes the current breakout bar, inflating the denominator used by the compression check (`vol_r = vols[i] / vol_avg`). Borderline compression windows can be missed. Demonstrated numerically: compression vol=2.0 with surge=25 → vol_r=0.635 > COMPRESS_VOL_MAX=0.6 → compression rejected, even though true pre-surge average volume was ~2.0 (i.e. genuinely quiet). With surge=30 the same setup passes at vol_r=0.588. Spec says "× average" so this is within spec — flagging as a sensitivity, not a bug.

### LOW (informational) — SHORT `value` is negative
`value = (current_price - breakout_level)/breakout_level*100` yields a negative number for SHORT (verified: -0.3505 in synthetic SHORT test). Consistent signed-% convention, but if any downstream consumer expects a magnitude for SHORT, it should use `abs()`. Not verified downstream in this audit.

### LOW (performance, no leak) — O(N) connection churn in `run()`
`run()` iterates `SELECT DISTINCT token FROM candles_5m` and each `detect()` opens 2 SQLite connections (candles + runtime). No leak (all closed), but N×2 connect/close per pipeline run. Pre-existing pattern in this codebase.

## Connection Leak Check

All connection paths traced — every path closes in `finally`:

| Path | Connect | Close | Exception-safe? |
|------|---------|-------|-----------------|
| `_get_candles` | `sqlite3.connect(_CANDLES_DB, timeout=10)` | `finally: conn.close()` (line 100-102) | ✅ early `return []` also hits finally |
| `_get_acceleration` | `sqlite3.connect(_RUNTIME_DB, timeout=5)` | `finally: conn.close()` (line 116-118) | ✅ |
| `run()` token list | `sqlite3.connect(_CANDLES_DB, timeout=10)` | `finally: conn.close()` (line 337-339) | ✅ `except: return 0` still hits finally |
| `detect()` | opens none directly (delegates) | — | ✅ |
| `price_age_minutes` (signal_schema) | `_get_conn` | `finally: conn.close()` (line 3743-3744) | ✅ |

No leak on any path, including exception and early-return paths.

## Edge Cases Tested

23 synthetic tests (monkeypatched `_get_candles`/`_get_acceleration`) + live run. All passed:

1. **SQL injection:** all 4 queries parameterized (`?` placeholders with tuple args). No string interpolation into SQL. ✅
2. **Division by zero:** `vol_avg<=0` guarded (line 191); `bar_range<=0` guarded (line 232) — doji test returned None, no ZeroDivisionError; `breakout_level>0` guarded (line 265); `std20>0` guarded (line 305); `sma<=0` guarded in `_bb_width`; accel fallback guards `closes[-2]>0`/`closes[-3]>0`. close<=0 guarded (line 186). ✅
3. **`_bb_width` period > len(closes):** returns None (line 156). Flat data → 0.0 width. Negative sma → None. ✅
4. **`_get_macd_hist` insufficient data:** 34 closes → (None, None) (line 124); short macd_line → (None, None) (line 141). ✅
5. **`_get_acceleration` missing token_speeds:** returns None → candle-close fallback ran without crash and produced a valid signal. ✅
6. **Compression loop off-by-one:** `range(compress_start, len(candles)-1)` correctly excludes the current bar; BB window `closes[:i+1]` includes bar i (BB as-of end of bar i). With `_MIN_CANDLES=30`, `compress_start = len-11 ≥ 19`, so the BB window is always ≥ 20 = BB_PERIOD — never None from insufficient data. ✅
7. **Compression never happened (BB always wide, ±5% swings):** `compressed` stays False → returns None. ✅
8. **Only 12 candles (COMPRESS_LOOKBACK=10):** caught by `_MIN_CANDLES=30` gate before the loop; returns None. At the 30-candle minimum the loop still has full BB windows — no crash. ✅
9. **Current-bar bug in resistance:** `highs[-res_bars-1:-1]` = exactly 20 bars ending at index -2, excluding the current bar. Sentinel test: current-bar high=999 did NOT inflate resistance. Same for support. ✅
10. **LONG path:** synthetic tight-range + 3× volume surge + close above resistance + accel>0 → detected LONG, confidence 85 (75 base +5 vol +3 accel +2 MACD). Rejected when accel<0. Rejected when overextended (+3.8% > MAX_MOVE_FROM_RANGE=3.0). ✅
11. **SHORT path mirrors LONG:** close < support detected SHORT; `bar_body = open - close` (correct red-bar body — green-bar breakdown rejected by body check); requires `accel < -ACCEL_MIN` (accel>0 rejected); `abs()` in overextension check works both ways; MACD bonus requires hist falling for SHORT. ✅
12. **MACD disagreement is not a hard filter:** declining-MACD backdrop + valid breakout → signal still fired (spec: bonus, not filter). Verified ✅ — and `GRIND_BREAKOUT_V2_MACD_RISE_ENABLED` only gates the bonus block (lines 272-279), never a `return None`.

## Registration Check

Source strings match across all files:

| Location | Value | Matches signal? |
|----------|-------|-----------------|
| `grind_breakout_v2.py` SOURCE_LONG / SOURCE_SHORT | `grind-breakout-v2+` / `grind-breakout-v2-` (lines 68-69) | — |
| `hermes_constants.py` STANDALONE_BYPASS_SIGNALS (line 2810) | `grind-breakout-v2+`, `grind-breakout-v2-`, `grind_breakout_v2` | ✅ (underscore variant is a harmless extra) |
| `volatility_gate_v2.py` REGIME_SIGNALS | present in ALL 4 regimes: FLAT (63), NORMAL (104), HIGH (160), EXTREME (191), same 3 strings | ✅ |
| `signals/__init__.py` import (line 373) | `from signals.grind_breakout_v2 import run` inside try/except | ✅ |
| `signals/__init__.py` registry (line 546) | `{'name': 'grind_breakout_v2', 'enabled': 'GRIND_BREAKOUT_V2_ENABLED', 'run': _grind_breakout_v2_run}` | ✅ resolved via `getattr(hc, 'GRIND_BREAKOUT_V2_ENABLED', False)` — constant exists (line 2330, True) |

- **Constants:** all 22 imported `GRIND_BREAKOUT_V2_*` names exist in `hermes_constants.py` (lines 2330-2354); module imported successfully in tests, proving the import list resolves. Plus LONG_BLACKLIST/SHORT_BLACKLIST (uppercase entries — `token.upper()` comparison is correct).
- **Values sensible:** BB_COMPRESS_MAX=3.0% (tight for 5m — reasonable; live ETH currently 0.31%); VOL_SURGE_MULT=2.0 (standard); ACCEL_MIN=0.0 means "must be strictly positive" (LONG) / strictly negative (SHORT) — matches spec.
- **API signatures:** `add_signal(token, direction, signal_type, source, confidence, value, price, exchange, timeframe, z_score)` — all kwargs exist (signal_schema.py:523). `get_cooldown(token, direction=...)` (3806) and `set_cooldown(token, direction, hours=...)` (3894) match.
- **Live run:** `detect()` executed against real candles.db for ETH/BTC/SOL/CHIP — no exceptions; all returned None (no current setup qualifies; ETH BB width 0.31%).

## Recommendation

**Ship.** The signal is safe: every guard fires, every connection closes, registration and source strings are consistent across all four files, and both direction paths behave per spec (MACD correctly bonus-only).

Optional cleanup before or after shipping:
1. Fix `_get_macd_hist` `hist_prev` to use the previous bar's signal value (MEDIUM, +2-confidence accuracy only).
2. Move the hardcoded `3.0`/`2.5`/`0.01` confidence thresholds into `hermes_constants.py` per repo convention.
3. Consider computing `vol_avg` over the 20 bars *excluding* the current bar so the surge bar doesn't inflate the compression volume baseline.
