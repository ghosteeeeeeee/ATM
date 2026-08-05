# Instant Reopen — Loss Cooldown Gap (2026-05-14)

## Symptom

Guardian closes CHIP:SHORT at 15:18:50 (loss). CHIP:SHORT reopens at 15:19:29 (39 seconds). LAYER:SHORT closed at 14:34:54, reopened at 14:35:21 (27 seconds).

## Root Cause — Cooldown Architecture Gap

`_is_loss_cooldown_active()` in signal_compactor.py (line 680) only blocks cooldowns with `reason in ('loss', 'guardian')`. It **completely ignores** `reason='signal'` cooldowns written by signal generators.

### How cooldowns are written

**Signal generator path** (e.g. accel_300.py, gap300.py):
```python
# signal_compactor.py — set_cooldown()
cooldowns[token_key] = {
    'expires': time.time() + cooldown_seconds,
    'reason': 'signal',   # ← signal generators always write this
    'hours': 0.1667,
    ...
}
```

**Guardian path** (hl-sync-guardian.py — `_close_paper_trade_db`):
```python
# Only writes cooldown if PnL < 0
if final_pnl_usdt < 0:
    _record_loss_cooldown(token, 'guardian', ...)
```

### Why CHIP reopened

CHIP:SHORT cooldown entry has `reason='signal'` (written by accel_300's own `set_cooldown()`). The guardian's `_is_loss_cooldown_active` never blocks it — it only looks for `'loss'` or `'guardian'`.

Even if guardian DID write a `reason='guardian'` entry, there's a second gap: guardian only writes that entry when `pnl_usdt < 0`. A near-breakeven close (e.g., -$0.12) might not trigger it.

### Why 'signal' cooldowns exist

They were designed as **internal per-generator deduplication** — preventing the same signal script from firing repeatedly for the same token+direction within a short window. They are NOT loss cooldowns and are intentionally excluded from `_is_loss_cooldown_active`.

## Fixes Needed

### Fix 1 — Guardian: always write cooldown regardless of PnL

In `hl-sync-guardian.py` `_close_paper_trade_db()` (line ~2561):
```python
# CHANGE FROM:
if final_pnl_usdt < 0:
    _record_loss_cooldown(token, 'guardian', ...)

# CHANGE TO:
# Always record cooldown when closing, regardless of PnL
_record_loss_cooldown(token, 'guardian', ...)
```

Even a 1-cent loss should block re-entry. Near-breakeven closes are still losses relative to entry price.

### Fix 2 — Close orphan path: also record cooldown

`close_orphan_paper_trades()` currently calls `_save_closing_marker()` only for `STALE_ROTATION` closes. It should also record a cooldown for `MAX_POSITIONS` and other non-loss closes.

### Fix 3 — `_is_loss_cooldown_active`: also check 'signal' cooldowns

When checking a signal cooldown, also check if there's an active `reason='signal'` cooldown for the same token+direction. The guardian closed this — the signal shouldn't re-fire immediately:

```python
# In _is_loss_cooldown_active (signal_compactor.py ~line 680)
def _is_loss_cooldown_active(token, direction, reason=None):
    # ... existing check for 'loss'/'guardian' ...
    
    # Also block if there's an active 'signal' cooldown for same token+direction
    token_key = f"{token}:{direction}"
    sig_cooldown = cooldowns.get(token_key, {})
    if sig_cooldown.get('reason') == 'signal' and sig_cooldown.get('expires', 0) > time.time():
        # Signal generator cooldown active — block it
        return True
```

### Fix 4 — Clear 'signal' cooldown when guardian closes

When guardian closes a position, clear any `reason='signal'` cooldown that exists for that token+direction. The guardian took over — the signal generator's cooldown is no longer relevant.

## Diagnostic

Check current cooldown states:
```bash
python3 -c "
import json
with open('/root/.hermes/data/loss_cooldowns.json') as f:
    d = json.load(f)
for k, v in d.items():
    if v.get('reason') == 'signal':
        remaining = max(0, v['expires'] - __import__('time').time())
        print(f'{k}: signal, {remaining:.0f}s remaining')
"
```

## Related Files

- `signal_compactor.py` line 680: `_is_loss_cooldown_active` — only blocks 'loss'/'guardian'
- `signal_compactor.py` line 1316: `_filter_safe_prev_hotset` — checks cooldown for previous hotset
- `hl-sync-guardian.py` line 2561: `_close_paper_trade_db` — only writes cooldown for `pnl_usdt < 0`
- `hl-sync-guardian.py` line 2186-2238: `close_orphan_paper_trades` — missing closing markers for MAX_POSITIONS
- `brain.py` line 38: `_record_loss_cooldown` writes `reason='brain'`
- `cascade_flip.py` line 208: `_record_loss_cooldown` writes `reason='cascade'`