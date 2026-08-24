#!/usr/bin/env python3
"""
continuation.py V2 — Smart Re-entry After Profitable Close.

After a trade closes in profit, assess whether to:
  1. Re-enter SAME direction (momentum alive, trend strong = catch next wave)
  2. Re-enter OPPOSITE direction (move exhausted, overextended = fade the exhaustion)

V1 failed (40% WR) because it only fired same-direction with a 5-min window.
V2 adds:
  - Extended window (30min-1hr configurable)
  - Trend strength analysis (EMA slope, velocity, gap)
  - Exhaustion detection (overextension + velocity death = reverse)
  - Smart direction decision based on market state
  - Wave counting (diminishing returns after wave 2+)

Signal types:
  - continuation_long  : LONG re-entry (same or reversal)
  - continuation_short : SHORT re-entry (same or reversal)

Data: PostgreSQL (trades) + candles.db (1m, 5m, 1h)
Speed: Fast (single-token poll per recent close)
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
    # V2 params
    CONTINUATION_EMA_PERIOD,
    CONTINUATION_SLOPE_PERIOD,
    CONTINUATION_VELOCITY_PERIOD,
    CONTINUATION_SLOPE_THRESHOLD,
    CONTINUATION_VELOCITY_THRESHOLD,
    CONTINUATION_EXHAUST_RSI_LONG,
    CONTINUATION_EXHAUST_RSI_SHORT,
    CONTINUATION_EXHAUST_ZSCORE,
    CONTINUATION_EXHAUST_GAP_PCT,
    CONTINUATION_WAVE_COOLDOWN_SEC,
    CONTINUATION_WAVE_MAX,
    CONTINUATION_CONF_BASE,
    CONTINUATION_CONF_FLOOR,
    CONTINUATION_CONF_CAP,
    CONTINUATION_CONF_EXHAUST_BONUS,
    CONTINUATION_CONF_TREND_BONUS,
    CONTINUATION_CONF_WAVE_PENALTY,
    CONTINUATION_COOLDOWN_MIN,
    # V2 additional tunables
    CONTINUATION_PULLBACK_THRESHOLD,
    CONTINUATION_CONF_ORIG_HIGH,
    CONTINUATION_CONF_ORIG_MED,
    CONTINUATION_CONF_1H_ALIGN,
    CONTINUATION_CONF_1H_RET_THRESHOLD,
    LONG_BLACKLIST,
    SHORT_BLACKLIST,
)

# ── Signal types & sources ────────────────────────────────────────────────
SIGNAL_TYPE_LONG  = 'continuation_long'
SIGNAL_TYPE_SHORT = 'continuation_short'
SOURCE_LONG       = 'continuation+'
SOURCE_SHORT      = 'continuation-'

_CANDLES_DB = os.path.join(HERMES_DATA, 'candles.db')
_VALID_TABLES = frozenset({'candles_1m', 'candles_5m', 'candles_15m', 'candles_1h', 'candles_4h'})

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
    if table not in _VALID_TABLES:
        return []
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
    if table not in _VALID_TABLES:
        return []
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


def _compute_ema(closes, period):
    """Compute EMA of closes, return latest value."""
    if len(closes) < period:
        return None
    k = 2.0 / (period + 1)
    ema = closes[0]
    for p in closes[1:]:
        ema = p * k + ema * (1 - k)
    return ema


def _compute_slope(closes, period):
    """Linear regression slope over last `period` bars, normalized as % per bar."""
    if len(closes) < period:
        return None
    chunk = closes[-period:]
    x_mean = (period - 1) / 2.0
    y_mean = sum(chunk) / period
    denom = sum((i - x_mean) ** 2 for i in range(period))
    if denom == 0 or y_mean == 0:
        return 0
    numer = sum((i - x_mean) * (chunk[i] - y_mean) for i in range(period))
    return (numer / denom) / y_mean * 100


def _compute_velocity(closes, period):
    """Velocity: rate of change over last `period` bars, % per bar."""
    if len(closes) < period + 1:
        return None
    ret = (closes[-1] - closes[-period - 1]) / closes[-period - 1] * 100
    return ret / period  # % per bar


# ═══════════════════════════════════════════════════════════════════════════════
# Trend analysis — the core V2 intelligence
# ═══════════════════════════════════════════════════════════════════════════════

def _analyze_trend(token):
    """Analyze current trend state for a token.
    
    Returns dict with trend metrics or None if insufficient data.
    """
    # 1m candles for velocity/slope (fast reacting)
    closes_1m = _get_closes(token, 'candles_1m', 120)
    # 5m candles for medium-term context
    closes_5m = _get_closes(token, 'candles_5m', 50)
    # 1h candles for exhaustion checks
    closes_1h = _get_closes(token, 'candles_1h', 30)
    
    if not closes_1m or len(closes_1m) < 60:
        return None
    
    result = {}
    
    # ── 1m trend metrics ────────────────────────────────────────────────
    # EMA gap: price vs EMA (positive = above, negative = below)
    ema = _compute_ema(closes_1m, CONTINUATION_EMA_PERIOD)
    if ema and ema > 0:
        result['gap_pct'] = (closes_1m[-1] - ema) / ema * 100
    else:
        result['gap_pct'] = 0
    
    # Slope: trend direction and strength
    result['slope'] = _compute_slope(closes_1m, CONTINUATION_SLOPE_PERIOD) or 0
    
    # Velocity: recent momentum direction and speed
    result['velocity'] = _compute_velocity(closes_1m, CONTINUATION_VELOCITY_PERIOD) or 0
    
    # ── 5m trend context ────────────────────────────────────────────────
    if closes_5m and len(closes_5m) >= 10:
        result['ret_5m'] = (closes_5m[-1] - closes_5m[-10]) / closes_5m[-10] * 100
        result['slope_5m'] = _compute_slope(closes_5m, 10) or 0
    else:
        result['ret_5m'] = 0
        result['slope_5m'] = 0
    
    # ── 1h exhaustion metrics ───────────────────────────────────────────
    if closes_1h and len(closes_1h) >= 20:
        result['rsi'] = _compute_rsi(closes_1h)
        result['zscore'] = _compute_zscore(closes_1h)
        result['ret_1h'] = (closes_1h[-1] - closes_1h[-5]) / closes_1h[-5] * 100 if len(closes_1h) >= 5 else 0
    else:
        result['rsi'] = None
        result['zscore'] = None
        result['ret_1h'] = 0
    
    result['price'] = closes_1m[-1]
    return result


def _is_exhausted(trend, direction):
    """Check if the move is exhausted (overextended + velocity dying).
    
    Returns True if exhaustion detected — signal should REVERSE.
    """
    rsi = trend.get('rsi')
    zscore = trend.get('zscore')
    gap = trend.get('gap_pct', 0)
    velocity = trend.get('velocity', 0)
    
    if direction == 'LONG':
        # Exhausted LONG: overbought + extended above EMA + velocity dying
        if rsi is not None and rsi > CONTINUATION_EXHAUST_RSI_LONG:
            return True
        if zscore is not None and zscore > CONTINUATION_EXHAUST_ZSCORE:
            return True
        if gap > CONTINUATION_EXHAUST_GAP_PCT and velocity < 0:
            return True
    else:  # SHORT
        # Exhausted SHORT: oversold + extended below EMA + velocity dying
        if rsi is not None and rsi < CONTINUATION_EXHAUST_RSI_SHORT:
            return True
        if zscore is not None and zscore < -CONTINUATION_EXHAUST_ZSCORE:
            return True
        if gap < -CONTINUATION_EXHAUST_GAP_PCT and velocity > 0:
            return True
    
    return False


def _is_trend_alive(trend, direction):
    """Check if the trend is still alive in the given direction.
    
    Returns True if momentum is healthy and trend is intact.
    """
    slope = trend.get('slope', 0)
    velocity = trend.get('velocity', 0)
    slope_5m = trend.get('slope_5m', 0)
    ret_5m = trend.get('ret_5m', 0)
    
    if direction == 'LONG':
        # Trend alive if slope positive, velocity positive, or 5m showing strength
        return (slope > CONTINUATION_SLOPE_THRESHOLD or
                velocity > CONTINUATION_VELOCITY_THRESHOLD or
                (slope_5m > 0 and ret_5m > 0))
    else:  # SHORT
        return (slope < -CONTINUATION_SLOPE_THRESHOLD or
                velocity < -CONTINUATION_VELOCITY_THRESHOLD or
                (slope_5m < 0 and ret_5m < 0))


def _decide_direction(trend, original_direction):
    """Smart direction decision based on trend state.
    
    Returns (direction, reason):
      - (original, 'continuation') if trend alive in original direction
      - (opposite, 'exhaustion') if move is exhausted
      - (None, 'skip') if unclear/no edge
    """
    exhausted = _is_exhausted(trend, original_direction)
    alive = _is_trend_alive(trend, original_direction)
    
    if exhausted:
        # Move is maxed out — fade it
        opposite = 'SHORT' if original_direction == 'LONG' else 'LONG'
        return opposite, 'exhaustion'
    
    if alive:
        # Trend still has juice — ride it
        return original_direction, 'continuation'
    
    # Neither clearly alive nor clearly exhausted — no edge
    return None, 'skip'


# ═══════════════════════════════════════════════════════════════════════════════
# Trade close lookup
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


def _count_recent_continuations(token, direction):
    """Count how many continuation signals fired for this token recently.
    
    Used for wave penalty — diminishing returns after wave 2+.
    """
    conn = None
    try:
        from paths import RUNTIME_DB
        conn = sqlite3.connect(RUNTIME_DB, timeout=5)
        cur = conn.cursor()
        # Count signals in the last WAVE_COOLDOWN period
        cur.execute("""
            SELECT COUNT(*) FROM signals
            WHERE token = ? AND direction = ?
            AND signal_type LIKE 'continuation%'
            AND created_at > datetime('now', ? || ' seconds')
        """, (token.upper(), direction, -CONTINUATION_WAVE_COOLDOWN_SEC))
        row = cur.fetchone()
        return row[0] if row else 0
    except Exception:
        return 0
    finally:
        if conn:
            conn.close()


# ═══════════════════════════════════════════════════════════════════════════════
# Detection — V2 core logic
# ═══════════════════════════════════════════════════════════════════════════════

def detect_continuation(token, direction, close_info):
    """V2: Smart re-entry detection after profitable close.
    
    Analyzes trend state to decide:
    1. Same direction (continuation) — if trend alive
    2. Opposite direction (exhaustion fade) — if move maxed out
    3. Skip — if no edge
    
    Returns {direction, confidence, value, price, decision} or None.
    """
    # ── Analyze current trend state ─────────────────────────────────────
    trend = _analyze_trend(token)
    if not trend:
        return None
    
    # ── Smart direction decision ────────────────────────────────────────
    new_direction, decision = _decide_direction(trend, direction)
    
    if new_direction is None:
        return None  # no edge
    
    # ── Pullback guard: don't enter if price reversed too far ───────────
    exit_price = close_info['exit_price']
    current_price = trend['price']
    
    if direction == 'LONG':
        pullback = (exit_price - current_price) / exit_price * 100 if exit_price > 0 else 0
    else:
        pullback = (current_price - exit_price) / exit_price * 100 if exit_price > 0 else 0
    
    # If price moved against us more than threshold since close, skip
    if pullback > CONTINUATION_PULLBACK_THRESHOLD:
        return None
    
    # ── Confidence scoring ──────────────────────────────────────────────
    conf = CONTINUATION_CONF_BASE
    
    # Decision type bonus
    if decision == 'exhaustion':
        conf += CONTINUATION_CONF_EXHAUST_BONUS
    elif decision == 'continuation':
        # Trend alive bonus — stronger trend = higher confidence
        slope = abs(trend.get('slope', 0))
        velocity = abs(trend.get('velocity', 0))
        if slope > CONTINUATION_SLOPE_THRESHOLD * 2:
            conf += CONTINUATION_CONF_TREND_BONUS
        elif slope > CONTINUATION_SLOPE_THRESHOLD:
            conf += CONTINUATION_CONF_TREND_BONUS // 2
        if velocity > CONTINUATION_VELOCITY_THRESHOLD * 2:
            conf += CONTINUATION_CONF_TREND_BONUS // 2
    
    # Original signal confidence bonus
    if close_info['confidence'] >= 90:
        conf += CONTINUATION_CONF_ORIG_HIGH
    elif close_info['confidence'] >= 85:
        conf += CONTINUATION_CONF_ORIG_MED
    
    # 1h trend aligned bonus
    ret_1h = trend.get('ret_1h', 0)
    if (direction == 'LONG' and ret_1h > CONTINUATION_CONF_1H_RET_THRESHOLD) or \
       (direction == 'SHORT' and ret_1h < -CONTINUATION_CONF_1H_RET_THRESHOLD):
        conf += CONTINUATION_CONF_1H_ALIGN
    
    # Wave penalty + hard cap
    wave_count = _count_recent_continuations(token, direction)
    if wave_count >= CONTINUATION_WAVE_MAX:
        return None  # hard cap — too many waves, no edge
    if wave_count >= 2:
        conf -= CONTINUATION_CONF_WAVE_PENALTY * (wave_count - 1)
    
    conf = max(CONTINUATION_CONF_FLOOR, min(CONTINUATION_CONF_CAP, conf))
    
    return {
        'direction': new_direction,
        'confidence': conf,
        'value': close_info['pnl_pct'],
        'price': current_price,
        'decision': decision,
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
        
        # Layer 1: per-direction kill-switch (check ORIGINAL direction's kill-switch)
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
        
        # V2: Smart detection
        sig = detect_continuation(token, direction, close_info)
        if not sig:
            continue
        
        # Use the DECIDED direction (may be continuation or reversal)
        decided_direction = sig['direction']
        
        # Layer 1: check decided direction's kill-switch
        if decided_direction == 'LONG' and not CONTINUATION_PLUS_ENABLED:
            continue
        if decided_direction == 'SHORT' and not CONTINUATION_MINUS_ENABLED:
            continue
        
        # Layer 1: check decided direction's blacklist
        if decided_direction == 'LONG' and token in LONG_BLACKLIST:
            continue
        if decided_direction == 'SHORT' and token in SHORT_BLACKLIST:
            continue
        
        sig_type = SIGNAL_TYPE_LONG if decided_direction == 'LONG' else SIGNAL_TYPE_SHORT
        source = SOURCE_LONG if decided_direction == 'LONG' else SOURCE_SHORT
        
        decision_tag = sig.get('decision', 'unknown')
        
        if DRY_RUN:
            _log(f"  [DRY] {decision_tag:11s} {decided_direction:5s} {token:8s} "
                 f"from_pnl={close_info['pnl_pct']:+.2f}% conf={sig['confidence']}% "
                 f"orig_dir={direction} [{source}]")
            continue
        
        try:
            sid = add_signal(
                token=token,
                direction=decided_direction,
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
                # Also cooldown the decided direction if different
                if decided_direction != direction:
                    set_cooldown(token, decided_direction, hours=CONTINUATION_COOLDOWN_MIN / 60.0)
                _log(f"  {decision_tag:11s} {decided_direction:5s} {token:8s} "
                     f"from_pnl={close_info['pnl_pct']:+.2f}% conf={sig['confidence']}% "
                     f"orig_dir={direction} [{source}]")
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
