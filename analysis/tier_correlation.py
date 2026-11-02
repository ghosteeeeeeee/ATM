#!/usr/bin/env python3
"""
tier_correlation.py — how closely does the Top-Dog Tracker composite tier
agree with the existing trust-tier system (T1/T2/T3)?  (T 2026-11-01)

Structural fact first: the universes are DISJOINT. copy_trust.json (trust
tiers, written by shadow_mirror.py, consumed by trust_tiers.py/hl_copy) is
92 EVM (0x…) HL-copy wallets; the JUP YOLO leaderboard is 129 Solana
base58 wallets. Address overlap = 0 (different chains), so wallet-level
correlation is impossible by construction. What CAN be measured is whether
the two SCORING PHILOSOPHIES agree when each is applied to the other's data:

  A) Trust universe (92 EVM): dashboard composite over
     (pnl_after_latency, wr, n)  [their universe has no volume field — n
     (activity) substitutes, documented] vs the actual T1/T2/T3 labels.
     -> Spearman rho(score, tier ordinal) + top-10%-vs-T1 overlap.
  B) JUP universe (129 Solana): dashboard composite top-10% (same rule as
     topdog_api.compute_tier) vs a T1-ANALOG rule using their published
     thresholds (copy_trust thresholds: T1 n>=20, wr>=0.65,
     pnl_after_latency>=5 -> jup has realized pnl, no latency, so pnl>=5).
     -> overlap table + median scores both ways.

Report-only; writes stdout (+ brain/verdicts file).
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))
from paths import HERMES_DATA

TRUST_FILE = os.path.join(HERMES_DATA, 'copy_trust.json')
JUP_FILE = os.path.join(HERMES_DATA, 'jup_yolo_leaderboard.json')


def pct_ranks(vals):
    """Best (highest) -> 1.0, average ranks on ties."""
    n = len(vals)
    order = sorted(range(n), key=lambda i: vals[i])
    ranks = [0.0] * n
    i = 0
    while i < n:
        j = i
        while j + 1 < n and vals[order[j + 1]] == vals[order[i]]:
            j += 1
        avg = (i + j) / 2.0          # 0-based average position
        for k in range(i, j + 1):
            ranks[order[k]] = avg / (n - 1) if n > 1 else 0.5
        i = j + 1
    return ranks


def spearman(xs, ys):
    rx, ry = pct_ranks(xs), pct_ranks(ys)
    n = len(xs)
    mx, my = sum(rx) / n, sum(ry) / n
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    den = (sum((a - mx) ** 2 for a in rx) * sum((b - my) ** 2 for b in ry)) ** 0.5
    return num / den if den else 0.0


def composite(rows, metrics):
    """rows: list of dicts; metrics: list of keys. Returns list of scores."""
    pct = {m: pct_ranks([float(r.get(m) or 0) for r in rows]) for m in metrics}
    n = len(rows)
    return [sum(pct[m][i] for m in metrics) / len(metrics) for i in range(n)]


def main():
    trust = json.load(open(TRUST_FILE))
    jup = json.load(open(JUP_FILE))['wallets']

    print("=" * 72)
    print("STRUCTURAL: address-space overlap")
    tset = set(trust['wallets'])
    jset = set(jup)
    print(f"  trust tiers: {len(tset)} wallets (all EVM 0x) | "
          f"jup yolo: {len(jset)} (all Solana base58) | shared: "
          f"{len(tset & jset)}")
    print("  -> wallet-level correlation impossible; measuring scoring "
          "agreement instead\n")

    # ── A) my composite on THEIR universe vs their T1/T2/T3 ──
    trows = []
    for w, v in trust['wallets'].items():
        if not isinstance(v, dict):
            continue
        trows.append({
            'wallet': w,
            'n': float(v.get('n') or 0),
            'wr': float(v.get('wr') or 0),
            'pnl': float(v.get('pnl_after_latency') or 0),
            'tier': str(v.get('tier') or 'T2').upper(),
        })
    scores_a = composite(trows, ('pnl', 'wr', 'n'))
    tier_ord = {'T3': 0, 'T2': 1, 'T1': 2}
    ys = [tier_ord.get(r['tier'], 1) for r in trows]
    rho = spearman(scores_a, ys)

    k = max(1, round(len(trows) * 0.10))
    top_idx = sorted(range(len(trows)), key=lambda i: -scores_a[i])[:k]
    top_set = {trows[i]['wallet'] for i in top_idx}
    t1_set = {r['wallet'] for r in trows if r['tier'] == 'T1'}
    inter = top_set & t1_set
    print("A) DASHBOARD composite (pnl_after_latency, wr, n) on the TRUST "
          "universe vs actual tiers")
    print(f"   n={len(trows)}  tiers: T1={len(t1_set)} "
          f"T2={sum(1 for r in trows if r['tier']=='T2')} "
          f"T3={sum(1 for r in trows if r['tier']=='T3')}")
    print(f"   Spearman(score, tier) rho = {rho:+.3f}")
    print(f"   top-10% ({k}) vs T1 ({len(t1_set)}): overlap {len(inter)} "
          f"— precision {len(inter)/k*100:.0f}%, "
          f"recall {len(inter)/len(t1_set)*100:.0f}%")
    # median score per tier (do their T1s sit at the top of my scoring?)
    for t in ('T1', 'T2', 'T3'):
        s = sorted(sc for sc, r in zip(scores_a, trows) if r['tier'] == t)
        if s:
            print(f"   median composite {t}: {s[len(s)//2]:.3f} "
                  f"(n={len(s)})")
    print()

    # ── B) THEIR rule on MY universe vs my top-10% ──
    th = trust.get('thresholds', {}).get('T1', {})
    min_n = float(th.get('n', 20))
    min_wr = float(th.get('wr', 0.65))
    min_pnl = float(th.get('pnl_after_latency', 5.0))
    jrows = [{'wallet': w, 'n': float(v.get('trades') or 0),
              'wr': float(v.get('wr') or 0),
              'pnl': float(v.get('pnl') or 0)}
             for w, v in jup.items() if isinstance(v, dict)]
    scores_b = composite(jrows, ('pnl', 'wr', 'n'))
    # dashboard tier = same rule as topdog_api (top 10% of eligible, >=10 trades)
    elig = [i for i, r in enumerate(jrows) if r['n'] >= 10]
    elig.sort(key=lambda i: -scores_b[i])
    k2 = max(1, round(len(elig) * 0.10))
    dash_set = {jrows[i]['wallet'] for i in elig[:k2]}
    analog_set = {r['wallet'] for r in jrows
                  if r['n'] >= min_n and r['wr'] >= min_wr
                  and r['pnl'] >= min_pnl}
    inter2 = dash_set & analog_set
    print(f"B) TRUST T1-RULE (n>={min_n:.0f}, wr>={min_wr}, pnl>=${min_pnl:.0f}"
          f" — no-latency caveat) on the JUP universe vs dashboard top-10%")
    print(f"   n={len(jrows)}  T1-analog: {len(analog_set)}  "
          f"dashboard tier: {len(dash_set)}")
    if dash_set or analog_set:
        print(f"   overlap: {len(inter2)} — precision(of dashboard tier "
              f"matching analog) {len(inter2)/max(1,len(dash_set))*100:.0f}%, "
              f"recall(of analog) {len(inter2)/max(1,len(analog_set))*100:.0f}%")
        jac = len(inter2) / max(1, len(dash_set | analog_set))
        print(f"   jaccard = {jac:.3f}")
    if analog_set:
        sa = sorted(sc for sc, r in zip(scores_b, jrows)
                    if r['wallet'] in analog_set)
        sb = sorted(sc for sc, r in zip(scores_b, jrows)
                    if r['wallet'] not in analog_set)
        print(f"   median composite: T1-analog {sa[len(sa)//2]:.3f} vs "
              f"rest {sb[len(sb)//2]:.3f}")
    # who's in one but not the other
    only_dash = sorted(dash_set - analog_set)
    only_analog = sorted(analog_set - dash_set)
    lab = lambda ws: [jup[w].get('label', w[:4]) for w in ws]
    print(f"   dashboard-only: {lab(only_dash)}")
    print(f"   analog-only: {lab(only_analog)}")

    out = {'universes': {'trust': len(tset), 'jup': len(jset),
                         'shared': len(tset & jset)},
           'A': {'rho': round(rho, 3), 'top10_k': k, 't1': len(t1_set),
                 'overlap': len(inter)},
           'B': {'analog': len(analog_set), 'tier': len(dash_set),
                 'overlap': len(inter2)}}
    path = os.path.join(HERMES_DATA, 'tier_correlation.json')
    with open(path, 'w') as f:
        json.dump(out, f, indent=2)
    print(f"\nreport -> {path}")


if __name__ == '__main__':
    main()
