#!/usr/bin/env python3
"""Stop-cluster counterfactual study — atr-trend shadow signal (ANALYSIS ONLY).

Replays static stop widths S over the closed atr-trend trades using path-worst
adverse excursion (mae_pct / highest-lowest wick extremes), in pnl_pct (margin)
units — the same space the checkpoint quotes "stops −3~−6%" and "winners
+1~3%" in.

Run:  python3 brain/analysis/atr_trend_stop_cluster_20261109.py
Reads PostgreSQL brain.trades, writes nothing, prints all tables to stdout.

Unit identities verified against the data (see UNIT CHECKS table):
  pnl_usdt  = raw_move_pct * amount_usdt / 100   (amount_usdt = NOTIONAL;
              confirmed: fee_total/amount ~ 4.6 bps = HL taker fee on notional)
  pnl_pct   = raw_move_pct * leverage            (return on margin) for 45/47
              rows; hard_tp / hard_sl rows store raw*1 instead (data wart)
  mfe_pct, mae_pct, highest/lowest extremes = RAW price pct
  margin pct = raw pct * leverage;  raw threshold for a margin stop S: S/leverage
"""
import json
import statistics

import psycopg2

WIDTHS = [0.75, 1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 6.0]
CHECKPOINT = dict(n=47, wr=57.4, net=-0.63, pm=1.12, stops=-1.97)


