#!/usr/bin/env python3
"""Test: does the claim reproduce when 30m momentum is anchored at CLOSE time
on the 41-trade SQLite trade_log set (which has no open_time)?"""
import sqlite3, statistics as st, datetime as dt
from collections import Counter

CAND = sqlite3.connect("file:/root/.hermes/data/candles.db?mode=ro", uri=True, timeout=10)
SQ = sqlite3.connect("/root/.hermes/brain/associative_memory.db")

rows = SQ.execute("""
    SELECT id, token, signal, won, pnl_pct, close_time FROM trade_log
    WHERE direction='LONG' AND signal LIKE '%pump-chain%'
      AND close_time >= '2026-09-26'
    ORDER BY close_time""").fetchall()
print(f"SQLite set n={len(rows)} W={sum(1 for r in rows if r[3]==1)} L={sum(1 for r in rows if r[3]==0)}")

def to_epoch(s):
    s = s.replace('T',' ').split('+')[0]
    return dt.datetime.fromisoformat(s).replace(tzinfo=dt.timezone.utc).timestamp()

def mom(token, anchor, n, step, closed_only):
    ts=int(anchor)
    if closed_only:
        q=f"SELECT close FROM candles_5m WHERE token=? AND is_closed=1 AND ts+{step}<=? ORDER BY ts DESC LIMIT {n}"
    else:
        q=f"SELECT close FROM candles_5m WHERE token=? AND is_closed=1 AND ts<=? ORDER BY ts DESC LIMIT {n}"
    cl=[r[0] for r in CAND.execute(q,(token.upper(),ts)).fetchall()]
    if len(cl)<n or cl[-1]==0: return None
    return (cl[0]-cl[-1])/cl[-1]*100

def analyze(data, field, thr=-0.1, label=""):
    have=[d for d in data if d.get(field) is not None]
    W=[d for d in have if d['won']==1]; L=[d for d in have if d['won']==0]
    bL=[d for d in L if d[field]<thr]; bW=[d for d in W if d[field]<thr]
    kL=[d for d in L if d[field]>=thr]; kW=[d for d in W if d[field]>=thr]
    wr=len(kW)/(len(kW)+len(kL))*100 if (kW or kL) else float('nan')
    wa=st.mean([d[field] for d in W]) if W else float('nan')
    la=st.mean([d[field] for d in L]) if L else float('nan')
    print(f"  [{label}] n={len(have)} {len(W)}W/{len(L)}L | BLOCKED {len(bL)}/{len(L)} losses, "
          f"{len(bW)}/{len(W)} wins | kept {len(kW)}W/{len(kL)}L WR {wr:.1f}% | "
          f"WINavg {wa:+.4f}% LOSSavg {la:+.4f}%")
    return wr

for label, anchor_field in [("ANCHOR=CLOSE_time", 'close_time')]:
    print(f"\n=== {label} : 30m momentum (6x5m candles) ===")
    data=[]
    for _id,tok,sig,won,pnl,ct in rows:
        a=to_epoch(ct)
        data.append(dict(won=won, m=mom(tok,a,6,300,True), m2=mom(tok,a,6,300,False),
                         m5=mom(tok,a,6,60,True)))
    analyze(data,'m', -0.1, "30m closed-candles")
    analyze(data,'m2',-0.1, "30m any-candles")
    print("=== 5m momentum (6x1m) at CLOSE ===")
    analyze(data,'m5',-0.1, "5m closed 1m-candles")

# Also: PG anchored at CLOSE to isolate set-vs-anchor
print("\n\n=== PG set (44) anchored at CLOSE_time, 30m momentum ===")
import psycopg2
pg=psycopg2.connect(host='/var/run/postgresql',database='brain',user='postgres',connect_timeout=5)
cur=pg.cursor()
cur.execute("""SELECT token, pnl_pct, close_time FROM trades
    WHERE direction='LONG' AND signal LIKE '%pump-chain%' AND close_time>='2026-09-26'
    ORDER BY close_time""")
data=[]
for tok,pnl,ct in cur.fetchall():
    a=to_epoch(str(ct)); data.append(dict(won=1 if pnl>0 else 0, m=mom(tok,a,6,300,True)))
analyze(data,'m',-0.1,"PG close-anchored 30m")
