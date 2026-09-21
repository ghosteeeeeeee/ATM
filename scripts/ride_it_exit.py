#!/usr/bin/env python3
"""
ride_it_exit.py — Ride-It Exit System

A 2-phase exit system designed to hold trades through delayed spikes.
Inspired by pump_exit's 3x ATR trail that survived BABY's +19% spike.

Phase 1 (Survival): Wide ATR-based SL, no trailing — survive the wait
Phase 2 (Trail): Tighter trail, momentum exit — lock in gains

Volume Spike Override: When volume >5x average, switch to tight 0.5% trail
immediately — catches explosive moves regardless of phase.

Usage:
    from ride_it_exit import manage_ride_it_exit
    result = manage_ride_it_exit(token, direction, current_price, pos, trade_id)
    # result = {'action': 'HOLD'} or {'action': 'TRAIL_SL', 'new_sl': ...} or {'action': 'EXIT', 'reason': ...}
"""

import os, sys, time
from datetime import datetime, timezone, timedelta

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPTS_DIR)

from paths import CANDLES_DB
from hermes_log import log

# ── Import constants ────────────────────────────────────────────────────────
try:
    from hermes_constants import (
        RIDE_IT_ENABLED,
        RIDE_IT_SL_PHASE1_MULT, RIDE_IT_SL_PHASE1_FLOOR, RIDE_IT_SL_PHASE1_CAP,
        RIDE_IT_TP_PHASE1_MULT,
        RIDE_IT_TRAIL_ACTIVATE, RIDE_IT_TRAIL_DISTANCE,
        RIDE_IT_MOMENTUM_VEL, RIDE_IT_MOMENTUM_CANDLES,
        RIDE_IT_SPIKE_VOLUME_MULT, RIDE_IT_SPIKE_TRAIL_DISTANCE, RIDE_IT_SPIKE_MIN_MOVE,
        RIDE_IT_PHASE1_TO_PHASE2_TIME,
        RIDE_IT_MAX_HOLD_HOURS,
    )
    _CONSTS_LOADED = True
except ImportError as e:
    _CONSTS_LOADED = False
    log(f"[RIDE-IT] Constants not loaded: {e}", 'WARN')


def _get_atr(token: str, period: int = 14) -> float:
    """Get ATR(14) from 1h candles."""
    conn = None
    try:
        import sqlite3
        conn = sqlite3.connect(CANDLES_DB, timeout=5)
        cur = conn.cursor()
        cur.execute("""
            SELECT open, high, low, close FROM candles_1h
            WHERE token = ? AND is_closed = 1
            ORDER BY ts DESC LIMIT ?
        """, (token.upper(), period + 5))
        rows = cur.fetchall()

        if len(rows) < period + 1:
            return 0

        trs = []
        for i in range(1, len(rows)):
            h, l, pc = rows[i][1], rows[i][2], rows[i - 1][3]
            trs.append(max(h - l, abs(h - pc), abs(l - pc)))
        return sum(trs[-period:]) / period
    except Exception as e:
        log(f"[RIDE-IT] ATR error for {token}: {e}", 'WARN')
        return 0
    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass


def _get_volume_ratio(token: str, lookback: int = 20) -> float:
    """Get current 5m volume / 20-bar average volume ratio."""
    conn = None
    try:
        import sqlite3
        conn = sqlite3.connect(CANDLES_DB, timeout=5)
        cur = conn.cursor()
        cur.execute("""
            SELECT volume FROM candles_5m
            WHERE token = ? AND is_closed = 1
            ORDER BY ts DESC LIMIT ?
        """, (token.upper(), lookback + 1))
        rows = [r[0] for r in cur.fetchall()]

        if len(rows) < lookback + 1:
            return 1.0

        current_vol = rows[0]
        avg_vol = sum(rows[1:]) / len(rows[1:]) if len(rows) > 1 else 1
        return current_vol / avg_vol if avg_vol > 0 else 1.0
    except Exception as e:
        log(f"[RIDE-IT] Volume ratio error for {token}: {e}", 'WARN')
        return 1.0
    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass


def _get_momentum_velocity(token: str, candles: int = 3) -> float:
    """Get recent 5m velocity (% change per candle)."""
    conn = None
    try:
        import sqlite3
        conn = sqlite3.connect(CANDLES_DB, timeout=5)
        cur = conn.cursor()
        cur.execute("""
            SELECT close FROM candles_5m
            WHERE token = ? AND is_closed = 1
            ORDER BY ts DESC LIMIT ?
        """, (token.upper(), candles + 1))
        closes = [r[0] for r in cur.fetchall()]

        if len(closes) < candles + 1:
            return 0

        velocities = []
        for i in range(1, len(closes)):
            if closes[i] > 0:
                vel = (closes[i - 1] - closes[i]) / closes[i] * 100
                velocities.append(vel)
        
        return sum(velocities) / len(velocities) if velocities else 0
    except Exception as e:
        log(f"[RIDE-IT] Momentum velocity error for {token}: {e}", 'WARN')
        return 0
    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass


