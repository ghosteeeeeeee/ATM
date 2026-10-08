#!/usr/bin/env python3
"""Winning DNA — POPULATION analysis, done right (2026-10-08).

Purpose: (A) descriptive pull of biggest winning trades, (B) proper
winner-vs-loser population tests with p-values + Bonferroni + forward OOS,
(C) per-signal expectancy ranking, (D) payoff-ratio root cause,
(E) RSI-band prospective test (the one surviving lead from today's audits).

Traps avoided (per brain/lessons/2026-10-08-winning-dna-failure.md):
 1. No top-K-only inference — top-K lists are DESCRIPTIVE ONLY; every
    inference test uses ALL winners vs ALL losers in the window.
 2. Selection-on-outcome — cohorts defined by sign of outcome only.
 3. Time-anchor — only entry-time recorded features used (anchored at
    open_time by construction); no close_time-anchored windows.
 4. Reproducibility — all SQL embedded; deterministic.
 5. Significance — Welch-t + Mann-Whitney + Fisher/chi2, Bonferroni
    corrected across each test family; forward-chaining OOS halves.
 6. Paper trades excluded (paper='f'), NULLs reported per variable.

Run: python3 analysis/winning_dna_pop_2026-10-08.py
"""
import sys
import psycopg2
import numpy as np
from scipy import stats

conn = psycopg2.connect(host="/var/run/postgresql", dbname="brain", user="postgres")
cur = conn.cursor()

LIVE30 = "status='closed' AND paper='f' AND pnl_pct IS NOT NULL AND close_time > now() - interval '30 days'"
LIVE90 = "status='closed' AND paper='f' AND pnl_pct IS NOT NULL AND close_time > now() - interval '90 days'"


def q(sql):
    cur.execute(sql)
    return cur.fetchall()


def meta(col):
    return f"(_signal_metadata->>'{col}')::numeric"


def hdr(t):
    print("\n" + "=" * 100)
    print(t)
    print("=" * 100)


# ---------------------------------------------------------------- PART A
hdr("PART A — BIGGEST WINNING TRADES (DESCRIPTIVE ONLY — NOT FOR INFERENCE)")

for label, where, order in [
    ("A1. ALL-TIME top 15 by pnl_pct (live closed)", "status='closed' AND paper='f' AND pnl_pct IS NOT NULL", "pnl_pct DESC"),
    ("A2. ALL-TIME top 15 by pnl_usdt (real dollars)", "status='closed' AND paper='f' AND pnl_usdt IS NOT NULL", "pnl_usdt DESC"),
    ("A3. 30d top 15 by pnl_pct", LIVE30, "pnl_pct DESC"),
    ("A4. 30d WORST 10 by pnl_pct (survivorship guard)", LIVE30, "pnl_pct ASC"),
]:
    print(f"\n--- {label}")
    rows = q(f"""
        SELECT id, token, REPLACE(strategy,'Hermes-',''), direction, ROUND(pnl_pct::numeric,2),
               ROUND(pnl_usdt::numeric,2), ROUND(leverage::numeric,1), ROUND(amount_usdt::numeric,0),
               COALESCE(exit_reason,'-'), volatility_regime,
               ROUND(entry_rsi_14::numeric,1), ROUND((trade_duration/60.0)::numeric,0),
               ROUND(mfe_pct::numeric,2), ROUND(mae_pct::numeric,2),
               open_time::timestamp(0)
        FROM trades WHERE {where} ORDER BY {order} LIMIT 15""")
    print(f"{'id':>6} {'token':<8} {'signal':<26} {'dir':<5} {'pnl%':>7} {'pnl$':>7} {'lev':>4} {'size$':>6} "
          f"{'exit':<22} {'vol':<8} {'rsi':>5} {'min':>5} {'mfe':>6} {'mae':>6}  opened")
    for r in rows:
        print(f"{r[0]:>6} {r[1]:<8} {r[2]:<26} {r[3]:<5} {r[4]:>7} {r[5]:>7} {r[6]:>4} {r[7]:>6} "
              f"{str(r[8]):<22} {str(r[9]):<8} {str(r[10]):>5} {str(r[11]):>5} {str(r[12]):>6} {str(r[13]):>6}  {r[14]}")

