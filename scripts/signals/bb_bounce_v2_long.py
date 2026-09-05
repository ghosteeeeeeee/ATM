#!/usr/bin/env python3
"""bb_bounce_v2_long — Bollinger Band Bounce LONG v2 (calibrated from SHORT winners).

V2 (2026-09-01): New signal calibrated from bb_bounce_short winner patterns.
Key learnings from SHORT analysis:
  1. Bounce strength matters — winners have stronger bounce (0.13% vs 0.04%)
  2. BB width matters — wider BB can work for mean reversion (max 2.5%)
  3. RSI matters — HIGHER RSI confirms bounce (RSI_MIN=35, not MAX)
  4. Velocity matters — lower velocity = better (price not extreme)
  5. Momentum matters — positive momentum for LONG (uptrend)
  6. Volatility matters — lower volatility = better (less choppy)

Entry conditions:
1. Price within 0.15% of lower BB
2. RSI > 35 (bounce confirmed — price recovering from oversold)
3. BB width < 2.5% (not too wide)
4. Bounce strength >= 0.10% (STRONGER than v1's 0.05%)
5. 15m velocity > -0.01% (not falling hard)
6. 30m momentum > 0 (uptrend confirmed)
7. Volatility < 0.5% (low volatility = less chop)
8. min_age_sec=600 (10 min candle age)

Backtest context:
- bb_bounce_short: 66.7% WR, 90T
- V2 calibration: targeting 75%+ WR with tighter filters
"""
import sqlite3
import time
import sys
import os
import statistics

sys.path.insert(0, os.path.dirname(__file__))
from paths import RUNTIME_DB, CANDLES_DB

# ── Parameters ─────────────────────────────────────────────────────────────
from hermes_constants import (
    BB_BOUNCE_V2_LONG_ENABLED,
    LONG_BLACKLIST,
    BB_BOUNCE_V2_BB_PERIOD as BB_PERIOD,
    BB_BOUNCE_V2_BB_STDDEV as BB_STDDEV,
    BB_BOUNCE_V2_BB_TOUCH_PCT as BB_TOUCH_PCT,
    BB_BOUNCE_V2_BB_MIN_BARS as BB_MIN_BARS,
    BB_BOUNCE_V2_BB_WIDTH_MAX as BB_WIDTH_MAX,
    BB_BOUNCE_V2_RSI_PERIOD as RSI_PERIOD,
    BB_BOUNCE_V2_RSI_MIN as RSI_MIN,
    BB_BOUNCE_V2_BOUNCE_MIN_PCT as BOUNCE_MIN_PCT,
    BB_BOUNCE_V2_VEL_MIN as VEL_MIN,
    BB_BOUNCE_V2_MOM_MIN as MOM_MIN,
    BB_BOUNCE_V2_VOL_MAX as VOL_MAX,
    BB_BOUNCE_V2_MIN_AGE_SEC as MIN_AGE_SEC,
)

# ── State ─────────────────────────────────────────────────────────────────
_cooldown = {}


def _log(msg):
    print(f"[bb-bounce-v2-long] {msg}", flush=True)


def _compute_bb(closes, period=BB_PERIOD, stddev=BB_STDDEV):
    if len(closes) < period:
        return None, None, None, None
    middle = sum(closes[-period:]) / period
    variance = sum((c - middle) ** 2 for c in closes[-period:]) / period
    std = variance ** 0.5
    upper = middle + stddev * std
    lower = middle - stddev * std
    width = (upper - lower) / middle * 100 if middle > 0 else 0  # percentage
    return middle, upper, lower, width


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
    """15m price velocity (% change over last 15 minutes)."""
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


def _get_30m_momentum(token):
    """30m momentum via linear regression slope of 1m closes."""
    conn = None
    try:
        conn = sqlite3.connect(CANDLES_DB, timeout=5)
        c = conn.cursor()
        c.execute("""
            SELECT close FROM candles_1m
            WHERE token = ?
            ORDER BY ts DESC LIMIT 30
        """, (token.upper(),))
        rows = c.fetchall()
        if len(rows) < 10:
            return None
        closes = [r[0] for r in reversed(rows)]
        n = len(closes)
        x_mean = (n - 1) / 2
        y_mean = sum(closes) / n
        num = sum((i - x_mean) * (closes[i] - y_mean) for i in range(n))
        den = sum((i - x_mean) ** 2 for i in range(n))
        return (num / den / y_mean * 100) if den > 0 and y_mean > 0 else 0
    except Exception:
        return None
    finally:
        if conn:
            conn.close()


def _get_candles(token, lookback=100):
    """Get 5m candles with minimum age filter."""
    conn = None
    try:
        conn = sqlite3.connect(CANDLES_DB, timeout=10)
        cur = conn.cursor()
        max_ts = int(time.time()) - MIN_AGE_SEC
        cur.execute("""
            SELECT close FROM candles_5m
            WHERE token = ? AND ts <= ?
            ORDER BY ts DESC
            LIMIT ?
        """, (token.upper(), max_ts, lookback))
        rows = cur.fetchall()
        return [r[0] for r in reversed(rows)] if rows else []
    except Exception:
        return []
    finally:
        if conn:
            conn.close()


def _get_volatility(token):
    """Get average volatility (range %) of last 10 1m candles."""
    conn = None
    try:
        conn = sqlite3.connect(CANDLES_DB, timeout=5)
        cur = conn.cursor()
        cur.execute("""
            SELECT high, low, close FROM candles_1m
            WHERE token = ?
            ORDER BY ts DESC LIMIT 10
        """, (token.upper(),))
        rows = cur.fetchall()
        if len(rows) < 5:
            return None
        ranges = [(r[0] - r[1]) / r[2] * 100 for r in rows if r[2] > 0]
        return statistics.mean(ranges) if ranges else None
    except Exception:
        return None
    finally:
        if conn:
            conn.close()


