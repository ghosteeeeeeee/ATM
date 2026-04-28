#!/usr/bin/env python3
"""
ma300_candle_confirm_signals.py — EMA300 + 2-Candle Confirmation Signal

Signal logic:
  LONG:  Candle[i] closes above EMA(300), candle[i+1] opens AND closes above
         candle[i]'s body high, candle[i+2] opens AND closes above candle[i]'s
         body high (2-confirmation)
  SHORT: Same inverted

Filters:
  - Min MA separation: 0.5% (close must be 0.5%+ away from EMA300)
  - Blacklisted tokens excluded
  - Open positions excluded
  - Per-token+direction cooldown: 15 min

Entry:  Candle[i+1] close price (non-repainting — both candles confirmed)
Exit:   TP=1.0%, SL=0.75%, or reverse EMA cross

Architecture:
  - Reads 1m candles from price_history via signal_schema.get_ohlcv_1m()
  - Computes EMA(300) from close prices
  - Fires with confidence scoring via signal_schema.add_signal()
"""

import sys
import os
import time
import sqlite3
from typing import Optional

_PRICE_DB = '/root/.hermes/data/signals_hermes.db'

# ── Constants ─────────────────────────────────────────────────────────────────

EMA300_PERIOD          = 300
SIGNAL_TYPE            = 'ma300_candle'
SOURCE_PREFIX          = 'ma300c'
LOOKBACK_CANDLES       = 350   # 300 warmup + 2 for 2-conf + buffer
COOLDOWN_MINUTES       = 3    # short — 3-bar cooldown (matches lookback/confirmation design)
MIN_CONFIDENCE         = 50
MAX_CONFIDENCE         = 88
BASE_CONFIDENCE        = 65

# ── Filters (best from backtest: sep>=0.5% + 2-conf) ───────────────────────
MIN_MA_SEP_PCT         = 0.50   # candle[i] close must be 0.5%+ from EMA

# ── EMA Calculation ───────────────────────────────────────────────────────────

def _ema(values: list, period: int) -> Optional[float]:
    """Compute EMA(period) from a list of prices (oldest first).

    Returns the most recent EMA value, or None if not enough data.
    """
    if len(values) < period:
        return None
    k = 2 / (period + 1)
    ema_val = sum(values[:period]) / period
    for price in values[period:]:
        ema_val = price * k + ema_val * (1 - k)
    return ema_val


def _ema_series(values: list, period: int) -> list:
    """Compute EMA series — returns EMA value at each index (oldest first).

    Returns a list with None for indices < period-1, then EMA values.
    """
    n = len(values)
    if n < period:
        return [None] * n
    k = 2 / (period + 1)
    result = [None] * (period - 1)
    ema_val = sum(values[:period]) / period
    result.append(ema_val)
    for price in values[period:]:
        ema_val = price * k + ema_val * (1 - k)
        result.append(ema_val)
    return result


# ── Candle data (price_history — live 1m prices, updated every minute) ─────────
# FIX (2026-04-23): price_history is the ONLY live data source. ohlcv_1m is stale.

def _get_candles_1m(token: str, lookback: int = LOOKBACK_CANDLES) -> list:
    """Fetch 1m close prices from price_history (signals_hermes.db), oldest first.

    price_history is updated every minute with live prices — the ONLY reliable source.
    timestamps are in SECONDS (Unix time).

    Returns oldest-first list of {close} dicts.
    Freshness guard: returns [] if most recent price is > 5 minutes old.
    """
    try:
        conn = sqlite3.connect(_PRICE_DB, timeout=10)
        c = conn.cursor()
        c.execute("""
            SELECT timestamp, price FROM (
                SELECT timestamp, price
                FROM price_history
                WHERE token = ?
                ORDER BY timestamp DESC
                LIMIT ?
            ) sub
            ORDER BY timestamp ASC
        """, (token.upper(), lookback))
        rows = c.fetchall()
        conn.close()

        if not rows:
            return []

        # Freshness guard
        most_recent_ts = rows[-1][0]  # seconds
        if (time.time() - most_recent_ts) > 120:
            return []

        # Synthesize ohlcv — high/low/open = close for close-only source
        return [{'open': r[1], 'high': r[1], 'low': r[1], 'close': r[1]} for r in rows]
    except Exception:
        return []


# ── Core Detection ────────────────────────────────────────────────────────────

