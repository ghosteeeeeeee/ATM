# UNI NOT_HOTSET — Orphan Recovery Signal Loss (2026-06-19)

## Timeline

| Time | Event |
|------|-------|
| ~20:58 | Guardian SELF-CLOSE fires on UNI SHORT #1 (atr_sl_hit) — calls market_close |
| 20:59:04 | Guardian logs: `No HL close fills found for MET`... actually UNI — `[FAIL] No HL close fills found for UNI` |
| 20:59:04 | Guardian creates orphan recovery trade #12029: UNI SHORT @ 3.0462 x5 |
| 20:59:05 | Guardian marks orphan as copied — waits for fill |
| 21:00 | Guardian polls: fill NOT found for #12029 (Trade #1's close) |
| 21:00 | But Trade #2's close order finally fills on HL — UNI disappears from HL |
| 21:00:08 | Guardian sees `HL: 3 positions | DB: 3 open trades` then `HL: 2 positions | DB: 3 open trades` |
| 21:00:08 | UNI in Missing (DB-only) — not in hot-set at that moment |
| 21:00:08 | Guardian closes paper trade #12029 as NOT_HOTSET @ 3.04725 — LOCKS IN -0.81% loss |
| 21:00:14 | Step8: `Dedup: trade #12029 already closed this cycle, skipping` |

## Root Cause

Guardian created orphan recovery #12029 BEFORE the original close order filled. When the original close finally filled, the orphan recovery still had no signal (guardian orphans don't carry signal info). When the orphan appeared as Missing (DB-only), the hot-set check found UNI wasn't in it and closed with NOT_HOTSET — even though the actual HL close reason was atr_sl_hit.

## Two Closes, One Coin

- **Trade #1**: UNI SHORT @ 3.0254, closed 20:59:04, reason=atr_sl_hit (SELF-CLOSE caught the breach)
- **Trade #2**: UNI SHORT @ 3.0462, closed 21:00:08, reason=NOT_HOTSET (orphan recovery, wrong reason)

Both were the same UNI SHORT direction. The second was the orphan recovery of the first.

## Fix Required

When closing Missing (DB-only) paper trades, the guardian should NOT check hot-set. Missing means the paper trade has no corresponding HL position — the HL position is gone. The close reason should be determined by the HL fill data (atr_sl_hit was the actual reason) or the paper trade's existing close_reason, not a hot-set lookup.

The hot-set check is appropriate for Extra (paper-only) trades that need to be purged, NOT for Missing trades that have a corresponding HL close.

## Related

- Guardian orphan recovery creates trades without preserving the original signal
- NOT_HOTSET close reason used when hot-set check fires on a legitimate signal-driven orphan recovery
