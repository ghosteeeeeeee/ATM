#!/usr/bin/env python3
"""
return_exhaustion.py — Percentile Exhaustion + Momentum Divergence Signal

Catches turning points by detecting when short-term returns are at a
percentile extreme relative to recent history, combined with momentum
divergence between fast and slow timeframes.

Key insight: In crypto, extreme short-term returns (>p90 or <p10 percentile)
are followed by reversals more often than continuations. The momentum
divergence filter confirms the exhaustion by showing that fast momentum
is already turning while slow momentum hasn't caught up.

Signal logic:
  LONG:  short-term return < p10 (extreme negative) AND
         fast momentum > slow momentum (turning up)
  SHORT: short-term return > p90 (extreme positive) AND
         fast momentum < slow momentum (turning down)

Architecture:
  1m price history from signals_hermes.db
  → percentile rank of returns
  → fast/slow momentum divergence
  → RSI confirmation
  → signal_schema.add_signal()

Run: scan_return_exhaustion_signals(prices_dict) — compatible with signals/__init__.py
"""

import math
import os
import sys
import time
import sqlite3
from typing import Optional, Dict, List

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from hermes_constants import (
    SHORT_BLACKLIST,
    LONG_BLACKLIST,
    RETURN_EXHAUSTION_MIN_CONFIDENCE,
)

# ── Constants ─────────────────────────────────────────────────────────────────

# Return periods for percentile analysis
RETURN_SHORT = 14       # 14-minute return (short-term exhaustion)
RETURN_MID = 30         # 30-minute return (medium-term context)
RETURN_LONG = 60        # 60-minute return (trend direction)

# Percentile lookback window (how many historical returns to rank against)
PERCENTILE_LOOKBACK = 20  # reduced from 200 — need enough data for percentile ranking

# Percentile thresholds for exhaustion
PCT_EXHAUST_LOW = 10    # below p10 = extreme negative → LONG exhaustion
PCT_EXHAUST_HIGH = 90   # above p90 = extreme positive → SHORT exhaustion

# Momentum divergence periods
MOM_FAST = 5            # fast momentum (5-bar return)
MOM_SLOW = 30           # slow momentum (30-bar return)

# Minimum data requirements
MIN_BARS = 220          # PERCENTILE_LOOKBACK + buffer

# RSI filter
RSI_PERIOD = 14
RSI_OVERSOLD = 30
RSI_OVERBOUGHT = 70

# Cooldown between signals per token+direction (minutes)
COOLDOWN_MINUTES = 15

# Confidence scoring
CONF_BASE = 60
CONF_PCT_EXTREME_MAX = 15   # more extreme percentile = higher conf
CONF_DIVERGENCE_BONUS = 10  # strong divergence bonus
CONF_RSI_BONUS = 5          # RSI confirmation bonus
CONF_MAX = 95

SIGNAL_TYPE = 'return_exhaustion'


# ── Price History ─────────────────────────────────────────────────────────────

def _get_price_history(token: str) -> list:
    """Fetch 1m close prices from signals_hermes.db. Oldest first."""
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
        conn.close()
        if not rows:
            return []
        # Reverse to oldest-first
        return [r[0] for r in reversed(rows)]
    except Exception:
        return []


# ── Indicator Calculations ───────────────────────────────────────────────────

def _compute_returns(prices: list, period: int) -> list:
    """Compute period-over-period returns. Returns list of (index, return_pct)."""
    if len(prices) < period + 1:
        return []
    returns = []
    for i in range(period, len(prices)):
        ret = (prices[i] - prices[i - period]) / (prices[i - period] + 1e-10) * 100
        returns.append(ret)
    return returns


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


def _get_speed(token: str) -> float:
    """Get speed percentile for token."""
    try:
        from speed_tracker import get_token_speed
        spd = get_token_speed(token)
        return spd.get('speed_percentile', 50) if spd else 50.0
    except Exception:
        return 50.0


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
            WHERE signal_type = 'return_exhaustion'
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

