# accel-300 LOOKBACK=250 Breaks Signal — Jun 2026

## Root Cause: LB=250 Pushes Detection Start Past All Crosses

`ACCEL_300_LOOKBACK=250` sets detection window start to `PERIOD + LOOKBACK = 300 + 250 = bar 550`.

- Bars 300-549 are **never scanned** by the detector loop
- All tokens had EMA below for extended periods during bars 300-549
- When detection finally starts at bar 550, `was_below_recently` finds238-250 bars of "below EMA" in its lookback window
- `was_below_recently = True` for every bar → `current_below AND NOT was_below_recently` is **always False**
- **Result: 0 signals for ALL tokens at LB=250**

## The was_below_recently Logic

```python
# Lines 204-217 — condition1 direction check
was_below_recently = any(
    gap_pcts[j] is not None and gap_pcts[j] < 0
    for j in range(i - LOOKBACK, i)
)
was_above_recently = any(
    gap_pcts[j] is not None and gap_pcts[j] > 0
    for j in range(i - LOOKBACK, i)
)

# SHORT needs: current_below AND NOT was_above_recently
# LONG needs:  current_above AND NOT was_below_recently
```

With LB=250, the window is 250 bars wide. If price was below EMA for 95%+ of those bars (typical for bearish tokens), `was_below_recently=True` always, and the SHORT condition `current_below AND NOT was_above_recently` is always False because `was_above_recently` is also True when price was below.

## GOAT Manual Trace at LB=30 (Working Case)

At i=330 with LB=30:
- `was_below_recently = True` (bars 300-329 all below EMA)
- `was_above_recently = False` (bars 300-329 had no above-EMA bars)
- `current_below = True` (price at bar 330 is below EMA)
- SHORT condition: `True AND NOT False = True` → **PASSES gate1**

But downstream fails:
- gap_pcts[330] = -1.4676% (valid, passes magnitude check)
- gap_pcts[326] = -1.0353% (4 bars ago), growth = 0.4323% > 0.05 ✓
- Cross search range: `max(310, 330-30)=310` to `331`
- GOAT's only SHORT cross is at bar 555 — **outside range** → cross_bar=None → returns None

## Cross Search Range Formula

```python
# Line 271 — cross search range
for j in range(max(310, i - LOOKBACK), i + 1):
```

With LB=30 at i=330: range is [310, 331]. Cross must be WITHIN 30 bars before detection bar.
With LB=250 at i=600: range is [600-250=350, 601]. Cross must be within 250 bars — but the detection never starts early enough to find crosses that are 81-149 bars ago.

## All 16 Fresh Tokens at LB=30 — Gate1 Passes

| Token | Gate1 Passes | Gate2 (cross) | Gate3+ |
|-------|-------------|---------------|--------|
| ZK    | 1 (i=602)   | 0 (cross search fails) | — |
| MET   | 1 (i=592)   | 0 (cross search fails) | — |
| BRETT | 0 | — | — |
| STX   | 0           | —             | — |
| All others | 0      | —             | — |

**ZK trace at i=602**: cross search range 568-599 finds no cross. ZK has SHORT crosses at 360, 374, 501, 555, 604... The cross at 555 is 47 bars before i=602 (outside LB=30 window). Cross at 604 is AFTER i=602.

## What Changed in This Session

| Constant | Was | Now | Note |
|----------|-----|-----|------|
| ACCEL_300_LOOKBACK | 250 | 30 | Restored to working value |
| ACCEL_300_STALE_BARS | 25 | 200 | Raised to pair with LB=250 (kept at 200) |
| ACCEL_300_REGIME_SLOPE_PCT | 0.008 | 0.003 | Lowered to be more permissive |

## Still Not Fixed

After lowering LB to 30, the signal still returns 0. The remaining issue is the **cross search failing** for all tokens:
- ZK and MET get1 gate1 pass each but cross search finds no cross within LB=30 window
- All other tokens show 0 gate1 passes (the was_below/was_above check is failing before cross search is even reached)

**Most likely remaining bug**: the `was_below_recently` / `was_above_recently` check requires ANY bar in the LOOKBACK window to have the opposite gap sign. For tokens that have been consistently below EMA for 300+ bars, there is no "recently" above-EMA bar to trigger the SHORT condition.

## Debug Command

```bash
cd /root/.hermes/scripts && python3 -m signals.accel_300 --scan 2>&1 | grep DEBUG
```

A DEBUG print was added to accel_300.py lines 213-217 tracing GOAT bars 328-335.

## Historical Constants (Pre-Session)

- ACCEL_300_LOOKBACK = 30 (original, before being set to 250)
- ACCEL_300_STALE_BARS = 20 (original, before being set to 25 then 200)
- ACCEL_300_REGIME_SLOPE_PCT = 0.008 (before being lowered to 0.003)

## Key Lesson

**LOOBACK controls the detection start point AND the was_above/was_below window size.** These are two different things:
1. Detection start = `PERIOD + LOOKBACK` (bars before this are never checked)
2. was_recently window = `LOOKBACK` bars immediately before detection bar

Large LOOKBACK (250) means: detection starts very late (bar 550+), AND was_recently window is 250 bars wide. Both effects combine to make the signal fail silently.
