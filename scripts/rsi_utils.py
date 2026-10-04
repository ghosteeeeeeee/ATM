#!/usr/bin/env python3
"""
rsi_utils.py — Authoritative RSI computation for Hermes Trading System.

Consolidates all RSI checks into one function with consistent methodology.
Replaces 6+ scattered RSI implementations with inconsistent candle sources.

Usage:
    from rsi_utils import compute_rsi
    rsi = compute_rsi(token)           # defaults to 1m, 15 candles
    rsi = compute_rsi(token, tf='5m')  # 5m candles
    rsi = compute_rsi(token, period=14, limit=20)  # custom params

Returns:
    float: RSI value (0-100)
    None: Insufficient data or error (caller should fail-closed for SHORT)

Method:
    Uses Wilder's RSI (same as industry standard) on closed candles only.
    Consistent across all callers — no more 1m vs 5m drift bugs.
"""

import sqlite3
from typing import Optional
from paths import CANDLES_DB

# Cache: {(token, tf, period): (rsi_value, timestamp)}
_rsi_cache = {}
_CACHE_TTL = 30  # seconds — RSI doesn't change fast enough to need faster


def compute_rsi(token: str, tf: str = '1m', period: int = 14, limit: int = 20) -> Optional[float]:
    """
    Compute RSI using Wilder's smoothing method.
    
    Args:
        token: Token symbol (e.g., 'BTC')
        tf: Timeframe — '1m', '5m', '15m', '1h' (default '1m')
        period: RSI period (default 14)
        limit: Number of candles to fetch (default 20, need period+1 minimum)
    
    Returns:
        RSI value (0-100) or None if insufficient data
    """
    import time
    
    # Check cache first
    cache_key = (token.upper(), tf, period)
    if cache_key in _rsi_cache:
        cached_rsi, cached_ts = _rsi_cache[cache_key]
        if time.time() - cached_ts < _CACHE_TTL:
            return cached_rsi
    
    conn = None
    try:
        conn = sqlite3.connect(f'file:{CANDLES_DB}?mode=ro', uri=True, timeout=5)
        cur = conn.cursor()
        cur.execute(
            f"SELECT close FROM candles_{tf} WHERE token = ? AND is_closed = 1 "
            f"ORDER BY ts DESC LIMIT ?",
            (token.upper(), limit)
        )
        closes = [row[0] for row in cur.fetchall()]
        
        if len(closes) < period + 1:
            return None  # Insufficient data
        
        # Calculate gains and losses
        deltas = [closes[i] - closes[i-1] for i in range(1, len(closes))]
        gains = [max(d, 0) for d in deltas]
        losses = [max(-d, 0) for d in deltas]
        
        # Wilder's smoothing (exponential moving average)
        avg_gain = sum(gains[:period]) / period
        avg_loss = sum(losses[:period]) / period
        
        for i in range(period, len(gains)):
            avg_gain = (avg_gain * (period - 1) + gains[i]) / period
            avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        
        if avg_loss == 0:
            rsi = 100.0
        else:
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))
        
        # Cache the result
        _rsi_cache[cache_key] = (rsi, time.time())
        return rsi
        
    except Exception:
        return None  # Fail-closed on error
    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass


def compute_rsi_1m(token: str, period: int = 14) -> Optional[float]:
    """Compute RSI from 1m candles (backwards-compatible wrapper)."""
    return compute_rsi(token, tf='1m', period=period)


def compute_rsi_5m(token: str, period: int = 14) -> Optional[float]:
    """Compute RSI from 5m candles (backwards-compatible wrapper)."""
    return compute_rsi(token, tf='5m', period=period)


def is_oversold(rsi: Optional[float], threshold: float = 30.0) -> bool:
    """Check if RSI indicates oversold conditions."""
    return rsi is not None and rsi < threshold


def is_overbought(rsi: Optional[float], threshold: float = 70.0) -> bool:
    """Check if RSI indicates overbought conditions."""
    return rsi is not None and rsi > threshold


# ── Self-test ──────────────────────────────────────────────────────────────
if __name__ == '__main__':
    import sys
    sys.path.insert(0, '/root/.hermes/scripts')
    
    test_tokens = ['BTC', 'ETH', 'SOL', 'DOGE']
    print("=== RSI UTILS SELF-TEST ===")
    for token in test_tokens:
        rsi_1m = compute_rsi_1m(token)
        rsi_5m = compute_rsi_5m(token)
        print(f"{token:6s} 1m={rsi_1m if rsi_1m else 'N/A':>6}  5m={rsi_5m if rsi_5m else 'N/A':>6}")
