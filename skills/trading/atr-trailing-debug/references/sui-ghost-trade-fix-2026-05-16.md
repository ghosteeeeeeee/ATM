# SUI Ghost Trade — ATR SL Initial Computation Bug

**Date:** 2026-05-16
**Trade:** SUI LONG #10051 — opened and closed in 3 seconds.

## The Bug

`compute_atr_sl_tp()` in `tpsl_utils.py` has a gate meant to detect new trades:

```python
is_new_trade = (highest_price == entry_price and pnl_pct >= 0)
```

This gate controls whether INIT k (0.5) and INIT floors (0.50%) are applied for the initial SL computation.

**Failure mode:** If price moves against the trade between `mirror_open` and the first ATR cycle:
1. `pnl_pct < 0` (trade is underwater)
2. `is_new_trade = False` — the INIT floor is bypassed
3. Phase k (1.0 for neutral, 0.75 for NORMAL_VOL) is applied immediately
4. `ref_price = highest_price` which equals `entry` (set at DB INSERT)
5. LONG: `new_sl = entry × (1 + k × atr_pct)` → SL placed **above** entry
6. Next cycle: price ticks up → `atr_sl_hit` fires → trade closed in seconds

**Key invariant that should have prevented this:** For a LONG trade, SL must always be **below** entry (protective). For a SHORT, SL must always be **above** entry. The bug violates this invariant on new trades.

## The Fix

When `current_sl <= 0` (no SL written to DB yet) AND `highest_price ≈ entry` AND `is_new_trade=False` (due to negative PnL): force INIT treatment using `entry_price` as the reference anchor.

```python
# In compute_atr_sl_tp(), replace or extend the is_new_trade gate:
force_init = (
    not is_new_trade
    and current_sl <= 0
    and abs(highest_price - entry_price) / entry_price < 0.001  # peak ≈ entry
)

if is_new_trade or force_init:
    # INIT treatment: wider k (0.5), INIT floors, entry_price as anchor
    eff_sl_pct = max(INIT_K * sl_pct, INIT_SL_MIN)
    ref_price = entry_price
    ...
```

**For SHORT:** Verify the same fix applies correctly. SHORT initial SL should be placed **above** entry using `entry × (1 + eff_sl_pct)`. With `ref_price = entry_price`, this produces the correct direction.

## Why sl_distance=0 in the trade record

The `sl_distance` column in `trades` is set at INSERT time from the A/B test value (control=0.03, test_a=0.015, test_b=0.01). The `stop_loss` price column is what position_manager writes via `_persist_atr_levels()`. `sl_distance=0` means the A/B distance field wasn't updated post-INSERT — but the computed price `stop_loss=1.0923` was written correctly by the ATR engine.

## SUI ATR values at time of trade

- ATR(14) = 0.005157 (~0.52% per bar)
- Entry = 1.064
- Correct initial SL: `1.064 × (1 - max(0.5×0.0052, 0.005)) = 1.064 × 0.995 ≈ 1.0587` (below entry, correct)
- Buggy SL: `1.064 × (1 + 0.75×0.0052) = 1.064 × 1.0039 ≈ 1.068` (above entry, wrong — but the actual was 1.0923, suggesting an even more aggressive k or a different formula path)

The exact 1.0923 value needs code trace — likely an even higher k multiplier or a mis-applied TP formula in the same computation pass.

## Open Questions

1. Why did `pnl_pct < 0` on the first ATR cycle? Price would need to move below entry immediately after open. This could happen if HL fills at a price worse than the entry recorded in the DB, or if there's a delay between `mirror_open` and the first ATR cycle during which price moved down.
2. Confirm the SUI entry price in HL vs the DB entry — if HL filled at 1.064 but price immediately dropped below that, that would trigger the negative PnL path.