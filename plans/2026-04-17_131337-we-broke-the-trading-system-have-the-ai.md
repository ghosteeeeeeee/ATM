# Plan: Fix Hot-Set → Trades Pipeline
**Date:** 2026-04-17
**Status:** PLANNING ONLY — do not execute

---

## Actual Architecture (Corrected)

```
signal_gen.py (every 1 min) → signals DB (PENDING)
                                     ↓
signal_compactor.py (every 5 min) → APPROVED signals + hotset.json
                                     ↓
decider_run.py (every 1 min via hermes-pipeline.timer) → picks APPROVED → brain.py → mirror_open → HL
                                     ↓
hl-sync-guardian.py (every 2 min) → BACKUP: mirrors paper trades to HL, hard closes
```

**Who places live orders:** `decider_run.py` is the primary execution path. Guardian is emergency backup.

---

## Root Causes Found

### CRITICAL BUG #1 (Root Cause of No Orders): `sl` Unassigned in Non-Pump Trades

**File:** `/root/.hermes/scripts/decider_run.py`, line ~553

**The actual crash:**
```
UnboundLocalError: cannot access local variable 'sl' where it is not associated with a value
```

**Root cause:** In `execute_trade()`, `sl` is only assigned inside the `if is_pump:` block. When `is_pump=False` (normal trades), the `else:` branch only sets `sl_pct_val` — a completely different variable. `sl` is never defined:

```python
# Line 536-550:
if is_pump:
    ...
    sl = round(price * (1 - PUMP_SL_PCT), 8)   # sl IS defined here
    tp = round(price * (1 + PUMP_TP_PCT), 8)   # tp IS defined here
else:
    # A/B TEST DISABLED (2026-04-17) — ATR handles SL/TP via position_manager.
    sl_pct_val = 0.0   # ← sl is NOT defined here!
    tp_pct_val = 0.0   # ← tp is NOT defined here!

# Line 553:
if sl > 0 and direction == 'LONG' and sl >= price:   # 💥 CRASH — sl doesn't exist!
```

**Every single trade is a non-pump trade** (the `source` is `hzscore+`, not `pump-*`). So ALL trades crash at the SL sanity check.

**Fix:** Initialize `sl` and `tp` before the if/else, or move the SL sanity check inside the if/else blocks.

---

### CRITICAL BUG #2: `hot_cycle_count` Never Incremented

**File:** `/root/.hermes/scripts/signal_compactor.py`, lines ~423-432

`signal_compactor` increments `compact_rounds` but never increments `hot_cycle_count`. Guardian's gate at line 1902 (`WHERE hot_cycle_count >= 1`) is permanently closed.

**Impact:** Guardian's backup mirroring path is blocked. (decider_run is the primary path and is not affected by this, but it's good to fix for defense-in-depth.)

**Fix:** Add `hot_cycle_count = COALESCE(hot_cycle_count, 0) + 1` to the APPROVED UPDATE.

---

### CRITICAL BUG #3: Confluence Filter Removed

**File:** `/root/.hermes/scripts/signal_compactor.py`, lines ~198-203

The confluence filter was "REMOVED 2026-04-17". All 20 hot-set entries are single-source. T requires 2+ sources for confluence.

**Additional problem:** Query window is `-5 minutes` but signals persist for 1 hour. Need 60-min window.

**Fix:**
1. Change window from `-5 minutes` to `-60 minutes`
2. Add `HAVING COUNT(DISTINCT source) >= 2` after GROUP BY
3. Apply +5% score bonus for multi-source confluence

---

### CRITICAL BUG #4: `_get_fills_cached()` Returns `[]` on Rate Limit

**File:** `/root/.hermes/scripts/hl-sync-guardian.py`, lines ~686-711

When 3 API calls/60s are exhausted, function returns `[]` instead of returning cached fills. Breaks Step 8 phantom close detection.

**Fix:** Return cached fills even when rate-limited.

---

## Step-by-Step Fix Plan

### Step 1: Fix `sl` UnboundLocalError — THE PRIMARY FIX

**File:** `/root/.hermes/scripts/decider_run.py`
**Location:** Lines ~525-555 (execute_trade function)

**Problem:** `sl` and `tp` are only assigned in the `if is_pump:` block but referenced after the if/else.

**Fix — initialize sl and tp before the if/else:**
```python
# Initialize defaults (will be overwritten in is_pump branch)
sl = 0.0
tp = 0.0
sl_pct_val = 0.0
tp_pct_val = 0.0

if is_pump:
    sl_pct_val = PUMP_SL_PCT
    tp_pct_val = PUMP_TP_PCT
    trailing_activation = 0
    trailing_distance = 0
    if direction == 'LONG':
        sl = round(price * (1 - PUMP_SL_PCT), 8)
        tp = round(price * (1 + PUMP_TP_PCT), 8)
    else:
        sl = round(price * (1 + PUMP_SL_PCT), 8)
        tp = round(price * (1 - PUMP_TP_PCT), 8)
    log(f'  [PUMP MODE] {token} {direction} — SL={PUMP_SL_PCT*100:.1f}% TP={PUMP_TP_PCT*100:.1f}% NO trailing')
else:
    sl_pct_val = 0.0  # defer to ATR via position_manager
    tp_pct_val = 0.0

# Now sl and tp are always defined:
if sl > 0 and direction == 'LONG' and sl >= price:
    sl = price * 0.99
    log(f'  [WARN] SL sanity check triggered for LONG {token}, reset to 1%')
elif direction == 'SHORT' and sl <= price:
    sl = price * 1.01
    log(f'  [WARN] SL sanity check triggered for SHORT {token}, reset to 1%')
```

