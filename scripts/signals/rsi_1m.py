#!/usr/bin/env python3
"""
rsi_1m.py — Compute 1m RSI for signal metadata.

The execution filter (decider_run.py) uses 1m RSI for drift detection.
Signal generators often use 5m/15m/1h candles for detection logic, which
can give different RSI values. This module provides a consistent 1m RSI
computation that signals can store in their metadata.

Usage:
    from signals.rsi_1m import compute_rsi_1m
    rsi_1m = compute_rsi_1m(token)
"""

import sqlite3
from typing import Optional

CANDLES_DB = '/root/.hermes/data/candles.db'


def compute_rsi_1m(token: str, period: int = 14) -> Optional[float]:
    """
    Compute RSI from 1m candles for a token.
    Returns RSI value or None if insufficient data.
    """
    conn = None
    try:
        conn = sqlite3.connect(f'file:{CANDLES_DB}?mode=ro', uri=True, timeout=5)
        cur = conn.cursor()
        cur.execute(
            "SELECT close FROM candles_1m WHERE token=? AND is_closed=1 "
            "ORDER BY ts DESC LIMIT ?",
            (token.upper(), period + 1)
        )
        closes = [r[0] for r in cur.fetchall()]
        if len(closes) < period + 1:
            return None
        
        # DESC order → reverse for correct delta direction
        closes.reverse()
        
        deltas = [closes[i] - closes[i-1] for i in range(1, len(closes))]
        gains = [d if d > 0 else 0 for d in deltas[-period:]]
        losses = [-d if d < 0 else 0 for d in deltas[-period:]]
        avg_gain = sum(gains) / period
        avg_loss = sum(losses) / period
        if avg_loss == 0:
            return 100.0
        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))
    except Exception:
        return None
    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass
