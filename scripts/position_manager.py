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
sys.path.insert(0, '/root/.hermes/scripts')
from hermes_file_lock import FileLock
from hermes_constants import (
    MAX_OPEN_POSITIONS,
    ATR_SL_MIN, ATR_SL_MAX, ATR_TP_MIN, ATR_TP_MAX, ATR_TP_K_MULT,
    ATR_SL_MIN_ACCEL, ATR_TP_MIN_ACCEL,
    ATR_SL_MIN_INIT, ATR_SL_MAX_INIT, SL_PCT_FALLBACK, TP_PCT_FALLBACK, STOP_LOSS_DEFAULT,
    ATR_K_LOW_VOL, ATR_K_NORMAL_VOL, ATR_K_HIGH_VOL,
    ATR_PCT_LOW_THRESH, ATR_PCT_HIGH_THRESH,
    PHASE_TIER_NEUTRAL, PHASE_TIER_BUILDING, PHASE_TIER_ACCELERATING,
    PHASE_TIER_EXHAUSTION, PHASE_TIER_EXTREME,
    K_PHASE_ACCEL_STALL, K_PHASE_ACCEL_FAST, K_PHASE_ACCEL_SLOW,
    K_PHASE_EXH_STALL, K_PHASE_EXH_FAST, K_PHASE_EXH_SLOW,
    K_PHASE_EXT_STALL, K_PHASE_EXT_FAST,
    WRONG_SIDE_AVG_PCT_THRESH,
    CASCADE_FLIP_ENABLED,
)
from paths import *
from _secrets import BRAIN_DB_DICT
from signal_schema import record_signal_outcome


import hype_cache as hc

# Speed tracker for stale winner/loser detection
try:
    from speed_tracker import SpeedTracker, get_token_speed
    SPEED_TRACKER = SpeedTracker()
except Exception as e:
    print(f"[Position Manager] SpeedTracker unavailable: {e}")
    SPEED_TRACKER = None

# Speed feature: stale winner/loser exit logic
# Tokens that are in profit but flat for 30+ min should be closed (book profits).
# Tokens that are in loss but flat for 15+ min should be cut (dead positions).
# Sourced from hermes_constants.py — adjust STALE_*, SPEED_HOTSET_WEIGHT there.
from hermes_constants import (
    STALE_WINNER_TIMEOUT_MINUTES, STALE_LOSER_TIMEOUT_MINUTES,
    STALE_WINNER_MIN_PROFIT, STALE_LOSER_MAX_LOSS, STALE_VELOCITY_THRESHOLD,
)

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
DB_CONFIG = BRAIN_DB_DICT
SERVER_NAME = "Hermes"

# Pipeline heartbeat file
_PM_HEARTBEAT_FILE = PIPELINE_HB_FILE
MAX_POSITIONS = MAX_OPEN_POSITIONS

# ─── Thresholds ────────────────────────────────────────────────────────────────
CUT_LOSER_PNL = -2.0   # cut if pnl_pct <= -2.0%
TP_PCT        = 0.08          # 8% fallback target (overridden by ATR-based TP in get_trade_params)
ATR_UPDATE_THRESHOLD_PCT = 0.0015  # only push SL/TP update to HL if delta > 0.15%
SL_PCT = 0.03          # 3% stop loss (cut loser threshold — DEFAULT fallback)
SL_PCT_MIN = 0.01      # minimum SL for any trade
MAX_LEVERAGE = 5

# ─── ATR Internal Close System ─────────────────────────────────────────────────
# Kill switch: disables pushing SL/TP orders to Hyperliquid.
# When False, _execute_atr_bulk_updates() is NOT called from the main loop.
# Hermes self-closes on ATR hits internally and mirrors to HL via market order.
ATR_HL_ORDERS_ENABLED = False

# ── Cascade Flip Kill Switch ─────────────────────────────────────────────────
# ── Cascade Flip Config ──────────────────────────────────────────────────────
# When an open position is losing AND an opposite signal fires with strong conf,
# cascade flip: close the losing position AND enter the opposite direction.

# BUG-8 fix: Push trailing SL updates to Hyperliquid.
# The position_manager computes trailing SL and writes it to brain DB, but the
# actual HL stop-loss order was never updated when trailing tightened.
# cascade flip: close the losing position AND enter the opposite direction.
CASCADE_FLIP_ARM_LOSS        = -0.10  # System ARMED at this loss % (speed check activates)
CASCADE_FLIP_TRIGGER_LOSS   = -0.15  # FLIP fires at this loss % (if armed + speed increasing)
CASCADE_FLIP_HF_TRIGGER_LOSS = -0.15  # Fast flip: high-momentum tokens (speed pctl > 80)
CASCADE_FLIP_MIN_CONF        = 60.0   # Opposite signal must have conf >= this % (lowered from 70)
CASCADE_FLIP_MAX_AGE_M       = 30     # Opposite signal must be created within this many minutes (expanded from 15)
CASCADE_FLIP_MIN_TYPES       = 1     # Opposite signal must have at least this many agreeing signal types
CASCADE_FLIP_MAX             = 3      # Max flips per token (permanent lockout after)
# NOTE: CASCADE_FLIP_POST_TRAIL_PCT removed 2026-04-08 — was only used by deprecated
# trailing stop. Cascade-flip positions will get their own tighter SL management
# when ATR-adaptive TP/SL is extended to cover post-flip scenarios.

# ── MACD-Triggered Cascade Flip ───────────────────────────────────────────────
# Tokens where MACD 1H crossing under signal (while LONG) or crossing over (while SHORT)
# triggers an immediate cascade flip — regardless of PnL.
# These are tokens where we entered at a local peak and MACD confirms reversal.
# Added 2026-04-06 based on TRB/IMX/SOPH/SCR post-mortems.
MACD_CASCADE_FLIP_TOKENS = {'TRB', 'IMX', 'SOPH', 'SCR'}

# cascade_flip lives in its own module (cascade_flip.py) for isolated testing.
# Also import _load_flip_counts (used by check_cascade_flip in this file).
from cascade_flip import cascade_flip, _load_flip_counts


def _get_macd_1h_state(token: str) -> Optional[str]:
    """
    Compute MACD(12,26,9) on 1h candles from Binance public API.
    Returns:
      'cross_under' — MACD line crossed under signal line (bearish, flip LONG → SHORT)
      'cross_over'  — MACD line crossed over signal line (bullish, flip SHORT → LONG)
      'none'         — no crossover on the last 1h candle
      None           — error fetching/computing
    """
    try:
        import requests
        # Fetch 40 × 1h candles (enough for MACD(12,26,9) to stabilize)
        url = f"https://api.binance.com/api/v3/klines?symbol={token}USDT&interval=1h&limit=40"
        resp = requests.get(url, timeout=10)
        if resp.status_code != 200:
            return None
        klines = resp.json()
        if len(klines) < 35:
            return None

        closes = [float(k[4]) for k in klines]  # close prices

        def ema(data, period):
            k = 2 / (period + 1)
            ema_val = data[0]
            for price in data[1:]:
                ema_val = price * k + ema_val * (1 - k)
            return ema_val

        ema_12 = ema(closes, 12)
        ema_26 = ema(closes, 26)
        macd_line = ema_12 - ema_26

        # Need prior MACD for signal line (use last 9 closes before current)
        macd_series = []
        for i in range(26, len(closes)):
            e12 = ema(closes[:i+1], 12)
            e26 = ema(closes[:i+1], 26)
            macd_series.append(e12 - e26)

        if len(macd_series) < 10:
            return None

        signal_line = ema(macd_series[-9:], 9)
        prev_macd = macd_series[-2]
        prev_signal = ema(macd_series[-10:-1], 9) if len(macd_series) >= 10 else macd_series[-2]
        curr_macd = macd_series[-1]

        # Detect crossover
        if prev_macd > prev_signal and curr_macd < signal_line:
            return 'cross_under'
        elif prev_macd < prev_signal and curr_macd > signal_line:
            return 'cross_over'
        return 'none'
    except Exception as e:
        print(f"  [MACD 1H] {token} error: {e}")
        return None


def _speed_increasing(token: str, speed_tracker) -> tuple:
    """
    Check if token's speed/momentum supports flipping.
    Returns (increasing: bool, percentile: float)
    increasing = True if speed_percentile >= 50 (token has momentum)
    """
    if speed_tracker is None:
        return (True, 50.0)  # Fail open: allow flip if no speed data
    try:
        # BUG FIX (2026-04-05): get_speed doesn't exist, should be get_token_speed
        # which returns dict, not tuple. Also add None guard for percentile.
        speed_data = speed_tracker.get_token_speed(token)
        percentile = speed_data.get("speed_percentile", 50)
        if percentile is None:
            percentile = 50
        return (percentile >= 50.0, percentile)
    except Exception:
        return (True, 50.0)  # Fail open


def _get_trigger_threshold(token: str, speed_tracker) -> float:
    """
    Return the flip trigger threshold for this token.
    High momentum (pctl > 80) → tighter threshold (-0.75%).
    Normal momentum (pctl 50-80) → standard threshold (-1.0%).
    """
    _, percentile = _speed_increasing(token, speed_tracker)
    if percentile > 80:
        return CASCADE_FLIP_HF_TRIGGER_LOSS
    return CASCADE_FLIP_TRIGGER_LOSS


# ─── Loss Cooldown Config ─────────────────────────────────────────────────────
# Imported from paths.py (SINGLE SOURCE). Do not redefine inline — import instead.
# This prevents the bug where hl-sync-guardian.py and position_manager.py had
# different values for the same constants, causing get_cooldown to disagree with
# _record_loss_cooldown.
from paths import LOSS_COOLDOWN_FILE, LOSS_COOLDOWN_BASE, LOSS_COOLDOWN_MAX
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
                   trailing_activation, trailing_distance, trailing_phase2_dist,
                   highest_price, lowest_price
            FROM trades
            WHERE status = 'open'
              AND server = %s
              AND (signal IS NULL OR signal NOT IN ('pump_hunter', 'zscore_pump'))
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
    """Count open positions for the given server (excludes pump_hunter and zscore_pump signals)."""
    conn = get_db_connection()
    if conn is None:
        return 0

    try:
        cur = get_cursor(conn)
        cur.execute("""
            SELECT COUNT(*) as cnt FROM trades
            WHERE status = 'open'
              AND server = %s
              AND (signal IS NULL OR signal NOT IN ('pump_hunter', 'zscore_pump'))
        """, (server,))
        row = cur.fetchone()
        return int(row["cnt"]) if row else 0
    except Exception as e:
        print(f"[Position Manager] get_position_count error: {e}")
        return 0
    finally:
        conn.close()


def is_position_open(token: str, server: str = SERVER_NAME) -> bool:
    """Check if token already has an open position (excludes pump_hunter and zscore_pump signals)."""
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
              AND (signal IS NULL OR signal NOT IN ('pump_hunter', 'zscore_pump'))
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


def check_atr_tp_sl_hits(open_positions: List[Dict]) -> List[Dict]:
    """
    Check every open position for ATR TP/SL hit.

    Returns list of dicts with trade_id and hit reason:
      LONG: current_price <= stop_loss  → SL hit
      LONG: current_price >= target     → TP hit
      SHORT: current_price >= stop_loss → SL hit
      SHORT: current_price <= target    → TP hit

    Handles edge cases: missing current_price, missing SL/TP in DB.
    """
    hits = []
    for pos in open_positions:
        token = str(pos.get('token', '')).upper()
        trade_id = pos.get('id')
        direction = str(pos.get('direction', '')).upper()
        current_price = pos.get('current_price')
        stop_loss = pos.get('stop_loss')
        target = pos.get('target')

        if not trade_id or not direction:
            continue
        if direction not in ('LONG', 'SHORT'):
            continue

        # Need a valid current_price to check
        try:
            cur = float(current_price)
            if cur <= 0:
                continue
        except (TypeError, ValueError):
            continue

        # Need both SL and TP set in DB to check ATR hits
        # 0.0 is not a valid SL/TP — treat it as unset
        try:
            sl = float(stop_loss) if stop_loss is not None else None
            tp = float(target) if target is not None else None
        except (TypeError, ValueError):
            continue

        if not sl or not tp:
            continue

        hit = None
        if direction == 'LONG':
            if cur <= sl:
                hit = 'atr_sl_hit'
            elif cur >= tp:
                hit = 'atr_tp_hit'
        elif direction == 'SHORT':
            if cur >= sl:
                hit = 'atr_sl_hit'
            elif cur <= tp:
                hit = 'atr_tp_hit'

        if hit:
            hits.append({
                'trade_id': trade_id,
                'token': token,
                'direction': direction,
                'hit_reason': hit,
                'current_price': cur,
                'stop_loss': sl,
                'target': tp,
            })

    return hits


