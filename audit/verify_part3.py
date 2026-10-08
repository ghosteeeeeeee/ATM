#!/usr/bin/env python3
"""Audit part 3: statistical attacks on the T=30/theta=-0.5 claim.
 - per-trade delta distribution / t-stat / bootstrap CI
 - permutation test of the fixed cell AND of the best-of-21 sweep (selection bias)
 - placebo rules
 - weekly stability + concentration
"""
import sqlite3, psycopg2, datetime as dt, random, math, statistics
import numpy as np
from collections import Counter, defaultdict

CAND = sqlite3.connect("file:/root/.hermes/data/candles.db?mode=ro", uri=True)
PG = psycopg2.connect(host="/var/run/postgresql", dbname="brain", user="postgres")
pc = PG.cursor()
pc.execute("""
  SELECT id, token, direction, entry_price, exit_price, pnl_usdt, pnl_pct, amount_usdt,
         leverage, exit_reason, strategy, open_time, close_time
  FROM trades
  WHERE status='closed' AND paper='f' AND pnl_usdt IS NOT NULL AND entry_price>0
    AND amount_usdt>0 AND open_time >= '2026-08-21'
  ORDER BY open_time""")
rows = pc.fetchall()

Ts = [10, 15, 20, 30, 45, 60, 120]
THETAS = [-0.5, 0.0, 2.0]
TMAX = 130
TR = []
for (tid, tok, dire, entry, xit, pnlu, pnlp, amt, lev, xr, strat, ot, ct) in rows:
    ots = int(ot.replace(tzinfo=dt.timezone.utc).timestamp())
    pth = CAND.execute(
        "SELECT ts,close FROM candles_1m WHERE token=? AND ts>=? AND ts<=? ORDER BY ts",
        (tok.upper(), ots - 90, ots + TMAX * 60 + 90)).fetchall()
    sgn = 1 if dire == 'LONG' else -1
    TR.append(dict(id=tid, tok=tok, sgn=sgn, entry=float(entry), pnlu=float(pnlu),
                   pnlp=float(pnlp or 0), amt=float(amt), xr=str(xr),
                   sig=str(strat).replace('Hermes-', ''), ot=ot, ots=ots,
                   hold=(ct - ot).total_seconds() / 60.0, pth=pth))
n = len(TR)
HR = np.array([1 if t['pnlp'] >= 10 else 0 for t in TR])

# ---- precompute per-T arrays: eligible index, move, amt, pnlu, week
def moves_for(T):
    idx, mv, amt, pnlu, wk = [], [], [], [], []
    for j, t in enumerate(TR):
        if t['hold'] < T or not t['pth']:
            continue
        target = t['ots'] + T * 60
        cl = None
        for (ts, c) in t['pth']:
            if ts + 60 >= target:
                cl = c; break
        if cl is None:
            continue
        idx.append(j); mv.append((cl - t['entry']) / t['entry'] * 100 * t['sgn'])
        amt.append(t['amt']); pnlu.append(t['pnlu']); wk.append(t['ot'].isocalendar()[1])
    return (np.array(idx), np.array(mv), np.array(amt), np.array(pnlu), np.array(wk))

M = {T: moves_for(T) for T in Ts}
print("eligible per T:", {T: len(M[T][0]) for T in Ts})

def cell(idx, mv, amt, pnlu, theta):
    sel = mv < theta
    d = (mv[sel] / 100 * amt[sel]) - pnlu[sel]
    return int(sel.sum()), float(d.sum()), d

# ---- headline cell
idx, mv, amt, pnlu, wk = M[30]
nt, dtot, dvec = cell(idx, mv, amt, pnlu, -0.5)
print(f"\n[headline] T=30/-0.5: trig={nt} delta=${dtot:+.3f}")
print(f"  per-trade delta: mean=${dvec.mean():+.4f} median=${np.median(dvec):+.4f} "
      f"sd=${dvec.std(ddof=1):.4f} min=${dvec.min():+.3f} max=${dvec.max():+.3f}")
se = dvec.std(ddof=1) / math.sqrt(len(dvec))
print(f"  t-stat vs 0 = {dvec.mean()/se:+.2f}  (n={len(dvec)})  -> two-sided p ~ "
      f"{2*(1-0.5*(1+math.erf(abs(dvec.mean()/se)/math.sqrt(2)))):.3f}")
