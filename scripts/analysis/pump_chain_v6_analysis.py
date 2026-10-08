#!/usr/bin/env python3
"""
pump_chain_v6_analysis.py — Winners vs Losers analysis for new pump-chain signal spec.

Pulls ALL closed pump-chain trades from PostgreSQL with detection-time metadata,
then compares winners vs losers feature-by-feature with:
- sample sizes (flag n < 20)
- Welch t-test p-values (manual, no scipy dependency assumed)
- time split: in-sample (first 70% by time) vs out-of-sample (last 30%)
- survivorship check: features evaluated on ALL trades, not just winners
"""
import json
import sys
import math
from datetime import datetime

import psycopg2

MIN_N = 20


def load_trades(days=60):
    conn = psycopg2.connect(host='/var/run/postgresql', database='brain', user='postgres')
    cur = conn.cursor()
    cur.execute("""
        SELECT token, direction, pnl_usdt, pnl_pct, open_time, close_time,
               signal, volatility_regime, _signal_metadata
        FROM trades
        WHERE status = 'closed'
          AND signal LIKE '%%pump-chain%%'
          AND open_time > now() - interval %s
          AND _signal_metadata IS NOT NULL
        ORDER BY open_time ASC
    """, (f'{days} days',))
    rows = cur.fetchall()
    cur.close()
    conn.close()

    trades = []
    for (token, direction, pnl_usdt, pnl_pct, ot, ct, signal, volreg, meta) in rows:
        if isinstance(meta, str):
            try:
                meta = json.loads(meta)
            except Exception:
                continue
        if not isinstance(meta, dict):
            continue
        trades.append({
            'token': token,
            'direction': direction,
            'pnl_usdt': float(pnl_usdt or 0),
            'pnl_pct': float(pnl_pct or 0) if pnl_pct is not None else None,
            'open_time': ot,
            'signal': signal,
            'volatility_regime': volreg,
            'meta': meta,
        })
    return trades


def welch_p(a, b):
    """Welch t-test p-value via normal approximation (n>=8 ok for screening)."""
    n1, n2 = len(a), len(b)
    if n1 < 3 or n2 < 3:
        return None
    m1 = sum(a) / n1
    m2 = sum(b) / n2
    v1 = sum((x - m1) ** 2 for x in a) / (n1 - 1)
    v2 = sum((x - m2) ** 2 for x in b) / (n2 - 1)
    se = math.sqrt(v1 / n1 + v2 / n2)
    if se == 0:
        return None
    t = (m1 - m2) / se
    # normal approximation
    return math.erfc(abs(t) / math.sqrt(2))


def fmt_p(p):
    if p is None:
        return '  n/a'
    if p < 0.001:
        return '<.001'
    return f'{p:.3f}'


