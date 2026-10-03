#!/usr/bin/env python3
"""STATISTICIAN pass 4 — per-signal date-split + regime-gate counterfactual check."""
import math
import sys
from collections import defaultdict
from datetime import timedelta

import psycopg2

sys.path.insert(0, "/root/.hermes/scripts")
from _secrets import BRAIN_DB_DICT  # noqa: E402


def norm_cdf(x):
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def wilson_ci(wins, n, z=1.96):
    if n == 0:
        return (0.0, 0.0)
    p = wins / n
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    half = (z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / denom
    return (max(0.0, center - half), min(1.0, center + half))


conn = psycopg2.connect(**BRAIN_DB_DICT)
cur = conn.cursor()
cur.execute("SELECT MAX(open_time) FROM trades WHERE open_time IS NOT NULL")
max_ts = cur.fetchone()[0]
cutoff = max_ts - timedelta(days=30)

cur.execute("""
    SELECT signal, direction, volatility_regime, pnl_usdt, open_time, status
    FROM trades
    WHERE open_time >= %s AND pnl_usdt IS NOT NULL
      AND status NOT IN ('OPEN','open','PENDING','pending','CANCELLED','cancelled')
""", (cutoff,))
rows = cur.fetchall()
conn.close()

# mid-window date: check if winners cluster in first half (possible filter change)
mid = cutoff + (max_ts - cutoff) / 2
print(f"window {cutoff.date()} .. {max_ts.date()}, mid={mid.date()}")

FAMS = ["volume-breakout", "open_skies", "open-skies", "doji", "rr-struct", "bb_bounce",
        "bb-bounce", "pump_chain", "pump-chain", "pump-chain+", "ema300_dip", "ema300-dip",
        "pullback-entry", "mover", "coiled_spring", "sma20_dip", "slow_grind", "trend_purity"]

print(f"\n{'signal/family':<28} {'half':<6} {'n':>4} {'W':>3} {'WR%':>6} {'PnL':>8} {'first':<12} {'last':<12}")
for fam in FAMS:
    sub = [r for r in rows if r[0] and fam in r[0].lower().replace("-", "_").replace("+", "")]
    if len(sub) < 6:
        continue
    first_ts = min(r[4] for r in sub)
    last_ts = max(r[4] for r in sub)
    for label, sel in [("early", [r for r in sub if r[4] < mid]),
                       ("late", [r for r in sub if r[4] >= mid])]:
        if not sel:
            continue
        ps = [float(r[3]) for r in sel]
        nw = sum(1 for p in ps if p > 0)
        nd = sum(1 for p in ps if p != 0)
        tp = sum(ps)
        print(f"{fam:<28} {label:<6} {len(sel):>4} {nw:>3} {nw/nd*100 if nd else 0:>5.1f}% {tp:>+8.2f} "
              f"{first_ts.date():<12} {last_ts.date():<12}")
    print()

# Regime-gate check: EXTREME-long families that volatility_gate blocks.
# If EXTREME LONG trades that DID execute are profitable, and the same families
# have positive PnL in EXTREME, blocked EXTREME trades were plausibly winners too.
print("=" * 70)
print("EXTREME-LONG: which signal families made the +5.24?")
print("=" * 70)
ext = [r for r in rows if (r[2] or "").upper() == "EXTREME" and (r[1] or "").upper() == "LONG"]
by_fam = defaultdict(list)
for r in ext:
    sig = (r[0] or "?").split(",")[0].strip().lower().replace("-", "_").rstrip("+-")
    by_fam[sig].append(float(r[3]))
for fam, ps in sorted(by_fam.items(), key=lambda x: -sum(x[1])):
    if len(ps) < 3:
        continue
    nw = sum(1 for p in ps if p > 0)
    print(f"  {fam:<30} n={len(ps):<4} WR={nw/len(ps)*100:>5.1f}%  PnL={sum(ps):>+7.2f}")

small = [(f, p) for f, ps in by_fam.items() if len(ps) < 3 for p in ps]
print(f"  (families with n<3 combined: n={len(small)}, PnL={sum(p for _, p in small):+.2f})")

# pump-chain detail: the two biggest-n signals
print("\n" + "=" * 70)
print("PUMP-CHAIN DETAIL (largest-n signal family)")
print("=" * 70)
for direction in ["LONG", "SHORT"]:
    sub = [r for r in rows if r[0] and "pump" in r[0].lower() and "chain" in r[0].lower()
           and (r[1] or "").upper() == direction]
    for reg in ["EXTREME", "HIGH", "NORMAL"]:
        s2 = [r for r in sub if (r[2] or "").upper() == reg]
        if not s2:
            continue
        ps = [float(r[3]) for r in s2]
        nw = sum(1 for p in ps if p > 0)
        nd = sum(1 for p in ps if p != 0)
        lo, hi = wilson_ci(nw, nd)
        print(f"  {direction} {reg:<8} n={len(s2):<4} WR={nw/nd*100 if nd else 0:>5.1f}% "
              f"CI[{lo*100:.1f}-{hi*100:.1f}] PnL={sum(ps):>+7.2f}")

# Tuesday / night-session detail: is it concentrated in specific signals?
print("\n" + "=" * 70)
print("TUESDAY + 02-06 UTC: which signals drove the loss?")
print("=" * 70)
tue = [r for r in rows if r[4].strftime("%A") == "Tuesday"]
night = [r for r in rows if 2 <= r[4].hour <= 5]
for label, sub in [("Tuesday", tue), ("02-06 UTC", night)]:
    by_fam = defaultdict(list)
    for r in sub:
        sig = (r[0] or "?").split(",")[0].strip().lower().replace("-", "_").rstrip("+-")
        by_fam[sig].append(float(r[3]))
    print(f"\n{label} (n={len(sub)}, PnL={sum(float(r[3]) for r in sub):+.2f}) — worst families:")
    for fam, ps in sorted(by_fam.items(), key=lambda x: sum(x[1]))[:8]:
        if len(ps) < 2:
            continue
        nw = sum(1 for p in ps if p > 0)
        print(f"  {fam:<28} n={len(ps):<4} WR={nw/len(ps)*100:>5.1f}%  PnL={sum(ps):>+7.2f}")

# Multiple-comparison awareness: distribution of bucket PnLs for 24 hours
print("\n" + "=" * 70)
print("MULTIPLE-COMPARISON CHECK: hour-bucket PnL dispersion")
print("=" * 70)
by_hour = defaultdict(list)
for r in rows:
    by_hour[r[4].hour].append(float(r[3]))
hour_pnls = []
for h in range(24):
    ps = by_hour.get(h, [])
    if ps:
        hour_pnls.append((h, sum(ps), len(ps)))
pnl_only = sorted(x[1] for x in hour_pnls)
print(f"worst 3 hours: {[(h, round(p,2), n) for h, p, n in sorted(hour_pnls, key=lambda x: x[1])[:3]]}")
print(f"best 3 hours:  {[(h, round(p,2), n) for h, p, n in sorted(hour_pnls, key=lambda x: -x[1])[:3]]}")
neg = sum(1 for p in pnl_only if p < 0)
print(f"hours negative: {neg}/24 — with a ~zero edge and 24 buckets, expect roughly half negative by chance")
print("→ hour-of-day findings are EXPLORATORY, not significant without correction")

print("\nDONE")
