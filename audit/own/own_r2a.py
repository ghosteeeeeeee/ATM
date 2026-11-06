#!/usr/bin/env python3
"""Own R2a: pooled direction from established higher-TF trend (15m EMA20/50 AND
4h EMA20/50 agreeing) at ATR% cross events, 12 coins, 24h direction-aligned.
Independent: talib EMA/ATR, own event/state/baseline construction, own stats
(iid bootstrap + day-block bootstrap + per-coin sign test + OOS halves)."""
import sqlite3, sys, datetime
import numpy as np, talib
from math import comb
DB='/root/.hermes/data/candles.db'
COINS=['BTC','SOL','SUI','TAO','PUMP','GALA','GMX','IMX','SAND','FOGO','COMP','DYM']
THR=0.076; HZ=1440

def load(tok,tab):
    c=sqlite3.connect(DB)
    r=c.execute(f"SELECT ts,high,low,close FROM {tab} WHERE token=? ORDER BY ts ASC",(tok,)).fetchall()
    c.close()
    if not r: return None
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

def ema_dirs(hc, iv, ts):
    """+1/-1/0 from EMA20 vs EMA50 on completed bars only. k = last bar with ts <= t-iv."""
    e20=talib.EMA(hc,20); e50=talib.EMA(hc,50)
    def d(t):
        k=np.searchsorted(ts, t-iv, side='right')-1
        if k<50 or np.isnan(e20[k]) or np.isnan(e50[k]): return 0
        return 1 if e20[k]>e50[k] else -1
    return d

def fwd(ts,c,i,hz,d):
    tgt=ts[i]+hz*60; j=np.searchsorted(ts,tgt)
    if j<len(ts) and ts[j]==tgt: pass
    elif j<len(ts) and abs(int(ts[j])-tgt)<=60: pass
    elif j>0 and abs(int(ts[j-1])-tgt)<=60: j-=1
    else: return None
    if j<=i: return None
    return (c[j]/c[i]-1)*100*d

