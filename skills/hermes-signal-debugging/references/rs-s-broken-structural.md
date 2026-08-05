# rs-s-broken Structural Asymmetry (2026-06-03)

## Finding

The `rs-s-broken` SHORT dominance (52 of 59 pending SHORTs) is **not a bug**. It's structurally correct for downtrending markets. Understanding why:

### How rs-s-broken Fires

```
Support level identified at price S
Price crosses below S and stays below for 2+ candles within 200-candle window
→ broken = True
→ level still in proximity (within RS_PROXIMITY_K * ATR of current price)
→ direction = SHORT (broken support = resistance)
```

In a downtrend, price breaks through support levels repeatedly. Each broken support accumulates as a valid SHORT trigger because price keeps re-touching broken levels from below (they act as resistance). This is correct market mechanics.

### Why 52 rs-s-broken vs 13 normal rs-r

- `rs-r` (normal resistance SHORT): fires when intact resistance is near price
- `rs-s-broken` (broken support SHORT): fires when a previously intact support was breached

In a downtrend:
1. Intact resistances are ABOVE current price → few exist near price
2. Broken supports accumulate BELOW current price → many exist in proximity
3. Result: more rs-s-broken SHORTs fire than rs-r SHORTs

This is the correct behavior. The **reclassify patch** (moved outside `if broken:` block) enables a broken support that price has recovered ABOVE to correctly fall through to `rs-s` LONG rather than staying stuck as `rs-s-broken` SHORT.

### Not a Bug — Market Structure

The asymmetry reflects market structure (downtrending = more broken supports below price, fewer intact resistances above). The patches applied to rs.py are correct. The signal is valid.

What WOULD be a bug: firing rs-s-broken when price is far below the broken level (e.g., level=100, price=85, 15% below). The level needs to still be "near" current price to fire — confirmed by `RS_PROXIMITY_K` check.

### Solo SHORT Performance

Archive data shows solo SHORTs (no co-signal) avg_pnl=+80%. But this is selection bias — trades that become "solo" are special cases. The real SHORT co-signal win rate is 49% vs LONG co-signal 30%.