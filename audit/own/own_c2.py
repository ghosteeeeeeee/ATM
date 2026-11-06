#!/usr/bin/env python3
"""Own C2: 1m MACD/RSI-agree direction at the ATR cross — BTC horizons + binomial,
plus cross-coin pooled big-move direction."""
import sqlite3, sys
import numpy as np, talib
from math import comb
sys.path.insert(0,'/root/.hermes/scripts')
import backtest_atr60_momentum as B
DB='/root/.hermes/data/candles.db'
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
def dir_at(mh,rsi,i):
    m=0 if np.isnan(mh[i]) else (1 if mh[i]>0 else (-1 if mh[i]<0 else 0))
    rr=0 if np.isnan(rsi[i]) else (1 if rsi[i]>50 else (-1 if rsi[i]<50 else 0))
    return m if (m!=0 and m==rr) else 0
def fwd(ts,c,i,hz,d):
    tgt=ts[i]+hz*60; j=np.searchsorted(ts,tgt)
    if j<len(ts) and ts[j]==tgt: pass
    elif j<len(ts) and abs(int(ts[j])-tgt)<=60: pass
    elif j>0 and abs(int(ts[j-1])-tgt)<=60: j-=1
    else: return None
    if j<=i: return None
    return (c[j]/c[i]-1)*100*d
def binom2(k,n):
    if n==0: return 1.0
    pu=sum(comb(n,i) for i in range(k,n+1))/2**n
    pd=sum(comb(n,i) for i in range(0,k+1))/2**n
    return min(1.0,2*min(pu,pd))
def boot(v,rounds=4000,seed=7):
    rng=np.random.default_rng(seed); v=np.asarray(v)
    m=np.array([rng.choice(v,len(v)).mean() for _ in range(rounds)])
    return np.percentile(m,[2.5,97.5])

# ---- BTC ----
ts,h,l,c=load('BTC')
atr=talib.ATR(h,l,c,14); rsi=talib.RSI(c,14)
mh=np.array([np.nan if v is None else v for v in B.tv_macd_hist(list(c))])
ev=[i for i in events(atr,60,0.9) if i<len(ts)-15]
print(f'BTC declustered={len(ev)}')
print('horizon |  n   mean dir%   WR>0%   CI95            two-sided binom p')
for hz in (15,30,60,240,1440):
    vals=[]; dirs=[]
    for i in ev:
        d=dir_at(mh,rsi,i)
        if d==0: continue
        v=fwd(ts,c,i,hz,d)
        if v is not None: vals.append(v); dirs.append(d)
    if not vals: continue
    k=sum(1 for x in vals if x>0); n=len(vals)
    lo,hi=boot(vals)
    print(f'{hz:>5}m  {n:>4}  {np.mean(vals):+8.3f}  {100*k/n:6.1f}%  [{lo:+.3f},{hi:+.3f}]  p={binom2(k,n):.3e}')
# entry at cross close losing first 15-30m: sign of mean
print('\n(n = tradeable events with determinable 1m direction)')

# ---- cross-coin pooled >=3% big-move direction ----
COINS8=['SOL','SUI','TAO','PUMP','GALA','GMX','IMX','SAND']
COINS12=['BTC','SOL','SUI','TAO','PUMP','GALA','GMX','IMX','SAND','FOGO','COMP','DYM']
def touch_dir(ts,c,i,d):
    t0=ts[i]; p0=c[i]; end=t0+1440*60; j=i+1
    while j<len(ts) and ts[j]<=end:
        pct=(c[j]/p0-1)*100*d
        if pct>=3: return 1
        if pct<=-3: return -1
        j+=1
    return 0
def pool(coins, mode):
    T=I=W=0
    per={}
    for ck in coins:
        ts,h,l,c=load(ck)
        atr=talib.ATR(h,l,c,14); rsi=talib.RSI(c,14)
        mh=np.array([np.nan if v is None else v for v in B.tv_macd_hist(list(c))])
        ap=atr/c*100
        thr=0.076 if mode=='abs' else np.nanpercentile(ap,85)
        ev=[i for i in events(ap,thr,0.9) if i<len(ts)-15]
        t_=i_=w_=0
        for i in ev:
            d=dir_at(mh,rsi,i)
            if d==0: continue
            r=touch_dir(ts,c,i,d)
            if r==1: t_+=1; I+=1
            elif r==-1: w_+=1; W+=1
        per[ck]=(t_,w_)
        T+=t_
    n=I+W
    print(f'  mode={mode} pooled big(>=3%) moves in-direction: {I}/{n} = {100*I/n:.1f}%  '
          f'(spec: abs 8-coin 672/626=51.8%; p85 12-coin 690/1361=50.7%)')
    print('   per-coin dir/opp:', {k:v for k,v in per.items()})
print('\nCross-coin pooled >=3% move direction (direction = 1m MACD/RSI agree):')
pool(COINS8,'abs')
pool(COINS12,'p85')
