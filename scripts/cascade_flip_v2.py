#!/usr/bin/env python3
"""
Cascade Flip v2 — Unified detection + execution for momentum-based position reversals.

Replaces the scattered cascade flip logic in position_manager.py, cascade_flip.py,
and counter_flip.py with a single scoring engine.

Architecture:
  open position + speed tracker + MACD data + cascade state
  → compute_flip_score() → composite 0-100 score
  → score >= dynamic threshold → cascade_flip_v2() → close + reverse

Key improvements over v1:
  1. Directional momentum gate (not just "speed increasing")
  2. Confidence-weighted adaptive threshold (stronger signal = flip earlier)
  3. Post-flip protection (min hold, tighter SL, progressive cooldown)
  4. Adaptive flip budget (win-rate aware, not hardcoded)
  5. Single module (no more 3-file duplication)

Kill switch: CASCADE_FLIP_V2_ENABLED (hermes_constants.py)
             CASCADE_FLIP_ENABLED (hermes_constants.py) — both must be True.

DB usage:
  - PostgreSQL (brain DB via psycopg2): trades table queries (close, SL/TP lookup)
  - SQLite (signals_hermes_runtime.db): cascade_sequences table, signal marking
  - JSON files: flip_counts, post_flip_state, loss_cooldowns
"""

import os
import sys
import json
import time
import sqlite3
from datetime import datetime, timezone
from typing import Optional, Dict, Tuple, List

# ── Path setup ─────────────────────────────────────────────────────────────────
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if _SCRIPT_DIR not in sys.path:
    sys.path.insert(0, _SCRIPT_DIR)

from hermes_constants import (
    RUNTIME_DB, FLIP_COUNTS_FILE, LOSS_COOLDOWN_FILE,
    LOSS_COOLDOWN_BASE, LOSS_COOLDOWN_MAX, DEFAULT_TRADE_SIZE_USDT,
    CASCADE_FLIP_ENABLED, CASCADE_FLIP_V2_ENABLED,
    CFV2_MTF_MAX_PTS, CFV2_CASCADE_MAX_PTS, CFV2_MACD_MAX_PTS, CFV2_MOMENTUM_MAX_PTS,
    CFV2_VEL_STRONG, CFV2_VEL_MODERATE,
    CFV2_POST_FLIP_MIN_CYCLES, CFV2_POST_FLIP_COOLDOWN_M,
    CFV2_BUDGET_WIN_RATE_HIGH, CFV2_BUDGET_WIN_RATE_LOW,
    CFV2_BUDGET_DEFAULT, CFV2_BUDGET_MIN_TRADES,
)
from _secrets import BRAIN_DB_DICT
from hermes_file_lock import FileLock

# PostgreSQL connection config for trades table
DB_CONFIG = BRAIN_DB_DICT

# HL minimum order size
MIN_NOTIONAL = 11.0  # $10 + $1 buffer


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 1: Scoring Engine
# ═══════════════════════════════════════════════════════════════════════════════

