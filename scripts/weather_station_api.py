#!/usr/bin/env python3
"""
Weather Station API — Generates JSON for the HTML dashboard.
Writes to /var/www/hermes/data/weather_station.json
"""

import sqlite3
import json
import os
import sys
from datetime import datetime, timedelta
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paths import HERMES_DATA, WWW_DATA

DB_PATH = os.path.join(HERMES_DATA, 'signals_hermes_runtime.db')
OUTPUT = os.path.join(WWW_DATA, 'weather_station.json')

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def analyze_tide(conn):
    """Tide direction — market flow balance."""
    result = {}
    for label, hours in [('24h', 24), ('7d', 168), ('30d', 720)]:
        cutoff = f"-{hours} hours"
        row = conn.execute("""
            SELECT
                SUM(CASE WHEN direction = 'LONG' THEN 1 ELSE 0 END) as longs,
                SUM(CASE WHEN direction = 'SHORT' THEN 1 ELSE 0 END) as shorts,
                COUNT(*) as total
            FROM signals WHERE created_at >= datetime('now', ?)
        """, (cutoff,)).fetchone()
        if row and row['total'] > 0:
            lp = 100.0 * row['longs'] / row['total']
            sp = 100.0 * row['shorts'] / row['total']
            imb = abs(lp - 50) / 50
            result[label] = {
                'long_pct': round(lp, 1),
                'short_pct': round(sp, 1),
                'imbalance': round(imb, 3),
                'total': row['total'],
            }
    return result

def analyze_waves(conn):
    """Wave height — signal intensity over time."""
    hourly = conn.execute("""
        SELECT
            strftime('%Y-%m-%d %H:00:00', created_at) as hour,
            COUNT(*) as count,
            COUNT(DISTINCT token) as tokens,
            AVG(confidence) as avg_conf,
            SUM(CASE WHEN direction = 'LONG' THEN 1 ELSE 0 END) * 1.0 / COUNT(*) as long_ratio
        FROM signals
        WHERE created_at >= datetime('now', '-7 days')
        GROUP BY hour ORDER BY hour
    """).fetchall()
    if not hourly:
        return {'hours': [], 'avg': 0, 'peak': 0, 'cv': 0}
    counts = [r['count'] for r in hourly]
    avg = sum(counts) / len(counts)
    variance = sum((x - avg) ** 2 for x in counts) / len(counts) if avg > 0 else 0
    cv = (variance ** 0.5) / avg if avg > 0 else 0
    return {
        'hours': [{'hour': r['hour'], 'count': r['count'], 'tokens': r['tokens'],
                    'long_ratio': round(r['long_ratio'] * 100, 1) if r['long_ratio'] else 50}
                  for r in hourly],
        'avg': round(avg, 1),
        'peak': max(counts),
        'low': min(counts),
        'cv': round(cv, 2),
    }

