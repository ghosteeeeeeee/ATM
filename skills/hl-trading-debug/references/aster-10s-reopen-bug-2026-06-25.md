# ASTER 10-Second Reopen Bug — 2026-06-25

## Pattern

Same token, same direction, **two trades opened 32 seconds apart**, second trade loses money. First trade is a guardian_orphan that closes almost immediately.

**Concrete example from 2026-06-25 22:07-22:08 UTC:**

Trade #12193 (ASTER SHORT):
- open_time: 22:07:07.265264
- close_time: 22:07:35.104536 (28 seconds later)
- exit_reason: `guardian_tp`
- pnl: -$0.00 (breakeven)
- entry: 0.61304, exit: 0.61313, SL: 0.61902
- **highest_price in DB: 1.0** (default, never updated)

Trade #12194 (ASTER SHORT, **32 seconds after #12193 closed**):
- open_time: 22:08:07.121777
- close_time: 01:38:19.539335 (3.5 hours later)
- exit_reason: `guardian_sl` at 0.61712 (BEFORE the recorded SL of 0.61838 was hit)
- pnl: -$0.06

## Why This Is a Bug

1. **No cooldown after guardian_orphan close** — once a trade orphans out, the system is free to re-enter the same token 32 seconds later with no check. The signal_cooldowns table is keyed by signal type, not by previous-trade-on-token.

2. **highest_price=1.0 default is never updated for orphan trades** — the position_manager's `_poll_open_fill_once` / `highest_price` update logic is in the regular path but NOT in the orphan close path. So any trade that goes through guardian_orphan close has `highest_price=1.0` (the column default) in DB forever.

3. **guardian_sl fired before SL was hit** — the 1m price data shows price ranged 0.611-0.617 for 3.5h, never reaching SL 0.61838. The guardian computed a tighter SL on the fly and fired it. This is the same pattern as `guardian-self-close-stale-tp-sl-2026-06-13.md` — stale or wrong-direction SL used for breach check.

## Diagnostic Queries

```sql
-- Find pairs of same-token trades opened within 5 minutes of each other
SELECT a.id, b.id, a.token, a.direction,
       a.open_time, b.open_time,
       EXTRACT(EPOCH FROM (b.open_time - a.close_time)) as reopen_seconds
FROM trades a
JOIN trades b ON a.token = b.token
              AND a.direction = b.direction
              AND b.open_time > a.close_time
              AND b.open_time < a.close_time + INTERVAL '5 minutes'
WHERE a.status = 'closed' AND b.status = 'closed'
ORDER BY a.close_time DESC;

-- Find trades with suspicious highest_price (default = 1.0)
SELECT id, token, direction, entry_price, highest_price, current_price
FROM trades
WHERE highest_price = 1.0
  AND status IN ('open', 'closed')
ORDER BY open_time DESC
LIMIT 20;
```

## Fix Direction (requires T's approval before implementing)

1. **Token-level cooldown after guardian_orphan close:** in `_close_orphan_paper_trade_by_id` (or whichever path fires for orphans), also write a token-level entry to `signal_cooldowns` or a new `token_recent_trades` table. Block new entries for that token for N minutes (start with 5-10 min).

2. **Update `highest_price` in orphan path:** the position_manager logic that writes `highest_price` is in the regular update path. Add the same write to the orphan close path so DB doesn't carry a 1.0 default forever.

3. **Investigate guardian_sl firing before SL was hit on #12194** — likely a separate stale-SL bug from the same family as `guardian-self-close-stale-tp-sl-2026-06-13.md`.

## Related Patterns in Skill

- `references/guardian-self-close-stale-tp-sl-2026-06-13.md` — stale TP/SL used for breach check causing false triggers
- `references/guardian-silent-hl-failure-2026-06-18.md` — guardian closes via API error but DB trade still marked closed
- `references/metr-duplicate-open-2026-06-19.md` — MET SHORT duplicate open from close-fill-not-confirmed
- `references/instant-reopen-cooldown-gap-2026-05-14.md` — earlier instant-reopen cooldown gap
- `references/uni-not-hotset-orphan-signal-loss-2026-06-19.md` — orphan recovery closes with wrong reason