def fetch():
    conn = psycopg2.connect(host="/var/run/postgresql", database="brain", user="postgres")
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT id, open_time, close_time, direction, leverage, amount_usdt,
                   pnl_usdt, pnl_pct, entry_price, exit_price, stop_loss,
                   exit_reason, mfe_pct, mae_pct, highest_price, lowest_price,
                   volatility_regime, confidence, fees
            FROM trades
            WHERE signal LIKE 'atr-trend%' AND status='closed'
            ORDER BY open_time
        """)
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, r)) for r in cur.fetchall()]
    finally:
        conn.close()


def enrich(rows):
    for r in rows:
        e, x = float(r["entry_price"]), float(r["exit_price"])
        d = 1.0 if r["direction"] == "LONG" else -1.0
        r["raw_loss"] = (x - e) / e * 100.0 * d          # signed raw move, % of price
        r["fav_raw"] = -r["raw_loss"] if r["raw_loss"] < 0 else 0.0
        # adverse extremes vs entry (raw price %)
        hi, lo = float(r["highest_price"]), float(r["lowest_price"])
        wick = (hi - e) / e * 100.0 if r["direction"] == "SHORT" else (e - lo) / e * 100.0
        mae = float(r["mae_pct"])
        r["worst_A"] = max(mae, wick)                     # recorded path-worst
        r["worst_B"] = max(r["worst_A"], -r["raw_loss"])  # + the exit itself (a loss IS an adverse point)
        r["fees_total"] = parse_fees(r["fees"])
    return rows


def parse_fees(f):
    if f is None:
        return None
    if isinstance(f, (int, float)):
        return float(f)
    try:
        j = json.loads(f)
    except (ValueError, TypeError):
        return None
    if isinstance(j, dict):
        return float(j.get("fee_total", 0.0) or 0.0)
    return float(j)


def table(headers, rows, aligns=None):
    aligns = aligns or ["<"] * len(headers)
    widths = [max(len(str(h)), *(len(str(r[i])) for r in rows)) for i, h in enumerate(headers)]
    line = "  ".join(str(h).ljust(w) if a == "<" else str(h).rjust(w)
                     for h, w, a in zip(headers, widths, aligns))
    print(line)
    print("-" * len(line))
    for r in rows:
        print("  ".join(str(c).ljust(w) if a == "<" else str(c).rjust(w)
                        for c, w, a in zip(r, widths, aligns)))


def q(vals, p):
    if not vals:
        return float("nan")
    return statistics.quantiles(vals, n=100, method="inclusive")[p - 1] if len(vals) >= 4 else sorted(vals)[min(len(vals) - 1, int(p / 100 * len(vals)))]


def baseline(rows):
    n = len(rows)
    wins = sum(1 for r in rows if r["pnl_usdt"] > 0)
    loss = sum(1 for r in rows if r["pnl_usdt"] < 0)
    scratch = n - wins - loss
    net = sum(float(r["pnl_usdt"]) for r in rows)
    psum = sum(float(r["pnl_pct"]) for r in rows)
    return n, wins, loss, scratch, net, psum


def exit_anatomy(rows):
    total = sum(float(r["pnl_usdt"]) for r in rows)
    absflow = sum(abs(float(r["pnl_usdt"])) for r in rows)
    out = []
    for reason in sorted({r["exit_reason"] for r in rows},
                         key=lambda s: -sum(float(x["pnl_usdt"]) for x in rows if x["exit_reason"] == s)):
        g = [r for r in rows if r["exit_reason"] == reason]
        w = sum(1 for r in g if r["pnl_usdt"] > 0)
        usd = sum(float(r["pnl_usdt"]) for r in g)
        pct = sum(float(r["pnl_pct"]) for r in g)
        out.append([reason, len(g), w, f"{w / len(g) * 100:.1f}%", f"{usd:+.2f}",
                    f"{pct:+.2f}", f"{usd / absflow * 100:+.1f}%", f"{usd / total * 100 if total else 0:+.0f}%"])
    out.append(["TOTAL", len(rows), sum(1 for r in rows if r["pnl_usdt"] > 0),
                f"{sum(1 for r in rows if r['pnl_usdt'] > 0) / len(rows) * 100:.1f}%",
                f"{total:+.2f}", f"{sum(float(r['pnl_pct']) for r in rows):+.2f}",
                "100.0%", "—"])
    return out


def unit_checks(rows):
    print("\n== UNIT CHECKS (identity verification) ==")
    ident_bad, basis_rows, fee_bps = [], [], []
    for r in rows:
        exp = r["raw_loss"] * float(r["amount_usdt"]) / 100.0
        if abs(round(exp, 2) - float(r["pnl_usdt"])) > 0.005 + 1e-9:
            ident_bad.append((r["id"], r["exit_reason"], f"{r['raw_loss']:+.4f}",
                              f"{exp:+.4f}", f"{float(r['pnl_usdt']):+.2f}",
                              f"{float(r['pnl_pct']):+.4f}",
                              f"{r['fees_total'] if r['fees_total'] is not None else 'NA'}"))
        if r["fees_total"]:
            fee_bps.append(r["fees_total"] / float(r["amount_usdt"]) * 10000)
        lev = float(r["leverage"])
        raw = r["raw_loss"]
        if abs(raw) > 0.1:
            m_ok = abs(float(r["pnl_pct"]) - raw * lev) < 0.01
            n_ok = abs(float(r["pnl_pct"]) - raw) < 0.01
            if m_ok and not n_ok:
                continue
            basis_rows.append((r["id"], r["exit_reason"], f"{raw:+.4f}",
                               f"{float(r['pnl_pct']):+.4f}", f"raw*{lev:g}" if n_ok else "NEITHER"))
    table(["id", "exit_reason", "raw%", "pnl_usdt exp", "pnl_usdt stored", "pnl_pct", "fee_total"],
          ident_bad or [["—", "all 47 match round(raw*amount/100,2)", "", "", "", "", ""]])
    print(f"\nfee bps on amount_usdt: median {statistics.median(fee_bps):.1f} "
          f"(n={len(fee_bps)}) -> amount_usdt is NOTIONAL at ~HL taker rate")
    table(["id", "exit_reason", "raw%", "pnl_pct stored", "basis"],
          basis_rows or [["—", "all margin basis", "", "", ""]])
    # mfe sanity: MFE must be >= favorable exit move for winners
    bad = [r["id"] for r in rows
           if r["raw_loss"] > 0 and float(r["mfe_pct"]) + 1e-9 < r["raw_loss"]]
    print(f"mfe_pct < favorable exit move (impossible if raw): {bad or 'none'} -> mfe_pct is raw price %")
    wick_vs_mae = [(r["id"], round(r["worst_A"] - float(r["mae_pct"]), 4))
                   for r in rows if abs(r["worst_A"] - float(r["mae_pct"])) > 1e-9]
    print(f"rows where wick extreme != mae_pct (use max of both): {wick_vs_mae or 'none'}")


def sweep(rows, variant, widths=WIDTHS):
    """variant: 'A' = recorded path-worst (mae/wick), 'B' = A + realized loss as floor."""
    res = []
    for S in widths:
        total = pctsum = 0.0
        wins = touched = killed = 0
        gain_loser = cost_winner = 0.0
        detail = []
        for r in rows:
            raw_S = S / float(r["leverage"])
            worst = r["worst_" + variant]
            if worst >= raw_S - 1e-12:
                cf_usdt = -S * float(r["amount_usdt"]) / (100.0 * float(r["leverage"]))
                cf_pct = -S
                touched += 1
                delta = cf_usdt - float(r["pnl_usdt"])
                if float(r["pnl_usdt"]) > 0:
                    killed += 1
                    cost_winner += delta
                else:
                    gain_loser += delta
                detail.append((r["id"], r["exit_reason"], r["volatility_regime"], r["direction"],
                               f"{float(r['pnl_pct']):+.2f}", f"{worst:.3f}",
                               f"{raw_S:.3f}", f"{cf_usdt:+.3f}"))
            else:
                cf_usdt, cf_pct = float(r["pnl_usdt"]), float(r["pnl_pct"])
            total += cf_usdt
            pctsum += cf_pct
            if cf_usdt > 0:
                wins += 1
        res.append(dict(S=S, n=len(rows), wr=wins / len(rows) * 100, net=total,
                        avg_pct=pctsum / len(rows), touched=touched, killed=killed,
                        gain_loser=gain_loser, cost_winner=cost_winner, detail=detail))
    return res


def print_sweep(title, res):
    print(f"\n== {title} ==")
    table(["S%", "n", "WR%", "net $", "avg pnl_pct%", "touched", "winners killed",
           "losers capped $", "winners cost $", "vs base $"],
          [[f"{r['S']:.2f}", r["n"], f"{r['wr']:.1f}", f"{r['net']:+.2f}",
            f"{r['avg_pct']:+.2f}", r["touched"], r["killed"],
            f"{r['gain_loser']:+.2f}", f"{r['cost_winner']:+.2f}",
            f"{r['net'] - BASE_NET:+.2f}"] for r in res],
          ["<", ">", ">", ">", ">", ">", ">", ">", ">", ">"])


def main():
    global BASE_NET
    rows = enrich(fetch())
    n, wins, loss, scratch, net, psum = baseline(rows)
    BASE_NET = net
    print(f"== BASELINE (n={n}) ==")
    table(["metric", "value", "checkpoint", "match"],
          [["closed n", n, CHECKPOINT["n"], "OK" if n == CHECKPOINT["n"] else "DIFF"],
           ["W/L/scratch", f"{wins}/{loss}/{scratch}", "27/19/1", "OK" if (wins, loss, scratch) == (27, 19, 1) else "DIFF"],
           ["WR %", f"{wins / n * 100:.1f}", CHECKPOINT["wr"], "OK" if abs(wins / n * 100 - CHECKPOINT["wr"]) < 0.05 else "DIFF"],
           ["sum pnl_usdt", f"{net:+.2f}", CHECKPOINT["net"], "OK" if abs(net - CHECKPOINT["net"]) < 0.005 else "DIFF"],
           ["sum pnl_pct", f"{psum:+.2f}", "-25.0", "OK" if abs(psum + 25.0) < 0.05 else "DIFF"],
           ["avg pnl_pct", f"{psum / n:+.2f}", "-0.53", "OK"]])
    pm = [r for r in rows if r["exit_reason"] == "profit-monster-trail"]
    stops = [r for r in rows if r["exit_reason"] in
             ("hard_max_loss", "atr_sl_hit", "cut-loser-CL-T1", "hard_sl", "stale_exit")]
    pm_usd = sum(float(r["pnl_usdt"]) for r in pm)
    st_usd = sum(float(r["pnl_usdt"]) for r in stops)
    print(f"PM-trail: n={len(pm)} ${pm_usd:+.2f} (ckpt +$1.12) | "
          f"stop cluster: n={len(stops)} ${st_usd:+.2f} (ckpt -$1.97)")
    fees = [r["fees_total"] for r in rows if r["fees_total"] is not None]
    print(f"fees (gross->net caveat): sum parsed {sum(fees):.3f} $ over {len(fees)} trades; "
          f"pnl_usdt is GROSS of fees (checkpoint basis kept)")
    print("\n== EXIT ANATOMY ==")
    table(["exit_reason", "n", "W", "WR", "sum pnl_usdt", "sum pnl_pct",
           "% |flow|", "% of net"], exit_anatomy(rows))

    unit_checks(rows)

    # stop-cluster realized widths
    print("\n== STOP CLUSTER REALIZED WIDTHS (18 exits, pnl_pct = margin %) ==")
    sw = sorted(float(r["pnl_pct"]) for r in stops)
    table(["stat", "pnl_pct %", "raw %"],
          [["min", f"{sw[0]:+.2f}", f"{sw[0] / 5:+.3f}~"],
           ["median", f"{statistics.median(sw):+.2f}", ""],
           ["max (widest loss)", f"{sw[-1]:+.2f}", ""],
           ["n beyond -4%", sum(1 for x in sw if x <= -4), ""],
           ["n beyond -3%", sum(1 for x in sw if x <= -3), ""]])

    resA = sweep(rows, "A")
    resB = sweep(rows, "B")
    print_sweep("SWEEP variant A: path-worst = max(mae_pct, wick extreme)", resA)
    print_sweep("SWEEP variant B (primary): path-worst = A + realized loss floor", resB)

    best = max(resB, key=lambda r: r["net"])
    print(f"\n== DETAIL at best S={best['S']:.2f}% (variant B): {best['touched']} touched ==")
    table(["id", "exit_reason", "regime", "dir", "orig pnl_pct", "worst%", "raw_S%",
           "cf usdt"], best["detail"])

    # winner-cap side
    print("\n== WINNER-CAP SIDE: MFE of profit-monster-trail winners ==")
    wm = [r for r in pm if r["pnl_usdt"] > 0]
    mfe_raw = [float(r["mfe_pct"]) for r in wm]
    mfe_mar = [float(r["mfe_pct"]) * float(r["leverage"]) for r in wm]
    real = [float(r["pnl_pct"]) for r in wm]
    table(["stat", "realized pnl_pct %", "MFE raw %", "MFE margin % (raw x lev)"],
          [["n", len(wm), len(mfe_raw), len(mfe_mar)],
           ["min", f"{min(real):+.2f}", f"{min(mfe_raw):+.3f}", f"{min(mfe_mar):+.2f}"],
           ["median", f"{statistics.median(real):+.2f}", f"{statistics.median(mfe_raw):+.3f}",
            f"{statistics.median(mfe_mar):+.2f}"],
           ["p75", f"{q(real, 75):+.2f}", f"{q(mfe_raw, 75):+.3f}", f"{q(mfe_mar, 75):+.2f}"],
           ["p90", f"{q(real, 90):+.2f}", f"{q(mfe_raw, 90):+.3f}", f"{q(mfe_mar, 90):+.2f}"],
           ["max", f"{max(real):+.2f}", f"{max(mfe_raw):+.3f}", f"{max(mfe_mar):+.2f}"]])
    print(f"winners with margin-MFE > +1%: {sum(1 for x in mfe_mar if x > 1)}/{len(wm)}; "
          f"> +3%: {sum(1 for x in mfe_mar if x > 3)}/{len(wm)}; "
          f"> +5%: {sum(1 for x in mfe_mar if x > 5)}/{len(wm)}")
    uncapped = sum(m - r for m, r in zip(mfe_mar, real))
    print(f"censored upper bound of extra capture if every winner held to its MFE: "
          f"{uncapped:+.2f} pct-points total ({uncapped / len(wm):+.2f}% per winner) — "
          f"NOT realizable without a different exit; MFE-after-exit is observable, not attainable")

    # regime cells
    print("\n== REGIME CELLS: volatility_regime x direction ==")
    cells = []
    for reg in sorted({r["volatility_regime"] for r in rows}):
        for dr in ("LONG", "SHORT"):
            g = [r for r in rows if r["volatility_regime"] == reg and r["direction"] == dr]
            if not g:
                continue
            w = sum(1 for r in g if r["pnl_usdt"] > 0)
            cells.append([reg, dr, len(g), w, f"{w / len(g) * 100:.1f}%",
                          f"{sum(float(r['pnl_usdt']) for r in g):+.2f}",
                          f"{sum(float(r['pnl_pct']) for r in g):+.2f}"])
    table(["regime", "dir", "n", "W", "WR", "sum pnl_usdt", "sum pnl_pct"], cells)

    # cells + halves under best S (robustness)
    print(f"\n== ROBUSTNESS of best S={best['S']:.2f}%: cells under counterfactual ==")
    cf_map = {}
    for r in rows:
        if r["worst_B"] >= best["S"] / float(r["leverage"]) - 1e-12:
            cf_map[r["id"]] = -best["S"] * float(r["amount_usdt"]) / (100.0 * float(r["leverage"]))
        else:
            cf_map[r["id"]] = float(r["pnl_usdt"])
    cells2 = []
    for reg in sorted({r["volatility_regime"] for r in rows}):
        for dr in ("LONG", "SHORT"):
            g = [r for r in rows if r["volatility_regime"] == reg and r["direction"] == dr]
            if not g:
                continue
            cells2.append([reg, dr, len(g), f"{sum(cf_map[r['id']] for r in g):+.2f}"])
    table(["regime", "dir", "n", "cf sum pnl_usdt"], cells2)

    # time split
    print("\n== TIME SPLIT (by open_time: first 24 / last 23) ==")
    h1, h2 = rows[:24], rows[24:]
    for i, h in enumerate((h1, h2), 1):
        n_, w_, l_, s_, net_, ps_ = baseline(h)
        print(f"half{i}: n={n_} {w_}/{l_}/{s_} WR={w_ / n_ * 100:.1f}% net={net_:+.2f} "
              f"avg_pct={ps_ / n_:+.2f} span {h[0]['open_time']} .. {h[-1]['open_time']}")
        res = sweep(h, "B")
        table(["S%", "n", "WR%", "net $", "avg pnl_pct%", "touched", "killed"],
              [[f"{r['S']:.2f}", r["n"], f"{r['wr']:.1f}", f"{r['net']:+.2f}",
                f"{r['avg_pct']:+.2f}", r["touched"], r["killed"]] for r in res],
              ["<", ">", ">", ">", ">", ">", ">"])

    # does anything flip? compare sign of delta vs baseline per S per half
    print("\n== NET POSITIVE? (variant B) ==")
    for r in resB:
        print(f"S={r['S']:.2f}%  net={r['net']:+.2f}  {'POSITIVE' if r['net'] > 0 else 'negative'}")

    # MFE of losers (did stops leave money on table first?)
    lm = [r for r in rows if r["pnl_usdt"] < 0]
    print(f"\nstop/losing exits that saw positive MFE first: "
          f"{sum(1 for r in lm if float(r['mfe_pct']) * float(r['leverage']) > 0.5)}/{len(lm)} "
          f"(margin MFE > +0.5% before reversing)")


if __name__ == "__main__":
    main()
