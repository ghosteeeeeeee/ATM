---
name: hermes-constants-sync
description: Keep ALL numeric constants in sync across Hermes scripts — audit Python files for hardcoded magic numbers and centralize them in hermes_constants.py. Covers position limits (MAX_POSITIONS/MAX_OPEN), ATR fallback values, SL/TP parameters, and any other numeric constant that appears in multiple files.
tags: [hermes, constants, positions, atr, bug-fix, magic-number-audit]
author: Hermes Agent
created: 2026-04-23
updated: 2026-04-26
---

# Hermes Constants Sync

## The Problem
Numeric constants are defined independently in multiple files. Changing one without changing the others causes silent bugs — trades use stale values, fallback ATR is wrong, position limits drift.

## Two Types of Constants to Centralize

### 1. Threshold/Limit Constants (e.g. MAX_POSITIONS, MAX_OPEN)
Changing one without the others causes the limit to be silently ignored.

### 2. Magic Numbers / Fallback Values (e.g. atr_pct = 0.02)
Hardcoded fallback values used when real data is unavailable. Must live in `hermes_constants.py` so they can be changed in one place.

## Audit Command — Find All Hardcoded Magic Numbers
```bash
grep -rn "= 0\.0[0-9]" /root/.hermes/scripts/*.py \
  --include="*.py" | grep -v ".pyc" | grep -v "atr_cache" | grep -v "comment\|#\|docstring\|Doc\|def \|class "
```
Also grep for `= 0\.02`, `= 0\.015`, `= 0\.025`, `= 2\.0` patterns in isolation.

## When to Run This Audit
- After adding any new numeric threshold to `hermes_constants.py`
- When fixing bugs involving SL/TP, position sizing, or cooldown thresholds
- When T says "make sure all [X] values are not hardcoded"

---

## Part A: MAX_POSITIONS / MAX_OPEN

### The Problem
`MAX_POSITIONS` and `MAX_OPEN` are defined independently in multiple files.

## All Locations (as of 2026-04-23)

| File | Constant | Line | Hardcoded String? |
|------|----------|------|-------------------|
| `position_manager.py` | `MAX_POSITIONS` | 61 | No |
| `ai_decider.py` | `MAX_OPEN` | 990 | No |
| `ai_decider.py` | `'{MAX_OPEN}': '10'` | 1292 | Yes — prompt substitution |
| `hl-sync-guardian.py` | Comment only `MAX_POSITIONS = ...` | 2319 | Just a doc comment |

## How to Change Max Positions

**Step 1:** Grep for ALL occurrences first:
```bash
grep -rn "MAX_POSITIONS\|MAX_OPEN" /root/.hermes/scripts/ \
  --include="*.py" | grep -v ".pyc" | grep -v "wandb/" | grep "=[0-9]"
```

**Step 2:** Update ALL numeric definitions (both `position_manager.py` and `ai_decider.py`).

**Step 3:** If there's a hardcoded `'{MAX_OPEN}': '10'` string in `ai_decider.py`, update that too — it gets substituted into the LLM prompt.

**Step 4:** Verify no other files define it.

## Key Files
- `position_manager.py` — `MAX_POSITIONS` (primary enforcement point)
- `ai_decider.py` — `MAX_OPEN` (blocks new entries when `get_open() >= MAX_OPEN`)

## Common Bug Pattern
---

## Part B: ATR Magic Numbers — Fallback Values

### The Problem
Scripts that compute SL/TP when real ATR is unavailable use hardcoded `atr_pct = 0.02` (2%). These must be centralized so the fallback assumption is controllable from one place.

### All Known Locations (as of 2026-04-26)

| File | Line | Issue |
|------|------|-------|
| `hl-sync-guardian.py` | ~2929 | `atr_pct = 0.02` hardcoded in self-close TP/SL block |
| `self_close_watcher.py` | ~246 | `atr_pct = 0.02` hardcoded in `compute_sl_tp()` |

### The Fix Pattern
```python
# 1. Ensure ATR_PCT_FALLBACK is in hermes_constants.py:
#    ATR_PCT_FALLBACK = 0.02

# 2. Import in the file that needs it:
from hermes_constants import ATR_PCT_FALLBACK, ATR_K_NORMAL_VOL
from atr_cache import get_atr

# 3. Use real ATR when available, fall back otherwise:
real_atr = get_atr(coin, interval='1h')
if real_atr is not None:
    atr_pct = real_atr / current_price
else:
    atr_pct = ATR_PCT_FALLBACK  # use the centralized fallback

k = ATR_K_NORMAL_VOL
```

### Critical: Make atr_cache.py Self-Contained
`atr_cache.py` had `from paths import *` at module level. This causes `NameError: ATR_CACHE_FILE is not defined` when `atr_cache` is imported before `paths`. 

**Fix:** Remove `from paths import *`. Define the cache path inside `atr_cache.py` itself:
```python
import os
_HERMES_DATA = os.environ.get('HERMES_DATA_DIR',
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data'))
_CACHE_FILE = os.path.join(_HERMES_DATA, 'atr_cache.json')
```

**Verification:** `python3 -c "from atr_cache import get_atr; from hermes_constants import ATR_PCT_FALLBACK"` must succeed with no errors.

