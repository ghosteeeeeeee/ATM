#!/usr/bin/env python3
"""Adversarial probe: can ANY reasonable split reproduce the claimed RSI half-gaps (+5.5/+3.9, p~0.08/0.10)?"""
import csv, json
import numpy as np
from scipy import stats

rows = list(csv.DictReader(open('/root/.hermes/audit/window30.csv')))
for r in rows:
    r['win'] = float(r['pnl_pct']) > 0
    try:
        m = json.loads(r['_signal_metadata']) if r['_signal_metadata'] else {}
    except Exception:
        m = {}
    r['meta_rsi'] = m.get('rsi_14')

def gaps(rows_a, rows_b, src):
    out = []
    for label, sub in [('H1', rows_a), ('H2', rows_b)]:
        w = [float(r[src]) for r in sub if r['win'] and r[src] not in ('', None)]
        l = [float(r[src]) for r in sub if not r['win'] and r[src] not in ('', None)]
        if len(w) < 2 or len(l) < 2:
            out.append(f"{label}: n/a")
            continue
        t, p = stats.ttest_ind(w, l, equal_var=False)
        out.append(f"{label} n={len(w)+len(l)} gap={np.mean(w)-np.mean(l):+.2f} p={p:.3f}")
    return ' | '.join(out)

# scan cut dates for column RSI
print("=== entry_rsi_14 column, various cut dates ===")
for cut in ['2026-09-16', '2026-09-18', '2026-09-20', '2026-09-22', '2026-09-24', '2026-09-28', '2026-09-30']:
    a = [r for r in rows if r['close_time'][:10] < cut]
    b = [r for r in rows if r['close_time'][:10] >= cut]
    print(f"cut {cut}: " + gaps(a, b, 'entry_rsi_14'))

print("\n=== meta rsi_14 (whole 30d + halves at Sep 20) ===")
allw = [float(r['meta_rsi']) for r in rows if r['win'] and isinstance(r['meta_rsi'], (int, float))]
alll = [float(r['meta_rsi']) for r in rows if not r['win'] and isinstance(r['meta_rsi'], (int, float))]
t, p = stats.ttest_ind(allw, alll, equal_var=False)
print(f"ALL: n_win={len(allw)} n_lose={len(alll)} avg_win={np.mean(allw):.2f} avg_lose={np.mean(alll):.2f} gap={np.mean(allw)-np.mean(alll):+.2f} p={p:.4f}")
a = [r for r in rows if r['close_time'][:10] < '2026-09-20']
b = [r for r in rows if r['close_time'][:10] >= '2026-09-20']
print("halves@Sep20: " + gaps(a, b, 'meta_rsi'))

# per-trade capture sanity re claim 3 losers formulation
print("\n=== claim3 loser formulations recap ===")
lose = [r for r in rows if not r['win'] and r['mae_pct'] not in ('', None) and float(r['mae_pct']) > 0 and r['leverage'] not in ('', None)]
realized = np.mean([float(r['pnl_pct']) for r in lose])
mae_lev = np.mean([float(r['mae_pct']) * float(r['leverage']) for r in lose])
ratios = np.mean([float(r['pnl_pct']) / (float(r['mae_pct']) * float(r['leverage'])) for r in lose])
print(f"losers n={len(lose)} ratio_of_avgs={100*realized/mae_lev:.1f}% avg_of_ratios={100*ratios:.1f}%")
