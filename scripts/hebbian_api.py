#!/usr/bin/env python3
"""hebbian_api.py — Generate JSON data for the Hebbian correlation dashboard.

Writes to /var/www/hermes/data/hebbian_data.json
Run via systemd timer or manually.
"""
import json, os, sqlite3, sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

CORRELATIONS_DB = "/root/.hermes/brain/correlations.db"
TRADE_LOG_DB = "/root/.hermes/brain/associative_memory.db"
OUTPUT = "/var/www/hermes/data/hebbian_data.json"


def generate():
    """Generate all Hebbian visualization data."""
    conn = sqlite3.connect(f"file:{CORRELATIONS_DB}?mode=ro", uri=True, timeout=10)
    conn.row_factory = sqlite3.Row

    data = {}

    # 1. Token chains for graph
    rows = conn.execute('''
        SELECT token_a, token_b, co_fires, win_rate, lift, confidence, avg_pnl_after_a
        FROM token_chains
        WHERE co_fires >= 3
        ORDER BY confidence * lift DESC
    ''').fetchall()
    data['chains'] = [
        {'a': r[0], 'b': r[1], 'n': r[2], 'wr': round(r[3], 3),
         'lift': round(r[4], 2), 'conf': round(r[5], 3), 'pnl': round(r[6], 4)}
        for r in rows
    ]

    # 2. Strong chains (for highlight)
    data['strong_chains'] = [
        c for c in data['chains']
        if c['lift'] >= 1.5 and c['n'] >= 5
    ][:30]

    # 3. Inverse chains (avoid)
    data['inverse_chains'] = [
        c for c in data['chains']
        if c['wr'] < 0.35 and c['n'] >= 5
    ][:15]

    # 4. Signal effectiveness
    rows = conn.execute('''
        SELECT token, signal, direction, trades, win_rate, confidence, avg_pnl
        FROM signal_effectiveness
        WHERE trades >= 3
        ORDER BY confidence * win_rate DESC
    ''').fetchall()
    data['signals'] = [
        {'token': r[0], 'signal': r[1], 'dir': r[2], 'n': r[3],
         'wr': round(r[4], 3), 'conf': round(r[5], 3), 'pnl': round(r[6], 4)}
        for r in rows
    ]

    # 5. Cadence (hourly heatmap)
    rows = conn.execute('''
        SELECT token, hour_dist, total_trades, peak_hour_utc
        FROM cadence
        WHERE total_trades >= 3
        ORDER BY total_trades DESC
    ''').fetchall()
    data['cadence'] = []
    for r in rows:
        try:
            hours = json.loads(r[1]) if r[1] else [0]*24
        except:
            hours = [0]*24
        data['cadence'].append({
            'token': r[0], 'hours': [round(h, 3) for h in hours],
            'n': r[2], 'peak': r[3]
        })

    # 6. Hub analysis (most connected)
    rows = conn.execute('''
        SELECT token_a, COUNT(*) as out_degree,
               AVG(win_rate) as avg_wr,
               AVG(lift) as avg_lift,
               SUM(CASE WHEN win_rate > 0.6 THEN 1 ELSE 0 END) as good_chains
        FROM token_chains
        WHERE co_fires >= 3
        GROUP BY token_a
        ORDER BY out_degree DESC
    ''').fetchall()
    data['hubs'] = [
        {'token': r[0], 'degree': r[1], 'avg_wr': round(r[2], 3),
         'avg_lift': round(r[3], 2), 'good': r[4]}
        for r in rows
    ][:20]

    # 7. Pump Loop (longest chain)
    data['pump_loop'] = {
        'chain': ['ME', 'GRIFFAIN', 'SKR', 'BSV', 'ASTER', 'CAKE', '0G', 'BCH', 'MORPHO', 'XMR'],
        'links': [],
    }
    for i in range(len(data['pump_loop']['chain']) - 1):
        a, b = data['pump_loop']['chain'][i], data['pump_loop']['chain'][i+1]
        r = conn.execute('''
            SELECT co_fires, win_rate, lift, confidence, avg_pnl_after_a
            FROM token_chains WHERE token_a=? AND token_b=?
        ''', (a, b)).fetchone()
        if r:
            data['pump_loop']['links'].append({
                'from': a, 'to': b, 'n': r[0],
                'wr': round(r[1], 3), 'lift': round(r[2], 2),
                'conf': round(r[3], 3), 'pnl': round(r[4], 4)
            })

    # Extended entry points
    data['pump_loop']['entries'] = [
        ('JUP', 'ME'), ('ONDO', 'FET'), ('FET', 'ASTER'),
        ('XMR', 'ASTER'), ('LINK', 'ME'), ('UNI', 'MORPHO')
    ]

    # 8. Stats
    data['stats'] = {
        'total_chains': conn.execute('SELECT COUNT(*) FROM token_chains').fetchone()[0],
        'total_signals': conn.execute('SELECT COUNT(*) FROM signal_effectiveness').fetchone()[0],
        'total_cadences': conn.execute('SELECT COUNT(*) FROM cadence').fetchone()[0],
        'tokens_covered': conn.execute('SELECT COUNT(DISTINCT token_a) FROM token_chains WHERE co_fires >= 3').fetchone()[0],
        'generated_at': datetime.now(timezone.utc).isoformat(),
    }

    conn.close()

    # Write atomically
    os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)
    fd, tmp = os.path.splitext(OUTPUT)
    tmp = OUTPUT + '.tmp'
    with open(tmp, 'w') as f:
        json.dump(data, f)
    os.replace(tmp, OUTPUT)

    print(f"Generated {OUTPUT}: {data['stats']}")
    return data


if __name__ == '__main__':
    generate()
