#!/usr/bin/env python3
"""Dedup by group (one trade per group), per-group stats, hold sensitivity."""
import sqlite3, math, json
from datetime import datetime, timezone
from collections import defaultdict

CAND_DB = '/root/.hermes/data/candles.db'
rows = json.load(open('/root/.hermes/brain/verdicts/audit_rows.json'))
cc = sqlite3.connect(f"file:{CAND_DB}?mode=ro", uri=True, timeout=60)

def c_at_or_before(token, t):
    return cc.execute("SELECT ts, close FROM candles_1m WHERE token=? AND ts<=? ORDER BY ts DESC LIMIT 1", (token, t)).fetchone()

def fwd(token, t, hold_min):
    e = c_at_or_before(token, t)
    x = c_at_or_before(token, t + hold_min*60)
    if not e or not x: return None
    return (x[1]-e[1])/e[1]*100

def wilson(w, n, z=1.96):
    p=w/n; d=1+z*z/n
    c=(p+z*z/(2*n))/d; h=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/d
    return (c-h, c+h)

def binom_p_ge(w, n, p0=0.5):
    mu=n*p0; sd=math.sqrt(n*p0*(1-p0)); z=(w-0.5-mu)/sd
    return 0.5*(1+math.erf(z/math.sqrt(2)))

print("="*70)
print("HOLD-PERIOD SENSITIVITY (entry at bypass candle, 184 events)")
print("="*70)
for hold in (15,30,60,120,240):
    rets=[]
    for r in rows:
        x=fwd(r['token'], r['bypass_t'], hold)
        if x is None: continue
        if r['direction']=='SHORT': x=-x
        rets.append(x)
    n=len(rets); w=sum(1 for x in rets if x>0)
    print(f"  hold={hold:>3}m: n={n} WR={w/n*100:.1f}% total={sum(rets):+.2f}% avg={sum(rets)/n:+.3f}%")

print()
print("="*70)
print("DEDUP: ONE TRADE PER (token,direction) GROUP — first bypass only")
print("="*70)
by_group=defaultdict(list)
for r in rows: by_group[(r['token'],r['direction'])].append(r)
for hold in (60,120):
    rets=[]; labels=[]
    for k, rs in by_group.items():
        rs_sorted=sorted(rs, key=lambda x:x['bypass_t'])
        first=rs_sorted[0]
        x=fwd(first['token'], first['bypass_t'], hold)
        if x is None: continue
        if first['direction']=='SHORT': x=-x
        rets.append(x); labels.append((k,x))
    n=len(rets); w=sum(1 for x in rets if x>0)
    lo,hi=wilson(w,n); p1=binom_p_ge(w,n)
    print(f"  hold={hold}m: n={n} (independent groups) WR={w/n*100:.1f}% total={sum(rets):+.2f}% avg={sum(rets)/n:+.3f}%")
    print(f"     Wilson 95% CI=[{lo*100:.1f}%,{hi*100:.1f}%] one-sided p={p1:.4f}")
    for lab,x in sorted(labels, key=lambda z:z[1]):
        print(f"       {lab[0][0]:>5} {lab[0][1]:<5} {x:+.2f}%")

print()
print("="*70)
print("DEDUP: max 1 trade per group within 4h cooldown (realistic execution)")
print("="*70)
for hold in (60,):
    taken=[]
    for k, rs in by_group.items():
        last_t=-1e9
        for r in sorted(rs, key=lambda x:x['bypass_t']):
            if r['bypass_t']-last_t < 4*3600: continue
            x=fwd(r['token'], r['bypass_t'], hold)
            if x is None: continue
            if r['direction']=='SHORT': x=-x
            taken.append(x); last_t=r['bypass_t']
    n=len(taken); w=sum(1 for x in taken if x>0)
    lo,hi=wilson(w,n); p1=binom_p_ge(w,n)
    print(f"  hold={hold}m 4h-cooldown: n={n} WR={w/n*100:.1f}% total={sum(taken):+.2f}% avg={sum(taken)/n:+.3f}%")
    print(f"     Wilson 95% CI=[{lo*100:.1f}%,{hi*100:.1f}%] one-sided p={p1:.4f}")

# LONG-only deduped
print()
print("="*70)
print("LONG vs SHORT — DEDUPED (1 trade per group)")
print("="*70)
for direction in ('SHORT','LONG'):
    rets=[]
    for k, rs in by_group.items():
        if k[1]!=direction: continue
        first=sorted(rs,key=lambda x:x['bypass_t'])[0]
        x=fwd(first['token'], first['bypass_t'], 60)
        if x is None: continue
        if direction=='SHORT': x=-x
        rets.append(x)
    if not rets: 
        print(f"  {direction}: none"); continue
    n=len(rets); w=sum(1 for x in rets if x>0)
    lo,hi=wilson(w,n); p1=binom_p_ge(w,n)
    print(f"  {direction}: n={n} WR={w/n*100:.1f}% total={sum(rets):+.2f}% CI=[{lo*100:.1f}%,{hi*100:.1f}%] p={p1:.4f}")

# Is BTC the whole edge? (BTC excluded)
print()
print("EDGE CONCENTRATION:")
for excl in ([], ['BTC'], ['BTC','CHIP'], ['BTC','CHIP','APT','CFX']):
    rets=[]
    for r in rows:
        if r['token'] in excl: continue
        x=fwd(r['token'], r['bypass_t'], 60)
        if x is None: continue
        if r['direction']=='SHORT': x=-x
        rets.append(x)
    if not rets: 
        print(f"  excl {excl}: none"); continue
    n=len(rets); w=sum(1 for x in rets if x>0)
    print(f"  excl {str(excl):<28}: n={n} WR={w/n*100:.1f}% total={sum(rets):+.2f}%")

cc.close()
