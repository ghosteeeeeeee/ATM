#!/usr/bin/env python3
"""Touch-bucket research — does a support's touch count predict its break?

CEO claim under test (2026-11-20): "multiple touches (under 8?) were the
sweet spot [for breakdowns], after that 18, 50 etc. were confirmed support
and not breaking." Feeds the multi-bounce-then-breakdown theory (BTC testing
it from 61,500 since Nov-19).

Method (all definitions reused verbatim from signals/rs.py — the signal's
own semantics, nothing re-invented):
  - swings:     rs._find_swing_highs_lows(candles, RS_LEVEL_LOOKBACK=300)
  - clustering: rs._cluster_levels(levels, RS_CLUSTER_ATR=1.0 as % of price)
  - touches:    rs._build_level_touches((highs, lows), level, atr) within
                RS_BOUNCE_THRESH_ATR=0.33 × ATR(14), trailing window only
  - break:      forward mirror of rs._level_recently_broken (two confirming
                closes on the far side) within RS_LEVEL_BROKEN_LOOKBACK=200
                bars — same K as the signal's own invalidation window.
Sampled every 4h (stated: episodes overlap — n = levels, not independent
trades; report block split, not just totals). Two TFs: 5m (signal-native,
Oct-21+, ~30d) and 15m (depth, Aug-22+, ~90d).

Usage: python3 research_touch_buckets.py            # parts 1+2
       python3 research_touch_buckets.py --trades   # + shadow trade study
"""
import sys, sqlite3, json, datetime
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from paths import HERMES_DATA
from hermes_constants import (RS_LEVEL_LOOKBACK, RS_CLUSTER_ATR,
                              RS_BOUNCE_THRESH_ATR, RS_LEVEL_BROKEN_LOOKBACK)
from signals import rs as R

BUCKETS = [(0, 8), (8, 18), (18, 50), (50, 100), (100, 10**9)]
SAMPLE_EVERY_BARS = 16  # 4h on 15m = 4h on 5m? no: 4h/15m=16 bars, 4h/5m=48


def load(tf):
    con = sqlite3.connect(f"file:{HERMES_DATA}/candles.db?mode=ro", uri=True)
    cur = con.cursor()
    cur.execute(f"SELECT ts, high, low, close FROM candles_{tf} "
                "WHERE token='BTC' ORDER BY ts")
    rows = cur.fetchall()
    con.close()
    return rows


def bucket_of(tc):
    for lo, hi in BUCKETS:
        if lo <= tc < hi:
            return f"{lo}-{hi - 1}" if hi < 10**9 else f"{lo}+"


def broken_forward(closes, level, t, k):
    """forward mirror of rs._level_recently_broken for 'support'."""
    end = min(t + k, len(closes) - 1)
    for i in range(t + 1, end + 1):
        if closes[i - 1] > level > closes[i]:
            if i + 1 <= end and closes[i + 1] < level:
                return i - t
    return None


