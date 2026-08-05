# rs.py Audit — 2026-06-14

## Bugs Found & Fixed

### Bug 1: `cand_signal` NameError at line 753 (HIGH)
**File:** signals/rs.py, resistance path in `detect_rs_signal()`

`cand_signal` was only defined inside `else: bounces` block (lines 695-751) but used
at line 753 regardless. Two paths hit the use with variable undefined:
1. `touch_count > RS_TOUCH_HARD_CAP` (line 683-684) → `nearest_resistance = None`
2. `bounces == False` (line 693-694) → `nearest_resistance = None`

Both still fell through to line 753 `if cand_signal is not None` → NameError.

**Fix:** Initialize `cand_signal = None` before the bounces gate (line 699).

Found by subagent, verified and fixed in main session.

---

### Bug 2: Bounce detection scale mismatch (HIGH)
**File:** signals/rs.py, `_bounce_confirmation()` lines 286, 295

**Problem:** Follow-through was compared to `c['close'] * 1.00025` instead of `level * 1.00025`.
With `touch_thresh = 0.2 * ATR` (0.2% for ATR=1.0), a candle could be 0.2% away from
the level and confirm bounce with only 0.025% move above ITSELF — 8:1 scale ratio.

**Fix:** Changed to `level * 1.00025` (LONG) and `level * 0.99975` (SHORT). Now the
next candle must move 0.025% beyond the LEVEL itself, properly calibrated with the touch threshold.

```python
# OLD (wrong scale)
if next_close > c['close'] * 1.00025:
if next_close < c['close'] * 0.99975:

# NEW (correct — compare to level)
if next_close > level * 1.00025:
if next_close < level * 0.99975:
```

---

## Subagent Audit Results

Subagent completed in 70s on 938-line file — did NOT time out.

**What subagent got right:**
- `cand_signal` scope issue (line 753) — confirmed HIGH, was real bug
- All 4 signal dict branches have `recency_score` — verified clean
- Broken level reclassification (lines 626-629, 699-702) — fall-through logic correct

**What subagent flagged incorrectly:**
- `_get_clustered_recency` "returns nearest raw level not cluster member" — this is the
  existing workaround, not a new bug (Pattern 28 was already documented)

**What subagent called "stale docstring":**
- `_cluster_levels` docstring says "weighted by touch count" but code does simple average —
  confirmed stale docstring only, not a logic bug (Pattern 30 from prior session)

---

## Verified Working

- `_level_recently_broken`: requires 2 confirming candles beyond crossing candle — correct
- Broken support reclassification (`price > level`): correctly treats recovered broken support as active
- Broken resistance reclassification (`price < level`): correctly treats recovered broken resistance as active
- Both broken-level paths (`RS_BROKEN_SHORT_ENABLED=False`, `RS_BROKEN_RESISTANCE_LONG_ENABLED=False`)
  correctly disable their respective broken-level signals
- `_compute_confidence`: base 65, ATR bonus +0-15, touch bonus +0-9, bounce bonus +5, recency bonus +0-8
- ATR band filter confirmed deprecated/not active

---

## Smoke Test

```python
# Bounce LONG: touch at 99.96, next_close 100.10 > level*1.00025=100.025 → True
# Bounce SHORT: touch at 100.04, next_close 99.88 < level*0.99975=99.975 → True
# Support broken: 101→99→98 (2 confirms below) → True
# Support NOT broken: 101→99→100.5 (bounce back above) → False
# Resistance broken: 99→101→102 (2 confirms above) → True
```

All tests pass post-fix.

---

## File State

- Lines: 938 → 945 (after 2 fixes)
- Syntax: clean (`python3 -m py_compile`)
- Subagent completion: 70s (no timeout)
