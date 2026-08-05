# Signal Bug Patterns — June 2026

Patterns caught during signal logic review of `signals/accel_300.py` and `signals/rs.py`.
Add new patterns here as they are discovered.

---

## Bug #16: Signed Metric in Confidence — SHORT Gets Zero Bonus

**When it fires**: A metric that is negative for SHORT (gap_pct, momentum, returns) is used in a
confidence formula like `max(0, (metric - threshold) * scalar)`.

**Why it breaks**: For SHORT, `metric - threshold` is always negative → `max(0, ...)` clamps it to 0.
SHORT confidence never earns the magnitude bonus even when the signal is strong.

**Fix**: Use `abs(metric)` for the magnitude term, or write per-direction formulas.

**Real example — accel_300.py (fixed 2026-06-14)**:
```python
# BEFORE: gap_pct is negative for SHORT → bonus always 0
gap_for_conf = sig['gap_pct']
confidence = int(min(70, 65 + max(0, (gap_for_conf - MIN_GAP_PCT) * 80) + gap_bonus))

# AFTER: abs() so SHORT earns the gap-strength bonus too
gap_for_conf = abs(sig['gap_pct'])
confidence = int(min(70, 65 + max(0, (gap_for_conf - MIN_GAP_PCT) * 80) + gap_bonus))
```

**Detection heuristic**: Search for `max(0, (sig['` or `max(0, (metric - threshold)` where `metric` is a signed
value that could be negative for one direction. Check both directions explicitly in review.

---

## Bug #17: Recovery Branch — Missing State for Downstream Hard Gate

**When it fires**: Code reclassifies a signal state (e.g. `broken → active`) in a conditional branch,
but omits updating a dependent variable (`bounces`, `confirmed`, etc.) that a downstream hard gate checks.

**Why it breaks**: The reclassification makes the signal valid, but the stale variable causes the
downstream gate to reject it anyway.

**Fix**: When reclassifying, set ALL state variables to values that satisfy every downstream gate.
Every branch that changes signal state must update all state.

**Real example — rs.py (fixed 2026-06-14)**:
```python
# Support path (already fixed): reclassify broken support → active support
if broken and price > level:
    broken = False     # reclassify
    bounces = True     # ← ALSO set bounces so hard gate below passes

if broken:
    nearest_support = None  # blocked by hard gate below

# Resistance path (fixed this session): was missing bounces=True update
if broken and price < level:
    broken = False
    # MISSING: bounces = True  ← caused valid recovered signals to be blocked
```

**Detection heuristic**: When adding a reclassification/recovery branch, list every variable
the downstream gate checks and verify each is set in the new branch.
