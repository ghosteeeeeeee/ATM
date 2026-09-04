#!/usr/bin/env python3
"""
ema300_dip_short.py — EMA300 Rally Seller Signal for SHORT entries.

Sells rallies to EMA300 during confirmed strong downtrends.
Only fires when:
  1. Price < EMA300 (downtrend confirmed)
  2. <30% of last 100 candles above EMA300 (strong downtrend)
  3. EMA300 slope < 0 (downtrend is real)
  4. Price within 0.5% of EMA300 (rally)
  5. RSI > 65 (overbought within downtrend)
  6. Red candle (bounce rejection confirmation)

Signal type: ema300_dip_short
Source: ema300-dip-short
"""

import sqlite3
import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from signal_schema import add_signal, get_cooldown, price_age_minutes, set_cooldown
from paths import HERMES_DATA, CANDLES_DB

from hermes_constants import (
    EMA300_DIP_SHORT_ENABLED,
    EMA300_DIP_SHORT_EMA_PERIOD,
    EMA300_DIP_SHORT_MAX_DIST_PCT,
    EMA300_DIP_SHORT_MIN_RSI,
    EMA300_DIP_SHORT_MAX_RSI,
    EMA300_DIP_SHORT_MIN_TREND_STRENGTH,
    EMA300_DIP_SHORT_MAX_EMA_SLOPE,
    EMA300_DIP_SHORT_COOLDOWN,
    EMA300_DIP_SHORT_TP_PCT,
    EMA300_DIP_SHORT_SL_PCT,
    CANDLES_STALENESS_SEC,
    SHORT_BLACKLIST,
)

# ── Constants ─────────────────────────────────────────────────────────────
SIGNAL_TYPE = 'ema300_dip_short'
SOURCE_PREFIX = 'ema300-dip-short'
LOOKBACK_CANDLES = 700
MIN_CONFIDENCE = 70
MAX_CONFIDENCE = 88
BASE_CONFIDENCE = 75
CONFIDENCE_BONUS_MAX = 13

_PRICE_DB = os.path.join(HERMES_DATA, 'signals_hermes.db')


# ── Trend Detection ─────────────────────────────────────────────────────

def detect_ema300_dip_short(token, candles, price):
    """Detect rally to EMA300 during confirmed downtrend.
    
    Fires SHORT when:
      - Price < EMA300 (downtrend confirmed)
      - <30% of last 100 candles above EMA300 (strong downtrend)
      - EMA300 slope < 0 (downtrend is real)
      - Price within 0.5% of EMA300 (rally)
      - RSI > 65 (overbought within downtrend)
      - Red candle (bounce rejection confirmation)
    """
    n = len(candles)
    if n < 500:
        return None
    
    closes = [c['close'] for c in candles]
    
    # Compute EMA300
    ema_vals = []
    ema = closes[0]
    k = 2.0 / (EMA300_DIP_SHORT_EMA_PERIOD + 1)
    for c in closes:
        ema = c * k + ema * (1 - k)
        ema_vals.append(ema)
    
    current_ema = ema_vals[-1]
    current_price = closes[-1]
    
    # ── Condition 1: Price < EMA300 (downtrend confirmed) ─────────────────
    if current_price >= current_ema:
        return None
    
    # ── Condition 2: Strong downtrend (<30% candles above EMA300) ────────
    lookback = min(100, n)
    above_count = sum(1 for i in range(n - lookback, n) if closes[i] > ema_vals[i])
    trend_strength = 100 - (above_count / lookback * 100)  # Invert: % below EMA
    
    if trend_strength < EMA300_DIP_SHORT_MIN_TREND_STRENGTH:
        return None
    
    # ── Condition 3: EMA300 slope < MAX_EMA_SLOPE (negative) ──────────────
    if n >= 20:
        ema_slope = (ema_vals[-1] - ema_vals[-20]) / ema_vals[-20] * 100
        if ema_slope >= EMA300_DIP_SHORT_MAX_EMA_SLOPE:
            return None
    else:
        return None
    
    # ── Condition 4: Price within 0.5% of EMA300 (rally) ────────────────
    dist = (current_price - current_ema) / current_ema * 100
    if dist > 0 or abs(dist) > EMA300_DIP_SHORT_MAX_DIST_PCT:
        return None
    
    # ── Condition 5: RSI > 65 (overbought within downtrend) ──────────────
    if len(closes) >= 15:
        deltas = [closes[i] - closes[i-1] for i in range(1, len(closes))]
        gains = [d if d > 0 else 0 for d in deltas[-14:]]
        losses_rsi = [-d if d < 0 else 0 for d in deltas[-14:]]
        avg_gain = sum(gains) / 14
        avg_loss = sum(losses_rsi) / 14
        if avg_loss > 0:
            rsi = 100 - (100 / (1 + avg_gain / avg_loss))
        else:
            rsi = 100.0
        
        if rsi < EMA300_DIP_SHORT_MIN_RSI or rsi > EMA300_DIP_SHORT_MAX_RSI:
            return None
    else:
        return None
    
    # ── Condition 6: Red candle (bounce rejection confirmation) ───────────
    if closes[-1] >= closes[-2]:
        return None
    
    # ── Confidence scoring ──────────────────────────────────────────────
    dist_bonus = max(0, (EMA300_DIP_SHORT_MAX_DIST_PCT - abs(dist)) / EMA300_DIP_SHORT_MAX_DIST_PCT * 6)
    rsi_bonus = max(0, (rsi - EMA300_DIP_SHORT_MIN_RSI) / (100 - EMA300_DIP_SHORT_MIN_RSI) * 6)
    trend_bonus = min(6, (trend_strength - EMA300_DIP_SHORT_MIN_TREND_STRENGTH) / 25 * 6)
    
    confidence = int(min(
        BASE_CONFIDENCE + dist_bonus + rsi_bonus + trend_bonus,
        MAX_CONFIDENCE
    ))
    
    source = f'{SOURCE_PREFIX}'
    
    return {
        'direction': 'SHORT',
        'confidence': confidence,
        'source': source,
        'dist': round(dist, 4),
        'rsi': round(rsi, 1),
        'trend_strength': round(trend_strength, 1),
        'ema_slope': round(ema_slope, 4),
        'value': float(confidence),
    }


