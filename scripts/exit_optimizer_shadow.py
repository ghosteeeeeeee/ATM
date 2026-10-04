#!/usr/bin/env python3
"""
exit_optimizer_shadow.py — Trade Learning System P2: shadow exit-config optimizer.

For every ADMITTED cell (n>=15) in the T2 cell store, replays recorded MFE/MAE
against a small bounded grid of initial SL/TP calibrations and compares
simulated expectancy vs the actual outcome. SHADOW MODE: writes proposals only
— changes nothing live. Proposals land in automation/ceo/ceo_kanban.md for CEO
approval; live application happens post-freeze via signal_exit_configs.

v1 calibration (per execution plan): SL from MAE quantiles, TP from MFE
quantiles of the cell itself. Search space does NOT touch PM_TRAIL_ACTIVATE_PCT
/ PM_TRAIL_DISTANCE_PCT (CEO-protected trailing params — initial SL/TP only).

Honest counterfactual limits (documented in output):
  - MFE/MAE were recorded UNDER current exit configs. Simulating TIGHTER SLs
    than the live ATR floor is defensible (mae is clipped at the live SL, so
    mae>=proposed-SL reliably implies the tighter stop would have fired).
  - Simulating WIDER SLs is NOT reliable (a trade stopped at -1.3% may have
    gone deeper; recorded mae is clipped). Wider-SL rows are flagged
    'unreliable_wider' and excluded from proposal candidates.
  - TP-side simulation assumes price touched MFE before adverse move; where
    mfe>=TP and mae>=SL simultaneously, path order is unknown — both bounds
    computed (optimistic: TP hit; pessimistic: SL hit).

Usage: python3 scripts/exit_optimizer_shadow.py [--days 90] [--min-n 15]
"""
import sys
import os
import json
import sqlite3
import argparse
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paths import HERMES_DATA

CELL_DB = os.path.join(os.path.dirname(HERMES_DATA), 'brain', 'cell_stats.db')
OUT_JSON = os.path.join(HERMES_DATA, 'exit_optimizer_proposals.json')
LIVE_CONFIG_TABLE = os.path.join(os.path.dirname(HERMES_DATA), 'brain', 'signal_exit_configs.db')

# Bounded v1 grid (fractions of price move, e.g. 0.013 = 1.3%)
SL_CANDIDATES = ('mae_p25', 'mae_p50')      # from cell's own MAE quantiles
TP_CANDIDATES = ('mfe_p50', 'mfe_p75')      # from cell's own MFE quantiles


def log(msg):
    ts = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
    print(f'[{ts}] [exit_opt_shadow] {msg}', flush=True)


def load_admitted_cells(min_n):
    conn = sqlite3.connect(CELL_DB)
    try:
        cur = conn.cursor()
        rows = cur.execute("""
            SELECT signal, direction, regime, n, wr_raw, avg_pnl_raw, total_pnl,
                   mfe_p25, mfe_p50, mfe_p75, mae_p25, mae_p50
            FROM cells WHERE n >= ?
        """, (min_n,)).fetchall()
        cur.close()
        return rows
    finally:
        conn.close()


def fetch_cell_trades(days):
    """All closed trades 90d with fields needed for simulation."""
    import psycopg2
    from _secrets import BRAIN_DB_DICT
    conn = None
    try:
        conn = psycopg2.connect(**BRAIN_DB_DICT)
        cur = conn.cursor()
        cur.execute("""
            SELECT signal, direction,
                   -- FIX 2026-10-04 (gap-hunt): must match cell_stats.py regime source
                   -- (volatility_regime preferred) or by_cell keys silently miss the
                   -- regime-correct store and admitted cells get skipped as having
                   -- 'insufficient trades' (the first gap-hunt P2 run evaluated only
                   -- 18/53 cells this way — verdict was noise, not signal).
                   COALESCE(NULLIF(volatility_regime, ''), NULLIF(regime, ''), 'UNKNOWN') AS regime,
                   pnl_pct, mfe_pct, mae_pct, exit_reason, entry_rsi_14
            FROM trades
            WHERE status='closed'
              AND close_time > NOW() - (%s || ' days')::interval
              AND pnl_usdt IS NOT NULL
        """, (str(days),))
        rows = cur.fetchall()
        cur.close()
        return rows
    finally:
        if conn:
            conn.close()


