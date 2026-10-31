#!/usr/bin/env python3
"""
copy_trader_api.py — copy_trader dashboard data generator.

FIX (2026-10-31): this file was found ZERO BYTES while its systemd service
(copy-trader-api.timer, every 60s) kept 'succeeding' — python3 exits 0 on an
empty script — so /var/www/hermes/data/copy_trader.json was FROZEN at
2026-08-27 and every table on copy_trader.html silently rendered two-month-old
data (leaderboard/trades tables broken entirely: the old JSON had no such keys).

Rebuilt from:
  - PostgreSQL (brain.trades)        — aggregates, equity curve, recent trades
  - HERMES_DATA/copy_trust.json      — the TIER leaderboard (trust system)
  - hl_copy.db (traders/performance) — pro-side stats per wallet

Section errors never abort the run (per-section try) — the file always writes
with a fresh 'updated'.
"""

import json
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone

try:
    from paths import WWW_DATA, HERMES_DATA
except ImportError:
    WWW_DATA = '/var/www/hermes/data'
    HERMES_DATA = '/root/.hermes/data'

OUT = os.path.join(WWW_DATA, 'copy_trader.json')
TRUST_FILE = os.path.join(HERMES_DATA, 'copy_trust.json')


def _pg():
    from _secrets import BRAIN_DB_DICT
    import psycopg2
    cfg = BRAIN_DB_DICT.copy()
    cfg.setdefault('port', 5432)
    cfg['connect_timeout'] = 10
    return psycopg2.connect(**cfg)


def _f(v, d=0.0):
    try:
        return float(v) if v is not None else d
    except (TypeError, ValueError):
        return d


