---
name: wave-phase-hotset-debug
description: Debug wave_phase in hot-set JSON — when all tokens show "neutral" or default values despite speed_tracker running. Found and fixed 2026-04-16.
category: trading
---

# Wave-Phase Hot-Set Debug Skill

## Symptom

All tokens in `/var/www/hermes/data/hotset.json` show `wave_phase: "neutral"` (or other default values like `speed_percentile: 50`, `momentum_score: 50`, `price_acceleration: 0`). But SpeedTracker is running and updating 500+ tokens.

## Root Cause

`ai_decider.py` creates a SpeedTracker singleton and calls `get_all_speeds()` **without first calling `.update()`. SpeedTracker `_speeds` dict starts empty `{}` — `get_all_speeds()` returns empty dict → all tokens get default values in the hot-set JSON.

## Bug Location

`ai_decider.py` line ~1741:
```python
# BEFORE (broken):
_speed_cache = speed_tracker_ai().get_all_speeds()

# AFTER (fixed):
_speed_tracker = speed_tracker_ai()
_speed_tracker.update()   # MUST call update() first
_speed_cache = _speed_tracker.get_all_speeds()
```

## Why This Happens

SpeedTracker is a lazy tracker:
1. `__init__()` creates empty `_speeds = {}`
2. `.update()` fetches prices, computes velocity/acceleration/wave_phase for all tokens, populates `_speeds`
3. `get_all_speeds()` returns `_speeds` (which is empty if update() was never called)
4. `ai_decider.py` uses a module-level singleton (`_get_speed_tracker()`) so the same instance is reused across compaction cycles — but if the FIRST call is `get_all_speeds()` before any `.update()`, all subsequent calls still see empty `_speeds`

## How to Diagnose

```bash
# Step 1: Check hot-set for all-neutral wave_phase
cat /var/www/hermes/data/hotset.json | python3 -c "
import json, sys
data = json.load(sys.stdin)
non_neutral = [e for e in data['hotset'] if e.get('wave_phase') != 'neutral']
print(f'Total: {len(data[\"hotset\"])}, Non-neutral: {len(non_neutral)}')
for e in data['hotset'][:5]:
    print(f'  {e[\"token\"]} WAVE={e.get(\"wave_phase\")} MOM={e.get(\"momentum_score\")} SPD={e.get(\"speed_percentile\")}')
"

# Step 2: Check speed_tracker is actually computing real values
cd /root/.hermes/scripts && python3 -c "
from speed_tracker import SpeedTracker
st = SpeedTracker()
st.update()  # KEY: must call update first
speeds = st.get_all_speeds()
non_neutral = [(k,v) for k,v in speeds.items() if v.get('wave_phase','neutral') != 'neutral']
print(f'Total tokens: {len(speeds)}, Non-neutral wave_phase: {len(non_neutral)}')
for k,v in non_neutral[:5]:
    print(f'  {k}: {v.get(\"wave_phase\")} accel={v.get(\"price_acceleration\")} vel={v.get(\"price_velocity_5m\")}')
"

# Step 3: Check ai_decider's speed_cache BEFORE FIX (will show empty or all defaults)
# Run ai_decider compaction and grep for wave in output
```

## All Wave-Phase Bugs (2026-04-16 Session)

### Bug 1: ai_decider not calling .update() before get_all_speeds()
- **File:** `ai_decider.py` line ~1741
- **Symptom:** All hot-set tokens have `wave_phase=neutral`, `speed_percentile=50`, `momentum_score=50`
- **Fix:** Add `_speed_tracker.update()` before `_speed_tracker.get_all_speeds()`
- **Status:** FIXED 2026-04-16

### Bug 2: Prompt wave_phase vocabulary mismatch
- **File:** `prompt/main-prompt.md` line 117
- **Symptom:** Prompt tells LLM wave_phase uses `emerging/building/peaking/declining/neutral` but speed_tracker actually computes `accelerating/decelerating/bottoming/falling/neutral`
- **Fix:** Update prompt schema to match actual values from speed_tracker.py
- **Status:** FIXED 2026-04-16