def check_stale_position(token: str, live_pnl: float, direction: str) -> Tuple[bool, str]:
    """
    SPEED FEATURE: Check if a position should be closed due to being stale.

    Logic: if speed has stalled (speed_percentile in a low range) for 15+ minutes,
    cut the loser. Winners are allowed more time.

    Speed stall is measured by speed_percentile being in bottom third (< ~33)
    AND velocity below threshold — indicates a flat/out-of-trend token.

    Returns: (should_close, reason)
    """
    if SPEED_TRACKER is None:
        return False, ""

    # Speed data already updated once per pipeline run in check_and_manage_positions
    speed_data = SPEED_TRACKER.get_token_speed(token)
    if speed_data is None:
        return False, ""

    vel_5m = speed_data.get('price_velocity_5m', 0)
    speed_pctl = speed_data.get('speed_percentile', 50)  # 0-100
    is_stale = speed_data.get('is_stale', False)
    last_move_at = speed_data.get('last_move_at')

    # ── Speed stall check ───────────────────────────────────────────────────
    # Speed in bottom third (<33) + velocity near zero = stalled
    SPEED_STALL_THRESHOLD = 33  # bottom third of percentile range
    is_stalled = speed_pctl < SPEED_STALL_THRESHOLD and abs(vel_5m) < STALE_VELOCITY_THRESHOLD

    # ── Stale loser: pnl < -1% AND stalled for 15+ min ──────────────────────
    if live_pnl <= STALE_LOSER_MAX_LOSS:
        if is_stalled:
            stale_minutes = 0
            if last_move_at:
                try:
                    last_dt = datetime.fromisoformat(last_move_at.replace('Z', '+00:00'))
                    stale_minutes = int((time.time() - last_dt.timestamp()) / 60)
                except Exception:
                    stale_minutes = 0
            if stale_minutes >= STALE_LOSER_TIMEOUT_MINUTES:  # Cut losers faster
                reason = f"stalled_loser_pnl{live_pnl:+.1f}%_spd{speed_pctl:.0f}_vel{vel_5m:+.3f}%_{stale_minutes}m"
                return True, reason

    # ── Stale winner: pnl > +1% AND stalled for 30+ min ────────────────────
    if live_pnl >= STALE_WINNER_MIN_PROFIT:
        if is_stalled:
            stale_minutes = 0
            if last_move_at:
                try:
                    last_dt = datetime.fromisoformat(last_move_at.replace('Z', '+00:00'))
                    stale_minutes = int((time.time() - last_dt.timestamp()) / 60)
                except Exception:
                    stale_minutes = 0
            if stale_minutes >= STALE_WINNER_TIMEOUT_MINUTES:  # Give winners more time
                reason = f"stalled_winner_pnl{live_pnl:+.1f}%_spd{speed_pctl:.0f}_vel{vel_5m:+.3f}%_{stale_minutes}m"
                return True, reason

    return False, ""


# ─── Trade Operations ─────────────────────────────────────────────────────────

# ─── Signal Quality Tracking ──────────────────────────────────────────────────

SIGNAL_DB = RUNTIME_DB

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
    sig_db = RUNTIME_DB
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
        conn_brain = psycopg2.connect(**BRAIN_DB_DICT)
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
                            signal_type: str = None, confidence: float = None,
                            net_pnl: float = None):
    """Record outcome for a signal type so we can track win/loss streaks.
    
    win/loss is determined by net_pnl if provided (after fees), otherwise gross pnl_usdt.
    """
    _ensure_signal_outcomes_table()
    import sqlite3
    # BUG-42 fix: use net_pnl (after fees) for win/loss classification if available
    record_pnl = net_pnl if net_pnl is not None else pnl_usdt
    is_win = 1 if float(record_pnl or 0) > 0 else 0
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

    # FIX (2026-04-22): Also write loss cooldowns to PostgreSQL so signal_gen's
    # get_cooldown() can find them. get_cooldown() checks JSON FIRST (streak-based)
    # then falls back to PostgreSQL (flat 1h). Writing to both ensures coverage
    # even if JSON is empty/expired or the JSON-only path is bypassed.
    if is_win == 0:  # loss
        set_loss_cooldown(token, direction)


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
            conn_fetch = psycopg2.connect(**BRAIN_DB_DICT)
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
            conn = psycopg2.connect(**BRAIN_DB_DICT)
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

        # ── Also write to ab-tests.jsonl for the dashboard ─────────────────────
        for test_name, variant_id in test_map.items():
            if test_name and variant_id:
                try:
                    from hermes_ab_utils import record_ab_outcome
                    record_ab_outcome(
                        test_name,
                        variant_id,
                        "win" if is_win else "loss",
                        metric_value=float(pnl_pct or 0)
                    )
                except Exception as ab_e:
                    print(f"[Position Manager] ab_utils.record_ab_outcome error: {ab_e}")

    # ── Signal Outcomes recording — ALWAYS (independent of A/B data) ─────────
    # This feeds the self-learning streak system so even pre-A/B trades contribute
    _record_signal_outcome(token, direction, pnl_pct, pnl_usdt,
                          signal_type=signal_type, confidence=confidence,
                          net_pnl=net_pnl)


