# RS Signal Implementation — Support/Resistance (2026-05-07, updated 2026-06-04)

## Current Status: WORKING ✅
RS signals are live and firing correctly. Last update: constants consolidated into hermes_constants.py.

## Architecture
```
signals/rs.py
    scan_rs_signals(prices_dict)  → writes to signals DB via add_signal()
    ├── _get_candles_1m()         → price_history table (signals_hermes.db), close-only O=H=L=C
    ├── _find_swing_highs_lows()  → rolling window swing detection
    ├── _build_level_touches()    → ATR-normalized touch counting
    ├── _cluster_levels()         → clusters nearby levels within RS_CLUSTER_ATR
    ├── _price_near_level()       → within RS_PROXIMITY_K ATRs of level
    ├── _bounce_confirmation()   → ATR-based proximity + subsequent price movement
    ├── _level_recently_broken() → open/close crossing detection
    └── _compute_confidence()     → log-scale touch bonus, 50-88 range

Signal output:
    signal_type = 'support_resistance'
    source = 'rs-s{touch_count}' or 'rs-r{touch_count}'  ← touch count encoded in source
    confidence = 50-88
```

## Canonical Constants — hermes_constants.py (SINGLE SOURCE OF TRUTH)

All RS constants live in `hermes_constants.py`. `signals/rs.py` imports from there.
**Do NOT add duplicate hardcoded constants in `signals/rs.py`.**

```python
RS_LOOKBACK_CANDLES   = 4700   # max available (~3+ days of 1m)
RS_LEVEL_LOOKBACK    = 300     # swing high/low detection window
RS_ATR_PERIOD        = 30      # ATR lookback for proximity normalization
RS_CLUSTER_ATR       = 1.0     # cluster levels within 1.0 × ATR
RS_PROXIMITY_K       = 0.70    # fire if price within 0.70 × ATR of level
RS_MIN_TOUCHES       = 3       # minimum historical touches
RS_COOLDOWN_HOURS    = 4
RS_SIGNAL_TYPE       = 'support_resistance'
RS_SOURCE_PREFIX     = 'rs'
RS_MIN_CONFIDENCE    = 50
RS_MAX_CONFIDENCE    = 88
RS_RECENCY_WINDOW    = 200     # recency weighting lookback
RS_RECENCY_BOOST_K   = 3.0     # multiplier: recent touch = K ancient touches
RS_BOUNCE_LOOKBACK   = 6       # candles to check for bounce confirmation
RS_BOUNCE_THRESH_ATR = 1.00    # touch = price within 1.00 × ATR(14) of level
```

### Bug #16: Constant Drift — signals/rs.py vs hermes_constants (FIXED 2026-06-04)
**Symptom**: `signals/rs.py` had hardcoded duplicates of RS constants that diverged from
`hermes_constants.py` (PROXIMITY_K=0.70 vs 1.75, MIN_TOUCHES=3 vs 8, COOLDOWN_HOURS=4 vs 0.25, etc.).
Live behavior used the hardcoded values; developers thought they were tuning hermes_constants.

**Fix applied**:
- All RS constants moved to `hermes_constants.py`
- `signals/rs.py` now imports: `from hermes_constants import RS_PROXIMITY_K, RS_MIN_TOUCHES, ...`
- `_BOUNCE_LOOKBACK` / `_BOUNCE_THRESH_ATR` renamed to `RS_BOUNCE_LOOKBACK` / `RS_BOUNCE_THRESH_ATR`

**Prevention**:
1. All RS constants MUST be defined in `hermes_constants.py` only.
2. When adding a new RS constant, add to `hermes_constants.py` first, then import.
3. Before tuning any RS constant, verify it is read from hermes_constants by the running process.
4. `rs_signals.py` (top-level) also has hardcoded values — same drift risk, consolidate if editing.

## Bug Fixes Applied (2026-05-07)

### Bug 1: Touch count 100× too high
**Root cause**: `_build_level_touches` used fixed 0.15% threshold on close-only data.
Every candle's close equaled every other candle's close → any level matched ALL candles.

**Fix**: `threshold = atr_value × RS_BOUNCE_THRESH_ATR` — ATR-normalized threshold.

### Bug 2: Bounce confirmation always False
**Root cause**: `_bounce_confirmation` checked `c['close'] > c['open']` on close-only candles.

**Fix**: ATR-based proximity + subsequent price movement:
```python
# Price touched level (within RS_BOUNCE_THRESH_ATR × ATR) AND next candle moved away = bounce
for i, c in enumerate(recent):
    if abs(c['close'] - level) < thresh:
        if i + 1 < len(recent):
            next_close = recent[i + 1]['close']
            if direction == 'LONG' and next_close > c['close'] * 1.0005:
                return True
```

### Bug 3: _level_recently_broken always True
**Root cause**: Used `high`/`low` which equal `close` on this data.

**Fix**: Use open/close crossing:
```python
# Resistance broken: opened below level, closed above
if opened < level < closed: return True
# Support broken: opened above level, closed below
if opened > level > closed: return True
```

### Bug 4: ATR band filter rejecting valid signals (REMOVED)
**Root cause**: `_RS_ATR_BAND_SOFT_MIN=0.30`, `_RS_ATR_BAND_SOFT_MAX=0.60` rejected
the exact range where you want signals (price near level = good).

**Fix**: Band filter removed entirely.

## Touch Count Quality Bands (Live Data — CONFIRMED)
From signal_outcomes analysis of historical RS+accel-300+ combo wins:
| Touch Count | WR | Avg Peak | Status |
|-------------|-----|---------|--------|
| rs-s < 16 | 0% | catastrophic | Weak level |
| **rs-s 16–150** | **100%** | **+343%** | **GOLD ZONE** |
| rs-s > 150 | 0% | -27% to -184% | Stale level |

**RS touch count IS the quality filter.** When combining with accel-300+:
- `accel-300+,rs-s48` → PURR +474%, GRIFFAIN +526%
- `accel-300+,rs-s72` → DASH +344%

## Naming Convention
Source field encodes touch count: `rs-s{touch_count}`.
- Found in signal_outcomes for winners: `accel-300+,rs-s48`, `accel-300+,rs-s150`

## Data Source Note
**price_history is close-only**: `open=high=low=close` for every candle.
RS detection uses this correctly (swing highs/lows from close values are valid).
Do NOT assume O/H/L columns have distinct values for this data source.
