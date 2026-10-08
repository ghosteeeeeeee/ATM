#!/usr/bin/env python3
"""
dm_verify_replay.py — INDEPENDENT adversarial verification of the pump_exit
dead-money time-exit concern claim (2026-10-08).

This is a from-scratch re-implementation. It does NOT reuse any prior
analysis script. Structure: a per-trade event sweep over closed 5m bars.

Replays the LIVE rule as written in scripts/position_manager.py (lines
2791-2950, verified by reading the code):
  time exit fires at the FIRST closed 5m bar such that:
     hold_h  = (bar_close_ts - entry_ts)/3600  >  PUMP_EXIT_TIME_HOURS (2.0)
     profit  = direction-aware (close - entry)/entry*100  <  2.0
     vel     = (close_i - close_{i-1})/close_{i-1}*100    <  0   (LONG)
  Exit simulated at the bar close; sim PnL$ = profit% / 100 * amount_usdt
  (amount_usdt = NOTIONAL per system convention).

Counterfactual frame: the trade continues to its ACTUAL close (valid because
the time exit does not alter the ATR trail / HML / any other exit's price
path — the trail depends only on price, and each other rule would have fired
at the same time as it actually did). Trades are TRUNCATED at actual
close_time: no fire can occur after the trade is closed (censoring guard).

Outputs JSON to /root/.hermes/audit/dm_verify_results.json + stdout summary.
Read-only against Postgres and SQLite.
"""
import json
import os
import sqlite3
import subprocess
import sys
from datetime import datetime, timedelta, timezone

PG = "host=/var/run/postgresql dbname=brain user=postgres"
CANDLES = "/root/.hermes/data/candles.db"
OUT_JSON = "/root/.hermes/audit/dm_verify_results.json"

# Engine-live moment (code landing in position_manager.py; git 273f00a).
# Trades that opened AND closed before this could never have been touched
# by the rule in production — replaying them is anachronistic.
ENGINE_LIVE = datetime(2026, 9, 13, 20, 15, 59, tzinfo=timezone.utc)

TIME_HOURS = 2.0
TIME_THRESHOLD = 2.0
MOM_VEL = -0.5          # PUMP_EXIT_MOMENTUM_VEL (adverse = < -0.5)
MOM_CANDLES = 2

