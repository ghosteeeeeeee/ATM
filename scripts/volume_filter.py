#!/usr/bin/env python3
"""
volume_filter.py — Directional volume corroboration for Hermes signals.

Architecture:
  Binance 1m klines (free, unlimited) → split into buy_vol / sell_vol per candle
  → compare recent directional volume vs lookback average → return confidence delta.

Key insight: raw volume surge is ambiguous. Directional volume confirms that momentum
has fuel in the right direction (buy-vol for LONG, sell-vol for SHORT) and rejects
distribution traps (price up + heavy sell-vol = trap for longs).

Usage:
  from volume_filter import get_directional_vol
  result = get_directional_vol('BTC', 'LONG', lookback=20)
  # result['delta'] = +15, +10, 0, -5, or -15  → add to signal confidence
"""

import requests
import sys
import os

# ── Constants ──────────────────────────────────────────────────────────────────

BINANCE_1M_URL = "https://api.binance.com/api/v3/klines"
BINANCE_1H_URL = "https://api.binance.com/api/v3/klines"

# Thresholds (can be overridden per-call)
DEFAULT_LOOKBACK          = 20    # candles to compare against
DEFAULT_STRONG_THRESHOLD = 2.0   # 2x avg = strong surge
DEFAULT_MODERATE_THRESHOLD= 1.5  # 1.5x avg = moderate surge
DEFAULT_WEAK_THRESHOLD   = 0.5   # < 0.5x avg = weak / dry
DEFAULT_CONTRARIAN_THRESHOLD = 2.0  # 2x opposite-direction = distribution trap

# Confidence deltas
DELTA_STRONG     = +15   # directional surge confirmed
DELTA_MODERATE   = +10   # moderate confirmation
DELTA_NEUTRAL    =   0   # nothing notable
DELTA_WEAK       =  -5   # quiet — less conviction
DELTA_CONTRARIAN = -15  # wrong-direction volume — distribution trap

# Cache: token → (timestamp, result) — 30s TTL to avoid hammering Binance
_CACHE: dict = {}
_CACHE_TTL   = 30


# ── Core function ─────────────────────────────────────────────────────────────

