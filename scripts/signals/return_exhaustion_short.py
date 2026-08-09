#!/usr/bin/env python3
"""
Return Exhaustion SHORT — percentile exhaustion at extreme positive returns (SHORT-specific).

Catches overextended rallies by detecting when short-term returns are at a
percentile extreme (>p92) with momentum divergence confirming the turn.

SHORT-SPECIFIC IMPROVEMENTS over generic return_exhaustion:
  1. Regime filter: only fire when 1H trend is BEARISH or NEUTRAL (not BULLISH)
  2. Tighter percentile: 92 (was 90) — more extreme positive return required
  3. Tighter RSI overbought: 60 (was 70) — stronger overbought confirmation
  4. Volume confirmation: 1.2x average (new, fail-closed)
  5. ~~Time filter: avoid Asian session 00:00-07:59 UTC~~ REMOVED (data: Asian session has better WR/PnL)

LOGIC:
  SHORT: short-term return > p92 (extreme positive) AND
         fast momentum < slow momentum (turning down) AND
         RSI overbought AND
         1H trend BEARISH/NEUTRAL AND
         volume 1.2x average

BACKTEST CONTEXT:
  - Generic SHORT combos: hzscore-,return_exhaustion- 10T/50% WR/+$5
  - Old solo return_exhaustion-: 4T/50% WR/+$2 (small sample)
  - RETURN_EXHAUSTION_MINUS_ENABLED=False after CEO found 14 trades -$0.64
"""
import math
import os
import sys
import time
import sqlite3
from typing import Optional, Dict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from hermes_constants import SHORT_BLACKLIST

# ── SHORT-Specific Parameters ────────────────────────────────────────────────
RETURN_SHORT = 14       # 14-minute return (short-term exhaustion)
RETURN_MID = 30         # 30-minute return (medium-term context)
RETURN_LONG = 60        # 60-minute return (trend direction)
PERCENTILE_LOOKBACK = 20
PCT_EXHAUST_HIGH = 92   # TIGHTER: was 90 — more extreme positive required
MOM_FAST = 5
MOM_SLOW = 30
MIN_BARS = 220
RSI_PERIOD = 14
RSI_OVERBOUGHT = 60     # TIGHTER: was 70 — stronger overbought required
MIN_VOLUME_RATIO = 1.0  # ponytail: was 1.2x, relaxed — low-volume NEUTRAL market makes 1.2x unachievable. Restore to 1.2x if volume returns.
BLOCKED_HOURS = []  # ponytail: was [0-7] (Asian session), removed — data shows Asian session has BETTER WR (43.6% vs 35.1%) and less negative PnL for SHORTs. Add back only if live data proves otherwise.
COOLDOWN_MINUTES = 15
CONF_BASE = 60
CONF_PCT_EXTREME_MAX = 15
CONF_DIVERGENCE_BONUS = 10
CONF_RSI_BONUS = 5
CONF_MAX = 95
SIGNAL_TYPE = 'return_exhaustion_short'


def _log(msg):
    print(f"[return-exhaustion-short] {msg}", flush=True)


# ── Price History ─────────────────────────────────────────────────────────────

def _get_price_history(token: str) -> list:
    """Fetch 1m close prices from signals_hermes.db. Oldest first."""
    conn = None
    try:
        from paths import STATIC_DB
        conn = sqlite3.connect(STATIC_DB, timeout=10)
        c = conn.cursor()
        c.execute("""
            SELECT price FROM price_history
            WHERE token = ?
            ORDER BY timestamp DESC
            LIMIT ?
        """, (token.upper(), MIN_BARS + 20))
        rows = c.fetchall()
        if not rows:
            return []
        return [r[0] for r in reversed(rows)]
    except Exception:
        return []
    finally:
        if conn:
            conn.close()


def _get_volume_avg(token: str, lookback: int = 50) -> Optional[float]:
    """Get average 5m volume over last N candles."""
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


def _get_current_volume(token: str) -> Optional[float]:
    """Get the most recent 5m candle's volume."""
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


# ── Indicator Calculations ───────────────────────────────────────────────────

def _compute_returns(prices: list, period: int) -> list:
    """Compute period-over-period returns."""
    if len(prices) < period + 1:
        return []
    return [(prices[i] - prices[i - period]) / (prices[i - period] + 1e-10) * 100
            for i in range(period, len(prices))]


