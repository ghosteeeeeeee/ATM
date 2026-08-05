# tpsl_utils.py — Shared ATR SL/TP Module (2026-05-15)

**Created:** 2026-05-15
**Purpose:** Centralize ATR-based SL/TP computation so `position_manager.py` is the single source of truth. Eliminates duplicated ATR logic across `self_close_watcher.py` and `hl-sync-guardian.py`.

## Module Exports

```python
from tpsl_utils import (
    get_atr,                    # uses atr_cache.get_atr (read-only, same as position_manager)
    _atr_multiplier,           # k tier: LOW=0.5, NORMAL=0.75, HIGH=1.25
    compute_atr_sl_price,       # canonical SL price (trailing for LONG, fixed for SHORT new/in-profit)
    compute_atr_tp_price,       # canonical TP price (k_tp = k × ATR_TP_K_MULT)
    compute_atr_sl_pct,         # raw SL% (before floor/cap clamping)
    compute_atr_tp_pct,         # raw TP% (before floor/cap clamping)
)
```

## Architecture

```
position_manager.py          # authoritative — _compute_dynamic_sl / _compute_dynamic_tp
        ↓ (reads via atr_cache.py)
tpsl_utils.py                # shared utility layer — compute_atr_sl_price / compute_atr_tp_price
        ↓ (imported by)
self_close_watcher.py        # inline ATR replaced → tpsl_utils calls
hl-sync-guardian.py          # two inline ATR blocks replaced → tpsl_utils calls
```

**Why `atr_cache.get_atr` instead of position_manager's `_force_fresh_atr`?**
- `_force_fresh_atr` writes to the ATR cache file (makes it the authoritative cache writer)
- `self_close_watcher` and `hl-sync-guardian` only READ cached ATR for SL/TP computation
- Using `atr_cache.get_atr` (read-only) in `tpsl_utils` is correct — it reads memory cache first (fastest), then file cache, then returns None (triggering fallback)
- `position_manager`'s pipeline step separately maintains the cache file every minute

## Key Functions

### `compute_atr_sl_price(token, direction, entry_price, current_price)`
- **LONG**: `sl_pct = k × (atr / current_price)` → `sl_price = current_price × (1 - sl_pct)`
- **SHORT new/in-profit**: `sl_price = entry_price × (1 + sl_pct)` — anchors to entry so SL stays ABOVE entry (protective, not profit-taking)
- **SHORT established**: `sl_price = lowest_price × (1 + sl_pct)` — trails down correctly
- Falls back to `SL_PCT_FALLBACK = 1.5%` if ATR unavailable

### `compute_atr_tp_price(token, direction, entry_price, current_price)`
- **LONG**: `tp_price = current_price × (1 - k_tp × atr_pct)`
- **SHORT**: `tp_price = ref_price × (1 + k_tp × atr_pct)`
- `k_tp = k × ATR_TP_K_MULT (1.25)`
- Falls back to `TP_PCT_FALLBACK = 8.0%` if ATR unavailable

### `_atr_multiplier(atr_pct)`
| ATR% tier | k value |
|-----------|---------|
| < ATR_PCT_LOW_THRESH (0.5%) | 0.5 (LOW_VOL) |
| 0.5% – 2.0% | 0.75 (NORMAL_VOL) |
| > 2.0% | 1.25 (HIGH_VOL) |

## Files Modified

| File | Change |
|------|--------|
| `/root/.hermes/scripts/tpsl_utils.py` | **CREATED** — 5,128 bytes |
| `/root/.hermes/scripts/self_close_watcher.py` | Lines 23-26: added import; Lines 250-260: replaced 14-line inline ATR block with `compute_atr_sl_price()` / `compute_atr_tp_price()` |
| `/root/.hermes/scripts/hl-sync-guardian.py` | Line 188: added import; Stale record refresh (was 16 lines → 2 lines); No-record init (was 17 lines → 2 lines) |

## Constants Used

All from `hermes_constants.py` (verified 2026-05-12):
- `ATR_SL_MIN = 0.005` (0.50%), `ATR_SL_MAX = 0.01` (1.0%)
- `ATR_TP_MIN = 0.015` (1.5%), `ATR_TP_MAX = 0.05` (5.0%)
- `ATR_TP_K_MULT = 1.25`
- `ATR_K_LOW_VOL = 0.5`, `ATR_K_NORMAL_VOL = 0.75`, `ATR_K_HIGH_VOL = 1.25`
- `SL_PCT_FALLBACK = 0.015` (1.5%), `TP_PCT_FALLBACK = 0.08` (8.0%)
- `ATR_PCT_LOW_THRESH = 0.005` (0.5%), `ATR_PCT_HIGH_THRESH = 0.02` (2.0%)

## Verification Commands

```bash
# Syntax check all three files
python3 -m py_compile /root/.hermes/scripts/tpsl_utils.py
python3 -m py_compile /root/.hermes/scripts/self_close_watcher.py
python3 -m py_compile /root/.hermes/scripts/hl-sync-guardian.py

# Import test
cd /root/.hermes/scripts && python3 -c "from tpsl_utils import compute_atr_sl_price, compute_atr_tp_price; print('OK')"

# Verify no remaining inline ATR in patched files
grep -n "ATR_K_NORMAL_VOL\|atr_pct.*SL\|sl_pct.*max.*min" /root/.hermes/scripts/self_close_watcher.py | grep -v "^#\|tpsl_utils"
grep -n "k_tp\|ATR_K_NORMAL_VOL\|atr_pct" /root/.hermes/scripts/hl-sync-guardian.py | grep -v "^#\|tpsl_utils"
```

## Test Vectors

| Scenario | Entry | Computed SL | Computed TP |
|----------|-------|-------------|-------------|
| MORPHO LONG, ATR=0.38% | 1.988 | 1.958180 (1.500%) | 2.147040 (8.000%) |
| FIL SHORT, fallback ATR=3% | 1.0362 | 1.051743 (1.500%) | 0.953304 (8.000%) |

## Lessons Learned

1. **Don't duplicate ATR logic** — when three files all compute SL/TP from ATR independently, they diverge. Centralize to one module.
2. **SHORT SL anchor rule**: new/in-profit SHORTs anchor SL to entry (stays above entry = protective), established SHORTs trail from lowest_price (correct trailing behavior).
3. **Use `atr_cache.get_atr` for read-only** — `_force_fresh_atr` is for the writer; readers should use the read-only cache interface.