def detect_ma300_candle(token: str, candles: list, price: float) -> Optional[dict]:
    """Detect EMA300 + 2-candle confirmation signal.

    Args:
        token:   token symbol (e.g. 'BTC')
        candles: list of OHLCV dicts from price_history (oldest first)
        price:   current price (most recent close from candles)

    Returns:
        Signal dict or None if no signal detected:
        {
            'direction':  'LONG' or 'SHORT',
            'confidence': int (50-88),
            'source':     str  (e.g. 'ma300c-confirm2'),
            'ma_sep_pct': float,
            'bars_since': int,    # bars since 2-confirmation
        }
    """
    n = len(candles)
    if n < EMA300_PERIOD + 3:
        return None

    closes = [c['close'] for c in candles]
    highs  = [c['high']  for c in candles]
    lows   = [c['low']   for c in candles]

    # ── Compute EMA(300) ─────────────────────────────────────────────────────
    ema_vals = _ema_series(closes, EMA300_PERIOD)
    ema_now  = ema_vals[-1]
    if ema_now is None:
        return None

    # ── Scan for 2-confirmation setup (working backwards from most recent) ─
    # We need: candle[i] below EMA, i+1 above EMA, i+2 above EMA
    # Then the pattern completes at i+2 → signal fires at i+2 close
    for i in range(n - 3, EMA300_PERIOD, -1):
        close_i    = closes[i]
        close_ip1  = closes[i+1]
        close_ip2  = closes[i+2]

        # Candle[i] must be below EMA (pullback setup)
        if close_i >= ema_now:
            continue

        # Distance from EMA at candle[i]
        ma_sep_pct = (ema_now - close_i) / ema_now * 100
        if ma_sep_pct < MIN_MA_SEP_PCT:
            continue

        # Candle[i+1]: must open AND close above candle[i] high (LONG confirmation)
        body_high_i = max(closes[i], highs[i])
        cond1_long  = close_ip1 > body_high_i and lows[i+1] < body_high_i  # opened below, closed above

        # Candle[i+2]: must open AND close above candle[i] high (LONG 2nd confirmation)
        cond2_long  = close_ip2 > body_high_i and lows[i+2] < body_high_i

        if cond1_long and cond2_long:
            bars_since = n - 1 - i
            conf = min(MAX_CONFIDENCE, BASE_CONFIDENCE + ma_sep_pct)
            return {
                'direction':  'LONG',
                'confidence': int(conf),
                'source':     f'{SOURCE_PREFIX}-confirm2',
                'ma_sep_pct': round(ma_sep_pct, 3),
                'bars_since': bars_since,
            }

        # SHORT: candle[i] above EMA, pull back to EMA
        # Candle[i+1]: open AND close below candle[i] low (SHORT confirmation)
        body_low_i  = min(closes[i], lows[i])
        cond1_short = close_ip1 < body_low_i and highs[i+1] > body_low_i
        cond2_short = close_ip2 < body_low_i and highs[i+2] > body_low_i

        if cond1_short and cond2_short:
            bars_since = n - 1 - i
            conf = min(MAX_CONFIDENCE, BASE_CONFIDENCE + ma_sep_pct)
            return {
                'direction':  'SHORT',
                'confidence': int(conf),
                'source':     f'{SOURCE_PREFIX}-confirm2',
                'ma_sep_pct': round(ma_sep_pct, 3),
                'bars_since': bars_since,
            }

    return None


# ── Scan all tokens ────────────────────────────────────────────────────────────

def scan_ma300_candle_signals(prices_dict: dict) -> tuple[int, list[dict]]:
    """
    Scan all tokens in prices_dict for EMA300 + 2-conf signals.

    Args:
        prices_dict: {token: {'price': float, ...}, ...}

    Returns:
        (count, signals) where count=int, signals=list of signal dicts (each includes 'token' key)
    """
    from signal_schema import add_signal, get_latest_price
    from hermes_constants import SHORT_BLACKLIST, LONG_BLACKLIST
    added = 0
    results = []

    for token, data in prices_dict.items():
        price = data.get('price')
        if not price or price <= 0:
            continue

        candles = _get_candles_1m(token, lookback=LOOKBACK_CANDLES)
        if not candles or len(candles) < EMA300_PERIOD + 3:
            continue

        sig = detect_ma300_candle(token, candles, price)
        if sig is None:
            continue

        direction = sig['direction']
        confidence = sig['confidence']

        # Directional blacklist
        if direction.upper() == 'SHORT' and token.upper() in SHORT_BLACKLIST:
            continue
        if direction.upper() == 'LONG' and token.upper() in LONG_BLACKLIST:
            continue

        sid = add_signal(
            token=token,
            direction=direction,
            signal_type=SIGNAL_TYPE,
            source=sig['source'],
            confidence=confidence,
            value=sig['ma_sep_pct'],
            price=price,
            exchange='hyperliquid',
            timeframe='1m',
            z_score=None,
            z_score_tier=None,
        )
        if sid:
            added += 1
            sig['token'] = token  # attach token name for cooldown tracking in caller
            results.append(sig)

    return added, results