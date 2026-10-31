#!/usr/bin/env python3
"""Forensic: was the CLAIMED table computed on a book whose candle data was
still incomplete (run-time truncation)?  Replays the claim's 45-trade cohort
with candles truncated at candidate run times T and scores against the claim."""
import sys
import sqlite3
import datetime as dt

sys.path.insert(0, '/root/.hermes/analysis')
import mfe_audit_replay as M

CLAIM = dict(pm_actual=-12.20, bg=-68.03, mfe30=29.63, mfe30a040=27.18,
             pmwalk=26.37, pm_mfe30=30.89, pm_mfe30a=28.65)
STRATS = [k for k in CLAIM if k != 'pm_actual']

trades = M.load_trades()
by_close = sorted(trades, key=lambda t: t['close_t'])
cohort = by_close[:45]
print("cohort n =", len(cohort),
      "first close", cohort[0]['close_t'], "last close", cohort[-1]['close_t'])
print("excluded (46th..):", [(t['id'], str(t['close_t'])) for t in by_close[45:]])

# candles cached fully, then sliced by T
full_cache = M.candles_cache(trades)


def agg_at(T):
    """aggregates for cohort with candles ts < T"""
    out = {}
    for s in STRATS:
        tot = 0.0
        for t in cohort:
            # only bars that had CLOSED before run-time T existed as is_closed=1
            c = [r for r in full_cache[t['id']] if r[0] + 300 <= T]
            px, xts, tag = M.walk(t, c, s)
            if px is None:
                tot = None
                break
            tot += M.pnl_pct(t['dir'], t['entry'], px) * t['lev']
        out[s] = tot
    out['pm_actual'] = sum(t['pnl'] for t in cohort)
    return out


base = dt.datetime(2026, 10, 31, 0, 0, tzinfo=dt.timezone.utc)
print(f"\n{'run-time T (UTC)':<20}" + "".join(f"{k:>11}" for k in STRATS)
      + f"{'rms-err':>9}")
print(f"{'CLAIM':<20}" + "".join(f"{CLAIM[k]:>+11.2f}" for k in STRATS))
best = None
t = dt.datetime(2026, 10, 31, 15, 0, tzinfo=dt.timezone.utc)
while t <= dt.datetime(2026, 10, 31, 19, 0, tzinfo=dt.timezone.utc):
    T = int(t.timestamp())
    vals = agg_at(T)
    if any(v is None for v in vals.values()):
        t += dt.timedelta(minutes=5)
        continue
    err = (sum((vals[k] - CLAIM[k]) ** 2 for k in STRATS) / len(STRATS)) ** 0.5
    if best is None or err < best[0]:
        best = (err, t, dict(vals))
    if err < 3.0:
        print(f"{t.strftime('%Y-%m-%d %H:%M'):<20}"
              + "".join(f"{vals[k]:>+11.2f}" for k in STRATS) + f"{err:>9.3f}")
    t += dt.timedelta(minutes=5)

print("\nbest:", best[1].strftime('%Y-%m-%d %H:%M'), "rms-err", round(best[0], 3))
for k in STRATS:
    print(f"   {k:<12} at best-T {best[2][k]:>+8.2f}  claim {CLAIM[k]:>+8.2f}")

# and the exact numbers with NO truncation (complete data) on the same 45
print("\nno truncation (complete candles today), same 45-trade cohort:")
vals = {}
for s in STRATS:
    tot = 0.0
    for t in cohort:
        px, xts, tag = M.walk(t, full_cache[t['id']], s)
        tot += M.pnl_pct(t['dir'], t['entry'], px) * t['lev']
    vals[s] = tot
for k in STRATS:
    print(f"   {k:<12} {vals[k]:>+8.2f}   claim {CLAIM[k]:>+8.2f}   "
          f"diff {vals[k]-CLAIM[k]:+8.2f}")
