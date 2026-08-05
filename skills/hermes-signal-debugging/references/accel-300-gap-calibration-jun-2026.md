# accel-300 Gap Calibration — UNI1min Move (June 2026)

## The Problem

accel-300 was designed for1min short-term acceleration moves, but it completely missed a real UNI move:
- 13:31 EST: $2.4717 → 13:41 EST: $2.5037 = **+3.2 cents (+1.3%) in 10 minutes**
- Clean breakout, strong momentum, exactly the pattern accel-300 targets

## Root Cause

**MIN_GAP_PCT threshold too high for small-price tokens.**

- `ACCEL_300_MIN_GAP_PCT_LONG = 0.20%` (requires price ≥ 0.20% above EMA300 to fire)
- On a ~$2.50 token,0.20% gap = only **0.5 cents** absolute
- UNI's actual gap at breakout: **0.09–0.17%** (below threshold)
- Result: signal never fires even though price clearly broke out and ran

**Secondary factor: close-only data hides intra-bar EMA touches.**
- price_history stores close-only ticks (open=high=low=close for each1min bucket)
- UNI spiked to ~$2.47 at12:32 EST — the intra-bar wick touched the EMA
- But the close was $2.47 (already above EMA), so the cross looked "clean" rather than "touched then bounced"
- This is not a bug — it's a data limitation. Signals must be calibrated for close-only data.

## Key Data (from UNI90-min1min chart, June 2026)

| Time (EST) | Close | Gap vs EMA80 | Gap % |
|---|---|---|---|
| 13:07 | 2.4684 | 0.41% | below threshold |
| 13:11 | 2.4836 | 0.92% | above threshold |
| 13:17 | 2.4933 | 1.15% | well above |
| 13:18 | 2.5037 | 1.54% | peak |

The signal would have fired at 13:11 if MIN_GAP_PCT were 0.10%.

## Recommended Parameter Changes

```python
# hermes_constants.py — lines ~482-483
ACCEL_300_MIN_GAP_PCT_LONG  = 0.20  →0.10  # catch small-token breakouts
ACCEL_300_MIN_GAP_PCT_SHORT = 0.25  →  0.15  # same logic for shorts
```

Optional secondary change (lower priority):
```python
ACCEL_300_PERSISTENCE_BARS = 2 →  1  # 1 bar confirms cross held on fast 1m breakouts
```

## Why 0.10% / 0.15% Instead of Removing the Gate Entirely?

The gap gate serves a real purpose — it prevents signals where price barely grazes
the EMA and immediately fades. For large tokens (BTC at $70k, 0.20% = $140), the
gate is meaningful. For small tokens (UNI at $2.50, 0.20% = $0.005), it's too tight.

0.10% for LONG /0.15% for SHORT is a reasonable middle ground that:
- Catches moves like UNI's (+1.3% in 10min)
- Still blocks marginal grazes on large tokens
- SHORT remains stricter (0.15% vs 0.10%) because SHORT side has40% WR vs 55% for LONG

## Volatility-Adjusted Alternative (Future Work)

A more robust fix would normalize gap_pct by token price:
```
effective_gap = gap_pct * price # or: gap_pct / log(price)
```
But this is a bigger refactor. The MIN_GAP_PCT tweak is the surgical fix.

## Verification

After applying the parameter changes, run:
```bash
python3 /root/.hermes/scripts/signals/accel_300.py --dry 2>&1 | grep -i UNI
```

Also check signal DB:
```sql
SELECT token, direction, gap_pct, created_at
FROM signals
WHERE token = 'UNI'
AND source LIKE 'accel-300%'
ORDER BY created_at DESC LIMIT 5;
```
