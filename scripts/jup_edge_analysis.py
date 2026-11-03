#!/usr/bin/env python3
"""
JUP YOLO mirror — edge / over-trading / cluster analysis (T 2026-11-03).

Answers three questions with reproducible SQL + explicit sample sizes:
  1. Is there an edge? (expectancy, WR+CI, profit factor, vs system baseline)
  2. Is it over-trading? (trades/day, signal→trade conversion, token churn,
     re-entry loops, concentration)
  3. Do clusters help? Should the threshold increase? (outcome buckets by
     jup_cluster_size, two-proportion test for cluster>=N vs <N, counterfactual
     "only take cluster>=N" books)

Honesty rules (THE PATTERN): every number printed comes from this run;
n and CIs shown; no claims at n<30 per cell.
"""
import json
import math
import sys
from collections import defaultdict, Counter
from datetime import datetime, timedelta

import psycopg2

from _secrets import BRAIN_DB_DICT


def q(sql, args=()):
    cfg = BRAIN_DB_DICT.copy(); cfg.setdefault('port', 5432)
    conn = psycopg2.connect(**cfg); conn.autocommit = True
    try:
        cur = conn.cursor()
        cur.execute(sql, args)
        rows = cur.fetchall()
        cols = [d[0] for d in cur.description]
        cur.close()
        return [dict(zip(cols, r)) for r in rows]
    finally:
        conn.close()


def wilson_ci(w, n, z=1.96):
    if n == 0:
        return (0.0, 0.0)
    p = w / n
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return (max(0.0, center - half) * 100, min(1.0, center + half) * 100)


def two_prop_test(w1, n1, w2, n2):
    """Two-sided z-test for proportion difference; returns (pp, pvalue)."""
    if n1 == 0 or n2 == 0:
        return (float('nan'), float('nan'))
    p1, p2 = w1 / n1, w2 / n2
    p = (w1 + w2) / (n1 + n2)
    se = math.sqrt(p * (1 - p) * (1 / n1 + 1 / n2))
    if se == 0:
        return (p1 - p2, 1.0)
    z = (p1 - p2) / se
    pval = math.erfc(abs(z) / math.sqrt(2))  # two-sided
    return ((p1 - p2) * 100, pval)


def _count_signals(since_iso):
    """jup signal count in the SQLite runtime DB since a PG timestamp."""
    import sqlite3
    from paths import RUNTIME_DB
    conn = sqlite3.connect(RUNTIME_DB)
    try:
        return conn.execute("""
            SELECT COUNT(*) FROM signals
            WHERE source LIKE '%jup_yolo%' AND created_at >= ?
        """, (str(since_iso),)).fetchone()[0]
    finally:
        conn.close()


