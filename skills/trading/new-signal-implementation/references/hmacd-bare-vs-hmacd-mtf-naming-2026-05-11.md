---
name: hmacd-bare-vs-hmacd-mtf-naming-2026-05-11
description: "Signal extraction naming: hmacd_bare vs hmacd_mtf — why they were renamed, how to avoid the collision."
category: trading
---

# hmacd_bare vs hmacd_mtf — Signal Extraction Naming (2026-05-11)

## What Happened

A signal was extracted from `signal_gen.py:_run_mtf_macd_signals()` into `signals/mtf_macd.py`. The extraction had a naming mismatch that caused ambiguity in the hot-set pipeline:

| Attribute | Original | After Fix |
|-----------|----------|-----------|
| signal_type (DB column) | `hmacd` | `hmacd_mtf` |
| source tag | `hmacd+` / `hmacd-` | `hmacd_mtf+` / `hmacd_mtf-` |
| registry name | `mtf_macd` | `hmacd_mtf` |
| kill-switch flag | HMACD_ENABLED | HMACD_ENABLED (same) |

Meanwhile, an existing `signals/hmacd.py` was already writing `signal_type='hmacd'` with source `hmacd+` / `hmacd-`. Two different detection logics writing the same `signal_type` — indistinguishable in DB, confusing in compactor.

## Why It Matters

When `signal_type` is `hmacd` for both bare and mtf variants:
- signal_compactor can't tell which logic fired
- SOURCE_BLACKLIST can't distinguish between them
- Hot-set shows `hmacd+` but you can't tell which signal actually wrote it
- Source tags in hot-set (`hmacd+,pct-hermes`) are ambiguous — which `hmacd+`?

## The Fix Applied

```
signals/hmacd.py    → signal_type = 'hmacd_bare',    source = 'hmacd_bare+', 'hmacd_bare-'
signals/mtf_macd.py → signal_type = 'hmacd_mtf',     source = 'hmacd_mtf+', 'hmacd_mtf-'
signals/__init__.py → registry name 'hmacd_mtf'       (was 'mtf_macd')
hermes_constants.py → blacklist entries renamed to 'hmacd_bare+-', 'hmacd_bare-+'
```

Both still use `HMACD_ENABLED` / `HMACD_PLUS_ENABLED` / `HMACD_MINUS_ENABLED` kill-switches — intentional sharing since they're the same signal family.

## The Naming Rule

When extracting a signal into a standalone file and registry entry:
1. Pick a `signal_type` name that is unique across ALL signals
2. Pick a `source` tag prefix that is unique
3. Make registry `name` match `signal_type`
4. Update ALL three atomically — never rename just one
5. Update blacklist comment entries in hermes_constants.py to match

```python
# Template for new signal extraction:
signal_type = '{family}_{variant}'      # e.g., 'hmacd_bare', 'hmacd_mtf'
source = f'{family}_{variant}-{dir_char}' # e.g., 'hmacd_bare+', 'hmacd_mtf+'

# Registry:
{'name': '{family}_{variant}', 'enabled': 'FLAG_ENABLED', 'run': _run}
```

## Key Distinction: hmacd_bare vs hmacd_mtf

| Aspect | hmacd_bare (hmacd.py) | hmacd_mtf (mtf_macd.py) |
|--------|----------------------|-------------------------|
| Entry trigger | 15m+1H histogram agreement only | z-score threshold (|z| > 2.0) + 15m+1H histogram |
| Confidence formula | `min(80, 50 + avg_hist*50)` | `min(75, 45 + (|z| - 2.0) * 10)` |
| MTF alignment boost | No | Yes (+5/+10 from `compute_mtf_macd_alignment`) |
| Cascade boost/block | No | Yes (+10 conf or block from `cascade_entry_signal`) |
| signal_type | `hmacd_bare` | `hmacd_mtf` |
| source prefix | `hmacd_bare+` / `hmacd_bare-` | `hmacd_mtf+` / `hmacd_mtf-` |

## Verification Commands

```bash
# Check registry has both
cd /root/.hermes/scripts && python3 -c "
from signals import SIGNAL_REGISTRY
for s in SIGNAL_REGISTRY:
    if 'hmacd' in s['name']:
        r = s['run']
        print(f\"{s['name']}: run={r.__name__ if r else None}\")
"

# Verify source tags are unique
grep "source = f'hmacd" signals/hmacd.py signals/mtf_macd.py

# Verify signal_type in add_signal calls
grep "signal_type='hmacd" signals/hmacd.py signals/mtf_macd.py

# Syntax check all modified files
cd /root/.hermes/scripts && python3 -m py_compile signals/hmacd.py signals/mtf_macd.py signals/__init__.py hermes_constants.py
```

## Related Reference Files

- `references/mtf-macd-signal-debug.md` — original debug session (2026-04-18), covers the `hmacd+` vs `hmacd-` merge artifact blacklist issue
- `references/mtf-macd-backtest-findings.md` — backtest results (83% WR, +1.394% avg), counterintuitive finding that signal is momentum continuation not mean-reversion