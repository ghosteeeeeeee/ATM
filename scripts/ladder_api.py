#!/usr/bin/env python3
"""ladder_api.py — the Ladder dashboard feed (CEO 2026-11-23).

Emits /var/www/hermes/data/ladder.json:
  price/age      live BTC from prices.json (the collector, ~5s fresh)
  candles[]      last 180 CLOSED 15m bars (the chart)
  rungs[]        armed BTC ladder rungs from pending_orders.json + states
  stats          ai-trader-pending: totals, windows, MFE split, recents

Refresh: hermes-ladder-api.timer (60s); the page polls every 30s.
Stdlib + local DB only (the local-data-first SOP).
"""
import json
import os
import sqlite3
import sys
import time

sys.path.insert(0, '/root/.hermes/scripts')
from paths import HERMES_DATA  # noqa: E402

OUT = '/var/www/hermes/data/ladder.json'


def live_price():
    try:
        d = json.load(open(os.path.join(HERMES_DATA, 'prices.json')))
        p = d.get('prices', {}).get('BTC')
        age = time.time() - float(d.get('updated') or 0)
        return (float(p) if p else None), age
    except Exception:
        return None, None


def candles(n=180):
    con = sqlite3.connect(
        f"file:{os.path.join(HERMES_DATA, 'candles.db')}?mode=ro", uri=True)
    try:
        cur = con.cursor()
        cur.execute(
            "SELECT ts, open, high, low, close FROM candles_15m "
            "WHERE token='BTC' AND is_closed=1 ORDER BY ts DESC LIMIT ?",
            (n,))
        rows = list(reversed(cur.fetchall()))
    finally:
        con.close()
    return [{'t': int(r[0]), 'o': float(r[1]), 'h': float(r[2]),
             'l': float(r[3]), 'c': float(r[4])} for r in rows]


def rungs():
    try:
        cfg = json.load(open(os.path.join(HERMES_DATA, 'pending_orders.json')))
        st = json.load(open(
            os.path.join(HERMES_DATA, 'pending_orders_state.json')))
    except Exception:
        return []
    out = []
    for o in cfg.get('orders', []):
        if o.get('coin') != 'BTC':
            continue
        s = st.get(o.get('id'), {}).get('status', 'UNFIRED')
        if s in ('fired', 'error'):
            continue  # consumed — not a planned entry anymore
        out.append({
            'id': o.get('id'), 'dir': o.get('direction'),
            'trig': float(o.get('trigger_price') or 0),
            'sl': float(o.get('sl') or 0) or None,
            'tp': float(o.get('target') or 0) or None,
            'style': o.get('entry_style', 'retest'),
            'state': s,
            'amt': o.get('amount_usdt'), 'lev': o.get('leverage'),
        })
    out.sort(key=lambda r: r['trig'])
    return out


def _net_of(fees, pnl_usdt):
    """HL's own net (the fees JSON blob) — falls back to pnl−fee_total."""
    if fees:
        try:
            f = json.loads(fees) if isinstance(fees, str) else fees
            if isinstance(f, dict) and f.get('net_pnl') is not None:
                return float(f['net_pnl'])
        except Exception:
            pass
    return float(pnl_usdt or 0)