# ── Candle Data ─────────────────────────────────────────────────────────

def _get_candles_1m(token, lookback=LOOKBACK_CANDLES):
    conn = None
    try:
        conn = sqlite3.connect(_PRICE_DB, timeout=10)
        c = conn.cursor()
        c.execute("""
            SELECT timestamp, price FROM (
                SELECT timestamp, price FROM price_history
                WHERE token = ? ORDER BY timestamp DESC LIMIT ?
            ) sub ORDER BY timestamp ASC
        """, (token.upper(), lookback))
        rows = c.fetchall()
        
        if not rows:
            return []
        
        most_recent_ts = rows[-1][0]
        if (time.time() - most_recent_ts) > CANDLES_STALENESS_SEC:
            return []
        
        return [{'close': r[1]} for r in rows]
    except Exception:
        return []
    finally:
        if conn:
            conn.close()


# ── Scanner ─────────────────────────────────────────────────────────────

def scan_signals(prices_dict=None):
    if not EMA300_DIP_SHORT_ENABLED:
        return 0
    
    if prices_dict is None:
        from signal_schema import get_all_latest_prices
        prices_dict = get_all_latest_prices()
    
    prices = prices_dict
    added = 0
    
    for token, data in prices.items():
        price = data.get('price')
        if not price or price <= 0:
            continue
        
        if price_age_minutes(token) > 10:
            continue
        
        if get_cooldown(token, direction='SHORT'):
            continue
        
        if token.upper() in SHORT_BLACKLIST:
            continue
        
        candles = _get_candles_1m(token)
        if not candles or len(candles) < 500:
            continue
        
        sig = detect_ema300_dip_short(token, candles, price)
        if sig is None:
            continue
        
        sid = add_signal(
            token=token.upper(),
            direction='SHORT',
            signal_type=SIGNAL_TYPE,
            source=sig['source'],
            confidence=sig['confidence'],
            value=sig['value'],
            price=price,
            exchange='hyperliquid',
            timeframe='1m',
            z_score=None,
            z_score_tier=None,
        )
        if sid:
            added += 1
            set_cooldown(token, direction='SHORT', hours=EMA300_DIP_SHORT_COOLDOWN / 60)
            print(f'  SHORT {token:8s} conf={sig["confidence"]:.0f}% '
                  f'dist={sig["dist"]:+.2f}% rsi={sig["rsi"]:.1f} '
                  f'trend={sig["trend_strength"]:.0f}% ema_slope={sig["ema_slope"]:+.3f}% '
                  f'[{sig["source"]}]')
    
    return added


# ── signals_runner entry point ──────────────────────────────────────────

def run(prices_dict=None):
    """Entry point for signals_runner. Returns count of signals emitted."""
    if prices_dict is None:
        from signal_schema import get_all_latest_prices
        prices_dict = get_all_latest_prices()
    return scan_signals(prices_dict)


if __name__ == '__main__':
    from signal_schema import get_all_latest_prices, init_db
    init_db()
    prices = get_all_latest_prices()
    test_tokens = {k: v for k, v in prices.items()
                   if k in ('BTC', 'ETH', 'SOL', 'DOGE', 'XRP') and v.get('price')}
    if not test_tokens:
        test_tokens = dict(list(prices.items())[:10])
    print(f"[ema300_dip_short] Testing on {len(test_tokens)} tokens...")
    n = scan_signals(test_tokens)
    print(f"[ema300_dip_short] Done. {n} signals emitted.")
