#!/usr/bin/env python3
"""repeat_after_stop_2026-10-26 — brain_auditor creative #1 (run #159)

Hypothesis:
  H1: re-entering a coin in the SAME direction shortly after a prior
      same-coin LOSS is worse than the control (same-direction re-entry
      after a prior same-coin WIN).

BAR (as implemented): blocked n>=20 at 30d, LEFT-tail Fisher p<0.025
(Bonferroni x2 — the 120m window was chosen AFTER seeing the gap-bucket
table, so both gap cells count as tests), 7d and 14d same sign, and
fkB<20%. An earlier draft of this docstring said "pre-registered p<0.05";
that was wrong and is why the Bonferroni correction exists.

Anchor: gap = close_time(prior) -> open_time(next), same token; pairs
whose gap is negative (overlapping/concurrent trades) are EXCLUDED and
counted, not silently dropped. Boundary: WHERE filters on open_time only,
so a prev trade opened before the window but closed inside it is invisible
(0 such rows at run time).
Units: pnl_usdt (unleveraged on notional) vs pnl_usdt. Never pnl_pct.
"""
import sys
import psycopg2
from math import comb

def fisher_2x2(a, b, c, d):
    """LEFT-tailed one-sided P(X <= a), table [[a,b],[c,d]].
    a = winners in the cohort we claim is WORSE. Small p = cohort has
    fewer winners than the control (c,d)."""
    n = a + b + c + d
    r1, c1 = a + b, a + c
    tot = comb(n, r1)
    p = 0.0
    for x in range(0, a + 1):
        if x > r1 or x > c1 or (r1 - x) > (n - c1):
            continue
        p += comb(c1, x) * comb(n - c1, r1 - x)
    return p / tot


def load(days):
    conn = psycopg2.connect(host='/var/run/postgresql', database='brain', user='postgres')
    cur = conn.cursor()
    cur.execute("""SELECT token, direction, pnl_usdt, exit_reason, open_time, close_time
                   FROM trades WHERE status='closed' AND open_time > NOW() - INTERVAL '%d days'
                   ORDER BY token, open_time""" % days)
    rows = cur.fetchall()
    conn.close()
    return rows


def cohorts(rows, max_gap_min=120.0):
    by = {}
    for r in rows:
        by.setdefault(r[0], []).append(r)
    out = {'same_after_loss': [], 'same_after_win': [], 'flip_after_loss': [],
           'flip_after_win': [], 'same_after_be': [], 'flip_after_be': [],
           'excluded_overlap': [], 'excluded_gap': []}
    for v in by.values():
        for i in range(1, len(v)):
            prev, nxt = v[i - 1], v[i]
            gap = (nxt[4] - prev[5]).total_seconds() / 60.0
            if gap < 0:
                out['excluded_overlap'].append(nxt)
                continue
            if gap > max_gap_min:
                out['excluded_gap'].append(nxt)
                continue
            # breakeven (pnl == 0) is neither win nor loss -> own bucket,
            # never folded into the control (bug_hunter #159 MEDIUM/LOW).
            prev_kind = 'loss' if prev[2] < 0 else ('win' if prev[2] > 0 else 'be')
            same = nxt[1] == prev[1]
            key = ('same' if same else 'flip') + '_after_' + prev_kind
            out[key].append((nxt, gap, prev))
    return out


def stat(c):
    n = len(c)
    w = sum(1 for x in c if x[0][2] > 0)
    p = sum(x[0][2] for x in c)
    return n, w, p


def show(label, c):
    n, w, p = stat(c)
    print(f"  {label:<22} n={n:<4} wr={100*w/n if n else 0:5.1f}%  pnl={p:+.2f}")
    return n, w, p


def run(days, gap=120.0, tag=''):
    rows = load(days)
    co = cohorts(rows, gap)
    print(f"== {days}d{tag} (gap<={gap:.0f}m)  closed={len(rows)}")
    n1, w1, p1 = show('same_after_loss', co['same_after_loss'])
    n2, w2, p2 = show('same_after_win CTRL', co['same_after_win'])
    n3, w3, p3 = show('flip_after_loss', co['flip_after_loss'])
    n4, w4, p4 = show('flip_after_win', co['flip_after_win'])
    show('same_after_be (excluded)', co['same_after_be'])
    show('flip_after_be (excluded)', co['flip_after_be'])
    print(f"  excluded: {len(co['excluded_overlap'])} overlapping, "
          f"{len(co['excluded_gap'])} gap>{gap:.0f}m")
    # primary test: same_after_loss vs same_after_win
    fish = fisher_2x2(w1, n1 - w1, w2, n2 - w2)
    print(f"  LEFT-tail Fisher P(WR <= ctrl) = {fish:.4f}")
    # winner impact if we block same_after_loss
    print(f"  fk (blocked winners / blocked) = {w1}/{n1} = {100*w1/n1 if n1 else 0:.1f}%  save={-p1:+.2f}")
    return dict(n=n1, w=w1, p=p1, ctrl_n=n2, ctrl_w=w2, ctrl_p=p2, fisher=fish,
                fk=100 * w1 / n1 if n1 else 0.0, blocked_pnl=p1)


