# Spec: AI Decision Making — Rule-Based Context Gate

**Date:** 2026-07-28
**Status:** SPEC COMPLETE — awaiting review
**Replaces:** Proposal 2 from `2026-07-28_winrate-improvement-plan.md`

---

## Problem

The system has 28+ checks before `execute_trade()` but they're scattered across two phases (`_run_hot_set()` eligibility and `run()` execution gate) with no unified "should we trade this?" decision. Key surfing principles are unimplemented at entry time:

| Surfing Rule | Status | Impact |
|-------------|--------|--------|
| #1 Dead hours (03-08 UTC) | **DONE** | — |
| #2 Speed >= 30th percentile | **MISSING** | Enters on dead tokens |
| #3 Phase alignment | **MISSING** | Enters at exhaustion points |
| #4 Range position | **In detection only** | Lost by execution time |
| #5 Counter-trend trap | **PARTIAL** | z-score + speed cross-check missing |
| #6 Ranging market filter | **MISSING** | Enters in whitewater |
| #7 Coin history gate | **DONE** | — |

All the data needed for these checks is **already available** in `hotset.json` at execution time — it just isn't being used for entry filtering.

---

## Solution

Add a unified `context_gate()` function to `decider_run.py` that runs ALL remaining surfing checks in one place, right before `execute_trade()`. This is the "AI decision" — not an LLM, but a structured rule engine that asks "should we actually trade this?" after all other checks pass.

### Why Not an LLM?

The plan mentioned Phase 2 (LLM-based) as future. Rule-based is better here because:
- **0ms latency** vs 2-5s for LLM
- **Deterministic** — same input = same output (debuggable)
- **No cost** — LLM calls cost money per decision
- **Existing data is rich** — z_score, speed, phase, regime, WR are all available
- **LLM would just learn these same rules** — no edge from adding one

If rules prove insufficient, LLM can be layered on top later.

---

## Implementation

### 1. New function in `decider_run.py`: `context_gate()`

```python
def context_gate(token, direction, sig):
    """
    Unified surfing-based context gate. Runs AFTER all eligibility checks,
    RIGHT BEFORE execute_trade(). Returns (pass/reject/flip, reason, new_direction).
    
    sig = hotset entry dict (contains z_score, speed_percentile, wave_phase, etc.)
    """
    
    # ── Rule 2: Wave quality minimum ──────────────────────────────────
    # "Below 20th percentile = no wave" — don't enter on dead tokens
    speed = sig.get('speed_percentile', 50.0)
    if speed < CONTEXT_GATE_SPEED_MIN:
        return 'REJECT', f'speed_too_low ({speed:.0f} < {CONTEXT_GATE_SPEED_MIN})', direction
    
    # ── Rule 3: Phase alignment ──────────────────────────────────────
    # accel_300: only during building/accelerating (momentum just starting)
    # inv_accel_300- (SHORT): accelerating phase is OK (betting on reversal FROM acceleration)
    # inv_accel_300+ (LONG): accelerating phase is WRONG (buying into strength)
    # inv_accel_300: only during exhaustion/extreme for LONG, accelerating OK for SHORT
    source = sig.get('source', '')
    phase = sig.get('wave_phase', 'neutral')
    
    is_accel = source.startswith('accel-300')
    is_inv_accel = source.startswith('inv-accel-300')
    is_inv_accel_plus = 'inv-accel-300+' in source
    
    if is_accel and phase in ('exhaustion', 'extreme'):
        return 'REJECT', f'accel300_in_{phase}_phase (move already done)', direction
    
    # inv-accel-300+ (LONG): block in quiet/building/accelerating (not reversion prime)
    if is_inv_accel_plus and phase in ('quiet', 'building', 'accelerating'):
        return 'REJECT', f'inv_accel300+_in_{phase}_phase (not reversion prime)', direction
    
    # inv-accel-300- (SHORT): block in quiet/building/bottoming (accelerating is OK)
    if is_inv_accel and not is_inv_accel_plus and phase in ('quiet', 'building', 'bottoming'):
        return 'REJECT', f'inv_accel300-_in_{phase}_phase (not reversion prime)', direction
    
    # ── Rule 5a: Speed direction cross-check → FLIP ──────────────────
    # "If wave_phase is falling and direction is LONG → flip to SHORT"
    # "If wave_phase is accelerating and direction is SHORT → flip to LONG"
    # ONLY for trend signals (tl_break, accel-300). NOT for reversion (inv-accel-300)
    # because reversion signals intentionally fade momentum.
    z_score = sig.get('z_score', 0.0)
    momentum = sig.get('momentum_score', 50.0)
    price_accel = sig.get('price_acceleration', 0.0)
    
    is_trend_signal = not is_inv_accel  # tl_break, accel-300, etc.
    
    if is_trend_signal and phase == 'falling' and direction == 'LONG':
        new_dir = 'SHORT'
        return 'FLIP', f'falling_speed_flipped_to_short (wave dying)', new_dir
    if is_trend_signal and phase == 'accelerating' and direction == 'SHORT':
        new_dir = 'LONG'
        return 'FLIP', f'accelerating_speed_flipped_to_long (wave building)', new_dir
    
    # ── Rule 5b: Momentum + acceleration cross-check ─────────────────
    # "If momentum is weak AND acceleration opposes direction → reject"
    # ONLY for trend signals. Reversion signals (inv-accel) intentionally fade momentum.
    if is_trend_signal and momentum < 25 and direction == 'LONG' and price_accel < -0.005:
        return 'REJECT', f'weak_momentum_opposing_long (mom={momentum:.0f}, accel={price_accel:+.4f})', direction
    if is_trend_signal and momentum < 25 and direction == 'SHORT' and price_accel > 0.005:
        return 'REJECT', f'weak_momentum_opposing_short (mom={momentum:.0f}, accel={price_accel:+.4f})', direction
    
    # ── Rule 5c: Counter-trend trap (z-score + speed cross-check) ──────
    if direction == 'LONG' and z_score > CONTEXT_GATE_Z_COUNTER_TREND and speed < 50:
        return 'REJECT', f'counter_trend_long (z={z_score:.2f}, speed={speed:.0f})', direction
    if direction == 'SHORT' and z_score < -CONTEXT_GATE_Z_COUNTER_TREND and speed < 50:
        return 'REJECT', f'counter_trend_short (z={z_score:.2f}, speed={speed:.0f})', direction
    
    # ── Rule 6: Ranging market filter ─────────────────────────────────
    if abs(z_score) < CONTEXT_GATE_Z_RANGING and speed < 25:
        return 'REJECT', f'ranging_market (|z|={abs(z_score):.2f}, speed={speed:.0f})', direction
    
    return 'PASS', 'context_gate_passed', direction
```

