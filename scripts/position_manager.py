#!/usr/bin/env python3
"""
Position Manager for Hermes Trading System
Manages open positions, SL/TP, max 10 positions.
Paper trading only — no real money.
Mirrors trades to Hyperliquid (real money) via hyperliquid_exchange.
"""

import psycopg2
import psycopg2.extras
import sys
import os
import json
from datetime import datetime, timezone
from typing import List, Dict, Optional, Tuple

import hype_cache as hc

# Hyperliquid mirroring — non-blocking, failures don't stop paper trading
try:
    from hyperliquid_exchange import (
        mirror_open, mirror_close, hype_coin,
        get_open_hype_positions_curl as get_open_hype_positions,
        is_live_trading_enabled,
    )
    HYPE_AVAILABLE = True
except Exception as e:
    HYPE_AVAILABLE = False
    print(f"[Position Manager] Hyperliquid mirroring unavailable: {e}")

# ─── DB Config ────────────────────────────────────────────────────────────────
DB_CONFIG = {
    "host": "/var/run/postgresql",
    "dbname": "brain",
    "user": "postgres",
    "password": "postgres",
}
SERVER_NAME = "Hermes"
MAX_POSITIONS = 10

# ─── Thresholds ────────────────────────────────────────────────────────────────
CUT_LOSER_PNL = -3.0   # cut if pnl_pct <= -3%
SL_PCT = 0.03          # 3% stop loss (cut loser threshold — DEFAULT fallback)
SL_PCT_MIN = 0.01      # minimum SL for any trade
MAX_LEVERAGE = 5

# ─── Trailing Stop-Loss Config ─────────────────────────────────────────────────
# Default fallback values (used when trade has no per-trade trailing settings)
TRAILING_START_PCT_DEFAULT  = 0.01   # engage at +1% profit
TRAILING_BUFFER_PCT_DEFAULT = 0.005  # keep 0.5% buffer above entry when first activated
TRAILING_TIGHTEN = True     # tighten buffer as profit grows
TRAILING_DATA_FILE = '/var/www/hermes/data/trailing_stops.json'

# ─── Loss Cooldown Config ─────────────────────────────────────────────────────
# After a losing trade, block the SAME direction for N hours
# This prevents the loss spiral: trade → cut → immediately re-enter → cut again
# INCREMENTAL: consecutive losses double the cooldown (2h → 4h → 8h), wins reset streak
LOSS_COOLDOWN_FILE     = '/var/www/hermes/data/loss_cooldowns.json'
LOSS_COOLDOWN_BASE     = 2.0   # hours for 1st consecutive loss
LOSS_COOLDOWN_MAX       = 8.0   # cap at 8 hours after 3+ consecutive losses
LOSS_STREAK_RESET_WIN   = True   # reset streak to 0 after a win (good trend continuation)
WIN_COOLDOWN_MINUTES    = 5     # block same direction for 5 min after a win

# ─── DB Helpers ────────────────────────────────────────────────────────────────
def get_db_connection():
    """Get a connection to the brain DB."""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        return conn
    except Exception as e:
        print(f"[Position Manager] DB connection error: {e}")
        return None


def get_cursor(conn):
    """Get a dict cursor."""
    return conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)


# ─── Core Queries ─────────────────────────────────────────────────────────────
def get_open_positions(server: str = SERVER_NAME) -> List[Dict]:
    """Query brain DB for open trades for the given server."""
    conn = get_db_connection()
    if conn is None:
        return []

    try:
        cur = get_cursor(conn)
        cur.execute("""
            SELECT id, token, direction, entry_price, current_price,
                   pnl_pct, pnl_usdt, stop_loss, target, exchange,
                   open_time, close_time, status, signal, confidence,
                   leverage, paper, sl_distance, sl_group,
                   trailing_activation, trailing_distance
            FROM trades
            WHERE status = 'open'
              AND server = %s
            ORDER BY open_time DESC
        """, (server,))
        rows = cur.fetchall()
        return [dict(r) for r in rows]
    except Exception as e:
        print(f"[Position Manager] get_open_positions error: {e}")
        return []
    finally:
        conn.close()


def get_position_count(server: str = SERVER_NAME) -> int:
    """Count open positions for the given server."""
    conn = get_db_connection()
    if conn is None:
        return 0

    try:
        cur = get_cursor(conn)
        cur.execute("""
            SELECT COUNT(*) as cnt FROM trades
            WHERE status = 'open' AND server = %s
        """, (server,))
        row = cur.fetchone()
        return int(row["cnt"]) if row else 0
    except Exception as e:
        print(f"[Position Manager] get_position_count error: {e}")
        return 0
    finally:
        conn.close()


def is_position_open(token: str, server: str = SERVER_NAME) -> bool:
    """Check if token already has an open position for the given server."""
    conn = get_db_connection()
    if conn is None:
        return False

    try:
        cur = get_cursor(conn)
        cur.execute("""
            SELECT COUNT(*) as cnt FROM trades
            WHERE status = 'open'
              AND server = %s
              AND LOWER(token) = LOWER(%s)
        """, (server, token))
        row = cur.fetchone()
        return int(row["cnt"]) > 0 if row else False
    except Exception as e:
        print(f"[Position Manager] is_position_open error: {e}")
        return False
    finally:
        conn.close()


