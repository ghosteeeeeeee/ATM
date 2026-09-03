#!/usr/bin/env python3
"""
ema300_dip.py — EMA300 Dip Buyer Signal for LONG entries.

Buys dips to EMA300 during confirmed strong uptrends.
Only fires when:
  1. Price > EMA300 (uptrend confirmed)
  2. >80% of last 100 candles above EMA300 (trend strength)
  3. EMA300 slope > 0 (uptrend is real)
  4. Price within 0.5% of EMA300 (dip)
  5. RSI < 35 (oversold within uptrend)
  6. Green candle (bounce confirmation)

Signal type: ema300_dip
Source: ema300-dip
"""

import sqlite3
import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from signal_schema import add_signal, get_cooldown, price_age_minutes, set_cooldown
from paths import HERMES_DATA, CANDLES_DB

from hermes_constants import (
    EMA300_DIP_ENABLED,
    EMA300_DIP_EMA_PERIOD,
    EMA300_DIP_MAX_DIST_PCT,
    EMA300_DIP_MIN_RSI,
    EMA300_DIP_MAX_RSI,
    EMA300_DIP_MIN_TREND_STRENGTH,
    EMA300_DIP_MIN_EMA_SLOPE,
    EMA300_DIP_COOLDOWN,
    EMA300_DIP_TP_PCT,
    EMA300_DIP_SL_PCT,
    CANDLES_STALENESS_SEC,
    LONG_BLACKLIST,
)

# ── Constants ─────────────────────────────────────────────────────────────
SIGNAL_TYPE = 'ema300_dip'
SOURCE_PREFIX = 'ema300-dip'
LOOKBACK_CANDLES = 700  # Need 700 candles for reliable EMA300 (matches accel_300_v2_long)
MIN_CONFIDENCE = 70
MAX_CONFIDENCE = 88
BASE_CONFIDENCE = 75
CONFIDENCE_BONUS_MAX = 13

_PRICE_DB = os.path.join(HERMES_DATA, 'signals_hermes.db')


# ── EMA Calculation ───────────────────────────────────────────────────────

def _compute_ema(prices, period):
    """Compute EMA for a list of prices."""
    if not prices or len(prices) < period:
        return prices[-1] if prices else 0
    k = 2.0 / (period + 1)
    ema = prices[0]
    for p in prices[1:]:
        ema = p * k + ema * (1 - k)
    return ema


# ── Trend Detection ─────────────────────────────────────────────────────

def detect_ema300_dip(token, candles, price):
    """Detect dip to EMA300 during confirmed uptrend.
    
    Fires LONG when:
      - Price > EMA300 (uptrend confirmed)
      - >80% of last 100 candles above EMA300 (trend strength)
      - EMA300 slope > 0 (uptrend is real)
      - Price within 0.5% of EMA300 (dip)
      - RSI < 35 (oversold within uptrend)
      - Green candle (bounce confirmation)
    """
    n = len(candles)
    if n < 500:  # Need at least 500 candles for reliable EMA300
        return None
    
    closes = [c['close'] for c in candles]
    
    # Compute EMA300
    ema_vals = []
    ema = closes[0]
    k = 2.0 / (EMA300_DIP_EMA_PERIOD + 1)
    for c in closes:
        ema = c * k + ema * (1 - k)
        ema_vals.append(ema)
    
    current_ema = ema_vals[-1]
    current_price = closes[-1]
    
    # ── Condition 1: Price > EMA300 ─────────────────────────────────────
    if current_price <= current_ema:
        return None
    
    # ── Condition 2: Trend strength (>70% candles above EMA300) ─────────
    lookback = min(100, n)
    above_count = sum(1 for i in range(n - lookback, n) if closes[i] > ema_vals[i])
    trend_strength = above_count / lookback * 100
    
    if trend_strength < EMA300_DIP_MIN_TREND_STRENGTH:
        return None
    
    # ── Condition 3: EMA300 slope > MIN_EMA_SLOPE ──────────────────────────
    if n >= 20:
        ema_slope = (ema_vals[-1] - ema_vals[-20]) / ema_vals[-20] * 100
        if ema_slope <= EMA300_DIP_MIN_EMA_SLOPE:
            return None
    else:
        return None
    
    # ── Condition 4: Price within 0.8% of EMA300 (dip) ─────────────────
    dist = (current_price - current_ema) / current_ema * 100
    if dist < 0 or dist > EMA300_DIP_MAX_DIST_PCT:
        return None
    
    # ── Condition 5: RSI < 40 ──────────────────────────────────────────
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
        
        if rsi < EMA300_DIP_MIN_RSI or rsi > EMA300_DIP_MAX_RSI:
            return None
    else:
        return None
    
    # ── Condition 6: Green candle (bounce confirmation) ─────────────────
    if closes[-1] <= closes[-2]:
        return None
    
    # ── Confidence scoring ──────────────────────────────────────────────
    # Higher confidence when:
    # - Closer to EMA300 (better entry)
    # - Lower RSI (more oversold)
    # - Higher trend strength
    dist_bonus = max(0, (EMA300_DIP_MAX_DIST_PCT - dist) / EMA300_DIP_MAX_DIST_PCT * 6)
    rsi_bonus = max(0, (EMA300_DIP_MAX_RSI - rsi) / EMA300_DIP_MAX_RSI * 6)
    trend_bonus = min(6, (trend_strength - EMA300_DIP_MIN_TREND_STRENGTH) / 25 * 6)
    
    confidence = int(min(
        BASE_CONFIDENCE + dist_bonus + rsi_bonus + trend_bonus,
        MAX_CONFIDENCE
    ))
    
    source = f'{SOURCE_PREFIX}'
    
    return {
        'direction': 'LONG',
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
    if not EMA300_DIP_ENABLED:
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
        
        if get_cooldown(token, direction='LONG'):
            continue
        
        if token.upper() in LONG_BLACKLIST:
            continue
        
        candles = _get_candles_1m(token)
        if not candles or len(candles) < 500:
            continue
        
        sig = detect_ema300_dip(token, candles, price)
        if sig is None:
            continue
        
        sid = add_signal(
            token=token.upper(),
            direction='LONG',
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
            set_cooldown(token, direction='LONG', hours=EMA300_DIP_COOLDOWN / 60)  # Convert candles to hours
            print(f'  LONG  {token:8s} conf={sig["confidence"]:.0f}% '
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
                   if k in ('ARB', 'CFX', 'FIL', 'AVNT', 'SYRUP') and v.get('price')}
    if not test_tokens:
        test_tokens = dict(list(prices.items())[:10])
    print(f"[ema300_dip] Testing on {len(test_tokens)} tokens...")
    n = scan_signals(test_tokens)
    print(f"[ema300_dip] Done. {n} signals emitted.")
