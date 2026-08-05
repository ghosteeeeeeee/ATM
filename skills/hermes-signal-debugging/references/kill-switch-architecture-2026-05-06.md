# Kill-Switch Architecture (2026-05-06)

## 3-Layer Kill-Switch System

| Layer | File | Mechanism | Notes |
|-------|------|-----------|-------|
| 1 | `hermes_constants.py` `*_ENABLED` flags | If False, `add_signal()` never called for that source | Script-level gate |
| 2 | `signal_schema.py` `add_signal()` | Per-source block after blacklist — catches directional variants | **Primary enforcement** |
| 3 | `decider_run.py` execution gate | Final block before trade executes | Defense in depth |

## `SIGNAL_SOURCE_BLACKLIST` — COMMENTED OUT

All entries in `SIGNAL_SOURCE_BLACKLIST` (`hermes_constants.py`, ~line 87) are **commented out** as of 2026-05-06. They are redundant with Layer 2 kill-switches. Kept for reference only.

## Layer 2 Kill-Switch Pattern

In `add_signal()`, the kill-switch checks each **component** of a source string (sources can be comma-separated combos like `pct-hermes+,hzscore+`):

```python
# signal_schema.py lines ~444-538
_components = _src.split(',')
for _comp in _components:
    # pct-hermes
    if _comp == 'pct-hermes+' and not PCT_HERMES_PLUS_ENABLED:
        print(f'  DEBUG add_signal BLOCKED: ... PCT_HERMES_PLUS_ENABLED=False', flush=True)
        return None
    if _comp == 'pct-hermes-' and not PCT_HERMES_MINUS_ENABLED:
        return None
    # vel-hermes
    if _comp == 'vel-hermes+' and not VEL_HERMES_PLUS_ENABLED:
        return None
    # ... etc
```

## Critical Bug: Bare-Source Check Misses Directional Variants

**Symptom:** `R2_REV_ENABLED=False` but `r2_rev+` and `r2_rev-` still pass through.

**Root cause:** Only the bare `'r2_rev'` entry was checked. The loop splits `r2_rev+` into `r2_rev+` as a single component, which doesn't match `'r2_rev'`.

**Fix — always add BOTH bare AND directional:**
```python
# WRONG:
if _comp == 'r2_rev' and not R2_REV_ENABLED:
    return None

# RIGHT:
if _comp == 'r2_rev+' and not R2_REV_ENABLED:
    return None
if _comp == 'r2_rev-' and not R2_REV_ENABLED:
    return None
if _comp == 'r2_rev' and not R2_REV_ENABLED:
    return None
```

**Affected signals with directional variants** (always check all three):
- `pct-hermes+/pct-hermes-/pct-hermes`
- `vel-hermes+/vel-hermes-/vel-hermes`
- `hzscore+/hzscore-/hzscore`
- `hmacd+/hmacd-/hmacd`
- `mtf-momentum+/mtf-momentum-/mtf-momentum`
- `phase-accel+/phase-accel-/phase-accel`
- `fast-momentum+/fast-momentum-/fast-momentum`
- `accel-300+/accel-300-` (uses `ACCEL_300_ENABLED` only — no +/- variants)
- `gap-300+/gap-300-` (uses `GAP_300_ENABLED` only — no +/- variants)
- `ma_cross+/ma_cross-` (uses `MA_CROSS_*_ENABLED`)
- `ma_cross_5m+/ma_cross_5m-` (uses `MA_CROSS_5M_*_ENABLED`)
- `r2_rev+/r2_rev-` (uses `R2_REV_ENABLED` only — no +/- variants)

## CRITICAL BUG: Removing Layer 1 Guard ≠ Blocked Signal (2026-05-06 Session)

**Symptom:** `momentum` and `mtf-momentum` registry scripts had their Layer 1 `if not MOMENTUM_ENABLED: return 0` guards removed during the signal_gen→signals_runner migration. The signals kept firing anyway — they had no Layer 2 kill-switch in `signal_schema.py`'s `add_signal()`.

**Root cause:** `momentum+/momentum-/momentum` were **never listed** in the Layer 2 kill-switch block of `add_signal()`. When Layer 1 guards were removed from registry scripts, nothing else stood between them and the DB.

**This is a silent kill-switch bypass** — no error, no warning, the signal just keeps passing through.

**The rule:** When removing a Layer 1 guard from a registry script, you MUST add/verify the Layer 2 check in `signal_schema.py add_signal()` for that source name. This must be done BEFORE removing the Layer 1 guard, not after.

**New flags added 2026-05-06:**
- `MOMENTUM_ENABLED`, `MOMENTUM_PLUS_ENABLED`, `MOMENTUM_MINUS_ENABLED` (all `False`)
- `OC_MTF_MACD_ENABLED`, `OC_RSI_ENABLED`, `OC_MTF_RSI_ENABLED`, `OC_PENDING_ENABLED` (all `False`)

**OC signals:** `oc_signal_importer.py` has 3 layers of protection now:
1. Master `any()` guard in `run_oc_import()` — skips entire function if all False
2. Early-return guard in each import function (`import_mtf_macd_signals`, `import_rsi_signals`, `import_pending_signals`)
3. Layer 2 in `add_signal()` — catches any signal that slips through layers 1 and 2

## Verified Kill-Switch Settings (2026-05-06)

