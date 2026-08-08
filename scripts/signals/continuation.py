#!/usr/bin/env python3
"""
continuation.py — Re-entry After Profitable Close.

When a trade closes in profit (profit-monster, T1, trail), scan for re-entry
in the same direction within a short window. The theory: momentum in the
current waters means more fish are likely around.

Data: PostgreSQL (trades) + candles.db (5m, 1h)
Speed: Fast (single-token poll, not full scan)

Signal types:
  - continuation_long  : LONG re-entry after LONG profit close
  - continuation_short : SHORT re-entry after SHORT profit close
"""

import os
import sys
import sqlite3
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from signal_schema import add_signal, get_cooldown, price_age_minutes, set_cooldown
from paths import HERMES_DATA

from hermes_constants import (
    CONTINUATION_ENABLED,
    CONTINUATION_PLUS_ENABLED,
    CONTINUATION_MINUS_ENABLED,
    CONTINUATION_MIN_PNL,
    CONTINUATION_WINDOW_SEC,
    CONTINUATION_TRIGGER_REASONS,
    CONTINUATION_RSI_MAX_LONG,
    CONTINUATION_RSI_MIN_SHORT,
    CONTINUATION_ZSCORE_MAX,
    CONTINUATION_PULLBACK_MAX_PCT,
    CONTINUATION_CONF_BASE,
    CONTINUATION_CONF_FLOOR,
    CONTINUATION_CONF_CAP,
    CONTINUATION_COOLDOWN_MIN,
    LONG_BLACKLIST,
    SHORT_BLACKLIST,
)

# ── Signal types & sources ────────────────────────────────────────────────
SIGNAL_TYPE_LONG  = 'continuation_long'
SIGNAL_TYPE_SHORT = 'continuation_short'
SOURCE_LONG       = 'continuation+'
SOURCE_SHORT      = 'continuation-'

_CANDLES_DB = os.path.join(HERMES_DATA, 'candles.db')

# ── Logging ───────────────────────────────────────────────────────────────
SIGNAL_LOG = '/var/www/hermes/logs/signals.log'
os.makedirs(os.path.dirname(SIGNAL_LOG), exist_ok=True)


def _log(msg):
    print(msg)
    try:
        with open(SIGNAL_LOG, 'a') as f:
            f.write(msg + '\n')
    except Exception:
        pass


DRY_RUN = '--dry' in sys.argv


# ═══════════════════════════════════════════════════════════════════════════════
# Data fetch
# ═══════════════════════════════════════════════════════════════════════════════

def _get_closes(token, table, limit):
    """Fetch close prices from candles.db, oldest first."""
    conn = None
    try:
        conn = sqlite3.connect(_CANDLES_DB, timeout=10)
        c = conn.cursor()
        c.execute(f"""
            SELECT close FROM {table}
            WHERE token = ? ORDER BY ts DESC LIMIT ?
        """, (token.upper(), limit))
        rows = c.fetchall()
        if not rows:
            return []
        return [r[0] for r in reversed(rows)]
    except Exception:
        return []
    finally:
        if conn:
            conn.close()


def _get_candle_range(token, table, limit):
    """Fetch (ts, open, high, low, close) from candles.db, oldest first."""
    conn = None
    try:
        conn = sqlite3.connect(_CANDLES_DB, timeout=10)
        c = conn.cursor()
        c.execute(f"""
            SELECT ts, open, high, low, close FROM {table}
            WHERE token = ? ORDER BY ts DESC LIMIT ?
        """, (token.upper(), limit))
        rows = c.fetchall()
        if not rows:
            return []
        return list(reversed(rows))
    except Exception:
        return []
    finally:
        if conn:
            conn.close()


# ═══════════════════════════════════════════════════════════════════════════════
# Indicator helpers
# ═══════════════════════════════════════════════════════════════════════════════

def _compute_rsi(closes, period=14):
    """RSI from close prices."""
    if len(closes) < period + 1:
        return None
    gains = []
    losses = []
    for i in range(-period, 0):
        diff = closes[i] - closes[i - 1]
        gains.append(max(0, diff))
        losses.append(max(0, -diff))
    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100 - 100 / (1 + rs)


