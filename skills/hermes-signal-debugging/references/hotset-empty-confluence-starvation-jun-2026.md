# Hot-Set Empty / Confluence Starvation (2026-06-15)

## Session Summary

signals.json state at 2026-06-15 02:33 UTC:
```
pending: 14  (all single-source — waiting for co-signal)
expired: 200  (all single-source — never got co-signal in 5 min)
hot_set:  0  (empty)
```

## Root Causes

### 1. RS Signal Collapse Bug
Multi-level RS signals (e.g., `rs-r12,rs-r8`) collapse to single `rs` type via `_signal_type_key()` in signal_compactor.py lines 541-565. All 13 expired multi-RS signals were blocked despite appearing multi-source.

Example: `rs-r12,rs-r8` → both collapse to `rs` → 1 unique type → CONFLUENCE-GATE-BLOCK

See: `hermes-hot-set/references/rs-signal-collapse-confluence-jun-2026.md`

### 2. ACCEL_300_STANDALONE_BYPASS Is Disabled
hermes_constants.py line 730: `ACCEL_300_STANDALONE_BYPASS_ENABLED = False`
When enabled, pure accel-300 at ≥70% confidence could bypass confluence. Disabled after 40% WR pure-accel trades.

### 3. Signal Timing Gap
accel-300 fires frequently (162 expired single-source). RS fires rarely (needs 80+ touches). They rarely arrive within the same 5-min window for the same token+direction.

## Key Constants

```python
# hermes_constants.py
ACCEL_300_STANDALONE_BYPASS_ENABLED = False  # line 730
ACCEL_300_STANDALONE_BYPASS_CONFIDENCE = 70   # not used when disabled
RS_DECIDER_MIN_TOUCHES = 80   # RS needs 80+ touches to fire
RS_TOUCH_HARD_CAP = 120       # block at 120+ touches
RS_DECIDER_CONF_FLOOR = 60    # below this confidence → blocked
CONFLUENCE_REQUIRED = True    # 2+ unique signal types required
```

## Diagnostic

```bash
# Hot-set empty?
cat /var/www/hermes/data/hotset.json

# Pending signals (waiting for co-signal)
python3 -c "
import json
d = json.load(open('/var/www/hermes/data/signals.json'))
for s in d['pending']:
    print(f'PENDING: {s[\"token\"]} {s[\"direction\"]} conf={s[\"confidence\"]} src={s[\"source\"]}')
"

# Multi-RS signals blocked by collapse
python3 -c "
import json, re
d = json.load(open('/var/www/hermes/data/signals.json'))
def collapse(src):
    parts = src.split(',')
    collapsed = []
    for p in parts:
        p = re.sub(r'-broken\$', '', p)
        p = re.sub(r'^rs-[sr]', 'rs', p)
        p = re.sub(r'\d+\$', '', p) or p
        collapsed.append(p)
    return collapsed
for s in d['expired']:
    if ',' in s['source']:
        c = collapse(s['source'])
        if len(set(c)) == 1:
            print(f'COLLAPSE-BLOCKED: {s[\"token\"]} {s[\"source\"]} -> {set(c)}')
"
```