rng = np.random.default_rng(7)
bs = [float(rng.choice(dvec, size=len(dvec), replace=True).sum()) for _ in range(20000)]
bs.sort()
print(f"  bootstrap 95% CI for total delta: ${bs[500]:+.2f} .. ${bs[19499]:+.2f}  (median ${bs[10000]:+.2f})")
top = np.argsort(-dvec)[:8]
sel_all = (mv < -0.5)
trigs = [TR[j] for j in idx[sel_all]]
print("  top-8 contributors to the +$1.85:")
for k in top:
    t = trigs[k]
    print(f"    id={t['id']} {t['tok']:<6} {t['sig'][:20]:<20} delta=${dvec[k]:+.3f} "
          f"actual_pnl=${t['pnlu']:+.2f} move30={mv[sel_all][k]:+.2f}% hold={t['hold']:.0f}m")
concentration = float(dvec[np.argsort(-dvec)[:10]].sum())
print(f"  top-10 trades contribute ${concentration:+.2f} of ${dtot:+.2f}")
print(f"  trades with delta>0: {(dvec>0).sum()}/{len(dvec)}  sum=${dvec[dvec>0].sum():+.2f}; "
      f"delta<=0: {(dvec<=0).sum()} sum=${dvec[dvec<=0].sum():+.2f}")

# ---- concentration by token/week/signal
by_tok = defaultdict(float); by_sig = defaultdict(float); by_wk = defaultdict(lambda: [0, 0.0])
tok_of = {t['id']: t['tok'] for t in TR}
for k, t in enumerate(trigs):
    by_tok[t['tok']] += dvec[k]; by_sig[t['sig']] += dvec[k]
    key = t['ot'].isocalendar()[:2]
    by_wk[key][0] += 1; by_wk[key][1] += dvec[k]
print("\n[concentration] worst 5 tokens:", sorted(by_tok.items(), key=lambda kv: kv[1])[:5])
print("[concentration] best 5 tokens:", sorted(by_tok.items(), key=lambda kv: -kv[1])[:5])
print("[concentration] best 5 signals:", sorted(by_sig.items(), key=lambda kv: -kv[1])[:5])
print("\n[3c] weekly delta for the chosen cell (iso year-week):  n_trig  delta")
tot = 0.0
for k in sorted(by_wk):
    c, d = by_wk[k]
    tot += d
    print(f"    {k[0]}-W{k[1]:02d}   {c:>3}   ${d:+.2f}")
print(f"    TOTAL            {nt}   ${tot:+.2f}")
weeks_pos = sum(1 for k in by_wk if by_wk[k][1] > 0)
print(f"    positive weeks: {weeks_pos}/{len(by_wk)}")
# drop-the-best-week sensitivity
best_wk = max(by_wk, key=lambda k: by_wk[k][1])
print(f"    delta without best week {best_wk}: ${tot - by_wk[best_wk][1]:+.2f}")
best_tok = max(by_tok, key=by_tok.get)
print(f"    delta without best token {best_tok}: ${tot - by_tok[best_tok]:+.2f}")

# ---- permutation tests
print("\n[3b] PERMUTATION TESTS (null: min-30 move carries no information about outcome)")
def sweep_on(idx, mv, amt, pnlu, HRv):
    """full 21-cell sweep; returns list of (T,theta,trig,delta,h1,h2,hrkill)"""
    out = []
    for T in Ts:
        i2, m2, a2, p2, w2 = idx, mv, amt, pnlu, None
        for th in THETAS:
            sel = m2 < th
            dd = m2[sel] / 100 * a2[sel] - p2[sel]
            out.append((T, th, int(sel.sum()), float(dd.sum())))
    return out

# real sweep (reproduce the analyst's table ordering)
print("  real sweep (my code):")
for T in Ts:
    i2, m2, a2, p2, w2 = M[T]
    line = []
    for th in THETAS:
        nt2, dl2, _ = cell(i2, m2, a2, p2, th)
        line.append(f"th={th:>4}: n={nt2:>4} d=${dl2:+7.2f}")
    print(f"    T={T:>3}  " + " | ".join(line))

