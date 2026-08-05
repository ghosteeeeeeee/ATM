# rs-s-broken bounce bug — 2026-06-02

## The Bug
`rs-s-broken` (SHORT on broken support) and `rs-r-broken` (LONG on broken resistance) hardcoded `bounces=False` when calling `_compute_confidence()`. The bounce confirmation was computed but discarded — the signal fired regardless of whether price actually rejected from the level.

The `_bounce_confirmation()` function returns True only when there's actual directional rejection (touch candle was directionally correct OR next candle continued >0.025%). With `bounces=False`, this result was ignored and the +5 bounce bonus was never applied.

## The Fix (applied 2026-06-02)
Both broken paths now use `bounces=bounces` instead of `bounces=False`:

```python
# rs.py line 527 (rs-s-broken SHORT path)
confidence = _compute_confidence(atr_pct, best_support_dist, touch_count, bounces=bounces, recency_score=recency)

# rs.py line 581 (rs-r-broken LONG path)
confidence = _compute_confidence(atr_pct, best_resist_dist, touch_count, bounces=bounces, recency_score=recency)
```

Before: signal fired at base 65 + proximity/touch bonuses only. After: signal fires at base 65 + bounce bonus (+5 if bounce confirmed, 0 if not).

## Why this matters
A broken support level near price from below could fire `rs-s-broken` even though price had retraced well above the level and was approaching it again from above — the level was "broken" hours ago, but the signal didn't require actual rejection on the current approach. The bounce fix adds the confirmation gate.

## Symptom in losing trades
`accel-300-,rs-s-broken` combo had 47 losing trades in 48h (41% loss rate). The combo fires 3x more than `accel-300-` standalone because `rs-s-broken` was easy to trigger — no bounce required. After the fix, volume should drop and win rate should improve.

## Key files
- `/root/.hermes/scripts/signals/rs.py` — patched lines 527 and 581
- `signals/rs.py` `bounce` field in signal dict is always `False` for broken paths — this is correct. The broken paths fire on level-break events, not on bounce confirmations. The `bounce` field reflects the signal's nature, not the bounce check used for confidence.