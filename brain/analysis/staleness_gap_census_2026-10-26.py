#!/usr/bin/env python3
"""Staleness + gap_at_entry census — run #155 (2026-10-26).

Two candidate entry-quality axes measured from trades._signal_metadata
(staleness_minutes and gap_at_entry are stamped live by decider_run
_exec_meta; the trades.signal_created_at COLUMN is dead since 2026-09-09
and is NOT used here).

Verdicts (bars: n>=20, same-sign across 7/14/30d, fk<20%):
  staleness_minutes  -> FLAT, no edge (5-15m cohort is the BEST bucket at 30d)
                        => REJECTED. Consistent with the 2026-10-04 removal of
                        the hard staleness block.
  gap_at_entry       -> OOS SIGN FLIP (7d chase >=0.5% loses -0.92 but
                        30d chase +2.55 = best bucket) => REJECTED.
                        Do not propose a universal MAX_ENTRY_GAP from a 7d read.

Usage:
  python3 brain/analysis/staleness_gap_census_2026-10-26.py           # tables
  python3 brain/analysis/staleness_gap_census_2026-10-26.py --selfcheck
"""
import json
import sys
from collections import defaultdict

import psycopg2

WINDOWS = (7, 14, 30)


def fetch_bucket(win, key, edges, labels):
    conn = psycopg2.connect(host="/var/run/postgresql", database="brain", user="postgres")
    cur = conn.cursor()
    cur.execute(
        """SELECT _signal_metadata, pnl_usdt FROM trades
           WHERE status='closed' AND close_time > NOW()-INTERVAL %s""",
        (f"{win} days",),
    )
    rows = cur.fetchall()
    agg = defaultdict(lambda: [0, 0, 0.0])
    keyed = 0
    for md, pnl in rows:
        try:
            d = json.loads(md) if isinstance(md, str) else (md or {})
        except Exception:
            continue
        if not isinstance(d, dict):
            continue
        v = d.get(key)
        if v is None:
            continue
        keyed += 1
        for i, e in enumerate(edges):
            if v < e:
                b = labels[i]
                break
        else:
            b = labels[-1]
        agg[b][0] += 1
        agg[b][1] += 1 if pnl > 0 else 0
        agg[b][2] += float(pnl)
    cur.close()
    conn.close()
    return {b: tuple(agg[b]) for b in labels if b in agg}, len(rows), keyed


def table(key, edges, labels, title):
    for win in WINDOWS:
        agg, total, keyed = fetch_bucket(win, key, edges, labels)
        print(f"=== {win}d {title} (bucketed {keyed}/{total} closed = "
              f"{100*keyed/total:.1f}% coverage) ===")
        for b in labels:
            if b in agg:
                n, w, p = agg[b]
                print(f"  {b:10s} {n:4d}T {100*w/n:5.1f}% {p:+.2f}")
        print()


def main():
    table(
        "staleness_minutes",
        [2, 5, 15, 1e9],
        ["<2m", "2-5m", "5-15m", ">=15m"],
        "staleness_minutes buckets",
    )
    table(
        "gap_at_entry",
        [-0.5, 0.0, 0.5, 1e9],
        ["<-0.5%", "-0.5..0", "0..0.5%", ">=0.5%"],
        "gap_at_entry buckets",
    )


def selfcheck():
    a, _, a_keyed = fetch_bucket(30, "staleness_minutes", [2, 5, 15, 1e9],
                                 ["<2m", "2-5m", "5-15m", ">=15m"])
    g30, _, g_keyed = fetch_bucket(30, "gap_at_entry", [-0.5, 0.0, 0.5, 1e9],
                                   ["<-0.5%", "-0.5..0", "0..0.5%", ">=0.5%"])
    g7, _, _ = fetch_bucket(7, "gap_at_entry", [-0.5, 0.0, 0.5, 1e9],
                            ["<-0.5%", "-0.5..0", "0..0.5%", ">=0.5%"])
    # reproduction anchors measured 2026-10-26 05:50 UTC (run #155)
    # both legs of the OOS flip must hold: 7d chase loses, 30d chase wins
    assert g7[">=0.5%"][2] < 0, g7
    assert g30[">=0.5%"][2] > 0 and g30[">=0.5%"][2] > g30["<-0.5%"][2], g30
    # staleness: 5-15m must be the BEST 30d bucket (flat, no edge — if any
    # bucket had a real edge this would fail and the verdict needs re-reading)
    assert a["5-15m"][2] == max(v[2] for v in a.values()), a
    assert a_keyed > 200 and g_keyed > 200, (a_keyed, g_keyed)
    print(f"SELF-CHECK PASS: staleness n={a_keyed} 5-15m best bucket (flat/no-edge); "
          f"gap n={g_keyed} 7d/30d OOS sign flip reproduced")


if __name__ == "__main__":
    if "--selfcheck" in sys.argv:
        selfcheck()
    else:
        main()
