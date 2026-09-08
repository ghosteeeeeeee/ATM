#!/usr/bin/env python3
"""
favorites_tracker.py — Track rolling 7d and 30d performance for FAVORITES tokens.

Queries brain DB for closed trades per FAVORITES token.
Writes:
  - favorites_performance.json — 7d stats (for live dashboard)
  - favorites_leaderboard.json — 30d leaderboard + hall of fame

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
LEADERBOARD_FILE = os.path.join(HERMES_DATA, 'favorites_leaderboard.json')
LOG_FILE = '/root/.hermes/logs/favorites_tracker.log'
LOOKBACK_DAYS = 7
LOOKBACK_DAYS_30D = 30
MIN_TRADES = 3
MIN_TRADES_30D = 10  # Higher bar for30d leaderboard


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


def get_30d_leaderboard():
    """Query 30d stats for leaderboard and hall of fame."""
    conn = None
    try:
        import psycopg2
        from _secrets import BRAIN_DB_DICT
        conn = psycopg2.connect(**BRAIN_DB_DICT)
        cur = conn.cursor()

        # All tokens with enough 30d trades
        cur.execute(f"""
            SELECT
                token,
                COUNT(*) as trades,
                SUM(CASE WHEN pnl_pct > 0 THEN 1 ELSE 0 END) as wins,
                ROUND(100.0 * SUM(CASE WHEN pnl_pct > 0 THEN 1 ELSE 0 END) / COUNT(*), 1) as winrate,
                ROUND(AVG(pnl_pct), 2) as avg_pnl_pct,
                ROUND(SUM(pnl_usdt), 2) as total_pnl_usdt,
                ROUND(MIN(pnl_pct), 2) as worst_trade,
                ROUND(MAX(pnl_pct), 2) as best_trade,
                CASE WHEN token = ANY(%s) THEN true ELSE false END as is_favorite
            FROM trades
            WHERE status = 'closed'
              AND server = 'Hermes'
              AND pnl_pct IS NOT NULL
              AND close_time > NOW() - INTERVAL '{LOOKBACK_DAYS_30D} days'
            GROUP BY token
            HAVING COUNT(*) >= %s
            ORDER BY total_pnl_usdt DESC
        """, (list(FAVORITES), MIN_TRADES_30D))

        columns = [desc[0] for desc in cur.description]
        all_tokens = [dict(zip(columns, [float(v) if hasattr(v, '__float__') else v for v in row])) for row in cur.fetchall()]

        # Hall of fame: consistent winners (30d WR >= 60%, trades >=15, profitable)
        hall_of_fame = [
            t for t in all_tokens
            if t['winrate'] >= 60 and t['trades'] >= 15 and t['total_pnl_usdt'] > 0
        ][:10]

        # Hall of shame: consistent losers (30d WR < 45%, trades >=15, losing)
        hall_of_shame = [
            t for t in all_tokens
            if t['winrate'] < 45 and t['trades'] >= 15 and t['total_pnl_usdt'] < 0
        ][:10]

        # Top leaderboard (all tokens, sorted by PnL)
        leaderboard = all_tokens[:20]

        return {
            'leaderboard': leaderboard,
            'hall_of_fame': hall_of_fame,
            'hall_of_shame': hall_of_shame,
        }

    except Exception as e:
        log(f"30d leaderboard error: {e}")
        return {'leaderboard': [], 'hall_of_fame': [], 'hall_of_shame': []}
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

        # ── 30d Leaderboard + Hall of Fame ──
        leaderboard_data = get_30d_leaderboard()
        leaderboard_output = {
            'updated_at': datetime.now(timezone.utc).isoformat(),
            'lookback_days': LOOKBACK_DAYS_30D,
            **leaderboard_data,
        }

        try:
            with open(LEADERBOARD_FILE, 'w') as f:
                json.dump(leaderboard_output, f, indent=2)
            SERVED_LEADERBOARD = '/var/www/hermes/data/favorites_leaderboard.json'
            with open(SERVED_LEADERBOARD, 'w') as f:
                json.dump(leaderboard_output, f, indent=2)
        except Exception:
            pass

        log(f"Written {len(favorites_stats)} favorites, {len(leaderboard_data.get('leaderboard', []))} leaderboard, "
            f"{len(leaderboard_data.get('hall_of_fame', []))} hall of fame")

    except Exception as e:
        log(f"Error: {e}")
    finally:
        if lock_fd:
            fcntl.flock(lock_fd, fcntl.LOCK_UN)
            lock_fd.close()


if __name__ == '__main__':
    run()
