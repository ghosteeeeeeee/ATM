#!/usr/bin/env python3
"""gate_attr.py — per-gate attribution of the SHORT-block +$290-eq aggregate.

READ-ONLY against brain/gate_shadow.db and data/candles.db (SELECT only).
Forward-return engine copied line-for-line from scripts/expiry_shadow.py
`_fwd_metrics` (and analysis/shadow_redundancy_deepdive_v2_2026-10-30.py
`fwd_metrics`, which produced the registered aggregate):
  entry candle  = first CLOSED 5m candle with ts >= event blocked_at
  fwd_4h        = sgn * (close[i+48] / open[i] - 1) * 100,  sgn=+1 LONG, -1 SHORT
  => fwd_4h is already expressed in the BLOCKED DIRECTION's sign.
"""
import os
import sys
import math
import json
import sqlite3
from datetime import datetime, timezone
from collections import defaultdict

HERMES = '/root/.hermes'
sys.path.insert(0, os.path.join(HERMES, 'brain', 'analysis'))
from cluster_t import cluster_t, naive_t  # noqa: E402

GATE_DB = os.path.join(HERMES, 'brain', 'gate_shadow.db')
CANDLES = os.path.join(HERMES, 'data', 'candles.db')
NOTIONAL = float(sys.argv[1]) if len(sys.argv) > 1 else 13.41  # PG last-30d avg amount_usdt
OUT = '/tmp/gate_attr_2026-10-31'

ANCHORS = {'t0': 0, 't10': 600, 't30': 1800}   # seconds after blocked_at
H4 = 48                                          # 48 x 5m = 4h
H1 = 12

# ── candles ─────────────────────────────────────────────────────────────────
_C = {}


def candles(tok):
    if tok in _C:
        return _C[tok]
    conn = sqlite3.connect(CANDLES, timeout=10)
    try:
        rows = conn.execute(
            "SELECT ts, open, close FROM candles_5m WHERE token=? AND is_closed=1"
            " ORDER BY ts", (tok,)).fetchall()
    finally:
        conn.close()
    _C[tok] = rows
    return rows


def _idx(rows, t):
    lo, hi = 0, len(rows)
    while lo < hi:
        mid = (lo + hi) // 2
        if rows[mid][0] < t:
            lo = mid + 1
        else:
            hi = mid
    return lo


def fwd(rows, entry_ts, direction, offset, horizon):
    i = _idx(rows, entry_ts + offset)
    if i + horizon >= len(rows):
        return None
    o = rows[i][1]
    if not o:
        return None
    sgn = 1.0 if direction == 'LONG' else -1.0
    return sgn * (rows[i + horizon][2] / o - 1.0) * 100.0


def tstr(v):
    return 'n/a' if v is None else f'{v:+.2f}'


def stat_block(vals):
    n = len(vals)
    if n < 2:
        return dict(n=n, mean=(vals[0] if vals else None), t=None)
    m = sum(vals) / n
    return dict(n=n, mean=m, t=naive_t(vals))


