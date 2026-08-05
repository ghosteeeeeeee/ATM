# GOOD_STANDALONE Fix + 3 Root Causes — 2026-05-08

## Root Cause 1: GOOD_STANDALONE_SIGNALS Naming Mismatch

`_signal_type_key()` converts source prefix to underscore format:
```python
# e.g. 'accel-300+' → 'accel_300_long'
```

`GOOD_STANDALONE_SIGNALS` dict uses **hyphen** format:
```python
{'accel-300+': {'wr': 42, ...}, 'pct-hermes-': {...}, ...}
```

Bypass check: `if base_type in GOOD_STANDALONE_SIGNALS` — compares `'accel_300_long'` against `{'accel-300+', ...}` → **NEVER MATCHES**.

**Result**: Every single-source signal (accel-300+, hzscore+, pct-hermes-, etc.) is held to the 2-signal co-signal gate regardless of whether it's in GOOD_STANDALONE_SIGNALS.

**Fix — change dict keys to underscore format**:
```python
GOOD_STANDALONE_SIGNALS = {
    'accel_300_long':   {'wr': 19, 'avg': -0.27, 'dir': 'LONG'},   # live: 23 trades, 17.4% WR
    'percentile_rank_short': {'wr': 0, 'avg': -0.51, 'dir': 'SHORT'}, # live: 32 trades, 0% WR
    'mtf_zscore_short':  {'wr': 21, 'avg': -0.34, 'dir': 'SHORT'}, # live
    'mtf_zscore_long':   {'wr': 16, 'avg': -0.70, 'dir': 'LONG'},  # live
    # Note: pct-hermes+ REMOVED (was 100% WR on 3 trades → live 4.7% WR on 64 trades)
}
```

Also update bypass check line ~519 to match: `if base_type in GOOD_STANDALONE_SIGNALS`.

---

## Root Cause 2: APPROVED Queue Is Dead Code

`signal_compactor.main()` only calls:
- `process_pending_signals()` — writes PENDING or EXPIRED
- `expire_stale_signals()` — writes EXPIRED

`compact_hot_set()` (contains `SET decision='APPROVED'`) is **never called**.

decider_run.py lines 922-944 reads `WHERE decision='PENDING'` directly — never reads APPROVED.

**Result**: APPROVED=0 in entire runtime DB. decider_run executes directly from PENDING, bypassing hot-set entirely.

---

## Root Cause 3: hzscore Hard-Blocked in decider_run

```python
# decider_run.py lines ~1121-1126
if sig_src == 'hzscore':
    rejection_reason = "combo-only, no confluence"
    continue
```

Blocks ALL signals whose first source prefix is 'hzscore', even valid directional combos.

---

## What Actually Works (Live Data)

| Signal | Trades | WR | avg_pnl% | Notes |
|--------|--------|-----|---------|-------|
| `accel-300+,rs-s16-150` | 9 | **100%** | +343% peak | Best combo in dataset |
| `accel-300+` (bare) | 23 | 17.4% | -27% | RS co-signal is the differentiator |
| `hzscore+` SHORT | 73 | 20.5% | -33.8% | hzscore hard-blocked in decider |
| `hzscore-` LONG | 76 | 15.8% | -70.4% | |
| `pct-hermes-` SHORT | 32 | **0%** | -51% | |
| `ma-cross-5m-short` | 10 | 0% | -0.5% | No co-signals merging |
| `hwave+,hzscore+` | 4 | 50% | +27% peak | hwave disabled April 18 |

**Live WR values for GOOD_STANDALONE_SIGNALS** (all stale/wrong):
- `'accel-300+': {'wr': 42}` — live: 17.4% WR / -27% avg_pnl
- `'pct-hermes-': {'wr': 35}` — live: **0% WR** / -51% avg_pnl
- `'hzscore+': {'wr': 32}` — live: 20.5% WR / -34% avg_pnl

---

## Fix Priority

| Priority | Fix | Expected Impact |
|----------|-----|-----------------|
| P0 | GOOD_STANDALONE_SIGNALS: convert keys to underscore + update WR values | Unblocks single-source signals, restores APPROVED flow |
| P1 | decider_run: remove hzscore block | Re-enables hzscore directional signals |
| P2 | Investigate hwave re-enablement | hwave+,hzscore+ = 50% WR, +27% peak (best SHORT) |
