# accel-300- Bug: abs(gap) Required for SHORT [SUPERSEDED]

## ⚠️ SUPERSEDED — See `references/accel-300-condition2-sign-bug-2026-05-14.md`

The abs() fix applied 2026-05-13 introduced a NEW bug: abs(gap_now) strips sign, causing SHORT signals to fire when price is ABOVE EMA (positive gap). The reversal fix (signed checks replacing abs) is documented in the new reference.

## Original Bug (2026-05-13)

**File:** `/root/.hermes/scripts/signals/accel_300.py`, line 222-224

**Symptom:** accel-300- (SHORT direction) fired 0 times across entire token universe. accel-300+ (LONG) worked fine — 2862+ signals.

**Root Cause:** The gap check used `gap_now < MIN_GAP_PCT` instead of `abs(gap_now) < MIN_GAP_PCT`. For SHORT signals, `gap_now` is negative, so `-0.243 < 0.20 = True` — every SHORT rejected.

**Fix applied 2026-05-13:** Added `abs()` to require magnitude >= 0.20 for both directions.

**Side effect (2026-05-14):** abs() strips sign → CHIP:SHORT fires when price is +0.25% ABOVE EMA. The abs() was the wrong fix — direction-specific signed comparison is correct.

## Key Lesson

abs() is appropriate for magnitude-only checks. For directional gap checks where sign carries semantic meaning, use explicit signed comparison:
- LONG: `gap_now < min_gap` (positive but too small = reject)
- SHORT: `gap_now > -min_gap` (positive = above EMA = reject for SHORT)

## Related

- `references/accel-300-condition2-sign-bug-2026-05-14.md` — the reversal fix
- `references/instant-reopen-cooldown-gap-2026-05-14.md` — CHIP/LAYER instant reopen root cause