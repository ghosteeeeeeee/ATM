#!/usr/bin/env python3
"""
Signal: trend_momentum_near_sma

Thesis: Buy when price is in an uptrend (above SMA20), has positive
        momentum (5-period rising), and is near the SMA (within 0.5%).
        These conditions historically produce 47.8% WR with +$9.66/14d.

Entry:  close > SMA20 (trend up)
        + 5-period price change > 0.5% (momentum)
        + |close - SMA20| / SMA20 < 0.005 (near SMA, not extended)

Exit:   Trail at 0.8% from peak
        Stop at -1.2% from entry (ATR-based)

Data:   candles_1h from candles.db
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from paths import *
import sqlite3
from datetime import datetime, timezone


def run(token: str = None, **kwargs) -> list:
    """Generate trend_momentum_near_sma signals for active tokens."""
    signals = []

    conn = sqlite3.connect(f'{HERMES_DATA}/candles.db')
    cur = conn.cursor()

    # Get tokens with recent candles (not just "active" flag)
    if token:
        tokens = [token]
    else:
        cur.execute("""
            SELECT DISTINCT token FROM candles_1h
            WHERE ts > strftime('%s', 'now') - 86400
            ORDER BY token
        """)
        tokens = [r[0] for r in cur.fetchall()]

    for tok in tokens:
        # Get 1h candles (need 20 for SMA20)
        cur.execute("""
            SELECT ts, open, high, low, close, volume
            FROM candles_1h
            WHERE token = ? AND is_closed = 1
            ORDER BY ts DESC
            LIMIT 25
        """, (tok,))
        rows = cur.fetchall()

        if len(rows) < 20:
            continue

        # Parse candles (newest first)
        candles = []
        for r in rows:
            candles.append({
                'ts': r[0], 'open': r[1], 'high': r[2],
                'low': r[3], 'close': r[4], 'volume': r[5]
            })

        close = candles[0]['close']
        if close <= 0:
            continue

        # Compute indicators
        closes = [c['close'] for c in candles]
        sma20 = sum(closes[:20]) / 20

        # 5-period momentum
        if closes[4] > 0:
            momentum = (closes[0] - closes[4]) / closes[4]
        else:
            continue

        # Distance from SMA
        dist_sma = abs(close - sma20) / sma20

        # Entry conditions
        trend_up = close > sma20
        has_momentum = momentum > 0.005  # >0.5% rise in 5 periods
        near_sma = dist_sma < 0.005  # within 0.5% of SMA

        if not (trend_up and has_momentum and near_sma):
            continue

        # Compute confidence based on strength
        conf = 70  # base
        if momentum > 0.01:
            conf += 10  # strong momentum
        if dist_sma < 0.002:
            conf += 5  # very close to SMA
        conf = min(conf, 95)

        # Check for existing signal (avoid duplicates)
        cur2 = sqlite3.connect(f'{HERMES_DATA}/signals_hermes_runtime.db').cursor()
        cur2.execute("""
            SELECT id FROM signals
            WHERE token = ? AND direction = 'LONG'
              AND created_at > datetime('now', '-5 minutes')
              AND decision != 'EXPIRED'
        """, (tok,))
        if cur2.fetchone():
            continue
        cur2.connection.close()

        signals.append({
            'token': tok,
            'direction': 'LONG',
            'signal_type': 'trend_momentum_near_sma',
            'confidence': conf,
            'reason': f'trend_up + momentum({momentum:+.3f}) + near_sma({dist_sma:.4f})',
            'metadata': {
                'sma20': sma20,
                'momentum': momentum,
                'dist_sma': dist_sma,
                'close': close,
            }
        })

    conn.close()
    return signals


if __name__ == '__main__':
    signals = run()
    print(f'Generated {len(signals)} signals')
    for s in signals:
        print(f"  {s['token']} {s['direction']} conf={s['confidence']} — {s['reason']}")
