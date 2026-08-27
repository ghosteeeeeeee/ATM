#!/usr/bin/env python3
"""
favorites_tracker.py — Track rolling 7d performance for FAVORITES tokens.

Queries brain DB for closed trades per FAVORITES token.
Writes /root/.hermes/data/favorites_performance.json for dashboard consumption.

Run via: python3 scripts/favorites_tracker.py
Timer: hermes-favorites-tracker.timer (hourly)
"""
import os, sys, json, fcntl
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paths import HERMES_DATA
from hermes_constants import FAVORITES

LOCK_FILE = '/tmp/hermes-favorites-tracker.lock'
OUTPUT_FILE = os.path.join(HERMES_DATA, 'favorites_performance.json')
LOG_FILE = '/root/.hermes/logs/favorites_tracker.log'
LOOKBACK_DAYS = 7
MIN_TRADES = 3


def log(msg):
    ts = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
    line = f"[{ts}] {msg}"
    print(line)
    try:
        os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
        with open(LOG_FILE, 'a') as f:
            f.write(line + '\n')
    except Exception:
        pass


def get_favorites_stats():
    """Query rolling 7d stats for FAVORITES tokens from brain DB."""
    conn = None
    try:
        import psycopg2
        from _secrets import BRAIN_DB_DICT
        conn = psycopg2.connect(**BRAIN_DB_DICT)
        cur = conn.cursor()

        # Per-token stats (7d)
        cur.execute(f"""
            SELECT
                token,
                COUNT(*) as trades,
                SUM(CASE WHEN pnl_pct > 0 THEN 1 ELSE 0 END) as wins,
                ROUND(100.0 * SUM(CASE WHEN pnl_pct > 0 THEN 1 ELSE 0 END) / COUNT(*), 1) as winrate,
                ROUND(AVG(pnl_pct), 2) as avg_pnl_pct,
                ROUND(SUM(pnl_pct), 2) as total_pnl_pct,
                ROUND(AVG(pnl_usdt), 4) as avg_pnl_usdt,
                ROUND(SUM(pnl_usdt), 2) as total_pnl_usdt,
                ROUND(MIN(pnl_pct), 2) as worst_trade,
                ROUND(MAX(pnl_pct), 2) as best_trade
            FROM trades
            WHERE status = 'closed'
              AND server = 'Hermes'
              AND pnl_pct IS NOT NULL
              AND close_time > NOW() - INTERVAL '{LOOKBACK_DAYS} days'
              AND token = ANY(%s)
            GROUP BY token
            ORDER BY total_pnl_usdt DESC
        """, (list(FAVORITES),))

        columns = [desc[0] for desc in cur.description]
        favorites_stats = [dict(zip(columns, [float(v) if hasattr(v, '__float__') else v for v in row])) for row in cur.fetchall()]

        # Field comparison (non-favorites)
        cur.execute(f"""
            SELECT
                COUNT(*) as trades,
                SUM(CASE WHEN pnl_pct > 0 THEN 1 ELSE 0 END) as wins,
                ROUND(100.0 * SUM(CASE WHEN pnl_pct > 0 THEN 1 ELSE 0 END) / COUNT(*), 1) as winrate,
                ROUND(AVG(pnl_pct), 2) as avg_pnl_pct,
                ROUND(SUM(pnl_usdt), 2) as total_pnl_usdt
            FROM trades
            WHERE status = 'closed'
              AND server = 'Hermes'
              AND pnl_pct IS NOT NULL
              AND close_time > NOW() - INTERVAL '{LOOKBACK_DAYS} days'
              AND token != ALL(%s)
        """, (list(FAVORITES),))

        field_row = cur.fetchone()
        if field_row:
            raw = dict(zip(['trades', 'wins', 'winrate', 'avg_pnl_pct', 'total_pnl_usdt'], field_row))
            field_stats = {k: float(v) if hasattr(v, '__float__') else v for k, v in raw.items()}
        else:
            field_stats = {}

        return favorites_stats, field_stats

    except Exception as e:
        log(f"DB query error: {e}")
        return [], {}
    finally:
        if conn:
            try: conn.close()
            except Exception: pass


def run():
    lock_fd = None
    try:
        lock_fd = open(LOCK_FILE, 'w')
        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except IOError:
        log("Another instance running — skipping")
        return

    try:
        favorites_stats, field_stats = get_favorites_stats()

        output = {
            'updated_at': datetime.now(timezone.utc).isoformat(),
            'lookback_days': LOOKBACK_DAYS,
            'favorites_count': len(FAVORITES),
            'favorites': favorites_stats,
            'field': field_stats,
        }

        # Add summary
        if favorites_stats:
            fav_trades = sum(s['trades'] for s in favorites_stats)
            fav_wins = sum(s['wins'] for s in favorites_stats)
            output['summary'] = {
                'favorites_wr': round(100 * fav_wins / fav_trades, 1) if fav_trades else 0,
                'favorites_trades': fav_trades,
                'favorites_total_pnl_usdt': round(sum(s['total_pnl_usdt'] for s in favorites_stats), 2),
                'field_wr': field_stats.get('winrate', 0),
                'field_trades': field_stats.get('trades', 0),
                'field_total_pnl_usdt': field_stats.get('total_pnl_usdt', 0),
                'edge': round(
                    (100 * fav_wins / fav_trades if fav_trades else 0) - (field_stats.get('winrate', 0) or 0), 1
                ),
            }

        os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
        with open(OUTPUT_FILE, 'w') as f:
            json.dump(output, f, indent=2)

        # Also write to served directory for dashboard access
        SERVED_FILE = '/var/www/hermes/data/favorites_performance.json'
        try:
            os.makedirs(os.path.dirname(SERVED_FILE), exist_ok=True)
            with open(SERVED_FILE, 'w') as f:
                json.dump(output, f, indent=2)
        except Exception:
            pass

        log(f"Written {len(favorites_stats)} favorites, {field_stats.get('trades', 0)} field trades")

    except Exception as e:
        log(f"Error: {e}")
    finally:
        if lock_fd:
            fcntl.flock(lock_fd, fcntl.LOCK_UN)
            lock_fd.close()


if __name__ == '__main__':
    run()
