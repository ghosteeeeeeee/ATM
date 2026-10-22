#!/usr/bin/env python3
"""brain_auditor #82 — BREAKEVEN-AFTER-ARM counterfactual, 3 variants.

A) ARM-BE, EXISTING SHADOW SCOPE (non-EXTREME, exclude 'volume-') — independent
   replication of the shipped ARM-BE-STOP shadow verdict (arm-breakeven-stop.md,
   2026-10-17: 30d, fk 9.7%, net +$3.46).
B) UNARMED-GIVEBACK (NEW idea) — same +0.40% favorable, price returns to entry,
   but the PM trail never armed (bypass exit engines: pump-exit / rr_engine /
   volbo / hl_fill). Real-time observable: trailing not armed at entry-cross.
C) ALL (arm-independent) — the naive rule.

Counterfactual exits AT entry => 0 price pp => pnl_usdt 0 for that trade.
Single exit each side, fees equal. Actual price pp = pnl_pct / leverage.
"""
import psycopg2, sqlite3, datetime, math, statistics
from collections import defaultdict

ARM = 0.40
conn = psycopg2.connect(host='/var/run/postgresql', database='brain', user='postgres')
cur = conn.cursor()
cur.execute("""
    SELECT id, token, direction, entry_price, pnl_pct, pnl_usdt, amount_usdt, leverage,
           open_time, close_time, COALESCE(signal,'(none)'), COALESCE(exit_reason,'(none)'),
           trailing_activated, COALESCE(volatility_regime,''), amount_usdt
    FROM trades WHERE status='closed' AND close_time > NOW() - INTERVAL '30 days'
    ORDER BY open_time
""")
rows = cur.fetchall(); conn.close()
db = sqlite3.connect('file:/root/.hermes/data/candles.db?mode=ro', uri=True)

recs = []
for (tid, tok, direc, entry, pnl_pct, pnl_usdt, amt, lev, ot, ct, sig, exr, trail, vol, amt2) in rows:
    entry = float(entry); lev = float(lev or 1); amt = float(amt or 0)
    # verify $ conversion
    implied = amt * float(pnl_pct or 0) / 100.0
    ts0 = int(ot.replace(tzinfo=datetime.timezone.utc).timestamp())
    ts1 = int(ct.replace(tzinfo=datetime.timezone.utc).timestamp())
    cands = list(db.execute(
        "SELECT high, low FROM candles_1m WHERE token=? AND ts>=? AND ts<=? ORDER BY ts",
        (tok, ts0, ts1 + 60)))
    if not cands:
        continue
    maxfav = 0.0; be_at = None; armed_at = None
    for i, (hi, lo) in enumerate(cands):
        fav = ((hi / entry - 1) * 100) if direc == 'LONG' else ((1 - lo / entry) * 100)
        if fav > maxfav:
            maxfav = fav
        if armed_at is None and fav >= ARM:
            armed_at = i
            continue
        if armed_at is not None and i > armed_at:
            if direc == 'LONG' and lo <= entry:
                be_at = i; break
            if direc == 'SHORT' and hi >= entry:
                be_at = i; break
    recs.append(dict(tid=tid, tok=tok, direc=direc, sig=sig, exr=exr, vol=vol,
                     trail=bool(trail), maxfav=maxfav, be=(be_at is not None),
                     armed_walk=(armed_at is not None),
                     actual_pp=float(pnl_pct) / lev, actual_usd=float(pnl_usdt or 0),
                     amt=amt, lev=lev, close_t=ct,
                     im_err=abs(implied - float(pnl_usdt or 0)) if pnl_pct else 0.0))

print(f"30d closed trades walked: {len(recs)}; median |$implied-actual| = "
      f"{statistics.median(r['im_err'] for r in recs):.4f} USDT (conversion sanity)")

