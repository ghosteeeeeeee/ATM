#!/usr/bin/env python3
"""
dm_verify_variants.py — part 2 of the independent audit.

Purpose: reverse-engineer which replay CONFIGURATION the original claim
analysis used, by sweeping two methodological switches:

  align='close' : conditions evaluated at bar CLOSE time (correct: the rule
                  reads CLOSED bars, so close_i is known at ts_i+300).
  align='open'  : conditions evaluated at bar OPEN time using close_i
                  (5-minute LOOKAHEAD — the exit would fire before the data
                  existed; exit price still close_i).

  censor=True   : no fire after the trade's actual close_time (correct —
                  the trade is gone).
  censor=False  : fires may occur after actual close (impossible trades).

Also: per-trade forensics for the 10 actual in-scope pump_exit_dead_money
exits (which config "predicts" them and whether the prediction used
post-close data).
"""
import json
import sqlite3
import subprocess
from datetime import datetime, timezone

PG = "host=/var/run/postgresql dbname=brain user=postgres"
CANDLES = "/root/.hermes/data/candles.db"

TIME_HOURS = 2.0
TIME_THRESHOLD = 2.0

SCOPE_SQL = """
SELECT id, token, direction, entry_price, pnl_usdt, pnl_pct, amount_usdt,
       exit_reason, open_time, close_time
FROM trades
WHERE paper=false AND status='closed'
  AND (strategy LIKE '%%pump-chain+%%' OR strategy LIKE '%%pump_chain+%%'
       OR strategy = 'pump_chain')
ORDER BY open_time
"""


def psql_rows(sql):
    out = subprocess.run(["psql", PG, "-t", "-A", "-F", "\t", "-c", sql],
                         capture_output=True, text=True, check=True)
    return [ln.split("\t") for ln in out.stdout.strip().split("\n") if ln]


def parse_ts(s):
    return datetime.fromisoformat(s.strip()).replace(tzinfo=timezone.utc)


def load_candles_5m(token, t0, t1):
    conn = sqlite3.connect("file:%s?mode=ro" % CANDLES, uri=True, timeout=10)
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT ts, close FROM candles_5m "
            "WHERE token=? AND is_closed=1 AND ts>=? AND ts<=? ORDER BY ts",
            (token.upper(), int(t0), int(t1)))
        return [(int(r[0]), float(r[1])) for r in cur.fetchall()]
    finally:
        conn.close()


def evaluate(t, align, censor, grace=0.0):
    """Return (fire_dict_or_None, n_impossible_bars).

    fire evaluation: profit & velocity from close_i; eligibility timestamp
    = bar close (align='close') or bar open (align='open', LOOKAHEAD).
    censor: no fire with eval_ts > close_ts + grace.
    """
    entry_ts = t["open_ts"].timestamp()
    close_ts = t["close_ts"].timestamp()
    entry = t["entry"]
    long_side = t["direction"] == "LONG"
    bars = load_candles_5m(t["token"], entry_ts - 1200,
                           max(close_ts, entry_ts) + 7200)
    n_impossible = 0
    for idx in range(1, len(bars)):
        ts_o, c = bars[idx]
        prev_c = bars[idx - 1][1]
        eval_ts = ts_o + (300.0 if align == "close" else 0.0)
        if eval_ts < entry_ts:
            continue
        post_close = eval_ts > close_ts + 1.0
        if post_close and eval_ts > close_ts + grace + 1.0:
            if censor:
                break
            n_impossible += 1
        hold_h = (eval_ts - entry_ts) / 3600.0
        raw = (c - entry) / entry * 100.0
        profit = raw if long_side else -raw
        vel = (c - prev_c) / prev_c * 100.0
        if hold_h > TIME_HOURS and profit < TIME_THRESHOLD and vel < 0:
            sim = profit / 100.0 * t["notional"]
            return dict(eval_ts=datetime.fromtimestamp(eval_ts,
                                                       tz=timezone.utc),
                        hold_h=hold_h, profit=profit, vel=vel,
                        sim=sim, delta=sim - t["pnl"],
                        post_close=post_close,
                        close_lag_min=(close_ts - eval_ts) / 60.0), n_impossible
    return None, n_impossible