def get_directional_vol(
    token: str,
    direction: str,
    lookback: int = DEFAULT_LOOKBACK,
    strong_threshold: float = DEFAULT_STRONG_THRESHOLD,
    moderate_threshold: float = DEFAULT_MODERATE_THRESHOLD,
    weak_threshold: float = DEFAULT_WEAK_THRESHOLD,
    contrarian_threshold: float = DEFAULT_CONTRARIAN_THRESHOLD,
    use_1h: bool = False,
) -> dict:
    """
    Fetch candles and return directional volume analysis.

    Args:
        token:          Trading symbol (e.g. 'BTC', 'ETH') — no USDT suffix
        direction:      'LONG' or 'SHORT'
        lookback:       Number of historical candles to average (excludes current)
        strong_threshold:  Multiplier for strong confirmation (default 2.0x)
        moderate_threshold: Multiplier for moderate confirmation (default 1.5x)
        weak_threshold:    Multiplier below which is considered weak (default 0.5)
        contrarian_threshold: Multiplier for opposite-direction volume (default 2.0)
        use_1h:         If True, use 1h candles instead of 1m (less noise)

    Returns:
        dict with keys:
            buy_ratio, sell_ratio  — current / avg for each side
            confirm               — 'strong' | 'moderate' | 'neutral' | 'weak' | 'contrarian'
            delta                 — confidence adjustment: +15, +10, 0, -5, or -15
            buy_vol,  sell_vol    — current candle directional volumes
            avg_buy_vol, avg_sell_vol — lookback averages
            token, direction, lookback, timeframe — echo back
            error                 — str or None
    """
    direction = direction.upper()
    if direction not in ('LONG', 'SHORT'):
        return {'error': f"direction must be 'LONG' or 'SHORT', got '{direction}'"}

    timeframe = '1h' if use_1h else '1m'
    limit     = lookback + 1   # +1 because we need history + current

    # ── Cache check ──────────────────────────────────────────────────────────
    cache_key = (token, direction, timeframe, lookback)
    if cache_key in _CACHE:
        cached_ts, cached_result = _CACHE[cache_key]
        import time as _time
        if _time.time() - cached_ts < _CACHE_TTL:
            return cached_result

    # ── Fetch candles ─────────────────────────────────────────────────────────
    interval = '1h' if use_1h else '1m'
    url = f"{BINANCE_1M_URL}?symbol={token}USDT&interval={interval}&limit={limit}"
    try:
        resp = requests.get(url, timeout=5)
        if resp.status_code == 429:
            # Rate limited — return neutral rather than erroring out
            result = _neutral_result(token, direction, lookback, timeframe, "rate_limited")
            _CACHE[cache_key] = (0, result)  # TTL=0 forces re-fetch next call
            return result
        resp.raise_for_status()
        candles = resp.json()
    except Exception as e:
        return {
            'error': str(e),
            'buy_ratio': 0, 'sell_ratio': 0,
            'confirm': 'neutral', 'delta': 0,
            'buy_vol': 0, 'sell_vol': 0,
            'avg_buy_vol': 0, 'avg_sell_vol': 0,
            'token': token, 'direction': direction,
            'lookback': lookback, 'timeframe': timeframe,
        }

    if not candles or len(candles) < 2:
        return _neutral_result(token, direction, lookback, timeframe, "no_candle_data")

    # ── Parse candles ─────────────────────────────────────────────────────────
    # Binance format: [open_time, open, high, low, close, volume, ...]
    current = candles[-1]
    history  = candles[:-1]

    def _split_vols(candles_list):
        """Return (buy_vols list, sell_vols list) for given candles."""
        buy_vols, sell_vols = [], []
        for c in candles_list:
            try:
                vol   = float(c[5])
                open_ = float(c[1])
                close = float(c[4])
                body  = close - open_
                if body > 0:
                    buy_vols.append(vol)
                elif body < 0:
                    sell_vols.append(vol)
                # body == 0 → doji → skip (indecision)
            except (ValueError, IndexError):
                continue
        return buy_vols, sell_vols

    curr_buys, curr_sells = _split_vols([current])
    curr_buy_vol  = curr_buys[0]  if curr_buys  else 0.0
    curr_sell_vol = curr_sells[0] if curr_sells else 0.0

    all_buys, all_sells = _split_vols(history)
    avg_buy_vol  = sum(all_buys)  / len(all_buys)  if all_buys  else 1.0
    avg_sell_vol = sum(all_sells) / len(all_sells) if all_sells else 1.0

    # Avoid div-by-zero
    avg_buy_vol  = avg_buy_vol  or 1.0
    avg_sell_vol = avg_sell_vol or 1.0

    buy_ratio   = curr_buy_vol  / avg_buy_vol
    sell_ratio  = curr_sell_vol / avg_sell_vol

    # ── Directional scoring ───────────────────────────────────────────────────
    if direction == 'LONG':
        ratio    = buy_ratio
        opp_ratio = sell_ratio
        if buy_ratio >= strong_threshold and sell_ratio < weak_threshold:
            confirm, delta = 'strong',     DELTA_STRONG
        elif buy_ratio >= moderate_threshold:
            confirm, delta = 'moderate',   DELTA_MODERATE
        elif buy_ratio < weak_threshold:
            confirm, delta = 'weak',       DELTA_WEAK
        elif sell_ratio >= contrarian_threshold:
            confirm, delta = 'contrarian', DELTA_CONTRARIAN   # distribution trap
        else:
            confirm, delta = 'neutral',    DELTA_NEUTRAL

    else:  # SHORT
        ratio    = sell_ratio
        opp_ratio = buy_ratio
        if sell_ratio >= strong_threshold and buy_ratio < weak_threshold:
            confirm, delta = 'strong',     DELTA_STRONG
        elif sell_ratio >= moderate_threshold:
            confirm, delta = 'moderate',   DELTA_MODERATE
        elif sell_ratio < weak_threshold:
            confirm, delta = 'weak',        DELTA_WEAK
        elif buy_ratio >= contrarian_threshold:
            confirm, delta = 'contrarian', DELTA_CONTRARIAN   # short squeeze building
        else:
            confirm, delta = 'neutral',     DELTA_NEUTRAL

    result = {
        # Raw values
        'buy_vol':       round(curr_buy_vol,  4),
        'sell_vol':      round(curr_sell_vol, 4),
        'avg_buy_vol':   round(avg_buy_vol,   4),
        'avg_sell_vol':  round(avg_sell_vol,  4),
        # Ratios
        'buy_ratio':     round(buy_ratio,  2),
        'sell_ratio':    round(sell_ratio, 2),
        # Interpretation
        'confirm':       confirm,
        'delta':         delta,   # ← the key number to add to confidence
        # Metadata
        'token':         token,
        'direction':     direction,
        'lookback':      lookback,
        'timeframe':     timeframe,
        'error':         None,
    }

    # ── Cache ────────────────────────────────────────────────────────────────
    import time as _time
    _CACHE[cache_key] = (_time.time(), result)

    return result


