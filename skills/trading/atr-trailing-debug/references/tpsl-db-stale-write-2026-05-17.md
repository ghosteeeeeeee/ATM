# TP/SL DB Write Failure — 2026-05-17

## Symptom
position_manager's `[TPSL]` debug log shows correct SL/TP values being computed via `tpsl_utils.compute_atr_sl_tp()`, but brain DB (`trades.stop_loss/target`) retains the stale original pump-mode values set at entry time.

Display layer (`trades.json` via `update-trades-json.py`) inherits the stale DB values.

## Positions affected
| Coin | Stale SL (in DB) | Correct SL (PM output) | Stale TP (in DB) | Correct TP (PM output) |
|------|-----------------|----------------------|-----------------|----------------------|
| ETH SHORT | 2210.01 | 2183.08 | 2122.92 | 2122.92 |
| AVAX SHORT | 9.3964 | 9.2954 | 9.0261 | 9.0261 |
| XMR SHORT | 399.194 | 395.96 | 383.46 | 383.46 |

## Root cause hypothesis
`_persist_atr_levels()` (position_manager.py line 1710) is the sole writer of ATR SL/TP to brain DB. The function's gate at line 1690:

```python
if needs_sl or needs_tp or sl_stale or tp_stale or is_init_to_accel:
```

For in-profit SHORTs with existing (but stale) SL/TP already in DB, `needs_sl` may be `False` because the trailing gate in `tpsl_utils.compute_atr_sl_tp()` only sets `needs_sl=True` when the new SL would be **below** the current SL for SHORTs. If the stale SL (2210.01) is above the computed new SL (2183.08), `needs_sl=True` — correct.
If the stale SL is below the computed new SL, `needs_sl=False` — write is skipped.

BUT the actual values show the stale SL is ABOVE the correct SL for all three tokens (2210.01 > 2183.08, 9.3964 > 9.2954, 399.194 > 395.96), so `needs_sl` should be True. The write should succeed.

**Contradiction:** The DB has stale values despite this. Something is blocking the UPDATE.

## Debugging steps (next session)
1. Add print at start of `_persist_atr_levels()` confirming trade_id and new_sl/new_tp values are received
2. Add print after `cur.execute()` to log `cur.rowcount` — how many rows were actually updated
3. Check if `WHERE id = %s AND status = 'open'` is matching — trade IDs may be integer vs string mismatch
4. Verify `_collect_atr_updates()` isn't returning empty `updates` list for these specific trades
5. Check if `highest_price`/`lowest_price` re-read from DB at line 1581 is returning None/0, causing the trailing gate to compute no-change
6. Confirm the `[TPSL]` log and the `_persist_atr_levels()` call happen in the same pipeline cycle — separate logging vs actual write timing

## Key files
- `position_manager.py:_collect_atr_updates()` line 1531 — computes updates
- `position_manager.py:_persist_atr_levels()` line 1710 — writes to DB
- `position_manager.py:check_atr_tp_sl_hits()` line 2350 — reads back from DB for hit detection
- `tpsl_utils.py:compute_atr_sl_tp()` — computes SL/TP, contains trailing gate logic
- `update-trades-json.py` — display layer, reads from brain DB