#!/usr/bin/env python3
"""Home-run winners deep profile (2026-10-08, evening) — user-requested narrowing.

Question: what do the BIGGEST winners (like CRV +42.3% pump-chain+ LONG atr_trail_hit,
IMX +10.8% pump-chain+ LONG stale_exit) look like — can we find more like them?

Design (audit-proofed per brain/lessons/2026-10-08-winning-dna-failure.md):
- Cases H = closed live trades with pnl_pct >= 10 (the "home runs"; a >=20% tier is
  also profiled). Selection on outcome is EXPLICIT here — the question is
  "given an entry, what predicts a home run", a case-control design.
- Comparison set R = SAME signals, SAME direction, opened in the same date span
  (not all losers — that confound killed attempt 6). Non-home-run R trades.
- Pre-entry features only for inference (recorded at entry). Exits/hold times are
  described but labeled POST-ENTRY (mechanics, not DNA).
- Fisher/MW tests, Bonferroni over the feature family, exact n everywhere,
  Wilson CIs on home-run rates.

Run: python3 analysis/home_run_winners_2026-10-08.py
"""
import psycopg2
import numpy as np
from scipy import stats
from collections import Counter
import datetime as _dt

conn = psycopg2.connect(host="/var/run/postgresql", dbname="brain", user="postgres")
cur = conn.cursor()


def q(sql):
    cur.execute(sql)
    return cur.fetchall()


def meta(c):
    return f"(_signal_metadata->>'{c}')::numeric"


def hdr(t):
    print("\n" + "=" * 100)
    print(t)
    print("=" * 100)


def wilson(k, n, z=1.96):
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    r = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (100 * (c - r) / d, 100 * (c + r) / d)


LIVE90 = ("status='closed' AND paper='f' AND pnl_pct IS NOT NULL "
          "AND close_time > now() - interval '90 days'")

# ------------------------------------------------------------------ inventory
hdr("STEP 1 — HOME-RUN INVENTORY (90d live, pnl_pct >= 10)")
rows = q(f"""
    SELECT COUNT(*), SUM(CASE WHEN pnl_pct>=20 THEN 1 ELSE 0 END),
           ROUND(MIN(pnl_pct)::numeric,1), ROUND(MAX(pnl_pct)::numeric,1),
           MIN(open_time)::date, MAX(open_time)::date
    FROM trades WHERE {LIVE90} AND pnl_pct >= 10""")
n_all = q(f"SELECT COUNT(*) FROM trades WHERE {LIVE90}")[0][0]
n_win = q(f"SELECT COUNT(*) FROM trades WHERE {LIVE90} AND pnl_pct > 0")[0][0]
n_hr, n_20, mn, mx, d1, d2 = rows[0]
print(f"total 90d trades={n_all}  winners={n_win}  HOME RUNS (>=10%)={n_hr} "
      f"({100*n_hr/n_all:.1f}% of all, {100*n_hr/n_win:.1f}% of winners)  >=20% tier={n_20}")
print(f"range {mn}% .. {mx}%  span {d1}..{d2}")
lo, hi = wilson(n_hr, n_all)
print(f"home-run base rate {100*n_hr/n_all:.1f}%  Wilson95% CI [{lo:.1f}%, {hi:.1f}%]")

# ------------------------------------------------------------------ full profile
hdr("STEP 2 — EVERY HOME RUN, FULL PROFILE (n above)")
hr = q(f"""
    SELECT id, token, REPLACE(strategy,'Hermes-',''), direction,
           ROUND(pnl_pct::numeric,2), ROUND(pnl_usdt::numeric,2), ROUND(leverage::numeric,1),
           ROUND(amount_usdt::numeric,0), COALESCE(exit_reason,'-'), volatility_regime,
           ROUND(entry_rsi_14::numeric,1), ROUND((trade_duration/60.0)::numeric,0),
           ROUND(mfe_pct::numeric,2), ROUND(mae_pct::numeric,2),
           ROUND({meta('btc_score')}::numeric,0), _signal_metadata->>'btc_regime',
           _signal_metadata->>'wave_phase', ROUND({meta('speed_percentile')}::numeric,0),
           ROUND({meta('gap_at_entry')}::numeric,2), ROUND({meta('staleness_minutes')}::numeric,1),
           EXTRACT(hour FROM open_time)::int, open_time::timestamp(0)
    FROM trades WHERE {LIVE90} AND pnl_pct >= 10 ORDER BY pnl_pct DESC""")
print(f"{'id':>6} {'tok':<8} {'signal':<24} {'dir':<5} {'pnl%':>7} {'pnl$':>6} {'lev':>3} {'sz$':>4} "
      f"{'exit':<20} {'vol':<8} {'rsi':>5} {'min':>4} {'mfe':>5} {'mae':>5} {'btc':>4} {'regime':<13} {'wave':<13} {'spd':>4} {'gap':>5} {'stl':>5} {'hr':>3}")
