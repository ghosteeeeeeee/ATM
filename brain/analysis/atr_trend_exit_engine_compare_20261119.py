#!/usr/bin/env python3
"""atr_trend_exit_engine_compare_20261119.py — which exit engine is most
profitable for atr_trend_accel, on shadow_trades.db (n=1807 complete-case
closed shadow replays of the SAME signals through every engine)?

Reproduces: engine table, paired diffs vs live pm_trail (t + normal-approx p),
time split (11-13), mfe_exit simulation (arm 0.40%, giveback 30% -> 70% of MFE
on armed rows; unarmed rows fall through to recorded outcome, gross basis).
Basis: GROSS pct (fee 0.04 + slippage 0.10 shown separately). Run: python3.
"""
import sqlite3, json, statistics, math

DB = '/root/.hermes/brain/shadow_trades.db'
ARM, GIVE = 0.40, 0.30

def P(v):
    try:
        return json.loads(v) if v else None
    except Exception:
        return None

def main():
    conn = sqlite3.connect(DB)
    rows = conn.execute("""SELECT created_at, net_pnl_pct, mfe_pct, fee_pct, slippage_pct,
        exit_pm_trail_json, exit_ride_it_json, exit_universal_hold_json, exit_atr_json,
        exit_pump_exit_json, exit_rr_engine_json, exit_hard_max_json, exit_cut_loser_json,
        exit_speed_stale_json
        FROM shadow_trades WHERE source LIKE 'atr-trend%' AND closed=1
        ORDER BY created_at""").fetchall()
    recs = []
    for r in rows:
        pm, ri, uh = P(r[5]), P(r[6]), P(r[7])
        if not (pm and ri and uh):
            continue
        recs.append({
            't': r[0], 'pm': float(pm['pnl_pct']), 'ri': float(ri['pnl_pct']),
            'uh': float(uh['pnl_pct']),
            'at': float(P(r[8])['pnl_pct']) if P(r[8]) else None,
            'pu': float(P(r[9])['pnl_pct']) if P(r[9]) else None,
            'rr': float(P(r[10])['pnl_pct']) if P(r[10]) else None,
            'hm': float(P(r[11])['pnl_pct']) if P(r[11]) else None,
            'cl': float(P(r[12])['pnl_pct']) if P(r[12]) else None,
            'ss': float(P(r[13])['pnl_pct']) if P(r[13]) else None,
            'mfe': float(r[2]) if r[2] is not None else None,
            'net': float(r[1]) if r[1] is not None else 0.0,
            'fee': float(r[3] or 0), 'slip': float(r[4] or 0),
        })
    print(f'complete-case rows: {len(recs)}')
    for name, k in (('pm_trail(LIVE)', 'pm'), ('ride_it(24h)', 'ri'), ('universal_hold(8h)', 'uh'),
                    ('atr_sl_tp', 'at'), ('hard_max', 'hm'), ('cut_loser', 'cl'),
                    ('speed_stale', 'ss'), ('pump_exit', 'pu'), ('rr_engine', 'rr')):
        v = [x[k] for x in recs if x[k] is not None]
        if not v:
            continue
        print(f'  {name:>20}  n={len(v):>4}  mean={statistics.mean(v):+.3f}pp  '
              f'med={statistics.median(v):+.3f}  WR={100*sum(1 for q in v if q>0)/len(v):.1f}%')

    def paired(a, b, label):
        d = [x[a] - x[b] for x in recs if x[a] is not None]
        m, n = statistics.mean(d), len(d)
        t = m / (statistics.stdev(d) / math.sqrt(n))
        p = 2 * (1 - 0.5 * (1 + math.erf(abs(t) / math.sqrt(2))))
        print(f'  {label}: {m:+.3f}pp  t={t:.1f}  p={p:.2e}  '
              f'pair-win {100*sum(1 for q in d if q>0)/n:.1f}%')

    print('paired vs pm_trail:')
    paired('ri', 'pm', 'ride_it  ')
    paired('uh', 'pm', 'universal')
    paired('at', 'pm', 'atr_sl_tp')

    h1 = [x for x in recs if x['t'] < '2026-11-13']
    h2 = [x for x in recs if x['t'] >= '2026-11-13']
    print(f'time split (11-13) n={len(h1)}/{len(h2)}:')
    for name, k in (('pm', 'pm'), ('ride_it', 'ri'), ('universal', 'uh'), ('atr', 'at')):
        print(f'  {name:>10}: {statistics.mean(x[k] for x in h1):+.3f} / '
              f'{statistics.mean(x[k] for x in h2):+.3f}')

    comb = [(x['mfe'] * (1 - GIVE)) if (x['mfe'] is not None and x['mfe'] >= ARM)
            else (x['net'] + x['fee'] + x['slip']) for x in recs]
    d = [comb[i] - recs[i]['pm'] for i in range(len(recs))]
    print(f'mfe_exit sim (gross basis): mean={statistics.mean(comb):+.3f}pp '
          f'WR={100*sum(1 for q in comb if q>0)/len(comb):.1f}%  '
          f'paired vs pm={statistics.mean(d):+.3f}pp  '
          f'halves={statistics.mean(comb[:len(h1)]):+.3f}/'
          f'{statistics.mean(comb[len(h1):]):+.3f}')
    conn.close()

if __name__ == '__main__':
    main()