| Source | Flag | Value | Expected |
|--------|------|-------|----------|
| `pct-hermes-` | `PCT_HERMES_MINUS_ENABLED` | False | BLOCKED |
| `pct-hermes+` | `PCT_HERMES_PLUS_ENABLED` | True | PASS |
| `vel-hermes+` | `VEL_HERMES_PLUS_ENABLED` | False | BLOCKED |
| `vel-hermes-` | `VEL_HERMES_MINUS_ENABLED` | True | PASS |
| `momentum` (bare) | `MOMENTUM_ENABLED` | False | BLOCKED |
| `momentum+` | `MOMENTUM_PLUS_ENABLED` | False | BLOCKED |
| `momentum-` | `MOMENTUM_MINUS_ENABLED` | False | BLOCKED |
| `mtf-momentum` (bare) | `MTF_MOMENTUM_ENABLED` | False | BLOCKED |
| `mtf-momentum+` | `MTF_MOMENTUM_PLUS_ENABLED` | True | PASS |
| `mtf-momentum-` | `MTF_MOMENTUM_MINUS_ENABLED` | True | PASS |
| `phase_accel` (bare) | `PHASE_ACCEL_ENABLED` | False | BLOCKED |
| `phase-accel+` | `PHASE_ACCEL_PLUS_ENABLED` | True | PASS |
| `phase-accel-` | `PHASE_ACCEL_MINUS_ENABLED` | True | PASS |
| `fast-momentum` (bare) | `FAST_MOMENTUM_ENABLED` | False | BLOCKED |
| `fast-momentum+` | `FAST_MOMENTUM_PLUS_ENABLED` | True | PASS |
| `fast-momentum-` | `FAST_MOMENTUM_MINUS_ENABLED` | False | BLOCKED |
| `gap-300+` | `GAP_300_PLUS_ENABLED` | False | BLOCKED |
| `gap-300-` | `GAP_300_MINUS_ENABLED` | False | BLOCKED |
| `ma_cross+` | `MA_CROSS_PLUS_ENABLED` | False | BLOCKED |
| `ma_cross-` | `MA_CROSS_MINUS_ENABLED` | True | PASS |
| `ma_cross_5m+` | `MA_CROSS_5M_PLUS_ENABLED` | False | BLOCKED |
| `ma_cross_5m-` | `MA_CROSS_5M_MINUS_ENABLED` | True | PASS |
| `r2_rev+` | `R2_REV_ENABLED` | False | BLOCKED |
| `r2_rev-` | `R2_REV_ENABLED` | False | BLOCKED |
| `hmacd+` | `HMACD_PLUS_ENABLED` | True | PASS |
| `hmacd-` | `HMACD_MINUS_ENABLED` | True | PASS |
| `hzscore+` | `HZSCORE_PLUS_ENABLED` | True | PASS |
| `accel-300+` | `ACCEL_300_ENABLED` | True | PASS |
| `oc-mtf-macd+` | `OC_MTF_MACD_ENABLED` | False | BLOCKED |
| `oc-mtf-macd-` | `OC_MTF_MACD_ENABLED` | False | BLOCKED |
| `oc-rsi+` | `OC_RSI_ENABLED` | False | BLOCKED |
| `oc-rsi-` | `OC_RSI_ENABLED` | False | BLOCKED |
| `oc-mtf-rsi+` | `OC_MTF_RSI_ENABLED` | False | BLOCKED |
| `oc-mtf-rsi-` | `OC_MTF_RSI_ENABLED` | False | BLOCKED |
| `oc-pending-*` | `OC_PENDING_ENABLED` | False | BLOCKED |

## `compute_regime()` Return Values

**Returns 5 values, not 3.** Migrated signal scripts that unpack incorrectly will get `ValueError: too many values to unpack`.

```python
# WRONG:
regime, long_mult, short_mult = compute_regime()

# RIGHT:
regime, long_mult, short_mult, *_ = compute_regime()
```

Affected: `mtf_momentum.py`, `momentum.py`

## `get_cooldown()` Return Type

`get_cooldown(token)` returns `bool` (True/None), NOT a dict. The old pattern `cd = get_cooldown(token) or {}` fails when `cd=True` (truthy but not subscriptable).

```python
# WRONG:
cd = get_cooldown(token) or {}
if cd.get(f"{token}:{direction}"):  # AttributeError: 'bool' object has no attribute 'get'

# RIGHT:
if get_cooldown(token, direction=direction):
    continue
```

Also: `get_cooldown` must be imported in the signal script — it is NOT automatically available from `signal_schema`.

## Quick Verification

```bash
cd /root/.hermes/scripts
python3 << 'EOF'
import sys, os, sqlite3, tempfile; sys.path.insert(0, '.')
import signal_schema

def test(source, expected_blocked, desc):
    db_path = tempfile.mktemp(suffix='.db')
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE signals (id INTEGER PRIMARY KEY AUTOINCREMENT, token TEXT, direction TEXT, signal_type TEXT, source TEXT, confidence REAL, entry_price REAL, created_at TEXT)")
    signal_schema._blacklist_cache = None
    try:
        sid = signal_schema.add_signal('BTC', 'LONG', 'test', source, 80.0, 100.0, conn=conn)
        blocked = sid is None
    except Exception as e:
        blocked = False
    conn.close()
    os.unlink(db_path)
    ok = "✓" if blocked == expected_blocked else "✗ MISMATCH"
    print(f"  {ok} {desc:30s} exp={'BLOCKED' if expected_blocked else 'PASS':6s}")
    return blocked == expected_blocked

all_pass = True
all_pass &= test('pct-hermes-', True, 'pct-hermes-')
all_pass &= test('pct-hermes+', False, 'pct-hermes+')
# ... add all sources being tested
print(f"\n{'ALL PASS ✓' if all_pass else 'FAILURES FOUND ✗'}")
EOF
```
