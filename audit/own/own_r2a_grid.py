#!/usr/bin/env python3
"""Independent R2a grid: rules x trend-TFs, pooled ev vs ATR-state vs random,
24h direction-aligned. Mirrors spec section 5b table (my own code, talib)."""
import sqlite3, sys
import numpy as np, talib
from math import comb
DB='/root/.hermes/data/candles.db'
COINS=['BTC','SOL','SUI','TAO','PUMP','GALA','GMX','IMX','SAND','FOGO','COMP','DYM']
THR=0.076; HZ=1440
def load(tok,tab):
    c=sqlite3.connect(DB)
    r=c.execute(f"SELECT ts,high,low,close FROM {tab} WHERE token=? ORDER BY ts ASC",(tok,)).fetchall(); c.close()
    return (np.array([x[0] for x in r],dtype=np.int64),np.array([x[1] for x in r]),np.array([x[2] for x in r]),np.array([x[3] for x in r])) if r else None
def events(a,thr,hy=0.9):
    ev,armed=[],True
    for i in range(1,len(a)):
        a0,a1=a[i-1],a[i]
        if np.isnan(a0) or np.isnan(a1): continue
        if armed and a0<thr<=a1: ev.append(i); armed=False
        if not armed and a1<thr*hy: armed=True
    return ev
def fwd(ts,c,i,d):
    tgt=ts[i]+HZ*60; j=np.searchsorted(ts,tgt)
    if j<len(ts) and ts[j]==tgt: pass
    elif j<len(ts) and abs(int(ts[j])-tgt)<=60: pass
    elif j>0 and abs(int(ts[j-1])-tgt)<=60: j-=1
    else: return None
    if j<=i: return None
    return (c[j]/c[i]-1)*100*d
IV={'5m':300,'15m':900,'1h':3600,'4h':14400}
def rule_fns(ck):
    """returns dict name -> fn(t)->+1/-1/0, plus strict fn"""
    out={}
    dirs={}
    for tf in ('5m','15m','1h','4h'):
        d=load(ck,f'candles_{tf}')
        if d is None: dirs[tf]=None; continue
        hts,hc=d[0],d[3]
        e20=talib.EMA(hc,20); e50=talib.EMA(hc,50); mh=talib.MACD(hc,12,26,9)[2]  # hist
        sn=max(6,int(3600/IV[tf]))
        def mk(e20,e50,hts,iv=IV[tf]):
            def f(t):
                k=np.searchsorted(hts,t-iv,side='right')-1
                if k<50 or np.isnan(e20[k]) or np.isnan(e50[k]): return 0
                return 1 if e20[k]>e50[k] else -1
            return f
        def mkm(mh,hts,iv=IV[tf]):
            def f(t):
                k=np.searchsorted(hts,t-iv,side='right')-1
                if k<30 or np.isnan(mh[k]): return 0
                return 1 if mh[k]>0 else (-1 if mh[k]<0 else 0)
            return f
        def mks(hc,hts,sn=sn,iv=IV[tf]):
            def f(t):
                k=np.searchsorted(hts,t-iv,side='right')-1
                if k<sn: return 0
                r=(hc[k]/hc[k-sn]-1)*100
                return 1 if r>0 else (-1 if r<0 else 0)
            return f
        dirs[tf]=(mk(e20,e50,hts), mkm(mh,hts), mks(hc,hts))
    for tf in ('5m','15m','1h'):
        if dirs.get(tf) is None or dirs.get('4h') is None: continue
        ema_fn,macd_fn,slope_fn=dirs[tf]; ema4=dirs['4h'][0]
        out[f'ema_{tf}']=ema_fn
        out[f'macd_{tf}']=macd_fn
        out[f'slope6_{tf}']=slope_fn
        out[f'ema_4h']=ema4
        out[f'{tf}+4h agree']=lambda t,f1=ema_fn,f2=ema4: (f1(t) if f1(t)==f2(t) and f1(t)!=0 else 0)
    return out, dirs
res={}
for ck in COINS:
    m1=load(ck,'candles_1m'); h15=load(ck,'candles_15m'); h4=load(ck,'candles_4h')
    ts,h,l,c=m1
    atr=talib.ATR(h,l,c,14); ap=atr/c*100
    mh1=np.array([np.nan if v is None else v for v in talib.MACD(c,12,26,9)[2]])  # hist
    rsi=talib.RSI(c,14)
    rules,dirs=rule_fns(ck)
    ev=[i for i in events(ap,THR,0.9) if i<len(ts)-15]; evset=set(ev)
    base=[i for i in range(0,len(ts),60) if i<len(ts)-15]
    state=[]; last=-10**18
    for i in range(len(ts)-15):
        if not np.isnan(ap[i]) and ap[i]>=THR and i not in evset and ts[i]-last>=3600:
            state.append(i); last=ts[i]
    names=list(rules)+['STRICT']
    for nm in names:
        for tag,idx in (('ev',ev),('state',state),('base',base)):
            for i in idx:
                if nm=='STRICT':
                    if dirs.get('15m') is None or dirs.get('4h') is None: continue
                    d=dirs['15m'][0](ts[i])
                    if d==0: continue
                    m=0 if np.isnan(mh1[i]) else (1 if mh1[i]>0 else (-1 if mh1[i]<0 else 0))
                    rr=0 if np.isnan(rsi[i]) else (1 if rsi[i]>50 else (-1 if rsi[i]<50 else 0))
                    if m==0 or m!=d or rr!=d: continue
                else:
                    d=rules[nm](ts[i])
                    if d==0: continue
                v=fwd(ts,c,i,d)
                if v is None: continue
                res.setdefault((nm,tag),[]).append(v)
print(f"{'rule':>16} {'ev n':>6} {'ev mean':>8} {'ev WR':>7} | {'state mean':>10} | {'ev-state':>9} {'iidCI':>18} | {'ev-rand':>9} | {'signs':>6}")
rng=np.random.default_rng(3)
for nm in sorted({k[0] for k in res}):
    E=np.array(res.get((nm,'ev'),[])); S=np.array(res.get((nm,'state'),[])); R=np.array(res.get((nm,'base'),[]))
    if len(E)<50 or len(S)<30: continue
    ds=np.array([rng.choice(E,len(E)).mean()-rng.choice(S,len(S)).mean() for _ in range(3000)])
    # per-coin signs
    pos=neg=0
    for ck in COINS:
        # per-coin ev/state means
        pass
    print(f'{nm:>16} {len(E):>6} {E.mean():>+8.3f} {100*(E>0).mean():>6.1f}% | {S.mean():>+10.3f} | '
          f'{E.mean()-S.mean():>+9.3f} [{np.percentile(ds,2.5):>+7.3f},{np.percentile(ds,97.5):>+7.3f}] | '
          f'{E.mean()-R.mean():>+9.3f} |  --')
