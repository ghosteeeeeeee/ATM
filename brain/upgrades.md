# Hermes Upgrade Plan
**Last updated:** 2026-04-05 20:34 UTC
**Status:** ACTIVE — Flip deployed and verified

---

## 1. OpenClaw Agent Upgrade

### 1.1 Tokyo → Dallas Sync
- **Status:** ✅ COMPLETE (2026-04-05)
- **What:** OpenClaw workspace on Tokyo (`root@117.55.192.97`) rsyncs to Dallas (`root@104.248.120.52`) every 5 minutes via cron
- **Sync path:** `/root/.hermes/` (excluding `__pycache__/`, `*.pyc`, `.git/`, `brain/`, `logs/`)
- **Dallas workspace:** `/root/hermes_workspace/` (dedicated, separate from other projects)
- **Verification:** `ls /root/hermes_workspace/` on Dallas shows Hermes files

### 1.2 OpenClaw Model Strategy
- **Current:** OpenClaw manages its own model selection via `litellm-ride` skill (routes to OpenRouter)
- **Goal:** OpenClaw handles non-trading tasks; Hermes handles all trading automation
- **Boundary:** OpenClaw can query/read Hermes state but NEVER executes trades

---

## 2. Trading Pipeline Upgrade

### 2.1 Signal Direction Flip (WR Incident Fix)

**Root Cause:** Win-rate analysis showed 10.6% WR across 2000 fills (Mar 10-25 2026), suggesting signals may be direction-inverted.

**Fix:** Flip all signal directions before execution.

#### Code Change (decider-run.py)
```python
# Line 28
_FLIP_SIGNALS = True

# Lines 1371-1375 (inside approved-signals execution loop)
flipped_direction = None
if _FLIP_SIGNALS:
    flipped_direction = 'SHORT' if direction == 'LONG' else 'LONG'
    log(f'  [FLIP] {token} {direction} → {flipped_direction} (WR incident fix)')
    direction = flipped_direction
```

#### Skill: signal_flip
```
/root/.hermes/scripts/signal_flip.py [on|off|status]
```
- `on`  → sets `_FLIP_SIGNALS = True`
- `off` → sets `_FLIP_SIGNALS = False`
- `status` → shows current state

#### Bug Fixed During Deployment
- **Error:** `TypeError: log() takes 1 positional argument but 2 were given`
- **Cause:** FLIP log line had spurious `'WARN'` second argument
- **Fix:** Removed extra argument from `log()` call at line 1374
- **Result:** ✅ Verified 2026-04-05 20:34 — AAVE LONG→SHORT, MORPHO LONG→SHORT both flipped and executed

#### Flip Behavior
- Every approved signal direction is reversed before execution
- `[FLIP] {token} {orig_dir} → {new_dir} (WR incident fix)` appears in pipeline log
- Applies to ALL signal sources (hot-set, hmacd, hzscore, etc.)
- Toggle with `signal_flip.py on/off`

#### Current Status (2026-04-05 20:34)
- **Flip:** ENABLED (`_FLIP_SIGNALS = True`)
- **Test trades executed:** AAVE SHORT, MORPHO SHORT (both flipped from LONG, 10/10 positions filled)
- **Blocking issue:** All hot-set tokens blocked by `speed=0%` (stale token filter) — speed tracker recovers when tokens move
- **Flip verified:** Working — 2 trades flipped and entered

### 2.2 Pipeline Crash Fix (decider-run.py line 1439)

**Symptom:** `decider-run.py` crashes at line 1439 (`if __name__ == '__main__'`) with no exception content visible in logs

**Root Cause:** `log()` function takes 1 argument, but FLIP message was passing 2 (`'WARN'`)

**Fix:** Removed extra argument — see 2.1 above

**Verification:** `decider-run.py` now runs to completion: `=== Decider Done: 2 entered | 0 skipped`

---

## 3. Known Issues

### 3.1 Speed Tracker Staleness (ALL hot-set tokens blocked)
- **Symptom:** Every token in hot-set shows `speed=0% (stale token)` and is hard-banned from execution
- **Cause:** SpeedTracker marks tokens as stale if no significant price movement detected
- **Recovery:** Speed recalculates every ~5 min as price data updates; tokens recover naturally when market moves
- **Impact:** No new approvals possible until speed recovers (~minutes to hours)
- **Note:** This is not a bug — it's an intentional filter to avoid trading dead tokens

### 3.2 Hot-Set Staleness (RESOLVED)
- **Symptom:** hotset.json age >11 min triggered staleness warning, blocking approvals
- **Root Cause:** Pipeline crash at 20:17 prevented ai_decider from writing fresh hotset.json; `hotset_last_updated.json` was updated but `hotset.json` was not
- **Resolution:** Manual write at 20:25; systemd service restarted at 20:31 — hot-set now refreshing normally
- **Fix needed:** hotset_last_updated.json and hotset.json writes should be atomic (both in same try/except)

### 3.3 decider-run Crash Loop (RESOLVED)
- **Symptom:** Crash at line 1439 on every run after pipeline restart
- **Root Cause:** log() TypeError in FLIP code
- **Fix:** Removed extra argument from log() call
- **Status:** RESOLVED

---

## 4. Deployment Checklist

- [x] signal_flip.py skill created
- [x] _FLIP_SIGNALS = True hardcoded in decider-run.py
- [x] FLIP log message added
- [x] log() TypeError fixed
- [x] Flip verified working (live execution)
- [ ] Update INCIDENT_WR_FAILURE.md with fix summary
- [ ] Disable flip if WR doesn't improve after 20 trades

---

## 5. Monitoring

### How to Watch the Flip
```bash
tail -f /root/.hermes/logs/pipeline.log | grep -E "FLIP|Decider"
```

### How to Disable Flip
```bash
/root/.hermes/scripts/signal_flip.py off
```

### Key Metrics to Watch
- Win rate on flipped trades (should improve from 10.6% if direction-inverted hypothesis correct)
- Position count (10/10 = full, flip can't fire on new entries until slots free)
- Hot-set age (< 11 min = fresh, > 11 min = stale, blocking)
- Speed filter: tokens with `speed=0%` are hard-blocked