def analyze_wind(conn):
    """Wind — momentum and velocity distribution."""
    speeds = conn.execute("SELECT * FROM token_speeds").fetchall()
    if not speeds:
        return {}
    velocities = [abs(r['price_velocity_5m']) for r in speeds if r['price_velocity_5m'] is not None]
    accels = [r['price_acceleration'] for r in speeds if r['price_acceleration'] is not None]
    stale = sum(1 for r in speeds if r['is_stale'])
    phases = defaultdict(int)
    speed_buckets = {'fast': 0, 'mid': 0, 'slow': 0}
    for r in speeds:
        if r['wave_phase']:
            phases[r['wave_phase']] += 1
        pct = r['speed_percentile'] or 50
        if pct >= 80: speed_buckets['fast'] += 1
        elif pct < 20: speed_buckets['slow'] += 1
        else: speed_buckets['mid'] += 1

    sorted_vel = sorted(velocities) if velocities else [0]
    n = len(sorted_vel)
    return {
        'sustained': round(sorted_vel[n // 2], 4),
        'gusts': round(sorted_vel[int(n * 0.95)], 4) if n > 1 else 0,
        'avg_velocity': round(sum(velocities) / len(velocities), 4) if velocities else 0,
        'avg_accel': round(sum(accels) / len(accels), 4) if accels else 0,
        'stale': stale,
        'total': len(speeds),
        'speed_buckets': speed_buckets,
        'phases': dict(phases),
    }

def analyze_sea_state(conn):
    """Sea state — overall health from outcomes."""
    outcomes = conn.execute("""
        SELECT DATE(created_at) as day, COUNT(*) as trades,
               SUM(is_win) as wins, SUM(pnl_pct) as pnl
        FROM signal_outcomes
        WHERE created_at >= datetime('now', '-14 days')
        GROUP BY day ORDER BY day
    """).fetchall()
    if not outcomes:
        return {}
    total_t = sum(r['trades'] for r in outcomes)
    total_w = sum(r['wins'] for r in outcomes)
    total_p = sum(r['pnl'] for r in outcomes)
    wr = 100.0 * total_w / total_t if total_t else 0
    daily = [{'day': r['day'], 'trades': r['trades'], 'wins': r['wins'],
              'pnl': round(r['pnl'], 2), 'winrate': round(100.0 * r['wins'] / r['trades'], 1) if r['trades'] else 0}
             for r in outcomes]
    return {
        'winrate': round(wr, 1),
        'total_pnl': round(total_p, 2),
        'total_trades': total_t,
        'good_days': sum(1 for r in outcomes if r['pnl'] > 0),
        'bad_days': sum(1 for r in outcomes if r['pnl'] <= 0),
        'daily': daily,
    }

def analyze_signals(conn):
    """Signal type performance breakdown."""
    rows = conn.execute("""
        SELECT signal_type, COUNT(*) as trades, SUM(is_win) as wins,
               ROUND(SUM(pnl_pct), 2) as total_pnl, ROUND(AVG(pnl_pct), 2) as avg_pnl,
               ROUND(AVG(confidence), 1) as avg_conf
        FROM signal_outcomes GROUP BY signal_type HAVING trades >= 5
        ORDER BY total_pnl DESC
    """).fetchall()
    return [{'type': r['signal_type'], 'trades': r['trades'], 'wins': r['wins'],
             'winrate': round(100.0 * r['wins'] / r['trades'], 1) if r['trades'] else 0,
             'total_pnl': r['total_pnl'], 'avg_pnl': r['avg_pnl'], 'avg_conf': r['avg_conf']}
            for r in rows]

def analyze_tokens(conn):
    """Token regime map — reef, sandbar, deep water."""
    rows = conn.execute("""
        SELECT token, COUNT(*) as trades, SUM(is_win) as wins,
               ROUND(SUM(pnl_pct), 2) as total_pnl, ROUND(AVG(pnl_pct), 2) as avg_pnl
        FROM signal_outcomes GROUP BY token HAVING trades >= 5
        ORDER BY total_pnl DESC
    """).fetchall()
    reef, sandbar, deep = [], [], []
    for r in rows:
        t = {'token': r['token'], 'trades': r['trades'], 'wins': r['wins'],
             'winrate': round(100.0 * r['wins'] / r['trades'], 1) if r['trades'] else 0,
             'total_pnl': r['total_pnl'], 'avg_pnl': r['avg_pnl']}
        if t['winrate'] > 55 and t['avg_pnl'] > 0.1:
            reef.append(t)
        elif t['winrate'] < 35 or t['avg_pnl'] < -0.5:
            deep.append(t)
        else:
            sandbar.append(t)
    return {'reef': reef, 'sandbar': sandbar[:20], 'deep': deep[:20]}

def analyze_time(conn):
    """Hourly and daily performance patterns."""
    hourly = conn.execute("""
        SELECT CAST(strftime('%H', created_at) AS INTEGER) as hour,
               COUNT(*) as trades, SUM(is_win) as wins, ROUND(SUM(pnl_pct), 2) as pnl
        FROM signal_outcomes GROUP BY hour ORDER BY hour
    """).fetchall()
    daily = conn.execute("""
        SELECT CASE CAST(strftime('%w', created_at) AS INTEGER)
            WHEN 0 THEN 'Sun' WHEN 1 THEN 'Mon' WHEN 2 THEN 'Tue' WHEN 3 THEN 'Wed'
            WHEN 4 THEN 'Thu' WHEN 5 THEN 'Fri' WHEN 6 THEN 'Sat' END as day,
            COUNT(*) as trades, SUM(is_win) as wins, ROUND(SUM(pnl_pct), 2) as pnl
        FROM signal_outcomes GROUP BY strftime('%w', created_at) ORDER BY strftime('%w', created_at)
    """).fetchall()
    return {
        'hourly': [{'hour': r['hour'], 'trades': r['trades'], 'wins': r['wins'],
                     'pnl': r['pnl'], 'winrate': round(100.0 * r['wins'] / r['trades'], 1) if r['trades'] else 0}
                    for r in hourly],
        'weekly': [{'day': r['day'], 'trades': r['trades'], 'wins': r['wins'],
                     'pnl': r['pnl'], 'winrate': round(100.0 * r['wins'] / r['trades'], 1) if r['trades'] else 0}
                    for r in daily],
    }

def analyze_lightning(conn):
    """Extreme events — crashes and pumps."""
    extremes = conn.execute("""
        SELECT token, direction, signal_type, pnl_pct, confidence, created_at
        FROM signal_outcomes WHERE ABS(pnl_pct) > 2.0 ORDER BY created_at
    """).fetchall()
    crash_tokens = conn.execute("""
        SELECT token, COUNT(*) as trades, SUM(is_win) as wins,
               ROUND(SUM(pnl_pct), 2) as total_pnl, ROUND(MIN(pnl_pct), 2) as worst
        FROM signal_outcomes GROUP BY token HAVING trades >= 3
        ORDER BY total_pnl ASC LIMIT 10
    """).fetchall()
    pump_tokens = conn.execute("""
        SELECT token, COUNT(*) as trades, SUM(is_win) as wins,
               ROUND(SUM(pnl_pct), 2) as total_pnl, ROUND(MAX(pnl_pct), 2) as best
        FROM signal_outcomes GROUP BY token HAVING trades >= 3
        ORDER BY total_pnl DESC LIMIT 10
    """).fetchall()
    return {
        'extreme_count': len(extremes),
        'big_wins': sum(1 for e in extremes if e['pnl_pct'] > 0),
        'big_losses': sum(1 for e in extremes if e['pnl_pct'] < 0),
        'crash_tokens': [{'token': r['token'], 'trades': r['trades'], 'wins': r['wins'],
                          'total_pnl': r['total_pnl'], 'worst': r['worst']} for r in crash_tokens],
        'pump_tokens': [{'token': r['token'], 'trades': r['trades'], 'wins': r['wins'],
                         'total_pnl': r['total_pnl'], 'best': r['best']} for r in pump_tokens],
    }

def analyze_category_performance(conn):
    """Signal categories — which families work."""
    categories = {
        'Copy Trader': ['copy', 'hl_copy', 'coin_tracker_hot', 'ct-hot'],
        'Bollinger': ['bb_bounce', 'bollinger', 'squeeze'],
        'Momentum': ['momentum', 'fast_momentum', 'accel_300', 'inverse_accel', 'phase_accel'],
        'Trend': ['ma_cross', 'ma_100', 'ema20_50', 'ema9_sma20', 'ma100', 'ma300'],
        'Z-Score': ['mtp_zscore', 'zscore', 'hzscore'],
        'Pattern': ['wyckoff', 'engulfing', 'tl_break', 'range_breakout', 'range_finder', 'hh_hl'],
        'Exhaustion': ['exhaustion', 'return_exhaustion', 'spike_exhaustion'],
        'Wave': ['wave_catcher'],
    }
    rows = conn.execute("""
        SELECT signal_type, COUNT(*) as trades, SUM(is_win) as wins, ROUND(SUM(pnl_pct), 2) as pnl
        FROM signal_outcomes GROUP BY signal_type
    """).fetchall()
    cat_stats = defaultdict(lambda: {'trades': 0, 'wins': 0, 'pnl': 0})
    for r in rows:
        sig = r['signal_type'].lower()
        matched = False
        for cat, kws in categories.items():
            if any(kw in sig for kw in kws):
                cat_stats[cat]['trades'] += r['trades']
                cat_stats[cat]['wins'] += r['wins']
                cat_stats[cat]['pnl'] += r['pnl']
                matched = True
                break
        if not matched:
            cat_stats['Other']['trades'] += r['trades']
            cat_stats['Other']['wins'] += r['wins']
            cat_stats['Other']['pnl'] += r['pnl']
    result = []
    for cat, s in sorted(cat_stats.items(), key=lambda x: -x[1]['pnl']):
        if s['trades'] > 0:
            result.append({'category': cat, 'trades': s['trades'], 'wins': s['wins'],
                           'winrate': round(100.0 * s['wins'] / s['trades'], 1),
                           'pnl': round(s['pnl'], 2)})
    return result

def main():
    conn = get_db()
    try:
        data = {
            'generated': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC'),
            'tide': analyze_tide(conn),
            'waves': analyze_waves(conn),
            'wind': analyze_wind(conn),
            'sea_state': analyze_sea_state(conn),
            'signals': analyze_signals(conn),
            'tokens': analyze_tokens(conn),
            'time': analyze_time(conn),
            'lightning': analyze_lightning(conn),
            'categories': analyze_category_performance(conn),
        }
        os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)
        with open(OUTPUT, 'w') as f:
            json.dump(data, f, indent=2)
        print(f"Written to {OUTPUT} ({os.path.getsize(OUTPUT)} bytes)")
    finally:
        conn.close()

if __name__ == '__main__':
    main()