def analyze(trades, label):
    print(f'\n{"=" * 100}')
    print(f'== {label} — n={len(trades)}')
    print(f'{"=" * 100}')

    wins = [t for t in trades if t['pnl_usdt'] > 0]
    losses = [t for t in trades if t['pnl_usdt'] <= 0]
    wr = 100.0 * len(wins) / len(trades) if trades else 0
    total = sum(t['pnl_usdt'] for t in trades)
    print(f'WINNERS n={len(wins)}  LOSERS n={len(losses)}  WR={wr:.1f}%  TOTAL PnL=${total:+.2f}')
    print(f'avg win=${sum(t["pnl_usdt"] for t in wins)/max(1,len(wins)):+.3f}  '
          f'avg loss=${sum(t["pnl_usdt"] for t in losses)/max(1,len(losses)):+.3f}')

    # Direction split
    print('\n-- Direction split --')
    for d in ('LONG', 'SHORT'):
        sub = [t for t in trades if t['direction'] == d]
        if not sub:
            continue
        w = [t for t in sub if t['pnl_usdt'] > 0]
        print(f'  {d:5s}: n={len(sub):3d} WR={100.0*len(w)/len(sub):.1f}% '
              f'PnL=${sum(t["pnl_usdt"] for t in sub):+.2f}')

    # Numeric features
    numeric_keys = [
        'rsi_14', 'z_score', 'btc_score', 'macd_hist', 'macd_value', 'bb_position',
        'volume_spike', 'momentum_score', 'speed_percentile', 'staleness_minutes',
        'price_acceleration', 'gap_at_entry', 'btc_trend_bias', 'btc_linreg_bias',
        'final_confidence',
    ]
    print('\n-- Numeric features (winner avg vs loser avg, p-value) --')
    print(f'  {"feature":22s} {"win_avg":>10s} {"loss_avg":>10s} {"p":>7s} {"win_n":>6s} {"loss_n":>6s}  note')
    for k in numeric_keys:
        wv = [t['meta'][k] for t in wins if isinstance(t['meta'].get(k), (int, float))]
        lv = [t['meta'][k] for t in losses if isinstance(t['meta'].get(k), (int, float))]
        if not wv or not lv:
            continue
        p = welch_p(wv, lv)
        note = ''
        if len(wv) < MIN_N or len(lv) < MIN_N:
            note = 'SMALL N'
        if p is not None and p < 0.05 and not note:
            note = '*** SIG'
        elif p is not None and p < 0.05:
            note += ' (sig, small n)'
        print(f'  {k:22s} {sum(wv)/len(wv):>10.3f} {sum(lv)/len(lv):>10.3f} {fmt_p(p):>7s} '
              f'{len(wv):>6d} {len(lv):>6d}  {note}')

    # Categorical features
    cat_keys = ['wave_phase', 'momentum_state', 'btc_regime', 'z_score_tier',
                'volatility_regime', 'is_stale']
    for k in cat_keys:
        print(f'\n-- Categorical: {k} --')
        buckets = {}
        for t in trades:
            v = t['meta'].get(k, t.get(k) if k == 'volatility_regime' else None)
            if v is None:
                v = t['volatility_regime'] if k == 'volatility_regime' else None
            if v is None:
                continue
            v = str(v)
            b = buckets.setdefault(v, {'n': 0, 'w': 0, 'pnl': 0.0})
            b['n'] += 1
            b['pnl'] += t['pnl_usdt']
            if t['pnl_usdt'] > 0:
                b['w'] += 1
        for v, b in sorted(buckets.items(), key=lambda x: -x[1]['n']):
            wr_b = 100.0 * b['w'] / b['n']
            flag = 'SMALL N' if b['n'] < MIN_N else ('WINNER-ish' if b['pnl'] > 0.5 else ('loser-ish' if b['pnl'] < -0.5 else ''))
            print(f'  {v:18s} n={b["n"]:3d} WR={wr_b:5.1f}% PnL=${b["pnl"]:+7.2f}  {flag}')

    # RSI bands (constants reference RSI windows for pump-chain)
    print('\n-- RSI bands --')
    bands = [(0, 40), (40, 45), (45, 50), (50, 55), (55, 60), (60, 70), (70, 100)]
    for lo, hi in bands:
        sub = [t for t in trades if isinstance(t['meta'].get('rsi_14'), (int, float))
               and lo <= t['meta']['rsi_14'] < hi]
        if not sub:
            continue
        w = [t for t in sub if t['pnl_usdt'] > 0]
        print(f'  RSI {lo:3d}-{hi:3d}: n={len(sub):3d} WR={100.0*len(w)/len(sub):5.1f}% '
              f'PnL=${sum(t["pnl_usdt"] for t in sub):+7.2f}')

    # z-score bands
    print('\n-- z-score bands --')
    zb = [(-99, -1.5), (-1.5, -0.5), (-0.5, 0.5), (0.5, 1.5), (1.5, 2.5), (2.5, 99)]
    for lo, hi in zb:
        sub = [t for t in trades if isinstance(t['meta'].get('z_score'), (int, float))
               and lo <= t['meta']['z_score'] < hi]
        if not sub:
            continue
        w = [t for t in sub if t['pnl_usdt'] > 0]
        print(f'  z {lo:+.1f}..{hi:+.1f}: n={len(sub):3d} WR={100.0*len(w)/len(sub):5.1f}% '
              f'PnL=${sum(t["pnl_usdt"] for t in sub):+7.2f}')

    # speed_percentile bands
    print('\n-- speed_percentile bands --')
    for lo, hi in [(0, 25), (25, 50), (50, 75), (75, 90), (90, 101)]:
        sub = [t for t in trades if isinstance(t['meta'].get('speed_percentile'), (int, float))
               and lo <= t['meta']['speed_percentile'] < hi]
        if not sub:
            continue
        w = [t for t in sub if t['pnl_usdt'] > 0]
        print(f'  speed {lo:3d}-{hi:3d}: n={len(sub):3d} WR={100.0*len(w)/len(sub):5.1f}% '
              f'PnL=${sum(t["pnl_usdt"] for t in sub):+7.2f}')

    # staleness bands
    print('\n-- staleness_minutes bands --')
    for lo, hi in [(0, 2), (2, 5), (5, 10), (10, 20), (20, 999)]:
        sub = [t for t in trades if isinstance(t['meta'].get('staleness_minutes'), (int, float))
               and lo <= t['meta']['staleness_minutes'] < hi]
        if not sub:
            continue
        w = [t for t in sub if t['pnl_usdt'] > 0]
        print(f'  stale {lo:3d}-{hi:4d}m: n={len(sub):3d} WR={100.0*len(w)/len(sub):5.1f}% '
              f'PnL=${sum(t["pnl_usdt"] for t in sub):+7.2f}')


def main():
    days = int(sys.argv[1]) if len(sys.argv) > 1 else 60
    trades = load_trades(days)
    if not trades:
        print('No trades found')
        return

    # Full sample
    analyze(trades, f'FULL SAMPLE last {days}d')

    # Time split: first 70% in-sample, last 30% out-of-sample
    n = len(trades)
    cut = int(n * 0.7)
    analyze(trades[:cut], 'IN-SAMPLE (first 70% by open_time)')
    analyze(trades[cut:], 'OUT-OF-SAMPLE (last 30% by open_time)')


if __name__ == '__main__':
    main()
