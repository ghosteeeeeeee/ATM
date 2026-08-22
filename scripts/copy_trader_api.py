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

    # Get all copy trades with more fields
    cur.execute('''
        SELECT id, token, direction, entry_price, hl_entry_price, pnl_pct, pnl_usdt,
               close_reason, _signal_metadata, open_time, close_time, status, leverage,
               signal, confidence, amount_usdt, hl_notional_usdt,
               mfe_pct, mae_pct, highest_price, lowest_price
        FROM trades
        WHERE signal LIKE '%hl_copy_trader%'
        ORDER BY id
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

        # MFE/MAE
        mfe = float(d['mfe_pct'] or 0)
        mae = float(d['mae_pct'] or 0)

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
            'amount_usdt': float(d['amount_usdt'] or 11),
            'notional': float(d['hl_notional_usdt'] or d['amount_usdt'] or 11),
            'mfe_pct': round(mfe, 2),
            'mae_pct': round(mae, 2),
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
    avg_hold = sum(t['hold_hours'] for t in closed) / len(closed) if closed else 0
    avg_notional = sum(t['notional'] for t in parsed) / len(parsed) if parsed else 0

    # Equity curve (cumulative PnL)
    equity_curve = []
    cum_pnl = 0
    for t in closed:
        cum_pnl += t['pnl_usdt']
        equity_curve.append({
            'id': t['id'],
            'pnl': round(cum_pnl, 3),
            'token': t['token'],
            'time': t['close_time'],
        })

    # Win/loss streaks
    max_win_streak = 0
    max_loss_streak = 0
    current_streak = 0
    streak_type = None
    for t in closed:
        if t['pnl_pct'] > 0.05:
            if streak_type == 'win':
                current_streak += 1
            else:
                current_streak = 1
                streak_type = 'win'
            max_win_streak = max(max_win_streak, current_streak)
        elif t['pnl_pct'] < -0.05:
            if streak_type == 'loss':
                current_streak += 1
            else:
                current_streak = 1
                streak_type = 'loss'
            max_loss_streak = max(max_loss_streak, current_streak)
        else:
            streak_type = None
            current_streak = 0

    # Per-token stats
    token_stats = {}
    for t in closed:
        tok = t['token']
        if tok not in token_stats:
            token_stats[tok] = {'wins': 0, 'losses': 0, 'pnl': 0, 'usdt': 0, 'count': 0, 'total_hold': 0}
        token_stats[tok]['count'] += 1
        token_stats[tok]['pnl'] += t['pnl_pct']
        token_stats[tok]['usdt'] += t['pnl_usdt']
        token_stats[tok]['total_hold'] += t['hold_hours']
        if t['pnl_pct'] > 0.05: token_stats[tok]['wins'] += 1
        elif t['pnl_pct'] < -0.05: token_stats[tok]['losses'] += 1

    for tok in token_stats:
        s = token_stats[tok]
        s['wr'] = round(s['wins'] / (s['wins'] + s['losses']) * 100) if (s['wins'] + s['losses']) > 0 else 0
        s['pnl'] = round(s['pnl'], 2)
        s['usdt'] = round(s['usdt'], 3)
        s['avg_hold'] = round(s['total_hold'] / s['count'], 1) if s['count'] > 0 else 0
        del s['total_hold']

    # Exit reason stats
    reason_stats = {}
    for t in closed:
        r = t['close_reason']
        if r not in reason_stats:
            reason_stats[r] = {'wins': 0, 'losses': 0, 'pnl': 0, 'count': 0, 'total_hold': 0}
        reason_stats[r]['count'] += 1
        reason_stats[r]['pnl'] += t['pnl_pct']
        reason_stats[r]['total_hold'] += t['hold_hours']
        if t['pnl_pct'] > 0.05: reason_stats[r]['wins'] += 1
        elif t['pnl_pct'] < -0.05: reason_stats[r]['losses'] += 1

    for r in reason_stats:
        s = reason_stats[r]
        s['wr'] = round(s['wins'] / (s['wins'] + s['losses']) * 100) if (s['wins'] + s['losses']) > 0 else 0
        s['pnl'] = round(s['pnl'], 2)
        s['avg_hold'] = round(s['total_hold'] / s['count'], 1) if s['count'] > 0 else 0
        del s['total_hold']

    # Per-wallet stats from trader_performance + pro trader fills
    hl_conn = get_db()
    tp_rows = hl_conn.execute('''
        SELECT tp.wallet, tp.token, tp.status, tp.pnl_pct, tp.close_reason,
               tp.trade_id, t.score, t.pattern
        FROM trader_performance tp
        LEFT JOIN traders t ON tp.wallet = t.wallet
        ORDER BY tp.created_at DESC
    ''').fetchall()

    # Get pro trader's own HYPE fills
    pro_fills = hl_conn.execute('''
        SELECT wallet, coin, closed_pnl, sz, px, is_open
        FROM trader_fills
        WHERE coin = 'HYPE'
    ''').fetchall()

    # Get all tracked traders (leaderboard)
    all_traders = hl_conn.execute('''
        SELECT wallet, score, pnl_all_time, win_rate, trade_count, pattern,
               copy_weight, copy_trades, copy_wins, copy_pnl, last_updated
        FROM traders
        WHERE active = 1
        ORDER BY score DESC
    ''').fetchall()
    hl_conn.close()

    # Build leaderboard summary
    leaderboard = []
    for r in all_traders:
        d = dict(r)
        leaderboard.append({
            'wallet': d['wallet'],
            'score': round(float(d['score'] or 0), 1),
            'pnl': round(float(d['pnl_all_time'] or 0), 2),
            'wr': round(float(d['win_rate'] or 0) * 100),
            'trades': int(d['trade_count'] or 0),
            'pattern': d['pattern'] or '?',
            'copy_trades': int(d['copy_trades'] or 0),
            'copy_wr': round(float(d['copy_wins'] or 0) / max(float(d['copy_trades'] or 1), 1) * 100),
            'copy_pnl': round(float(d['copy_pnl'] or 0), 2),
            'account_value': round(float(d.get('account_value', 0) or 0), 2),
            'last_updated': d['last_updated'],
        })

    # Last leaderboard refresh
    last_leaderboard_file = os.path.join('/root/.hermes/data', 'hl_copy_last_leaderboard.txt')
    try:
        with open(last_leaderboard_file) as f:
            last_leaderboard_ts = int(f.read().strip())
    except:
        last_leaderboard_ts = 0

    # Compute pro trader HYPE stats
    pro_hype = {}
    for r in pro_fills:
        d = dict(r)
        w = d['wallet']
        if w not in pro_hype:
            pro_hype[w] = {'wins': 0, 'losses': 0, 'total_pnl': 0, 'count': 0, 'sizes': []}
        ph = pro_hype[w]
        pnl = float(d['closed_pnl'] or 0)
        if pnl != 0:
            ph['count'] += 1
            ph['total_pnl'] += pnl
            if pnl > 0: ph['wins'] += 1
            else: ph['losses'] += 1
        ph['sizes'].append(float(d['sz'] or 0))

    wallet_stats = {}
    for r in tp_rows:
        d = dict(r)
        w = d['wallet'] or 'unknown'
        if w not in wallet_stats:
            wallet_stats[w] = {
                'score': d.get('score', 0) or 0,
                'pattern': d.get('pattern', '?') or '?',
                'wins': 0, 'losses': 0, 'be': 0, 'open': 0,
                'total_pnl': 0, 'trades': [], 'sizes': []
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

    # Enrich wallet stats with position sizes and pro trader data
    for w in wallet_stats:
        ws = wallet_stats[w]
        total = ws['wins'] + ws['losses']
        ws['wr'] = round(ws['wins'] / total * 100) if total > 0 else 0
        ws['total_pnl'] = round(ws['total_pnl'], 2)

        # Get position sizes from our trades
        our_sizes = [t['notional'] for t in parsed if t['trader_wallet'] == w]
        ws['avg_position'] = round(sum(our_sizes) / len(our_sizes), 2) if our_sizes else 0
        ws['total_volume'] = round(sum(our_sizes), 2)

        # Pro trader's own HYPE performance
        ph = pro_hype.get(w, {})
        ws['pro_hype_wr'] = round(ph.get('wins', 0) / (ph.get('wins', 0) + ph.get('losses', 0)) * 100) if (ph.get('wins', 0) + ph.get('losses', 0)) > 0 else 0
        ws['pro_hype_pnl'] = round(ph.get('total_pnl', 0), 2)
        ws['pro_hype_trades'] = ph.get('count', 0)
        pro_sizes = ph.get('sizes', [])
        ws['pro_avg_position'] = round(sum(pro_sizes) / len(pro_sizes), 2) if pro_sizes else 0

    # Time-of-day analysis
    hour_stats = {}
    for t in closed:
        if t['open_time']:
            try:
                h = int(t['open_time'][11:13])
            except:
                continue
            if h not in hour_stats:
                hour_stats[h] = {'wins': 0, 'losses': 0, 'pnl': 0, 'count': 0}
            hour_stats[h]['count'] += 1
            hour_stats[h]['pnl'] += t['pnl_pct']
            if t['pnl_pct'] > 0.05: hour_stats[h]['wins'] += 1
            elif t['pnl_pct'] < -0.05: hour_stats[h]['losses'] += 1

    for h in hour_stats:
        s = hour_stats[h]
        s['wr'] = round(s['wins'] / (s['wins'] + s['losses']) * 100) if (s['wins'] + s['losses']) > 0 else 0
        s['pnl'] = round(s['pnl'], 2)

    # Hold time distribution
    hold_buckets = {'0-0.5h': 0, '0.5-1h': 0, '1-2h': 0, '2-4h': 0, '4-8h': 0, '8h+': 0}
    hold_wr = {'0-0.5h': [0, 0], '0.5-1h': [0, 0], '1-2h': [0, 0], '2-4h': [0, 0], '4-8h': [0, 0], '8h+': [0, 0]}
    for t in closed:
        h = t['hold_hours']
        if h < 0.5: bucket = '0-0.5h'
        elif h < 1: bucket = '0.5-1h'
        elif h < 2: bucket = '1-2h'
        elif h < 4: bucket = '2-4h'
        elif h < 8: bucket = '4-8h'
        else: bucket = '8h+'
        hold_buckets[bucket] += 1
        if t['pnl_pct'] > 0.05: hold_wr[bucket][0] += 1
        elif t['pnl_pct'] < -0.05: hold_wr[bucket][1] += 1

    hold_dist = {}
    for bucket in hold_buckets:
        w, l = hold_wr[bucket]
        hold_dist[bucket] = {
            'count': hold_buckets[bucket],
            'wr': round(w / (w + l) * 100) if (w + l) > 0 else 0
        }

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
            'avg_hold': round(avg_hold, 1),
            'avg_notional': round(avg_notional, 2),
            'max_win_streak': max_win_streak,
            'max_loss_streak': max_loss_streak,
            'tracked_traders': len(leaderboard),
            'last_leaderboard_refresh': datetime.fromtimestamp(last_leaderboard_ts).isoformat() if last_leaderboard_ts else None,
        },
        'by_token': token_stats,
        'by_reason': reason_stats,
        'by_wallet': wallet_stats,
        'by_hour': hour_stats,
        'hold_dist': hold_dist,
        'equity_curve': equity_curve,
        'leaderboard': leaderboard[:30],  # Top 30 by score
        'trades': list(reversed(parsed)),  # newest first for display
    }

    _atomic_write(output, OUTPUT_FILE)
    print(f"[copy_trader_api] Wrote {len(parsed)} trades to {OUTPUT_FILE}")
    return output


if __name__ == '__main__':
    generate_data()