def _is_solo(token, direction):
    """Check if this token+direction has any other active signals."""
    conn = None
    try:
        conn = sqlite3.connect(RUNTIME_DB, timeout=5)
        cur = conn.cursor()
        cur.execute("""
            SELECT COUNT(*) FROM signals
            WHERE token = ? AND direction = ? AND signal_type != 'bb_bounce_v2_long'
              AND created_at > datetime('now', '-10 minutes')
        """, (token.upper(), direction))
        count = cur.fetchone()[0]
        return count == 0
    except Exception:
        return True
    finally:
        if conn:
            conn.close()


def detect_bb_bounce_v2_long(token, closes):
    """Detect BB bounce LONG v2 with calibrated filters."""
    if len(closes) < BB_MIN_BARS:
        return None

    middle, upper, lower, width = _compute_bb(closes)
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
        # FILTER 1: BB width (tight squeeze required)
        if width > BB_WIDTH_MAX:
            return None  # BB too wide, not a squeeze

        # FILTER 2: RSI (bounce confirmation — price recovering)
        if rsi < RSI_MIN:
            return None  # RSI too low, bounce not confirmed

        # FILTER 3: Trend (not bearish)
        if trend == 'BEARISH':
            return None  # Counter-trend

        # FILTER 4: Bounce strength (STRONGER than v1)
        if current <= lower:
            return None  # Still below band, no bounce yet

        bounce_pct = (current - lower) / lower * 100 if lower > 0 else 0
        if bounce_pct < BOUNCE_MIN_PCT:
            return None  # Bounce too weak

        # FILTER 5: Velocity (not falling hard)
        vel = _get_15m_velocity(token)
        if vel is not None and vel < VEL_MIN:
            return None  # Price still falling

        # FILTER 6: Momentum (uptrend required)
        mom = _get_30m_momentum(token)
        if mom is not None and mom < MOM_MIN:
            return None  # Not in uptrend

        # FILTER 7: Volatility (low vol = less chop)
        vol = _get_volatility(token)
        if vol is not None and vol > VOL_MAX:
            return None  # Too volatile

        return {
            'direction': 'LONG',
            'middle': middle,
            'upper': upper,
            'lower': lower,
            'width': width,
            'rsi': rsi,
            'trend': trend,
            'bounce_pct': bounce_pct,
            'velocity': vel,
            'momentum': mom,
            'volatility': vol,
        }

    return None


def scan_bb_bounce_v2_long_signals(prices_dict):
    """Scan tokens for BB bounce v2 LONG signals."""
    from signal_schema import add_signal, get_cooldown, set_cooldown
    from hyperliquid_exchange import is_delisted

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
        if not BB_BOUNCE_V2_LONG_ENABLED:
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

        sig = detect_bb_bounce_v2_long(token, closes)
        if sig is None:
            continue

        # Confidence based on calibrated factors
        base_conf = 70
        if sig['bounce_pct'] > 0.20:
            base_conf += 5   # strong bounce
        if sig['width'] < 1.5:
            base_conf += 5   # tight squeeze
        if sig['trend'] == 'BULLISH':
            base_conf += 5   # trend-aligned
        if sig['volatility'] and sig['volatility'] < 0.3:
            base_conf += 5   # low volatility

        # Solo mode penalty
        solo = _is_solo(token, 'LONG')
        if solo:
            base_conf -= 3

        base_conf = min(max(base_conf, 50), 88)  # clamp

        sid = add_signal(
            token=token,
            direction='LONG',
            signal_type='bb_bounce_v2_long',
            source='bb-bounce-v2-long+',
            confidence=base_conf,
            value=sig['middle'],
            price=price,
            exchange='hyperliquid',
            timeframe='5m',
        )
        if sid:
            added += 1
            _cooldown[token.upper()] = now
            vel_str = f"{sig['velocity']:.3f}%" if sig['velocity'] is not None else "N/A"
            mom_str = f"{sig['momentum']:.4f}" if sig['momentum'] is not None else "N/A"
            vol_str = f"{sig['volatility']:.3f}%" if sig['volatility'] is not None else "N/A"
            _log(f"{token} LONG conf={base_conf} rsi={sig['rsi']:.0f} "
                 f"bounce={sig['bounce_pct']:.2f}% width={sig['width']:.2f}% "
                 f"vel={vel_str} mom={mom_str} vol={vol_str}")

    return added


def run(prices_dict=None):
    if prices_dict is None:
        try:
            from signal_schema import get_all_latest_prices
            prices_dict = get_all_latest_prices()
        except Exception:
            return 0
    return scan_bb_bounce_v2_long_signals(prices_dict)


if __name__ == '__main__':
    import statistics
    token = sys.argv[1] if len(sys.argv) > 1 else 'ETH'
    closes = _get_candles(token, 100)
    if closes:
        sig = detect_bb_bounce_v2_long(token, closes)
        if sig:
            vel_str = f"{sig['velocity']:.3f}%" if sig['velocity'] is not None else "N/A"
            mom_str = f"{sig['momentum']:.4f}" if sig['momentum'] is not None else "N/A"
            vol_str = f"{sig['volatility']:.3f}%" if sig['volatility'] is not None else "N/A"
            print(f"{token} {sig['direction']} rsi={sig['rsi']:.0f} "
                  f"bounce={sig['bounce_pct']:.2f}% width={sig['width']:.2f}% "
                  f"vel={vel_str} mom={mom_str} vol={vol_str}")
        else:
            print(f"{token}: no signal")
    else:
        print(f"{token}: no data")
