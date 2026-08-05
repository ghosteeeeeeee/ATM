#!/usr/bin/env python3
"""
vortex_break.py — Vortex Indicator + ADX Trend Confirmation Signal

Uses the Vortex Indicator (VI), which measures directional movement using
TRUE RANGE (high-low) instead of just price closes. This makes it
fundamentally different from EMA/RSI/MACD/Z-score signals.

Signal logic:
  LONG:  VI+ crosses above VI- AND ADX > 20 AND price above EMA20
  SHORT: VI- crosses above VI+ AND ADX > 20 AND price below EMA20

The Vortex Indicator captures trend inception by measuring how far the
current high/low extends beyond the previous close — a structural property
of price movement, not a derived indicator.

Architecture:
  5m OHLCV candles from candles.db
  → Vortex Indicator computation (14-period)
  → ADX trend strength confirmation (14-period)
  → EMA20 alignment filter
  → signal_schema.add_signal()
  → signals_hermes_runtime.db → signal_compactor → hotset.json → guardian

Run: scan_vortex_break_signals(prices_dict) — compatible with signals/__init__.py registry
"""

import os
import sys
import time
import sqlite3
from typing import Optional, Dict, List, Tuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from hyperliquid_exchange import _HL_BLOCKLIST
from hermes_constants import VORTEX_BREAK_MIN_CONFIDENCE

# ── Constants ─────────────────────────────────────────────────────────────────

# Vortex Indicator period (14 is standard)
VORTEX_PERIOD = 14

# ADX period (14 is standard)
ADX_PERIOD = 14

# ADX threshold — only trade when trend is confirmed
ADX_MIN = 20

# Minimum lookback candles (need VORTEX_PERIOD + ADX warmup + EMA warmup)
MIN_LOOKBACK = 100

# Cooldown between signals per token+direction (hours)
COOLDOWN_HOURS = 3

# Confidence scoring
CONF_BASE = 65
CONF_ADX_BONUS_MAX = 15   # ADX > 25 → +15
CONF_VI_STRENGTH_MAX = 10 # VI spread strength bonus
CONF_EMA_BONUS = 5        # EMA alignment bonus
CONF_MAX = 95

# EMA periods for alignment
EMA_FAST = 20
EMA_SLOW = 50

SIGNAL_TYPE = 'vortex_break'
PRICE_DB = '/root/.hermes/data/candles.db'


# ── Candle Fetching ───────────────────────────────────────────────────────────

def _get_candles_5m(token: str, lookback: int = MIN_LOOKBACK + 50) -> list:
    """Fetch 5m OHLCV candles from candles.db, oldest first.
    Returns [] if candles are stale (>10 min old)."""
    try:
        conn = sqlite3.connect(PRICE_DB, timeout=10)
        c = conn.cursor()
        c.execute("""
            SELECT ts, open, high, low, close, volume
            FROM candles_5m
            WHERE token = ?
            ORDER BY ts DESC
            LIMIT ?
        """, (token.upper(), lookback))
        rows = c.fetchall()
        conn.close()

        if not rows:
            return []

        most_recent_ts = rows[0][0]
        rows = list(reversed(rows))

        # Staleness guard: 5m candles should be < 10 min old
        if (time.time() - most_recent_ts) > 600:
            return []

        return [
            {'open_time': r[0], 'open': r[1], 'high': r[2],
             'low': r[3], 'close': r[4], 'volume': r[5]}
            for r in rows
        ]
    except Exception:
        return []


# ── Indicator Calculations ───────────────────────────────────────────────────

def _true_range(candles: list) -> list:
    """Compute True Range for each candle (oldest first)."""
    tr = [candles[0]['high'] - candles[0]['low']]  # first candle: just H-L
    for i in range(1, len(candles)):
        h = candles[i]['high']
        l = candles[i]['low']
        prev_c = candles[i - 1]['close']
        tr.append(max(h - l, abs(h - prev_c), abs(l - prev_c)))
    return tr


