#!/usr/bin/env python3
"""
JUP HML shadow eval (pre-registered 2026-10-31 CEO verdict #1; executed
2026-11-02 per CEO consult item (a)).

Question: would a TIGHTER hard-max-loss for jup_yolo trades — floor at
-0.65% or -0.50% price (vs the current CUT_LOSER/lev baseline, -0.80% @5x)
— be net-positive on the closed mirror book?

CEO guardrails implemented here (verbatim from consult verdict):
  G1  REPLAY FILLS, don't count flags: every counterfactual runs through the
      audited replay_layers engine (jup_exit_sim, independently verified
      288/288), distinct-id basis, one row per trade.
  G2  COUNT WINNER PREEMPTION, not just loser savings: both legs reported
      (the 10-31 verdict's failure mode: saved +$0.69, preempted winners
      -$0.79 -> net -$0.10).
  G3  SIGN-STABILITY: report the min number of worst (dip-event) deltas whose
      removal flips the net <= 0, plus a seeded bootstrap 95% CI. Marginal
      net (< ~$0.50) or flips <= 2 -> EXTEND, do not enforce.
  G4  FEES IN: dollar nets carry 0.09% of notional round-trip; the DELTA
      between arms is fee-neutral (same n, same trades) and says so.

Stack per trade = shipped reality: pm-trail layer + mfe-exit (arm 0.40,
giveback 0.30) + floor + ATR TP + 12h timeout, complete-bars candles.
Pre-registration: enforce ONLY if net-positive vs the -4.00 baseline.

ANALYSIS ONLY — enforcement (if any) is a separate, reviewed change.
"""
import json
import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

import jup_exit_sim as jes
from paths import *
from hermes_constants import CUT_LOSER_PNL
from tpsl_utils import compute_atr_sl_pct, compute_atr_tp_pct

FEE_ROUND_TRIP = 0.0009          # 0.045%/side x2 of NOTIONAL
CF_FLOORS = (('hml65', 0.0065), ('hml50', 0.0050))   # fixed price-% floors
MFE_ARM_PRICE = 0.40             # shipped arm, literal (sim M3 lesson)
N_BOOT = 10000
FLIP_STABILITY_REQ = 3           # G3: net must survive removing < 3 dip events
MARGINAL_USD = 0.50              # G3: below this at n>=40 -> extend sample


