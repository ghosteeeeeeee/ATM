#!/usr/bin/env python3
"""R2a statistics done MY way: paired day-block bootstrap, day-level sign-flip
permutation, cross-coin correlation of daily event returns (effective n)."""
import sqlite3, datetime, sys
import numpy as np, talib
from math import comb
DB='/root/.hermes/data/candles.db'
COINS=['BTC','SOL','SUI','TAO','PUMP','GALA','GMX','IMX','SAND','FOGO','COMP','DYM']
THR=0.076; HZ=1440

def load(tok,tab):
    c=sqlite3.connect(DB)
    r=c.execute(f"SELECT ts,high,low,close FROM {tab} WHERE token=? ORDER BY ts ASC",(tok,)).fetchall(); c.close()
    return (np.array([x[0] for x in r],dtype=np.int64), np.array([x[1] for x in r]),
            np.array([x[2] for x in r]), np.array([x[3] for x in r])) if r else None
def events(a,thr,hy=0.9):
    ev,armed=[],True
    for i in range(1,len(a)):
        a0,a1=a[i-1],a[i]
        if np.isnan(a0) or np.isnan(a1): continue
        if armed and a0<thr<=a1: ev.append(i); armed=False
        if not armed and a1<thr*hy: armed=True
    return ev
def ema_dirs(hc,iv,hts):
    e20=talib.EMA(hc,20); e50=talib.EMA(hc,50)
    def d(t):
        k=np.searchsorted(hts,t-iv,side='right')-1
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

ev_by_day={}; st_by_day={}; coin_daily={c:{} for c in COINS}
for ck in COINS:
    m1=load(ck,'candles_1m'); h15=load(ck,'candles_15m'); h4=load(ck,'candles_4h')
    ts,h,l,c=m1
    atr=talib.ATR(h,l,c,14); ap=atr/c*100
    d15=ema_dirs(h15[3],900,h15[0]); d4=ema_dirs(h4[3],14400,h4[0])
    ev=[i for i in events(ap,THR,0.9) if i<len(ts)-15]; evset=set(ev)
    state=[]; last=-10**18
    for i in range(len(ts)-15):
        if not np.isnan(ap[i]) and ap[i]>=THR and i not in evset and ts[i]-last>=3600:
            state.append(i); last=ts[i]
    for i in ev:
        a,b=d15(ts[i]),d4(ts[i])
        if a==0 or b==0 or a!=b: continue
        v=fwd(ts,c,i,HZ,a)
        if v is None: continue
        d0=datetime.date.fromtimestamp(int(ts[i]))
        ev_by_day.setdefault(d0,[]).append(v)
        coin_daily[ck].setdefault(d0,[]).append(v)
    for i in state:
        a,b=d15(ts[i]),d4(ts[i])
        if a==0 or b==0 or a!=b: continue
        v=fwd(ts,c,i,HZ,a)
        if v is None: continue
        st_by_day.setdefault(datetime.date.fromtimestamp(int(ts[i])),[]).append(v)

days=sorted(set(ev_by_day)&set(st_by_day))
print(f'days with both ev and state rows: {len(days)}')
# per-day pooled ev mean, state mean, diff
de=np.array([np.mean(ev_by_day[d]) for d in days])
ds=np.array([np.mean(st_by_day[d]) for d in days])
diff=de-ds
print(f'per-day ev mean={de.mean():+.3f} state mean={ds.mean():+.3f} diff={diff.mean():+.3f} sd(days)={diff.std(ddof=1):.3f}')
pos=int((diff>0).sum()); n=len(diff)
print(f'days with ev>state: {pos}/{n}  sign p(one-sided)={sum(comb(n,i) for i in range(pos,n+1))/2**n:.4f}')
from scipy import stats as st
print(f'paired t-test on day diffs: t={st.ttest_1samp(diff,0).statistic:.2f} p={st.ttest_1samp(diff,0).pvalue:.4f}')
print(f'wilcoxon day diffs: p={st.wilcoxon(diff).pvalue:.4f}')
# sign-flip permutation on day diffs
rng=np.random.default_rng(9); obs=abs(diff.mean()); cnt=0; R=20000
for _ in range(R):
    s=np.where(rng.random(n)>0.5,1,-1)
    if abs((diff*s).mean())>=obs: cnt+=1
print(f'day-level sign-flip permutation (2-sided): p={(cnt+1)/(R+1):.4f}   [audit claimed day sign-flip p=0.0073]')

# paired day-block bootstrap (resample days for BOTH ev and state)
rng=np.random.default_rng(11); dsb=[]
E={d:np.array(ev_by_day[d]) for d in days}; S={d:np.array(st_by_day[d]) for d in days}
for _ in range(5000):
    pick=[days[int(rng.integers(0,len(days)))] for _ in range(len(days))]
    a=np.concatenate([E[d] for d in pick]); b=np.concatenate([S[d] for d in pick])
    dsb.append(a.mean()-b.mean())
print(f'paired day-block CI = [{np.percentile(dsb,2.5):+.3f},{np.percentile(dsb,97.5):+.3f}]  '
      f'(audit: [+0.151,+1.343])')

# cross-coin correlation of DAILY mean event returns
cd=np.array([[np.mean(coin_daily[ck][d]) if d in coin_daily[ck] else np.nan for ck in COINS] for d in days])
valid=[j for j in range(len(COINS)) if np.sum(~np.isnan(cd[:,j]))>10]
cc=np.corrcoef(np.ma.masked_invalid(cd[:,valid]).filled(np.nan), rowvar=False)
iu=np.triu_indices(len(valid),1)
vals=cc[iu]
print(f'cross-coin corr of daily MEAN EVENT returns: mean r={np.nanmean(vals):.3f} median={np.nanmedian(vals):.3f} '
      f'min={np.nanmin(vals):.3f} max={np.nanmax(vals):.3f} (coins={len(valid)}, days={len(days)})')
rho=np.nanmean(vals)
print(f'effective independent coins via design effect n/(1+(n-1)rho) = {len(valid)/(1+(len(valid)-1)*rho):.1f}')
