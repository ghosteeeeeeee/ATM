# hermes-signal-debugging — 2026-05-12 Session Addendum

## New Failure Modes Discovered

### 1. signal_compactor Timer Disabled → Stuck APPROVED Signals

**Symptom:** APEX SHORT, ZK LONG, LTC SHORT, FIL SHORT, SKY SHORT all stuck as APPROVED for 1+ hours, not expiring.

**Root cause:** `hermes-signal-compactor.timer` was **disabled since April 29** (`Deactivated successfully`). signal_compactor never runs → APPROVED signals never transition to EXPIRED.

**Why signals appear stuck:**
- signal_compactor does EXPIRED transitions (step 12: age_m >= 5 → EXPIRED)
- Without the timer firing, no new compaction runs → no EXPIRED transitions
- Old signals persist in DB as APPROVED indefinitely

**Diagnostic:**
```bash
systemctl status hermes-signal-compactor.timer | grep Active:
# → "inactive (dead)" = TIMER DISABLED (not waiting, actually dead)

journalctl -u hermes-signal-compactor.service --since "24 hours ago" | wc -l
# → 0 lines = timer has NOT fired in 24h
```

**Fix:**
```bash
systemctl enable hermes-signal-compactor.timer
systemctl start hermes-signal-compactor.timer
```

### 2. pump_hunter Bypasses Hot-Set Entirely

**Symptom:** ASTER SHORT traded at 04:26 without appearing in hotset.json.

**Root cause:** `pump_hunter.py` calls `_create_brain_record()` which does a direct PostgreSQL INSERT to `brain.trades` table, bypassing:
- signal_compactor (no hot-set entry)
- decider_run (no execution gate)
- confluence requirement
- WR filter

**Execution path:**
```
hermes-pump-hunter.timer → pump_hunter.py --live → _create_brain_record()
                                                  → direct PostgreSQL INSERT
```

**Fix:** pump_hunter should write to signals DB like other signal scripts, not directly to brain DB.

### 3. trend_purity Requirement Not Honored

**Symptom:** Single-source signals (accel-300+) reaching hot-set despite trend_purity being required for all entries since 2026-05-12.

**Root cause:** The signals in hot-set (ZK, 2Z) predate the trend_purity requirement change. signal_compactor timer was disabled → the new trend_purity filter never ran on those tokens.

### 4. hh_hl SHORT Bounce Problem

**Symptom:** hh_hl SHORT fires at bounce point (price approaches LL from below), price bounces up 99% of the time.

**Fix applied (2026-05-12):** Range-position filter in `signals/hh_hl.py`:
- SHORT blocked if `price > recent_high - atr` (too close to top of range = bounce territory)
- LONG blocked if `price < recent_low + atr` (too close to low = no breakout room)

## Key Diagnostic Query — Stuck Signals

```python
conn = sqlite3.connect('/root/.hermes/data/signals_hermes_runtime.db')
c = conn.execute("""
    SELECT token, direction, decision, source, created_at,
           ROUND((julianday('now') - julianday(created_at)) * 1440, 1) as age_min
    FROM signals
    WHERE decision='APPROVED' AND executed=0
    ORDER BY age_min DESC
""")
# age_min > 60 = stuck (should have been expired by signal_compactor)
```

## Timer Checklist (always check first)

When signals appear stuck or hot-set is empty:
1. `systemctl status hermes-pipeline.timer`
2. `systemctl status hermes-signal-compactor.timer` ← most commonly disabled
3. `systemctl list-timers | grep hermes`
4. Check journal for recent firings

**Timer states:**
- `active (waiting)` = running correctly
- `inactive (dead)` = DISABLED, not just waiting to fire