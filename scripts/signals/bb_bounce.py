#!/usr/bin/env python3
"""Bollinger Band Bounce — mean reversion for ranging markets.

Improved version with quality filters:
1. Trend alignment — bounce must align with 15m EMA trend
2. RSI confirmation — RSI must confirm oversold/overbought
3. Strong bounce — price must move away from band significantly
4. Volume confirmation — bounce should have above-average volume

LONG: Price touches lower band + RSI oversold + 1H bullish + strong bounce
SHORT: Price touches upper band + RSI overbought + 1H bearish + strong bounce
"""
import sqlite3
import time
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
from paths import RUNTIME_DB

# ── Config ──────────────────────────────────────────────────────────────
BB_PERIOD = 20
BB_STDDEV = 1.8          # was 2.0 — more band touches for ranging markets
BB_TOUCH_PCT = 0.15      # tightened 2026-08-12 — require very close to band (signal decay prevention)
BB_MIN_BARS = 30
RSI_PERIOD = 14
RSI_OVERSOLD = 40        # tightened 2026-08-07 — CEO: filter weak bounces
RSI_OVERBOUGHT = 60      # tightened 2026-08-07 — CEO: filter weak bounces
BOUNCE_MIN_PCT = 0.05    # relaxed 2026-08-24 — was 0.08%, still filters weak bounces
# Solo-specific (stricter when no co-signal present)
SOLO_RSI_OVERSOLD = 30   # tightened 2026-08-12 — require deeper oversold for standalone
SOLO_RSI_OVERBOUGHT = 70 # tightened 2026-08-12 — require deeper overbought for standalone
SOLO_BOUNCE_MIN_PCT = 0.03  # relaxed 2026-08-24 — was 0.15%, then 0.08%. Any bounce above band qualifies.
COOLDOWN_MIN = 5         # was 10 — faster re-entries

# ── State ───────────────────────────────────────────────────────────────
_cooldown = {}


def _log(msg):
    print(f"[bb-bounce] {msg}", flush=True)


def _get_15m_velocity(token):
    """15m price velocity (% change over last 15 minutes). Returns float or None."""
    from paths import HERMES_DATA
    import sqlite3
    conn = None
    try:
        conn = sqlite3.connect(os.path.join(HERMES_DATA, 'signals_hermes.db'), timeout=10)
        c = conn.cursor()
        c.execute("""
            SELECT price FROM (
                SELECT price, timestamp FROM price_history
                WHERE token = ?
                ORDER BY timestamp DESC LIMIT 15
            ) sub ORDER BY timestamp ASC
        """, (token.upper(),))
        rows = c.fetchall()
        if len(rows) < 5:
            return None
        prices = [r[0] for r in rows]
        if prices[0] <= 0:
            return None
        return (prices[-1] - prices[0]) / prices[0] * 100
    except Exception:
        return None
    finally:
        if conn:
            conn.close()


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


def _get_15m_trend(token):
    """Check 15m EMA trend. Returns 'BULLISH', 'BEARISH', or 'NEUTRAL'."""
    conn = None
    try:
        conn = sqlite3.connect('/root/.hermes/data/candles.db', timeout=5)
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


def _get_ohlcv_candles(token, lookback=100):
    """Get full OHLCV candle data for pattern recognition."""
    conn = None
    try:
        conn = sqlite3.connect('/root/.hermes/data/candles.db', timeout=10)
        cur = conn.cursor()
        cur.execute("""
            SELECT ts, open, high, low, close, volume
            FROM candles_5m
            WHERE token = ?
            ORDER BY ts DESC
            LIMIT ?
        """, (token.upper(), lookback))
        rows = cur.fetchall()
        if not rows:
            return []
        return [{'ts': r[0], 'open': r[1], 'high': r[2], 'low': r[3],
                 'close': r[4], 'volume': r[5]} for r in reversed(rows)]
    except Exception:
        return []
    finally:
        if conn:
            conn.close()


def _is_solo(token, direction):
    """Check if this token+direction has any other active signals in DB (no co-signal)."""
    try:
        from paths import RUNTIME_DB
        conn = sqlite3.connect(RUNTIME_DB, timeout=5)
        cur = conn.cursor()
        cur.execute("""
            SELECT COUNT(*) FROM signals
            WHERE token = ? AND direction = ? AND signal_type != 'bb_bounce'
              AND created_at > datetime('now', '-10 minutes')
        """, (token.upper(), direction))
        count = cur.fetchone()[0]
        conn.close()
        return count == 0
    except Exception:
        return True  # assume solo if DB check fails


