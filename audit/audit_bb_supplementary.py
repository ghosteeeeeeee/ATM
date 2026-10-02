#!/usr/bin/env python3
"""Supplementary tests: signal x band interactions + filter's-eye-view (metadata bb)."""
import numpy as np
import psycopg2
from collections import defaultdict

CONN = dict(host='/var/run/postgresql', dbname='brain', user='postgres')

def q(sql):
    conn = psycopg2.connect(**CONN)
    try:
        cur = conn.cursor()
        cur.execute(sql)
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, r)) for r in cur.fetchall()]
    finally:
        conn.close()

def ztest(x1, n1, x2, n2):
    if not n1 or not n2: return float('nan'), float('nan')
    p1, p2 = x1/n1, x2/n2
    p = (x1+x2)/(n1+n2)
    se = np.sqrt(p*(1-p)*(1/n1+1/n2))
    if se == 0: return 0.0, 1.0
    z = (p1-p2)/se
    return z, 2*(1 - __import__('scipy').stats.norm.cdf(abs(z)))

def perm_pnl(a, b, n_iter=20000, seed=1):
    rng = np.random.default_rng(seed)
    a = np.array(a, float); b = np.array(b, float)
    if not len(a) or not len(b): return float('nan'), float('nan'), (float('nan'),)*2
    obs = a.mean() - b.mean()
    pooled = np.concatenate([a, b]); n_a = len(a); exc = 0
    for _ in range(n_iter):
        rng.shuffle(pooled)
        if abs(pooled[:n_a].mean() - pooled[n_a:].mean()) >= abs(obs): exc += 1
    bs = [rng.choice(a, len(a), True).mean() - rng.choice(b, len(b), True).mean() for _ in range(3000)]
    return obs, (exc+1)/(n_iter+1), (np.percentile(bs,2.5), np.percentile(bs,97.5))

def wr(rows): return 100.0*sum(1 for r in rows if r['pnl']>0)/len(rows) if rows else float('nan')

print("="*90)
print("1) SIGNAL x DEAD-ZONE interaction — formal tests (column bb)")
print("="*90)
rows = q("""
  SELECT signal, entry_bb_position::float8 AS bb, COALESCE(pnl_usdt,0)::float8 AS pnl
  FROM trades WHERE direction='SHORT' AND status='closed' AND entry_bb_position IS NOT NULL
""")
for sig in ['accel_300_,rs_s_broken', 'accel_300_,rs_r', 'pullback-entry-']:
    indz = [r for r in rows if r['signal']==sig and 0.70 <= r['bb'] < 0.85]
    outdz = [r for r in rows if r['signal']==sig and not (0.70 <= r['bb'] < 0.85)]
    if not indz: continue
    x1 = sum(1 for r in indz if r['pnl']>0); x2 = sum(1 for r in outdz if r['pnl']>0)
    z, p = ztest(x1, len(indz), x2, len(outdz))
    d, pp, ci = perm_pnl([r['pnl'] for r in indz], [r['pnl'] for r in outdz])
    print(f"{sig}: IN-DZ n={len(indz)} WR={wr(indz):.1f}% pnl={sum(r['pnl'] for r in indz):+.2f} | "
          f"OUT n={len(outdz)} WR={wr(outdz):.1f}% pnl={sum(r['pnl'] for r in outdz):+.2f}")
    print(f"   WR z={z:.3f} p={p:.4f} | mean-pnl diff {d:+.4f} p={pp:.4f} CI[{ci[0]:+.4f},{ci[1]:+.4f}]")

print("\n" + "="*90)
print("2) SIGNAL x 0.85+ interaction — formal tests (column bb)")
print("="*90)
for sig in ['accel_300_,rs_s_broken', 'accel_300_,rs_r', 'pullback-entry-', 'rs_r,rs_s_broken']:
    inb = [r for r in rows if r['signal']==sig and r['bb'] >= 0.85]
    outb = [r for r in rows if r['signal']==sig and r['bb'] < 0.85]
    if not inb: continue
    x1 = sum(1 for r in inb if r['pnl']>0); x2 = sum(1 for r in outb if r['pnl']>0)
    z, p = ztest(x1, len(inb), x2, len(outb))
    d, pp, ci = perm_pnl([r['pnl'] for r in inb], [r['pnl'] for r in outb])
    print(f"{sig}: IN-085 n={len(inb)} WR={wr(inb):.1f}% pnl={sum(r['pnl'] for r in inb):+.2f} | "
          f"OUT n={len(outb)} WR={wr(outb):.1f}% pnl={sum(r['pnl'] for r in outb):+.2f}")
    print(f"   WR z={z:.3f} p={p:.4f} | mean-pnl diff {d:+.4f} p={pp:.4f} CI[{ci[0]:+.4f},{ci[1]:+.4f}]")

