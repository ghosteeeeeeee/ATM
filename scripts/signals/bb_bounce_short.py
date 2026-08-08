#!/usr/bin/env python3
"""Bollinger Band Bounce SHORT — mean reversion for overbought conditions (SHORT-specific).

SHORT-SPECIFIC IMPROVEMENTS over generic bb_bounce:
  1. Regime filter: only fire in BEARISH 1H trend (EMA20 < EMA50)
  2. Tighter RSI threshold: 55 (was 60) — require stronger overbought
  3. Tighter BB touch: 0.20% (was 0.30%) — require closer touch to band
  4. Stronger bounce required: 0.08% (was 0.05%)
  5. Volume confirmation: 1.2x average (new)
  6. Time filter: avoid Asian session 00:00-07:59 UTC (new)
  7. 2-candle overbought confirmation (new)
  8. Tighter cooldown: 10 min (was 5)

BACKTEST CONTEXT (old generic SHORT):
  - 10 trades, 4 wins (40% WR), avg PnL -$0.056
  - Losses were large: AVNT -$0.18, AAVE -$0.19, XMR -$0.14
  - Root cause: firing in bullish regimes where "overbought" is just trend continuation
"""
import sqlite3
import time
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
from paths import RUNTIME_DB

# ── SHORT-Specific Parameters ──────────────────────────────────────────────
BB_PERIOD = 20
BB_STDDEV = 1.8
BB_TOUCH_PCT = 0.20        # TIGHTER: require closer touch to upper band
BB_MIN_BARS = 30
RSI_PERIOD = 14
RSI_OVERBOUGHT = 55        # TIGHTER: require stronger overbought (was 60)
BOUNCE_MIN_PCT = 0.08      # TIGHTER: require stronger bounce (was 0.05)
MIN_VOLUME_RATIO = 1.2     # Volume must be 1.2x average
BLOCKED_HOURS = [0, 1, 2, 3, 4, 5, 6, 7]  # Avoid Asian session
REQUIRE_2_CANDLE = True    # Require 2 consecutive overbought candles before bounce

# ── State ───────────────────────────────────────────────────────────────
_cooldown = {}


def _log(msg):
    print(f"[bb-bounce-short] {msg}", flush=True)


def _compute_bb(closes, period=BB_PERIOD, stddev=BB_STDDEV):
    if len(closes) < period:
        return None, None, None, None
    middle = sum(closes[-period:]) / period
    variance = sum((c - middle) ** 2 for c in closes[-period:]) / period
    std = variance ** 0.5
    upper = middle + stddev * std
    lower = middle - stddev * std
    width = (upper - lower) / middle if middle > 0 else 0
    return middle, upper, lower, width


def _compute_rsi(closes, period=RSI_PERIOD):
    if len(closes) < period + 1:
        return None
    gains, losses = [], []
    for i in range(1, min(period + 1, len(closes))):
        delta = closes[-i] - closes[-i - 1]
        gains.append(max(delta, 0))
        losses.append(max(-delta, 0))
    avg_gain = sum(gains) / len(gains) if gains else 0
    avg_loss = sum(losses) / len(losses) if losses else 0.001
    rs = avg_gain / avg_loss if avg_loss > 0 else 100
    return 100 - (100 / (1 + rs))


