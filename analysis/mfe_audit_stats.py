#!/usr/bin/env python3
"""Statistical honesty checks on the claim's 45-trade cohort:
sign tests, iid bootstrap, token-cluster bootstrap, fee math, horizon status."""
import math
import random
import sys
import datetime as dt
from collections import defaultdict

sys.path.insert(0, '/root/.hermes/analysis')
import mfe_audit_replay as M

random.seed(31102026)
trades = M.load_trades()
by_close = sorted(trades, key=lambda t: t['close_t'])
cohort = by_close[:45]
cache = M.candles_cache(trades)

vals = defaultdict(dict)
for t in cohort:
    vals[t['id']]['actual'] = t['pnl']
    vals[t['id']]['tok'] = t['token']
    for s in ('bg', 'mfe30', 'mfe30a040', 'pmwalk', 'pm_mfe30'):
        px, xts, tag = M.walk(t, cache[t['id']], s)
        vals[t['id']][s] = M.pnl_pct(t['dir'], t['entry'], px) * t['lev']
        vals[t['id']][s + '_tag'] = tag

ids = [t['id'] for t in cohort]
mfe = [vals[i]['mfe30'] for i in ids]
bg = [vals[i]['bg'] for i in ids]
act = [vals[i]['actual'] for i in ids]

print(f"cohort n = {len(ids)}")
for name, v in (('mfe30', mfe), ('bg', bg), ('pm_actual', act)):
    w = sum(1 for x in v if x > 0.05)
    l = sum(1 for x in v if x < -0.05)
    print(f"  {name:<9} net={sum(v):+8.2f}  WR={w/(w+l)*100:.0f}% (W{w}/L{l})")

d_bg = [a - b for a, b in zip(mfe, bg)]
d_ac = [a - b for a, b in zip(mfe, act)]


def sign_test(diffs, label):
    pos = sum(1 for d in diffs if d > 1e-9)
    neg = sum(1 for d in diffs if d < -1e-9)
    n = pos + neg
    k = min(pos, neg)
    p = min(1.0, 2 * sum(math.comb(n, i) for i in range(0, k + 1)) / 2 ** n)
    print(f"  sign test {label:<26} +{pos}/-{neg} n={n} two-sided p={p:.4f}")
    return p


def boot(v, B=20000):
    n = len(v)
    out = sorted(sum(v[random.randrange(n)] for _ in range(n)) for _ in range(B))
    return out[int(.025 * B)], out[int(.975 * B)]


def cluster_boot(pairs, B=20000):
    """resample TOKEN clusters with replacement (4 tokens)"""
    by_tok = defaultdict(list)
    for tok, v in pairs:
        by_tok[tok].append(v)
    toks = list(by_tok)
    out = []
    for _ in range(B):
        s = 0.0
        for _ in range(len(toks)):
            tk = toks[random.randrange(len(toks))]
            s += sum(by_tok[tk])
        out.append(s)
    out.sort()
    return out[int(.025 * B)], out[int(.975 * B)]


print("\n--- paired tests (mfe30 vs alternatives, claim's 45) ---")
sign_test(d_bg, "mfe30 vs bg")
sign_test(d_ac, "mfe30 vs pm_actual")

print("\n--- iid bootstrap 95% CI (per-trade resample) ---")
for label, v in (('mfe30 net', mfe), ('mfe30-bg delta', d_bg),
                 ('mfe30-pm_actual delta', d_ac), ('bg net', bg)):
    lo, hi = boot(v)
    print(f"  {label:<26} point={sum(v):+8.2f}  95% CI [{lo:+.2f}, {hi:+.2f}]")

print("\n--- token-cluster bootstrap 95% CI (resample 4 token clusters) ---")
pairs_mfe = [(vals[i]['tok'], vals[i]['mfe30']) for i in ids]
pairs_dbg = [(vals[i]['tok'], vals[i]['mfe30'] - vals[i]['bg']) for i in ids]
pairs_dac = [(vals[i]['tok'], vals[i]['mfe30'] - vals[i]['actual']) for i in ids]
for label, pr in (('mfe30 net', pairs_mfe), ('mfe30-bg delta', pairs_dbg),
                  ('mfe30-pm_actual delta', pairs_dac)):
    lo, hi = cluster_boot(pr)
    print(f"  {label:<26} 95% CI [{lo:+.2f}, {hi:+.2f}]")

print("\n--- token composition ---")
ct = defaultdict(int)
for i in ids:
    ct[vals[i]['tok']] += 1
print("  ", dict(ct))

print("\n--- clustering in time (entries within 15 min of another entry) ---")
opens = sorted(t['open_t'] for t in cohort)
close_clu = 0
for a, b in zip(opens, opens[1:]):
    if (b - a).total_seconds() <= 900:
        close_clu += 1
print(f"   {close_clu}/{len(opens)-1} consecutive pairs open within 15 min")

print("\n--- horizon status of the 45 ---")
now = dt.datetime.now(dt.timezone.utc)
not_yet = [t['id'] for t in cohort if t['open_t'].replace(tzinfo=dt.timezone.utc)
           + dt.timedelta(hours=12) > now]
print(f"   open+12h still in the future: {len(not_yet)} -> {not_yet}")
print(f"   bg timeouts among them: "
      f"{[i for i in not_yet if vals[i]['bg_tag'] == 'timeout']}")
print(f"   mfe30 timeouts among them: "
      f"{[i for i in not_yet if vals[i]['mfe30_tag'] == 'timeout']}")
for i in not_yet:
    print(f"     id={i} {vals[i]['tok']} open+12h elapsed? NO | "
          f"bg={vals[i]['bg']:+.2f} ({vals[i]['bg_tag']}) "
          f"mfe30={vals[i]['mfe30']:+.2f} ({vals[i]['mfe30_tag']})")

print("\n--- fee arithmetic ---")
notional_side = 0.045 / 100            # HL taker, % of notional per side
rt_price = notional_side * 2           # 0.09% of notional round trip
at_lev = rt_price * 5                  # as % of margin (pnl_pct units)
print(f"   taker/side 0.045% of notional -> round trip {rt_price*100:.3f}% of notional")
print(f"   at 5x -> {at_lev*100:.2f}% of margin (= pnl_pct units) per round trip")
print(f"   mfe30 net {sum(mfe):+.2f} -> after fees {sum(mfe)-0.45*len(ids):+.2f}")
print(f"   bg net    {sum(bg):+.2f} -> after fees {sum(bg)-0.45*len(ids):+.2f}")
print(f"   pm_actual {sum(act):+.2f} -> after fees {sum(act)-0.45*len(ids):+.2f}")

print("\n--- claim deltas ---")
print(f"   claimed: mfe30 +29.63 vs bg -68.03 -> +97.66")
print(f"   mine(45): mfe30 {sum(mfe):+.2f} vs bg {sum(bg):+.2f} -> {sum(mfe)-sum(bg):+.2f}")
print(f"   mine(45): mfe30 {sum(mfe):+.2f} vs pm_actual {sum(act):+.2f} -> {sum(mfe)-sum(act):+.2f}")
print(f"   after 0.45/trade fee (equal n, ranking preserved): "
      f"delta unchanged {sum(mfe)-sum(bg):+.2f}")