def selfcheck():
    # hand-built table: [[13,32],[41,40]] -> known Fisher value
    p = fisher_2x2(13, 32, 41, 40)
    assert 0.0 < p < 1.0, p
    # monotonicity: more winners in the bad cohort => larger (less significant) p
    assert fisher_2x2(20, 25, 41, 40) > fisher_2x2(5, 50, 41, 40)
    # reference value cross-checked against scipy.stats.hypergeom.cdf
    # and scipy.stats.fisher_exact(alternative='less') this run
    assert abs(fisher_2x2(13, 32, 41, 40) - 0.014202) < 1e-5
    assert abs(fisher_2x2(13, 32, 41, 48) - 0.040932) < 1e-5
    assert abs(fisher_2x2(5, 10, 21, 22) - 0.231419) < 1e-5
    # cohort builder on synthetic series
    from datetime import datetime, timedelta
    base = datetime(2026, 1, 1)
    syn = [
        ('A', 'LONG', -1.0, 'hard_max_loss', base, base + timedelta(minutes=10)),
        ('A', 'LONG',  2.0, 'profit-monster-trail', base + timedelta(minutes=100), base + timedelta(minutes=130)),
        ('A', 'SHORT', -1.0, 'atr_sl_hit', base + timedelta(minutes=160), base + timedelta(minutes=180)),
        ('B', 'LONG',  1.0, 'hard_tp', base, base + timedelta(minutes=5)),
        ('B', 'LONG',  1.0, 'hard_tp', base + timedelta(minutes=20), base + timedelta(minutes=30)),
        ('C', 'SHORT', -1.0, 'atr_sl_hit', base, base + timedelta(minutes=10)),
        ('C', 'LONG',  1.5, 'atr_trail_hit', base + timedelta(minutes=50), base + timedelta(minutes=70)),
    ]
    co = cohorts(syn, 120.0)
    assert len(co['same_after_loss']) == 1, co
    assert len(co['same_after_win']) == 1, co
    assert len(co['flip_after_loss']) == 1, co
    assert len(co['flip_after_win']) == 1, co
    assert len(co['same_after_be']) == 0, co
    # gap boundary: gap == exactly max counts, gap > max is excluded
    syn2 = [('D', 'LONG', -1.0, 'hard_max_loss', base, base + timedelta(minutes=10)),
            ('D', 'LONG', 1.0, 'hard_tp', base + timedelta(minutes=130), base + timedelta(minutes=140))]
    assert len(cohorts(syn2, 120.0)['same_after_loss']) == 1
    assert len(cohorts(syn2, 119.0)['same_after_loss']) == 0
    assert len(cohorts(syn2, 119.0)['excluded_gap']) == 1
    # breakeven prior must NOT be folded into the win control
    syn3 = [('E', 'LONG', 0.0, 'manual_close', base, base + timedelta(minutes=10)),
            ('E', 'LONG', 1.0, 'hard_tp', base + timedelta(minutes=40), base + timedelta(minutes=50))]
    co3 = cohorts(syn3, 120.0)
    assert len(co3['same_after_be']) == 1 and len(co3['same_after_win']) == 0, co3
    # overlapping (negative-gap) pair excluded and counted, not binned
    syn4 = [('F', 'LONG', -1.0, 'atr_sl_hit', base, base + timedelta(minutes=60)),
            ('F', 'LONG', 1.0, 'hard_tp', base + timedelta(minutes=30), base + timedelta(minutes=70))]
    co4 = cohorts(syn4, 120.0)
    assert len(co4['excluded_overlap']) == 1 and len(co4['same_after_loss']) == 0, co4
    print("SELF-CHECK PASS")
    return True


def verdict(res):
    # honesty: the 120m window was chosen AFTER seeing the bucket table in this
    # same session, so two gap cells are tested -> Bonferroni alpha 0.025.
    checks = {
        'n>=20 (30d)': res['n30']['n'] >= 20,
        'fisher<0.025 (Bonferroni x2 gap cells)': res['n30']['fisher'] < 0.025,
        '14d same sign (pnl<0)': res['n14']['p'] < 0,
        '7d same sign (pnl<0)': res['n7']['p'] < 0,
        'fk<20%': res['n30']['fk'] < 20.0,
    }
    for k, v in checks.items():
        print(f"  {'PASS' if v else 'FAIL'}  {k}")
    print("SHIP" if all(checks.values()) else "REJECT-WITH-DATA")
    return all(checks.values())


if __name__ == '__main__':
    if '--selfcheck' in sys.argv:
        selfcheck()
        sys.exit(0)
    print("H: same-dir re-entry after same-coin loss is worse than after win")
    print("BAR: n>=20(30d) AND fisher<0.025 Bonferroni(2 gap cells) "
          "AND 7d/14d same sign AND fk<20%")
    for gap in (120.0, 720.0):
        print(f"\n##### GAP <= {gap:.0f}m #####")
        res = {'n30': run(30, gap), 'n14': run(14, gap), 'n7': run(7, gap)}
        print("\n== VERDICT (gap<=%.0fm) ==" % gap)
        verdict(res)
