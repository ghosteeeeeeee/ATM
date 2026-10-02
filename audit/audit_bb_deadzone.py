#!/usr/bin/env python3
"""Independent audit: SHORT-BB-DEAD-ZONE filter verification.

Verifies previous analysis claims about SHORT trades binned by entry_bb_position.
All numbers computed fresh from PostgreSQL brain.trades. No memory, no estimates.
"""
import json
import sys
from collections import defaultdict

import numpy as np
import psycopg2
from scipy import stats

CONN = dict(host='/var/run/postgresql', dbname='brain', user='postgres')
REF = "2026-10-02 15:37:43.850009"  # max(close_time) among SHORT w/ bb


def q(sql, params=None):
    conn = psycopg2.connect(**CONN)
    try:
        cur = conn.cursor()
        cur.execute(sql, params)
        cols = [d[0] for d in cur.description]
        rows = cur.fetchall()
        return [dict(zip(cols, r)) for r in rows]
    finally:
        conn.close()


def load():
    rows = q("""
        SELECT id, token, signal, entry_bb_position::float8 AS bb,
               COALESCE(pnl_usdt,0)::float8 AS pnl_usdt,
               COALESCE(pnl_pct,0)::float8 AS pnl_pct,
               COALESCE(amount_usdt,0)::float8 AS amount,
               close_time, open_time, paper, sl_group, experiment,
               volatility_regime, entry_regime_4h, entry_trend,
               exit_reason, leverage,
               (_signal_metadata->>'bb_position')::float8 AS meta_bb
        FROM trades
        WHERE direction='SHORT' AND status='closed' AND entry_bb_position IS NOT NULL
        ORDER BY close_time
    """)
    return rows


def band_of(bb):
    if bb < 0.20: return '1_<0.20'
    if bb < 0.35: return '2_0.20-0.35'
    if bb < 0.50: return '3_0.35-0.50'
    if bb < 0.55: return '3b_0.50-0.55'
    if bb < 0.70: return '4_0.55-0.70'
    if bb < 0.85: return '5_DEAD_0.70-0.85'
    if bb < 0.95: return '6a_0.85-0.95'
    if bb <= 1.00: return '6b_0.95-1.00'
    return '6c_>1.00'


def wr(trades):
    if not trades: return float('nan')
    return 100.0 * sum(1 for t in trades if t['pnl_usdt'] > 0) / len(trades)


def sum_pnl(trades):
    return sum(t['pnl_usdt'] for t in trades)


def mean_pnl(trades):
    return np.mean([t['pnl_usdt'] for t in trades]) if trades else float('nan')


def two_prop_ztest(x1, n1, x2, n2):
    """Two-sided two-proportion z-test. Returns (z, p)."""
    if n1 == 0 or n2 == 0:
        return float('nan'), float('nan')
    p1, p2 = x1 / n1, x2 / n2
    p = (x1 + x2) / (n1 + n2)
    se = np.sqrt(p * (1 - p) * (1 / n1 + 1 / n2))
    if se == 0:
        return 0.0, 1.0
    z = (p1 - p2) / se
    return z, 2 * (1 - stats.norm.cdf(abs(z)))


def perm_test_pnl(a, b, n_iter=20000, seed=42):
    """Permutation test: is mean pnl of group A different from group B?"""
    rng = np.random.default_rng(seed)
    a = np.array([t['pnl_usdt'] for t in a], dtype=float)
    b = np.array([t['pnl_usdt'] for t in b], dtype=float)
    if len(a) == 0 or len(b) == 0:
        return float('nan'), float('nan'), (float('nan'),) * 2
    obs = a.mean() - b.mean()
    pooled = np.concatenate([a, b])
    n_a = len(a)
    exceed = 0
    for _ in range(n_iter):
        rng.shuffle(pooled)
        d = pooled[:n_a].mean() - pooled[n_a:].mean()
        if abs(d) >= abs(obs):
            exceed += 1
    p = (exceed + 1) / (n_iter + 1)
    # bootstrap CI on difference
    bs = []
    for _ in range(5000):
        bs.append(rng.choice(a, len(a), replace=True).mean()
                  - rng.choice(b, len(b), replace=True).mean())
    ci = (np.percentile(bs, 2.5), np.percentile(bs, 97.5))
    return obs, p, ci


