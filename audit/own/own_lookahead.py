#!/usr/bin/env python3
"""Mechanical lookahead test: indicators/events/directions computed on a TRUNCATED
prefix (data <= cutoff) must be identical to those computed on the full series.
Any future-data leakage shows up as a mismatch."""
import sqlite3, sys
import numpy as np, talib
sys.path.insert(0,'/root/.hermes/scripts')
import backtest_atr60_momentum as B
DB='/root/.hermes/data/candles.db'
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
COINS=['BTC','SOL','SUI','TAO','PUMP','GALA','GMX','IMX','SAND','FOGO','COMP','DYM']
CUT_DAYS=10
tot_mismatch=0
for ck in COINS:
    ts,h,l,c=load(ck,'candles_1m'); h15=load(ck,'candles_15m'); h4=load(ck,'candles_4h')
    cut=int(ts[0])+CUT_DAYS*86400
    # --- FULL series values ---
    atr_f=talib.ATR(h,l,c,14); ap_f=atr_f/c*100
    rsi_f=talib.RSI(c,14)
    mh_f=np.array([np.nan if v is None else v for v in B.tv_macd_hist(list(c))])
    e20f=talib.EMA(h15[3],20); e50f=talib.EMA(h15[3],50)
    e204f=talib.EMA(h4[3],20); e504f=talib.EMA(h4[3],50)
    def d15f(t):
        k=np.searchsorted(h15[0],t-900,side='right')-1
        if k<50 or np.isnan(e20f[k]) or np.isnan(e50f[k]): return 0
        return 1 if e20f[k]>e50f[k] else -1
    def d4f(t):
        k=np.searchsorted(h4[0],t-14400,side='right')-1
        if k<50 or np.isnan(e204f[k]) or np.isnan(e504f[k]): return 0
        return 1 if e204f[k]>e504f[k] else -1
    ev_f=[i for i in events(ap_f,0.076,0.9) if ts[i]<=cut]
    # --- TRUNCATED series (only bars with ts<=cut) ---
    m1=ts<=cut; ts1,h1,l1,c1=ts[m1],h[m1],l[m1],c[m1]
    t15=h15[0]<=cut; ts15,h15_1,l15,c15=h15[0][t15],h15[1][t15],h15[2][t15],h15[3][t15]
    t4=h4[0]<=cut; ts4,h4_1,l4,c4=h4[0][t4],h4[1][t4],h4[2][t4],h4[3][t4]
    atr_t=talib.ATR(h1,l1,c1,14); ap_t=atr_t/c1*100
    rsi_t=talib.RSI(c1,14)
    mh_t=np.array([np.nan if v is None else v for v in B.tv_macd_hist(list(c1))])
    e20t=talib.EMA(c15,20); e50t=talib.EMA(c15,50)
    e204t=talib.EMA(c4,20); e504t=talib.EMA(c4,50)
    def d15t(t):
        k=np.searchsorted(ts15,t-900,side='right')-1
        if k<50 or np.isnan(e20t[k]) or np.isnan(e50t[k]): return 0
        return 1 if e20t[k]>e50t[k] else -1
    def d4t(t):
        k=np.searchsorted(ts4,t-14400,side='right')-1
        if k<50 or np.isnan(e204t[k]) or np.isnan(e504t[k]): return 0
        return 1 if e204t[k]>e504t[k] else -1
    ev_t=[i for i in events(ap_t,0.076,0.9)]
    # compare on common indices
    idx_map={int(t):i for i,t in enumerate(ts1)}
    ev_t_idx=[idx_map[int(ts[i])] for i in ev_t]
    same_ev = [ts[i] for i in ev_f]==[ts1[i] for i in ev_t_idx]
    # indicator diffs over prefix
    n=len(ts1)
    d_atr=np.nanmax(np.abs(atr_f[:n]-atr_t)) if n>50 else 0
    d_rsi=np.nanmax(np.abs(rsi_f[:n]-rsi_t)) if n>50 else 0
    d_mh=np.nanmax(np.abs(mh_f[:n]-mh_t)) if n>50 else 0
    # direction comparisons at event times (prefix events)
    dmis=sum(1 for i in ev_t if d15t(int(ts1[i]))!=d15f(int(ts1[i])) or d4t(int(ts1[i]))!=d4f(int(ts1[i])))
    rmis=sum(1 for i in ev_t if (not np.isnan(rsi_t[i]) and not np.isnan(rsi_f[i])) and np.sign(rsi_t[i]-50)!=np.sign(rsi_f[i]-50))
    hm=[i for i in ev_t if not np.isnan(mh_t[i]) and not np.isnan(mh_f[i]) and np.sign(mh_t[i])!=np.sign(mh_f[i])]
    flag='' if (same_ev and d_atr==0 and d_rsi==0 and dmis==0 and rmis==0 and not hm) else '  <<< MISMATCH'
    tot_mismatch += (0 if same_ev else 1)+dmis+rmis+len(hm)
    print(f'{ck:>5}: events prefix full={len(ev_f)} trunc={len(ev_t)} identical={same_ev} | '
          f'max|dATR|={d_atr:.2e} max|dRSI|={d_rsi:.2e} max|dMACD|={d_mh:.2e} | '
          f'15m/4h dir mismatches={dmis} RSI-sign={rmis} MACD-sign={len(hm)}{flag}',flush=True)
print(f'\nTOTAL lookahead mismatches: {tot_mismatch}  (0 = no lookahead in event/direction construction)')
