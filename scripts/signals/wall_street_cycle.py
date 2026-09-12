#!/usr/bin/env python3
"""Wall Street Psychology Cycle — Euphoria/Capitulation reversal signal.

Based on the Wall Street Cheat Sheet (Liberated Stock Trader, 2000 Dotcom Bubble).
The market psychology cycle describes emotional extremes at tops and bottoms:

  UPSIDE:   Disbelief → Hope → Optimism → Belief → Thrill → Euphoria (TOP)
  DOWNSIDE: Complacency → Anxiety → Denial → Panic → Capitulation → Anger → Depression (BOTTOM)

THESIS: Emotional extremes are measurable via price extension, RSI, volume, and
volatility. When price reaches a EUPHORIC extreme (parabolic up, everyone buying),
fade it SHORT for the mean reversion. When price reaches a CAPITULATION extreme
(crashed, everyone selling), fade it LONG for the bounce.

DIFFERENT from volume_climax:
  - volume_climax is purely volume+wick based on a single candle
  - This signal uses MULTI-TIMEFRAME structural analysis (5m+1h+4h)
  - Looks for PARABOLIC extension (not just one candle rejection)
  - Combines RSI extremes + EMA gap + volume + BB width

DIFFERENT from return_exhaustion:
  - return_exhaustion uses simple percentage return thresholds
  - This signal uses COMPOSITE scoring across multiple emotional indicators
  - Specifically models the Wall Street psychology cycle phases

LOGIC (EUPHORIA SHORT):
  1. RSI(14) on 1h > EUPHORIA_RSI_THRESHOLD (extreme overbought)
  2. Price > EMA50 by EUPHORIA_EMA_GAP_PCT% (parabolic extension)
  3. Volume spike on 5m (last buyers piling in)
  4. BB width expansion on 1h (volatility expansion = blow-off top)
  5. Price near 4h high (at the extreme)

LOGIC (CAPITULATION LONG):
  1. RSI(14) on 1h < CAPITULATION_RSI_THRESHOLD (extreme oversold)
  2. Price < EMA50 by CAPITULATION_EMA_GAP_PCT% (crashed)
  3. Volume spike on 5m (panic selling)
  4. Long lower wick on 5m candle (buyers stepping in)
  5. Price near 4h low (at the extreme)
"""

import sys
import os
import sqlite3
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from signal_schema import add_signal, get_cooldown, price_age_minutes, set_cooldown
from paths import HERMES_DATA
from entry_gates import (
    rr_gate, volume_gate, candle_close_gate, session_timing_gate,
)

from hermes_constants import (
    WALL_ST_CYCLE_ENABLED,
    WALL_ST_CYCLE_PLUS_ENABLED,
    WALL_ST_CYCLE_MINUS_ENABLED,
    # Euphoria (SHORT) params
    WALL_ST_CYCLE_EUPHORIA_RSI,
    WALL_ST_CYCLE_EUPHORIA_EMA_GAP_PCT,
    WALL_ST_CYCLE_EUPHORIA_BB_EXPANSION,
    WALL_ST_CYCLE_EUPHORIA_VOLUME_MULT,
    # Capitulation (LONG) params
    WALL_ST_CYCLE_CAPITULATION_RSI,
    WALL_ST_CYCLE_CAPITULATION_EMA_GAP_PCT,
    WALL_ST_CYCLE_CAPITULATION_VOLUME_MULT,
    WALL_ST_CYCLE_CAPITULATION_WICK_RATIO,
    # Common
    WALL_ST_CYCLE_LOOKBACK,
    WALL_ST_CYCLE_AVG_PERIOD,
    WALL_ST_CYCLE_EXTREME_WINDOW,
    WALL_ST_CYCLE_CONF_BASE,
    WALL_ST_CYCLE_CONF_FLOOR,
    WALL_ST_CYCLE_CONF_CAP,
    WALL_ST_CYCLE_COOLDOWN_HOURS,
    LONG_BLACKLIST,
    SHORT_BLACKLIST,
)

