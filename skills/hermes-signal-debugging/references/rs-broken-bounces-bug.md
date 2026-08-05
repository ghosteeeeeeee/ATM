# rs-s-broken SHORT bounces=False Bug (2026-06-01)

## Symptom
Losing SHORT trades firing during intraday uptrends. All 12 losing tokens had NEUTRAL regime.
Signal source: `rs-s-broken` (broken support → SHORT).

## Root Cause — rs.py:527

```python
# Line 527: broken-support SHORT — bounces=False (no bounce check)
confidence = _compute_confidence(bounces=False, recency_score=recency, ...)

# vs Line 545: normal support bounce LONG — bounces=True (bounce required)
confidence = _compute_confidence(bounces, recency_score=recency, ...)
```

The `rs-s-broken` path fires without requiring actual bounce confirmation.
It only checks `_level_recently_broken()` — "was this level crossed sometime in the last 200 candles (~3.3 hours)?"

During an uptrend retrace, price breaks support → then bounces back up toward it.
On the bounce-back, `nearest_support` finds the broken level again.
`_level_recently_broken()` returns True (level was crossed 50 bars ago).
`rs-s-broken` fires with no bounce filter → SHORT in uptrend.

## Why the Bounce Path Is Asymmetric

| Path | Direction | Bounces Check | Regime Suppression |
|------|-----------|---------------|-------------------|
| rs-s-broken (520-543) | SHORT | False (no bounce) | Haircut only, no return None |
| rs-r-broken-LONG (574-597) | LONG | False (no bounce) | Haircut only, no return None |
| Normal bounce (545+) | LONG | True (requires bounce) | None |

In NEUTRAL regime (which all 12 losing tokens had), both broken paths apply a 15% haircut
but never suppress. The normal bounce LONG path also has no regime suppression.

## Comparison: accel_300.py:410 (correct pattern)

```python
if regime == 'LONG_BIAS':
    if direction == 'SHORT':
        return None  # Suppress SHORT in uptrend — correct
```

accel_300 correctly suppresses SHORT in LONG_BIAS. rs.py broken paths do not.

## Fix Approach

Add `bounces=True` to the `rs-s-broken` path at line 527. This requires actual rejection
confirmation off the broken level (close below level + next candle also lower), not just
the fact that the level was crossed hours ago.

Also consider: reduce `RS_LEVEL_BROKEN_LOOKBACK` from 200 to ~30 candles (reducing stale
broken flags persisting 3+ hours).

## DB Evidence
- 12 losing SHORT trades, all in NEUTRAL regime
- All combos: `accel-300-,rs-s-broken` or `rs-rN,rs-s-broken`
- rs-s-broken fires every scan cycle once level is in broken state
- 200-candle lookback = ~3.3 hours of stale broken flags