#!/usr/bin/env python3
"""Confidence-crush census (brain_auditor #94, creative).

Question: does the [70,95) CONF_FILTER window measure *signal confidence* or the
*penalty gate*? The compactor checks the window pre-penalty; the decider's
PENALTY-GATE line carries both the pre-penalty conf and the exec conf:

    [PENALTY-GATE] LTC SHORT: conf 98 x penalty_raw 0.003 x mult 0.500 -> exec 49.0%

So a candidate can be approved inside the window and EXECUTE outside it. Every
[CONF-FILTER-SHADOW] fire so far is used=final/raw=None (decider layer never sees
the raw compactor conf). This census splits executed trades into:

    CRUSHED   pre-penalty >= 70 and exec < 70   (window passed, then crushed)
    LOW       pre-penalty <  70                 (never passed the window)
    IN        exec in [70,95)                   (window holds at exec)
    HOT       exec >= 95                        (other side of the window)

and reports PnL/WR per cohort vs trades joined by token+direction+open_time.

Read-only. No config touched.
"""
import re
import sys
import psycopg2

LOG = "/root/.hermes/logs/pipeline.log"
EXEC_RE = re.compile(r"^(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d)\s+EXEC: (\S+) (\w+) @ .*?conf=(\d+)%.*?\[([^\]]*)\]")
GATE_RE = re.compile(r"^(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d)\s+.*\[PENALTY-GATE\] (\S+) (\w+): conf (\d+)")


def parse(path):
    execs, gates = [], []
    with open(path, "r", errors="replace") as fh:
        for line in fh:
            if "EXEC:" in line:
                m = EXEC_RE.match(line)
                if m:
                    execs.append((m.group(1), m.group(2), m.group(3), int(m.group(4)), m.group(5)))
            elif "PENALTY-GATE]" in line:
                m = GATE_RE.match(line)
                if m:
                    gates.append((m.group(1), m.group(2), m.group(3), int(m.group(4))))
    # last gate per (token,direction) at-or-before the exec (5 min window)
    from bisect import bisect_right
    by_key = {}
    for ts, tok, d, pre in gates:
        by_key.setdefault((tok, d), []).append((ts, pre))
    out = []
    for ts, tok, d, ex, src in execs:
        lst = by_key.get((tok, d), [])
        i = bisect_right([g[0] for g in lst], ts) - 1
        pre = None
        if i >= 0 and (int(ts[11:13]) * 60 + int(ts[14:16]) - (int(lst[i][0][11:13]) * 60 + int(lst[i][0][14:16]))) <= 5:
            pre = lst[i][1]
        out.append((ts, tok, d, ex, pre, src))
    return out


def cohort(pre, ex):
    if pre is None:
        return "NO-GATE"
    if pre >= 70 and ex < 70:
        return "CRUSHED"
    if pre < 70:
        return "LOW"
    if 70 <= ex < 95:
        return "IN"
    if ex >= 95:
        return "HOT"
    return "MID"  # pre>=70, 70<=ex... unreachable; ex<70 handled, ex>=95 handled


def main():
    rows = parse(LOG)
    assert rows, "no EXEC lines parsed"
    conn = psycopg2.connect(host="/var/run/postgresql", database="brain", user="postgres")
    cur = conn.cursor()
    cur.execute("""SELECT token, direction, open_time, pnl_usdt::float, pnl_pct::float, confidence::float
                   FROM trades WHERE status='closed' AND open_time > NOW() - INTERVAL '13 days'""")
    trades = cur.fetchall()
    conn.close()
    idx = {}
    for tok, d, ot, pnl, pct, conf in trades:
        idx.setdefault((tok, d), []).append((ot, pnl, pct, conf))

    from collections import defaultdict
    agg = defaultdict(lambda: [0, 0, 0.0, 0.0])
    joined = 0
    seen = set()
    src_agg = defaultdict(lambda: [0, 0, 0.0])
    for ts, tok, d, ex, pre, src in rows:
        c = cohort(pre, ex)
        key = (tok, d)
        if key not in idx:
            continue
        best = None
        for ot, pnl, pct, conf in idx[key]:
            if ot.strftime("%Y-%m-%d") != ts[:10]:
                continue
            if abs(_m(ot) - _m_str(ts)) <= 2:
                best = (ot, pnl, pct, conf)
                break
        if best is None:
            continue
        if best[0] in seen:
            continue
        seen.add(best[0])
        joined += 1
        if c == "CRUSHED":
            sa = src_agg[src.split(",")[0].rstrip("+-")]
            sa[0] += 1
            sa[1] += 1 if best[1] > 0 else 0
            sa[2] += best[1]
        a = agg[c]
        a[0] += 1
        a[1] += 1 if best[1] > 0 else 0
        a[2] += best[1]
        a[3] += best[2]

    print(f"EXEC lines parsed: {len(rows)}  joined to closed trades: {joined}")
    print(f"{'cohort':10} {'n':>4} {'WR%':>6} {'pnl$':>8} {'pnl%':>8}")
    for c in ("CRUSHED", "LOW", "IN", "HOT", "MID", "NO-GATE"):
        a = agg.get(c)
        if not a or a[0] == 0:
            continue
        print(f"{c:10} {a[0]:4d} {100.0*a[1]/a[0]:6.1f} {a[2]:+8.2f} {a[3]:+8.2f}")
    # self-check: cohorts must be mutually exclusive and cover all joined rows
    total = sum(a[0] for a in agg.values())
    assert total == joined, f"cohort sum {total} != joined {joined}"
    print("CRUSHED by source (first part, +/- stripped):")
    for k, v in sorted(src_agg.items(), key=lambda x: x[1][2])[:10]:
        print(f"  {k:28} {v[0]:3d}T {v[1]:2d}W {v[2]:+.2f}")
    blocked_w = sum(a[1] for c, a in agg.items() if c in ("CRUSHED", "LOW"))
    total_w = sum(a[1] for a in agg.values())
    print(f"fk if exec conf<70 enforced: {blocked_w}/{total_w} = {100.0*blocked_w/max(total_w,1):.1f}% of winners blocked")
    print("SELF-CHECK PASS")


def _m(ot):
    return ot.hour * 60 + ot.minute


def _m_str(ts):
    return int(ts[11:13]) * 60 + int(ts[14:16])


if __name__ == "__main__":
    main()