SIGNAL_TYPE_LONG = 'wall_street_cycle_long'
SIGNAL_TYPE_SHORT = 'wall_street_cycle_short'
SOURCE_LONG = 'wall-st-cycle+'
SOURCE_SHORT = 'wall-st-cycle-'

_CANDLES_DB = os.path.join(HERMES_DATA, 'candles.db')


def _log(msg):
    print(f"[wall-st-cycle] {msg}", flush=True)


def _get_candles(token, table='candles_5m', limit=100):
    """Fetch OHLCV candles. Returns list of {ts, open, high, low, close, volume} oldest-first."""
    _VALID_TABLES = {'candles_1m', 'candles_5m', 'candles_15m', 'candles_1h', 'candles_4h'}
    if table not in _VALID_TABLES:
        return []
    conn = None
    try:
        conn = sqlite3.connect(_CANDLES_DB, timeout=10)
        cur = conn.cursor()
        cur.execute(f"""
            SELECT ts, open, high, low, close, volume FROM {table}
            WHERE token = ?
            ORDER BY ts DESC
            LIMIT ?
        """, (token.upper(), limit))
        rows = cur.fetchall()
        if not rows or len(rows) < 20:
            return []
        return [{'ts': r[0], 'open': r[1], 'high': r[2], 'low': r[3], 'close': r[4], 'volume': r[5]}
                for r in reversed(rows)]
    except Exception:
        return []
    finally:
        if conn:
            conn.close()


def _compute_rsi(closes, period=14):
    """Compute RSI from a list of closes (oldest-first). Returns current RSI."""
    if len(closes) < period + 1:
        return 50.0  # neutral default

    deltas = [closes[i] - closes[i - 1] for i in range(1, len(closes))]

    # Seed with SMA of first `period` deltas
    gains = [d if d > 0 else 0 for d in deltas[:period]]
    losses = [-d if d < 0 else 0 for d in deltas[:period]]
    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period

    # Wilder's smoothing
    for d in deltas[period:]:
        gain = d if d > 0 else 0
        loss = -d if d < 0 else 0
        avg_gain = (avg_gain * (period - 1) + gain) / period
        avg_loss = (avg_loss * (period - 1) + loss) / period

    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def _compute_ema(closes, period):
    """Compute EMA from a list of closes (oldest-first)."""
    if not closes:
        return 0.0
    k = 2 / (period + 1)
    val = closes[0]
    for v in closes[1:]:
        val = v * k + val * (1 - k)
    return val


def _compute_bb(closes, period=20):
    """Compute Bollinger Band width as percentage of middle band. Returns (width_pct, upper, lower, middle)."""
    if len(closes) < period:
        return (0.0, 0.0, 0.0, 0.0)

    window = closes[-period:]
    middle = sum(window) / period
    variance = sum((x - middle) ** 2 for x in window) / period
    std = variance ** 0.5
    upper = middle + 2 * std
    lower = middle - 2 * std

    if middle == 0:
        return (0.0, upper, lower, middle)

    width_pct = (upper - lower) / middle * 100
    return (width_pct, upper, lower, middle)


def _is_at_extreme(candles, direction, window=None):
    """Check if current price is at a recent extreme (high for SHORT, low for LONG)."""
    w = window or WALL_ST_CYCLE_EXTREME_WINDOW
    if len(candles) < w:
        return False

    recent = candles[-w:]
    highs = [c['high'] for c in recent]
    lows = [c['low'] for c in recent]
    range_high = max(highs)
    range_low = min(lows)

    if range_high == range_low:
        return False

    price = candles[-1]['close']
    range_size = range_high - range_low
    position = (price - range_low) / range_size

    if direction == 'SHORT':
        return position > 0.90  # top 10%
    else:
        return position < 0.10  # bottom 10%


