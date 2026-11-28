#!/usr/bin/env python3
"""LONG-BYPASS-SHORT-BIAS-BLOCK two-base reconcile (brain_auditor #311, 2026-11-28).

Serves disposition `amplify-longbypass-dual-basis-reconcile` (deadline 2026-11-28):
run BOTH bases on the SAME cohort and SAME window and report the divergence.

  BASE A (PRIMARY, gate_shadow): fwd_4h direction-adjusted price move % after the
    block, token-day dedup (dedup_key convention: gate|token|direction|UTC-day).
  BASE B (realized, PG): the first live LONG trade on the same token opening
    inside LOOKAHEAD_H of the block -> sum(pnl_usdt). This is the "did the block
    suppress a winner?" realized book. Units = pnl_usdt only (#193).

Bars (from the entry, unchanged):
  reconcile first, then a scoped exempt proposal may be drafted only if PRIMARY
  survives on the realized book. Default NO CHANGE.

Usage:
    python3 brain/analysis/longbypass_reconcile_2026-11-28.py --selfcheck
    python3 brain/analysis/longbypass_reconcile_2026-11-28.py [--days 30]
"""
import argparse
import os
import sqlite3
import sys
from datetime import datetime, timedelta, timezone

GATE_DB = "/root/.hermes/brain/gate_shadow.db"
GATE = "LONG-BYPASS-SHORT-BIAS-BLOCK"
LOOKAHEAD_H = 24


def dedup_blocked(rows):
    """token|direction|UTC-day dedup, earliest blocked_at wins. Shared by load and selfcheck."""
    dedup = {}
    for token, direction, blocked_at, fwd in rows:
        day = blocked_at[:10]  # UTC day of the blocked_at string (format 'YYYY-MM-DD hh:mm:ss+00:00')
        key = (token, direction, day)
        if key not in dedup or blocked_at < dedup[key][1]:
            dedup[key] = (token, blocked_at, fwd)
    return sorted(dedup.values(), key=lambda r: r[1].replace("T", " "))


def load_blocked(gate_db, days):
    con = sqlite3.connect(f"file:{gate_db}?mode=ro", uri=True)
    rows = con.execute(
        "SELECT token, direction, blocked_at, fwd_4h FROM events "
        "WHERE gate=? AND blocked_at >= datetime('now', ?) AND fwd_done=1",
        (GATE, f"-{days} days"),
    ).fetchall()
    con.close()
    return dedup_blocked(rows)


def realized_join(blocked, pg_conn, lookahead_h):
    """Return [(token, blocked_at, trade_id, pnl_usdt, is_win, open_time)].

    One PG trade may fall inside the 24h window of two consecutive token-day
    blocks; each trade id is claimed at most once (earliest block first, blocks
    processed in time order) so net is never double counted.
    """
    out = []
    seen = set()
    for token, blocked_at, _fwd in blocked:
        t0 = datetime.fromisoformat(blocked_at.replace("Z", "+00:00"))
        t1 = t0 + timedelta(hours=lookahead_h)
        cur = pg_conn.cursor()
        cur.execute(
            "SELECT id, pnl_usdt, open_time FROM trades "
            "WHERE token=%s AND direction='LONG' AND open_time >= %s AND open_time < %s "
            "ORDER BY open_time",
            (token, t0.replace(tzinfo=None), t1.replace(tzinfo=None)),
        )
        for tid, pnl, opened in cur.fetchall():
            if tid in seen:
                continue
            if pnl is None:  # unfilled/cancelled row — no outcome to count
                continue
            seen.add(tid)
            val = float(pnl)
            out.append((token, blocked_at, tid, val, val > 0, opened))
            break  # first CLAIMED in-window trade for this block
    return out


