# RS Co-Signal Quality: Touch Count vs PnL (2026-05-10)

## Key Finding: RS Touch Count Is the Quality Filter

Analyzing 38 accel-300+ trades against RS co-signal touch counts reveals a clear pattern:

| RS Touch Count | Trades | Win Rate | Avg PnL |
|----------------|--------|----------|---------|
| **1-20** | 9 | **44%** | **+0.80%** |
| 21-50 | 11 | 18% | +0.24% |
| 51-100 | 5 | 20% | +0.47% |
| 100+ | 10 | 40% | +0.02% |
| Accel alone (no RS) | 3 | 33% | +0.90% |

**Sweet spot: RS levels with 8-50 touches** — reactive structural bounces.
**Avoid: ancient macro levels (100-12,000+ touches)** — structurally valid but price has moved on.

## The 8 Big Winners (all LONG, all accel-300+)

| Token | PnL | RS Touches |
|-------|-----|-----------|
| S | +4.00% | 8 |
| ASTER | +3.59% | 84 |
| MON | +3.41% | 36 |
| FET | +3.18% | 34 |
| ETH | +3.13% | none |
| APEX | +2.18% | 8 |
| ORDI | +1.80% | 10 |
| 0G | +1.70% | 112 |

**Pattern: 8-36 touches** (fresh reactive levels), not 264-12,284.

## Root Cause: RS Finds Ancient Macro Levels

Current RS config:
- `RS_LOOKBACK_CANDLES = 4700` (~3+ days of 1m)
- `RS_PROXIMITY_K = 1.00` (fire when price within 1.0 ATR)
- No recency weighting

Results: RS fires on levels with 264, 104, 188, **12,284** touches — ancient levels that price has tested hundreds of times. These are structurally valid but NOT reactive bounce zones. The 8-touch levels that produced big wins are drowned out.

## bounce=True Is Almost Never True

Current: `RS_PROXIMITY_K=1.00`, `_BOUNCE_THRESH_ATR=1.00`

With price at 1.0 ATR from the level, it's already too far for a reactive bounce. Bounce confirmation requires the NEXT candle to move >0.025% in signal direction — but if price is already 1 ATR away, the "bounce" is the move back TO the level, not a continuation through it.

## Confluence Gate Bottleneck

- 87 early accel-300+ fires (bars ≤ 3) available
- Only 7/32 (22%) have RS co-signal at time of detection
- The other 78% are blocked at 2-source confluence requirement

## Two RS Fixes to Make It Fire Earlier + Better

### Fix 1: Lower RS_PROXIMITY_K 1.00 → 0.70
Fire when price is CLOSER to the level (within 0.7 ATR). Catches the reactive bounce zone before price has run away from it.

### Fix 2: Add Recency Bonus to Confidence
A level with 10 recent touches should score HIGHER than a level with 200 ancient touches, even if both pass `RS_MIN_TOUCHES=8`.

```python
# In _compute_confidence():
# Current: log-scale touch bonus (3-9 pts for 1-50+ touches)
# Add recency: bonus decays with age of last touch
# Recent touch (within 20 candles) = full bonus
# Old touch (100+ candles ago) = half bonus
```

## Trade Data Field Name: `signal` not `source`

When analyzing trades.json: the field is `t['signal']` and `t['pnl_pct']`, NOT `t['source']` and `t['pnl']`.

```python
# CORRECT
src = t.get('signal', '')
pnl = t.get('pnl_pct', 0)

# WRONG (field doesn't exist in trades.json)
src = t.get('source', '')
pnl = t.get('pnl', 0)
```

## Analysis Scripts

- `/root/.hermes/scripts/analyze_accel_cosigs.py` — co-signal breakdown
- `/root/.hermes/scripts/analyze_winners.py` — big winners vs small losers
- `/root/.hermes/scripts/check_early_fires.py` — early accel fires with RS availability check