E=[]; S=[]; R=[]   # pooled event/state/random direction-aligned values (val, ts, coin)
per={}             # coin -> {'e':[], 's':[], 'r':[], 'mid':ts}
for ck in COINS:
    m1=load(ck,'candles_1m'); h15=load(ck,'candles_15m'); h4=load(ck,'candles_4h')
    if not (m1 and h15 and h4): print('missing data',ck); continue
    ts,h,l,c=m1
    atr=talib.ATR(h,l,c,14); ap=atr/c*100
    d15=ema_dirs(h15[3], 900, h15[0]); d4=ema_dirs(h4[3], 14400, h4[0])
    ev=[i for i in events(ap,THR,0.9) if i<len(ts)-15]
    evset=set(ev)
    base=[i for i in range(0,len(ts),60) if i<len(ts)-15]
    state=[]; last=-10**18
    for i in range(len(ts)-15):
        if not np.isnan(ap[i]) and ap[i]>=THR and i not in evset and ts[i]-last>=3600:
            state.append(i); last=ts[i]
    rec={'e':[], 's':[], 'r':[], 'mid':(int(ts[0])+int(ts[-1]))//2, 'ev_n':len(ev)}
    for tag,idx,lst in (('e',ev,E),('s',state,S),('r',base,R)):
        for i in idx:
            a=d15(ts[i]); b=d4(ts[i])
            if a==0 or b==0 or a!=b: continue
            v=fwd(ts,c,i,HZ,a)
            if v is None: continue
            rec[tag].append((v,int(ts[i])))
            lst.append((v,int(ts[i]),ck))
    per[ck]=rec
    print(f'{ck:>5}: events={len(ev)} ev_rows={len(rec["e"])} state_rows={len(rec["s"])} base_rows={len(rec["r"])}',flush=True)

ev=np.array([v for v,_,_ in E]); st=np.array([v for v,_,_ in S]); rb=np.array([v for v,_,_ in R])
print(f'\nPOOLED (15m+4h agree, 24h): ev n={len(ev)} mean={ev.mean():+.3f}% WR={100*(ev>0).mean():.1f}%')
print(f'  state n={len(st)} mean={st.mean():+.3f}% WR={100*(st>0).mean():.1f}%')
print(f'  rand  n={len(rb)} mean={rb.mean():+.3f}% WR={100*(rb>0).mean():.1f}%')
print(f'  ev-state = {ev.mean()-st.mean():+.3f}   ev-rand = {ev.mean()-rb.mean():+.3f}   (spec: +0.77 ev-state, WR 58.8%, mean +0.72)')

def iid_ci(a,b,rounds=4000,seed=1):
    rng=np.random.default_rng(seed); a=np.asarray(a); b=np.asarray(b)
    ds=np.array([rng.choice(a,len(a)).mean()-rng.choice(b,len(b)).mean() for _ in range(rounds)])
    return np.percentile(ds,[2.5,97.5])
print(f'  iid bootstrap ev-state CI = [{iid_ci(ev,st)[0]:+.3f},{iid_ci(ev,st)[1]:+.3f}]')

# day-block bootstrap: resample CALENDAR DAYS (all coins' events on that day together)
days={}
for v,t,ck in E: days.setdefault(datetime.date.fromtimestamp(t),[]).append(v)
daylist=list(days.keys()); print(f'  distinct event days = {len(daylist)}')
rng=np.random.default_rng(2); ds=[]
s_by_day={d:np.array([v for v,tt,cc in S if datetime.date.fromtimestamp(tt)==d]) for d in daylist}
for _ in range(4000):
    pick=[daylist[int(rng.integers(0, len(daylist)))] for _ in range(len(daylist))]
    a=np.concatenate([days[d] for d in pick])
    sb=[s_by_day[d] for d in daylist if len(s_by_day[d])]
    b=np.concatenate([sb[int(rng.integers(0, len(sb)))] for _ in range(len(sb))])
    ds.append(a.mean()-b.mean())
print(f'  day-block bootstrap ev-state CI = [{np.percentile(ds,2.5):+.3f},{np.percentile(ds,97.5):+.3f}]')

# per-coin signs + sign test
pos=neg=0; signs={}
for ck,rec in per.items():
    if not rec['e'] or not rec['s']: continue
    me=np.mean([v for v,_ in rec['e']]); ms=np.mean([v for v,_ in rec['s']])
    signs[ck]=me-ms
    if me>ms: pos+=1
    elif me<ms: neg+=1
n=pos+neg; p=sum(comb(n,i) for i in range(pos,n+1))/2**n
print(f'  coin signs {pos}/{neg} (of {n}), one-sided sign p={p:.3f}   (spec: 10/2, p=0.019)')
for ck,v in sorted(signs.items(), key=lambda x:-x[1]): print(f'     {ck:>5} ev-state={v:+.3f}')

# OOS halves (each coin midpoint: ts < mid = first half)
for half in ('first','second'):
    A=[]; Bv=[]
    for ck,rec in per.items():
        for v,t in rec['e']: (A if (t<rec['mid'])==(half=='first') else Bv).append(v)
    Sv=[]
    for ck,rec in per.items():
        for v,t in rec['s']: (Sv if (t<rec['mid'])==(half=='first') else []).append(v)
    A=np.array(A); Sv=np.array(Sv)
    if len(A)<5 or len(Sv)<5:
        print(f'  half={half}: too few (ev={len(A)} state={len(Sv)})'); continue
    ci=iid_ci(A,Sv,rounds=3000,seed=3)
    # day-block within half
    days2={}
    for ck,rec in per.items():
        for v,t in rec['e']:
            if (t<rec['mid'])==(half=='first'): days2.setdefault(datetime.date.fromtimestamp(t),[]).append(v)
    dl=list(days2); rng=np.random.default_rng(4); ds2=[]
    for _ in range(3000):
        pick=[dl[int(rng.integers(0, len(dl)))] for _ in range(len(dl))]
        ds2.append(np.concatenate([days2[d] for d in pick]).mean()-Sv.mean())
    print(f'  half={half}: ev n={len(A)} mean={A.mean():+.3f} WR={100*(A>0).mean():.1f}% | '
          f'state n={len(Sv)} mean={Sv.mean():+.3f} | ev-state={A.mean()-Sv.mean():+.3f} '
          f'iid CI[{ci[0]:+.3f},{ci[1]:+.3f}] day-block CI[{np.percentile(ds2,2.5):+.3f},{np.percentile(ds2,97.5):+.3f}]')

# correlation of daily 24h returns across coins (effective-n evidence)
daily={}
for ck in COINS:
    m1=load(ck,'candles_1m')
    ts,h,l,c=m1
    r=[(c[min(i+1440,len(c)-1)]/c[i]-1) for i in range(0,len(c)-1440,1440)]
    d=[datetime.date.fromtimestamp(int(ts[i])) for i in range(0,len(c)-1440,1440)]
    daily[ck]=dict(zip(d,r))
days_all=sorted(set.intersection(*[set(v) for v in daily.values()]))
X=np.array([[daily[ck][d] for ck in COINS] for d in days_all])
cm=np.corrcoef(X.T)
iu=np.triu_indices(len(COINS),1)
print(f'\ndaily 24h return correlation across {len(COINS)} coins (n_days={len(days_all)}): '
      f'mean pairwise r={cm[iu].mean():.3f}  median={np.median(cm[iu]):.3f}  min={cm[iu].min():.3f} max={cm[iu].max():.3f}')
