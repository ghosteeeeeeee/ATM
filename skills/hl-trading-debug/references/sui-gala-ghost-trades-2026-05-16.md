# SUI LONG + GALA SHORT Ghost Trades — 2026-05-16

## SUI LONG Trade #10051 (PostgreSQL) — SL at Entry Instead of Below

**Symptom:** Entry=1.064, SL=1.0923 (above entry for LONG). Position opened and closed in 3 seconds by `atr_sl_hit`.

**Root cause:** In `compute_atr_sl_tp()`, when a trade is freshly opened, `is_new_trade = (highest_price == entry)` gate should use `entry_price` as the SL anchor. But `highest_price` is read from the DB row — at trade creation time it is set to `hl_entry if direction == 'LONG' else 0`. If HL fills at a slightly different price than `entry`, or if the guardian reads the row before this value is properly set, the anchor becomes `highest_price > entry`, bypassing the new-trade breathing room and applying full phase/k scaling immediately.

**Affected code path:**
1. `hl-sync-guardian` calls `mirror_open` → `brain.py add_trade` inserts row with `highest_price = hl_entry`
2. `position_manager._collect_atr_updates()` reads back `highest_price` from DB
3. `compute_atr_sl_tp()` sees `highest_price == entry` (or `> entry`) → `is_new_trade` may already be False
4. Phase/k scaling applied immediately → SL placed at wrong level

**Fix (tpsl_utils.py `compute_atr_sl_tp`):** When `is_new_trade` is True, force `ref_price = entry_price` regardless of `highest_price`. The new-trade phase exists specifically to give the position breathing room — it should not be skipped because of a pre-existing `highest_price` value.

## GALA SHORT Trade #10046 (PostgreSQL) — SL Exactly at Entry

**Symptom:** Entry=0.00341, SL=0.00341 (exactly at entry). Any upward movement triggers SL immediately. Trade closed at small loss, guardian immediately reopened a second SHORT at 0.00341.

**Root cause:** GALA's initial SL was computed using `sl_distance=0.03` (3%) as a placeholder, but `stop_price = entry_price` for SHORT means `entry × (1 + 0.03) = entry` (rounded). The 3% multiplier on the wrong side of entry results in SL = entry.

Additionally: only the second small loss trade (#9847) was recorded locally. The first GALA SHORT trade was closed on HL (presumably via an HL TP/SL order that was placed but should not have been) — guardian then opened #9847 to close the orphan, but since the first close left no local record, this appears as a fresh orphan close.

**Guardian/Orphan pattern confirmed:**
- First GALA SHORT: closed on HL (not locally recorded) — likely an HL-side TP/SL triggered
- Guardian detected orphan → opened trade #9847 → closed it seconds later at loss
- Only #9847 appears in local DB; first trade is ghost

## Key Diagnostic

```python
# SUI ghost trade — check if highest_price > entry at creation time
conn = psycopg2.connect(**BRAIN_DB_DICT)
cur.execute("""
    SELECT trade_id, token, entry_price, highest_price, stop_loss, direction
    FROM trades WHERE token='SUI' AND status='closed'
    ORDER BY opened_at DESC LIMIT 3
""")
# If highest_price > entry_price for a brand-new trade → anchor bug

# GALA ghost trade — check if SL == entry for SHORT
cur.execute("""
    SELECT trade_id, token, entry_price, stop_loss, exit_price, close_reason
    FROM trades WHERE token='GALA' ORDER BY opened_at DESC LIMIT 5
""")
# If stop_loss == entry_price → SL at entry bug
```

## References

- `references/atr-tp-sl-authority-2026-05-15.md` — ATR computation authority, phase system, trailing SL logic
- `references/hl-db-insert-silent-failure.md` — guardian orphan path when DB INSERT fails after HL confirm
