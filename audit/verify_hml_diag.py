#!/usr/bin/env python3
"""Diagnose the HML 63/70 claim: try window/method variants to see which reproduces it."""
import sqlite3, psycopg2, datetime as dt

CAND = sqlite3.connect("file:/root/.hermes/data/candles.db?mode=ro", uri=True)
PG = psycopg2.connect(host="/var/run/postgresql", dbname="brain", user="postgres")
pc = PG.cursor()
pc.execute("""
  SELECT id, token, direction, entry_price, open_time, close_time, mfe_pct, mae_pct, highest_price, lowest_price
  FROM trades
  WHERE status='closed' AND paper='f' AND exit_reason='hard_max_loss'
    AND close_time >= now() - interval '30 days'
  ORDER BY open_time""")
rows = pc.fetchall()
print(f"hard_max_loss closed in last 30d: {len(rows)}")

recs = []
for (tid, tok, dire, entry, ot, ct, mfe, mae, hi, lo) in rows:
    ots = int(ot.replace(tzinfo=dt.timezone.utc).timestamp())
    cts = int(ct.replace(tzinfo=dt.timezone.utc).timestamp())
    r = CAND.execute("SELECT ts, high, low, close FROM candles_1m WHERE token=? AND ts>=? AND ts<=?",
                     (tok.upper(), ots - 60, cts + 60)).fetchall()
    if not r:
        recs.append((tid, tok, dire, ot, ct, None, None, None, mfe)); continue
    e = float(entry); sgn = 1 if dire == 'LONG' else -1
    pd_ = max(((h - e) / e * 100 * sgn if sgn > 0 else (e - l) / e * 100) for (ts, h, l, c) in r)
    pc_ = max(((c - e) / e * 100 * sgn) for (ts, h, l, c) in r)
    # excluding the candle that contains the entry minute
    r2 = [x for x in r if x[0] + 60 > ots + 60]
    pd2 = max(((h - e) / e * 100 * sgn if sgn > 0 else (e - l) / e * 100) for (ts, h, l, c) in r2) if r2 else None
    recs.append((tid, tok, dire, ot, ct, pd_, pc_, pd2, mfe))

def report(label, sel):
    xs = sorted(x[5] for x in sel if x[5] is not None)
    if not xs:
        print(f"  {label}: EMPTY"); return
    n = len(xs)
    print(f"  {label}: n={n}  <0.40%: {sum(1 for v in xs if v < 0.40)}  median={xs[n//2]:+.3f}%  mean={sum(xs)/n:+.3f}%")

print("\nwindow variants (direction-aware candle peak):")
report("close_time >= now-14d", [x for x in recs if x[4] >= dt.datetime.utcnow() - dt.timedelta(days=14)])
report("open_time  >= now-14d", [x for x in recs if x[3] >= dt.datetime.utcnow() - dt.timedelta(days=14)])
report("close_time >= 2026-09-24 00:00", [x for x in recs if x[4] >= dt.datetime(2026, 9, 24)])
report("close_time >= 2026-09-24 21:00", [x for x in recs if x[4] >= dt.datetime(2026, 9, 24, 21)])
report("last 70 by close_time", sorted(recs, key=lambda x: x[4])[-70:])
report("last 70 by open_time", sorted(recs, key=lambda x: x[3])[-70:])

print("\nmethod variants on close_time>=now-14d:")
sel = [x for x in recs if x[4] >= dt.datetime.utcnow() - dt.timedelta(days=14)]
report("candle HIGH/LOW direction-aware", sel)
report("candle CLOSE direction-aware   ", [(x[0],x[1],x[2],x[3],x[4],x[6],x[6],x[7],x[8]) for x in sel])
report("exclude entry candle          ", [(x[0],x[1],x[2],x[3],x[4],x[7],x[7],x[7],x[8]) for x in sel])
mfe_vals = sorted(float(x[8]) for x in sel if x[8] is not None)
print(f"  recorded mfe_pct: n={len(mfe_vals)} <0.40: {sum(1 for v in mfe_vals if v<0.40)} "
      f"median={mfe_vals[len(mfe_vals)//2]:+.3f}% nonzero={sum(1 for v in mfe_vals if v!=0)}")
PG.close(); CAND.close()
print("DONE hml-diag")