def bootstrap_mean_ci(trades, n_iter=5000, seed=7):
    rng = np.random.default_rng(seed)
    arr = np.array([t['pnl_usdt'] for t in trades], dtype=float)
    if len(arr) == 0:
        return (float('nan'),) * 2
    bs = [rng.choice(arr, len(arr), replace=True).mean() for _ in range(n_iter)]
    return (np.percentile(bs, 2.5), np.percentile(bs, 97.5))


def window(rows, days):
    if days is None:
        return rows
    from datetime import datetime, timedelta
    ref = datetime(2026, 10, 2, 15, 37, 43)
    cut = ref - timedelta(days=days)
    return [r for r in rows if r['close_time'] and r['close_time'] >= cut]


def band_table(rows, title):
    print(f"\n{'='*100}\nBAND TABLE — {title} (n={len(rows)})\n{'='*100}")
    hdr = f"{'band':<20}{'n':>6}{'WR%':>8}{'sumPnL$':>10}{'avgPnL$':>10}{'avgPnL%':>10}{'sumPnL%':>10}{'avgAmt':>9}{'CI95 meanPnL':>26}"
    print(hdr)
    print('-' * len(hdr))
    bands = defaultdict(list)
    for r in rows:
        bands[band_of(r['bb'])].append(r)
    order = ['1_<0.20', '2_0.20-0.35', '3_0.35-0.50', '3b_0.50-0.55',
             '4_0.55-0.70', '5_DEAD_0.70-0.85', '6a_0.85-0.95', '6b_0.95-1.00', '6c_>1.00']
    for b in order:
        tr = bands.get(b, [])
        if not tr:
            continue
        ci = bootstrap_mean_ci(tr)
        print(f"{b:<20}{len(tr):>6}{wr(tr):>8.1f}{sum_pnl(tr):>10.2f}{mean_pnl(tr):>10.4f}"
              f"{np.mean([t['pnl_pct'] for t in tr]):>10.4f}{sum(t['pnl_pct'] for t in tr):>10.2f}"
              f"{np.mean([t['amount'] for t in tr]):>9.2f}"
              f"       [{ci[0]:+.4f}, {ci[1]:+.4f}]")
    return bands


def sig_tests(rows, focus_band, label):
    print(f"\n--- SIGNIFICANCE: {label} (band={focus_band}) vs REST ---")
    inb = [r for r in rows if band_of(r['bb']) == focus_band]
    out = [r for r in rows if band_of(r['bb']) != focus_band]
    if not inb:
        print("  no trades"); return
    w_in, w_out = wr(inb), wr(out)
    x_in = sum(1 for t in inb if t['pnl_usdt'] > 0)
    x_out = sum(1 for t in out if t['pnl_usdt'] > 0)
    z, p = two_prop_ztest(x_in, len(inb), x_out, len(out))
    odds, p_fisher = stats.fisher_exact([[x_in, len(inb) - x_in],
                                         [x_out, len(out) - x_out]])
    print(f"  WR: band {w_in:.1f}% (n={len(inb)}) vs rest {w_out:.1f}% (n={len(out)})")
    print(f"  2-prop z-test: z={z:.3f}, p={p:.4f}")
    print(f"  Fisher exact: odds={odds:.3f}, p={p_fisher:.4f}")
    d, pp, ci = perm_test_pnl(inb, out)
    print(f"  Permutation (mean pnl diff): {d:+.4f} USD/trade, p={pp:.4f}, 95% CI [{ci[0]:+.4f}, {ci[1]:+.4f}]")
    # one-sample: is band WR different from overall SHORT WR (bb-recorded)?
    w_all = wr(rows)
    x_all = sum(1 for t in rows if t['pnl_usdt'] > 0)
    z2, p2 = two_prop_ztest(x_in, len(inb), x_all, len(rows))
    print(f"  vs overall bb-recorded SHORT WR {w_all:.1f}%: z={z2:.3f}, p={p2:.4f}")
    # CI on band WR
    se = np.sqrt(w_in / 100 * (1 - w_in / 100) / len(inb)) * 100
    print(f"  band WR 95% CI: [{w_in - 1.96*se:.1f}, {w_in + 1.96*se:.1f}]")
    print(f"  band total pnl: {sum_pnl(inb):+.2f} USD | avg pnl_pct {np.mean([t['pnl_pct'] for t in inb]):+.4f}%")
    print(f"  blocked-if-filter-always-on: {len(inb)} trades, {sum_pnl(inb):+.2f} USD foregone ({'profit avoided' if sum_pnl(inb) < 0 else 'PROFIT FOREGONE'})")


