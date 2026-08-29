#!/usr/bin/env python3
"""bb_bounce_long — Bollinger Band Bounce LONG signal (solo variant).

V2 (2026-08-29): Separated from bb_bounce.py for independent testing.
Features velocity filter to catch falling knife entries.

Thesis: Mean reversion — price touches lower BB in ranging/neutral market,
RSI oversold, price bounces above lower band. Velocity filter ensures
price has stopped falling before entry.

Entry conditions:
1. Price within 0.15% of lower BB (BB_TOUCH_PCT)
2. RSI < 40 (oversold) or < 30 (solo mode)
3. 15m trend is BULLISH or NEUTRAL (not BEARISH)
4. Price above lower BB (bounce confirmed)
5. Bounce strength >= 0.05% (confluence) or 0.03% (solo)
6. 15m velocity > -0.015% (not falling hard)

Backtest context:
- Original bb_bounce+ LONG: 65T, 58.5% WR, +$0.32
- V2 velocity filter (backtest): 84.6% WR across 65 trades
"""
import sqlite3
import time
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
from paths import RUNTIME_DB, CANDLES_DB

# ── Parameters (all tunable via hermes_constants.py) ──────────────────────
from hermes_constants import (
    BB_BOUNCE_LONG_ENABLED,
    LONG_BLACKLIST,
    SHORT_BLACKLIST,
)

# BB parameters (same as bb_bounce.py for consistency)
BB_PERIOD = 20
BB_STDDEV = 1.8
BB_TOUCH_PCT = 0.15      # max distance from lower band to qualify
BB_MIN_BARS = 30
RSI_PERIOD = 14
RSI_OVERSOLD = 40        # confluence mode
SOLO_RSI_OVERSOLD = 30   # solo mode (deeper oversold required)
BOUNCE_MIN_PCT = 0.05    # confluence mode
SOLO_BOUNCE_MIN_PCT = 0.03  # solo mode

# V2 velocity filter
VEL_THRESHOLD = 0.015    # block if 15m velocity < -0.015% (price still falling)

# ── State ─────────────────────────────────────────────────────────────────
_cooldown = {}


def _log(msg):
    print(f"[bb-bounce-long] {msg}", flush=True)


def _compute_bb(closes, period=BB_PERIOD, stddev=BB_STDDEV):
    if len(closes) < period:
        return None, None, None
    middle = sum(closes[-period:]) / period
    variance = sum((c - middle) ** 2 for c in closes[-period:]) / period
    std = variance ** 0.5
    upper = middle + stddev * std
    lower = middle - stddev * std
    return middle, upper, lower


def _compute_rsi(closes, period=RSI_PERIOD):
    if len(closes) < period + 1:
        return None
    gains, losses = [], []
    for i in range(1, period + 1):
        delta = closes[-i] - closes[-i - 1]
        gains.append(max(delta, 0))
        losses.append(max(-delta, 0))
    avg_gain = sum(gains) / len(gains) if gains else 0
    avg_loss = sum(losses) / len(losses) if losses else 0.001
    rs = avg_gain / avg_loss if avg_loss > 0 else 100
    return 100 - (100 / (1 + rs))


def _get_15m_trend(token):
    """Check 15m EMA trend. Returns 'BULLISH', 'BEARISH', or 'NEUTRAL'."""
    conn = None
    try:
        conn = sqlite3.connect(CANDLES_DB, timeout=5)
        cur = conn.cursor()
        cur.execute("""
            SELECT close FROM candles_15m
            WHERE token = ?
            ORDER BY ts DESC
            LIMIT 60
        """, (token.upper(),))
        rows = cur.fetchall()
        if not rows or len(rows) < 50:
            return 'NEUTRAL'
        closes = [r[0] for r in reversed(rows)]

        def ema(data, period):
            k = 2 / (period + 1)
            val = data[0]
            for v in data[1:]:
                val = v * k + val * (1 - k)
            return val

        ema20 = ema(closes, 20)
        ema50 = ema(closes, 50)
        if ema50 == 0:
            return 'NEUTRAL'
        spread = abs(ema20 - ema50) / ema50 * 100
        if spread < 0.1:
            return 'NEUTRAL'
        return 'BULLISH' if ema20 > ema50 else 'BEARISH'
    except Exception:
        return 'NEUTRAL'
    finally:
        if conn:
            conn.close()


def _get_15m_velocity(token):
    """15m price velocity (% change over last 15 minutes).
    Reads from candles_1m (accurate, real-time)."""
    conn = None
    try:
        conn = sqlite3.connect(CANDLES_DB, timeout=5)
        c = conn.cursor()
        c.execute("""
            SELECT close FROM candles_1m
            WHERE token = ?
            ORDER BY ts DESC LIMIT 15
        """, (token.upper(),))
        rows = c.fetchall()
        if len(rows) < 5:
            return None
        closes = [r[0] for r in reversed(rows)]
        if closes[0] <= 0:
            return None
        return (closes[-1] - closes[0]) / closes[0] * 100
    except Exception:
        return None
    finally:
        if conn:
            conn.close()


def _get_candles(token, lookback=100):
    conn = None
    try:
        conn = sqlite3.connect(CANDLES_DB, timeout=10)
        cur = conn.cursor()
        cur.execute("""
            SELECT close FROM candles_5m
            WHERE token = ?
            ORDER BY ts DESC
            LIMIT ?
        """, (token.upper(), lookback))
        rows = cur.fetchall()
        return [r[0] for r in reversed(rows)] if rows else []
    except Exception:
        return []
    finally:
        if conn:
            conn.close()


