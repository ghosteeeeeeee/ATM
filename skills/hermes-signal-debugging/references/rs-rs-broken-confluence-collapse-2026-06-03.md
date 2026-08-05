# RS-R / RS-S-BROKEN Confluence Collapse Bug — 2026-06-03

## Symptoms
`rs-r86,rs-s-broken` treated as 2 unique signal types → passed confluence gate.
14 losing SHORT trades fired on 2026-06-03 between 05:38-07:19 UTC with this source
signature. These were bounce-fade shorts — price had recovered above broken support
but the broken-path SHORT was firing alongside a normal-resistance SHORT.

## Root Cause
`_signal_type_key()` in `signal_compactor.py` (line ~558) stripped trailing digits
(`rs-s386 → rs-s`) but did NOT strip:
1. The `-broken` suffix: `rs-s-broken → rs-s-broken` (not `rs-s`)
2. The directional suffix on resistance: `rs-r86 → rs-r` (correct, but different from `rs-s`)

Result: `rs-s-broken` and `rs-r` were counted as two distinct signal types when they
are the same signal family (support/resistance). They should collapse to `rs`.

## The Fix
```python
# In _signal_type_key() inside signal_compactor.py
part = re.sub(r'-broken$', '', part)           # rs-s-broken → rs-s
part = re.sub(r'^rs-[sr]', 'rs', part)        # rs-s, rs-r → rs
return re.sub(r'\d+$', '', part) or part       # strip trailing digits
```

## Before / After

| Source | Before (unique types) | After (unique types) |
|--------|----------------------|---------------------|
| `rs-r86,rs-s-broken` | 2 → PASS | 1 → BLOCK |
| `rs-r86,accel-300` | 2 → PASS | 2 → PASS |
| `rs-s386,rs-s406` | 2 → PASS | 1 → BLOCK (same level) |

## Verification
```python
import re

def _signal_type_key(part):
    part = re.sub(r'-broken$', '', part)
    part = re.sub(r'^rs-[sr]', 'rs', part)
    return re.sub(r'\d+$', '', part) or part

# Block test
parts = ['rs-r86', 'rs-s-broken']
assert len(set(_signal_type_key(p) for p in parts)) == 1  # 1 type = blocked

# Pass test
parts = ['rs-r86', 'accel-300']
assert len(set(_signal_type_key(p) for p in parts)) == 2  # 2 types = pass
```

## File Changed
`/root/.hermes/scripts/signal_compactor.py` — `_signal_type_key()` function (~line 558)

## Lessons
- Directional sub-prefixes (`rs-s`, `rs-r`) must normalize to the same base family
  when the path modifier (`-broken`) is involved. Different directions of the same
  signal family are NOT real confluence.
- The trailing-digit strip alone was insufficient — signal modifiers like `-broken`
  create new type strings that appear distinct but represent the same signal concept.
- Counter-regime signals (bounce against broken support) should not pass confluence
  by combining broken-path + opposite-direction normal path.