def build():
    out = {
        'updated': datetime.now(timezone.utc).isoformat(),
        'summary': {}, 'by_token': {}, 'by_reason': {}, 'by_wallet': {},
        'by_hour': {}, 'by_regime': {}, 'hold_dist': {},
        'equity_curve': [], 'leaderboard': [], 'trades': [],
    }

    try:
        import sqlite3
        conn = _pg()
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT id, token, direction, status, pnl_pct, pnl_usdt,
                       open_time, close_time, close_reason, confidence,
                       _signal_metadata, amount_usdt, volatility_regime
                FROM trades
                WHERE signal LIKE '%%hl_copy%%'
                ORDER BY id ASC
            """)
            rows = cur.fetchall()
        finally:
            conn.close()

        # ---- normalize rows ----
        trades = []
        for r in rows:
            meta = r[10] if isinstance(r[10], dict) else (
                json.loads(r[10]) if r[10] else {})
            hold_h = 0.0
            if r[6] and r[7]:
                try:
                    hold_h = (r[7] - r[6]).total_seconds() / 3600
                except Exception:
                    hold_h = 0.0
            trades.append({
                'id': r[0], 'token': r[1], 'direction': r[2], 'status': r[3],
                'pnl_pct': _f(r[4]), 'pnl': _f(r[5]), 'pnl_usdt': _f(r[5]),
                'open_time': r[6].isoformat() if r[6] else None,
                'close_time': r[7].isoformat() if r[7] else None,
                'close_reason': r[8] or '', 'confidence': _f(r[9]),
                'wallet': meta.get('trader_wallet', ''),
                'trust_tier': meta.get('trust_tier', ''),
                'amount_usdt': _f(r[11], 11.0),
                'volatility_regime': r[12] or 'unknown',
                'hold_h': hold_h,
            })

        closed = [t for t in trades if t['status'] == 'closed']
        opn = [t for t in trades if t['status'] == 'open']
        wins = len([t for t in closed if t['pnl_pct'] > 0.1])
        losses = len([t for t in closed if t['pnl_pct'] < -0.1])

        # win/loss streaks
        max_w = max_l = cw = cl = 0
        for t in sorted(closed, key=lambda x: x['close_time'] or ''):
            if t['pnl_pct'] > 0.1:
                cw += 1; cl = 0
            elif t['pnl_pct'] < -0.1:
                cl += 1; cw = 0
            else:
                cw = cl = 0
            max_w, max_l = max(max_w, cw), max(max_l, cl)

        n_closed = len(closed) or 1
        out['summary'] = {
            'total': len(trades),
            'closed': len(closed),
            'open': len(opn),
            'wins': wins,
            'losses': losses,
            'win_rate': round(wins / n_closed * 100) if closed else 0,
            'total_pnl': round(sum(t['pnl'] for t in closed), 2),
            'total_usdt': round(sum(t['pnl_usdt'] for t in closed), 2),
            'avg_hold': round(sum(t['hold_h'] for t in closed) / n_closed, 1),
            'avg_notional': round(
                sum(t['amount_usdt'] for t in trades) / (len(trades) or 1), 1),
            'max_win_streak': max_w,
            'max_loss_streak': max_l,
            'tracked_traders': 0,
            'last_leaderboard_refresh': '',
        }

        # ---- per-dimension aggregates ----
        def agg(keyfn, target, hold=True):
            bucket = defaultdict(lambda: {'wins': 0, 'losses': 0, 'pnl': 0.0,
                                          'count': 0, 'hold': []})
            for t in closed:
                k = keyfn(t)
                b = bucket[k]
                b['count'] += 1
                b['pnl'] += t['pnl_pct']
                if t['pnl_pct'] > 0.1:
                    b['wins'] += 1
                elif t['pnl_pct'] < -0.1:
                    b['losses'] += 1
                b['hold'].append(t['hold_h'])
            for k, b in bucket.items():
                entry = {
                    'wins': b['wins'], 'losses': b['losses'],
                    'pnl': round(b['pnl'], 2), 'count': b['count'],
                    'wr': round(b['wins'] / b['count'] * 100) if b['count'] else 0,
                }
                if hold and b['hold']:
                    entry['avg_hold'] = round(sum(b['hold']) / len(b['hold']), 1)
                out[target][str(k)] = entry

        agg(lambda t: t['token'], 'by_token')
        agg(lambda t: t['close_reason'] or 'open', 'by_reason')
        agg(lambda t: (t['open_time'] or 'xx')[11:13], 'by_hour', hold=False)

        # regime × direction
        bucket = defaultdict(lambda: {'n': 0, 'w': 0, 'pnl': 0.0})
        for t in closed:
            b = bucket[(t['volatility_regime'], t['direction'])]
            b['n'] += 1
            b['pnl'] += t['pnl_pct']
            if t['pnl_pct'] > 0.1:
                b['w'] += 1
        for (reg, dr), b in bucket.items():
            out['by_regime'].setdefault(reg, {})[dr] = {
                'count': b['n'],
                'wr': round(b['w'] / b['n'] * 100, 1) if b['n'] else 0,
                'pnl': round(b['pnl'], 2),
                'avg_pnl': round(b['pnl'] / b['n'], 3) if b['n'] else 0,
            }

        # hold-time distribution
        bands = [('0-0.5h', 0, 0.5), ('0.5-1h', 0.5, 1), ('1-2h', 1, 2),
                 ('2-4h', 2, 4), ('4-8h', 4, 8), ('>8h', 8, 1e9)]
        for lbl, lo, hi in bands:
            sel = [t for t in closed if lo <= t['hold_h'] < hi]
            if sel:
                w = len([t for t in sel if t['pnl_pct'] > 0.1])
                out['hold_dist'][lbl] = {'count': len(sel),
                                         'wr': round(w / len(sel) * 100)}

        # equity curve (closed, capped)
        out['equity_curve'] = [
            {'id': t['id'], 'pnl': t['pnl'], 'token': t['token'],
             'time': t['close_time'] or t['open_time']}
            for t in closed[-300:]]

        # recent trades table (newest first)
        out['trades'] = sorted(trades, key=lambda t: t['id'], reverse=True)[:100]

        # ---- per-wallet (pro + ours) ----
        w_bucket = defaultdict(lambda: {'wins': 0, 'losses': 0, 'be': 0,
                                        'open': 0, 'pnl': 0.0, 'trades': [],
                                        'usdt': []})
        for t in trades:
            if not t['wallet']:
                continue
            b = w_bucket[t['wallet']]
            if t['status'] == 'open':
                b['open'] += 1
                continue
            b['pnl'] += t['pnl_pct']
            if t['pnl_pct'] > 0.1:
                b['wins'] += 1
            elif t['pnl_pct'] < -0.1:
                b['losses'] += 1
            else:
                b['be'] += 1
            b['usdt'].append(t['amount_usdt'])
            b['trades'].append({'id': t['id'], 'token': t['token'],
                                'pnl': t['pnl'], 'status': t['status'],
                                'reason': t['close_reason']})

        # pro stats from hl_copy.db for context
        pro = {}
        try:
            hc = sqlite3.connect(os.path.join(HERMES_DATA, 'hl_copy.db'),
                                 timeout=5)
            hc.row_factory = sqlite3.Row
            for r in hc.execute(
                    "SELECT wallet, copy_wr, copy_pnl, copy_trades FROM traders "
                    "WHERE wallet IS NOT NULL"):
                pro[r['wallet'].lower()] = dict(r)
            hc.close()
        except Exception:
            pro = {}

        for w, b in w_bucket.items():
            p = pro.get(w.lower(), {})
            out['by_wallet'][w] = {
                'wins': b['wins'], 'losses': b['losses'], 'be': b['be'],
                'open': b['open'], 'total_pnl': round(b['pnl'], 2),
                'trades': b['trades'][-10:],
                'wr': round(b['wins'] / (b['wins'] + b['losses']) * 100)
                      if (b['wins'] + b['losses']) else 0,
                'avg_position': round(sum(b['usdt']) / len(b['usdt']), 2)
                                if b['usdt'] else 0,
                'total_volume': round(sum(b['usdt']), 2),
                'copy_wr': p.get('copy_wr') or 0,
                'pro_hype_pnl': p.get('copy_pnl') or 0,
                'pro_hype_wr': 0,
                'pro_hype_trades': p.get('copy_trades') or 0,
                'pro_avg_position': 0,
                'score': 0, 'pattern': '',
            }

        # ---- TIER leaderboard (trust system) ----
        try:
            with open(TRUST_FILE) as f:
                tf = json.load(f)
            for e in (tf.get('leaderboard') or [])[:50]:
                wl = out['by_wallet'].get(e.get('wallet'), {})
                out['leaderboard'].append({
                    'wallet': e.get('wallet'),
                    'tier': e.get('tier', 'T2'),
                    'wr': round(_f(e.get('wr')) * 100),
                    'pnl': _f(e.get('pnl_after_latency')),
                    'trades': int(_f(e.get('n'))),
                    'copy_wr': wl.get('wr', 0),
                    'copy_trades': len(wl.get('trades', [])),
                    'their_pnl': _f(e.get('pnl_their_size')),
                })
            out['summary']['tracked_traders'] = len(tf.get('wallets') or {})
            out['summary']['last_leaderboard_refresh'] = datetime.fromtimestamp(
                tf.get('updated') or 0, timezone.utc).isoformat()
        except Exception as e:
            print(f"[copy_trader_api] trust leaderboard unavailable: {e}")

    except Exception as e:
        print(f"[copy_trader_api] section build error: {e}")

    try:
        os.makedirs(WWW_DATA, exist_ok=True)
        with open(OUT, 'w') as f:
            json.dump(out, f, default=str)
        print(f"[copy_trader_api] wrote {OUT} "
              f"({len(out['trades'])} trades, {len(out['leaderboard'])} leaderboard)")
    except OSError as e:
        print(f"[copy_trader_api] write failed: {e}")
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(build())