def _vortex_indicator(candles: list, period: int = VORTEX_PERIOD) -> Optional[Tuple[List[float], List[float]]]:
    """Compute Vortex Indicator (VI+, VI-) from OHLCV candles.

    VI+ = sum of |high[i] - low[i-1]| for last N periods / ATR
    VI- = sum of |low[i] - high[i-1]| for last N periods / ATR

    Returns (vi_plus_list, vi_minus_list) or None if insufficient data.
    Each list has len(candles) entries (None for warmup period).
    """
    if len(candles) < period + 1:
        return None

    n = len(candles)
    tr = _true_range(candles)

    # Compute directional movement
    plus_dm = [0.0]  # first candle: no prior candle
    minus_dm = [0.0]
    for i in range(1, n):
        h = candles[i]['high']
        l = candles[i]['low']
        prev_h = candles[i - 1]['high']
        prev_l = candles[i - 1]['low']
        up = h - prev_h
        down = prev_l - l
        plus_dm.append(up if up > down and up > 0 else 0)
        minus_dm.append(down if down > up and down > 0 else 0)

    # Rolling sums for Vortex calculation
    vi_plus = [None] * period
    vi_minus = [None] * period

    # Initial sums
    sum_tr = sum(tr[1:period + 1])
    sum_plus = sum(plus_dm[1:period + 1])
    sum_minus = sum(minus_dm[1:period + 1])

    for i in range(period, n):
        if i > period:
            sum_tr = sum_tr - tr[i - period] + tr[i]
            sum_plus = sum_plus - plus_dm[i - period] + plus_dm[i]
            sum_minus = sum_minus - minus_dm[i - period] + minus_dm[i]

        if sum_tr > 0:
            vi_plus.append(sum_plus / sum_tr)
            vi_minus.append(sum_minus / sum_tr)
        else:
            vi_plus.append(1.0)
            vi_minus.append(1.0)

    return vi_plus, vi_minus


def _adx(candles: list, period: int = ADX_PERIOD) -> Optional[float]:
    """Compute ADX (Average Directional Index) from OHLCV candles.
    Uses Wilder's smoothing. Returns the latest ADX value or None."""
    if len(candles) < period * 2 + 1:
        return None

    n = len(candles)
    highs = [c['high'] for c in candles]
    lows = [c['low'] for c in candles]
    closes = [c['close'] for c in candles]

    # True Range, +DM, -DM
    tr_list = []
    plus_dm = []
    minus_dm = []
    for i in range(1, n):
        tr = max(highs[i] - lows[i],
                 abs(highs[i] - closes[i - 1]),
                 abs(lows[i] - closes[i - 1]))
        tr_list.append(tr)
        up = highs[i] - highs[i - 1]
        down = lows[i - 1] - lows[i]
        plus_dm.append(up if up > down and up > 0 else 0)
        minus_dm.append(down if down > up and down > 0 else 0)

    if len(tr_list) < period * 2:
        return None

    # Wilder's smoothing
    atr_s = sum(tr_list[:period]) / period
    pdm_s = sum(plus_dm[:period]) / period
    mdm_s = sum(minus_dm[:period]) / period

    dx_list = []
    for i in range(period, len(tr_list)):
        atr_s = (atr_s * (period - 1) + tr_list[i]) / period
        pdm_s = (pdm_s * (period - 1) + plus_dm[i]) / period
        mdm_s = (mdm_s * (period - 1) + minus_dm[i]) / period

        pdi = 100 * pdm_s / (atr_s + 1e-10)
        mdi = 100 * mdm_s / (atr_s + 1e-10)
        dx = abs(pdi - mdi) / (pdi + mdi + 1e-10) * 100
        dx_list.append(dx)

    if len(dx_list) < period:
        return None

    adx_val = sum(dx_list[-period:]) / period
    return adx_val


def _ema(closes: list, period: int) -> float:
    """Compute EMA of the last `period` values."""
    if len(closes) < period:
        return sum(closes) / len(closes) if closes else 0
    k = 2 / (period + 1)
    val = sum(closes[:period]) / period
    for v in closes[period:]:
        val = v * k + val * (1 - k)
    return val


# ── Cooldown Cache ────────────────────────────────────────────────────────────

_cooldown_cache: Dict[str, float] = {}  # token -> last_fire_timestamp

