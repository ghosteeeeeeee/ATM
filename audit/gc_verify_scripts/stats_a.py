#!/usr/bin/env python3
"""Stats + verdict verification on top of episodes.json."""
import json, math, subprocess, sys
import numpy as np
from scipy import stats as sps

RNG = np.random.default_rng(12345)
D = json.load(open('/tmp/gaudit/episodes.json'))
recs = D['recs']
mkt_mean = {k: {int(b): v for b, v in d.items()} for k, d in D['mkt_mean'].items()}
mkt_med = {k: {int(b): v for b, v in d.items()} for k, d in D['mkt_med'].items()}
btc_fwd = {k: {int(b): v for b, v in d.items()} for k, d in D['btc_fwd'].items()}

AUDIT_GATES = {'SHORT-CONTINUUM','LONG-RSI-BLOCK','LONG-NEUTRAL','PUMP-CHAIN-SHORT-RSI-MIN',
 'SHORT-NEUTRAL','HALL-SHAME','LONG-RSI-CEILING','BTC-CHOP-GATE','SHORT-RSI-FLOOR',
 'PUMP-CHAIN-RSI-MAX','OVERSOLD-SHORT','CTX-GATE','BTC-CRASH','PUMP-CHAIN-SHORT-HIGH',
 'SPIKE-FILTER','PUMP-CHAIN-VEL-SHORT','SHORT-BB-DEAD-ZONE2','PUMP-CHAIN-RSI-MIN',
 'SHORT-REGIME-GATE','CHOP','EXEC-RSI-HARD-FLOOR','PUMP-CHAIN-VEL','EXEC-RSI-CEILING',
 'PHANTOM-WRITE','LONG-RSI-FLOOR','SHORT-RSI-CEILING','EXEC-BLOCK','SHORT-BB-DEAD-ZONE',
 'HOT-SET-COOLDOWN','PRESERVE-SPIKE-BLOCK','HOTSET-FILTER-WR','VEL-FILTER','HARD-BLOCK',
 'EXEC-RSI-FLOOR','V3-LONG-EXTREME','BTC-ACCEL','V2-RECHECK','BB-SQUEEZE-EXTREME'}

def wald(v):
    v = np.asarray([x for x in v if x is not None and not (isinstance(x, float) and math.isnan(x))], dtype=float)
    return v

def summarize(v, do_stats=True):
    v = wald(v)
    n = len(v)
    if n == 0:
        return None
    out = dict(n=n, mean=float(v.mean()), med=float(np.median(v)), wr=float((v > 0).mean() * 100))
    if do_stats and n >= 10:
        try:
            out['wp'] = float(sps.wilcoxon(v).pvalue)
        except Exception:
            out['wp'] = None
        # permutation sign-flip test on the mean
        B = 4000
        idx = RNG.integers(0, n, size=(B, n))
        signs = RNG.choice(np.array([-1.0, 1.0]), size=(B, n))
        perms = (v[idx] * signs).mean(axis=1)
        out['pp'] = float((np.abs(perms) >= abs(v.mean())).mean())
        # bootstrap CI of mean
        bmeans = v[idx].mean(axis=1)
        out['ci'] = (float(np.percentile(bmeans, 2.5)), float(np.percentile(bmeans, 97.5)))
    else:
        out['wp'] = out['pp'] = None; out['ci'] = None
    return out

def fmt(s):
    if s is None: return "  n=0"
    ci = f"[{s['ci'][0]:+.2f},{s['ci'][1]:+.2f}]" if s.get('ci') else ""
    wp = f"{s['wp']:.3f}" if s.get('wp') is not None else "  - "
    pp = f"{s['pp']:.3f}" if s.get('pp') is not None else "  - "
    return f"n={s['n']:4} mean={s['mean']:+.3f} med={s['med']:+.3f} wr={s['wr']:4.1f} wp={wp} pp={pp} {ci}"

# ---------- 1. headline: blocked universe ----------
print("=" * 100)
print("HEADLINE BLOCKED-SIDE NUMBERS")
aud = [r for r in recs if r['gate'] in AUDIT_GATES]
mine = recs
for label, sub in (("audit-gate-universe (38 gates, but incl. token W)", aud), ("my full universe (55 gates)", mine)):
    s = summarize([r['ex_4h'] for r in sub])
    s2 = summarize([r['exn_4h'] for r in sub])
    s3 = summarize([r['4h'] for r in sub])
    print(f"{label}:")
    print(f"   ex4h(audit formula) {fmt(s)}")
    print(f"   exn4h(neutral base) {fmt(s2)}")
    print(f"   raw4h               {fmt(s3)}")

# ---------- 2. passed side ----------
psql = subprocess.run(['psql', 'host=/var/run/postgresql dbname=brain user=postgres', '-A', '-t', '-F', '|', '-c',
    "SELECT token, direction, EXTRACT(EPOCH FROM open_time)::bigint FROM trades "
    "WHERE status='closed' AND paper='f' AND open_time >= '2026-10-02 20:00:00+00' "
    "AND open_time < '2026-10-08 23:05:00+00' ORDER BY open_time"],
    capture_output=True, text=True)
