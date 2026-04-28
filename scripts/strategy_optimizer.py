#!/usr/bin/env python3
"""
strategy_optimizer.py — A/B testing and self-improvement for Hermes trading.
Tracks parameter variants, evaluates win rates, evolves strategy over time.
"""
import sys, json, sqlite3, time
from datetime import datetime
from collections import defaultdict

sys.path.insert(0, '/root/.hermes/scripts')

from paths import *
BRAIN_DB = "host=/var/run/postgresql dbname=brain user=postgres password=postgres"
DB_PATH = '/root/.openclaw/workspace/data/signals.db'

# Default tracked parameters and their variants
DEFAULT_PARAMS = {
    'rsi_threshold_low':   {'current': 35, 'variants': [30, 35, 40], 'unit': ''},
    'rsi_threshold_high':  {'current': 65, 'variants': [60, 65, 70], 'unit': ''},
    'zscore_threshold':    {'current': 2.0, 'variants': [1.5, 2.0, 2.5], 'unit': 'σ'},
    'stop_loss_pct':       {'current': 3.0, 'variants': [2.0, 3.0, 5.0], 'unit': '%'},
    'take_profit_pct':    {'current': 8.0, 'variants': [6.0, 8.0, 12.0], 'unit': '%'},
    'max_leverage':       {'current': 10, 'variants': [5, 10, 20], 'unit': 'x'},
    'min_confidence':      {'current': 60, 'variants': [55, 60, 70], 'unit': '%'},
}


def get_pg_conn():
    import psycopg2
    return psycopg2.connect(BRAIN_DB)


def init_tables():
    """Create A/B tracking tables in SQLite."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS strategy_params (
            param_name TEXT PRIMARY KEY,
            current_value REAL,
            updated_at TEXT
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS ab_tests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            param_name TEXT NOT NULL,
            param_value REAL NOT NULL,
            token TEXT,
            pnl_pct REAL,
            won INTEGER,
            trade_id INTEGER,
            closed_at TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS active_trades (
            trade_id INTEGER PRIMARY KEY,
            token TEXT,
            params_used TEXT,  -- JSON
            opened_at TEXT
        )
    ''')
    conn.commit()
    conn.close()

    # Seed default params if not set
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    for name, cfg in DEFAULT_PARAMS.items():
        c.execute('SELECT 1 FROM strategy_params WHERE param_name=?', (name,))
        if not c.fetchone():
            c.execute(
                'INSERT INTO strategy_params (param_name, current_value, updated_at) VALUES (?, ?, ?)',
                (name, cfg['current'], datetime.now().isoformat())
            )
    conn.commit()
    conn.close()


def get_active_params():
    """Get current best params from DB or defaults."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    params = {}
    for name in DEFAULT_PARAMS:
        c.execute('SELECT current_value FROM strategy_params WHERE param_name=?', (name,))
        row = c.fetchone()
        params[name] = row[0] if row else DEFAULT_PARAMS[name]['current']
    conn.close()
    return params


def set_param(name, value):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        'INSERT OR REPLACE INTO strategy_params (param_name, current_value, updated_at) VALUES (?, ?, ?)',
        (name, value, datetime.now().isoformat())
    )
    conn.commit()
    conn.close()


def record_trade_open(trade_id, token, params):
    """Record that a trade opened with specific param values."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        'INSERT OR REPLACE INTO active_trades (trade_id, token, params_used, opened_at) VALUES (?, ?, ?, ?)',
        (trade_id, token, json.dumps(params), datetime.now().isoformat())
    )
    conn.commit()
    conn.close()


def record_trade_result(trade_id, pnl_pct):
    """Record trade result and update A/B test data."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT token, params_used FROM active_trades WHERE trade_id=?', (trade_id,))
    row = c.fetchone()
    if not row:
        conn.close()
        return
    token, params_json = row
    params = json.loads(params_json) if params_json else {}

    won = 1 if pnl_pct > 0 else 0
    now = datetime.now().isoformat()

    for name, val in params.items():
        c.execute(
            'INSERT INTO ab_tests (param_name, param_value, token, pnl_pct, won, trade_id, closed_at) VALUES (?, ?, ?, ?, ?, ?, ?)',
            (name, val, token, pnl_pct, won, trade_id, now)
        )

    c.execute('DELETE FROM active_trades WHERE trade_id=?', (trade_id,))
    conn.commit()
    conn.close()


