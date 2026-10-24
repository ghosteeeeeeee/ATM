#!/usr/bin/env python3
"""
Manual Exit Manager — the single exit authority for CEO trades:
ai-trader-manual / ai-trader-pending / ai-trader-auto*.

CEO directive (2026-10-22, refined 2026-10-24): manual and pending trades
are managed by a DYNAMIC SL that TRAILS AND BOOKS PROFITS like the
profit-monster, with the TP kept only as a giant-candle backstop:
  1. PREDEFINED SL/TP honored until the dynamic system takes over.
  2. BREAKEVEN LOCK at +0.10% (PM_BREAKEVEN_LOCK_PCT): SL → entry.
  3. TIERED PEAK TRAIL from +0.40% (PM_TRAIL_ACTIVATE_PCT): the profit
     floor = PEAK profit − tier distance, where the distance loosens as
     profit grows — the exact profit-monster tier function
     (profit_monster._trail_distance_for_peak, PM_TRAIL_TIERS:
      peak <1.5% → 0.20% giveback, ≥1.5% → 0.50%, ≥3.0% → 0.80%,
      ≥5.0% → 1.20%). Tight while small, roomy while winning: the trail
     books profit on weakness but never amputates a runner.
     Floor is always ≥ +0.20% after activation — every exit BOOKS profit.

Peak tracking is PM-style state (HERMES_DATA/manual_trail_state.json):
{trade_id: {peak_frac, last_sl, ts}}. If the live SL differs from
last_sl (the CEO tightened it by hand), the trail only ever IMPROVES on
it (ratchet) — never relaxes a CEO stop. Tier-boundary relaxation
(peak 1.50→1.51 widens giveback 0.20→0.50) applies only to our own
stops, mirroring profit-monster semantics.

The RR engine is EXCLUDED for these signals. Guardian safety nets
(staleness, hard caps, max-hold) still apply — this module owns SL/TP
semantics, not safety.

Exit labels (via position_manager hit check):
    manual_sl_hit     — stop did its job (predefined / BE-lock)
    manual_tp_hit     — the predefined target hit (giant candle)
    manual_trail_hit  — the tiered trail booked the profit
"""
from hermes_constants import (PM_TRAIL_ACTIVATE_PCT,
                              PM_BREAKEVEN_LOCK_PCT)
from hermes_log import log
import math
import json
import os
import time

# The tier function IS the profit-monster's — single source, never diverges.
from profit_monster import _trail_distance_for_peak  # runtime percent tiers

_STATE_FILE = os.path.join(
    os.environ.get('HERMES_DATA_OVERRIDE',
                   os.path.join(os.path.dirname(os.path.dirname(
                       os.path.abspath(__file__))), 'data')),
    'manual_trail_state.json')
_STATE_MAX_AGE_S = 72 * 3600   # prune closed-trade entries after 3 days

# Any signal containing one of these tags is managed by this module.
MANAGED_TAGS = ('ai-trader-manual', 'ai-trader-pending', 'ai-trader-auto')


def is_managed_signal(signal) -> bool:
    """True when this signal's exits belong to the manual/pending system."""
    s = str(signal or '')
    return any(tag in s for tag in MANAGED_TAGS)


def _load_state() -> dict:
    try:
        with open(_STATE_FILE) as f:
            return json.load(f)
    except Exception:
        return {}


def _save_state(state: dict) -> None:
    try:
        # prune stale entries (closed trades) opportunistically
        now = time.time()
        state = {k: v for k, v in state.items()
                 if now - float(v.get('ts') or 0) < _STATE_MAX_AGE_S}
        tmp = _STATE_FILE + '.tmp'
        with open(tmp, 'w') as f:
            json.dump(state, f)
        os.replace(tmp, _STATE_FILE)
    except Exception as e:
        log(f"  [MANUAL-TRAIL] state save failed: {e}", "WARN")


