# ATR SL Direction Bug — SHORT SL Below Entry (2026-05-15)

## Bug: SHORT SL Placed Below Entry Instead of Above

**Symptom:** FIL SHORT trade (2026-05-14 20:28:06):
- Entry: 1.05370000
- SL: **1.00700000** (4.43% BELOW entry — WRONG for SHORT)
- TP: 0.99000000 (6.05% BELOW entry)
- Trade closed in **4 seconds** by `check_atr_tp_sl_hits()` — `lowest_price=1.0 < SL=1.007`

**Root cause:** `position_manager.py` `_collect_atr_updates()` — SHORT SL uses `ref_price = lowest_price` as anchor.

```python
# Lines 1599-1601:
if direction == "SHORT":
    ref_price = _peak_low if _peak_low > 0 else (current_price if ... else _entry)

# Line 1653 (pre-fix):
new_sl = round(ref_price * (1 + effective_sl_pct), 8)  # SHORT
```

For FIL SHORT: `ref_price = lowest_price = 1.0000` (price immediately fell to profit).

**The structural problem:** Both SL and TP are BELOW entry for a SHORT:
- SL=1.007 = 4.43% below entry → profit direction (price must RISE to hit it)
- TP=0.990 = 6.05% below entry → profit direction (price must FALL to hit it)

When price fell to 1.0 (best SHORT profit), it went BELOW the SL of 1.007. The protective SL was in profit territory. `check_atr_tp_sl_hits()` fires because `lowest_price=1.0 < SL=1.007` for SHORT.

---

## FIX APPLIED — position_manager.py line 1647-1654

```python
elif direction == "SHORT":
    # For NEW or IN-PROFIT SHORTs: anchor SL to _entry so it stays ABOVE entry.
    # Using ref_price (lowest_price) would place SL below entry when price has
    # already fallen — leaving the trade with zero protective barrier.
    # Established (underwater) SHORTs continue trailing from ref_price correctly.
    if is_new_trade or _in_profit:
        new_sl = round(_entry * (1 + effective_sl_pct), 8)
    else:
        new_sl = round(ref_price * (1 + effective_sl_pct), 8)
    new_tp = round(ref_price * (1 - effective_tp_pct), 8)
```

**Effect for FIL SHORT:**
- `is_new_trade=False` (diff = 5.1% >> 0.1% threshold) but `_in_profit=True` (4.28% gain)
- Before fix: `SL = 1.0000 × 1.007 = 1.0070` → below entry, no protection
- After fix: `SL = 1.0537 × 1.007 = 1.0611` → above entry, protects against reversal

Underwater SHORTs (`_in_profit=False`) correctly fall through to `ref_price` anchor — they have no profitable peak to protect, so trailing from the lowest tracked price is the right behavior.

---

## Key Lesson: SHORT SL Must Be Above Entry

| Direction | SL anchor | Purpose |
|-----------|-----------|---------|
| LONG | `ref_price` (highest_price or current) | Below current price — protects against drop |
| SHORT new/in-profit | `_entry` | ABOVE entry — protects against reversal/rise |
| SHORT underwater | `ref_price` (lowest_price) | Above lowest price — trails down as price falls |

The subagent audit confirmed: "anchor to _entry instead of ref_price gives a wider SL (more protective, not less protective) for new/in-profit SHORTs — no downside."

---

## Related: MON SHORT #9831 — SL Below Entry (Same Root Cause)

Same pattern: position_manager computed SL BELOW entry for SHORT, decider_run SL sanity check partially corrected it.

Trace (2026-05-14 22:10:02):
- position_manager computed: SL = 0.029626 (below entry 0.029884 — wrong direction)
- Log showed: `SL=0.029626` but DB shows `SL=0.02995129`
- Decider_run sanity check (line 630): `direction=='SHORT' and sl <= price` → reset to `price × 1.01`
- DB SL = 0.02995129 is just above entry (0.05%) — the sanity check corrected it, but the correction was still tighter than the proper 1% (1.01 for SHORT)

The root issue is the same: `_collect_atr_updates` computing SL from `ref_price` (lowest_price) when price had already fallen, producing a below-entry SL.