def compute_flip_score(
    token: str,
    position_dir: str,
    live_pnl: float,
    speed_tracker=None,
) -> Optional[Dict]:
    """
    Score the reversal strength for an open position.

    Returns None (no flip warranted) or a dict:
    {
        'flip_score': float,          # 0-100 composite score
        'threshold': float,           # dynamic threshold this token needs
        'trigger_level': str,         # 'immediate' | 'fast' | 'standard' | 'none'
        'components': {
            'mtf_alignment': float,   # 0-30 points
            'cascade_active': float,  # 0-25 points
            'macd_exit': float,       # 0-20 points
            'momentum': float,        # 0-25 points
        },
        'opposite_dir': str,
        'source': str,
        'reasons': list[str],
        'price': float,               # current price for execution
    }
    """
    opposite_dir = 'SHORT' if position_dir == 'LONG' else 'LONG'

    # ── Gate 1: Not armed yet ──────────────────────────────────────────────
    # Only evaluate if position is losing (near-breakeven flips only on ultra-high scores)
    if live_pnl > 0.01:
        return None  # In profit — never flip

    # ── Gate 2: Minimum velocity — don't flip in dead markets ─────────────
    # If price isn't moving, there's no reversal to flip into.
    # This prevents flipping on noise when speed_pctl is very low.
    if speed_tracker is not None:
        try:
            spd = speed_tracker.get_token_speed(token)
            vel_5m = abs(spd.get('price_velocity_5m', 0) or 0)
            if vel_5m < 0.15:
                return None  # Market too quiet — no directional momentum
        except Exception:
            pass

    components = {}
    reasons = []

    # ── Component 1: MTF Alignment (0-30 points) ───────────────────────────
    mtf_pts, mtf_reasons = _score_mtf_alignment(token, position_dir)
    components['mtf_alignment'] = mtf_pts
    reasons.extend(mtf_reasons)

    # ── Component 2: Cascade Active (0-25 points) ──────────────────────────
    cascade_pts, cascade_reasons = _score_cascade_active(token, position_dir)
    components['cascade_active'] = cascade_pts
    reasons.extend(cascade_reasons)

    # ── Component 3: MACD Exit Signal (0-20 points) ────────────────────────
    macd_pts, macd_reasons = _score_macd_exit(token, position_dir)
    components['macd_exit'] = macd_pts
    reasons.extend(macd_reasons)

    # ── Component 4: Momentum Confirmation (0-25 points) ───────────────────
    momentum_pts, momentum_reasons = _score_momentum(
        token, position_dir, speed_tracker
    )
    components['momentum'] = momentum_pts
    reasons.extend(momentum_reasons)

    # ── Composite score ────────────────────────────────────────────────────
    flip_score = mtf_pts + cascade_pts + macd_pts + momentum_pts

    # ── Dynamic threshold ──────────────────────────────────────────────────
    threshold = _get_score_threshold(live_pnl)

    # ── Determine trigger level ────────────────────────────────────────────
    if flip_score >= 90:
        trigger_level = 'immediate'
    elif flip_score >= 75:
        trigger_level = 'fast'
    elif flip_score >= threshold:
        trigger_level = 'standard'
    else:
        trigger_level = 'none'

    # ── Source string ──────────────────────────────────────────────────────
    source_parts = []
    if mtf_pts >= 15:
        source_parts.append('mtf_alignment')
    if cascade_pts >= 20:
        source_parts.append('cascade_active')
    if macd_pts >= 15:
        source_parts.append('macd_exit')
    if momentum_pts >= 15:
        source_parts.append('momentum')
    source = '+'.join(source_parts) if source_parts else 'weak_reversal'

    return {
        'flip_score': flip_score,
        'threshold': threshold,
        'trigger_level': trigger_level,
        'components': components,
        'opposite_dir': opposite_dir,
        'source': source,
        'reasons': reasons,
        'price': 0,  # price not available from scoring — caller provides
    }


def _score_mtf_alignment(token: str, position_dir: str) -> Tuple[float, List[str]]:
    """Score MTF MACD alignment against position direction. Returns (points 0-30, reasons)."""
    try:
        from macd_rules import compute_mtf_macd_alignment
        mtf = compute_mtf_macd_alignment(token)
    except Exception:
        return 0, []

    if mtf is None:
        return 0, []

    aligned_count = 0
    tf_details = []

    for tf_name in ['15m', '1h', '4h']:
        state = mtf.get('tf_states', {}).get(tf_name)
        if state is None:
            continue
        is_aligned = False
        if position_dir == 'LONG':
            is_aligned = not state.macd_above_signal and not state.histogram_positive
        else:
            is_aligned = state.macd_above_signal and state.histogram_positive
        if is_aligned:
            aligned_count += 1
            tf_details.append(tf_name)

    if aligned_count >= 3:
        return CFV2_MTF_MAX_PTS, [f'mtf: all 3 TFs ({", ".join(tf_details)}) bearish against {position_dir}']
    elif aligned_count == 2:
        return CFV2_MTF_MAX_PTS * 0.5, [f'mtf: {aligned_count}/3 TFs aligned against position']
    elif aligned_count == 1:
        return CFV2_MTF_MAX_PTS * (1/6), [f'mtf: lead TF ({tf_details[0]}) flipped against position']
    return 0, []


