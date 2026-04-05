#!/usr/bin/env python3
"""
ab_learner.py — Closes the self-improvement loop.

Run this after trades close to:
  1. Populate trade_patterns from completed trades (learned SL/TP adjustments)
  2. Score which token regimes, market conditions, and time-of-day work best
  3. Write insights back so get_learned_adjustments() in ai-decider can use them

The pipeline: trade_patterns → get_learned_adjustments() → bias toward winning configs
"""
import json, os, sys, psycopg2
from datetime import datetime, timedelta
from collections import defaultdict

BRAIN_DB = {
    'host': '/var/run/postgresql', 'dbname': 'brain',
    'user': 'postgres', 'password': 'postgres'
}
TRADE_PATTERNS_FILE = '/var/www/hermes/data/trade_patterns.json'
os.makedirs(os.path.dirname(TRADE_PATTERNS_FILE), exist_ok=True)


def log(msg):
    print(f'{datetime.now().strftime("%Y-%m-%d %H:%M:%S")} [ab_learner] {msg}')


def _db_conn():
    return psycopg2.connect(**BRAIN_DB)


def get_closed_trades(since_hours=168):
    """Fetch trades closed in the last N hours with their A/B metadata."""
    conn = _db_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT
            t.id, t.token, t.direction, t.entry_price, t.exit_price,
            t.pnl_pct, t.pnl_usdt, t.sl_distance, t.experiment,
            t.created_at, t.close_time
        FROM trades t
        WHERE t.status = 'closed'
          AND t.close_time IS NOT NULL
          AND t.close_time >= NOW() - (%s || ' hours')::interval
          AND t.sl_distance IS NOT NULL
        ORDER BY t.close_time DESC
    """, (str(since_hours),))
    rows = cur.fetchall()
    cur.close(); conn.close()
    return rows


def compute_token_stats():
    """
    Aggregate per-token performance: which tokens give best win rate,
    average pnl, and which SL distances work best per token.
    """
    conn = _db_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT
            token, direction,
            COUNT(*) as trades,
            SUM(CASE WHEN pnl_usdt > 0 THEN 1 ELSE 0 END) as wins,
            AVG(pnl_pct) as avg_pnl,
            AVG(pnl_usdt) as avg_usdt,
            sl_distance,
            COUNT(DISTINCT sl_distance) as unique_sl_count
        FROM trades
        WHERE status = 'closed'
          AND close_time IS NOT NULL
          AND pnl_pct IS NOT NULL
          AND sl_distance IS NOT NULL
          AND sl_distance > 0
        GROUP BY token, direction, sl_distance
        HAVING COUNT(*) >= 2
        ORDER BY token, avg_pnl DESC
    """)
    rows = cur.fetchall()
    cur.close(); conn.close()

    patterns = {}
    for (token, direction, trades, wins, avg_pnl,
         avg_usdt, sl_dist, unique_sl) in rows:
        win_rate = (wins / trades * 100) if trades > 0 else 0
        key = f"{token}_{direction}"
        if key not in patterns:
            patterns[key] = {
                'token': token,
                'direction': direction,
                'sl_distances': [],
            }
        patterns[key]['sl_distances'].append({
            'sl_distance': float(sl_dist),
            'trades': int(trades),
            'wins': int(wins),
            'win_rate': round(win_rate, 1),
            'avg_pnl': round(float(avg_pnl), 3),
            'avg_usdt': round(float(avg_usdt), 2),
        })
        # Keep only the best SL for this token+dir
        patterns[key]['sl_distances'].sort(key=lambda x: x['win_rate'], reverse=True)

    return patterns