### Bug 3: ai_decider reads/writes wrong key `wave` instead of `wave_phase`
- **Files:** `ai_decider.py` lines ~1321 and ~1687
- **Symptom:** LLM prompt for survivors received `wave=unknown` instead of real wave_phase because code read `s.get('wave')` but hotset.json has `s['wave_phase']`. Also intermediate hotset_entries dict used `wave`/`momentum`/`speed`/`overextended` keys instead of canonical `wave_phase`/`momentum_score`/`speed_percentile`/`is_overextended`.
- **Root cause:** Two intermediate code paths (survivor prompt builder at line 1321, and hotset_entries dict builder at line 1687) used abbreviated/old key names while the final hotset.json write (line 1867) used correct canonical keys. The bug was SILENT because the final write was correct — but the LLM was fed wrong data.
- **Fix:** Standardize all three code paths to use canonical keys:
  - Line 1321: `s.get('wave_phase', 'neutral')` (not `s.get('wave', 'unknown')`)
  - Line 1687: `'wave_phase': s.get('wave_phase', 'neutral')` (not `'wave': s.get('wave', 'unknown')`)
- **Status:** FIXED 2026-04-16

### Bug 4: LLM-parsed wave has no vocabulary validation
- **File:** `ai_decider.py` lines ~1512-1513
- **Symptom:** LLM could return `WAVE=ACCELERATING` (uppercase) or `WAVE=acceleratingg` (typo) and it would pass through without validation
- **Fix:** Normalize to lowercase and validate against 5 valid values

## Verify Fix Worked

```bash
# After fix, run ai_decider compaction directly
cd /root/.hermes/scripts && timeout 120 python3 -c "
import sys; sys.path.insert(0,'.')
from ai_decider import _do_compaction_llm
_do_compaction_llm()
" 2>&1 | grep -E "WAVE|hotset.json|wave"

# Then check hot-set JSON
cat /var/www/hermes/data/hotset.json | python3 -c "
import json, sys
data = json.load(sys.stdin)
non_neutral = [e for e in data['hotset'] if e.get('wave_phase') != 'neutral']
print(f'Non-neutral: {len(non_neutral)}/{len(data[\"hotset\"])}')
"
```

## Vocabulary Reference

speed_tracker.py wave_phase values (line ~172-183):
- `accelerating` = vel > 0 AND accel > 0 (rising momentum)
- `decelerating` = vel > 0 AND accel < 0 (momentum peaking)
- `bottoming` = vel < 0 AND accel > 0 (reversal imminent)
- `falling` = vel < 0 AND accel < 0 (down momentum continuing)
- `neutral` = insufficient data or flat

## Key Debugging Insight: hotset.json Is Ground Truth

The LLM output showed `WAVE=neutral` for all tokens — but this was the LLM's own assessment, NOT the actual data. The hotset.json (written by Python) was correct (16/17 non-neutral). Always verify against hotset.json, not LLM output.

Also: run the compaction directly instead of waiting for the 10-minute timer:
```bash
cd /root/.hermes/scripts && timeout 120 python3 -c "
import sys; sys.path.insert(0,'.')
from ai_decider import _do_compaction_llm
_do_compaction_llm()
" 2>&1
```

## Related Files

- `/root/.hermes/scripts/speed_tracker.py` — wave_phase computation (line ~160-183)
- `/root/.hermes/scripts/ai_decider.py` — hot-set JSON builder (3 code paths: ~1321 survivor prompt, ~1687 hotset_entries, ~1867 final write)
- `/root/.hermes/scripts/decider_run.py` — reads from hotset.json at ~line 911
- `/root/.hermes/prompt/main-prompt.md` — LLM prompt (wave schema line 117)
- `/var/www/hermes/data/hotset.json` — output hot-set (ground truth)
