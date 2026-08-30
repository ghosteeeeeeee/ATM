#!/usr/bin/env python3
"""Volume Breakout — Volume Spike + Price Momentum Signal.

Detects institutional volume entering the market with price confirmation.
Volume is the PRIMARY signal type (contributes 'Volume' family to confluence).

LONG fires when:
  1. Current volume >= 2x average volume (20-bar lookback)
  2. Price moved UP over last 3 bars (price momentum)
  3. RSI(14) > 50 (bullish bias)
  4. Close > 20-period SMA (above average)

SHORT fires when:
  1. Current volume >= 2x average volume (20-bar lookback)
  2. Price moved DOWN over last 3 bars (price momentum)
  3. RSI(14) < 50 (bearish bias)
  4. Close < 20-period SMA (below average)

Architecture:
  5m candles → volume spike detection → price momentum check → RSI filter
  → add_signal() → signals_hermes_runtime.db → signal_compactor → hotset.json

Signal types:
  - volume_breakout_long  : bullish volume spike
  - volume_breakout_short : bearish volume spike

Family: Volume (pairs with ANY other family for 2-type confluence)
"""

import sys, os, sqlite3, time
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from signal_schema import add_signal, price_age_minutes, get_cooldown, set_cooldown
from paths import HERMES_DATA

# ── Paths ─────────────────────────────────────────────────────────────────────
_CANDLES_DB = os.path.join(HERMES_DATA, 'candles.db')
_SIGNAL_LOG = '/var/www/hermes/logs/signals.log'
os.makedirs(os.path.dirname(_SIGNAL_LOG), exist_ok=True)

# ── Constants ──────────────────────────────────────────────────────────────────
VOL_SPIKE_MULT = 2.0        # volume must be >= 2x average
VOL_AVG_PERIOD = 20         # bars for average volume
VOL_MOMENTUM_BARS = 3       # bars for price momentum check
VOL_RSI_PERIOD = 14         # RSI period
VOL_COOLDOWN_MINUTES = 60   # cooldown between signals per token
VOL_LOOKBACK_5M = 200       # 5m candles to fetch

SIGNAL_TYPE_LONG = 'volume_breakout_long'
SIGNAL_TYPE_SHORT = 'volume_breakout_short'
SOURCE_LONG = 'volume-breakout-long+'
SOURCE_SHORT = 'volume-breakout-short-'


def _log(msg: str) -> None:
    print(msg)
    try:
        with open(_SIGNAL_LOG, 'a') as f:
            f.write(msg + '\n')
    except OSError:
        pass


def _get_5m_candles(token: str, lookback: int = VOL_LOOKBACK_5M) -> list:
    """Fetch 5m candles (oldest first) with volume."""
    conn = None
    try:
        conn = sqlite3.connect(_CANDLES_DB, timeout=10)
        c = conn.cursor()
        c.execute("""
            SELECT ts, open, high, low, close, volume FROM (
                SELECT ts, open, high, low, close, volume
                FROM candles_5m
                WHERE token = ? AND is_closed = 1
                ORDER BY ts DESC
                LIMIT ?
            ) sub
            ORDER BY ts ASC
        """, (token.upper(), lookback))
        rows = c.fetchall()
        if not rows:
            return []
        most_recent_ts = rows[-1][0]
        # 5m candles can be stale in flat markets — check age but allow up to 4h
        candle_age = time.time() - most_recent_ts
        if candle_age > 14400:
            return []
        return [{'ts': r[0], 'open': r[1], 'high': r[2], 'low': r[3],
                 'close': r[4], 'volume': r[5]} for r in rows]
    except Exception as e:
        _log(f"  [volume_breakout] candles error {token}: {e}")
        return []
    finally:
        if conn:
            conn.close()


def _rsi(closes: list, period: int = VOL_RSI_PERIOD) -> Optional[float]:
    """Calculate RSI."""
    if len(closes) < period + 1:
        return None
    deltas = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
    gains = [d if d > 0 else 0 for d in deltas]
    losses = [-d if d < 0 else 0 for d in deltas]
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    for i in range(period, len(deltas)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))


def _sma(values: list, period: int) -> Optional[float]:
    """Simple moving average."""
    if len(values) < period:
        return None
    return sum(values[-period:]) / period


