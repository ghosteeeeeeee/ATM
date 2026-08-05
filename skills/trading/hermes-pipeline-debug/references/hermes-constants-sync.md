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

### 3. Boolean Kill Switches / System Toggles (e.g. LIVE_TRADING_ENABLED, CONFLUENCE_REQUIRED)
System-level on/off flags that control execution behavior. Must live in `hermes_constants.py` — NOT in runtime files like `hype_live_trading.json`. The pattern:
```python
# hermes_constants.py
LIVE_TRADING_ENABLED = True

# hyperliquid_exchange.py
from hermes_constants import LIVE_TRADING_ENABLED

def is_live_trading_enabled() -> bool:
    return LIVE_TRADING_ENABLED  # replaces _load_flags().get("live_trading", False)
```
All callers continue calling `is_live_trading_enabled()` unchanged — backward compatible.

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
ATR_K_INITIAL      = 2.0   # initial SL only — wider than trailing, gives new trades room
ATR_K_LOW_VOL      = 0.5  # trailing/accel SL — atr_pct < 1%
ATR_K_NORMAL_VOL   = 0.75 # trailing/accel SL — 1.25% <= atr_pct <= 3%
ATR_K_HIGH_VOL     = 1.0  # trailing/accel SL — atr_pct > 3%
ATR_PCT_LOW_THRESH = 0.01 # 1%
ATR_PCT_HIGH_THRESH= 0.03 # 3%
ATR_PCT_FALLBACK   = 0.02 # 2% fallback when real ATR unavailable
ATR_TP_K_MULT      = 1.25 # TP k = sl_k × 1.25
ATR_SL_MIN_INIT    = 0.0050 # 0.50% — initial SL floor
ATR_SL_MAX_INIT    = 0.020  # 2.00% — initial SL ceiling
ATR_SL_MIN_ACCEL   = 0.0020 # 0.20% — acceleration/established trade floor
ATR_TP_MIN         = 0.0075 # 0.75% — TP floor
ATR_TP_MAX         = 0.050  # 5.00% — TP ceiling
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
- Added `LIVE_TRADING_ENABLED = True` to `hermes_constants.py` — master kill switch moved from `hype_live_trading.json` (runtime JSON) to compile-time Python constant.
- **New pattern — SEPARATE k FOR INITIAL SL vs TRAILING SL**: When the same k multiplier serves two different purposes that need different values, create a separate constant. Example: `ATR_K_LOW_VOL = 0.5` was used for both initial SL (`get_trade_params`) and trailing SL (`_atr_sl_k_scaled`). For ultra-low-vol tokens (IP, ATR 0.43%), k=0.5 → sl_pct = 0.21% → MIN_SL_ACCEL floor kicks in → initial SL only 0.07% from entry. Tighter initial SL requires wider k. Fix: add `ATR_K_INITIAL = 2.0` for `get_trade_params` only; trailing/acceleration keeps using `_atr_sl_k_scaled` with normal k values. Files changed: `hermes_constants.py` (added `ATR_K_INITIAL`), `position_manager.py` (import + use in `get_trade_params` line ~1976).
- Updated `hyperliquid_exchange.py`: added `from hermes_constants import LIVE_TRADING_ENABLED`, changed `is_live_trading_enabled()` to return `LIVE_TRADING_ENABLED` directly (was reading from JSON file via `_load_flags()`).
- All existing callers of `is_live_trading_enabled()` work unchanged — backward compatible.
- Note: `enable_live_trading()`/`disable_live_trading()` still write to `hype_live_trading.json` but nothing reads it anymore. Dead CLI interface; can be cleaned up separately.
- Replaced hardcoded `1.5` in `position_manager.py:3087` (`_is_wrong_side_stall`) with `WRONG_SIDE_AVG_PCT_THRESH`
- Fixed 3 docstring/comment drifts in `position_manager.py`:
  - `get_trade_params` docstring (line ~1943): stale k values 1.5/2.0/2.5 → corrected to 1.0/1.25/1.5, fixed threshold names, fixed TP multiplier description
  - `_compute_dynamic_tp` docstring (line ~1435): `k_tp = 2.5 × k_SL` → `k_tp = k * ATR_TP_K_MULT (1.25)`
  - SL floor comment (line ~1617): `1.0% floor` → `0.50% floor` to match `ATR_SL_MIN_INIT`
