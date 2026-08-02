# Graceful Escalation & De-Escalation Protocol for Counter-Regime Signals

## What to Fix

### Hard-Block #1: `ai_decider.py` lines 2696-2703
```
# HARD BLOCK: If market regime is against the trade direction, skip it entirely
if (regime == "LONG_BIAS" and decision == "short") or \
   (regime == "SHORT_BIAS" and decision == "long"):
    decision = "wait"
    confidence = 0   ← THIS IS THE HARD-BLOCK
```

### Hard-Block #2: `decider_run.py` lines 1463-1473
```
if regime == 'NEUTRAL' and regime_conf > 60:
    block ← hard block
if regime_conf < 50:
    block ← hard block
```

### Graceful-Penalty Region: `decider_run.py` lines 1474-1484 (ALREADY GRACEFUL — keep this)
```
counter-regime → penalize 40% of regime_conf (max 30pts) → if still above MIN_EXEC → execute
```

---

## The Protocol

### On Entry (ai_decider.py compaction)
- Counter-regime signals enter hot-set at `confidence - 15%` (already done via LLM prompt penalty)
- Survival bonus still applies: `1.0 + (compact_rounds * 0.10)` capped at 1.5x
- Staleness decay starts: `0.95 ^ hours_old` after 2h
- They compete fairly for top-20 — they can win if strong enough

### During Execution (decider_run.py)
- Counter-regime: penalize `min(regime_conf * 0.4, 30)` pts from confidence
- If resulting confidence ≥ MIN_EXEC_CONFIDENCE → EXECUTE
- If below MIN_EXEC_CONFIDENCE → de-escalate to PENDING, don't hard-block
- NEUTRAL regime with weak conf → de-escalate, don't hard-block

### On Exit (graceful de-escalation)
- APPROVED but not executed after N cycles → de-escalation score applies
- `effective_conf = raw_conf * (0.88 ** hot_cycle_count)` — signals fade organically
- After 5 de-escalation cycles → state returns to PENDING (not rejected)
- New signal for same token resets de-escalation state

---

## Changes Required

### 1. ai_decider.py — Remove hard-block at line 2696-2703
Replace with graceful penalty:
```python
# GRACEFUL REGIME ALIGNMENT: penalize counter-regime decisions
# Don't hard-block — let strong signals survive
if decision != "wait" and regime != "NEUTRAL" and regime_conf > 50:
    if (regime == "LONG_BIAS" and decision == "short") or \
       (regime == "SHORT_BIAS" and decision == "long"):
        # Fighting the regime — penalize but don't block
        penalty = min((regime_conf - 50) // 3, 25)  # up to 25pt penalty
        confidence = max(10, confidence - penalty)
        # Let it compete — if it's still strong it stays in hot-set
```

### 2. decider_run.py — Remove NEUTRAL/weaker hard-blocks (lines 1463-1473)
Keep the Case 4 graceful penalty (1474-1484). Replace Cases 2 & 3 with de-escalation:
```python
# Case 2: NEUTRAL regime — de-escalate, don't hard-block
if regime == 'NEUTRAL' and regime_conf > 60:
    # De-escalate: back to PENDING, not executed
    log(f'  📉 [DEESC] {token} {direction} de-escalated: NEUTRAL regime')
    # Don't mark_executed — let it come back naturally
    # Signal stays alive in pipeline
    continue

# Case 3: weak regime confidence — de-escalate, don't hard-block  
if regime_conf < 50:
    log(f'  📉 [DEESC] {token} {direction} de-escalated: weak regime conf ({regime_conf:.0f}%)')
    continue
```

### 3. decider_run.py — Case 4 already graceful — ensure MIN_EXEC threshold is the only gate
The penalty at 1474-1484 is already graceful. The check at 1479 (`confidence < MIN_EXEC_CONFIDENCE`) 
is a soft floor, not a regime hard-block — this is fine to keep.

### 4. Add de-escalation state tracking to signals
Add columns if not present:
- `escalation_state` TEXT DEFAULT 'normal'  ('normal' | 'deescalating')
- `deescalation_score` REAL DEFAULT 1.0

Update on each APPROVED cycle without execution:
```sql
UPDATE signals 
SET deescalation_score = deescalation_score * 0.88,
    escalation_state = CASE WHEN deescalation_score * 0.88 < 0.3 THEN 'deescalating' ELSE 'normal' END
WHERE decision = 'APPROVED' AND executed = 0 AND hot_cycle_count > 0
```

---

## Files to Modify
1. `/root/.hermes/scripts/ai_decider.py` — remove hard-block (line ~2696)
2. `/root/.hermes/scripts/decider_run.py` — replace hard-blocks with de-escalation (lines ~1463)