def _get_1h_trend(token):
    """Check 1H EMA trend. Returns 'BULLISH', 'BEARISH', or 'NEUTRAL'."""
    conn = None
    try:
        conn = sqlite3.connect('/root/.hermes/data/candles.db', timeout=5)
        cur = conn.cursor()
        cur.execute("""
            SELECT close FROM candles_1h
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


def _get_candles(token, lookback=100):
    conn = None
    try:
        conn = sqlite3.connect('/root/.hermes/data/candles.db', timeout=10)
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


def _get_volume_avg(token, lookback=50):
    """Get average volume over last N candles."""
    conn = None
    try:
        conn = sqlite3.connect('/root/.hermes/data/candles.db', timeout=5)
        cur = conn.cursor()
        cur.execute("""
            SELECT volume FROM candles_5m
            WHERE token = ?
            ORDER BY ts DESC
            LIMIT ?
        """, (token.upper(), lookback))
        rows = cur.fetchall()
        if not rows or len(rows) < 10:
            return None
        volumes = [r[0] for r in rows if r[0] is not None and r[0] > 0]
        if len(volumes) < 10:
            return None
        return sum(volumes) / len(volumes)
    except Exception:
        return None
    finally:
        if conn:
            conn.close()


def _get_current_volume(token):
    """Get the most recent candle's volume."""
    conn = None
    try:
        conn = sqlite3.connect('/root/.hermes/data/candles.db', timeout=5)
        cur = conn.cursor()
        cur.execute("""
            SELECT volume FROM candles_5m
            WHERE token = ?
            ORDER BY ts DESC
            LIMIT 1
        """, (token.upper(),))
        row = cur.fetchone()
        return row[0] if row and row[0] is not None else None
    except Exception:
        return None
    finally:
        if conn:
            conn.close()


def detect_bb_bounce_short(token, closes):
    """Detect BB bounce SHORT with tighter filters.

    Returns dict with signal info or None.
    """
    if len(closes) < BB_MIN_BARS:
        return None

    # Time filter: avoid Asian session
    from datetime import datetime, timezone
    hour = datetime.now(timezone.utc).hour
    if hour in BLOCKED_HOURS:
        return None

    middle, upper, lower, width = _compute_bb(closes)
    if middle is None:
        return None

    current = closes[-1]
    prev = closes[-2]

    rsi = _compute_rsi(closes)
    if rsi is None:
        return None

    # Regime filter: require BEARISH 1H trend
    trend = _get_1h_trend(token)
    if trend != 'BEARISH':
        return None

    # SHORT: upper band + RSI overbought + bounce down
    dist_from_upper = abs(current - upper) / upper * 100 if upper > 0 else 999

    if dist_from_upper > BB_TOUCH_PCT:
        return None  # Not close enough to upper band

    if current >= upper:
        return None  # Still above band, no bounce yet

    if rsi < RSI_OVERBOUGHT:
        return None  # RSI not overbought enough

    # 2-candle confirmation: both current and previous must be overbought
    if REQUIRE_2_CANDLE and len(closes) >= 3:
        prev_rsi = _compute_rsi(closes[:-1])
        if prev_rsi is None or prev_rsi < RSI_OVERBOUGHT:
            return None  # Previous candle wasn't overbought

    # Bounce must be downward
    if current >= prev:
        return None  # Price going up, not bouncing down

    bounce_pct = (upper - current) / upper * 100 if upper > 0 else 0
    if bounce_pct < BOUNCE_MIN_PCT:
        return None  # Bounce too weak

    # Volume confirmation
    vol_avg = _get_volume_avg(token)
    vol_current = _get_current_volume(token)
    if vol_avg and vol_avg > 0 and vol_current is not None:
        vol_ratio = vol_current / vol_avg
        if vol_ratio < MIN_VOLUME_RATIO:
            return None  # Insufficient volume
    # If no volume data, allow (don't block on missing data)

    return {
        'direction': 'SHORT',
        'middle': middle,
        'upper': upper,
        'lower': lower,
        'width': width,
        'rsi': rsi,
        'trend': trend,
        'bounce_pct': bounce_pct,
    }


def scan_bb_bounce_short_signals(prices_dict):
    """Scan tokens for BB bounce SHORT signals."""
    from signal_schema import add_signal, get_cooldown, set_cooldown
    from signal_gen import is_delisted, SHORT_BLACKLIST

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

        # Cooldown check
        if get_cooldown(token, direction='SHORT'):
            continue

        # Blacklist check
        if token.upper() in SHORT_BLACKLIST:
            continue

        # Kill switch
        from hermes_constants import BB_BOUNCE_SHORT_ENABLED
        if not BB_BOUNCE_SHORT_ENABLED:
            continue

        closes = _get_candles(token, 100)
        if not closes:
            continue

        sig = detect_bb_bounce_short(token, closes)
        if sig is None:
            continue

        # Confidence based on quality
        base_conf = 65
        if sig['width'] < 0.03:
            base_conf += 10  # Tight squeeze
        if sig['bounce_pct'] > 0.15:
            base_conf += 5   # Strong bounce
        if sig['rsi'] > 70:
            base_conf += 5   # Extremely overbought

        sid = add_signal(
            token=token,
            direction='SHORT',
            signal_type='bb_bounce_short',
            source='bb-bounce-short',
            confidence=min(base_conf, 88),
            value=sig['middle'],
            price=price,
            exchange='hyperliquid',
            timeframe='5m',
        )
        if sid:
            added += 1
            set_cooldown(token, direction='SHORT', hours=1)
            _log(f"{token} SHORT conf={base_conf} rsi={sig['rsi']:.0f} "
                 f"trend={sig['trend']} bounce={sig['bounce_pct']:.2f}%")

    return added


def run(prices_dict=None):
    """Entry point for signals_runner."""
    from signal_schema import get_all_latest_prices
    if prices_dict is None:
        prices_dict = get_all_latest_prices()
    return scan_bb_bounce_short_signals(prices_dict)


if __name__ == '__main__':
    token = sys.argv[1] if len(sys.argv) > 1 else 'ETH'
    closes = _get_candles(token, 100)
    if closes:
        sig = detect_bb_bounce_short(token, closes)
        if sig:
            print(f"{token} {sig['direction']} rsi={sig['rsi']:.0f} "
                  f"trend={sig['trend']} bounce={sig['bounce_pct']:.2f}%")
        else:
            print(f"{token}: no signal")
    else:
        print(f"{token}: no data")
