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

# Pipeline heartbeat file
_PM_HEARTBEAT_FILE = '/var/www/hermes/data/pipeline_heartbeat.json'
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

# ── Cascade Flip Config ──────────────────────────────────────────────────────
# When an open position is losing AND an opposite signal fires with strong conf,
# cascade flip: close the losing position AND enter the opposite direction.

# TODO (2026-04-02): Push trailing SL updates to Hyperliquid.
# Currently position_manager computes the trailing SL and writes it to the brain DB,
# but it never pushes the updated SL order to HL. The guardian only syncs HL → DB
# (PnL, fills, prices) but has no code to push SL modifications back.
# We need to add a call to hyperliquid_exchange to cancel the existing SL order
# and place a new one when the trailing SL moves. This is critical for protecting
# profits on leveraged positions — the local trailing SL fires correctly but the
# remote HL order stays static until manually closed.
# This prevents riding losing trades while the market has already reversed.
CASCADE_FLIP_MIN_LOSS  = -0.5   # Position must be down >= this % to qualify
CASCADE_FLIP_MIN_CONF   = 70.0   # Opposite signal must have conf >= this %
CASCADE_FLIP_MAX_AGE_M  = 15     # Opposite signal must be created within this many minutes
CASCADE_FLIP_MIN_TYPES  = 1      # Opposite signal must have at least this many agreeing signal types

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

# ─── Signal Quality Tracking ──────────────────────────────────────────────────

SIGNAL_DB = '/root/.hermes/data/signals_hermes_runtime.db'

def _ensure_signal_outcomes_table():
    """Create signal_outcomes table if it doesn't exist."""
    import sqlite3
    try:
        conn = sqlite3.connect(SIGNAL_DB)
        c = conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS signal_outcomes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                token TEXT NOT NULL,
                direction TEXT NOT NULL,
                signal_type TEXT NOT NULL,
                is_win INTEGER NOT NULL,
                pnl_pct REAL NOT NULL,
                pnl_usdt REAL NOT NULL,
                confidence REAL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                closed_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        c.execute("""
            CREATE INDEX IF NOT EXISTS idx_sigout_token ON signal_outcomes(token, direction)
        """)
        c.execute("""
            CREATE INDEX IF NOT EXISTS idx_sigout_stype ON signal_outcomes(signal_type)
        """)
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[Position Manager] signal_outcomes table error: {e}")


def get_signal_streak(token: str, direction: str, signal_type: str = None) -> Dict:
    """Get recent win/loss streak and streak-adjusted weight for a signal.

    Returns:
        streak: net wins - losses over last 20 outcomes (positive = hot, negative = cold)
        multiplier: 1.0 base, +0.1 per consecutive win, -0.1 per consecutive loss
                    Cap at 2.0x (very hot) and 0.5x (very cold)
        win_rate_20: win rate over last 20 outcomes
    """
    _ensure_signal_outcomes_table()
    import sqlite3
    conn = sqlite3.connect(SIGNAL_DB)
    c = conn.cursor()
    try:
        base_query = """
            SELECT is_win, pnl_pct FROM signal_outcomes
            WHERE token = ? AND direction = ?
        """
        if signal_type:
            base_query += " AND signal_type = ?"
            params = (token.upper(), direction.upper(), signal_type)
        else:
            params = (token.upper(), direction.upper())

        base_query += " ORDER BY id DESC LIMIT 20"
        c.execute(base_query, params)
        rows = c.fetchall()
        conn.close()

        if not rows:
            return {'streak': 0, 'multiplier': 1.0, 'win_rate_20': 0.5, 'n': 0}

        wins = sum(1 for r in rows if r[0])
        losses = len(rows) - wins
        streak = wins - losses

        # Streak multiplier: consecutive wins/losses at the tail
        # Walk backwards from most recent to find run length
        consecutive = 0
        direction_run = None
        for r in rows:
            if direction_run is None:
                direction_run = r[0]
                consecutive = 1
            elif r[0] == direction_run:
                consecutive += 1
            else:
                break

        # multiplier: +0.1 per consecutive win, -0.1 per consecutive loss, capped [0.5, 2.0]
        if direction_run == 1:  # last outcome was a win
            mult = min(2.0, 1.0 + (consecutive * 0.1))
        else:  # last outcome was a loss
            mult = max(0.5, 1.0 - (consecutive * 0.1))

        return {
            'streak': streak,
            'multiplier': round(mult, 2),
            'win_rate_20': round(wins / len(rows), 3),
            'n': len(rows),
            'consecutive': consecutive,
            'last_was_win': rows[0][0] if rows else None
        }
    except Exception as e:
        print(f"[Position Manager] get_signal_streak error: {e}")
        return {'streak': 0, 'multiplier': 1.0, 'win_rate_20': 0.5, 'n': 0}