print("\n" + "="*90)
print("3) FILTER'S-EYE-VIEW: metadata bb_position bands (only signals the filter can see)")
print("="*90)
mrows = q("""
  SELECT signal,
         (_signal_metadata->>'bb_position')::float8 AS bb,
         COALESCE(pnl_usdt,0)::float8 AS pnl
  FROM trades WHERE direction='SHORT' AND status='closed' AND _signal_metadata ? 'bb_position'
""")
print(f"n={len(mrows)} closed SHORTs carrying metadata bb_position")
def mband(b):
    if b < 0.20: return '<0.20'
    if b < 0.35: return '0.20-0.35'
    if b < 0.50: return '0.35-0.50'
    if b < 0.55: return '0.50-0.55'
    if b < 0.70: return '0.55-0.70'
    if b <= 0.85: return 'DZ_0.70-0.85(code-incl)'
    if b < 0.95: return '0.85-0.95'
    if b <= 1.00: return '0.95-1.00'
    return '>1.00'
mb = defaultdict(list)
for r in mrows: mb[mband(r['bb'])].append(r)
order = ['<0.20','0.20-0.35','0.35-0.50','0.50-0.55','0.55-0.70','DZ_0.70-0.85(code-incl)','0.85-0.95','0.95-1.00','>1.00']
rest_all = mrows
tot_n = len(mrows); tot_x = sum(1 for r in mrows if r['pnl']>0)
tot_pnl = [r['pnl'] for r in mrows]
print(f"  {'band':<24}{'n':>5}{'WR%':>7}{'pnl$':>8}{'vs-rest WR p':>13}{'vs-rest pnl p':>14}")
for b in order:
    tr = mb.get(b, [])
    if not tr: continue
    idx = set(id(r) for r in tr)
    rest = [r for r in mrows if id(r) not in idx]
    x1 = sum(1 for r in tr if r['pnl']>0); x2 = sum(1 for r in rest if r['pnl']>0)
    z, p = ztest(x1, len(tr), x2, len(rest))
    d, pp, ci = perm_pnl([r['pnl'] for r in tr], [r['pnl'] for r in rest])
    print(f"  {b:<24}{len(tr):>5}{wr(tr):>7.1f}{sum(r['pnl'] for r in tr):>8.2f}{p:>13.4f}{pp:>14.4f}")
    if b in ('DZ_0.70-0.85(code-incl)', '0.85-0.95', '>1.00', '0.50-0.55'):
        print(f"      -> mean-pnl diff {d:+.4f} CI[{ci[0]:+.4f},{ci[1]:+.4f}]")

print("\n" + "="*90)
print("4) Exact-0.85 boundary trades (blocked by current inclusive dead zone)")
print("="*90)
b85 = q("""
  SELECT token, signal, entry_bb_position::float8 AS bb, COALESCE(pnl_usdt,0)::float8 AS pnl, close_time::date AS d
  FROM trades WHERE direction='SHORT' AND status='closed' AND entry_bb_position = 0.85
  ORDER BY close_time
""")
print(f"n={len(b85)}, net pnl={sum(r['pnl'] for r in b85):+.2f}, WR={wr(b85):.1f}%")
for r in b85:
    print(f"  {r['d']} {r['token']:<8} pnl={r['pnl']:+.2f} {(r['signal'] or '(null)')[:34]}")

print("\n" + "="*90)
print("5) Code-vs-comment check: signal_compactor dead-zone2 claims vs all-time data")
print("="*90)
z2 = q("""
  SELECT CASE
           WHEN entry_bb_position < 0.35 THEN 'below_0.35'
           WHEN entry_bb_position < 0.50 THEN '0.35-0.50'
           WHEN entry_bb_position < 0.55 THEN '0.50-0.55'
           ELSE '0.55+'
         END AS band,
         count(*)::int AS n,
         round(100.0*count(*) FILTER (WHERE pnl_usdt>0)/count(*),1) AS wr,
         round(sum(pnl_usdt)::numeric,2) AS pnl
  FROM trades WHERE direction='SHORT' AND status='closed'
    AND entry_bb_position IS NOT NULL AND entry_bb_position >= 0.35
  GROUP BY 1 ORDER BY 1
""")
for r in z2:
    print(f"  {r['band']:<12} n={r['n']:<5} WR={r['wr']}%  pnl={r['pnl']}")
print("  (code comment claims: 0.35-0.55 chop 25T 44%WR -$0.99/7d; preserves 0.55-0.70 at 70.6%WR +$0.95)")

print("\nDONE")
