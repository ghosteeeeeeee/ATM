#!/usr/bin/env python3
"""Per-gate SHORT relax-bar evaluator for gate_shadow (audit #306).

Serves disposition `other-gate-short-withhold-review` (deadline 2026-11-27,
owner signal_analyst): splits the aggregate "none" approval-block cell into its
per-gate components and applies each gate's own pre-registered bar.

Bar (from the disposition threshold, unchanged):
    token-day dedup, PRIMARY fwd_4h basis, n>=30, net >= +$1.50/14d,
    p<0.05, OOS (two 7d halves) same-sign.

Two measurement additions this run (NOT part of the original bar, reported
alongside it, never used to overrule a gate that already passes):
    BASE-RATE  = gate mean fwd_4h vs the population mean of ALL blocked SHORTs
                 in the same window. A bear-drift window makes every gate look
                 "profitable if relaxed" against zero, so a gate only withholds
                 SELECTIVELY bad shorts when it beats the population.
    CONCENTRATION = top-5 token share of the gate's net fwd. >70% = the pass is
                 a few tokens, not a property of the gate.

Units: fwd_4h is direction-adjusted price-move % (verified: same token same
minute LONG row = -x, SHORT row = +x). $ translation uses --notional (default
13.22 = measured avg notional, audit #305) and is APPROXIMATE — never mix with
stored pnl_pct (units rule, #193).

Usage:
    python3 brain/analysis/gate_relax_bar_2026-11-27.py --selfcheck
    python3 brain/analysis/gate_relax_bar_2026-11-27.py --days 14
    python3 brain/analysis/gate_relax_bar_2026-11-27.py --days 14 --gates RR-ENGINE
"""
import argparse
import math
import os
import sqlite3
import statistics
import sys
from collections import defaultdict

DB = "/root/.hermes/brain/gate_shadow.db"

# Gates named in the disposition threshold ("floor/regime/vol excluded").
DEFAULT_GATES = [
    "RR-ENGINE",
    "CONFLUENCE-GATE-BLOCK",
    "OVERSOLD-SHORT",
    "PUMP-CHAIN-SHORT-HIGH",
    "PENDING-APPROVE-BLOCK",
]
# The floor/regime/vol trio the disposition excludes from the "none" cell —
# measured for reconcile only, never proposed for relax here.
RECONCILE_GATES = ["SHORT-RSI-HARD-FLOOR", "SHORT-REGIME-GATE", "VOL-GATE-BYPASS"]

BAR_N = 30
BAR_NET_USD = 1.50
BAR_P = 0.05
BAR_CONC = 0.70  # advisory only


def t_pvalue(xs):
    """Two-sided normal-approx p for the mean of xs (n>=30 bar makes this fine)."""
    n = len(xs)
    if n < 2:
        return 0.0, 0.0
    m = statistics.mean(xs)
    sd = statistics.stdev(xs)
    if sd == 0:
        return 0.0, m
    t = m / (sd / math.sqrt(n))
    return 2 * (1 - 0.5 * (1 + math.erf(abs(t) / math.sqrt(2)))), m


def token_day_dedup(rows):
    """rows = [(gate, token, day, fwd)] -> {(gate, token, day): avg_fwd}."""
    acc = defaultdict(list)
    for g, tok, d, f in rows:
        acc[(g, tok, d)].append(f)
    return {k: statistics.mean(v) for k, v in acc.items()}


def split_halves(by_day, mid):
    h1 = [f for (_, _, d), f in by_day.items() if d < mid]
    h2 = [f for (_, _, d), f in by_day.items() if d >= mid]
    return sum(h1), sum(h2)


