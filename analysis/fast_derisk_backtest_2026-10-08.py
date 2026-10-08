#!/usr/bin/env python3
"""Fast de-risk backtest — the "goes up immediately" mechanic (2026-10-08).

Hypothesis (from home-run analysis, §7 of the population report): home runs are
never underwater (94% MAE<1% unleveraged), so trades that are NOT in profit by
minute T are unlikely to become home runs and can be cut early at a better price
than their eventual stop.

Method: candle-level counterfactual replay. For every live closed trade opened
on/after 2026-08-21 (pnl_pct leverage-convention boundary; candles_1m cover all
alt tokens from Aug 11), walk 1-minute closes from open_time:
  - Rule fires at minute T if direction-aware unrealized price PnL < theta.
  - Simulated book: triggered -> exit at the 1m close at T (price move x notional);
    not triggered (or trade already closed before T) -> actual recorded pnl_usdt.
  - Note on fees: actual pnl_usdt excludes fees (verified on CRV: 0.94 = 11.10 x
    8.47%); the simulated exit replaces the actual exit, so round-trip fee drag
    is identical -> fee-neutral comparison. Slippage on the extra market exit
    (~0.02-0.05%) is a caveat, not modeled.

Guard metric (pre-registered): HOME RUN KILLS must be 0 (or <=1) for a cell to
be a candidate. HR = pnl_pct >= 10 (post-Aug-21 leveraged convention).
Baseline to beat: existing pump_exit_dead_money time/profit part (T=120m, theta=2.0%,
pump-chain only; its velocity clause can't reduce exits below this upper bound).
Param sweep T x theta is evaluated with per-half stability + explicit
multiple-comparison honesty (choose best cell only if 0 HR kills AND both halves positive).

Run: python3 analysis/fast_derisk_backtest_2026-10-08.py
"""
import sqlite3
import psycopg2
import numpy as np
from datetime import datetime, timezone

CAND = sqlite3.connect("/root/.hermes/data/candles.db")
PG = psycopg2.connect(host="/var/run/postgresql", dbname="brain", user="postgres")
cur = PG.cursor()

cur.execute("""
    SELECT id, token, direction, entry_price, pnl_usdt, pnl_pct, amount_usdt, leverage,
           exit_reason, REPLACE(strategy,'Hermes-',''), open_time, close_time
    FROM trades
    WHERE status='closed' AND paper='f' AND pnl_usdt IS NOT NULL AND entry_price > 0
      AND amount_usdt > 0 AND open_time >= '2026-08-21'
    ORDER BY open_time""")
TR = cur.fetchall()
print(f"population: {len(TR)} live closed trades opened >= 2026-08-21")
hr_ids = {r[0] for r in TR if (r[6] is not None) and (r[5] is not None) and float(r[5]) >= 10}
print(f"home runs in population (pnl_pct>=10): {len(hr_ids)}")
big_win_ids = {r[0] for r in TR if r[5] is not None and float(r[5]) >= 5}
print(f"big winners (>=5%): {len(big_win_ids)}")

TMAX = 120  # minutes of path to load (covers baseline 120m rule)
path_cache = {}