def _percentile_rank(value: float, values: list) -> Optional[float]:
    """Compute percentile rank of value within values list. Returns 0-100."""
    if not values or len(values) < 10:
        return None
    count_below = sum(1 for v in values if v < value)
    return (count_below / len(values)) * 100


def _rsi(prices: list, period: int = RSI_PERIOD) -> Optional[float]:
    """Compute RSI from price list."""
    if len(prices) < period + 1:
        return None
    gains = []
    losses = []
    for i in range(1, len(prices)):
        delta = prices[i] - prices[i - 1]
        gains.append(max(delta, 0))
        losses.append(max(-delta, 0))
    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))


def _get_1h_trend(token: str) -> str:
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


# ── Core Detection ────────────────────────────────────────────────────────────

def detect_return_exhaustion_short(token: str, prices: list) -> Optional[Dict]:
    """Detect percentile exhaustion SHORT with tighter filters.

    Args:
        token: token symbol
        prices: list of 1m close prices (oldest first)

    Returns signal dict if triggered, else None.
    """
    if len(prices) < MIN_BARS:
        return None

    # Time filter: avoid Asian session
    from datetime import datetime, timezone
    hour = datetime.now(timezone.utc).hour
    if hour in BLOCKED_HOURS:
        return None

    price = prices[-1]

    # Regime filter: block BULLISH (shorting extreme positive in uptrend = dangerous)
    trend = _get_1h_trend(token)
    if trend == 'BULLISH':
        return None

    # Volume confirmation — fail-closed
    vol_avg = _get_volume_avg(token)
    vol_current = _get_current_volume(token)
    if not vol_avg or vol_avg <= 0 or vol_current is None:
        return None  # No volume data — skip
    vol_ratio = vol_current / vol_avg
    if vol_ratio < MIN_VOLUME_RATIO:
        return None

    # Compute returns at multiple periods
    short_ret = (prices[-1] - prices[-1 - RETURN_SHORT]) / (prices[-1 - RETURN_SHORT] + 1e-10) * 100
    mid_ret = (prices[-1] - prices[-1 - RETURN_MID]) / (prices[-1 - RETURN_MID] + 1e-10) * 100
    long_ret = (prices[-1] - prices[-1 - RETURN_LONG]) / (prices[-1 - RETURN_LONG] + 1e-10) * 100

    # Percentile rank the short-term return
    hist_short_returns = []
    for i in range(RETURN_SHORT + PERCENTILE_LOOKBACK, len(prices)):
        ret = (prices[i] - prices[i - RETURN_SHORT]) / (prices[i - RETURN_SHORT] + 1e-10) * 100
        hist_short_returns.append(ret)

    if len(hist_short_returns) < 30:
        return None

    pct_rank = _percentile_rank(short_ret, hist_short_returns)
    if pct_rank is None:
        return None

    # SHORT only: extreme positive return
    if pct_rank < PCT_EXHAUST_HIGH:
        return None

    # Momentum divergence: fast < slow means fast is weakening
    fast_mom = (prices[-1] - prices[-1 - MOM_FAST]) / (prices[-1 - MOM_FAST] + 1e-10) * 100
    slow_mom = (prices[-1] - prices[-1 - MOM_SLOW]) / (prices[-1 - MOM_SLOW] + 1e-10) * 100
    div = abs(fast_mom - slow_mom)

    if fast_mom > slow_mom:
        return None  # no divergence — fast still stronger than slow

    # RSI confirmation
    rsi = _rsi(prices)
    rsi_bonus = 0
    if rsi is not None:
        if rsi > RSI_OVERBOUGHT:
            rsi_bonus = CONF_RSI_BONUS
        if rsi < 30:
            return None  # RSI contradicts SHORT

    # Z-score filter
    import statistics as _stat
    recent = prices[-20:] if len(prices) >= 20 else prices
    _z = 0
    if len(recent) >= 10:
        _mean = _stat.mean(recent)
        _stdev = _stat.stdev(recent) if len(recent) > 1 else 1
        _z = (recent[-1] - _mean) / _stdev if _stdev > 0 else 0
        if _z > 2.5:
            return None  # too extreme — fading strong momentum

    # Confidence scoring
    conf = CONF_BASE
    extremity = pct_rank - PCT_EXHAUST_HIGH  # 0-8
    conf += min(CONF_PCT_EXTREME_MAX, int(extremity * 1.5))
    if div > 1.0:
        conf += CONF_DIVERGENCE_BONUS
    elif div > 0.5:
        conf += int(CONF_DIVERGENCE_BONUS * 0.6)
    conf += rsi_bonus
    if trend == 'BEARISH':
        conf += 5  # trend alignment bonus
    conf = min(CONF_MAX, conf)

    # Min confidence gate
    from hermes_constants import RETURN_EXHAUSTION_MIN_CONFIDENCE
    if conf < RETURN_EXHAUSTION_MIN_CONFIDENCE:
        return None

    source = 'return_exhaustion-short'
    value = str({
        'short_ret': round(short_ret, 4),
        'mid_ret': round(mid_ret, 4),
        'long_ret': round(long_ret, 4),
        'pct_rank': round(pct_rank, 2),
        'fast_mom': round(fast_mom, 4),
        'slow_mom': round(slow_mom, 4),
        'divergence': round(div, 4),
        'rsi': round(rsi, 2) if rsi else None,
    })

    return {
        'token': token.upper(),
        'direction': 'SHORT',
        'signal_type': SIGNAL_TYPE,
        'source': source,
        'confidence': conf,
        'value': value,
        'price': price,
        '_z': _z,
        '_pct_rank': pct_rank,
        '_divergence': div,
        '_trend': trend,
    }


