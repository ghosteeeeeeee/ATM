# Signal Quality Incidents — June 2026

## Incident 1: Accel-300 Standalone Bypass Failed

**Date**: 2026-06-09
**Problem**: Set `ACCEL_300_STANDALONE_BYPASS_ENABLED=True` with `ACCEL_300_STANDALONE_BYPASS_CONFIDENCE=70` to bypass confluence gate for pure accel-300 signals.

**Why it failed**: Accel-300 confidence is capped at exactly 70. Any threshold <=70 passes ALL pure accel signals (they all fire at conf=70). Any threshold >70 passes NONE. The parameter is fundamentally broken by design.

**Result**: Wave of losses from pure accel-300 signals (40% WR historically) all passing confluence → hotset flooded with weak signals.

**Fix**: `ACCEL_300_STANDALONE_BYPASS_ENABLED=False` (disabled). Kept `ACCEL_300_STANDALONE_BYPASS_CONFIDENCE=70` in hermes_constants for reference.

**Lesson**: Never create a threshold-based bypass where the signal's natural confidence ceiling equals the bypass threshold.

---

## Incident 2: RS_TOUCH_HARD_CAP Raised to 180 (Too Permissive)

**Date**: 2026-06-09
**Problem**: Originally set to 150 based on trade data (120-1380 touches = 0% WR). Raised to 180 to "preserve 151-180 range."

**Why it failed**: Losing trades (ORDI, ADA, ONDO) had touches 154-164 — all passed 180 cap. The 151-180 range had no proven validity.

**Fix**: `RS_TOUCH_HARD_CAP=120` (restored).

**Lesson**: When historical data says "120+ = 0% WR", trust the data. Don't loosen thresholds based on speculation.

---

## Incident 3: Confluence Gate Misdiagnosed as Bottleneck

**Problem**: Dry spell with no trades. Root cause assumed to be signal detection thresholds being too tight.

**Finding**: 262 pure accel + 762 RS signals blocked by confluence gate (requires 2+ unique types). Signal detection was fine. Gate was bottleneck.

**Lesson**: Always verify WHERE in the pipeline the bottleneck is before changing detection thresholds.

---

## Current Constants (Jun 2026)

```
RS_TOUCH_HARD_CAP = 120
RS_DECIDER_MIN_TOUCHES = 80
ACCEL_300_STANDALONE_BYPASS_ENABLED = False
RS_BROKEN_SHORT_ENABLED = False
```

## Win Rate vs Signal Fire Rate

The 2-type confluence requirement maintains win rate by only firing when momentum AND structure agree. Accept dry spells as the cost. Bypassing it (even with "high confidence" guards) leads to losses.