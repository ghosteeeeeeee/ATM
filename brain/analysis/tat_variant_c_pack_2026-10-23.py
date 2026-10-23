#!/usr/bin/env python3
"""tat_variant_c_pack_2026-10-23.py — TAT variant-C counterfactual, UNITS-CORRECT.

WHY (brain_auditor run #103, 2026-10-23):
The TAT variant-C pack queued for CEO GO (#93/#98) reported net "+13.40pp" and per-trade
credits like WLFI "+4.22pp". That per-trade number is exactly `live_pnl (-0.61) -
trades.pnl_pct (-4.83)` = 4.22 — i.e. an UNLEVERAGED poll snapshot subtracted from a
LEVERAGED close figure. The trail-arm-candle-oos verdict (2026-10-17) flagged this as the
"units landmine": pnl_pct = unleveraged_move x leverage, pnl_usdt = amount_usdt x
unleveraged_move. Mixing them inflates every credit by ~leverage (~5x).

This script computes BOTH:
  * naive_pp  = live_pnl_at_first_fire - trades.pnl_pct        (prior method, reproduces
                the published pack so the diagnosis is verifiable)
  * correct   = amount_usdt * live_pnl/100  vs  trades.pnl_usdt (money truth, cf$ =
                amount x unleveraged move, same basis as pnl_usdt)

Counterfactual: close at FIRST shadow fire (the minute TAT would actually have cut).
  BASE      = cut every in-scope fire
  VARIANT-C = cut only when live_pnl < 0   (the pre-registered variant)

In-scope mirrors position_manager.py:3763 exactly: direction LONG AND
('bb-bounce' in sig or 'ai-trader+' in sig) — manual/pending never match that substring
(#39 fix); scope flag BB_BOUNCE_TRAIL_ARM_TIMEOUT_SHADOW must be on (it is).

Usage:
    python3 brain/analysis/tat_variant_c_pack_2026-10-23.py [--log PATH]
    python3 brain/analysis/tat_variant_c_pack_2026-10-23.py --selfcheck
"""

import re
import sys
from datetime import datetime
from pathlib import Path

LOG_DEFAULT = Path('/root/.hermes/logs/pipeline.log')

RE_FIRE = re.compile(
    r'^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}).*?\[SHADOW\] TRAIL-ARM would-fire '
    r'(\S+) (\S+) ([+-]\d+\.\d+)% \[.*?\] trade=(\d+) sig=(\S+)')


def parse_first_fires(path=LOG_DEFAULT, since='2026-10-16'):
    """First fire minute per trade_id (shadow logs every pipeline minute, dedup = min ts)."""
    fires = {}
    for raw in open(path, errors='replace'):
        m = RE_FIRE.match(raw)
        if not m:
            continue
        ts, token, direction, live, tid, sig = m.groups()
        if ts < since:
            continue
        rec = (ts, token, direction.upper(), float(live), sig)
        if int(tid) not in fires or ts < fires[int(tid)][0]:
            fires[int(tid)] = rec
    return fires


def in_scope(direction, sig):
    s = (sig or '').lower()
    return direction == 'LONG' and ('bb-bounce' in s or 'ai-trader+' in s)


def evaluate(fires, rows):
    """rows: {trade_id: (status, pnl_usdt, pnl_pct, amount, leverage, signal, open_time)}

    Returns (base, variant_c) dicts of UNITS-CORRECT numbers plus naive reproducer.
    """
    out = {'base': [], 'variant_c': [], 'naive_base': [], 'naive_c': []}
    excluded = []
    for tid, (ts, token, direction, live, sig) in sorted(fires.items()):
        if not in_scope(direction, sig):
            continue
        row = rows.get(tid)
        if row is None:
            excluded.append((tid, 'no row'))
            continue
        status, pnl_usdt, pnl_pct, amount, lev, db_sig, open_time = row
        if status != 'closed':
            excluded.append((tid, f'status={status}'))
            continue
        amount = float(amount or 0)
        pnl_usdt = float(pnl_usdt or 0)
        pnl_pct = float(pnl_pct or 0)
        cf_usdt = amount * live / 100.0
        correct_delta = cf_usdt - pnl_usdt
        naive_delta = live - pnl_pct
        rec = {
            'tid': tid, 'token': token, 'sig': db_sig or sig, 'open': open_time,
            'fire_ts': ts, 'live': live, 'pnl_usdt': pnl_usdt, 'pnl_pct': pnl_pct,
            'amount': amount, 'lev': lev,
            'cf_usdt': cf_usdt, 'delta_usdt': correct_delta,
            'delta_pp': (correct_delta / amount * 100.0) if amount else 0.0,
            'naive_pp': naive_delta,
            'was_winner': pnl_usdt > 0,
        }
        out['base'].append(rec)
        out['naive_base'].append(rec)
        if live < 0:
            out['variant_c'].append(rec)
            out['naive_c'].append(rec)
    return out, excluded


def summarize(cuts):
    net_usdt = sum(r['delta_usdt'] for r in cuts)
    net_pp = sum(r['delta_pp'] for r in cuts)
    net_naive = sum(r['naive_pp'] for r in cuts)
    fk = sum(1 for r in cuts if r['was_winner'])
    pos = sum(1 for r in cuts if r['delta_usdt'] > 0)
    neg = sum(1 for r in cuts if r['delta_usdt'] < 0)
    return {
        'n_cuts': len(cuts),
        'net_usdt': round(net_usdt, 3),
        'net_pp': round(net_pp, 2),
        'net_naive_pp': round(net_naive, 2),
        'fk_winners_cut': fk,
        'fk_pct': round(100.0 * fk / len(cuts), 1) if cuts else 0.0,
        'improved': pos, 'worsened': neg,
        'sign_p_two_sided': _sign_p(pos, neg),
    }


