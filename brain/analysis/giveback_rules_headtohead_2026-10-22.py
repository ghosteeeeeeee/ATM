#!/usr/bin/env python3
"""brain_auditor #82 — candle OOS for EXT #44 (peak-trail) AND the new
breakeven-at-entry rule, head-to-head on the ARM-GAP giveback cohort.

COHORT (matches ARM-GAP instrumentation, position_manager.py:1336):
  30d closed trades with candle-walked MFE >= +0.40% AND trailing_activated = FALSE
  (PM trail never armed — bypass exit engines: pump-exit / rr_engine / volbo / hl_fill).

RULES COMPARED (each is a single exit => fees equal vs actual):
  ACTUAL      — what really happened (price pp = pnl_pct / leverage; $ = pnl_usdt)
  BE          — after reaching +0.40% favorable, if price ever returns to ENTRY,
                exit at entry (0 price pp). [brain_auditor #82 new idea]
  PEAK-TRAIL  — EXT #44: after arm, stop = running_peak * (1 - 0.003) for LONG /
                running_trough * (1 + 0.003) for SHORT; exit at first touch of stop.
                Uses real candle path, not the static mfe_price estimate.
"""
import psycopg2, sqlite3, datetime, statistics
from collections import defaultdict
from math import comb

ARM = 0.40
TRAIL_D = 0.003

conn = psycopg2.connect(host='/var/run/postgresql', database='brain', user='postgres')
cur = conn.cursor()
cur.execute("""
    SELECT id, token, direction, entry_price, pnl_pct, pnl_usdt, leverage,
           open_time, close_time, COALESCE(signal,'(none)'), COALESCE(exit_reason,'(none)'),
           trailing_activated, COALESCE(volatility_regime,'')
    FROM trades WHERE status='closed' AND close_time > NOW() - INTERVAL '30 days'
    ORDER BY open_time
""")
rows = cur.fetchall(); conn.close()
db = sqlite3.connect('file:/root/.hermes/data/candles.db?mode=ro', uri=True)

recs = []
for (tid, tok, direc, entry, pnl_pct, pnl_usdt, lev, ot, ct, sig, exr, trail, vol) in rows:
    if trail:
        continue
    entry = float(entry); lev = float(lev or 1)
    ts0 = int(ot.replace(tzinfo=datetime.timezone.utc).timestamp())
    ts1 = int(ct.replace(tzinfo=datetime.timezone.utc).timestamp())
    c = list(db.execute("SELECT high, low FROM candles_1m WHERE token=? AND ts>=? AND ts<=? ORDER BY ts",
                        (tok, ts0, ts1 + 60)))
    if not c:
        continue
    arm_i = None; be_px = None; pt_px = None
    peak = entry
    for i, (hi, lo) in enumerate(c):
        if direc == 'LONG':
            fav = (hi / entry - 1) * 100
            if arm_i is None and fav >= ARM:
                arm_i = i
            if arm_i is not None and i >= arm_i:
                peak = max(peak, hi)
                stop = peak * (1 - TRAIL_D)
                if be_px is None and lo <= entry:
                    be_px = entry
                if pt_px is None and lo <= stop:
                    pt_px = stop
                    # trail stop can never sit below entry+~0.1% at arm; keep going only if unset
        else:
            fav = (1 - lo / entry) * 100
            if arm_i is None and fav >= ARM:
                arm_i = i
            if arm_i is not None and i >= arm_i:
                peak = min(peak, lo)
                stop = peak * (1 + TRAIL_D)
                if be_px is None and hi >= entry:
                    be_px = entry
                if pt_px is None and hi >= stop:
                    pt_px = stop
        if be_px is not None and pt_px is not None:
            break
    if arm_i is None:
        continue  # never reached +0.40 -> not in cohort
    actual_pp = float(pnl_pct) / lev
    be_pp = 0.0 if be_px is not None else actual_pp
    if pt_px is not None:
        pt_pp = (pt_px / entry - 1) * 100 if direc == 'LONG' else (1 - pt_px / entry) * 100
    else:
        pt_pp = actual_pp
    recs.append(dict(tid=tid, tok=tok, direc=direc, sig=sig, exr=exr, vol=vol,
                     actual_pp=actual_pp, be_pp=be_pp, pt_pp=pt_pp,
                     be=be_px is not None, pt=pt_px is not None, close_t=ct))

