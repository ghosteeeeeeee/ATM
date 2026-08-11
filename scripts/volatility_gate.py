#!/usr/bin/env python3
"""
volatility_gate — Surf the right waves.

Thesis: Don't trade in flat water (no edge) or storms (too risky).
        Trade in the sweet spot: normal volatility with clear waves.

Classification (from 30d ATR distribution across 143 tokens):
  FLAT:    ATR% < 0.48  (P25)  → SKIP (no wave to surf)
  NORMAL:  ATR% 0.48-1.0 (P25-P75) → TRADE with standard SL
  HIGH:    ATR% 1.0-1.5 (P75-P90) → TRADE with wider SL
  EXTREME: ATR% > 1.5 (P90)  → SKIP (storm)

Data: candles_1h from candles.db
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from paths import HERMES_DATA
import sqlite3


def get_atr_pct(token):
    """Get current ATR(14) as percentage of close price for a token."""
    conn = None
    try:
        conn = sqlite3.connect(f'{HERMES_DATA}/candles.db', timeout=10)
        cur = conn.cursor()
        cur.execute("""
            SELECT open, high, low, close
            FROM candles_1h
            WHERE token = ? AND is_closed = 1
            ORDER BY ts DESC
            LIMIT 20
        """, (token.upper(),))
        rows = cur.fetchall()
        if len(rows) < 15:
            return None
    except Exception:
        return None
    finally:
        if conn:
            conn.close()

    # rows are newest-first, reverse for chronological
    candles = list(reversed(rows))

    # Compute true ranges
    trs = []
    for i in range(1, len(candles)):
        h, l, pc = candles[i][1], candles[i][2], candles[i-1][3]
        tr = max(h - l, abs(h - pc), abs(l - pc))
        trs.append(tr)

    if len(trs) < 14:
        return None

    atr14 = sum(trs[-14:]) / 14
    close = candles[-1][3]
    if close <= 0:
        return None

    return (atr14 / close) * 100


def classify_volatility(atr_pct):
    """Classify volatility regime from ATR% (as percentage, e.g. 0.5 = 0.5%)."""
    if atr_pct < 0.48:    # <0.48% — flat
        return 'FLAT'
    elif atr_pct < 1.0:   # 0.48-1.0% — normal
        return 'NORMAL'
    elif atr_pct < 1.5:   # 1.0-1.5% — high
        return 'HIGH'
    else:                  # >1.5% — extreme
        return 'EXTREME'


def should_trade(token):
    """Main entry point: should we trade this token based on volatility?
    Returns: ('TRADE', regime) or ('SKIP', reason)
    """
    atr_pct = get_atr_pct(token)
    if atr_pct is None:
        return ('SKIP', 'no_data')

    regime = classify_volatility(atr_pct)

    if regime == 'FLAT':
        return ('SKIP', f'flat_water: ATR={atr_pct:.4f}% < 0.48%')
    elif regime == 'EXTREME':
        return ('SKIP', f'storm: ATR={atr_pct:.4f}% > 1.5%')
    else:
        return ('TRADE', regime)


def get_sl_multiplier(atr_pct):
    """Return SL multiplier based on volatility (percentage)."""
    if atr_pct < 0.48:
        return 0  # don't trade
    elif atr_pct < 0.8:
        return 1.0  # normal
    elif atr_pct < 1.0:
        return 1.2  # slightly wider
    elif atr_pct < 1.5:
        return 1.5  # wide
    else:
        return 0  # don't trade


if __name__ == '__main__':
    # Test on a few tokens
    test_tokens = ['BTC', 'ETH', 'SOL', 'ALGO', 'CC', 'AVNT']
    for tok in test_tokens:
        result = should_trade(tok)
        atr = get_atr_pct(tok)
        print(f'{tok}: ATR={atr:.4f}% → {result}')
