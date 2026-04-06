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
from _secrets import BRAIN_DB_DICT

import hype_cache as hc

# Speed tracker for stale winner/loser detection
try:
    from speed_tracker import SpeedTracker, get_token_speed
    SPEED_TRACKER = SpeedTracker()
except Exception as e:
    print(f"[Position Manager] SpeedTracker unavailable: {e}")
    SPEED_TRACKER = None

# Speed feature: stale winner/loser exit logic
# Tokens that are in profit but flat for 15+ min should be closed (book profits).
# Tokens that are in loss but flat for 30+ min should be cut (dead positions).
STALE_WINNER_TIMEOUT_MINUTES = 15  # close winners who've been stale for 15+ min
STALE_LOSER_TIMEOUT_MINUTES = 30  # close losers who've been stale for 30+ min
STALE_WINNER_MIN_PROFIT = 1.0    # % profit required to be a "winner"
STALE_LOSER_MAX_LOSS = -1.0      # % loss (more negative) required to be a "loser"
# Speed threshold: velocity < 0.2% over 5 min = stale
STALE_VELOCITY_THRESHOLD = 0.2   # % change — below this = flat/stale

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
_PM_HEARTBEAT_FILE = '/var/www/hermes/data/pipeline_heartbeat.json'
MAX_POSITIONS = 10

# ─── Thresholds ────────────────────────────────────────────────────────────────
CUT_LOSER_PNL = -2.0   # cut if pnl_pct <= -2.0%
TP_PCT        = 0.08          # 8% target (used in get_trade_params for reference)
SL_PCT = 0.03          # 3% stop loss (cut loser threshold — DEFAULT fallback)
SL_PCT_MIN = 0.01      # minimum SL for any trade
MAX_LEVERAGE = 5

# ─── Trailing Stop-Loss Config ─────────────────────────────────────────────────
# Default fallback values (used when trade has no per-trade trailing settings)
TRAILING_START_PCT_DEFAULT   = 0.01   # engage at +1% profit (ATR-aware below)
TRAILING_BUFFER_PCT_DEFAULT  = 0.003  # keep 0.3% buffer above entry when first activated
TRAILING_PHASE2_BUFFER_DEFAULT = 0.002 # Phase 2: 0.2% buffer (floor — tightened 2026-04-05)
# ── ATR-aware trailing parameters ───────────────────────────────────────────
# These are multipliers on ATR.  Activate trailing when profit >= ATR_MULT_START × ATR.
# Buffer = ATR_MULT_BUFFER × ATR (floored at TRAILING_BUFFER_MIN_ABS).
TRAILING_ATR_MULT_START   = 1.0   # activate at 1× ATR profit
TRAILING_ATR_MULT_BUFFER = 0.30  # buffer = 30% of ATR
TRAILING_BUFFER_MIN_ABS  = 0.002 # 0.2% absolute floor (per 1% trailing)
# Volume-confirmed tightening: when candle volume > 24h MA in trade direction
# LONG → buy volume > MA  |  SHORT → sell volume > MA
# Gives more room on high-momentum moves, tighter on low-volume
TRAILING_VOL_CONF_BUFFER   = 0.0035  # 0.35% buffer when volume confirms direction
TRAILING_VOL_NO_CONF_BUFFER = 0.0025  # 0.25% buffer when volume is weak/absent
TRAILING_VOL_LOOKBACK      = 24      # candles for volume MA
TRAILING_TIGHTEN = True      # tighten buffer as profit grows
TRAILING_DATA_FILE = '/var/www/hermes/data/trailing_stops.json'
VOLUME_CACHE_FILE  = '/var/www/hermes/data/volume_cache.json'
VOLUME_CACHE_TTL  = 60       # seconds — one fetch per pipeline minute

# ── Cascade Flip Config ──────────────────────────────────────────────────────
# When an open position is losing AND an opposite signal fires with strong conf,
# cascade flip: close the losing position AND enter the opposite direction.

