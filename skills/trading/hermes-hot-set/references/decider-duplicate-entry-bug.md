# MON Duplicate-Entry Bug — Decider Run (2026-05-14)

## What Happened

MON SHORT opened twice on 2026-05-14:
- 21:47:03 — MON SHORT #9830, entry=0.030064, closed by profit-monster at 21:47:07 (+$1.31, 4 sec)
- 22:10:06 — MON SHORT #9831, entry=0.029884, closed by profit-monster at 22:10:07 (+$1.46, 1 sec)

Guardian showed no orphan at either timestamp. The two entries were 23 minutes apart, not seconds.

User described it as "in seconds" because profit-monster closed #9830, then 23 minutes later the pipeline opened #9831 — the rapid close→reopen pattern made it appear as duplicate entries.

## Actual Bug (Not Duplicate Entry)

The root issue was NOT duplicate entries for the same direction. The bug was:
- `profit-monster` closed the position via `brain.py trade close --close-reason profit-monster`
- `brain.py close_trade()` does NOT call `_record_loss_cooldown()` for closing trades
- The cooldown system only records when `_record_loss_cooldown(token, direction)` is called
- profit-monster bypasses cooldown entirely → MON could be immediately re-entered

## Per-Run Token Dedup Fix (2026-05-15)

**File:** `decider_run.py`, top of the scored loop

**Problem:** `signal_compactor` can emit duplicate token+direction entries in the same hotset. The PostgreSQL duplicate check in `brain.py add_trade()` reads the DB state at the START of decider_run — it doesn't track tokens already processed IN THE CURRENT RUN.

**Fix applied:**
```python
# At line ~1513 (top of scored loop)
entered = 0
skipped = 0
_processed_tokens_this_run = set()   # ← NEW

for i, sig in enumerate(scored):
    # ... hotset reload ...
    
    # After hotset token check:
    if token in _processed_tokens_this_run:
        log(f'  [SKIP] {token} {direction} — already processed in this pipeline run')
        if sig_id:
            mark_signal_executed(token, direction, 'SKIPPED', signal_id=sig_id)
        skipped += 1
        continue
    _processed_tokens_this_run.add(token)
```

**Behavior:** First occurrence of a token in the pipeline run is processed. Any subsequent signal for the same token (any direction) is skipped. This is slightly over-blocking (MON SHORT then MON LONG would both be blocked), but safe — capital is already deployed, and opposite-direction entries right after are questionable.

## profit-monster Cooldown Bypass (Separate Issue)

profit-monster does NOT call `_record_loss_cooldown()` after closing:

```python
# brain.py close_trade() line 661:
if hype_pnl_usdt is not None and hype_pnl_usdt < 0:
    _record_loss_cooldown(token, direction)  # ← only called on LOSS
```

profit-monster closes only profitable positions (by design), so `hype_pnl_usdt < 0` is never true → no cooldown recorded.

If immediate re-entry after profit-monster close is undesired, profit-monster should call `_record_loss_cooldown()` or at minimum record a signal cooldown for the token after closing.