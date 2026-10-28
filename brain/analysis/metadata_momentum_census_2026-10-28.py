#!/usr/bin/env python3
"""Run #191 pre-registered lever: metadata-only no-momentum census.

Question: do detect-stamped metadata fields (momentum_state, momentum_score,
volume_spike, speed_percentile, price_acceleration, rsi_drift) separate
ARMED (mfe>=0.40) from UNARMED entries — i.e. can any of them gate chop?

Ship bar (locked #190): 30d same-sign AND p<0.05 AND winner-kill <20%
AND n>=20/cell AND not-already-in-constants.

No candle joins, no lookahead: fields come from trades._signal_metadata,
stamped at detect time.

Usage: python3 brain/analysis/metadata_momentum_census_2026-10-28.py [--selfcheck]
"""
import json
import math
import sys
from collections import Counter
from math import comb

import psycopg2

FIELDS = [
    "momentum_score",
    "volume_spike",
    "speed_percentile",
    "price_acceleration",
    "rsi_drift",
]


def fisher_two_sided(a, b, c, d):
    n = a + b + c + d
    if n == 0:
        return 1.0

    def prob(x):
        r1, c1 = a + b, a + c
        lo, hi = max(0, r1 + c1 - n), min(r1, c1)
        if x < lo or x > hi:
            return 0.0
        return comb(c1, x) * comb(n - c1, r1 - x) / comb(n, r1)

    p0 = prob(a)
    lo, hi = max(0, (a + b) + (a + c) - n), min(a + b, a + c)
    total = sum(prob(x) for x in range(lo, hi + 1) if prob(x) <= p0 + 1e-12)
    return min(1.0, total)


def load(days):
    conn = psycopg2.connect(host="/var/run/postgresql", database="brain", user="postgres")
    cur = conn.cursor()
    cur.execute(
        """SELECT token, signal, direction, pnl_usdt, mfe_pct, _signal_metadata::json
           FROM trades
           WHERE status='closed' AND close_time > NOW() - INTERVAL '%s days'
             AND mfe_pct IS NOT NULL AND _signal_metadata IS NOT NULL""" % days
    )
    rows = []
    for tok, sig, d, pnl, mfe, m in cur.fetchall():
        try:
            md = json.loads(m) if isinstance(m, str) else m
        except Exception:
            continue
        rows.append(
            dict(tok=tok, sig=sig, d=d, pnl=float(pnl or 0), mfe=float(mfe), md=md)
        )
    conn.close()
    return rows


def num(row, key):
    v = row["md"].get(key)
    if v is None:
        return None
    if isinstance(v, str):
        try:
            return float(v)
        except ValueError:
            return None
    if isinstance(v, (int, float)):
        return float(v)
    return None


def tercile_split(rows, field):
    vals = [(num(r, field), r) for r in rows]
    vals = [(v, r) for v, r in vals if v is not None]
    if len(vals) < 60:
        return None
    vs = sorted(v for v, _ in vals)
    c1 = vs[int(0.33 * (len(vs) - 1))]
    c2 = vs[int(0.66 * (len(vs) - 1))]
    bins = {"low": [], "mid": [], "high": []}
    for v, r in vals:
        if v <= c1:
            bins["low"].append(r)
        elif v <= c2:
            bins["mid"].append(r)
        else:
            bins["high"].append(r)
    return c1, c2, bins


def summarize(grp):
    n = len(grp)
    if n == 0:
        return None
    armed = sum(1 for r in grp if r["mfe"] >= 0.40)
    wins = sum(1 for r in grp if r["pnl"] > 0)
    return dict(
        n=n,
        armed=armed,
        unarmed=n - armed,
        armed_pct=100.0 * armed / n,
        wins=wins,
        wr=100.0 * wins / n,
        pnl=sum(r["pnl"] for r in grp),
    )


def gate_candidate(rows, field, lo=None, hi=None, keep="low"):
    """Return kept/blocked groups for a threshold gate."""
    vals = [(num(r, field), r) for r in rows]
    vals = [(v, r) for v, r in vals if v is not None]
    kept, blocked = [], []
    for v, r in vals:
        in_keep = True
        if lo is not None and v < lo:
            in_keep = False
        if hi is not None and v > hi:
            in_keep = False
        (kept if in_keep else blocked).append(r)
    return kept, blocked