def evaluate(gate_rows, population_mean, notional):
    """gate_rows: {(gate,token,day): avg_fwd} already deduped, filtered to one gate."""
    xs = list(gate_rows.values())
    n = len(xs)
    if n < BAR_N:
        return {"n": n, "verdict": "FAIL n<%d" % BAR_N}
    p, mean = t_pvalue(xs)
    net_pct = sum(xs)
    net_usd = net_pct / 100.0 * notional
    days = sorted({d for (_, _, d) in gate_rows})
    mid = days[len(days) // 2]
    h1, h2 = split_halves(gate_rows, mid)
    same_sign = (h1 > 0 and h2 > 0) or (h1 < 0 and h2 < 0)
    tok = defaultdict(float)
    for (_, t, _), f in gate_rows.items():
        tok[t] += f
    top5 = sum(sorted(tok.values(), reverse=True)[:5])
    conc = (top5 / net_pct) if net_pct > 0 else None
    base_ratio = (mean / population_mean) if population_mean else None
    checks = {
        "n>=30": True,
        "net>=$%.2f" % BAR_NET_USD: net_usd >= BAR_NET_USD,
        "p<%.2f" % BAR_P: p < BAR_P,
        "halves same-sign": same_sign,
    }
    passed = all(checks.values())
    return {
        "n": n,
        "sum_pct": net_pct,
        "net_usd": net_usd,
        "mean_pct": mean,
        "p": p,
        "halves": (h1, h2),
        "same_sign": same_sign,
        "tokens": len(tok),
        "top5_share": conc,
        "base_ratio": base_ratio,
        "checks": checks,
        "verdict": "PASS" if passed else "FAIL",
    }


def run(days, gates, notional):
    con = sqlite3.connect(DB)
    cur = con.cursor()
    since = "-%d days" % days
    cur.execute(
        "SELECT gate, token, substr(blocked_at,1,10), AVG(fwd_4h) FROM events "
        "WHERE direction='SHORT' AND fwd_done=1 AND fwd_4h IS NOT NULL "
        "AND blocked_at >= datetime('now', ?) GROUP BY 1,2,3",
        (since,),
    )
    rows = cur.fetchall()
    dedup = token_day_dedup(rows)
    pop = statistics.mean([v for v in dedup.values()])
    print("window %dd  token-day rows=%d  population mean fwd=%.4f%%" % (days, len(dedup), pop))
    print("%-26s %5s %9s %8s %7s %7s %5s %6s %5s" % (
        "gate", "n", "net%", "net$", "mean%", "p", "same", "conc", "verdict"))
    out = {}
    for g in gates:
        sub = {k: v for k, v in dedup.items() if k[0] == g}
        r = evaluate(sub, pop, notional)
        out[g] = r
        if "verdict" in r and "net_usd" not in r:
            print("%-26s %5d %9s %8s %7s %7s %5s %6s %5s" % (
                g, r["n"], "-", "-", "-", "-", "-", "-", r["verdict"]))
            continue
        print("%-26s %5d %+9.2f %+8.2f %+7.3f %7.4f %5s %5s %s" % (
            g, r["n"], r["sum_pct"], r["net_usd"], r["mean_pct"], r["p"],
            "Y" if r["same_sign"] else "N",
            ("%.0f%%" % (100 * r["top5_share"])) if r["top5_share"] is not None else "-",
            r["verdict"]))
        if r["base_ratio"] is not None:
            # sign-robust: a negative population mean makes raw ratios meaningless
            beats = r["mean_pct"] > pop
            print("%-26s   base-rate %s (mean %.4f%% vs population %.4f%%, delta %+.4f); tokens=%d; halves %+.2f/%+.2f" % (
                "", "BEATS" if beats else "BELOW", r["mean_pct"], pop,
                r["mean_pct"] - pop, r["tokens"], r["halves"][0], r["halves"][1]))
    con.close()
    return out, pop


def selfcheck():
    # 1. dedup collapses duplicate (gate,token,day) rows to their mean
    d = token_day_dedup([("A", "X", "2026-11-01", 1.0), ("A", "X", "2026-11-01", 3.0), ("A", "Y", "2026-11-01", 0.0)])
    assert len(d) == 2 and d[("A", "X", "2026-11-01")] == 2.0, d

    # 2. known p-value: 40 identical positive values -> mean exact, sd 0 -> p 0
    xs = [(g := "G", "T%d" % i, "2026-11-0%d" % (i % 9 + 1), 0.5) for i in range(40)]
    ded = token_day_dedup(xs)
    r = evaluate(ded, 0.1, 13.22)
    assert r["n"] == 40, r
    assert r["net_usd"] > BAR_NET_USD, r
    assert r["verdict"] == "PASS", r
    assert r["same_sign"], r

    # 3. small sample must FAIL regardless of sign
    small = token_day_dedup([("G", "T%d" % i, "2026-11-01", 5.0) for i in range(10)])
    assert evaluate(small, 0.1, 13.22)["verdict"].startswith("FAIL n<")

    # 4. negative-sum gate with n>=30 fails the net bar
    neg = token_day_dedup([("G", "T%d" % i, "2026-11-0%d" % (i % 9 + 1), -0.5) for i in range(40)])
    rn = evaluate(neg, 0.1, 13.22)
    assert rn["net_usd"] < 0 and rn["verdict"] == "FAIL", rn

    # 5. sign-flip halves must fail same-sign even with positive net
    flip_rows = token_day_dedup(
        [("G", "T%02d" % i, "2026-11-01", 1.0) for i in range(20)] +
        [("G", "T%02d" % i, "2026-11-15", -0.6) for i in range(20)])
    rf = evaluate(flip_rows, 0.1, 13.22)
    assert rf["same_sign"] is False and rf["verdict"] == "FAIL", rf

    # 6. base ratio computed and concentration bounded in [0,1]
    assert 0 <= (r["top5_share"] or 0) <= 1.0000001, r
    assert abs(r["base_ratio"] - (r["mean_pct"] / 0.1)) < 1e-9, r

    print("selfcheck PASS (6 assertions)")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--selfcheck", action="store_true")
    ap.add_argument("--days", type=int, default=14)
    ap.add_argument("--notional", type=float, default=13.22)
    ap.add_argument("--gates", nargs="*", default=None)
    a = ap.parse_args()
    if a.selfcheck:
        sys.exit(selfcheck())
    if not os.path.exists(DB):
        print("missing %s" % DB)
        sys.exit(1)
    gates = a.gates or (DEFAULT_GATES + RECONCILE_GATES)
    run(a.days, gates, a.notional)
