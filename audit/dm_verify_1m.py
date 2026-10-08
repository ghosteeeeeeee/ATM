#!/usr/bin/env python3
"""
dm_verify_1m.py — attack vector (b): timing fidelity of the 6 home-run
"kills" at the live system's actual ~1-minute evaluation cycle.

The live engine runs about every minute reading: current price, hold time,
and the two newest CLOSED 5m candles (velocity). This script replays the
time-exit at 1-minute resolution on candles_1m:
   fire at the FIRST closed 1m bar where hold > 2h, profit < 2%,
   and the newest closed 5m pair velocity < 0.
Compares fire time/profit vs the 5m-granularity replay.
Also reports robustness: how many consecutive qualifying minutes exist at
the fire, and the profit trajectory around the fire.
"""
import json
import sqlite3
import subprocess
from datetime import datetime, timezone

PG = "host=/var/run/postgresql dbname=brain user=postgres"
CANDLES = "/root/.hermes/data/candles.db"

# the 6 kill trades identified by BOTH engines (claim + this audit)
KILL_IDS = [15126, 15493, 15518, 15520, 15565, 15567]


def parse_ts(s):
    return datetime.fromisoformat(s.strip()).replace(tzinfo=timezone.utc)


def conn():
    return sqlite3.connect("file:%s?mode=ro" % CANDLES, uri=True, timeout=10)


def q(sql, args):
    c = conn()
    try:
        return c.execute(sql, args).fetchall()
    finally:
        c.close()


def main():
    ids = ",".join(str(i) for i in KILL_IDS)
    rows = subprocess.run(
        ["psql", PG, "-t", "-A", "-F", "\t", "-c",
         "SELECT id, token, direction, entry_price, pnl_usdt, pnl_pct, "
         "amount_usdt, open_time, close_time FROM trades WHERE id IN (%s)" % ids],
        capture_output=True, text=True, check=True).stdout.strip().split("\n")

    out = []
    for ln in rows:
        tid, token, direction, ep, pnl, pnlpct, amt, ot, ct = ln.split("\t")
        tid = int(tid)
        entry = float(ep)
        entry_ts = parse_ts(ot).timestamp()
        close_ts = parse_ts(ct).timestamp()
        notional = float(amt)

        m1 = q("SELECT ts, close FROM candles_1m WHERE token=? AND is_closed=1 "
               "AND ts>=? AND ts<=? ORDER BY ts",
               (token.upper(), int(entry_ts - 600), int(close_ts + 60)))
        m5 = q("SELECT ts, close FROM candles_5m WHERE token=? AND is_closed=1 "
               "AND ts>=? AND ts<=? ORDER BY ts",
               (token.upper(), int(entry_ts - 1200), int(close_ts + 60)))
        m5 = [(int(a), float(b)) for a, b in m5]

        fire = None
        consec = 0
        best_consec = 0
        traj = []
        for ts, c in m1:
            ts = int(ts)
            c = float(c)
            mclose = ts + 60.0
            if mclose < entry_ts or mclose > close_ts + 1.0:
                continue
            hold_h = (mclose - entry_ts) / 3600.0
            profit = (c - entry) / entry * 100.0
            # newest CLOSED 5m pair as of this minute
            closed5 = [b for b in m5 if b[0] + 300.0 <= mclose]
            vel = None
            if len(closed5) >= 2:
                vel = (closed5[-1][1] - closed5[-2][1]) / closed5[-2][1] * 100.0
            ok = (hold_h > 2.0 and profit < 2.0 and vel is not None and vel < 0)
            if ok:
                consec += 1
                best_consec = max(best_consec, consec)
                if fire is None:
                    fire = dict(min=datetime.fromtimestamp(mclose,
                                                           tz=timezone.utc),
                                hold_h=hold_h, profit=profit, vel=vel)
            else:
                consec = 0
            if 2.0 <= hold_h <= 2.6:
                traj.append((round((mclose - entry_ts) / 3600.0, 3),
                             round(profit, 3),
                             None if vel is None else round(vel, 3)))
        # profit at 5m-close of the 5m-fire (compare granularity)
        rec = dict(id=tid, token=token, fired_1m=fire is not None,
                   consec_qualifying_min=best_consec,
                   actual_pnl_pct=float(pnlpct), actual_usdt=float(pnl))
        if fire:
            rec.update(fire_at=str(fire["min"]),
                       hold_h=round(fire["hold_h"], 3),
                       profit=round(fire["profit"], 3),
                       vel=round(fire["vel"], 3),
                       sim_usdt=round(fire["profit"] / 100.0 * notional, 4),
                       delta=round(fire["profit"] / 100.0 * notional
                                   - float(pnl), 4))
        # profit just before the 2h mark and its crossing under 2%
        pre = [x for x in traj if x[0] < 2.05]
        rec["profit_at_2h02"] = traj[0][1] if traj else None
        rec["traj_head"] = traj[:12]
        out.append(rec)
        print("1m replay #%d %s: fire=%s hold=%s profit=%s%% vel=%s%% "
              "consec_min=%d sim=$%s" %
              (tid, token, rec.get("fire_at"), rec.get("hold_h"),
               rec.get("profit"), rec.get("vel"), best_consec,
               rec.get("sim_usdt")))
        print("   trajectory (hold_h, profit%, vel%):", traj[:14])

    with open("/root/.hermes/audit/dm_verify_1m.json", "w") as fh:
        json.dump(out, fh, indent=1, default=str)
    print("saved: /root/.hermes/audit/dm_verify_1m.json")


if __name__ == "__main__":
    main()
