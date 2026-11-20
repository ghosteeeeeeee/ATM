#!/usr/bin/env python3
"""Retest-Fade harness — pinned detector, evidence tables for the plan
(/root/.hermes/plans/2026-11-20_retest-fade-system-plan.md §7).

CEO thesis under test (2026-11-20): "if a coin is in a confirmed downtrend
and is hammering the same support over and over again, eventually that
support breaks, and usually in a major way. the bounces in between could
even be long opportunities. very rarely is there a straight slice through
a major support/resistance."

Sections
  H1  hammered-support breaks: do N>=3-touch supports break more
      "majorly" than 1-2 touch ones? + retest-after-break frequency
      ("no straight slices").
  H2  bounce-longs at support touches inside confirmed downtrends.
  H3  fade-shorts at failed retests (prior studies, corrected).

Audit columns (own-conclusions 2026-11-20 §7): every H2/H3 row prints
  col1 as-simulated  = lookahead levels, queued entries, gross
  col2 confirmable   = swings require +3-bar confirmation, queued, gross
  col3 flat-only     = confirmable, one position at a time, gross
  col4 net           = confirmable, flat-only, minus costs
Exit models printed separately: FIXED (1.5% target) vs TRAIL (the shipped
structure-governed proxy: 15m lower-high trail + birth BE-lock, no TP).

PINNED CONSTANTS — do not tune without re-running the audit (plan G2).
Data: 15m from 2026-08-22 (5m only exists from 2026-10-21 — not used).
Costs (audit §7): 0.09% RT fees + 0.10% slip = 0.19% price / round trip.
"""
import sqlite3, json, sys, datetime
from pathlib import Path

# ── pinned detector ───────────────────────────────────────────────────────
TF = "15m"
SWING_LB = 3           # local-extremum half-window (bars)
PROM = 0.0025          # prominence vs opposite extreme in window
MIN_GAP = 6            # min bars between swings
CONFIRM_DELAY = 3      # bars after the swing bar at which its level is known
ZONE = 0.003           # touch = price enters ±0.3% of the level
BROKEN = 0.005         # break = close beyond level by 0.5%
CLUSTER_TOL = 0.006    # swing-lows within 0.6% (chained) = same support
TREND_EMA_F, TREND_EMA_S = 80, 320   # on 15m: 20h / 80h — 'confirmed down'
TARGET_PCT = 0.015     # fixed-TP model
STOP_PCTS = (0.004, 0.008)
FEE_RT, SLIP_RT = 0.0009, 0.0010
BARS_4H, BARS_12H, BARS_24H = 16, 48, 96

HERE = Path(__file__).resolve().parent
DB = (HERE.parent / "data" / "candles.db").as_posix()


def load():
    con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    cur = con.cursor()
    cur.execute(f"SELECT ts, open, high, low, close FROM candles_{TF} "
                "WHERE token='BTC' ORDER BY ts")
    rows = cur.fetchall()
    con.close()
    closes = [r[4] for r in rows]
    ema_f = ema_s = closes[0]
    k_f, k_s = 2 / (TREND_EMA_F + 1), 2 / (TREND_EMA_S + 1)
    trend = []
    for c in closes:
        ema_f += k_f * (c - ema_f)
        ema_s += k_s * (c - ema_s)
        trend.append(ema_f < ema_s and c < ema_s)
    return rows, trend


def swings(rows):
    """local minima; each carries available_from = i + CONFIRM_DELAY."""
    out = []
    for i in range(SWING_LB, len(rows) - SWING_LB):
        lo = rows[i][3]
        win = rows[i - SWING_LB:i + SWING_LB + 1]
        if lo == min(r[3] for r in win) and \
           lo <= max(r[3] for r in win) * (1 - PROM):
            if not out or i - out[-1][0] >= MIN_GAP:
                out.append((i, lo))
    return out


def clusters(rows, sw):
    """chained swing-lows within CLUSTER_TOL = one hammered support."""
    out = []
    for idx, val in sw:
        if out and val <= out[-1]["anchor"] * (1 + CLUSTER_TOL) and \
           val >= out[-1]["lo"] * (1 - CLUSTER_TOL):
            c = out[-1]
            c["idxs"].append(idx); c["vals"].append(val)
            c["lo"] = min(c["lo"], val); c["hi"] = max(c["hi"], val)
            c["anchor"] = sum(c["vals"]) / len(c["vals"])
        else:
            out.append({"idxs": [idx], "vals": [val], "lo": val, "hi": val,
                        "anchor": val})
    # touches: swing-lows in cluster + bar-level zone entries
    for c in out:
        c["touches"] = len(c["vals"])
        first, last = c["idxs"][0], c["idxs"][-1]
        zone_hi = c["anchor"] * (1 + ZONE)
        extra = sum(1 for i in range(first, last + 1)
                    if rows[i][3] <= zone_hi)
        c["zone_bars"] = extra
    return out


