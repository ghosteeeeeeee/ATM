#!/usr/bin/env python3
"""
Cascade Flip — standalone module for executing cascade flips.

Extractable from position_manager.py for isolated testing.
Orchestrates:
  1. Close losing position (paper DB + HL mirror)
  2. Wait for HL fill confirmation
  3. Enter opposite direction
  4. Place SL/TP on HL
  5. Record cascade sequence, persist flip counts, hot-set eviction
"""

import os
import sys
import json
import sqlite3
import importlib
import time
from datetime import datetime, timezone
from typing import Dict

# ── Path setup ─────────────────────────────────────────────────────────────────
# Add scripts/ to path so we can import from other Hermes modules
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if _SCRIPT_DIR not in sys.path:
    sys.path.insert(0, _SCRIPT_DIR)

from paths import RUNTIME_DB, FLIP_COUNTS_FILE, LOSS_COOLDOWN_FILE, LOSS_COOLDOWN_BASE, LOSS_COOLDOWN_MAX
from hermes_file_lock import FileLock


# ── Constants ──────────────────────────────────────────────────────────────────
CASCADE_FLIP_MAX = 3       # Max flips per token before permanent lockout
MIN_NOTIONAL = 11.0       # HL minimum $10 + $1 buffer


# ── Helpers (copied from position_manager.py) ───────────────────────────────────

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
        print(f"  [CASCADE FLIP] ⚠️ Could not save flip counts: {e}")