def _bridge_signal_history_to_patterns(token: str, direction: str, trade_id: int,
                                       is_win: bool, compact_rounds: int = 0):
    """
    Bridge hot-set signal_history data → brain.trade_patterns.

    When a trade closes with compact_rounds >= 3, record the signal as a
    permanent pattern in brain.trade_patterns so survival knowledge persists
    beyond the 5-minute hot-set window.

    WIN  → positive pattern (survived AI review and turned profitable)
    LOSS → cautionary pattern (survived review but lost — weaker signal)
    """
    if compact_rounds < 3:
        return  # only record patterns from signals that survived >= 3 AI reviews

    try:
        import sqlite3 as _sqlite3
    except ImportError:
        return

    # Read signals from signal_history for this trade_id
    sig_db = '/root/.hermes/data/signals_hermes_runtime.db'
    try:
        conn_sig = _sqlite3.connect(sig_db, timeout=5)
        c_sig = conn_sig.cursor()
        c_sig.execute("""
            SELECT signal_type, compact_round, survived, score_before, score_after, reason
            FROM signal_history
            WHERE trade_id=? AND survived=1
            ORDER BY compact_round DESC
            LIMIT 10
        """, (trade_id,))
        rows = c_sig.fetchall()
        conn_sig.close()
    except Exception as e:
        print(f"[Position Manager] _bridge: failed to read signal_history: {e}")
        return

    if not rows:
        return  # no survival data

    # Write to brain.trade_patterns
    try:
        conn_brain = psycopg2.connect(
            host='/var/run/postgresql', dbname='brain',
            user='postgres', password='postgres'
        )
        cur_brain = conn_brain.cursor()

        for row in rows:
            sig_type, cround, survived, score_b, score_a, reason = row
            # Pattern name: direction + token + signal_type + outcome
            pattern_name = f"survival_{direction.lower()}_{token.lower()}_{sig_type}_{'win' if is_win else 'loss'}"
            is_positive = 1 if is_win else 0

            cur_brain.execute("""
                INSERT INTO trade_patterns
                    (pattern_name, token, side, is_positive, confidence,
                     adjustment, sample_count, reason, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, 1, %s, NOW())
                ON CONFLICT (pattern_name, token) DO UPDATE SET
                    sample_count = trade_patterns.sample_count + 1,
                    is_positive = CASE
                        WHEN trade_patterns.is_positive = 1 THEN 1
                        WHEN trade_patterns.is_positive = 0 AND %s = 1 THEN 1
                        ELSE trade_patterns.is_positive END,
                    confidence = (trade_patterns.confidence * trade_patterns.sample_count + %s)
                                / (trade_patterns.sample_count + 1),
                    updated_at = NOW()
            """, (
                pattern_name, token.upper(), direction.upper(), is_positive,
                0.7 if is_win else 0.4,
                json.dumps({'compact_rounds': cround, 'score_before': score_b,
                            'score_after': score_a, 'survival_reason': reason}),
                is_positive,
                0.7 if is_win else 0.4,
            ))

        conn_brain.commit()
        cur_brain.close()
        conn_brain.close()
        print(f"[Position Manager] _bridge: wrote {len(rows)} patterns for {token} {direction} ({'WIN' if is_win else 'LOSS'})")
    except Exception as e:
        print(f"[Position Manager] _bridge: failed to write to trade_patterns: {e}")


