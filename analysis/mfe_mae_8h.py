#!/usr/bin/env python3
"""
mfe_mae_8h.py — T directive 2026-10-26: last 100 trades, MFE/MAE over the 8h
since OPEN, how many were exited early while a bigger move followed AFTER our
exit, and what MAE must be survived to capture the big MFEs.

Definitions (explicit, so numbers are reproducible):
  Window W     = [open_time, open_time + 8h] (fixed for every trade, regardless
                 of when we exited).
  MFE_8h       = max favorable excursion in W  (SHORT: (entry-min_low)/entry;
                 LONG: (max_high-entry)/entry) using is_closed candles.
  MAE_8h       = max adverse excursion in W   (SHORT: (max_high-entry)/entry;
                 LONG: (entry-min_low)/entry).
  fav_at_exit  = signed favorable move entry->exit (only if exit within W).
  fav_after    = max favorable move strictly AFTER exit_time up to window end.
  stopped_early_and_bigger_move:
                 exit happened inside W AND fav_after >= fav_at_exit + T
                 (T = threshold; swept 0.2/0.3/0.5%).
  MAE_to_peak  = max adverse from open up to the candle of MFE_8h's peak —
                 the drawdown you must survive if you ride to the big MFE.
  HML cap      = CUT_LOSER_PNL account% / leverage  (price-term cap; imported live
                 from hermes_constants — was 4% when the 2026-10-26 report was
                 produced, 6% since the 2026-10-27 coupled trial).

Data: brain PG (trades) + data/candles.db (candles_1m, fallback candles_5m).
Deterministic; no network; read-only.
"""
import os
import sys
import datetime as dt
from collections import Counter, defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'scripts'))
from paths import HERMES_DATA  # noqa: E402

import psycopg2  # noqa: E402
from psycopg2.extras import RealDictCursor  # noqa: E402
import sqlite3  # noqa: E402
from _secrets import BRAIN_DB_DICT  # noqa: E402

N = 100
WINDOW_S = 8 * 3600
from hermes_constants import CUT_LOSER_PNL  # live value — do NOT hardcode (review MED-1: hardcoding froze 4.0 after the 10-27 trial moved it to 6.0)
CUT_LOSER_PNL_PCT = abs(CUT_LOSER_PNL)   # % account loss -> hard_max_loss trigger
BIG_MFE_SWEEP = (0.5, 0.8, 1.0, 1.5)     # % price
EARLY_SWEEP = (0.2, 0.3, 0.5)            # % price post-exit continuation


def ep(ts):
    return int(ts.timestamp())


def pct(x):
    return f"{x * 100:+.2f}%"


def load_trades():
    conn = psycopg2.connect(**BRAIN_DB_DICT)
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("""
        SELECT token, direction, signal, entry_price, exit_price,
               open_time, close_time, leverage, pnl_pct, pnl_usdt,
               amount_usdt, exit_reason, stop_loss, status
        FROM trades
        WHERE status = 'closed' AND entry_price > 0 AND exit_price > 0
          AND open_time > NOW() - INTERVAL '30 days'
        ORDER BY open_time DESC
        LIMIT %s
    """, (N,))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows


def load_candles(db, table, token, t0, t1):
    c = sqlite3.connect(db, timeout=10)
    try:
        return c.execute(
            f"SELECT ts, open, high, low, close FROM {table} "
            f"WHERE token = ? AND ts >= ? AND ts <= ? AND is_closed = 1 ORDER BY ts",
            (token, t0, t1)).fetchall()
    finally:
        c.close()