SCOPE_SQL = """
SELECT id, token, direction, entry_price, exit_price, pnl_usdt, pnl_pct,
       amount_usdt, leverage, exit_reason, open_time, close_time, strategy
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
    # open_time/close_time are 'timestamp without time zone', stored UTC.
    s = s.strip()
    if "." in s:
        return datetime.fromisoformat(s).replace(tzinfo=timezone.utc)
    return datetime.fromisoformat(s).replace(tzinfo=timezone.utc)


def load_trades():
    rows = psql_rows(SCOPE_SQL)
    trades = []
    for r in rows:
        (tid, token, direction, ep, xp, pnl, pnlpct, amt, lev, xreason,
         ot, ct, strat) = r
        trades.append(dict(
            id=int(tid), token=token.strip(), direction=direction.strip(),
            entry=float(ep), exit=float(xp) if xp not in ("", None) else None,
            pnl=float(pnl) if pnl not in ("", None) else 0.0,
            pnl_pct=float(pnlpct) if pnlpct not in ("", None) else 0.0,
            notional=float(amt), leverage=int(float(lev or 1)),
            exit_reason=(xreason or "").strip(),
            open_ts=parse_ts(ot), close_ts=parse_ts(ct),
            strategy=strat.strip()))
    return trades


def load_candles_5m(token, t0, t1):
    """Closed 5m candles, ascending by ts. ts = bar OPEN time."""
    conn = sqlite3.connect("file:%s?mode=ro" % CANDLES, uri=True, timeout=10)
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT ts, open, close FROM candles_5m "
            "WHERE token=? AND is_closed=1 AND ts>=? AND ts<=? ORDER BY ts",
            (token.upper(), int(t0), int(t1)))
        return [(int(r[0]), float(r[1]), float(r[2])) for r in cur.fetchall()]
    finally:
        conn.close()


def evaluate(trade, params):
    """Sweep closed bars; return per-bar series + first fire + features.

    params: dict with keys time_hours, threshold, exempt_ge (or None).
    All comparisons STRICT, matching the live code.
    """
    entry_ts = trade["open_ts"].timestamp()
    close_ts = trade["close_ts"].timestamp()
    entry = trade["entry"]
    notional = trade["notional"]
    long_side = trade["direction"] == "LONG"

    bars = load_candles_5m(trade["token"], entry_ts - 1200, close_ts + 600)

    series = []          # per eligible bar
    fire = None
    max_profit = None    # running max direction-aware profit (for exemptions)
    first_mom_bar = None # first bar where MOMENTUM exit would have fired
    mom_bar_at_fire = None

    for idx in range(1, len(bars)):
        ts_o, _op, c = bars[idx]
        _po, prev_c = bars[idx - 1][0], bars[idx - 1][2]
        bar_close_ts = ts_o + 300.0
        if bar_close_ts < entry_ts:
            continue                    # bar closed before we were in the trade
        if bar_close_ts > close_ts + 1.0:
            break                       # CENSORING GUARD: trade already closed
        hold_h = (bar_close_ts - entry_ts) / 3600.0
        raw_move = (c - entry) / entry * 100.0
        profit = raw_move if long_side else -raw_move
        vel = (c - prev_c) / prev_c * 100.0
        if max_profit is None or profit > max_profit:
            max_profit = profit
        # momentum exit condition (both newest intervals adverse beyond -0.5)
        mom = False
        if idx >= 2:
            c2 = bars[idx - 2][2]
            v_prev = (prev_c - c2) / c2 * 100.0
            mom = (vel < MOM_VEL) and (v_prev < MOM_VEL)
        if first_mom_bar is None and mom:
            first_mom_bar = idx

        rec = dict(idx=idx, bar_close=datetime.fromtimestamp(
                       bar_close_ts, tz=timezone.utc), hold_h=hold_h,
                   profit=profit, vel=vel, mom=mom, close=c)
        series.append(rec)

        if fire is None and hold_h > params.get("time_hours", TIME_HOURS) \
                and profit < params.get("threshold", TIME_THRESHOLD) \
                and vel < 0:
            if params.get("exempt_ge") is not None and \
                    max_profit >= params["exempt_ge"]:
                pass  # exemption: trade already showed strength, never kill
            else:
                fire = dict(rec)
                fire["sim_usdt"] = profit / 100.0 * notional
                fire["delta_usdt"] = fire["sim_usdt"] - trade["pnl"]

    return series, fire, first_mom_bar, max_profit


def main():
    trades = load_trades()
    res = {"generated": datetime.now(timezone.utc).isoformat(),
           "n_scope": len(trades)}

    # ---------- BASELINE REPLAY (claims 2,3,4) + attack features ----------
    fires = []
    rows = []
    for t in trades:
        series, fire, mom_bar, maxp = evaluate(
            t, dict(time_hours=TIME_HOURS, threshold=TIME_THRESHOLD))
        entry_min_ts = (t["open_ts"].timestamp() - 1200) // 300
        hr = t["pnl_pct"] >= 10
        rows.append(dict(id=t["id"], token=t["token"], hr=hr,
                         exit_reason=t["exit_reason"], pnl=t["pnl"],
                         pnl_pct=t["pnl_pct"], n_bars=len(series),
                         fired=fire is not None, max_profit=maxp,
                         anachronistic_open=t["close_ts"] < ENGINE_LIVE))
        if fire:
            fired = dict(fire)
            fired.update(
                id=t["id"], token=t["token"], hr=hr, pnl=t["pnl"],
                pnl_pct=t["pnl_pct"],
                notional=t["notional"], exit_reason=t["exit_reason"],
                actual_close=t["close_ts"],
                fired_iso=datetime.isocalendar(fired["bar_close"]),
                entry_iso=datetime.isocalendar(t["open_ts"]),
                opened=t["open_ts"],
                anachronistic_open=t["close_ts"] < ENGINE_LIVE,
                exit_after_fire=t["close_ts"] > fired["bar_close"],
                lag_h=(t["close_ts"] - fired["bar_close"]).total_seconds() / 3600)
            # velocity context (attack c)
            si = [s for s in series if s["idx"] == fire["idx"]][0]
            k = series.index(si)
            fired["vel_prev"] = series[k - 1]["vel"] if k >= 1 else None
            fired["vel_next"] = series[k + 1]["vel"] if k + 1 < len(series) else None
            fired["mom_before_fire"] = (mom_bar is not None and
                                        mom_bar < fire["idx"])
            fired["mom_at_fire"] = bool(si["mom"])
            # profit persistence: consecutive bars (incl fire, backwards)
            # below threshold
            n_below = 0
            for s in reversed(series[:k + 1]):
                if s["profit"] < TIME_THRESHOLD:
                    n_below += 1
                else:
                    break
            fired["bars_below_thresh_run"] = n_below
            fires.append(fired)

    fired_ids = {f["id"] for f in fires}
    actual_dm = [t for t in trades if t["exit_reason"] == "pump_exit_dead_money"]
    overlap = sorted(fired_ids & {t["id"] for t in actual_dm})

    tot_delta = sum(f["delta_usdt"] for f in fires)
    winners = [f for f in fires if f["pnl"] > 0]
    losers = [f for f in fires if f["pnl"] <= 0]
    wk = {}
    for f in fires:
        wk[f["fired_iso"][1]] = wk.get(f["fired_iso"][1], 0) + 1

    res["baseline"] = dict(
        n_fires=len(fires),
        total_delta=round(tot_delta, 4),
        delta_winners=round(sum(f["delta_usdt"] for f in winners), 4),
        delta_losers=round(sum(f["delta_usdt"] for f in losers), 4),
        n_fired_winners=len(winners),
        actual_dead_money=len(actual_dm),
        overlap_actual_dm=len(overlap), overlap_ids=overlap,
        fires_by_iso_week={str(k): v for k, v in sorted(wk.items())},
        wk40_41=sum(v for k, v in wk.items() if k in (40, 41)),
        n_fires_anachronistic=sum(1 for f in fires if f["anachronistic_open"]),
        delta_anachronistic=round(sum(f["delta_usdt"] for f in fires
                                      if f["anachronistic_open"]), 4),
        all_exits_after_fire=all(f["exit_after_fire"] for f in fires),
        min_lag_h=round(min(f["lag_h"] for f in fires), 3),
    )

    # kills = fires on home-run trades
    kills = [f for f in fires if f["hr"]]
    res["kills"] = [
        dict(id=f["id"], token=f["token"], opened=str(f["opened"]),
             fired_at=str(f["bar_close"]), hold_h=round(f["hold_h"], 2),
             profit_pct=round(f["profit"], 2), vel_pct=round(f["vel"], 3),
             vel_prev=(round(f["vel_prev"], 3) if f["vel_prev"] is not None else None),
             vel_next=(round(f["vel_next"], 3) if f["vel_next"] is not None else None),
             mom_before_fire=f["mom_before_fire"], mom_at_fire=f["mom_at_fire"],
             bars_below_run=f["bars_below_thresh_run"],
             actual_exit=f["exit_reason"], actual_close=str(f["actual_close"]),
             actual_pnl_pct=f["pnl_pct"], actual_usdt=f["pnl"],
             sim_usdt=round(f["sim_usdt"], 4),
             gave_up=round(-f["delta_usdt"], 4),
             lag_fire_to_close_h=round(f["lag_h"], 2),
             anachronistic_open=f["anachronistic_open"],
             fired_iso_week=f["fired_iso"][1])
        for f in sorted(kills, key=lambda x: -x["pnl"])]

    # top-5 delta contributors (attack f)
    by_abs = sorted(fires, key=lambda f: f["delta_usdt"])
    res["top5_negative"] = [dict(id=f["id"], token=f["token"], hr=f["hr"],
                                 exit_reason=f["exit_reason"],
                                 profit_at_fire=round(f["profit"], 2),
                                 actual_usdt=f["pnl"],
                                 delta=round(f["delta_usdt"], 4))
                            for f in by_abs[:5]]
    res["top5_positive"] = [dict(id=f["id"], token=f["token"], hr=f["hr"],
                                 exit_reason=f["exit_reason"],
                                 profit_at_fire=round(f["profit"], 2),
                                 actual_usdt=f["pnl"],
                                 delta=round(f["delta_usdt"], 4))
                            for f in by_abs[-5:][::-1]]

    # exit-family breakdown (attack e)
    fam = {}
    LOSS_FAM = ("hard_max_loss", "cut-loser", "HML")
    for f in fires:
        er = f["exit_reason"]
        if any(x in er for x in LOSS_FAM):
            key = "loss_kill_family"
        elif er in ("atr_sl_hit", "atr_trail_hit", "profit-monster-trail"):
            key = "trail_ride_family"
        else:
            key = er or "unknown"
        fam.setdefault(key, [0, 0.0])
        fam[key][0] += 1
        fam[key][1] += f["delta_usdt"]
    res["fired_exit_families"] = {k: [v[0], round(v[1], 4)]
                                  for k, v in fam.items()}

    # momentum preemption (attack g)
    preempted = [f for f in fires if f["mom_before_fire"]]
    res["momentum_preemption"] = dict(
        n_preempted=len(preempted),
        preempted_ids=[f["id"] for f in preempted],
        delta_excl_preempted=round(tot_delta - sum(f["delta_usdt"]
                                                   for f in preempted), 4),
        n_preempted_kills=sum(1 for f in preempted if f["hr"]),
    )
    # recompute rule with momentum BEFORE time (production ordering):
    # fire only if no momentum bar strictly before the fire bar
    fires_ordered = [f for f in fires if not f["mom_before_fire"]]
    res["momentum_preemption"]["delta_prod_ordering"] = round(
        sum(f["delta_usdt"] for f in fires_ordered), 4)
    res["momentum_preemption"]["n_prod_ordering_fires"] = len(fires_ordered)

    # anachronism-adjusted (post-engine trades only)
    post = [f for f in fires if not f["anachronistic_open"]]
    res["baseline"]["delta_post_engine_only"] = round(
        sum(f["delta_usdt"] for f in post), 4)
    res["baseline"]["n_fires_post_engine"] = len(post)
    res["baseline"]["kills_post_engine"] = sum(1 for f in post if f["hr"])

    # ---------- CLAIM 5: premise test ----------
    premise = {}
    for align in ("floor", "ceil"):
        below, below_hr, have_data = 0, 0, 0
        hr_below_ids = []
        for t in trades:
            entry_ts = t["open_ts"].timestamp()
            t2 = entry_ts + TIME_HOURS * 3600
            if t["close_ts"].timestamp() <= t2 + 1.0:
                continue  # trade closed before the 2h point: no state at 2h
            bars = load_candles_5m(t["token"], t2 - 900, t2 + 900)
            closes = [(ts + 300.0, c) for ts, _o, c in bars]
            closes = [x for x in closes if x[0] <= t["close_ts"].timestamp() + 1.0]
            if not closes:
                continue
            if align == "floor":
                elig = [x for x in closes if x[0] <= t2]
                if not elig or elig[-1][0] <= t2 - 300.0:
                    continue          # no bar within 5m before the 2h point
                px = elig[-1][1]
            else:
                elig = [x for x in closes if x[0] >= t2]
                if not elig or elig[0][0] >= t2 + 300.0:
                    continue          # no bar within 5m after the 2h point
                px = elig[0][1]
            have_data += 1
            move = (px - t["entry"]) / t["entry"] * 100.0
            prof = move if t["direction"] == "LONG" else -move
            if prof < TIME_THRESHOLD:
                below += 1
                if t["pnl_pct"] >= 10:
                    below_hr += 1
                    hr_below_ids.append(t["id"])
        premise[align] = dict(n_below=below, n_with_data=have_data,
                              hr_in_subset=below_hr, hr_ids=hr_below_ids,
                              rate=round(100.0 * below_hr / below, 2)
                              if below else None)
    premise["baseline_hr_rate_pct"] = round(
        100.0 * sum(1 for t in trades if t["pnl_pct"] >= 10) / len(trades), 2)
    res["premise_2h"] = premise

    # ---------- CLAIM 6: fix variants ----------
    variants = {}
    for name, params in [
            ("thresh0", dict(time_hours=TIME_HOURS, threshold=0.0)),
            ("time3h", dict(time_hours=3.0, threshold=TIME_THRESHOLD)),
            ("exempt_ge2", dict(time_hours=TIME_HOURS,
                                threshold=TIME_THRESHOLD, exempt_ge=2.0)),
            ("exempt_ge1", dict(time_hours=TIME_HOURS,
                                threshold=TIME_THRESHOLD, exempt_ge=1.0))]:
        vf = []
        for t in trades:
            _s, fire, _m, _p = evaluate(t, params)
            if fire:
                vf.append((t, fire))
        vkills = [(t["id"], t["token"]) for t, f in vf if t["pnl_pct"] >= 10]
        variants[name] = dict(
            n_fires=len(vf),
            net_delta=round(sum(f["delta_usdt"] for _t, f in vf), 4),
            kills=vkills)
    res["variants"] = variants

    # ---------- CLAIM 7: post-fire drift of ALL actual dead_money exits ----------
    all_dm = psql_rows(
        "SELECT id, token, direction, exit_price, close_time FROM trades "
        "WHERE status='closed' AND exit_reason='pump_exit_dead_money' "
        "AND paper=false")
    drift = []
    for tid, token, direction, xp, ct in all_dm:
        if xp in ("", None):
            continue
        xp = float(xp)
        cts = parse_ts(ct).timestamp()
        bars = load_candles_5m(token, cts - 300, cts + 3900)
        closes = [(ts + 300.0, c) for ts, _o, c in bars]
        after = [x for x in closes if x[0] >= cts + 1800]   # >= 30 min
        if not after:
            continue
        at60 = [x for x in closes if x[0] >= cts + 3600]
        px = (at60[0][1] if at60 else after[-1][1])
        d = (px - xp) / xp * 100.0
        if direction != "LONG":
            d = -d  # direction-aware: positive = price moved our way post-exit
        drift.append(dict(id=int(tid), token=token, direction=direction,
                          drift_pct=round(d, 3)))
    dd = sorted(x["drift_pct"] for x in drift)
    med = dd[len(dd) // 2] if dd else None
    res["post_exit_drift"] = dict(
        n=len(drift),
        recovered_gt_0_3=sum(1 for x in drift if x["drift_pct"] > 0.3),
        adverse_lt_m0_3=sum(1 for x in drift if x["drift_pct"] < -0.3),
        flat=sum(1 for x in drift if -0.3 <= x["drift_pct"] <= 0.3),
        median=med, detail=drift)

    res["rows"] = rows
    res["fires"] = [dict(f, bar_close=str(f["bar_close"]),
                         actual_close=str(f["actual_close"]),
                         opened=str(f["opened"]))
                    for f in fires]

    with open(OUT_JSON, "w") as fh:
        json.dump(res, fh, indent=1, default=str)

    # ---------- stdout summary ----------
    b = res["baseline"]
    print("SCOPE n=%d  HR(pnl_pct>=10)=%d" %
          (len(trades), sum(1 for t in trades if t["pnl_pct"] >= 10)))
    print("FIRES=%d  net_delta=$%+.2f  (winners n=%d $%+.2f | losers n=%d $%+.2f)"
          % (b["n_fires"], b["total_delta"], b["n_fired_winners"],
             b["delta_winners"], len(losers), b["delta_losers"]))
    print("overlap with actual dead_money=%d %s" %
          (b["overlap_actual_dm"], b["overlap_ids"]))
    print("exits after fire: %s (min lag %.2fh)" %
          (b["all_exits_after_fire"], b["min_lag_h"]))
    print("fires by iso week:", b["fires_by_iso_week"], " wk40+41:",
          b["wk40_41"])
    print("anachronistic fires (closed before engine live): %d  delta=$%+.2f"
          % (b["n_fires_anachronistic"], b["delta_anachronistic"]))
    print("post-engine-only: fires=%d delta=$%+.2f kills=%d"
          % (b["n_fires_post_engine"], b["delta_post_engine_only"],
             b["kills_post_engine"]))
    print("KILLS n=%d:" % len(kills))
    for k in res["kills"]:
        print("  #%d %s hold=%.2fh prof=%+.2f%% vel=%.3f%% (prev %s next %s) "
              "momBefore=%s run=%d actual=%s %+.1f%%/$%+.2f sim=$%+.2f "
              "gaveUp=$%.2f lag=%.1fh anach=%s wk%d" %
              (k["id"], k["token"], k["hold_h"], k["profit_pct"], k["vel_pct"],
               k["vel_prev"], k["vel_next"], k["mom_before_fire"],
               k["bars_below_run"], k["actual_exit"], k["actual_pnl_pct"],
               k["actual_usdt"], k["sim_usdt"], k["gave_up"],
               k["lag_fire_to_close_h"], k["anachronistic_open"],
               k["fired_iso_week"]))
    print("premise(floor):", premise["floor"])
    print("premise(ceil):", premise["ceil"])
    print("variants:", json.dumps(variants, default=str))
    print("families:", res["fired_exit_families"])
    print("top5 neg:", res["top5_negative"])
    print("momentum preemption:", res["momentum_preemption"])
    print("drift:", {k: v for k, v in res["post_exit_drift"].items()
                     if k != "detail"})
    print("saved:", OUT_JSON)


if __name__ == "__main__":
    main()
