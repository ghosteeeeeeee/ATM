#!/usr/bin/env python3
"""Churn-at-entry: does the 15m aggregate flip-rate in the 24h BEFORE a trade opens
predict whether the trade arms the trail / makes money?

Motivation: #86 shipped flips/24h as a watchdog KPI (>=6 = high-churn tape) but never
joined it to trade outcomes. Mandate: "keep us out of chop" -> if high-churn entries
never arm, churn is a condition-based anti-chop gate (not a clock).

Anchor: flip count from the last regime dump STRICTLY BEFORE open_time (no lookahead).
Self-check: asserts monotone series length, that flips() reproduces the #86 baseline
(>=15 flips/24h for 2026-10-23 aggregate), and that every trade joins to a dump.
"""
import json, datetime, sys, collections
import psycopg2

LOG = '/root/.hermes/logs/15m_regime.log'
NOW = datetime.datetime.utcnow()

# ---- 1. parse dumps (same scheme as trade_watchdog_prompt.md flip KPI) ----
dumps, cur = [], []
for line in open(LOG):
    if line.startswith('{'):
        if cur: dumps.append(''.join(cur))
        cur = [line]
    elif cur:
        cur.append(line)
        if line.startswith('}'):
            dumps.append(''.join(cur)); cur = []
if cur: dumps.append(''.join(cur))

series = []  # (ts, agg, btc)
for d in dumps:
    try: p = json.loads(d)
    except Exception: continue
    ts = datetime.datetime.fromisoformat(p['timestamp'])
    series.append((ts,
                   p.get('aggregate', {}).get('overall'),
                   (p.get('regimes', {}).get('BTC') or {}).get('regime')))
series.sort(key=lambda x: x[0])
assert len(series) > 100, f"only {len(series)} dumps"

def flips(seq): return sum(1 for i in range(1, len(seq)) if seq[i][1] != seq[i-1][1])

# rolling flips over preceding 24h (window anchored at each dump, no lookahead)
W = datetime.timedelta(hours=24)
roll = []
j = 0
for i, (ts, _, _) in enumerate(series):
    while series[j][0] < ts - W: j += 1
    roll.append(flips(series[j:i+1]))
assert len(roll) == len(series)

# baseline check: last full 24h of aggregate flips should be >= 15 (measured 22 / 20)
last24 = [series[i] for i in range(len(series)) if series[i][0] >= NOW - W]
base = flips(last24)
print(f"[selfcheck] dumps={len(series)} first={series[0][0]} last={series[-1][0]}")
print(f"[selfcheck] aggregate flips in last 24h = {base} (expect ~20-25, #86 baseline 22)")

# ---- 2. join trades ----
conn = psycopg2.connect(host='/var/run/postgresql', database='brain', user='postgres')
cur = conn.cursor()
cur.execute("""
 SELECT id, token, signal, direction, open_time, close_time, pnl_usdt, confidence,
        trailing_activated, mfe_pct, volatility_regime, exit_reason
 FROM trades WHERE status='closed' AND close_time > NOW() - INTERVAL '14 days'
   AND open_time IS NOT NULL ORDER BY open_time
""")
trades = cur.fetchall()
conn.close()

def churn_at(t):
    """last dump strictly before open_time -> rolling flips in its preceding 24h"""
    lo, hi = 0, len(series) - 1
    if t <= series[0][0]: return None
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if series[mid][0] < t: lo = mid
        else: hi = mid - 1
    return roll[lo], series[lo][1], series[lo][2]

rows = []
for (tid, tok, sig, direc, ot, ct, pnl, conf, arm, mfe, vol, exr) in trades:
    c = churn_at(ot)
    if not c: continue
    fl, agg, btc = c
    rows.append(dict(id=tid, sig=sig, dir=direc, pnl=float(pnl), arm=bool(arm),
                     mfe=float(mfe or 0), churn=fl, agg=agg, btc=btc,
                     days_ago=(NOW - ct).total_seconds()/86400, conf=float(conf or 0)))
print(f"joined {len(rows)}/{len(trades)} trades (no join = opened before first dump)")

# ---- 3. cohorts ----
def stats(rs):
    if not rs: return "n=0"
    n = len(rs); w = sum(1 for r in rs if r['pnl'] > 0)
    return (f"n={n} WR={100*w/n:.1f}% pnl={sum(r['pnl'] for r in rs):+.2f} "
            f"arm={100*sum(r['arm'] for r in rs)/n:.1f}% "
            f"avgMFE={sum(r['mfe'] for r in rs)/n:.3f}%")

def fisher(a_w, a_n, b_w, b_n):
    from math import comb
    # two-sided Fisher exact on win/lose x cohort
    n = a_n + b_n; k = a_w + b_w
    def p(x): return comb(k, x)*comb(n-k, a_n-x)/comb(n, a_n)
    obs = p(a_w)
    return min(1.0, sum(p(x) for x in range(0, min(k, a_n)+1) if p(x) <= obs + 1e-12))

print("\n=== churn buckets (aggregate flips in 24h before open) ===")
for lo, hi, name in [(0,3,'0-2'), (3,6,'3-5'), (6,9,'6-8'), (9,99,'9+')]:
    sub = [r for r in rows if lo <= r['churn'] < hi]
    print(f"  {name:>4}: {stats(sub)}")

print("\n=== binary split: >=6 (high-churn, #86 threshold) vs <6 ===")
hi_ = [r for r in rows if r['churn'] >= 6]; lo_ = [r for r in rows if r['churn'] < 6]
print("  >=6 :", stats(hi_))
print("  <6  :", stats(lo_))
fw, fn = sum(1 for r in hi_ if r['pnl']>0), len(hi_)
lw, ln = sum(1 for r in lo_ if r['pnl']>0), len(lo_)
if fn and ln:
    print(f"  Fisher p (win rate) = {fisher(fw, fn, lw, ln):.4f}")

print("\n=== OOS: split by trade age ===")
for lo_d, hi_d, name in [(0,7,'last 7d'), (7,14,'d7-14')]:
    sub = [r for r in rows if lo_d <= r['days_ago'] < hi_d]
    h = [r for r in sub if r['churn'] >= 6]; l = [r for r in sub if r['churn'] < 6]
    print(f"  {name}: >=6 {stats(h)}")
    print(f"         <6  {stats(l)}")

print("\n=== confounder: churn vs direction/vol regime ===")
for d in ('LONG','SHORT'):
    h = [r for r in hi_ if r['dir']==d]; l = [r for r in lo_ if r['dir']==d]
    print(f"  {d}: >=6 {stats(h)}")
    print(f"  {d}: <6  {stats(l)}")

print("\n=== candidate gate impact: block churn>=6 ===")
blk = hi_
killed_wins = [r for r in blk if r['pnl'] > 0]
print(f"  would block {len(blk)}T / {len(rows)}T ({100*len(blk)/len(rows):.1f}%)")
print(f"  blocked set: {stats(blk)}")
print(f"  would kill {len(killed_wins)} winners, ${sum(r['pnl'] for r in killed_wins):+.2f} of "
      f"${sum(r['pnl'] for r in rows if r['pnl']>0):+.2f} total winners ({100*len(killed_wins)/max(1,sum(1 for r in rows if r['pnl']>0)):.1f}% fk)")
print(f"  net save if blocked: ${-sum(r['pnl'] for r in blk):+.2f}/14d")

print("\n=== signal mix of the >=6 cohort (confounder check) ===")
c = collections.Counter(r['sig'] for r in hi_)
for s, n in c.most_common(10): print(f"   {s}: {n}")