def stats():
    try:
        from brain import get_db_connection
    except Exception as e:
        return {'error': f'brain import: {e}'}
    out = {}
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT id, direction, entry_price, exit_price, exit_reason, "
            "pnl_usdt, fees, amount_usdt, leverage, open_time, close_time, "
            "highest_price, lowest_price "
            "FROM trades WHERE status='closed' AND signal='ai-trader-pending' "
            "AND close_time > (now() - interval '14 days') "
            "ORDER BY close_time DESC")
        rows = cur.fetchall()
        cols = [d[0] for d in cur.description]

        now = time.time()
        recs = []
        for r in rows:
            d = dict(zip(cols, r))
            entry = float(d['entry_price'] or 0)
            hi = float(d['highest_price'] or 0)
            lo = float(d['lowest_price'] or 0)
            if entry and hi and lo:
                mfe = ((hi / entry - 1) if d['direction'] == 'LONG'
                       else (1 - lo / entry)) * 100
            else:
                mfe = 0.0
            hold = 0.0
            if d['open_time'] and d['close_time']:
                hold = (d['close_time'] - d['open_time']).total_seconds() / 60
            ct = d['close_time']
            recs.append({
                'id': d['id'], 'dir': d['direction'],
                'entry': entry,
                'exit': float(d['exit_price'] or 0) if d['exit_price'] else None,
                'reason': d['exit_reason'],
                'net': _net_of(d['fees'], d['pnl_usdt']),
                'mfe': round(mfe, 2), 'hold': int(hold),
                'ts': ct.isoformat() if ct else None,
                'ts_epoch': ct.timestamp() if ct else 0,
            })

        n = len(recs)
        net = sum(r['net'] for r in recs)
        wins = sum(1 for r in recs if r['net'] > 0)
        fees_paid = 0.0
        for r in rows:
            try:
                f = json.loads(r[6]) if isinstance(r[6], str) else (r[6] or {})
                fees_paid += float((f or {}).get('fee_total') or 0)
            except Exception:
                pass

        def window(hours):
            cut = now - hours * 3600
            w = [r for r in recs if r['ts_epoch'] >= cut]
            return len(w), round(sum(x['net'] for x in w), 4)

        # recency-weighted (half-life 3d) — the CEO's training tilt
        wnet = 0.0
        for r in recs:
            if not r['ts_epoch']:
                continue
            age_d = (now - r['ts_epoch']) / 86400.0
            wnet += (0.5 ** (age_d / 3.0)) * r['net']

        buckets = {'ran': [0, 0.0], 'mid': [0, 0.0], 'never': [0, 0.0]}
        for r in recs:
            k = ('ran' if r['mfe'] >= 1.0
                 else 'mid' if r['mfe'] >= 0.3 else 'never')
            buckets[k][0] += 1
            buckets[k][1] += r['net']

        cur.execute(
            "SELECT id, direction, entry_price, stop_loss, pnl_pct, amount_usdt "
            "FROM trades WHERE status='open' AND signal='ai-trader-pending'")
        opens = cur.fetchall()

        out = {
            'n': n, 'net': round(net, 4),
            'wr': round(wins / n * 100, 1) if n else 0,
            'wins': wins,
            'fees': round(fees_paid, 4),
            'per_trade': round(net / n, 4) if n else 0,
            'w24': window(24), 'w72': window(72), 'w168': window(168),
            'weighted_net_3d': round(wnet, 4),
            'closes_per_day': round(n / 14.0, 1),
            'mfe_split': {
                k: {'n': v[0], 'net': round(v[1], 4)}
                for k, v in buckets.items()},
            'open': [{'id': o[0], 'dir': o[1], 'entry': float(o[2] or 0),
                      'sl': float(o[3] or 0) if o[3] else None,
                      'pnl_pct': float(o[4] or 0), 'amt': o[5]}
                     for o in opens],
            'recent': recs[:25],
        }
        cur.close()
        conn.close()
    except Exception as e:
        out = {'error': str(e)}
    return out


def main():
    price, age = live_price()
    feed = {
        'ts': int(time.time()),
        'price': price,
        'price_age_s': round(age, 1) if age is not None else None,
        'candles': candles(),
        'rungs': rungs(),
        'stats': stats(),
    }
    tmp = OUT + '.tmp'
    with open(tmp, 'w') as f:
        json.dump(feed, f)
    os.replace(tmp, OUT)
    print(f"[ladder_api] price={price} candles={len(feed['candles'])} "
          f"rungs={len(feed['rungs'])} stats_n={feed['stats'].get('n')}")


if __name__ == '__main__':
    main()