def evaluate_gate(kept, blocked, label):
    k, b = summarize(kept), summarize(blocked)
    if not k or not b or k["n"] < 20 or b["n"] < 20:
        return dict(label=label, verdict="n<20 COLLECT", kept=k, blocked=b)
    # fisher on armed: kept-armed vs blocked-armed
    a, bb = k["armed"], k["unarmed"]
    c, d = b["armed"], b["unarmed"]
    p = fisher_two_sided(a, bb, c, d)
    # winner-kill: fraction of ALL winners that the gate would block
    total_wins = k["wins"] + b["wins"]
    fk = (100.0 * b["wins"] / total_wins) if total_wins else 0.0
    net = k["pnl"]
    return dict(
        label=label,
        kept=k,
        blocked=b,
        fisher_armed_p=round(p, 4),
        winner_kill_pct=round(fk, 1),
        kept_pnl=round(net, 2),
        blocked_pnl=round(b["pnl"], 2),
    )


def run():
    rows30 = load(30)
    rows14 = load(14)
    rows7 = load(7)
    print(f"n: 30d={len(rows30)} 14d={len(rows14)} 7d={len(rows7)}")

    print("\n=== A. momentum_state categorical vs ARMED (30d) ===")
    for st in ["rising", "flat", "falling"]:
        grp = [r for r in rows30 if str(r["md"].get("momentum_state")) == st]
        s = summarize(grp)
        if s:
            print(
                f"  {st:8s} n={s['n']:3d} armed%={s['armed_pct']:5.1f} "
                f"wr={s['wr']:5.1f} pnl={s['pnl']:+.2f}"
            )
    trending = [r for r in rows30 if str(r["md"].get("momentum_state")) in ("rising", "falling")]
    flat = [r for r in rows30 if str(r["md"].get("momentum_state")) == "flat"]
    t, f = summarize(trending), summarize(flat)
    if t and f:
        p = fisher_two_sided(t["armed"], t["unarmed"], f["armed"], f["unarmed"])
        print(
            f"  trending(rid+fall) vs flat: armed {t['armed_pct']:.1f}% vs {f['armed_pct']:.1f}% "
            f"fisher p={p:.4f}  pnl {t['pnl']:+.2f} vs {f['pnl']:+.2f}"
        )

    print("\n=== B. numeric terciles: ARMED% flatness (30d) ===")
    for field in FIELDS:
        res = tercile_split(rows30, field)
        if not res:
            print(f"  {field}: insufficient n")
            continue
        c1, c2, bins = res
        parts = []
        for name in ("low", "mid", "high"):
            s = summarize(bins[name])
            if s:
                parts.append(f"{name} n={s['n']} armed%={s['armed_pct']:.1f} wr={s['wr']:.1f} pnl={s['pnl']:+.2f}")
        print(f"  {field} cuts=({c1:.4g},{c2:.4g})")
        for p in parts:
            print(f"     {p}")

    print("\n=== C. gate candidates (30d) — ship bar: p<0.05, fk<20%, n>=20/cell ===")
    results = []
    # low-keep gates on each field at tercile boundary
    for field in FIELDS:
        res = tercile_split(rows30, field)
        if not res:
            continue
        c1, c2, _ = res
        kept, blocked = gate_candidate(rows30, field, hi=c1)
        r = evaluate_gate(kept, blocked, f"{field} keep<=p33 ({c1:.4g})")
        results.append(r)
        print_gate(r)
        kept, blocked = gate_candidate(rows30, field, hi=c2)
        r = evaluate_gate(kept, blocked, f"{field} keep<=p66 ({c2:.4g})")
        results.append(r)
        print_gate(r)

    print("\n=== D. OOS re-check on any p<0.05 candidate (14d / 7d) ===")
    passing = [r for r in results if r.get("fisher_armed_p", 1) < 0.05]
    if not passing:
        print("  no candidate passed the 30d p<0.05 bar — OOS stage skipped (locked bar order)")
    else:
        for r in passing:
            field = r["label"].split()[0]
            for days, rows in ((14, rows14), (7, rows7)):
                res = tercile_split(rows, field)
                if not res:
                    continue
                c1, c2, _ = res
                kept, blocked = gate_candidate(rows, field, hi=c1)
                rr = evaluate_gate(kept, blocked, f"{field} 14d/7d")
                print_gate(rr)

    print("\n=== E. rsi_drift coverage bias check ===")
    with_d = [r for r in rows30 if num(r, "rsi_drift") is not None]
    without = [r for r in rows30 if num(r, "rsi_drift") is None]
    print(f"  stamped n={len(with_d)}  unstamped n={len(without)}")
    print(f"  stamped  pnl={sum(r['pnl'] for r in with_d):+.2f} "
          f"armed%={summarize(with_d)['armed_pct']:.1f} wr={summarize(with_d)['wr']:.1f}")
    print(f"  unstamped pnl={sum(r['pnl'] for r in without):+.2f} "
          f"armed%={summarize(without)['armed_pct']:.1f} wr={summarize(without)['wr']:.1f}")

    return results