def _compute_zscore(closes, period=20):
    """Z-score of current price vs recent mean."""
    if len(closes) < period:
        return None
    recent = closes[-period:]
    mean = sum(recent) / len(recent)
    std = (sum((x - mean) ** 2 for x in recent) / len(recent)) ** 0.5
    if std == 0:
        return 0
    return (closes[-1] - mean) / std


# ═══════════════════════════════════════════════════════════════════════════════
# Detection
# ═══════════════════════════════════════════════════════════════════════════════

def find_recent_close(token, direction):
    """Check if this token had a recent profitable close in given direction.
    
    Returns dict with close info or None.
    """
    conn = None
    try:
        from _secrets import BRAIN_DB_DICT
        import psycopg2
        conn = psycopg2.connect(**BRAIN_DB_DICT)
        cur = conn.cursor()
        cur.execute("""
            SELECT exit_price, pnl_pct, close_time, close_reason, signal, confidence
            FROM trades
            WHERE token = %s AND direction = %s AND status = 'closed'
            AND close_reason = ANY(%s)
            AND pnl_pct >= %s
            AND close_time > now() - make_interval(secs => %s)
            ORDER BY close_time DESC
            LIMIT 1
        """, (
            token.upper(), direction,
            list(CONTINUATION_TRIGGER_REASONS),
            CONTINUATION_MIN_PNL,
            CONTINUATION_WINDOW_SEC,
        ))
        row = cur.fetchone()
        if row:
            return {
                'exit_price': float(row[0]),
                'pnl_pct': float(row[1]),
                'close_time': row[2],
                'close_reason': row[3],
                'signal': row[4],
                'confidence': float(row[5]) if row[5] else 75,
            }
    except Exception as e:
        _log(f"  [continuation] DB error for {token}: {e}")
    finally:
        if conn:
            conn.close()
    return None


