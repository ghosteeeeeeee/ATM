#!/usr/bin/env python3
"""UGB-PT fire ledger: counterfactual forward return after each ugb_pt exit.

Direction-signed price-move % (never pnl_pct — leverage landmine):
positive = holding past the exit would have won, negative = exit saved money.
Forward price = close of the 1m bar CONTAINING target = exit + m minutes
(deterministic, 0-60s after target; only closed bars are used).

Criteria locked pre-data: keep enforcement if at n>=20 fires the summed
fwd-30m delta <= 0 (exit saved money) and harm rate (delta > +0.10%) < 40%;
otherwise bring UGB_PT_DISTANCE_PCT tuning to CEO.
"""
import datetime as dt
import os
import sqlite3
import sys

import psycopg2

EXIT_REASON = "ugb_pt"
HORIZONS = (15, 30, 60)  # minutes
CANDLES = "/root/.hermes/data/candles.db"


def pg_rows():
    conn = psycopg2.connect(host='/var/run/postgresql', database='brain', user='postgres')
    try:
        cur = conn.cursor()
        cur.execute("""SELECT id, token, direction, exit_price, close_time, pnl_usdt
                       FROM trades WHERE exit_reason=%s AND status='closed'
                       ORDER BY close_time ASC""", (EXIT_REASON,))
        return cur.fetchall()
    finally:
        conn.close()


def fwd(candles, token, direction, close_time, exit_price):
    """{minutes: signed pct vs exit_price} — + = hold would have won."""
    cur = candles.cursor()
    now = int(dt.datetime.now(dt.timezone.utc).timestamp())
    base = close_time.replace(tzinfo=dt.timezone.utc).timestamp()
    sign = 1.0 if direction == 'LONG' else -1.0
    out = {}
    for m in HORIZONS:
        target = int(base) + m * 60
        bar_ts = (target // 60) * 60
        if bar_ts + 60 > now:
            continue  # bar not finished — not reproducible run-to-run
        cur.execute("SELECT close FROM candles_1m WHERE token=? AND ts=?", (token, bar_ts))
        row = cur.fetchone()
        if row:
            out[m] = sign * (row[0] / float(exit_price) - 1) * 100
    return out


def main():
    rows = pg_rows()
    if not rows:
        print("no ugb_pt exits yet")
        return
    if not os.path.exists(CANDLES):
        print(f"no candle db at {CANDLES}")
        return
    candles = sqlite3.connect(f"file:{CANDLES}?mode=ro", uri=True)
    print(f"ugb_pt fires n={len(rows)} (direction-signed price-move % vs exit, + = hold would have won)")
    sums = {m: 0.0 for m in HORIZONS}
    cnt = {m: 0 for m in HORIZONS}
    n30 = harm = 0
    try:
        for tid, token, direction, exit_price, close_time, pnl in rows:
            f = fwd(candles, token, direction, close_time, exit_price)
            if not f:
                print(f"  {tid} {token} {direction} exit={float(exit_price)} NO-CANDLE-DATA")
                continue
            if 30 in f:
                n30 += 1
                harm += 1 if f[30] > 0.10 else 0
            for m in f:
                sums[m] += f[m]
                cnt[m] += 1
            print(f"  {tid} {token} {direction} exit={float(exit_price)} pnl={float(pnl):+.3f} "
                  + " ".join(f"fwd{m}={f[m]:+.3f}%" for m in sorted(f)))
    finally:
        candles.close()
    if n30:
        print("SUM: " + " ".join(f"fwd{m}={sums[m]:+.2f}pp(n={cnt[m]})" for m in HORIZONS)
              + f" | harm_rate(fwd30>+0.10%) {harm}/{n30} = {100.0*harm/n30:.0f}%")


def selfcheck():
    rows = pg_rows()
    assert rows, "selfcheck: need at least one ugb_pt exit"
    tid, token, direction, exit_price, close_time, pnl = rows[0]  # oldest fire
    now = dt.datetime.now(dt.timezone.utc).replace(tzinfo=None)
    assert close_time < now, "selfcheck: fire not in the past"
    assert os.path.exists(CANDLES), "selfcheck: candles db missing"
    base = close_time.replace(tzinfo=dt.timezone.utc).timestamp()
    expected = {m for m in HORIZONS if (int(base) + m * 60) // 60 * 60 + 60 <= int(now.timestamp())}
    assert expected, f"selfcheck: fire too fresh ({now - close_time}), rerun later"
    candles = sqlite3.connect(f"file:{CANDLES}?mode=ro", uri=True)
    try:
        f = fwd(candles, token, direction, close_time, exit_price)
    finally:
        candles.close()
    assert set(f) == expected, f"selfcheck: horizon set {set(f)} != expected {expected}"
    for m, v in f.items():
        assert -100 < v < 100, f"selfcheck: implausible fwd {m}m {v}"
    # direction-signed value is a plain pct, must stay in range (checked above)
    # target bar contains exit + m minutes: expect_ts - floor_minute(base) == m0*60
    m0 = min(expected)
    expect_ts = ((int(base) + m0 * 60) // 60) * 60
    assert expect_ts - (int(base) // 60) * 60 == m0 * 60, "selfcheck: ts math"
    print(f"selfcheck PASS: {tid} {token} {direction} {f} (fwd{m0} bar_ts={expect_ts})")


if __name__ == "__main__":
    selfcheck() if "--selfcheck" in sys.argv else main()
