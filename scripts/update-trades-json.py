#!/usr/bin/python3
"""Standalone trades.json writer — no signal_schema (avoids init_db hangs on large DBs).
Updates P&L on open trades using live prices from the static SQLite DB.
Uses atomic write (flock) for safe concurrent access with hermes-trades-api.py."""
import sys, os, json, sqlite3, psycopg2, fcntl
from datetime import datetime, timezone

BRAIN_DB  = 'host=/var/run/postgresql dbname=brain user=postgres password=Brain123'
PRICE_DB  = '/root/.hermes/data/signals_hermes.db'
OUT_TRADES = '/var/www/hermes/data/trades.json'


def _atomic_write(data: dict, path: str):
    """Write JSON atomically using flock — safe for concurrent writers."""
    lock_path = path + '.lock'
    with open(lock_path, 'w') as lf:
        fcntl.flock(lf.fileno(), fcntl.LOCK_EX)
        with open(path, 'w') as f:
            json.dump(data, f, indent=2)
        fcntl.flock(lf.fileno(), fcntl.LOCK_UN)

def get_current_price(token):
    try:
        conn_p = sqlite3.connect(PRICE_DB, timeout=3)
        cur_p = conn_p.cursor()
        cur_p.execute(
            'SELECT price FROM price_history WHERE token=? ORDER BY timestamp DESC LIMIT 1',
            (token,)
        )
        row = cur_p.fetchone()
        conn_p.close()
        return float(row[0]) if row else None
    except:
        return None

conn = psycopg2.connect(BRAIN_DB)
cur = conn.cursor()
cur.execute("""
    SELECT id, token, direction, entry_price, leverage, amount_usdt,
           stop_loss, target
    FROM trades WHERE status='open' LIMIT 100
""")
open_t = cur.fetchall()
cur.execute("""
    SELECT COUNT(*) FROM trades
    WHERE (server='Hermes' OR server IS NULL) AND status='closed'
""")
total_closed = cur.fetchone()[0]
cur.execute("""
    SELECT id, token, direction, entry_price, exit_price, pnl_usdt, pnl_pct,
           leverage, amount_usdt, close_reason, close_time, signal
    FROM trades
    WHERE (server='Hermes' OR server IS NULL) AND status='closed'
    ORDER BY close_time DESC
    LIMIT 200
""")
closed_t = cur.fetchall()
cur.close(); conn.close()

out = []
closed_out = []
for r in open_t:
    tkn=r[1]; direction=r[2]; entry_px=float(r[3]); lev=float(r[4]); amt=float(r[5] or 0)
    sl=float(r[6]) if r[6] is not None else 0.0
    tp=float(r[7]) if r[7] is not None else 0.0
    cp = get_current_price(tkn) or entry_px
    if entry_px > 0:
        pnl_pct = round((entry_px-cp)/entry_px*100, 4) if direction=='SHORT' else round((cp-entry_px)/entry_px*100, 4)
        pnl_usdt = round(pnl_pct/100*amt, 4)
    else:
        pnl_pct = 0.0; pnl_usdt = 0.0
    out.append({
        'token': tkn, 'direction': direction,
        'entry': entry_px, 'current': round(cp, 6),
        'pnl_pct': round(pnl_pct, 2), 'pnl_usdt': round(pnl_usdt, 2),
        'sl': round(sl, 6), 'tp': round(tp, 6)
    })

# Build closed trades array
for r in closed_t:
    tid, token, direction, entry_px, exit_px, pnl_usdt, pnl_pct, lev, amt, reason, close_time, signal = r
    # Format close_time: datetime object -> 'YYYY-MM-DD HH:MM:SS'
    if close_time:
        ct_str = str(close_time)[:19]
    else:
        ct_str = ''
    closed_out.append({
        'id': int(tid) if tid else 0,
        'token': str(token) if token else '',
        'direction': str(direction) if direction else '',
        'entry': float(entry_px) if entry_px else 0.0,
        'exit': float(exit_px) if exit_px else 0.0,
        'pnl_pct': round(float(pnl_pct), 4) if pnl_pct else 0.0,
        'pnl_usdt': round(float(pnl_usdt), 2) if pnl_usdt else 0.0,
        'lev': float(lev) if lev else 1.0,
        'size': float(amt) if amt else 0.0,
        'close_reason': str(reason) if reason else '',
        'signal': str(signal) if signal else '',
        'closed': ct_str
    })

result = {
    'updated': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
    'open_count': len(open_t), 'closed_count': total_closed,
    'page_size': 50, 'open': out, 'closed': closed_out
}
_atomic_write(result, OUT_TRADES)

print(f'Written {os.path.getsize(OUT_TRADES)} bytes | open={len(out)} closed={len(closed_out)}')
for t in out:
    print(f"  {t['token']:<6} {t['direction']:<5} ep={t['entry']:.4f} cp={t['current']:.4f} pnl%={t['pnl_pct']:>8.2f}% pnl$={t['pnl_usdt']:>8.2f}")
