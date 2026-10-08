#!/usr/bin/env python3
"""Rev1 gate validation: revised gates after independent-audit fixes.
LONG: block RSI<40 or momentum flat (RSI>70 dropped — sign-unstable, CEO reversed it)
SHORT: block RSI<45 or momentum flat (floor aligned with live PUMP_CHAIN_SHORT_RSI_MIN=45)
Samples: (a) hyphen-only, (b) extended family incl. underscore variants.
Split: IS/OOS robustness screen + permutation + Fisher/Welch."""
import math
import psycopg2
from scipy import stats as st


def q(sql, args=()):
    conn = psycopg2.connect(host='/var/run/postgresql', database='brain', user='postgres')
    cur = conn.cursor()
    cur.execute(sql, args)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows


def load(ext=False):
    cond = "(signal LIKE '%%pump-chain%%' OR position('pump_chain' in signal) > 0)" if ext \
        else "signal LIKE '%%pump-chain%%'"
    return q(f"""
        SELECT open_time, direction, token, pnl_usdt::float8,
               (_signal_metadata->>'rsi_14')::numeric,
               _signal_metadata->>'momentum_state'
        FROM trades
        WHERE status='closed' AND {cond}
          AND open_time > now() - interval '60 days' AND _signal_metadata IS NOT NULL
        ORDER BY open_time;""")


def rsi(r):
    return 50.0 if r[4] is None else float(r[4])


def ms(r):
    return r[5] or ''


def gate_long(r):
    return rsi(r) >= 40 and ms(r) != 'flat'


def gate_short45(r):
    return rsi(r) >= 45 and ms(r) != 'flat'


def gate_short45_rsi_only(r):
    return rsi(r) >= 45


def stats(sub, blk):
    def agg(x):
        w = sum(1 for r in x if r[3] > 0)
        return len(x), w, (100.0 * w / len(x) if x else 0), sum(r[3] for r in x)
    kn, kw, kwr, kp = agg(sub)
    bn, bw, bwr, bp = agg(blk)
    fw = st.fisher_exact([[kw, kn - kw], [bw, bn - bw]])[1] if kn and bn else float('nan')
    wp = st.ttest_ind([r[3] for r in sub], [r[3] for r in blk], equal_var=False).pvalue if kn > 1 and bn > 1 else float('nan')
    return kn, kw, kwr, kp, bn, bw, bwr, bp, fw, wp


def perm(sub_all, gate, iters=20000):
    """Permutation: how often does a random block of same size do as well on kept-PnL?"""
    import random
    random.seed(42)
    kept_pnl = sum(r[3] for r in sub_all if gate(r))
    n_blk = sum(1 for r in sub_all if not gate(r))
    vals = [r[3] for r in sub_all]
    beat = 0
    for _ in range(iters):
        idx = set(random.sample(range(len(vals)), n_blk))
        kp = sum(v for i, v in enumerate(vals) if i not in idx)
        if kp >= kept_pnl:
            beat += 1
    return beat / iters


for ext in (False, True):
    rows = load(ext)
    n = len(rows)
    cut = int(n * 0.7)
    label = 'EXTENDED family' if ext else 'HYPHEN-only'
    print(f'\n{"="*90}\n== {label}: n={n} (IS {cut} / OOS {n-cut})\n{"="*90}')

    for d, gate, name in (('LONG', gate_long, 'block RSI<40 or flat'),
                          ('SHORT', gate_short45, 'block RSI<45 or flat'),
                          ('SHORT', gate_short45_rsi_only, 'block RSI<45 (rsi only)')):
        sub_all = [r for r in rows if r[1] == d]
        dcut = int(len(sub_all) * 0.7)
        splits = (('FULL', sub_all), ('IS', sub_all[:dcut]), ('OOS', sub_all[dcut:]))
        for split, part in splits:
            kept = [r for r in part if gate(r)]
            blk = [r for r in part if not gate(r)]
            if not kept or not blk:
                print(f'  {d:5s} {name:26s} {split:4s}: kept={len(kept)} blk={len(blk)} (skip)')
                continue
            kn, kw, kwr, kp, bn, bw, bwr, bp, fw, wp = stats(kept, blk)
            print(f'  {d:5s} {name:26s} {split:4s}: kept {kn:3d}T {kwr:5.1f}% ${kp:+6.2f} | '
                  f'blocked {bn:3d}T ({bw}W/{bn-bw}L) ${bp:+6.2f} | '
                  f'Fisher p={fw:.3f} Welch p={wp:.3f}')
        if d == 'LONG' or name == 'block RSI<45 or flat':
            p = perm(sub_all, gate)
            print(f'  {d:5s} {name:26s} PERM: {p:.4f} (frac random blocks doing as well)')