def _get_neg_candle_count(token: str, candles: int = 3) -> int:
    """Count consecutive negative 5m candles (price dropping)."""
    conn = None
    try:
        import sqlite3
        conn = sqlite3.connect(CANDLES_DB, timeout=5)
        cur = conn.cursor()
        cur.execute("""
            SELECT close FROM candles_5m
            WHERE token = ? AND is_closed = 1
            ORDER BY ts DESC LIMIT ?
        """, (token.upper(), candles + 1))
        closes = [r[0] for r in cur.fetchall()]

        if len(closes) < 2:
            return 0

        neg_count = 0
        for i in range(1, len(closes)):
            if closes[i] > 0:
                pct_change = (closes[i - 1] - closes[i]) / closes[i] * 100
                if pct_change < RIDE_IT_MOMENTUM_VEL:
                    neg_count += 1
                else:
                    break
            else:
                break
        return neg_count
    except Exception as e:
        return 0
    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass


def _get_pos_candle_count(token: str, candles: int = 3) -> int:
    """Count consecutive positive 5m candles (price rising) — for SHORT momentum exit."""
    conn = None
    try:
        import sqlite3
        conn = sqlite3.connect(CANDLES_DB, timeout=5)
        cur = conn.cursor()
        cur.execute("""
            SELECT close FROM candles_5m
            WHERE token = ? AND is_closed = 1
            ORDER BY ts DESC LIMIT ?
        """, (token.upper(), candles + 1))
        closes = [r[0] for r in cur.fetchall()]

        if len(closes) < 2:
            return 0

        pos_count = 0
        for i in range(1, len(closes)):
            if closes[i] > 0:
                pct_change = (closes[i - 1] - closes[i]) / closes[i] * 100
                if pct_change > abs(RIDE_IT_MOMENTUM_VEL):
                    pos_count += 1
                else:
                    break
            else:
                break
        return pos_count
    except Exception as e:
        return 0
    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass


def _persist_sl(trade_id: int, new_sl: float) -> None:
    """Persist trailing SL to brain DB."""
    conn = None
    try:
        import psycopg2
        from _secrets import BRAIN_DB_DICT
        conn = psycopg2.connect(**BRAIN_DB_DICT)
        cur = conn.cursor()
        cur.execute("UPDATE trades SET stop_loss = %s WHERE id = %s", (new_sl, trade_id))
        conn.commit()
    except Exception as e:
        log(f"[RIDE-IT] Persist SL error: {e}", 'WARN')
    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass


def _parse_hold_time(open_time_val) -> float:
    """Parse open_time from various formats (datetime object, ISO string, etc). Returns hold hours."""
    try:
        if open_time_val is None:
            return 0
        
        # If it's already a datetime object (from psycopg2)
        if isinstance(open_time_val, datetime):
            entry_dt = open_time_val
            if entry_dt.tzinfo is None:
                entry_dt = entry_dt.replace(tzinfo=timezone.utc)
        # If it's a string
        elif isinstance(open_time_val, str):
            # Try ISO format with timezone
            try:
                entry_dt = datetime.fromisoformat(open_time_val.replace('Z', '+00:00'))
            except (ValueError, TypeError):
                try:
                    entry_dt = datetime.strptime(open_time_val, '%Y-%m-%d %H:%M:%S.%f')
                    entry_dt = entry_dt.replace(tzinfo=timezone.utc)
                except (ValueError, TypeError):
                    return 0
        else:
            return 0
        
        now = datetime.now(timezone.utc)
        hold_seconds = (now - entry_dt).total_seconds()
        return max(0, hold_seconds / 3600)
    except Exception:
        return 0


