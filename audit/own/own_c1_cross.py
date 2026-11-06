#!/usr/bin/env python3
"""C1 cross-coin: per-coin p85 ATR% cross, non-overlapping 1h windows, ev vs random |1h move|."""
import sqlite3, sys, time
import numpy as np, talib
from math import comb
DB='/root/.hermes/data/candles.db'
COINS=['BTC','SOL','SUI','TAO','PUMP','GALA','GMX','IMX','SAND','FOGO','COMP','DYM']
def load(t):
    c=sqlite3.connect(DB); r=c.execute("SELECT ts,high,low,close FROM candles_1m WHERE token=? ORDER BY ts ASC",(t,)).fetchall(); c.close()
    return (np.array([x[0] for x in r],dtype=np.int64), np.array([x[1] for x in r]),
            np.array([x[2] for x in r]), np.array([x[3] for x in r]))
def events(a,thr,hy=0.9):
    ev,armed=[],True
    for i in range(1,len(a)):
        a0,a1=a[i-1],a[i]
        if np.isnan(a0) or np.isnan(a1): continue
        if armed and a0<thr<=a1: ev.append(i); armed=False
        if not armed and a1<thr*hy: armed=True
    return ev
def fwd(ts,c,i,hz):
    tgt=ts[i]+hz*60; j=np.searchsorted(ts,tgt)
    if j<len(ts) and ts[j]==tgt: pass
    elif j<len(ts) and abs(int(ts[j])-tgt)<=60: pass
    elif j>0 and abs(int(ts[j-1])-tgt)<=60: j-=1
    else: return None
    if j<=i: return None
    return abs(c[j]/c[i]-1)*100
def thin(idxs,ts,sp):
    out=[]; last=-10**18
    for i in idxs:
        if ts[i]-last>=sp: out.append(i); last=ts[i]
    return out
def boot(a,b,rounds=3000,seed=5):
    rng=np.random.default_rng(seed); a=np.asarray(a); b=np.asarray(b)
    ds=np.array([rng.choice(a,len(a)).mean()-rng.choice(b,len(b)).mean() for _ in range(rounds)])
    return np.percentile(ds,[2.5,97.5])
rows=[]; diffs=[]
t0=time.time()
for ck in COINS:
    ts,h,l,c=load(ck)
    if len(ts)<1000: print(ck,'insufficient'); continue
    atr=talib.ATR(h,l,c,14); ap=atr/c*100
    thr=np.nanpercentile(ap,85)
    ev=thin([i for i in events(ap,thr,0.9) if i<len(ts)-15],ts,3600)
    base=thin([i for i in range(0,len(ts),60) if i<len(ts)-15],ts,3600)
    E=[x for x in (fwd(ts,c,i,60) for i in ev) if x is not None]
    Bv=[x for x in (fwd(ts,c,i,60) for i in base) if x is not None]
    if len(E)<10: print(f'{ck}: too few events ({len(E)})'); continue
    d=np.mean(E)-np.mean(Bv); lo,hi=boot(E,Bv)
    diffs.append(d); rows.append((ck,len(E),len(Bv),np.mean(E),np.mean(Bv),d,lo,hi))
    print(f'{ck:>5} n={len(E):>4}/{len(Bv):>4}  ev={np.mean(E):.3f}% base={np.mean(Bv):.3f}% diff={d:+.3f}% CI[{lo:+.3f},{hi:+.3f}] {"SIG" if lo>0 else ""}  p85={thr:.4f}%',flush=True)
pos=sum(1 for d in diffs if d>0); n=len(diffs)
p=sum(comb(n,i) for i in range(pos,n+1))/2**n
print(f'\npositive: {pos}/{n}  sign-test one-sided p={p:.4f}   (spec: 12/12, 8/12 sig, p=0.0002)  [{time.time()-t0:.0f}s]')
