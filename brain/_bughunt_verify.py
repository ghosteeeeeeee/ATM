#!/usr/bin/env python3
"""Bug hunt verification queries — audit claims vs live data."""
import sys, os
sys.path.insert(0, '/root/.hermes/scripts')
os.chdir('/root/.hermes/scripts')
import psycopg2
from psycopg2.extras import RealDictCursor
from _secrets import BRAIN_DB_DICT

cfg = BRAIN_DB_DICT.copy()
cfg.setdefault('port', 5432)
conn = psycopg2.connect(host=cfg['host'], port=cfg['port'], database=cfg['database'],
                        user=cfg['user'], password=cfg['password'])
cur = conn.cursor(cursor_factory=RealDictCursor)

def q(title, sql, params=None):
    print(f"\n{'='*70}\n== {title}\n{'='*70}")
    print(f"SQL: {sql}")
    try:
        cur.execute(sql, params)
        rows = cur.fetchall()
        if not rows:
            print("(no rows)")
            return rows
        for r in rows:
            print(dict(r))
        return rows
    except Exception as e:
        print(f"ERROR: {e}")
        conn.rollback()
        return None

# ---- Schema discovery ----
q("TABLES", """SELECT table_name FROM information_schema.tables WHERE table_schema='public' ORDER BY table_name""")