def print_gate(r):
    if "kept" not in r or not r.get("kept"):
        print(f"  {r['label']}: {r.get('verdict','skip')}")
        return
    k, b = r["kept"], r["blocked"]
    print(
        f"  {r['label']}: kept n={k['n']} armed%={k['armed_pct']:.1f} wr={k['wr']:.1f} "
        f"pnl={k['pnl']:+.2f} | blocked n={b['n']} armed%={b['armed_pct']:.1f} "
        f"pnl={b['pnl']:+.2f} | p={r.get('fisher_armed_p')} fk={r.get('winner_kill_pct')}%"
    )


def selfcheck():
    # fisher hand-check: known small table
    p = fisher_two_sided(1, 9, 11, 3)
    assert 0.0 < p <= 1.0, p
    # classic example: a=1,b=9,c=11,d=3 -> p ~ 0.0027 (one-sided ~0.00135)
    assert abs(p - 0.0027) < 0.002, p
    # degenerate
    assert fisher_two_sided(0, 0, 0, 0) == 1.0
    assert fisher_two_sided(10, 0, 0, 10) < 0.001
    # gate_candidate monotonicity
    rows = [dict(md={"x": float(i)}, mfe=0.5 if i % 2 == 0 else 0.1,
                 pnl=1.0 if i % 3 == 0 else -0.5) for i in range(100)]
    kept, blocked = gate_candidate(rows, "x", hi=50.0)
    assert len(kept) == 51 and len(blocked) == 49, (len(kept), len(blocked))
    print("ASSERT PASS: fisher hand-check + gate split")


def stamp_selfcheck():
    """Verify the run #191 BTC tape stamp in decider_run.py against live continuum.db."""
    import os
    import sqlite3
    import time

    sys.path.insert(0, "/root/.hermes/scripts")
    import paths

    conn = sqlite3.connect(os.path.join(paths.HERMES_DATA, "continuum.db"), timeout=3)
    try:
        row = conn.execute(
            "SELECT price, ema300, ema300_position, ema300_duration, "
            "consecutive_above, consecutive_below, trend_quality, ts "
            "FROM continuum_states WHERE token='BTC' AND timeframe='1m' "
            "ORDER BY ts DESC LIMIT 1"
        ).fetchone()
    finally:
        conn.close()
    assert row, "no BTC 1m row in continuum.db"
    price, ema, pos, dur, above, below, tq, ts = row
    assert pos in ("ABOVE", "BELOW", "AT"), pos
    assert ts and (time.time() - ts) < 600, "row stale"
    assert ema and ema > 0, "ema300 unusable"
    if pos == "ABOVE":
        streak = above
    elif pos == "BELOW":
        streak = below
    else:
        streak = None  # 'AT' has no directional streak — must not record below=0
    assert streak is None or (isinstance(streak, int) and streak >= 0)
    if price is not None:
        dist = (float(price) - float(ema)) / float(ema) * 100
        assert abs(dist) < 20, "BTC within 20% of EMA300 sanity"
    print(
        f"ASSERT PASS: tape stamp self-check pos={pos} dur={dur} "
        f"streak={streak} trend={tq} age={time.time()-ts:.0f}s"
    )


if __name__ == "__main__":
    if "--selfcheck" in sys.argv:
        selfcheck()
    elif "--stamp-selfcheck" in sys.argv:
        stamp_selfcheck()
    else:
        run()