def compute_sl_learnings():
    """
    Global SL distance analysis: which SL distances have highest win rates overall.
    Returns a dict: {sl_distance: {trades, wins, win_rate, avg_pnl}}
    """
    conn = _db_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT
            sl_distance,
            COUNT(*) as trades,
            SUM(CASE WHEN pnl_usdt > 0 THEN 1 ELSE 0 END) as wins,
            AVG(pnl_pct) as avg_pnl,
            STDDEV(pnl_pct) as stddev_pnl,
            MIN(pnl_pct) as worst,
            MAX(pnl_pct) as best
        FROM trades
        WHERE status = 'closed'
          AND close_time IS NOT NULL
          AND pnl_pct IS NOT NULL
          AND sl_distance IS NOT NULL
          AND sl_distance > 0
        GROUP BY sl_distance
        HAVING COUNT(*) >= 3
        ORDER BY avg_pnl DESC
    """)
    rows = cur.fetchall()
    cur.close(); conn.close()

    learnings = {}
    for (sl_dist, trades, wins, avg_pnl, stddev, worst, best) in rows:
        win_rate = (wins / trades * 100) if trades > 0 else 0
        learnings[float(sl_dist)] = {
            'sl_distance': float(sl_dist),
            'trades': int(trades),
            'wins': int(wins),
            'win_rate': round(win_rate, 1),
            'avg_pnl': round(float(avg_pnl), 3),
            'stddev_pnl': round(float(stddev or 0), 3),
            'worst': round(float(worst), 3),
            'best': round(float(best), 3),
        }
    return learnings


def compute_token_regime_performance():
    """
    Analyze which token types / market regimes perform best.
    Groups tokens by category prefix (e.g. BTC, ETH, DEGEN, etc.)
    """
    conn = _db_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT
            SUBSTRING(token FROM 1 FOR 3) as token_family,
            direction,
            COUNT(*) as trades,
            SUM(CASE WHEN pnl_usdt > 0 THEN 1 ELSE 0 END) as wins,
            AVG(pnl_pct) as avg_pnl,
            SUM(pnl_usdt) as total_usdt
        FROM trades
        WHERE status = 'closed'
          AND close_time IS NOT NULL
          AND pnl_pct IS NOT NULL
        GROUP BY SUBSTRING(token FROM 1 FOR 3), direction
        HAVING COUNT(*) >= 3
        ORDER BY avg_pnl DESC
    """)
    rows = cur.fetchall()
    cur.close(); conn.close()

    regimes = {}
    for (family, direction, trades, wins, avg_pnl, total_usdt) in rows:
        win_rate = (wins / trades * 100) if trades > 0 else 0
        key = f"{family}_{direction}"
        regimes[key] = {
            'token_family': family,
            'direction': direction,
            'trades': int(trades),
            'wins': int(wins),
            'win_rate': round(win_rate, 1),
            'avg_pnl': round(float(avg_pnl), 3),
            'total_usdt': round(float(total_usdt), 2),
        }
    return regimes


