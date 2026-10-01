#!/usr/bin/env python3
"""Bug hunt verification — Part 1: PnL + trade-level data."""
import sys, os, json
sys.path.insert(0, '/root/.hermes/scripts')
os.chdir('/root/.hermes/scripts')
import psycopg2
from psycopg2.extras import RealDictCursor
from _secrets import BRAIN_DB_DICT

cfg = BRAIN_DB_DICT.copy(); cfg.setdefault('port', 5432)
conn = psycopg2.connect(host=cfg['host'], port=cfg['port'], database=cfg['database'],
                        user=cfg['user'], password=cfg['password'])
cur = conn.cursor(cursor_factory=RealDictCursor)

def q(title, sql, params=None, show_sql=True):
    print(f"\n{'='*70}\n== {title}\n{'='*70}")
    if show_sql: print(f"SQL: {sql}")
    try:
        cur.execute(sql, params)
        rows = cur.fetchall()
        if not rows:
            print("(no rows)"); return rows
        for r in rows:
            print({k: (float(v) if hasattr(v,'as_tuple') and not isinstance(v,(str,bool)) else v) for k,v in dict(r).items()})
        return rows
    except Exception as e:
        print(f"ERROR: {e}"); conn.rollback(); return None

# ---- Discovery: statuses and time columns ----
q("STATUS VALUES", "SELECT status, count(*) n, min(open_time) min_ot, max(open_time) max_ot FROM trades GROUP BY status ORDER BY n DESC")
q("SAMPLE ROW", "SELECT id, token, signal, status, pnl_usdt, open_time, close_time, created_at, paper, direction FROM trades ORDER BY open_time DESC LIMIT 5")

# ---- CLAIM 1: PnL 7d / 30d / all-time ----
# Closed trades with pnl, grouped by window. Use close_time (when PnL realized).
q("PnL BY WINDOW (close_time, closed trades, non-null pnl)", """
SELECT
  count(*) FILTER (WHERE close_time >= now() - interval '7 days')  AS n_7d,
  round(sum(pnl_usdt)  FILTER (WHERE close_time >= now() - interval '7 days')::numeric, 2) AS pnl_7d,
  count(*) FILTER (WHERE close_time >= now() - interval '30 days') AS n_30d,
  round(sum(pnl_usdt) FILTER (WHERE close_time >= now() - interval '30 days')::numeric, 2) AS pnl_30d,
  count(*) AS n_all,
  round(sum(pnl_usdt)::numeric, 2) AS pnl_all
FROM trades
WHERE pnl_usdt IS NOT NULL AND status NOT ILIKE '%open%'
""")

q("PnL BY WINDOW (open_time, ALL trades incl open w/ pnl)", """
SELECT
  count(*) FILTER (WHERE open_time >= now() - interval '7 days')  AS n_7d,
  round(coalesce(sum(pnl_usdt)  FILTER (WHERE open_time >= now() - interval '7 days'),0)::numeric, 2) AS pnl_7d,
  count(*) FILTER (WHERE open_time >= now() - interval '30 days') AS n_30d,
  round(coalesce(sum(pnl_usdt) FILTER (WHERE open_time >= now() - interval '30 days'),0)::numeric, 2) AS pnl_30d,
  count(*) AS n_all,
  round(coalesce(sum(pnl_usdt),0)::numeric, 2) AS pnl_all
FROM trades
WHERE pnl_usdt IS NOT NULL
""")

q("OPEN/NULL-PNL TRADE COUNT", """
SELECT count(*) FILTER (WHERE pnl_usdt IS NULL) AS null_pnl,
       count(*) FILTER (WHERE status ILIKE '%open%') AS open_status,
       count(*) AS total FROM trades""")

conn.close()
print("\nDONE PART 1")
