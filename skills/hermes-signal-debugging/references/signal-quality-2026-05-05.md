# Signal Quality Fix — 2026-05-05

## 3-Layer Kill-Switch Architecture

Signals can be disabled at three independent layers. All three must pass for a signal to execute.

### Layer 1 — hermes_constants.py GENERATION FLAG

```python
# SIGNAL KILL SWITCHES — top of hermes_constants.py (~line 352)
PCT_HERMES_PLUS_ENABLED = True   # pct-hermes+  (100% WR, +$2.31 — LEAVE ON)
PCT_HERMES_MINUS_ENABLED = True  # UNBLOCKED 2026-05-06 — only exists in combos
VEL_HERMES_PLUS_ENABLED = False   # vel-hermes+ (31% WR — BLOCKED)
VEL_HERMES_MINUS_ENABLED = True  # vel-hermes- (40% WR standalone)
GAP_300_ENABLED = False           # BLOCKED (14.3% WR, -1.52% PnL)
ACCEL_300_ENABLED = True          # accel-300+ (42.2% WR, +24.72% PnL)
FAST_MOMENTUM_PLUS_ENABLED = True
FAST_MOMENTUM_MINUS_ENABLED = False
MTF_MOMENTUM_PLUS_ENABLED = False  # BLOCKED 2026-05-06 — 0% WR in combos
MTF_MOMENTUM_MINUS_ENABLED = False # BLOCKED 2026-05-06 — 0% WR in combos
# ... etc
```

Each directional signal gets `*_PLUS_ENABLED` / `*_MINUS_ENABLED` independently. `pct-hermes+ ON, pct-hermes- OFF` — same signal family, independent control.

### Layer 2 — signal_schema.py add_signal() GUARD

After blacklist check in `add_signal()`, each signal source is checked against its `*_ENABLED` flag before DB insert. Returns `None` silently if disabled.

### Layer 3 — decider_run.py EXECUTION GATE

Before any trade executes, `decider_run` checks `*_ENABLED` flags by source string match. Logs and skips disabled signals even if they survived Layers 1+2.

**Three-layer protection: a signal is dead even if called via standalone script.**

---

## Signal Philosophy — What Each Signal Actually Measures

> T's empirical findings (2026-05-05): `pct-hermes+` fires at price TOPS (mean reversion works). `pct-hermes-` was BLOCKED as "catching knives" but this was wrong — pct-hermes- NEVER fires standalone, only exists in combos. The best SHORT combo is `hzscore+,pct-hermes-,vel-hermes-` at 46.2% WR / +0.382% avg (39 trades). Always check actual WR/PnL data before blocking/unblocking.

| Signal | Direction | Behavior | WR | PnL | Status |
|--------|-----------|---------|-----|------|--------|
| pct-hermes | + | Fires at price TOP (mean reversion long) | 30.6% | +4.08% | UNBLOCKED |
| pct-hermes | - | Only exists in combos. `hzscore+,pct-hermes-,vel-hermes-` = 46.2% WR. **NEVER standalone.** Blocked 2026-04-22 as "catching knives" — was wrong. Unblocked 2026-05-06. | 46.2% | +0.38% | **UNBLOCKED 2026-05-06** |
| vel-hermes | + | Instant reversal, momentum collapse | 31% | -0.13% | BLOCKED |
| vel-hermes | - | 40% WR standalone. Best in `hzscore+,pct-hermes-,vel-hermes-` combo. | 40% | +0.33% | UNBLOCKED |
| hzscore | + | Strong confluence SHORT signal | 34% | +0.31% | UNBLOCKED |
| accel-300 | + | Momentum acceleration | 42.2% | +24.72% | UNBLOCKED |
| gap-300 | + | Gap fill — counter-trend | 14.3% | -1.52% | BLOCKED |

**Counter-regime signals (hzscore-, accel-300-): DO NOT block them. Per-coin regime filter decides. Low-conf counter-trend = de-escalation. Strong enough counter-trend = escalation. Never hard-block anti-regime signals.**

---

## Signal Quality Diagnosis — Coin Immediately Reverses After Entry

**Symptom**: Signal fires, trade enters, coin instantly moves the wrong way. ATR SL was tightened but the problem is signal quality, not SL width.

**Key lesson (2026-05-05)**: T tightened ATR params (MIN_ATR_PCT=0.50%, MAX_SL=2.0%) thinking the problem was risk management. The real problem was signal quality — tighter SL just loses money faster when signals are wrong. ATR params are for managing good entries, not for fixing bad signals.

**Check first**: Is the signal itself wrong, or is the entry timing bad?
- Coin reverses within 1-2 candles of entry → signal direction is likely wrong
- Coin trends with signal then reverses → entry timing was bad but direction was right

**If most signals are immediately wrong**:
1. Check which signals are actually firing — look at `hotset.json` source counts
2. Check `signal_compactor.py` `validate_source()` — is a blocked signal leaking through?
3. Check the signal's empirical WR/PnL — if <40% WR or negative PnL, block it at Layer 1
4. DO NOT tighten ATR params as a fix for bad signals — tighter SL just gets hit faster

---

## Signal Registry — scripts/signals/ Architecture

All signals migrated to `/root/.hermes/scripts/signals/` as standalone scripts.

**Registry entry point**: `scripts/signals/__init__.py`
- `SIGNAL_REGISTRY` — list of all registered signals with their run functions
- `get_registered_signals()` — returns only enabled signals
- `run_all_signals(prices_dict, **kwargs)` — run all enabled signals

**Each signal script**: `scripts/signals/{signal_name}.py`
- Imports `*_ENABLED` flags from `hermes_constants`
- Has kill-switch guard at top of `run()` function
- Returns `(count, tokens_fired)` tuple

**Wiring into pipeline** (run_pipeline.py STEPS_EVERY_MIN):
```python
# Replace: signal_gen.run()
# With:
from signals import run_all_signals
run_all_signals(prices_dict)
```

**momentum.py gap**: There is no `scripts/signals/momentum.py`. The `momentum`/`momentum+`/`momentum-` source strings from `signal_gen.py` lines ~2484-2513 and ~2579-2592 are only partially covered by `mtf_momentum.py`. Needs a dedicated `momentum.py`.

---

## Confluence Gate — 2 Unique Types Required

**Symptom**: hot-set.json has 0 entries. Every passing signal gets blocked at HOTSET-FILTER by `vel-hermes+` in blacklist.

**Why 2 not 1**: Single-source signals are blocked at source generation (single-source → PENDING, never APPROVED). The 2-type floor ensures at least two independent indicators must agree.