for r in hr:
    print(f"{r[0]:>6} {r[1]:<8} {r[2]:<24} {r[3]:<5} {r[4]:>7} {r[5]:>6} {r[6]:>3} {r[7]:>4} "
          f"{str(r[8]):<20} {str(r[9]):<8} {str(r[10]):>5} {str(r[11]):>4} {str(r[12]):>5} {str(r[13]):>5} "
          f"{str(r[14]):>4} {str(r[15]):<13} {str(r[16]):<13} {str(r[17]):>4} {str(r[18]):>5} {str(r[19]):>5} {r[20]:>3}")

hr_ids = [r[0] for r in hr]
hr_sig = Counter(r[2] for r in hr)
hr_tok = Counter(r[1] for r in hr)
hr_exit = Counter(r[8] for r in hr)
hr_vol = Counter(str(r[9]) for r in hr)
hr_dir = Counter(r[3] for r in hr)
hr_lev = Counter(r[6] for r in hr)

# ------------------------------------------------------------------ concentration
hdr("STEP 3 — CONCENTRATION: where do home runs come from vs the 90d base rates")
pop_sig = dict(q(f"SELECT REPLACE(strategy,'Hermes-',''), COUNT(*) FROM trades WHERE {LIVE90} GROUP BY 1"))
pop_dir = dict(q(f"SELECT direction, COUNT(*) FROM trades WHERE {LIVE90} GROUP BY 1"))
pop_vol = dict(q(f"SELECT volatility_regime, COUNT(*) FROM trades WHERE {LIVE90} GROUP BY 1"))

print(f"\nBy signal (HR count vs its own 90d trade count; Fisher vs rest):")
for sig, c in hr_sig.most_common(10):
    tot = pop_sig.get(sig, 0)
    # 2x2: (HR in sig, non-HR in sig) vs (HR outside, non-HR outside)
    hr_out = n_hr - c
    non_hr_in = tot - c
    non_hr_out = (n_all - tot) - hr_out
    _, p = stats.fisher_exact([[c, non_hr_in], [hr_out, non_hr_out]])
    print(f"  {sig:<26} HR={c:>3} / {tot:>4} trades ({100*c/max(tot,1):>4.1f}% HR rate)  fisher p={p:.4f}")
print("\nBy direction / vol regime / leverage:")
for lab, cnt_map, pop_map in (("dir", hr_dir, pop_dir), ("vol", hr_vol, pop_vol)):
    for k, c in cnt_map.most_common():
        tot = pop_map.get(k, 0) or pop_map.get(k.upper(), 0) or 0
        hr_out = n_hr - c
        _, p = stats.fisher_exact([[c, max(tot - c, 0)], [hr_out, max((n_all - tot) - hr_out, 0)]])
        print(f"  {lab}:{k:<10} HR={c:>3} / {tot:>4} ({100*c/max(tot,1):>4.1f}% HR rate)  fisher p={p:.4f}")
for lev, c in hr_lev.most_common():
    tot = q(f"SELECT COUNT(*) FROM trades WHERE {LIVE90} AND leverage={lev}")[0][0]
    _, p = stats.fisher_exact([[c, tot - c], [n_hr - c, (n_all - tot) - (n_hr - c)]])
    print(f"  lev:{lev:<8} HR={c:>3} / {tot:>4} ({100*c/max(tot,1):>4.1f}% HR rate)  fisher p={p:.4f}")
print("\nTop repeat tokens among HRs:", dict(hr_tok.most_common(8)))
print("Top HR exit reasons:", dict(hr_exit.most_common(8)))

# ------------------------------------------------------------------ case-control
hdr("STEP 4 — CASE-CONTROL: HRs vs SAME-SIGNAL/SAME-DIRECTION/SAME-PERIOD non-HR trades")
hr_open = [r[21] for r in hr]
span_lo, span_hi = min(hr_open), max(hr_open)
sigs = tuple(set(r[2] for r in hr))
sig_in = ",".join(f"'{s}'" for s in sigs)
ctrl = q(f"""
    SELECT id, pnl_pct, entry_rsi_14, entry_bb_position,
           CASE WHEN entry_price>0 THEN entry_atr_14/entry_price*100 END,
           leverage, amount_usdt, volatility_regime,
           {meta('rsi_14')}, {meta('bb_position')}, {meta('z_score')}, {meta('btc_score')},
           {meta('speed_percentile')}, {meta('gap_at_entry')}, {meta('staleness_minutes')},
           {meta('momentum_score')}, _signal_metadata->>'btc_regime', _signal_metadata->>'wave_phase',
           EXTRACT(hour FROM open_time)::int, direction, REPLACE(strategy,'Hermes-','')
    FROM trades WHERE {LIVE90} AND open_time BETWEEN '{span_lo}' AND '{span_hi}'
      AND strategy LIKE 'Hermes-%' AND (REPLACE(strategy,'Hermes-','')) IN ({sig_in})""")
