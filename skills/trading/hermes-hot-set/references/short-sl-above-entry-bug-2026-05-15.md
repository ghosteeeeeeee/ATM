# SHORT SL Above Entry Bug — 2026-05-14/15

*Session-specific diagnostic — archived from `hermes-hot-set` skill.*

## Symptom

TAO SHORT, 2Z SHORT, and ZK SHORT all opened with stop-loss prices ABOVE their entry prices:
- TAO SHORT: entry=302.750, SL=303.365 (+0.20% above entry)
- 2Z SHORT: entry=0.100350, SL=0.101052 (+0.70% above entry)
- ZK SHORT: entry=0.017633, SL=0.017756 (+0.70% above entry)

Same bug affected FIL SHORT on 2026-05-14.

## Root Cause

`position_manager.py` anchor logic for SHORT positions sets the SL at `entry_price × (1 + ATR_mult × ATR / entry_price)`. This places the SL **above** the entry for SHORT, which is backwards — a SHORT needs to be closed when price moves UP past the SL (against the short direction).

The anchor is meant to lock in profit for SHORTs that are in profit. But the same formula was applied to ALL SHORTs (new positions and in-profit ones), causing new SHORT entries to have inverted SL placement.

## The Fix

Position manager anchor logic for SHORTs needs to distinguish:
1. **New SHORTs (no/minimal profit):** SL should be BELOW entry (standard SHORT stop-loss)
2. **In-profit SHORTs (profit > threshold):** SL anchors ABOVE entry to lock in profit

The anchor should only activate when `profit_pct > ANCHOR_ACTIVATION_PCT` (e.g., 0.5%), not on every SHORT position.

## Related

See `references/decider-duplicate-entry-bug.md` for the MON duplicate entry investigation from the same session.