def detect_return_exhaustion(token: str, prices: list) -> Optional[Dict]:
    """Detect percentile exhaustion with momentum divergence.

    Args:
        token: token symbol
        prices: list of 1m close prices (oldest first)

    Returns signal dict if triggered, else None.
    """
    if len(prices) < MIN_BARS:
        return None

    price = prices[-1]

    # ── Speed check: need some market activity ────────────────────────────
    speed = _get_speed(token)
    if speed < 30:
        return None  # too slow

    # ── Compute returns at multiple periods ────────────────────────────────
    short_ret = (prices[-1] - prices[-1 - RETURN_SHORT]) / (prices[-1 - RETURN_SHORT] + 1e-10) * 100
    mid_ret = (prices[-1] - prices[-1 - RETURN_MID]) / (prices[-1 - RETURN_MID] + 1e-10) * 100
    long_ret = (prices[-1] - prices[-1 - RETURN_LONG]) / (prices[-1 - RETURN_LONG] + 1e-10) * 100

    # ── Percentile rank the short-term return ──────────────────────────────
    # Build rolling distribution of historical short-term returns
    hist_short_returns = []
    for i in range(RETURN_SHORT + PERCENTILE_LOOKBACK, len(prices)):
        ret = (prices[i] - prices[i - RETURN_SHORT]) / (prices[i - RETURN_SHORT] + 1e-10) * 100
        hist_short_returns.append(ret)

    if len(hist_short_returns) < 30:
        return None  # not enough history

    pct_rank = _percentile_rank(short_ret, hist_short_returns)
    if pct_rank is None:
        return None

    # ── Exhaustion detection ───────────────────────────────────────────────
    is_long_exhaustion = pct_rank <= PCT_EXHAUST_LOW   # extreme negative
    is_short_exhaustion = pct_rank >= PCT_EXHAUST_HIGH  # extreme positive

    if not is_long_exhaustion and not is_short_exhaustion:
        return None

    # ── Momentum divergence filter ─────────────────────────────────────────
    # Fast momentum (5-bar) vs Slow momentum (30-bar)
    fast_mom = (prices[-1] - prices[-1 - MOM_FAST]) / (prices[-1 - MOM_FAST] + 1e-10) * 100
    slow_mom = (prices[-1] - prices[-1 - MOM_SLOW]) / (prices[-1 - MOM_SLOW] + 1e-10) * 100

    # Divergence magnitude
    div = abs(fast_mom - slow_mom)

    if is_long_exhaustion:
        # LONG: price fell hard (short return extreme negative)
        # Divergence: fast_mom > slow_mom means fast is recovering faster
        # (fast_mom is less negative or turning positive while slow_mom is still negative)
        if fast_mom < slow_mom:
            return None  # no divergence — fast still weaker than slow
        direction = 'LONG'
    else:
        # SHORT: price rose hard (short return extreme positive)
        # Divergence: fast_mom < slow_mom means fast is weakening
        if fast_mom > slow_mom:
            return None  # no divergence — fast still stronger than slow
        direction = 'SHORT'

    # ── RSI confirmation ───────────────────────────────────────────────────
    rsi = _rsi(prices)
    rsi_bonus = 0
    if rsi is not None:
        if direction == 'LONG' and rsi < RSI_OVERSOLD:
            rsi_bonus = CONF_RSI_BONUS
        elif direction == 'SHORT' and rsi > RSI_OVERBOUGHT:
            rsi_bonus = CONF_RSI_BONUS
        # Block if RSI contradicts
        if direction == 'LONG' and rsi > 70:
            return None
        if direction == 'SHORT' and rsi < 30:
            return None

    # ── Z-score filter — block extreme counter-trend ───────────────────────
    import statistics as _stat
    recent = prices[-20:] if len(prices) >= 20 else prices
    if len(recent) >= 10:
        _mean = _stat.mean(recent)
        _stdev = _stat.stdev(recent) if len(recent) > 1 else 1
        _z = (recent[-1] - _mean) / _stdev if _stdev > 0 else 0
        if direction == 'LONG' and _z < -2.5:
            return None  # too extreme — catching falling knife
        if direction == 'SHORT' and _z > 2.5:
            return None  # too extreme — fading strong momentum
    else:
        _z = 0

    # ── Regime filter ──────────────────────────────────────────────────────
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
                return None
            if _token_reg == 'SHORT_BIAS' and direction == 'LONG':
                return None
            if _token_reg == 'NEUTRAL':
                regime_penalty = 10
    except Exception:
        pass

    # ── Confidence scoring ─────────────────────────────────────────────────
    conf = CONF_BASE

    # Percentile extremity bonus: more extreme = higher confidence
    if is_long_exhaustion:
        extremity = PCT_EXHAUST_LOW - pct_rank  # 0-10
        conf += min(CONF_PCT_EXTREME_MAX, int(extremity * 1.5))
    else:
        extremity = pct_rank - PCT_EXHAUST_HIGH  # 0-10
        conf += min(CONF_PCT_EXTREME_MAX, int(extremity * 1.5))

    # Divergence bonus
    if div > 1.0:
        conf += CONF_DIVERGENCE_BONUS
    elif div > 0.5:
        conf += int(CONF_DIVERGENCE_BONUS * 0.6)

    # RSI confirmation
    conf += rsi_bonus

    # Speed bonus
    if speed > 70:
        conf += 3

    # Apply regime penalty
    if regime_penalty:
        conf = max(50, conf - regime_penalty)

    conf = min(CONF_MAX, conf)

    # Paper observation gate — only exceptional setups fire
    if conf < RETURN_EXHAUSTION_MIN_CONFIDENCE:
        return None

    # ── Build signal ───────────────────────────────────────────────────────
    signal_type = f'return_exhaustion_{direction.lower()}'
    source = f'return_exhaustion_{direction.lower()}' if direction == 'LONG' else 'return_exhaustion-'

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
        'direction': direction,
        'signal_type': signal_type,
        'source': source,
        'confidence': conf,
        'value': value,
        'price': price,
        '_z': _z,
        '_pct_rank': pct_rank,
        '_divergence': div,
    }


