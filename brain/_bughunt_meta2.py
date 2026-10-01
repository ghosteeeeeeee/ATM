#!/usr/bin/env python3
"""Bug hunt verification — Part 2: confluence tiers, signal families, hourly PnL."""
import sys, os, json, re
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
            out = {}
            for k,v in d.items():
                if isinstance(v, bool): out[k]=v
                elif isinstance(v,(int,)): out[k]=v
                elif isinstance(v,(float,)): out[k]=round(v,4)
                else:
                    try: out[k]=round(float(v),4)
                    except Exception: out[k]=v
            print(out)
        return rows
    except Exception as e:
        print(f"ERROR: {e}"); conn.rollback(); return None

# ══════════════════════════════════════════════════════════════════════
# CLAIM 3: Confluence tiers — source count from comma-separated signal col
# ══════════════════════════════════════════════════════════════════════
print("\n" + "#"*70)
print("# CLAIM 3: CONFLUENCE TIERS (30d, source count = comma-parts of signal)")
print("#"*70)

q("TIERS: n_parts of signal column, 30d closed trades", """
SELECT
  array_length(string_to_array(signal, ','), 1) AS src_n,
  count(*) AS trades,
  round(100.0*avg(CASE WHEN pnl_usdt>0 THEN 1.0 ELSE 0.0 END),1) AS wr_pct,
  round(sum(pnl_usdt)::numeric,2) AS pnl,
  round(avg(pnl_usdt)::numeric,5) AS avg_pnl
FROM trades
WHERE close_time >= now() - interval '30 days' AND pnl_usdt IS NOT NULL AND status='closed'
GROUP BY 1 ORDER BY 1
""")

q("MULTI vs SINGLE summary, 30d", """
SELECT
  CASE WHEN array_length(string_to_array(signal,','),1) >= 2 THEN 'multi' ELSE 'single' END AS grp,
  count(*) AS trades,
  round(100.0*avg(CASE WHEN pnl_usdt>0 THEN 1.0 ELSE 0.0 END),1) AS wr_pct,
  round(sum(pnl_usdt)::numeric,2) AS pnl,
  round(avg(pnl_usdt)::numeric,5) AS avg_pnl
FROM trades
WHERE close_time >= now() - interval '30 days' AND pnl_usdt IS NOT NULL AND status='closed'
GROUP BY 1
""")

# ══════════════════════════════════════════════════════════════════════
# CLAIM 6: Signal family profitability 30d
# ══════════════════════════════════════════════════════════════════════
print("\n" + "#"*70)
print("# CLAIM 6: SIGNAL FAMILY PROFITABILITY (30d)")
print("#"*70)

q("Distinct signal labels 30d + profitable/losing counts", """
WITH per_label AS (
  SELECT signal, count(*) AS n, sum(pnl_usdt) AS pnl
  FROM trades
  WHERE close_time >= now() - interval '30 days' AND pnl_usdt IS NOT NULL AND status='closed'
  GROUP BY signal
)
SELECT count(*) AS distinct_labels,
       count(*) FILTER (WHERE pnl > 0) AS profitable_labels,
       count(*) FILTER (WHERE pnl <= 0) AS losing_labels,
       count(*) FILTER (WHERE n >= 5) AS labels_ge5,
       count(*) FILTER (WHERE n >= 5 AND pnl > 0) AS profitable_ge5,
       count(*) FILTER (WHERE n >= 10) AS labels_ge10,
       count(*) FILTER (WHERE n >= 10 AND pnl > 0) AS profitable_ge10
FROM per_label
""")

q("Top profitable labels 30d", """
SELECT signal, count(*) AS n,
       round(100.0*avg(CASE WHEN pnl_usdt>0 THEN 1.0 ELSE 0.0 END),1) AS wr_pct,
       round(sum(pnl_usdt)::numeric,2) AS pnl
FROM trades
WHERE close_time >= now() - interval '30 days' AND pnl_usdt IS NOT NULL AND status='closed'
GROUP BY signal HAVING sum(pnl_usdt) > 0
ORDER BY pnl DESC LIMIT 15
""")

q("Gross wins / gross losses by label, 30d", """
WITH per_label AS (
  SELECT signal, sum(pnl_usdt) AS pnl
  FROM trades
  WHERE close_time >= now() - interval '30 days' AND pnl_usdt IS NOT NULL AND status='closed'
  GROUP BY signal
)
SELECT round(sum(pnl) FILTER (WHERE pnl>0)::numeric,2) AS gross_wins,
       count(*) FILTER (WHERE pnl>0) AS n_winning_labels,
       round(sum(pnl) FILTER (WHERE pnl<=0)::numeric,2) AS gross_losses,
       count(*) FILTER (WHERE pnl<=0) AS n_losing_labels
FROM per_label
""")

# Normalized families: take first comma-part, strip +/- suffix
q("Normalized families (first comma-part, strip +/-), profitable/losing", """
WITH fam AS (
  SELECT regexp_replace(split_part(signal, ',', 1), '[+-]+$', '') AS family,
         count(*) AS n, sum(pnl_usdt) AS pnl
  FROM trades
  WHERE close_time >= now() - interval '30 days' AND pnl_usdt IS NOT NULL AND status='closed'
  GROUP BY 1
)
SELECT count(*) AS n_families,
       count(*) FILTER (WHERE pnl>0) AS profitable_families,
       count(*) FILTER (WHERE pnl<=0) AS losing_families,
       count(*) FILTER (WHERE n>=5 AND pnl>0) AS profitable_families_ge5
FROM fam
""")

q("Family PnL ranking 30d (all families)", """
WITH fam AS (
  SELECT regexp_replace(split_part(signal, ',', 1), '[+-]+$', '') AS family,
         count(*) AS n,
         round(100.0*avg(CASE WHEN pnl_usdt>0 THEN 1.0 ELSE 0.0 END),1) AS wr_pct,
         round(sum(pnl_usdt)::numeric,2) AS pnl
  FROM trades
  WHERE close_time >= now() - interval '30 days' AND pnl_usdt IS NOT NULL AND status='closed'
  GROUP BY 1
)
SELECT * FROM fam WHERE pnl > 0 ORDER BY pnl DESC
""")

# ══════════════════════════════════════════════════════════════════════
# Hourly PnL 30d (audit §7/Q7 claims)
# ══════════════════════════════════════════════════════════════════════
print("\n" + "#"*70)
print("# HOURLY PnL 30d (audit: 03h worst -3.45/52T 38.5%WR; 16-19h best)")
print("#"*70)

q("Hourly PnL 30d", """
SELECT date_part('hour', open_time) AS hr,
       count(*) AS n,
       round(100.0*avg(CASE WHEN pnl_usdt>0 THEN 1.0 ELSE 0.0 END),1) AS wr_pct,
       round(sum(pnl_usdt)::numeric,2) AS pnl
FROM trades
WHERE close_time >= now() - interval '30 days' AND pnl_usdt IS NOT NULL AND status='closed'
  AND open_time IS NOT NULL
GROUP BY 1 ORDER BY 1
""")

# ══════════════════════════════════════════════════════════════════════
# 7d signal label split (audit: 118 trades 7d)
# ══════════════════════════════════════════════════════════════════════
q("7d tiers sanity", """
SELECT array_length(string_to_array(signal,','),1) AS src_n, count(*) AS n,
       round(sum(pnl_usdt)::numeric,2) AS pnl
FROM trades
WHERE close_time >= now() - interval '7 days' AND pnl_usdt IS NOT NULL AND status='closed'
GROUP BY 1 ORDER BY 1
""")

conn.close()
print("\nDONE PART 2")