def detect_volume_breakout(token: str, candles: list) -> Optional[dict]:
    """Detect volume spike with price momentum confirmation."""
    min_bars = max(VOL_AVG_PERIOD, VOL_RSI_PERIOD + 1, VOL_MOMENTUM_BARS + 1) + 5
    if len(candles) < min_bars:
        return None

    closes = [c['close'] for c in candles]
    volumes = [c['volume'] for c in candles]

    current_vol = volumes[-1]
    avg_vol = sum(volumes[-VOL_AVG_PERIOD - 1:-1]) / VOL_AVG_PERIOD
    if avg_vol <= 0:
        return None

    vol_ratio = current_vol / avg_vol
    if vol_ratio < VOL_SPIKE_MULT:
        return None

    price_now = closes[-1]
    price_prev = closes[-1 - VOL_MOMENTUM_BARS]
    if price_prev == 0:
        return None
    price_change_pct = (price_now - price_prev) / price_prev * 100.0

    rsi_val = _rsi(closes)
    if rsi_val is None:
        return None

    sma_val = _sma(closes, VOL_AVG_PERIOD)
    if sma_val is None:
        return None

    direction = None
    if price_change_pct > 0 and rsi_val > 50 and price_now > sma_val:
        direction = 'LONG'
    elif price_change_pct < 0 and rsi_val < 50 and price_now < sma_val:
        direction = 'SHORT'

    if direction is None:
        return None

    # Confidence: base on volume spike strength + RSI extremity
    vol_bonus = min(20, (vol_ratio - VOL_SPIKE_MULT) * 10)
    rsi_extremity = abs(rsi_val - 50) / 50.0 * 15
    momentum_bonus = min(10, abs(price_change_pct) * 5)
    confidence = int(min(85, 55 + vol_bonus + rsi_extremity + momentum_bonus))
    confidence = max(55, confidence)

    return {
        'direction': direction,
        'vol_ratio': round(vol_ratio, 2),
        'price_change_pct': round(price_change_pct, 4),
        'rsi': round(rsi_val, 1),
        'price': price_now,
        'confidence': confidence,
    }


def run(prices_dict=None) -> int:
    """Entry point for signals_runner."""
    if prices_dict is None:
        from signal_schema import get_all_latest_prices
        prices_dict = get_all_latest_prices()

    from hermes_constants import LONG_BLACKLIST, SHORT_BLACKLIST
    from position_manager import get_open_positions
    from signals.fast_momentum import recent_trade_exists, MIN_TRADE_INTERVAL_MINUTES

    open_pos = {p['token']: p['direction'] for p in get_open_positions()}
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
        if price_age_minutes(token) > 10:
            continue

        candles = _get_5m_candles(token)
        if not candles:
            continue

        sig = detect_volume_breakout(token, candles)
        if sig is None:
            continue

        direction = sig['direction']
        if direction == 'LONG' and token.upper() in LONG_BLACKLIST:
            continue
        if direction == 'SHORT' and token.upper() in SHORT_BLACKLIST:
            continue

        if get_cooldown(token, direction=direction):
            continue

        try:
            sid = add_signal(
                token=token.upper(),
                direction=direction,
                signal_type=SIGNAL_TYPE_LONG if direction == 'LONG' else SIGNAL_TYPE_SHORT,
                source=SOURCE_LONG if direction == 'LONG' else SOURCE_SHORT,
                confidence=sig['confidence'],
                value=sig['vol_ratio'],
                price=sig['price'],
                exchange='hyperliquid',
                timeframe='5m',
                z_score=None,
                z_score_tier=None,
            )
            if sid:
                added += 1
                set_cooldown(token, direction, hours=VOL_COOLDOWN_MINUTES / 60.0)
                _log(f"  {direction}-volume-breakout {token:8s} conf={sig['confidence']}% "
                     f"vol={sig['vol_ratio']}x rsi={sig['rsi']} "
                     f"chg={sig['price_change_pct']:.2f}% "
                     f"price={sig['price']:.8g} [{SOURCE_LONG if direction == 'LONG' else SOURCE_SHORT}]")
        except Exception as e:
            _log(f"  [volume_breakout] add_signal error {token}: {e}")

    return added


if __name__ == '__main__':
    from signal_schema import init_db, get_all_latest_prices
    init_db()
    prices = get_all_latest_prices()
    n = run(prices)
    print(f"[volume_breakout] Done. {n} signals emitted.")
