#!/usr/bin/env python3
"""Phase D: coalescing sensitivity, ties, passed-vs-blocked interplay,
regime (BTC daily), OOS flip counts under both baselines, small-gate matrix."""
import json, math, sqlite3, subprocess
import numpy as np
from collections import defaultdict
from scipy import stats as sps

recs = json.load(open('/tmp/gaudit/recs_solo.json'))
side = json.load(open('/tmp/gaudit/side.json'))
RNG = np.random.default_rng(4242)

def w(v):
    return np.array([x for x in v if x is not None and not (isinstance(x, float) and math.isnan(x))], dtype=float)

# ---- 1. ties / zeros (attack I) ----
print("1. TIE/ZERO COUNTS + wilcoxon-vs-permutation for top gates")
by_gate = defaultdict(list)
for r in recs:
    by_gate[r['gate']].append(r)
for g in sorted(by_gate, key=lambda x: -len(by_gate[x]))[:12]:
    v = w([r['ex_4h'] for r in by_gate[g]])
    zeros = int((v == 0).sum())
    uniq = len(np.unique(v))
    print(f"  {g:26} n={len(v):5} zeros={zeros:3} unique={uniq:5}")

# ---- 2. small gates (<30 eps) full baseline matrix ----
print()
print("2. GATES WITH n in [20,45) — baseline matrix (mean / wilcoxon p)")
for g in sorted(by_gate, key=lambda x: -len(by_gate[x])):
    rs = by_gate[g]
    if not (20 <= len(rs) <= 45):
        continue
    cells = []
    for key in ('ex_4h', 'exn_4h', '4h'):
        v = w([r[key] for r in rs])
        p = float(sps.wilcoxon(v).pvalue) if len(v) >= 10 and len(np.unique(v)) > 1 else None
        cells.append(f"{v.mean():+.3f} p={(p if p is not None else float('nan')):.3f}")
    print(f"  {g:26} n={len(rs):3} audit={cells[0]:>18} neutral={cells[1]:>18} raw={cells[2]:>18}")

# ---- 3. OOS flip counts under audit vs neutral ----
print()
print("3. OOS HALF SIGN FLIPS (Oct5 12:00 split)")
SPLIT = int((__import__('datetime').datetime(2026, 10, 5, 12, 0, tzinfo=__import__('datetime').timezone.utc)).timestamp())
fl_audit = fl_neu = tot = 0
for g, rs in by_gate.items():
    a = w([r['ex_4h'] for r in rs if r['ts'] < SPLIT])
    b = w([r['ex_4h'] for r in rs if r['ts'] >= SPLIT])
    an = w([r['exn_4h'] for r in rs if r['ts'] < SPLIT])
    bn = w([r['exn_4h'] for r in rs if r['ts'] >= SPLIT])
    if len(a) >= 10 and len(b) >= 10:
        tot += 1
        if a.mean() * b.mean() < 0:
            fl_audit += 1
        if an.mean() * bn.mean() < 0:
            fl_neu += 1
print(f"  gates with >=10 eps in both halves: {tot}; sign-flips: audit-formula {fl_audit}, neutral-baseline {fl_neu}")

# ---- 4. regime: BTC daily returns + market daily ----
print()
print("4. REGIME: BTC daily close-to-close + market mean 4h fwd per day")
conn = sqlite3.connect('/root/.hermes/data/candles.db')
cur = conn.cursor()
rows = cur.execute("SELECT ts, close FROM candles_5m WHERE token='BTC' AND is_closed=1 AND ts>=? AND ts<=?",
                   (1789000000, 1791501000)).fetchall()
import datetime as dt
day_close = {}
for ts, c in rows:
    d = dt.datetime.utcfromtimestamp(ts).strftime('%m-%d')
    day_close[d] = c
days_sorted = sorted(day_close)
prev = None
for d in days_sorted:
    if prev and prev != d:
        pass
    prev = d
# simpler: close at 00:00 each day
for d in days_sorted:
    pass
cs = [day_close[d] for d in days_sorted]
# daily return using first/last candle of each day
day_fl = defaultdict(list)
for ts, c in rows:
    d = dt.datetime.utcfromtimestamp(ts).strftime('%m-%d')
    day_fl[d].append((ts, c))
for d in sorted(day_fl):
    v = sorted(day_fl[d])
    print(f"  BTC {d}: open={v[0][1]:8.1f} close={v[-1][1]:8.1f} ret={(v[-1][1]/v[0][1]-1)*100:+.2f}%")

# ---- 5. passed trades vs blocked episodes interplay (attack H) ----
print()
print("5. PASSED TRADES vs BLOCKED EPISODES")
ptoks = side['passed']['tok']; pdirs = side['passed']['dir']; pb = side['passed']['bucket']
blocked_td = defaultdict(list)
for r in recs:
    blocked_td[(r['token'], r['dir'])].append(r['ts'])
cnt30 = cnt120 = 0
for t, d, b in zip(ptoks, pdirs, pb):
    tss = blocked_td.get((t, d), [])
    if any(abs(ts - b) <= 1800 for ts in tss):
        cnt30 += 1
    if any(abs(ts - b) <= 7200 for ts in tss):
        cnt120 += 1
n = len(pb)
print(f"  passed trades with a blocked episode same token+dir within ±30min: {cnt30}/{n} ({cnt30/n*100:.0f}%)")
print(f"  ... within ±2h: {cnt120}/{n} ({cnt120/n*100:.0f}%)")
# direction mix
print(f"  passed dir mix: LONG {np.mean([1 if d=='LONG' else 0 for d in pdirs])*100:.0f}% "
      f"| blocked dir mix: LONG {np.mean([1 if r['dir']=='LONG' else 0 for r in recs])*100:.0f}%")