### 2. Integration point in `decider_run.py`

Insert AFTER the signal inversion (line ~2037) and BEFORE `execute_trade()` (line ~2045):

```python
        # ── Context Gate (surfing rules) ───────────────────────────────
        gate_result, gate_reason, gate_dir = context_gate(token, direction, sig)
        
        if gate_result == 'REJECT':
            log(f'  🚫 [CONTEXT-GATE] {token} {direction} rejected: {gate_reason}')
            if sig_id:
                mark_signal_executed(token, direction, 'SKIPPED', signal_id=sig_id)
            skipped += 1
            continue
        
        if gate_result == 'FLIP':
            log(f'  🔄 [CONTEXT-GATE] {token} {direction} → {gate_dir}: {gate_reason}')
            direction = gate_dir
            # Update entry direction for the flip
            entry['direction'] = direction
```

### 3. New constant in `hermes_constants.py`

```python
# ── Context Gate ──────────────────────────────────────────────────────────────
# Unified surfing-based context gate. Runs all remaining checks before execution.
CONTEXT_GATE_ENABLED = True

# Tunable thresholds
CONTEXT_GATE_SPEED_MIN = 30        # Rule 2: minimum speed percentile
CONTEXT_GATE_Z_COUNTER_TREND = 1.5 # Rule 5: z-score threshold for counter-trend
CONTEXT_GATE_Z_RANGING = 0.5       # Rule 6: |z-score| below this = ranging
CONTEXT_GATE_ACCEL_THRESHOLD = 0.005 # Rule 4: price_accel threshold for range position
```

### 4. Logging

Every rejection logs:
```
🚫 [CONTEXT-GATE] BTC LONG rejected: accel300_in_exhaustion_phase (move already done)
```

Every pass is silent (no log spam).

The gate result is also stored in the trade metadata for post-analysis:
```python
success, msg = execute_trade(
    ...,
    signal_metadata={
        ...existing fields...,
        'context_gate_reason': gate_reason,
    },
)
```

---

## Data Flow

