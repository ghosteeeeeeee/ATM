#!/usr/bin/env python3
"""Neutral Sniper — Mean-reversion confluence for NEUTRAL regime.

Fires in flat/ranging markets when price is at extreme levels with volume
confirmation. Designed specifically for NEUTRAL regime signal starvation.

THESIS:
  In NEUTRAL regime, 102/104 tokens are flat. Momentum signals starve.
  Mean-reversion signals catch bounces at extremes — the only edge in flat markets.

LONG fires when:
  1. RSI oversold (< 35) — price at lower extreme
  2. Chaikin Money Flow positive (accumulation despite oversold price)
  3. ATR confirms low volatility (range-bound, not crashing)

SHORT fires when:
  1. RSI overbought (> 65) — price at upper extreme
  2. Chaikin Money Flow negative (distribution despite overbought price)
  3. ATR confirms low volatility (range-bound, not spiking)

INDICATORS:
  - RSI: momentum at extremes (oversold/overbought)
  - Chaikin Money Flow: volume-weighted accumulation/distribution
  - ATR range filter: confirm ranging market, not trending

Architecture:
  5m candles → RSI → CMF → ATR filter → add_signal()
  → signals_hermes_runtime.db → signal_compactor → hotset.json

Signal types:
  - neutral_sniper_long  : buy at range bottom
  - neutral_sniper_short : sell at range top

Family: MeanReversion (pairs with ANY other family for 2-type confluence)
"""

import sys, os, sqlite3, time
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from signal_schema import add_signal, price_age_minutes, get_cooldown, set_cooldown
from paths import HERMES_DATA

_CANDLES_DB = os.path.join(HERMES_DATA, 'candles.db')
_SIGNAL_LOG = '/var/www/hermes/logs/signals.log'
os.makedirs(os.path.dirname(_SIGNAL_LOG), exist_ok=True)

# ── Constants ──────────────────────────────────────────────────────────────────
NS_RSI_PERIOD = 14
NS_RSI_OVERSOLD = 35           # LONG: RSI below this
NS_RSI_OVERBOUGHT = 65         # SHORT: RSI above this

NS_CMF_PERIOD = 20             # Chaikin Money Flow period
NS_CMF_LONG_MIN = 0.0          # LONG: CMF must be > 0 (accumulation)
NS_CMF_SHORT_MAX = 0.0         # SHORT: CMF must be < 0 (distribution)

NS_ATR_PERIOD = 14             # ATR for volatility check
NS_ATR_RANGE_MAX_PCT = 1.2     # max ATR% to confirm range (not trending/crashing)
NS_ATR_RANGE_MIN_PCT = 0.05    # min ATR% to avoid dead tokens

NS_LOOKBACK_5M = 150           # 5m candles to fetch
NS_MIN_BARS = 40               # minimum candles for detection
NS_COOLDOWN_MINUTES = 45       # per token+direction cooldown

SIGNAL_TYPE_LONG = 'neutral_sniper_long'
SIGNAL_TYPE_SHORT = 'neutral_sniper_short'
SOURCE_LONG = 'neutral-sniper-long+'
SOURCE_SHORT = 'neutral-sniper-short-'

SHADOW_MODE = True  # shadow mode — log without trading


def _log(msg: str) -> None:
    print(msg)
    try:
        with open(_SIGNAL_LOG, 'a') as f:
            f.write(msg + '\n')
    except OSError:
        pass


def _get_5m_candles(token: str, lookback: int = NS_LOOKBACK_5M) -> list:
    """Fetch 5m candles (oldest first) with OHLCV."""
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
        candle_age = time.time() - most_recent_ts
        if candle_age > 14400:  # 4h stale
            return []
        return [{'ts': r[0], 'open': r[1], 'high': r[2], 'low': r[3],
                 'close': r[4], 'volume': r[5]} for r in rows]
    except Exception as e:
        _log(f"  [neutral_sniper] candles error {token}: {e}")
        return []
    finally:
        if conn:
            conn.close()


def _rsi(closes: list, period: int = NS_RSI_PERIOD) -> Optional[float]:
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


def _cmf(candles: list, period: int = NS_CMF_PERIOD) -> Optional[float]:
    """Calculate Chaikin Money Flow."""
    if len(candles) < period:
        return None
    mfv_sum = 0.0
    vol_sum = 0.0
    for c in candles[-period:]:
        high_low = c['high'] - c['low']
        if high_low == 0:
            mfm = 0.0
        else:
            mfm = ((c['close'] - c['low']) - (c['high'] - c['close'])) / high_low
        mfv = mfm * c['volume']
        mfv_sum += mfv
        vol_sum += c['volume']
    if vol_sum == 0:
        return None
    return mfv_sum / vol_sum


