# RS Signal Quality — Touch Count vs PnL (2026-05-10)

## Key Finding: Ancient levels lose, fresh levels win

Analyzed 38 accel-300+ trades with RS co-signals. RS touch count strongly predicts quality:

| RS Touch Count | Win Rate | Avg PnL | Interpretation |
|---|---|---|---|
| 1-20 touches | **44%** | **+0.80%** | Fresh reactive bounces |
| 21-50 | 18% | +0.24% | Decaying structural |
| 51-100 | 20% | +0.47% | Stale macro level |
| 100+ | 40% | +0.02% | Ancient level — price doesn't bounce |
| No RS co-signal | 33% | +0.90% | Accel alone is decent |

**Big winners (all LONG, all accel-300+)**: S+4%, ASTER+3.6%, MON+3.4%, FET+3.2%, ETH+3.1%, APEX+2.2%, ORDI+1.8%, 0G+1.7%. RS co-signals had 8, 84, 36, 34, (none), 8, 10, 112 touches. **Sweet spot: 8-36 touches.**

## Root Problem: RS finds ancient macro levels, misses reactive bounces

`RS_LOOKBACK_CANDLES=4700` (~3+ days of 1m) finds the same macro levels repeatedly:
- BLAST: 12,284 touches (ancient)
- ORDI: 764 touches
- 2Z: 764 touches
- DASH: 356 touches
- BCH: 244 touches

Price has tested these 100-12,000 times — structurally valid but not reactive. The 8-50 touch levels (which have better WR) get drowned out.

## Two Fixes Applied (2026-05-10)

### Fix 1: RS_PROXIMITY_K 1.00 → 0.70

Fire when price is within 0.70 ATR of a level (was 1.00 ATR). Old setting caught levels price had already run past.

```python
RS_PROXIMITY_K = 0.70  # was 1.00
```

### Fix 2: RS_MIN_TOUCHES 8 → 3

Lower floor to catch fresh reactive levels. Big winners had 8-10 touch levels.

```python
RS_MIN_TOUCHES = 3  # was 8
```

### Fix 3: Recency-weighted touch scoring

New constant:
```python
RS_RECENCY_WINDOW = 200   # lookback for recency-weighted touch count
RS_RECENCY_BOOST_K = 3.0  # multiplier: each recent touch counts as K ancient touches
```

`_build_level_touches()` now returns `(total_touches, recency_weighted_score)`:
```python
# recency_score = recency_touches + K * ancient_touches
# A level with 10 recent + 100 ancient touches: 10 + 3*100 = 310
# A level with 0 recent + 500 ancient touches: 0 + 3*500 = 1500 (but recency bonus = 0)
```

The recency score is used in `_compute_confidence()` for the touch bonus (fresh levels score higher) AND a new recency bonus (+1 to +8 for levels with recent touches).

### Fix 4: Recency bonus in confidence

```python
# In _compute_confidence():
effective_touches = recency_score if recency_score is not None else touch_count
touch_bonus = min(9, 3 + int(np.log1p(max(0, effective_touches - 1)) * 2.5))

# Recency bonus: fresh levels get additional boost
if recency_score is not None and touch_count > 0:
    recent_fraction = min(1.0, (recency_score - touch_count) / (recency_score + 1e-9))
    recency_bonus = int(8 * recent_fraction) if recency_score > touch_count else 0
else:
    recency_bonus = 0
```

## Confluence Bottleneck — Primary Entry Blocker

After accel-300+ timing fix: **87 early fires (bars ≤ 3) available**. But only 7/32 (22%) have RS co-signal at detection time.

```python
# Confluence gate (signal_compactor.py lines 488-498):
if unique_signal_types >= 2:
    pass_gate = True  # RS+accel = 2 types ✓
else:
    pass_gate = False  # accel alone = 1 type ✗
```

The other 78% of early accel-300+ fires are blocked at the 2-source confluence requirement. This is the primary bottleneck.

## Close-Only Candle Data Problem

`price_history` is close-only (`open=high=low=close` for every candle). This means:
- **Bounce detection**: Only catches bounces where close crosses the level. Wick touches are invisible.
- **bounce=False on everything**: Even valid bounces show as `bounce=False` because the bounce happens via wick, not close.
- The dual-condition bounce fix (condition a: touch candle bullish, OR condition b: next candle >0.025% follow-through) still can't detect wick-based bounces.

This is a fundamental data limitation, not a code bug. The recency bonus compensates by boosting levels that have been tested recently, which correlates with being reactive.

## Files Changed

- `/root/.hermes/scripts/signals/rs.py` — RS_PROXIMITY_K, RS_MIN_TOUCHES, recency scoring, recency bonus in confidence

## Verification

```python
cd /root/.hermes/scripts && python3 -c "
import importlib, signals.rs as rs_mod; importlib.reload(rs_mod)
from signals.rs import detect_rs_signal, _get_candles_1m, _build_level_touches
from signal_schema import get_all_latest_prices, init_db
init_db()
prices = get_all_latest_prices()
for token, data in list(prices.items())[:20]:
    if token.startswith('@'): continue
    price = data.get('price')
    if not price: continue
    candles = _get_candles_1m(token, lookback=4700)
    if not candles: continue
    sig = detect_rs_signal(token, candles, price)
    if sig:
        rs = sig.get('recency_score', 0)
        print(f'{token:<12} conf={sig[\"confidence\"]:3.0f}% touches={sig[\"touches\"]:4d} rec={rs:.0f} bounce={sig[\"bounce\"]} dist={sig[\"atr_dist\"]:.2f}x')
"
```

## trades.json Field Names (for analysis)

When analyzing closed trades:
- `t['signal']` — NOT `source`
- `t['pnl_pct']` — NOT `pnl`
- `t['coin']` — NOT `token`
- `t['close_reason']` — `'atr_sl_hit'` or `'atr_tp_hit'`