def main():
    conn = sqlite3.connect(GATE_DB)
    ev = conn.execute("SELECT id, gate, token, direction, blocked_at FROM events"
                      " ORDER BY blocked_at").fetchall()
    conn.close()
    print(f'events in corpus: {len(ev)}')

    recs = []
    nocand = defaultdict(int)
    nofwd = defaultdict(int)
    for eid, gate, tok, d, bat in ev:
        d = (d or '').upper()
        tok = (tok or '').upper()
        try:
            ts = datetime.fromisoformat(bat).timestamp()
        except (ValueError, TypeError):
            continue
        rows = candles(tok)
        if not rows:
            nocand[tok] += 1
            continue
        r = {'id': eid, 'gate': gate, 'tok': tok, 'dir': d,
             'day': datetime.fromtimestamp(ts, timezone.utc).strftime('%Y-%m-%d'),
             'ts': ts}
        ok = True
        for an, off in ANCHORS.items():
            v = fwd(rows, ts, d, off, H4)
            r[an] = v
            if v is None:
                ok = False
        r['t0h1'] = fwd(rows, ts, d, 0, H1)
        if not ok:
            nofwd[tok] += 1
            continue
        recs.append(r)

    print(f'events with full fwd4h coverage @ t0/t+10m/t+30m: {len(recs)}'
          f' ({len(recs)/len(ev)*100:.1f}%)')
    print(f'no candles for token: {sum(nocand.values())} events, tokens={dict(nocand)}')
    print(f'insufficient forward window: {sum(nofwd.values())} events, tokens={dict(nofwd)}')

    # ── dedupe: one event per gate+token+direction+UTC-day (earliest block) ──
    seen = set()
    ded = []
    for r in recs:
        k = (r['gate'], r['tok'], r['dir'], r['day'])
        if k in seen:
            continue
        seen.add(k)
        ded.append(r)
    print(f'deduped (gate|token|direction|UTC-day, keep earliest): {len(ded)}')

    def agg(rows):
        v0 = [r['t0'] for r in rows]
        out = stat_block(v0)
        out['sum'] = sum(v0)
        out['eq'] = sum(v0) * NOTIONAL / 100.0
        out['pos'] = sum(1 for v in v0 if v > 0)
        out['tok_t'] = out['day_t'] = None
        if len(v0) >= 4 and len({r['tok'] for r in rows}) >= 3:
            try:
                out['tok_t'] = cluster_t(v0, [r['tok'] for r in rows])[0]
            except ValueError:
                pass
        if len(v0) >= 4 and len({r['day'] for r in rows}) >= 3:
            try:
                out['day_t'] = cluster_t(v0, [r['day'] for r in rows])[0]
            except ValueError:
                pass
        for an in ('t10', 't30'):
            vv = [r[an] for r in rows]
            out[an] = sum(vv) / len(vv) if vv else None
        vh = [r['t0h1'] for r in rows if r['t0h1'] is not None]
        out['h1'] = sum(vh) / len(vh) if vh else None
        # day split + LOO
        byday = defaultdict(list)
        for r in rows:
            byday[r['day']].append(r['t0'])
        daymeans = {k: sum(v) / len(v) for k, v in byday.items()}
        out['n_days'] = len(daymeans)
        out['pos_days'] = sum(1 for v in daymeans.values() if v > 0)
        loo = []
        for dk in daymeans:
            rest = [v for r in rows if r['day'] != dk for v in [r['t0']]]
            if rest:
                loo.append(sum(rest) / len(rest))
        out['loo_min'] = min(loo) if loo else None
        out['loo_neg_days'] = sum(1 for v in loo if v <= 0)
        return out

    # ── aggregate reproduction (same basis as the registered capstone numbers) ─
    print('\n===== AGGREGATE (raw event basis, fwd4h in blocked direction) =====')
    for dirn in ('SHORT', 'LONG'):
        rows = [r for r in recs if r['dir'] == dirn]
        a = agg(rows)
        print(f'{dirn:6} n_raw={a["n"]:6d} mean={a["mean"]:+.4f}% t_naive={tstr(a["t"])} '
              f't_tokCR={tstr(a["tok_t"])} t_dayCR={tstr(a["day_t"])} '
              f'sum={a["sum"]:+.1f} $-eq={a["eq"]:+.2f}')
    print('===== AGGREGATE (deduped gate|token|dir|day basis) =====')
    for dirn in ('SHORT', 'LONG'):
        rows = [r for r in ded if r['dir'] == dirn]
        a = agg(rows)
        print(f'{dirn:6} n_ded={a["n"]:6d} mean={a["mean"]:+.4f}% t_naive={tstr(a["t"])} '
              f't_tokCR={tstr(a["tok_t"])} t_dayCR={tstr(a["day_t"])} '
              f'sum={a["sum"]:+.1f} $-eq={a["eq"]:+.2f}')

    # ── per-gate ────────────────────────────────────────────────────────────
    gates = sorted({r['gate'] for r in recs})
    res = {}
    for g in gates:
        rraw = [r for r in recs if r['gate'] == g]
        rd = [r for r in ded if r['gate'] == g]
        res[g] = {'SHORT': agg([r for r in rraw if r['dir'] == 'SHORT']),
                  'LONG': agg([r for r in rraw if r['dir'] == 'LONG']),
                  'SHORT_ded': agg([r for r in rd if r['dir'] == 'SHORT']),
                  'LONG_ded': agg([r for r in rd if r['dir'] == 'LONG'])}

    with open(os.path.join(OUT, 'gate_attr_results.json'), 'w') as f:
        json.dump({'notional': NOTIONAL, 'n_events': len(ev),
                   'n_fwd': len(recs), 'n_ded': len(ded), 'gates': res}, f, indent=1)

    hdr = (f'{"gate":26} {"dir":5} {"nraw":>6} {"nded":>5} {"meanDed%":>9} {"tDed":>6} '
           f'{"tTok":>6} {"tDay":>6} {"$eqRaw":>9} {"$eqDed":>8} {"posD":>6} '
           f'{"t10%":>7} {"t30%":>7} {"LOOmin":>7} {"LOOneg":>6}')
    print('\n===== PER-GATE =====')
    print(hdr)
    print('-' * len(hdr))
    rows_out = []
    for g in gates:
        for dirn in ('SHORT', 'LONG'):
            a, ad = res[g][dirn], res[g][dirn + '_ded']
            if a['n'] == 0:
                continue
            line = (f'{g:26} {dirn:5} {a["n"]:6d} {ad["n"]:5d} '
                    f'{ad["mean"] if ad["mean"] is not None else float("nan"):+9.4f} '
                    f'{tstr(ad["t"]):>6} {tstr(ad["tok_t"]):>6} {tstr(ad["day_t"]):>6} '
                    f'{a["eq"]:+9.2f} {ad["eq"]:+8.2f} '
                    f'{ad["pos_days"]}/{ad["n_days"]:<4} '
                    f'{(ad["t10"] if ad["t10"] is not None else float("nan")):+7.3f} '
                    f'{(ad["t30"] if ad["t30"] is not None else float("nan")):+7.3f} '
                    f'{(ad["loo_min"] if ad["loo_min"] is not None else float("nan")):+7.3f} '
                    f'{ad["loo_neg_days"]:6d}')
            print(line)
            rows_out.append((g, dirn, a, ad))

    # ── attribution: does the per-gate sum explain the aggregate? ──────────
    print('\n===== ATTRIBUTION (SHORT, raw-event $-eq basis) =====')
    sr = sorted([(g, res[g]['SHORT']['eq'], res[g]['SHORT']['n'])
                 for g in gates if res[g]['SHORT']['n']], key=lambda x: -x[1])
    tot = sum(e for _, e, _ in sr)
    cum = 0.0
    for g, e, n in sr[:15]:
        cum += e
        print(f'  {g:26} n={n:6d} $-eq={e:+9.2f}  share={e/tot*100 if tot else 0:+6.1f}%'
              f'  cum={cum:+9.2f}')
    print(f'  {"SUM all SHORT gates":26}        $-eq={tot:+9.2f}')

    print('\n===== TOP-3 by $-eq: full LOO day profile =====')
    for g, e, n in sr[:3]:
        rows = [r for r in ded if r['gate'] == g and r['dir'] == 'SHORT']
        byday = defaultdict(list)
        for r in rows:
            byday[r['day']].append(r['t0'])
        print(f'  {g}: {len(byday)} days')
        for dk in sorted(byday):
            v = byday[dk]
            rest = [x for d2, vv in byday.items() if d2 != dk for x in vv]
            loo_m = sum(rest) / len(rest) if rest else float('nan')
            print(f'     {dk} n={len(v):4d} daymean={sum(v)/len(v):+7.3f}% '
                  f'LOO_mean={loo_m:+7.3f}%')


if __name__ == '__main__':
    main()