def _record_signal_outcome(token: str, direction: str, pnl_pct: float, pnl_usdt: float,
                            signal_type: str = None, confidence: float = None):
    """Record outcome for a signal type so we can track win/loss streaks."""
    _ensure_signal_outcomes_table()
    import sqlite3
    is_win = 1 if float(pnl_usdt or 0) > 0 else 0
    try:
        conn = sqlite3.connect(SIGNAL_DB)
        c = conn.cursor()
        # Dedup: skip if we already recorded this exact outcome in the last 5 min
        c.execute("""
            SELECT id FROM signal_outcomes
            WHERE token=? AND direction=? AND ABS(pnl_pct - ?) < 0.0001
            AND created_at > datetime('now', '-5 minutes')
        """, (token.upper(), direction.upper(), float(pnl_pct or 0)))
        if c.fetchone():
            print(f"[Signal Quality] Dedup: {signal_type or 'decider'} {direction} {token} "
                  f"already recorded recently, skipping")
            conn.close()
            return
        c.execute("""
            INSERT INTO signal_outcomes
                (token, direction, signal_type, is_win, pnl_pct, pnl_usdt, confidence)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (token.upper(), direction.upper(),
              signal_type or 'decider', is_win,
              float(pnl_pct or 0), float(pnl_usdt or 0), float(confidence or 0)))
        conn.commit()
        conn.close()
        print(f"[Signal Quality] {signal_type or 'decider'} {direction} {token}: "
              f"{'WIN' if is_win else 'LOSS'} (conf={confidence}, pnl={pnl_pct:+.2f}%)")
    except Exception as e:
        print(f"[Position Manager] _record_signal_outcome error: {e}")


# ─── A/B Results Recording ─────────────────────────────────────────────────────

def _record_ab_close(token, direction, pnl_pct, pnl_usdt, experiment, sl_dist, net_pnl=None,
                     signal_type=None, confidence=None):
    """Record trade close to ab_results table + signal_outcomes table.

    experiment can be:
      - A pipe-separated string: "sl-distance-test:SL1pct|entry-timing-test:IMMEDIATE|..."
      - A dict: {'experiment': 'sl-distance-test:SL1pct|...'}
      - A garbled JSON string (old format)

    net_pnl is the true PnL after Hyperliquid fees (0.045% per side on notional).
    Used for win/loss determination if provided.

    signal_type and confidence: if not provided, fetches from trades DB.
    """
    import psycopg2, json, re
    ab_data_present = bool(experiment and experiment != 'None')

    # ── Auto-fetch signal_type and confidence from trades DB if not provided ───
    if signal_type is None or confidence is None:
        try:
            conn_fetch = psycopg2.connect(host='/var/run/postgresql', dbname='brain',
                                          user='postgres', password='Brain123')
            cur_fetch = conn_fetch.cursor()
            cur_fetch.execute(
                "SELECT signal, confidence FROM trades WHERE token=%s AND server='Hermes' "
                "AND status IN ('closed','open') ORDER BY id DESC LIMIT 1",
                (token.upper(),))
            row = cur_fetch.fetchone()
            if row:
                if signal_type is None:
                    signal_type = row[0]  # e.g. 'conf-2s', 'rsi_confluence', etc.
                if confidence is None:
                    confidence = row[1]
            cur_fetch.close()
            conn_fetch.close()
        except Exception as fetch_err:
            print(f"[Position Manager] signal fetch fallback error: {fetch_err}")


    # Use net_pnl for win/loss and recording (or raw pnl_usdt if fees not available)
    record_pnl = net_pnl if net_pnl is not None else pnl_usdt
    is_win = float(record_pnl or 0) > 0

    # ── A/B Results recording — only if we have experiment data ─────────────
    if ab_data_present:
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

        try:
            conn = psycopg2.connect(host='/var/run/postgresql', dbname='brain', user='postgres', password='Brain123')
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

    # ── Signal Outcomes recording — ALWAYS (independent of A/B data) ─────────
    # This feeds the self-learning streak system so even pre-A/B trades contribute
    _record_signal_outcome(token, direction, pnl_pct, pnl_usdt,
                          signal_type=signal_type, confidence=confidence)


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
                exit_reason = %s,
                exit_price = %s,
                pnl_pct = %s,
                pnl_usdt = %s,
                fees = %s,
                is_guardian_close = FALSE,
                hype_realized_pnl_usdt = %s,
                hype_realized_pnl_pct = %s
            WHERE id = %s AND status = 'open'
        """, (now, reason, reason, current_price,
              round(pnl_pct, 4), round(pnl_usdt, 4),
              json.dumps({'entry_fee': round(entry_fee_paid, 6), 'exit_fee': round(exit_fee, 6), 'fee_total': round(fee_total, 6), 'net_pnl': round(net_pnl, 6)}),
              None, None,  # hype_realized_pnl_* will be backfilled after HL confirms
              trade_id))
        if cur.rowcount == 0:
            print(f"[Position Manager] Dedup: trade {trade_id} already closed, skipping")
            conn.rollback()
            return
        # DB UPDATE done — do NOT commit yet. Commit only after HL confirms, or rollback if HL fails.
        print(f"[Position Manager] Closed trade {trade_id} ({reason})")

        # ── Mirror to Hyperliquid (real trade) ───────────────────────
        # Commit DB FIRST, then close on HL. This prevents the worst-case scenario
        # where HL closes but DB rollback leaves them permanently divergent.
        # If DB commit succeeds but HL close fails → hype-sync catches it next run.
        # If DB commit fails → rollback (safe), HL is still open for retry.
        # Capture HL exit info for backfill — but don't let errors prevent DB commit
        hl_exit_info = None
        if HYPE_AVAILABLE and is_live_trading_enabled():
            hype_token = hype_coin(token)
            conn.commit()  # lock in DB close
            try:
                hl_exit_info = mirror_close(hype_token, direction)
                print(f"[Position Manager] HYPE mirror_close SUCCESS: {hype_token}")
            except RuntimeError as me:
                print(f"[Position Manager] HYPE mirror_close FAILED (DB committed, HL still open): {me}")
                print(f"[Position Manager] hype-sync will reconcile on next run")
                hl_exit_info = None
            except Exception as me:
                print(f"[Position Manager] HYPE mirror_close ERROR (DB committed, HL still open): {me}")
                print(f"[Position Manager] hype-sync will reconcile on next run")
                hl_exit_info = None
        elif HYPE_AVAILABLE:
            # Live trading OFF → paper only
            print(f"[Position Manager] Live trading OFF — paper close only (no HL)")
            conn.commit()
        else:
            # No HYPE available at all
            conn.commit()

        # ── Backfill HL ground truth after close ───────────────────
        # mirror_close returns {hl_exit_price, hl_realized_pnl} — backfill these
        # into hype_realized_pnl_* columns so we have ground-truth PnL going forward.
        if hl_exit_info and hl_exit_info.get('hl_realized_pnl') is not None:
            try:
                conn2 = get_db_connection()
                if conn2:
                    cur2 = conn2.cursor()
                    hl_rp = hl_exit_info.get('hl_realized_pnl', 0)
                    hl_ep = hl_exit_info.get('hl_exit_price')
                    # Use stored amount_usdt for pct calculation
                    cur2.execute(
                        "SELECT amount_usdt FROM trades WHERE id=%s",
                        (trade_id,))
                    row = cur2.fetchone()
                    amt = float(row[0] or 50) if row else 50
                    hype_pct = round(hl_rp / amt * 100, 4)
                    cur2.execute("""
                        UPDATE trades SET
                            hype_realized_pnl_usdt = %s,
                            hype_realized_pnl_pct = %s
                        WHERE id=%s
                    """, (round(hl_rp, 4), hype_pct, trade_id))
                    conn2.commit()
                    cur2.close()
                    conn2.close()
                    print(f"[Position Manager] Backfilled HL realized_pnl={hl_rp:+.4f} "
                          f"({hype_pct:+.4f}%) for trade {trade_id}")
            except Exception as e:
                print(f"[Position Manager] HL backfill failed (non-fatal): {e}")

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
        # ── Always record outcome (A/B + signal_outcomes) — single call ─────────
        # _record_ab_close handles both: A/B data if present, signal_outcomes always
        _record_ab_close(token, direction, pnl_pct, pnl_usdt, experiment, sl_dist, net_pnl=net_pnl)

        # ── Bridge signal_history → brain.trade_patterns ─────────────────────────
        # Persist hot-set survival data as permanent knowledge in brain DB.
        # compact_rounds >= 3 means the AI reviewed the signal multiple times
        # and kept it alive — good signal. Record the pattern.
        try:
            import sqlite3 as _sqlite3
            conn_s = _sqlite3.connect('/root/.hermes/data/signals_hermes_runtime.db', timeout=5)
            c_s = conn_s.cursor()
            c_s.execute("""
                SELECT MAX(compact_round) FROM signal_history
                WHERE token=? AND direction=? AND trade_id=? AND survived=1
            """, (token.upper(), direction.upper(), trade_id))
            row_cr = c_s.fetchone()
            conn_s.close()
            compact_rounds_val = row_cr[0] or 0 if row_cr else 0
        except Exception:
            compact_rounds_val = 0
        _bridge_signal_history_to_patterns(token, direction, trade_id, is_win, compact_rounds_val)

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
    trailing_start   = float(trade.get('trailing_activation') or TRAILING_START_PCT_DEFAULT)
    trailing_buffer  = float(trade.get('trailing_distance') or TRAILING_BUFFER_PCT_DEFAULT)
    # Phase 2: tighter trailing once profit doubles from activation threshold
    phase2_dist      = trade.get('trailingPhase2DistancePct')
    phase2_threshold = trailing_start * 2  # phase2 activates at 2x activation profit

    # If not yet activated and profit < threshold → skip activation check
    # pnl_pct is already in percentage (e.g. 1.23 = 1.23%), trailing_start is a fraction (0.01 = 1%)
    if not is_active and pnl_pct < trailing_start:
        return None

    # If trailing is not active yet → don't return a value
    if not is_active:
        return None

    # Trailing is active → always compute current SL regardless of pnl_pct
    # (pnl might dip but the trailing SL from the peak still protects)

    # ── Phase 2: tighten buffer once profit doubles from activation ─────────────
    # Check if phase 2 should activate (and persist to file so it sticks across calls)
    if phase2_dist is not None and not trade_data.get("phase2_activated", False):
        if pnl_pct >= phase2_threshold:
            data[str(trade_id)]["phase2_activated"] = True
            data[str(trade_id)]["phase2_at_pnl"] = pnl_pct
            _save_trailing_data(data)
            trade_data = data.get(str(trade_id), {})

    # Use phase 2 buffer if activated, otherwise phase 1
    active_buffer = float(phase2_dist) if trade_data.get("phase2_activated") and phase2_dist else trailing_buffer

    # Calculate buffer — tighter floor, faster tighten as profit grows.
    # SHORT pnl is positive when in profit (entry > current).
    # Formula: 0.5% at 5% pnl → 0.3% at 15% → 0.2% floor at 25%+.
    # Floor = 0.2% (2x max daily move for most alts, won't stop you out on noise).
    # Tighten rate: every 10% pnl reduces buffer by 0.1%.
    if TRAILING_TIGHTEN:
        tighten_per_10pnl = 0.001  # 0.1% tighter per 10% pnl gained
        buffer_pct = max(0.002, active_buffer - (pnl_pct / 10) * tighten_per_10pnl)
        buffer_pct = max(0.002, buffer_pct)  # 0.2% floor — won't stop on daily noise
    else:
        buffer_pct = active_buffer

    # Track best price
    # best_price from JSON is float; current_price from PostgreSQL may be Decimal
    # (psycopg2 returns numeric/decimal columns as Python Decimal).
    # Always coerce to float for comparison/arithmetic.
    if direction == "LONG":
        best_price = float(trade_data.get("best_price", current_price))
        if float(current_price) > best_price:
            best_price = current_price
            data[str(trade_id)]["best_price"] = best_price
            _save_trailing_data(data)
        trailing_sl = best_price * (1 - buffer_pct)
    elif direction == "SHORT":
        best_price = float(trade_data.get("best_price", current_price))
        if float(current_price) < best_price:
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

    # ── RECONCILIATION OWNED BY GUARDIAN ──────────────────────────────────────
    # DB↔HL reconciliation (orphans/ghosts) is handled exclusively by
    # hl-sync-guardian.py (60s cycle). This function ONLY updates current_price
    # and pnl_pct for positions already confirmed in the DB.
    # Having two processes reconcile independently causes race conditions and
    # duplicate trade records (the orphan_recovery/guardian_missing bug).

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
            # SHORTs activate trailing only when in profit (pnl_pct positive = price moved down).
            # Never activate on loss — cascade_flip handles reversals, cut_loser is the safety net.
            adverse_pct = pnl_pct if direction == 'SHORT' else pnl_pct
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

        # ── 3. Cascade flip (proactive reversal — fires before cut_loser) ────
        # Only fires if trailing is NOT active (don't flip during trailing)
        # and only if position is losing AND an opposite signal exists with conf >= 70%
        cascade_flipped = False
        if not trailing_active and live_pnl <= CASCADE_FLIP_MIN_LOSS:
            flip_info = check_cascade_flip(token, direction, live_pnl)
            if flip_info:
                cascade_flipped = cascade_flip(token, direction, trade_id,
                                               live_pnl, flip_info,
                                               entry=float(pos.get('entry_price') or 0))
                if cascade_flipped:
                    closed_count += 1
                    continue  # Position was flipped — skip remaining checks for this pos

        # ── 4. Cut loser (fallback — only fires if trailing is NOT active) ──
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

    # ── Pipeline heartbeat ─────────────────────────────────────────────────────
    _update_pm_heartbeat()

    return open_count, closed_count, adjusted_count