# ── Scanner ───────────────────────────────────────────────────────────────────

def scan_return_exhaustion_signals(prices_dict: dict) -> tuple:
    """Scan tokens for return_exhaustion signals.

    Args:
        prices_dict: token -> {'price': float, ...}

    Returns:
        (count of signals written, list of token names that fired)
    """
    from signal_schema import add_signal, price_age_minutes, get_price_history

    _load_cooldowns()
    added = 0
    signaled_tokens = []
    now = time.time()

    from hyperliquid_exchange import _HL_BLOCKLIST

    for token, data in prices_dict.items():
        price = data.get('price')
        if not price or price <= 0:
            continue

        if token.upper() in _HL_BLOCKLIST:
            continue

        if token in SHORT_BLACKLIST or token in LONG_BLACKLIST:
            continue

        # Cooldown check
        last_fire = _cooldown_cache.get(token.upper(), 0)
        if now - last_fire < COOLDOWN_MINUTES * 60:
            continue

        # Staleness check
        if price_age_minutes(token) > 10:
            continue

        # Fetch price history
        rows = get_price_history(token, lookback_minutes=MIN_BARS + 20)
        if not rows or len(rows) < MIN_BARS:
            continue

        prices = [r[1] for r in reversed(rows)]  # oldest first

        # Per-direction kill-switch
        from hermes_constants import (
            RETURN_EXHAUSTION_PLUS_ENABLED,
            RETURN_EXHAUSTION_MINUS_ENABLED,
        )

        sig = detect_return_exhaustion(token, prices)
        if sig is None:
            continue

        if sig['direction'] == 'LONG' and not RETURN_EXHAUSTION_PLUS_ENABLED:
            continue
        if sig['direction'] == 'SHORT' and not RETURN_EXHAUSTION_MINUS_ENABLED:
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
            timeframe='1m',
            z_score=sig.get('_z'),
            z_score_tier=None,
        )

        if sid:
            added += 1
            signaled_tokens.append(token)
            _cooldown_cache[token.upper()] = now
            print(f"[return_exhaustion] {sig['direction']} {sig['token']} "
                  f"conf={sig['confidence']} pct_rank={sig['_pct_rank']:.1f} "
                  f"div={sig['_divergence']:.4f}")

    return added, signaled_tokens


def run(prices_dict: dict = None) -> int:
    """Entry point for signals/__init__.py registry. Returns count of signals emitted."""
    from signal_schema import get_all_latest_prices, price_age_minutes, get_price_history

    all_prices = get_all_latest_prices()
    if not all_prices:
        return 0

    added, _ = scan_return_exhaustion_signals(all_prices)
    return added


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='return_exhaustion signal scanner')
    parser.add_argument('--dry', action='store_true', help='Dry run')
    args = parser.parse_args()

    from signal_schema import get_all_latest_prices
    prices = get_all_latest_prices()
    added, tokens = scan_return_exhaustion_signals(prices)
    print(f"[return_exhaustion] {'Dry ' if args.dry else ''}run: {added} signals on {tokens}")