def main():
    rows = psql_rows(SCOPE_SQL)
    trades = []
    for r in rows:
        (tid, token, direction, ep, pnl, pnlpct, amt, xreason, ot, ct) = r
        trades.append(dict(
            id=int(tid), token=token.strip(), direction=direction.strip(),
            entry=float(ep), pnl=float(pnl or 0),
            pnl_pct=float(pnlpct or 0), notional=float(amt),
            exit_reason=(xreason or "").strip(),
            open_ts=parse_ts(ot), close_ts=parse_ts(ct)))

    dm_ids = {t["id"] for t in trades
              if t["exit_reason"] == "pump_exit_dead_money"}

    matrix = {}
    for align in ("close", "open"):
        for censor in (True, False):
            fires, impossible_fires, overlap, kills = [], 0, [], []
            for t in trades:
                fire, _ni = evaluate(t, align, censor)
                if fire:
                    fires.append((t, fire))
                    if fire["post_close"]:
                        impossible_fires += 1
                    if t["id"] in dm_ids:
                        overlap.append(t["id"])
                    if t["pnl_pct"] >= 10:
                        kills.append((t["id"], t["token"],
                                      round(fire["hold_h"], 2)))
            key = "%s|censor=%s" % (align, censor)
            matrix[key] = dict(
                n_fires=len(fires),
                n_impossible_post_close=impossible_fires,
                net_delta=round(sum(f["delta"] for _t, f in fires), 4),
                overlap_dm=len(overlap), overlap_ids=sorted(overlap),
                n_kills=len(kills), kills=kills)
            print("%-22s fires=%2d impossible=%2d delta=$%+.2f "
                  "dm_overlap=%d %s kills=%d" %
                  (key, len(fires), impossible_fires,
                   matrix[key]["net_delta"], len(overlap),
                   sorted(overlap), len(kills)))
            for k in kills:
                print("    kill #%d %s hold=%.2fh prof=%+.2f%% vel=%.3f%%"
                      % (k[0], k[1], k[2],
                         next(f["profit"] for t, f in fires if t["id"] == k[0]),
                         next(f["vel"] for t, f in fires if t["id"] == k[0])))

    # ---- grace sweep: which (align, grace) reproduces 36 fires / 7 overlap?
    print("\nGrace sweep (target from claim: fires=36, dm_overlap=7, "
          "delta=-2.60):")
    for align in ("open", "close"):
        for grace in (0, 60, 120, 180, 240, 300, 600):
            fires, overlap, postc = [], [], 0
            for t in trades:
                fire, _ = evaluate(t, align, censor=True, grace=float(grace))
                if fire:
                    fires.append((t, fire))
                    if t["id"] in dm_ids:
                        overlap.append(t["id"])
                    if fire["post_close"]:
                        postc += 1
            print("  align=%-5s grace=%3ds -> fires=%2d (post-close %2d) "
                  "delta=$%+.2f dm_overlap=%d %s" %
                  (align, grace, len(fires), postc,
                   sum(f["delta"] for _t, f in fires), len(overlap),
                   sorted(overlap)))

    # ---- forensics on the 10 actual in-scope dead_money exits ----
    print("\nActual in-scope dead_money exits — replay behavior per config:")
    forensics = []
    for t in trades:
        if t["id"] not in dm_ids:
            continue
        row = dict(id=t["id"], token=t["token"],
                   closed=str(t["close_ts"]),
                   hold_h=round((t["close_ts"] - t["open_ts"]).total_seconds()
                                / 3600, 3))
        for align in ("close", "open"):
            fire, _ = evaluate(t, align, censor=False)
            fire_c, _ = evaluate(t, align, censor=True)
            row["align_" + align] = (None if not fire else
                                     dict(fire_at=str(fire["eval_ts"]),
                                          hold=round(fire["hold_h"], 3),
                                          post_close=fire["post_close"],
                                          lag_min=round(fire["close_lag_min"], 1),
                                          censored_hit=fire_c is not None))
        forensics.append(row)
        print("  #%d %s closed=%s hold=%.2fh | close-align: %s | "
              "open-align: %s" %
              (row["id"], row["token"], row["closed"][11:19], row["hold_h"],
               row["align_close"], row["align_open"]))
    out = dict(matrix=matrix, dead_money_forensics=forensics)
    with open("/root/.hermes/audit/dm_verify_variants.json", "w") as fh:
        json.dump(out, fh, indent=1, default=str)
    print("\nsaved: /root/.hermes/audit/dm_verify_variants.json")


if __name__ == "__main__":
    main()