def _neutral_result(token, direction, lookback, timeframe, reason: str) -> dict:
    """Return a neutral result when we can't get data."""
    return {
        'buy_vol': 0, 'sell_vol': 0,
        'avg_buy_vol': 0, 'avg_sell_vol': 0,
        'buy_ratio': 0, 'sell_ratio': 0,
        'confirm': 'neutral', 'delta': 0,
        'token': token, 'direction': direction,
        'lookback': lookback, 'timeframe': timeframe,
        'error': f'no_data: {reason}',
    }


def apply_to_confidence(token: str, direction: str, base_confidence: int) -> tuple:
    """
    Convenience wrapper: fetch directional volume and return (adjusted_confidence, result).

    Usage:
        conf, vol = apply_to_confidence('BTC', 'LONG', base_confidence=60)
            → conf = 75 (if strong), vol = {...}
    """
    vol = get_directional_vol(token, direction)
    delta  = vol.get('delta', 0)
    # Don't let volume push confidence below 1 or above 100
    adjusted = max(1, min(100, base_confidence + delta))
    return adjusted, vol


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    import json, argparse

    parser = argparse.ArgumentParser(description='Directional volume check')
    parser.add_argument('token', nargs='?', default='BTC')
    parser.add_argument('direction', nargs='?', default='LONG')
    parser.add_argument('--lookback', type=int, default=20)
    parser.add_argument('--1h', dest='use_1h', action='store_true', help='Use 1h candles instead of 1m')
    args = parser.parse_args()

    result = get_directional_vol(
        token=args.token,
        direction=args.direction,
        lookback=args.lookback,
        use_1h=args.use_1h,
    )

    print(f"\n{'='*50}")
    print(f"  {args.token}  {args.direction}")
    print(f"  Timeframe: {'1h' if args.use_1h else '1m'}  Lookback: {args.lookback}")
    print(f"{'='*50}")
    print(f"  Current : buy_vol={result['buy_vol']}  sell_vol={result['sell_vol']}")
    print(f"  Average : buy_vol={result['avg_buy_vol']}  sell_vol={result['avg_sell_vol']}")
    print(f"  Ratios  : buy_ratio={result['buy_ratio']}x  sell_ratio={result['sell_ratio']}x")
    print(f"  Confirm : {result['confirm'].upper()}")
    print(f"  Delta   : {result['delta']:+d}")
    if result.get('error'):
        print(f"  Error   : {result['error']}")
    print()
