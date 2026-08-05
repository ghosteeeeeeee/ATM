# Guardian Duplicate Orphan Trades — 2026-06-12 Audit (2nd Pass)

## Overview

Second audit pass on hl-sync-guardian.py after applying the first-pass fixes.
Manual verification found 2 additional bugs introduced by the first-pass patches.

## Bug A — CRASH: `close_ok` NameError (self-introduced)

**Severity**: CRASH (NameError at runtime)  
**Introduced by**: First-pass patch that restructured the orphan close `if-else` block  
**Root cause**: The dedup path (`orphan_id in _CLOSED_THIS_CYCLE`) was inside the `else` branch. `close_ok` was only assigned inside the inner `else` block. When dedup triggered, `close_ok` was undefined — referenced at `if close_ok:` outside the `else` block → `NameError`.

```python
# BEFORE (broken — close_ok only in inner else)
orphan_row = cur_orphan.fetchone()
if orphan_row:
    ...
    if orphan_id in _CLOSED_THIS_CYCLE:
        log(f'  Dedup: skipping')  # close_ok NOT set here
    else:
        close_ok = _close_orphan_paper_trade_by_id(...)  # only path that sets close_ok
# close_ok referenced here — NameError when dedup path fires!
if close_ok:
    _clear_closing_marker(coin)
```

**Fix**: Initialize `close_ok = False` before the `if-else` block:

```python
orphan_row = cur_orphan.fetchone()
close_ok = False  # default: not confirmed close (covers dedup/no-record cases)
if orphan_row:
    ...
```

**Verification**: `python3 -m py_compile hl-sync-guardian.py` → Syntax OK

## Bug K — MEDIUM: `pending_gone` Infinite Retry Leak (self-introduced)

**Severity**: MEDIUM (infinite retry loop, never terminates)  
**Introduced by**: First-pass patch moved `_clear_pending_retry` inside `if trade_id:` block  
**Root cause**: When a pending-retry token fell out of HL (close succeeded but pending retry not cleared), the `pending_gone` handler checked `if trade_id:` before clearing. If `_get_reconciled_trade_id()` returned None, the `else` branch didn't exist — `_clear_pending_retry` was never called for that token. Token stays in `_PENDING_RETRY_FILE` forever → infinite retry loop every cycle.

```python
# BEFORE (broken)
for tok in pending_gone:
    trade_id = _get_reconciled_trade_id(tok)
    if trade_id:
        _CLOSED_HL_COINS.add(tok.upper())
        _clear_pending_retry([tok])  # only called when trade_id exists
    # if trade_id=None → _clear_pending_retry NEVER called → LEAK
```

**Fix**: Always call `_clear_pending_retry` regardless of trade_id:

```python
for tok in pending_gone:
    trade_id = _get_reconciled_trade_id(tok)
    if trade_id:
        _CLOSED_HL_COINS.add(tok.upper())
    # Always clear — if no trade_id there's no DB record to close anyway
    _clear_pending_retry([tok])
```

## Pattern: Self-Introduced Bugs from Multi-Pass Fixes

When restructuring code blocks (especially collapsing nested if-else branches):
1. Every variable assigned in ANY branch of a conditional must be initialized BEFORE the first `if`
2. Every `_clear_pending_retry(X)` call must be checked for reachability from ALL code paths
3. After any restructuring patch, always run `python3 -m py_compile` immediately — catches NameError before runtime crash

## Final State

hl-sync-guardian.py: 4236 lines, Syntax OK. All 12 bugs fixed (10 from first pass + Bug A + Bug K).

## _CLOSED_HL_COINS Invariants (Final)

Every `_clear_pending_retry(X)` must be immediately preceded or followed by `_CLOSED_HL_COINS.add(X.upper())`.  
Every `_save_pending_retry(X)` must be matched by exactly one `_clear_pending_retry(X)` per token per lifecycle.