# ─── Decision Helpers ─────────────────────────────────────────────────────────
def should_cut_loser(pnl_pct: float, trade: Dict = None) -> bool:
    """
    Return True if price has crossed the trade's stop-loss threshold.

    Checks in order of priority:
    1. Actual stop_loss price (if set in DB) — compares live price vs SL price
    2. Trade's sl_distance (A/B test param, e.g. 0.015 = -1.5% threshold)
    3. Global CUT_LOSER_PNT (-3% default fallback)
    """
    if trade:
        sl_price = trade.get('stop_loss')
        entry_price = trade.get('entry_price')
        direction = trade.get('direction', '').upper()
        live_price = trade.get('current_price')

        # Priority 1: check actual stop_loss price if we have all values
        if sl_price and entry_price and live_price and direction:
            try:
                sl = float(sl_price)
                entry = float(entry_price)
                live = float(live_price)
                if direction == 'SHORT':
                    if live >= sl:
                        return True
                elif direction == 'LONG':
                    if live <= sl:
                        return True
            except (TypeError, ValueError):
                pass

        # Priority 2: sl_distance from A/B test
        sl_dist = trade.get('sl_distance') or trade.get('sl_group')
        if sl_dist is not None:
            try:
                threshold = -float(sl_dist) * 100  # sl_dist=0.015 → -1.5%
                return pnl_pct <= threshold
            except (TypeError, ValueError):
                pass

    # Priority 3: global hard stop
    return pnl_pct <= CUT_LOSER_PNL


# ─── Trade Operations ─────────────────────────────────────────────────────────

def _record_ab_close(token, direction, pnl_pct, pnl_usdt, experiment, sl_dist, net_pnl=None):
    """Record trade close to ab_results table.

    experiment can be:
      - A pipe-separated string: "sl-distance-test:SL1pct|entry-timing-test:IMMEDIATE|..."
      - A dict: {'experiment': 'sl-distance-test:SL1pct|...'}
      - A garbled JSON string (old format)

    net_pnl is the true PnL after Hyperliquid fees (0.045% per side on notional).
    Used for win/loss determination if provided.
    """
    import psycopg2, json, re
    if not experiment:
        return

    # Normalize experiment to a plain string
    if isinstance(experiment, dict):
        exp_str = experiment.get('experiment', '')
    elif isinstance(experiment, str) and experiment.startswith('{'):
        try:
            exp_str = json.loads(experiment).get('experiment', '')
        except Exception:
            exp_str = experiment
    else:
        exp_str = str(experiment)

    # Parse test_name:variant_id pairs from pipe-separated string
    test_map = {}
    for part in exp_str.split('|'):
        if ':' in part:
            test_name, variant_id = part.split(':', 1)
            test_name = test_name.strip()
            variant_id = variant_id.strip()
            test_map[test_name] = variant_id

    # Use net_pnl for win/loss and recording (or raw pnl_usdt if fees not available)
    record_pnl = net_pnl if net_pnl is not None else pnl_usdt
    is_win = float(record_pnl or 0) > 0

    try:
        conn = psycopg2.connect(host='/var/run/postgresql', dbname='brain', user='postgres', password='***')
        cur = conn.cursor()
        for test_name, variant_id in test_map.items():
            if not test_name or not variant_id:
                continue
            try:
                cur.execute("""
                    INSERT INTO ab_results (test_name, variant_id, trades, wins, losses,
                                           total_pnl_pct, total_pnl_usdt, updated_at)
                    VALUES (%s, %s, 1, %s, %s, %s, %s, now())
                    ON CONFLICT (test_name, variant_id)
                    DO UPDATE SET
                        trades = ab_results.trades + 1,
                        wins = ab_results.wins + %s,
                        losses = ab_results.losses + %s,
                        total_pnl_pct = ab_results.total_pnl_pct + %s,
                        total_pnl_usdt = ab_results.total_pnl_usdt + %s,
                        win_rate_pct = CASE
                            WHEN ab_results.trades + 1 > 0
                            THEN (ab_results.wins + %s)::float / (ab_results.trades + 1) * 100
                            ELSE 0 END,
                        updated_at = now()
                """, (test_name, variant_id,
                      1 if is_win else 0, 0 if is_win else 1,
                      float(pnl_pct or 0), float(record_pnl or 0),
                      1 if is_win else 0, 0 if is_win else 1,
                      float(pnl_pct or 0), float(record_pnl or 0),
                      1 if is_win else 0))
                print(f"[Position Manager] AB UPSERT OK: test={test_name} variant={variant_id} is_win={is_win}")
            except Exception as ue:
                import traceback; traceback.print_exc()
                print(f"[Position Manager] AB UPSERT FAIL: test={test_name} variant={variant_id} — {ue}")
        conn.commit()
        cur.close(); conn.close()
    except Exception as e:
        import traceback; traceback.print_exc()
        print(f"[Position Manager] ab_results close error: {e}")