# BUG-8 fix: Push trailing SL updates to Hyperliquid.
# The position_manager computes trailing SL and writes it to brain DB, but the
# actual HL stop-loss order was never updated when trailing tightened.
# cascade flip: close the losing position AND enter the opposite direction.
CASCADE_FLIP_ARM_LOSS        = -0.25  # System ARMED at this loss % (speed check activates)
CASCADE_FLIP_TRIGGER_LOSS   = -0.50  # FLIP fires at this loss % (if armed + speed increasing)
CASCADE_FLIP_HF_TRIGGER_LOSS = -0.35  # Fast flip: high-momentum tokens (speed pctl > 80)
CASCADE_FLIP_MIN_CONF        = 60.0   # Opposite signal must have conf >= this % (lowered from 70)
CASCADE_FLIP_MAX_AGE_M       = 30     # Opposite signal must be created within this many minutes (expanded from 15)
CASCADE_FLIP_MIN_TYPES       = 1     # Opposite signal must have at least this many agreeing signal types
CASCADE_FLIP_MAX             = 3      # Max flips per token (permanent lockout after)
CASCADE_FLIP_POST_TRAIL_PCT  = 0.5    # Post-flip trailing SL window (tight — 0.5%)
FLIP_COUNTS_FILE            = '/var/www/hermes/data/flip_counts.json'

# ── MACD-Triggered Cascade Flip ───────────────────────────────────────────────
# Tokens where MACD 1H crossing under signal (while LONG) or crossing over (while SHORT)
# triggers an immediate cascade flip — regardless of PnL.
# These are tokens where we entered at a local peak and MACD confirms reversal.
# Added 2026-04-06 based on TRB/IMX/SOPH/SCR post-mortems.
MACD_CASCADE_FLIP_TOKENS = {'TRB', 'IMX', 'SOPH', 'SCR'}

# ─── Cascade Flip Helpers ─────────────────────────────────────────────────────

def _load_flip_counts() -> dict:
    """Load persisted flip counts. Returns {TOKEN: {flips, last_flip_dir, last_flip_time}}"""
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
        os.makedirs(os.path.dirname(FLIP_COUNTS_FILE), exist_ok=True)
        with open(FLIP_COUNTS_FILE, 'w') as f:
            json.dump(counts, f, indent=2)
    except Exception as e:
        print(f"  [Flip Count] ⚠️ Failed to persist flip counts: {e}")


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
                   trailing_activation, trailing_distance, trailing_phase2_dist
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
            if stale_minutes >= 30:  # Give winners more time — 30 min stall
                reason = f"stalled_winner_pnl{live_pnl:+.1f}%_spd{speed_pctl:.0f}_vel{vel_5m:+.3f}%_{stale_minutes}m"
                return True, reason

    return False, ""


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
        is_loss = pnl_usdt_val < 0
        if is_loss:
            set_loss_cooldown(token, direction)
            # Post-mortem: if we lost on a direction, was the market moving against us first?
            _analyze_loss_direction(token, direction, entry_price, current_price)

        # ── Trigger win cooldown ──────────────────────────────────
        # Also: clear loss streak since WIN confirms this was the right direction
        is_win = pnl_usdt_val > 0
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
# ATR-based SL for position_manager internal use.
# Imports the same ATR engine from decider-run (shared module-level cache).

def _pm_get_atr(token: str, period: int = 14, interval: str = '1h') -> float | None:
    """
    Fetch ATR(14) for token. Reuses _ATR_CACHE from decider-run if available
    via module-level cache. Falls back to direct HL API call.
    """
    import time as _time
    _ATR_TTL = 300

    # Try decider-run's cache first (shared process memory)
    try:
        from decider_run import _ATR_CACHE as _dr_cache
        cache_key = (token.upper(), interval)
        if cache_key in _dr_cache:
            atr_val, ts = _dr_cache[cache_key]
            if _time.time() - ts < _ATR_TTL:
                return atr_val
    except Exception:
        pass

    # Direct fetch
    try:
        from hyperliquid.info import Info
        info = Info('https://api.hyperliquid.xyz', skip_ws=True)
        now = _time.time()
        end_t = int(now * 1000)
        start_t = end_t - (60 * 60 * 1000 * (period + 5))
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


def _pm_atr_multiplier(atr_pct: float) -> float:
    if atr_pct < 0.01:
        return 1.5
    elif atr_pct > 0.03:
        return 2.5
    else:
        return 2.0


