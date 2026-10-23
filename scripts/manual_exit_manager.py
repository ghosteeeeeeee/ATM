#!/usr/bin/env python3
"""
Manual Exit Manager — the single exit authority for CEO trades:
ai-trader-manual / ai-trader-pending / ai-trader-auto*.

CEO directive (2026-10-22): manual and pending trades must be managed by
exactly two things —
  1. PREDEFINED SL/TP, honored as set (CEO sets them at open; nothing
     structurally rewrites them), and
  2. DYNAMIC SL management in profit (all ratchet-only, CAS-protected,
     never touching the TP — CEO-approved 2026-10-23):
       a. BREAKEVEN LOCK at +0.10% (PM_BREAKEVEN_LOCK_PCT): SL → entry.
          Turns chop-wiggles into scratches instead of max-hold bleeds
          (#16353 -1.53% / #16358 -1.03% would have been 0.00%).
       b. CLOSE TRAIL from +0.40% (PM_TRAIL_ACTIVATE_PCT): trail 0.20%
          (PM_TRAIL_DISTANCE_PCT) behind price. Untuned — the runner
          (+4.65% #16351) pays for the chop; tight trails amputate it.

The RR engine is EXCLUDED for these signals (it was moving SLs
structurally — #16306 81990→82486, #16317 83150→82965 — and mislabeling
exits rr_engine_*). Guardian safety nets (staleness, hard caps,
max-hold) still apply — this module owns SL/TP semantics, not safety.

Exit labels produced for these trades (via position_manager hit check):
    manual_sl_hit     — the stop did its job (predefined OR breakeven lock)
    manual_tp_hit     — the predefined target hit
    manual_trail_hit  — the close trail took profit
"""
from hermes_constants import (PM_TRAIL_ACTIVATE_PCT, PM_TRAIL_DISTANCE_PCT,
                              PM_BREAKEVEN_LOCK_PCT)
from hermes_log import log

# Any signal containing one of these tags is managed by this module.
MANAGED_TAGS = ('ai-trader-manual', 'ai-trader-pending', 'ai-trader-auto')


def is_managed_signal(signal) -> bool:
    """True when this signal's exits belong to the manual/pending system."""
    s = str(signal or '')
    return any(tag in s for tag in MANAGED_TAGS)


def decide_sl(direction: str, current_price: float, entry_price: float,
              old_sl: float):
    """Pure phase decision: what should the SL become? Returns
    (new_sl, profit_pct, phase) or None when the SL must stay put.

    Phases (ratchet-only in every branch):
      — profit <  PM_BREAKEVEN_LOCK_PCT:          untouched
      — BE lock ≤ profit <  PM_TRAIL_ACTIVATE_PCT: SL := entry (breakeven)
      — profit ≥ PM_TRAIL_ACTIVATE_PCT:            SL := price ∓ trail distance
    """
    if direction not in ('LONG', 'SHORT'):
        return None                        # validate — never fall through
    if current_price <= 0 or entry_price <= 0 or old_sl <= 0:
        return None

    if direction == 'LONG':
        profit_pct = (current_price - entry_price) / entry_price
        if profit_pct < PM_BREAKEVEN_LOCK_PCT:
            return None                    # SL untouched
        if profit_pct < PM_TRAIL_ACTIVATE_PCT:
            new_sl = round(entry_price, 8)         # breakeven lock
            if new_sl <= old_sl:
                return None                # ratchet: LONG SL only rises
            return new_sl, profit_pct, 'BE-LOCK'
        new_sl = round(current_price * (1 - PM_TRAIL_DISTANCE_PCT), 8)
        if new_sl <= old_sl:
            return None                    # ratchet: LONG SL only rises
        return new_sl, profit_pct, f'TRAIL {PM_TRAIL_DISTANCE_PCT*100:.2f}%'
    else:  # SHORT
        profit_pct = (entry_price - current_price) / entry_price
        if profit_pct < PM_BREAKEVEN_LOCK_PCT:
            return None
        if profit_pct < PM_TRAIL_ACTIVATE_PCT:
            new_sl = round(entry_price, 8)         # breakeven lock
            if new_sl >= old_sl:
                return None                # ratchet: SHORT SL only falls
            return new_sl, profit_pct, 'BE-LOCK'
        new_sl = round(current_price * (1 + PM_TRAIL_DISTANCE_PCT), 8)
        if new_sl >= old_sl:
            return None                    # ratchet: SHORT SL only falls
        return new_sl, profit_pct, f'TRAIL {PM_TRAIL_DISTANCE_PCT*100:.2f}%'


def update_trail(pos: dict, direction: str, current_price: float,
                 entry_price: float) -> bool:
    """Dynamic SL for a managed trade (breakeven lock + close trail).

    Returns True if the SL moved. Writes are CAS-protected: only if the
    SL hasn't changed since read and the trade is still open — the CEO's
    own concurrent edits always win.
    """
    try:
        current_price = float(current_price or 0)
        entry_price = float(entry_price or 0)
        old_sl = float(pos.get('stop_loss') or 0)
    except (TypeError, ValueError):
        return False
    trade_id = pos.get('id')
    if not trade_id:
        return False

    decided = decide_sl(direction, current_price, entry_price, old_sl)
    if decided is None:
        return False                       # nothing to do — SL untouched
    new_sl, profit_pct, phase = decided

    # CAS write — only if the SL hasn't changed since read, trade still open
    db_conn = None
    db_cur = None
    try:
        import psycopg2
        from _secrets import BRAIN_PASSWORD, BRAIN_HOST
        db_conn = psycopg2.connect(host=BRAIN_HOST, dbname='brain',
                                   user='postgres', password=BRAIN_PASSWORD,
                                   connect_timeout=5)
        db_cur = db_conn.cursor()
        db_cur.execute(
            "UPDATE trades SET stop_loss = %s WHERE id = %s AND status = 'open' AND stop_loss = %s",
            (new_sl, trade_id, old_sl))
        written = db_cur.rowcount > 0
        db_conn.commit()
        if not written:
            log(f"  [MANUAL-TRAIL] {pos.get('token')} {direction}: CAS skip — "
                f"SL changed since read (CEO edit?) or trade closed", "WARN")
            return False
        pos['stop_loss'] = new_sl           # keep in-memory copy consistent
        log(f"  [MANUAL-TRAIL] {pos.get('token')} {direction}: "
            f"${old_sl:.6g} → ${new_sl:.6g} ({phase}, profit {profit_pct*100:.2f}%)")
        return True
    except Exception as e:
        log(f"  [MANUAL-TRAIL] {pos.get('token')} {direction}: DB write failed: {e}",
            "WARN")
        return False
    finally:
        try:
            if db_cur:
                db_cur.close()
        except Exception:
            pass
        try:
            if db_conn:
                db_conn.close()
        except Exception:
            pass
