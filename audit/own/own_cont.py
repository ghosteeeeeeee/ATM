#!/usr/bin/env python3
"""Own continuum direction tests: R2b/R2c (BTC, RECORDED scores) and R2d
(BTC + 12 coins, REPLAYED scores). Independent implementation."""
import sqlite3, datetime, sys
import numpy as np, talib
from math import comb
DB='/root/.hermes/data/candles.db'
COINS=['BTC','SOL','SUI','TAO','PUMP','GALA','GMX','IMX','SAND','FOGO','COMP','DYM']
def load(tok,tab='candles_1m'):
    c=sqlite3.connect(DB)
    r=c.execute(f"SELECT ts,high,low,close FROM {tab} WHERE token=? ORDER BY ts ASC",(tok,)).fetchall(); c.close()
    return (np.array([x[0] for x in r],dtype=np.int64),np.array([x[1] for x in r]),np.array([x[2] for x in r]),np.array([x[3] for x in r]))
def events(a,thr,hy=0.9):
    ev,armed=[],True
    for i in range(1,len(a)):
        a0,a1=a[i-1],a[i]
        if np.isnan(a0) or np.isnan(a1): continue
        if armed and a0<thr<=a1: ev.append(i); armed=False
        if not armed and a1<thr*hy: armed=True
    return ev
def load_scores(tok,src):
    p = '/root/.hermes/data/continuum_replay.db' if src=='replay' else '/root/.hermes/data/continuum.db'
    tab = 'continuum_replay' if src=='replay' else 'continuum_states'
    col = 'score' if src=='replay' else 'state_score'
    c=sqlite3.connect(p)
    r=c.execute(f"SELECT ts,{col} FROM {tab} WHERE token=? AND {col} IS NOT NULL ORDER BY ts",(tok,)).fetchall(); c.close()
    return np.array([x[0] for x in r],dtype=np.int64), np.array([x[1] for x in r],dtype=float)
def score_at(sts,ss,t):
    k=np.searchsorted(sts,t,side='right')-1
    return ss[k] if k>=0 else np.nan
def fwd(ts,c,i,hz,d):
    tgt=ts[i]+hz*60; j=np.searchsorted(ts,tgt)
    if j<len(ts) and ts[j]==tgt: pass
    elif j<len(ts) and abs(int(ts[j])-tgt)<=60: pass
    elif j>0 and abs(int(ts[j-1])-tgt)<=60: j-=1
    else: return None
    if j<=i: return None
    return (c[j]/c[i]-1)*100*d
def binom2(k,n):
    pu=sum(comb(n,i) for i in range(k,n+1))/2**n; pd=sum(comb(n,i) for i in range(0,k+1))/2**n
    return min(1.0,2*min(pu,pd))
def boot(a,b,rounds=3000,seed=21):
    rng=np.random.default_rng(seed); a=np.asarray(a); b=np.asarray(b)
    ds=np.array([rng.choice(a,len(a)).mean()-rng.choice(b,len(b)).mean() for _ in range(rounds)])
    return np.percentile(ds,[2.5,97.5])