# Exit-reason mix of the top-25 all-time winners vs the 30d population
print("\n--- A5. Exit-reason mix: all-time top-25 winners vs 30d population")
top25 = q(f"""SELECT COALESCE(exit_reason,'-') FROM trades
               WHERE status='closed' AND paper='f' AND pnl_pct IS NOT NULL
               ORDER BY pnl_pct DESC LIMIT 25""")
pop30 = q(f"SELECT COALESCE(exit_reason,'-') FROM trades WHERE {LIVE30}")
from collections import Counter
c_top, c_pop = Counter(x[0] for x in top25), Counter(x[0] for x in pop30)
print(f"{'exit_reason':<24} {'top25':>6} {'top25%':>7} {'pop30%':>7}")
for k, v in c_top.most_common():
    print(f"{k:<24} {v:>6} {100*v/25:>6.1f}% {100*c_pop.get(k,0)/len(pop30):>6.1f}%")

# ---------------------------------------------------------------- PART B
hdr("PART B — POPULATION DNA TEST (ALL winners vs ALL losers, 30d live, n≈819)")
rows = q(f"""
    SELECT pnl_pct, pnl_usdt, entry_rsi_14, entry_bb_position,
           CASE WHEN entry_price > 0 THEN entry_atr_14/entry_price*100 END,
           leverage, amount_usdt, direction, volatility_regime,
           COALESCE(exit_reason,'-'), mfe_pct, mae_pct,
           {meta('rsi_14')}, {meta('bb_position')}, {meta('z_score')}, {meta('btc_score')},
           {meta('speed_percentile')}, {meta('gap_at_entry')}, {meta('staleness_minutes')},
           {meta('momentum_score')}, {meta('volume_spike')},
           _signal_metadata->>'btc_regime', _signal_metadata->>'wave_phase',
           date_trunc('hour', open_time), open_time
    FROM trades WHERE {LIVE30}""")
arr = list(zip(*rows))
(pnl_pct, pnl_usd, e_rsi, e_bb, atr_n, lev, size, direction, volreg,
 er, mfe, mae, m_rsi, m_bb, zsc, btcsc, speed, gap, stale, mom, vspike, btcrg, wave, hour, opents) = arr
pnl_pct = np.array([float(x) for x in pnl_pct])
win = pnl_pct > 0
lose = ~win
print(f"n={len(pnl_pct)}  winners={win.sum()}  losers={lose.sum()}  WR={100*win.mean():.1f}%")

CONT = [
    ("entry_rsi_14 (DB col)", e_rsi), ("entry_bb_position (DB)", e_bb),
    ("entry_atr_norm% (ATR/price)", atr_n), ("leverage", lev), ("size_usdt", size),
    ("meta rsi_14 (signal-time)", m_rsi), ("meta bb_position", m_bb), ("meta z_score", zsc),
    ("meta btc_score", btcsc), ("meta speed_percentile", speed),
    ("meta gap_at_entry%", gap), ("meta staleness_min", stale),
    ("meta momentum_score", mom), ("meta volume_spike", vspike),
]
print(f"\n{'variable':<30} {'n_win':>6} {'n_lose':>6} {'win_mu':>8} {'lose_mu':>8} {'win_med':>8} {'lose_med':>8} {'t_p':>9} {'mw_p':>9} {'sig(Bonf)':>10}")
pvals_t, pvals_mw = [], []
tested = []
for name, raw in CONT:
    vals = np.array([np.nan if x is None else float(x) for x in raw], dtype=float)
    wv, lv = vals[win & ~np.isnan(vals)], vals[lose & ~np.isnan(vals)]
    if len(wv) < 10 or len(lv) < 10:
        print(f"{name:<30} INSUFFICIENT DATA (n={len(wv)}/{len(lv)})")
        continue
    tp = stats.ttest_ind(wv, lv, equal_var=False).pvalue
    mp = stats.mannwhitneyu(wv, lv, alternative="two-sided").pvalue
    pvals_t.append(tp); pvals_mw.append(mp); tested.append(name)
    print(f"{name:<30} {len(wv):>6} {len(lv):>6} {wv.mean():>8.2f} {lv.mean():>8.2f} "
          f"{np.median(wv):>8.2f} {np.median(lv):>8.2f} {tp:>9.4f} {mp:>9.4f}")