def manage_ride_it_exit(token: str, direction: str, current_price: float,
                        pos: dict, trade_id: int) -> dict:
    """
    Manage exit for Ride-It signals.
    
    Returns dict with:
        action: 'HOLD', 'TRAIL_SL', 'EXIT'
        reason: str (if EXIT)
        new_sl: float (if TRAIL_SL)
    """
    if not _CONSTS_LOADED:
        return {'action': 'HOLD'}
    
    if not RIDE_IT_ENABLED:
        return {'action': 'HOLD'}
    
    entry_price = float(pos.get('entry_price') or 0)
    current_sl = float(pos.get('stop_loss') or 0)
    highest_price = float(pos.get('highest_price') or entry_price)
    lowest_price = float(pos.get('lowest_price') or entry_price)
    open_time_val = pos.get('open_time')
    
    if not entry_price or not current_price or not open_time_val:
        return {'action': 'HOLD'}
    
    # Calculate hold time (handles datetime objects, ISO strings, etc)
    hold_hours = _parse_hold_time(open_time_val)
    hold_seconds = hold_hours * 3600
    
    # Calculate profit (direction-aware)
    if direction == 'LONG':
        profit_pct = (current_price - entry_price) / entry_price
    else:
        profit_pct = (entry_price - current_price) / entry_price
    
    # Get ATR
    atr = _get_atr(token)
    if atr <= 0:
        return {'action': 'HOLD'}
    
    atr_pct = atr / entry_price
    
    # ── Check Volume Spike Override (any phase) ──────────────────────────
    vol_ratio = _get_volume_ratio(token)
    if vol_ratio >= RIDE_IT_SPIKE_VOLUME_MULT and abs(profit_pct) >= RIDE_IT_SPIKE_MIN_MOVE:
        # Volume spike detected — switch to tight trail
        trail_distance = current_price * RIDE_IT_SPIKE_TRAIL_DISTANCE
        
        if direction == 'LONG':
            peak_price = max(current_price, highest_price)
            new_sl = peak_price - trail_distance
            should_update = new_sl > current_sl  # LONG: higher SL = tighter
        else:
            trough_price = min(current_price, lowest_price)
            new_sl = trough_price + trail_distance
            should_update = new_sl < current_sl  # SHORT: lower SL = tighter
        
        if should_update:
            _persist_sl(trade_id, new_sl)
            log(f"  [RIDE-IT-SPIKE] {token} {direction}: vol={vol_ratio:.1f}x profit={profit_pct*100:+.1f}% TRAIL_SL → ${new_sl:.6f}")
            return {'action': 'TRAIL_SL', 'new_sl': new_sl}
        return {'action': 'HOLD'}
    
    # ── Check Max Hold Time ──────────────────────────────────────────────
    if hold_hours >= RIDE_IT_MAX_HOLD_HOURS:
        reason = f"ride_it_max_hold: {hold_hours:.1f}h, {profit_pct*100:+.1f}%"
        log(f"  [RIDE-IT] {token} {direction}: {reason}")
        return {'action': 'EXIT', 'reason': reason}
    
    # ── Phase 1: Survival (0-2h) — Wide SL, no trailing ──────────────────
    if hold_seconds < RIDE_IT_PHASE1_TO_PHASE2_TIME:
        # Calculate ATR-based SL
        sl_distance = atr * RIDE_IT_SL_PHASE1_MULT
        sl_distance = max(sl_distance, entry_price * RIDE_IT_SL_PHASE1_FLOOR)
        sl_distance = min(sl_distance, entry_price * RIDE_IT_SL_PHASE1_CAP)
        
        if direction == 'LONG':
            phase1_sl = entry_price - sl_distance
            should_update = phase1_sl > current_sl  # LONG: higher SL = tighter
        else:
            phase1_sl = entry_price + sl_distance
            should_update = phase1_sl < current_sl  # SHORT: lower SL = tighter
        
        if should_update:
            _persist_sl(trade_id, phase1_sl)
            log(f"  [RIDE-IT-P1] {token} {direction}: SL → ${phase1_sl:.6f} ({sl_distance/entry_price*100:.1f}%)")
            return {'action': 'TRAIL_SL', 'new_sl': phase1_sl}
        
        return {'action': 'HOLD'}
    
    # ── Phase 2: Trail (2h+) — Tight trail + momentum exit ──────────────
    
    # Check momentum exit (DIRECTION-AWARE)
    # LONG: exit when price dropping (negative candles)
    # SHORT: exit when price rising (positive candles)
    if direction == 'LONG':
        bad_candles = _get_neg_candle_count(token, RIDE_IT_MOMENTUM_CANDLES)
    else:
        bad_candles = _get_pos_candle_count(token, RIDE_IT_MOMENTUM_CANDLES)
    
    if bad_candles >= RIDE_IT_MOMENTUM_CANDLES:
        # Only exit on momentum if we have something to protect
        if profit_pct > 0.01:  # >1% profit
            reason = f"ride_it_momentum: dir={direction}, bad_candles={bad_candles}, profit={profit_pct*100:+.1f}%"
            log(f"  [RIDE-IT] {token} {direction}: {reason}")
            return {'action': 'EXIT', 'reason': reason}
    
    # Check trailing activation (direction-aware)
    if profit_pct >= RIDE_IT_TRAIL_ACTIVATE:
        trail_distance = current_price * RIDE_IT_TRAIL_DISTANCE
        
        if direction == 'LONG':
            peak_price = max(current_price, highest_price)
            new_sl = peak_price - trail_distance
            should_update = new_sl > current_sl  # LONG: higher SL = tighter
        else:
            trough_price = min(current_price, lowest_price)
            new_sl = trough_price + trail_distance
            should_update = new_sl < current_sl  # SHORT: lower SL = tighter
        
        if should_update:
            _persist_sl(trade_id, new_sl)
            log(f"  [RIDE-IT-P2] {token} {direction}: TRAIL_SL → ${new_sl:.6f} (profit={profit_pct*100:+.1f}%)")
            return {'action': 'TRAIL_SL', 'new_sl': new_sl}
    
    return {'action': 'HOLD'}