def confounder_table(rows, keyfn, title, focus):
    print(f"\n--- CONFOUNDER: {title} — {focus} band breakdown ---")
    inb = [r for r in rows if band_of(r['bb']) in focus]
    agg = defaultdict(lambda: [0, 0, 0.0])
    for r in inb:
        k = keyfn(r) or '(null)'
        agg[k][0] += 1
        agg[k][1] += 1 if r['pnl_usdt'] > 0 else 0
        agg[k][2] += r['pnl_usdt']
    print(f"  {'value':<40}{'n':>6}{'WR%':>8}{'sumPnL':>10}")
    for k, (n, w, s) in sorted(agg.items(), key=lambda kv: -kv[1][0]):
        if n >= 5:
            print(f"  {k:<40}{n:>6}{100*w/n:>8.1f}{s:>10.2f}")


def main():
    rows = load()
    print(f"Loaded {len(rows)} closed SHORT trades with entry_bb_position (all-time)")
    ref_dt = rows[-1]['close_time']
    print(f"Date range: {rows[0]['close_time']} .. {ref_dt}")

    # Baseline: all closed shorts (with/without bb recorded)
    allshort = q("""
        SELECT count(*)::int AS n,
               count(*) FILTER (WHERE entry_bb_position IS NOT NULL)::int AS with_bb,
               round(100.0*count(*) FILTER (WHERE pnl_usdt>0)/count(*),2) AS wr_all,
               round(avg(pnl_usdt)::numeric,4) AS avg_pnl_all
        FROM trades WHERE direction='SHORT' AND status='closed'
    """)[0]
    print(f"\nBaseline all closed SHORTs: n={allshort['n']}, with_bb={allshort['with_bb']} "
          f"({100*allshort['with_bb']/allshort['n']:.1f}% coverage), WR={allshort['wr_all']}%, avg_pnl={allshort['avg_pnl_all']}")
    print(f"bb-recorded subset WR: {wr(rows):.2f}%  avg_pnl={mean_pnl(rows):.4f}")

    band_table(rows, "ALL-TIME")
    for d, lab in [(30, "LAST 30 DAYS"), (90, "LAST 90 DAYS")]:
        w = window(rows, d)
        band_table(w, lab)

    print("\n" + "=" * 100)
    print("STATISTICAL SIGNIFICANCE TESTS (all-time)")
    print("=" * 100)
    sig_tests(rows, '5_DEAD_0.70-0.85', 'Dead zone 0.70-0.85')
    sig_tests(rows, '6a_0.85-0.95', '0.85-0.95')
    sig_tests(rows, '6b_0.95-1.00', '0.95-1.00')
    sig_tests(rows, '6c_>1.00', '>1.00')
    # combined 0.85+
    print("\n--- combined 0.85+ vs rest ---")
    inb = [r for r in rows if r['bb'] >= 0.85]
    out = [r for r in rows if r['bb'] < 0.85]
    x_in = sum(1 for t in inb if t['pnl_usdt'] > 0)
    x_out = sum(1 for t in out if t['pnl_usdt'] > 0)
    z, p = two_prop_ztest(x_in, len(inb), x_out, len(out))
    print(f"  WR: {wr(inb):.1f}% (n={len(inb)}) vs {wr(out):.1f}% (n={len(out)}) | z={z:.3f} p={p:.4f}")
    d, pp, ci = perm_test_pnl(inb, out)
    print(f"  mean pnl diff {d:+.4f} p={pp:.4f} CI[{ci[0]:+.4f},{ci[1]:+.4f}]")
    sig_tests(rows, '4_0.55-0.70', 'Good band 0.55-0.70')
    sig_tests(rows, '3b_0.50-0.55', '0.50-0.55 (cut by DEAD_ZONE2)')
    sig_tests(rows, '1_<0.20', 'Most profitable <0.20')

    print("\n" + "=" * 100)
    print("CONFOUNDERS")
    print("=" * 100)
    for focus, lab in [(['5_DEAD_0.70-0.85'], 'DEAD ZONE'),
                       (['6a_0.85-0.95', '6b_0.95-1.00', '6c_>1.00'], '0.85+'),
                       (['4_0.55-0.70'], 'GOOD 0.55-0.70')]:
        confounder_table(rows, lambda r: r['signal'], f"signal type [{lab}]", focus)
        confounder_table(rows, lambda r: r['volatility_regime'], f"volatility_regime [{lab}]", focus)
        confounder_table(rows, lambda r: r['entry_regime_4h'], f"entry_regime_4h [{lab}]", focus)
        confounder_table(rows, lambda r: r['close_time'].strftime('%Y-%m') if r['close_time'] else None,
                         f"month [{lab}]", focus)
        confounder_table(rows, lambda r: 'paper' if r['paper'] else 'live', f"paper/live [{lab}]", focus)
        confounder_table(rows, lambda r: r['sl_group'], f"sl_group [{lab}]", focus)

    # Signal x band interaction: top signals overall, do they differ inside vs outside dead zone?
    print("\n--- SIGNAL x DEAD-ZONE interaction (top 12 SHORT signals) ---")
    sig_counts = defaultdict(int)
    for r in rows:
        sig_counts[r['signal']] += 1
    top = [s for s, _ in sorted(sig_counts.items(), key=lambda kv: -kv[1])[:15] if s]
    top = top[:12]
    print(f"  {'signal':<40}{'inDZ n':>8}{'WR':>7}{'pnl':>8}{'outDZ n':>9}{'WR':>7}{'pnl':>8}")
    for s in top:
        indz = [r for r in rows if r['signal'] == s and band_of(r['bb']) == '5_DEAD_0.70-0.85']
        outdz = [r for r in rows if r['signal'] == s and band_of(r['bb']) != '5_DEAD_0.70-0.85']
        print(f"  {s:<40}{len(indz):>8}{wr(indz):>7.1f}{sum_pnl(indz):>8.2f}{len(outdz):>9}{wr(outdz):>7.1f}{sum_pnl(outdz):>8.2f}")

    print("\n--- SIGNAL x 0.85+ interaction (top 12 SHORT signals) ---")
    print(f"  {'signal':<40}{'in085 n':>8}{'WR':>7}{'pnl':>8}{'out085 n':>9}{'WR':>7}{'pnl':>8}")
    for s in top:
        inb = [r for r in rows if r['signal'] == s and r['bb'] >= 0.85]
        outb = [r for r in rows if r['signal'] == s and r['bb'] < 0.85]
        print(f"  {s:<40}{len(inb):>8}{wr(inb):>7.1f}{sum_pnl(inb):>8.2f}{len(outb):>9}{wr(outb):>7.1f}{sum_pnl(outb):>8.2f}")

    # Winners analysis: would the filter have blocked winners?
    print("\n" + "=" * 100)
    print("WINNERS INSIDE BLOCKED ZONES (opportunity cost)")
    print("=" * 100)
    for lab, pred in [('DEAD 0.70-0.85', lambda b: 0.70 <= b <= 0.85),
                      ('0.85+', lambda b: b >= 0.85)]:
        zone = [r for r in rows if pred(r['bb'])]
        wins = [r for r in zone if r['pnl_usdt'] > 0]
        losses = [r for r in zone if r['pnl_usdt'] <= 0]
        print(f"\n{lab}: n={len(zone)}, winners={len(wins)} ({wr(zone):.1f}%), losers/flat={len(losses)}")
        print(f"  winners pnl sum: {sum_pnl(wins):+.2f} | losers pnl sum: {sum_pnl(losses):+.2f} | net: {sum_pnl(zone):+.2f}")
        best = sorted(wins, key=lambda t: -t['pnl_usdt'])[:5]
        print(f"  top-5 winners:")
        for t in best:
            print(f"    {t['close_time']:%Y-%m-%d} {t['token']:<8} {(t['signal'] or '(null)')[:32]:<34} bb={t['bb']:.4f} pnl={t['pnl_usdt']:+.2f} regime={t['volatility_regime']}")
        worst = sorted([r for r in zone if r['pnl_usdt'] < 0], key=lambda t: t['pnl_usdt'])[:5]
        print(f"  top-5 losers:")
        for t in worst:
            print(f"    {t['close_time']:%Y-%m-%d} {t['token']:<8} {(t['signal'] or '(null)')[:32]:<34} bb={t['bb']:.4f} pnl={t['pnl_usdt']:+.2f} regime={t['volatility_regime']}")

    # Boundary / precision analysis
    print("\n" + "=" * 100)
    print("BOUNDARY & DATA-QUALITY CHECKS")
    print("=" * 100)
    near = [r for r in rows if 0.83 <= r['bb'] <= 0.87]
    print(f"Trades with bb in [0.83,0.87] (boundary of proposed 0.85 cut): n={len(near)}")
    for r in sorted(near, key=lambda t: t['bb']):
        print(f"  {r['close_time']:%Y-%m-%d} {r['token']:<8} bb={r['bb']:.2f} pnl={r['pnl_usdt']:+.2f} {(r['signal'] or '(null)')[:30]}")
    # column vs metadata agreement
    both = [r for r in rows if r['meta_bb'] is not None]
    print(f"\nTrades with BOTH column bb and metadata bb: n={len(both)}")
    if both:
        diffs = [abs(float(r['meta_bb']) - float(r['bb'])) for r in both]
        print(f"  |col - meta| mean={np.mean(diffs):.4f} max={np.max(diffs):.4f}")
        mism = [r for r in both if band_of(float(r['meta_bb'])) != band_of(float(r['bb']))]
        print(f"  band assignments that differ (col vs meta, incl. rounding at 0.85): n={len(mism)}")
        for r in mism[:10]:
            print(f"    {r['close_time']:%Y-%m-%d} {r['token']:<8} col={r['bb']} meta={r['meta_bb']} pnl={r['pnl_usdt']:+.2f}")
    # bb recorded coverage over time
    print("\nbb_position recording coverage by month (all closed SHORTs):")
    cov = q("""
        SELECT to_char(date_trunc('month', close_time),'YYYY-MM') AS mo,
               count(*)::int AS n,
               count(*) FILTER (WHERE entry_bb_position IS NOT NULL)::int AS with_bb
        FROM trades WHERE direction='SHORT' AND status='closed'
        GROUP BY 1 ORDER BY 1
    """)
    for c in cov:
        pct = 100 * c['with_bb'] / c['n'] if c['n'] else 0
        print(f"  {c['mo']}: {c['with_bb']}/{c['n']} ({pct:.0f}%)")

    # July crash check: was dead zone concentrated in a bad period?
    print("\nDead-zone share of bb-recorded shorts by month:")
    dz = [r for r in rows if band_of(r['bb']) == '5_DEAD_0.70-0.85']
    mo_all = defaultdict(int); mo_dz = defaultdict(int)
    for r in rows:
        mo_all[r['close_time'].strftime('%Y-%m')] += 1
    for r in dz:
        mo_dz[r['close_time'].strftime('%Y-%m')] += 1
    for m in sorted(mo_all):
        print(f"  {m}: dz {mo_dz.get(m,0)}/{mo_all[m]} ({100*mo_dz.get(m,0)/mo_all[m]:.1f}%)")

    # Recent-window verdicts (what matters for the live decision)
    print("\n" + "=" * 100)
    print("RECENT-WINDOW VERDICTS")
    print("=" * 100)
    for d in (30, 90):
        w = window(rows, d)
        dzw = [r for r in w if band_of(r['bb']) == '5_DEAD_0.70-0.85']
        hz = [r for r in w if r['bb'] >= 0.85]
        print(f"\nLast {d} days (n={len(w)}):")
        if dzw:
            print(f"  DEAD 0.70-0.85: n={len(dzw)} WR={wr(dzw):.1f}% pnl={sum_pnl(dzw):+.2f} avg={mean_pnl(dzw):+.4f}")
            z_, p_ = two_prop_ztest(sum(1 for t in dzw if t['pnl_usdt'] > 0), len(dzw),
                                    sum(1 for t in w if t['pnl_usdt'] > 0), len(w))
            print(f"    vs rest-of-window WR: z={z_:.3f} p={p_:.4f}")
        else:
            print("  DEAD 0.70-0.85: no trades")
        if hz:
            print(f"  0.85+: n={len(hz)} WR={wr(hz):.1f}% pnl={sum_pnl(hz):+.2f} avg={mean_pnl(hz):+.4f}")
            z_, p_ = two_prop_ztest(sum(1 for t in hz if t['pnl_usdt'] > 0), len(hz),
                                    sum(1 for t in w if t['pnl_usdt'] > 0), len(w))
            print(f"    vs rest-of-window WR: z={z_:.3f} p={p_:.4f}")
        else:
            print("  0.85+: no trades")

    # Meta-bb view: what the filter actually sees
    print("\n" + "=" * 100)
    print("FILTER'S ACTUAL VIEW: metadata bb_position (what signal_compactor reads)")
    print("=" * 100)
    meta_rows = q("""
        SELECT id, token, signal,
               (_signal_metadata->>'bb_position')::float8 AS bb,
               COALESCE(pnl_usdt,0)::float8 AS pnl_usdt, close_time
        FROM trades
        WHERE direction='SHORT' AND status='closed'
          AND _signal_metadata ? 'bb_position'
        ORDER BY close_time
    """)
    print(f"n={len(meta_rows)} closed SHORTs with metadata bb_position")
    for r in meta_rows:
        r['band'] = band_of(r['bb'])
    mb = defaultdict(list)
    for r in meta_rows:
        mb[r['band']].append(r)
    for b in sorted(mb):
        tr = mb[b]
        print(f"  {b:<20} n={len(tr):>4} WR={wr(tr):>6.1f}% pnl={sum_pnl(tr):>+8.2f} avg={mean_pnl(tr):>+.4f}")

    # Counterfactual: dead zone vs bands the filter would still allow
    print("\n" + "=" * 100)
    print("COUNTERFACTUAL: dead zone vs currently-ALLOWED bands")
    print("=" * 100)
    allowed_pred = lambda b: (b < 0.35) or (0.55 <= b < 0.70)
    dz = [r for r in rows if 0.70 <= r['bb'] <= 0.85]
    alw = [r for r in rows if allowed_pred(r['bb'])]
    x_dz = sum(1 for t in dz if t['pnl_usdt'] > 0)
    x_alw = sum(1 for t in alw if t['pnl_usdt'] > 0)
    z, p = two_prop_ztest(x_dz, len(dz), x_alw, len(alw))
    print(f"  dead zone WR {wr(dz):.1f}% (n={len(dz)}) vs allowed-bands WR {wr(alw):.1f}% (n={len(alw)}) | z={z:.3f} p={p:.4f}")
    d, pp, ci = perm_test_pnl(dz, alw)
    print(f"  mean pnl diff {d:+.4f} p={pp:.4f} CI[{ci[0]:+.4f},{ci[1]:+.4f}]")
    hz = [r for r in rows if r['bb'] >= 0.85]
    x_hz = sum(1 for t in hz if t['pnl_usdt'] > 0)
    z, p = two_prop_ztest(x_hz, len(hz), x_alw, len(alw))
    print(f"  0.85+ WR {wr(hz):.1f}% (n={len(hz)}) vs allowed-bands WR {wr(alw):.1f}% | z={z:.3f} p={p:.4f}")
    d, pp, ci = perm_test_pnl(hz, alw)
    print(f"  mean pnl diff {d:+.4f} p={pp:.4f} CI[{ci[0]:+.4f},{ci[1]:+.4f}]")

    # Overall SHORT book context
    print("\n" + "=" * 100)
    print("SHORT BOOK CONTEXT")
    print("=" * 100)
    ctx = q("""
        SELECT count(*)::int AS n,
               round(sum(pnl_usdt)::numeric,2) AS sum_pnl,
               round(100.0*count(*) FILTER (WHERE pnl_usdt>0)/count(*),2) AS wr,
               round(avg(amount_usdt)::numeric,2) AS avg_amt
        FROM trades WHERE direction='SHORT' AND status='closed'
    """)[0]
    print(f"  all closed SHORTs: n={ctx['n']}, sum_pnl={ctx['sum_pnl']} USD, WR={ctx['wr']}%, avg_amount={ctx['avg_amt']} USD")
    print(f"  bb-recorded subset: n={len(rows)}, sum_pnl={sum_pnl(rows):+.2f} USD, WR={wr(rows):.1f}%")
    print(f"  dead zone share of bb shorts: {len(dz)}/{len(rows)} ({100*len(dz)/len(rows):.1f}%)")
    print(f"  0.85+ share of bb shorts: {len(hz)}/{len(rows)} ({100*len(hz)/len(rows):.1f}%)")
    print(f"  combined block 0.70+: {len(dz)+len(hz)}/{len(rows)} ({100*(len(dz)+len(hz))/len(rows):.1f}%) of bb-recorded SHORTs")
    print(f"  combined 0.70+ net pnl if always blocked: {-(sum_pnl(dz)+sum_pnl(hz)):+.2f} USD avoided")

    # MFE/MAE by band (was downside follow-through available?)
    print("\n--- MFE/MAE by band (downside excursion available to SHORT) ---")
    mfe = q("""
        SELECT
          CASE
            WHEN entry_bb_position < 0.2 THEN '1_<0.20'
            WHEN entry_bb_position < 0.35 THEN '2_0.20-0.35'
            WHEN entry_bb_position < 0.50 THEN '3_0.35-0.50'
            WHEN entry_bb_position < 0.55 THEN '3b_0.50-0.55'
            WHEN entry_bb_position < 0.70 THEN '4_0.55-0.70'
            WHEN entry_bb_position < 0.85 THEN '5_DEAD_0.70-0.85'
            WHEN entry_bb_position < 0.95 THEN '6a_0.85-0.95'
            WHEN entry_bb_position <= 1.00 THEN '6b_0.95-1.00'
            ELSE '6c_>1.00'
          END AS band,
          count(*)::int AS n,
          round(avg(mfe_pct)::numeric,3) AS avg_mfe,
          round(avg(mae_pct)::numeric,3) AS avg_mae,
          round(avg(mfe_pct) FILTER (WHERE pnl_usdt>0)::numeric,3) AS avg_mfe_win,
          round(avg(mfe_pct) FILTER (WHERE pnl_usdt<=0)::numeric,3) AS avg_mfe_loss
        FROM trades
        WHERE direction='SHORT' AND status='closed' AND entry_bb_position IS NOT NULL
        GROUP BY 1 ORDER BY 1
    """)
    print(f"  {'band':<20}{'n':>6}{'avgMFE':>9}{'avgMAE':>9}{'MFE_win':>9}{'MFE_loss':>9}")
    for m in mfe:
        print(f"  {m['band']:<20}{m['n']:>6}{str(m['avg_mfe']):>9}{str(m['avg_mae']):>9}{str(m['avg_mfe_win']):>9}{str(m['avg_mfe_loss']):>9}")

    # Filter coverage: which signals actually carry bb_position in metadata?
    print("\n" + "=" * 100)
    print("FILTER COVERAGE: metadata bb_position by signal family (closed SHORTs)")
    print("=" * 100)
    cov2 = q("""
        SELECT COALESCE(signal,'(null)') AS signal,
               count(*)::int AS n,
               count(*) FILTER (WHERE _signal_metadata ? 'bb_position')::int AS with_meta_bb
        FROM trades WHERE direction='SHORT' AND status='closed'
        GROUP BY 1 HAVING count(*) >= 10
        ORDER BY 2 DESC LIMIT 15
    """)
    for c in cov2:
        pct = 100 * c['with_meta_bb'] / c['n']
        print(f"  {c['signal']:<45}{c['with_meta_bb']:>5}/{c['n']:<5} ({pct:.0f}%)")

    print("\nDONE")


if __name__ == '__main__':
    main()