m = len(tested)
print(f"\nBonferroni over {m} continuous tests -> threshold p < {0.05/m:.5f}")
for name, tp, mp in zip(tested, pvals_t, pvals_mw):
    flag = " **SIG**" if min(tp, mp) < 0.05/m else (" (raw-only)" if min(tp, mp) < 0.05 else "")
    if flag:
        print(f"  {name:<30} t_p={tp:.4f} mw_p={mp:.4f}{flag}")

print("\nCategorical:")
for name, col in [("direction", direction), ("volatility_regime", volreg),
                  ("btc_regime", btcrg), ("wave_phase", wave)]:
    cats = sorted({c for c in col if c})
    idx = {c: i for i, c in enumerate(cats)}
    W = np.zeros(len(cats)); L = np.zeros(len(cats))
    for x, isw in zip(col, win):
        if x in idx:
            if isw: W[idx[x]] += 1
            else: L[idx[x]] += 1
    try:
        chi2, p, dof, _ = stats.chi2_contingency(np.vstack([W, L]))
    except Exception:
        p = float("nan")
    print(f"  {name:<22} chi2 p={p:.4f}  | " + "  ".join(
        f"{c}:{int(W[i])}W/{int(L[i])}L({100*W[i]/max(1,W[i]+L[i]):.0f}%)" for i, c in enumerate(cats)))

