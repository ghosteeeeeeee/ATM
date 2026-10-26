#!/usr/bin/env python3
"""Creative #150: volume-precondition counterfactual for pump-chain+ LONG.

Hypothesis: volume-buildup- (only healthy SHORT, 75% WR) is volume-native and arms
78.6%; pump-chain+ has ZERO volume checks and arms ~58% while bleeding at conf<30.
Would a 1.5x 20-bar 5m volume precondition at entry have blocked the bleed without
killing the conf>=30 winners?

Pre-registered criteria (locked BEFORE looking at groups):
  - primary threshold: entry-bar 5m volume >= 1.5x prior-20-bar mean
  - scope: pump-chain+ signal, direction LONG, closed, 30d
  - ship bar (later, separate): n>=20 in blocked set, fk<20%, 30d same-sign,
    winner-impact <20%. THIS script only measures — no ship.
"""
import sqlite3
import statistics
import sys

import psycopg2

CANDLES = "/root/.hermes/data/candles.db"
THRESHOLD = 1.5
PRIOR = 20


def load_trades(days=30):
    conn = psycopg2.connect(host="/var/run/postgresql", database="brain", user="postgres")
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, token, open_time, confidence, trailing_activated,
               pnl_usdt, pnl_pct, exit_reason, mfe_pct
        FROM trades
        WHERE status='closed' AND signal='pump-chain+' AND direction='LONG'
          AND close_time > NOW() - INTERVAL '%d days'
        """ % days
    )
    rows = cur.fetchall()
    conn.close()
    return rows


def vol_ratio(c, token, open_ts):
    """Entry-bar 5m volume / mean of PRIOR closed 5m bars. None if no data."""
    t0 = int(open_ts.timestamp()) if hasattr(open_ts, "timestamp") else int(open_ts)
    # bars strictly before entry, take last PRIOR+1 closed
    rows = c.execute(
        "SELECT ts, volume FROM candles_5m WHERE token=? AND ts<=? AND is_closed=1 "
        "ORDER BY ts DESC LIMIT ?",
        (token, t0, PRIOR + 1),
    ).fetchall()
    if len(rows) < PRIOR + 1:
        return None
    entry_v = rows[0][1]
    prior = [r[1] for r in rows[1:]]
    avg = statistics.fmean(prior)
    if avg <= 0:
        return None
    return entry_v / avg


def main():
    days = 30
    rows = load_trades(days)
    c = sqlite3.connect(CANDLES)
    vals = [(r, vol_ratio(c, r[1], r[2])) for r in rows]
    c.close()
    j = [(r, v) for r, v in vals if v is not None]
    miss = len(rows) - len(j)
    hi = [r for r, v in j if v >= THRESHOLD]
    lo = [r for r, v in j if v < THRESHOLD]

    if "--selfcheck" in sys.argv:
        assert len(rows) > 0, "no trades loaded"
        assert len(hi) + len(lo) == len(j), "groups do not partition"
        assert miss + len(j) == len(rows), "missing + joined != total"
        print(f"SELF CHECK PASS: trades={len(rows)} joined={len(j)} missing={miss} "
              f"hi={len(hi)} lo={len(lo)}")
        return 0

    print(f"pump-chain+ LONG {days}d: {len(rows)} trades, {len(j)} joined on 5m vol, {miss} no-data")
    print(f"threshold: entry 5m vol >= {THRESHOLD}x prior-{PRIOR} mean\n")

    def summarize(label, subset_rows):
        n = len(subset_rows)
        if not n:
            print(f"  {label:28s} n=0")
            return
        wins = sum(1 for r in subset_rows if r[5] and float(r[5]) > 0)
        armed = sum(1 for r in subset_rows if r[4])
        pnl = sum(float(r[5]) for r in subset_rows)
        print(f"  {label:28s} n={n:3d}  armed={100.0*armed/n:5.1f}%  "
              f"WR={100.0*wins/n:5.1f}%  pnl={pnl:+.2f}")

    summarize("PASS vol>=1.5x", hi)
    summarize("BLOCK vol<1.5x", lo)
    print()
    for cname, cpred in [("conf>=30", lambda r: r[3] and float(r[3]) >= 30),
                         ("conf<30", lambda r: r[3] is not None and float(r[3]) < 30)]:
        print(f"  -- {cname} --")
        summarize(f"  PASS / {cname}", [r for r in hi if cpred(r)])
        summarize(f"  BLOCK / {cname}", [r for r in lo if cpred(r)])

    winners_blocked = sum(1 for r in lo if r[5] and float(r[5]) > 0)
    winners_total = sum(1 for r, _ in j if r[5] and float(r[5]) > 0)
    print(f"\nwinner-impact: {winners_blocked}/{winners_total} winners would be blocked "
          f"({100.0*winners_blocked/max(winners_total,1):.1f}%)")
    print("NOTE: measurement only. Ship bar (n>=20 blocked, fk<20%, OOS same-sign, "
          "winner-impact<20%) evaluated separately if ever proposed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