def btc_study(src, flip, half=None):
    ts,h,l,c=load('BTC')
    atr=talib.ATR(h,l,c,14)
    sts,ss=load_scores('BTC',src)
    ev=[i for i in events(atr,60,0.9) if i<len(ts)-15]
    mid=(int(ts[0])+int(ts[-1]))//2
    if half: ev=[i for i in ev if (ts[i]<mid)==(half=='first')]
    state=[]; last=-10**18
    for i in range(len(ts)-15):
        if half and not ((ts[i]<mid)==(half=='first')): continue
        if not np.isnan(atr[i]) and atr[i]>=60 and i not in set(ev) and ts[i]-last>=3600:
            state.append(i); last=ts[i]
    base=[i for i in range(0,len(ts),60) if i<len(ts)-15 and (not half or (ts[i]<mid)==(half=='first'))]
    def collect(idxs):
        out=[]; stales=[]
        for i in idxs:
            s=score_at(sts,ss,int(ts[i]))
            if np.isnan(s): continue
            d=(-1 if s>=50 else 1) if flip else (1 if s>=50 else -1)
            v=fwd(ts,c,i,1440,d)
            if v is None: continue
            out.append(v); stales.append(int(ts[i])-int(sts[np.searchsorted(sts,int(ts[i]),side='right')-1]))
        return out, stales
    E,stale=collect(ev); S,_=collect(state); R,_=collect(base)
    if not E: print('  no events'); return
    k=sum(1 for x in E if x>0); n=len(E)
    lo,hi=boot(np.array(E),np.array(S)) if S else (0,0)
    print(f'  {src} flip={flip} half={half}: n={n} WR={100*k/n:.1f}% mean={np.mean(E):+.3f}% | '
          f'state n={len(S)} mean={np.mean(S):+.3f} | rand mean={np.mean(R):+.3f} | '
          f'ev-state={np.mean(E)-np.mean(S):+.3f} CI[{lo:+.3f},{hi:+.3f}] | '
          f'WR-state={100*(sum(1 for x in S if x>0)/len(S)) if S else 0:.1f}% | '
          f'p(WR>50)={binom2(k,n):.3f} | median staleness={int(np.median(stale)) if stale else "NA"}s')

print('== R2b/R2c: BTC, RECORDED scores (spec: unflipped 34.0% WR, flipped 67.3%, ev-state ~0, halves 72.0/62.5) ==')
btc_study('recorded', False)
btc_study('recorded', True)
btc_study('recorded', True, 'first')
btc_study('recorded', True, 'second')
btc_study('recorded', False, 'first')
btc_study('recorded', False, 'second')

print('\n== R2d BTC: REPLAYED scores (spec: cont_50 37.8%, flip 62.2%, n=98, ev-state n.s.) ==')
btc_study('replay', False)
btc_study('replay', True)

print('\n== R2d pooled 12 coins: REPLAYED scores, ATR% 0.076 (spec: unflipped 52.2%, ev-state +0.293 sig, 9/3) ==')
def pooled(flip):
    E=[];S=[];per={}
    for ck in COINS:
        ts,h,l,c=load(ck)
        atr=talib.ATR(h,l,c,14); ap=atr/c*100
        sts,ss=load_scores(ck,'replay')
        if len(sts)<1000: print('  no replay scores',ck); continue
        ev=[i for i in events(ap,0.076,0.9) if i<len(ts)-15]; evset=set(ev)
        state=[]; last=-10**18
        for i in range(len(ts)-15):
            if not np.isnan(ap[i]) and ap[i]>=0.076 and i not in evset and ts[i]-last>=3600:
                state.append(i); last=ts[i]
        def coll(idxs):
            o=[]
            for i in idxs:
                s=score_at(sts,ss,int(ts[i]))
                if np.isnan(s): continue
                d=(-1 if s>=50 else 1) if flip else (1 if s>=50 else -1)
                v=fwd(ts,c,i,1440,d)
                if v is not None: o.append(v)
            return o
        e=coll(ev); s=coll(state)
        if not e or not s: continue
        E+=e; S+=s; per[ck]=(np.mean(e),np.mean(s),len(e))
    k=sum(1 for x in E if x>0); n=len(E)
    lo,hi=boot(np.array(E),np.array(S))
    pos=sum(1 for ck,(me,ms,_) in per.items() if me>ms); neg=sum(1 for ck,(me,ms,_) in per.items() if me<ms)
    nn=pos+neg; psp=sum(comb(nn,i) for i in range(pos,nn+1))/2**nn
    print(f'  flip={flip}: pooled n={n} WR={100*k/n:.1f}% mean={np.mean(E):+.3f}% | state n={len(S)} mean={np.mean(S):+.3f} | '
          f'ev-state={np.mean(E)-np.mean(S):+.3f} CI[{lo:+.3f},{hi:+.3f}] | signs {pos}/{neg} p={psp:.3f}')
    for ck,(me,ms,ne) in sorted(per.items(), key=lambda x:-(x[1][0]-x[1][1])):
        print(f'     {ck:>5} n={ne:>4} ev={me:+.3f} state={ms:+.3f} diff={me-ms:+.3f}')
pooled(False)
pooled(True)
