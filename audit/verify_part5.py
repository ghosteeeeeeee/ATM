#!/usr/bin/env python3
"""Audit part 5: honest out-of-sample test of the sweep, and selection-bias
quantification via the SAME selection procedure applied to random cells.
Also: fragility of the 0-HR-kill guard and economics."""
import sqlite3, psycopg2, datetime as dt, math
import numpy as np

CAND = sqlite3.connect("file:/root/.hermes/data/candles.db?mode=ro", uri=True)
PG = psycopg2.connect(host="/var/run/postgresql", dbname="brain", user="postgres")
pc = PG.cursor()
pc.execute("""
  SELECT id, token, direction, entry_price, pnl_usdt, pnl_pct, amount_usdt, open_time, close_time
  FROM trades
  WHERE status='closed' AND paper='f' AND pnl_usdt IS NOT NULL AND entry_price>0
    AND amount_usdt>0 AND open_time >= '2026-08-21'
  ORDER BY open_time""")
rows = pc.fetchall()
TR = []
for (tid, tok, dire, entry, pnlu, pnlp, amt, ot, ct) in rows:
    ots = int(ot.replace(tzinfo=dt.timezone.utc).timestamp())
    pth = CAND.execute("SELECT ts,close FROM candles_1m WHERE token=? AND ts>=? AND ts<=? ORDER BY ts",
                       (tok.upper(), ots - 90, ots + 130 * 60 + 90)).fetchall()
    sgn = 1 if dire == 'LONG' else -1
    TR.append(dict(id=tid, sgn=sgn, entry=float(entry), pnlu=float(pnlu), pnlp=float(pnlp or 0),
                   amt=float(amt), ot=ot, ots=ots, hold=(ct - ot).total_seconds() / 60.0, pth=pth))
