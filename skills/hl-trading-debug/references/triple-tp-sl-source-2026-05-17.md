# brain.py + cascade_flip + pump_hunter — Triple HL TP/SL Source (2026-05-17)

## Root Cause
TP/SL orders appearing on HL for new trades had THREE active sources, not one:

| Source | Function | Flag | Status |
|--------|----------|------|--------|
| `brain.py` | `add_trade()` Step 5 | None (always runs) | **DISABLED 2026-05-17** |
| `cascade_flip.py` | `_execute_cascade_flip()` lines 409-421 | `CASCADE_FLIP_ENABLED=False` | **DISABLED 2026-05-17** (belt+ suspenders) |
| `pump_hunter.py` | `_open_pump_position()` lines 670-692 | `PUMP_HUNTER_ENABLED=False` | **PENDING** — not yet disabled |

## Key Finding: cascade_flip / pump_hunter had flag but code still live

`CASCADE_FLIP_ENABLED=False` blocks the `scan_and_fire()` entry point, but inside `_open_pump_position()` (pump_hunter) the TP/SL calls at lines 671-677 fire independently — the `PUMP_HUNTER_ENABLED` flag only guards the top-level scan, NOT the internal `_open_pump_position()` function. If `_open_pump_position()` is called directly from another code path, the HL orders fire regardless of the flag.

Same pattern for cascade_flip: `CASCADE_FLIP_ENABLED=False` at the function entry, but the internal `hl_place_sl`/`hl_place_tp` calls at lines 414-415 were not guarded.

**Fix pattern**: Wrap the actual Python calls with `if FLAG and condition: pass` + commented code. Belt-and-suspenders.

## AI-Engineer Audit Findings (2026-05-17)

### P0 — HL Order Placement
- ✅ `brain.py:539-553` — Step 5 disabled (pass block)
- ✅ `cascade_flip.py:409-421` — wrapped with `if CASCADE_FLIP_ENABLED and sl_val > 0: pass` + added import
- ⏳ `pump_hunter.py:670-692` — pending same treatment

### P1 — Logic Bugs
- `ai_decider.py:1580` — Stale print says "65% threshold" but code uses `score >= 50`. Fix: change to "score>=50 threshold"
- `hl-sync-guardian.py:3351-3373` — `_place_or_replace_tp` dead code, never called anywhere. Mark as disabled or remove.

### P2 — Minor
- `hermes_constants.py:104-127` — `SIGNAL_SOURCE_BLACKLIST = {}` has 20+ stale commented entries. Clean up to single line.
- `brain.py:542` — `if sz and stop_loss: pass` — change to `if False:` for clarity as dead code marker.

## Verification Commands

```bash
# Confirm no active HL TP/SL place calls in brain.py
grep -n "place_sl\|place_tp" /root/.hermes/scripts/brain.py

# Confirm cascade_flip calls are commented
grep -n "hl_place_sl\|hl_place_tp" /root/.hermes/scripts/cascade_flip.py

# Confirm pump_hunter calls still active (PENDING)
grep -n "place_tp\|place_sl" /root/.hermes/scripts/pump_hunter.py | grep -v "^#"

# Syntax check all patched files
python3 -m py_compile /root/.hermes/scripts/brain.py
python3 -m py_compile /root/.hermes/scripts/cascade_flip.py
python3 -m py_compile /root/.hermes/scripts/pump_hunter.py

# Check live HL orders (should have no new TP/SL after fix)
python3 -c "
import sys; sys.path.insert(0, '/root/.hermes/scripts')
from hyperliquid_exchange import get_open_orders_curl
orders = get_open_orders_curl()
reduce_only = [o for o in orders if o.get('reduceOnly', False)]
print(f'Reduce-only orders: {len(reduce_only)}')
for o in reduce_only:
    print(f\"  oid={o['oid']} sz={o['sz']} limitPx={o['limitPx']} side={o['side']} tpsl={o.get('tpsl')}\")
"
```

## Pattern: "TP/SL disabled but still appearing"
The pattern: multiple components place HL TP/SL, disabling ONE doesn't disable ALL.
When diagnosing this, always check ALL of: brain.py Step 5, cascade_flip, pump_hunter,
hl-sync-guardian reconcile_tp_sl, position_manager _execute_atr_bulk_updates.