def decide_sl(direction: str, current_price: float, entry_price: float,
              old_sl: float, peak_frac: float = None):
    """Pure phase decision: what should the SL become? Returns
    (new_sl, profit_frac, phase, peak_frac) or None to leave the SL put.

    Phases:
      — profit <  PM_BREAKEVEN_LOCK_PCT:      untouched
      — BE lock ≤ profit <  PM_TRAIL_ACTIVATE_PCT: SL := entry (breakeven)
      — profit ≥ PM_TRAIL_ACTIVATE_PCT:       SL := entry ∓ floor, where
        floor = peak profit − tier_dist(peak)  (profit-monster tiers)
    """
    if direction not in ('LONG', 'SHORT'):
        return None                        # validate — never fall through
    # NaN/Inf guards (bug_hunter 2026-10-23 F-2): NaN survives `<=0` compares
    # and PG numeric NaN equality would create a permanently dead stop.
    if not (math.isfinite(current_price) and math.isfinite(entry_price)
            and math.isfinite(old_sl)):
        return None
    if current_price <= 0 or entry_price <= 0 or old_sl <= 0:
        return None

    if direction == 'LONG':
        profit_frac = (current_price - entry_price) / entry_price
    else:
        profit_frac = (entry_price - current_price) / entry_price
    if profit_frac < PM_BREAKEVEN_LOCK_PCT:
        return None                        # SL untouched

    if profit_frac < PM_TRAIL_ACTIVATE_PCT:
        new_sl = round(entry_price, 8)             # breakeven lock
        better = (new_sl > old_sl) if direction == 'LONG' else (new_sl < old_sl)
        if not better:
            return None                    # ratchet: never worsen the stop
        return new_sl, profit_frac, 'BE-LOCK', peak_frac

    # ── Tiered peak trail (profit-monster semantics) ──
    peak_frac = max(peak_frac or 0.0, profit_frac)   # peak tracks the best
    dist_frac = _trail_distance_for_peak(peak_frac * 100) / 100.0
    floor_frac = max(0.0, peak_frac - dist_frac)
    # exit at the floor-profit PRICE: LONG locks entry*(1+floor),
    # SHORT locks entry*(1−floor) — verified against #16377's actual
    # manual_trail_hit fill (79,721 entry, floor 0.3506% → 79,442.0 vs
    # real exit 79,441.50).
    new_sl = (round(entry_price * (1 - floor_frac), 8) if direction == 'SHORT'
              else round(entry_price * (1 + floor_frac), 8))
    return (new_sl, profit_frac,
            f'TRAIL floor +{floor_frac*100:.2f}% (dist {dist_frac*100:.2f}%)',
            peak_frac)


def update_trail(pos: dict, direction: str, current_price: float,
                 entry_price: float) -> bool:
    """Dynamic SL for a managed trade: breakeven lock + tiered peak trail.

    Returns True if the SL moved. Writes are CAS-protected (only if the SL
    is unchanged since read and the trade is open). A CEO-tightened stop
    (SL differs from our last write) is only ever IMPROVED, never relaxed;
    tier-boundary relaxation applies to our own stops only.
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

    state = _load_state()
    st = state.get(str(trade_id)) or {}
    peak_frac = st.get('peak_frac')

    decided = decide_sl(direction, current_price, entry_price, old_sl,
                        peak_frac)
    if decided is None:
        _save_state(state)                # persist peak progress (prune too)
        return False                      # SL untouched
    new_sl, profit_frac, phase, new_peak = decided

    # CEO-tightened stop protection: if the live SL is NOT what we last wrote,
    # only improve on it (never relax a hand-set stop at a tier boundary).
    last_sl = st.get('last_sl')
    if last_sl is not None and abs(float(last_sl) - old_sl) > 1e-8:
        better = (new_sl > old_sl) if direction == 'LONG' else (new_sl < old_sl)
        if not better:
            st.update({'peak_frac': new_peak or peak_frac, 'ts': time.time()})
            state[str(trade_id)] = st
            _save_state(state)
            log(f"  [MANUAL-TRAIL] {pos.get('token')} {direction}: CEO stop "
                f"${old_sl:.6g} differs from last write ${float(last_sl):.6g} — "
                f"improve-only, no relax", "WARN")
            return False

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
        state[str(trade_id)] = {'peak_frac': new_peak or peak_frac,
                                'last_sl': new_sl, 'ts': time.time()}
        _save_state(state)
        log(f"  [MANUAL-TRAIL] {pos.get('token')} {direction}: "
            f"${old_sl:.6g} → ${new_sl:.6g} ({phase}, profit {profit_frac*100:.2f}%)")
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
