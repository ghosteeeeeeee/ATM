#!/usr/bin/env python3
"""brain_auditor #143 creative: pre-entry displacement (mandate: trend entries win, chop entries lose).

Hypothesis: winners already moved in our direction in the 5 1m candles BEFORE open_time;
losers entered flat/chop (no displacement) or chased (already >0.4% extended).

Method: for every closed trade in window, signed pre-entry return =
  dir-adjusted (close[t-1] - close[t-6]) / close[t-6] over 1m candles strictly before open_time.
Units: PRICE-MOVE % (NOT pnl_pct — leverage landmine).
Stats: n/WR/pnl_usdt by bucket, Fisher exact (scipy-free), split-half OOS, winner-impact.
Self-check: n_trades_matched must be >=90% of queried trades.
"""
import sys, sqlite3, datetime, math
sys.path.insert(0, '/root/.hermes/scripts')
from paths import *
import psycopg2

WINDOW = sys.argv[1] if len(sys.argv) > 1 else '14 days'
MIN_OPEN = sys.argv[2] if len(sys.argv) > 2 else None

def fisher_2x2(w1, l1, w2, l2):
    """Two-sided Fisher exact on [[w1,l1],[w2,l2]] (hypergeometric, margins fixed).

    #143 bug fix: the first version passed `a` (wins in group1) as the count for the
    WRONG margin class, producing p=0.106 where the correct value is 0.5101 for the
    14d table. Self-checked against independent brute force (see FISHER_SELFCHECK).
    """
    from math import comb
    N = w1 + l1 + w2 + l2
    R1 = w1 + l1          # group1 size
    C1 = w1 + w2          # total wins
    def P(x):
        return comb(R1, x) * comb(N - R1, C1 - x) / comb(N, C1)
    lo, hi = max(0, C1 - (N - R1)), min(R1, C1)
    p_obs = P(w1)
    return sum(P(x) for x in range(lo, hi + 1) if P(x) <= p_obs + 1e-12) / \
           sum(P(x) for x in range(lo, hi + 1))

# independent brute-force references (computed outside this code path, 2026-10-25)
FISHER_SELFCHECK = [((53, 100, 40, 63), 0.5101), ((5, 5, 5, 5), 1.0),
                    ((9, 1, 1, 9), 0.001093)]
for _cells, _ref in FISHER_SELFCHECK:
    _got = fisher_2x2(*_cells)
    assert abs(_got - _ref) < 0.0005, f"Fisher selfcheck FAIL {_cells}: {_got} != {_ref}"
print("FISHER SELFCHECK PASS:", [(c, round(fisher_2x2(*c), 4)) for c, _ in FISHER_SELFCHECK])

conn_pg = psycopg2.connect(host='/var/run/postgresql', database='brain', user='postgres')
cur = conn_pg.cursor()
q = """SELECT id, token, signal, direction, open_time, entry_price, pnl_usdt, pnl_pct, mfe_pct
       FROM trades WHERE status='closed' AND close_time > NOW() - INTERVAL %s"""
args = [WINDOW]
if MIN_OPEN:
    q += " AND open_time > %s"; args.append(MIN_OPEN)
cur.execute(q, args)
trades = cur.fetchall()
conn_pg.close()

cdb = sqlite3.connect(str(CANDLES_DB), timeout=15)
rows_out = []
miss = 0
for tid, tok, sig, d, ot, ep, pnl, pnlp, mfe in trades:
    ots = int(ot.replace(tzinfo=datetime.timezone.utc).timestamp())
    rs = cdb.execute(
        "SELECT ts, close FROM candles_1m WHERE token=? AND ts < ? ORDER BY ts DESC LIMIT 6",
        (tok.upper(), ots)).fetchall()
    if len(rs) < 6:
        miss += 1; continue
    rs = rs[::-1]
    base, lastc = rs[0][1], rs[-1][1]
    if not base:
        miss += 1; continue
    ret = (lastc - base) / base * 100.0
    if d == 'SHORT':
        ret = -ret
    rows_out.append(dict(id=tid, tok=tok, sig=sig, d=d, ret=ret, pnl=float(pnl),
                         win=float(pnl) > 0, ot=ot, mfe=float(mfe) if mfe is not None else None))

print(f"window={WINDOW} trades={len(trades)} matched={len(rows_out)} miss={miss}")
if len(rows_out) < 0.9 * len(trades):
    print("SELFCHECK FAIL: match rate < 90%"); sys.exit(1)