def _detect_euphoria(candles_5m, candles_1h, candles_4h):
    """Detect Euphoria phase (SHORT signal).

    Euphoria = parabolic extension + extreme RSI + volume climax + wide BB.
    This is the 'I am a genius!' moment before the crash.
    """
    if len(candles_1h) < 60:
        return None
    if len(candles_5m) < WALL_ST_CYCLE_AVG_PERIOD + 5:
        return None

    current_5m = candles_5m[-1]
    current_1h = candles_1h[-1]
    price = current_1h['close']
    if price <= 0:
        return None

    # 1. RSI on 1h — must be extreme overbought
    closes_1h = [c['close'] for c in candles_1h]
    rsi_1h = _compute_rsi(closes_1h, 14)
    if rsi_1h < WALL_ST_CYCLE_EUPHORIA_RSI:
        return None

    # 2. Price above EMA50 — parabolic extension
    ema50_1h = _compute_ema(closes_1h, 50)
    if ema50_1h == 0:
        return None
    ema_gap_pct = (price - ema50_1h) / ema50_1h * 100
    if ema_gap_pct < WALL_ST_CYCLE_EUPHORIA_EMA_GAP_PCT:
        return None

    # 3. Volume spike on 5m — last buyers piling in
    avg_vol = sum(c['volume'] for c in candles_5m[-WALL_ST_CYCLE_AVG_PERIOD - 1:-1]) / WALL_ST_CYCLE_AVG_PERIOD
    if avg_vol <= 0:
        return None
    vol_ratio = current_5m['volume'] / avg_vol
    if vol_ratio < WALL_ST_CYCLE_EUPHORIA_VOLUME_MULT:
        return None

    # 4. BB width expansion on 1h — volatility expansion = blow-off top
    bb_width, _, _, _ = _compute_bb(closes_1h, 20)
    if bb_width < WALL_ST_CYCLE_EUPHORIA_BB_EXPANSION:
        return None

    # 5. Price at 4h extreme high
    if candles_4h and len(candles_4h) >= WALL_ST_CYCLE_EXTREME_WINDOW:
        if not _is_at_extreme(candles_4h, 'SHORT', WALL_ST_CYCLE_EXTREME_WINDOW):
            # Relax: if 4h data is thin, allow based on 1h
            if not _is_at_extreme(candles_1h, 'SHORT', WALL_ST_CYCLE_EXTREME_WINDOW):
                return None

    # Confidence scoring
    conf = WALL_ST_CYCLE_CONF_BASE

    # RSI strength bonus
    if rsi_1h > 90:
        conf += 8  # extreme euphoria
    elif rsi_1h > 85:
        conf += 5
    elif rsi_1h > 80:
        conf += 3

    # EMA gap bonus (bigger extension = more euphoric)
    if ema_gap_pct > 10:
        conf += 8
    elif ema_gap_pct > 7:
        conf += 5
    elif ema_gap_pct > 5:
        conf += 3

    # Volume climax bonus
    if vol_ratio > WALL_ST_CYCLE_EUPHORIA_VOLUME_MULT * 3:
        conf += 8
    elif vol_ratio > WALL_ST_CYCLE_EUPHORIA_VOLUME_MULT * 2:
        conf += 5

    # BB width bonus (wider = more volatile = more euphoric)
    if bb_width > 8:
        conf += 5
    elif bb_width > 6:
        conf += 3

    conf = min(conf, WALL_ST_CYCLE_CONF_CAP)
    conf = max(conf, WALL_ST_CYCLE_CONF_FLOOR)

    return {
        'direction': 'SHORT',
        'confidence': conf,
        'value': round(ema_gap_pct, 2),  # EMA gap as the signal value
        'price': price,
        'rsi': round(rsi_1h, 1),
        'vol_ratio': round(vol_ratio, 2),
        'bb_width': round(bb_width, 2),
    }


