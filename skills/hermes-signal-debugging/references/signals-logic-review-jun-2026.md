# Signal Logic Review — Jun 2026 Audit Results

Source: `/root/shared/signal-logic-review.md` — external line-by-line review of `signals/accel_300.py` and `signals/rs.py`.

## CONFIRMED FIXED (vs prior review)

### accel_300.py
- hermes_constants imports: all flags now defined (`ACCEL_300_ENABLED`, `ACCEL_300_TOKEN_ALLOWLIST`, `ACCEL_300_PLUS/MINUS_ENABLED`, etc.)
- SHORT 4a sign inversion: `avg_gap_growth >= -min_gap_growth_dir` — correct sign-flipped comparison for widening negative gaps
- SHORT LOOKBACK = 500 via `ACCEL_300_LOOKBACK_SHORT`
- SHORT MIN_GAP_PCT = 0.25 via `ACCEL_300_MIN_GAP_PCT_SHORT`
- SHORT growth threshold = 0.07 via `ACCEL_300_MIN_GAP_GROWTH_SHORT`
- Gap expansion gate from actual cross point (lines 505-510)
- Regime slope filter (lines 549-565)
- Stale gap decay check (lines 567-575)
- Chop filter at cross point (lines 577-601)
- SHORT_BLACKLIST direction-aware — blocks SHORT only, not all directions (lines 685-689)

### rs.py
- `RS_COOLDOWN_HOURS` now enforced (lines 814-831)
- Return type consistency: `scan_rs_signals` always returns `tuple[int, list]` even when disabled (`return 0, []`)
- Bounce confirmation `(a)` dead code acknowledged in comments; follow-through path `(b)` functions

---

## FIXES APPLIED THIS SESSION

### accel_300.py — Most-recent-bar detection (NEW 2026-06-14)

**Problem**: Detection loop scanned forward and returned on the FIRST qualifying bar found — a setup from hours ago would fire with that stale bar's timestamp, despite a more recent bar also qualifying.

**Fix**: Changed to scan-and-track pattern:
1. Initialize `signal_bar = None` before loop
2. On qualifying bar: save all state into `signal_bar` dict
3. `break` — exit loop immediately (return most recent match)
4. After loop: `return signal_bar` (or `None`)

Previously: `return {...}` inside loop → returned oldest match.
Now: `signal_bar = {...}; break` → returns most recent match.

Also adds `ACCEL_300_STALE_LOOKBACK = 400` absolute backstop gate.

---

### rs.py — Recency formula inversion (NEW 2026-06-14)

**Problem**: `recency_score = K × recent_touches + ancient_touches` — ancient touches were multiplied, recent touches were not. Opposite of intent.

**Fix**: `recency_score = recent_touches × K + ancient_touches` — recent touches weighted MORE.

File's own comment ("each recent touch counts as K ancient touches") had the same inversion. Both comment and formula corrected.

---

### rs.py — Bounce confirmation hard gate (NEW 2026-06-14)

**Problem**: Signals fired when `bounces=False`, just lost a +5 bonus. Spec says bounce confirmation should be required.

**Fix**: Wrapped both support and resistance bodies in `if bounces: ... else: nearest_xxx = None`. No bounce = no signal.

Note: The restructure from linear `if/elif/else` to nested `if bounces: if broken: ... else: ...` required moving the entire inner block — this is a multi-branch edit, not a simple line patch.

---

### rs.py — RS_TOUCH_HARD_CAP null-check (NEW 2026-06-14)

**Problem**: `if RS_TOUCH_HARD_CAP and touch_count > RS_TOUCH_HARD_CAP` — if constant is `None` or `0`, cap silently bypassed.

**Fix**: `if RS_TOUCH_HARD_CAP is not None and touch_count > RS_TOUCH_HARD_CAP` — applied to both support and resistance paths.

---

## STILL OPEN (lower priority)

1. **Rolling max/min is trailing-window, not centered** — `highs[i] == roll_high[i]` detects prior-window max, not true local peak. Over-detects trend highs/lows. Medium risk.

2. **Recency lookup loses clustered scores** — `_get_clustered_recency()` exists but clustered levels (averaged prices) don't match raw level keys in `recency_by_level`. Medium risk.

3. **Nearest level by distance, not recency** — `dist_pct < best_support_dist` picks physically nearest; recency only affects confidence after selection. Comment at line 511 says "use recency_score for best level selection" — comment is wrong, code is right. Low risk.

---

## KEY PITFALLS FROM THIS AUDIT

### `continue` outside a loop
The LSP/Pyright error "continue not properly in loop" is a genuine Python SyntaxError, not a false positive. Python `continue` is only valid inside `for` or `while` loops. If you see this error after a patch, the `continue` is inside an `if/elif/else` block that isn't itself a loop — restructure to use `if/else` wrapping instead.

### Multi-branch restructure needs full context
When restructuring a linear `if/elif/else` chain into a nested `if bounces: ... else: ...` wrapper, read ALL branches before patching. The SHORT bounce gate fix required reading 65 lines of context to avoid breaking the `cand_signal` merge logic at the end of the block.

### Always verify with `python3 -m py_compile` after patching
Both files passed `py_compile` cleanly after all changes. Always run this before declaring a fix complete.
