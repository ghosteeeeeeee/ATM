#!/usr/bin/env python3
"""Claim 4 median-split variants + Claim 5 binomial tests — independent verification."""
import csv, json
import numpy as np
from scipy import stats

rows = list(csv.DictReader(open('/root/.hermes/audit/window30.csv')))
for r in rows:
    r['win'] = float(r['pnl_pct']) > 0

def fnum(v):
    return float(v) if v not in ('', None) else None

def half_test(rows_sub, label):
    w = [fnum(r['entry_rsi_14']) for r in rows_sub if r['win'] and r['entry_rsi_14'] not in ('', None)]
    l = [fnum(r['entry_rsi_14']) for r in rows_sub if not r['win'] and r['entry_rsi_14'] not in ('', None)]
    if len(w) < 2 or len(l) < 2:
        print(f"{label}: insufficient ({len(w)}/{len(l)})")
        return
    t, p = stats.ttest_ind(w, l, equal_var=False)
    u, pm = stats.mannwhitneyu(w, l, alternative='two-sided')
    print(f"{label}: trades={len(rows_sub)} n_win={len(w)} n_lose={len(l)} "
          f"avg_win={np.mean(w):.2f} avg_lose={np.mean(l):.2f} gap={np.mean(w)-np.mean(l):+.2f} "
          f"welch_p={p:.4f} mw_p={pm:.4f}")

# Variant A: split by open_time median
ots = sorted(r['open_time'] for r in rows)
med_ot = ots[len(ots)//2]
half_test([r for r in rows if r['open_time'] <= med_ot], f"A first-half open_time<={med_ot}")
half_test([r for r in rows if r['open_time'] > med_ot], f"A second-half open_time>{med_ot}")

# Variant B: split by close_time median
cts = sorted(r['close_time'] for r in rows)
med_ct = cts[len(cts)//2]
half_test([r for r in rows if r['close_time'] <= med_ct], f"B first-half close_time<={med_ct}")
half_test([r for r in rows if r['close_time'] > med_ct], f"B second-half close_time>{med_ct}")

# Variant C: split by median open_time AMONG NON-NULL RSI rows
rsi_rows = [r for r in rows if r['entry_rsi_14'] not in ('', None)]
rots = sorted(r['open_time'] for r in rsi_rows)
med_rot = rots[len(rots)//2]
half_test([r for r in rsi_rows if r['open_time'] <= med_rot], f"C first-half nonnullRSI open_time<={med_rot}")
half_test([r for r in rsi_rows if r['open_time'] > med_rot], f"C second-half nonnullRSI open_time>{med_rot}")

# how many non-null RSI by half / by week
print("\nnon-null entry_rsi_14 coverage by week (close_time):")
from collections import Counter
wk = Counter()
wkn = Counter()
for r in rows:
    k = r['close_time'][:10]
    wkn[k] += 1
    if r['entry_rsi_14'] not in ('', None):
        wk[k] += 1
import itertools
days = sorted(wkn)
for d in days:
    print(f"  {d}: {wk[d]}/{wkn[d]}")

# ---------------- CLAIM 5 binomial tests ----------------
print("\n=== CLAIM 5: binomial tests, 90d live, signals n>=20, H0: p=0.5 ===")
import subprocess
res = subprocess.run(['psql', 'host=/var/run/postgresql dbname=brain user=postgres', '-A', '-F', '|', '-t', '-c', """
SELECT replace(strategy,'Hermes-',''), count(*), count(*) FILTER (WHERE pnl_pct>0)
FROM trades
WHERE status='closed' AND paper='f' AND pnl_pct IS NOT NULL AND close_time > now() - interval '90 days'
GROUP BY strategy HAVING count(*) >= 20;
"""], capture_output=True, text=True)
sigs = []
for line in res.stdout.strip().split('\n'):
    name, n, wins = line.split('|')
    sigs.append((name, int(n), int(wins)))
print(f"signals tested: {len(sigs)} -> Bonferroni threshold p < {0.05/len(sigs):.5f}")
thr = 0.05 / len(sigs)
sig_pos, sig_neg = [], []
for name, n, wins in sorted(sigs, key=lambda x: -x[1]):
    bt = stats.binomtest(wins, n, 0.5)
    if bt.pvalue < thr:
        (sig_pos if wins/n > 0.5 else sig_neg).append((name, n, wins, bt.pvalue))
for name, n, wins, p in sig_pos:
    print(f"  SIG+ {name}: n={n} wins={wins} wr={100*wins/n:.1f}% binom_p={p:.6f}")
for name, n, wins, p in sig_neg:
    print(f"  SIG- {name}: n={n} wins={wins} wr={100*wins/n:.1f}% binom_p={p:.6f}")
if not sig_pos:
    print("  (no significantly positive signals)")
if not sig_neg:
    print("  (no significantly negative signals)")