def evaluate_results(min_trades=5):
    """Evaluate A/B results and suggest/implement param improvements."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    recommendations = []

    for name, cfg in DEFAULT_PARAMS.items():
        c.execute('''
            SELECT param_value, COUNT(*) as n, SUM(won) as wins, AVG(pnl_pct) as avg_pnl
            FROM ab_tests
            WHERE param_name=? AND won IS NOT NULL
            GROUP BY param_value
            HAVING COUNT(*) >= ?
            ORDER BY avg_pnl DESC
        ''', (name, min_trades))
        rows = c.fetchall()
        if len(rows) < 2:
            continue

        best_value = max(rows, key=lambda r: (r[1] >= min_trades, r[3] if r[3] else 0))
        best_val = best_value[0]
        best_wr = (best_value[2] or 0) / max(best_value[1], 1) * 100
        best_pnl = best_value[3] or 0

        current = get_active_params().get(name, cfg['current'])
        if best_val != current and best_pnl > 0:
            recommendations.append({
                'param': name,
                'current': current,
                'new': best_val,
                'unit': cfg['unit'],
                'win_rate': best_wr,
                'avg_pnl': best_pnl,
                'variant_count': len(rows)
            })

    conn.close()
    return recommendations


def apply_recommendations(recommendations):
    """Apply winning param changes to the strategy."""
    applied = []
    for rec in recommendations:
        if rec['avg_pnl'] > 0.5:  # Only apply if meaningful positive pnl
            set_param(rec['param'], rec['new'])
            applied.append(rec)
    return applied


def get_closed_trades(since_hours=24):
    """Get closed Hermes trades from brain DB."""
    try:
        conn = get_pg_conn()
        cur = conn.cursor()
        cur.execute('''
            SELECT id, token, direction, pnl_pct, signal, confidence, leverage,
                   stop_loss, target, entry_price, open_time, close_time
            FROM trades
            WHERE server='Hermes' AND status='closed'
            AND close_time > NOW() - INTERVAL '%s hours'
            ORDER BY close_time DESC
        ''', (since_hours,))
        cols = [d[0] for d in cur.description]
        rows = [dict(zip(cols, r)) for r in cur.fetchall()]
        cur.close()
        conn.close()
        return rows
    except Exception as e:
        print(f'PG error: {e}')
        return []


def get_open_trade_ids():
    """Get IDs of currently open trades."""
    try:
        conn = get_pg_conn()
        cur = conn.cursor()
        cur.execute("SELECT id FROM trades WHERE server='Hermes' AND status='open'")
        ids = [r[0] for r in cur.fetchall()]
        cur.close()
        conn.close()
        return set(ids)
    except:
        return set()


def sync_active_trades():
    """Remove stale entries from active_trades for trades that closed."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT trade_id FROM active_trades')
    stale = [r[0] for r in c.fetchall()]
    open_ids = get_open_trade_ids()
    closed = [t for t in stale if t not in open_ids]
    for tid in closed:
        c.execute('DELETE FROM active_trades WHERE trade_id=?', (tid,))
    conn.commit()
    removed = c.rowcount
    conn.close()
    return removed


def run():
    init_tables()
    params = get_active_params()

    # Sync: remove closed trades from active_trades
    removed = sync_active_trades()

    # Get closed trades and record results
    closed = get_closed_trades(since_hours=24 * 7)  # last week
    fresh = [t for t in closed if t.get('pnl_pct') is not None]

    recorded = 0
    for t in fresh:
        if t['pnl_pct'] != 0:  # Skip the 0-pnl placeholder trades
            record_trade_result(t['id'], t['pnl_pct'])
            recorded += 1

    # Evaluate
    recommendations = evaluate_results(min_trades=3)
    applied = apply_recommendations(recommendations)

    total_trades = len(fresh)
    winners = sum(1 for t in fresh if t['pnl_pct'] > 0)
    avg_pnl = sum(t['pnl_pct'] for t in fresh) / max(len(fresh), 1)

    print(f'=== Strategy Optimizer ===')
    print(f'  Active params: {len(params)} tracked | {total_trades} closed trades this week | {winners} wins')
    if fresh:
        print(f'  Avg PnL: {avg_pnl:+.2f}% | Win rate: {winners/max(len(fresh),1)*100:.0f}%')
    if removed:
        print(f'  Synced: removed {removed} stale active trade records')
    if applied:
        for r in applied:
            print(f'  OPTIMIZED: {r["param"]} {r["current"]}{r["unit"]} → {r["new"]}{r["unit"]} (win rate: {r["win_rate"]:.0f}%, avg pnl: {r["avg_pnl"]:+.2f}%)')
    elif recommendations:
        print(f'  {len(recommendations)} improvements found (need more data to apply)')
    else:
        print(f'  No parameter changes needed yet')


if __name__ == '__main__':
    run()
