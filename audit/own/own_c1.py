#!/usr/bin/env python3
"""Own-conclusions C1: |forward move| after ATR(14,1m) UP-cross vs
(1) random-time baseline, (2) ATR>=60 STATE baseline (high-ATR non-crossing minutes).
Fully independent implementation (talib ATR, own event detector, own outcome math)."""
import sqlite3, datetime, sys
import numpy as np, talib
from scipy import stats

DB='/root/.hermes/data/candles.db'
H=[15,30,60,240,1440]

def load(tok):
    c=sqlite3.connect(DB); r=c.execute("SELECT ts,high,low,close FROM candles_1m WHERE token=? ORDER BY ts ASC",(tok,)).fetchall(); c.close()
    return np.array([x[0] for x in r],dtype=np.int64), np.array([x[1] for x in r]), np.array([x[2] for x in r]), np.array([x[3] for x in r])

def events(a, thr, hy=0.9):
    ev,armed=[],True
    for i in range(1,len(a)):
        a0,a1=a[i-1],a[i]
        if np.isnan(a0) or np.isnan(a1): continue
        if armed and a0<thr<=a1: ev.append(i); armed=False
        if not armed and a1<thr*hy: armed=True
    return ev

def fwd_abs(ts,c,i,h):
    """|%| move from bar i close to bar i+h minutes (exact ts lookup, ±60s)."""
    tgt=ts[i]+h*60
    j=np.searchsorted(ts,tgt)
    if j<len(ts) and ts[j]==tgt: pass
    elif j<len(ts) and abs(int(ts[j])-tgt)<=60: pass
    elif j>0 and abs(int(ts[j-1])-tgt)<=60: j=j-1
    else: return None
    if j<=i: return None
    return abs(c[j]/c[i]-1)*100

def thin(idxs, ts, spacing_s):
    out=[]; last=-10**18
    for i in idxs:
        if ts[i]-last>=spacing_s: out.append(i); last=ts[i]
    return out

def ci_diff(a,b,rounds=4000,seed=7):
    rng=np.random.default_rng(seed); a=np.asarray(a); b=np.asarray(b)
    ds=np.empty(rounds)
    for k in range(rounds):
        ds[k]=rng.choice(a,len(a)).mean()-rng.choice(b,len(b)).mean()
    return np.percentile(ds,[2.5,97.5])

ts,h,l,c=load('BTC')
atr=talib.ATR(h,l,c,14)
ev_all=events(atr,60,0.9)
ev_trade=[i for i in ev_all if i<len(ts)-15]   # direction filter irrelevant for |move|
print(f'BTC declustered events: {len(ev_all)}  usable(n<end-15): {len(ev_trade)}')

base=[i for i in range(0,len(ts),60) if i<len(ts)-15]
print(f'random baseline (every 60th bar): {len(base)}')

print('\n--- (1) events vs RANDOM baseline |move| ---')
for hz in (60,240,1440):
    e=[v for v in (fwd_abs(ts,c,i,hz) for i in ev_trade) if v is not None]
    b=[v for v in (fwd_abs(ts,c,i,hz) for i in base) if v is not None]
    lo,hi=ci_diff(e,b,seed=11)
    print(f'  {hz:>4}m: ev n={len(e)} mean={np.mean(e):.3f}%  base n={len(b)} mean={np.mean(b):.3f}%  '
          f'diff={np.mean(e)-np.mean(b):+.3f}%  CI[{lo:+.3f},{hi:+.3f}]')

# --- (2) STATE baseline: variants to identify the spec's n=2856 construction ---
print('\n--- state-baseline construction hunt (ATR>=60, events excluded) ---')
evset=set(ev_all)
evset_t=set(ev_trade)
for name,cond in [
  ('all ATR>=60 usable, excl declustered-ev', [i for i in range(len(ts)) if not np.isnan(atr[i]) and atr[i]>=60 and i not in evset and i<len(ts)-15]),
  ('all ATR>=60 usable, excl tradeable-ev',    [i for i in range(len(ts)) if not np.isnan(atr[i]) and atr[i]>=60 and i not in evset_t and i<len(ts)-15]),
  ('all ATR>=60 usable (events included)',     [i for i in range(len(ts)) if not np.isnan(atr[i]) and atr[i]>=60 and i<len(ts)-15]),
]:
    print(f'  {name}: n={len(cond)}')

state=[i for i in range(len(ts)) if not np.isnan(atr[i]) and atr[i]>=60 and i not in evset and i<len(ts)-15]
print('\n--- (2) events vs ATR>=60 STATE baseline |move| ---')
for hz in (60,240,1440):
    e=[v for v in (fwd_abs(ts,c,i,hz) for i in ev_trade) if v is not None]
    s=[v for v in (fwd_abs(ts,c,i,hz) for i in state) if v is not None]
    lo,hi=ci_diff(e,s,seed=13)
    print(f'  {hz:>4}m: ev n={len(e)} mean={np.mean(e):.3f}%  state n={len(s)} mean={np.mean(s):.3f}%  '
          f'diff={np.mean(e)-np.mean(s):+.3f}%  CI[{lo:+.3f},{hi:+.3f}]')

# ATR quartile monotonicity check (spec: 0.14 -> 0.20 -> 0.24 -> 0.39 @1h)
q=np.nanpercentile(atr,[25,50,75])
print('\n--- |1h move| by ATR quartile (all usable minutes) ---')
ok=[i for i in range(len(ts)) if not np.isnan(atr[i]) and i<len(ts)-15]
labs=['Q1','Q2','Q3','Q4']
for k in range(4):
    if k==0: sel=[i for i in ok if atr[i]<=q[0]]
    elif k==3: sel=[i for i in ok if atr[i]>q[2]]
    else: sel=[i for i in ok if q[k-1]<atr[i]<=q[k]]
    v=[x for x in (fwd_abs(ts,c,i,60) for i in sel) if x is not None]
    print(f'  {labs[k]} (ATR<={q[min(k,2)]:.0f}): n={len(v)} mean|1h|={np.mean(v):.3f}%')

# >=3% move within 24h: events vs baseline (z test) + direction of big moves
print('\n--- >=3% move within 24h ---')
def touch3(i):
    t0=ts[i]; p0=c[i]; end=t0+1440*60
    j=i+1; hit=0
    while j<len(ts) and ts[j]<=end:
        pct=(c[j]/p0-1)*100
        if pct>=3: hit=1; break
        if pct<=-3: hit=-1; break
        j+=1
    return hit
ev3=[touch3(i) for i in ev_trade]; bs3=[touch3(i) for i in base]
eh=sum(1 for x in ev3 if x!=0); bh=sum(1 for x in bs3 if x!=0)
z=(eh/len(ev3)-bh/len(bs3))/np.sqrt((eh/len(ev3)*(1-eh/len(ev3))/len(ev3))+(bh/len(bs3)*(1-bh/len(bs3))/len(bs3)))
print(f'  events {eh}/{len(ev3)}={100*eh/len(ev3):.1f}%  base {bh}/{len(bs3)}={100*bh/len(bs3):.1f}%  z={z:.2f} p={2*(1-stats.norm.cdf(abs(z))):.3f}')
ind=sum(1 for x in ev3 if x==1); n3=eh
from math import comb
pv=sum(comb(n3,i) for i in range(ind,n3+1))/2**n3
print(f'  big-move direction: {ind}/{n3} in momentum dir, one-sided binom p={pv:.4f}')
indb=sum(1 for x in bs3 if x==1); nb=bh
print(f'  baseline big-move direction: {indb}/{nb} = {100*indb/nb:.1f}%')