def _detect_capitulation(candles_5m, candles_1h, candles_4h):
    """Detect Capitulation phase (LONG signal).

    Capitulation = crash + extreme oversold + panic volume + buyer rejection wicks.
    This is the 'My retirement is lost!' moment before the bounce.
    """
    if len(candles_1h) < 60:
        return None
    if len(candles_5m) < WALL_ST_CYCLE_AVG_PERIOD + 5:
        return None

    current_5m = candles_5m[-1]
    current_1h = candles_1h[-1]
    price = current_1h['close']
    if price <= 0:
        return None

    # 1. RSI on 1h — must be extreme oversold
    closes_1h = [c['close'] for c in candles_1h]
    rsi_1h = _compute_rsi(closes_1h, 14)
    if rsi_1h > WALL_ST_CYCLE_CAPITULATION_RSI:
        return None

    # 2. Price below EMA50 — crashed
    ema50_1h = _compute_ema(closes_1h, 50)
    if ema50_1h == 0:
        return None
    ema_gap_pct = (ema50_1h - price) / ema50_1h * 100  # positive = below EMA
    if ema_gap_pct < WALL_ST_CYCLE_CAPITULATION_EMA_GAP_PCT:
        return None

    # 3. Volume spike on 5m — panic selling
    avg_vol = sum(c['volume'] for c in candles_5m[-WALL_ST_CYCLE_AVG_PERIOD - 1:-1]) / WALL_ST_CYCLE_AVG_PERIOD
    if avg_vol <= 0:
        return None
    vol_ratio = current_5m['volume'] / avg_vol
    if vol_ratio < WALL_ST_CYCLE_CAPITULATION_VOLUME_MULT:
        return None

    # 4. Long lower wick — buyers stepping in (rejection of lower prices)
    body = abs(current_5m['close'] - current_5m['open'])
    if body == 0:
        return None  # doji — skip
    lower_wick = min(current_5m['open'], current_5m['close']) - current_5m['low']
    wick_ratio = lower_wick / body
    if wick_ratio < WALL_ST_CYCLE_CAPITULATION_WICK_RATIO:
        return None

    # 5. Price at 4h extreme low
    if candles_4h and len(candles_4h) >= WALL_ST_CYCLE_EXTREME_WINDOW:
        if not _is_at_extreme(candles_4h, 'LONG', WALL_ST_CYCLE_EXTREME_WINDOW):
            if not _is_at_extreme(candles_1h, 'LONG', WALL_ST_CYCLE_EXTREME_WINDOW):
                return None

    # Confidence scoring
    conf = WALL_ST_CYCLE_CONF_BASE

    # RSI depth bonus (lower = more capitulation)
    if rsi_1h < 10:
        conf += 8  # extreme capitulation
    elif rsi_1h < 15:
        conf += 5
    elif rsi_1h < 20:
        conf += 3

    # EMA gap bonus (bigger crash = more capitulation)
    if ema_gap_pct > 10:
        conf += 8
    elif ema_gap_pct > 7:
        conf += 5
    elif ema_gap_pct > 5:
        conf += 3

    # Volume panic bonus
    if vol_ratio > WALL_ST_CYCLE_CAPITULATION_VOLUME_MULT * 3:
        conf += 8
    elif vol_ratio > WALL_ST_CYCLE_CAPITULATION_VOLUME_MULT * 2:
        conf += 5

    # Wick rejection bonus (longer wick = stronger buyer rejection)
    if wick_ratio > 3.0:
        conf += 5
    elif wick_ratio > 2.0:
        conf += 3

    conf = min(conf, WALL_ST_CYCLE_CONF_CAP)
    conf = max(conf, WALL_ST_CYCLE_CONF_FLOOR)

    return {
        'direction': 'LONG',
        'confidence': conf,
        'value': round(ema_gap_pct, 2),  # EMA gap (crash depth) as the signal value
        'price': price,
        'rsi': round(rsi_1h, 1),
        'vol_ratio': round(vol_ratio, 2),
        'wick_ratio': round(wick_ratio, 2),
    }


def _get_1h_trend(token):
    """Check 1h EMA20/50 trend. Returns 'BULLISH', 'BEARISH', or 'NEUTRAL'."""
    conn = None
    try:
        conn = sqlite3.connect(_CANDLES_DB, timeout=5)
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


