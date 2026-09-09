#!/usr/bin/env python3
"""breakout_long.py — Volume-confirmed breakout LONG.

Thesis: Consolidation (low ATR) followed by breakout with volume = real move.
Price breaks resistance with momentum confirmation.

Entry: ATR(14) < 0.5% + price breaks 1h high by 0.3% + volume > 2x avg
Exit: Trail 2.0x ATR, SL 1.5x ATR, time exit 4h
"""

import sys, os, sqlite3, time
from typing import Optional

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from signal_schema import add_signal, get_cooldown, set_cooldown, price_age_minutes

SIGNAL_LOG = '/var/www/hermes/logs/signals.log'
os.makedirs(os.path.dirname(SIGNAL_LOG), exist_ok=True)


def _log(msg: str) -> None:
    print(msg)
    try:
        with open(SIGNAL_LOG, 'a') as log_file:
            log_file.write(msg + '\n')
    except OSError:
        pass


# ── Paths ─────────────────────────────────────────────────────────────────────
from paths import RUNTIME_DB, STATIC_DB, CANDLES_DB
_RUNTIME_DB = RUNTIME_DB
_PRICE_DB = STATIC_DB
_CANDLES_DB = CANDLES_DB

# ── Constants (from hermes_constants.py) ──────────────────────────────────────
from hermes_constants import (
    BREAKOUT_LONG_ENABLED,
    BREAKOUT_LONG_PLUS_ENABLED,
    BREAKOUT_LONG_MINUS_ENABLED,
    BREAKOUT_LONG_ATR_PERIOD,
    BREAKOUT_LONG_ATR_MAX_PCT,
    BREAKOUT_LONG_RANGE_PERIOD,
    BREAKOUT_LONG_BREAKOUT_PCT,
    BREAKOUT_LONG_CLOSE_STRENGTH,
    BREAKOUT_LONG_VOL_LOOKBACK,
    BREAKOUT_LONG_VOL_MULT,
    BREAKOUT_LONG_CONF_BASE,
    BREAKOUT_LONG_CONF_FLOOR,
    BREAKOUT_LONG_CONF_CAP,
    BREAKOUT_LONG_COOLDOWN_HOURS,
    LONG_BLACKLIST,
)

SIGNAL_TYPE = 'breakout_long'
SOURCE = 'breakout-long+'
PERIOD = 300  # EMA300 period (for reference)
DRY_RUN = '--dry' in sys.argv


# ═══════════════════════════════════════════════════════════════════════════════
# Data fetch
# ═══════════════════════════════════════════════════════════════════════════════

def _get_5m_candles(token: str, limit: int = 500) -> list:
    """Fetch 5m candles from DB. Returns oldest-first list of dicts."""
    conn = None
    try:
        conn = sqlite3.connect(_CANDLES_DB, timeout=10)
        c = conn.cursor()
        c.execute("""
            SELECT ts, open, high, low, close, volume FROM candles_5m
            WHERE token = ? ORDER BY ts DESC LIMIT ?
        """, (token.upper(), limit))
        rows = c.fetchall()
        if not rows:
            return []
        return [{'timestamp': r[0], 'open': r[1], 'high': r[2], 'low': r[3],
                 'close': r[4], 'volume': r[5]} for r in reversed(rows)]
    except Exception as e:
        print(f"  [breakout-long] DB error for {token}: {e}")
        return []
    finally:
        if conn:
            conn.close()


# ═══════════════════════════════════════════════════════════════════════════════
# Indicators
# ═══════════════════════════════════════════════════════════════════════════════

def _atr(highs: list, lows: list, closes: list, period: int = 14) -> list:
    """ATR using Wilder smoothing. Returns list (None for first period-1 bars)."""
    if len(closes) < period + 1:
        return [None] * len(closes)
    trs = []
    for i in range(1, len(closes)):
        tr = max(highs[i] - lows[i], abs(highs[i] - closes[i-1]), abs(lows[i] - closes[i-1]))
        trs.append(tr)
    atrs = [None] * period
    atr_val = sum(trs[:period]) / period
    atrs.append(atr_val)
    for i in range(period, len(trs)):
        atr_val = (atr_val * (period - 1) + trs[i]) / period
        atrs.append(atr_val)
    return atrs


# ═══════════════════════════════════════════════════════════════════════════════
# Detection
# ═══════════════════════════════════════════════════════════════════════════════