def _is_solo(token, direction):
    """Check if this token+direction has any other active signals in DB."""
    conn = None
    try:
        conn = sqlite3.connect(RUNTIME_DB, timeout=5)
        cur = conn.cursor()
        cur.execute("""
            SELECT COUNT(*) FROM signals
            WHERE token = ? AND direction = ? AND signal_type != 'bb_bounce_long'
              AND created_at > datetime('now', '-10 minutes')
        """, (token.upper(), direction))
        count = cur.fetchone()[0]
        return count == 0
    except Exception:
        return True
    finally:
        if conn:
            conn.close()


def detect_bb_bounce_long(token, closes):
    """Detect BB bounce LONG with V2 velocity filter."""
    if len(closes) < BB_MIN_BARS:
        return None

    middle, upper, lower = _compute_bb(closes)
    if middle is None:
        return None

    current = closes[-1]

    # Compute RSI
    rsi = _compute_rsi(closes)
    if rsi is None:
        return None

    # Distance from lower band
    dist_from_lower = abs(current - lower) / lower * 100 if lower > 0 else 999

    # Check 15m trend
    trend = _get_15m_trend(token)

    # LONG: lower band + RSI oversold + bullish/neutral trend + bounce up
    if dist_from_lower <= BB_TOUCH_PCT:
        solo_l = _is_solo(token, 'LONG')
        rsi_thresh = SOLO_RSI_OVERSOLD if solo_l else RSI_OVERSOLD
        bounce_thresh = SOLO_BOUNCE_MIN_PCT if solo_l else BOUNCE_MIN_PCT

        # Quality filters
        if rsi > rsi_thresh:
            return None  # RSI not oversold enough
        if trend == 'BEARISH':
            return None  # Counter-trend

        # Check bounce strength — price must be above the band
        if current <= lower:
            return None  # Still below band, no bounce yet

        bounce_pct = (current - lower) / lower * 100 if lower > 0 else 0
        if bounce_pct < bounce_thresh:
            return None  # Bounce too weak

        # V2 velocity filter — block if price still falling hard
        vel = _get_15m_velocity(token)
        if vel is not None and vel < -VEL_THRESHOLD:
            return None  # Price still falling, bounce not confirmed

        return {
            'direction': 'LONG',
            'middle': middle,
            'upper': upper,
            'lower': lower,
            'rsi': rsi,
            'trend': trend,
            'bounce_pct': bounce_pct,
            'solo': solo_l,
            'velocity': vel,
        }

    return None


def scan_bb_bounce_long_signals(prices_dict):
    """Scan tokens for BB bounce LONG signals."""
    from signal_schema import add_signal, get_cooldown, set_cooldown
    from signal_gen import is_delisted

    added = 0
    now = time.time()

    for token, data in prices_dict.items():
        if token.startswith('@'):
            continue
        price = data.get('price')
        if not price or price <= 0:
            continue
        if is_delisted(token.upper()):
            continue

        # Kill switch
        if not BB_BOUNCE_LONG_ENABLED:
            continue

        # Blacklist check
        if token.upper() in LONG_BLACKLIST:
            continue

        # Cooldown check
        if get_cooldown(token, direction='LONG'):
            continue

        closes = _get_candles(token, 100)
        if not closes:
            continue

        sig = detect_bb_bounce_long(token, closes)
        if sig is None:
            continue

        # Confidence based on quality indicators
        base_conf = 70
        if sig['rsi'] < 30:
            base_conf += 10  # deeply oversold
        if sig['bounce_pct'] > 0.15:
            base_conf += 5   # strong bounce
        if sig['trend'] == 'BULLISH':
            base_conf += 5   # trend-aligned

        # Solo mode penalty (no co-signal confirmation)
        if sig['solo']:
            base_conf -= 5

        base_conf = min(max(base_conf, 50), 88)  # clamp

        sid = add_signal(
            token=token,
            direction='LONG',
            signal_type='bb_bounce_long',
            source='bb-bounce-long+',
            confidence=base_conf,
            value=sig['middle'],
            price=price,
            exchange='hyperliquid',
            timeframe='5m',
        )
        if sid:
            added += 1
            _cooldown[token.upper()] = now
            _log(f"{token} LONG conf={base_conf} rsi={sig['rsi']:.0f} "
                 f"trend={sig['trend']} bounce={sig['bounce_pct']:.2f}% "
                 f"vel={sig['velocity']:.3f}%" if sig['velocity'] is not None else "")

    return added


def run(prices_dict=None):
    if prices_dict is None:
        try:
            from signal_schema import get_all_latest_prices
            prices_dict = get_all_latest_prices()
        except Exception:
            return 0
    return scan_bb_bounce_long_signals(prices_dict)


if __name__ == '__main__':
    token = sys.argv[1] if len(sys.argv) > 1 else 'ETH'
    closes = _get_candles(token, 100)
    if closes:
        sig = detect_bb_bounce_long(token, closes)
        if sig:
            print(f"{token} {sig['direction']} rsi={sig['rsi']:.0f} "
                  f"trend={sig['trend']} bounce={sig['bounce_pct']:.2f}% "
                  f"vel={sig['velocity']:.3f}%" if sig['velocity'] is not None else "")
        else:
            print(f"{token}: no signal")
    else:
        print(f"{token}: no data")