def run(label, part):
    part = [c for c in part if c['maxfav'] >= ARM]
    if not part:
        print(f"{label}: empty"); return
    n = len(part)
    cf_part = [c for c in part if c['be']]
    a_pp = sum(c['actual_pp'] for c in part)
    # counterfactual: 0 pp for round-trippers, actual otherwise
    cf_pp = sum(0.0 if c['be'] else c['actual_pp'] for c in part)
    a_usd = sum(c['actual_usd'] for c in part)
    cf_usd = sum(0.0 if c['be'] else c['actual_usd'] for c in part)
    killers = [c for c in cf_part if c['actual_pp'] > 0]
    winners = [c for c in part if c['actual_pp'] > 0]
    fk = 100.0 * len(killers) / len(winners) if winners else 0.0
    d = [(-c['actual_pp'] if c['be'] and c['actual_pp'] > 0 else (0.0 - c['actual_pp'] if c['be'] else 0.0)) for c in part]
    nz = [x for x in d if abs(x) > 1e-9]
    pos = sum(1 for x in nz if x > 0); neg = sum(1 for x in nz if x < 0)
    from math import comb
    p = min(1.0, 2 * sum(comb(pos + neg, k) for k in range(0, min(pos, neg) + 1)) / 2 ** (pos + neg)) if nz else 1.0
    print(f"{label:44} n={n:4} BE-fires={len(cf_part):3} | actual {a_pp:+8.2f}pp ${a_usd:+.2f} "
          f"-> BE {cf_pp:+8.2f}pp ${cf_usd:+.2f} | delta ${cf_usd - a_usd:+.2f} ({cf_pp - a_pp:+.2f}pp) "
          f"| fk {len(killers)}/{len(winners)}={fk:.1f}% | sign-p={p:.5f}")
    return dict(n=n, delta_usd=cf_usd - a_usd, fk=fk, p=p, fires=len(cf_part))

def scope(c):
    return ('volume-' not in c['sig'].lower()) and (c['vol'] != 'EXTREME')

print("\n== A) ARM-BE under EXISTING SHADOW SCOPE (non-EXTREME, exclude volume-) ==")
run("A1 30d armed(=trailing_activated)", [c for c in recs if c['trail'] and scope(c)])
run("A2 30d armed(candle-arm observed)", [c for c in recs if c['armed_walk'] and scope(c)])
run("A3 14d armed(=trailing_activated)", [c for c in recs if c['trail'] and scope(c)
                                          and c['close_t'] >= max(r['close_t'] for r in recs) - datetime.timedelta(days=14)])
print("\n== B) UNARMED-GIVEBACK (NEW) ==")
run("B1 30d unarmed(=NOT trailing_activated)", [c for c in recs if not c['trail']])
run("B1s 30d unarmed + same scope", [c for c in recs if not c['trail'] and scope(c)])
run("B2 14d unarmed", [c for c in recs if not c['trail']
                       and c['close_t'] >= max(r['close_t'] for r in recs) - datetime.timedelta(days=14)])
run("B3 7d unarmed (OOS half)", [c for c in recs if not c['trail']
                                 and c['close_t'] >= max(r['close_t'] for r in recs) - datetime.timedelta(days=7)])
run("B4 d8-14 unarmed (IS half)", [c for c in recs if not c['trail']
                                   and max(r['close_t'] for r in recs) - datetime.timedelta(days=14)
                                   <= c['close_t'] < max(r['close_t'] for r in recs) - datetime.timedelta(days=7)])
print("\n== C) ARM-INDEPENDENT (naive) ==")
run("C1 30d all", recs)

# unarmed breakdown
un = [c for c in recs if not c['trail'] and c['maxfav'] >= ARM]
d = defaultdict(lambda: [0, 0.0, 0.0])
for c in un:
    key = (c['exr'], )
    d[key][0] += 1
    d[key][1] += c['actual_usd']
    d[key][2] += 0.0 if c['be'] else c['actual_usd']
print("\n30d UNARMED by exit_reason (n, actual$, BE$):")
for k, (n, a, b) in sorted(d.items(), key=lambda x: x[1][2] - x[1][1]):
    print(f"  {k[0]:26} n={n:3} actual {a:+7.2f} -> BE {b:+7.2f}  delta {b-a:+7.2f}")
s = defaultdict(lambda: [0, 0.0, 0.0])
for c in un:
    s[c['sig']][0] += 1; s[c['sig']][1] += c['actual_usd']; s[c['sig']][2] += 0.0 if c['be'] else c['actual_usd']
print("\n30d UNARMED by signal (n, actual$ -> BE$ delta):")
for k, (n, a, b) in sorted(s.items(), key=lambda x: -(x[1][2] - x[1][1])):
    print(f"  {k[:36]:36} n={n:3} {a:+7.2f} -> {b:+7.2f}  {b-a:+7.2f}")