# permutation: shuffle (move,amt) pairs across eligible trades within a T
NPERM = 4000
rng = np.random.default_rng(1234)
fixed_deltas = []; best_deltas = []; pass_counts = []; best_npass = 0
fixed_cell_pass = 0
for rep in range(NPERM):
    tot_best = -1e9; npass = 0; fixed = None; fixed_ok = False
    for T in Ts:
        i2, m2, a2, p2, w2 = M[T]
        perm = rng.permutation(len(m2))
        mp, ap = m2[perm], a2[perm]           # shuffle moves+notionals across trades
        hr2 = HR[i2]
        for th in THETAS:
            sel = mp < th
            dd = mp[sel] / 100 * ap[sel] - p2[sel]
            dlt = float(dd.sum())
            kills = int(hr2[sel].sum())
            # halves by original trade order
            half = (i2 < n // 2)
            d1 = float((dd[half[sel]]).sum()); d2 = float((dd[~half[sel]]).sum())
            guard = (kills <= 1) and d1 > 0 and d2 > 0
            if guard:
                npass += 1
            tot_best = max(tot_best, dlt)
            if T == 30 and th == -0.5:
                fixed = dlt
                fixed_ok = guard
    fixed_deltas.append(fixed); best_deltas.append(tot_best); pass_counts.append(npass)
    fixed_cell_pass += int(fixed_ok)
fd = np.array(fixed_deltas); bd = np.array(best_deltas); pc_ = np.array(pass_counts)
print(f"  fixed cell (30,-0.5) under null: mean=${fd.mean():+.2f} sd=${fd.std():.2f} "
      f"p95=${np.percentile(fd,95):+.2f} p99=${np.percentile(fd,99):+.2f} "
      f"P(delta>=+1.85)={np.mean(fd>=1.85):.3f}")
print(f"  best-of-21 under null:           mean=${bd.mean():+.2f} sd=${bd.std():.2f} "
      f"median=${np.median(bd):+.2f} p95=${np.percentile(bd,95):+.2f}")
print(f"  => expected overstatement of picking the best of 21 cells ~ ${np.median(bd):+.2f} (median) / "
      f"${np.percentile(bd,95):+.2f} (95th pct)")
print(f"  guard-passing cells per permuted sweep: mean={pc_.mean():.2f}  "
      f"P(at least one guard-passing cell)={np.mean(pc_>0):.3f}  P(fixed cell passes guard)={fixed_cell_pass/NPERM:.3f}")
print(f"  P(best-of-21 >= real best +$7.09)={np.mean(bd>=7.09):.3f}")

# ---- placebo rules on real data
print("\n[3b] PLACEBO RULES (real data):")
# 1. sham theta just inside the noise: -0.05
for th in (-0.05, -0.2, -0.35, -0.5, -0.65, -0.8):
    nt2, dl2, dv = cell(idx, mv, amt, pnlu, th)
    print(f"    T=30 theta={th:>5}: trig={nt2:>4} delta=${dl2:+.2f}")
# 2. random-minute rule: exit at a random eligible minute instead of 30
rng2 = np.random.default_rng(99)
dts = []
for rep in range(2000):
    tot = 0.0; cnt = 0
    for j, t in enumerate(TR):
        if t['hold'] < 10 or not t['pth']:
            continue
        Tm = int(rng2.integers(5, 120))
        if t['hold'] < Tm:
            continue
        target = t['ots'] + Tm * 60
        cl = None
        for (ts, c) in t['pth']:
            if ts + 60 >= target:
                cl = c; break
        if cl is None:
            continue
        m = (cl - t['entry']) / t['entry'] * 100 * t['sgn']
        if m < -0.5:
            tot += m / 100 * t['amt'] - t['pnlu']; cnt += 1
    dts.append((cnt, tot))
arr = np.array([x[1] for x in dts]); cnts = np.array([x[0] for x in dts])
print(f"    random-minute (theta=-0.5): n_trig mean={cnts.mean():.0f}  delta mean=${arr.mean():+.2f} "
      f"sd=${arr.std():.2f} p95=${np.percentile(arr,95):+.2f}  P(>=1.85)={np.mean(arr>=1.85):.3f}")

# 3. theta grid resolution around the chosen cell
print("\n[3b] theta grid at T=30 (was the winner an isolated spike?):")
for th in [-1.5, -1.25, -1.0, -0.9, -0.8, -0.7, -0.6, -0.55, -0.5, -0.45, -0.4, -0.3, -0.2, -0.1, 0.0]:
    nt2, dl2, _ = cell(idx, mv, amt, pnlu, th)
    hrk = int(HR[idx][mv < th].sum())
    print(f"    theta={th:>5}: trig={nt2:>4} delta=${dl2:+7.2f}  HRkills={hrk}")

# 4. T grid resolution
print("\n[3b] T grid at theta=-0.5:")
for T in [5, 8, 10, 12, 15, 20, 25, 30, 35, 40, 45, 50, 60, 75, 90, 120]:
    if T not in M:
        i2, m2, a2, p2, w2 = moves_for(T)
    else:
        i2, m2, a2, p2, w2 = M[T]
    nt2, dl2, _ = cell(i2, m2, a2, p2, -0.5)
    hrk = int(HR[i2][m2 < -0.5].sum())
    print(f"    T={T:>4}: trig={nt2:>4} delta=${dl2:+7.2f}  HRkills={hrk}")

CAND.close(); PG.close()
print("DONE part3")
