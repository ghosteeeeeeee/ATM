#!/usr/bin/env python3
"""
Manual Exit Manager — the single exit authority for CEO trades:
ai-trader-manual / ai-trader-pending / ai-trader-auto*.

CEO directive (2026-10-22): manual and pending trades must be managed by
exactly two things —
  1. PREDEFINED SL/TP, honored as set (CEO sets them at open; nothing
     structurally rewrites them), and
  2. CLOSE TRAILING once in profit (activate 0.40%, trail 0.20% behind
     price, ratchet-only — the stop never moves backward).

The RR engine is EXCLUDED for these signals (it was moving SLs
structurally — #16306 81990→82486, #16317 83150→82965 — and mislabeling
exits rr_engine_*). Guardian safety nets (staleness, hard caps,
max-hold) still apply — this module owns SL/TP semantics, not safety.

Exit labels produced for these trades (via position_manager hit check):
    manual_sl_hit     — the predefined stop did its job
    manual_tp_hit     — the predefined target hit
    manual_trail_hit  — the close trail took profit
"""
from hermes_constants import PM_TRAIL_ACTIVATE_PCT, PM_TRAIL_DISTANCE_PCT
from hermes_log import log

# Any signal containing one of these tags is managed by this module.
MANAGED_TAGS = ('ai-trader-manual', 'ai-trader-pending', 'ai-trader-auto')


def is_managed_signal(signal) -> bool:
    """True when this signal's exits belong to the manual/pending system."""
    s = str(signal or '')
    return any(tag in s for tag in MANAGED_TAGS)


def update_trail(pos: dict, direction: str, current_price: float,
                 entry_price: float) -> bool:
    """Close-trail ratchet for a managed trade. Returns True if the SL moved.

    Phases:
      — Before activation (price profit < PM_TRAIL_ACTIVATE_PCT): SL stays
        EXACTLY where the CEO set it. No writes, no touches.
      — After activation: trail = price ∓ PM_TRAIL_DISTANCE_PCT, written only
        if it IMPROVES on the current stop (ratchet — LONG SL only rises,
        SHORT SL only falls). Never touches the TP.
    """
    try:
        current_price = float(current_price or 0)
        entry_price = float(entry_price or 0)
        old_sl = float(pos.get('stop_loss') or 0)
    except (TypeError, ValueError):
        return False
    if current_price <= 0 or entry_price <= 0 or old_sl <= 0:
        return False
    trade_id = pos.get('id')
    if not trade_id:
        return False

    if direction == 'LONG':
        profit_pct = (current_price - entry_price) / entry_price
        if profit_pct < PM_TRAIL_ACTIVATE_PCT:
            return False                    # not in profit enough — SL untouched
        new_sl = round(current_price * (1 - PM_TRAIL_DISTANCE_PCT), 8)
        if new_sl <= old_sl:
            return False                    # ratchet: never move SL down
    else:  # SHORT
        profit_pct = (entry_price - current_price) / entry_price
        if profit_pct < PM_TRAIL_ACTIVATE_PCT:
            return False
        new_sl = round(current_price * (1 + PM_TRAIL_DISTANCE_PCT), 8)
        if new_sl >= old_sl:
            return False                    # ratchet: never move SL up

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
            f"${old_sl:.6g} → ${new_sl:.6g} (profit {profit_pct*100:.2f}%, "
            f"activate {PM_TRAIL_ACTIVATE_PCT*100:.2f}% / trail "
            f"{PM_TRAIL_DISTANCE_PCT*100:.2f}%)")
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
