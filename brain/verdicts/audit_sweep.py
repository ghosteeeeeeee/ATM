#!/usr/bin/env python3
"""Threshold/window sweep: does 90m/4 actually beat baselines?"""
import sqlite3, math
from datetime import datetime, timezone
from collections import defaultdict

CAND='/root/.hermes/data/candles.db'
sc=sqlite3.connect('/root/.hermes/data/signals_hermes_runtime.db')
rows=sc.execute("""SELECT token,direction,created_at,price FROM signals
 WHERE decision IN ('PENDING','EXPIRED') AND created_at > datetime('now','-7 days')
   AND source NOT LIKE '%,%' AND price>0""").fetchall()
sc.close()
def ep(s): return int(datetime.strptime(s,'%Y-%m-%d %H:%M:%S').replace(tzinfo=timezone.utc).timestamp())
g=defaultdict(list)
for tok,d,ca,p in rows: g[(tok,d)].append(ep(ca))
cc=sqlite3.connect(f'file:{CAND}?mode=ro',uri=True,timeout=60)
def fwd(tok,t,h=60):
    e=cc.execute('SELECT close FROM candles_1m WHERE token=? AND ts<=? ORDER BY ts DESC LIMIT 1',(tok,t)).fetchone()
    x=cc.execute('SELECT close FROM candles_1m WHERE token=? AND ts<=? ORDER BY ts DESC LIMIT 1',(tok,t+h*60)).fetchone()
    if not e or not x: return None
    return (x[0]-e[0])/e[0]*100

def run(win_min, thresh):
    rets=[]
    for (tok,d),ts in g.items():
        ts=sorted(ts)
        for i,t in enumerate(ts):
            wstart=t-win_min*60
            cnt=sum(1 for j in range(i+1) if ts[j]>=wstart)
            if cnt>=thresh:
                r=fwd(tok,t)
                if r is None: continue
                if d=='SHORT': r=-r
                rets.append(r)
    n=len(rets)
    if not n: return None
    w=sum(1 for x in rets if x>0)
    return n, w/n*100, sum(rets), sum(rets)/n

print(f"{'win':>5} {'thresh':>6} {'n':>5} {'WR%':>6} {'total%':>8} {'avg%':>7}")
print("-"*45)
for win in (30,60,90,120):
    for thresh in (2,3,4,5):
        r=run(win,thresh)
        if r:
            n,wr,tot,avg=r
            print(f"{win:>5} {thresh:>6} {n:>5} {wr:>6.1f} {tot:>+8.2f} {avg:>+7.3f}")
print()
print("BASELINE (thresh=1): n=1222 WR=48.3% total=+151.11% avg=+0.124%")
cc.close()
