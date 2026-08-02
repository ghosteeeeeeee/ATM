# Plan: Surfing — Wait for the Wave to Build

## Goal

Implement the Surfing philosophy from `brain/surfing.md`: "Wait for the real swell, don't chase every ripple." The system should NOT execute on the first signal. Instead, signals must survive N hot-set cycles (prove they are not noise) before execution eligibility kicks in. This creates a natural "wave building" effect where conviction grows over time.

---

## Current Context

**The execution gap:**
- `signal_compactor.py` tracks `compact_rounds` (how many times a token+direction has appeared in hot-set) and `survival_round` (same thing, incremented from previous hot-set)
- `decider_run.py` executes signals with `confidence >= 50` — NO survival check
- The hot-set already has the data needed; it's just not enforced at execution time

**Signal flow:**
```
signal_gen (each 1-min cycle)
    → individual indicator signals (hwave, hzscore, pct-hermes, vel-hermes)
    → signal_compactor (every 10 min)
        → groups by token+direction, merges sources in 180-min window
        → increments compact_rounds if APPROVED signal reappears
        → writes to hotset.json with survival_round
    → decider_run (every 1 min)
        → reads APPROVED signals from DB
        → executes if confidence >= 50 ← NO survival check here!
```

**What surfing.md says:**
- "Don't paddle for every ripple"
- "Wait for the real swell"
- "Position yourself, let it carry you"
- Speed tells you IF a wave exists; you still need to wait for the right moment

**Current surf violations:**
- Signal appears once at conf=65 → immediately eligible for execution
- No "prove it" gate — one signal = instant execution eligibility
- System already has 10/10 positions full, many from single-source signals

---

## Proposed Approach

### Primary Fix: Add `min_compact_rounds` execution gate in decider_run.py

**Concept:** A signal must survive N hot-set compaction cycles before it can execute. Each cycle is 10 minutes. The hot-set already tracks `compact_rounds` per token+direction — we just need to enforce it at execution time.

**Recommended threshold:** `min_compact_rounds = 2`
- Cycle 1: Signal appears, compact_rounds=1 → NOT eligible, observe
- Cycle 2 (10 min later): Signal reappears, compact_rounds=2 → NOW eligible
- Rationale: 2 cycles = 10 min of survival = signal proved it's not a one-shot noise burst

**Why not higher?**
- 3 cycles = 20 min — good for quality but delays all entries significantly
- 2 cycles is the minimum viable "prove it" gate — one re-confirmation

### Secondary: Increase signal window from 180 min to 240 min in signal_compactor

**Concept:** Longer window = more historical signals merged = bigger wave. If hzscore fired 30 min ago and hwave fires now, they should be combined as one growing wave.

**Change:** Line 196: `created_at > datetime('now', '-180 minutes')` → `'-240 minutes'`

### Tertiary: Count distinct BASE signal types for entries_count

**Current bug (already fixed):** `entries_count = len([p for p in src.split(',') if p.strip()])` → counts raw items including duplicates like `h+,h+,h+` = 3 even though only 1 distinct base type.

**What it should show:** The number of DISTINCT base signal TYPES that have confirmed this direction. If `hwave+` and `hzscore+` and `vel-hermes+` all agree → entries_count = 3. But if it's just `hzscore+` repeated 3 times → entries_count = 1.

The current fix counts raw comma items. The correct fix should count distinct base types: strip trailing `+/-` from each source part, dedupe, count.

---

## Step-by-Step Plan

### Step 1 — Add `min_compact_rounds` gate in decider_run.py

**File:** `/root/.hermes/scripts/decider_run.py`

Find where `MIN_EXEC_CONFIDENCE` is defined (around line 1280). Add:

```python
# Surfing gate: require signal to survive N hot-set cycles before executing.
# Cycle 1: appears in hot-set, NOT eligible (observe only)
# Cycle 2+: eligible — signal proved it's not a one-shot noise burst
# This implements "wait for the real swell" from surfing.md
MIN_COMPACT_ROUNDS = 2
```

Then in the execution loop (around line 1365), after confidence check:

```python
# Surfing gate: skip if signal hasn't survived enough hot-set cycles
sig_compact_rounds = sig.get('hot_rounds', 0)  # hot_rounds from get_approved_signals()
if sig_compact_rounds < MIN_COMPACT_ROUNDS:
    log(f'SKIP SURF: {token} {direction} — compact_rounds={sig_compact_rounds} < {MIN_COMPACT_ROUNDS} (wave still building)')
    skipped += 1
    continue
```