# ─── Cascade Flip ─────────────────────────────────────────────────────────────
# When an open position is losing and an opposite signal fires, close and reverse.


def check_cascade_flip(token: str, position_direction: str,
                      live_pnl: float) -> Optional[Dict]:
    """
    Check if an open position should be cascade-flipped.

    Trigger: position is losing >= CASCADE_FLIP_MIN_LOSS AND
             an OPPOSITE direction signal exists in the DB with
             conf >= CASCADE_FLIP_MIN_CONF within CASCADE_FLIP_MAX_AGE_M minutes.

    Returns: Dict with flip details {opposite_dir, conf, source, sig_id, price}
             or None if no flip warranted.
    """
    if live_pnl > CASCADE_FLIP_MIN_LOSS:
        return None  # Not losing enough

    opposite_dir = 'SHORT' if position_direction == 'LONG' else 'LONG'

    # Query signals DB for opposite-direction signals
    import sqlite3
    db_path = '/root/.hermes/data/signals_hermes_runtime.db'
    if not os.path.exists(db_path):
        return None

    try:
        conn = sqlite3.connect(db_path, timeout=5)
        c = conn.cursor()
        # First: count distinct signal types agreeing on this direction (confluence)
        c.execute("""
            SELECT COUNT(DISTINCT signal_type)
            FROM signals
            WHERE UPPER(token) = ?
              AND direction = ?
              AND decision IN ('PENDING', 'WAIT')
              AND confidence >= ?
              AND created_at >= datetime('now', ?)
        """, (token.upper(), opposite_dir, CASCADE_FLIP_MIN_CONF,
              f'-{CASCADE_FLIP_MAX_AGE_M} minutes'))
        agreeing_types = c.fetchone()[0]
        if agreeing_types < CASCADE_FLIP_MIN_TYPES:
            conn.close()
            return None

        c.execute("""
            SELECT id, signal_type, source, confidence, price, created_at
            FROM signals
            WHERE UPPER(token) = ?
              AND direction = ?
              AND decision IN ('PENDING', 'WAIT')
              AND confidence >= ?
              AND created_at >= datetime('now', ?)
            ORDER BY confidence DESC, created_at DESC
            LIMIT 1
        """, (token.upper(), opposite_dir, CASCADE_FLIP_MIN_CONF,
              f'-{CASCADE_FLIP_MAX_AGE_M} minutes'))
        row = c.fetchone()
        conn.close()

        if not row:
            return None

        sig_id, sig_type, source, conf, price, created_at = row
        return {
            'opposite_dir': opposite_dir,
            'conf': conf,
            'source': source,
            'sig_id': sig_id,
            'price': price,
            'created_at': created_at,
            'signal_type': sig_type,
        }
    except Exception as e:
        print(f"  [Cascade Flip] DB error checking {token}: {e}")
        return None


