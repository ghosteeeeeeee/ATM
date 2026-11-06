#!/usr/bin/env python3
"""Own replay-vs-recorded fidelity check (claim 7) — independent join/stats."""
import sqlite3, numpy as np, datetime
p=sqlite3.connect('/root/.hermes/data/continuum.db')
rec=p.execute("SELECT ts, state_score FROM continuum_states WHERE token='BTC' AND state_score IS NOT NULL ORDER BY ts").fetchall(); p.close()
r=sqlite3.connect('/root/.hermes/data/continuum_replay.db')
rep=r.execute("SELECT ts, score FROM continuum_replay WHERE token='BTC' AND score IS NOT NULL ORDER BY ts").fetchall()
alltok=r.execute("SELECT token, count(*) FROM continuum_replay GROUP BY token").fetchall(); r.close()
print('recorded rows:', len(rec), datetime.datetime.utcfromtimestamp(rec[0][0]), '->', datetime.datetime.utcfromtimestamp(rec[-1][0]))
print('replay rows:', len(rep), datetime.datetime.utcfromtimestamp(rep[0][0]), '->', datetime.datetime.utcfromtimestamp(rep[-1][0]))
print('replay tokens:', alltok)
rts=np.array([x[0] for x in rep]); rs=np.array([x[1] for x in rep])
pts=np.array([x[0] for x in rec]); ps=np.array([x[1] for x in rec])
pairs=[]; stales=[]
for t,s in zip(rts,rs):
    k=np.searchsorted(pts,t)
    cands=[]
    if k<len(pts) and abs(int(pts[k])-t)<=60: cands.append(k)
    if k-1>=0 and abs(int(pts[k-1])-t)<=60: cands.append(k-1)
    if not cands: continue
    j=min(cands,key=lambda j:abs(int(pts[j])-t))
    pairs.append((s,ps[j])); stales.append(abs(int(t)-int(pts[j])))
a=np.array([x[0] for x in pairs]); b=np.array([x[1] for x in pairs])
from scipy import stats
pear=np.corrcoef(a,b)[0,1]
spear=stats.spearmanr(a,b).statistic
agree=np.mean((a>=50)==(b>=50))
mae=np.mean(np.abs(a-b))
print(f'matched pairs (|dt|<=60s): {len(pairs)}   median |dt| = {int(np.median(stales))}s  max {max(stales)}s')
print(f'Pearson={pear:.4f}  Spearman={spear:.4f}  sign(50) agreement={100*agree:.1f}%  MAE={mae:.2f} pts')
print(f'replay range [{a.min():.1f},{a.max():.1f}] recorded [{b.min():.1f},{b.max():.1f}]')
# also: max |dt| sensitivity — require dt<=5s
sel=[(x,s) for x,s in zip(pairs,stales) if s<=5]
if len(sel)>100:
    a2=np.array([x[0] for x,_ in sel]); b2=np.array([x[1] for x,_ in sel])
    print(f'strict (|dt|<=5s): n={len(sel)} pearson={np.corrcoef(a2,b2)[0,1]:.4f} sign agree={100*np.mean((a2>=50)==(b2>=50)):.1f}%')