def _score_cascade_active(token: str, position_dir: str) -> Tuple[float, List[str]]:
    """Score cascade entry signal against position direction. Returns (points 0-25, reasons)."""
    try:
        from macd_rules import cascade_entry_signal
        cascade = cascade_entry_signal(token)
    except Exception:
        return 0, []

    if not cascade.get('cascade_active'):
        return 0, []

    cascade_dir = cascade.get('cascade_direction')
    if cascade_dir is None or cascade_dir == position_dir:
        return 0, []

    lead_tf = cascade.get('lead_tf', '?')
    confirmations = cascade.get('confirmation_count', 0)
    score = cascade.get('cascade_score', 0)

    return CFV2_CASCADE_MAX_PTS, [
        f'cascade: active {cascade_dir} (lead={lead_tf}, confirms={confirmations}, score={score:.2f})'
    ]


def _score_macd_exit(token: str, position_dir: str) -> Tuple[float, List[str]]:
    """Score MACD rules engine exit signal. Returns (points 0-20, reasons)."""
    try:
        from macd_rules import get_macd_exit_signal
        macd = get_macd_exit_signal(token, position_dir)
    except Exception:
        return 0, []

    if macd is None or macd.get('state') is None:
        return 0, []

    if macd.get('should_flip'):
        reasons_list = macd.get('reasons', [])
        flip_reasons = [r for r in reasons_list if r.startswith('FLIP:')]
        return CFV2_MACD_MAX_PTS, [f'macd: flip signal — {"; ".join(flip_reasons[:2])}']

    if macd.get('should_exit'):
        reasons_list = macd.get('reasons', [])
        return CFV2_MACD_MAX_PTS * 0.5, [f'macd: exit signal — {"; ".join(reasons_list[:2])}']

    return 0, []


def _score_momentum(
    token: str, position_dir: str, speed_tracker=None
) -> Tuple[float, List[str]]:
    """
    Score directional momentum confirmation. Returns (points 0-25, reasons).

    KEY V2 IMPROVEMENT: Requires velocity in the OPPOSITE direction of our position.
    """
    if speed_tracker is None:
        return CFV2_MOMENTUM_MAX_PTS * 0.4, ['momentum: no speed tracker — fail-open']

    try:
        spd = speed_tracker.get_token_speed(token)
    except Exception:
        return CFV2_MOMENTUM_MAX_PTS * 0.4, ['momentum: speed lookup error — fail-open']

    if not spd:
        return CFV2_MOMENTUM_MAX_PTS * 0.4, ['momentum: no speed data — fail-open']

    vel_5m = spd.get('price_velocity_5m', 0) or 0
    accel = spd.get('price_acceleration', 0) or 0
    vel_magnitude = abs(vel_5m)

    # Directional check: momentum confirms reversal against our position
    if position_dir == 'LONG':
        confirms_reversal = vel_5m < 0 and accel < 0
    else:
        confirms_reversal = vel_5m > 0 and accel > 0

    reasons = []

    if vel_magnitude > CFV2_VEL_STRONG and confirms_reversal:
        pts = CFV2_MOMENTUM_MAX_PTS
        reasons.append(f'momentum: STRONG reversal (vel={vel_5m:+.3f}%/candle, accel={accel:+.5f})')
    elif vel_magnitude > CFV2_VEL_MODERATE and confirms_reversal:
        pts = CFV2_MOMENTUM_MAX_PTS * 0.6
        reasons.append(f'momentum: moderate reversal (vel={vel_5m:+.3f}%, accel={accel:+.5f})')
    elif vel_magnitude > CFV2_VEL_MODERATE:
        pts = CFV2_MOMENTUM_MAX_PTS * 0.2
        reasons.append(f'momentum: some speed but NOT confirming reversal (vel={vel_5m:+.3f}%)')
    else:
        pts = 0
        reasons.append(f'momentum: weak (vel={vel_5m:+.3f}%, accel={accel:+.5f})')

    # Bonus: overextended adds extra conviction
    if spd.get('is_overextended'):
        pts = min(CFV2_MOMENTUM_MAX_PTS, pts + 3)
        reasons.append('momentum: overextended bonus +3')

    return pts, reasons