def cascade_flip(token: str, position_direction: str, trade_id: int,
                 live_pnl: float, flip_info: Dict,
                 entry_price: float) -> bool:
    """
    Execute a cascade flip: close losing position, enter opposite direction.
    Returns True if both close and new entry succeeded.
    """
    opposite_dir = flip_info['opposite_dir']
    conf = flip_info['conf']
    source = flip_info['source']
    sig_id = flip_info['sig_id']

    print(f"  [CASCADE FLIP] {token} {position_direction}→{opposite_dir} "
          f"(loss={live_pnl:+.2f}%, opp_conf={conf:.1f}%, src={source})")

    # 1. Close the losing position
    close_ok = close_paper_position(trade_id, f"cascade_flip_{live_pnl:+.2f}%")
    if not close_ok:
        print(f"  [CASCADE FLIP] ❌ Failed to close {token} #{trade_id}")
        return False

    # 2. Enter the opposite direction at current price
    from hyperliquid_exchange import place_market_order
    current_price = flip_info['price']
    if not current_price or current_price <= 0:
        try:
            from hyperliquid_exchange import get_price
            current_price = get_price(token)
        except Exception:
            print(f"  [CASCADE FLIP] ❌ Could not get price for {token}")
            return True  # Position closed, new entry failed but not fatal

    ok = place_market_order(
        token=token,
        direction=opposite_dir,
        entry_price=current_price,
        confidence=conf,
        source=f"cascade-{source}",
        trade_id=None,  # new trade
    )

    if ok:
        print(f"  [CASCADE FLIP] ✅ {token} {opposite_dir} entered @ ${current_price:.6f}")
        # Mark the signal that triggered the flip as executed
        try:
            conn = sqlite3.connect('/root/.hermes/data/signals_hermes_runtime.db')
            c = conn.cursor()
            c.execute("UPDATE signals SET decision='EXECUTED', trade_id=? WHERE id=?",
                      (trade_id, sig_id))
            conn.commit()
            conn.close()
        except Exception:
            pass
    else:
        print(f"  [CASCADE FLIP] ⚠️ {token} {opposite_dir} entry failed (position closed)")

    return True


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