def scan_wall_street_cycle_signals():
    """Scan all tokens for Wall Street Psychology Cycle setups."""
    added = 0

    # GATE: Session timing
    if not session_timing_gate():
        return 0

    from signal_schema import get_all_latest_prices
    prices = get_all_latest_prices()

    for token, data in prices.items():
        if token.startswith('@'):
            continue
        price = data.get('price')
        if not price or price <= 0:
            continue

        # Staleness check
        if price_age_minutes(token) > 10:
            continue

        # Get candles across timeframes
        raw_candles_5m = _get_candles(token, 'candles_5m', WALL_ST_CYCLE_LOOKBACK)
        if not raw_candles_5m:
            continue

        # GATE: Candle close
        candles_5m = candle_close_gate(raw_candles_5m, timeframe_seconds=300)
        if len(candles_5m) < 20:
            continue

        # GATE: Reject synthesized candles (V=0 = price_history, not real exchange data)
        if candles_5m[-1].get('volume', 0) <= 0:
            continue

        candles_1h = _get_candles(token, 'candles_1h', 100)
        candles_4h = _get_candles(token, 'candles_4h', 60)

        # Try both detection modes
        sig = _detect_euphoria(candles_5m, candles_1h, candles_4h)
        if not sig:
            sig = _detect_capitulation(candles_5m, candles_1h, candles_4h)
        if not sig:
            continue

        direction = sig['direction']

        # Layer 1: kill-switch
        if direction == 'LONG' and not WALL_ST_CYCLE_PLUS_ENABLED:
            continue
        if direction == 'SHORT' and not WALL_ST_CYCLE_MINUS_ENABLED:
            continue

        # Layer 1: blacklists
        if direction == 'LONG' and token.upper() in LONG_BLACKLIST:
            continue
        if direction == 'SHORT' and token.upper() in SHORT_BLACKLIST:
            continue

        # Cooldown
        if get_cooldown(token, direction=direction):
            continue

        # GATE: 1h trend alignment (boost confidence if aligned)
        trend = _get_1h_trend(token)
        if trend == 'BEARISH' and direction == 'SHORT':
            sig['confidence'] = min(sig['confidence'] + 3, WALL_ST_CYCLE_CONF_CAP)
        if trend == 'BULLISH' and direction == 'LONG':
            sig['confidence'] = min(sig['confidence'] + 3, WALL_ST_CYCLE_CONF_CAP)

        # GATE: R:R pre-check
        rr_pass, sl, tp, rr = rr_gate(token, direction, price, raw_candles_5m)
        if not rr_pass:
            continue

        sig_type = SIGNAL_TYPE_LONG if direction == 'LONG' else SIGNAL_TYPE_SHORT
        source = SOURCE_LONG if direction == 'LONG' else SOURCE_SHORT

        sid = add_signal(
            token=token.upper(),
            direction=direction,
            signal_type=sig_type,
            source=source,
            confidence=sig['confidence'],
            value=sig['value'],
            price=sig['price'],
            exchange='hyperliquid',
            timeframe='5m',
        )
        if sid:
            added += 1
            set_cooldown(token, direction, hours=WALL_ST_CYCLE_COOLDOWN_HOURS)
            rsi_info = f"rsi={sig.get('rsi', '?')}"
            vol_info = f"vol={sig.get('vol_ratio', '?')}x"
            if direction == 'SHORT':
                _log(f"{token} EUPHORIA {direction} conf={sig['confidence']} "
                     f"ema_gap={sig['value']}% {rsi_info} {vol_info} "
                     f"bb={sig.get('bb_width', '?')} trend={trend} rr={rr:.1f}")
            else:
                _log(f"{token} CAPITULATION {direction} conf={sig['confidence']} "
                     f"crash={sig['value']}% {rsi_info} {vol_info} "
                     f"wick={sig.get('wick_ratio', '?')}x trend={trend} rr={rr:.1f}")

    return added


def run():
    """Entry point for signals_runner."""
    return scan_wall_street_cycle_signals()


if __name__ == '__main__':
    n = scan_wall_street_cycle_signals()
    print(f"wall_street_cycle: {n} signals emitted")