def summarize(blocked, joined):
    fwd = [f for _, _, f in blocked if f is not None]
    a = {
        "tok_n": len({t for t, _, _ in blocked}),
        "n": len(fwd),
        "avg_fwd": round(sum(fwd) / len(fwd), 4) if fwd else None,
        "pos": sum(1 for f in fwd if f > 0),
        "pos_rate": round(100.0 * sum(1 for f in fwd if f > 0) / len(fwd), 1) if fwd else None,
    }
    pnls = [p for _, _, _, p, _, _ in joined]
    b = {
        "n": len(joined),
        "net": round(sum(pnls), 3),
        "wr": round(100.0 * sum(1 for p in pnls if p > 0) / len(pnls), 1) if pnls else None,
        "avg": round(sum(pnls) / len(pnls), 4) if pnls else None,
        "winners_net": round(sum(p for p in pnls if p > 0), 3),
        "losers_net": round(sum(p for p in pnls if p <= 0), 3),
    }
    return a, b


def run(days):
    blocked = load_blocked(GATE_DB, days)
    import psycopg2
    pg = psycopg2.connect(host="/var/run/postgresql", database="brain", user="postgres")
    joined = realized_join(blocked, pg, LOOKAHEAD_H)
    pg.close()
    a, b = summarize(blocked, joined)
    print(f"GATE {GATE}  window={days}d  dedup=tok|dir|UTC-day  lookahead={LOOKAHEAD_H}h")
    print(f"  BASE A fwd_4h (PRIMARY): tok_n={a['tok_n']} n={a['n']} "
          f"avg_fwd={a['avg_fwd']}% pos={a['pos']}/{a['n']} ({a['pos_rate']}%)")
    print(f"  BASE B realized (PG)   : n={b['n']} net={b['net']} pnl_usdt "
          f"WR={b['wr']}% avg={b['avg']} (winners {b['winners_net']} / losers {b['losers_net']})")
    agree = (a["avg_fwd"] or 0) > 0 and (b["net"] or 0) > 0
    print(f"  DIVERGENCE: {'SAME-SIGN (both positive)' if agree else 'DISAGREE'}")
    return a, b


def selfcheck():
    """Exercises the REAL dedup function + summarize; pins the no-double-count contract."""
    # format matches the live DB exactly (space-separated; verified 127,853 rows, 0 T-format)
    rows = [
        ("AAA", "LONG", "2026-11-01 10:00:00+00:00", 1.0),
        ("AAA", "LONG", "2026-11-01 11:00:00+00:00", -9.9),  # same token-day, later -> dropped
        ("BBB", "LONG", "2026-11-01 09:00:00+00:00", -0.5),  # different token, same day
        ("CCC", "LONG", "2026-11-02 10:00:00+00:00", None),
    ]
    got = dedup_blocked(rows)
    assert len(got) == 3, got                       # 1 same-token-day dup removed
    by_tok = {t: f for t, _, f in got}
    assert by_tok["AAA"] == 1.0, f"earliest AAA row must win: {by_tok}"
    assert sum(1 for _, _, f in got if f is None) == 1
    assert [t for t, _, _ in got] == ["BBB", "AAA", "CCC"], got  # chronological
    a, b = summarize(got, [("AAA", got[1][1], 1, 0.50, True, None)])
    assert a["n"] == 2 and a["pos"] == 1, a
    assert a["tok_n"] == 3 and a["avg_fwd"] == 0.25, a
    assert b["net"] == 0.50 and b["wr"] == 100.0, b
    a2, b2 = summarize(got, [("AAA", got[1][1], 1, -0.50, False, None)])
    assert not ((a2["avg_fwd"] or 0) > 0 and (b2["net"] or 0) > 0)
    # no-double-count contract: summarize ADDS duplicates, so the guard must live in
    # realized_join's seen-set (verified live: trade 16920 was claimed once after the fix).
    a3, b3 = summarize(got, [("AAA", got[1][1], 1, 0.50, True, None),
                             ("AAA", got[1][1], 1, 0.50, True, None)])
    assert b3["net"] == 1.00 and b3["n"] == 2, b3
    print("SELFCHECK PASS")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=30)
    ap.add_argument("--selfcheck", action="store_true")
    args = ap.parse_args()
    if args.selfcheck:
        selfcheck()
    else:
        run(args.days)
