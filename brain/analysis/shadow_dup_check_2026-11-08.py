#!/usr/bin/env python3
"""shadow_dup_check_2026-11-08.py — pseudo-replication detector for brain/shadow_trades.db.

Audit #239 finding: shadow_trades rows are unique by signal_id but the SAME signal
is re-emitted under multiple signal_ids in the same second (same source+token+created_at).
Per-source n in `shadow_trader.py --report` is therefore INFLATED and any "pattern"
measured on raw n can collapse on dedup.

Measured 2026-11-08:
  * whole DB:            75,694 rows -> 72,712 distinct(source,token,created_at)  (3.9%)
  * grind-breakout-:         32 rows -> 11 deduped (2.9x)  -> its "n=32 93.8% WR t=5.40"
                            becomes n=11 81.8% t=1.42 (n.s., second half NEGATIVE)
                            => the AMPLIFY candidate was REFUTED-WITH-DATA
  * CTX-GATE block count: 2,453 -> 929 deduped (2.6x)
  * btc-pump-rider+:        904 -> 486 (1.9x)

Same defect class as gate-shadow-dedup-convention (event n is 7-10x pseudo-replicated).
Rule: DEDUP by (source, token, created_at) BEFORE quoting any shadow per-source n.

Usage:
    python3 brain/analysis/shadow_dup_check_2026-11-08.py            # report
    python3 brain/analysis/shadow_dup_check_2026-11-08.py --selfcheck  # invariants, exit 1 on fail
"""
import os
import sqlite3
import sys

DB = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                  'brain', 'shadow_trades.db')


def dedup_counts(rows, key=(0, 1, 2)):
    """rows: iterable of tuples. -> (raw, deduped) using rows[i][key] as identity."""
    rows = list(rows)
    return len(rows), len({tuple(r[i] for i in key) for r in rows})


def dedup_ratio(rows, key=(0, 1, 2)):
    """raw/deduped inflation factor. ponytail: single source of the ratio so the
    selfcheck can test the MATH without depending on the live defect still existing."""
    raw, ded = dedup_counts(rows, key)
    return (raw / ded) if ded else 0.0


def _table(rows, group_index, dedup_key):
    """group rows by rows[i][group_index], dedup on dedup_key -> (ratio, key, raw, deduped) desc."""
    by = {}
    for r in rows:
        by.setdefault(r[group_index], []).append(r)
    out = []
    for k, grp in by.items():
        raw, ded = dedup_counts(grp, dedup_key)
        out.append((dedup_ratio(grp, dedup_key), k, raw, ded))
    out.sort(reverse=True)
    return out


def source_table(conn):
    cur = conn.cursor()
    cur.execute("""SELECT source, token, created_at FROM shadow_trades""")
    # dedup identity is always (source, token, created_at) = cols 0,1,2
    return _table(cur.fetchall(), 0, (0, 1, 2))


def gate_table(conn):
    cur = conn.cursor()
    cur.execute("""SELECT gate_name, source, token, created_at FROM shadow_trades
                   WHERE gate_blocked=1 AND gate_name IS NOT NULL""")
    # cols are (gate_name, source, token, created_at) -> identity is 1,2,3
    return _table(cur.fetchall(), 0, (1, 2, 3))


def report(limit=12):
    if not os.path.exists(DB):
        print(f"MISSING {DB}")
        return 1
    conn = sqlite3.connect(DB)
    try:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*), COUNT(DISTINCT signal_id) FROM shadow_trades")
        total, uniq_sid = cur.fetchone()
        cur.execute("SELECT COUNT(*) FROM (SELECT DISTINCT source, token, created_at FROM shadow_trades)")
        dist = cur.fetchone()[0]
        print(f"rows={total}  distinct_signal_id={uniq_sid}  distinct(source,token,created_at)={dist}  "
              f"dup={100.0 * (total - dist) / total:.1f}%")
        print(f"signal_id unique: {'YES' if total == uniq_sid else 'NO — PK VIOLATION'}")
        # ponytail: print only sources with enough raw n for the ratio to mean anything
        print(f"\nTOP inflated sources raw>=20 (raw/dedup):")
        shown = 0
        for ratio, s, raw, ded in source_table(conn):
            if raw < 20 or shown >= limit:
                continue
            flag = "  <-- INFLATED" if ratio >= 1.5 else ""
            print(f"  {s:40s} raw={raw:6d} dedup={ded:6d} x{ratio:4.1f}{flag}")
            shown += 1
        print(f"\nTOP inflated gate block counts:")
        shown = 0
        for ratio, g, raw, ded in gate_table(conn):
            if raw < 20 or shown >= limit:
                continue
            flag = "  <-- INFLATED" if ratio >= 1.5 else ""
            print(f"  {g:28s} raw={raw:6d} dedup={ded:6d} x{ratio:4.1f}{flag}")
            shown += 1
    finally:
        conn.close()
    return 0