def get_trade_params(direction: str, price: float, max_leverage: int = MAX_LEVERAGE,
                     token: str = '', sl_pct_fallback: float = 0.015) -> Dict:
    """
    Compute SL and TP for a new trade.
    SL is ATR(14)-based:
      ATR < 1%  → k=1.5 (LOW_VOL)
      ATR 1-3%  → k=2.0 (NORMAL)
      ATR > 3%  → k=2.5 (HIGH_VOL)
    Falls back to sl_pct_fallback if ATR unavailable or token not provided.
    TP is fixed 8% target.
    """
    MIN_ATR_PCT = 0.0075
    MAX_SL_PCT  = 0.05
    STOP_LOSS_DEFAULT = 0.03   # 3% fallback SL if everything fails

    direction = direction.upper()
    leverage = min(max_leverage, MAX_LEVERAGE)

    token = token.upper().strip()

    # ── ATR-based SL ─────────────────────────────────────────────────────
    if token:
        atr = _pm_get_atr(token)
        if atr is not None:
            atr_pct = atr / price
            k = _pm_atr_multiplier(atr_pct)
            atr_sl_pct = (k * atr) / price
            effective_sl_pct = max(atr_sl_pct, MIN_ATR_PCT)
            effective_sl_pct = min(effective_sl_pct, MAX_SL_PCT)
        else:
            effective_sl_pct = sl_pct_fallback
    else:
        effective_sl_pct = sl_pct_fallback

    if direction == "LONG":
        stop_loss = round(price * (1 - effective_sl_pct), 8)
        target = round(price * (1 + TP_PCT), 8)
    elif direction == "SHORT":
        stop_loss = round(price * (1 + effective_sl_pct), 8)
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


# ─── Volume Confirmation Cache (HL candles via ccxt) ────────────────────────────
# One fetch per 60s — shared across all trades in the same pipeline run.

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
        os.replace(tmp, VOLUME_CACHE_FILE)
    except Exception as e:
        print(f"[Position Manager] _save_volume_cache error: {e}")


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


def get_volume_confirmation(token: str, direction: str) -> bool:
    """
    Returns True if the most recent candle volume confirms the trade direction:
      LONG  → vol_last > vol_ma  (buy-side volume above average)
      SHORT → vol_last > vol_ma  (sell-side volume above average)

    Volume data is fetched ONCE per 60s and cached in VOLUME_CACHE_FILE.
    All subsequent calls within the same cycle return the cached result.
    """
    import time as _time
    data = _load_volume_cache()
    now = _time.time()

    # Cache hit — still fresh
    if data.get(token) and (now - data[token].get("ts", 0)) < VOLUME_CACHE_TTL:
        return data[token].get("confirmed", False)

    # Cache miss — fetch fresh
    fresh = _fetch_volume_data(token)
    if not fresh:
        return False  # Fail closed: no data = no relaxed buffer

    data[token] = fresh
    _save_volume_cache(data)
    return fresh.get("confirmed", False)


