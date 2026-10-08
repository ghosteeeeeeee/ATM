#!/usr/bin/env python3
"""Independent verification of CLAIM 4 (RSI effect) from scratch using scipy."""
import csv, json
import numpy as np
from scipy import stats

rows = list(csv.DictReader(open('/root/.hermes/audit/window30.csv')))
for r in rows:
    r['win'] = float(r['pnl_pct']) > 0

def fnum(v):
    return float(v) if v not in ('', None) else None

# --- RSI winner vs loser ---
rsi = [(fnum(r['entry_rsi_14']), r['win']) for r in rows if r['entry_rsi_14'] not in ('', None)]
w = [x for x, win in rsi if win]
l = [x for x, win in rsi if not win]
print(f"RSI n_win={len(w)} n_lose={len(l)} avg_win={np.mean(w):.3f} avg_lose={np.mean(l):.3f} gap={np.mean(w)-np.mean(l):+.3f}")
t, pt = stats.ttest_ind(w, l, equal_var=False)
u, pm = stats.mannwhitneyu(w, l, alternative='two-sided')
print(f"Welch t={t:.3f} p={pt:.4f} | Mann-Whitney U={u:.0f} p={pm:.4f}")
print(f"Bonferroni over 14 vars: threshold p<0.00357 -> {'PASS' if min(pt,pm)<0.05/14 else 'FAIL'}")

# --- median-time split ---
times = sorted(r['open_time'] for r in rows if r['open_time'])
med_t = times[len(times)//2]
print(f"\nmedian open_time split point: {med_t}")
for label, cond in [('first half', lambda r: r['open_time'] <= med_t), ('second half', lambda r: r['open_time'] > med_t)]:
    sub = [(fnum(r['entry_rsi_14']), r['win']) for r in rows if cond(r) and r['entry_rsi_14'] not in ('', None)]
    sw = [x for x, win in sub if win]
    sl = [x for x, win in sub if not win]
    tt, pp = stats.ttest_ind(sw, sl, equal_var=False)
    um, pmm = stats.mannwhitneyu(sw, sl, alternative='two-sided')
    print(f"{label}: n_win={len(sw)} n_lose={len(sl)} avg_win={np.mean(sw):.2f} avg_lose={np.mean(sl):.2f} "
          f"gap={np.mean(sw)-np.mean(sl):+.2f} welch_p={pp:.4f} mw_p={pmm:.4f}")

# --- other categorical tests ---
from scipy.stats import chi2_contingency

def cat_test(name, keyfn):
    tbl = {}
    for r in rows:
        k = keyfn(r)
        if k in (None, ''):
            continue
        tbl.setdefault(k, [0, 0])
        tbl[k][0 if r['win'] else 1] += 1
    ks = sorted(tbl)
    if len(ks) < 2:
        print(f"{name}: <2 categories, skipped")
        return
    m = np.array([tbl[k] for k in ks])
    c2, p, dof, exp = chi2_contingency(m)
    print(f"{name}: categories={len(ks)} chi2={c2:.3f} p={p:.4f} table={ {k: tuple(tbl[k]) for k in ks} }")

print()
cat_test('direction', lambda r: r['direction'])
cat_test('volatility_regime', lambda r: r['volatility_regime'])

def meta(r, k):
    try:
        m = json.loads(r['_signal_metadata']) if r['_signal_metadata'] else {}
        return m.get(k)
    except Exception:
        return None

cat_test('btc_regime(meta)', lambda r: meta(r, 'btc_regime'))

def num_test(name, vals_w, vals_l):
    if len(vals_w) < 2 or len(vals_l) < 2:
        print(f"{name}: insufficient data ({len(vals_w)}/{len(vals_l)})")
        return
    t, pt = stats.ttest_ind(vals_w, vals_l, equal_var=False)
    u, pm = stats.mannwhitneyu(vals_w, vals_l, alternative='two-sided')
    print(f"{name}: n_win={len(vals_w)} n_lose={len(vals_l)} avg_win={np.mean(vals_w):.3f} avg_lose={np.mean(vals_l):.3f} "
          f"gap={np.mean(vals_w)-np.mean(vals_l):+.3f} welch_p={pt:.4f} mw_p={pm:.4f}")

sp_w, sp_l, zs_w, zs_l, st_w, st_l, lv_w, lv_l = [], [], [], [], [], [], [], []
for r in rows:
    v = meta(r, 'speed_percentile')
    if isinstance(v, (int, float)):
        (sp_w if r['win'] else sp_l).append(float(v))
    v = meta(r, 'z_score')
    if isinstance(v, (int, float)):
        (zs_w if r['win'] else zs_l).append(float(v))
    v = meta(r, 'staleness_minutes')
    if isinstance(v, (int, float)):
        (st_w if r['win'] else st_l).append(float(v))
    if r['leverage'] not in ('', None):
        (lv_w if r['win'] else lv_l).append(float(r['leverage']))

print()
num_test('speed_percentile(meta)', sp_w, sp_l)
num_test('z_score(meta)', zs_w, zs_l)
num_test('staleness_minutes(meta)', st_w, st_l)
num_test('leverage', lv_w, lv_l)