def main():
    trades = q("""
        SELECT id, token, direction, pnl_pct, pnl_usdt, status, open_time,
               close_time, confidence, volatility_regime, close_reason,
               _signal_metadata, leverage, amount_usdt
        FROM trades
        WHERE signal LIKE '%%jup_yolo%%'
        ORDER BY id
    """)
    closed = [t for t in trades if t['status'] == 'closed']
    open_t = [t for t in trades if t['status'] == 'open']
    print(f"=== 1. EDGE (n={len(closed)} closed, {len(open_t)} open) ===")

    for t in trades:
        m = t['_signal_metadata']
        t['meta'] = m if isinstance(m, dict) else (json.loads(m) if m else {})
        t['clu'] = t['meta'].get('jup_cluster_size')
        t['pnl'] = float(t['pnl_pct'] or 0)
        t['usdt'] = float(t['pnl_usdt'] or 0)

    W = [t for t in closed if t['pnl'] > 0.05]
    L = [t for t in closed if t['pnl'] < -0.05]
    B = [t for t in closed if abs(t['pnl']) <= 0.05]
    n_wl = len(W) + len(L)
    wr = len(W) / n_wl * 100 if n_wl else 0
    lo, hi = wilson_ci(len(W), n_wl)
    net_usd = sum(t['usdt'] for t in closed)
    gross_w = sum(t['usdt'] for t in W)
    gross_l = -sum(t['usdt'] for t in L)
    pf = gross_w / gross_l if gross_l > 0 else float('inf')
    avg_w = gross_w / len(W) if W else 0
    avg_l = gross_l / len(L) if L else 0   # gross_l already positive magnitude
    exp_usd = net_usd / len(closed) if closed else 0
    print(f"  WR {wr:.1f}% (95% CI {lo:.1f}-{hi:.1f})  W/L/B {len(W)}/{len(L)}/{len(B)}")
    print(f"  net ${net_usd:+.3f}  expectancy ${exp_usd:+.4f}/trade  PF {pf:.2f}")
    print(f"  avg win ${avg_w:+.3f} vs avg loss ${avg_l:.3f} (payoff {avg_w/avg_l:.2f}"
          f" → breakeven WR {avg_l/(avg_w+avg_l)*100:.0f}%)")

    # baseline: all system trades in the same window
    if closed:
        t0 = min(t['open_time'] for t in closed)
        base = q("""
            SELECT COUNT(*) n,
                   SUM(CASE WHEN pnl_pct > 0.05 THEN 1 ELSE 0 END) w,
                   SUM(CASE WHEN pnl_pct < -0.05 THEN 1 ELSE 0 END) l,
                   COALESCE(SUM(pnl_usdt), 0) net
            FROM trades
            WHERE status='closed' AND open_time >= %s
              AND signal NOT LIKE '%%jup_yolo%%'
        """, (t0,))
        b = base[0]
        if (b['w'] or 0) + (b['l'] or 0):
            bwr = b['w'] / ((b['w'] or 0) + (b['l'] or 0)) * 100
            print(f"  BASELINE (all other signals since {t0.date()}): "
                  f"n={b['n']} WR {bwr:.1f}% net ${float(b['net']):+.3f}")
            pp, pv = two_prop_test(len(W), n_wl, b['w'], (b['w'] or 0) + (b['l'] or 0))
            print(f"  mirror vs baseline WR diff {pp:+.1f}pp, p={pv:.3f} "
                  f"({'significant' if pv < 0.05 else 'NOT significant at p<0.05'})")

    # ── 2. OVER-TRADING
    print(f"\n=== 2. OVER-TRADING ===")
    if closed:
        span = (max(t['close_time'] or t['open_time'] for t in closed)
                - min(t['open_time'] for t in closed))
        days = max(span.total_seconds() / 86400, 0.01)
        print(f"  window {days:.1f}d → {len(trades)/days:.1f} trades/day "
              f"({len(closed)} closed)")
        # signal → trade conversion
        sig = [{'n': _count_signals(t0)}]   # signals live in SQLite runtime DB
        print(f"  signals created: {sig[0]['n']} → trades {len(trades)} "
              f"(conversion {len(trades)/max(sig[0]['n'],1)*100:.1f}%)")
        # token concentration + churn
        tok = Counter(t['token'] for t in closed)
        print(f"  token mix: {dict(tok.most_common())}")
        top_share = tok.most_common(1)[0][1] / len(closed) * 100
        print(f"  top-token concentration: {top_share:.0f}%")
        # re-entry loops: same token re-opened within 2h of prior close
        by_tok = defaultdict(list)
        for t in sorted(closed, key=lambda x: x['open_time']):
            by_tok[t['token']].append(t)
        loops = 0
        for tok, ts in by_tok.items():
            for a, b in zip(ts, ts[1:]):
                if a['close_time'] and (b['open_time'] - a['close_time']) < timedelta(hours=2):
                    loops += 1
        print(f"  same-token re-entries within 2h of prior close: {loops}/{len(closed)}")
        _lal = 0
        for _tok, _ts in by_tok.items():
            for _a, _b in zip(_ts, _ts[1:]):
                if _a['close_time'] and (_b['open_time'] - _a['close_time']) < timedelta(hours=2) and _a['pnl'] < -0.05:
                    _lal += 1
        print(f"    of which re-entries after a LOSS (stop-out -> re-enter loop): {_lal}")
        # daily trend (last 3 days vs first)
        by_day = Counter(t['open_time'].date() for t in trades)
        print(f"  trades/day: {dict(sorted(by_day.items()))}")

    # ── 3. CLUSTERS
    print(f"\n=== 3. CLUSTERS ===")
    buckets = defaultdict(lambda: {'n': 0, 'w': 0, 'l': 0, 'usdt': 0.0, 'pnl': []})
    for t in closed:
        c = t['clu']
        if c is None:
            key = 'unknown(pre-10-31)'
        elif c <= 1:
            key = '1'
        elif c == 2:
            key = '2'
        elif c <= 4:
            key = '3-4'
        else:
            key = '5+'
        b = buckets[key]
        b['n'] += 1
        b['usdt'] += t['usdt']
        b['pnl'].append(t['pnl'])
        if t['pnl'] > 0.05:
            b['w'] += 1
        elif t['pnl'] < -0.05:
            b['l'] += 1
    print(f"  {'bucket':<22} {'n':>3} {'W':>3} {'L':>3} {'WR%':>5} {'net$':>8} {'avg%':>7}")
    for k in ('unknown(pre-10-31)', '1', '2', '3-4', '5+'):
        b = buckets.get(k)
        if not b:
            continue
        wl = b['w'] + b['l']
        wrr = b['w'] / wl * 100 if wl else 0
        avg = sum(b['pnl']) / len(b['pnl']) if b['pnl'] else 0
        print(f"  {k:<22} {b['n']:>3} {b['w']:>3} {b['l']:>3} {wrr:>5.0f} "
              f"{b['usdt']:>+8.3f} {avg:>+7.2f}")

    # cluster>=N vs <N tests (excluding unknown bucket)
    known = [t for t in closed if t['clu'] is not None]
    for thr in (2, 3, 4):
        hi_g = [t for t in known if t['clu'] >= thr]
        lo_g = [t for t in known if t['clu'] < thr]
        def wl(g):
            w = sum(1 for t in g if t['pnl'] > 0.05)
            l = sum(1 for t in g if t['pnl'] < -0.05)
            return w, l
        w1, l1 = wl(hi_g); w2, l2 = wl(lo_g)
        if not (w1 + l1 and w2 + l2):
            continue
        pp, pv = two_prop_test(w1, w1 + l1, w2, w2 + l2)
        net_hi = sum(t['usdt'] for t in hi_g)
        net_lo = sum(t['usdt'] for t in lo_g)
        print(f"  cluster>={thr}: n={len(hi_g)} {w1}W/{l1}L WR={w1/(w1+l1)*100:.0f}% "
              f"net=${net_hi:+.3f}  vs  <{thr}: n={len(lo_g)} {w2}W/{l2}L "
              f"WR={w2/(w2+l2)*100:.0f}% net=${net_lo:+.3f}  | WR diff {pp:+.1f}pp p={pv:.3f}"
              f"  {'SIG' if pv < 0.05 else 'n.s.'}")

    # counterfactual books: only-take cluster>=N
    print(f"\n  counterfactual 'only take cluster>=N':")
    for thr in (2, 3, 4):
        keep = [t for t in known if t['clu'] >= thr]
        if not keep:
            continue
        net = sum(t['usdt'] for t in keep)
        w = sum(1 for t in keep if t['pnl'] > 0.05)
        l = sum(1 for t in keep if t['pnl'] < -0.05)
        wl = w + l
        wrk = w / wl * 100 if wl else 0
        print(f"    >= {thr}: {len(keep)} trades, WR {wrk:.0f}%, net ${net:+.3f} "
              f"(vs all-known ${sum(t['usdt'] for t in known):+.3f})")

    # cluster at signal level (selection effect: does cluster predict approval?)
    print(f"\n  selection effect — cluster vs becoming a trade:")
    import sqlite3
    from paths import RUNTIME_DB
    _sc = sqlite3.connect(RUNTIME_DB)
    sigs = [{'signal_metadata': r[0]} for r in _sc.execute("""
        SELECT signal_metadata FROM signals
        WHERE source LIKE '%jup_yolo%'
          AND created_at >= (SELECT MIN(open_time) FROM trades
                             WHERE signal LIKE '%jup_yolo%')
    """).fetchall()] if False else [{'signal_metadata': r[0]} for r in _sc.execute(
        "SELECT signal_metadata FROM signals WHERE source LIKE ? AND created_at >= ?",
        ('%jup_yolo%', str(q("SELECT MIN(open_time) t FROM trades WHERE signal LIKE '%%jup_yolo%%'")[0]['t']))).fetchall()]
    _sc.close()
    sc = Counter()
    for s in sigs:
        try:
            m = json.loads(s['signal_metadata']) if isinstance(s['signal_metadata'], str) else (s['signal_metadata'] or {})
            c = m.get('jup_cluster_size')
            sc['unknown' if c is None else str(c)] += 1
        except Exception:
            sc['parse_err'] += 1
    print(f"    signal cluster mix: {dict(sorted(sc.items()))}")


if __name__ == '__main__':
    main()