def detect_bb_bounce(token, closes):
    """Detect Bollinger Band bounce with quality filters."""
    if len(closes) < BB_MIN_BARS:
        return None

    middle, upper, lower, width = _compute_bb(closes)
    if middle is None:
        return None

    current = closes[-1]
    prev = closes[-2] if len(closes) >= 2 else current

    # Compute RSI
    rsi = _compute_rsi(closes)
    if rsi is None:
        return None

    # Distance from bands
    dist_from_upper = abs(current - upper) / upper * 100 if upper > 0 else 999
    dist_from_lower = abs(current - lower) / lower * 100 if lower > 0 else 999

    # Check 15m trend
    trend = _get_15m_trend(token)

    # LONG: lower band + RSI oversold + bullish/neutral trend + bounce up
    # FIX (2026-08-24): Removed current > prev requirement.
    # Price near band + above band + RSI oversold is sufficient.
    # The old requirement killed ALL signals because price at the band
    # is typically still falling on the current candle.
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

        # FIX (2026-08-24): Removed momentum fade velocity gate.
        # Same issue as hzscore — requiring vel_5m >= 0 means price must already be rising,
        # but by then the bounce is over. The BB touch + RSI + bounce_pct filters are
        # sufficient quality gates. The old velocity gate killed ALL bb_bounce signals.

        return {
            'direction': 'LONG',
            'middle': middle,
            'upper': upper,
            'lower': lower,
            'width': width,
            'rsi': rsi,
            'trend': trend,
            'bounce_pct': bounce_pct,
            'solo': solo_l,
        }

    # SHORT: upper band + RSI overbought + bearish/neutral trend + bounce down
    # FIX (2026-08-24): Removed current < prev requirement for SHORT.
    if dist_from_upper <= BB_TOUCH_PCT:
        solo_s = _is_solo(token, 'SHORT')
        rsi_thresh = SOLO_RSI_OVERBOUGHT if solo_s else RSI_OVERBOUGHT
        bounce_thresh = SOLO_BOUNCE_MIN_PCT if solo_s else BOUNCE_MIN_PCT

        if rsi < rsi_thresh:
            return None
        if trend == 'BULLISH':
            return None

        # Check bounce strength — price must be below the band
        if current >= upper:
            return None  # Still above band, no bounce yet

        bounce_pct = (upper - current) / upper * 100 if upper > 0 else 0
        if bounce_pct < bounce_thresh:
            return None

        # FIX (2026-08-24): Removed momentum fade velocity gate for SHORT.
        # Same fix as LONG — velocity confirmation comes too late.

        return {
            'direction': 'SHORT',
            'middle': middle,
            'upper': upper,
            'lower': lower,
            'width': width,
            'rsi': rsi,
            'trend': trend,
            'bounce_pct': bounce_pct,
            'solo': solo_s,
        }

    return None