**Verification:**
```bash
cd /root/.hermes/scripts && python3 decider_run.py 2>&1 | tail -20
# Should NOT crash — should show trade attempts hitting brain.py
```

---

### Step 2: Fix `hot_cycle_count` in signal_compactor.py

**File:** `/root/.hermes/scripts/signal_compactor.py`, lines ~423-432

**Add `hot_cycle_count` increment to APPROVED UPDATE:**
```python
c.execute(f"""
    UPDATE signals
    SET decision = 'APPROVED',
        compact_rounds = COALESCE(compact_rounds, 0) + 1,
        hot_cycle_count = COALESCE(hot_cycle_count, 0) + 1,
        updated_at = CURRENT_TIMESTAMP
    WHERE id IN ({placeholders})
""", approved_ids)
```

**Also:** Change query window from `-5 minutes` to `-60 minutes` at lines ~175 and ~408.

**Verification:**
```bash
python3 /root/.hermes/scripts/signal_compactor.py --verbose
sqlite3 /root/.hermes/data/signals_hermes_runtime.db \
  "SELECT hot_cycle_count, COUNT(*) FROM signals WHERE decision='APPROVED' GROUP BY hot_cycle_count"
# Should show hot_cycle_count >= 1
```

---

### Step 3: Fix Confluence Filter in signal_compactor.py

**3A. Change window (lines ~175, ~408):**
```sql
AND created_at > datetime('now', '-60 minutes')
```

**3B. Add HAVING after GROUP BY (line ~181):**
```sql
GROUP BY token, direction
HAVING COUNT(DISTINCT source) >= 2
```

**3C. Score bonus for multi-source (line ~135):**
```python
source_count = len(set(source.split(','))) if source else 0
source_mult = 1.05 if source_count >= 2 else 0.0
```

**Verification:**
```bash
cat /var/www/hermes/data/hotset.json | python3 -c "
import json,sys; d=json.load(sys.stdin)
for e in d['hotset']:
    n=len([s for s in e.get('source','').split(',') if s])
    tag = '✓' if n>=2 else '✗ SINGLE-SOURCE'
    print(f\"{e['token']:8} sources={n} {tag}\")
"
```

---

### Step 4: Fix `_get_fills_cached()` Rate Limit

**File:** `/root/.hermes/scripts/hl-sync-guardian.py`, lines ~686-711

**Current:**
```python
if count >= _MAX_API_CALLS_PER_CYCLE:
    return []
```

**Fix:**
```python
if count >= _MAX_API_CALLS_PER_CYCLE:
    if cache_key in _FILL_CACHE:
        cached = _FILL_CACHE[cache_key]
        if now - cached['fetched_at'] < _FILL_CACHE_TTL:
            return cached['fills']
    return []
```

---

## Files to Change

| File | Changes |
|------|---------|
| `/root/.hermes/scripts/decider_run.py` | Bug #1: Initialize `sl`, `tp` before if/else |
| `/root/.hermes/scripts/signal_compactor.py` | Bug #2: `hot_cycle_count`, Bug #3: confluence + 60-min window |
| `/root/.hermes/scripts/hl-sync-guardian.py` | Bug #4: `_get_fills_cached` rate limit |

---

## Fix Order

**Fix #1 (decider_run `sl` crash) must be done FIRST** — it's the actual reason no orders are being placed. The other bugs are secondary improvements.

---

## Verification Steps

1. **After Bug #1 fix:**
   ```bash
   cd /root/.hermes/scripts && python3 decider_run.py 2>&1 | grep -E "EXEC|ENTERED|FAILED|brain.py|SL=|TP="
   # Should show trades being attempted (even if they fail for other reasons)
   ```

2. **After Bug #2 fix:**
   ```bash
   python3 /root/.hermes/scripts/signal_compactor.py
   sqlite3 /root/.hermes/data/signals_hermes_runtime.db \
     "SELECT hot_cycle_count, COUNT(*) FROM signals WHERE decision='APPROVED' GROUP BY hot_cycle_count"
   ```

3. **After Bug #3 fix:**
   ```bash
   cat /var/www/hermes/data/hotset.json | python3 -c "
   import json,sys; d=json.load(sys.stdin)
   for e in d['hotset']:
       n=len([s for s in e.get('source','').split(',') if s])
       print(f\"{e['token']:8} sources={n}\")
   "
   ```
