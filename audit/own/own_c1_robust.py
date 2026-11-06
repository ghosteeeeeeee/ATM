#!/usr/bin/env python3
"""C1 robustness: (a) does the MACD/RSI-agree FILTER itself select bigger moves?
(b) state baseline excluding ALL raw-cross minutes + +/-15min around events."""
import sqlite3, numpy as np, talib, sys
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
def fwd(i,hz,aligned=False):
    tgt=ts[i]+hz*60; j=np.searchsorted(ts,tgt)
    if j<len(ts) and ts[j]==tgt: pass
    elif j<len(ts) and abs(int(ts[j])-tgt)<=60: pass
    elif j>0 and abs(int(ts[j-1])-tgt)<=60: j-=1
    else: return None
    if j<=i: return None
    v=(px[j]/px[i]-1)*100
    return abs(v)
raw=events(atr,60,1.0); dec=events(atr,60,0.9)
agree=[i for i in dec if dir_at(i)!=0]; dis=[i for i in dec if dir_at(i)==0]
print(f'(a) declustered events: agree={len(agree)} disagree/skip={len(dis)}')
for hz in (60,240,1440):
    A=[v for v in (fwd(i,hz) for i in agree) if v is not None]
    D=[v for v in (fwd(i,hz) for i in dis) if v is not None]
    if A and D:
        print(f'   {hz}m: agree |move|={np.mean(A):.3f}% (n={len(A)})  skip |move|={np.mean(D):.3f}% (n={len(D)})  diff={np.mean(A)-np.mean(D):+.3f}')
# (b) state excluding raw-cross minutes and +/-15 min around declustered events
evset=set(dec); rawset=set(raw)
ev_t=ts[list(evset)]
def state_mask(excl_raw=True, pad=0):
    out=[]
    last=-10**18
    for i in range(len(ts)-15):
        if np.isnan(atr[i]) or atr[i]<60 or i in evset: continue
        if excl_raw and i in rawset: continue
        if pad:
            if any(abs(int(ts[i])-int(t))<=pad*60 for t in ev_t): continue
        if ts[i]-last>=3600: out.append(i); last=ts[i]
    return out
base=[i for i in range(0,len(ts),60) if i<len(ts)-15]
for label,kw in [('state (hourly, excl declustered-ev)',dict(excl_raw=False,pad=0)),
                 ('state excl ALL raw-cross minutes',dict(excl_raw=True,pad=0)),
                 ('state excl +/-15min around events',dict(excl_raw=True,pad=15)),
                 ('state excl +/-60min around events',dict(excl_raw=True,pad=60))]:
    S=state_mask(**kw)
    row=[]
    for hz in (60,240,1440):
        E=[v for v in (fwd(i,hz) for i in agree) if v is not None]
        V=[v for v in (fwd(i,hz) for i in S) if v is not None]
        row.append(f'{hz}m ev={np.mean(E):.3f} st={np.mean(V):.3f} d={np.mean(E)-np.mean(V):+.3f} (n_st={len(V)})')
    print(f'(b) {label}: '+' | '.join(row))
