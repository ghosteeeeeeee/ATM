#!/usr/bin/env python3
"""Contributor sensitivity + by-signal split for the ARMED-TRAIL-DISTANCE sweep (#17 leg 2).

House bar (escalation #17 pre-req): a result must survive top-3-contributor removal.
Self-check: python3 brain/analysis/trail_distance_probe_2026-10-25.py --selfcheck
"""
import sys, sqlite3, datetime as dt, argparse, importlib.util
import psycopg2

SPEC = importlib.util.spec_from_file_location(
    'tdo', '/root/.hermes/brain/analysis/trail_distance_oos_2026-10-25.py')
tdo = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(tdo)


def collect(days, dist, scoped=True):
    """Per-trade deltas at a single distance. Returns list of dicts."""
    pg = psycopg2.connect(host='/var/run/postgresql', database='brain', user='postgres')
    candles = sqlite3.connect('/root/.hermes/data/candles.db')
    rows = []
    try:
        cur = pg.cursor()
        all_tr = tdo.load_trades(cur, days)
        cur.close()
        cutoff = dt.datetime.now(dt.UTC).replace(tzinfo=None) - dt.timedelta(days=days)
        for (tid, token, direction, amt, entry, exitp, pnl, exitr, ot, ct, sig, vol, arm, mfe) in all_tr:
            if ct <= cutoff:
                continue
            if scoped and ((vol or '') == 'EXTREME' or 'volume-' in (sig or '').lower()):
                continue
            pnl = float(pnl)
            armed, ats, res = tdo._replay(candles, token, ot, ct, entry, direction, arm, (dist,))
            if not armed:
                continue
            ex = res.get(dist)
            if ex is None:
                continue
            cf = tdo.pnl_from(amt, entry, ex, direction)
            rows.append(dict(tid=tid, sig=sig, token=token, pnl=pnl, cf=cf,
                             delta=cf - pnl, ct=ct, ot=ot, exitr=exitr))
    finally:
        pg.close()
        candles.close()
    return rows


def summarize(rows, armed_winners, label):
    net = sum(r['delta'] for r in rows)
    print(f"  {label}: fills={len(rows)} net={net:+.3f}")
    return net


def selfcheck():
    # synthetic: three trades, deltas +1/-0.5/+0.25 -> top-2 contributors are +1 and +0.25
    rows = [dict(delta=1.0, tid=1), dict(delta=-0.5, tid=2), dict(delta=0.25, tid=3)]
    net = sum(r['delta'] for r in rows)
    top = sorted(rows, key=lambda r: -abs(r['delta']))[:3]
    rest = [r for r in rows if r not in top]
    assert abs(net - 0.75) < 1e-9
    assert [r['tid'] for r in top] == [1, 2, 3]
    assert abs(sum(r['delta'] for r in rest) - 0.0) < 1e-9
    print('probe selfcheck PASS: delta sum + top-|delta| ordering + remainder')
    # live probe: pnl_from must reproduce stored pnl on the real cohort
    pg = psycopg2.connect(host='/var/run/postgresql', database='brain', user='postgres')
    cur = pg.cursor()
    cur.execute("""SELECT amount_usdt, entry_price, exit_price, direction, pnl_usdt FROM trades
                   WHERE status='closed' AND pnl_usdt IS NOT NULL AND entry_price IS NOT NULL
                   AND exit_price IS NOT NULL ORDER BY close_time DESC LIMIT 40""")
    errs = []
    for amt, e, x, d, p in cur.fetchall():
        errs.append(abs(tdo.pnl_from(float(amt), float(e), float(x), d) - float(p)))
    pg.close()
    med = sorted(errs)[len(errs) // 2]
    assert med < 0.005, med
    print(f'probe live-units PASS: median_err {med:.4f}')


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--selfcheck', action='store_true')
    ap.add_argument('--dist', type=float, default=0.20, help='trail distance in %%')
    ap.add_argument('--days', type=int, default=30)
    a = ap.parse_args()
    if a.selfcheck:
        selfcheck()
        sys.exit(0)
    d = a.dist / 100.0
    rows = collect(a.days, d)
    rows.sort(key=lambda r: r['ct'])
    mid = rows[len(rows) // 2]['ct'] if rows else None
    armed_w = len([1 for r in rows if r['pnl'] > 0])  # lower bound; main script has the exact count
    net = sum(r['delta'] for r in rows)
    print(f"=== D={a.dist}% {a.days}d scoped: fills={len(rows)} NET {net:+.3f}")
    print(f"  halves: old {sum(r['delta'] for r in rows if r['ct'] <= mid):+.3f} "
          f"new {sum(r['delta'] for r in rows if r['ct'] > mid):+.3f}")
    # top-3 contributor sensitivity
    top3 = sorted(rows, key=lambda r: -abs(r['delta']))[:3]
    rest = [r for r in rows if r not in top3]
    print(f"  top3 contributors: {[(r['tid'], r['sig'], r['token'], round(r['delta'],3)) for r in top3]}")
    print(f"  net EX-top3: {sum(r['delta'] for r in rest):+.3f}  "
          f"({'PASS' if sum(r['delta'] for r in rest) > 0 else 'FAIL'})")
    # by ACTUAL exit engine — is the edge PM's own tier ladder, or the bypass engines?
    byexit = {}
    for r in rows:
        b = byexit.setdefault(r['exitr'], [0, 0.0])
        b[0] += 1
        b[1] += r['delta']
    print("  by ACTUAL exit engine:")
    for s2, (n, v) in sorted(byexit.items(), key=lambda kv: -kv[1][1]):
        print(f"    {str(s2):34s} n={n:3d} net={v:+.3f}")
    # by signal
    bysig = {}
    for r in rows:
        b = bysig.setdefault(r['sig'], [0, 0.0])
        b[0] += 1
        b[1] += r['delta']
    print("  by signal:")
    for s, (n, v) in sorted(bysig.items(), key=lambda kv: -kv[1][1]):
        print(f"    {str(s):34s} n={n:3d} net={v:+.3f}")
    # by exit-reason class of the ACTUAL trade is in the main script; here: losers vs winners
    print(f"  actual losers touched: {len([r for r in rows if r['pnl']<0])} "
          f"net {sum(r['delta'] for r in rows if r['pnl']<0):+.3f} | "
          f"actual winners touched: {len([r for r in rows if r['pnl']>0])} "
          f"net {sum(r['delta'] for r in rows if r['pnl']>0):+.3f}")
