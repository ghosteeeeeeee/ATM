#!/usr/bin/env python3
"""
dm_verify_final.py — closing computations for the dead-money audit.

1. ERA SPLIT: the dead-money time exit was broken (datetime TypeError,
   swallowed by except:pass) from engine commit (Sep 13) until commit
   8c09684b landed (first observed fire 2026-09-21 15:05:52). Split the
   clean 29-fire replay into era1 (fires on trades closed before the fix)
   and era2 (after) — kills and dollars per era.
2. CLAIM-CONFIG reproduction (align=open, grace=300s) with iso-week,
   winner/loser and family breakdown + post-close count (verifies claim 4
   sub-numbers under the claim's own methodology).
3. PREMISE count "all 147 regardless of closed status" (floor/ceil at 2h)
   to explain the claim's 116/88 figures.
4. Era2 home runs (ME/CRV/IMX): did the replay fire on any? (forward-looking
   kill test in the era where the rule actually worked)
5. Realized cost of the 10 ACTUAL live dead_money exits: exit vs MFE.
"""
import json
import sqlite3
import subprocess
from datetime import datetime, timezone

PG = "host=/var/run/postgresql dbname=brain user=postgres"
CANDLES = "/root/.hermes/data/candles.db"
FIX_TS = datetime(2026, 9, 21, 15, 5, 52, tzinfo=timezone.utc).timestamp()


def psql_rows(sql):
    out = subprocess.run(["psql", PG, "-t", "-A", "-F", "\t", "-c", sql],
                         capture_output=True, text=True, check=True)
    return [ln.split("\t") for ln in out.stdout.strip().split("\n") if ln]


def parse_ts(s):
    return datetime.fromisoformat(s.strip()).replace(tzinfo=timezone.utc)


def candles5(token, t0, t1):
    c = sqlite3.connect("file:%s?mode=ro" % CANDLES, uri=True, timeout=10)
    try:
        return [(int(a), float(b)) for a, b in c.execute(
            "SELECT ts, close FROM candles_5m WHERE token=? AND is_closed=1 "
            "AND ts>=? AND ts<=? ORDER BY ts",
            (token.upper(), int(t0), int(t1))).fetchall()]
    finally:
        c.close()


def load_trades(scope=True):
    sql = ("SELECT id, token, direction, entry_price, pnl_usdt, pnl_pct, "
           "amount_usdt, exit_reason, open_time, close_time, mfe_pct "
           "FROM trades WHERE paper=false AND status='closed' ")
    if scope:
        sql += ("AND (strategy LIKE '%%pump-chain+%%' OR "
                "strategy LIKE '%%pump_chain+%%' OR strategy='pump_chain') ")
    sql += "ORDER BY open_time"
    out = []
    for r in psql_rows(sql):
        (tid, token, direction, ep, pnl, pnlpct, amt, xreason, ot, ct, mfe) = r
        out.append(dict(
            id=int(tid), token=token.strip(), direction=direction.strip(),
            entry=float(ep), pnl=float(pnl or 0), pnl_pct=float(pnlpct or 0),
            notional=float(amt), exit_reason=(xreason or "").strip(),
            open_ts=parse_ts(ot), close_ts=parse_ts(ct),
            mfe=float(mfe) if mfe not in ("", None) else None))
    return out


def evaluate(t, align="close", censor=True, grace=0.0,
             time_h=2.0, thr=2.0, exempt_ge=None):
    entry_ts = t["open_ts"].timestamp()
    close_ts = t["close_ts"].timestamp()
    entry, long_side = t["entry"], t["direction"] == "LONG"
    bars = candles5(t["token"], entry_ts - 1200,
                    max(close_ts, entry_ts) + 7200)
    maxp = None
    for i in range(1, len(bars)):
        ts_o, c = bars[i]
        prev = bars[i - 1][1]
        ev = ts_o + (300.0 if align == "close" else 0.0)
        if ev < entry_ts:
            continue
        post = ev > close_ts + 1.0
        if post and ev > close_ts + grace + 1.0:
            if censor:
                break
        hold = (ev - entry_ts) / 3600.0
        raw = (c - entry) / entry * 100.0
        prof = raw if long_side else -raw
        vel = (c - prev) / prev * 100.0
        maxp = prof if maxp is None or prof > maxp else maxp
        if hold > time_h and prof < thr and vel < 0:
            if exempt_ge is not None and maxp >= exempt_ge:
                continue
            sim = prof / 100.0 * t["notional"]
            return dict(eval=ev, hold=hold, prof=prof, vel=vel,
                        sim=sim, delta=sim - t["pnl"], post=post)
    return None


def iso_week(dt):
    return datetime.isocalendar(dt)[1]