def compute_direction_performance():
    """Long vs short overall win rates."""
    conn = _db_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT
            direction,
            COUNT(*) as trades,
            SUM(CASE WHEN pnl_usdt > 0 THEN 1 ELSE 0 END) as wins,
            AVG(pnl_pct) as avg_pnl,
            SUM(pnl_usdt) as total_usdt
        FROM trades
        WHERE status = 'closed'
          AND close_time IS NOT NULL
          AND pnl_pct IS NOT NULL
        GROUP BY direction
    """)
    rows = cur.fetchall()
    cur.close(); conn.close()

    results = {}
    for (direction, trades, wins, avg_pnl, total_usdt) in rows:
        win_rate = (wins / trades * 100) if trades > 0 else 0
        results[direction] = {
            'trades': int(trades),
            'wins': int(wins),
            'losses': int(trades) - int(wins),
            'win_rate': round(win_rate, 1),
            'avg_pnl': round(float(avg_pnl), 3),
            'total_usdt': round(float(total_usdt), 2),
        }
    return results


def compute_evolution_signals():
    """
    Return recommendations for the evolution engine.
    Which variants should be spawned? Which should be killed early?
    """
    sl_learnings = compute_sl_learnings()
    conn = _db_conn()
    cur = conn.cursor()

    # Are there SL distances that haven't been tested but might work?
    cur.execute("""
        SELECT
            sl_distance,
            COUNT(*) as trades,
            AVG(pnl_pct) as avg_pnl
        FROM trades
        WHERE status = 'closed'
          AND close_time IS NOT NULL
          AND sl_distance IS NOT NULL
        GROUP BY sl_distance
        ORDER BY sl_distance
    """)
    all_sl = {(float(r[0]),): {'sl_distance': float(r[0]), 'trades': r[1], 'avg_pnl': r[2]}
              for r in cur.fetchall()}
    cur.close(); conn.close()

    # Recommend new SL values to test
    # If a gap exists between tested SL values, recommend testing it
    sorted_sl = sorted(all_sl.keys())
    recommendations = []

    if len(sorted_sl) >= 2:
        for i in range(len(sorted_sl) - 1):
            gap = sorted_sl[i+1][0] - sorted_sl[i][0]
            if gap >= 0.005:  # 0.5% gap — worth testing
                mid = round((sorted_sl[i][0] + sorted_sl[i+1][0]) / 2, 3)
                recommendations.append({
                    'type': 'sl_gap',
                    'recommendation': f"Test SL={mid*100:.1f}% — gap between "
                                      f"{sorted_sl[i][0]*100:.1f}% and {sorted_sl[i+1][0]*100:.1f}%",
                    'gap': gap,
                    'suggested_sl': mid,
                })

    return {
        'sl_learnings': sl_learnings,
        'recommendations': recommendations[:5],  # top 5
        'best_sl': max(sl_learnings.items(), key=lambda x: x[1]['avg_pnl'])[1] if sl_learnings else None,
        'worst_sl': min(sl_learnings.items(), key=lambda x: x[1]['avg_pnl'])[1] if sl_learnings else None,
    }


def write_trade_patterns(patterns, sl_learnings, regimes, direction_stats):
    """Write learned patterns to both JSON file and trade_patterns table."""
    from decimal import Decimal

    def _float(v):
        """Convert to float, handling Decimal, None, etc."""
        if v is None:
            return None
        if isinstance(v, Decimal):
            return float(v)
        if isinstance(v, float):
            return v
        if isinstance(v, int):
            return float(v)
        try:
            return float(v)
        except (TypeError, ValueError):
            return None

    # ── Clean snapshot ───────────────────────────────────────────
    def _clean(d):
        if isinstance(d, dict):
            return {k: _clean(v) for k, v in d.items()}
        if isinstance(d, list):
            return [_clean(v) for v in d]
        return _float(d)

    snapshot = {
        'timestamp': datetime.now().isoformat(),
        'token_sl_patterns': _clean(patterns),
        'sl_learnings': _clean(sl_learnings),
        'token_regimes': _clean(regimes),
        'direction_stats': _clean(direction_stats),
    }

    # ── Write JSON ───────────────────────────────────────────────
    with open(TRADE_PATTERNS_FILE, 'w') as f:
        json.dump(snapshot, f, indent=2)

    # ── Write to brain DB trade_patterns table ───────────────────
    conn = _db_conn()
    cur = conn.cursor()

    # Upsert each pattern
    for key, pat in patterns.items():
        token = pat['token']
        direction = pat['direction']
        best_sl = pat['sl_distances'][0] if pat['sl_distances'] else {}
        cur.execute("""
            INSERT INTO trade_patterns (token, side, pattern_name, confidence, adjustment)
            VALUES (%s, %s, 'sl_distance', %s, %s)
            ON CONFLICT DO NOTHING
        """, (
            token, direction,
            best_sl.get('win_rate', 50),
            json.dumps({
                'best_sl_distance': best_sl.get('sl_distance'),
                'win_rate': best_sl.get('win_rate'),
                'avg_pnl': best_sl.get('avg_pnl'),
                'sample_count': best_sl.get('trades'),
                'all_sl_distances': pat['sl_distances'],
            })
        ))

    conn.commit()
    cur.close(); conn.close()
    log(f'Wrote {len(patterns)} token patterns, {len(sl_learnings)} SL learnings to DB + JSON')


def run():
    """Full learning cycle."""
    log('Starting learning cycle...')

    sl_learnings = compute_sl_learnings()
    patterns = compute_token_stats()
    regimes = compute_token_regime_performance()
    direction_stats = compute_direction_performance()
    evolution = compute_evolution_signals()

    write_trade_patterns(patterns, sl_learnings, regimes, direction_stats)

    # Print summary
    print('\n  ── Direction Performance ─────────────────────────────')
    for direction, stats in sorted(direction_stats.items()):
        print(f"  {direction:8s}: {stats['trades']:3d} trades | "
              f"{stats['win_rate']:5.1f}% WR | pnl={stats['avg_pnl']:+.2f}% | "
              f"${stats['total_usdt']:+.2f}")

    if sl_learnings:
        print('\n  ── SL Distance Performance ────────────────────────────')
        for sl, stats in sorted(sl_learnings.items(), key=lambda x: x[1]['avg_pnl'], reverse=True):
            print(f"  SL={sl*100:.1f}%: {stats['trades']:3d} trades | "
                  f"{stats['win_rate']:5.1f}% WR | avg_pnl={stats['avg_pnl']:+.2f}% | "
                  f"range=[{stats['worst']:+.1f}%, {stats['best']:+.1f}%]")

    if evolution.get('recommendations'):
        print('\n  ── Evolution Recommendations ───────────────────────────')
        for rec in evolution['recommendations']:
            print(f"  • {rec['recommendation']}")

    log(f'Done. Patterns saved to {TRADE_PATTERNS_FILE}')


if __name__ == '__main__':
    run()