def _atr(candles: list, period: int = NS_ATR_PERIOD) -> Optional[float]:
    """Calculate ATR as percentage of price."""
    if len(candles) < period + 1:
        return None
    trs = []
    for i in range(1, len(candles)):
        tr = max(candles[i]['high'] - candles[i]['low'],
                 abs(candles[i]['high'] - candles[i - 1]['close']),
                 abs(candles[i]['low'] - candles[i - 1]['close']))
        trs.append(tr)
    if len(trs) < period:
        return None
    atr_val = sum(trs[-period:]) / period
    price = candles[-1]['close']
    if price <= 0:
        return None
    return atr_val / price * 100.0


def detect_neutral_sniper(token: str, candles: list) -> Optional[dict]:
    """Detect mean-reversion setup in NEUTRAL regime."""
    if len(candles) < NS_MIN_BARS:
        return None

    closes = [c['close'] for c in candles]

    # RSI
    rsi_val = _rsi(closes)
    if rsi_val is None:
        return None

    # CMF
    cmf_val = _cmf(candles)
    if cmf_val is None:
        return None

    # ATR range filter
    atr_pct = _atr(candles)
    if atr_pct is None:
        return None
    if atr_pct < NS_ATR_RANGE_MIN_PCT or atr_pct > NS_ATR_RANGE_MAX_PCT:
        return None

    price = closes[-1]
    direction = None
    confidence = 65

    # LONG: RSI oversold + CMF accumulation (volume confirms bounce)
    if rsi_val < NS_RSI_OVERSOLD and cmf_val > NS_CMF_LONG_MIN:
        direction = 'LONG'
        if rsi_val < 25:
            confidence += 5   # deeply oversold
        if cmf_val > 0.1:
            confidence += 5   # strong accumulation
        if atr_pct < 0.5:
            confidence += 3   # tight range = high conviction

    # SHORT: RSI overbought + CMF distribution (volume confirms rejection)
    elif rsi_val > NS_RSI_OVERBOUGHT and cmf_val < NS_CMF_SHORT_MAX:
        direction = 'SHORT'
        if rsi_val > 75:
            confidence += 5
        if cmf_val < -0.1:
            confidence += 5
        if atr_pct < 0.5:
            confidence += 3

    if direction is None:
        return None

    confidence = max(60, min(confidence, 88))

    return {
        'direction': direction,
        'rsi': round(rsi_val, 1),
        'cmf': round(cmf_val, 4),
        'atr_pct': round(atr_pct, 3),
        'price': price,
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

        sig = detect_neutral_sniper(token, candles)
        if sig is None:
            continue

        direction = sig['direction']
        if direction == 'LONG' and token.upper() in LONG_BLACKLIST:
            continue
        if direction == 'SHORT' and token.upper() in SHORT_BLACKLIST:
            continue

        if get_cooldown(token, direction=direction):
            continue

        tag = '[SHADOW]' if SHADOW_MODE else '[LIVE]'
        _log(f"  {tag} {direction}-neutral-sniper {token:8s} conf={sig['confidence']}% "
             f"rsi={sig['rsi']} cmf={sig['cmf']:.4f} "
             f"atr%={sig['atr_pct']:.3f} "
             f"price={sig['price']:.8g} [{SOURCE_LONG if direction == 'LONG' else SOURCE_SHORT}]")
        if SHADOW_MODE:
            added += 1
            continue
        try:
            sid = add_signal(
                token=token.upper(),
                direction=direction,
                signal_type=SIGNAL_TYPE_LONG if direction == 'LONG' else SIGNAL_TYPE_SHORT,
                source=SOURCE_LONG if direction == 'LONG' else SOURCE_SHORT,
                confidence=sig['confidence'],
                value=sig['rsi'],
                price=sig['price'],
                exchange='hyperliquid',
                timeframe='5m',
            )
            if sid:
                added += 1
                set_cooldown(token, direction, hours=NS_COOLDOWN_MINUTES / 60.0)
        except Exception as e:
            _log(f"  [neutral_sniper] add_signal error {token}: {e}")

    return added


if __name__ == '__main__':
    from signal_schema import init_db, get_all_latest_prices
    init_db()
    prices = get_all_latest_prices()
    n = run(prices)
    print(f"[neutral_sniper] Done. {n} signals emitted.")
