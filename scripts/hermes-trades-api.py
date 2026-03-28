#!/usr/bin/env python3
"""Hermes trades + signals API — outputs JSON for the dashboard."""
import sys, json, os, sqlite3
sys.path.insert(0, '/root/.hermes/scripts')
from signal_schema import init_db
import psycopg2
from datetime import datetime, timezone

BRAIN_DB  = "host=/var/run/postgresql dbname=brain user=postgres password=postgres"
OUT_TRADES   = "/var/www/hermes/data/trades.json"
OUT_SIGNALS  = "/var/www/hermes/data/signals.json"
from signal_schema import RUNTIME_DB as SIGNALS_DB
os.makedirs("/var/www/hermes/data", exist_ok=True)


def _live_trailing_sl(trade_id, direction, entry_price, current_price, trail_act, trail_dist):
    """
    Compute the live trailing SL for an open position using trailing_stops.json.
    Returns None if not yet activated.
    """
    import json
    try:
        with open("/var/www/hermes/data/trailing_stops.json") as f:
            data = json.load(f)
    except:
        return None

    entry = float(entry_price or 0)
    current = float(current_price or 0)
    direction = str(direction or '').upper()
    trail_act_pct = float(trail_act or 0.01) * 100
    trail_dist_pct = float(trail_dist or 0.01)

    if entry <= 0 or current <= 0:
        return None

    if direction == 'LONG':
        pnl_pct = (current - entry) / entry * 100
    elif direction == 'SHORT':
        pnl_pct = (entry - current) / entry * 100
    else:
        return None

    if pnl_pct < trail_act_pct:
        return None  # trailing not yet active

    # Get best_price from trailing_stops.json
    ts = data.get(str(trade_id), {})
    if not ts.get('active'):
        return None

    best_price = float(ts.get('best_price', current))

    if direction == 'LONG':
        return round(best_price * (1 - trail_dist_pct), 8)
    else:
        return round(best_price * (1 + trail_dist_pct), 8)


def get_trades(status='open', limit=20, offset=0):
    try:
        conn = psycopg2.connect(BRAIN_DB)
        cur = conn.cursor()
        cur.execute("""
            SELECT id, token, direction, entry_price, current_price, pnl_pct, pnl_usdt,
                   stop_loss, target, exchange, open_time, close_time, status, close_reason,
                   signal, confidence, leverage, amount_usdt,
                   trailing_activation, trailing_distance, exit_price
            FROM trades
            WHERE (server = 'Hermes' OR server IS NULL) AND status = %s
            ORDER BY
                CASE WHEN %s = 'open' THEN id END DESC,
                CASE WHEN %s = 'closed' THEN close_time END DESC
            LIMIT %s OFFSET %s
        """, (status, status, status, limit, offset))
        rows = cur.fetchall()
        cur.close(); conn.close()
        return rows
    except:
        return []


def get_signals_from_db(limit=100):
    """Read recent signals from SQLite."""
    if not os.path.exists(SIGNALS_DB):
        return []
    try:
        conn = sqlite3.connect(SIGNALS_DB)
        c = conn.cursor()
        c.execute("""
            SELECT token, direction, confidence, signal_type, source, price,
                   z_score, rsi_14, macd_hist, decision, created_at
            FROM signals
            ORDER BY created_at DESC
            LIMIT ?
        """, (limit,))
        rows = c.fetchall()
        conn.close()
        return [{
            'token': r[0], 'direction': r[1], 'confidence': float(r[2]) if r[2] else 0,
            'type': r[3], 'source': r[4], 'price': float(r[5]) if r[5] else 0,
            'zscore': float(r[6]) if r[6] else None,
            'rsi': float(r[7]) if r[7] else None,
            'macd': float(r[8]) if r[8] else None,
            'decision': r[9] or 'PENDING',
            'time': r[10]
        } for r in rows]
    except:
        return []