def analyze_one(tr, db1m, db5m):
    tok = tr['token']
    d = tr['direction'].upper()
    entry = float(tr['entry_price'])
    o = ep(tr['open_time'])
    w1 = o + WINDOW_S
    exit_t = ep(tr['close_time']) if tr['close_time'] else None
    exit_in_w = exit_t is not None and exit_t <= w1

    # Union of BOTH series for extremes: partial 1m windows (gaps) stay correct
    # when 5m covers them and vice versa — min/max over the union can only widen
    # toward the true extremes.
    c1 = load_candles(db1m, 'candles_1m', tok, o, w1)
    c5 = load_candles(db1m, 'candles_5m', tok, o, w1)  # 5m table lives in candles.db
    cov1 = len(c1) / (WINDOW_S // 60)
    cov5 = len(c5) / (WINDOW_S // 300)
    coverage = max(cov1, cov5)
    method = '1m' if cov1 >= cov5 else '5m'
    if coverage < 0.50:
        return {'token': tok, 'direction': d, 'ok': False,
                'reason': f'insufficient candles 1m={len(c1)} 5m={len(c5)} (cov={coverage:.0%})'}
    cands = sorted(c1 + c5, key=lambda r: r[0])

    if d == 'SHORT':
        fav_fn = lambda v: (entry - v) / entry      # favorable = price down
        adv_fn = lambda v: (v - entry) / entry
    else:
        fav_fn = lambda v: (v - entry) / entry
        adv_fn = lambda v: (entry - v) / entry

    best_fav, best_fav_ts = -1e9, None
    best_adv = -1e9
    for (ts, op, hi, lo, cl) in cands:
        f_cand = max(fav_fn(lo), fav_fn(hi))
        a_cand = max(adv_fn(hi), adv_fn(lo))
        if f_cand > best_fav:
            best_fav, best_fav_ts = f_cand, ts
        if a_cand > best_adv:
            best_adv = a_cand

    # MAE from open up to the MFE-peak candle (drawdown endured while riding to peak)
    mae_to_peak = -1e9
    for (ts, op, hi, lo, cl) in cands:
        if ts > best_fav_ts:
            break
        mae_to_peak = max(mae_to_peak, max(adv_fn(hi), adv_fn(lo)))
    if mae_to_peak <= -1e8:
        mae_to_peak = 0.0

    # fav_at_exit depends only on the two prices — compute directly
    fav_at_exit = None
    if exit_t is not None and exit_in_w:
        fav_at_exit = ((entry - float(tr['exit_price'])) / entry if d == 'SHORT'
                       else (float(tr['exit_price']) - entry) / entry)

    # Post-exit continuation inside the window (candles STARTING at/after exit —
    # the candle straddling exit_t is excluded, conservative for "bigger move")
    fav_after_best, adv_after_best = 0.0, 0.0
    if exit_t is not None and exit_in_w:
        for (ts, op, hi, lo, cl) in cands:
            if ts >= exit_t:
                fav_after_best = max(fav_after_best,
                                     max(fav_fn(lo), fav_fn(hi)))
                adv_after_best = max(adv_after_best,
                                     max(adv_fn(hi), adv_fn(lo)))

    lev = int(tr['leverage'] or 1)
    hml_cap = CUT_LOSER_PNL_PCT / lev if lev else None   # price-term % cap
    sl_dist = None
    if tr['stop_loss']:
        sl_dist = abs(float(tr['stop_loss']) - entry) / entry * 100.0  # % price

    return {
        'token': tok, 'direction': d, 'ok': True, 'method': method,
        'n_candles': len(cands), 'coverage': coverage,
        'signal': tr['signal'], 'lev': lev,
        'amount_usdt': float(tr['amount_usdt'] or 0),
        'open': tr['open_time'], 'exit': tr['close_time'], 'exit_in_w': exit_in_w,
        'open_epoch': o, 'peak_ts': best_fav_ts,
        'entry': entry, 'exit_price': float(tr['exit_price']),
        'exit_reason': tr['exit_reason'] or '?',
        'pnl_pct': float(tr['pnl_pct'] or 0), 'pnl_usdt': float(tr['pnl_usdt'] or 0),
        'mfe': best_fav, 'mae': best_adv, 'mae_to_peak': mae_to_peak,
        'fav_at_exit': fav_at_exit, 'fav_after': fav_after_best,
        'adv_after': adv_after_best,
        'sl_dist_pct': sl_dist, 'hml_cap_pct': hml_cap,
        'held_to_window': not exit_in_w,
    }


def main():
    db1m = os.path.join(HERMES_DATA, 'candles.db')
    db5m = os.path.join(HERMES_DATA, 'candles_5m.db')
    rows = load_trades()
    print(f"# MFE/MAE 8h — last {len(rows)} closed trades (30d, by open_time DESC)\n")
    res, skipped = [], []
    for tr in rows:
        a = analyze_one(tr, db1m, db5m)
        (res if a['ok'] else skipped).append(a)

    skipped_txt = ', '.join(f"{s['token']}:{s['reason']}" for s in skipped) or 'none'
    print(f"analyzed={len(res)}  skipped={len(skipped)} ({skipped_txt})")
    methods = Counter(r['method'] for r in res)
    print(f"dominant candle method: {dict(methods)} (union of 1m+5m used for extremes)")
    covs = sorted(r['coverage'] for r in res)
    print(f"window coverage (best series): min={covs[0]:.0%} "
          f"median={covs[len(covs)//2]:.0%} max={covs[-1]:.0%}")
    low = [r for r in res if r['coverage'] < 0.80]
    low_txt = ', '.join(f"{r['token']} {r['coverage']:.0%}" for r in low) or 'none'
    print(f"coverage <80% (extremes may understate): {len(low)} ({low_txt})")

    # ── 1. Exit census ────────────────────────────────────────────────────
    print("\n## 1. Exit-reason census (n=%d)" % len(res))
    for k, v in Counter(r['exit_reason'] for r in res).most_common():
        sub = [r for r in res if r['exit_reason'] == k]
        wp = sum(1 for r in sub if r['pnl_usdt'] > 0)
        print(f"  {k:28s} n={v:3d}  win={wp:2d}  pnl=${sum(r['pnl_usdt'] for r in sub):+.2f}")

    # ── 2. How many exited early while a bigger move followed AFTER exit ──
    # Definition (v2, audited): bigger_move_T = fav_after >= max(fav_at_exit, 0) + T.
    # Requiring max(cap,0) fixes v1's flaw: a stopped-out loser (cap<0) used to
    # "count" on any mildly favorable post-exit tick. Losers and winners are
    # reported separately.
    exitable = [r for r in res if r['fav_at_exit'] is not None and not r['held_to_window']]
    losers = [r for r in exitable if r['fav_at_exit'] < 0]
    winners = [r for r in exitable if r['fav_at_exit'] >= 0]
    print(f"\n## 2. Exits inside the 8h window (n={len(exitable)}; held-to-8h excluded: "
          f"{sum(1 for r in res if r['held_to_window'])})")
    print(f"  split: profitable exits={len(winners)}, stopped-out/negative={len(losers)}")
    for T in EARLY_SWEEP:
        thr = T / 100.0
        early = [r for r in exitable
                 if r['fav_after'] >= max(r['fav_at_exit'], 0.0) + thr]
        wl = sum(1 for r in early if r['fav_at_exit'] < 0)
        print(f"  T={T:.1f}% price: stopped-early + bigger-move-followed = "
              f"{len(early)}/{len(exitable)} ({100*len(early)/max(1,len(exitable)):.0f}%)  "
              f"[{len(early)-wl} winners giving up tail, {wl} losers it went without us]")
    print("  (a) LOSERS — post-exit continuation (trade stopped out, then it moved our way):")
    for T in (0.3, 0.5, 1.0, 2.0):
        n = sum(1 for r in losers if r['fav_after'] >= T / 100.0)
        print(f"    fav_after >= {T:.1f}% : {n}/{len(losers)}")
    print("  (b) WINNERS — tail given up (fav_after beyond what we captured):")
    for T in (0.3, 0.5, 1.0):
        n = sum(1 for r in winners if r['fav_after'] >= r['fav_at_exit'] + T / 100.0)
        print(f"    fav_after >= cap + {T:.1f}pp : {n}/{len(winners)}")
    print("  by exit reason @T=0.3% (v2 definition):")
    T = 0.3
    early = [r for r in exitable
             if r['fav_after'] >= max(r['fav_at_exit'], 0.0) + T / 100.0]
    c = Counter(r['exit_reason'] for r in early)
    for k, v in c.most_common():
        print(f"    {k:28s} {v}")

    # Magnitude + dollars of what was left (foregone = fav_after - capture, x notional)
    if early:
        misses = sorted((r['fav_after'] - r['fav_at_exit']) * 100 for r in early)
        q = lambda p: misses[min(len(misses) - 1, int(p * len(misses)))]
        forg = sum((r['fav_after'] - r['fav_at_exit']) * r['amount_usdt'] for r in early)
        realized = sum(r['pnl_usdt'] for r in early)
        print(f"  magnitude of foregone move (early group, n={len(early)}): "
              f"median {q(.5):.2f}pp  p75 {q(.75):.2f}pp  p90 {q(.9):.2f}pp  max {misses[-1]:.2f}pp")
        print(f"  foregone GROSS dollars vs captured (early group): "
              f"-${forg - realized:.2f}  [foregone ${forg:+.2f} vs realized ${realized:+.2f} net]")
        long_n = sum(1 for r in early if r['direction'] == 'LONG')
        print(f"  direction split of early group: LONG {long_n} / SHORT {len(early) - long_n}")

    # Did we exit before the window peak at all?
    exit_before_peak = [r for r in exitable if r['fav_at_exit'] is not None
                        and r['mfe'] > r['fav_at_exit'] + 1e-9]
    print(f"  exited before the 8h favorable peak at all: {len(exit_before_peak)}/{len(exitable)}")

    # ── 3. Big-MFE cohort and the MAE needed to ride it ───────────────────
    print("\n## 3. Big-MFE cohort — MAE you must survive to catch the move")
    hdr = (f"  {'MFE>=':>6s} {'n':>3s} {'MAE_to_peak p50':>15s} {'p75':>7s} {'p90':>7s} "
           f"{'max':>7s} {'>SLdist':>8s} {'>HMLcap':>8s} {'med exit':>10s}")
    print(hdr)
    for thr in BIG_MFE_SWEEP:
        coh = [r for r in res if r['mfe'] >= thr / 100.0]
        if not coh:
            print(f"  {thr:>5.1f}% {'':>3s}  n=0")
            continue
        mae_pk = sorted(r['mae_to_peak'] * 100 for r in coh)
        q = lambda p: mae_pk[min(len(mae_pk) - 1, int(p * len(mae_pk)))]
        over_sl = sum(1 for r in coh
                      if r['sl_dist_pct'] is not None
                      and r['mae_to_peak'] * 100 > r['sl_dist_pct'])
        over_hml = sum(1 for r in coh
                       if r['hml_cap_pct'] and r['mae_to_peak'] * 100 > r['hml_cap_pct'])
        med_exit = sorted(r['exit_reason'] for r in coh)[len(coh) // 2]
        print(f"  {thr:>5.1f}% {len(coh):>3d} {q(.5):>15.2f} {q(.75):>7.2f} {q(.9):>7.2f} "
              f"{mae_pk[-1]:>7.2f} {over_sl:>4d}/{len(coh):<3d} {over_hml:>4d}/{len(coh):<3d} "
              f"{med_exit:>10s}")

    # Leverage math: to survive MAE with HML(cut_loser% acct) intact, max lev = cut_loser / MAE%
    print(f"\n  HML survival math (CUT_LOSER {CUT_LOSER_PNL_PCT:g}% account / MAE price%):")
    for thr in (0.8, 1.0, 1.5):
        coh = [r for r in res if r['mfe'] >= thr / 100.0]
        if not coh:
            continue
        mae_pk = sorted(r['mae_to_peak'] * 100 for r in coh)
        for p in (0.5, 0.75, 0.9):
            m = mae_pk[min(len(mae_pk) - 1, int(p * len(mae_pk)))]
            max_lev = (CUT_LOSER_PNL_PCT / m) if m > 0 else float('inf')
            print(f"    MFE>={thr:.1f}% cohort, MAE@p{int(p*100)}={m:.2f}% price "
                  f"-> max leverage with HML intact = {max_lev:.1f}x "
                  f"(account risk {CUT_LOSER_PNL_PCT}% = ${CUT_LOSER_PNL_PCT/100*50:.2f} on $50)")

    # What current stops would do vs what big-MFE required
    print("\n## 4. Would current stops have survived the ride? (MFE>=0.8% cohort)")
    coh = [r for r in res if r['mfe'] >= 0.8 / 100.0]
    if coh:
        killed_by_sl = [r for r in coh if r['sl_dist_pct'] is not None
                        and r['mae_to_peak'] * 100 > r['sl_dist_pct']]
        killed_by_hml = [r for r in coh if r['hml_cap_pct']
                         and r['mae_to_peak'] * 100 > r['hml_cap_pct']]
        surv = [r for r in coh if r not in killed_by_sl and r not in killed_by_hml]
        print(f"  n={len(coh)}: per-trade SL stops you first: {len(killed_by_sl)} | "
              f"HML cap stops you first: {len(killed_by_hml)} | "
              f"survivable to peak with BOTH intact: {len(surv)}")
        if surv:
            s_pnl = sum(r['pnl_usdt'] for r in surv)
            # Riding to the 8h peak: dollar PnL = price-move(decimal) x NOTIONAL
            # (amount_usdt is notional incl. leverage; pnl_pct is ROI on margin).
            # Gross — fees not deducted (realized figures include fees).
            ride = sum(r['mfe'] * r['amount_usdt'] for r in surv)
            print(f"  survivors to peak: realized-as-traded ${s_pnl:+.2f} (net of fees) vs "
                  f"riding-to-8h-peak ${ride:+.2f} (gross, same trades/size)")
        # minimal SL to survive
        mae_pk = sorted(r['mae_to_peak'] * 100 for r in coh)
        need = lambda p: mae_pk[min(len(mae_pk) - 1, int(p * len(mae_pk)))]
        print(f"  SL needed to survive to peak: p50 {need(.5):.2f}% | p75 {need(.75):.2f}% | "
              f"p90 {need(.9):.2f}% price  (vs HARD floor SL band 0.6-1.03%)")
        # What stops do we actually have on these trades?
        sls = sorted(r['sl_dist_pct'] for r in coh if r['sl_dist_pct'] is not None)
        if sls:
            qs = lambda p: sls[min(len(sls) - 1, int(p * len(sls)))]
            print(f"  actual per-trade SL distance on the cohort: p50 {qs(.5):.2f}% | "
                  f"p75 {qs(.75):.2f}% | p90 {qs(.9):.2f}% | max {sls[-1]:.2f}%")
        # how long until the peak (capital lock time)
        ttp = sorted((r['peak_ts'] - r['open_epoch']) / 60 for r in coh)
        qt = lambda p: ttp[min(len(ttp) - 1, int(p * len(ttp)))]
        print(f"  minutes from open to 8h-peak: p50 {qt(.5):.0f}m | p75 {qt(.75):.0f}m | "
              f"p90 {qt(.9):.0f}m | max {ttp[-1]:.0f}m")

        # 4b. WHOLE-COHORT scenario (no survivor selection): what if every trade in
        # the cohort had stop = W and HML coupled to allow it (CUT_LOSER >= lev*W)?
        # outcome = ride to 8h peak if MAE_to_peak <= W, else stopped at -W.
        # Gross of fees both ways; scenario, not a recommendation.
        print("\n  4b. Wider-stop scenario applied to the WHOLE cohort (gross, no fees):")
        actual = sum(r['pnl_usdt'] for r in coh)
        print(f"    actual (as traded, net): ${actual:+.2f}")
        for W in (0.8, 1.17, 1.62):
            outcomes = []
            for r in coh:
                if r['mae_to_peak'] * 100 <= W:
                    outcomes.append(r['mfe'] * r['amount_usdt'])          # ride to peak
                else:
                    outcomes.append(-(W / 100.0) * r['amount_usdt'])      # stopped at -W
            n_stop = sum(1 for r in coh if r['mae_to_peak'] * 100 > W)
            cut_los = 5 * W  # required CUT_LOSER % account at 5x to not HML-first
            print(f"    SL={W:.2f}% (+HML coupled to {cut_los:.1f}% account @5x): "
                  f"scenario gross ${sum(outcomes):+.2f} | stops hit {n_stop}/{len(coh)} | "
                  f"max single-trade scenario loss ${min(outcomes):+.2f}")

    # ── 5. Split-half OOS sanity (first 50 vs last 50 by time) ────────────
    print("\n## 5. Split-half check (reproducibility of the early-exit phenomenon @T=0.3%)")
    ordered = sorted(exitable, key=lambda r: r['open'])
    for name, half in (("older half", ordered[:len(ordered)//2]),
                       ("newer half", ordered[len(ordered)//2:])):
        e = [r for r in half if r['fav_after'] >= max(r['fav_at_exit'], 0.0) + 0.003]
        print(f"  {name:11s}: {len(e)}/{len(half)}")

    # ── 6. The ugb_pt / trail family detail ───────────────────────────────
    print("\n## 6. Early-exit detail @T=0.3% (v2) — worst 15 (most missed)")
    early = sorted([r for r in exitable
                    if r['fav_after'] >= max(r['fav_at_exit'], 0.0) + 0.003],
                   key=lambda r: -(r['fav_after'] - r['fav_at_exit']))[:15]
    for r in early:
        print(f"  {r['open'].strftime('%m-%d %H:%M')} {r['token']:6s} {r['direction']:5s} "
              f"{(r['exit_reason'] or '?'):22s} cap={r['fav_at_exit']*100:+.2f}% "
              f"after={r['fav_after']*100:+.2f}%  missed={(r['fav_after']-r['fav_at_exit'])*100:+.2f}pp "
              f"mfe8h={r['mfe']*100:+.2f}% mae_pk={r['mae_to_peak']*100:.2f}% "
              f"pnl=${r['pnl_usdt']:+.2f}")

    print("\nDONE")


if __name__ == '__main__':
    main()