def detect_continuation(token, direction, close_info):
    """Check if re-entry conditions are met after a profitable close.
    
    Returns {direction, confidence, value, price} or None.
    """
    exit_price = close_info['exit_price']
    
    # ── 5m check: is momentum still alive? ───────────────────────────────
    candles_5m = _get_candle_range(token, 'candles_5m', 4)
    if not candles_5m or len(candles_5m) < 2:
        return None
    
    # Current price vs exit price
    current_price = candles_5m[-1][4]  # latest close
    
    # Pullback check: has price reversed more than CONTINUATION_PULLBACK_MAX_PCT?
    if direction == 'LONG':
        pullback = (exit_price - current_price) / exit_price * 100 if exit_price > 0 else 0
    else:
        pullback = (current_price - exit_price) / exit_price * 100 if exit_price > 0 else 0
    
    # If price moved further in our direction, great — no pullback concern
    # If price pulled back against us, check threshold
    if pullback > CONTINUATION_PULLBACK_MAX_PCT * (close_info['pnl_pct'] / 100):
        return None  # pulled back too much
    
    # ── 1h check: not exhausted ──────────────────────────────────────────
    closes_1h = _get_closes(token, 'candles_1h', 25)
    if closes_1h and len(closes_1h) >= 15:
        rsi = _compute_rsi(closes_1h)
        zscore = _compute_zscore(closes_1h)
        
        if rsi is not None:
            if direction == 'LONG' and rsi > CONTINUATION_RSI_MAX_LONG:
                return None  # overbought — don't re-enter LONG
            if direction == 'SHORT' and rsi < CONTINUATION_RSI_MIN_SHORT:
                return None  # oversold — don't re-enter SHORT
        
        if zscore is not None and abs(zscore) > CONTINUATION_ZSCORE_MAX:
            return None  # extreme z-score — mean reversion likely
    else:
        rsi = None
        zscore = None
    
    # ── Confidence ───────────────────────────────────────────────────────
    conf = CONTINUATION_CONF_BASE
    
    # Bonus: original signal confidence was high
    if close_info['confidence'] >= 90:
        conf += 3
    elif close_info['confidence'] >= 85:
        conf += 1
    
    # Bonus: 1h trend aligned
    if closes_1h and len(closes_1h) >= 5:
        ret_1h = (closes_1h[-1] - closes_1h[-5]) / closes_1h[-5] * 100
        if (direction == 'LONG' and ret_1h > 0.5) or (direction == 'SHORT' and ret_1h < -0.5):
            conf += 3
    
    # Penalty: RSI approaching extremes
    if rsi is not None:
        if direction == 'LONG' and rsi > 65:
            conf -= 5
        if direction == 'SHORT' and rsi < 35:
            conf -= 5
    
    conf = max(CONTINUATION_CONF_FLOOR, min(CONTINUATION_CONF_CAP, conf))
    
    return {
        'direction': direction,
        'confidence': conf,
        'value': close_info['pnl_pct'],
        'price': current_price,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# Scan — poll PostgreSQL for recent closes, check each
# ═══════════════════════════════════════════════════════════════════════════════

def scan_continuation_signals():
    """Scan for re-entry opportunities after recent profitable closes."""
    if not CONTINUATION_ENABLED:
        return 0
    
    # Get all tokens with recent profitable closes
    conn = None
    try:
        from _secrets import BRAIN_DB_DICT
        import psycopg2
        conn = psycopg2.connect(**BRAIN_DB_DICT)
        cur = conn.cursor()
        cur.execute("""
            SELECT DISTINCT token, direction
            FROM trades
            WHERE status = 'closed'
            AND close_reason = ANY(%s)
            AND pnl_pct >= %s
            AND close_time > now() - make_interval(secs => %s)
        """, (
            list(CONTINUATION_TRIGGER_REASONS),
            CONTINUATION_MIN_PNL,
            CONTINUATION_WINDOW_SEC,
        ))
        recent_closes = cur.fetchall()
    except Exception as e:
        _log(f"[continuation] DB scan error: {e}")
        return 0
    finally:
        if conn:
            conn.close()
    
    added = 0
    for token, direction in recent_closes:
        token = token.upper()
        
        # Price freshness check
        if price_age_minutes(token) > 5:
            continue
        
        # Layer 1: per-direction kill-switch
        if direction == 'LONG' and not CONTINUATION_PLUS_ENABLED:
            continue
        if direction == 'SHORT' and not CONTINUATION_MINUS_ENABLED:
            continue
        
        # Layer 1: blacklists
        if direction == 'LONG' and token in LONG_BLACKLIST:
            continue
        if direction == 'SHORT' and token in SHORT_BLACKLIST:
            continue
        
        # Cooldown
        if get_cooldown(token, direction=direction):
            continue
        
        # Get close details
        close_info = find_recent_close(token, direction)
        if not close_info:
            continue
        
        # Detect continuation
        sig = detect_continuation(token, direction, close_info)
        if not sig:
            continue
        
        sig_type = SIGNAL_TYPE_LONG if direction == 'LONG' else SIGNAL_TYPE_SHORT
        source = SOURCE_LONG if direction == 'LONG' else SOURCE_SHORT
        
        if DRY_RUN:
            _log(f"  [DRY] {direction:5s}-continuation {token:8s} "
                 f"from_pnl={close_info['pnl_pct']:+.2f}% conf={sig['confidence']}% "
                 f"src={close_info['signal']} [{source}]")
            continue
        
        try:
            sid = add_signal(
                token=token,
                direction=direction,
                signal_type=sig_type,
                source=source,
                confidence=sig['confidence'],
                value=sig.get('value'),
                price=sig['price'],
                exchange='hyperliquid',
                timeframe='5m',
            )
            if sid:
                added += 1
                set_cooldown(token, direction, hours=CONTINUATION_COOLDOWN_MIN / 60.0)
                _log(f"  {direction:5s}-continuation {token:8s} "
                     f"from_pnl={close_info['pnl_pct']:+.2f}% conf={sig['confidence']}% "
                     f"src={close_info['signal']} [{source}]")
        except Exception as e:
            _log(f"[continuation] add_signal error for {token}: {e}")
    
    return added


# ═══════════════════════════════════════════════════════════════════════════════
# Entry point
# ═══════════════════════════════════════════════════════════════════════════════

def run():
    """Entry point for signals_runner. Polls PostgreSQL for recent closes."""
    return scan_continuation_signals()


if __name__ == '__main__':
    from signal_schema import init_db
    init_db()
    n = scan_continuation_signals()
    print(f'continuation: {n} signals emitted')