def detect_breakout_long(token: str, candles: list) -> Optional[dict]:
    """Detect volume-confirmed breakout LONG.
    
    Entry conditions:
      1. ATR(14) < 0.5% — consolidation
      2. Price breaks 1h high by 0.3% — breakout
      3. Volume > 2x average — confirmation
      4. Close near high (close > high * 0.997) — candle strength
    """
    if len(candles) < BREAKOUT_LONG_RANGE_PERIOD + 20:
        return None

    closes = [c['close'] for c in candles]
    highs = [c['high'] for c in candles]
    lows = [c['low'] for c in candles]
    volumes = [c['volume'] for c in candles]

    latest_idx = len(closes) - 1
    price = closes[latest_idx]

    # ── FILTER 1: ATR compression ──────────────────────────────────────
    atr_vals = _atr(highs, lows, closes, BREAKOUT_LONG_ATR_PERIOD)
    if atr_vals[latest_idx] is None:
        return None
    atr_pct = atr_vals[latest_idx] / price * 100
    if atr_pct > BREAKOUT_LONG_ATR_MAX_PCT:
        return None  # not compressed enough

    # ── FILTER 2: Range breakout ───────────────────────────────────────
    range_high = max(highs[latest_idx - BREAKOUT_LONG_RANGE_PERIOD:latest_idx])
    if range_high <= 0:
        return None  # degenerate data
    breakout_threshold = range_high * (1 + BREAKOUT_LONG_BREAKOUT_PCT / 100)
    if price <= breakout_threshold:
        return None  # no breakout

    # ── FILTER 3: Volume confirmation ──────────────────────────────────
    vol_avg = sum(volumes[latest_idx - BREAKOUT_LONG_VOL_LOOKBACK:latest_idx]) / BREAKOUT_LONG_VOL_LOOKBACK
    if vol_avg <= 0:
        return None
    vol_ratio = volumes[latest_idx] / vol_avg
    if vol_ratio < BREAKOUT_LONG_VOL_MULT:
        return None  # volume too low

    # ── FILTER 4: Candle strength ──────────────────────────────────────
    if price < highs[latest_idx] * BREAKOUT_LONG_CLOSE_STRENGTH:
        return None  # weak close

    # ── Confidence ─────────────────────────────────────────────────────
    vol_bonus = min(15, (vol_ratio - 2.0) * 5)
    breakout_mag = (price - range_high) / range_high * 100
    breakout_bonus = min(10, breakout_mag * 5)
    confidence = int(min(BREAKOUT_LONG_CONF_CAP,
        BREAKOUT_LONG_CONF_BASE + vol_bonus + breakout_bonus))
    confidence = max(BREAKOUT_LONG_CONF_FLOOR, confidence)

    return {
        'direction': 'LONG',
        'confidence': confidence,
        'value': round(atr_pct, 4),
        'price': price,
        'z_score': None,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# Scanner
# ═══════════════════════════════════════════════════════════════════════════════

def scan_breakout_long_signals(prices_dict: dict) -> int:
    """Scan tokens for breakout_long signals."""
    from hermes_constants import BREAKOUT_LONG_ENABLED
    if not BREAKOUT_LONG_ENABLED:
        return 0

    from position_manager import get_open_positions as _get_open_pos
    from hyperliquid_exchange import is_delisted
    from signals.fast_momentum import recent_trade_exists, MIN_TRADE_INTERVAL_MINUTES

    open_pos = {p['token']: p['direction'] for p in _get_open_pos()}
    added = 0

    for token, data in prices_dict.items():
        if token.startswith('@'):
            continue
        price = data.get('price')
        if not price or price <= 0:
            continue
        if token.upper() in open_pos:
            continue
        if recent_trade_exists(token, MIN_TRADE_INTERVAL_MINUTES):
            continue
        if is_delisted(token.upper()):
            continue
        if price_age_minutes(token) > 10:
            continue

        candles = _get_5m_candles(token)
        if not candles or len(candles) < BREAKOUT_LONG_RANGE_PERIOD + 20:
            continue

        sig = detect_breakout_long(token, candles)
        if sig is None:
            continue

        if get_cooldown(token, direction='LONG'):
            continue

        if token.upper() in LONG_BLACKLIST:
            continue

        if DRY_RUN:
            _log(f"  [DRY] LONG-breakout-long {token:8s} conf={sig['confidence']:.0f}% "
                 f"price={sig['price']:.8g} atr={sig['value']:.4f}% [{SOURCE}]")
            continue

        try:
            sid = add_signal(
                token=token.upper(),
                direction='LONG',
                signal_type=SIGNAL_TYPE,
                source=SOURCE,
                confidence=sig['confidence'],
                value=sig.get('value'),
                price=sig['price'],
                exchange='hyperliquid',
                timeframe='5m',
                z_score=sig.get('z_score'),
            )
            if sid:
                added += 1
                set_cooldown(token, 'LONG', hours=BREAKOUT_LONG_COOLDOWN_HOURS)
                _log(f"  LONG-breakout-long {token:8s} conf={sig['confidence']:.0f}% "
                     f"price={sig['price']:.8g} atr={sig['value']:.4f}% [{SOURCE}]")
        except Exception as e:
            print(f"[breakout-long] add_signal error for {token}: {e}")

    return added


# ═══════════════════════════════════════════════════════════════════════════════
# CLI entry point
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == '__main__':
    from signal_schema import init_db

    conn = None
    try:
        conn = sqlite3.connect(_PRICE_DB, timeout=10)
        c = conn.cursor()
        c.execute("""
            SELECT DISTINCT token FROM price_history
            WHERE timestamp > ?
            ORDER BY token
        """, (int(time.time()) - 600,))
        tokens = [r[0] for r in c.fetchall()]
    finally:
        if conn:
            conn.close()

    prices = {}
    conn = None
    try:
        conn = sqlite3.connect(_PRICE_DB, timeout=10)
        c = conn.cursor()
        c.execute("""
            SELECT token, price FROM price_history
            WHERE (token, timestamp) IN (
                SELECT token, MAX(timestamp) FROM price_history
                WHERE timestamp > ?
                GROUP BY token
            )
        """, (int(time.time()) - 600,))
        for row in c.fetchall():
            prices[row[0]] = {'price': row[1]}
    finally:
        if conn:
            conn.close()

    mode = "DRY" if DRY_RUN else "LIVE"
    print(f"[breakout-long] Testing on {len(prices)} tokens ({mode} mode)...")
    init_db()
    n = scan_breakout_long_signals(prices)
    print(f"[breakout-long] Done. {n} signals emitted.")


# ═══════════════════════════════════════════════════════════════════════════════
# signals_runner entry point
# ═══════════════════════════════════════════════════════════════════════════════

def run(prices_dict=None):
    """Entry point for signals_runner."""
    if prices_dict is None:
        from signal_schema import get_all_latest_prices
        prices_dict = get_all_latest_prices()
    return scan_breakout_long_signals(prices_dict)