def has_volume_confirmation(token: str, direction: str) -> bool:
    """Alias for get_volume_confirmation — volume confirms directional move."""
    return get_volume_confirmation(token, direction)


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
    token = str(trade.get("token", "")).upper()

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
    # Post-flip override: cascade-flipped positions use tighter 0.5% trailing window
    # instead of the default 1% activation / variable buffer.
    source = str(trade.get('source') or '')
    if source.startswith('cascade-reverse-'):
        trailing_start  = CASCADE_FLIP_POST_TRAIL_PCT  # 0.5% activation
        trailing_buffer = CASCADE_FLIP_POST_TRAIL_PCT  # 0.5% buffer — tight
        phase2_dist     = None   # Disable phase2 tightening for post-flip
    # Phase 2: tighter trailing once profit doubles from activation threshold
    phase2_dist      = trade.get('trailing_phase2_dist')  # DB column: trailing_phase2_dist
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

    # ATR-aware buffer: buffer = 30% of ATR (floored at absolute minimum).
    # Falls back to per-trade / global defaults if ATR unavailable.
    atr_for_buffer = _pm_get_atr(token) if token else None
    if atr_for_buffer is not None:
        atr_buffer_pct = TRAILING_ATR_MULT_BUFFER * atr_for_buffer / entry_price
        # Absolute floor so low-price tokens don't get razor buffers
        atr_buffer_pct = max(atr_buffer_pct, TRAILING_BUFFER_MIN_ABS)
        if trailing_buffer == 0:
            trailing_buffer = atr_buffer_pct
        # Phase 2 also gets ATR treatment
        if phase2_dist == 0 or phase2_dist is None:
            phase2_buffer_atr = TRAILING_ATR_MULT_BUFFER * 0.7 * atr_for_buffer / entry_price
            phase2_buffer_atr = max(phase2_buffer_atr, TRAILING_BUFFER_MIN_ABS * 0.7)
    # If phase2 activated but per-trade phase2_dist is None, use global default
    if trade_data.get("phase2_activated") and phase2_dist:
        active_buffer = float(phase2_dist)
    elif trade_data.get("phase2_activated"):
        # Phase 2: use ATR-based buffer if available, else volume-confirmed
        if 'phase2_buffer_atr' in dir() and atr_for_buffer is not None:
            active_buffer = phase2_buffer_atr
        else:
            token=str(trade.get("token", "")).upper()
            vol_confirmed = has_volume_confirmation(token, direction)
            if vol_confirmed:
                active_buffer = TRAILING_VOL_CONF_BUFFER   # 0.35% — room for high-momentum
            else:
                active_buffer = TRAILING_VOL_NO_CONF_BUFFER  # 0.25% — tighten on weak volume
    else:
        active_buffer = trailing_buffer

    # Calculate buffer — tighter floor, faster tighten as profit grows.
    # SHORT pnl is positive when in profit (entry > current).
    # Formula: buffer% at 5% pnl → floor at 25%+.
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
    """
    Fetch live prices from Hyperliquid, update pnl_pct in brain DB for open positions.

    FIX (2026-04-03): Use HL's authoritative unrealized_pnl directly instead of
    computing from mids (which was stale/wrong due to per-fill averaging).
    HL's unrealized_pnl = (entryPx - currentPx) / entryPx * positionValue * leverage
    This is the GROUND TRUTH — use it for all exit decisions.

    DB↔HL reconciliation (orphans/ghosts) is handled exclusively by
    hl-sync-guardian.py (60s cycle). This function ONLY updates current_price
    and pnl_pct for positions already confirmed in the DB.
    """

    # Get brain DB positions (source of truth for trade IDs and metadata)
    positions = get_open_positions(server)
    if not positions:
        return []

    # Get HL's authoritative position data (includes unrealized_pnl)
    try:
        hl_positions = get_open_hype_positions()
    except Exception as e:
        print(f"  [Position Manager] Failed to fetch HL positions: {e}")
        return positions

    if not hl_positions:
        return []

    # Fetch live mids for current_price (more accurate than deriving from unrealized_pnl)
    try:
        mids = hc.get_allMids()
    except Exception as e:
        print(f"  [Position Manager] Failed to fetch mids: {e}")
        mids = {}

    # Warn if paper trading without HL access
    if not HYPE_AVAILABLE:
        print(f"  [Position Manager] WARNING: Paper trading WITHOUT Hyperliquid — prices may be stale")

    updated = 0
    for pos in positions:
            token = str(pos.get('token') or '').upper()
            trade_id = pos.get('id')
            entry = float(pos.get('entry_price') or 0)
            leverage = float(pos.get('leverage') or 1)
            if not entry or not trade_id:
                continue

            # Get HL authoritative data for this token
            hl_data = hl_positions.get(token)
            if not hl_data:
                continue

            hl_entry = float(hl_data.get('entry_px', 0))
            hl_unrealized = float(hl_data.get('unrealized_pnl', 0))
            hl_size = float(hl_data.get('size', 0))

            if hl_size <= 0 or hl_entry <= 0:
                continue

            # pnl_pct from HL's unrealized_pnl (ground truth)
            # unrealized_pnl = (entryPx - currentPx) / entryPx * positionValue
            # where positionValue = entryPx * size (leverage already baked into size)
            position_value = hl_entry * hl_size
            pnl_pct = (hl_unrealized / position_value) * 100 if position_value > 0 else 0
            pnl_pct = round(pnl_pct, 4)

            # current_price from mids (most accurate for DB)
            cur_price_str = mids.get(token, '0')
            try:
                cur_price = round(float(cur_price_str), 6)
            except:
                cur_price = 0

            # pnl_usdt = unrealized_pnl directly (already in USDT)
            pnl_usdt = round(hl_unrealized, 2)

            if cur_price > 0:
                # Update in-memory so subsequent checks use fresh values
                pos['pnl_pct'] = pnl_pct
                pos['current_price'] = cur_price
                pos['pnl_usdt'] = pnl_usdt
                updated += 1

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

    # ── Volume cache warm-up ──────────────────────────────────────────────
    # Pre-fetch volume data for all open positions before trailing SL evaluation.
    # Lazy-warms the cache so subsequent has_volume_confirmation() calls are instant.
    _warmup_volume_cache_pm([p.get("token") for p in positions])

    # SPEED FEATURE: update speed tracker once per pipeline run (<2s)
    if SPEED_TRACKER is not None:
        SPEED_TRACKER.update()

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
        # ATR-aware activation: use ATR-based threshold unless A/B test overrides.
        # SHORTs activate trailing only when in profit (pnl_pct positive = price moved down).
        # Never activate on loss — cascade_flip handles reversals, cut_loser is the safety net.
        token_for_atr = token if token else ''
        atr_for_trailing = _pm_get_atr(token_for_atr) if token_for_atr else None
        trailing_start_pct = float(pos.get('trailing_activation') or 0)  # A/B override?
        if atr_for_trailing is not None and trailing_start_pct == 0:
            # No A/B override — use ATR-based activation threshold
            trailing_start_atr = atr_for_trailing * TRAILING_ATR_MULT_START  # 1× ATR profit
            trailing_start_pct = trailing_start_atr  # in absolute % terms (pnl_pct already %)
        elif trailing_start_pct == 0:
            # No ATR available and no A/B override — use global default
            trailing_start_pct = TRAILING_START_PCT_DEFAULT

        profit_pct = pnl_pct if direction == 'SHORT' else pnl_pct
        if profit_pct >= trailing_start_pct:
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

        # ── 2b. MACD-Rules Engine Cascade Flip (2026-04-06) ───────────────────
        # Use macd_rules.py for proper entry/exit/flip signal detection.
        # Replaces the simple cross_under/cross_over check with full state machine.
        if token.upper() in MACD_CASCADE_FLIP_TOKENS and not trailing_active:
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

            if mtf_all_flipped:
                # Ultra-confirmed cascade flip — all TFs flipped direction
                flip_info = {
                    'opposite_dir': 'SHORT' if direction == 'LONG' else 'LONG',
                    'conf': 95.0,
                    'source': 'mtf_macd_alignment',
                    'reason': 'all_tfs_reversed'
                }
                cascade_flipped = cascade_flip(
                    token, direction, trade_id,
                    live_pnl, flip_info,
                    entry=float(pos.get('entry_price') or 0)
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
            if cascade['cascade_active'] and cascade['cascade_direction'] and cascade['cascade_direction'] != direction:
                print(f"  [CASCADE FLIP] {token} {direction} → {cascade['cascade_direction']} "
                      f"(cascade active, lead={cascade['lead_tf']}, confirm={cascade['confirmation_count']}, "
                      f"reason={cascade['entry_block_reason']})")
                flip_info = {
                    'opposite_dir': cascade['cascade_direction'],
                    'conf': 95.0,
                    'source': 'cascade_direction',
                    'reason': f'cascade_{cascade["cascade_direction"].lower()}_confirmed'
                }
                cascade_flipped = cascade_flip(
                    token, direction, trade_id,
                    live_pnl, flip_info,
                    entry=float(pos.get('entry_price') or 0)
                )
                if cascade_flipped:
                    closed_count += 1
                    continue

            if macd_result['should_flip'] and macd_result['reasons']:
                primary_reason = macd_result['reasons'][0]
                print(f"  [MACD FLIP] {token} {direction} → flipping: {macd_result['reasons']}")
                flip_info = {
                    'opposite_dir': 'SHORT' if direction == 'LONG' else 'LONG',
                    'conf': 85.0,
                    'source': 'macd_rules_engine',
                    'reason': primary_reason[:80]
                }
                cascade_flipped = cascade_flip(
                    token, direction, trade_id,
                    live_pnl, flip_info,
                    entry=float(pos.get('entry_price') or 0)
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
        if not trailing_active and live_pnl <= CASCADE_FLIP_ARM_LOSS:
            flip_info = check_cascade_flip(token, direction, live_pnl, SPEED_TRACKER)
            if flip_info:
                cascade_flipped = cascade_flip(
                    token, direction, trade_id,
                    live_pnl, flip_info,
                    entry=float(pos.get('entry_price') or 0)
                )
                if cascade_flipped:
                    closed_count += 1
                    continue  # Position was flipped — skip remaining checks

        # ── 4. WAVE TURN EXIT (SPEED FEATURE) ─────────────────────────────────
        # Wave turn detection: z-score extreme AND acceleration flipping direction.
        # These exits fire BEFORE stale loser checks — wave turns are higher conviction.
        #
        # TOP FORMING:  z_score > +1.5 AND acceleration < 0 → close LONGs
        # BOTTOM FORMING: z_score < -1.5 AND acceleration > 0 → close SHORTs
        #
        # Rationale from surfing.md:
        # - Z-score far from mean = price has moved to an extreme
        # - Acceleration opposite to position direction = momentum shifting
        # - This is the "wave cresting" signal — close longs before the drop
        #
        # Only fires when trailing is NOT active (don't interfere with trailing exits).
        if not trailing_active:
            if SPEED_TRACKER is not None:
                spd = SPEED_TRACKER.get_token_speed(token)
                if spd:
                    z_score = spd.get('price_velocity_5m', 0)  # Use velocity_5m as z-proxy
                    accel = spd.get('price_acceleration', 0)
                    # Wave turn: extreme z-score (using velocity as proxy) + acceleration flipping
                    # For LONGs: z>1.5 (price elevated) + accel<0 (momentum turning down)
                    # For SHORTs: z<-1.5 (price depressed) + accel>0 (momentum turning up)
                    wave_turn = False
                    if direction == 'LONG' and z_score > 1.5 and accel is not None and accel < 0:
                        wave_turn = True
                        reason = f"wave_turn_top_z{z_score:+.2f}_acc{accel:+.4f}"
                    elif direction == 'SHORT' and z_score < -1.5 and accel is not None and accel > 0:
                        wave_turn = True
                        reason = f"wave_turn_bottom_z{z_score:+.2f}_acc{accel:+.4f}"

                    if wave_turn:
                        close_paper_position(trade_id, f"wave_turn_{reason}")
                        closed_count += 1
                        print(f"  🌊 WAVE TURN EXIT {token} {direction} {live_pnl:+.2f}% [{reason}]")
                        continue  # Position closed — skip remaining checks

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

        # ── 7. Update trailing SL in DB and push to Hyperliquid ─────
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
                    cur_pm.close()
                    conn_pm.close()
            except Exception:
                pass
            # BUG-8 fix: push updated trailing SL to Hyperliquid
            try:
                from hyperliquid_exchange import get_exchange, _hl_tick_round, _HL_TICK_DECIMALS
                exchange = get_exchange()
                decimals = _HL_TICK_DECIMALS.get(token, 6)
                sl_rounded = _hl_tick_round(trailing_sl, decimals)
                # Get position size from HL to set SL at correct size
                from hyperliquid_exchange import get_open_hype_positions
                positions = get_open_hype_positions() or {}
                size = 0.0
                for coin_name, p in positions.items():
                    if coin_name.upper() == token.upper():
                        size = float(p.get('szi', 0) or 0)
                        break
                if size > 0:
                    is_buy = direction.upper() == "SHORT"
                    order_type = {
                        "trigger": {
                            "triggerPx": sl_rounded,
                            "isMarket": True,
                            "tpsl": "sl",
                        }
                    }
                    exchange.order(token, is_buy, abs(size), sl_rounded, order_type, reduce_only=True)
                    print(f"  [BUG-8] Pushed trailing SL to HL: {token} {direction} SL=${sl_rounded:.6f}")
            except Exception as e:
                import traceback
                print(f"  [BUG-8] Failed to push trailing SL to HL ({token}): {e}")
                traceback.print_exc()

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

    # ── 5. Flip warranted ──────────────────────────────────────────────────────
    opposite_dir = 'SHORT' if position_direction == 'LONG' else 'LONG'

    db_path = '/root/.hermes/data/signals_hermes_runtime.db'
    if not os.path.exists(db_path):
        return None

    try:
        conn = sqlite3.connect(db_path, timeout=5)
        c = conn.cursor()
        # Confluence check: count distinct signal types agreeing on opposite direction
        # SKIPPED is included — the pipeline generated an opposite-direction signal but
        # couldn't enter (max positions, cooldown, etc.). That's valid confluence.
        c.execute("""
            SELECT COUNT(DISTINCT signal_type)
            FROM signals
            WHERE UPPER(token) = ?
              AND direction = ?
              AND decision IN ('PENDING', 'WAIT', 'APPROVED', 'SKIPPED')
              AND confidence >= ?
              AND created_at >= datetime('now', ?)
        """, (token.upper(), opposite_dir, CASCADE_FLIP_MIN_CONF,
              f'-{CASCADE_FLIP_MAX_AGE_M} minutes'))
        agreeing_types = c.fetchone()[0]
        if agreeing_types < CASCADE_FLIP_MIN_TYPES:
            conn.close()
            # ── 5b. No-confluence fallback: use coin-specific momentum as entry signal ─
            # If cascade flip triggers but there's no opposite signal in the DB,
            # use the token's own momentum/velocity as a coin-specific regime check.
            # This is the fallback for when the entire signal pipeline is wrong-dir
            # (like VVV SHORT — every signal was SHORT, nothing to flip into).
            #
            # Entry conditions (regime acts as the signal source for the opposite trade):
            #   LONG + price_velocity_5m < -1.0  → momentum turning down → flip to SHORT
            #   SHORT + price_velocity_5m > +1.0  → momentum turning up   → flip to LONG
            # Acceleration is directional confirmation (speed must be increasing).
            if speed_tracker is not None:
                try:
                    spd = speed_tracker.get_token_speed(token)
                    vel = spd.get('price_velocity_5m', 0) or 0
                    accel = spd.get('price_acceleration', 0) or 0
                    regime_conf = min(100.0, max(0.0, abs(vel) * 30))  # vel 1.0→30%, 2.0→60%
                    if position_direction == 'LONG' and vel < -1.0:
                        print(f"  [CASCADE FLIP] {token} no opposite signal confluence "
                              f"(need {CASCADE_FLIP_MIN_TYPES}, got {agreeing_types}), "
                              f"using coin-regime as entry signal: vel={vel:+.2f} accel={accel:+.4f} conf={regime_conf:.0f}%")
                        return {
                            'opposite_dir': opposite_dir,
                            'conf': regime_conf,
                            'source': 'coin-regime-fallback',
                            'sig_id': None,   # No DB signal — regime IS the signal
                            'price': 0,
                            'created_at': None,
                            'signal_type': 'coin-regime',
                        }
                    elif position_direction == 'SHORT' and vel > +1.0:
                        print(f"  [CASCADE FLIP] {token} no opposite signal confluence "
                              f"(need {CASCADE_FLIP_MIN_TYPES}, got {agreeing_types}), "
                              f"using coin-regime as entry signal: vel={vel:+.2f} accel={accel:+.4f} conf={regime_conf:.0f}%")
                        return {
                            'opposite_dir': opposite_dir,
                            'conf': regime_conf,
                            'source': 'coin-regime-fallback',
                            'sig_id': None,
                            'price': 0,
                            'created_at': None,
                            'signal_type': 'coin-regime',
                        }
                except Exception:
                    pass
            print(f"  [CASCADE FLIP] {token} flip triggered but no opposite confluence "
                  f"(need {CASCADE_FLIP_MIN_TYPES}, got {agreeing_types})")
            return None

        c.execute("""
            SELECT id, signal_type, source, confidence, price, created_at
            FROM signals
            WHERE UPPER(token) = ?
              AND direction = ?
              AND decision IN ('PENDING', 'WAIT', 'APPROVED', 'SKIPPED')
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

        print(f"  [CASCADE FLIP] ✅ {token} FLIP TRIGGERED "
              f"(loss={live_pnl:+.2f}%, pctl={percentile:.1f}%, "
              f"opp_conf={conf:.1f}%, src={source})")

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
    Uses HL reduce-only market order (close) then market order (open).
    Source string 'cascade-reverse-{src}' is used so post-flip trailing
    can detect flipped positions and use the tighter 0.5% window.

    Returns True if close succeeded (entry result doesn't block the return).
    """
    opposite_dir = flip_info['opposite_dir']
    conf = flip_info['conf']
    source = flip_info['source']
    sig_id = flip_info['sig_id']
    # Use cascade-reverse- prefix so should_use_trailing_stop() can detect
    # this is a post-flip position and apply the tighter 0.5% trailing window.
    source_tag = f"cascade-reverse-{source}"

    print(f"  [CASCADE FLIP] {token} {position_direction}→{opposite_dir} "
          f"(loss={live_pnl:+.2f}%, opp_conf={conf:.1f}%, src={source})")

    # ── 1. Close the losing position ───────────────────────────────────────────
    close_ok = close_paper_position(trade_id, f"cascade_flip_{live_pnl:+.2f}%")
    if not close_ok:
        print(f"  [CASCADE FLIP] ❌ Failed to close {token} #{trade_id}")
        return False

    # ── 2. Enter the opposite direction at current market price ───────────────
    # sig_id=None case: coin-regime-fallback — regime momentum IS the entry signal,
    # no DB signal to mark as executed. Proceed to entry with regime-based confidence.
    from hyperliquid_exchange import place_order, get_price
    try:
        current_price = get_price(token)
        if not current_price or current_price <= 0:
            current_price = flip_info.get('price') or 0
    except Exception:
        current_price = flip_info.get('price') or 0
    if not current_price or current_price <= 0:
        print(f"  [CASCADE FLIP] ❌ Could not get price for {token}")
        return True  # Position closed; new entry failed but not fatal

    # Get position size to maintain roughly same notional exposure
    # (use entry_price from the closed position as reference)
    if entry_price > 0 and current_price > 0:
        # Approximate: same dollar amount, different direction
        # close_position already closed the full size, so we re-enter with
        # the same size in the opposite direction.
        sz = None  # let place_order use its default sizing
    else:
        sz = None

    ok = place_order(
        name=token,
        side='BUY' if opposite_dir == 'LONG' else 'SELL',
        sz=sz,
        price=current_price,
        order_type='Market',
    )

    if ok and ok.get('success'):
        print(f"  [CASCADE FLIP] ✅ {token} {opposite_dir} entered @ ${current_price:.6f}")
        # ── 3. Persist flip count ─────────────────────────────────────────────
        flip_counts = _load_flip_counts()
        entry = flip_counts.get(token.upper(), {})
        flip_counts[token.upper()] = {
            'flips': entry.get('flips', 0) + 1,
            'last_flip_dir': opposite_dir,
            'last_flip_time': datetime.now().isoformat(),
        }
        _save_flip_counts(flip_counts)
        print(f"  [CASCADE FLIP] {token} flip count: "
              f"{flip_counts[token.upper()]['flips']}/{CASCADE_FLIP_MAX}")
        # ── 4. Mark triggering signal as executed ─────────────────────────────
        # Skip for coin-regime-fallback (sig_id=None) — no DB signal to update.
        if sig_id is not None:
            try:
                conn = sqlite3.connect('/root/.hermes/data/signals_hermes_runtime.db')
                c = conn.cursor()
                c.execute(
                    "UPDATE signals SET decision='EXECUTED', trade_id=? WHERE id=?",
                    (trade_id, sig_id)
                )
                conn.commit()
                conn.close()
            except Exception:
                pass
    else:
        err = ok.get('error', 'unknown') if ok else 'no response'
        print(f"  [CASCADE FLIP] ⚠️ {token} {opposite_dir} entry failed: {err} "
              f"(position closed, will retry next cycle)")

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
