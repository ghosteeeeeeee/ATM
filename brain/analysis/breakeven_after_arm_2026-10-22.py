#!/usr/bin/env python3
"""CREATIVE (brain_auditor #82): BREAKEVEN-AFTER-ARM counterfactual.

Distinct from the BLOCKED trail counterfactual (escalation #17 / #78):
instead of re-trailing givebacks, simply move SL to entry once the trade has
reached +0.40% price-favorable (the same level that arms the trail family).
If price ever returns to entry afterwards, exit at entry (0 price pp).

Cohort: 14d closed trades whose direction-favorable excursion reached +0.40%.
Compare actual (price pp = pnl_pct / leverage) vs counterfactual exit.
Single exit each side => fees equal => raw pp comparison is fair.
"""
import psycopg2, sqlite3, datetime, statistics, sys

ARM = 0.40  # percent price-favorable, matches trail-arm level

conn = psycopg2.connect(host='/var/run/postgresql', database='brain', user='postgres')
cur = conn.cursor()
cur.execute("""
    SELECT id, token, direction, entry_price, pnl_pct, leverage, open_time, close_time,
           signal, exit_reason, trailing_activated, highest_price, lowest_price
    FROM trades
    WHERE status='closed' AND close_time > NOW() - INTERVAL '14 days'
    ORDER BY open_time
""")
trades = cur.fetchall()
conn.close()
db = sqlite3.connect('file:/root/.hermes/data/candles.db?mode=ro', uri=True)

cohort, skipped = [], 0
for (tid, tok, direc, entry, pnl_pct, lev, ot, ct, sig, exr, trail, hp, lp) in trades:
    entry = float(entry)
    if direc == 'LONG':
        fav = (float(hp or 0) / entry - 1) * 100 if hp else None
        hit_arm = fav is not None and fav >= ARM
    else:
        fav = (1 - float(lp or 0) / entry) * 100 if lp else None
        hit_arm = fav is not None and fav >= ARM
    if not hit_arm:
        skipped += 1
        continue
    ts0 = int(ot.replace(tzinfo=datetime.timezone.utc).timestamp())
    ts1 = int(ct.replace(tzinfo=datetime.timezone.utc).timestamp())
    rows = list(db.execute(
        "SELECT high, low FROM candles_1m WHERE token=? AND ts>=? AND ts<=? ORDER BY ts",
        (tok, ts0, ts1 + 60)))
    if not rows:
        skipped += 1
        continue
    armed_at = None
    be_at = None
    for i, (hi, lo) in enumerate(rows):
        fav_now = ((hi / entry - 1) * 100) if direc == 'LONG' else ((1 - lo / entry) * 100)
        if armed_at is None and fav_now >= ARM:
            armed_at = i
            continue
        if armed_at is not None and i > armed_at:
            if direc == 'LONG' and lo <= entry:
                be_at = i
                break
            if direc == 'SHORT' and hi >= entry:
                be_at = i
                break
    actual_pp = float(pnl_pct) / float(lev or 1)   # price percent
    if be_at is not None:
        cf_pp = 0.0  # exited at entry
        helped = cf_pp - actual_pp
    else:
        cf_pp = actual_pp  # never touched entry again -> identical outcome
        helped = 0.0
    cohort.append(dict(tid=tid, tok=tok, direc=direc, sig=sig or '(none)', exr=exr,
                       actual=actual_pp, cf=cf_pp, delta=helped,
                       be=be_at is not None, trail=bool(trail),
                       dur=(ct - ot).total_seconds() / 60.0, close_t=ct))

n = len(cohort)
act = sum(c['actual'] for c in cohort)
cf = sum(c['cf'] for c in cohort)
be_n = sum(1 for c in cohort if c['be'])
helped = [c for c in cohort if c['delta'] > 1e-9]
harmed = [c for c in cohort if c['delta'] < -1e-9]
print(f"Cohort: {n} trades reached +{ARM:.2f}% favorable (14d); skipped {skipped}")
print(f"actual total  {act:+.2f} pp")
print(f"BE-after-arm  {cf:+.2f} pp   delta {cf - act:+.2f} pp")
print(f"breakeven exit fired on {be_n}/{n}")
print(f"helped (actual<0, BE saves): {len(helped)}  sum {sum(c['delta'] for c in helped):+.2f} pp")
print(f"harmed (winner cut to 0):    {len(harmed)}  sum {sum(c['delta'] for c in harmed):+.2f} pp")
print(f"winner-kill rate: {len(harmed)}/{n} = {100.0*len(harmed)/n:.1f}% of cohort, "
      f"{len(harmed)}/{sum(1 for c in cohort if c['actual']>0)} of actual winners")
print("\nTop harmed (actual winners turned to 0):")
for c in sorted(harmed, key=lambda x: x['delta'])[:10]:
    print(f"  #{c['tid']} {c['tok']} {c['direc']} {c['sig'][:28]:28} actual {c['actual']:+.3f}pp "
          f"{c['exr'][:20]:20} dur {c['dur']:.0f}m trail={c['trail']}")
print("\nTop helped (givebacks saved at breakeven):")
for c in sorted(helped, key=lambda x: -x['delta'])[:10]:
    print(f"  #{c['tid']} {c['tok']} {c['direc']} {c['sig'][:28]:28} actual {c['actual']:+.3f}pp "
          f"{c['exr'][:20]:20} dur {c['dur']:.0f}m trail={c['trail']}")

# OOS split: first 7d of the 14d window vs last 7d
import datetime as dt
cut = dt.timedelta(days=7)
anchor = max(c['close_t'] for c in cohort)
in_sample = [c for c in cohort if c['close_t'] >= anchor - cut]
oos = [c for c in cohort if c['close_t'] < anchor - cut]
for lbl, part in (('IS (last 7d)', in_sample), ('OOS (d7-14)', oos)):
    a = sum(c['actual'] for c in part); b = sum(c['cf'] for c in part)
    hk = sum(1 for c in part if c['delta'] < -1e-9)
    print(f"  {lbl}: n={len(part)} actual {a:+.2f} vs BE {b:+.2f} = {b-a:+.2f} pp, winner-kills {hk}")
print("\nBy trailing_activated:")
for t in (True, False):
    part = [c for c in cohort if c['trail'] == t]
    if not part: continue
    a = sum(c['actual'] for c in part); b = sum(c['cf'] for c in part)
    print(f"  trail={t}: n={len(part)} actual {a:+.2f} vs BE {b:+.2f} = {b-a:+.2f} pp")
print("\nBy exit_reason (delta pp):")
from collections import defaultdict
d = defaultdict(lambda: [0, 0.0])
for c in cohort:
    d[c['exr']][0] += 1
    d[c['exr']][1] += c['delta']
for k, (cnt, s) in sorted(d.items(), key=lambda x: x[1][1]):
    print(f"  {k:24} n={cnt:3} delta {s:+.2f} pp")