print("SELFCHECK PASS: match rate >= 90%")

BUCKETS = [("<=0 (no displacement)", -99, 0.0),
           ("0-0.15", 0.0, 0.15),
           ("0.15-0.40", 0.15, 0.40),
           (">0.40 (chased)", 0.40, 99)]
print("\nbucket                     n   WR%   pnl_usdt  avg_mfe")
res = {}
for name, lo, hi in BUCKETS:
    g = [r for r in rows_out if lo < r['ret'] <= hi] if lo > -99 else \
        [r for r in rows_out if r['ret'] <= 0]
    if not g:
        continue
    n = len(g); w = sum(1 for r in g if r['win']); pnl = sum(r['rstrip'] if False else r['pnl'] for r in g)
    mfe = [r['mfe'] for r in g if r['mfe'] is not None]
    res[name] = (n, w, pnl)
    print(f"{name:26s} {n:3d} {100*w/n:5.1f} {pnl:+9.2f}  {sum(mfe)/len(mfe):.3f}")

# key contrast: no-displacement vs >=0.15
nd = [r for r in rows_out if r['ret'] <= 0]
dv = [r for r in rows_out if r['ret'] > 0.15]
a, b = sum(1 for r in nd if r['win']), len(nd)
c, d_ = sum(1 for r in dv if r['win']), len(dv)
if b and d_:
    p = fisher_2x2(a, b - a, c, d_ - c)
    print(f"\nCONTRAST no-disp n={b} WR={100*a/b:.1f} pnl={sum(r['pnl'] for r in nd):+.2f} "
          f"vs >0.15 n={d_} WR={100*c/d_:.1f} pnl={sum(r['pnl'] for r in dv):+.2f}  fisher_p={p:.3f}")

# split-half OOS (by open_time)
rows_out.sort(key=lambda r: r['ot'])
h = len(rows_out)//2
for label, half in (("old", rows_out[:h]), ("new", rows_out[h:])):
    n1 = [r for r in half if r['ret'] <= 0]; n2 = [r for r in half if r['ret'] > 0.15]
    if n1 and n2:
        print(f"{label} half: no-disp n={len(n1)} WR={100*sum(r['win'] for r in n1)/len(n1):.1f} "
              f"pnl={sum(r['pnl'] for r in n1):+.2f} | >0.15 n={len(n2)} "
              f"WR={100*sum(r['win'] for r in n2)/len(n2):.1f} pnl={sum(r['pnl'] for r in n2):+.2f}")

# winner-impact: winners with ret<=0 (a filter requiring displacement would kill them)
winn = [r for r in rows_out if r['win']]
kill_w = [r for r in winn if r['ret'] <= 0]
print(f"\nWINNER IMPACT: {len(kill_w)}/{len(winn)} winners had ret<=0 "
      f"({100*len(kill_w)/len(winn):.1f}% of winners, pnl {sum(r['pnl'] for r in kill_w):+.2f})")

# confound: top families
from collections import defaultdict
fam = defaultdict(list)
for r in rows_out:
    fam[r['sig']].append(r)
print("\nfamily confound (n>=10):  no-disp WR/pnl vs disp WR/pnl")
for f, g in sorted(fam.items(), key=lambda kv: -len(kv[1])):
    if len(g) < 10: continue
    ndg = [r for r in g if r['ret'] <= 0]; dvg = [r for r in g if r['ret'] > 0.15]
    s = f"{f:24s} n={len(g):3d} | no-disp "
    s += f"n={len(ndg)} WR={100*sum(r['win'] for r in ndg)/len(ndg):.0f}% pnl={sum(r['pnl'] for r in ndg):+.2f}" if ndg else "n=0"
    s += f" | disp n={len(dvg)} WR={100*sum(r['win'] for r in dvg)/len(dvg):.0f}% pnl={sum(r['pnl'] for r in dvg):+.2f}" if dvg else " | disp n=0"
    print(" ", s)

# extremes: chase bucket outcome
ch = [r for r in rows_out if r['ret'] > 0.40]
print(f"\nCHASE >0.40: n={len(ch)} WR={100*sum(r['win'] for r in ch)/len(ch) if ch else 0:.1f}% "
      f"pnl={sum(r['pnl'] for r in ch):+.2f}")