def get_path(token, open_ts):
    """Return list of (minute_index, close) for minutes 1..TMAX after open_ts."""
    key = (token, open_ts)
    if key in path_cache:
        return path_cache[key]
    rows = CAND.execute(
        "SELECT ts, close FROM candles_1m WHERE token=? AND ts>=? AND ts<? ORDER BY ts",
        (token, open_ts - 60, open_ts + TMAX * 60 + 60)).fetchall()
    out = []
    for ts, cl in rows:
        m = int((ts - open_ts) // 60) + 1  # minute bucket relative to entry
        if 1 <= m <= TMAX:
            out.append((m, cl))
    path_cache[key] = out
    return out


def price_at(path, T):
    """Closest close at minute >= T; None if unavailable."""
    prev = None
    for m, cl in path:
        if m >= T:
            return cl
        prev = cl
    return prev


covered = 0
missing = 0
TRD = []  # enriched rows
for (tid, tok, dire, entry, pnlu, pnlp, amt, lev, xr, sig, ot, ct) in TR:
    ots = int(ot.replace(tzinfo=timezone.utc).timestamp())
    path = get_path(tok.upper(), ots)
    if not path:
        missing += 1
        continue
    covered += 1
    hold_min = (ct - ot).total_seconds() / 60.0
    TRD.append(dict(id=tid, tok=tok, dire=dire, entry=float(entry), pnlu=float(pnlu),
                    pnlp=float(pnlp) if pnlp is not None else 0.0, amt=float(amt),
                    lev=float(lev or 1), xr=str(xr), sig=sig, ot=ot, ots=ots,
                    hold=hold_min, path=path, is_hr=tid in hr_ids, is_big=tid in big_win_ids))
print(f"candle coverage: {covered} covered, {missing} missing (excluded)")
print(f"HRs covered: {sum(1 for t in TRD if t['is_hr'])}/{len(hr_ids)}")

Ts = [10, 15, 20, 30, 45, 60, 120]
thetas = [-0.5, 0.0, 2.0]


def simulate(T, theta, pop):
    """Return metrics dict for rule (T,theta) on population pop."""
    trig = 0
    delta = 0.0          # sim - actual, dollars (fee-neutral)
    hr_kills = []
    big_killed = []
    saved_losers = 0.0
    givenup_winners = 0.0
    trig_recovered = 0
    trig_died = 0
    for t in pop:
        if t['hold'] < T:
            continue  # trade closed before the checkpoint -> rule can't fire
        cl = price_at(t['path'], T)
        if cl is None:
            continue
        move = (cl - t['entry']) / t['entry'] * 100 * (1 if t['dire'] == 'LONG' else -1)
        if move < theta:
            trig += 1
            sim_usd = move / 100 * t['amt']     # unleveraged price move x notional
            d = sim_usd - t['pnlu']
            delta += d
            if t['pnlu'] < 0:
                saved_losers += d
                trig_died += 1
            else:
                givenup_winners += d
                trig_recovered += 1
            if t['is_hr']:
                hr_kills.append((t['id'], t['tok'], t['sig'], round(move, 2), round(t['pnlp'], 1)))
            if t['is_big']:
                big_killed.append((t['id'], round(t['pnlp'], 1)))
    actual_total = sum(t['pnlu'] for t in pop)
    return dict(n=len(pop), trig=trig, delta=delta, hr_kills=hr_kills, big_killed=big_killed,
                saved=saved_losers, givenup=givenup_winners,
                rec=trig_recovered, died=trig_died, actual=actual_total)


mid = TRD[len(TRD) // 2]['ot']
h1 = [t for t in TRD if t['ot'] < mid]
h2 = [t for t in TRD if t['ot'] >= mid]
print(f"halves split at {mid}: h1 n={len(h1)} (actual ${sum(t['pnlu'] for t in h1):+.2f}), "
      f"h2 n={len(h2)} (actual ${sum(t['pnlu'] for t in h2):+.2f})")

print("\n" + "=" * 110)
print("RULE SWEEP — sim vs actual book (fee-neutral $). Guard: HR kills must be 0-1; "
      "both halves must improve.")
print("=" * 110)
print(f"{'T(min)':>6} {'theta%':>7} {'trig':>5} {'trig%':>6} {'delta_$':>8} {'h1_$':>7} {'h2_$':>7} "
      f"{'saved$':>7} {'givup$':>7} {'HRkill':>6} {'>=5%cut':>8}")
results = []
for T in Ts:
    for th in thetas:
        r = simulate(T, th, TRD)
        r1 = simulate(T, th, h1)
        r2 = simulate(T, th, h2)
        results.append((T, th, r, r1, r2))
        print(f"{T:>6} {th:>7.1f} {r['trig']:>5} {100*r['trig']/len(TRD):>5.1f}% {r['delta']:>+8.2f} "
              f"{r1['delta']:>+7.2f} {r2['delta']:>+7.2f} {r['saved']:>+7.2f} {r['givenup']:>+7.2f} "
              f"{len(r['hr_kills']):>6} {len(r['big_killed']):>8}")

print("\nBaseline — existing pump_exit_dead_money time/profit part (T=120, theta=2.0) "
      "restricted to pump-chain+ (its live scope):")
pc = [t for t in TRD if t['sig'].startswith('pump-chain')]
rb = simulate(120, 2.0, pc)
print(f"  pump-chain+ pop n={len(pc)}  trig={rb['trig']}  delta=${rb['delta']:+.2f}  "
      f"saved=${rb['saved']:+.2f} givenup=${rb['givenup']:+.2f}  HR kills={len(rb['hr_kills'])}")

print("\nSame (T=120,theta=2.0) applied to ALL signals — what the current rule misses:")
r_all = simulate(120, 2.0, TRD)
print(f"  trig={r_all['trig']}  delta=${r_all['delta']:+.2f}  HR kills={len(r_all['hr_kills'])}")

# ---------------------------------------------------------------- candidate detail
print("\n" + "=" * 110)
print("CANDIDATE CELLS (0 HR kills) — triggered-trade breakdown by signal")
print("=" * 110)
for T, th, r, r1, r2 in results:
    if len(r['hr_kills']) == 0 and r['delta'] > 0 and r1['delta'] > 0 and r2['delta'] > 0:
        print(f"\n>>> T={T}min theta={th}%  delta=${r['delta']:+.2f} (h1 ${r1['delta']:+.2f}, h2 ${r2['delta']:+.2f}) "
              f"trig={r['trig']} (died={r['died']}, recovered&cut={r['rec']})")
        bysig = {}
        for t in TRD:
            if t['hold'] < T:
                continue
            cl = price_at(t['path'], T)
            if cl is None:
                continue
            move = (cl - t['entry']) / t['entry'] * 100 * (1 if t['dire'] == 'LONG' else -1)
            if move < th:
                sim_usd = move / 100 * t['amt']
                bysig.setdefault(t['sig'], [0, 0.0])
                bysig[t['sig']][0] += 1
                bysig[t['sig']][1] += sim_usd - t['pnlu']
        for s, (n, d) in sorted(bysig.items(), key=lambda kv: -kv[1][1])[:8]:
            print(f"    {s:<28} trig={n:>3} delta=${d:+.2f}")

# ---------------------------------------------------------------- HR early behavior
print("\n" + "=" * 110)
print("GUARD ANALYSIS — were home runs really 'up immediately'? (profit at minute T, "
      "unleveraged price %, direction-aware)")
print("=" * 110)
print(f"{'T(min)':>6} {'HR n':>5} {'HR in-profit%':>13} {'HR med%':>8} {'nonHR win n':>11} "
      f"{'nw in-profit%':>13} {'nw med%':>8} {'HR rate if in-profit':>20} {'HR rate if not':>15}")
for T in [5, 10, 15, 20, 30, 45, 60]:
    hr_p, nw_p, hr_np, nw_np = [], [], [], []
    for t in TRD:
        if t['hold'] < T:
            continue
        cl = price_at(t['path'], T)
        if cl is None:
            continue
        move = (cl - t['entry']) / t['entry'] * 100 * (1 if t['dire'] == 'LONG' else -1)
        (hr_p if t['is_hr'] else nw_p if move > 0 else nw_np if not t['is_hr'] else hr_np)
        if t['is_hr']:
            (hr_p if move > 0 else hr_np).append((t, move))
        else:
            (nw_p if move > 0 else nw_np).append((t, move))
    hp = [m for _, m in hr_p]; hnp = [m for _, m in hr_np]
    wp = [m for _, m in nw_p]; wnp = [m for _, m in nw_np]
    n_all_hr = len(hp) + len(hnp)
    n_all_nw = len(wp) + len(wnp)
    r_ip = 100 * len(hp) / max(len(hp) + len(wp), 1)
    r_np = 100 * len(hnp) / max(len(hnp) + len(wnp), 1)
    print(f"{T:>6} {n_all_hr:>5} {100*len(hp)/max(n_all_hr,1):>12.0f}% {np.median(hp+hnp) if hp+hnp else 0:>8.2f} "
          f"{n_all_nw:>11} {100*len(wp)/max(n_all_nw,1):>12.0f}% {np.median(wp+wnp) if wp+wnp else 0:>8.2f} "
          f"{r_ip:>19.2f}% {r_np:>14.2f}%")

# ---------------------------------------------------------------- spot checks
print("\nSpot checks — first 60 min of the user-cited winners:")
for want in (15984, 15990):
    t = next((x for x in TRD if x['id'] == want), None)
    if not t:
        print(f"  id {want}: not in covered population")
        continue
    pts = [(m, round((cl - t['entry']) / t['entry'] * 100 * (1 if t['dire'] == 'LONG' else -1), 2))
           for m, cl in t['path'] if m in (1, 5, 10, 15, 20, 30, 45, 60)]
    print(f"  id {want} {t['tok']} {t['sig']}: profit% at min -> {pts} | actual {t['pnlp']:+.1f}% hold {t['hold']:.0f}m")

CAND.close(); PG.close()
print("\nDONE.")