def close_paper_position(trade_id: int, reason: str) -> bool:
    """Close a paper position via direct SQL UPDATE."""
    conn = get_db_connection()
    if conn is None:
        return False

    try:
        cur = get_cursor(conn)
        now = datetime.now(timezone.utc)

        # Fetch trade details before closing
        cur.execute("""
            SELECT token, direction, entry_price, current_price,
                   pnl_pct, experiment, sl_distance, amount_usdt
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
        experiment = row['experiment']
        sl_dist = row['sl_distance']

        # ── Fee calculation ──────────────────────────────────────────
        # Hyperliquid charges 0.045% per side on NOTIONAL value
        TAKER_FEE = 0.00045
        leverage = float(row.get('leverage') or 10)
        entry_fee_paid = float(row.get('entry_fee') or 0)
        notional = amount_usdt * leverage

        # If entry_fee was never recorded, calculate it now
        if entry_fee_paid == 0 and notional > 0:
            entry_fee_paid = notional * TAKER_FEE

        exit_fee = notional * TAKER_FEE
        fee_total = entry_fee_paid + exit_fee

        # Calculate pnl_usdt at close (direction-aware)
        if direction == 'LONG':
            pnl_pct = ((current_price - entry_price) / entry_price * 100) if entry_price > 0 else 0
        else:
            pnl_pct = ((entry_price - current_price) / entry_price * 100) if entry_price > 0 else 0
        pnl_usdt = amount_usdt * leverage * (pnl_pct / 100)

        # Net PnL after fees
        net_pnl = pnl_usdt - fee_total

        # ── Trigger loss cooldown (incremental: 2h → 4h → 8h per consecutive loss) ──
        is_loss = float(pnl_usdt or 0) < 0
        if is_loss:
            set_loss_cooldown(token, direction)
            # Post-mortem: if we lost on a direction, was the market moving against us first?
            _analyze_loss_direction(token, direction, entry_price, current_price)

        # ── Trigger win cooldown ──────────────────────────────────
        # Also: clear loss streak since WIN confirms this was the right direction
        is_win = float(pnl_usdt or 0) > 0
        if is_win:
            _set_win_cooldown(token, direction)
            if LOSS_STREAK_RESET_WIN:
                clear_loss_streak(token, direction)

        cur.execute("""
            UPDATE trades
            SET status = 'closed',
                close_time = %s,
                close_reason = %s,
                exit_price = %s,
                pnl_pct = %s,
                pnl_usdt = %s,
                fees = %s
            WHERE id = %s
        """, (now, reason, current_price,
              round(pnl_pct, 4), round(pnl_usdt, 4),
              json.dumps({'entry_fee': round(entry_fee_paid, 6), 'exit_fee': round(exit_fee, 6), 'fee_total': round(fee_total, 6), 'net_pnl': round(net_pnl, 6)}),
              trade_id))
        # DB UPDATE done — do NOT commit yet. Commit only after HL confirms, or rollback if HL fails.
        print(f"[Position Manager] Closed trade {trade_id} ({reason})")

        # ── Mirror to Hyperliquid (real trade) ───────────────────────
        # Commit DB FIRST, then close on HL. This prevents the worst-case scenario
        # where HL closes but DB rollback leaves them permanently divergent.
        # If DB commit succeeds but HL close fails → hype-sync catches it next run.
        # If DB commit fails → rollback (safe), HL is still open for retry.
        if HYPE_AVAILABLE and is_live_trading_enabled():
            hype_token = hype_coin(token)
            conn.commit()  # lock in DB close
            try:
                mirror_close(hype_token, direction)
                print(f"[Position Manager] HYPE mirror_close SUCCESS: {hype_token}")
            except RuntimeError as me:
                print(f"[Position Manager] HYPE mirror_close FAILED (DB committed, HL still open): {me}")
                print(f"[Position Manager] hype-sync will reconcile on next run")
            except Exception as me:
                print(f"[Position Manager] HYPE mirror_close ERROR (DB committed, HL still open): {me}")
                print(f"[Position Manager] hype-sync will reconcile on next run")
        elif HYPE_AVAILABLE:
            # Live trading OFF → paper only
            print(f"[Position Manager] Live trading OFF — paper close only (no HL)")
            conn.commit()
        else:
            # No HYPE available at all
            conn.commit()

        # Record to ab_results on close — wrap with verbose logging so failures are never silent
        ab_errors = []
        if experiment and sl_dist:
            exp_str = ''
            if isinstance(experiment, dict):
                exp_str = experiment.get('experiment', '')
            elif isinstance(experiment, str) and experiment.startswith('{'):
                import json as _json
                try:
                    exp_str = _json.loads(experiment).get('experiment', '')
                except Exception as _e:
                    exp_str = experiment
                    ab_errors.append(f"json parse fail: {_e}")
            else:
                exp_str = str(experiment)
            print(f"[Position Manager] AB tracking: trade_id={trade_id} pnl_usdt={pnl_usdt:.2f} is_win={is_win} exp_str={exp_str!r}")
            try:
                _record_ab_close(token, direction, pnl_pct, pnl_usdt, exp_str, sl_dist, net_pnl=net_pnl)
                print(f"[Position Manager] AB recorded: {token} {direction} {'WIN' if is_win else 'LOSS'} pnl={pnl_usdt:.2f}")
            except Exception as _e:
                import traceback
                traceback.print_exc()
                print(f"[Position Manager] AB RECORD FAIL: trade_id={trade_id} token={token} — {_e}")
                ab_errors.append(str(_e))
        elif experiment is None:
            print(f"[Position Manager] AB SKIP: experiment=None for trade_id={trade_id} (no A/B data on this trade)")
        elif not sl_dist:
            print(f"[Position Manager] AB SKIP: sl_distance=None for trade_id={trade_id} (pre-AB trade)")

        return True
    except Exception as e:
        conn.rollback()
        print(f"[Position Manager] close_position error: {e}")
        return False
    finally:
        conn.close()


def adjust_stop_loss(trade_id: int, new_sl: float) -> bool:
    """Update SL in brain DB."""
    conn = get_db_connection()
    if conn is None:
        return False

    try:
        cur = get_cursor(conn)
        cur.execute("""
            UPDATE trades SET stop_loss = %s WHERE id = %s AND paper = TRUE
        """, (new_sl, trade_id))
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        print(f"[Position Manager] adjust_stop_loss error: {e}")
        return False
    finally:
        conn.close()


def enforce_max_positions(max_pos: int = MAX_POSITIONS) -> bool:
    """Return True if new positions can be opened (under max)."""
    count = get_position_count()
    return count < max_pos


# ─── Trade Parameters ─────────────────────────────────────────────────────────
def get_trade_params(direction: str, price: float, max_leverage: int = MAX_LEVERAGE) -> Dict:
    """
    Compute SL and TP for a new trade.
    LONG:  SL = price * 0.97 (3% stop), TP = price * 1.08 (8% target)
    SHORT: SL = price * 1.03 (3% stop), TP = price * 0.92 (8% target)
    Leverage: min(max_leverage, 10) capped
    
    NOTE: Trailing SL engages at +1% profit (see TRAILING_START_PCT).
    - At +1%, trailing SL is set 0.5% above entry (locks in 0.5%)
    - As profit grows, trailing SL tightens (TRAILING_TIGHTEN=True)
    """
    direction = direction.upper()
    leverage = min(max_leverage, MAX_LEVERAGE)

    if direction == "LONG":
        stop_loss = round(price * (1 - SL_PCT), 8)
        target = round(price * (1 + TP_PCT), 8)
    elif direction == "SHORT":
        stop_loss = round(price * (1 + SL_PCT), 8)
        target = round(price * (1 - TP_PCT), 8)
    else:
        raise ValueError(f"Invalid direction: {direction}")

    return {
        "stop_loss": stop_loss,
        "target": target,
        "leverage": leverage,
    }


# ─── Trailing Stop-Loss State ──────────────────────────────────────────────────
def _load_trailing_data() -> Dict:
    """Load trailing stop state from JSON file."""
    try:
        if os.path.exists(TRAILING_DATA_FILE):
            with open(TRAILING_DATA_FILE, "r") as f:
                return json.load(f)
    except Exception as e:
        print(f"[Position Manager] Error loading trailing data: {e}")
    return {}


def _save_trailing_data(data: Dict) -> None:
    """Save trailing stop state to JSON file."""
    try:
        os.makedirs(os.path.dirname(TRAILING_DATA_FILE), exist_ok=True)
        with open(TRAILING_DATA_FILE, "w") as f:
            json.dump(data, f, indent=2, default=str)
    except Exception as e:
        print(f"[Position Manager] Error saving trailing data: {e}")


def is_trailing_active(trade_id: int) -> bool:
    """Check if trailing stop is active for a trade.

    IMPORTANT: Also verify the trade exists and is open in DB.
    Orphaned entries in trailing_stops.json (from deleted trades) must not
    cause false positives that immediately close new trades with matching IDs.
    """
    # First verify the trade actually exists and is open in the DB
    conn = get_db_connection()
    if conn is None:
        return False
    try:
        cur = get_cursor(conn)
        cur.execute("SELECT id FROM trades WHERE id=%s AND status='open'", (trade_id,))
        exists = cur.fetchone() is not None
        cur.close()
        conn.close()
        if not exists:
            # Trade doesn't exist (deleted/closed) — clean up orphaned entry
            data = _load_trailing_data()
            if str(trade_id) in data:
                del data[str(trade_id)]
                _save_trailing_data(data)
            return False
    except Exception:
        if conn:
            conn.close()
        return False

    # Trade is open — check trailing file
    data = _load_trailing_data()
    return str(trade_id) in data and data[str(trade_id)].get("active", False)


def get_trailing_stop(trade: Dict, live_pnl: Optional[float] = None) -> Optional[float]:
    """
    Compute the current trailing stop for a position.
    Returns trailing SL value, or None if not yet engaged.

    - Trailing SL engages at +1% profit (pnl_pct >= TRAILING_START_PCT)
    - Tracks best price (highest for LONG, lowest for SHORT)
    - Buffer tightens as profit grows (TRAILING_TIGHTEN=True)

    Always returns a value when trailing is already active (live_pnl overrides trade dict).
    """
    direction = str(trade.get("direction", "")).upper()
    entry_price = float(trade.get("entry_price") or 0)
    current_price = float(trade.get("current_price") or 0)
    trade_id = trade.get("id")

    if entry_price <= 0 or current_price <= 0:
        return None

    # Compute pnl from live price (not stale DB value)
    if live_pnl is not None:
        pnl_pct = live_pnl
    else:
        pnl_pct = float(trade.get("pnl_pct") or 0)

    # Load trailing data
    data = _load_trailing_data()
    trade_data = data.get(str(trade_id), {})
    is_active = trade_data.get("active", False)

    # Per-trade trailing settings (from A/B test), else defaults
    trailing_start  = float(trade.get('trailing_activation') or TRAILING_START_PCT_DEFAULT)
    trailing_buffer = float(trade.get('trailing_distance') or TRAILING_BUFFER_PCT_DEFAULT)

    # If not yet activated and profit < threshold → skip activation check
    # pnl_pct is already in percentage (e.g. 1.23 = 1.23%), trailing_start is a fraction (0.01 = 1%)
    if not is_active and pnl_pct < trailing_start:
        return None

    # If trailing is not active yet → don't return a value
    if not is_active:
        return None

    # Trailing is active → always compute current SL regardless of pnl_pct
    # (pnl might dip but the trailing SL from the peak still protects)

    # Calculate buffer (tightens as profit grows)
    if TRAILING_TIGHTEN:
        buffer_pct = max(0.002, trailing_buffer / (1 + pnl_pct / 10))
    else:
        buffer_pct = trailing_buffer

    # Track best price
    if direction == "LONG":
        best_price = trade_data.get("best_price", current_price)
        if current_price > best_price:
            best_price = current_price
            data[str(trade_id)]["best_price"] = best_price
            _save_trailing_data(data)
        trailing_sl = best_price * (1 - buffer_pct)
    elif direction == "SHORT":
        best_price = trade_data.get("best_price", current_price)
        if current_price < best_price:
            best_price = current_price
            data[str(trade_id)]["best_price"] = best_price
            _save_trailing_data(data)
        trailing_sl = best_price * (1 + buffer_pct)
    else:
        return None
    
    return round(trailing_sl, 8)


def check_trailing_stop(trade: Dict, live_pnl: Optional[float] = None) -> bool:
    """
    Check if trailing stop is hit for a position.
    Returns True if trailing SL is hit (position should be closed).
    """
    trade_id = trade.get("id")
    direction = str(trade.get("direction", "")).upper()
    current_price = float(trade.get("current_price") or 0)
    entry_price = float(trade.get("entry_price") or 0)

    if entry_price <= 0 or current_price <= 0:
        return False

    # Get trailing stop value
    trailing_sl = get_trailing_stop(trade, live_pnl=live_pnl)
    if trailing_sl is None:
        return False

    # Check if trailing stop is hit
    # LONG: trailing SL is a floor — hit when price drops below it
    # SHORT: trailing SL is a ceiling — hit when price rises above it
    if direction == "LONG":
        hit = current_price < trailing_sl
    elif direction == "SHORT":
        hit = current_price > trailing_sl
    else:
        return False

    # If hit, mark as inactive so close_position doesn't double-close
    if hit:
        try:
            data = _load_trailing_data()
            if str(trade_id) in data:
                data[str(trade_id)]["active"] = False
                _save_trailing_data(data)
        except:
            pass

    return hit


def activate_trailing_stop(trade_id: int, trade: Dict) -> None:
    """Mark trailing stop as active for a trade, initializing best_price."""
    data = _load_trailing_data()
    if str(trade_id) not in data:
        data[str(trade_id)] = {}

    direction = str(trade.get("direction", "")).upper()
    entry_price = float(trade.get("entry_price") or 0)
    current_price = float(trade.get("current_price") or 0)

    # Initialize best_price based on direction
    # LONG:  best = current (entry is the low so far)
    # SHORT: best = entry (entry is the high — we haven't seen the low yet)
    # For SHORT, using current_price risks capturing a stale/old price from a
    # previous pipeline run, causing the trailing SL to fire immediately.
    if direction == "LONG":
        best_price = current_price
    else:
        best_price = entry_price

    data[str(trade_id)]["active"] = True
    data[str(trade_id)]["token"] = trade.get("token")
    data[str(trade_id)]["direction"] = direction
    data[str(trade_id)]["entry_price"] = entry_price
    data[str(trade_id)]["best_price"] = best_price
    data[str(trade_id)]["activated_at_pnl"] = float(trade.get("pnl_pct") or 0)
    data[str(trade_id)]["activated_at_price"] = current_price

    _save_trailing_data(data)
    print(f"  TRAILING STOP ACTIVATED: {trade.get('token')} {direction} "
          f"(best={best_price}, pnl={trade.get('pnl_pct'):.2f}%)")


# ─── Position Management ──────────────────────────────────────────────────────

def refresh_current_prices(server: str = SERVER_NAME):
    """Fetch live prices from Hyperliquid, update pnl_pct in brain DB for open positions of given server."""

    # ── RECONCILIATION: sync DB ↔ HL ─────────────────────────────────────────
    # This prevents orphan/ghost positions where DB and HL diverge.
    # Runs every pipeline cycle so drift is always caught.
    if HYPE_AVAILABLE and is_live_trading_enabled():
        try:
            from hyperliquid_exchange import get_open_hype_positions, close_position as hl_close_position, hype_coin
            hl_live = get_open_hype_positions()
            conn_recon = get_db_connection()
            if not conn_recon:
                return []  # fall through to normal path

            cur_recon = get_cursor(conn_recon)

            # ── Always reconcile: fetch fresh HL state and compare ─────────────
            # This runs even when DB has 0 open positions (prevents orphaned HL trades)

            # ── Ghosts: DB open, HL closed ────────────────────────
            # Only close PAPER trades (paper=FALSE) — live HL trades need manual handling.
            # Use close_paper_position to properly record AB results before HL close.
            cur_recon.execute("SELECT id, token, experiment, sl_distance FROM trades WHERE status='open' AND exchange='Hyperliquid' AND paper=FALSE")
            for row in cur_recon.fetchall():
                tok_id = row['id']
                tok = row['token']
                experiment = row.get('experiment')
                sl_dist = row.get('sl_distance')
                if tok not in hl_live:
                    print(f"  [Sync] Ghost: {tok} in DB but not HL (paper=FALSE)")
                    # Record AB results before closing so wins are tracked
                    if experiment and sl_dist:
                        try:
                            cur_recon.execute("SELECT pnl_usdt, pnl_pct FROM trades WHERE id=%s", (tok_id,))
                            pr = cur_recon.fetchone()
                            if pr:
                                _record_ab_close(tok, 'UNKNOWN', pr.pnl_pct, pr.pnl_usdt, experiment, sl_dist)
                        except Exception as e:
                            print(f"  [Sync] Ghost AB record error: {e}")
                    cur_recon.execute("UPDATE trades SET status='closed', close_time=NOW(), close_reason='ghost_recovery' WHERE id=%s", (tok_id,))
                    try:
                        hl_close_position(hype_coin(tok))
                    except Exception:
                        pass
                    print(f"  [Sync] Ghost closed: {tok} (id={tok_id})")

            # ── Orphans: HL open, DB closed/missing ─────────────────
            cur_recon.execute("SELECT DISTINCT ON (token) id, token, status FROM trades WHERE token IN %s ORDER BY token, id DESC",
                              (tuple(hl_live.keys()),) if hl_live else (('',),))
            db_token_status = {row['token']: row['status'] for row in cur_recon.fetchall()}
            for tok, hdata in hl_live.items():
                db_status = db_token_status.get(tok, 'MISSING')
                if db_status != 'open':
                    print(f"  [Sync] Orphan: {tok} on HL but DB={db_status} — closing on HL")
                    try:
                        close_res = hl_close_position(hype_coin(tok))
                        if close_res.get('success'):
                            print(f"  [Sync] Orphan closed on HL: {tok}")
                            try:
                                mids = hc.get_allMids()
                                exit_px = mids.get(tok, hdata['entry_px'])
                            except Exception:
                                exit_px = hdata['entry_px']
                            unreal = hdata.get('unrealized_pnl', 0)
                            cur_recon.execute("""
                                INSERT INTO trades (token, direction, amount_usdt, entry_price, exit_price,
                                    status, exchange, server, paper, pnl_pct, pnl_usdt, close_time, close_reason, open_time)
                                VALUES (%s, %s, %s, %s, %s, 'closed', 'Hyperliquid', %s, FALSE, %s, %s, NOW(), 'orphan_recovery', NOW())
                            """, (tok, hdata['direction'], 50.0, hdata['entry_px'], exit_px,
                                  SERVER_NAME, unreal, unreal * 50.0))
                            print(f"  [Sync] Orphan record inserted: {tok}")
                    except Exception as e:
                        print(f"  [Sync] Orphan close error {tok}: {e}")

            conn_recon.commit()
            cur_recon.close()
            conn_recon.close()

        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"  [Sync] Reconciliation error: {e}")

    positions = get_open_positions(server)
    if not positions:
        return []

    try:
        mids = hc.get_allMids()
    except Exception as e:
        print(f"  [Position Manager] Failed to fetch prices: {e}")
        return positions

    conn = get_db_connection()
    if not conn:
        return positions

    updated = 0
    try:
        cur = get_cursor(conn)
        for pos in positions:
            token = pos.get('token', '')
            cur_str = mids.get(token, '0')
            try:
                cur_price = float(cur_str)
            except:
                continue
            if cur_price <= 0:
                continue

            entry = float(pos.get('entry_price') or 0)
            direction = str(pos.get('direction', '')).upper()
            trade_id = pos.get('id')
            if not entry or not trade_id:
                continue

            if direction == 'LONG':
                pnl_pct = ((cur_price - entry) / entry) * 100
            else:
                pnl_pct = ((entry - cur_price) / entry) * 100

            cur.execute("""
                UPDATE trades
                SET pnl_pct = %s, current_price = %s,
                    pnl_usdt = %s
                WHERE id = %s
            """, (round(pnl_pct, 4), cur_price,
                  round(pnl_pct / 100 * pos.get('amount_usdt', 50) * pos.get('leverage', 1), 2),
                  trade_id))

            # Update in-memory so subsequent checks use fresh values
            pos['pnl_pct'] = round(pnl_pct, 4)
            pos['current_price'] = cur_price
            updated += 1

        conn.commit()
    except Exception as e:
        print(f"  [Position Manager] Price update error: {e}")
        conn.rollback()
    finally:
        conn.close()

    if updated:
        print(f"  [Position Manager] Updated {updated} position prices")
    return positions


def check_and_manage_positions() -> Tuple[int, int, int]:
    """
    Called every pipeline run.

    Exit strategy (trailing SL is the primary exit, no fixed TP):
    1. Cut losers: pnl <= -3% → immediate exit via static SL
    2. At +1% profit: trailing SL activates, starts at breakeven + 0.5%
    3. As profit grows: trailing SL tightens (buffer shrinks from 0.5% → 0.2%)
       → Long:  trailing SL = best_price * (1 - buffer%)
       → Short: trailing SL = best_price * (1 + buffer%)
    4. Exit when price crosses the trailing SL (reverses from peak)
       With 10x leverage, a 3-5% move = 30-50% gross profit

    Returns: (open_count, closed_count, adjusted_count)
    """
    positions = refresh_current_prices()
    open_count = len(positions)
    closed_count = 0
    adjusted_count = 0

    for pos in positions:
        token = str(pos.get("token", "UNKNOWN"))
        direction = str(pos.get("direction", "UNKNOWN")).upper()
        pnl_pct = float(pos.get("pnl_pct") or 0)
        trade_id = pos.get("id")

        # ── Compute live pnl first (before any exit decisions) ──
        entry = float(pos.get("entry_price") or 0)
        cur = float(pos.get("current_price") or 0)
        if entry > 0 and cur > 0:
            if direction == "LONG":
                live_pnl = ((cur - entry) / entry) * 100
            else:
                live_pnl = ((entry - cur) / entry) * 100
        else:
            live_pnl = pnl_pct

        trailing_active = is_trailing_active(trade_id)

        # ── 1. Trailing stop management ────────────────────────────
        # IMPORTANT: Use stored pnl_pct (not live_pnl) for activation.
        # live_pnl is recalculated from the freshest price but using it can cause
        # a race condition: price moves +1% between the price fetch and the
        # activation check, triggering immediately. Stored pnl_pct reflects the
        # price at the START of this pipeline run, giving consistent activation.
        if not trailing_active:
            trailing_start_pct = float(pos.get('trailing_activation') or TRAILING_START_PCT_DEFAULT)
            # SHORTs in loss have negative pnl_pct — use abs() so 2% adverse move activates TS
            adverse_pct = abs(pnl_pct) if direction == 'SHORT' else pnl_pct
            if adverse_pct >= trailing_start_pct:
                activate_trailing_stop(trade_id, pos)
                adjusted_count += 1
                trailing_active = True

        # ── 2. Trailing SL exit (primary) ─────────────────────────
        # Once trailing is active, it is the ONLY exit — cut_loser is DISABLED.
        # This prevents the cut_loser from firing during a retrace from a big gain.
        trailing_sl = None
        if trailing_active:
            trailing_sl = get_trailing_stop(pos, live_pnl=live_pnl)
            if check_trailing_stop(pos, live_pnl=live_pnl):
                reason = f"trailing_exit_{live_pnl:+.2f}%"
                close_paper_position(trade_id, reason)
                closed_count += 1
                print(f"  TRAILING EXIT {token} {direction} {live_pnl:+.2f}% (SL: {trailing_sl:.6f})")

        # ── 3. Cut loser (fallback — only fires if trailing is NOT active) ──
        # Cut_loser is a safety net for new positions before trailing activates.
        # After trailing activates, the trailing SL is the only exit.
        if not trailing_active and should_cut_loser(live_pnl, pos):
            reason = f"cut_loser_{live_pnl:+.2f}%"
            close_paper_position(trade_id, reason)
            closed_count += 1
            print(f"  CUT_LOSER {token} {direction} {live_pnl:+.2f}%")

        # ── 4. Update trailing SL in DB for dashboard display ───────
        if trailing_sl:
            try:
                conn_pm = get_db_connection()
                if conn_pm:
                    cur_pm = get_cursor(conn_pm)
                    cur_pm.execute(
                        "UPDATE trades SET stop_loss=%s WHERE id=%s",
                        (round(trailing_sl, 8), trade_id)
                    )
                    conn_pm.commit()
                    conn_pm.close()
            except Exception:
                pass

    print(f"Position Manager: {open_count} open | {closed_count} closed | {adjusted_count} adjusted")
    return open_count, closed_count, adjusted_count


# ─── Loss Cooldown (Incremental) ──────────────────────────────────────────────
# Entries store: {key: {"expires": unix_ts, "streak": 3}}
# Each consecutive loss: streak++, hours doubles (2h → 4h → 8h cap)
# Wins optionally reset the streak (LOSS_STREAK_RESET_WIN)

def _load_cooldowns() -> Dict:
    """Load cooldown data from JSON file.

    Handles two formats:
    - Old: {"KEY": unix_timestamp} — convert to new format
    - New: {"KEY": {"expires": unix_ts, "streak": N, ...}}
    """
    try:
        if os.path.exists(LOSS_COOLDOWN_FILE):
            with open(LOSS_COOLDOWN_FILE) as f:
                raw = json.load(f)
            # Migrate old float entries to new dict format
            migrated = False
            for k, v in raw.items():
                if isinstance(v, float):
                    raw[k] = {"expires": v, "streak": 1}
                    migrated = True
            if migrated:
                _save_cooldowns(raw)
                print(f"[Position Manager] Migrated {migrated} old cooldown entries to new format")
            return raw
    except Exception as e:
        print(f"[Position Manager] Error loading cooldowns: {e}")
    return {}


def _save_cooldowns(data: Dict) -> None:
    """Save cooldown data to JSON file."""
    try:
        os.makedirs(os.path.dirname(LOSS_COOLDOWN_FILE), exist_ok=True)
        with open(LOSS_COOLDOWN_FILE, "w") as f:
            json.dump(data, f, indent=2, default=str)
    except Exception as e:
        print(f"[Position Manager] Error saving cooldowns: {e}")


def _clean_expired(data: Dict) -> Dict:
    """Remove expired entries. Handles both old float and new dict formats."""
    now = datetime.now(timezone.utc).timestamp()
    def expiry(v):
        if isinstance(v, dict):
            return v.get("expires", 0)
        return v  # old float format
    return {k: v for k, v in data.items() if expiry(v) > now}


def is_loss_cooldown_active(token: str, direction: str) -> bool:
    """Return True if token+direction is in loss cooldown."""
    key = f"{token.upper()}:{direction.upper()}"
    data = _clean_expired(_load_cooldowns())
    return key in data


def set_loss_cooldown(token: str, direction: str, hours: float = None) -> None:
    """Increment loss streak and set cooldown for token+direction."""
    key = f"{token.upper()}:{direction.upper()}"
    data = _load_cooldowns()
    entry = data.get(key, None)

    # Handle old float format: convert to new dict
    if entry is None:
        streak = 1
    elif isinstance(entry, float):
        streak = 1  # old entry expired already in this case, start fresh
    else:
        streak = entry.get("streak", 0) + 1

    # Incremental hours: 2 → 4 → 8 (capped)
    if hours is None:
        hours = min(LOSS_COOLDOWN_BASE * (2 ** (streak - 1)), LOSS_COOLDOWN_MAX)

    now = datetime.now(timezone.utc).timestamp()
    expiry = now + (hours * 3600)
    data[key] = {"expires": expiry, "streak": streak, "hours": hours}
    _save_cooldowns(data)
    print(f"[Position Manager] LOSS COOLDOWN: {token} {direction} streak={streak} blocked for {hours:.1f}h")


def clear_loss_streak(token: str, direction: str) -> None:
    """Clear loss cooldown and streak entirely. Used when a win confirms the direction."""
    key = f"{token.upper()}:{direction.upper()}"
    data = _load_cooldowns()
    if key in data:
        del data[key]
        _save_cooldowns(data)
        print(f"[Position Manager] LOSS STREAK CLEARED: {token} {direction}")


def get_loss_streak(token: str, direction: str) -> int:
    """Return current loss streak for token+direction, or 0."""
    key = f"{token.upper()}:{direction.upper()}"
    data = _clean_expired(_load_cooldowns())
    return data.get(key, {}).get("streak", 0)


def get_loss_cooldown_remaining(token: str, direction: str) -> float:
    """Return hours remaining on loss cooldown, or 0 if none."""
    key = f"{token.upper()}:{direction.upper()}"
    data = _load_cooldowns()
    entry = data.get(key, {})
    # Old format: entry is a float (unix ts). New: entry is a dict.
    if isinstance(entry, float):
        expiry = entry
    else:
        expiry = entry.get("expires", 0)
    now = datetime.now(timezone.utc).timestamp()
    if expiry <= now:
        return 0.0
    return max(0, (expiry - now) / 3600)


# ─── Wrong-Side Learning ────────────────────────────────────────────────────────
# After a loss, analyze whether the market moved against us FIRST
# before eventually moving in our favor (wrong-side entry = we faded a real move)
# Stores findings in a JSON file for decider to use as a pre-trade filter

WRONG_SIDE_FILE = '/var/www/hermes/data/wrong_side_learning.json'


def _load_wrong_side() -> Dict:
    """Load wrong-side learning data."""
    try:
        if os.path.exists(WRONG_SIDE_FILE):
            with open(WRONG_SIDE_FILE) as f:
                return json.load(f)
    except Exception:
        pass
    return {}


def _save_wrong_side(data: Dict) -> None:
    """Save wrong-side learning data."""
    try:
        os.makedirs(os.path.dirname(WRONG_SIDE_FILE), exist_ok=True)
        with open(WRONG_SIDE_FILE, "w") as f:
            json.dump(data, f, indent=2, default=str)
    except Exception:
        pass


def _analyze_loss_direction(token: str, direction: str, entry_price: float, exit_price: float) -> None:
    """
    Post-mortem on a losing trade.

    Check: did price move AGAINST us first (counter-move), before eventually
    moving in our favor and hitting our SL?

    Example: we SHORT at $10, price spikes to $10.50 (we're wrong), then
    eventually drifts back down and we exit near $10.30 via trailing SL.
    This tells us the initial move was real — we were on the wrong side.

    Stores count + avg counter-move % per token+direction.
    Future SHORTs on KAITO will check this and require stronger confirmation.
    """
    import sqlite3 as _sqlite3

    token_upper = token.upper()
    key = f"{token_upper}:{direction.upper()}"

    try:
        # Get price history for the last ~4 hours to find the counter-move
        conn = _sqlite3.connect('/root/.hermes/data/signals_hermes.db')
        cur = conn.cursor()
        cur.execute("""
            SELECT timestamp, price FROM price_history
            WHERE token=? AND timestamp > datetime('now', '-4 hours')
            ORDER BY timestamp ASC
        """, (token_upper,))
        rows = cur.fetchall()
        conn.close()

        if len(rows) < 5:
            return

        prices = [(int(r[0]), float(r[1])) for r in rows]  # (unix_ts, price)
        entry_ts = None

        # Find the bar closest to entry_price (within 2%)
        entry_val = float(entry_price or 0)
        for ts, p in prices:
            if entry_val > 0 and abs(p - entry_val) / entry_val < 0.02:
                entry_ts = ts
                break

        if entry_ts is None:
            return

        # Slice prices from entry onward
        post_entry = [(ts, p) for ts, p in prices if ts >= entry_ts]
        if len(post_entry) < 2:
            return

        if direction.upper() == 'SHORT':
            # For SHORT: we want price to go DOWN. Bad = price went UP first (counter-move)
            worst_idx = max(range(len(post_entry)), key=lambda i: post_entry[i][1])
            worst_ts, worst_price = post_entry[worst_idx]
            counter_move = (worst_price - entry_val) / entry_val * 100
        else:  # LONG
            # For LONG: we want price to go UP. Bad = price went DOWN first (counter-move)
            worst_idx = min(range(len(post_entry)), key=lambda i: post_entry[i][1])
            worst_ts, worst_price = post_entry[worst_idx]
            counter_move = (entry_val - worst_price) / worst_price * 100

        # Only record if counter-move > 0.5% (small noise doesn't count)
        if counter_move < 0.5:
            print(f"[Loss Analysis] {token} {direction}: no counter-move ({counter_move:.2f}%)")
            return

        # Check how long until the counter-move peak (in minutes)
        counter_minutes = (worst_ts - entry_ts) / 60 if worst_ts > entry_ts else 0

        # Update learning data
        data = _load_wrong_side()
        if key not in data:
            data[key] = {"count": 0, "total_counter_pct": 0.0, "total_minutes": 0, "last_seen": None}

        entry = data[key]
        entry["count"] = entry.get("count", 0) + 1
        entry["total_counter_pct"] = entry.get("total_counter_pct", 0.0) + counter_move
        entry["total_minutes"] = entry.get("total_minutes", 0) + counter_minutes
        entry["last_seen"] = datetime.now(timezone.utc).isoformat()
        entry["avg_counter_pct"] = round(entry["total_counter_pct"] / entry["count"], 2)
        entry["avg_minutes"] = round(entry["total_minutes"] / entry["count"], 1)

        _save_wrong_side(data)
        print(f"[Loss Analysis] WRONG SIDE: {token} {direction} counter-move=+{counter_move:.2f}% "
              f"(took {counter_minutes:.0f}min) | avg now={entry['avg_counter_pct']:.2f}% | n={entry['count']}")

    except Exception as e:
        print(f"[Loss Analysis] Error analyzing {token} {direction}: {e}")


def is_wrong_side_risky(token: str, direction: str, confidence: float = 70) -> Tuple[bool, str]:
    """
    Pre-trade check: should we be more careful entering this token+direction?

    Returns (is_risky, reason_str)
    - True if wrong-side entries are common (>3 occurrences) AND avg counter-move > 1.5%
    - Reduces confidence by 15 pts as a penalty for wrong-side history
    """
    key = f"{token.upper()}:{direction.upper()}"
    data = _load_wrong_side()
    entry = data.get(key, {})

    if not entry:
        return False, ""

    count = entry.get("count", 0)
    avg_pct = entry.get("avg_counter_pct", 0)
    avg_min = entry.get("avg_minutes", 0)

    if count >= 3 and avg_pct >= 1.5:
        reason = f"wrong-side x{count} avg+{avg_pct:.1f}%/{avg_min:.0f}min"
        return True, reason

    return False, ""


# ─── Win Cooldown ────────────────────────────────────────────────────────────────
def _win_cd_key(token: str, direction: str) -> str:
    """Key for win cooldown entries in the cooldown file."""
    return f"WIN:{token.upper()}:{direction.upper()}"


def _set_win_cooldown(token: str, direction: str, minutes: float = WIN_COOLDOWN_MINUTES) -> None:
    """Block re-entry for same token+direction for N minutes after a win."""
    key = _win_cd_key(token, direction)
    expiry = datetime.now(timezone.utc).timestamp() + (minutes * 60)
    data = _load_cooldowns()
    data[key] = {"expires": expiry, "streak": 0}
    _save_cooldowns(data)
    print(f"[Position Manager] WIN COOLDOWN: {token} {direction} blocked for {minutes:.0f}min")


def _is_win_cooldown_active(token: str, direction: str) -> bool:
    """Return True if token+direction is in win cooldown."""
    key = _win_cd_key(token, direction)
    data = _clean_expired(_load_cooldowns())
    return key in data


# ─── Main / Test ──────────────────────────────────────────────────────────────
def main():
    """Test run — print current position state and run management check."""
    print(f"[Position Manager] Starting check at {datetime.now()}")
    print(f"[Position Manager] Connecting to DB: {DB_CONFIG['host']}/{DB_CONFIG['dbname']}")

    # refresh_current_prices() is called inside check_and_manage_positions()
    # Run management check (it calls refresh_current_prices internally)
    print()
    open_n, closed_n, adjusted_n = check_and_manage_positions()
    print(f"\n[Position Manager] Done. Open: {open_n} | Closed: {closed_n} | Adjusted: {adjusted_n}")


if __name__ == "__main__":
    main()