```
hotset.json entry
    ↓
Existing eligibility checks (blacklist, cooldown, speed=0, etc.)
    ↓
Signal inversion (SIGNAL_INVERSION_MAP)
    ↓
context_gate(token, direction, sig)
    ├── Rule 2: speed >= 30?
    ├── Rule 3: phase aligned with signal type?
    ├── Rule 5a: speed direction vs signal direction?
    ├── Rule 5b: momentum + acceleration vs signal direction?
    ├── Rule 5c: z-score contradicts + low speed?
    ├── Rule 6: ranging market?
    └── Rule 4: range position?
    ↓
PASS → execute_trade()
REJECT → mark SKIPPED, continue
```

---

## What Already Exists (NOT Duplicated)

| Check | Existing Location | Status |
|-------|------------------|--------|
| Dead hours (Rule 1) | `decider_run.py:1892` | DONE |
| Coin history (Rule 7) | `decider_run.py:1938` | DONE |
| Speed = 0% (stale) | `decider_run.py:1903` | DONE |
| Wrong-side learning | `decider_run.py:1926` | DONE |
| Loss cooldown | `decider_run.py:1918` | DONE |
| Counter-trend trap (partial) | `decider_run.py:1227` | EXTENDED |
| Wave-awareness (partial) | `decider_run.py:1121` | NOT TOUCHED |

The context gate adds ONLY the missing surfing rules. It does not duplicate existing checks.

---

## Config Toggles

| Constant | Default | Purpose |
|----------|---------|---------|
| `CONTEXT_GATE_ENABLED` | `True` | Master toggle |
| `CONTEXT_GATE_SPEED_MIN` | `20` | Rule 2: minimum speed percentile (lowered from 30 — AI traded at 23-28) |
| `CONTEXT_GATE_Z_COUNTER_TREND` | `1.5` | Rule 5c: z-score threshold for counter-trend |
| `CONTEXT_GATE_Z_RANGING` | `0.5` | Rule 6: |z-score| below this = ranging |
| `CONTEXT_GATE_RANGING_SPEED` | `25` | Rule 6: speed threshold for ranging (separate from speed min) |

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Gate blocks too many signals | Set `CONTEXT_GATE_ENABLED = False` instantly |
| Thresholds too tight | All thresholds are tunable constants |
| False rejects on good trades | Log all rejects — analyze after 48h |
| Speed data stale | speed_percentile refreshed every 1 min via speed_tracker |
| Phase data stale | wave_phase refreshed every 1 min via speed_tracker |

---

## Expected Impact

Based on 200-trade analysis + AI test on 11 pending signals:

| Rule | Estimated Bad Trades Blocked | WR Impact |
|------|------------------------------|-----------|
| Speed >= 30 | ~10% of trades (dead tokens) | +2-3% |
| Phase alignment (expanded) | ~18% of trades (exhaustion + wrong phase) | +4-6% |
| Speed direction cross-check | ~5% of trades (falling speed + LONG, etc.) | +1-2% |
| Momentum + accel cross-check | ~5% of trades (weak momentum opposing) | +1-2% |
| Counter-trend + speed | ~5% of trades | +1-2% |
| Ranging market | ~5% of trades | +1-2% |
| Range position | ~5% of trades | +1-2% |
| **Combined** | **~30-40% of bad trades** | **+10-16%** |

**Conservative estimate**: 29% → 39-45% WR (with inversion + dead-hours already deployed)
**Optimistic estimate**: 29% → 45-52% WR

---

## Testing Plan

1. **Dry run**: Add `CONTEXT_GATE_ENABLED = True` but log only (don't reject). Run 24h. Check what would have been blocked.
2. **Paper mode**: Enable gate in paper mode. Compare paper WR to live WR.
3. **Monitor rejects**: Track reject reasons — if one rule dominates, adjust threshold.
4. **A/B test**: Gate ON for 48h vs previous 48h baseline.

---

## Open Questions (Save for Implementation)

1. **Range position threshold (Rule 4)**: Using `price_acceleration` as proxy is imprecise. Should we compute actual range position from candle data? (Adds DB query but more accurate.)

2. **Phase thresholds for inv_accel_300**: Should we allow inv_accel_300 during `accelerating` phase too, or only `exhaustion`/`extreme`? The surfing principle says "reversion prime" at exhaustion, but accelerating might be too early.

3. **Speed threshold tuning**: Is 30th percentile the right floor? Data shows ~15% WR below 30, but some tokens at 20-30 still win.

4. **Should the gate also affect delayed entries?** Currently only hotset entries go through the gate. Delayed entries (pending-delayed-entries.json) skip it.

5. **Should we add the gate to `signal_compactor.py` too?** This would filter signals earlier (before they enter hotset), reducing hotset noise. But compactor runs less frequently (1 min) and has less fresh data.