def main():
    # --pm-only: run the pre-mfe-exit stack (pm trail alone) for robustness —
    # the pre-registration predates mfe-exit; REJECT on BOTH stacks is the
    # only result that closes the question cleanly.
    pm_only = '--pm-only' in sys.argv
    trades = jes.load_trades()
    print(f"closed mirror trades: {len(trades)}  "
          f"stack: {'pm-trail only' if pm_only else 'pm-trail + mfe(0.40)'}")

    sl_pct = compute_atr_sl_pct(1.0)
    tp_pct = compute_atr_tp_pct(1.0)
    rows, skipped = [], 0
    pending_horizon = 0
    import time as _time
    now_ts = int(_time.time())

    for t in trades:
        entry = float(t['entry'])
        if not entry or entry <= 0:
            continue
        open_ts = int(t['open_t'].timestamp())
        horizon_ts = open_ts + jes.HORIZON_S
        candles = jes.load_candles(t['token'].upper(), open_ts - jes.SEC_5M,
                                   horizon_ts + jes.SEC_5M)
        if not candles:
            skipped += 1
            continue
        if horizon_ts > now_ts:
            pending_horizon += 1
        lev = float(t['lev'] or 1)
        notional = float(t['amount'] or 0)
        long_ = jes.long_p(t['dir'])

        tp_px = entry * (1 + tp_pct) if long_ else entry * (1 - tp_pct)
        layers = ([('pm_trail', 'pm', 0.0)] if pm_only else
                  [('pm_trail', 'pm', 0.0), ('mfe_exit', 'mfe', MFE_ARM_PRICE)])

        def _run(floor_frac):
            fp = entry * (1 - floor_frac) if long_ else entry * (1 + floor_frac)
            xp, xt, tag = jes.replay_layers(
                entry, t['dir'], candles, open_ts, horizon_ts, layers, fp, tp_px)
            if xp is None:
                return None, None
            return jes.price_pnl_pct(t['dir'], entry, xp) * lev, tag

        base_frac = abs(CUT_LOSER_PNL) / 100.0 / lev      # actual system floor
        pnl_b, tag_b = _run(base_frac)
        if pnl_b is None:
            skipped += 1
            continue
        row = {'id': t['id'], 'token': t['token'], 'dir': t['dir'],
               'base': pnl_b, 'base_tag': tag_b, 'lev': lev,
               'notional': notional, 'base_usd': pnl_b / 100.0 / lev * notional}
        for name, frac in CF_FLOORS:
            pnl_c, tag_c = _run(frac)
            row[name] = pnl_c
            row[name + '_tag'] = tag_c
            row[name + '_delta'] = pnl_c - pnl_b
            row[name + '_delta_usd'] = (pnl_c - pnl_b) / 100.0 / lev * notional
        rows.append(row)

    n = len(rows)
    print(f"walked: {n}  skipped(no candles/baseline): {skipped}  "
          f"horizon-unfinished: {pending_horizon}")
    if n < 40:
        print(f"PRE-REGISTRATION: n={n} < 40 — NOT evaluable, EXTEND.")
        return

    def boot_ci(vals, seed=20261102):
        rng = random.Random(seed)
        means = []
        m = len(vals)
        for _ in range(N_BOOT):
            means.append(sum(vals[rng.randrange(m)] for _ in range(m)) / m)
        means.sort()
        return means[int(0.025 * N_BOOT)], means[int(0.975 * N_BOOT)]

    def min_flips_to_erase(deltas):
        """G3: count of worst deltas that must be removed to flip net <= 0."""
        if sum(deltas) <= 0:
            return 0
        s = sorted(deltas)          # most negative first
        run = 0.0
        for k, d in enumerate(s, 1):
            run += d
            if sum(deltas) - run <= 0:
                return k
        return len(s) + 1           # cannot be erased

    base_win = sum(1 for r in rows if r['base'] > 0.05)
    base_net = sum(r['base'] for r in rows)
    base_usd = sum(r['base_usd'] for r in rows)
    print(f"\nbaseline (CUT_LOSER {CUT_LOSER_PNL}/lev, stack pm+mfe): "
          f"net={base_net:+.2f} lev% = ${base_usd:+.2f}  wins={base_win}/{n}")

    verdicts = {}
    for name, frac in CF_FLOORS:
        deltas = [r[name + '_delta'] for r in rows]
        deltas_usd = [r[name + '_delta_usd'] for r in rows]
        net = sum(deltas)
        net_usd = sum(deltas_usd)
        savings_pos = sum(d for d in deltas_usd if d > 0)
        preempt_neg = sum(d for d in deltas_usd if d < 0)
        # G2 granular: base WIN -> cf non-win (the true preemption class)
        win_to_nonwin = [r for r in rows
                         if r['base'] > 0.05 and r[name] <= 0.05]
        winners_hurt = [r for r in rows
                        if r['base'] > 0.05 and r[name + '_delta'] < -0.05]
        cf_net = sum(r[name] for r in rows)
        cf_usd = sum(r[name] / 100.0 / r['lev'] * r['notional'] for r in rows)
        lo, hi = boot_ci(deltas_usd)
        flips = min_flips_to_erase(deltas_usd)
        # G3 decision
        if net_usd <= 0:
            decision = 'REJECT'
        elif flips <= 2:
            decision = 'EXTEND (sign-fragile: <=2 dip events flip it)'
        elif net_usd < MARGINAL_USD:
            decision = f'EXTEND (marginal: ${net_usd:.2f} < ${MARGINAL_USD})'
        else:
            decision = 'ENFORCE'
        verdicts[name] = decision
        print(f"\n--- {name} (floor {-frac*100:.2f}% price) ---")
        print(f"  cf net: {cf_net:+.2f} lev% = ${cf_usd:+.2f}  "
              f"(baseline ${base_usd:+.2f})")
        print(f"  DELTA vs baseline: {net:+.2f} lev% = ${net_usd:+.2f}   "
              f"[fees: delta is fee-neutral — same n/trades in both arms]")
        print(f"  legs (USD): loser savings ${savings_pos:+.2f} | "
              f"winner preemption ${preempt_neg:+.2f}   "
              f"(G2: win→nonwin n={len(win_to_nonwin)}, "
              f"winners-hurt n={len(winners_hurt)})")
        print(f"  sign-stability: bootstrap95% CI of mean-per-trade delta "
              f"${lo:+.3f}..${hi:+.3f} (×n≈ total) | "
              f"min dip-events to erase net = {flips} (need >= "
              f"{FLIP_STABILITY_REQ})")
        print(f"  VERDICT: {decision}")

    # after-fee absolute nets (G4) for context
    fee_total = FEE_ROUND_TRIP * sum(r['notional'] for r in rows)
    print(f"\n[G4] total round-trip fees on book = ${fee_total:.2f} "
          f"(applies identically to baseline and both arms)")

    out = {'n': n, 'skipped': skipped, 'pending_horizon': pending_horizon,
           'base_net_lev': round(base_net, 2), 'base_net_usd': round(base_usd, 2),
           'verdicts': verdicts,
           'per_threshold': {
               name: {
                   'net_lev': round(sum(r[name + '_delta'] for r in rows), 2),
                   'net_usd': round(sum(r[name + '_delta_usd'] for r in rows), 2),
                   'decision': verdicts[name],
               } for name, _ in CF_FLOORS}}
    path = os.path.join(HERMES_DATA,
                        'jup_hml_shadow_eval_pm_only.json' if pm_only
                        else 'jup_hml_shadow_eval.json')
    with open(path, 'w') as f:
        json.dump(out, f, indent=2)
    print(f"\nreport -> {path}")
    print("ANALYSIS ONLY — enforcement (if verdict=ENFORCE) is a separate "
          "reviewed change per pre-registration.")


if __name__ == '__main__':
    main()
