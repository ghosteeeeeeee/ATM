#!/usr/bin/env python3
"""Range Reversion — Mean-reversion signal for flat/ranging markets.

Fires when price is at range extremes (BB bands) in a confirmed ranging market.
Designed specifically for NEUTRAL regime where momentum signals starve.

LONG fires when:
  1. Bollinger Band width is narrow (range confirmed, BBWIDTH < threshold)
  2. Price touches lower BB band (oversold in range)
  3. RSI is oversold (< threshold)
  4. Price shows bounce from lower band (prev candle was lower, current bounced)

SHORT fires when:
  1. Bollinger Band width is narrow (range confirmed)
  2. Price touches upper BB band (overbought in range)
  3. RSI is overbought (> threshold)
  4. Price shows rejection from upper band

Architecture:
  5m candles → BB computation → range detection → RSI filter → bounce confirmation
  → add_signal() → signals_hermes_runtime.db → signal_compactor → hotset.json

Signal types:
  - range_reversion_long  : buy at range bottom
  - range_reversion_short : sell at range top

Family: Range (pairs with Momentum/Trend signals for 2-type confluence)
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
RR_BB_PERIOD = 20
RR_BB_STDDEV = 1.8
RR_BB_WIDTH_MAX = 0.04       # narrow BB = range confirmed (4% width)
RR_BB_WIDTH_SQUEEZE = 0.025  # tight squeeze = higher confidence
RR_TOUCH_ATR_MULT = 0.3     # price within 0.3*ATR of band = "touch"
RR_RSI_PERIOD = 14
RR_RSI_OVERSOLD = 35         # LONG entry: RSI below this
RR_RSI_OVERBOUGHT = 65       # SHORT entry: RSI above this
RR_ATR_PERIOD = 14
RR_MIN_BARS = 40
RR_LOOKBACK_5M = 150
RR_COOLDOWN_MINUTES = 45
RR_MIN_ATR_PCT = 0.08       # min ATR% to avoid noise (0.08% = very flat but tradeable)

SIGNAL_TYPE_LONG = 'range_reversion_long'
SIGNAL_TYPE_SHORT = 'range_reversion_short'
SOURCE_LONG = 'range-reversion-long+'
SOURCE_SHORT = 'range-reversion-short-'
SHADOW_MODE = True  # CEO 2026-09-01 — log signals without trading. Set False to go live.


def _log(msg: str) -> None:
    print(msg)
    try:
        with open(_SIGNAL_LOG, 'a') as f:
            f.write(msg + '\n')
    except OSError:
        pass


def _get_5m_candles(token: str, lookback: int = RR_LOOKBACK_5M) -> list:
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
        if candle_age > 14400:
            return []
        return [{'ts': r[0], 'open': r[1], 'high': r[2], 'low': r[3],
                 'close': r[4], 'volume': r[5]} for r in rows]
    except Exception as e:
        _log(f"  [range_reversion] candles error {token}: {e}")
        return []
    finally:
        if conn:
            conn.close()


def _rsi(closes: list, period: int = RR_RSI_PERIOD) -> Optional[float]:
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


def _atr(highs: list, lows: list, closes: list, period: int = RR_ATR_PERIOD) -> Optional[float]:
    if len(closes) < period + 1:
        return None
    trs = []
    for i in range(1, len(closes)):
        tr = max(highs[i] - lows[i],
                 abs(highs[i] - closes[i - 1]),
                 abs(lows[i] - closes[i - 1]))
        trs.append(tr)
    if len(trs) < period:
        return None
    atr_val = sum(trs[-period:]) / period
    for i in range(period, len(trs)):
        atr_val = (atr_val * (period - 1) + trs[i]) / period
    return atr_val


def detect_range_reversion(token: str, candles: list) -> Optional[dict]:
    if len(candles) < RR_MIN_BARS:
        return None

    closes = [c['close'] for c in candles]
    highs = [c['high'] for c in candles]
    lows = [c['low'] for c in candles]

    # Bollinger Bands
    if len(closes) < RR_BB_PERIOD:
        return None
    middle = sum(closes[-RR_BB_PERIOD:]) / RR_BB_PERIOD
    variance = sum((c - middle) ** 2 for c in closes[-RR_BB_PERIOD:]) / RR_BB_PERIOD
    std = variance ** 0.5
    upper = middle + RR_BB_STDDEV * std
    lower = middle - RR_BB_STDDEV * std
    bb_width = (upper - lower) / middle if middle > 0 else 0

    # Range filter: BB must be narrow
    if bb_width > RR_BB_WIDTH_MAX:
        return None

    # ATR filter: need some volatility to trade
    atr_val = _atr(highs, lows, closes)
    if atr_val is None:
        return None
    atr_pct = atr_val / closes[-1] * 100 if closes[-1] > 0 else 0
    if atr_pct < RR_MIN_ATR_PCT:
        return None

    # RSI
    rsi_val = _rsi(closes)
    if rsi_val is None:
        return None

    current = closes[-1]
    prev = closes[-2] if len(closes) >= 2 else current

    # Distance from bands (normalized by ATR)
    dist_lower = (current - lower) / atr_val if atr_val > 0 else 999
    dist_upper = (upper - current) / atr_val if atr_val > 0 else 999

    direction = None
    confidence = 60

    # LONG: price near lower band + oversold RSI + bounce starting
    if dist_lower <= RR_TOUCH_ATR_MULT and rsi_val < RR_RSI_OVERSOLD and current > prev:
        direction = 'LONG'
        # Confidence boosts
        if bb_width < RR_BB_WIDTH_SQUEEZE:
            confidence += 10  # tight squeeze = high conviction
        if rsi_val < 25:
            confidence += 5   # deeply oversold
        if dist_lower < 0:
            confidence += 5   # price was below lower band (extreme)
        # Bounce strength
        bounce_pct = (current - prev) / prev * 100 if prev > 0 else 0
        if bounce_pct > 0.05:
            confidence += 5

    # SHORT: price near upper band + overbought RSI + rejection starting
    elif dist_upper <= RR_TOUCH_ATR_MULT and rsi_val > RR_RSI_OVERBOUGHT and current < prev:
        direction = 'SHORT'
        if bb_width < RR_BB_WIDTH_SQUEEZE:
            confidence += 10
        if rsi_val > 75:
            confidence += 5
        if dist_upper < 0:
            confidence += 5
        rejection_pct = (prev - current) / prev * 100 if prev > 0 else 0
        if rejection_pct > 0.05:
            confidence += 5

    if direction is None:
        return None

    confidence = max(55, min(confidence, 88))

    return {
        'direction': direction,
        'bb_width': round(bb_width, 4),
        'rsi': round(rsi_val, 1),
        'atr_pct': round(atr_pct, 3),
        'dist_lower': round(dist_lower, 2),
        'dist_upper': round(dist_upper, 2),
        'price': current,
        'confidence': confidence,
    }


def run(prices_dict=None) -> int:
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

        sig = detect_range_reversion(token, candles)
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
        _log(f"  {tag} {direction}-range-reversion {token:8s} conf={sig['confidence']}% "
             f"bbw={sig['bb_width']:.3f} rsi={sig['rsi']} "
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
                value=sig['bb_width'],
                price=sig['price'],
                exchange='hyperliquid',
                timeframe='5m',
            )
            if sid:
                added += 1
                set_cooldown(token, direction, hours=RR_COOLDOWN_MINUTES / 60.0)
        except Exception as e:
            _log(f"  [range_reversion] add_signal error {token}: {e}")

    return added


if __name__ == '__main__':
    from signal_schema import init_db, get_all_latest_prices
    init_db()
    prices = get_all_latest_prices()
    n = run(prices)
    print(f"[range_reversion] Done. {n} signals emitted.")
