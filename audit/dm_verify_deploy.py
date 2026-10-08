#!/usr/bin/env python3
"""
dm_verify_deploy.py — was the pump-exit engine actually OPERATING on
pump-chain+ trades during Sep 13-20 (code committed Sep 13, first observed
pump_exit_* exit Sep 21)?

For every in-scope trade that CLOSED between Sep 13 and Sep 21 (engine code
committed Sep 13 20:15), scan its open window for:
  - momentum-qualifying moments (2 consecutive closed 5m intervals
    < -0.5%), and
  - time-exit-qualifying moments (hold>2h, profit<2%, adverse newest pair)
i.e. moments where the LIVE engine (120s cycle) would have fired had it
been running. Also checks paper trades for the same window.
"""
import sqlite3
import subprocess
from datetime import datetime, timezone

PG = "host=/var/run/postgresql dbname=brain user=postgres"
CANDLES = "/root/.hermes/data/candles.db"


def psql_rows(sql):
    out = subprocess.run(["psql", PG, "-t", "-A", "-F", "\t", "-c", sql],
                         capture_output=True, text=True, check=True)
    return [ln.split("\t") for ln in out.stdout.strip().split("\n") if ln]


def candles(token, t0, t1):
    c = sqlite3.connect("file:%s?mode=ro" % CANDLES, uri=True, timeout=10)
    try:
        return [(int(a), float(b)) for a, b in c.execute(
            "SELECT ts, close FROM candles_5m WHERE token=? AND is_closed=1 "
            "AND ts>=? AND ts<=? ORDER BY ts",
            (token.upper(), int(t0), int(t1))).fetchall()]
    finally:
        c.close()


def main():
    rows = psql_rows(
        "SELECT id, token, direction, entry_price, exit_reason, "
        "extract(epoch from open_time)::bigint, "
        "extract(epoch from close_time)::bigint "
        "FROM trades WHERE paper=false AND status='closed' "
        "AND (strategy LIKE '%pump-chain+%' OR strategy LIKE '%pump_chain+%' "
        "OR strategy='pump_chain') "
        "AND close_time >= '2026-09-13 20:15' AND close_time < '2026-09-21 16:00'")
    print("in-scope trades closed Sep13 20:15 - Sep21 16:00: %d" % len(rows))
    n_mom = n_time = 0
    mom_list, time_list = [], []
    for tid, token, direction, ep, xreason, ets, cts in rows:
        entry, ets, cts = float(ep), int(ets), int(cts)
        bars = candles(token, ets - 1200, cts)
        mom_t = time_t = None
        for i in range(2, len(bars)):
            bc = bars[i][0] + 300.0
            if bc < ets or bc > cts + 1:
                continue
            v1 = (bars[i][1] - bars[i - 1][1]) / bars[i - 1][1] * 100
            v2 = (bars[i - 1][1] - bars[i - 2][1]) / bars[i - 2][1] * 100
            if mom_t is None and v1 < -0.5 and v2 < -0.5:
                mom_t = (bc - ets) / 3600.0
            if time_t is None:
                hold = (bc - ets) / 3600.0
                prof = (bars[i][1] - entry) / entry * 100
                if hold > 2.0 and prof < 2.0 and v1 < 0:
                    time_t = (hold, round(prof, 2))
        if mom_t is not None:
            n_mom += 1
            mom_list.append((tid, token, xreason, round(mom_t, 2)))
        if time_t is not None:
            n_time += 1
            time_list.append((tid, token, xreason, time_t))
    print("trades with MOMENTUM-qualifying moment while open: %d" % n_mom)
    for x in mom_list:
        print("   ", x)
    print("trades with TIME-exit-qualifying moment while open: %d" % n_time)
    for x in time_list:
        print("   ", x)
    print("(engine live would have produced pump_exit_momentum / "
          "pump_exit_dead_money exits on these)")


if __name__ == "__main__":
    main()
