# accel-300 FINAL_VERIFY — What It Does and Doesn't Catch

## What FINAL_VERIFY Does (2026-05-14 addition)

Added after detecting a valid historical crossing bar, FINAL_VERIFY re-checks the **current bar's state**:

```python
if current_bar_idx >= 2:
    cur_gap = (closes[current_bar_idx] - ema300[current_bar_idx]) / ema300[current_bar_idx] * 100
    cur_direction = 'LONG' if cur_gap > 0 else 'SHORT'
    if cur_direction != direction:
        return None  # market flipped since signal bar — reject
    if direction == 'LONG' and cur_gap < MIN_GAP_PCT_LONG:
        return None
    if direction == 'SHORT' and cur_gap > -MIN_GAP_PCT_SHORT:
        return None
```

**Checks:**
- Current gap direction matches signal direction
- Gap magnitude meets minimum threshold for the direction

**Purpose:** Prevents stale signals from returning — signals found at bar n-100 should not fire when the market has since crossed above EMA.

---

## What FINAL_VERIFY Does NOT Check

**The stop_loss value in the DB.**

FINAL_VERIFY validates the signal's market premise (gap direction/magnitude at signal time and current time).
It does NOT validate the trade's protective SL level.

**The gap:** When a signal fires and executes, the SL is set either:
1. At entry time by `decider_run` passing `sl=0` (deferred to position_manager)
2. By `position_manager._collect_atr_updates()` which runs in the same pipeline cycle

The correction in `_collect_atr_updates()` only triggers when `current_sl <= 0`. If the initial SL
is set to a non-zero hardcoded value (even a wrong one), the correction is skipped.

**Example:** FIL SHORT opens at 1.0537 with SL=1.007 (wrong — should be 1.043).
FINAL_VERIFY passes (gap is correct, direction is correct).
Trade opens with broken SL. `_collect_atr_updates()` never corrects it because `current_sl = 1.007 > 0`.

---

## Related

- `hl-trading-debug/references/fil-short-initial-sl-bug-2026-05-15.md` — FIL SHORT SL=1.007 root cause
- `hl-trading-debug/references/mon-duplicate-short-entries-2026-05-15.md` — MON back-to-back SHORT entries
- `references/accel-300-debug-me-aster-2026-05-14.md` — original ME/ASTER debug session