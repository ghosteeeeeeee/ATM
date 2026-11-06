#!/usr/bin/env python3
"""C1b: direction-aligned >=3% touch (fixed), plus state-construction hunt for n=2856."""
import sqlite3, sys
import numpy as np, talib
from math import comb
sys.path.insert(0,'/root/.hermes/scripts')
import backtest_atr60_momentum as B

c=sqlite3.connect('/root/.hermes/data/candles.db')
r=c.execute("SELECT ts,high,low,close FROM candles_1m WHERE token='BTC' ORDER BY ts ASC").fetchall(); c.close()
ts=np.array([x[0] for x in r],dtype=np.int64); h=np.array([x[1] for x in r]); l=np.array([x[2] for x in r]); px=np.array([x[3] for x in r])
atr=talib.ATR(h,l,px,14); rsi=talib.RSI(px,14)
mh=np.array([np.nan if v is None else v for v in B.tv_macd_hist(list(px))])
def dir_at(i):
    m=0 if np.isnan(mh[i]) else (1 if mh[i]>0 else (-1 if mh[i]<0 else 0))
    rr=0 if np.isnan(rsi[i]) else (1 if rsi[i]>50 else (-1 if rsi[i]<50 else 0))
    return m if (m!=0 and m==rr) else 0
def events(a,thr,hy=0.9):
    ev,armed=[],True
    for i in range(1,len(a)):
        a0,a1=a[i-1],a[i]
        if np.isnan(a0) or np.isnan(a1): continue
        if armed and a0<thr<=a1: ev.append(i); armed=False
        if not armed and a1<thr*hy: armed=True
    return ev
def touch_dir(i,d):
    t0=ts[i]; p0=px[i]; end=t0+1440*60; j=i+1
    while j<len(ts) and ts[j]<=end:
        pct=(px[j]/p0-1)*100*d
        if pct>=3: return 1
        if pct<=-3: return -1
        j+=1
    return 0

ev=[i for i in events(atr,60,0.9) if i<len(ts)-15]
base=[i for i in range(0,len(ts),60) if i<len(ts)-15]
ev=[i for i in ev if dir_at(i)!=0]; base=[i for i in base if dir_at(i)!=0]
print(f'tradeable events={len(ev)} direction-filtered baseline={len(base)}')
e3=[touch_dir(i,dir_at(i)) for i in ev]; b3=[touch_dir(i,dir_at(i)) for i in base]
eh=sum(1 for x in e3 if x!=0); bh=sum(1 for x in b3 if x!=0)
print(f'>=3% within 24h: ev {eh}/{len(e3)}={100*eh/len(e3):.1f}%  base {bh}/{len(b3)}={100*bh/len(b3):.1f}%')
ind=sum(1 for x in e3 if x==1); n=eh
p=sum(comb(n,i) for i in range(ind,n+1))/2**n
print(f'ev big-move direction: {ind}/{n} in momentum dir, one-sided p={p:.4f}  (spec: 14/18, p=0.015)')
indb=sum(1 for x in b3 if x==1)
print(f'base big-move direction: {indb}/{bh} = {100*indb/bh:.1f}%  (spec: 51.2%)')

# state construction hunt for n~2856
evset=set(events(atr,60,0.9))
cand=[i for i in range(len(ts)) if not np.isnan(atr[i]) and atr[i]>=60 and i not in evset and i<len(ts)-15]
def fwd(i,hz):
    tgt=ts[i]+hz*60; j=np.searchsorted(ts,tgt)
    if j<len(ts) and ts[j]==tgt: pass
    elif j<len(ts) and abs(int(ts[j])-tgt)<=60: pass
    elif j>0 and abs(int(ts[j-1])-tgt)<=60: j-=1
    else: return None
    return abs(px[j]/px[i]-1)*100
print(f'\nraw state n={len(cand)}')
# variant: exclude minutes within +/- X min of an event
for X in (30,60,120,240):
    evts=ts[list(evset)]
    import bisect
    sel=[i for i in cand if not any(abs(ts[i]-t)<=X*60 for t in evts)]
    print(f'  exclude within {X}min of an event: n={len(sel)}')
# variant: spacing
for sp in (60,120,300,600,900,1800):
    out=[]; last=-10**18
    for i in cand:
        if ts[i]-last>=sp: out.append(i); last=ts[i]
    v=[x for x in (fwd(i,60) for i in out) if x is not None]
    print(f'  spacing {sp}s: n={len(out)} mean|1h|={np.mean(v):.3f}%')
# variant: spacing120s + report all horizons means
def rep(idxs,label):
    row=[]
    for hz in (60,240,1440):
        v=[x for x in (fwd(i,hz) for i in idxs) if x is not None]
        row.append(f'{hz}m n={len(v)} mean={np.mean(v):.3f}')
    print(f'  {label}: '+' | '.join(row))
out=[]; last=-10**18
for i in cand:
    if ts[i]-last>=120: out.append(i); last=ts[i]
rep(out,'spacing120')
