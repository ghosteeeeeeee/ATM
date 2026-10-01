#!/usr/bin/env python3
"""Bug hunt verification — Part 2: confluence tiers, signal families, hourly."""
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

def q(title, sql, params=None):
    print(f"\n{'='*70}\n== {title}\n{'='*70}")
    try:
        cur.execute(sql, params)
        rows = cur.fetchall()
        if not rows:
            print("(no rows)"); return rows
        for r in rows:
            d = dict(r)
            print({k: (round(float(v),4) if isinstance(v,(int,float)) and not isinstance(v,bool) and k not in ('n','trades','cnt') else v) for k,v in d.items()})
        return rows
    except Exception as e:
        print(f"ERROR: {e}"); conn.rollback(); return None

# ---- Inspect _signal_metadata structure ----
q("SAMPLE _signal_metadata (recent 30d trades)", """
SELECT id, signal, direction, pnl_usdt, _signal_metadata
FROM trades
WHERE close_time >= now() - interval '30 days' AND _signal_metadata IS NOT NULL
ORDER BY close_time DESC LIMIT 3
""")