def _get_score_threshold(live_pnl: float) -> float:
    """Dynamic score threshold based on position loss. Deeper loss = lower threshold."""
    if live_pnl > -0.01:
        return 90   # Near breakeven — only ultra-strong reversal
    elif live_pnl > -0.03:
        return 75
    elif live_pnl > -0.06:
        return 65   # Raised from 60 — don't flip easily at small losses
    elif live_pnl > -0.10:
        return 55   # Raised from 50
    elif live_pnl > -0.20:
        return 50   # Raised from 40 — need real conviction at this loss
    else:
        return 45   # Deep underwater — still need moderate signal


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 2: Post-Flip Protection (delegates to cascade_flip_helpers)
# ═══════════════════════════════════════════════════════════════════════════════

def is_in_post_flip_window(token: str) -> bool:
    """Check if token is in the post-flip protection window. Delegates to helpers."""
    from cascade_flip_helpers import is_in_post_flip_window as _helper_check
    return _helper_check(token)


def record_post_flip(token: str):
    """Record that a token just underwent a cascade flip. Delegates to helpers."""
    from cascade_flip_helpers import record_post_flip as _helper_record
    _helper_record(token)


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 3: Adaptive Flip Budget
# ═══════════════════════════════════════════════════════════════════════════════

def get_flip_budget(token: str) -> int:
    """
    Max flips allowed based on historical flip win rate.
    Queries PostgreSQL trades table for cascade_flip close outcomes.
    """
    try:
        import psycopg2
        conn = psycopg2.connect(**DB_CONFIG)
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT COUNT(*),
                       SUM(CASE WHEN pnl_usdt > 0 THEN 1 ELSE 0 END)
                FROM trades
                WHERE status = 'closed'
                  AND token = %s
                  AND close_reason LIKE 'cascade_flip_%%'
            """, (token.upper(),))
            row = cur.fetchone()
            cur.close()

            total = row[0] or 0
            wins = row[1] or 0

            if total < CFV2_BUDGET_MIN_TRADES:
                return CFV2_BUDGET_DEFAULT

            win_rate = wins / total
            if win_rate > CFV2_BUDGET_WIN_RATE_HIGH:
                return 5
            elif win_rate > CFV2_BUDGET_WIN_RATE_LOW:
                return 3
            else:
                return 1
        finally:
            conn.close()
    except Exception:
        return CFV2_BUDGET_DEFAULT


def get_current_flip_count(token: str) -> int:
    """Get current flip count for a token from flip_counts.json."""
    try:
        if os.path.exists(FLIP_COUNTS_FILE):
            with open(FLIP_COUNTS_FILE) as f:
                counts = json.load(f)
            return counts.get(token.upper(), {}).get('flips', 0)
    except Exception:
        pass
    return 0


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 4: Flip Outcome Tracking
# ═══════════════════════════════════════════════════════════════════════════════

def record_flip_outcome(token: str, pnl_usdt: float, pnl_pct: float):
    """
    Record the outcome of a cascade-flip-opened position.
    Called when a post-flip position closes.
    """
    try:
        counts = {}
        if os.path.exists(FLIP_COUNTS_FILE):
            with open(FLIP_COUNTS_FILE) as f:
                counts = json.load(f)

        entry = counts.get(token.upper(), {})
        wins = entry.get('wins', 0)
        losses = entry.get('losses', 0)

        if pnl_usdt > 0:
            wins += 1
        else:
            losses += 1

        total = wins + losses
        win_rate = wins / total if total > 0 else 0
        total_pnl = entry.get('total_pnl_usdt', 0) + pnl_usdt

        counts[token.upper()] = {
            **entry,
            'wins': wins,
            'losses': losses,
            'total_pnl_usdt': round(total_pnl, 4),
            'win_rate': round(win_rate, 3),
            'last_outcome': 'win' if pnl_usdt > 0 else 'loss',
            'last_pnl_pct': round(pnl_pct, 4),
            'last_outcome_time': datetime.now(timezone.utc).isoformat(),
        }

        with FileLock('flip_counts'):
            os.makedirs(os.path.dirname(FLIP_COUNTS_FILE), exist_ok=True)
            with open(FLIP_COUNTS_FILE, 'w') as f:
                json.dump(counts, f, indent=2)

        print(f"  [CFV2] {token} flip outcome: {'WIN' if pnl_usdt > 0 else 'LOSS'} "
              f"({pnl_pct:+.2f}%, ${pnl_usdt:+.4f}) — WR now {win_rate:.0%} ({wins}W/{losses}L)")

    except Exception as e:
        print(f"  [CFV2] ⚠️ Could not record flip outcome for {token}: {e}")


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 5: Execution Engine
# ═══════════════════════════════════════════════════════════════════════════════

def cascade_flip_v2(
    token: str,
    position_dir: str,
    trade_id: int,
    live_pnl: float,
    flip_info: Dict,
    entry_price: float,
) -> bool:
    """
    Execute a cascade flip v2: close losing position, enter opposite direction.

    Uses position_manager.close_paper_position() for the close (full feature set:
    HL mirror, audit logging, hype_realized backfill, signal_outcome tracking).

    Returns True ONLY if both close AND entry succeeded.
    """
    opposite_dir = flip_info['opposite_dir']
    source = flip_info.get('source', 'v2')
    score = flip_info.get('flip_score', 0)
    threshold = flip_info.get('threshold', 60)
    reasons = flip_info.get('reasons', [])

    print(f"  [CFV2] {token} {position_dir}→{opposite_dir} "
          f"(loss={live_pnl:+.2f}%, score={score:.0f}/{threshold:.0f}, src={source})")
    for r in reasons[:4]:
        print(f"    └─ {r}")

    # ── 0. Look up old trade data ───────────────────────────────────────────
    old_amount = DEFAULT_TRADE_SIZE_USDT
    old_lev = 10
    try:
        import psycopg2
        conn_old = psycopg2.connect(**DB_CONFIG)
        try:
            cur_old = conn_old.cursor()
            cur_old.execute(
                "SELECT amount_usdt, leverage FROM trades WHERE id = %s",
                (trade_id,)
            )
            row_old = cur_old.fetchone()
            cur_old.close()
            if row_old:
                old_amount = float(row_old[0]) if row_old[0] else DEFAULT_TRADE_SIZE_USDT
                old_lev = float(row_old[1] or 10) if row_old[1] else 10
        finally:
            conn_old.close()
    except Exception:
        pass

    # ── 1. Close the losing position ────────────────────────────────────────
    # Use position_manager.close_paper_position for full feature set:
    # HL mirror, audit logging, hype_realized backfill, signal_outcome, cooldown
    try:
        import importlib
        pm = importlib.import_module('position_manager')
        close_fn = getattr(pm, 'close_paper_position', None)
        if close_fn is None:
            raise AttributeError("close_paper_position not found in position_manager")
        close_fn(trade_id, f"cascade_flip_{live_pnl:+.2f}%")
        close_ok = True
    except Exception as e:
        print(f"  [CFV2] ❌ close_paper_position failed for {token} #{trade_id}: {e}")
        return False

    # ── 1b. Wait for HL fill confirmation ─────────────────────────────────
    print(f"  [CFV2] Waiting for {token} {position_dir} to close on HL...")
    filled = _wait_for_hl_close(token, timeout=15)
    if not filled:
        print(f"  [CFV2] ❌ {token} still on HL after fill-wait — aborting flip. "
              f"Paper closed, HL orphan handled by guardian.")
        return False
    print(f"  [CFV2] ✅ {token} {position_dir} confirmed closed on HL")

    # ── 1c. Record cascade close ────────────────────────────────────────────
    close_pnl_usdt = (live_pnl / 100) * old_amount * old_lev
    _record_cascade_sequence(
        parent_trade_id=trade_id, token=token,
        entry_px=entry_price,
        current_px=flip_info.get('price') or entry_price,
        pnl_usdt=close_pnl_usdt, pnl_pct=live_pnl,
        direction=position_dir,
        child_trade_id=None,
    )

    # ── 2. Enter opposite direction ─────────────────────────────────────────
    current_price = flip_info.get('price', 0)
    if not current_price or current_price <= 0:
        try:
            from hyperliquid_exchange import get_prices
            price_map = get_prices([token])
            current_price = price_map.get(token, 0) or 0
        except Exception:
            current_price = 0
    if not current_price or current_price <= 0:
        print(f"  [CFV2] ❌ Could not get price for {token} — flip incomplete")
        return False

    sz_coins = MIN_NOTIONAL / current_price if current_price > 0 else 0
    if sz_coins <= 0:
        sz_coins = old_amount / current_price if current_price > 0 else old_amount

    from hyperliquid_exchange import place_order, _round_position_sz
    sz_coins = _round_position_sz(sz_coins, token)

    ok = place_order(
        name=token,
        side='BUY' if opposite_dir == 'LONG' else 'SELL',
        sz=sz_coins,
        price=current_price,
        order_type='Market',
    )

    if ok and ok.get('success'):
        print(f"  [CFV2] ✅ {token} {opposite_dir} entered @ ${current_price:.6f}")

        # ── 2a. Record cascade entry ─────────────────────────────────────────
        try:
            import psycopg2
            conn_seq = psycopg2.connect(**DB_CONFIG)
            try:
                cur_seq = conn_seq.cursor()
                cur_seq.execute(
                    "SELECT id FROM trades WHERE token = %s AND status = 'open' ORDER BY id DESC LIMIT 1",
                    (token.upper(),)
                )
                row_seq = cur_seq.fetchone()
                cur_seq.close()
                new_trade_id = row_seq[0] if row_seq else None
                if new_trade_id:
                    _record_cascade_sequence(
                        parent_trade_id=trade_id, token=token,
                        entry_px=current_price,
                        current_px=0, pnl_usdt=0, pnl_pct=0,
                        direction=opposite_dir,
                        child_trade_id=new_trade_id,
                    )
            finally:
                conn_seq.close()
        except Exception as e:
            print(f"  [CFV2] ⚠️ Could not record cascade entry: {e}")

        # ── 2b. Fetch SL/TP values ───────────────────────────────────────────
        sl_val = tp_val = leverage_db = 0.0
        try:
            import psycopg2
            conn_sl = psycopg2.connect(**DB_CONFIG)
            try:
                cur_sl = conn_sl.cursor()
                cur_sl.execute("""
                    SELECT stop_loss, target, leverage
                    FROM trades
                    WHERE token = %s AND status = 'open'
                    ORDER BY id DESC LIMIT 1
                """, (token.upper(),))
                sl_row = cur_sl.fetchone()
                if sl_row:
                    sl_val = float(sl_row[0] or 0)
                    tp_val = float(sl_row[1] or 0)
                    leverage_db = int(sl_row[2] or 10)
                cur_sl.close()
            finally:
                conn_sl.close()
        except Exception:
            pass

        # ── 2c. Sync DB entry for post-flip position ──────────────────────────
        try:
            from cascade_flip_helpers import insert_post_flip_trade
            new_tid = insert_post_flip_trade(
                token=token,
                direction=opposite_dir,
                entry_price=current_price,
                hl_entry_price=current_price,
                amount_usdt=MIN_NOTIONAL,  # actual USDT ordered (not coin count)
                leverage=leverage_db,
                stop_loss=sl_val,
                target=tp_val,
                signal=f'cascade-reverse-v2-{source}',
                signal_source=f'cascade-reverse-v2-{source}',
            )
            if new_tid:
                print(f"  [CFV2] ✅ Post-flip DB entry created: trade_id={new_tid} atr_managed=TRUE")
            else:
                print(f"  [CFV2] ⚠️ Post-flip DB entry not inserted (guardian likely synced it)")
        except Exception as e:
            print(f"  [CFV2] ⚠️ Post-flip DB INSERT skipped: {e}")

        # ── 3. Persist flip count + hot-set eviction ─────────────────────────
        flip_counts = _load_flip_counts()
        entry = flip_counts.get(token.upper(), {})
        new_flip_count = entry.get('flips', 0) + 1
        flip_counts[token.upper()] = {
            **entry,
            'flips': new_flip_count,
            'last_flip_dir': opposite_dir,
            'last_flip_time': datetime.now(timezone.utc).isoformat(),
            'last_flip_source': f'v2-{source}',
            'last_flip_score': score,
        }
        _save_flip_counts(flip_counts)
        try:
            from cascade_flip_helpers import mark_token_flipped
            mark_token_flipped(token, new_flip_count, opposite_dir)
        except Exception as e:
            print(f"  [CFV2] ⚠️ Failed to write eviction metadata: {e}")
        print(f"  [CFV2] {token} flip count: {new_flip_count}/{get_flip_budget(token)}")

        # ── 4. Record post-flip window entry ─────────────────────────────────
        record_post_flip(token)

        # ── 5. Mark triggering signal as executed ────────────────────────────
        sig_id = flip_info.get('sig_id')
        if sig_id is not None:
            conn_sig = None
            try:
                conn_sig = sqlite3.connect(RUNTIME_DB)
                c = conn_sig.cursor()
                c.execute(
                    "UPDATE signals SET decision='EXECUTED', trade_id=? WHERE id=?",
                    (trade_id, sig_id)
                )
                conn_sig.commit()
            except Exception:
                pass
            finally:
                if conn_sig:
                    conn_sig.close()

        # ── 6. Clear reconciled state ────────────────────────────────────────
        try:
            import importlib
            hg_mod = importlib.import_module('hl-sync-guardian')
            clear_fn = getattr(hg_mod, '_clear_reconciled_token', None)
            if clear_fn:
                clear_fn(token)
        except (SystemExit, ImportError, Exception):
            pass  # Best-effort — guardian may sys.exit if another instance running

        return True

    else:
        err = ok.get('error', 'unknown') if ok else 'no response'
        print(f"  [CFV2] ⚠️ {token} {opposite_dir} entry failed: {err} "
              f"(position closed, will retry next cycle)")
        _set_loss_cooldown(token, opposite_dir)
        return False


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 6: Internal Helpers
# ═══════════════════════════════════════════════════════════════════════════════

def _load_flip_counts() -> dict:
    """Load persisted flip counts from disk."""
    try:
        if os.path.exists(FLIP_COUNTS_FILE):
            with open(FLIP_COUNTS_FILE) as f:
                return json.load(f)
    except Exception:
        pass
    return {}


def _save_flip_counts(counts: dict):
    """Persist flip counts to disk."""
    try:
        with FileLock('flip_counts'):
            os.makedirs(os.path.dirname(FLIP_COUNTS_FILE), exist_ok=True)
            with open(FLIP_COUNTS_FILE, 'w') as f:
                json.dump(counts, f, indent=2)
    except Exception as e:
        print(f"  [CFV2] ⚠️ Could not save flip counts: {e}")


def _record_cascade_sequence(parent_trade_id: int, token: str, entry_px: float,
                              current_px: float, pnl_usdt: float, pnl_pct: float,
                              direction: str, child_trade_id: int = None):
    """Record cascade sequence in SQLite for post-mortem analysis."""
    conn = None
    try:
        conn = sqlite3.connect(RUNTIME_DB)
        cur = conn.cursor()
        # Create table if it doesn't exist (idempotent)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS cascade_sequences (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                parent_trade_id INTEGER,
                token TEXT,
                entry_px REAL,
                current_px REAL,
                pnl_usdt REAL,
                pnl_pct REAL,
                direction TEXT,
                child_trade_id INTEGER,
                recorded_at TEXT
            )
        """)
        conn.commit()
        cur.execute("""
            INSERT INTO cascade_sequences
                (parent_trade_id, token, entry_px, current_px,
                 pnl_usdt, pnl_pct, direction, child_trade_id, recorded_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (parent_trade_id, token.upper(), entry_px, current_px,
              pnl_usdt, pnl_pct, direction.upper(), child_trade_id,
              datetime.now(timezone.utc).isoformat()))
        conn.commit()
    except Exception as e:
        print(f"  [CFV2] ⚠️ Could not record cascade sequence: {e}")
    finally:
        if conn:
            conn.close()


def _wait_for_hl_close(token: str, timeout: int = 15) -> bool:
    """
    Wait for a position to disappear from HL.
    Returns True if position is gone OR if we can't check (proceed with flip).
    Returns False only if we can confirm position is STILL open on HL.
    """
    try:
        import importlib
        hg_mod = importlib.import_module('hl-sync-guardian')
        _wait_fn = getattr(hg_mod, '_wait_for_position_closed', None)
        if _wait_fn is None:
            raise AttributeError("_wait_for_position_closed not found")
        return _wait_fn(token, timeout=timeout)
    except SystemExit:
        # Guardian's lock check sys.exit'd — guardian is running.
        # mirror_close already closed HL, so proceed with flip.
        print(f"  [CFV2] ⚠️ _wait_for_hl_close: guardian running for {token} — proceeding (mirror_close handled HL)")
        return True
    except Exception as e:
        # Other error — proceed (mirror_close already handled HL)
        print(f"  [CFV2] ⚠️ _wait_for_hl_close failed for {token}: {e} — proceeding")
        return True


def _set_loss_cooldown(token: str, direction: str, hours: float = None):
    """Set loss cooldown on a token/direction pair."""
    try:
        import importlib
        pm = importlib.import_module('position_manager')
        pm.set_loss_cooldown(token, direction, hours)
        return
    except Exception:
        pass
    # Fallback: update loss_cooldowns.json directly
    try:
        data = {}
        if os.path.exists(LOSS_COOLDOWN_FILE):
            with open(LOSS_COOLDOWN_FILE) as f:
                data = json.load(f)
        key = f"{token.upper()}:{direction.upper()}"
        if hours is None:
            streak_entry = data.get(key, {})
            streak = streak_entry.get('streak', 0) + 1
            hours = min(LOSS_COOLDOWN_MAX * 60, LOSS_COOLDOWN_BASE * 60 * (2 ** (streak - 1))) / 60
        else:
            streak = 1
        data[key] = {
            'expires': time.time() + hours * 3600,
            'streak': streak,
        }
        with FileLock('loss_cooldowns'):
            with open(LOSS_COOLDOWN_FILE, 'w') as f:
                json.dump(data, f, indent=2)
    except Exception as e2:
        print(f"  [CFV2] ⚠️ Could not set cooldown: {e2}")


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 7: CLI Test
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == '__main__':
    print("cascade_flip_v2 module — import this from position_manager.py")
    print("Usage: from cascade_flip_v2 import compute_flip_score, cascade_flip_v2")
    print()
    print(f"CASCADE_FLIP_ENABLED     = {CASCADE_FLIP_ENABLED}")
    print(f"CASCADE_FLIP_V2_ENABLED  = {CASCADE_FLIP_V2_ENABLED}")
    print(f"Scoring: MTF={CFV2_MTF_MAX_PTS} + Cascade={CFV2_CASCADE_MAX_PTS} "
          f"+ MACD={CFV2_MACD_MAX_PTS} + Momentum={CFV2_MOMENTUM_MAX_PTS} = 100 max")
    print(f"Post-flip: min_cycles={CFV2_POST_FLIP_MIN_CYCLES}, "
          f"cooldown={CFV2_POST_FLIP_COOLDOWN_M}min")
    print(f"Budget: high_WR={CFV2_BUDGET_WIN_RATE_HIGH:.0%}→5, "
          f"low_WR={CFV2_BUDGET_WIN_RATE_LOW:.0%}→1, default={CFV2_BUDGET_DEFAULT}")
