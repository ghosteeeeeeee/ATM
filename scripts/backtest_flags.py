#!/usr/bin/env python3
"""
backtest_flags.py — Backtest bull/bear/micro flag patterns against historical 1m prices.

Slides a window through price_history, runs flag detectors, and tracks outcomes.
"""

import sys, os, time, sqlite3
from datetime import datetime, timedelta
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pattern_scanner import (
    detect_bull_flag, detect_bear_flag,
    detect_micro_bull_flag, detect_micro_bear_flag,
)

PRICE_DB = '/root/.hermes/data/signals_hermes.db'

# Backtest parameters
LOOKBACK_MINUTES = 240   # 4h window for pattern detection
HOLD_PERIODS = [15, 30, 60, 120]  # minutes to check outcome
MIN_DATAPOINTS = 300     # skip tokens with less data
SLIDE_STEP = 60          # slide window every 60 minutes

# Tokens to backtest (top volume on HL)
TOKENS = [
    'ETH', 'BTC', 'SOL', 'DOGE', 'XRP',
]


def load_prices(token: str, days: int = 30) -> list:
    """Load 1m close prices for a token, oldest first. Last N days only."""
    try:
        conn = sqlite3.connect(PRICE_DB, timeout=10)
        c = conn.cursor()
        cutoff = int(time.time()) - days * 86400
        c.execute("""
            SELECT timestamp, price FROM price_history
            WHERE token = ? AND timestamp > ? ORDER BY timestamp ASC
        """, (token.upper(), cutoff))
        rows = c.fetchall()
        conn.close()
        return [(r[0], r[1]) for r in rows]
    except Exception:
        return []


def run_backtest():
    """Run backtest across all tokens and flag types."""
    results = {
        'bull_flag': {'wins': 0, 'losses': 0, 'total': 0, 'pnl': []},
        'bear_flag': {'wins': 0, 'losses': 0, 'total': 0, 'pnl': []},
        'micro_bull_flag': {'wins': 0, 'losses': 0, 'total': 0, 'pnl': []},
        'micro_bear_flag': {'wins': 0, 'losses': 0, 'total': 0, 'pnl': []},
    }

    # Per-hold-period tracking
    by_period = {}
    for hp in HOLD_PERIODS:
        by_period[hp] = {
            'bull_flag': {'wins': 0, 'losses': 0, 'total': 0},
            'bear_flag': {'wins': 0, 'losses': 0, 'total': 0},
            'micro_bull_flag': {'wins': 0, 'losses': 0, 'total': 0},
            'micro_bear_flag': {'wins': 0, 'losses': 0, 'total': 0},
        }

    total_signals = 0
    tokens_tested = 0

    for token in TOKENS:
        prices = load_prices(token)
        if len(prices) < MIN_DATAPOINTS:
            print(f'  {token}: insufficient data ({len(prices)} points)')
            continue

        tokens_tested += 1
        timestamps = [p[0] for p in prices]
        close_prices = [p[1] for p in prices]

        # Slide window through data
        signals_found = 0
        for start_idx in range(0, len(close_prices) - LOOKBACK_MINUTES, SLIDE_STEP):
            window = close_prices[start_idx:start_idx + LOOKBACK_MINUTES]

            # Create candle dicts for detector
            candles = [
                {'close': c, 'high': c, 'low': c, 'open': c, 'volume': 0, 'open_time': 0}
                for c in window
            ]

            # Try each detector
            detectors = [
                ('bull_flag', detect_bull_flag),
                ('bear_flag', detect_bear_flag),
                ('micro_bull_flag', detect_micro_bull_flag),
                ('micro_bear_flag', detect_micro_bear_flag),
            ]

            for pattern_type, detector in detectors:
                signal = detector(candles)
                if signal is None:
                    continue

                signals_found += 1
                total_signals += 1

                # Get entry price (close of signal candle)
                entry_idx = start_idx + LOOKBACK_MINUTES - 1
                entry_price = close_prices[entry_idx]
                direction = signal['direction']

                # Check outcome at each hold period
                for hp in HOLD_PERIODS:
                    outcome_idx = entry_idx + hp
                    if outcome_idx >= len(close_prices):
                        continue

                    exit_price = close_prices[outcome_idx]
                    if direction == 'LONG':
                        pnl_pct = (exit_price - entry_price) / entry_price * 100
                    else:  # SHORT
                        pnl_pct = (entry_price - exit_price) / entry_price * 100

                    is_win = pnl_pct > 0

                    results[pattern_type]['total'] += 1
                    results[pattern_type]['pnl'].append(pnl_pct)
                    if is_win:
                        results[pattern_type]['wins'] += 1
                    else:
                        results[pattern_type]['losses'] += 1

                    by_period[hp][pattern_type]['total'] += 1
                    if is_win:
                        by_period[hp][pattern_type]['wins'] += 1
                    else:
                        by_period[hp][pattern_type]['losses'] += 1

        print(f'  {token}: {signals_found} signals (data: {len(close_prices)} candles)')

    # ── Print Results ────────────────────────────────────────────────────────
    print(f'\n{"="*70}')
    print(f'BACKTEST RESULTS — {tokens_tested} tokens, {total_signals} total signals')
    print(f'{"="*70}\n')

    for pattern_type in ['bull_flag', 'bear_flag', 'micro_bull_flag', 'micro_bear_flag']:
        r = results[pattern_type]
        if r['total'] == 0:
            continue

        wr = r['wins'] / r['total'] * 100 if r['total'] > 0 else 0
        avg_pnl = sum(r['pnl']) / len(r['pnl']) if r['pnl'] else 0
        print(f'{pattern_type}:')
        print(f'  Signals: {r["total"]//4} (across 4 hold periods)')
        print(f'  Win rate: {wr:.1f}% ({r["wins"]}/{r["total"]})')
        print(f'  Avg PnL: {avg_pnl:+.3f}%')
        print()

    # Per hold period breakdown
    print(f'{"="*70}')
    print(f'BY HOLD PERIOD')
    print(f'{"="*70}\n')

    for hp in HOLD_PERIODS:
        print(f'--- {hp} min hold ---')
        for pattern_type in ['bull_flag', 'bear_flag', 'micro_bull_flag', 'micro_bear_flag']:
            r = by_period[hp][pattern_type]
            if r['total'] == 0:
                continue
            wr = r['wins'] / r['total'] * 100
            print(f'  {pattern_type:25s}: {wr:5.1f}% WR ({r["wins"]}/{r["total"]})')
        print()


if __name__ == '__main__':
    run_backtest()