def _record_cascade_sequence(parent_trade_id: int, token: str, entry_px: float,
                              current_px: float, pnl_usdt: float, pnl_pct: float,
                              direction: str, child_trade_id: int = None):
    """
    Record cascade sequence for post-mortem analysis.
    Uses cascade_sequences table (created by cascade_flip_helpers).
    """
    try:
        conn = sqlite3.connect(RUNTIME_DB)
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO cascade_sequences
                (parent_trade_id, token, entry_px, current_px,
                 pnl_usdt, pnl_pct, direction, child_trade_id, recorded_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT DO NOTHING
        """, (parent_trade_id, token.upper(), entry_px, current_px,
              pnl_usdt, pnl_pct, direction.upper(), child_trade_id,
              datetime.now(timezone.utc).isoformat()))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"  [CASCADE FLIP] ⚠️ Could not record cascade sequence: {e}")


def _wait_for_hl_close(token: str, timeout: int = 15) -> bool:
    """
    Wait for a position to actually disappear from HL.
    Uses _wait_for_position_closed from hl-sync-guardian.py (loaded via importlib
    since the filename has a dash).
    Returns True if position is gone (closed/filled), False if still open.
    """
    try:
        import importlib
        hg_mod = importlib.import_module('hl-sync-guardian')
        _wait_fn = getattr(hg_mod, '_wait_for_position_closed', None)
        if _wait_fn is None:
            raise AttributeError("_wait_for_position_closed not found")
        return _wait_fn(token, timeout=timeout)
    except Exception as e:
        print(f"  [CASCADE FLIP] ⚠️ _wait_for_hl_close failed: {e} — proceeding without wait")
        return True  # Proceed on error (old behavior fallback)


def _get_db_connection():
    """Get a SQLite connection to the runtime DB."""
    try:
        conn = sqlite3.connect(RUNTIME_DB, timeout=5)
        conn.row_factory = sqlite3.Row
        return conn
    except Exception as e:
        print(f"  [CASCADE FLIP] ⚠️ DB connection failed: {e}")
        return None


def _close_paper_position(trade_id: int, reason: str) -> bool:
    """Close paper trade in DB. Returns True on success."""
    reason = reason[:20]
    conn = _get_db_connection()
    if conn is None:
        return False
    try:
        cur = conn.cursor()
        now = datetime.now(timezone.utc)
        # Fetch current price before closing
        cur.execute("""
            SELECT token, direction, entry_price, current_price,
                   amount_usdt, leverage, signal, confidence
            FROM trades WHERE id = %s
        """, (trade_id,))
        row = cur.fetchone()
        if not row:
            conn.rollback()
            return False
        token = row['token']
        direction = row['direction']
        entry_price = float(row['entry_price'] or 0)
        current_price = float(row['current_price'] or entry_price)
        amount_usdt = float(row['amount_usdt'] or 50)
        leverage = float(row['leverage'] or 10)
        signal_type = row['signal']
        confidence = row['confidence']
        notional = amount_usdt * leverage
        TAKER_FEE = 0.00045
        entry_fee = notional * TAKER_FEE
        exit_fee = notional * TAKER_FEE
        fee_total = entry_fee + exit_fee
        if direction == 'LONG':
            pnl_pct = ((current_price - entry_price) / entry_price * 100) if entry_price > 0 else 0
        else:
            pnl_pct = ((entry_price - current_price) / entry_price * 100) if entry_price > 0 else 0
        pnl_usdt_val = amount_usdt * (abs(pnl_pct) / 100) * (1 if pnl_pct >= 0 else -1)
        net_pnl = pnl_usdt_val - fee_total
        cur.execute("""
            UPDATE trades
            SET status = 'closed',
                close_time = ?,
                close_reason = ?,
                exit_reason = ?,
                exit_price = ?,
                pnl_pct = ?,
                pnl_usdt = ?,
                fees = ?,
                is_guardian_close = FALSE,
                hype_realized_pnl_usdt = ?,
                hype_realized_pnl_pct = ?
            WHERE id = %s AND status = 'open'
        """, (now, reason, reason, current_price,
              round(pnl_pct, 4), round(pnl_usdt_val, 4),
              json.dumps({'entry_fee': round(entry_fee, 6), 'exit_fee': round(exit_fee, 6),
                          'fee_total': round(fee_total, 6), 'net_pnl': round(net_pnl, 6)}),
              None, None, trade_id))
        if cur.rowcount == 0:
            conn.rollback()
            conn.close()
            return False
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"  [CASCADE FLIP] ⚠️ _close_paper_position error: {e}")
        try:
            conn.rollback()
            conn.close()
        except Exception:
            pass
        return False


def _set_loss_cooldown(token: str, direction: str, hours: float = None):
    """Set loss cooldown on a token/direction pair (fallback when position_manager unavailable)."""
    # Try position_manager first, fall back to direct JSON update
    try:
        # Use lazy import to avoid circular dependency
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
            # hours = min(40min, 10min * 2^(streak-1))
        else:
            streak = 1
        data[key] = {
            'expires': time.time() + hours * 3600,
            'streak': streak
        }
        with FileLock('loss_cooldowns'):
            with open(LOSS_COOLDOWN_FILE, 'w') as f:
                json.dump(data, f, indent=2)
    except Exception as e2:
        print(f"  [CASCADE FLIP] ⚠️ Could not set cooldown: {e2}")


# ── Main cascade_flip function ─────────────────────────────────────────────────

def cascade_flip(token: str, position_direction: str, trade_id: int,
                 live_pnl: float, flip_info: Dict,
                 entry_price: float) -> bool:
    """
    Execute a cascade flip: close losing position, enter opposite direction.

    Orchestrates:
      1. Close paper trade (DB)
      2. Wait for HL fill confirmation
      3. Enter opposite direction
      4. Place SL/TP on HL
      5. Record cascade sequence + flip counts + hot-set eviction

    Returns True ONLY if both close AND entry succeeded.
    Returns False if either fails.
    """
    opposite_dir = flip_info['opposite_dir']
    conf = flip_info['conf']
    source = flip_info['source']
    sig_id = flip_info['sig_id']
    source_tag = f"cascade-reverse-{source}"

    print(f"  [CASCADE FLIP] {token} {position_direction}→{opposite_dir} "
          f"(loss={live_pnl:+.2f}%, opp_conf={conf:.1f}%, src={source})")

    # ── 0. Look up old trade data ───────────────────────────────────────────
    try:
        conn_old = _get_db_connection()
        if conn_old:
            cur_old = conn_old.cursor()
            cur_old.execute(
                "SELECT amount_usdt, leverage FROM trades WHERE id=%s",
                (trade_id,)
            )
            row_old = cur_old.fetchone()
            cur_old.close(); conn_old.close()
            old_amount = float(row_old['amount_usdt']) if row_old else 50.0
        else:
            old_amount = 50.0
    except Exception:
        old_amount = 50.0
    close_pnl_usdt = round(live_pnl / 100 * old_amount, 4)

    # ── 1. Close the losing position ────────────────────────────────────────
    close_ok = _close_paper_position(trade_id, f"cascade_flip_{live_pnl:+.2f}%")
    if not close_ok:
        print(f"  [CASCADE FLIP] ❌ Failed to close {token} #{trade_id}")
        return False

    # ── 1b. Wait for HL fill confirmation ─────────────────────────────────
    # This is the critical fix: we must verify the old position is actually
    # gone from HL before placing the new opposite order. Without this, both
    # old and new can exist simultaneously, causing orphan sweep to close both.
    print(f"  [CASCADE FLIP] Waiting for {token} {position_direction} to close on HL...")
    filled = _wait_for_hl_close(token, timeout=15)
    if not filled:
        print(f"  [CASCADE FLIP] ❌ {token} still on HL after fill-wait — aborting flip. "
              f"Will retry next cycle. Paper closed, HL orphan handled by guardian.")
        return False
    print(f"  [CASCADE FLIP] ✅ {token} {position_direction} confirmed closed on HL")

    # ── 1c. Record cascade close ────────────────────────────────────────────
    _record_cascade_sequence(
        parent_trade_id=trade_id, token=token,
        entry_px=entry_price,
        current_px=flip_info.get('price') or entry_price,
        pnl_usdt=close_pnl_usdt, pnl_pct=live_pnl,
        direction=position_direction,
        child_trade_id=None
    )

    # ── 2. Enter opposite direction ─────────────────────────────────────────
    from hyperliquid_exchange import place_order, get_prices, _round_position_sz
    try:
        price_map = get_prices([token])
        current_price = price_map.get(token, 0) or 0
        if not current_price or current_price <= 0:
            current_price = flip_info.get('price') or 0
    except Exception:
        current_price = flip_info.get('price') or 0
    if not current_price or current_price <= 0:
        print(f"  [CASCADE FLIP] ❌ Could not get price for {token} — flip incomplete")
        return False  # Paper closed but new entry never attempted

    sz_coins = MIN_NOTIONAL / current_price if current_price > 0 else 0
    if sz_coins <= 0:
        sz_coins = old_amount / current_price if current_price > 0 else old_amount
    sz_coins = _round_position_sz(sz_coins, token)

    ok = place_order(
        name=token,
        side='BUY' if opposite_dir == 'LONG' else 'SELL',
        sz=sz_coins,
        price=current_price,
        order_type='Market',
    )

    if ok and ok.get('success'):
        print(f"  [CASCADE FLIP] ✅ {token} {opposite_dir} entered @ ${current_price:.6f}")

        # ── 2a. Record cascade entry ─────────────────────────────────────────
        try:
            conn_seq = _get_db_connection()
            if conn_seq:
                cur_seq = conn_seq.cursor()
                cur_seq.execute(
                    "SELECT id FROM trades WHERE token=%s AND status='open' ORDER BY id DESC LIMIT 1",
                    (token.upper(),)
                )
                row_seq = cur_seq.fetchone()
                cur_seq.close(); conn_seq.close()
                new_trade_id = row_seq['id'] if row_seq else None
                if new_trade_id:
                    _record_cascade_sequence(
                        parent_trade_id=trade_id, token=token,
                        entry_px=current_price,
                        current_px=0, pnl_usdt=0, pnl_pct=0,
                        direction=opposite_dir,
                        child_trade_id=new_trade_id
                    )
        except Exception as e:
            print(f"  [CASCADE FLIP] ⚠️ Could not record cascade entry: {e}")

        # ── 2b. Fetch SL/TP values ───────────────────────────────────────────
        conn_sl = _get_db_connection()
        sl_val = tp_val = leverage_db = 0.0
        if conn_sl:
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
                    sl_val = float(sl_row['stop_loss'] or 0)
                    tp_val = float(sl_row['target'] or 0)
                    leverage_db = int(sl_row['leverage'] or 10)
                cur_sl.close()
            except Exception:
                pass
            finally:
                conn_sl.close()

        trade_sz = sz_coins

        # ── 2c. Sync DB entry for post-flip position ──────────────────────────
        try:
            from cascade_flip_helpers import insert_post_flip_trade
            new_tid = insert_post_flip_trade(
                token=token,
                direction=opposite_dir,
                entry_price=current_price,
                hl_entry_price=current_price,
                amount_usdt=float(trade_sz),
                leverage=leverage_db,
                stop_loss=sl_val,
                target=tp_val,
                signal=source_tag,
                signal_source=source_tag,
            )
            if new_tid:
                print(f"  [CASCADE FLIP] ✅ Post-flip DB entry created: trade_id={new_tid} atr_managed=TRUE")
            else:
                print(f"  [CASCADE FLIP] ⚠️ Post-flip DB entry not inserted (guardian likely synced it)")
        except Exception as e:
            print(f"  [CASCADE FLIP] ⚠️ Post-flip DB INSERT skipped: {e}")

        # ── 2d. Place SL + TP on HL ──────────────────────────────────────────
        if sl_val > 0:
            try:
                from hyperliquid_exchange import place_sl as hl_place_sl, place_tp as hl_place_tp, hype_coin
                hl_token = hype_coin(token)
                sl_result = hl_place_sl(hl_token, opposite_dir, sl_val, float(trade_sz))
                tp_result = hl_place_tp(hl_token, opposite_dir, tp_val, float(trade_sz)) if tp_val > 0 else {"success": True}
                if sl_result.get("success"):
                    print(f"  [CASCADE FLIP] ✅ SL+TP placed on HL: {hl_token} {opposite_dir} SL={sl_val:.6f} TP={tp_val:.6f if tp_val > 0 else 'N/A'}")
                else:
                    print(f"  [CASCADE FLIP] ⚠️ SL placement failed: {sl_result.get('error')}")
            except Exception as e:
                print(f"  [CASCADE FLIP] ⚠️ HL SL/TP order skipped: {e}")

        # ── 3. Persist flip count + hot-set eviction ─────────────────────────
        flip_counts = _load_flip_counts()
        entry = flip_counts.get(token.upper(), {})
        new_flip_count = entry.get('flips', 0) + 1
        flip_counts[token.upper()] = {
            'flips': new_flip_count,
            'last_flip_dir': opposite_dir,
            'last_flip_time': datetime.now().isoformat(),
        }
        _save_flip_counts(flip_counts)
        try:
            from cascade_flip_helpers import mark_token_flipped
            mark_token_flipped(token, new_flip_count, opposite_dir)
        except Exception as e:
            print(f"  [CASCADE FLIP] ⚠️ Failed to write eviction metadata: {e}")
        print(f"  [CASCADE FLIP] {token} flip count: {new_flip_count}/{CASCADE_FLIP_MAX}")

        # ── 4. Mark triggering signal as executed ─────────────────────────────
        if sig_id is not None:
            try:
                conn = sqlite3.connect(RUNTIME_DB)
                c = conn.cursor()
                c.execute(
                    "UPDATE signals SET decision='EXECUTED', trade_id=? WHERE id=?",
                    (trade_id, sig_id)
                )
                conn.commit()
                conn.close()
            except Exception:
                pass

        # FIX (2026-04-22): Clear reconciled state so token can be re-reconciled
        # if a new position opens after the flip. Without this, the reconciled
        # state from the original trade persists and may cause re-reconciliation
        # issues on subsequent cycles.
        try:
            import importlib
            hg_mod = importlib.import_module('hl-sync-guardian')
            clear_fn = getattr(hg_mod, '_clear_reconciled_token', None)
            if clear_fn:
                clear_fn(token)
        except Exception:
            pass  # Best-effort — guardian handles on next cycle

        return True

    else:
        err = ok.get('error', 'unknown') if ok else 'no response'
        print(f"  [CASCADE FLIP] ⚠️ {token} {opposite_dir} entry failed: {err} "
              f"(position closed, will retry next cycle)")
        _set_loss_cooldown(token, opposite_dir)
        return False


# ── CLI test ───────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    print("cascade_flip module — import this from position_manager.py")
    print("Usage: from cascade_flip import cascade_flip")