def part1(rows, tf):
    step = 4 * 60 // (15 if tf == "15m" else 5)  # sample every 4h
    closes = [r[3] for r in rows]
    n_samp = 0
    obs = []  # (bucket, broke_idx_or_None, sample_t)
    t = RS_LEVEL_LOOKBACK * 2 + 1
    while t < len(rows) - RS_LEVEL_BROKEN_LOOKBACK:
        window = [dict(ts=r[0], high=r[1], low=r[2], close=r[3])
                  for r in rows[:t]]
        sw_hi, sw_lo = R._find_swing_highs_lows(window, RS_LEVEL_LOOKBACK)
        if sw_lo:
            atrs = [abs(window[i]["high"] - window[i]["low"])
                    for i in range(max(0, len(window) - 15), len(window))]
            atr = float(np.mean(atrs)) if atrs else None
            clustered = R._cluster_levels(
                [(p, 1) for _, p in sw_lo], RS_CLUSTER_ATR)
            highs = np.array([w["high"] for w in window], dtype=float)
            lows = np.array([w["low"] for w in window], dtype=float)
            for price, _tc in clustered:
                tc = R._build_level_touches((highs, lows), price, atr)
                br = broken_forward(closes, price, t, RS_LEVEL_BROKEN_LOOKBACK)
                obs.append((tc, br, t))
        n_samp += 1
        t += step
    # bucket table
    print(f"\n--- PART 1: support break rate by touch bucket ({tf}, "
          f"{n_samp} samples, window≤t, forward K={RS_LEVEL_BROKEN_LOOKBACK} bars) ---")
    print(f"{'bucket':>9} {'levels':>7} {'broke%':>7} {'med-bars-to-break':>18}")
    base_b = sum(1 for _, b, _ in obs if b is not None)
    print(f"{'BASE':>9} {len(obs):>7} {100.0*base_b/len(obs):>6.1f}%")
    half = len(obs) // 2
    for lo, hi in BUCKETS:
        sel = [(b, t_) for tc, b, t_ in obs if lo <= tc < hi]
        if not sel:
            continue
        br = sum(1 for b, _ in sel if b is not None)
        bars = sorted(b for b, _ in sel if b is not None)
        med = bars[len(bars) // 2] if bars else None
        print(f"{bucket_of(lo):>9} {len(sel):>7} {100.0*br/len(sel):>6.1f}% "
              f"{str(med) if med else '-':>18}")
    # block split (first/second half of the window) — episode dependence
    for name, seg in (("1st half", obs[:half]), ("2nd half", obs[half:])):
        b = sum(1 for _, x, _ in seg if x is not None)
        print(f"  {name}: n={len(seg)} broke%={100.0*b/max(len(seg),1):.1f}%")


def part2(rows, tf, since_ts):
    """BTC now: the 61.5k bounce zone — chart-style swing lows (small
    window: the rs ±300-bar extrema exclude the right edge, where the
    current bounces live) + rs-style touch count at the zone level."""
    closes = [r[3] for r in rows]
    lows = [r[2] for r in rows]
    # chart-style swing lows: local min ±6 bars (4h on 15m / 30m on 5m)
    sw = []
    W = 6
    for i in range(W, len(rows) - W):
        if lows[i] == min(lows[i - W:i + W + 1]):
            if not sw or i - sw[-1][0] >= 2 * W:
                sw.append((i, lows[i]))
    zone_lows = [(rows[i][0], p) for i, p in sw
                 if rows[i][0] >= since_ts and 61_000 <= p <= 62_500]
    print(f"\n--- PART 2: BTC 61.5k zone now ({tf}) ---")
    print(f"chart-style swing-low bounces in 61,000-62,500 since Nov-19: "
          f"{[round(p) for _, p in zone_lows]} (count={len(zone_lows)})")
    # rs-style touch count at the zone anchor (mean of the bounces)
    if zone_lows:
        anchor = sum(p for _, p in zone_lows) / len(zone_lows)
        atrs = [abs(rows[i][1] - rows[i][2]) for i in range(len(rows) - 15, len(rows))]
        atr = float(np.mean(atrs))
        highs = np.array([r[1] for r in rows], dtype=float)
        lowsa = np.array([r[2] for r in rows], dtype=float)
        tc = R._build_level_touches((highs, lowsa), anchor, atr)
        print(f"zone anchor ~{anchor:.0f}: rs-style touches (0.33·ATR, full "
              f"window) = {tc} -> bucket {bucket_of(tc)}")
        # touches since Nov-19 only
        mask = np.array([r[0] >= since_ts for r in rows])
        tc_since = R._build_level_touches(
            (highs[mask], lowsa[mask]), anchor, atr)
        print(f"touches since Nov-19 only = {tc_since} -> bucket "
              f"{bucket_of(tc_since)}")
        # two-close-cross breaks of the anchor since Nov-19 (the live test)
        idx0 = next((i for i, r in enumerate(rows) if r[0] >= since_ts), 0)
        br = broken_forward(closes, anchor, idx0, len(rows) - idx0 - 1)
        print(f"anchor broken since Nov-19: "
              f"{'YES at bar +' + str(br) if br else 'NO (still holding)'}")


def part3_real():
    sh = sqlite3.connect("/root/.hermes/brain/shadow_trades.db")
    sc = sh.cursor()
    sc.execute("""SELECT signal_id, token, direction, created_at, net_pnl_pct
      FROM shadow_trades WHERE signal_type='support_resistance'
      AND net_pnl_pct IS NOT NULL AND created_at >= '2026-10-21'""")
    all_rows = sc.fetchall()
    sh.close()
    # sample: every 5th row (state n) — 5m-era only (5m data starts Oct-21)
    rows = all_rows[::5]
    con = sqlite3.connect(f"file:{HERMES_DATA}/candles.db?mode=ro", uri=True)
    cache = {}
    skips = {}
    obs = []
    for sid, token, direc, created, pnl in rows:
        if token not in cache:
            c = con.cursor()
            c.execute("""SELECT ts, high, low, close FROM candles_5m
              WHERE token=? AND ts <= strftime('%s',?) ORDER BY ts DESC LIMIT ?""",
                      (token, created, RS_LEVEL_LOOKBACK * 4 + 5))
            rws = list(reversed(c.fetchall()))
            cache[token] = rws
        rws = cache[token]
        if len(rws) < RS_LEVEL_LOOKBACK * 2 + 1:
            skips['short_history'] = skips.get('short_history', 0) + 1
            continue
        window = [dict(ts=x[0], high=x[1], low=x[2], close=x[3]) for x in rws]
        sw_hi, sw_lo = R._find_swing_highs_lows(window, RS_LEVEL_LOOKBACK)
        if not sw_lo:
            skips['no_swing'] = skips.get('no_swing', 0) + 1
            continue
        price = rws[-1][3]
        nearest = min((p for _, p in sw_lo), key=lambda p: abs(p - price))
        if abs(nearest - price) / price > 0.02:  # >2% away = not the traded level
            skips['level_gt_2pct'] = skips.get('level_gt_2pct', 0) + 1
            continue
        atrs = [abs(window[i]["high"] - window[i]["low"])
                for i in range(len(window) - 15, len(window))]
        atr = float(np.mean(atrs))
        highs = np.array([w["high"] for w in window], dtype=float)
        lows = np.array([w["low"] for w in window], dtype=float)
        tc = R._build_level_touches((highs, lows), nearest, atr)
        obs.append((tc, direc, pnl))
    con.close()
    print(f"  skips: {skips}")
    print(f"\n--- PART 3: shadow support_resistance, tc recomputed at fire "
          f"(5m-era, every 5th, n={len(obs)} of {len(all_rows)}) ---")
    print(f"{'bucket':>9} {'dir':>6} {'n':>5} {'win%':>6} {'avg net%':>9}")
    for lo, hi in BUCKETS:
        for direc in ("LONG", "SHORT"):
            sel = [p for tc, d, p in obs if lo <= tc < hi and d == direc]
            if len(sel) >= 5:
                w = 100.0 * sum(1 for p in sel if p > 0) / len(sel)
                print(f"{bucket_of(lo):>9} {direc:>6} {len(sel):>5} "
                      f"{w:>5.1f}% {sum(sel)/len(sel):>+8.3f}")


def main():
    print(f"touch-bucket research | RS constants: LOOKBACK={RS_LEVEL_LOOKBACK} "
          f"CLUSTER_ATR={RS_CLUSTER_ATR} BOUNCE_ATR={RS_BOUNCE_THRESH_ATR} "
          f"BROKEN_K={RS_LEVEL_BROKEN_LOOKBACK}")
    for tf in ("5m", "15m"):
        rows = load(tf)
        print(f"\n=== {tf}: {len(rows)} bars "
              f"{datetime.datetime.utcfromtimestamp(rows[0][0]).date()}"
              f"→{datetime.datetime.utcfromtimestamp(rows[-1][0]).date()} ===")
        part1(rows, tf)
        part2(rows, tf, int(datetime.datetime(2026, 11, 19,
                                             tzinfo=datetime.timezone.utc)
                            .timestamp()))
    if "--trades" in sys.argv:
        part3_real()
    print("\nnote: overlapping episodes (n = levels, not independent trades) "
          "— read block splits; single 30-90d window, one asset (plan §8 G1).")


if __name__ == "__main__":
    main()