# ---------------------------------------------------------------- PART B2
hdr("PART B2 — FORWARD OOS SPLIT (first half = derive, second half = test)")
times = sorted(opents)
mid = times[len(times)//2]
print(f"Split at open_time {mid}")
h1 = np.array([t < mid for t in times])
h2 = ~h1
print(f"half1 n={h1.sum()} (WR {100*win[h1].mean():.1f}%)  half2 n={h2.sum()} (WR {100*win[h2].mean():.1f}%)")
print(f"{'variable':<30} {'h1_diff':>9} {'h1_p':>9} {'h2_diff':>9} {'h2_p':>9} {'same_sign':>10}")
for name, raw in CONT:
    vals = np.array([np.nan if x is None else float(x) for x in raw], dtype=float)
    out = []
    for half in (h1, h2):
        wv = vals[half & win & ~np.isnan(vals)]; lv = vals[half & lose & ~np.isnan(vals)]
        if len(wv) < 8 or len(lv) < 8:
            out = None; break
        p = stats.mannwhitneyu(wv, lv, alternative="two-sided").pvalue
        out.append((wv.mean() - lv.mean(), p))
    if out is None:
        print(f"{name:<30} (insufficient in one half)")
        continue
    same = "YES" if np.sign(out[0][0]) == np.sign(out[1][0]) else "NO (flip!)"
    print(f"{name:<30} {out[0][0]:>9.2f} {out[0][1]:>9.4f} {out[1][0]:>9.2f} {out[1][1]:>9.4f} {same:>10}")

# ---------------------------------------------------------------- PART C
hdr("PART C — PER-SIGNAL EXPECTANCY (90d live, n>=20), Bonferroni-corrected")
rows = q(f"""
    SELECT REPLACE(strategy,'Hermes-',''), COUNT(*),
           SUM(CASE WHEN pnl_pct>0 THEN 1 ELSE 0 END),
           ROUND(AVG(pnl_pct)::numeric,3), ROUND((STDDEV(pnl_pct)/SQRT(COUNT(*)))::numeric,3),
           ROUND(SUM(pnl_usdt)::numeric,2), ROUND(AVG(amount_usdt)::numeric,2),
           MIN(open_time)::date, MAX(open_time)::date
    FROM trades WHERE {LIVE90}
    GROUP BY 1 HAVING COUNT(*) >= 20
    ORDER BY SUM(pnl_usdt) DESC""")
print(f"{'signal':<26} {'n':>5} {'WR%':>6} {'avg%':>7} {'sem%':>7} {'t_p':>8} {'binom_p':>8} {'sum$':>8} {'avg_size':>8} {'days'}")
n_sig = len(rows)
for r in rows:
    name, n, w, avg, sem, tot, avgsize, d1, d2 = r
    avg, sem = float(avg), float(sem)
    tp = 2 * (1 - stats.t.cdf(abs(avg / sem), n - 1)) if sem > 0 else float("nan")
    bp = stats.binomtest(int(w), int(n), 0.5).pvalue
    flag = " *" if min(tp, bp) < 0.05 / n_sig else ""
    print(f"{name:<26} {n:>5} {100*w/n:>6.1f} {avg:>7.3f} {sem:>7.3f} {tp:>8.4f} {bp:>8.4f} {tot:>8.2f} {avgsize:>8.0f} {d1}..{d2}{flag}")
print(f"(*) = significant after Bonferroni over {n_sig} signals (p < {0.05/n_sig:.5f})")

# ---------------------------------------------------------------- PART D
hdr("PART D — PAYOFF-RATIO ROOT CAUSE (30d live)")
w_pct = pnl_pct[win]; l_pct = pnl_pct[lose]
w_usd = np.array([float(x) for x in pnl_usd])[win]; l_usd = np.array([float(x) for x in pnl_usd])[lose]
print(f"Winners : n={win.sum():>4}  mean {w_pct.mean():+.2f}%  median {np.median(w_pct):+.2f}%  mean ${w_usd.mean():+.2f}")
print(f"Losers  : n={lose.sum():>4}  mean {l_pct.mean():+.2f}%  median {np.median(l_pct):+.2f}%  mean ${l_usd.mean():+.2f}")
print(f"Payoff ratio (mean): {abs(w_pct.mean()/l_pct.mean()):.3f}   (median): {abs(np.median(w_pct)/np.median(l_pct)):.3f}")
print(f"Expectancy/trade: {pnl_pct.mean():+.3f}%  ${np.array([float(x) for x in pnl_usd]).mean():+.3f}")
print(f"\nLoss tail:  beyond -3%: {100*np.mean(l_pct<-3):.1f}% of losers | beyond -5%: {100*np.mean(l_pct<-5):.1f}% | beyond -10%: {100*np.mean(l_pct<-10):.1f}%")
print(f"Win  tail:  beyond +3%: {100*np.mean(w_pct>3):.1f}% of winners | beyond +5%: {100*np.mean(w_pct>5):.1f}% | beyond +10%: {100*np.mean(w_pct>10):.1f}%")

print(f"\n{'exit_reason':<24} {'n':>5} {'WR%':>6} {'avgW%':>7} {'avgL%':>7} {'sum$':>8} {'avg_mfe':>8} {'avg_mae':>8}")
er = np.array([str(x) for x in er])
mfe = np.array([np.nan if x is None else float(x) for x in mfe], dtype=float)
mae = np.array([np.nan if x is None else float(x) for x in mae], dtype=float)
usd = np.array([float(x) for x in pnl_usd])
for reason in sorted(set(er), key=lambda k: -sum(usd[er == k])):
    mask = er == reason
    if mask.sum() < 5:
        continue
    wp = pnl_pct[mask & win]; lp = pnl_pct[mask & lose]
    print(f"{reason:<24} {mask.sum():>5} {100*win[mask].mean():>6.1f} "
          f"{wp.mean() if len(wp) else 0:>7.2f} {lp.mean() if len(lp) else 0:>7.2f} {usd[mask].sum():>8.2f} "
          f"{np.nanmean(mfe[mask]):>8.2f} {np.nanmean(mae[mask]):>8.2f}")

print("\nMFE capture (winners): avg MFE vs avg realized -> left on table")
print(f"  winners avg mfe={np.nanmean(mfe[win]):.2f}%  realized={w_pct.mean():.2f}%  captured {100*w_pct.mean()/np.nanmean(mfe[win]):.0f}% of MFE")
print(f"  losers avg mae={np.nanmean(mae[lose]):.2f}%  realized={l_pct.mean():.2f}%  (realized worse than MAE => slippage/gap beyond stop)")

print("\nBy leverage (30d):")
lev_a = np.array([float(x) for x in lev])
for lv_ in sorted(set(lev_a)):
    mask = lev_a == lv_
    if mask.sum() < 10:
        continue
    print(f"  {lv_:>4.0f}x: n={mask.sum():>4} WR={100*win[mask].mean():>5.1f}%  avg={pnl_pct[mask].mean():+.2f}%  sum=${usd[mask].sum():+.2f}")

# ---------------------------------------------------------------- PART E
hdr("PART E — RSI-BAND PROSPECTIVE TEST (the surviving lead; weekly stability + OOS)")
for side in ("LONG", "SHORT"):
    dmask = np.array([d == side for d in direction])
    vals = np.array([np.nan if x is None else float(x) for x in e_rsi])
    usable = dmask & ~np.isnan(vals)
    print(f"\n{side} (entry_rsi_14 coverage: {usable.sum()}/{dmask.sum()})")
    bands = [(-1, 35, "<35 oversold"), (35, 50, "35-50"), (50, 65, "50-65"), (65, 101, ">=65 overbought")]
    print(f"  {'band':<18} {'n':>5} {'WR%':>6} {'avg%':>7} {'sum$':>8}")
    for lo, hi, lab in bands:
        b = usable & (vals >= lo) & (vals < hi)
        if b.sum() < 5:
            print(f"  {lab:<18} {b.sum():>5}  (too few)")
            continue
        print(f"  {lab:<18} {b.sum():>5} {100*win[b].mean():>6.1f} {pnl_pct[b].mean():>7.3f} {usd[b].sum():>8.2f}")
    import datetime as _dt
print("\n  weekly stability (LONG only, RSI>=50 vs <50):")
dmask = np.array([d == "LONG" for d in direction])
vals = np.array([np.nan if x is None else float(x) for x in e_rsi])
usable = dmask & ~np.isnan(vals)
wk_key = np.array([_dt.date(t.year, t.month, t.day) - _dt.timedelta(days=t.weekday()) for t in opents])
for wk in sorted(set(wk_key[usable])):
    hi_ = usable & (wk_key == wk) & (vals >= 50)
    lo_ = usable & (wk_key == wk) & (vals < 50)
    if hi_.sum() + lo_.sum() < 10:
        continue
    print(f"    wk {wk}: RSI>=50 n={hi_.sum():>3} WR={100*win[hi_].mean() if hi_.sum() else 0:>5.1f}% sum${usd[hi_].sum():>6.2f} | "
          f"RSI<50 n={lo_.sum():>3} WR={100*win[lo_].mean() if lo_.sum() else 0:>5.1f}% sum${usd[lo_].sum():>6.2f}")

# Prospective filter test: LONG + entry_rsi>=50 (population, both halves)
print("\nProspective test: LONG & entry_rsi>=50 KEEP vs BLOCK (30d, and per half)")
keep = usable & (vals >= 50)
blk = usable & (vals < 50)
for lab, mask in (("30d", np.ones(len(win), bool)), ("half1", h1), ("half2", h2)):
    k = keep & mask; b = blk & mask
    if k.sum() < 5 or b.sum() < 5:
        continue
    print(f"  {lab}: KEEP n={k.sum()} WR={100*win[k].mean():.1f}% avg={pnl_pct[k].mean():+.3f}% sum=${usd[k].sum():+.2f} | "
          f"BLOCK n={b.sum()} WR={100*win[b].mean():.1f}% avg={pnl_pct[b].mean():+.3f}% sum=${usd[b].sum():+.2f}")

cur.close(); conn.close()
print("\nDONE.")