def simulate(trades, sl_dist, tp_dist):
    """Simulate initial SL/TP for a list of (pnl_pct, mfe_pct, mae_pct) trades.
    Returns (pessimistic_avg, optimistic_avg, n_ambiguous, n_tightened, n_widened)."""
    pess, opt = [], []
    n_amb = n_tight = n_widen = 0
    for pnl, mfe, mae in trades:
        pnl = float(pnl or 0)
        mfe = abs(float(mfe or 0))
        mae = abs(float(mae or 0))
        sl_hit = mae >= sl_dist
        tp_hit = mfe >= tp_dist
        if sl_hit and tp_hit:
            n_amb += 1
            pess.append(-sl_dist * 100)   # pessimistic: SL first
            opt.append(tp_dist * 100)     # optimistic: TP first
        elif tp_hit:
            opt.append(tp_dist * 100)
            pess.append(tp_dist * 100)
        elif sl_hit:
            # tighter-than-live SL: clipped mae reliably implies stop would fire
            if mae <= sl_dist * 1.25:
                n_tight += 1
            else:
                n_widen += 1
            pess.append(-sl_dist * 100)
            opt.append(-sl_dist * 100)
        else:
            # neither level touched: actual trailing/other exit stands in
            pess.append(pnl)
            opt.append(pnl)
    avg = lambda xs: round(sum(xs) / len(xs), 4) if xs else 0.0
    return avg(pess), avg(opt), n_amb, n_tight, n_widen


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--days', type=int, default=90)
    ap.add_argument('--min-n', type=int, default=15)
    args = ap.parse_args()

    if not os.path.exists(CELL_DB):
        log(f'cell store missing: {CELL_DB} — run cell_stats.py first')
        return 1

    cells = load_admitted_cells(args.min_n)
    log(f'{len(cells)} admitted cells (n>={args.min_n}) loaded from T2 store')
    all_trades = fetch_cell_trades(args.days)
    log(f'{len(all_trades)} closed trades fetched ({args.days}d)')

    # index trades by cell
    by_cell = {}
    for sig, direction, regime, pnl, mfe, mae, exit_reason, rsi in all_trades:
        key = ((sig or '').strip(), (direction or '').strip().upper(),
               (regime or 'UNKNOWN').strip().upper())
        by_cell.setdefault(key, []).append((pnl, mfe, mae))

    proposals = []
    for (signal, direction, regime, n, wr, avg_pnl, total_pnl,
         mfe25, mfe50, mfe75, mae25, mae50) in cells:
        trades = by_cell.get((signal, direction, regime), [])
        if len(trades) < args.min_n or mae25 is None or mfe75 is None:
            continue
        actual_avg = round(avg_pnl, 4)
        for sl_q, sl_dist in (('mae_p25', mae25 / 100.0), ('mae_p50', mae50 / 100.0)):
            if not sl_dist or sl_dist <= 0:
                continue
            for tp_q, tp_dist in (('mfe_p50', mfe50 / 100.0), ('mfe_p75', mfe75 / 100.0)):
                if not tp_dist or tp_dist <= 0:
                    continue
                pess, opt, n_amb, n_tight, n_widen = simulate(trades, sl_dist, tp_dist)
                # reliability: proposals require the SL simulation to be tight-side dominated
                reliable = n_widen <= len(trades) * 0.25
                delta_pess = round(pess - actual_avg, 4)
                delta_opt = round(opt - actual_avg, 4)
                proposals.append({
                    'signal': signal, 'direction': direction, 'regime': regime,
                    'n': len(trades), 'actual_avg_pct': actual_avg,
                    'sl_quantile': sl_q, 'sl_dist_pct': round(sl_dist * 100, 3),
                    'tp_quantile': tp_q, 'tp_dist_pct': round(tp_dist * 100, 3),
                    'sim_pessimistic_pct': pess, 'sim_optimistic_pct': opt,
                    'delta_pessimistic': delta_pess, 'delta_optimistic': delta_opt,
                    'n_ambiguous': n_amb, 'n_tightened': n_tight, 'n_widened': n_widen,
                    'reliable': reliable,
                    'proposal_candidate': bool(reliable and delta_pess > 0.05),
                })

    candidates = [p for p in proposals if p['proposal_candidate']]
    snapshot = {
        'computed_at': datetime.now(timezone.utc).isoformat(),
        'window_days': args.days, 'min_n': args.min_n,
        'cells_evaluated': len({(p['signal'], p['direction'], p['regime']) for p in proposals}),
        'configs_simulated': len(proposals),
        'proposal_candidates': len(candidates),
        'mode': 'SHADOW — nothing applied live; CEO kanban approval required',
        'counterfactual_caveat': ('MFE/MAE recorded under live configs; tight-side SL sims reliable, '
                                  'wide-side flagged; ambiguous mfe+mae trades bounded pessimistic/optimistic'),
        'proposals': sorted(proposals, key=lambda p: (-p['delta_pessimistic'], p['signal'])),
    }
    tmp = OUT_JSON + '.tmp'
    with open(tmp, 'w') as f:
        json.dump(snapshot, f, indent=1)
    os.replace(tmp, OUT_JSON)

    log(f"cells_evaluated={snapshot['cells_evaluated']} configs_simulated={snapshot['configs_simulated']} "
        f"proposal_candidates={snapshot['proposal_candidates']}")
    log('top 8 candidates by pessimistic delta:')
    for p in sorted(candidates, key=lambda x: -x['delta_pessimistic'])[:8]:
        log(f"  {p['signal'][:30]:30} {p['direction']:5} {p['regime']:8} n={p['n']:3} "
            f"SL={p['sl_dist_pct']:.2f}%({p['sl_quantile']}) TP={p['tp_dist_pct']:.2f}%({p['tp_quantile']}) "
            f"actual={p['actual_avg_pct']:+.3f}% pess={p['sim_pessimistic_pct']:+.3f}% "
            f"Δ={p['delta_pessimistic']:+.3f}% amb={p['n_ambiguous']}")
    log(f'proposals JSON: {OUT_JSON}')
    log(f'live config store NOT written: {LIVE_CONFIG_TABLE} (post-freeze, CEO-approved only)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