def get_opposite_direction_cooldown_hours(token: str, direction: str) -> float:
    """
    Return hours remaining on the OPPOSITE direction's cooldown.
    Used by scanner to boost signals when the opposing trade is about to clear —
    a cooldown clears because the direction was wrong, so the opposite is now
    more likely correct.
    Returns 0.0 if no cooldown or already expired.
    """
    opp_dir = 'SHORT' if direction.upper() == 'LONG' else 'LONG'
    key = f"{token.upper()}:{opp_dir.upper()}"
    data = _load_cooldowns()
    entry = data.get(key)
    if not entry:
        return 0.0
    now = datetime.now(timezone.utc).timestamp()
    if isinstance(entry, dict):
        expires = entry.get("expires", 0)
    else:
        expires = entry  # old float format
    remaining = (expires - now) / 3600.0
    return max(0.0, remaining)


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



def _update_pm_heartbeat():
    """Update pipeline heartbeat for position_manager."""
    try:
        data = {}
        if os.path.exists(_PM_HEARTBEAT_FILE):
            with open(_PM_HEARTBEAT_FILE) as f:
                data = json.load(f)
        data['position_manager'] = {
            "timestamp": datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
            "status": "ok"
        }
        with open(_PM_HEARTBEAT_FILE, 'w') as f:
            json.dump(data, f, indent=2)
    except Exception:
        pass  # never crash on heartbeat failures


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