def write_trades():
    # Get open trades
    open_t = get_trades('open', 100)

    # Get total closed count
    try:
        conn = psycopg2.connect(BRAIN_DB)
        cur = conn.cursor()
        cur.execute(
            "SELECT COUNT(*) FROM trades WHERE (server = 'Hermes' OR server IS NULL) AND status = 'closed'"
        )
        total_closed = cur.fetchone()[0]
        cur.close(); conn.close()
    except:
        total_closed = 0

    # Get closed trades — 50 per page, page from query param (default 1)
    # The API will return all closed trades with pagination info
    # We'll write a separate endpoint approach: fetch all IDs, split into pages
    # For simplicity, write a flat list with pagination metadata
    closed_t = get_trades('closed', 200)  # enough for 4 pages

    result = {
        "updated": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
        "open_count": len(open_t),
        "closed_count": total_closed,
        "page_size": 50,
        "open": [{
            "token": r[1], "direction": r[2],
            "entry": float(r[3]) if r[3] else 0,
            "current": float(r[4]) if r[4] else 0,
            "pnl_pct": round(float(r[5]), 2) if r[5] else 0,
            # pnl_usdt from DB already includes leverage — use directly
            "pnl_usdt": round(float(r[6]), 2) if r[6] else 0,
            "sl": round(float(r[7]), 6) if r[7] else 0,
            "tp": round(float(r[8]), 6) if r[8] else 0,
            "exchange": r[9], "opened": str(r[10]) if r[10] else "",
            "signal": r[14], "confidence": float(r[15]) if r[15] else 0,
            "leverage": float(r[16]) if r[16] else 1,
            "amount_usdt": float(r[17]) if r[17] else 50.0,
            "effective_size": round(float(r[17]) * float(r[16]), 2) if r[17] and r[16] else 50.0,
            "trailing_activation": float(r[18]) if r[18] else 0.01,
            "trailing_distance": float(r[19]) if r[19] else 0.01,
            "trailing_sl": _live_trailing_sl(r[0], r[2], r[3], r[4], float(r[18]) if r[18] else 0.01, float(r[19]) if r[19] else 0.01)
        } for r in open_t],
        "closed": [{
            "token": r[1], "direction": r[2],
            "entry": float(r[3]) if r[3] else 0,
            "exit": float(r[20]) if r[20] else 0,
            "closed": str(r[11]) if r[11] else "",
            "pnl_pct": round(float(r[5]), 2) if r[5] else 0,
            # pnl_usdt from DB already includes leverage — use directly (FIX: was * leverage)
            "pnl_usdt": round(float(r[6]), 2) if r[6] else 0,
            "exchange": r[9], "opened": str(r[10]) if r[10] else "",
            "status": r[12], "signal": r[14],
            "confidence": float(r[15]) if r[15] else 0,
            "leverage": float(r[16]) if r[16] else 1,
            "amount_usdt": float(r[17]) if r[17] else 50.0,
            "close_reason": r[13] if r[13] else ""
        } for r in closed_t]
    }
    with open(OUT_TRADES, 'w') as f:
        json.dump(result, f, indent=2)


def write_signals():
    """Export signals from DB + win rate stats for the web dashboard."""
    signals = get_signals_from_db(200)

    # Compute win rate from brain DB using pnl_pct (after fees)
    # Filter out corrupted trades: exit_price sanity check
    # (some trades have exit prices 1000x entry price — data errors)
    conn = psycopg2.connect(BRAIN_DB)
    cur = conn.cursor()

    # Count ALL closed trades for total_executed
    cur.execute("""
        SELECT COUNT(*)
        FROM trades
        WHERE status = 'closed'
          AND (server = 'Hermes' OR server IS NULL)
          AND entry_price > 0 AND exit_price > 0
          AND exit_price / entry_price BETWEEN 0.01 AND 100
          AND pnl_pct IS NOT NULL
    """)
    total_closed = cur.fetchone()[0]

    # Get stats using pnl_pct (fees already deducted)
    cur.execute("""
        SELECT
            COUNT(*) FILTER (WHERE pnl_pct > 0) as wins,
            COUNT(*) FILTER (WHERE pnl_pct <= 0) as losses,
            SUM(pnl_pct) as total_pnl,
            AVG(pnl_pct) as avg_pnl
        FROM trades
        WHERE status = 'closed'
          AND (server = 'Hermes' OR server IS NULL)
          AND entry_price > 0 AND exit_price > 0
          AND exit_price / entry_price BETWEEN 0.01 AND 100
          AND pnl_pct IS NOT NULL
    """)
    row = cur.fetchone()
    wins = row[0] or 0
    losses = row[1] or 0
    total_pnl = float(row[2] or 0)
    avg_pnl = float(row[3] or 0)
    win_rate = (wins / total_closed * 100) if total_closed > 0 else 0

    cur.close(); conn.close()

    approved = sum(1 for s in signals if s['decision'] == 'APPROVED')
    executed = sum(1 for s in signals if s['decision'] == 'EXECUTED')
    pending  = sum(1 for s in signals if s['decision'] == 'PENDING')

    result = {
        "updated": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
        "approved": approved, "executed": executed, "pending": pending,
        "total": len(signals),
        "stats": {
            "total_executed": total_closed,
            "wins": wins,
            "losses": losses,
            "win_rate": round(win_rate, 1),
            "total_pnl": round(total_pnl, 2),
            "avg_pnl": round(avg_pnl, 4),
        },
        "signals": signals
    }
    with open(OUT_SIGNALS, 'w') as f:
        json.dump(result, f, indent=2)


def main():
    write_trades()
    write_signals()
    print(f"trades.json: written | signals.json: written")


if __name__ == '__main__':
    main()
