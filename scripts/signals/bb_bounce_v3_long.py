#!/usr/bin/env python3
"""bb_bounce_v3_long — Bollinger Band Bounce LONG v3 (high-winrate filter set).

V3 (2026-09-17): Built on v2 base with 7 new filters from trade analysis.
Key findings from 133-trade dataset:
  1. Winners: RSI 30-50, BB position 0.2-0.5, negative speed, fresh signals
  2. Losers: Extreme RSI (<20 or >60), stale=True, EXTREME regime, BB >0.6
  3. profit-monster-trail exits: 97.4% WR — the money maker
  4. cut-loser-CL-T1 exits: 0% WR — premature exits kill performance

V3 new filters (vs v2):
  1. RSI band: 25-55 (not extreme oversold/overbought)
  2. Stale filter: Block stale=True signals (fresh = better)
  3. Speed filter: 15m speed > -0.5% (not free-falling)
  4. BB position band: 0.10-0.65 (not chasing)
  5. RSI recovery: RSI rising (current > N bars ago)
  6. Volume confirmation: > 1.2x average (bounce confirmed by volume)
  7. Regime-aware confidence: EXTREME 0.7x, NORMAL 1.1x

Shadow mode — not enabled for live trading yet.
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
    BB_BOUNCE_V3_LONG_ENABLED,
    LONG_BLACKLIST,
    BB_BOUNCE_V3_BB_PERIOD as BB_PERIOD,
    BB_BOUNCE_V3_BB_STDDEV as BB_STDDEV,
    BB_BOUNCE_V3_BB_TOUCH_PCT as BB_TOUCH_PCT,
    BB_BOUNCE_V3_BB_MIN_BARS as BB_MIN_BARS,
    BB_BOUNCE_V3_BB_WIDTH_MAX as BB_WIDTH_MAX,
    BB_BOUNCE_V3_RSI_PERIOD as RSI_PERIOD,
    BB_BOUNCE_V3_RSI_MIN as RSI_MIN,
    BB_BOUNCE_V3_RSI_MAX as RSI_MAX,
    BB_BOUNCE_V3_RSI_RECOVERY_BARS as RSI_RECOVERY_BARS,
    BB_BOUNCE_V3_BOUNCE_MIN_PCT as BOUNCE_MIN_PCT,
    BB_BOUNCE_V3_VEL_MIN as VEL_MIN,
    BB_BOUNCE_V3_MOM_MIN as MOM_MIN,
    BB_BOUNCE_V3_BB_POS_MIN as BB_POS_MIN,
    BB_BOUNCE_V3_BB_POS_MAX as BB_POS_MAX,
    BB_BOUNCE_V3_VOL_RATIO_MIN as VOL_RATIO_MIN,
    BB_BOUNCE_V3_VOL_LOOKBACK as VOL_LOOKBACK,
    BB_BOUNCE_V3_VOLATILITY_MAX as VOL_MAX,
    BB_BOUNCE_V3_MIN_AGE_SEC as MIN_AGE_SEC,
    BB_BOUNCE_V3_STALE_MAX_AGE_SEC as STALE_MAX_AGE_SEC,
    BB_BOUNCE_V3_CONF_BASE as CONF_BASE,
    BB_BOUNCE_V3_CONF_CAP as CONF_CAP,
    BB_BOUNCE_V3_REGIME_NORMAL_MULT as REGIME_NORMAL_MULT,
    BB_BOUNCE_V3_REGIME_HIGH_MULT as REGIME_HIGH_MULT,
    BB_BOUNCE_V3_REGIME_EXTREME_MULT as REGIME_EXTREME_MULT,
    BB_BOUNCE_V3_REGIME_FLAT_MULT as REGIME_FLAT_MULT,
)

# ── State ─────────────────────────────────────────────────────────────────
_cooldown = {}


def _log(msg):
    print(f"[bb-bounce-v3-long] {msg}", flush=True)


def _compute_bb(closes, period=BB_PERIOD, stddev=BB_STDDEV):
    """Compute Bollinger Bands: middle, upper, lower, width (%)."""
    if len(closes) < period:
        return None, None, None, None
    middle = sum(closes[-period:]) / period
    variance = sum((c - middle) ** 2 for c in closes[-period:]) / period
    std = variance ** 0.5
    upper = middle + stddev * std
    lower = middle - stddev * std
    width = (upper - lower) / middle * 100 if middle > 0 else 0
    return middle, upper, lower, width


def _compute_rsi(closes, period=RSI_PERIOD):
    """Compute RSI from closes."""
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


def _compute_rsi_at(closes, offset, period=RSI_PERIOD):
    """Compute RSI at a specific offset from the end of closes (offset 0 = current)."""
    if offset >= len(closes):
        return None
    sliced = closes[:len(closes) - offset] if offset > 0 else closes
    return _compute_rsi(sliced, period)


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


def _get_volume_ratio(token):
    """Current volume / 20-bar average volume ratio (5m candles)."""
    conn = None
    try:
        conn = sqlite3.connect(CANDLES_DB, timeout=5)
        cur = conn.cursor()
        cur.execute("""
            SELECT volume FROM candles_5m
            WHERE token = ?
            ORDER BY ts DESC
            LIMIT ?
        """, (token.upper(), VOL_LOOKBACK + 1))
        rows = cur.fetchall()
        if not rows or len(rows) < VOL_LOOKBACK:
            return None
        # rows are newest-first
        current_vol = rows[0][0] if rows[0][0] else 0
        avg_vol = sum(r[0] for r in rows[1:]) / len(rows[1:]) if len(rows) > 1 else 0
        if avg_vol <= 0:
            return None
        return current_vol / avg_vol
    except Exception:
        return None
    finally:
        if conn:
            conn.close()


def _get_regime(token):
    """Get volatility regime from signal_schema."""
    try:
        from signal_schema import _get_volatility_regime
        return _get_volatility_regime(token)
    except Exception:
        return 'UNKNOWN'


def _is_solo(token, direction):
    """Check if this token+direction has any other active signals."""
    conn = None
    try:
        conn = sqlite3.connect(RUNTIME_DB, timeout=5)
        cur = conn.cursor()
        cur.execute("""
            SELECT COUNT(*) FROM signals
            WHERE token = ? AND direction = ? AND signal_type != 'bb_bounce_v3_long'
              AND created_at > datetime('now', '-10 minutes')
        """, (token.upper(), direction))
        count = cur.fetchone()[0]
        return count == 0
    except Exception:
        return True
    finally:
        if conn:
            conn.close()


def detect_bb_bounce_v3_long(token, closes):
    """Detect BB bounce LONG v3 with high-winrate filters.

    Returns signal dict if all filters pass, None otherwise.
    """
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

    # ── FILTER 1: BB proximity — price must be near lower band ──
    dist_from_lower = abs(current - lower) / lower * 100 if lower > 0 else 999
    if dist_from_lower > BB_TOUCH_PCT:
        return None

    # ── FILTER 2: Stale signal — reject old signals (new in v3) ──
    conn = None
    try:
        conn = sqlite3.connect(CANDLES_DB, timeout=5)
        cur = conn.cursor()
        cur.execute("SELECT MAX(ts) FROM candles_5m WHERE token = ?", (token.upper(),))
        row = cur.fetchone()
        latest_ts = row[0] if row and row[0] else 0
    except Exception:
        latest_ts = 0
    finally:
        if conn:
            conn.close()
    candle_age_sec = time.time() - latest_ts
    if candle_age_sec > STALE_MAX_AGE_SEC:
        return None

    # ── FILTER 3: BB width — not too wide (squeeze condition) ──
    if width > BB_WIDTH_MAX:
        return None

    # ── FILTER 4: RSI band — 25-55 (not extreme oversold/overbought) ──
    if rsi < RSI_MIN or rsi > RSI_MAX:
        return None

    # ── FILTER 4: Trend — not bearish ──
    trend = _get_15m_trend(token)
    if trend == 'BEARISH':
        return None

    # ── FILTER 5: Bounce confirmation — price above lower band ──
    if current <= lower:
        return None
    bounce_pct = (current - lower) / lower * 100 if lower > 0 else 0
    if bounce_pct < BOUNCE_MIN_PCT:
        return None

    # ── FILTER 6: Velocity — not free-falling ──
    vel = _get_15m_velocity(token)
    if vel is not None and vel < VEL_MIN:
        return None

    # ── FILTER 7: Momentum — uptrend required ──
    mom = _get_30m_momentum(token)
    if mom is not None and mom < MOM_MIN:
        return None

    # ── FILTER 8: BB position band — 0.10-0.65 (new in v3) ──
    if upper is not None and lower is not None and upper > lower:
        bb_position = (current - lower) / (upper - lower)
        if bb_position < BB_POS_MIN or bb_position > BB_POS_MAX:
            return None
    else:
        bb_position = None

    # ── FILTER 9: RSI recovery — RSI rising (new in v3) ──
    rsi_prev = _compute_rsi_at(closes, RSI_RECOVERY_BARS)
    if rsi_prev is not None and rsi <= rsi_prev:
        return None  # RSI not rising — bounce not confirmed

    # ── FILTER 10: Volume confirmation — bounce backed by volume (new in v3) ──
    vol_ratio = _get_volume_ratio(token)
    if vol_ratio is not None and vol_ratio < VOL_RATIO_MIN:
        return None  # low volume = weak bounce, skip

    # ── FILTER 11: Volatility — low vol = less chop ──
    vol = _get_volatility(token)
    if vol is not None and vol > VOL_MAX:
        return None

    return {
        'direction': 'LONG',
        'middle': middle,
        'upper': upper,
        'lower': lower,
        'width': width,
        'rsi': rsi,
        'rsi_prev': rsi_prev,
        'trend': trend,
        'bounce_pct': bounce_pct,
        'bb_position': bb_position,
        'velocity': vel,
        'momentum': mom,
        'volatility': vol,
        'volume_ratio': vol_ratio,
    }


def _compute_confidence(sig, token):
    """Compute confidence with regime-aware adjustments."""
    conf = CONF_BASE

    # Bounce strength bonus
    if sig['bounce_pct'] > 0.20:
        conf += 5

    # Tight squeeze bonus
    if sig['width'] < 1.5:
        conf += 5

    # Trend-aligned bonus
    if sig['trend'] == 'BULLISH':
        conf += 5

    # Low volatility bonus
    if sig['volatility'] is not None and sig['volatility'] < 0.3:
        conf += 3

    # RSI in sweet spot bonus (35-45 = recovering from oversold)
    if 35 <= sig['rsi'] <= 45:
        conf += 3

    # Volume confirmation bonus
    if sig['volume_ratio'] is not None and sig['volume_ratio'] > 1.5:
        conf += 3

    # Strong volume + bounce combo bonus
    if sig['volume_ratio'] is not None and sig['bounce_pct'] > 0.15:
        conf += 2

    # Solo mode penalty (no other signals confirming)
    solo = _is_solo(token, 'LONG')
    if solo:
        conf -= 3

    # Regime-aware multiplier (new in v3)
    regime = _get_regime(token)
    if regime == 'NORMAL':
        conf *= REGIME_NORMAL_MULT
    elif regime == 'HIGH':
        conf *= REGIME_HIGH_MULT
    elif regime == 'EXTREME':
        conf *= REGIME_EXTREME_MULT
    elif regime == 'FLAT':
        conf *= REGIME_FLAT_MULT
    # UNKNOWN keeps 1.0x

    # Clamp
    conf = int(min(max(conf, 50), CONF_CAP))

    return conf, regime


def scan_bb_bounce_v3_long_signals(prices_dict):
    """Scan tokens for BB bounce v3 LONG signals."""
    from signal_schema import add_signal, get_cooldown
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
        if not BB_BOUNCE_V3_LONG_ENABLED:
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

        sig = detect_bb_bounce_v3_long(token, closes)
        if sig is None:
            continue

        conf, regime = _compute_confidence(sig, token)

        sid = add_signal(
            token=token,
            direction='LONG',
            signal_type='bb_bounce_v3_long',
            source='bb-bounce-v3-long+',
            confidence=conf,
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
            vr_str = f"{sig['volume_ratio']:.2f}x" if sig['volume_ratio'] is not None else "N/A"
            bb_pos_str = f"{sig['bb_position']:.3f}" if sig['bb_position'] is not None else "N/A"
            rsi_prev_str = f"{sig['rsi_prev']:.0f}" if sig['rsi_prev'] is not None else "N/A"
            _log(f"{token} LONG conf={conf} rsi={sig['rsi']:.0f} rsi_prev={rsi_prev_str} "
                 f"bounce={sig['bounce_pct']:.2f}% bb_pos={bb_pos_str} width={sig['width']:.2f}% "
                 f"vel={vel_str} mom={mom_str} vol={vol_str} vr={vr_str} regime={regime}")

    return added


def run(prices_dict=None):
    if prices_dict is None:
        try:
            from signal_schema import get_all_latest_prices
            prices_dict = get_all_latest_prices()
        except Exception:
            return 0
    return scan_bb_bounce_v3_long_signals(prices_dict)


if __name__ == '__main__':
    import statistics
    token = sys.argv[1] if len(sys.argv) > 1 else 'ETH'
    closes = _get_candles(token, 100)
    if closes:
        sig = detect_bb_bounce_v3_long(token, closes)
        if sig:
            vel_str = f"{sig['velocity']:.3f}%" if sig['velocity'] is not None else "N/A"
            mom_str = f"{sig['momentum']:.4f}" if sig['momentum'] is not None else "N/A"
            vol_str = f"{sig['volatility']:.3f}%" if sig['volatility'] is not None else "N/A"
            vr_str = f"{sig['volume_ratio']:.2f}x" if sig['volume_ratio'] is not None else "N/A"
            bb_pos_str = f"{sig['bb_position']:.3f}" if sig['bb_position'] is not None else "N/A"
            rsi_prev_str = f"{sig['rsi_prev']:.0f}" if sig['rsi_prev'] is not None else "N/A"
            print(f"{token} {sig['direction']} rsi={sig['rsi']:.0f} rsi_prev={rsi_prev_str} "
                  f"bounce={sig['bounce_pct']:.2f}% bb_pos={bb_pos_str} width={sig['width']:.2f}% "
                  f"vel={vel_str} mom={mom_str} vol={vol_str} vr={vr_str}")
        else:
            print(f"{token}: no signal")
    else:
        print(f"{token}: no data")
