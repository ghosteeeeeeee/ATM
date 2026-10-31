#!/usr/bin/env python3
"""Compare my independent replay against the probed sim per-trade, and test
whether ANY plausible cohort (prefix by close_time) reproduces the CLAIM."""
import json
import sys
import datetime as dt

sys.path.insert(0, '/root/.hermes/analysis')
import mfe_audit_replay as M

probe = json.load(open('/root/.hermes/analysis/mfe_audit_sim_probe.json'))
simwalk = probe['per_trade_walkers']
trades = M.load_trades()
cache = M.candles_cache(trades)

STRATS = ['bg', 'mfe30', 'mfe30a040', 'pmwalk', 'pm_mfe30', 'pm_mfe30a']

# ---- 1. per-trade: mine vs sim -------------------------------------------
print("=== per-trade mine vs sim (exit px + tag) ===")
mism = 0
compared = 0
for t in trades:
    tid = str(t['id'])
    if tid not in simwalk:
        continue
    for rec in simwalk[tid]:
        key = rec['layers'][0] if rec['layers'] else 'bg'
        # map sim layer-name -> my strategy name
        if rec['layers'] == []:
            mine_key = 'bg'
        elif rec['layers'] == ['mfe_exit']:
            mine_key = 'mfe30'          # sim arm constant is 0.0
        elif rec['layers'] == ['pm_trail']:
            mine_key = 'pmwalk'
        elif rec['layers'] == ['pm_trail', 'mfe_exit']:
            mine_key = 'pm_mfe30'
        else:
            continue
        px, xts, tag = M.walk(t, cache[t['id']], mine_key)
        compared += 1
        same_px = (px is not None and rec['exit_px'] is not None and
                   abs(px - rec['exit_px']) < 1e-9)
        same_tag = (tag == rec['tag'])
        if not (same_px and same_tag):
            mism += 1
            print(f"  MISMATCH id={t['id']} {mine_key}: mine px={px} tag={tag} "
                  f"| sim px={rec['exit_px']} tag={rec['tag']}")
print(f"compared {compared} per-trade exits, mismatches = {mism}")

# ---- 2. pm_actual straight from DB ---------------------------------------
print("\n=== pm_actual = DB pnl_pct? ===")
tot = 0.0
bad = 0
for t in trades:
    p = M.pnl_pct(t['dir'], t['entry'], t['exit']) * t['lev']
    if abs(p - t['pnl']) > 0.06:
        bad += 1
        print(f"  id={t['id']} DB pnl={t['pnl']:+.4f} price%*lev={p:+.4f} "
              f"price%={M.pnl_pct(t['dir'], t['entry'], t['exit']):+.4f} "
              f"lev={t['lev']}")
    tot += t['pnl']
print(f"rows where DB pnl_pct != price%*leverage (tol .06): {bad}/{len(trades)}")
print(f"sum of DB pnl_pct over cohort = {tot:+.2f}")

# ---- 3. prefix cohorts by close_time vs the CLAIM ------------------------
CLAIM = dict(pm_actual=-12.20, bg=-68.03, mfe30=29.63, mfe30a040=27.18,
             pmwalk=26.37, pm_mfe30=30.89, pm_mfe30a=28.65)
print("\n=== claim vs prefix cohorts (first k trades by close_time) ===")
by_close = sorted(trades, key=lambda t: t['close_t'])
print(f"{'k':>3} " + " ".join(f"{k:>9}" for k in CLAIM))
print(f"{'claim':>3} " + " ".join(f"{CLAIM[k]:>+9.2f}" for k in CLAIM))
for k in range(len(by_close) - 3, len(by_close) + 1):
    if k < 1:
        continue
    sub = by_close[:k]
    vals = {}
    for s in CLAIM:
        if s == 'pm_actual':
            vals[s] = sum(t['pnl'] for t in sub)
        else:
            v = 0.0
            for t in sub:
                px, xts, tag = M.walk(t, cache[t['id']], s)
                v += M.pnl_pct(t['dir'], t['entry'], px) * t['lev']
            vals[s] = v
    print(f"{k:>3} " + " ".join(f"{vals[s]:>+9.2f}" for s in CLAIM))

# ---- 4. brute force any subset of size 45 (on ids) -----------------------
print("\n=== brute force: any 45-of-48 subset matching claim? ===")
per = {}
for t in trades:
    row = {'pm_actual': t['pnl']}
    for s in STRATS:
        px, xts, tag = M.walk(t, cache[t['id']], s)
        row[s] = M.pnl_pct(t['dir'], t['entry'], px) * t['lev']
    per[t['id']] = row
need = {s: CLAIM[s] for s in CLAIM}     # subset must sum to claim exactly
# only check pairs/triples dropped from full set
best = None
from itertools import combinations
full = {s: sum(per[t['id']][s] for t in trades) for s in CLAIM}
ids = [t['id'] for t in trades]
for drop_n in (1, 2, 3):
    for combo in combinations(ids, drop_n):
        err = sum(((full[s] - sum(per[i][s] for i in combo)) - CLAIM[s]) ** 2
                  for s in CLAIM) / len(CLAIM)
        if best is None or err < best[0]:
            best = (err, combo)
print(f"best drop-set = {best[1]}  rms-err = {best[0]**0.5:.3f} "
      f"(<0.05 would mean 'claim reproduces')")
err, combo = best
for s in CLAIM:
    got = full[s] - sum(per[i][s] for i in combo)
    print(f"   {s:<12} {got:>+8.2f}   claim {CLAIM[s]:>+8.2f}   diff {got-CLAIM[s]:+8.2f}")
