# RS Signals — Confluence Gate Blocking Hot-Set (2026-06-18)

## Problem
Hot-set is empty. RS and accel signals exist as PENDING in DB but never reach hot-set.

## Root Cause — Confluence Gate Architecture

The `signal_compactor.py` confluence gate (lines 571-599) requires **2+ unique signal types** to pass:

```python
unique_signal_types = len(set(_signal_type_key(p) for p in source_parts))
if unique_signal_types >= 2:
    pass_gate = True
```

Single-source signals (e.g., `accel-300-` alone, or `rs-s20` alone) are **always blocked** — no bypass except `ACCEL_300_STANDALONE_BYPASS_ENABLED=True` which was disabled for 40% WR.

## Why RS + Accel Never Co-occur

| Signal | Firing rate (30-min sample) | Passes confluence? |
|--------|---------------------------|-------------------|
| `accel-300` | 35 signals (1,680/hr) | NEVER — single source |
| `rs` | 3 signals (6/hr) | NEVER — single source |

RS is sparse and timing doesn't align with accel in the same 5-minute PENDING window. **Zero RS+accel combos in 30 minutes.**

RS signals (AVAX rs-s20, AXS rs-s42) fire alone → 5-min staleness timer → EXPIRED.

## Confluence Key Normalization

```python
def _signal_type_key(part):
    part = re.sub(r'-broken$', '', part)      # rs-s-broken → rs-s
    part = re.sub(r'^rs-[sr]', 'rs', part)    # rs-s86, rs-r1774 → rs
    return re.sub(r'\d+$', '', part) or part  # rs-s86 → rs-s
```

Collapses `rs-s86`, `rs-r1774`, `rs-s-broken` → `rs`. `accel-300-` → `accel-300`.

## Constants That Control This

```
ACCEL_300_STANDALONE_BYPASS_ENABLED = False  # DISABLED — was 40% WR
ACCEL_300_STANDALONE_BYPASS_CONFIDENCE = 70
CONFLUENCE_REQUIRED = True
```

## RS Param Fixes Applied 2026-06-18 (Correct but Insufficient Alone)

| Constant | Was | Now | Effect |
|----------|-----|-----|--------|
| `RS_PROXIMITY_K` | 0.70 | 3.0 | Price can now be 3 ATRs from level (was 0.029% max distance — physically impossible) |
| `RS_BOUNCE_THRESH_ATR` | 1.0 | 0.33 | Touch gate = 0.067 ATR; bounce follow-through now achievable (was 3x — impossible) |
| `RS_TOUCH_HARD_CAP` | 120 | 200 | Unblocks best SHORT bucket (151-200 tc = 66.7% WR avg) |
| `RS_BROKEN_SHORT_ENABLED` | True | **False** | Was True despite comment saying "DISABLED" — counter-trend trap |
| `RS_BROKEN_RESISTANCE_LONG_ENABLED` | True | **False** | Counter-trend trap (BLUR/BRETT loss pattern) |

## Diagnosis Command

```python
python3 /root/.hermes/scripts/signal_compactor.py --verbose --dry 2>&1 | grep CONFLUENCE
```

Shows every confluence decision. All blocked signals show `BLOCK — need 2+ unique types`.

## What Would Fix It

| Option | Effect | Risk |
|--------|--------|------|
| Enable `ACCEL_300_STANDALONE_BYPASS_ENABLED=True` | Accel alone bypasses confluence → signals fire | Was disabled for 40% WR |
| Change pipeline order (signals_runner before compactor) | Signals persist longer as PENDING → more combo chance | Minor timing change |
| Widen confluence time window | Older signals combined with new ones | RS signals expire at 5 min anyway |
| Reduce confluence requirement to 1 unique type | RS or accel alone passes | Defeats filtering purpose |

## Related Files

- `signals/rs.py` — RS signal generator
- `signal_compactor.py` — Confluence gate logic (lines 538-599)
- `hermes_constants.py` — `ACCEL_300_STANDALONE_BYPASS_ENABLED`, `RS_PROXIMITY_K`, `RS_BOUNCE_THRESH_ATR`