trades = [l.split('|') for l in psql.stdout.strip().split('\n') if l]
print(f"\npassed trades from PG: {len(trades)}")

# load candles for traded tokens
import sqlite3
toks = sorted({t[0] for t in trades})
conn = sqlite3.connect('/root/.hermes/data/candles.db')
cur = conn.cursor()
tcand = {}
for t in toks:
    rows = cur.execute("SELECT ts, open, high, low, close FROM candles_5m WHERE token=? AND is_closed=1 "
                       "AND ts>=? AND ts<=? ORDER BY ts", (t, 1788908700 - 3600, 1791501000 + 3600)).fetchall()
    if rows:
        tcand[t] = np.array(rows, dtype=np.float64)
conn.close()

H = {'30m': 6, '1h': 12, '4h': 48}
passed = {k: [] for k in list(H) + ['ex_30m', 'ex_1h', 'ex_4h', 'exn_4h', 'bucket', 'tok', 'dir']}
nocov = 0
for tok, d, ets in trades:
    ets = int(ets)
    a = tcand.get(tok)
    if a is None:
        nocov += 1; continue
    i = int(np.searchsorted(a[:, 0], ets, side='left'))
    if i + 48 >= len(a):
        nocov += 1; continue
    b = int(a[i, 0]); o = a[i, 1]; sgn = 1.0 if d == 'LONG' else -1.0
    for name, n in H.items():
        f = (a[i + n, 4] / o - 1.0) * 100.0
        signed = sgn * f
        passed[name].append(signed)
        mm = mkt_mean[name].get(b)
        passed['ex_' + name].append(signed - mm if mm is not None else None)
        if name == '4h':
            passed['exn_4h'].append(signed - (mm if d == 'LONG' else -mm) if mm is not None else None)
    passed['bucket'].append(b); passed['tok'].append(tok); passed['dir'].append(d)
print(f"passed w/ coverage: {len(passed['4h'])} (no cov: {nocov})")
for h in H:
    print(f"  fwd {h:3}: {fmt(summarize(passed[h]))}")
print(f"  ex_4h (audit formula): {fmt(summarize(passed['ex_4h']))}")
print(f"  exn_4h (neutral base): {fmt(summarize(passed['exn_4h']))}")

# ---------- 3. MWU passed vs blocked ----------
def mwu(a, b, alt='two-sided'):
    a = wald(a); b = wald(b)
    u, p = sps.mannwhitneyu(a, b, alternative=alt)
    return u, p
# dedup blocked by (token, dir, bucket)
seen = set(); ded = []
for r in recs:
    k = (r['token'], r['dir'], r['bucket'])
    if k in seen: continue
    seen.add(k); ded.append(r)
print(f"\nblocked episodes deduped by (token,dir,bucket): {len(ded)}")
for alt in ('two-sided', 'greater'):
    u, p = mwu([r['ex_4h'] for r in ded], passed['ex_4h'], alt)
    print(f"MWU blocked-vs-passed ex_4h ({alt}): U={u:.0f} p={p:.4f}")
u, p = mwu([r['exn_4h'] for r in ded], passed['exn_4h'], 'two-sided')
print(f"MWU neutral-baseline exn_4h (two-sided): U={u:.0f} p={p:.4f}")
u, p = mwu([r['4h'] for r in ded], passed['4h'], 'two-sided')
print(f"MWU raw fwd 4h (two-sided): U={u:.0f} p={p:.4f}")
# rank-biserial / Cliff's delta effect size
def cliffs(a, b):
    a = wald(a); b = wald(b)
    return float((sps.rankdata(np.concatenate([a, b]))[:len(a)].sum() - len(a) * (len(a) + 1) / 2) / (len(a) * len(b)) * 2 - 1)
print(f"cliff's delta blocked-vs-passed ex_4h: {cliffs([r['ex_4h'] for r in ded], passed['ex_4h']):+.3f}")

# ---------- 4. overlap / solo ----------
from collections import defaultdict
by_td = defaultdict(list)
for r in recs:
    by_td[(r['token'], r['dir'])].append(r)
for (tok, d), rs in by_td.items():
    rs.sort(key=lambda x: x['ts'])
    for r in rs:
        r['nsolo'] = sum(1 for o in rs if o is not r and abs(o['ts'] - r['ts']) <= 600)
        r['ovgates'] = sorted({o['gate'] for o in rs if o is not r and abs(o['ts'] - r['ts']) <= 600})

json.dump({'n_blocked': len(recs), 'n_dedup': len(ded),
           'passed': {k: v for k, v in passed.items() if k in ('30m', '1h', '4h', 'ex_30m', 'ex_1h', 'ex_4h', 'exn_4h', 'bucket', 'tok', 'dir')}},
          open('/tmp/gaudit/side.json', 'w'))
json.dump(recs, open('/tmp/gaudit/recs_solo.json', 'w'))
print("\ndone phase A")