Note: `sig.get('hot_rounds', 0)` maps from the `hot_rounds` field returned by `get_approved_signals()` (signal_schema.py line 1012: `as hot_rounds`). This is the MAX compact_rounds of any APPROVED signal for this token+direction.

### Step 2 — Increase signal window in signal_compactor.py

**File:** `/root/.hermes/scripts/signal_compactor.py`

Line ~196:
```python
# Before
AND created_at > datetime('now', '-180 minutes')
# After
AND created_at > datetime('now', '-240 minutes')
```

Also line ~440 (Step 13 query for rejected signals):
```python
AND created_at > datetime('now', '-60 minutes')
```
→ no change needed for 60-min rejection window.

### Step 3 — Fix entries_count to count distinct base types

**File:** `/root/.hermes/scripts/signal_compactor.py`

The current fix at lines 497-499 counts raw comma items:
```python
entries_count = len([p for p in src.split(',') if p.strip()]) if src else 0
```

Change to count distinct base types (strip trailing `+`/`-`):
```python
# Count DISTINCT base signal types: 'hwave+,hzscore-,hzscore+' → 2 distinct types
# Trailing +/- indicates direction, base type is the indicator name
base_types = set()
for part in (src or '').split(','):
    part = part.strip()
    if part:
        # Strip trailing +/-
        base = part.rstrip('+-')
        if base:
            base_types.add(base)
entries_count = len(base_types)
```

Also update `_preserve_previous_hotset` (line ~605) with the same logic.

### Step 4 — Verify syntax

```bash
python3 -c "import signal_compactor; print('signal_compactor OK')"
python3 -c "import decider_run; print('decider_run OK')"
```

### Step 5 — Verify hot-set output

```bash
python3 signal_compactor.py --dry 2>&1 | grep -E "entries_count|src=|compact_rounds"
```

Expected: `entries_count` now shows 1 for single-type signals (e.g., only `hzscore+`), 2+ for multi-type.

### Step 6 — Check pipeline log after next cycle

Monitor `/root/.hermes/logs/pipeline.log` for:
- "SKIP SURF" messages for compact_rounds=1 signals
- After 10+ min: signals with compact_rounds=2 becoming eligible
- Entries count in hotset.json updating correctly

---

## Files Likely to Change

1. `/root/.hermes/scripts/decider_run.py` — add `MIN_COMPACT_ROUNDS = 2` gate at execution
2. `/root/.hermes/scripts/signal_compactor.py` — increase 180→240 min window, fix entries_count to distinct base types
3. `/root/.hermes/scripts/signal_schema.py` — no changes needed, `hot_rounds` already in `get_approved_signals()`

---

## Tests / Validation

- [ ] `python3 -c "import signal_compactor; import decider_run; print('Both OK')"`
- [ ] Dry-run shows entries_count=1 for single-type signals, 2+ for multi-type
- [ ] Pipeline log shows "SKIP SURF" for first-cycle signals
- [ ] After 10+ min, compact_rounds=2 signals start executing
- [ ] No new trades open from first-cycle signals (surfing gate working)
- [ ] Existing positions at 10/10 still honored (position limit not affected)

---

## Risks and Tradeoffs

| Risk | Severity | Mitigation |
|---|---|---|
| min_compact_rounds=2 delays ALL new entries by 10 min | Medium | This IS the point — wait for wave confirmation. 10 min is acceptable. |
| System at 10/10 — gate may never allow new trades if old ones don't close | High | Position manager exits (stale winner/loser rules) must work. If positions don't close, no new entries regardless of gate. |
| Existing APPROVED signals with compact_rounds=1 will be blocked | Medium | On first cycle after deploy, many signals will be blocked. This is expected — let them re-qualify in cycle 2. |
| Longer signal window (240 min) may merge stale signals | Low | Staleness penalty in scoring handles this — older signals get lower scores. |
| entries_count changes from raw items to distinct types | Low | Display changes but reflects actual signal count better |

## Open Questions

1. **Should min_compact_rounds be 1 or 2?** Currently proposed=2. If set to 1, the gate has no effect (every signal that appears has compact_rounds >= 1). min_compact_rounds must be >= 2 to enforce the "wait" principle.
2. **Should we add a MAX wait time?** If a signal survives 5+ cycles but never gets a second confirming signal, should it auto-expire or keep waiting?
3. **Should we distinguish between "signal reappeared same cycle" vs "signal reappeared next cycle"?** Current compact_rounds increments every time compactor sees an existing APPROVED signal — it counts reappearances, not elapsed time.
4. **What about counter-regime signals?** Surfing says don't execute counter-regime. The existing regime filter handles this, but should we also add a surfing-specific regime check?
