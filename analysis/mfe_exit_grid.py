#!/usr/bin/env python3
"""
MFE-exit parameter grid (T 2026-11-01 request): does 40% give better returns,
longer holds, more profit?

Two readings of "40%" tested on the SAME closed-mirror cohort:
  arm     = MFE_EXIT_ARM_PCT in {0, 0.20, 0.40, 0.65, 1.00}% price
  giveback= MFE_EXIT_GIVEBACK_PCT in {30%, 40%}
Background stack identical to the audited jup_exit_sim v4 (tightest floor
HML CUT_LOSER/lev vs ATR SL + ATR TP + 12h timeout), engine = the replay_layers
walker the independent verifier matched 288/288. Complete-bars filter applies.

Also: entry-quality note for T's "pros enter right after peak/trough" —
first-15m favorable move + time-to-peak per trade.

Report-only: writes stdout + data/mfe_exit_grid.json. Touches nothing live.
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

import jup_exit_sim as jes
from paths import *
from hermes_constants import CUT_LOSER_PNL, PM_TRAIL_ACTIVATE_PCT
from tpsl_utils import compute_atr_sl_pct, compute_atr_tp_pct

FEE_PER_TRADE_LEV_PCT = 0.09 * 5  # taker 0.045%/side x2 x lev5 = 0.45 lev%
ARMS = (0.0, 0.20, 0.40, 0.65, 1.00)          # % price peak to engage
GIVEBACKS = (0.30, 0.40)                      # fraction of peak given back


def stats_new():
    return {'n': 0, 'w': 0, 'l': 0, 'pnl': [], 'hold': [], 'tag': {}}


def acc(s, pnl, hold, tag):
    s['n'] += 1
    s['w'] += 1 if pnl > 0.05 else 0
    s['l'] += 1 if pnl < -0.05 else 0
    s['pnl'].append(pnl)
    s['hold'].append(hold)
    s['tag'][tag] = s['tag'].get(tag, 0) + 1


def summarize(s):
    n = s['n']
    if not n:
        return None
    tot = sum(s['pnl'])
    wl = s['w'] + s['l']
    holds = sorted(s['hold'])
    return {
        'n': n, 'w': s['w'], 'l': s['l'],
        'wr': round(s['w'] / wl * 100, 1) if wl else 0.0,
        'net_gross': round(tot, 2),
        'net_after_fee': round(tot - FEE_PER_TRADE_LEV_PCT * n, 2),
        'avg': round(tot / n, 2),
        'med': round(sorted(s['pnl'])[n // 2], 2),
        'avg_hold_h': round(sum(s['hold']) / n, 2),
        'med_hold_h': round(holds[n // 2], 2),
        'tags': s['tag'],
    }


def main():
    trades = jes.load_trades()
    print(f"closed mirror trades: {len(trades)}")

    sl_pct = compute_atr_sl_pct(1.0)
    tp_pct = compute_atr_tp_pct(1.0)

    results = {}
    entry_q = []          # entry-quality note
    # baselines that don't depend on the grid
    base = {k: stats_new() for k in ('pm_actual', 'bg', 'pmwalk_g30')}

    for t in trades:
        entry = float(t['entry'])
        if not entry or entry <= 0:
            continue
        open_ts = int(t['open_t'].timestamp())
        horizon_ts = open_ts + jes.HORIZON_S
        candles = jes.load_candles(t['token'].upper(), open_ts - jes.SEC_5M,
                                   horizon_ts + jes.SEC_5M)
        if not candles:
            continue
        long_ = jes.long_p(t['dir'])
        lev = float(t['lev'] or 1)

        # floors/TP identical to shipped sim
        hml_frac = abs(CUT_LOSER_PNL) / 100.0 / max(lev, 1.0)
        floor_frac = min(hml_frac, sl_pct)
        floor_px = entry * (1 - floor_frac) if long_ else entry * (1 + floor_frac)
        tp_px = entry * (1 + tp_pct) if long_ else entry * (1 - tp_pct)

        # pm_actual baseline
        actual = float(t['pnl_pct'] or 0)
        acc(base['pm_actual'], actual,
            jes.pct_time(t['open_t'], t['close_t']), 'actual')

        # entry-quality: favorable move in first 3 bars (15m), time-to-peak
        fav15, ttp = None, None
        peak_fav, peak_ts = 0.0, open_ts
        n_bars = 0
        for ts, o, h, l, c in candles:
            if ts < open_ts or ts > horizon_ts:
                continue
            if n_bars < 3:
                f = ((max(h, o) / entry) - 1) * 100 if long_ else \
                    (1 - (min(l, o) / entry)) * 100
                fav15 = f if fav15 is None else max(fav15, f)
            f = ((h / entry) - 1) * 100 if long_ else (1 - (l / entry)) * 100
            if f > peak_fav:
                peak_fav, peak_ts = f, ts
            n_bars += 1
        if fav15 is not None:
            entry_q.append((t['id'], fav15, (peak_ts - open_ts) / 60.0, peak_fav))

        # grid: giveback outer, arm inner — rebinding jup_exit_sim's imported
        # constant is analysis-local (function reads its module global per call)
        for g in GIVEBACKS:
            jes.MFE_EXIT_GIVEBACK_PCT = g
            for a in ARMS:
                key = f"g{int(g*100)}_arm{a:.2f}"
                s = results.setdefault(key, stats_new())
                xp, xt, tag = jes.replay_layers(
                    entry, t['dir'], candles, open_ts, horizon_ts,
                    [('mfe_exit', 'mfe', a)], floor_px, tp_px)
                if xp is None:
                    continue
                pnl = jes.price_pnl_pct(t['dir'], entry, xp) * lev
                acc(s, pnl, (xt - open_ts) / 3600.0, tag)
            if g == 0.30:
                # baselines at shipped giveback
                xp, xt, tag = jes.replay_layers(
                    entry, t['dir'], candles, open_ts, horizon_ts,
                    [], floor_px, tp_px)
                if xp:
                    acc(base['bg'],
                        jes.price_pnl_pct(t['dir'], entry, xp) * lev,
                        (xt - open_ts) / 3600.0, tag)
                xp, xt, tag = jes.replay_layers(
                    entry, t['dir'], candles, open_ts, horizon_ts,
                    [('pm_trail', 'pm', 0.0)], floor_px, tp_px)
                if xp:
                    acc(base['pmwalk_g30'],
                        jes.price_pnl_pct(t['dir'], entry, xp) * lev,
                        (xt - open_ts) / 3600.0, tag)
                # COMBO rows: live system runs pm-trail AND the mfe layer
                # together (first touch wins) — these approximate shipped.
                for a in (0.20, 0.40):
                    key = f"pm+g30_arm{a:.2f}"
                    s = results.setdefault(key, stats_new())
                    xp, xt, tag = jes.replay_layers(
                        entry, t['dir'], candles, open_ts, horizon_ts,
                        [('pm_trail', 'pm', 0.0), ('mfe_exit', 'mfe', a)],
                        floor_px, tp_px)
                    if xp is None:
                        continue
                    pnl = jes.price_pnl_pct(t['dir'], entry, xp) * lev
                    acc(s, pnl, (xt - open_ts) / 3600.0, tag)
    jes.MFE_EXIT_GIVEBACK_PCT = 0.30  # restore shipped value

    # ── report ──
    hdr = (f"{'row':<14} {'n':>3} {'W':>3} {'L':>3} {'WR%':>5} {'gross':>7} "
           f"{'afterFee':>9} {'avg':>6} {'med':>6} {'avgHold':>8} "
           f"{'medHold':>8} {'floor':>5} {'mfe':>4}")
    print("\n=== GRID (arms x givebacks) + baselines — 12h horizon, gross lev% ===")
    print(hdr)
    print('-' * len(hdr))
    out = {'baselines': {}, 'grid': {}}
    for k, s in base.items():
        r = summarize(s)
        if not r:
            continue
        out['baselines'][k] = r
        print(f"{k:<14} {r['n']:>3} {r['w']:>3} {r['l']:>3} {r['wr']:>5.0f} "
              f"{r['net_gross']:>+7.2f} {r['net_after_fee']:>+9.2f} "
              f"{r['avg']:>+6.2f} {r['med']:>+6.2f} {r['avg_hold_h']:>7.1f}h "
              f"{r['med_hold_h']:>7.1f}h {r['tags'].get('floor', 0):>5} "
              f"{r['tags'].get('mfe_exit', 0):>4}")
    for key in sorted(results):
        r = summarize(results[key])
        out['grid'][key] = r
        print(f"{key:<14} {r['n']:>3} {r['w']:>3} {r['l']:>3} {r['wr']:>5.0f} "
              f"{r['net_gross']:>+7.2f} {r['net_after_fee']:>+9.2f} "
              f"{r['avg']:>+6.2f} {r['med']:>+6.2f} {r['avg_hold_h']:>7.1f}h "
              f"{r['med_hold_h']:>7.1f}h {r['tags'].get('floor', 0):>5} "
              f"{r['tags'].get('mfe_exit', 0):>4}")

    # entry-quality note
    if entry_q:
        favs = sorted(q[1] for q in entry_q)
        ttps = sorted(q[2] for q in entry_q)
        peaks = sorted(q[3] for q in entry_q)
        n = len(entry_q)
        share = sum(1 for f in favs if f >= 0.20) / n * 100
        print(f"\n=== entry-quality (T: 'pros enter right after peak/trough') ===")
        print(f"n={n}  first-15m favorable %: med={favs[n//2]:+.3f}  "
              f"share >= +0.20% in 15m: {share:.0f}%")
        print(f"time-to-peak: med={ttps[n//2]:.0f}min  "
              f"peak favorable %: med={peaks[n//2]:+.2f}")

    path = os.path.join(HERMES_DATA, 'mfe_exit_grid.json')
    with open(path, 'w') as f:
        json.dump(out, f, indent=2)
    print(f"\nreport -> {path}")
    print("ANALYSIS ONLY — no live behavior changes.")


if __name__ == '__main__':
    main()