# ── H1: hammered breaks vs control, retest-after-break ────────────────────
def h1(rows, trend, cls):
    print("\n=== H1 — hammered-support breaks (confirmed 1h-down proxy) ===")
    print("break = first 15m CLOSE < support_lo × (1−BROKEN) while trend_down")
    buckets = {1: [], 2: [], "3+": []}
    retests = []
    for c in cls:
        lo_i, hi_i = c["idxs"][0], c["idxs"][-1]
        if not any(trend[i] for i in range(lo_i, min(hi_i + 1, len(trend)))):
            pass  # still evaluate; gate by trend AT the break below
        b = None
        thr = c["lo"] * (1 - BROKEN)
        for i in range(hi_i + 1, len(rows)):
            if not trend[i]:
                continue
            if rows[i][4] < thr:
                b = i; break
        if b is None:
            continue
        n = c["touches"]
        key = 1 if n == 1 else (2 if n == 2 else "3+")
        base = rows[b][4]
        disps = {}
        for lbl, k in (("4h", BARS_4H), ("12h", BARS_12H), ("24h", BARS_24H)):
            if b + k < len(rows):
                disps[lbl] = (rows[b + k][4] - base) / base * 100
        buckets[key].append(disps)
        # retest: after break, does price return to the zone within 24h?
        zone = c["anchor"] * (1 - ZONE)
        rt = any(rows[i][2] >= zone for i in range(b + 1, min(b + BARS_24H, len(rows))))
        retests.append(rt)
    hdr = f"{'touches':>8} {'n':>4} | {'med 4h':>8} {'med 12h':>9} {'med 24h':>9} | {'P(≤−1%)24h':>10} {'P(≤−2%)24h':>10}"
    print(hdr)
    for key in (1, 2, "3+"):
        v = buckets[key]
        if not v:
            print(f"{str(key):>8} {0:>4} | (none)"); continue
        def med(col):
            xs = sorted(d[col] for d in v if col in d)
            return xs[len(xs) // 2] if xs else float("nan")
        p1 = sum(1 for d in v if d.get("24h", 0) <= -1) / len(v) * 100
        p2 = sum(1 for d in v if d.get("24h", 0) <= -2) / len(v) * 100
        print(f"{str(key):>8} {len(v):>4} | {med('4h'):>7.2f}% {med('12h'):>8.2f}% {med('24h'):>8.2f}% | {p1:>9.0f}% {p2:>9.0f}%")
    if retests:
        print(f"retest-of-broken-support within 24h (no straight slice): "
              f"{sum(retests)}/{len(retests)} = {sum(retests)/len(retests)*100:.0f}%")


# ── shared entry walker (H2/H3) ───────────────────────────────────────────
def run_h(rows, trend, sw, side, style, stop_pct, delay, flat_only,
          exit_model, costs, require_trend=False, limit_bars=96 * 6):
    """Generic episode engine for H2 (longs at support) / H3 (short
    fade-retests). delay: 0 = as-simulated, CONFIRM_DELAY = confirmable.
    flat_only: one position at a time. costs: subtract FEE+SLIP per RT."""
    # build episodes: for each swing (available at i+delay) as the LEVEL,
    # the next touch of its zone after availability.
    episodes = []
    for k, (li, lval) in enumerate(sw):
        avail = li + delay
        if avail >= len(rows):
            continue
        # find the touch after availability (and after the swing's own bar)
        touch = None
        for i in range(max(avail, li + 1), min(li + 400, len(rows))):
            if side == "SHORT":
                # fade a rally INTO the swing-high zone (retest fails)
                if rows[i][2] >= lval * (1 - ZONE):
                    touch = i; break
            else:
                if rows[i][3] <= lval * (1 + ZONE):
                    touch = i; break
        if touch is None:
            continue
        if require_trend and not trend[touch]:
            continue
        if side == "SHORT":
            level = lval
            entry = level * (1 - ZONE)
            stop = level * (1 + stop_pct)
            tgt = entry * (1 - TARGET_PCT) if exit_model == "FIXED" else None
        else:
            level = lval
            entry = level * (1 + ZONE)
            stop = level * (1 - stop_pct)
            tgt = entry * (1 + TARGET_PCT) if exit_model == "FIXED" else None
        episodes.append((touch, entry, stop, tgt))
    episodes.sort()
    results = []
    open_until = -1
    for (ti, entry, stop, tgt) in episodes:
        if flat_only and ti < open_until:
            continue
        # resolve
        outcome, exit_px, ei = None, None, None
        end = min(ti + limit_bars, len(rows))
        for i in range(ti, end):
            hi, lo = rows[i][2], rows[i][3]
            if side == "SHORT":
                # trail model: lower the stop to (confirmed SH ×1.001) — uses
                # swings that CONFIRMED by this bar (lookahead-safe)
                if exit_model == "TRAIL":
                    for (sj, sv) in sw:
                        if ti <= sj and sj + CONFIRM_DELAY <= i and sv < entry:
                            stop = min(stop, sv * 1.001)
                if hi >= stop:
                    outcome, exit_px, ei = "STOP", stop, i; break
                if tgt and lo <= tgt:
                    outcome, exit_px, ei = "TP", tgt, i; break
            else:
                if exit_model == "TRAIL":
                    for (sj, sv) in sw:
                        if ti <= sj and sj + CONFIRM_DELAY <= i and sv > entry:
                            stop = max(stop, sv * 0.999)
                if lo <= stop:
                    outcome, exit_px, ei = "STOP", stop, i; break
                if tgt and hi >= tgt:
                    outcome, exit_px, ei = "TP", tgt, i; break
        if outcome is None:
            outcome = "OPEN"
            exit_px = rows[end - 1][4]
            ei = end - 1
        if side == "SHORT":
            pnl_px = (entry - exit_px) / entry
        else:
            pnl_px = (exit_px - entry) / entry
        margin = pnl_px * 100 * 10
        if outcome == "STOP" or outcome == "TP":
            margin -= (FEE_RT + SLIP_RT) * 100 * 10 if costs else 0.0
        else:
            margin -= (FEE_RT + SLIP_RT) * 100 * 10 if costs else 0.0
        results.append((ti, outcome, margin))
        if flat_only:
            open_until = ei + 1
    return results


def summ(res):
    if not res:
        return "n=0"
    n = len(res)
    tp = sum(1 for r in res if r[1] == "TP")
    st = sum(1 for r in res if r[1] == "STOP")
    op = sum(1 for r in res if r[1] == "OPEN")
    tot = sum(r[2] for r in res)
    wins = sum(1 for r in res if r[2] > 0)
    return (f"n={n:>3} | TP {tp:>3} · STOP {st:>3} · OPEN {op:>2} | "
            f"win {wins/n*100:>3.0f}% | sum {tot:>+8.1f}% | "
            f"med/ep {sorted(r[2] for r in res)[n//2]:>+6.1f}%")


def h2_h3(rows, trend, sw_all, sw_highs, cls):
    def cols_for(side, sw, stop_pct, model, gated):
        out = []
        for (delay, flat, costs) in ((0, False, False),
                                     (CONFIRM_DELAY, False, False),
                                     (CONFIRM_DELAY, True, False),
                                     (CONFIRM_DELAY, True, True)):
            res = run_h(rows, trend, sw, side, "fade", stop_pct,
                        delay, flat, model, costs, require_trend=gated)
            out.append(summ(res))
        return out
    for side, sw, label in (("LONG", sw_all, "bounce-LONGS at hammered support"),
                            ("SHORT", sw_highs, "fade-SHORTS at failed rally retests")):
        for gated in (True, False):
            tag = "GATED (thesis: trend-down at entry)" if gated else "ungated (all regimes)"
            print(f"\n=== H{2 if side=='LONG' else 3} — {label} | {tag} ===")
            print("col1 as-sim | col2 confirmable | col3 flat-only | col4 net(costs)")
            for stop_pct in STOP_PCTS:
                for model in ("FIXED", "TRAIL"):
                    cols = cols_for(side, sw, stop_pct, model, gated)
                    print(f"{side} stop {stop_pct*100:.1f}% {model:>6}:")
                    for i, c in enumerate(cols, 1):
                        print(f"   col{i}: {c}")


def trend_gate_report(trend, cls, rows):
    """share of time in confirmed-down, and episode counts gated/ungated"""
    n = len(trend)
    print(f"\n=== gate context: confirmed-downtrend share of {n} bars "
          f"= {sum(trend)/n*100:.0f}% ===")


def main():
    rows, trend = load()
    sw = swings(rows)                      # swing lows
    # swing highs (mirror detector)
    sw_h = []
    for i in range(SWING_LB, len(rows) - SWING_LB):
        hi = rows[i][2]
        win = rows[i - SWING_LB:i + SWING_LB + 1]
        if hi == max(r[2] for r in win) and \
           hi >= min(r[2] for r in win) * (1 + PROM):
            if not sw_h or i - sw_h[-1][0] >= MIN_GAP:
                sw_h.append((i, hi))
    cls = clusters(rows, sw)
    span = (datetime.datetime.utcfromtimestamp(rows[0][0]).strftime("%Y-%m-%d"),
            datetime.datetime.utcfromtimestamp(rows[-1][0]).strftime("%Y-%m-%d"))
    print(f"retest-fade harness | {TF} {span[0]} → {span[1]} | "
          f"{len(rows)} bars | pinned constants (see module docstring)")
    print(f"detector: {len(sw)} swing-lows, {len(sw_h)} swing-highs, "
          f"{len(cls)} support clusters | costs: "
          f"{(FEE_RT+SLIP_RT)*100:.2f}% price/RT")
    trend_gate_report(trend, cls, rows)
    h1(rows, trend, cls)
    h2_h3(rows, trend, sw, sw_h, cls)
    print("\nnote: single 3-month cycle, 15m only, first-touch modeling, "
          "no intra-bar path — direction-of-evidence (plan §7 G1/G6).")


if __name__ == "__main__":
    main()
