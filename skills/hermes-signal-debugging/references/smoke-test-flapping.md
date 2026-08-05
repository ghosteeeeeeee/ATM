# smoke_test no_flapping False Positive (2026-05-16)

## Problem
`[FAIL] no_flapping: Pipeline flapping: 60 cycles in last 60min (>55 threshold)`

Pipeline was running normally — exactly 1 cycle/min = 60 cycles in 60 min. The
check threshold was 55, which is below what clean normal operation looks like.

## Root Cause
smoke_test.py `check_no_flapping()` threshold was 55, but a healthy 1-cycle/min
pipeline produces 60 completions per hour. The comment said "60/min max" but
the actual threshold was set below that number.

## Fix
Patch `/root/.hermes/scripts/smoke_test.py`:

```python
# OLD (line 476-478):
if completions > 55:
    return False, f"Pipeline flapping: {completions} cycles in last 60min (>55 threshold)"

# NEW:
if completions > 65:
    return False, f"Pipeline flapping: {completions} cycles in last 60min (>65 threshold)"
```

Threshold bumped from 55 → 65. Allows some overrun above 60 without false-positive.
Also updated comment to reflect reality: "60/min normal" not "60/min max".

## Verification
```bash
python3 smoke_test.py 2>&1 | grep no_flapping
# [PASS] no_flapping: pipeline stable (60 cycles, 0 restarts)
```

## Lesson
Flapping check counts "Pipeline done" entries with timestamps in last 60 min.
Threshold must be above the expected rate (60/min) to avoid false positives on
healthy pipelines. 65 gives 5-min headroom above normal.