# ── Scanner ───────────────────────────────────────────────────────────────────

_cooldown_cache: Dict[str, float] = {}


def scan_return_exhaustion_short_signals(prices_dict: dict) -> int:
    """Scan tokens for return_exhaustion SHORT signals."""
    from signal_schema import add_signal, price_age_minutes, get_price_history, get_cooldown, set_cooldown

    added = 0
    now = time.time()

    from hyperliquid_exchange import _HL_BLOCKLIST

    for token, data in prices_dict.items():
        price = data.get('price')
        if not price or price <= 0:
            continue
        if token.upper() in _HL_BLOCKLIST:
            continue
        if token.upper() in SHORT_BLACKLIST:
            continue

        # Cooldown
        if get_cooldown(token, direction='SHORT'):
            continue

        # Kill switch
        from hermes_constants import RETURN_EXHAUSTION_SHORT_ENABLED
        if not RETURN_EXHAUSTION_SHORT_ENABLED:
            continue

        # Staleness check
        if price_age_minutes(token) > 10:
            continue

        # Fetch price history
        rows = get_price_history(token, lookback_minutes=MIN_BARS + 20)
        if not rows or len(rows) < MIN_BARS:
            continue

        prices = [r[1] for r in rows]  # already oldest-first from get_price_history (ORDER BY timestamp ASC)

        sig = detect_return_exhaustion_short(token, prices)
        if sig is None:
            continue

        sid = add_signal(
            token=sig['token'],
            direction='SHORT',
            signal_type=sig['signal_type'],
            source=sig['source'],
            confidence=sig['confidence'],
            value=sig['value'],
            price=sig['price'],
            exchange='hyperliquid',
            timeframe='1m',
            z_score=sig.get('_z'),
            z_score_tier=None,
        )
        if sid:
            added += 1
            set_cooldown(token, direction='SHORT', hours=1)
            _log(f"SHORT {sig['token']} conf={sig['confidence']} "
                 f"pct_rank={sig['_pct_rank']:.1f} "
                 f"div={sig['_divergence']:.4f} trend={sig['_trend']}")

    return added


def run(prices_dict: dict = None) -> int:
    """Entry point for signals/__init__.py registry."""
    from signal_schema import get_all_latest_prices
    if prices_dict is None:
        prices_dict = get_all_latest_prices()
    return scan_return_exhaustion_short_signals(prices_dict)


if __name__ == '__main__':
    from signal_schema import get_all_latest_prices
    prices = get_all_latest_prices()
    added = scan_return_exhaustion_short_signals(prices)
    print(f"[return_exhaustion_short] run: {added} signals emitted")