def _load_cooldowns():
    """Load cooldowns from runtime DB."""
    if _cooldown_cache:
        return
    try:
        from paths import RUNTIME_DB
        conn = sqlite3.connect(RUNTIME_DB, timeout=5)
        cur = conn.cursor()
        cur.execute("""
            SELECT token, MAX(created_at) FROM signals
            WHERE signal_type = 'vortex_break'
            GROUP BY token
        """)
        for tok, ts in cur.fetchall():
            try:
                import datetime as dt
                ts_str = str(ts)
                dt_obj = dt.datetime.strptime(ts_str, '%Y-%m-%d %H:%M:%S')
                _cooldown_cache[tok] = dt_obj.timestamp()
            except Exception:
                pass
        conn.close()
    except Exception:
        pass


# ── Core Detection ────────────────────────────────────────────────────────────

def detect_vortex_break(token: str, candles: list, price: float) -> Optional[Dict]:
    """Detect Vortex Indicator breakout with ADX confirmation.

    Returns signal dict if triggered, else None.
    """
    if len(candles) < MIN_LOOKBACK:
        return None

    closes = [c['close'] for c in candles]

    # ── Speed check: need some momentum ───────────────────────────────────
    if len(closes) >= 10:
        recent_move = closes[-1] - closes[-5]
        atr_est = max(c['high'] - c['low'] for c in candles[-14:])
        if atr_est > 0 and abs(recent_move) / atr_est < 0.2:
            return None  # no wave

    # ── Phase 1: Vortex Indicator ─────────────────────────────────────────
    vi_result = _vortex_indicator(candles, VORTEX_PERIOD)
    if vi_result is None:
        return None

    vi_plus, vi_minus = vi_result

    # Look for crossover in last 5 candles and check if it passes all phases
    for i in range(-5, 0):
        if vi_plus[i] is None or vi_minus[i] is None:
            continue
        if vi_plus[i-1] is None or vi_minus[i-1] is None:
            continue
        
        long_cross = vi_plus[i-1] <= vi_minus[i-1] and vi_plus[i] > vi_minus[i]
        short_cross = vi_minus[i-1] <= vi_plus[i-1] and vi_minus[i] > vi_plus[i]
        
        if not long_cross and not short_cross:
            continue
        
        direction = 'LONG' if long_cross else 'SHORT'
        
        # Use values at crossover point
        cur_vi_plus = vi_plus[i]
        cur_vi_minus = vi_minus[i]
        vi_spread = abs(cur_vi_plus - cur_vi_minus)
        
        # Price at crossover candle
        crossover_price = closes[len(closes)+i]
        
        # Check ADX at crossover
        adx_val = _adx(candles[:len(candles)+i+1], ADX_PERIOD)
        if adx_val is None or adx_val < ADX_MIN:
            continue
        
        # Check EMA at crossover
        ema_fast = _ema(closes[:len(closes)+i+1], EMA_FAST)
        if direction == 'LONG' and crossover_price < ema_fast:
            continue
        if direction == 'SHORT' and crossover_price > ema_fast:
            continue
        
        # Check Z-score at crossover
        recent_closes = closes[max(0, len(closes)+i-20):len(closes)+i]
        if len(recent_closes) >= 10:
            import statistics as _stat
            _mean = _stat.mean(recent_closes)
            _stdev = _stat.stdev(recent_closes) if len(recent_closes) > 1 else 1
            _z = (crossover_price - _mean) / _stdev if _stdev > 0 else 0
            if direction == 'LONG' and _z < -2.0:
                continue
            if direction == 'SHORT' and _z > 2.0:
                continue
        else:
            _z = 0
        
        # Regime filter — block signals that contradict regime
        regime_penalty = 0
        try:
            import json as _json
            regime_file = '/var/www/hermes/data/regime_5m.json'
            if os.path.exists(regime_file):
                with open(regime_file) as _f:
                    _regime_data = _json.load(_f)
                _token_regime = _regime_data.get('regimes', {}).get(token.upper(), {})
                _token_reg = _token_regime.get('regime', 'NEUTRAL')
                if _token_reg == 'LONG_BIAS' and direction == 'SHORT':
                    continue
                if _token_reg == 'SHORT_BIAS' and direction == 'LONG':
                    continue
                if _token_reg == 'NEUTRAL':
                    pass  # No penalty for neutral regime — only block contradictions
        except Exception:
            pass
        
        # All phases passed — calculate confidence
        conf = CONF_BASE
        if adx_val >= 30: conf += CONF_ADX_BONUS_MAX
        elif adx_val >= 25: conf += int(CONF_ADX_BONUS_MAX * 0.7)
        elif adx_val >= 20: conf += int(CONF_ADX_BONUS_MAX * 0.4)
        
        vi_strength = min(1.0, vi_spread / 0.5)
        conf += int(CONF_VI_STRENGTH_MAX * vi_strength)
        
        ema_slow = _ema(closes[:len(closes)+i+1], EMA_SLOW)
        if direction == 'LONG' and crossover_price > ema_slow:
            conf += CONF_EMA_BONUS
        elif direction == 'SHORT' and crossover_price < ema_slow:
            conf += CONF_EMA_BONUS
        
        # Apply regime penalty
        if regime_penalty:
            conf = max(50, conf - regime_penalty)
        
        conf = min(CONF_MAX, conf)
        
        if conf < VORTEX_BREAK_MIN_CONFIDENCE:
            continue
        
        # Build signal
        signal_type = f'vortex_break_{direction.lower()}'
        source = f'vortex_break_{direction.lower()}'
        
        return {
            'token': token.upper(),
            'direction': direction,
            'signal_type': signal_type,
            'source': source,
            'confidence': conf,
            'value': str({
                'vi_plus': round(cur_vi_plus, 4),
                'vi_minus': round(cur_vi_minus, 4),
                'adx': round(adx_val, 1),
                'ema_fast': round(ema_fast, 4),
            }),
            'price': price,
            '_adx': adx_val,
            '_vi_spread': vi_spread,
            '_z': _z,
        }
    
    return None

