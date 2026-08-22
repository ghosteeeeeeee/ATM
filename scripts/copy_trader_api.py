#!/usr/bin/env python3
"""Copy Trader API — generates JSON data for the web dashboard."""
import sys, json, os, time, fcntl
sys.path.insert(0, '/root/.hermes/scripts')

from _secrets import BRAIN_DB_DICT
from hl_copy_db import get_db
import psycopg2
from datetime import datetime

WWW_DATA = '/var/www/hermes/data'
OUTPUT_FILE = os.path.join(WWW_DATA, 'copy_trader.json')


def _atomic_write(data: dict, path: str):
    """Write JSON atomically using flock."""
    lock_path = path + '.lock'
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(lock_path, 'w') as lf:
        fcntl.flock(lf.fileno(), fcntl.LOCK_EX)
        with open(path, 'w') as f:
            json.dump(data, f, indent=2, default=str)
        fcntl.flock(lf.fileno(), fcntl.LOCK_UN)


def generate_data():
    """Generate copy trader dashboard data."""
    # PostgreSQL connection
    DB_CONFIG = BRAIN_DB_DICT.copy()
    DB_CONFIG.setdefault('port', 5432)
    pg = psycopg2.connect(**DB_CONFIG)
    pg.autocommit = True
    cur = pg.cursor()

    # Get all copy trades
    cur.execute('''
        SELECT id, token, direction, entry_price, hl_entry_price, pnl_pct, pnl_usdt,
               close_reason, _signal_metadata, open_time, close_time, status, leverage,
               signal, confidence
        FROM trades
        WHERE signal LIKE '%hl_copy_trader%'
        ORDER BY id DESC
    ''')
    trades = cur.fetchall()
    cols = [desc[0] for desc in cur.description]
    cur.close()
    pg.close()

    # Parse trades
    parsed = []
    for row in trades:
        d = dict(zip(cols, row))
        meta = d['_signal_metadata'] if isinstance(d['_signal_metadata'], dict) else {}
        if isinstance(d['_signal_metadata'], str):
            try: meta = json.loads(d['_signal_metadata'])
            except: meta = {}

        pnl = float(d['pnl_pct'] or 0)
        open_t = d['open_time']
        close_t = d['close_time']
        hold_hours = 0
        if open_t and close_t:
            hold_hours = round((close_t - open_t).total_seconds() / 3600, 1)

        parsed.append({
            'id': d['id'],
            'token': d['token'],
            'direction': d['direction'],
            'entry': float(d['hl_entry_price'] or d['entry_price'] or 0),
            'pnl_pct': round(pnl, 2),
            'pnl_usdt': round(float(d['pnl_usdt'] or 0), 3),
            'close_reason': d['close_reason'] or 'unknown',
            'status': d['status'],
            'hold_hours': hold_hours,
            'leverage': d['leverage'],
            'confidence': float(d['confidence'] or 0),
            'trader_wallet': meta.get('trader_wallet', ''),
            'trader_score': meta.get('trader_score', 0),
            'trader_wr': meta.get('trader_win_rate', 0),
            'open_time': open_t.isoformat() if open_t else None,
            'close_time': close_t.isoformat() if close_t else None,
        })

    # Overall stats
    closed = [t for t in parsed if t['status'] == 'closed']
    open_trades = [t for t in parsed if t['status'] == 'open']
    wins = len([t for t in closed if t['pnl_pct'] > 0.05])
    losses = len([t for t in closed if t['pnl_pct'] < -0.05])
    total_pnl = sum(t['pnl_pct'] for t in closed)
    total_usdt = sum(t['pnl_usdt'] for t in closed)

    # Per-token stats
    token_stats = {}
    for t in closed:
        tok = t['token']
        if tok not in token_stats:
            token_stats[tok] = {'wins': 0, 'losses': 0, 'pnl': 0, 'usdt': 0, 'count': 0}
        token_stats[tok]['count'] += 1
        token_stats[tok]['pnl'] += t['pnl_pct']
        token_stats[tok]['usdt'] += t['pnl_usdt']
        if t['pnl_pct'] > 0.05: token_stats[tok]['wins'] += 1
        elif t['pnl_pct'] < -0.05: token_stats[tok]['losses'] += 1

    for tok in token_stats:
        s = token_stats[tok]
        s['wr'] = round(s['wins'] / (s['wins'] + s['losses']) * 100) if (s['wins'] + s['losses']) > 0 else 0
        s['pnl'] = round(s['pnl'], 2)
        s['usdt'] = round(s['usdt'], 3)

    # Exit reason stats
    reason_stats = {}
    for t in closed:
        r = t['close_reason']
        if r not in reason_stats:
            reason_stats[r] = {'wins': 0, 'losses': 0, 'pnl': 0, 'count': 0}
        reason_stats[r]['count'] += 1
        reason_stats[r]['pnl'] += t['pnl_pct']
        if t['pnl_pct'] > 0.05: reason_stats[r]['wins'] += 1
        elif t['pnl_pct'] < -0.05: reason_stats[r]['losses'] += 1

    for r in reason_stats:
        s = reason_stats[r]
        s['wr'] = round(s['wins'] / (s['wins'] + s['losses']) * 100) if (s['wins'] + s['losses']) > 0 else 0
        s['pnl'] = round(s['pnl'], 2)

    # Per-wallet stats from trader_performance
    hl_conn = get_db()
    tp_rows = hl_conn.execute('''
        SELECT tp.wallet, tp.token, tp.status, tp.pnl_pct, tp.close_reason,
               tp.trade_id, t.score, t.pattern
        FROM trader_performance tp
        LEFT JOIN traders t ON tp.wallet = t.wallet
        ORDER BY tp.created_at DESC
    ''').fetchall()
    hl_conn.close()

    wallet_stats = {}
    for r in tp_rows:
        d = dict(r)
        w = d['wallet'] or 'unknown'
        if w not in wallet_stats:
            wallet_stats[w] = {
                'score': d.get('score', 0) or 0,
                'pattern': d.get('pattern', '?') or '?',
                'wins': 0, 'losses': 0, 'be': 0, 'open': 0,
                'total_pnl': 0, 'trades': []
            }
        ws = wallet_stats[w]
        pnl = float(d['pnl_pct'] or 0)
        ws['total_pnl'] += pnl
        if d['status'] == 'closed_win': ws['wins'] += 1
        elif d['status'] == 'closed_loss': ws['losses'] += 1
        elif d['status'] == 'closed_breakeven': ws['be'] += 1
        elif d['status'] == 'open': ws['open'] += 1
        ws['trades'].append({
            'id': d['trade_id'], 'token': d['token'], 'pnl': round(pnl, 2),
            'status': d['status'], 'reason': d['close_reason']
        })

    for w in wallet_stats:
        ws = wallet_stats[w]
        total = ws['wins'] + ws['losses']
        ws['wr'] = round(ws['wins'] / total * 100) if total > 0 else 0
        ws['total_pnl'] = round(ws['total_pnl'], 2)

    # Build output
    output = {
        'updated': datetime.now().isoformat(),
        'summary': {
            'total': len(parsed),
            'closed': len(closed),
            'open': len(open_trades),
            'wins': wins,
            'losses': losses,
            'win_rate': round(wins / (wins + losses) * 100) if (wins + losses) > 0 else 0,
            'total_pnl': round(total_pnl, 2),
            'total_usdt': round(total_usdt, 3),
        },
        'by_token': token_stats,
        'by_reason': reason_stats,
        'by_wallet': wallet_stats,
        'trades': parsed,
    }

    _atomic_write(output, OUTPUT_FILE)
    print(f"[copy_trader_api] Wrote {len(parsed)} trades to {OUTPUT_FILE}")
    return output


if __name__ == '__main__':
    generate_data()