ctrl = [c for c in ctrl if c[0] not in set(hr_ids)]
# restrict controls to HR directions too (per-signal direction is fixed by +- suffix, but be safe)
ctrl = [c for c in ctrl if (c[19], c[20]) in set((r[3], r[2]) for r in hr)]
print(f"risk set: {len(ctrl)} non-HR trades on the same signals+directions in the HR date span "
      f"({span_lo.date()}..{span_hi.date()}); HRs n={n_hr}")

# rebuild HR rows in the same column order
hr_cols = q(f"""
    SELECT id, pnl_pct, entry_rsi_14, entry_bb_position,
           CASE WHEN entry_price>0 THEN entry_atr_14/entry_price*100 END,
           leverage, amount_usdt, volatility_regime,
           {meta('rsi_14')}, {meta('bb_position')}, {meta('z_score')}, {meta('btc_score')},
           {meta('speed_percentile')}, {meta('gap_at_entry')}, {meta('staleness_minutes')},
           {meta('momentum_score')}, _signal_metadata->>'btc_regime', _signal_metadata->>'wave_phase',
           EXTRACT(hour FROM open_time)::int, direction, REPLACE(strategy,'Hermes-','')
    FROM trades WHERE {LIVE90} AND pnl_pct >= 10""")
FEATURES = [
    ("entry_rsi_14", 2), ("entry_bb_position", 3), ("atr_norm%", 4), ("leverage", 5),
    ("size_usdt", 6), ("meta rsi_14", 8), ("meta bb_pos", 9), ("meta z_score", 10),
    ("meta btc_score", 11), ("meta speed_pct", 12), ("meta gap%", 13),
    ("meta staleness", 14), ("meta momentum", 15), ("hour_of_day", 18),
]
pvals = []
print(f"\n{'feature':<18} {'HR_n':>5} {'HR_mu':>8} {'ctrl_n':>7} {'ctrl_mu':>8} {'MW_p':>9}")
for name, idx in FEATURES:
    hv = np.array([np.nan if r[idx] is None else float(r[idx]) for r in hr_cols])
    cv = np.array([np.nan if r[idx] is None else float(r[idx]) for r in ctrl])
    hv, cv = hv[~np.isnan(hv)], cv[~np.isnan(cv)]
    if len(hv) < 5 or len(cv) < 5:
        print(f"{name:<18} insufficient (HR {len(hv)}, ctrl {len(cv)})")
        continue
    p = stats.mannwhitneyu(hv, cv, alternative="two-sided").pvalue
    pvals.append((name, p))
    print(f"{name:<18} {len(hv):>5} {hv.mean():>8.2f} {len(cv):>7} {cv.mean():>8.2f} {p:>9.4f}")

print("\nCategorical (Fisher/chi2):")
for name, idx in [("vol_regime", 7), ("btc_regime", 16), ("wave_phase", 17)]:
    hc = Counter(str(r[idx]) for r in hr_cols)
    cc = Counter(str(r[idx]) for r in ctrl)
    cats = sorted(set(hc) | set(cc), key=lambda k: -(hc.get(k, 0)))
    table = [[hc.get(k, 0), cc.get(k, 0)] for k in cats]
    try:
        chi2, p, _, _ = stats.chi2_contingency(np.array(table).T)
    except Exception:
        p = float("nan")
    print(f"  {name:<12} chi2 p={p:.4f} | " + "  ".join(f"{k}:{hc.get(k,0)}/{cc.get(k,0)}" for k in cats[:6]))

m = len(pvals)
print(f"\nBonferroni over {m} continuous features -> threshold p < {0.05/m:.5f}")
any_sig = False
for name, p in pvals:
    if p < 0.05 / m:
        print(f"  ** SURVIVES: {name} (p={p:.5f}) **")
        any_sig = True
if not any_sig:
    print("  (nothing survives)")

# ------------------------------------------------------------------ mechanics
hdr("STEP 5 — POST-ENTRY MECHANICS of HRs (descriptive: how home runs are captured, not DNA)")
print("exit reasons:", dict(hr_exit.most_common()))
durs = [r[11] for r in hr if r[11] is not None]
maes = [float(r[13]) for r in hr if r[13] is not None]
print(f"hold minutes: median {np.median(durs):.0f}, mean {np.mean(durs):.0f}, "
      f"min {min(durs):.0f}, max {max(durs):.0f}")
print(f"in-trade MAE: median {np.median(maes):.2f}%, max {max(maes):.2f}%")
print(f"share with MAE < 1%: {100*np.mean(np.array(maes)<1):.0f}%  (how few HRs ever went underwater)")
hod = Counter(r[20] for r in hr)
print("open hour (UTC) histogram:", dict(sorted(hod.items())))
# weekly
wk = Counter(_dt.date(r[21].year, r[21].month, r[21].day) - _dt.timedelta(days=r[21].weekday()) for r in hr)
print("by week (Mon-start):", dict(sorted(wk.items())))

cur.close(); conn.close()
print("\nDONE.")