def selfcheck():
    fails = []
    # synthetic: known duplicates  -> raw 5, dedup 3, ratio 5/3
    rows = [('a', 'X', 't1')] * 3 + [('a', 'Y', 't1')] + [('b', 'X', 't2')]
    raw, ded = dedup_counts(rows)
    if (raw, ded) != (5, 3):
        fails.append(f"dedup_counts synthetic got {(raw, ded)} want (5, 3)")
    # MED fix: assert the RATIO math itself, not the live defect (defect may be fixed later)
    if abs(dedup_ratio(rows) - 5.0 / 3.0) > 1e-9:
        fails.append(f"dedup_ratio synthetic got {dedup_ratio(rows)} want {5.0/3.0}")
    if dedup_ratio([]) != 0.0:
        fails.append("dedup_ratio empty must be 0.0")
    if dedup_counts([]) != (0, 0):
        fails.append("dedup_counts empty")
    # all-unique must not collapse
    rows2 = [('a', 'X', 't1'), ('a', 'X', 't2'), ('a', 'Y', 't1')]
    if dedup_counts(rows2) != (3, 3):
        fails.append("dedup_counts unique-set collapsed")
    if dedup_ratio(rows2) != 1.0:
        fails.append("dedup_ratio unique-set must be 1.0")
    # gate-shaped rows: identity is (source, token, created_at) = cols 1,2,3, NOT 0,1,2
    grows = [('G1', 'a', 'X', 't1'), ('G1', 'a', 'X', 't1'), ('G1', 'a', 'X', 't2')]
    if dedup_counts(grows, (1, 2, 3)) != (3, 2):
        fails.append(f"gate-key dedup got {dedup_counts(grows, (1,2,3))} want (3, 2)")
    # fixture must be able to tell the two keys apart, else it proves nothing
    if dedup_counts(grows, (0, 1, 2)) != (3, 1):
        fails.append("gate-key fixture is degenerate — wrong key gives the same answer")
    # real DB invariants (report-only; missing DB = skip, not fail)
    if os.path.exists(DB):
        conn = sqlite3.connect(DB)
        try:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*), COUNT(DISTINCT signal_id) FROM shadow_trades")
            total, uniq = cur.fetchone()
            if total != uniq:
                fails.append(f"signal_id not unique: {total} rows / {uniq} ids")
            for table, name in ((source_table(conn), 'source'), (gate_table(conn), 'gate')):
                for ratio, key, r, d in table:
                    if d > r:
                        fails.append(f"dedup > raw for {name} {key}")
                    if r > 0 and d == 0:
                        fails.append(f"dedup=0 for nonempty {name} {key}")
                    if d and abs(ratio - r / d) > 1e-9:
                        fails.append(f"ratio mismatch for {name} {key}: {ratio} vs {r/d}")
            inflated = [x for x in source_table(conn) if x[0] >= 1.5]
            print(f"[selfcheck] real DB: rows={total} inflated_sources(>=1.5x)={len(inflated)} "
                  f"(informational — not asserted, defect may be fixed)")
        finally:
            conn.close()
    else:
        print("[selfcheck] real DB missing — synthetic assertions only")
    if fails:
        for f in fails:
            print(f"FAIL: {f}")
        return 1
    print("SELFCHECK PASS")
    return 0


if __name__ == '__main__':
    sys.exit(selfcheck() if '--selfcheck' in sys.argv else report())
