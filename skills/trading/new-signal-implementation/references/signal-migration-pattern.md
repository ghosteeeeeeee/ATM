# Signal Migration Pattern — Inline → Standalone Registry

Migrating inline signal code from `signal_gen.py` to standalone scripts in `scripts/signals/`, wired through `signals/__init__.py` registry and called by `signals_runner.py`.

---

## Problem: Dual-Fire

If inline signal code stays enabled in `signal_gen.py` while the same signals also fire from `scripts/signals/`, you get double signals — same token, same direction, double the noise.

**The naive approach (wrong):** Flip `*_ENABLED` flags to `False` — this kills BOTH the inline AND the registry version simultaneously.

**The correct approach (two-step guard pattern):**

---

## Two-Step Guard Pattern

### Step 1 — Remove Layer 1 guards from registry scripts

Registry scripts in `scripts/signals/` have top-of-`run()` guards like:

```python
if not PCT_HERMES_ENABLED:
    return 0
```

Remove these. Replace with a comment:

```python
# NOTE: PCT_HERMES_ENABLED guard is in signal_gen.py (inline version).
# This registry version is called by signals_runner.py — Layer 2 add_signal()
# guard handles per-source filtering.
```

**Why:** If the master flag is `True`, the inline version fires AND the registry fires → double. If the master flag is `False`, NEITHER fires → registry is dead. Removing the guard breaks this dependency.

**Key:** Per-direction guards (e.g., `if not VEL_HERMES_PLUS_ENABLED: continue`) should STAY — those are the real kill-switches.

### Step 2 — Flip master flags to `False` in `hermes_constants.py`

```python
PCT_HERMES_ENABLED    = False  # disabled — signals now fire via signals_runner
VEL_HERMES_ENABLED    = False
HMACD_ENABLED         = False
MTF_MOMENTUM_ENABLED = False
PHASE_ACCEL_ENABLED  = False
FAST_MOMENTUM_ENABLED= False
MOMENTUM_ENABLED     = False
HZSCORE_ENABLED      = False
```

Now `signal_gen.py` inline code is blocked. Registry scripts fire freely. `add_signal()` Layer 2 handles directional filtering.

---

## Why This Works

| Layer | Where | Guards |
|-------|-------|--------|
| Layer 1 | `hermes_constants.py` `*_ENABLED` | Master on/off |
| Layer 2 | `signal_schema.py` `add_signal()` | Per-source directional |
| Layer 3 | `decider_run.py` | Final execution gate |

Registry scripts go straight to `add_signal()` (Layer 2) — so directional flags still filter correctly.

---

## Migration Checklist

- [ ] Extract signal code to `scripts/signals/{name}.py` with `run()` function
- [ ] Add to `scripts/signals/__init__.py` registry
- [ ] Test standalone: `python3 scripts/signals_runner.py`
- [ ] **Remove** `if not *_ENABLED: return` guard from the registry script's `run()`
- [ ] **Flip** master `*_ENABLED` to `False` in `hermes_constants.py`
- [ ] **Keep** per-direction guards (e.g., `VEL_HERMES_PLUS_ENABLED`) — these are the real kill-switches
- [ ] Verify: `signal_gen` inline blocked, registry signals flow through `add_signal()` Layer 2
- [ ] Run full pipeline: `python3 run_pipeline.py`

---

## Debugging: Registry Shows Fewer Signals Than Expected

**Symptom:** Registry shows 15 signals instead of 23 after migration.

**Likely cause:** Silent import failure when `signals/__init__.py` loads all scripts together. One of the 8 extracted scripts has an import that only fails in the full module context (circular import, missing transitive dep).

**Diagnosis:**
```bash
cd /root/.hermes/scripts && python3 << 'EOF'
import sys; sys.path.insert(0, '.')
import signals.pct_hermes, signals.vel_hermes, signals.hzscore
import signals.hmacd, signals.mtf_momentum, signals.phase_accel
import signals.fast_momentum, signals.momentum
print('All 8 import OK')
from signals import get_registered_signals
print(f'Registered: {len(get_registered_signals())}')
EOF
```

**Common causes:**
- `compute_regime()` returns 5 values; code unpacks 3 → `ValueError: not enough values to unpack`
- `get_cooldown()` returns `bool`, not `dict` → `'str' object has no attribute 'get'`
- Import not added to `__init__.py` after script creation
- Wrong function name in registry (`scan` vs `scan_xxx_signals`)

---

## Key Files

| File | Role |
|------|------|
| `/root/.hermes/scripts/signal_gen.py` | Inline signal code (now disabled via `*_ENABLED=False`) |
| `/root/.hermes/scripts/signals_runner.py` | Pipeline step — calls `run_all_signals()` |
| `/root/.hermes/scripts/signals/__init__.py` | Registry — 24 signals, `run_all_signals()` dispatcher |
| `/root/.hermes/scripts/signals/{name}.py` | Standalone signal scripts |
| `/root/.hermes/scripts/hermes_constants.py` | Kill-switch flags |
| `/root/.hermes/scripts/signal_schema.py` | `add_signal()` Layer 2 enforcement |

---

## Critical Bug: `compute_regime()` Return Count

`signal_gen.compute_regime()` returns **5 values**:
```python
return (regime, long_mult, short_mult, regime_filtered, macd_hist)
```

Any extracted script that calls `compute_regime()` must unpack 5:
```python
# WRONG (ValueError):
regime, long_mult, short_mult = compute_regime()

# CORRECT:
regime, long_mult, short_mult, *_ = compute_regime()
```

Found in: `scripts/signals/mtf_momentum.py`, `scripts/signals/momentum.py`

---

## Critical Bug: `get_cooldown()` Return Type

`signal_schema.get_cooldown(token)` returns:
- `None` — no cooldown
- `True` — cooldown active (boolean, NOT a dict)
- `dict` — cooldown data (only for some tokens)

**Never do:** `cd = get_cooldown(token) or {}; cd.get(...)` — `True.get(...)` raises `AttributeError`.

**Correct pattern:**
```python
if get_cooldown(token, direction=direction):
    continue  # cooldown active, skip
```
