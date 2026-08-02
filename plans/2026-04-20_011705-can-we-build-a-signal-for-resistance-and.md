# Plan: Fix Cascade Flip — Verify HL Close Before Opening Opposite

## Goal
Fix `cascade_flip()` in `position_manager.py` so it **waits for the old HL position to actually close** before placing the new opposite order. Prevents the scenario where:
1. Old close fails on HL (fills not confirmed)
2. New order placed anyway
3. Both old and new positions exist on HL simultaneously
4. Orphan sweep closes both = net zero but two wasted trades

## Current Behavior (BUG)

```python
# ── 1. Close the losing position ───
close_ok = close_paper_position(trade_id, ...)  # DB close only
if not close_ok:
    return False  # ← returns on DB failure, correct

# ── 2. Enter opposite immediately (BUG — no HL fill verification) ───
ok = place_order(token, opposite_dir, ...)  # Places new order RIGHT AWAY
# Old position may still be open on HL!
```

**TST timeline showing the bug:**
```
00:08:12  Guardian HARD_SL → close_position(LONG) called
00:08:20-34  Fill wait fails (15 retries, HL close not confirmed)
00:08:41  FATAL: close failed after 2 attempts — OLD LONG still on HL
00:09:06  cascade_flip fires → close_paper_position (DB closed)
                        → place_order(SHORT) immediately ← BUG: OLD LONG still on HL!
00:09:16  Orphan sweep: OLD LONG + NEW SHORT both on HL → both closed
Result: 2 opens, 2 closes, net ~zero. Old LONG took -0.72% loss.
```

## Fix: Insert HL Fill-Wait Verification

After `close_paper_position()` succeeds, **wait for the HL position to actually clear** before placing the new order. Use the same pattern as guardian's `check_hard_stop_loss()` which already does this correctly:

```python
# From guardian (hl-sync-guardian.py, line 1253):
filled = _wait_for_position_closed(token, timeout=15)
if not filled:
    log(f'  [FLIP] FATAL: {token} still on HL after 2 close attempts — not opening opposite', 'FAIL')
    return  # Do NOT open opposite position while original is still open
```

## Changes Required

### 1. `position_manager.py` — `cascade_flip()` function (line ~2914)

**Location:** Lines 2914–2944 (the section between `close_paper_position` and `place_order`)

**Change:** Add fill-wait verification after `close_paper_position` succeeds:

```python
    # ── 1. Close the losing position ───────────────────────────────────────────
    close_ok = close_paper_position(trade_id, f"cascade_flip_{live_pnl:+.2f}%")
    if not close_ok:
        print(f"  [CASCADE FLIP] ❌ Failed to close {token} #{trade_id}")
        return False

    # ── 1b. WAIT for HL position to actually close (FIX: orphan prevention) ──
    # close_paper_position only closes the DB — we must verify the HL position
    # is actually gone before placing the opposite order. Without this, both
    # old and new positions can exist on HL simultaneously, causing orphan
    # sweep to close both (net zero or loss).
    # Reuse guardian's _wait_for_position_closed() for fill confirmation.
    try:
        from hl_sync_guardian import _wait_for_position_closed
        print(f"  [CASCADE FLIP] Waiting for {token} {position_direction} to close on HL...")
        filled = _wait_for_position_closed(token, timeout=15)
        if not filled:
            print(f"  [CASCADE FLIP] ❌ {token} still on HL after fill-wait — aborting flip. "
                  f"Will retry next cycle.")
            # Don't return False — paper side is closed but HL orphan will be
            # caught by guardian orphan sweep. Return False so caller doesn't
            # count this as a successful flip.
            return False
        print(f"  [CASCADE FLIP] ✅ {token} {position_direction} confirmed closed on HL")
    except ImportError:
        # Fallback: if guardian module unavailable, proceed with old behavior
        # (risk of orphans but better than not flipping at all)
        print(f"  [CASCADE FLIP] ⚠️ Could not import guardian fill-wait — proceeding anyway")
    except Exception as fw_err:
        print(f"  [CASCADE FLIP] ⚠️ Fill-wait error ({fw_err}) — proceeding anyway")
```

**Also update the docstring (line 2878-2885):**
```python
    """
    Execute a cascade flip: close losing position, enter opposite direction.
    Uses HL reduce-only market order (close) then market order (open).
    Source string 'cascade-reverse-{src}' is used so post-flip trailing
    can detect flipped positions and use the tighter 0.5% window.

    Returns True ONLY if both close AND entry succeeded.
    Returns False if either fails — caller should not count as successful flip.
    """
```

**Also update the return at line 3090:**
```python
    return True  # ← Only reaches here if place_order succeeded (line 2963)
```

**And add failure return after entry failure (line ~3088):**
```python
        set_loss_cooldown(token, opposite_dir)
        return False  # ← NEW: entry failed, flip did not complete

    return True       # ← Only on success
```

### 2. Also fix the cascade_flip caller's handling (line 2556-2563)

When `cascade_flip` returns `False`, the caller currently does:
```python
if cascade_flipped:
    closed_count += 1
    continue
```

If it returns `False`, it falls through and might hit other exit logic (like cut_loser). We should make sure a failed flip doesn't then trigger another exit on the same position in the same cycle.

**No code change needed here** — `cascade_flip` returning `False` means the position is still open (paper not closed OR HL close failed). The position stays in the loop for other checks. This is correct behavior.

## Files to Change

| File | Change |
|-------|--------|
| `position_manager.py` | `cascade_flip()`: add HL fill-wait between close and entry; update docstring; fix return to `False` on entry failure |

## Verification

1. **Import test:** `python3 -c "from position_manager import cascade_flip; print('OK')"` — should load clean
2. **Simulate TST scenario:** Force a cascade flip on a test token and verify `_wait_for_position_closed` is called before `place_order`
3. **Check return behavior:** Entry failure should return `False`, not `True`

## Risks

1. **Import cycle:** `hl_sync_guardian` might import from `position_manager` — need to verify no circular import. If circular, copy the `_wait_for_position_closed` function logic directly into `cascade_flip`.
2. **Timeout too short:** 15s might not be enough for slow-fill tokens. But we already know 15s was used in guardian and TST still failed — the issue is the fill never came even after 15s. In that case, returning `False` is correct.
3. **Old cascade flips that returned `True` will now return `False`** — this is correct behavior but changes the `closed_count` semantics.

## Open Questions

1. **Should we retry the close instead of aborting?** The guardian already retried twice before giving up. `close_paper_position` uses `mirror_close` which has 3 fill polls built-in. If `mirror_close` returned successfully, the fill should be there... unless the issue is the fill happened but `mirror_get_exit_fill` returned nothing (the WARN at line 1013). If the close DID succeed but the fill polling failed, we're aborting a valid flip. **Better approach: check HL position state directly** — if `get_positions()` shows the token is gone, proceed; if still there, abort.
