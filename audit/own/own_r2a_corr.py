import sqlite3, datetime
import numpy as np, talib
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
# daily mean event returns per coin
cd={}
for ck in COINS:
    m1=load(ck,'candles_1m'); h15=load(ck,'candles_15m'); h4=load(ck,'candles_4h')
    ts,h,l,c=m1
    atr=talib.ATR(h,l,c,14); ap=atr/c*100
    d15=ema_dirs(h15[3],900,h15[0]); d4=ema_dirs(h4[3],14400,h4[0])
    for i in [i for i in events(ap,THR,0.9) if i<len(ts)-15]:
        a,b=d15(ts[i]),d4(ts[i])
        if a==0 or b==0 or a!=b: continue
        v=fwd(ts,c,i,HZ,a)
        if v is None: continue
        cd.setdefault(datetime.date.fromtimestamp(int(ts[i])),{}).setdefault(ck,[]).append(v)
days=sorted(cd)
def pair_r(x,y):
    x=np.asarray(x); y=np.asarray(y); m=~np.isnan(x)&~np.isnan(y)
    if m.sum()<8: return np.nan
    return np.corrcoef(x[m],y[m])[0,1]
rs=[]
for i in range(len(COINS)):
    for j in range(i+1,len(COINS)):
        a=[np.mean(cd[d].get(COINS[i],[np.nan])) for d in days]
        b=[np.mean(cd[d].get(COINS[j],[np.nan])) for d in days]
        rs.append(pair_r(a,b))
rs=np.array(rs)
print(f'cross-coin corr of daily mean event returns: n_pairs={len(rs)} valid={np.sum(~np.isnan(rs))} '
      f'mean r={np.nanmean(rs):.3f} median={np.nanmedian(rs):.3f} min={np.nanmin(rs):.3f} max={np.nanmax(rs):.3f}')
rho=np.nanmean(rs); n=len(COINS)
print(f'design-effect effective independent coins = {n/(1+(n-1)*rho):.1f}  (of {n})')
# simple market-factor correlation: daily 24h returns
dr={}
for ck in COINS:
    m1=load(ck,'candles_1m'); ts,h,l,c=m1
    r=[(c[min(i+1440,len(c)-1)]/c[i]-1) for i in range(0,len(c)-1440,1440)]
    d=[datetime.date.fromtimestamp(int(ts[i])) for i in range(0,len(c)-1440,1440)]
    dr[ck]=dict(zip(d,r))
common=sorted(set.intersection(*[set(v) for v in dr.values()]))
X=np.array([[dr[ck][d] for ck in COINS] for d in common])
cm=np.corrcoef(X.T); iu=np.triu_indices(len(COINS),1)
print(f'daily 24h return corr: mean={cm[iu].mean():.3f} median={np.median(cm[iu]):.3f} (days={len(common)})')