def _sign_p(pos, neg):
    n = pos + neg
    if n == 0:
        return 1.0
    k = min(pos, neg)
    from math import comb
    tail = sum(comb(n, i) for i in range(0, k + 1))
    return min(1.0, 2.0 * tail / (2 ** n))


def report(path=LOG_DEFAULT):
    fires = parse_first_fires(path)
    import psycopg2
    conn = psycopg2.connect(host='/var/run/postgresql', database='brain', user='postgres')
    cur = conn.cursor()
    cur.execute("""
        SELECT id, status, pnl_usdt, pnl_pct, amount_usdt, leverage, signal,
               to_char(open_time, 'YYYY-MM-DD HH24:MI')
        FROM trades WHERE id = ANY(%s)""", (list(fires.keys()),))
    rows = {r[0]: (r[1], r[2], r[3], r[4], r[5], r[6], r[7]) for r in cur.fetchall()}
    conn.close()

    res, excluded = evaluate(fires, rows)
    base = summarize(res['base'])
    varc = summarize(res['variant_c'])

    print(f"TAT VARIANT-C PACK (units-correct rebuild) — log {path}")
    print(f"  shadow trades parsed: {len(fires)}  in-scope closed: {len(res['base'])}  excluded: {excluded}")
    print(f"  BASE     n={base['n_cuts']} cuts  net ${base['net_usdt']:+.3f} "
          f"({base['net_pp']:+.2f} unleveraged pp)  naive-prior {base['net_naive_pp']:+.2f}pp  "
          f"fk {base['fk_winners_cut']}/{base['n_cuts']}={base['fk_pct']}%  "
          f"sign {base['improved']}+/{base['worsened']}- p={base['sign_p_two_sided']:.3f}")
    print(f"  VARIANT-C n={varc['n_cuts']} cuts  net ${varc['net_usdt']:+.3f} "
          f"({varc['net_pp']:+.2f} unleveraged pp)  naive-prior {varc['net_naive_pp']:+.2f}pp  "
          f"fk {varc['fk_winners_cut']}/{varc['n_cuts']}={varc['fk_pct']}%  "
          f"sign {varc['improved']}+/{varc['worsened']}- p={varc['sign_p_two_sided']:.3f}")

    # split halves on open date (pre-registered in #93: Oct17-19 / Oct20-23)
    for name, lo, hi in (('Oct17-19', '2026-10-17', '2026-10-20'),
                         ('Oct20-23', '2026-10-20', '2026-10-24')):
        half = [r for r in res['variant_c'] if r['open'] and lo <= r['open'][:10] < hi]
        s = summarize(half)
        print(f"  VARIANT-C {name}: n={s['n_cuts']} net ${s['net_usdt']:+.3f} "
              f"({s['net_pp']:+.2f}pp) naive {s['net_naive_pp']:+.2f}pp fk {s['fk_winners_cut']}")

    print("  per-cut detail (variant-C):")
    for r in sorted(res['variant_c'], key=lambda x: -x['delta_usdt']):
        print(f"    #{r['tid']} {r['token']:6} {r['sig'][:26]:26} fire {r['fire_ts'][5:16]} "
              f"live {r['live']:+.2f}%  actual {r['pnl_pct']:+.2f}%lev / ${r['pnl_usdt']:+.3f} "
              f"-> cf ${r['cf_usdt']:+.3f}  delta ${r['delta_usdt']:+.3f} ({r['delta_pp']:+.2f}pp) "
              f"naive {r['naive_pp']:+.2f}pp")
    return res, base, varc


def _selfcheck():
    # 1) units discrimination on the published WLFI credit (#93/#98 '+4.22pp')
    amount, live, pnl_pct, pnl_usdt, lev = 11.10, -0.61, -4.8306, -0.11, 5
    cf = amount * live / 100.0
    naive = live - pnl_pct
    correct = cf - pnl_usdt
    assert abs(naive - 4.2206) < 0.01, f'naive reproducer broken: {naive}'
    assert abs(correct - 0.0423) < 0.005, f'correct delta broken: {correct}'
    assert correct < naive / 10, 'correct must be ~5x smaller (leverage inflation)'
    # 2) leveraged-consistency: pnl_pct/lev must equal pnl_usdt/amount
    assert abs(pnl_pct / lev - pnl_usdt / amount * 100) < 0.15, 'units model wrong'
    # 3) variant-C never cuts a winner at fire time by construction (live<0)
    rec = {'pnl_usdt': 0.05, 'live': -0.1}
    assert (rec['live'] < 0) and rec['pnl_usdt'] > 0  # fk possible only via recovery after fire
    # 4) parser round-trip on a real-format line
    line = ('2026-10-23 14:12:18   [SHADOW] TRAIL-ARM would-fire POLYX LONG -0.29% '
            '[162m < arm 0.40%] trade=16365 sig=bb-bounce-v2-long+\n')
    m = RE_FIRE.match(line)
    assert m and m.group(4) == '-0.29' and m.group(5) == '16365', 'regex broken'
    assert in_scope('LONG', 'bb-bounce-v2-long+') and not in_scope('LONG', 'ai-trader-manual')
    print('tat_variant_c_pack --selfcheck PASS '
          f'(naive {naive:+.2f}pp vs correct {correct:+.3f}pp, parser+scope ok)')
    return True


if __name__ == '__main__':
    if '--selfcheck' in sys.argv:
        _selfcheck()
    else:
        report(Path(sys.argv[sys.argv.index('--log') + 1]) if '--log' in sys.argv else LOG_DEFAULT)