n = len(TR)
HR = np.array([1 if t['pnlp'] >= 10 else 0 for t in TR])
order = np.arange(n)
half1 = np.array([t['ot'] < TR[n // 2]['ot'] for t in TR])

TGRID = list(range(5, 125, 5))
def moves_for(T):
    idx, mv, amt, pnlu = [], [], [], []
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
        amt.append(t['amt']); pnlu.append(t['pnlu'])
    return np.array(idx), np.array(mv), np.array(amt), np.array(pnlu)

M = {T: moves_for(T) for T in TGRID}

def cell_stats(T, theta, mask_half=None):
    idx, mv, amt, pnlu = M[T]
    sel = mv < theta
    if mask_half is not None:
        sel = sel & mask_half[idx]
    d = mv[sel] / 100 * amt[sel] - pnlu[sel]
    return int(sel.sum()), float(d.sum()), int(HR[idx][sel].sum()), idx, sel, d

def guard_pass(T, theta):
    """0 HR kills, delta>0, delta>0 in BOTH halves"""
    idx, mv, amt, pnlu = M[T]
    sel = mv < theta
    if int(HR[idx][sel].sum()) > 1:
        return False, None
    d = mv[sel] / 100 * amt[sel] - pnlu[sel]
    if d.sum() <= 0:
        return False, None
    h = half1[idx[sel]]
    if d[h].sum() <= 0 or d[~h].sum() <= 0:
        return False, None
    return True, float(d.sum())

# ---------------- 1. honest out-of-sample
print("[OOS] pick best guard-passing cell on ONE half, evaluate on the OTHER half:")
for name, pick_mask, eval_mask in [("pick h1 -> eval h2", half1, ~half1),
                                   ("pick h2 -> eval h1", ~half1, half1)]:
    cands = []
    for T in TGRID:
        for th in np.arange(-1.5, 2.01, 0.05):
            ok, dl = guard_pick = (None, None)
            idx, mv, amt, pnlu = M[T]
            sel = (mv < th) & pick_mask[idx]
            if sel.sum() == 0:
                continue
            d = mv[sel] / 100 * amt[sel] - pnlu[sel]
            if int(HR[idx][sel].sum()) > 1 or d.sum() <= 0:
                continue
            # both sub-halves of the pick half positive is not required; require 0 kills + positive
            cands.append((float(d.sum()), T, th))
    cands.sort(reverse=True)
    if not cands:
        print(f"  {name}: NO cell passes the guard on the pick half")
        continue
    best = cands[0]
    n2, d2, k2, _, _, _ = cell_stats(best[1], best[2])
    sel2 = (M[best[1]][1] < best[2]) & eval_mask[M[best[1]][0]]
    idx2 = M[best[1]][0]; mv2 = M[best[1]][1]; amt2 = M[best[1]][2]; pnlu2 = M[best[1]][3]
    dvec = (mv2[sel2] / 100 * amt2[sel2]) - pnlu2[sel2]
    print(f"  {name}: best cell T={best[1]} theta={best[2]:+.2f}  pick-half delta=${best[0]:+.2f} "
          f"-> OUT-OF-SAMPLE: trig={int(sel2.sum())} delta=${float(dvec.sum()):+.2f} HRkills={int(HR[idx2][sel2].sum())}")
    print(f"      all guard-passing cells on pick half: {len(cands)}; their eval-half deltas:")
    for dl, T, th in cands[:8]:
        s = (M[T][1] < th) & eval_mask[M[T][0]]
        dv = (M[T][1][s] / 100 * M[T][2][s]) - M[T][3][s]
        print(f"        T={T:>3} th={th:+.2f} pick=${dl:+6.2f} -> eval=${float(dv.sum()):+6.2f} "
              f"(trig={int(s.sum())}, kills={int(HR[M[T][0]][s].sum())})")

# ---------------- 2. selection procedure on RANDOM cells
print("\n[SEL] analyst's selection procedure applied to 21 RANDOM cells (2000 reps):")
rng = np.random.default_rng(20261008)
chosen_deltas = []; chosen_trigs = []; npass_dist = []; chosen_cells = []
for rep in range(2000):
    cells = [(int(rng.choice(TGRID)), float(rng.choice(np.arange(-1.5, 2.01, 0.05)))) for _ in range(21)]
    passers = []
    for (T, th) in cells:
        ok, dl = guard_pass(T, th)
        if ok:
            passers.append((dl, T, th))
    npass_dist.append(len(passers))
    if passers:
        passers.sort(reverse=True)
        chosen_deltas.append(passers[0][0]); chosen_cells.append((passers[0][1], passers[0][2]))
npass_dist = np.array(npass_dist)
cd = np.array(chosen_deltas)
print(f"  P(a random 21-cell sweep contains >=1 guard-passing cell) = {np.mean(npass_dist>0):.3f}")
print(f"  P(>=3 guard-passing cells) = {np.mean(npass_dist>=3):.3f}; mean #passing = {npass_dist.mean():.2f}")
if len(cd):
    print(f"  best guard-passing cell delta under random search: median=${np.median(cd):+.2f} "
          f"p75=${np.percentile(cd,75):+.2f} p90=${np.percentile(cd,90):+.2f} p99=${np.percentile(cd,99):+.2f}")
    print(f"  P(best random guard-passing cell >= +$1.85) = {np.mean(cd>=1.85):.3f}")
    print(f"  P(best random guard-passing cell >= +$2.50) = {np.mean(cd>=2.50):.3f}")

# ---------------- 3. fragility of the 0-HR-kill guard
print("\n[FRAG] HR-kill fragility near the chosen cell (T grid, theta=-0.5):")
for T in [20, 25, 28, 29, 30, 31, 32, 35, 40]:
    if T not in M:
        M[T] = moves_for(T)
    nt, dl, k, idx, sel, d = cell_stats(T, -0.5)
    hr_cost = float(sum(TR[j]['pnlu'] for j in idx[sel] if HR[j]))
    print(f"    T={T:>3}: trig={nt:>3} delta=${dl:+6.2f} HRkills={k} (those HRs' actual pnl=${hr_cost:+.2f})")
print("  theta grid at T=30 (HR kill cost):")
for th in [-0.7, -0.6, -0.55, -0.5, -0.475, -0.45, -0.425, -0.4, -0.35]:
    nt, dl, k, idx, sel, d = cell_stats(30, th)
    hr_cost = float(sum(TR[j]['pnlu'] for j in idx[sel] if HR[j]))
    print(f"    theta={th:>6}: trig={nt:>3} delta=${dl:+6.2f} HRkills={k} (HR pnl=${hr_cost:+.2f})")

# ---------------- 4. economics
print("\n[ECON] economics of the chosen cell:")
nt, dl, k, idx, sel, d = cell_stats(30, -0.5)
trig_notional = sum(TR[j]['amt'] for j in idx[sel])
actual_book = float(sum(t['pnlu'] for t in TR))
avg_not = float(np.mean([t['amt'] for t in TR]))
print(f"  triggered={nt}  avg notional=${avg_not:.2f}  triggered notional=${trig_notional:.0f}")
print(f"  actual book PnL (post Aug-21, unleveraged $) = ${actual_book:+.2f}")
for slip_bp in [2, 5, 10, 15, 20]:
    cost = trig_notional * slip_bp / 10000.0
    print(f"  slippage {slip_bp:>2}bp on {nt} exits -> cost ${cost:.2f}  net delta = ${dl-cost:+.2f}  "
          f"as % of book = {100*(dl-cost)/abs(actual_book):+.1f}%")
# breakeven slippage
print(f"  breakeven slippage = {1e4*dl/trig_notional:.2f} bp on the triggered notional")
# per-trade round-trip fee reality check on a few trades (does pnl_usdt exclude fees?)
print("\n[FEE] fee check: does pnl_usdt match (exit-entry)*notional exactly (i.e. no fee)?")
pc.execute("""select id, token, direction, entry_price, exit_price, pnl_usdt, amount_usdt, fees, close_time
  from trades where status='closed' and paper='f' and open_time>='2026-08-21' and exit_price>0
  order by random() limit 6""")
for (tid, tok, dire, e, x, pnlu, amt, fees, ct) in pc.fetchall():
    e = float(e); x = float(x); amt = float(amt); sgn = 1 if dire == 'LONG' else -1
    implied = (x - e) / e * amt * sgn
    print(f"    id={tid} {tok} {dire}: (exit-entry)/entry*notional=${implied:+.4f}  pnl_usdt=${float(pnlu):+.2f}  "
          f"fees={str(fees)[:40]}")

CAND.close(); PG.close()
print("DONE part5")
