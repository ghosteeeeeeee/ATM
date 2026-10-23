#!/usr/bin/env python3
"""tat_variant_c_pack_2026-10-23.py — TAT variant-C counterfactual, UNITS-CORRECT.

WHY (brain_auditor run #103, 2026-10-23):
The TAT variant-C pack queued for CEO GO reported net "+13.00pp" at #93 (6 cuts, Oct 23
08:49) and "+13.40pp" at #98 (7 cuts with POLYX open-time +0.40), with per-trade credits
like WLFI "+4.22pp". That per-trade number is exactly `live_pnl (-0.61) - trades.pnl_pct
(-4.83)` = 4.22 — an UNLEVERAGED poll snapshot subtracted from a LEVERAGED close figure.
The trail-arm-candle-oos verdict (2026-10-17) flagged this as the "units landmine": for the
leveraged class pnl_pct = price_move x leverage and pnl_usdt = notional x price_move.
Mixing the bases inflates every credit by ~leverage (~5x). Reproducer check: this script's
naive column on the #93 cohort (ex-POLYX) = +13.00pp EXACT; with POLYX closed = +14.08pp
(+13.00 + POLYX's own 1.09, vs the 0.40 the open-time snapshot showed).

This script computes BOTH:
  * naive_pp  = live_pnl_at_first_fire - trades.pnl_pct        (prior method, reproduces
                the published pack so the diagnosis is verifiable)
  * correct   = amount_usdt * live_pnl/100  vs  trades.pnl_usdt (money truth, cf$ =
                amount x unleveraged move, same basis as pnl_usdt)

Counterfactual: close at FIRST shadow fire (the minute TAT would actually have cut).
  BASE      = cut every in-scope fire
  VARIANT-C = cut only when live_pnl < 0   (the pre-registered variant)

In-scope mirrors position_manager.py:3760-3762 exactly: direction LONG AND
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


def evaluate(fires, rows, excluded=None):
    """rows: {trade_id: (status, pnl_usdt, pnl_pct, notional, leverage, signal, open_time)}

    notional = COALESCE(hl_notional_usdt, amount_usdt) — pnl_usdt is computed on
    hl_notional (pnl_utils.compute_close_pnl), so cf$ must use the same basis.
    excluded: optional list to record why a fired trade was dropped.
    """
    out = {'base': [], 'variant_c': [], 'naive_base': [], 'naive_c': []}
    excluded = excluded if excluded is not None else []
    for tid, (ts, token, direction, live, sig) in sorted(fires.items()):
        if not in_scope(direction, sig):
            excluded.append((tid, f'scope {direction} {sig}'))
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
        SELECT id, status, pnl_usdt, pnl_pct,
               COALESCE(hl_notional_usdt, amount_usdt) AS notional, leverage, signal,
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
    """Runs the REAL evaluate()/summarize()/_sign_p() on a fixture — bug_hunter MED-1
    (2026-10-23): a constant-only selfcheck survived a dropped /100, a sign inversion
    and a one-sided sign test. Break-test: any of those now fails an assert below."""
    fires = {
        101: ('2026-10-23 07:58:00', 'WLFI', 'LONG', -0.61, 'bb-bounce-v2-long+'),
        102: ('2026-10-18 04:28:00', 'BANANA', 'LONG', -0.17, 'bb-bounce-v2-long+'),
        103: ('2026-10-19 22:07:00', 'LTC', 'LONG', -0.25, 'bb-bounce-v2-long+'),
        104: ('2026-10-23 13:00:00', 'SAFE', 'LONG', 0.25, 'bb-bounce-v2-long+'),
        105: ('2026-10-23 13:05:00', 'MAN', 'LONG', -0.50, 'ai-trader-manual'),
    }
    rows = {
        101: ('closed', -0.11, -4.8306, 11.10, 5, 'bb-bounce-v2-long+', '2026-10-23 07:02'),
        102: ('closed', -0.09, -2.2400, 11.10, 5, 'bb-bounce-v2-long+', '2026-10-18 03:30'),
        103: ('closed', -0.04, -1.7200, 11.10, 5, 'bb-bounce-v2-long+', '2026-10-19 21:40'),
        104: ('closed', 0.05, 1.3500, 11.10, 5, 'bb-bounce-v2-long+', '2026-10-23 12:30'),
        105: ('closed', -0.10, -4.5000, 11.10, 5, 'ai-trader-manual', '2026-10-23 12:40'),
    }
    res, excluded = evaluate(fires, rows)
    base, varc = summarize(res['base']), summarize(res['variant_c'])

    # scope: manual dropped, live>0 kept only in BASE
    assert len(excluded) == 1 and excluded[0][0] == 105, f'scope drop broken: {excluded}'
    assert base['n_cuts'] == 4, f"base should cut all 4 in-scope, got {base['n_cuts']}"
    assert varc['n_cuts'] == 3, f"variant-C should cut the 3 live<0, got {varc['n_cuts']}"

    # units inside the real code path (the bug this script exists to catch)
    wlfi = [r for r in res['variant_c'] if r['tid'] == 101][0]
    assert abs(wlfi['naive_pp'] - 4.2206) < 0.01, f"naive reproducer broken: {wlfi['naive_pp']}"
    assert abs(wlfi['delta_usdt'] - 0.0423) < 0.005, f"correct delta broken: {wlfi['delta_usdt']}"
    assert wlfi['delta_usdt'] < wlfi['naive_pp'] / 10, 'correct must be ~5x smaller than naive'

    # summarize: net, fk, sign (fixture = 3 improving cuts, no winner among them)
    assert abs(varc['net_usdt'] - 0.126) < 0.005, f"variant net broken: {varc['net_usdt']}"
    assert varc['fk_winners_cut'] == 0 and varc['improved'] == 3 and varc['worsened'] == 0
    assert abs(varc['sign_p_two_sided'] - 0.25) < 1e-9, f"sign p(3/0) broken: {varc['sign_p_two_sided']}"
    # base includes the positive-live winner -> fk 1/4 and a worse net
    assert base['fk_winners_cut'] == 1, f"base fk broken: {base['fk_winners_cut']}"
    assert abs(base['net_usdt'] - 0.103) < 0.005, f"base net broken: {base['net_usdt']}"

    # two-sided sign test (one-sided would return half of these)
    assert abs(_sign_p(7, 0) - 0.015625) < 1e-9, f'_sign_p(7,0) broken: {_sign_p(7,0)}'
    assert abs(_sign_p(0, 4) - 0.125) < 1e-9, f'_sign_p(0,4) broken: {_sign_p(0,4)}'

    # parser round-trip on a real-format line + scope mirror
    line = ('2026-10-23 14:12:18   [SHADOW] TRAIL-ARM would-fire POLYX LONG -0.29% '
            '[162m < arm 0.40%] trade=16365 sig=bb-bounce-v2-long+\n')
    m = RE_FIRE.match(line)
    assert m and m.group(4) == '-0.29' and m.group(5) == '16365', 'regex broken'
    assert in_scope('LONG', 'bb-bounce-v2-long+') and not in_scope('LONG', 'ai-trader-manual')

    print('tat_variant_c_pack --selfcheck PASS '
          '(evaluate+summarize+sign on fixture: naive +4.22pp vs correct +$0.042, '
          'base 4 cuts fk1 / variant 3 cuts fk0 p=0.25, parser+scope ok)')
    return True


if __name__ == '__main__':
    if '--selfcheck' in sys.argv:
        _selfcheck()
    else:
        report(Path(sys.argv[sys.argv.index('--log') + 1]) if '--log' in sys.argv else LOG_DEFAULT)