# token overlap
ptok_set = set(ptoks); btok_set = {r['token'] for r in recs}
print(f"  passed tokens: {len(ptok_set)}; blocked tokens: {len(btok_set)}; overlap: {len(ptok_set & btok_set)}")
# excess by direction, both sides (neutral baseline)
for d in ('LONG', 'SHORT'):
    pv = w([e for e, dd in zip(side['passed']['exn_4h'], pdirs) if dd == d])
    bv = w([r['exn_4h'] for r in recs if r['dir'] == d])
    if len(pv) and len(bv):
        u, p = sps.mannwhitneyu(bv, pv, alternative='two-sided')
        print(f"  {d}: passed exn4h n={len(pv)} mean={pv.mean():+.3f} | blocked n={len(bv)} mean={bv.mean():+.3f} | MWU p={p:.3f}")
conn.close()

# ---- 6. coalescing sensitivity: episodes at 30/60/120 gaps ----
print()
print("6. COALESCING SENSITIVITY (from events.json; headline ex4h on audit-gate universe)")
ev = json.load(open('/tmp/gaudit/events.json'))['events']
D = json.load(open('/tmp/gaudit/episodes.json'))
mkt_mean = {k: {int(b): v for b, v in d.items()} for k, d in D['mkt_mean'].items()}
AUDIT_GATES = {'SHORT-CONTINUUM','LONG-RSI-BLOCK','LONG-NEUTRAL','PUMP-CHAIN-SHORT-RSI-MIN',
 'SHORT-NEUTRAL','HALL-SHAME','LONG-RSI-CEILING','BTC-CHOP-GATE','SHORT-RSI-FLOOR',
 'PUMP-CHAIN-RSI-MAX','OVERSOLD-SHORT','CTX-GATE','BTC-CRASH','PUMP-CHAIN-SHORT-HIGH',
 'SPIKE-FILTER','PUMP-CHAIN-VEL-SHORT','SHORT-BB-DEAD-ZONE2','PUMP-CHAIN-RSI-MIN',
 'SHORT-REGIME-GATE','CHOP','EXEC-RSI-HARD-FLOOR','PUMP-CHAIN-VEL','EXEC-RSI-CEILING',
 'PHANTOM-WRITE','LONG-RSI-FLOOR','SHORT-RSI-CEILING','EXEC-BLOCK','SHORT-BB-DEAD-ZONE',
 'HOT-SET-COOLDOWN','PRESERVE-SPIKE-BLOCK','HOTSET-FILTER-WR','VEL-FILTER','HARD-BLOCK',
 'EXEC-RSI-FLOOR','V3-LONG-EXTREME','BTC-ACCEL','V2-RECHECK','BB-SQUEEZE-EXTREME'}
# reload candles for the tokens involved and recompute forward returns inline
import sqlite3
toks = sorted({e[2] for e in ev} - {'TESTTOKEN'})
conn = sqlite3.connect('/root/.hermes/data/candles.db')
cur = conn.cursor()
cand = {}
WIN0 = int((__import__('datetime').datetime(2026, 10, 2, 20, 0, tzinfo=__import__('datetime').timezone.utc)).timestamp())
WIN1 = int((__import__('datetime').datetime(2026, 10, 8, 23, 2, tzinfo=__import__('datetime').timezone.utc)).timestamp())
for t in toks:
    rows = cur.execute("SELECT ts, open, close FROM candles_5m WHERE token=? AND is_closed=1 AND ts>=? AND ts<=? ORDER BY ts",
                       (t, WIN0, WIN1 + 4 * 3600 + 600)).fetchall()
    if len(rows) > 100:
        cand[t] = np.array(rows, dtype=np.float64)
conn.close()

def fwd4h(tok, ts, d):
    a = cand.get(tok)
    if a is None:
        return None, None
    i = int(np.searchsorted(a[:, 0], ts, side='left'))
    if i + 48 >= len(a):
        return None, None
    b = int(a[i, 0]); o = a[i, 1]
    f = (a[i + 48, 2] / o - 1.0) * 100.0
    signed = f if d == 'LONG' else -f
    mm = mkt_mean['4h'].get(b)
    if mm is None:
        return None, None
    return signed - mm, signed - (mm if d == 'LONG' else -mm)

for gap in (1800, 3600, 7200):
    by = defaultdict(list)
    for ts, g, tok, d in ev:
        by.setdefault((g, tok, d), []).append(ts)
    eps = []
    for (g, tok, d), tss in by.items():
        tss.sort()
        s = last = tss[0]
        for ts in tss[1:]:
            if ts - last > gap:
                eps.append((s, g, tok, d)); s = ts
            last = ts
        eps.append((s, g, tok, d))
    vals, vals_n, per = [], [], defaultdict(lambda: [[], []])
    for ts, g, tok, d in eps:
        if g not in AUDIT_GATES:
            continue
        e, en = fwd4h(tok, ts, d)
        if e is None:
            continue
        vals.append(e); vals_n.append(en)
        per[g][0].append(e); per[g][1].append(en)
    v = np.array(vals); vn = np.array(vals_n)
    print(f"  gap={gap//60:3}min: eps(38-gate universe w/ coverage)={len(v):5} "
          f"ex4h mean={v.mean():+.3f} med={np.median(v):+.3f} | neutral mean={vn.mean():+.3f}")
    for g in ('SHORT-CONTINUUM', 'OVERSOLD-SHORT', 'BTC-CHOP-GATE', 'SHORT-RSI-FLOOR', 'CHOP'):
        vv = np.array(per[g][0]); vvn = np.array(per[g][1])
        if len(vv):
            print(f"      {g:24} n={len(vv):4} ex={vv.mean():+.3f} neu={vvn.mean():+.3f}")
