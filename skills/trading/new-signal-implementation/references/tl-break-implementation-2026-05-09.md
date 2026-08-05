# tl_break Signal Implementation — 2026-05-09

## Pattern Described by T
- Sustained diagonal downtrend (6-10h on 5m charts)
- Price bounces off the diagonal trendline, forming a horizontal resistance zone at bounce points
- Decisive breakout above the diagonal → LONG entry
- Same logic in reverse for shorts

## Why ME and 2Z Didn't Fire (Root Causes)

**ME** (`slope=-1.17e-06`):
- Slope was too flat — met the threshold but marginal
- Only 1 valid bounce in the lookback window (need 2+)
- The diagonal portion was ~5-6h, then flat for 4-5h — regression averages the flat portion, weakening the slope

**2Z** (`slope=+2.93e-05`, valid SHORT):
- 2 bounces found at indices [26, 74]
- BUT bounces didn't cluster within `TL_ZONE_ATR_K=0.75` — `zone_price=None`
- Bounce cluster logic: bounces within `0.75 * ATR` price distance → horizontal zone
- 2Z's bounce prices at indices 26 and 74 were too far apart to cluster
- Breakout check skipped because `zone_price=None`

## Fixes Applied

1. **`_get_candles_5m` query order**: `ORDER BY ts ASC` → `ORDER BY ts DESC` + `list(reversed(rows))`
2. **Freshness guard**: 300s → 600s (5m candles have update lag)
3. **Slope thresholds**: tuned to absolute minimum `1e-6` to catch ME's flat -0.66% over 10h
4. **`TL_ZONE_ATR_K`**: 0.75 → 1.5 (bounces at indices [26, 74] need more room to cluster)
5. **`RS_PROXIMITY_K`**: 1.20 → 1.00 (fires closer to level = earlier entry) — same fix applies to tl_break

## Remaining Debugging

Signal still not firing for ME (bounce count=1) and 2Z (zone_price=None). Options:

1. **Reduce `TL_MIN_BOUNCES` from 2 to 1** — single bounce still forms a zone
2. **Add "recent slope" check** — last 30-40 candles must also show diagonal direction
3. **Widen bounce price tolerance further** — try `TL_ZONE_ATR_K=2.0`
4. **Reduce lookback to 60 candles (6h)** — focus on the actual diagonal portion

## Key Params (Current)

```python
TL_SLOPE_LONG     = -0.000001   # negative slope for LONG diagonal
TL_SLOPE_SHORT    =  0.000001   # positive slope for SHORT diagonal
TL_SLOPE_MAG_MIN  =  0.000001   # minimum absolute slope magnitude
TL_ZONE_ATR_K     =  1.5        # bounce clustering tolerance (×ATR)
TL_MIN_BOUNCES    =  2          # minimum bounces to form zone
TL_BREAKOUT_ATR   =  1.5        # breakout confirmation (×ATR)
TL_FOLLOW_ATR     =  2.0        # follow-through requirement (×ATR)
TL_COOLDOWN_HRS   =  2          # cooldown between signals
```

## signal_metadata Output

```python
{
    "tl_break": {
        "slope": float,           # linear regression slope
        "slope_pct": float,       # slope as % of price
        "zone_price": float,      # clustered horizontal zone price
        "bounce_count": int,      # total bounces found
        "breakout_pct_atr": float,# breakout distance in ATR units
        "follow_through": float   # follow-through in ATR units
    }
}
```

## Registration

```python
# hermes_constants.py
TL_BREAK_ENABLED = True

# signals/__init__.py
from signals.tl_break import scan_tl_break_signals
SIGNAL_REGISTRY.append({'name': 'tl_break', 'enabled': 'TL_BREAK_ENABLED', 'run': scan_tl_break_signals})
```

## Testing Pattern

```python
import sys; sys.path.insert(0, '/root/.hermes/scripts')
from signals.tl_break import detect_tl_break, _get_candles_5m

for token in ['ME', '2Z']:
    candles = _get_candles_5m(token, 120)
    if candles:
        price = candles[-1]['close']
        sig = detect_tl_break(token, candles, price)
        if sig:
            print(f'SIGNAL: {sig["direction"]} conf={sig["confidence"]}')
        else:
            print(f'No signal')
```