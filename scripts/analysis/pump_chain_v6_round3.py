#!/usr/bin/env python3
"""Round-3: out-of-sample validation of candidate filters with time split."""
import psycopg2


def q(sql, args=()):
    conn = psycopg2.connect(host='/var/run/postgresql', database='brain', user='postgres')
    cur = conn.cursor()
    cur.execute(sql, args)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows


rows = q("""
    SELECT open_time, direction, pnl_usdt::float8,
           (_signal_metadata->>'rsi_14')::numeric,
           _signal_metadata->>'momentum_state',
           (_signal_metadata->>'z_score')::numeric
    FROM trades
    WHERE status='closed' AND signal LIKE '%%pump-chain%%'
      AND open_time > now() - interval '60 days' AND _signal_metadata IS NOT NULL
    ORDER BY open_time;
""")
n = len(rows)
cut = int(n * 0.7)
splits = [('IS (first 70%)', rows[:cut]), ('OOS (last 30%)', rows[cut:]), ('FULL', rows)]


def rsi(r):
    return 50.0 if r[3] is None else float(r[3])


def ms(r):
    return r[4] or ''


def report(label, subset, pred):
    sub = [r for r in subset if pred(r)]
    blk = [r for r in subset if not pred(r)]
    if not sub:
        return f'{label}: n=0'
    w = sum(1 for r in sub if r[2] > 0)
    bw = sum(1 for r in blk if r[2] > 0)
    return (f'{label:22s} kept n={len(sub):3d} WR={100.0*w/len(sub):5.1f}% '
            f'pnl=${sum(r[2] for r in sub):+6.2f} | blocked n={len(blk):3d} '
            f'({bw}W/{len(blk)-bw}L) pnl=${sum(r[2] for r in blk):+6.2f}')


print('=== LONG candidate filters, time-split validation ===')
long_preds = [
    ('baseline', lambda r: True),
    ('block RSI<40', lambda r: rsi(r) >= 40),
    ('block RSI>70', lambda r: rsi(r) <= 70),
    ('block RSI extremes', lambda r: 40 <= rsi(r) <= 70),
    ('block mom flat', lambda r: ms(r) != 'flat'),
    ('RSI ext + flat (combo)', lambda r: 40 <= rsi(r) <= 70 and ms(r) != 'flat'),
]
for label, subset in splits:
    long_sub = [r for r in subset if r[1] == 'LONG']
    print(f'-- {label} (LONG n={len(long_sub)}) --')
    for name, pred in long_preds:
        print('   ', report(name, long_sub, pred))

print('\n=== SHORT candidate filters, time-split validation ===')
short_preds = [
    ('baseline', lambda r: True),
    ('block RSI<40', lambda r: rsi(r) >= 40),
    ('block RSI>70', lambda r: rsi(r) <= 70),
    ('block RSI extremes', lambda r: 40 <= rsi(r) <= 70),
    ('block mom flat', lambda r: ms(r) != 'flat'),
    ('RSI<40 + flat (combo)', lambda r: rsi(r) >= 40 and ms(r) != 'flat'),
]
for label, subset in splits:
    short_sub = [r for r in subset if r[1] == 'SHORT']
    print(f'-- {label} (SHORT n={len(short_sub)}) --')
    for name, pred in short_preds:
        print('   ', report(name, short_sub, pred))

print('\n=== Joint LONG+SHORT combined, time-split ===')
combo = {
    'LONG': lambda r: 40 <= rsi(r) <= 70 and ms(r) != 'flat',
    'SHORT': lambda r: rsi(r) >= 40 and ms(r) != 'flat',
}
for label, subset in splits:
    pred = lambda r: combo[r[1]](r)
    print('   ', f'{label}', report('both-side combo', subset, pred))
    print('   ', f'{label}', report('baseline', subset, lambda r: True))

print('\n=== Staleness <2m LONG block, time-split (sanity check odd finding) ===')
for label, subset in splits:
    long_sub = [r for r in subset if r[1] == 'LONG' and r[3] is not None]
    # staleness not selected here; pull separately below
print('(staleness checked separately)')

print('\n=== Missing-metadata rows (rsi=0 anomaly check) ===')
rows2 = q("""
    SELECT COUNT(*) FROM trades
    WHERE status='closed' AND signal LIKE '%%pump-chain%%'
      AND open_time > now() - interval '60 days'
      AND (_signal_metadata->>'rsi_14') IS NULL;
""")
print(f'  rows with NULL rsi_14: {rows2[0][0]}')
rows3 = q("""
    SELECT COUNT(*) FROM trades
    WHERE status='closed' AND signal LIKE '%%pump-chain%%'
      AND open_time > now() - interval '60 days'
      AND _signal_metadata IS NULL;
""")
print(f'  rows with NULL metadata entirely: {rows3[0][0]}')
