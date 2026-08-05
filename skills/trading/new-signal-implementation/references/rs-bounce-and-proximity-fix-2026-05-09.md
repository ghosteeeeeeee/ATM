# RS Signal Implementation — Bounce Confirmation Fix (2026-05-09)

## Files
- `/root/.hermes/scripts/signals/rs.py` — canonical implementation
- `/root/.hermes/scripts/hermes_constants.py` — RS_* constants

## Key Constants (2026-05-09 applied)
```python
RS_LOOKBACK_CANDLES   = 4700  # ~3+ days of 1m
RS_LEVEL_LOOKBACK     = 20    # swing high/low detection window
RS_ATR_PERIOD         = 14
RS_CLUSTER_ATR        = 0.50  # cluster levels within 0.50 * ATR
RS_PROXIMITY_K        = 1.00  # fire if price within 1.00 * ATR of level (tightened from 1.20)
RS_MIN_TOUCHES        = 8     # minimum touches to be valid (raised from 5)
RS_COOLDOWN_HOURS     = 4
RS_MIN_CONFIDENCE     = 50
RS_MAX_CONFIDENCE     = 88    # cap — R&S is structural, not momentum

# Bounce confirmation (2026-05-09 fix applied)
_BOUNCE_LOOKBACK      = 6     # candles to check for bounce
_BOUNCE_THRESH_ATR    = 1.00  # touch: within 1.00 * ATR(14) of level (raised from 0.20)
```

## Bounce Confirmation Fix (2026-05-09)

**Problem:** `_BOUNCE_THRESH_ATR=0.20` was 31x too tight for most tokens. For ADA at $0.272:
- ATR = 0.0000653 → threshold = 0.000013 (0.0048% of price)
- Price must be within 0.005% of the level — impossible to satisfy
- Fallback (`price * 0.0015`) is 31x wider but never used

**Result:** Every RS signal showed `bounce=False` — bounce confirmation was completely broken.

**Fix applied:**
- `_BOUNCE_THRESH_ATR`: 0.20 → 1.00 (5x more forgiving)
- `RS_MIN_TOUCHES`: 5 → 8 (only stronger structural levels qualify)
- `RS_PROXIMITY_K`: 1.20 → 1.00 (fire closer to the level = earlier entry)

**Effect:**
- BIGTIME is first token to achieve `bounce=True`
- Signal count dropped from 11 → 8 tokens (fewer but higher quality)
- `bounce=True` now earns the +5 confidence bonus

## Key Insight: price_history is Close-Only

`signals_hermes.db` → `price_history` table has `open=high=low=close` for every row.
This means:
- Traditional ATR (H-L, |H-PC|, |L-PC|) = 0 for every row
- Bounce detection must use close prices only
- Swing highs/lows detected via rolling max/min of closes

## Bounce Detection Logic (post-fix)

```python
# Two conditions, either/or:
# (a) touch candle was bullish (close > open) → fires immediately
# (b) next candle moved >0.025% in signal direction → partial follow-through

if direction == 'LONG':
    for i, c in enumerate(recent):
        if abs(c['close'] - level) < thresh:  # close at the level
            if c['close'] > c['open']:          # (a) this candle was bullish
                return True
            if i + 1 < len(recent):              # (b) next candle follow-through
                if next_close > c['close'] * 1.00025:
                    return True
```

## Level Recently Broken Fix (2026-05-08)

`_level_recently_broken()` checked `opened < level < closed` — impossible with
`open == close` on synthesized candles. Changed to compare successive candle closes:

```python
# Resistance broken: prev_close < level < curr_close
# Support broken:   prev_close > level > curr_close
for i in range(1, len(recent)):
    prev_close = recent[i - 1]['close']
    curr_close = recent[i]['close']
    if prev_close < level < curr_close: return True
    if prev_close > level > curr_close: return True
```

## HH_HL Threshold Bug (2026-05-09)

**Separate bug in `signals/hh_hl.py`:** `breakout_strength` from `_classify_structure()` is
in **percent units** (e.g., `0.014 = 0.014%`), but `HH_HL_BREAKOUT_THRESHOLD = 0.0005` is in
**decimal fraction** (0.05%). Comparison `0.014 >= 0.0005` always True → phantom breakouts.

**Fix:** Normalize before comparing:
```python
if structure == 'HH_HL' and (breakout_strength / 100) >= HH_HL_BREAKOUT_THRESHOLD:
```

Full trace: `references/hh-hl-threshold-bug-2026-05-09.md`