def close_paper_position(trade_id: int, reason: str) -> bool:
    """Close a paper position via direct SQL UPDATE."""
    reason = reason[:20]  # DB column is VARCHAR(20) — truncate if needed
    conn = get_db_connection()
    if conn is None:
        return False

    try:
        cur = get_cursor(conn)
        now = datetime.now(timezone.utc)

        # Fetch trade details before closing
        cur.execute("""
            SELECT token, direction, entry_price, current_price,
                   pnl_pct, experiment, sl_distance, amount_usdt, signal
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
        signal_type = row['signal']  # fallback for record_signal_outcome

        # BUG-FIX (2026-04-19): 'confidence' was never fetched in this function scope
        # causing "name 'confidence' is not defined" errors in record_signal_outcome.
        # Fix: fetch confidence from the trades table alongside signal_type.
        try:
            cur.execute("SELECT confidence FROM trades WHERE id = %s", (trade_id,))
            conf_row = cur.fetchone()
            confidence = float(conf_row['confidence'] or 0) if conf_row and conf_row['confidence'] else None
        except Exception:
            confidence = None

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
        # pnl_pct = raw % price change (e.g., 10 = 10% move)
        # pnl_usdt = amount_usdt * |pnl_pct|/100 (proportional to actual capital, NO leverage)
        # NOTE: leverage is already embedded in the % change when using notional PnL from HL,
        # but here pnl_pct is raw market return so we don't double-apply leverage.
        if direction == 'LONG':
            pnl_pct = ((current_price - entry_price) / entry_price * 100) if entry_price > 0 else 0
        else:
            pnl_pct = ((entry_price - current_price) / entry_price * 100) if entry_price > 0 else 0
        pnl_usdt = amount_usdt * (abs(pnl_pct) / 100) * (1 if pnl_pct >= 0 else -1)
        pnl_usdt_val = float(pnl_usdt or 0)

        # Net PnL after fees
        net_pnl = pnl_usdt_val - fee_total

        # ── Trigger loss cooldown (incremental: 2h → 4h → 8h per consecutive loss) ──
        # FIX (2026-04-05): if pnl_usdt is 0 but reason contains a realized PnL%
        # (e.g. "trailing_exit_-0.55%"), use that to determine loss/win.
        # close_paper_position() uses current_price which may have reverted to entry
        # by the time the exit is processed, losing the realized PnL info.
        if pnl_usdt_val == 0 and reason:
            import re
            m = re.search(r'([+-]\d+\.\d+)%', reason)
            if m:
                pnl_pct_from_reason = float(m.group(1))
                # pnl_pct_from_reason is the realized pnl% at time of exit
                pnl_usdt_val = amount_usdt * (abs(pnl_pct_from_reason) / 100) * (1 if pnl_pct_from_reason >= 0 else -1)
                pnl_pct = pnl_pct_from_reason  # also correct the stored pnl_pct
                # BUG-49 fix: net_pnl must be kept in sync after reason override
                net_pnl = pnl_usdt_val - fee_total
        is_loss = pnl_usdt_val < 0
        if is_loss:
            set_loss_cooldown(token, direction)
            # Post-mortem: if we lost on a direction, was the market moving against us first?
            _analyze_loss_direction(token, direction, entry_price, current_price)

        # ── Trigger win: clear loss streak since WIN confirms this was the right direction ──
        is_win = pnl_usdt_val > 0
        if is_win and LOSS_STREAK_RESET_WIN:
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
              round(pnl_pct, 4), round(pnl_usdt_val, 4),
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

            # ── Best-effort HL order cleanup for ATR hits ─────────────────────
            # If closing due to ATR SL/TP hit, cancel any stale HL trigger orders
            # so they don't fire after the position is already closed.
            # This is best-effort: failures don't block the mirror_close.
            if reason in ('atr_sl_hit', 'atr_tp_hit'):
                try:
                    from hyperliquid_exchange import cancel_all_open_orders as _cancel_all
                    cleanup = _cancel_all(hype_token)
                    if cleanup.get('cancelled'):
                        print(f"  [ATR CLEANUP] Cancelled {len(cleanup['cancelled'])} stale HL orders for {hype_token}")
                    if cleanup.get('errors'):
                        for e in cleanup['errors']:
                            print(f"  [ATR CLEANUP] Warning: {e}")
                except Exception as cleanup_err:
                    print(f"  [ATR CLEANUP] Failed to cancel stale orders for {hype_token}: {cleanup_err}")

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

        # ── Signal outcomes via signal_schema (with real PnL) ────────────────────
        # Use net_pnl (after fees) as the authoritative PnL for the outcomes table
        actual_pnl_usdt = net_pnl if net_pnl is not None else pnl_usdt_val
        actual_pnl_pct = (actual_pnl_usdt / amount_usdt * 100) if amount_usdt > 0 else pnl_pct
        try:
            record_signal_outcome(
                token=token,
                direction=direction,
                pnl_pct=round(actual_pnl_pct, 4),
                pnl_usdt=round(actual_pnl_usdt, 4),
                signal_type=signal_type or 'decider',
                confidence=confidence
            )
        except Exception as rso_err:
            print(f"[Position Manager] record_signal_outcome error (non-fatal): {rso_err}")

        # ── Bridge signal_history → brain.trade_patterns ─────────────────────────
        # Persist hot-set survival data as permanent knowledge in brain DB.
        # compact_rounds >= 3 means the AI reviewed the signal multiple times
        # and kept it alive — good signal. Record the pattern.
        try:
            import sqlite3 as _sqlite3
            conn_s = _sqlite3.connect(RUNTIME_DB, timeout=5)
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
# ATR-based SL for position_manager internal use.
# Imports the same ATR engine from decider-run (shared module-level cache).

def _pm_get_atr(token: str, period: int = 14, interval: str = '15m') -> float | None:
    """
    Fetch ATR(14) for token. Reuses _ATR_CACHE from decider-run if available
    via module-level cache. Falls back to direct HL API call.
    Default interval: 15m (intraday feel vs 1h swing-trade).
    """
    import time as _time
    _ATR_TTL = 300

    # Try local atr_cache.json (shared file, no decider_run dependency)
    try:
        cache_file = ATR_CACHE_FILE
        if _os.path.exists(cache_file):
            with open(cache_file) as f:
                data = _json.load(f)
            entry = data.get(token.upper(), {})
            atr_val = entry.get('atr')
            ts = entry.get('ts', 0)
            if atr_val is not None and (_time.time() - ts) < _ATR_TTL:
                return float(atr_val)
    except Exception:
        pass

    # Direct fetch
    try:
        from hyperliquid.info import Info
        info = Info('https://api.hyperliquid.xyz', skip_ws=True)
        now = _time.time()
        end_t = int(now * 1000)
        # 15m candles: each interval = 15min = 15*60*1000 ms
        start_t = end_t - (15 * 60 * 1000 * (period + 5))
        candles = info.candles_snapshot(token.upper(), interval, start_t, end_t)
        if not candles or len(candles) < period + 1:
            return None
        trs = []
        for i in range(1, min(period + 1, len(candles))):
            high = float(candles[i]['h'])
            low  = float(candles[i]['l'])
            prev_close = float(candles[i - 1]['c'])
            tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
            trs.append(tr)
        return sum(trs) / len(trs) if trs else None
    except Exception:
        return None


# ─── ATR-Adaptive TP/SL ────────────────────────────────────────────────────

def _atr_multiplier(atr_pct: float) -> float:
    """Canonical k multiplier — must match decider_run._atr_multiplier."""
    if atr_pct < ATR_PCT_LOW_THRESH:
        return ATR_K_LOW_VOL    # LOW_VOLATILITY: tight SL for stable tokens
    elif atr_pct > ATR_PCT_HIGH_THRESH:
        return ATR_K_HIGH_VOL   # HIGH_VOLATILITY: wide SL for volatile tokens
    else:
        return ATR_K_NORMAL_VOL  # NORMAL_VOLATILITY: balanced


def _dr_atr(token: str, atr_pct: float) -> float:
    """Local proxy — uses _atr_multiplier from this module (no decider_run dependency)."""
    return _atr_multiplier(atr_pct)


def _atr_sl_k_scaled(
    token: str,
    direction: str,
    atr_pct: float,
    speed_percentile: float = 50,
    momentum_stats: dict = None,
) -> float:
    """
    Scale k_SL by z-score exhaustion + velocity stall + speed.
    Returns k multiplier to apply on top of base _dr_atr().
    momentum_stats: from get_momentum_stats(token) — {percentile_long, percentile_short, velocity, phase}
    """
    from signal_gen import PHASE_BUILDING, PHASE_ACCELERATING, PHASE_EXHAUSTION, PHASE_EXTREME, detect_phase

    base_k = _dr_atr(token, atr_pct)

    if momentum_stats is None:
        return base_k  # can't assess — no change

    phase_str = momentum_stats.get('phase', 'neutral')
    velocity = momentum_stats.get('velocity', 0)

    # Direction-aware percentile — use LONG/SHORT specific pct for phase classification
    if direction == 'LONG':
        pct = momentum_stats.get('percentile_long', 50)
    else:
        pct = momentum_stats.get('percentile_short', 50)

    # FIX (2026-04-28): phase was computed from OVERALL percentile in get_momentum_stats
    # (percentile=1.1 → 'quiet'), ignoring direction-specific conviction (percentile_long=95.5).
    # Re-compute phase using DIRECTION-SPECIFIC percentile so LONG conviction drives tight k.
    phase = detect_phase(pct, velocity)

    # Phase tier map (string -> int for comparison)
    PHASE_TIER = {
        'neutral':     PHASE_TIER_NEUTRAL,
        'building':    PHASE_TIER_BUILDING,
        'accelerating':PHASE_TIER_ACCELERATING,
        'exhaustion':  PHASE_TIER_EXHAUSTION,
        'extreme':     PHASE_TIER_EXTREME,
    }
    phase_tier = PHASE_TIER.get(phase, PHASE_TIER_NEUTRAL)

    # Velocity stall: negative velocity at accelerating+ phase = tired
    stalling = (velocity < 0) and (phase_tier >= PHASE_TIER_ACCELERATING)

    # Phase-based multiplier — TIGHT: first candle against us, we're out
    if phase_tier < PHASE_TIER_ACCELERATING:
        return base_k  # neutral/building — no change
    elif phase_tier == PHASE_TIER_ACCELERATING:
        # ACCELERATING: first candle against us, OUT. mult < 1.0 = tighter SL.
        # ATR% is the only stop we need — floor is the hard floor.
        if stalling:
            mult = K_PHASE_ACCEL_STALL  # stalling + accelerating = momentum fading, snap out
        elif speed_percentile >= 70:
            mult = K_PHASE_ACCEL_FAST   # fast momentum but first reversal = out
        else:
            mult = K_PHASE_ACCEL_SLOW   # low speed = no room needed, stay tight
    elif phase_tier == PHASE_TIER_EXHAUSTION:
        # EXHAUSTION: still tight — 1.25-1.5× only
        if stalling:
            mult = K_PHASE_EXH_STALL    # stalling exhaustion = snap out faster
        elif speed_percentile >= 70:
            mult = K_PHASE_EXH_FAST     # fast momentum
        else:
            mult = K_PHASE_EXH_SLOW     # slow momentum
    else:
        # EXTREME: 1.5× max
        if stalling:
            mult = K_PHASE_EXT_STALL   # stalling extreme
        else:
            mult = K_PHASE_EXT_FAST     # fast extreme

    return base_k * mult


def _force_fresh_atr(token: str, period: int = 14, interval: str = '15m') -> float | None:
    """
    Get ATR for a token. Reads from local atr_cache.json FIRST (no rate limits).
    If cache is stale (>300s), fetches from HL API.
    If HL fails (rate-limited) AND no cache exists, falls back to Binance public API.
    Saved ATR values are in dollar terms (converted from Binance quote currency).
    This makes position_manager the authoritative ATR writer (every 1 min via pipeline).
    Default interval: 15m (intraday feel vs 1h swing-trade).
    """
    import time as _time
    import json as _json
    import os as _os
    import requests as _requests

    cache_file = ATR_CACHE_FILE
    cache_key = token.upper()
    _STALE_MAX = 3600  # accept cache up to 1h old as fallback during rate limiting

    # 1. Try persistent cache first
    stale_cached_atr = None
    try:
        if _os.path.exists(cache_file):
            with open(cache_file) as f:
                data = _json.load(f)
            entry = data.get(cache_key, {})
            atr_val = entry.get('atr')
            ts = entry.get('ts', 0)
            age = _time.time() - ts
            if atr_val is not None and age < 300:
                return float(atr_val)  # fresh cache — return immediately
            elif atr_val is not None and age < _STALE_MAX:
                stale_cached_atr = float(atr_val)  # save for fallback below
    except Exception:
        pass

    # 2. Cache miss or stale — fetch from HL API
    atr = None
    try:
        from hyperliquid.info import Info
        info = Info('https://api.hyperliquid.xyz', skip_ws=True)
        now = _time.time()
        end_t = int(now * 1000)
        start_t = end_t - (15 * 60 * 1000 * (period + 5))
        candles = info.candles_snapshot(token.upper(), interval, start_t, end_t)
        if candles and len(candles) >= period + 1:
            trs = []
            for i in range(1, min(period + 1, len(candles))):
                high = float(candles[i]['h'])
                low  = float(candles[i]['l'])
                prev_close = float(candles[i - 1]['c'])
                tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
                trs.append(tr)
            atr = sum(trs) / len(trs) if trs else None
    except Exception:
        pass  # HL failed

    # 3. No ATR from HL AND no stale cache — try Binance public API
    if atr is None and stale_cached_atr is None:
        try:
            # Binance klines: interval mapping
            binance_interval = '15m'  # maps directly to Binance
            url = (f"https://api.binance.com/api/v3/klines"
                   f"?symbol={token.upper()}USDT&interval={binance_interval}&limit={period + 1}")
            resp = _requests.get(url, timeout=10)
            if resp.status_code == 200:
                klines = resp.json()
                if klines and len(klines) >= period + 1:
                    trs = []
                    for i in range(1, min(period + 1, len(klines))):
                        high = float(klines[i][2])   # high price
                        low  = float(klines[i][3])   # low price
                        prev_close = float(klines[i - 1][4])  # previous close
                        tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
                        trs.append(tr)
                    atr = sum(trs) / len(trs) if trs else None
                    if atr is not None:
                        print(f"  [ATR] {token}: Binance ATR={atr:.4f} ({atr/float(klines[-1][4])*100:.2f}%)")
        except Exception:
            pass  # Binance also failed

    # 4. Save to atr_cache.json
    if atr is not None:
        try:
            file_data = {}
            if _os.path.exists(cache_file):
                with open(cache_file) as f:
                    file_data = _json.load(f)
            file_data[cache_key] = {'atr': atr, 'ts': _time.time()}
            _os.makedirs(os.path.dirname(cache_file), exist_ok=True)
            with open(cache_file, 'w') as f:
                _json.dump(file_data, f)
        except Exception:
            pass

    # 5. Return fresh ATR if available, otherwise fall back to stale cache
    if atr is not None:
        return atr
    if stale_cached_atr is not None:
        try:
            if _os.path.exists(cache_file):
                with open(cache_file) as f:
                    data = _json.load(f)
                ts = data.get(cache_key, {}).get('ts', 0)
                age = _time.time() - ts
                print(f"  [ATR] {token}: using stale cache (age={age:.0f}s)")
        except Exception:
            pass
        return stale_cached_atr

    return None

def _compute_dynamic_sl(token: str, direction: str, entry_price: float,
                        current_price: float,
                        sl_pct_fallback: float = SL_PCT_FALLBACK) -> float:
    """
    Compute dynamic trailing SL using ATR(14). Same formula used by decider_run and guardian.
    ATR-based SL replaces fixed % SL. Falls back to sl_pct_fallback if ATR unavailable.

    Trailing behavior:
      LONG  → SL starts at entry - k·ATR, trails DOWN as price rises (locks in profit)
      SHORT → SL starts at entry + k·ATR, trails DOWN as price falls (locks in profit)

    SL is always on the profitable side of current price.
    """
    atr = _force_fresh_atr(token)
    if atr is None:
        if direction == 'LONG':
            return current_price * (1 - sl_pct_fallback)
        else:
            return current_price * (1 + sl_pct_fallback)

    atr_pct = atr / current_price
    k = _atr_multiplier(atr_pct)
    atr_distance = k * atr

    effective_sl_pct = max(atr_distance / current_price, ATR_SL_MIN)
    effective_sl_pct = min(effective_sl_pct, ATR_SL_MAX)

    if direction == 'LONG':
        # SL = entry - k·ATR, never above current price (catches drops)
        sl = entry_price * (1 - effective_sl_pct)
        return min(sl, current_price * (1 - ATR_SL_MIN))
    else:
        # SHORT: SL trails ABOVE current price as it falls (locks in profit)
        # SL = current_price + ATR_SL_MIN buffer — tight trailing for acceleration phase
        # The buffer is relative to current price, so as price falls, SL falls too
        return current_price * (1 + ATR_SL_MIN)


def _compute_dynamic_tp(token: str, direction: str, entry_price: float,
                        current_price: float,
                        tp_pct_fallback: float = TP_PCT_FALLBACK) -> float:
    """
    Compute dynamic TP using ATR(14). Same formula used by decider_run and guardian.
    TP = current_price ± (k_tp * ATR(14)) where k_tp = k * ATR_TP_K_MULT (1.25).
    """
    atr = _force_fresh_atr(token)
    if atr is None:
        if direction == 'LONG':
            return current_price * (1 + tp_pct_fallback)
        else:
            return current_price * (1 - tp_pct_fallback)

    atr_pct = atr / current_price
    k = _atr_multiplier(atr_pct)
    k_tp = k * ATR_TP_K_MULT  # TP tighter — book profit, don't let it ride
    atr_distance_tp = k_tp * atr

    effective_tp_pct = max(atr_distance_tp / current_price, ATR_TP_MIN)
    effective_tp_pct = min(effective_tp_pct, ATR_TP_MAX)

    if direction == 'LONG':
        return current_price * (1 + effective_tp_pct)
    else:
        return current_price * (1 - effective_tp_pct)


def _collect_atr_updates(open_positions: List[Dict]) -> List[Dict]:
    """
    Collect all open positions (excluding cascade-flip) whose SL or TP has drifted
    > ATR_UPDATE_THRESHOLD_PCT from current ATR.

    Called once per cycle after the main position loop.
    Returns list of update dicts:
      {trade_id, token, direction, entry_price,
       old_sl, new_sl, old_tp, new_tp,
       needs_sl, needs_tp, atr, atr_pct, k}
    """
    if not open_positions:
        return []

    # Deduplicate tokens — one ATR fetch per unique token
    tokens_seen: Dict[str, float | None] = {}
    for pos in open_positions:
        token = str(pos.get('token', '')).upper()
        if token and token not in tokens_seen:
            atr = _force_fresh_atr(token)
            tokens_seen[token] = atr

    # Fetch momentum and speed for each unique token once (dedup like ATR)
    momentum_by_token: Dict[str, Any] = {}
    speed_by_token: Dict[str, float] = {}
    for pos in open_positions:
        token = str(pos.get('token', '')).upper()
        if token and token not in momentum_by_token:
            try:
                from signal_gen import get_momentum_stats
                ms = get_momentum_stats(token)
                momentum_by_token[token] = ms
            except Exception:
                momentum_by_token[token] = None
        if token and token not in speed_by_token:
            try:
                sd = SPEED_TRACKER.get_token_speed(token) if SPEED_TRACKER else None
                speed_by_token[token] = sd.get('speed_percentile', 50) if sd else 50
            except Exception:
                speed_by_token[token] = 50

    # P2 FIX (2026-04-19): Re-read peak prices from DB to ensure _collect_atr_updates
    # always has fresh values. The in-memory pos dict might not have been refreshed
    # with the latest persisted values from the previous cycle's
    # refresh_current_prices() call.
    _peak_cache: Dict[int, tuple] = {}
    try:
        _conn_peak = get_db_connection()
        if _conn_peak:
            _cur_peak = _conn_peak.cursor()
            _trade_ids = [p.get('id') for p in open_positions if p.get('id')]
            if _trade_ids:
                _placeholders = ','.join(['%s'] * len(_trade_ids))
                _cur_peak.execute(
                    f"SELECT id, highest_price, lowest_price FROM trades WHERE id IN ({_placeholders}) AND status = 'open'",
                    _trade_ids
                )
                for _row in _cur_peak.fetchall():
                    _peak_cache[int(_row[0])] = (_row[1], _row[2])
            _cur_peak.close()
            _conn_peak.close()
    except Exception:
        pass

    updates = []
    for pos in open_positions:
        token = str(pos.get('token', '')).upper()
        direction = str(pos.get('direction', '')).upper()
        entry_price = float(pos.get('entry_price') or 0)
        current_price = float(pos.get('current_price') or 0)
        trade_id = pos.get('id')
        current_sl = float(pos.get('stop_loss') or 0)
        current_tp = float(pos.get('target') or 0)
        source = str(pos.get('source') or '')

        # P2 FIX: use DB-cached peak prices to ensure trailing SL is accurate
        if trade_id and trade_id in _peak_cache:
            _db_high, _db_low = _peak_cache[trade_id]
            pos['highest_price'] = float(_db_high) if _db_high else 0
            pos['lowest_price'] = float(_db_low) if _db_low else 0

        # ── Post-flip eviction check: if token was recently flipped, use k=1.0
        # (tightest possible — the flip entry was at a known bad moment, cut fast)
        flip_k_override = None
        try:
            from cascade_flip_helpers import is_token_evicted
            if is_token_evicted(token):
                flip_k_override = 1.0
                print(f"  [ATR] {token}: post-flip eviction active — forcing k=1.0")
        except Exception:
            pass

        if not token or not trade_id:
            continue

        atr = tokens_seen.get(token)
        if atr is None:
            continue

        # ── Resolve effective entry price ─────────────────────────────────────────
        # If entry_price is 0/None (stale DB entry), use current_price from the
        # already-refreshed position dict (refresh_current_prices fetches live HL data
        # and also patches entry_price in-memory when DB entry was 0).
        _entry = entry_price
        if not _entry or float(_entry) <= 0:
            if current_price and float(current_price) > 0:
                _entry = float(current_price)
                print(f"  [ATR] {token}: used current_price {_entry:.6f} as entry (DB entry was 0/None)")
            else:
                continue

        # ── Compute ATR-based SL/TP ───────────────────────────────────────────────
        # atr_pct is calculated from effective entry (not current price)
        atr_pct = atr / _entry
        momentum = momentum_by_token.get(token)
        speed_pctl = speed_by_token.get(token, 50)
        k = _atr_sl_k_scaled(token, direction, atr_pct, speed_pctl, momentum)
        if flip_k_override is not None:
            k = flip_k_override
        sl_pct = k * atr_pct
        tp_pct = k * ATR_TP_K_MULT * atr_pct  # canonical: momentum-scaled k × 1.25 × atr_pct

        # BUG FIX: clamp sl_pct to ATR_SL_MAX_INIT on initial SL set (when current_sl is 0/None).
        # Un-clamped sl_pct bypasses hermes_constants SL caps (ATR_SL_MAX=2.0%) entirely.
        # Phase-tier k multipliers (0.05-0.25) provide tightening; this clamp is the hard ceiling.
        if not current_sl or float(current_sl) <= 0:
            sl_pct = min(sl_pct, ATR_SL_MAX_INIT)

        # ── Trailing SL anchor: use peak price instead of current price ────────────
        # For SHORT: lowest_price seen since entry (SL trails DOWN from the short's best price)
        # For LONG:  highest_price seen since entry (SL trails UP from the long's best price)
        # This implements proper trailing — SL only moves in profit direction.
        _peak_high = float(pos.get('highest_price') or 0) or 0
        _peak_low  = float(pos.get('lowest_price')  or 0) or 0
        if direction == "SHORT":
            # SHORT wins when price falls — use the lowest price seen as profit anchor
            ref_price = _peak_low if _peak_low > 0 else (current_price if (current_price and float(current_price) > 0) else _entry)
        elif direction == "LONG":
            # LONG wins when price rises — use the highest price seen as profit anchor
            ref_price = _peak_high if _peak_high > 0 else (current_price if (current_price and float(current_price) > 0) else _entry)
        else:
            ref_price = current_price if (current_price and float(current_price) > 0) else _entry
        if not ref_price or float(ref_price) <= 0:
            continue

        # ── New-trade gate: give fresh PROFITABLE positions breathing room ───────────
        # If peak price == entry price AND position is in profit, the trade just opened
        # with no real candle formed yet. Applying phase-acceleration multipliers
        # (k=0.05–0.25) squeezes the SL to near-zero. Use base_k + INIT floor instead.
        #
        # IMPORTANT: If the trade is ALREADY underwater, let the phase multiplier tighten.
        # is_new_trade=True without profit check caused SL to be set below entry
        # (worst-case: base_k=1.250, MIN_SL=0.50% floor → SL = entry-0.50% < entry).
        _entry_f = float(_entry)
        _pnl_pct = float(pos.get('pnl_pct', 0) or 0)
        _in_profit = _pnl_pct > 0
        is_new_trade = False
        if _in_profit:
            if direction == "LONG" and _peak_high > 0 and abs(_peak_high - _entry_f) / _entry_f < 0.001:
                is_new_trade = True
            elif direction == "SHORT" and _peak_low > 0 and abs(_peak_low - _entry_f) / _entry_f < 0.001:
                is_new_trade = True

        if is_new_trade:
            k = _dr_atr(token, atr_pct)  # use base k — no acceleration squeeze
            sl_pct = k * atr_pct
            MIN_SL_PCT_TRAILING = ATR_SL_MIN_INIT  # 0.50% floor for new trades
            MIN_TP_PCT_TRAILING = ATR_TP_MIN        # 0.75% floor for new trades
        else:
            # Established trade: acceleration-phase logic applies
            MIN_SL_PCT_TRAILING = ATR_SL_MIN_ACCEL  # 0.20% floor — first candle against us, out
            MIN_TP_PCT_TRAILING = ATR_TP_MIN_ACCEL  # 0.50% floor — book profit fast

        # Enforce minimum SL/TP percentages to prevent razor-thin stops on low-vol tokens.
        effective_sl_pct = max(sl_pct, MIN_SL_PCT_TRAILING)
        effective_tp_pct = max(tp_pct, MIN_TP_PCT_TRAILING)

        if direction == "LONG":
            new_sl = round(ref_price * (1 - effective_sl_pct), 8)
            new_tp = round(ref_price * (1 + effective_tp_pct), 8)
        elif direction == "SHORT":
            # SHORT: SL = ref_price + ATR buffer (trailing from lowest trough)
            # _peak_low = lowest price seen (best price for SHORT = max profit)
            # As price falls to new lows, _peak_low drops → SL drops (tightens from below)
            # As price bounces, _peak_low stays fixed → SL stays fixed (doesn't chase)
            # Uses effective_sl_pct (ATR-scaled) not raw MIN_SL_PCT_TRAILING constant
            new_sl = round(ref_price * (1 + effective_sl_pct), 8)
            new_tp = round(ref_price * (1 - effective_tp_pct), 8)
        else:
            continue

        # INIT-to-ACCEL migration: save the ORIGINAL new_sl (INIT-floor wide value) BEFORE
        # the tighten gate below modifies new_sl in place with current_sl.
        # This is the value we want to write to DB when migrating stale accel-floor SLs.
        _atr_computed_new_sl = new_sl  # always use this for migration writes

        # Debug: log computed ATR levels for monitoring
        print(f"  [ATR] {token}: k={k:.3f} ATR={atr:.4f} ({atr_pct*100:.2f}%) → SL={new_sl:.6f} TP={new_tp:.6f} [ref={ref_price:.6f}]")

        # ── Trailing TP: only tighten, never loosen ─────────────────────────────
        #
        # GOLDEN RULE: TP can only move in the PROFIT direction.
        #
        # LONG:  TP only increases  (higher = further from entry = more profit locked)
        # SHORT: TP only decreases  (lower = further from entry = more profit locked)
        #
        # Implementation: compute new TP from current price, then ONLY apply it
        # if it's better than the current TP. This handles SHORT TP loosening correctly:
        # price drops to 0.36 → TP=0.349 (locked). Price bounces to 0.38 → TP would be
        # 0.368, but that's LOOSER than 0.349 so we keep 0.349. Position stays on.
        #
        needs_sl = False
        needs_tp = False
        if direction == "LONG":
            # new_sl = ref_price * (1 - effective_sl_pct) — already computed above
            # SL tightens as price rises: higher SL = closer to current price = more locked in.
            # Only tighten: accept if new_sl > current_sl (higher = tighter).
            if current_sl > 0:
                if new_sl > current_sl:
                    needs_sl = True      # ATR tightens — accept
                else:
                    new_sl = current_sl  # would loosen — keep current
                    needs_sl = False
            else:
                needs_sl = True

            # TP: compute from current price, only raise if it would improve (higher)
            # TP = price × (1 + tp_pct)  — as price rises, TP rises (numerically higher)
            if current_tp > 0:
                tp_at_ref = round(ref_price * (1 + tp_pct), 8)
                # For LONG: higher TP = more profit locked. If ATR would raise TP (tighten), update.
                # Only block if ATR would lower the TP (loosen).
                if tp_at_ref < current_tp:
                    new_tp = current_tp    # ATR would loosen — keep current
                    needs_tp = False
                else:
                    new_tp = tp_at_ref      # ATR tightens (higher) — update
                    needs_tp = True
            else:
                needs_tp = True

        elif direction == "SHORT":
            # SL trailing: new_sl = ref_price * (1 + effective_sl_pct)
            # ref_price = _peak_low (lowest seen) — SHORT's profit anchor.
            # As price falls to new lows: ref_price drops → SL drops (tightens from below).
            # As price bounces: ref_price stays fixed → SL stays fixed (no chase).
            # Only accept if new_sl < current_sl (tightening). Block if >= (loosening).
            if current_sl > 0:
                if new_sl >= current_sl:
                    new_sl = current_sl    # would loosen — block it
                    needs_sl = False
                else:
                    needs_sl = True        # new_sl < current_sl — tighten, accept
            else:
                needs_sl = True

            # TP: ONLY decrease — never loosen a SHORT TP.
            # Compute TP from current price, but only accept if it's LOWER (better).
            # Price drops to 0.36:  TP=0.36×0.968=0.3488 (tightened from entry)
            # Price bounces to 0.38: TP=0.38×0.968=0.3680 — but 0.3680 > 0.3488
            #                         → TP would LOOSEN → KEEP 0.3488 instead.
            if current_tp > 0:
                tp_at_ref = round(ref_price * (1 - effective_tp_pct), 8)
                if tp_at_ref >= current_tp:
                    new_tp = current_tp    # would loosen (not lower) — KEEP locked TP
                    needs_tp = False
                else:
                    new_tp = tp_at_ref     # would tighten (lower) — update
                    needs_tp = True
            else:
                # First time setting TP — compute from current (entry) price
                # Use effective_tp_pct (floor-enforced) not raw tp_pct
                new_tp = round(ref_price * (1 - effective_tp_pct), 8)
                needs_tp = True

        # ── Force-write conditions (bypass delta gate for stale/missing values) ──────
        # If current SL/TP is 0 or None, this is a stale/missing entry — always write.
        sl_stale = not current_sl or float(current_sl) <= 0
        tp_stale = not current_tp or float(current_tp) <= 0

        # INIT-to-ACCEL migration: detect stale accel-floor SLs on new trades
        # BEFORE the tighten gate below modifies new_sl in place with current_sl.
        INIT_TO_ACCEL_MIGRATION = False
        if is_new_trade and not sl_stale and current_sl and float(current_sl) > 0:
            old_sl_pct = abs(float(current_sl) - float(entry_price)) / float(entry_price)
            if old_sl_pct < ATR_SL_MIN_INIT * 0.95:  # old was < 0.475% (stale accel floor)
                INIT_TO_ACCEL_MIGRATION = True

        # ── Check deltas (only gates HL push, NOT DB persistence) ──────────────────
        if needs_sl:
            sl_delta = abs(new_sl - current_sl) / current_sl if current_sl > 0 else 1.0
            hl_needs_sl = sl_delta > ATR_UPDATE_THRESHOLD_PCT or sl_stale
        else:
            hl_needs_sl = False

        if needs_tp:
            tp_delta = abs(new_tp - current_tp) / current_tp if current_tp > 0 else 1.0
            hl_needs_tp = tp_delta > ATR_UPDATE_THRESHOLD_PCT or tp_stale
        else:
            hl_needs_tp = False

        # Always append for DB persistence — delta gate only affects HL push
        # INIT_TO_ACCEL_MIGRATION bypasses tighten gate to correct stale accel-floor SLs
        if needs_sl or needs_tp or sl_stale or tp_stale or INIT_TO_ACCEL_MIGRATION:
            updates.append({
                'trade_id': trade_id,
                'token': token,
                'direction': direction,
                'entry_price': entry_price,
                'old_sl': current_sl,
                'new_sl': _atr_computed_new_sl,  # always use ATR-computed (INIT floor) for migrations
                'old_tp': current_tp,
                'new_tp': new_tp,
                # HL push is gated by delta + stale check; DB persist always happens
                'needs_sl': hl_needs_sl,
                'needs_tp': hl_needs_tp,
                'atr': atr,
                'atr_pct': atr_pct,
                'k': k,
            })

    return updates


def _persist_atr_levels(updates: List[Dict]) -> None:
    """
    Write ATR-computed SL/TP levels to brain DB.
    Called once per cycle after _collect_atr_updates() — BEFORE hit detection.
    This wires the dynamic ATR levels into check_atr_tp_sl_hits() next cycle.

    NOTE: unlike _execute_atr_bulk_updates (HL path), this ALWAYS writes to DB
    regardless of ATR_UPDATE_THRESHOLD_PCT. The delta gate only controls whether
    we push orders to Hyperliquid, not whether we update our own self-close levels.
    """
    if not updates:
        return

    conn = get_db_connection()
    if conn is None:
        return

    try:
        cur = get_cursor(conn)
        for u in updates:
            trade_id = u.get('trade_id')
            new_sl = u.get('new_sl')
            new_tp = u.get('new_tp')
            if not trade_id or new_sl is None or new_tp is None:
                continue
            cur.execute(
                "UPDATE trades SET stop_loss = %s, target = %s, atr_managed = TRUE WHERE id = %s AND status = 'open'",
                (round(new_sl, 8), round(new_tp, 8), trade_id)
            )
        conn.commit()
    except Exception as e:
        print(f"  [ATR] DB persist error: {e}")
    finally:
        conn.close()


def _execute_atr_bulk_updates(updates: List[Dict]) -> dict:
    """
    Execute SL/TP updates for all affected positions in exactly 2 HL API calls:
      1. cancel_bulk_orders  — cancel only the stale SL+TP orders for affected trades
      2. place_bulk_orders  — place all new SL+TP orders

    BUG-1 FIX: Track SL/TP OIDs per trade_id so only the right orders get cancelled.
    Previously cancelled ALL reduceOnly orders for a token, which could affect
    other positions of the same token that weren't being updated.

    Position sizes fetched once from HL, reused across all updates.
    """
    if not updates:
        return {'cancelled': 0, 'placed': 0, 'errors': []}

    from hyperliquid_exchange import (
        get_exchange, get_open_hype_positions,
        _HL_TICK_DECIMALS, _hl_tick_round,
        cancel_bulk_orders, place_bulk_orders, build_order,
        MAIN_ACCOUNT_ADDRESS,
    )

    exchange = get_exchange()

    # ── 1. Get position sizes — read from shared cache if available ─────────────
    # The cache is populated by check_and_manage_positions() before this is called.
    # Falls back to direct API call only if cache is cold.
    try:
        import hype_cache as hc
        positions = hc.get_cached_positions()
    except Exception:
        positions = {}
    if not positions:
        positions = get_open_hype_positions()
    if not positions:
        return {'cancelled': 0, 'placed': 0, 'errors': ['no positions on HL']}

    sz_map: Dict[str, float] = {}
    for coin_name, p in positions.items():
        sz_map[coin_name.upper()] = abs(float(p.get('size', 0) or 0))

    # ── 2. Build set of trade_ids being updated ───────────────────────────────
    updated_trade_ids = {u['trade_id'] for u in updates}

    # ── 3. Find stale order IDs to cancel — SELECTIVE per trade_id ───────────
    all_open = exchange.info.open_orders(MAIN_ACCOUNT_ADDRESS)
    stale_order_reqs = []
    for order in all_open:
        coin = order.get('coin', '').upper()
        oid = order.get('oid')
        if not oid or not coin:
            continue
        # Check if this order belongs to any of the affected trades
        # We check by matching token AND by checking the order's trigger price
        # matches either the SL or TP of one of our updates
        for u in updates:
            if u['token'].upper() != coin:
                continue
            # For this update's token, check if this OID's trigger price matches
            # the old SL or TP (indicating it belongs to this trade)
            order_trigger = float(order.get('triggerPrice', 0) or 0)
            if order.get('reduceOnly', False):
                # Match by trigger price proximity to old SL or TP
                if order_trigger > 0:
                    if (abs(order_trigger - u['old_sl']) < 0.001 or
                        abs(order_trigger - u['old_tp']) < 0.001):
                        stale_order_reqs.append({'oid': oid, 'coin': coin})
                        break

    # ── 3. Cancel all stale orders (one bulk call) ─────────────────────────────
    if stale_order_reqs:
        cancel_bulk_orders(stale_order_reqs)

    # ── 4. Build and place all new SL+TP orders (one bulk call) ───────────────
    new_orders = []
    for u in updates:
        token = u['token']
        direction = u['direction']
        sz = sz_map.get(token.upper(), 0)
        if sz <= 0:
            continue

        decimals = _HL_TICK_DECIMALS.get(token.upper(), 6)
        is_short = direction == 'SHORT'

        if u['needs_sl']:
            sl_px = _hl_tick_round(u['new_sl'], decimals)
            sl_type = {"trigger": {"triggerPx": sl_px, "isMarket": True, "tpsl": "sl"}}
            buy_side = "SELL" if not is_short else "BUY"
            new_orders.append(build_order(
                token, buy_side, sz, sl_px, sl_type, reduce_only=True
            ))

        if u['needs_tp']:
            tp_px = _hl_tick_round(u['new_tp'], decimals)
            tp_type = {"trigger": {"triggerPx": tp_px, "isMarket": True, "tpsl": "tp"}}
            buy_side = "SELL" if not is_short else "BUY"
            new_orders.append(build_order(
                token, buy_side, sz, tp_px, tp_type, reduce_only=True
            ))

    placed = 0
    errors = []
    if new_orders:
        # HL batch endpoint has limits with large order counts.
        # Chunk into sub-batches of MAX_BATCH_ORDERS to avoid rejections.
        MAX_BATCH_ORDERS = 10  # 5 positions × 2 orders (SL+TP)
        for i in range(0, len(new_orders), MAX_BATCH_ORDERS):
            chunk = new_orders[i:i + MAX_BATCH_ORDERS]
            result = place_bulk_orders(chunk)
            if result.get('success') or result.get('status') == 'ok':
                placed += len(chunk)
            else:
                # Collect ALL error fields: 'errors' (API-level) and 'error' (exception)
                errs = result.get('errors', [])
                if isinstance(errs, list):
                    errors.extend([str(e) for e in errs])
                # Also catch the 'error' key set by exception handler
                single_err = result.get('error')
                if single_err:
                    errors.append(str(single_err))

    return {
        'cancelled': len(stale_order_reqs),
        'placed': placed,
        'errors': errors,
    }


def get_trade_params(direction: str, price: float, max_leverage: int = MAX_LEVERAGE,
                     token: str = '', sl_pct_fallback: float = SL_PCT_FALLBACK) -> Dict:
    """
    Compute SL and TP for a new trade.
    SL is ATR(14)-based via _dr_atr() → _atr_multiplier():
      atr_pct < ATR_PCT_LOW_THRESH (1%)  → k=ATR_K_LOW_VOL (1.0)
      atr_pct <= ATR_PCT_HIGH_THRESH (3%) → k=ATR_K_NORMAL_VOL (1.25)
      atr_pct > ATR_PCT_HIGH_THRESH (3%)  → k=ATR_K_HIGH_VOL (1.5)
    Clamped by ATR_SL_MIN_INIT / ATR_SL_MAX_INIT floors and caps.
    Falls back to sl_pct_fallback if ATR unavailable or token not provided.
    TP = k * ATR_TP_K_MULT (1.25) * atr_pct, floored at TP_PCT_FALLBACK (8%).
    """
    direction = direction.upper()
    leverage = min(max_leverage, MAX_LEVERAGE)

    token = token.upper()

    # ── ATR-based SL ─────────────────────────────────────────────────────
    if token:
        atr = _pm_get_atr(token)
        if atr is not None:
            atr_pct = atr / price
            k = _dr_atr(token, atr_pct)
            atr_sl_pct = (k * atr) / price
            effective_sl_pct = max(atr_sl_pct, ATR_SL_MIN_INIT)
            effective_sl_pct = min(effective_sl_pct, ATR_SL_MAX_INIT)
        else:
            effective_sl_pct = sl_pct_fallback
    else:
        effective_sl_pct = sl_pct_fallback

    # ── ATR-based TP (2:1 R:R — TP = 2 × SL distance) ───────────────────
    tp_pct = TP_PCT_FALLBACK  # fallback
    if token:
        atr = _pm_get_atr(token)
        if atr is not None:
            atr_pct_tp = atr / price
            k_tp = _dr_atr(token, atr_pct_tp) * ATR_TP_K_MULT
            tp_pct = k_tp * atr_pct_tp  # canonical: k × 1.25 × atr_pct
            tp_pct = max(tp_pct, TP_PCT_FALLBACK)     # floor at 8%

    if direction == "LONG":
        stop_loss = round(price * (1 - effective_sl_pct), 8)
        target = round(price * (1 + tp_pct), 8)
    elif direction == "SHORT":
        stop_loss = round(price * (1 + effective_sl_pct), 8)
        target = round(price * (1 - tp_pct), 8)
    else:
        raise ValueError(f"Invalid direction: {direction}")

    return {
        "stop_loss": stop_loss,
        "target": target,
        "leverage": leverage,
    }


# ─── Volume Confirmation Cache (HL candles via ccxt) ────────────────────────────
# One fetch per 60s — shared across all trades in the same pipeline run.
# NOTE: Volume confirmation is unused by the new ATR-adaptive TP/SL system but
# _warmup_volume_cache_pm still calls _fetch_volume_data, so keep these functions.
TRAILING_VOL_LOOKBACK = 24  # candles for volume MA (used by _fetch_volume_data)
VOLUME_CACHE_FILE  = '/var/www/hermes/data/volume_cache.json'
VOLUME_CACHE_TTL  = 60       # seconds — one fetch per pipeline minute

def _load_volume_cache() -> dict:
    """Load cached volume data. Returns {token: {ts, vol_last, vol_ma, confirmed}}"""
    try:
        if os.path.exists(VOLUME_CACHE_FILE):
            with open(VOLUME_CACHE_FILE) as f:
                return json.load(f)
    except Exception:
        pass
    return {}


def _save_volume_cache(data: dict) -> None:
    """Save volume cache to disk atomically."""
    try:
        os.makedirs(os.path.dirname(VOLUME_CACHE_FILE), exist_ok=True)
        tmp = VOLUME_CACHE_FILE + f".{os.getpid()}.tmp"
        with open(tmp, "w") as f:
            json.dump(data, f, default=str)
        os.rename(tmp, VOLUME_CACHE_FILE)
    except Exception:
        pass


def _fetch_volume_data(token: str) -> dict:
    """
    Fetch last 24h of 1h candles for token via ccxt+Hyperliquid.
    Returns {vol_last, vol_ma, confirmed} or empty dict on failure.
    Hard timeout of 5s — failures are silent (volume confirmation = False).
    """
    try:
        import ccxt
        import time as _time
    except Exception:
        return {}

    try:
        ex = ccxt.hyperliquid()
        ex.http_timeout = 5  # hard cap — don't block the pipeline
        # HL uses /USDC suffix for perps
        symbol = f"{token.upper()}/USDC:USDC"
        candles = ex.fetch_ohlcv(symbol, "1h", limit=TRAILING_VOL_LOOKBACK)
        if not candles or len(candles) < 2:
            return {}
        # candles: [ts, open, high, low, close, volume]
        vols = [float(c[5]) for c in candles]
        vol_last = vols[-1]
        vol_ma = sum(vols[:-1]) / len(vols[:-1])  # MA excluding current candle
        return {
            "vol_last": vol_last,
            "vol_ma": vol_ma,
            "confirmed": vol_last > vol_ma,
            "ratio": round(vol_last / vol_ma, 2) if vol_ma > 0 else 0,
            "ts": _time.time(),
        }
    except Exception:
        # Fail silent — volume confirmation defaults to False (tighter SL)
        return {}


# ─── Position Management ──────────────────────────────────────────────────────

def refresh_current_prices(server: str = SERVER_NAME):
    """
    Fetch live prices from Hyperliquid, update pnl_pct in brain DB for open positions.

    FIX (2026-04-03): Use HL's authoritative unrealized_pnl directly instead of
    computing from mids (which was stale/wrong due to per-fill averaging).
    HL's unrealized_pnl = (entryPx - currentPx) / entryPx * positionValue * leverage
    This is the GROUND TRUTH — use it for all exit decisions.

    FIX (2026-04-10): Also persist pnl_pct, pnl_usdt, current_price to DB.
    Previously only updated in-memory dict, so direct DB queries returned stale values.

    DB↔HL reconciliation (orphans/ghosts) is handled exclusively by
    hl-sync-guardian.py (60s cycle). This function ONLY updates current_price
    and pnl_pct for positions already confirmed in the DB.
    """

    # Get brain DB positions (source of truth for trade IDs and metadata)
    positions = get_open_positions(server)
    if not positions:
        return []

    # Get HL's authoritative position data (includes unrealized_pnl)
    # Try shared hype_cache first (written by this same pipeline run), then fall
    # back to direct API call. This avoids a duplicate /info call when the cache
    # has already been populated by fetch_and_cache_positions() above.
    try:
        import hype_cache as hc
        hl_positions = hc.get_cached_positions()
    except Exception:
        hl_positions = {}
    
    if not hl_positions:
        try:
            hl_positions = get_open_hype_positions()
        except Exception as e:
            print(f"  [Position Manager] HL positions API failed: {e}")
            hl_positions = {}
    
    # Legacy fallback: read hl_cache.json directly (before our new get_cached_positions)
    if not hl_positions:
        try:
            import json as _json
            _cache = '/var/www/hermes/data/hl_cache.json'
            if os.path.exists(_cache):
                with open(_cache) as _f:
                    _cached = _json.load(_f)
                _cached_pos = {_p['coin']: _p for _p in _cached.get('positions', [])}
                hl_positions = {}
                for _tok, _pdata in _cached_pos.items():
                    hl_positions[_tok] = {
                        'entry_px': float(_pdata.get('entryPrice', 0) or 0),
                        'unrealized_pnl': float(_pdata.get('unrealizedPnl', 0) or 0),
                        'size': float(_pdata.get('size', 0) or 0),
                        'leverage': float(_pdata.get('leverage', 1) or 1),
                        'direction': _pdata.get('side', '').upper(),
                    }
                if hl_positions:
                    print(f"  [Position Manager] Using legacy hl_cache.json fallback ({len(hl_positions)} positions)")
        except Exception:
            pass

    if not hl_positions:
        print(f"  [Position Manager] No HL position data available (rate limited + no cache)")
        return positions

    # Fetch live mids for current_price (more accurate than deriving from unrealized_pnl)
    try:
        mids = hc.get_allMids()
    except Exception as e:
        print(f"  [Position Manager] Failed to fetch mids: {e}")
        mids = {}

    # Warn if paper trading without HL access
    if not HYPE_AVAILABLE:
        print(f"  [Position Manager] WARNING: Paper trading WITHOUT Hyperliquid — prices may be stale")

    # DB connection for persisting PnL (BUG FIX 2026-04-10)
    db_conn = get_db_connection()
    db_cur = db_conn.cursor() if db_conn else None

    updated = 0
    for pos in positions:
            token = str(pos.get('token') or '').upper()
            trade_id = pos.get('id')
            if not trade_id:
                continue
            direction = str(pos.get('direction') or '').upper()
            entry = float(pos.get('entry_price') or 0)
            leverage = float(pos.get('leverage') or 1)

            # Get current price from HL mids (most up-to-date)
            cur_price_str = mids.get(token, '0')
            try:
                cur_price = round(float(cur_price_str), 6)
            except:
                cur_price = 0

            # Fallback for entry=0: use mid price as proxy
            if not entry and cur_price > 0:
                entry = cur_price
                pos['entry_price'] = cur_price
                if db_cur:
                    try:
                        db_cur.execute("""
                            UPDATE trades SET entry_price = %s WHERE id = %s AND status = 'open'
                        """, (cur_price, trade_id))
                    except Exception:
                        pass

            # Get HL authoritative data for this token
            hl_data = hl_positions.get(token)
            if hl_data:
                # Use HL unrealized_pnl as ground truth for PnL
                hl_entry = float(hl_data.get('entry_px', 0))
                hl_unrealized = float(hl_data.get('unrealized_pnl', 0))
                hl_size = float(hl_data.get('size', 0))

                # If entry is 0 but HL has it, backfill from HL
                if entry <= 0 and hl_entry > 0:
                    entry = hl_entry
                    pos['entry_price'] = hl_entry
                    if db_cur:
                        try:
                            db_cur.execute("""
                                UPDATE trades SET entry_price = %s WHERE id = %s AND status = 'open'
                            """, (hl_entry, trade_id))
                        except Exception:
                            pass

                # Use mid price as current_price (most accurate real-time value)
                if cur_price > 0:
                    pos['current_price'] = cur_price

                if entry > 0 and cur_price > 0 and direction:
                    # Use hl_entry for PnL computation, NOT the DB entry_price.
                    # DB entry may be stale/wrong (e.g. stale signal price vs actual HL fill).
                    # HL's unrealized_pnl is already computed against hl_entry, so using
                    # hl_entry here ensures PnL is consistent with what HL reports.
                    # If hl_entry is 0 (edge case), fall back to DB entry.
                    _ep = hl_entry if hl_entry > 0 else entry
                    pnl_pct = round(((cur_price - _ep) / _ep * 100) if direction == 'LONG'
                                    else ((_ep - cur_price) / _ep * 100), 4)
                    pos['pnl_pct'] = pnl_pct
                    pos['pnl_usdt'] = hl_unrealized if hl_unrealized else 0
                    pos['entry_price'] = _ep  # fix in-memory entry to match HL
                    updated += 1
                    if db_cur:
                        try:
                            db_cur.execute("""
                                UPDATE trades
                                SET current_price = %s, pnl_pct = %s, pnl_usdt = %s,
                                    entry_price = %s, updated_at = NOW()
                                WHERE id = %s AND status = 'open'
                            """, (cur_price, pnl_pct, pos['pnl_usdt'], _ep, trade_id))
                        except Exception:
                            pass
            else:
                # No HL position data — skip PnL update (only mids price available)
                if cur_price > 0:
                    pos['current_price'] = cur_price
                continue

            # ── HL position data available — use authoritative PnL + peak tracking ──
            if hl_size <= 0 or hl_entry <= 0:
                continue

            # FIX (2026-04-17): If entry_price in DB is 0 but HL has a valid entry_px,
            # update entry_price too — so _collect_atr_updates can compute ATR levels.
            if entry <= 0 and hl_entry > 0:
                entry = hl_entry
                pos['entry_price'] = hl_entry  # patch in-memory so _collect_atr_updates sees it
                if db_cur:
                    try:
                        db_cur.execute("""
                            UPDATE trades SET entry_price = %s WHERE id = %s AND status = 'open'
                        """, (hl_entry, trade_id))
                    except Exception as e:
                        print(f"  [Position Manager] Failed to fix entry_price for trade {trade_id}: {e}")

            # pnl_pct from HL's unrealized_pnl (ground truth)
            # unrealized_pnl = (entryPx - currentPx) / entryPx * positionValue
            # where positionValue = entryPx * size (leverage already baked into size)
            position_value = hl_entry * hl_size
            pnl_pct = (hl_unrealized / position_value) * 100 if position_value > 0 else 0
            pnl_pct = round(pnl_pct, 4)

            # current_price from mids (most accurate for DB)
            if cur_price <= 0:
                cur_price_str = mids.get(token, '0')
                try:
                    cur_price = round(float(cur_price_str), 6)
                except:
                    cur_price = 0

            # pnl_usdt = unrealized_pnl directly (already in USDT)
            pnl_usdt = round(hl_unrealized, 2)

            if cur_price > 0:
                # ── Peak price tracking for trailing SL ────────────────────────
                # SHORT: track highest_price (peak pump), SL trails DOWN from highest
                # LONG:  track lowest_price (bottom trough), SL trails UP from lowest
                existing_high = float(pos.get('highest_price') or 0) or 0
                existing_low  = float(pos.get('lowest_price')  or 0) or 0

                # FIX (2026-04-25): Initialize peak to entry_price when trade just opened
                # and no real peak has formed yet. This prevents ATR trailing from using
                # current_price as a moving reference instead of a true peak anchor.
                if existing_high <= 0 and direction == "SHORT":
                    existing_high = entry  # SHORT: start tracking from entry
                if existing_low <= 0 and direction == "LONG":
                    existing_low = entry   # LONG: start tracking from entry

                if direction == "SHORT":
                    new_high = max(existing_high, cur_price)
                    new_low  = min(existing_low, cur_price)   # track new lows for SHORT
                elif direction == "LONG":
                    new_high = max(existing_high, cur_price)  # track peak for LONG trailing
                    new_low  = min(existing_low, cur_price)
                else:
                    new_high = existing_high
                    new_low  = existing_low

                # Update in-memory so subsequent checks use fresh values
                pos['pnl_pct'] = pnl_pct
                pos['current_price'] = cur_price
                pos['pnl_usdt'] = pnl_usdt
                pos['highest_price'] = new_high
                pos['lowest_price']  = new_low
                updated += 1

                # BUG FIX (2026-04-10): persist to DB so direct DB queries return correct PnL
                # Also persist peak prices for trailing SL (BUG FIX 2026-04-19)
                if db_cur:
                    try:
                        db_cur.execute("""
                            UPDATE trades
                            SET pnl_pct = %s, pnl_usdt = %s, current_price = %s,
                                highest_price = %s, lowest_price = %s, updated_at = NOW()
                            WHERE id = %s AND status = 'open'
                        """, (pnl_pct, pnl_usdt, cur_price, new_high, new_low, trade_id))
                    except Exception as e:
                        print(f"  [Position Manager] Failed to persist PnL for trade {trade_id}: {e}")

    # Commit and close DB connection
    if db_conn:
        try:
            db_conn.commit()
        except Exception as e:
            print(f"  [Position Manager] DB commit failed: {e}")
        finally:
            if db_cur:
                db_cur.close()
            if db_conn:
                db_conn.close()

    if updated:
        print(f"  [Position Manager] Updated {updated} position prices from HL")
    return positions


def _warmup_volume_cache_pm(tokens: List[str]):
    """
    Pre-fetch HL volume data for a list of tokens — non-blocking.
    Reads existing cache, fetches only stale/missing entries (one HL call per token).
    Each fetch has a 5s timeout — failures are silent, cache stays fresh for existing entries.
    This is called at the START of check_and_manage_positions so the cache is warm
    by the time we evaluate trailing SLs in the loop below.
    """
    if not tokens:
        return
    import threading, time as _time

    def _fetch_one(token: str):
        data = _fetch_volume_data(token)
        if data:
            cache = _load_volume_cache()
            cache[token.upper()] = data
            _save_volume_cache(cache)

    cache = _load_volume_cache()
    now = _time.time()
    stale = [t.upper() for t in tokens
             if t.upper() not in cache or (now - cache.get(t.upper(), {}).get("ts", 0)) >= VOLUME_CACHE_TTL]
    if not stale:
        return

    # Fire one thread per stale token — threads die on timeout, no blocking
    for token in stale:
        t = threading.Thread(target=_fetch_one, args=(token,), daemon=True)
        t.start()


def check_and_manage_positions() -> Tuple[int, int, int]:
    """
    Called every pipeline run.

    Exit priority (all exits self-close via close_paper_position):
    1. ATR TP/SL hit      — price crossed dynamically-computed ATR SL/TP (DB-written each cycle)
    2. MACD cascade flip  — MTF MACD alignment reversal (MACD_CASCADE_FLIP_TOKENS)
    3. Cascade flip       — loss > -0.25% + speed increasing + opposite signal
    4. Wave turn exit     — z-score extreme (>±1.5) + acceleration reversing
    5. Stale winner/loser — flat >15min in profit OR flat >30min in loss

    ATR SL/TP is recomputed each cycle via _collect_atr_updates() (z-score/speed-adaptive k)
    and written to the brain DB via _persist_atr_levels() before hit detection runs.
    HL order push (_execute_atr_bulk_updates) is controlled by ATR_HL_ORDERS_ENABLED kill switch.

    Returns: (open_count, closed_count, adjusted_count)
    """
    # ── Pre-fetch HL positions into shared cache for guardian and downstream ──────
    # Both refresh_current_prices() and _execute_atr_bulk_updates() call
    # get_open_hype_positions() directly. Writing to the shared cache here means
    # they can both read from it instead of making 2 separate /info API calls.
    try:
        import hype_cache as hc
        hc.fetch_and_cache_positions()
    except Exception:
        pass  # Never fail the pipeline over a cache write

    positions = refresh_current_prices()

    # ── Volume cache warm-up ──────────────────────────────────────────────
    # Pre-fetch volume data for all open positions before trailing SL evaluation.
    # Lazy-warms the cache so subsequent has_volume_confirmation() calls are instant.
    _warmup_volume_cache_pm([p.get("token") for p in positions])

    # SPEED FEATURE: update speed tracker once per pipeline run (<2s)
    if SPEED_TRACKER is not None:
        SPEED_TRACKER.update()

    # ── 0. Refresh ATR SL/TP levels in DB ─────────────────────────────────────
    # Compute fresh ATR-based SL/TP for all positions and write to DB.
    # check_atr_tp_sl_hits() will use these new levels in this cycle's hit checks.
    # This wires the z-score/speed-adaptive k multiplier into self-close detection.
    _atr_updates = _collect_atr_updates(positions)
    if _atr_updates:
        _persist_atr_levels(_atr_updates)  # NEW: write to DB (always runs)
        # BUG FIX: also update in-memory positions so check_atr_tp_sl_hits() sees fresh values
        # (check_atr_tp_sl_hits reads from the in-memory dict, not the DB)
        updates_by_id = {u['trade_id']: u for u in _atr_updates}
        for pos in positions:
            tid = pos.get('id')
            if tid in updates_by_id:
                u = updates_by_id[tid]
                pos['stop_loss'] = u['new_sl']
                pos['target'] = u['new_tp']
        if ATR_HL_ORDERS_ENABLED:
            _execute_atr_bulk_updates(_atr_updates)  # HL path (kill switch controlled)
        print(f"  [ATR] Updated {len(_atr_updates)} position SL/TP levels")

    open_count = len(positions)
    closed_count = 0
    adjusted_count = 0
    original_closed = closed_count  # FIX (2026-04-09): track baseline before exit logic

    for pos in positions:
        # ── EXIT PRIORITY ORDER ─────────────────────────────────────────────────
        # 1. Wave turn exit      — z-score extreme (>±1.5) + acceleration reversing
        #                          (HIGHEST CONVICTION — fires before ATR if in profit)
        # 2. ATR TP/SL hit       — price crossed DB SL/TP (dynamically updated above)
        # 3. MACD cascade flip   — MTF MACD alignment reversal (MACD_CASCADE_FLIP_TOKENS)
        # 4. Cascade flip        — loss > -0.25% + speed increasing + opposite signal
        # ─────────────────────────────────────────────────────────────────────────────
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

        # ── 1. ATR TP/SL hit detection (internal close) ────────────────────────
        # ATR TP/SL is the primary exit — run FIRST so standard exits always fire
        # before speculative wave_turn counter-trend exits.
        # close_paper_position() handles internal DB close + market mirror to HL.
        atr_hits = check_atr_tp_sl_hits([pos])
        for hit in atr_hits:
            print(f"  [ATR HIT] {token} {direction} {hit['hit_reason']}: "
                  f"price={hit['current_price']:.6f} SL={hit['stop_loss']:.6f} TP={hit['target']:.6f}")
            close_paper_position(hit['trade_id'], hit['hit_reason'])
            closed_count += 1
        if atr_hits:
            continue  # Position closed — skip remaining checks

        # ── 2. WAVE TURN EXIT (SPEED FEATURE) ─────────────────────────────────
        # Wave turn detection: z-score extreme AND acceleration flipping direction.
        # Fires AFTER ATR — wave turns are counter-trend exits that should only
        # fire on positions that survived standard TP/SL.
        #
        # TOP FORMING:  z_score > +1.5 AND acceleration < 0 → close LONGs
        # BOTTOM FORMING: z_score < -1.5 AND acceleration > 0 → close SHORTs
        wave_turn_fired = False
        trailing_active = False  # always False (trailing stop is computed via ATR SL, not a separate mechanism)
        if SPEED_TRACKER is not None:
            spd = SPEED_TRACKER.get_token_speed(token)
            if spd:
                z_score = spd.get('price_velocity_5m', 0)
                accel = spd.get('price_acceleration', 0)
                wave_turn = False
                if direction == 'LONG' and z_score > 1.5 and accel is not None and accel < 0:
                    wave_turn = True
                    reason = f"wave_turn_top_z{z_score:+.2f}_acc{accel:+.4f}"
                elif direction == 'SHORT' and z_score < -1.5 and accel is not None and accel > 0:
                    wave_turn = True
                    reason = f"wave_turn_bottom_z{z_score:+.2f}_acc{accel:+.4f}"

                if wave_turn:
                    trailing_active = False  # always False (trailing stop removed)
                    # Don't exit if trailing is active AND position is underwater
                    if trailing_active and live_pnl <= 0:
                        print(f"  🌊 WAVE TURN {token} {direction} {live_pnl:+.2f}% — trailing active, skipping (still underwater)")
                    else:
                        close_paper_position(trade_id, f"wave_turn_{reason}")
                        closed_count += 1
                        wave_turn_fired = True
                        print(f"  🌊 WAVE TURN EXIT {token} {direction} {live_pnl:+.2f}% [{reason}]")

                        # ── 2b. Counter-signal injection ──────────────────────────
                        opposite_dir = 'SHORT' if direction == 'LONG' else 'LONG'
                        counter_source = 'wave_turn,momentum'
                        counter_conf = min(85, max(60, abs(accel) * 500 + 60))
                        counter_sig_type = 'wave_turn'
                        try:
                            from signal_schema import add_signal as _add_sig
                            new_sid = _add_sig(
                                token=token,
                                direction=opposite_dir,
                                signal_type=counter_sig_type,
                                source=counter_source,
                                confidence=counter_conf,
                                value=str(abs(accel)),
                                price=0,
                                exchange='hyperliquid',
                                timeframe='5m',
                                z_score=z_score,
                                z_score_tier='wave_turn_exit',
                            )
                            print(f"  🌊 WAVE TURN counter injected: {token} {opposite_dir} conf={counter_conf:.0f}% sig_id={new_sid}")
                        except Exception as inj_err:
                            print(f"  🌊 WAVE TURN counter injection failed for {token}: {inj_err}")

                        continue  # Position closed — skip remaining checks

        # ── 3. MACD-Rules Engine Cascade Flip (2026-04-06) ───────────────────
        # Use macd_rules.py for proper entry/exit/flip signal detection.
        # Replaces the simple cross_under/cross_over check with full state machine.
        if token.upper() in MACD_CASCADE_FLIP_TOKENS:
            from macd_rules import get_macd_exit_signal, compute_macd_state, compute_mtf_macd_alignment

            # ── MTF MACD Alignment ultra-confirmation (2026-04-06) ──────────
            # If ALL 3 TFs (4H/1H/15m) flip direction, this is an extremely
            # rare event — trigger cascade flip immediately with max confidence.
            mtf_align = compute_mtf_macd_alignment(token)
            mtf_all_flipped = False
            if mtf_align is not None:
                # all_tfs_bearish means all 3 TFs bearish → SHORT direction confirmed
                # If we're LONG and all TFs bearish → immediate cascade flip
                # all_tfs_bullish means all 3 TFs bullish → LONG direction confirmed
                # If we're SHORT and all TFs bullish → immediate cascade flip
                if mtf_align['all_tfs_bearish'] and direction == 'LONG':
                    mtf_all_flipped = True
                    print(f"  [MTF ALIGN] {token} 4H/1H/15m all bearish → immediate cascade flip")
                elif mtf_align['all_tfs_bullish'] and direction == 'SHORT':
                    mtf_all_flipped = True
                    print(f"  [MTF ALIGN] {token} 4H/1H/15m all bullish → immediate cascade flip")

                # Log TF states for monitoring
                for tf_name, state in mtf_align['tf_states'].items():
                    if state is not None:
                        print(f"    [MTF ALIGN {tf_name}] regime={state.regime.name} "
                              f"bull_score={state.bullish_score:+d} macd_above={state.macd_above_signal} "
                              f"hist={state.histogram:+.6f}")

            macd_result = get_macd_exit_signal(token, direction)

            if macd_result['state'] is not None:
                s = macd_result['state']
                # Log MACD state for monitoring
                print(f"  [MACD] {token} bull_score={s.bullish_score:+d} "
                      f"regime={'BULL' if s.regime.value==1 else 'BEAR' if s.regime.value==-1 else 'NEUTRAL'} "
                      f"xover={'FRESH' if abs(s.crossover_freshness.value)==2 else 'STALE'} "
                      f"hist={s.histogram:+.6f} rate={s.histogram_rate:+.2f}")

            if CASCADE_FLIP_ENABLED and mtf_all_flipped:
                # Ultra-confirmed cascade flip — all TFs flipped direction
                flip_info = {
                    'opposite_dir': 'SHORT' if direction == 'LONG' else 'LONG',
                    'conf': 95.0,
                    'source': 'mtf_macd_alignment',
                    'reason': 'all_tfs_reversed',
                    'sig_id': None,
                }
                cascade_flipped = cascade_flip(
                    token, direction, trade_id,
                    live_pnl, flip_info,
                    entry_price=float(pos.get('entry_price') or 0)
                )
                if cascade_flipped:
                    closed_count += 1
                    continue

            # ── Cascade Direction Flip (2026-04-06) ─────────────────────────────
            # If cascade is ACTIVE and the cascade direction is OPPOSITE to our
            # current position — flip immediately. Cascade is the LEAD indicator
            # and means the market is already cascading in the other direction.
            from macd_rules import cascade_entry_signal
            cascade = cascade_entry_signal(token)
            if CASCADE_FLIP_ENABLED and cascade['cascade_active'] and cascade['cascade_direction'] and cascade['cascade_direction'] != direction:
                print(f"  [CASCADE FLIP] {token} {direction} → {cascade['cascade_direction']} "
                      f"(cascade active, lead={cascade['lead_tf']}, confirm={cascade['confirmation_count']}, "
                      f"reason={cascade['entry_block_reason']})")
                flip_info = {
                    'opposite_dir': cascade['cascade_direction'],
                    'conf': 95.0,
                    'source': 'cascade_direction',
                    'reason': f'cascade_{cascade["cascade_direction"].lower()}_confirmed',
                    'sig_id': None,
                }
                cascade_flipped = cascade_flip(
                    token, direction, trade_id,
                    live_pnl, flip_info,
                    entry_price=float(pos.get('entry_price') or 0)
                )
                if cascade_flipped:
                    closed_count += 1
                    continue

            if CASCADE_FLIP_ENABLED and macd_result['should_flip'] and macd_result['reasons']:
                primary_reason = macd_result['reasons'][0]
                print(f"  [MACD FLIP] {token} {direction} → flipping: {macd_result['reasons']}")
                flip_info = {
                    'opposite_dir': 'SHORT' if direction == 'LONG' else 'LONG',
                    'conf': 85.0,
                    'source': 'macd_rules_engine',
                    'reason': primary_reason[:80],
                    'sig_id': None,
                }
                cascade_flipped = cascade_flip(
                    token, direction, trade_id,
                    live_pnl, flip_info,
                    entry_price=float(pos.get('entry_price') or 0)
                )
                if cascade_flipped:
                    closed_count += 1
                    continue
            elif macd_result['should_exit'] and macd_result['reasons']:
                # Exit without flip (market not set up for reverse)
                for reason in macd_result['reasons']:
                    if reason.startswith('FLIP:'):
                        continue
                    print(f"  [MACD EXIT] {token} {direction} → exiting: {reason}")
                    close_paper_position(trade_id, reason)
                    closed_count += 1
                    break
                if closed_count > original_closed:
                    continue

        # ── 3. Cascade flip (speed-armed reversal — fires before cut_loser) ───
        # Only fires if trailing is NOT active (don't flip during trailing).
        # Speed-armed state machine inside check_cascade_flip():
        #   loss > -0.25%  → not armed, nothing fires
        #   loss <= -0.25% → armed: speed check, log, wait for trigger
        #   loss <= -0.50% (pctl 50-80) OR -0.35% (pctl > 80) → FLIP
        cascade_flipped = False
        if CASCADE_FLIP_ENABLED and not trailing_active and live_pnl <= CASCADE_FLIP_ARM_LOSS:
            flip_info = check_cascade_flip(token, direction, live_pnl, SPEED_TRACKER)
            if flip_info:
                cascade_flipped = cascade_flip(
                    token, direction, trade_id,
                    live_pnl, flip_info,
                    entry_price=float(pos.get('entry_price') or 0)
                )
                if cascade_flipped:
                    closed_count += 1
                    continue  # Position was flipped — skip remaining checks

        # ── 5. Cut loser (DISABLED — guardian handles all emergency exits) ──
        # Cut_loser was causing races: position_manager uses fresh prices and cuts tight
        # (sl_distance from A/B test can be 0.5%), before guardian's flip can fire.
        # Guardian is the designated emergency handler (flip, hard SL, cut_loser at -5%).
        # Cut_loser is DISABLED here to prevent duplicate closing of the same position.
        # if not trailing_active and should_cut_loser(live_pnl, pos):
        #     reason = f"cut_loser_{live_pnl:+.2f}%"
        #     close_paper_position(trade_id, reason)
        #     closed_count += 1
        #     print(f"  CUT_LOSER {token} {direction} {live_pnl:+.2f}%")

        # ── 6. SPEED: Stale winner/loser exit ─────────────────────────────────
        # SPEED FEATURE: closes positions that are in profit but flat (stale winner)
        # or in loss but flat for 30+ min (stale loser).
        # Fires alongside trailing SL — doesn't replace it. Compliments cascade_flip.
        # Only fires when trailing is NOT active (don't interfere with trailing exits).
        if not trailing_active:
            stale_close, stale_reason = check_stale_position(token, live_pnl, direction)
            if stale_close:
                close_paper_position(trade_id, f"stale_exit_{stale_reason}")
                closed_count += 1
                print(f"  STALE EXIT {token} {direction} {live_pnl:+.2f}% [{stale_reason}]")
                continue  # Skip trailing SL update for closed position

    # ── End of per-position loop ─────────────────────────────────────────────

    print(f"Position Manager: {open_count} open | {closed_count} closed | {adjusted_count} adjusted")

    # ── Pipeline heartbeat ─────────────────────────────────────────────────────
    _update_pm_heartbeat()

    return open_count, closed_count, adjusted_count


# ─── Cascade Flip ─────────────────────────────────────────────────────────────
# When an open position is losing and an opposite signal fires, close and reverse.


def check_cascade_flip(token: str, position_direction: str,
                      live_pnl: float, speed_tracker=None) -> Optional[Dict]:
    """
    Speed-armed cascade flip check.

    State machine (tightened 2026-04-06):
      pnl > -0.25%                             → NOT ARMED: nothing fires
      -0.50% < pnl <= -0.25% (pctl 50-80)    → ARMED: speed check, log, wait
      -0.35% < pnl <= -0.25% (pctl > 80)      → ARMED: speed check, log, wait
      pnl <= -0.50% (pctl 50-80)              → FLIP TRIGGERED
      pnl <= -0.35% (pctl > 80)               → FAST FLIP (high momentum)

    Opposite signal confluence required:
      - Signal in PENDING/WAIT/APPROVED state
      - Confidence >= 60% (lowered from 70 to catch near-breakeven wrong-direction)
      - Created within last 30 minutes (expanded from 15 — signals expire before flip fires)
      - At least 1 distinct signal type agreeing

    Returns: Dict with flip details {opposite_dir, conf, source, sig_id, price}
             or None if no flip warranted.
    """
    import sqlite3

    # ── 1. Arm check ───────────────────────────────────────────────────────────
    if live_pnl > CASCADE_FLIP_ARM_LOSS:
        return None  # Not even armed yet

    # ── 2. Flip count check ────────────────────────────────────────────────────
    flip_counts = _load_flip_counts()
    current_flips = flip_counts.get(token.upper(), {}).get('flips', 0)
    if current_flips >= CASCADE_FLIP_MAX:
        print(f"  [CASCADE FLIP] {token} at max flips ({CASCADE_FLIP_MAX}) — skipped")
        return None

    # ── 3. Speed check ─────────────────────────────────────────────────────────
    speed_ok, percentile = _speed_increasing(token, speed_tracker)
    trigger_pct = _get_trigger_threshold(token, speed_tracker)

    if not speed_ok:
        # Armed but speed not increasing — log and wait
        print(f"  [CASCADE ARMED] {token} armed (loss={live_pnl:+.2f}%, "
              f"speed_pctl={percentile:.1f}, waiting for trigger <={trigger_pct:.2f}%)")
        return None

    # ── 4. Trigger check ───────────────────────────────────────────────────────
    if live_pnl > trigger_pct:
        # Armed, speed increasing, but haven't hit trigger yet
        print(f"  [CASCADE ARMED] {token} armed (loss={live_pnl:+.2f}%, "
              f"speed_pctl={percentile:.1f}, trigger={trigger_pct:.2f}%)")
        return None

    # ── 5. Flip warranted — NO SIGNAL REQUIRED ─────────────────────────────────
    # T: don't wait for opposing signal. Momentum + loss is enough to flip.
    # Use coin-regime momentum as the signal source always.
    opposite_dir = 'SHORT' if position_direction == 'LONG' else 'LONG'

    if speed_tracker is not None:
        try:
            spd = speed_tracker.get_token_speed(token)
            vel = spd.get('price_velocity_5m', 0) or 0
            accel = spd.get('price_acceleration', 0) or 0
            regime_conf = min(100.0, max(0.0, abs(vel) * 30))  # vel 1.0→30%, 2.0→60%
            if regime_conf >= 20.0:  # Require some minimum momentum to flip
                print(f"  [CASCADE FLIP] {token} flipping on momentum: vel={vel:+.2f} accel={accel:+.4f} conf={regime_conf:.0f}%")
                return {
                    'opposite_dir': opposite_dir,
                    'conf': regime_conf,
                    'source': 'coin-regime',
                    'sig_id': None,
                    'price': 0,
                    'created_at': None,
                    'signal_type': 'coin-regime',
                }
            else:
                print(f"  [CASCADE FLIP] {token} not flipping: vel={vel:+.2f} conf={regime_conf:.0f}% < 20%")
                return None
        except Exception as e:
            print(f"  [CASCADE FLIP] {token} speed lookup error: {e}")
            return None
    return None


# ── BUG-FIX B4: Cascade sequence PnL tracking ─────────────────────────────────
# ─── Loss Cooldown
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
        with FileLock('loss_cooldowns'):
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
    """Return True if token+direction is in loss cooldown.

    FIX (2026-04-22): Check BOTH stores.
    - Primary: loss_cooldowns.json (guardian's streak-based cooldowns).
    - Fallback: PostgreSQL signal_cooldowns (1h flat, written by HL live-close path
      via _record_trade_outcome). Without this check, HL live closes (HL_SL_CLOSED,
      HL_CLOSED, etc.) were invisible to this function, allowing immediate re-entry.

    PostgreSQL stores tokens as 'TOKEN:DIRECTION' (e.g. 'BTC:LONG').
    """
    key = f"{token.upper()}:{direction.upper()}"

    # Primary: loss_cooldowns.json (guardian's streak-based cooldowns)
    data = _clean_expired(_load_cooldowns())
    if key in data:
        return True

    # Fallback: PostgreSQL signal_cooldowns (written by _record_trade_outcome on
    # HL live closes — HL_SL_CLOSED, HL_CLOSED, etc. never write to JSON)
    try:
        import psycopg2
        from _secrets import BRAIN_DB_DICT
        conn = psycopg2.connect(**BRAIN_DB_DICT)
        cur = conn.cursor()
        # PostgreSQL stores token='BTC:LONG', direction='LONG' — check both match
        cur.execute(
            "SELECT 1 FROM signal_cooldowns WHERE token=%s AND direction=%s AND expires_at > NOW()",
            (key, direction.upper()))
        result = cur.fetchone()
        cur.close()
        conn.close()
        if result:
            return True
    except Exception:
        pass

    return False


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
    data[key] = {"expires": expiry, "streak": streak, "hours": hours, "reason": "loss"}
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
        with FileLock('wrong_side_learning'):
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
        conn = _sqlite3.connect(STATIC_DB)
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

    if count >= 3 and avg_pct >= WRONG_SIDE_AVG_PCT_THRESH:
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
        with FileLock('pipeline_heartbeat'):
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
    try:
        print(f"[Position Manager] Starting check at {datetime.now()}")
        print(f"[Position Manager] Connecting to DB: {DB_CONFIG.get('host')}/{DB_CONFIG.get('database','?')}")

        # refresh_current_prices() is called inside check_and_manage_positions()
        # Run management check (it calls refresh_current_prices internally)
        print()
        open_n, closed_n, adjusted_n = check_and_manage_positions()
        print(f"\n[Position Manager] Done. Open: {open_n} | Closed: {closed_n} | Adjusted: {adjusted_n}")
    except Exception as e:
        import traceback
        print(f"[Position Manager] FATAL in main(): {e}")
        traceback.print_exc()
        raise


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        import traceback
        print(f"[Position Manager] FATAL: {e}")
        traceback.print_exc()
        exit(1)