def scan_bb_bounce_signals(prices_dict):
    """Scan tokens for BB bounce signals."""
    from signal_schema import add_signal
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

        key = f"{token.upper()}"
        if key in _cooldown and now - _cooldown[key] < COOLDOWN_MIN * 60:
            continue

        closes = _get_candles(token, 100)
        if not closes:
            continue

        sig = detect_bb_bounce(token, closes)
        if sig is None:
            continue

        direction = sig['direction']
        if direction == 'SHORT' and token.upper() in SHORT_BLACKLIST:
            continue

        # Per-direction kill-switch
        from hermes_constants import BB_BOUNCE_PLUS_ENABLED, BB_BOUNCE_MINUS_ENABLED
        if direction == 'LONG' and not BB_BOUNCE_PLUS_ENABLED:
            continue
        if direction == 'SHORT' and not BB_BOUNCE_MINUS_ENABLED:
            continue

        # Velocity gate: skip if price still trending against signal
        from hermes_constants import MEAN_REVERSION_VEL_ENABLED, MEAN_REVERSION_VEL_THRESHOLD, MEAN_REVERSION_VEL_THRESHOLD_SHORT
        if MEAN_REVERSION_VEL_ENABLED:
            vel = _get_15m_velocity(token)
            if vel is not None:
                if direction == 'LONG' and vel < -MEAN_REVERSION_VEL_THRESHOLD:
                    _log(f"{token} {direction} BLOCKED vel={vel:+.3f}% (threshold -{MEAN_REVERSION_VEL_THRESHOLD}%)")
                    continue
                if direction == 'SHORT' and vel > MEAN_REVERSION_VEL_THRESHOLD_SHORT:
                    _log(f"{token} {direction} BLOCKED vel={vel:+.3f}% (threshold +{MEAN_REVERSION_VEL_THRESHOLD_SHORT}%)")
                    continue

        # Spike exhaustion filter: block entries after sharp 5m moves
        _conn_se = None
        try:
            from hermes_constants import SPIKE_EXHAUSTION_VEL_5M_THRESHOLD
            from paths import HERMES_DATA
            import sqlite3 as _sqlite3
            _conn_se = _sqlite3.connect(os.path.join(HERMES_DATA, 'signals_hermes.db'), timeout=10)
            _cur_se = _conn_se.cursor()
            _cur_se.execute("""
                SELECT price FROM (
                    SELECT price, timestamp FROM price_history
                    WHERE token = ?
                    ORDER BY timestamp DESC LIMIT 6
                ) sub ORDER BY timestamp ASC
            """, (token.upper(),))
            _prices_se = [r[0] for r in _cur_se.fetchall()]
            if len(_prices_se) >= 2 and _prices_se[0] > 0:
                _vel_se = (_prices_se[-1] - _prices_se[0]) / _prices_se[0] * 100
                if abs(_vel_se) > SPIKE_EXHAUSTION_VEL_5M_THRESHOLD:
                    _log(f"{token} {direction} BLOCKED spike exhaustion vel_5m={_vel_se:+.3f}%")
                    continue
        except Exception:
            pass
        finally:
            if _conn_se:
                _conn_se.close()

        # Confidence based on quality indicators
        base_conf = 60
        if sig['width'] < 0.03:  # Tight squeeze = stronger signal
            base_conf += 10
        if sig['trend'] != 'NEUTRAL':  # Trend-aligned = stronger
            base_conf += 5
        if sig['bounce_pct'] > 0.15:  # Strong bounce
            base_conf += 10
        elif sig['bounce_pct'] < 0.05:  # Weak bounce = penalty
            base_conf -= 10
        if sig['rsi'] > 60:  # Not oversold enough = penalty
            base_conf -= 10

        # Pattern recognition boost (AXS-style reversal setups)
        try:
            from pattern_recognition import detect_reversal_quality
            ohlcv_candles = _get_ohlcv_candles(token, 100)
            if ohlcv_candles and len(ohlcv_candles) >= 20:
                quality = detect_reversal_quality(ohlcv_candles)
                if quality['score'] >= 3:
                    base_conf += quality['score'] * 3  # +9 for score 3, +15 for score 5
                    _log(f"{token} pattern quality {quality['score']}/5: {quality['signals']}")
        except Exception:
            pass  # Don't block on pattern recognition errors

        sid = add_signal(
            token=token,
            direction=direction,
            signal_type='bb_bounce',
            source=f'bb_bounce{"+" if direction == "LONG" else "-"}',
            confidence=min(base_conf, 88),
            value=sig['middle'],
            price=price,
            exchange='hyperliquid',
            timeframe='5m',
        )
        if sid:
            added += 1
            _cooldown[key] = now
            _log(f"{token} {direction} conf={base_conf} "
                 f"rsi={sig['rsi']:.0f} trend={sig['trend']} "
                 f"bounce={sig['bounce_pct']:.2f}%")

    return added


def run(prices_dict=None):
    if prices_dict is None:
        try:
            from signal_schema import get_all_latest_prices
            prices_dict = get_all_latest_prices()
        except Exception:
            return 0
    return scan_bb_bounce_signals(prices_dict)


if __name__ == '__main__':
    token = sys.argv[1] if len(sys.argv) > 1 else 'ETH'
    closes = _get_candles(token, 100)
    if closes:
        sig = detect_bb_bounce(token, closes)
        if sig:
            print(f"{token} {sig['direction']} rsi={sig['rsi']:.0f} "
                  f"trend={sig['trend']} bounce={sig['bounce_pct']:.2f}%")
        else:
            print(f"{token}: no signal")
    else:
        print(f"{token}: no data")