def main():
    trades = load_trades(scope=True)

    # ---- 1. era split of clean replay (align=close, censor=True) ----------
    era = {"pre_fix": [], "post_fix": []}
    for t in trades:
        f = evaluate(t)
        if f:
            key = "post_fix" if t["close_ts"].timestamp() >= FIX_TS else "pre_fix"
            era[key].append((t, f))
    for k, v in era.items():
        d = sum(f["delta"] for _t, f in v)
        hr = [(t["id"], t["token"], round(f["delta"], 3))
              for t, f in v if t["pnl_pct"] >= 10]
        print("ERA %s: fires=%d delta=$%+.2f kills=%s" %
              (k, len(v), d, hr))
    era2_fire_ids = {t["id"] for t, f in era["post_fix"]}
    print("era2 fired ids:", sorted(era2_fire_ids))

    # ---- 2. claim-config details ------------------------------------------
    fires = []
    for t in trades:
        f = evaluate(t, align="open", censor=True, grace=300.0)
        if f:
            fires.append((t, f))
    wk, win_d, lose_d, nwin, nlose, postc = {}, 0.0, 0.0, 0, 0, 0
    fam = {}
    for t, f in fires:
        w = iso_week(t["open_ts"])
        wk[w] = wk.get(w, 0) + 1
        if f["post"]:
            postc += 1
        if t["pnl"] > 0:
            nwin += 1
            win_d += f["delta"]
        else:
            nlose += 1
            lose_d += f["delta"]
        er = t["exit_reason"]
        fam[er] = fam.get(er, 0) + 1
    print("CLAIM-CFG fires=%d wk(by entry)=%s post_close=%d winners=%d "
          "$%+.2f losers=%d $%+.2f families=%s" %
          (len(fires), {str(k): v for k, v in sorted(wk.items())}, postc,
           nwin, win_d, nlose, lose_d, fam))
    # weeks by FIRE time as well
    wkf = {}
    for t, f in fires:
        w = iso_week(datetime.fromtimestamp(f["eval"], tz=timezone.utc))
        wkf[w] = wkf.get(w, 0) + 1
    print("CLAIM-CFG fires by FIRE-time iso week:", wkf,
          " wk40+41:", wkf.get(40, 0) + wkf.get(41, 0))

    # ---- 3. premise on all 147 regardless of close ------------------------
    for align in ("floor", "ceil"):
        below, hr_below, n_data = 0, 0, 0
        for t in trades:
            t2 = t["open_ts"].timestamp() + 7200.0
            bars = candles5(t["token"], t2 - 900, t2 + 900)
            closes = [(ts + 300.0, c) for ts, c in bars]
            if align == "floor":
                elig = [x for x in closes if x[0] <= t2]
                if not elig or elig[-1][0] <= t2 - 300.0:
                    continue
                px = elig[-1][1]
            else:
                elig = [x for x in closes if x[0] >= t2]
                if not elig or elig[0][0] >= t2 + 300.0:
                    continue
                px = elig[0][1]
            n_data += 1
            prof = (px - t["entry"]) / t["entry"] * 100.0
            if t["direction"] != "LONG":
                prof = -prof
            if prof < 2.0:
                below += 1
                if t["pnl_pct"] >= 10:
                    hr_below += 1
        print("PREMISE-all147(%s): with_data=%d below2%%=%d HR_in=%d" %
              (align, n_data, below, hr_below))

    # ---- 4. era2 home runs: any replay fire? ------------------------------
    print("ERA2 HRs (pnl_pct>=10, closed after fix):")
    for t in trades:
        if t["pnl_pct"] >= 10 and t["close_ts"].timestamp() >= FIX_TS:
            f = evaluate(t)
            print("   #%d %s hold=%.2fh fired=%s %s" %
                  (t["id"], t["token"],
                   (t["close_ts"] - t["open_ts"]).total_seconds() / 3600,
                   f is not None,
                   "" if not f else "prof=%.2f%% delta=$%+.2f" %
                   (f["prof"], f["delta"])))

    # ---- 5. realized cost of actual live dead_money exits (MFE vs exit) ---
    print("ACTUAL dead_money exits: exit vs MFE (direction-aware, unleveraged):")
    rows = psql_rows(
        "SELECT id, token, direction, pnl_pct, mfe_pct, exit_conditions "
        "FROM trades WHERE paper=false AND status='closed' "
        "AND exit_reason='pump_exit_dead_money' AND strategy LIKE '%pump-chain+%' "
        "ORDER BY close_time")
    tot_left = 0.0
    for tid, token, direction, pnlpct, mfe, xcond in rows:
        mfe = float(mfe) if mfe not in ("", None) else None
        pp = float(pnlpct or 0)
        left = (mfe - pp) if mfe is not None else None
        if left is not None:
            tot_left += left
        print("   #%s %s exit_pnl_pct=%.2f mfe_pct=%s left=%.2fpp %s" %
              (tid, token, pp, mfe, left if left is not None else float('nan'),
               xcond or ""))
    print("   sum of pnl_pct left on table (leverage-multiplied pp): %.2f"
          % tot_left)


if __name__ == "__main__":
    main()