def scan_vortex_break_signals(prices_dict: dict) -> tuple:
    """Scan pre-filtered tokens for vortex_break signals.

    Args:
        prices_dict: token -> {'price': float, ...}

    Returns:
        (count of signals written, list of token names that fired)
    """
    from signal_schema import add_signal

    _load_cooldowns()
    added = 0
    signaled_tokens = []
    now = time.time()

    for token, data in prices_dict.items():
        price = data.get('price')
        if not price or price <= 0:
            continue

        if token.upper() in _HL_BLOCKLIST:
            continue

        # Cooldown check
        last_fire = _cooldown_cache.get(token.upper(), 0)
        if now - last_fire < COOLDOWN_HOURS * 3600:
            continue

        # Per-direction kill-switch
        from hermes_constants import (
            VORTEX_BREAK_PLUS_ENABLED,
            VORTEX_BREAK_MINUS_ENABLED,
        )

        candles = _get_candles_5m(token)
        if not candles or len(candles) < MIN_LOOKBACK:
            continue

        sig = detect_vortex_break(token, candles, price)
        if sig is None:
            continue

        if sig['direction'] == 'LONG' and not VORTEX_BREAK_PLUS_ENABLED:
            continue
        if sig['direction'] == 'SHORT' and not VORTEX_BREAK_MINUS_ENABLED:
            continue

        sid = add_signal(
            token=sig['token'],
            direction=sig['direction'],
            signal_type=sig['signal_type'],
            source=sig['source'],
            confidence=sig['confidence'],
            value=sig['value'],
            price=sig['price'],
            exchange='hyperliquid',
            timeframe='5m',
            z_score=sig.get('_z'),
            z_score_tier=None,
        )

        if sid:
            added += 1
            signaled_tokens.append(token)
            _cooldown_cache[token.upper()] = now
            print(f"[vortex_break] {sig['direction']} {sig['token']} "
                  f"conf={sig['confidence']} adx={sig['_adx']:.1f} "
                  f"vi_spread={sig['_vi_spread']:.4f}")

    return added, signaled_tokens


def run(prices_dict: dict = None) -> tuple:
    """Entry point for signals/__init__.py registry."""
    if prices_dict is None:
        from signal_schema import get_all_latest_prices
        prices_dict = get_all_latest_prices()
    return scan_vortex_break_signals(prices_dict)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='vortex_break signal scanner')
    parser.add_argument('--dry', action='store_true', help='Dry run (no DB write)')
    args = parser.parse_args()

    from signal_schema import get_all_latest_prices
    prices = get_all_latest_prices()
    added, tokens = scan_vortex_break_signals(prices)
    print(f"[vortex_break] {'Dry ' if args.dry else ''}run: {added} signals on {tokens}")