def stats(part, label):
    n = len(part)
    if not n:
        print(f"{label}: empty"); return
    a = sum(c['actual_pp'] for c in part)
    b = sum(c['be_pp'] for c in part)
    p_ = sum(c['pt_pp'] for c in part)
    winners = [c for c in part if c['actual_pp'] > 0]
    def nz(deltas):
        d = [x for x in deltas if abs(x) > 1e-9]
        pos = sum(1 for x in d if x > 0); neg = sum(1 for x in d if x < 0)
        if not d: return 0, 1.0
        pv = min(1.0, 2 * sum(comb(pos + neg, k) for k in range(0, min(pos, neg) + 1)) / 2 ** (pos + neg))
        return len(d), pv
    nbe, pbe = nz([c['be_pp'] - c['actual_pp'] for c in part])
    npt, ppt = nz([c['pt_pp'] - c['actual_pp'] for c in part])
    fkb = sum(1 for c in part if c['be'] and c['actual_pp'] > 0)
    fkp = sum(1 for c in part if c['pt'] and c['actual_pp'] > 0)
    print(f"{label:34} n={n:3} actual {a:+8.2f}pp | BE {b:+8.2f} ({b-a:+7.2f}, p={pbe:.5f}, fk {fkb}/{n}) "
          f"| PEAK-TRAIL {p_:+8.2f} ({p_-a:+7.2f}, p={ppt:.5f}, fk {fkp}/{n})")

print(f"COHORT: unarmed (trailing_activated=FALSE) trades reaching +{ARM:.2f}% favorable, 30d, n={len(recs)}")
stats(recs, "ALL")
anchor = max(c['close_t'] for c in recs)
stats([c for c in recs if c['close_t'] >= anchor - datetime.timedelta(days=7)], "OOS (last 7d)")
stats([c for c in recs if anchor - datetime.timedelta(days=14) <= c['close_t'] < anchor - datetime.timedelta(days=7)],
      "IS (d8-14)")
stats([c for c in recs if anchor - datetime.timedelta(days=21) <= c['close_t'] < anchor - datetime.timedelta(days=14)],
      "d15-21")
# scope-matched (existing ARM-BE scope: non-EXTREME, exclude volume-)
sc = [c for c in recs if 'volume-' not in c['sig'].lower() and c['vol'] != 'EXTREME']
stats(sc, "non-EXTREME excl volume-")

print("\nBy exit_reason (unarmed cohort):")
d = defaultdict(lambda: [0, 0.0, 0.0, 0.0])
for c in recs:
    d[c['exr']][0] += 1
    d[c['exr']][1] += c['actual_pp']
    d[c['exr']][2] += c['be_pp']
    d[c['exr']][3] += c['pt_pp']
for k, (n, a, b, p_) in sorted(d.items(), key=lambda x: (x[1][2] + x[1][3] - 2 * x[1][1])):
    print(f"  {k:26} n={n:3} actual {a:+8.2f} | BE {b:+8.2f} ({b-a:+7.2f}) | PT {p_:+8.2f} ({p_-a:+7.2f})")

print("\nBy signal (top 12 by combined delta):")
s = defaultdict(lambda: [0, 0.0, 0.0, 0.0])
for c in recs:
    s[c['sig']][0] += 1; s[c['sig']][1] += c['actual_pp']; s[c['sig']][2] += c['be_pp']; s[c['sig']][3] += c['pt_pp']
rows2 = sorted(s.items(), key=lambda x: -(x[1][2] + x[1][3] - 2 * x[1][1]))[:12]
for k, (n, a, b, p_) in rows2:
    print(f"  {k[:34]:34} n={n:3} actual {a:+7.2f} | BE {b-a:+7.2f} | PT {p_-a:+7.2f}")

# concentration / sensitivity: drop single largest contributor
for rule in ('be', 'pt'):
    col = f'{rule}_pp'
    deltas = sorted(((c[col] - c['actual_pp'], c['tid'], c['tok']) for c in recs), key=lambda x: -x[0])
    tot = sum(x[0] for x in deltas)
    worst = deltas[-1]
    top3 = sum(x[0] for x in deltas[:3])
    print(f"\n{rule.upper()} sensitivity: total {tot:+.2f}pp | top3 {top3:+.2f} | worst trade {worst} "
          f"| ex-top3 {tot - top3:+.2f} | ex-worst {tot - worst[0]:+.2f}")