### atr_cache.get_atr() Returns
- `float | None` — actual ATR ratio (atr/price) if cached and fresh
- `None` if coin not in cache or cache missing — caller must fall back to `ATR_PCT_FALLBACK`

### Relevant Constants in hermes_constants.py
```
ATR_PCT_FALLBACK  = 0.02    # 2% fallback when real ATR unavailable
ATR_K_NORMAL_VOL  = 2.0     # k multiplier for normal volatility phase
ATR_SL_MIN        = 0.005   # 0.50% — standard SL floor
ATR_SL_MAX        = 0.020   # 2.00% — SL ceiling
ATR_TP_MIN        = 0.0075  # 0.75% — TP floor
ATR_TP_MAX        = 0.050   # 5.00% — TP ceiling
ATR_TP_K_MULT     = 1.25   # TP k = sl_k × 1.25
```

### Relevant Files
- `/root/.hermes/scripts/hermes_constants.py` — canonical source for all ATR constants
- `/root/.hermes/scripts/atr_cache.py` — `get_atr(coin, interval)`, must be self-contained
- `/root/.hermes/scripts/hl-sync-guardian.py` — self-close TP/SL fallback
- `/root/.hermes/scripts/self_close_watcher.py` — `compute_sl_tp()` fallback

---

## Session Log (2026-04-23)
- Reduced max positions from 10 → 5
- Found `MAX_OPEN = 10` in `ai_decider.py:990` and hardcoded string `'{MAX_OPEN}': '10'` at line 1292
- Both updated to 5

## Session Log (2026-04-28)
- Centralized speed tracker constants into `hermes_constants.py`:
  - SPEED_MIN_THRESHOLD, SPEED_BOOST_THRESHOLD, SPEED_BOOST_FACTOR
  - SPEED_HOTSET_WEIGHT, SPEED_HOTSET_THRESHOLD, SPEED_HOTSET_BONUS
  - STALE_VELOCITY_THRESHOLD, STALE_WINNER_TIMEOUT_MINUTES, STALE_LOSER_TIMEOUT_MINUTES, STALE_WINNER_MIN_PROFIT, STALE_LOSER_MAX_LOSS
- Updated consumers:
  - `signal_gen.py` → imports SPEED_MIN_THRESHOLD, SPEED_BOOST_THRESHOLD, SPEED_BOOST_FACTOR
  - `decider_run.py` → imports SPEED_HOTSET_WEIGHT as SPEED_WEIGHT
  - `position_manager.py` → imports STALE_* constants
  - `speed_tracker.py` → imports all speed/stale constants
  - `paths.py` → re-exports SPEED_HOTSET_THRESHOLD, SPEED_HOTSET_BONUS from hermes_constants (was hardcoded duplicate)
- **Bug found**: SPEED_WEIGHT=0.15 was defined in `decider_run.py:63` but never used anywhere in the approval logic — speed_percentile was being read from hot_sig but not contributing to effective_conf. Fixed by wiring `(speed_pctl - 50) / 100 × SPEED_WEIGHT × sig_conf` into effective_conf.
- **Dead code found**: SPEED_COMPACTION_WEIGHT=0.10 in speed_tracker.py was defined but never referenced anywhere. Removed.
- **Bug found (pass 1)**: `signal_compactor.py:227` used hardcoded `0.10` and `80` instead of `SPEED_HOTSET_BONUS` and `SPEED_HOTSET_THRESHOLD`. Fixed: added imports, replaced with named constants.
- **Bug found (pass 2)**: docstring on `signal_compactor.py:194` still said `+10%` after pass-1 fix. Fixed to `+15%`.
- **New pattern — "defined but never used"**: When centralizing, always grep for the constant name across ALL files to confirm it's actually referenced in logic, not just defined.
- **New pattern — "docstring drift"**: When fixing hardcoded magic numbers, always check docstrings/comments that describe the same value — they drift independently and create false documentation.

## Session Log (2026-04-26)
- Fixed hardcoded `atr_pct = 0.02` in `hl-sync-guardian.py:2929` (unprotectable coins self-close)
- Fixed hardcoded `atr_pct = 0.02` in `self_close_watcher.py:246` (compute_sl_tp fallback)
- Removed `from paths import *` from `atr_cache.py` — made it self-contained
- Added `ATR_PCT_FALLBACK = 0.02` to `hermes_constants.py`
- Both services restarted: hermes-pipeline.service, hermes-hl-sync-guardian.service

## Session Log (2026-04-28)
- Added `WRONG_SIDE_AVG_PCT_THRESH = 1.5` to `hermes_constants.py` (new section: wrong-side stall detection)
- Replaced hardcoded `1.5` in `position_manager.py:3087` (`_is_wrong_side_stall`) with `WRONG_SIDE_AVG_PCT_THRESH`
- Fixed 3 docstring/comment drifts in `position_manager.py`:
  - `get_trade_params` docstring (line ~1943): stale k values 1.5/2.0/2.5 → corrected to 1.0/1.25/1.5, fixed threshold names, fixed TP multiplier description
  - `_compute_dynamic_tp` docstring (line ~1435): `k_tp = 2.5 × k_SL` → `k_tp = k * ATR_TP_K_MULT (1.25)`
  - SL floor comment (line ~1617): `1.0% floor` → `0.50% floor` to match `ATR_SL_MIN_INIT`
- Syntax verified: `python3 -c "import position_manager; print('OK')"`
