#!/usr/bin/env python3
"""Independent audit (fresh eyes) — cohort introspection for the mfe-exit sim.
Does NOT import jup_exit_sim. Re-derives the cohort from scratch."""
import sys, os
sys.path.insert(0, '/root/.hermes/scripts')
import psycopg2
from _secrets import BRAIN_DB_DICT

cfg = BRAIN_DB_DICT.copy(); cfg.setdefault('port', 5432)
conn = psycopg2.connect(**cfg); conn.autocommit = True
cur = conn.cursor()

def q(sql, args=()):
    cur.execute(sql, args)
    return cur.fetchall()

print("== total trades with jup_yolo in signal ==")
print(q("""SELECT status, count(*), count(*) FILTER (WHERE entry_price IS NULL),
  count(*) FILTER (WHERE exit_price IS NULL) FROM trades
  WHERE signal LIKE %s GROUP BY status ORDER BY status""", ('%jup_yolo%',)))

print("\n== closed + entry/exit NOT NULL (the sim's cohort) ==")
print(q("""SELECT count(*), min(close_time), max(close_time) FROM trades
  WHERE signal LIKE %s AND status='closed' AND entry_price IS NOT NULL
  AND exit_price IS NOT NULL""", ('%jup_yolo%',)))

print("\n== closed but NULL exit_price (excluded by sim) ==")
for r in q("""SELECT id, token, direction, status, entry_price, exit_price, pnl_pct,
  open_time, close_time, close_reason, leverage FROM trades
  WHERE signal LIKE %s AND status='closed' AND exit_price IS NULL
  ORDER BY id""", ('%jup_yolo%',)):
    print("  ", r)

print("\n== non-closed (open/pending etc) with jup_yolo ==")
for r in q("""SELECT id, token, direction, status, entry_price, pnl_pct, open_time,
  leverage, signal FROM trades WHERE signal LIKE %s AND status<>'closed'
  ORDER BY id""", ('%jup_yolo%',)):
    print("  ", r)

print("\n== distinct signals in cohort ==")
print(q("""SELECT signal, count(*) FROM trades
  WHERE signal LIKE %s AND status='closed' AND entry_price IS NOT NULL
  AND exit_price IS NOT NULL GROUP BY signal""", ('%jup_yolo%',)))

print("\n== leverage distribution in cohort ==")
print(q("""SELECT leverage, count(*) FROM trades
  WHERE signal LIKE %s AND status='closed' AND entry_price IS NOT NULL
  AND exit_price IS NOT NULL GROUP BY leverage ORDER BY 1""", ('%jup_yolo%',)))

print("\n== cohort rows (id, token, dir, entry, exit, pnl_pct, lev, open, close, reason, signal) ==")
rows = q("""SELECT id, token, direction, entry_price, exit_price, pnl_pct, leverage,
  open_time, close_time, close_reason, signal FROM trades
  WHERE signal LIKE %s AND status='closed' AND entry_price IS NOT NULL
  AND exit_price IS NOT NULL ORDER BY id""", ('%jup_yolo%',))
for r in rows:
    print("  ", r)

# leveraged-unit check: is pnl_pct == price% * leverage ?
print("\n== unit check: pnl_pct vs price%*lev vs price% ==")
bad = 0
for (tid, tok, d, en, ex, pnl, lev, ot, ct, rs, sig) in rows:
    p = (ex/en - 1)*100 if d == 'LONG' else (1 - ex/en)*100
    lev_amt = p * float(lev or 1)
    ok_lev = abs(lev_amt - float(pnl or 0)) < 0.05
    ok_raw = abs(p - float(pnl or 0)) < 0.05
    if not ok_lev:
        bad += 1
        print(f"  MISMATCH id={tid} lev_match={ok_lev} raw_match={ok_raw} pnl={pnl} price%={p:.4f} price%*lev={lev_amt:.4f} lev={lev}")
print(f"  rows where pnl_pct != price%*lev (tol .05): {bad} / {len(rows)}")

# time window: has the 12h horizon elapsed?
print("\n== horizon elapsed? close_time vs open_time+12h ==")
late = 0; soon = 0
for (tid, tok, d, en, ex, pnl, lev, ot, ct, rs, sig) in rows:
    import datetime as dt
    hz = ot + dt.timedelta(hours=12)
    if ct > hz:
        late += 1
    else:
        soon += 1
print(f"  closed at/before open+12h (horizon fully elapsed): {soon}; closed after 12h: {late}")
# actually horizon elapsed means open+12h is in the PAST now
import datetime as dt
now = dt.datetime.utcnow()
el = sum(1 for r in rows if r[7] + dt.timedelta(hours=12) <= now)
print(f"  trades whose open+12h is already in the past (fully observed): {el} / {len(rows)}")

# hold time distribution
holds = sorted(((r[8]-r[7]).total_seconds()/3600.0, r[0]) for r in rows)
print("\n== hold hours (actual closes): min/med/max =",
      round(holds[0][0],2), round(holds[len(holds)//2][0],2), round(holds[-1][0],2))
over12 = [h for h in holds if h[0] > 12]
print(f"  actual closes beyond 12h: {len(over12)} -> {over12[:10]}")

cur.close(); conn.close()
