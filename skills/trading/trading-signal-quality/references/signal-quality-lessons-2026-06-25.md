# Signal QA — Lessons Captured Across Audits (2026-06-25 / 2026-07-05)

Pointers to the most important signal-quality learnings. See
the linked reference files for the full story each.

## Critical: accel-300 Stale-Direction Bug (NEW, 2026-06-25)

Even AFTER the 2026-06-23 backward-scan fix, accel-300 fires
short signals when live price is ABOVE EMA300 (and the mirror
for long). Cause: the scan-backward finds the most recent
qualifying bar going backward, but never checks the LATEST bar
also qualifies.

Verification: 27 / 121 trades (22%) wrong direction over 7d.

**Fixes (two parts):**
1. Code patch in `signals/accel_300.py` near line 617: add
   "live-bar direction check" requiring `direction == last_bar_side`
2. Tighten two stale constants:
   - `ACCEL_300_STALE_LOOKBACK`: 400 → 10 (was 6.6 hours, too lenient)
   - `ACCEL_300_STALE_GAP_DECAY_THRESHOLD`: 0.50 → 0.80

→ `references/accel-300-stale-direction-fix-incomplete-2026-06-25.md`

## Critical: "value" field in signal DB ≠ gap_pct

`signals/accel_300.py` line 734 stores `value=float(sig['gap_growth'])`
into the signal DB record. The DB column is `value`. Reading the
DB to debug, it's tempting to interpret `value = -0.30` as
"gap_pct is -0.30%". It isn't — `gap_growth = gap_now - gap_then`
(a delta). Always recompute gap_pct from `price` directly:

```python
ema = price_history.ema(closes_at_signal_time)
gap_pct = (price - ema) / ema * 100
```

→ `references/accel-300-stale-direction-fix-incomplete-2026-06-25.md`

## Critical: Detection docstring stale vs. code reality

accel-300.py top docstring at lines 14-26 lists 10 conditions.
The `detect_accel_300()` docstring at lines 213-223 lists 5.
The internal one (used during reviews) is stale.

When patching the detector, also update both docstrings to match
actual gate order and count, including the new live-bar direction
check (Part 1 of the above fix).

## Don't add profit-lock features

T (user) explicitly said: "we don't want to add new features,
like profit-lock, that is supposed to happen already with the SL
following the price." If SL doesn't capture profit, FIX THE SL
(constants) or FIX THE SIGNAL DIRECTION (accel-300 patch),
don't add a new profit-lock mechanism. A profit-lock is a
band-aid that masks the underlying trail-too-wide bug.

## ATLAS verification scripts

For accel-300 direction verification:
- `/root/.hermes/scripts/analysis/check_all_accel_direction.py` —
  replays detector EMA on 7-day history, reports WRONG-DIRECTION count
