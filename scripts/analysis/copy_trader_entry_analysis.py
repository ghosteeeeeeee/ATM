#!/usr/bin/env python3
"""
Copy Trader Entry Timing Analysis
Deep dive into what makes winning vs losing copy trades.

Usage:
    cd /root/.hermes/scripts
    python3 analysis/copy_trader_entry_analysis.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from _secrets import BRAIN_DB_DICT
from hl_copy_db import get_db
import psycopg2
import json
from datetime import datetime


def get_copy_trades():
    """Pull all copy trader trades from PostgreSQL."""
    DB_CONFIG = BRAIN_DB_DICT.copy()
    DB_CONFIG.setdefault('port', 5432)
    pg = psycopg2.connect(**DB_CONFIG)
    pg.autocommit = True
    cur = pg.cursor()

    cur.execute('''
        SELECT id, token, direction, entry_price, hl_entry_price, pnl_pct, pnl_usdt,
               close_reason, _signal_metadata, open_time, close_time, status, leverage,
               signal, confidence, signal_z_score, signal_rsi_14, signal_macd_hist,
               signal_momentum_state, signal_z_score_tier, regime
        FROM trades
        WHERE signal LIKE '%hl_copy_trader%'
        ORDER BY id
    ''')
    trades = cur.fetchall()
    cols = [desc[0] for desc in cur.description]
    cur.close()
    pg.close()
    return trades, cols


def parse_trades(trades, cols):
    """Parse raw trade rows into structured dicts."""
    parsed = []
    for row in trades:
        d = dict(zip(cols, row))
        meta = d['_signal_metadata'] if isinstance(d['_signal_metadata'], dict) else {}
        if isinstance(d['_signal_metadata'], str):
            try:
                meta = json.loads(d['_signal_metadata'])
            except:
                meta = {}

        pnl = float(d['pnl_pct'] or 0)
        open_t = d['open_time']
        close_t = d['close_time']
        hold_hours = (close_t - open_t).total_seconds() / 3600 if open_t and close_t else 0
        hour = open_t.hour if open_t else -1

        parsed.append({
            'id': d['id'], 'token': d['token'], 'direction': d['direction'],
            'entry': float(d['hl_entry_price'] or d['entry_price'] or 0),
            'pnl_pct': pnl, 'pnl_usdt': float(d['pnl_usdt'] or 0),
            'close_reason': d['close_reason'] or 'unknown',
            'is_win': pnl > 0.05, 'is_loss': pnl < -0.05,
            'hold_hours': hold_hours, 'hour': hour,
            'z_score': float(d['signal_z_score'] or 0),
            'rsi': float(d['signal_rsi_14'] or 0),
            'macd_hist': float(d['signal_macd_hist'] or 0),
            'confidence': float(d['confidence'] or 0),
            'regime': d['regime'] or 'unknown',
            'trader_wallet': meta.get('trader_wallet', ''),
            'trader_score': meta.get('trader_score', 0),
            'trader_wr': meta.get('trader_win_rate', 0),
            'open_time': open_t, 'close_time': close_t,
            'leverage': d['leverage'],
        })
    return parsed


def analyze(parsed):
    """Run all analyses and print results."""
    winners = [t for t in parsed if t['is_win']]
    losers = [t for t in parsed if t['is_loss']]

    print(f"Total trades: {len(parsed)}")
    print(f"Winners: {len(winners)} | Losers: {len(losers)} | Breakeven: {len(parsed) - len(winners) - len(losers)}")
    print(f"Win rate: {len(winners)/(len(winners)+len(losers))*100:.1f}%" if (winners or losers) else "N/A")
    print(f"Total PnL: {sum(t['pnl_pct'] for t in parsed):+.2f}%")
    print(f"Total PnL $: ${sum(t['pnl_usdt'] for t in parsed):+.3f}")

    # Time of day
    print("\n=== TIME OF DAY (UTC) ===")
    hour_stats = {}
    for t in parsed:
        h = t['hour']
        if h not in hour_stats:
            hour_stats[h] = {'wins': 0, 'losses': 0, 'total_pnl': 0, 'count': 0}
        hour_stats[h]['count'] += 1
        hour_stats[h]['total_pnl'] += t['pnl_pct']
        if t['is_win']:
            hour_stats[h]['wins'] += 1
        elif t['is_loss']:
            hour_stats[h]['losses'] += 1

    for h in sorted(hour_stats.keys()):
        s = hour_stats[h]
        wr = s['wins'] / (s['wins'] + s['losses']) * 100 if (s['wins'] + s['losses']) > 0 else 0
        print(f"  {h:02d}:00  n={s['count']:2d}  W/L={s['wins']:2d}/{s['losses']:2d}  "
              f"WR={wr:5.1f}%  PnL={s['total_pnl']:+6.2f}%")

    # Hold time
    print("\n=== HOLD TIME DISTRIBUTION ===")
    hold_buckets = [(0, 0.5), (0.5, 1), (1, 2), (2, 4), (4, 8), (8, 24)]
    for lo, hi in hold_buckets:
        bucket = [t for t in parsed if lo <= t['hold_hours'] < hi]
        if not bucket:
            continue
        wins = len([t for t in bucket if t['is_win']])
        losses = len([t for t in bucket if t['is_loss']])
        total_pnl = sum(t['pnl_pct'] for t in bucket)
        wr = wins / (wins + losses) * 100 if (wins + losses) > 0 else 0
        print(f"  {lo:.0f}-{hi:.0f}h: n={len(bucket):2d}  W/L={wins}/{losses}  WR={wr:.0f}%  PnL={total_pnl:+.2f}%")

    # Filter combinations
    print("\n=== FILTER COMBINATION ANALYSIS ===")
    filters = [
        ("No filter", lambda t: True),
        ("LONG only", lambda t: t['direction'] == 'LONG'),
        ("Not 14/18/20 UTC", lambda t: t['hour'] not in [14, 18, 20]),
        ("LONG + not bad hours", lambda t: t['direction'] == 'LONG' and t['hour'] not in [14, 18, 20]),
    ]
    for label, fn in filters:
        filtered = [t for t in parsed if fn(t)]
        wins = len([t for t in filtered if t['is_win']])
        losses = len([t for t in filtered if t['is_loss']])
        total_pnl = sum(t['pnl_pct'] for t in filtered)
        wr = wins / (wins + losses) * 100 if (wins + losses) > 0 else 0
        print(f"  {label:<30s} n={len(filtered):2d}  WR={wr:.0f}%  PnL={total_pnl:+.2f}%")


if __name__ == '__main__':
    trades, cols = get_copy_trades()
    parsed = parse_trades(trades, cols)
    analyze(parsed)