- Syntax verified: `python3 -c "import position_manager; print('OK')"`
- Added `CONFLUENCE_REQUIRED = True` to `hermes_constants.py` — controls whether single-source signals require 2+ sources to enter hot-set
- Updated `signal_compactor.py` to import and use `CONFLUENCE_REQUIRED` instead of hardcoded gate logic

## Session Log (2026-04-26)
- Fixed hardcoded `atr_pct = 0.02` in `hl-sync-guardian.py:2929` (unprotectable coins self-close)
- Fixed hardcoded `atr_pct = 0.02` in `self_close_watcher.py:246` (compute_sl_tp fallback)
- Removed `from paths import *` from `atr_cache.py` — made it self-contained
- Added `ATR_PCT_FALLBACK = 0.02` to `hermes_constants.py`
- Both services restarted: hermes-pipeline.service, hermes-hl-sync-guardian.service

## Session Log (2026-04-28)
- Added `LIVE_TRADING_ENABLED = True` to `hermes_constants.py` — master kill switch moved from `hype_live_trading.json` (runtime JSON) to compile-time Python constant.
- **New pattern — SEPARATE k FOR INITIAL SL vs TRAILING SL**: When the same k multiplier serves two different purposes that need different values, create a separate constant. Example: `ATR_K_LOW_VOL = 0.5` was used for both initial SL (`get_trade_params`) and trailing SL (`_atr_sl_k_scaled`). For ultra-low-vol tokens (IP, ATR 0.43%), k=0.5 → sl_pct = 0.21% → MIN_SL_ACCEL floor kicks in → initial SL only 0.07% from entry. Tighter initial SL requires wider k. Fix: add `ATR_K_INITIAL = 2.0` for `get_trade_params` only; trailing/acceleration keeps using `_atr_sl_k_scaled` with normal k values. Files changed: `hermes_constants.py` (added `ATR_K_INITIAL`), `position_manager.py` (import + use in `get_trade_params` line ~1976).
- Updated `hyperliquid_exchange.py`: added `from hermes_constants import LIVE_TRADING_ENABLED`, changed `is_live_trading_enabled()` to return `LIVE_TRADING_ENABLED` directly (was reading from JSON file via `_load_flags()`).
- All existing callers of `is_live_trading_enabled()` work unchanged — backward compatible.
- Note: `enable_live_trading()`/`disable_live_trading()` still write to `hype_live_trading.json` but nothing reads it anymore. Dead CLI interface; can be cleaned up separately.
- Replaced hardcoded `1.5` in `position_manager.py:3087` (`_is_wrong_side_stall`) with `WRONG_SIDE_AVG_PCT_THRESH`
- Fixed 3 docstring/comment drifts in `position_manager.py`:
  - `get_trade_params` docstring (line ~1943): stale k values 1.5/2.0/2.5 → corrected to 1.0/1.25/1.5, fixed threshold names, fixed TP multiplier description
  - `_compute_dynamic_tp` docstring (line ~1435): `k_tp = 2.5 × k_SL` → `k_tp = k * ATR_TP_K_MULT (1.25)`
  - SL floor comment (line ~1617): `1.0% floor` → `0.50% floor` to match `ATR_SL_MIN_INIT`
- Syntax verified: `python3 -c "import position_manager; print('OK')"`
- Added `CONFLUENCE_REQUIRED = True` to `hermes_constants.py` — controls whether single-source signals require 2+ sources to enter hot-set
- Updated `signal_compactor.py` to import and use `CONFLUENCE_REQUIRED` instead of hardcoded gate logic
