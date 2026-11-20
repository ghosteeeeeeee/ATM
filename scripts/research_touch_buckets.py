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



def part4():
    """Trade-side probabilities from the shadow troves (CEO 2026-11-20):
    source strings embed the touch count for the bounce fires
    ('rs-s{tc}' / 'rs-r{tc}'); 'rs-s-broken' rows = the breakdown events.
    A. outcomes by tc bucket (bounce fires)
    B. P(same-token breakdown within 24h | bounce at tc bucket) — the
       'more touches -> confirmed vs breaks' gradient on TRADE data
       (token-level pairing approximation: any rs-s-broken on that token;
       level pairing needs the new instrumentation going forward)
    C. breakdown-event ('rs-s-broken') outcomes = the ride-the-breakdowns
       performance itself.
    tc gate: detect() enforces 30<=tc<=200 at fire (RS_MIN_TOUCHES/HARD_CAP)
    so tradeable buckets are 30-49 / 50-99 / 100-199 / 200+ (blocked)."""
    import re, bisect
    sh = sqlite3.connect("/root/.hermes/brain/shadow_trades.db")
    sc = sh.cursor()
    sc.execute("""SELECT token, direction, source, created_at, net_pnl_pct,
        first_exit_reason FROM shadow_trades
        WHERE signal_type='support_resistance' AND net_pnl_pct IS NOT NULL""")
    rows = sc.fetchall()
    sc.execute("""SELECT token, direction, created_at, net_pnl_pct
        FROM shadow_trades
        WHERE signal_type='support_resistance' AND source='rs-s-broken'
        AND net_pnl_pct IS NOT NULL""")
    broken = sc.fetchall()
    sh.close()
    pat = re.compile(r"^rs-[sr](\d+)$")
    bounces, unparsed = [], 0
    for tok, direc, srcv, created, pnl, exit_r in rows:
        m = pat.match(srcv or "")
        if not m:
            unparsed += 1
            continue
        bounces.append((int(m.group(1)), tok, direc, created, pnl))
    # broken timestamps per token (sorted)
    from collections import defaultdict
    bt = defaultdict(list)
    for tok, direc, created, pnl in broken:
        bt[tok].append(created)
    for k in bt:
        bt[k].sort()
    print(f"\n--- PART 4: shadow SR trade-side (source-parsed tc) ---")
    print(f"bounce rows: {len(bounces)} parsed, {unparsed} unparsed "
          f"(rs-s-broken etc.); breakdown events: {len(broken)}")
    def bucket_rows(sel):
        out = {}
        for tc, tok, direc, created, pnl in sel:
            b = bucket_of(tc)
            out.setdefault(b, []).append(pnl)
        return out
    print("\nA. bounce-fire outcomes by tc bucket (30+ = the detect gate):")
    print(f"{'bucket':>9} {'n':>5} {'win%':>6} {'avg net%':>9} {'med net%':>9}")
    for lo, hi in BUCKETS:
        vals = [p for tc, *_ , p in
                [(t, k, d, c, p) for t, k, d, c, p in bounces if lo <= t < hi]]
        # (kept simple below)
    for bname, vals in sorted(bucket_rows(bounces).items()):
        if len(vals) >= 5:
            vals_s = sorted(vals)
            print(f"{bname:>9} {len(vals):>5} "
                  f"{100.0*sum(1 for v in vals if v>0)/len(vals):>5.1f}% "
                  f"{sum(vals)/len(vals):>+8.3f} {vals_s[len(vals_s)//2]:>+8.3f}")
    print("\nB. breakdown within 24h of a bounce (same token), by tc bucket:")
    print(f"{'bucket':>9} {'n':>5} {'P(break24h)':>12}")
    for lo, hi in BUCKETS:
        sel = [(tok, created) for tc, tok, direc, created, pnl in bounces
               if lo <= tc < hi]
        if len(sel) < 5:
            continue
        from datetime import datetime, timedelta
        hits = 0
        for tok, created in sel:
            lst = bt.get(tok, [])
            i = bisect.bisect_right(lst, created)
            if i >= len(lst):
                continue
            try:
                t0 = datetime.strptime(created, "%Y-%m-%d %H:%M:%S")
                t1 = (t0 + timedelta(hours=24)).strftime("%Y-%m-%d %H:%M:%S")
            except ValueError:
                continue
            # created_at formats may include microseconds/TZ — compare on
            # the date-truncated prefix both sides share
            if lst[i][:19] <= t1 and lst[i][:19] >= created[:19]:
                hits += 1
        # CONTROL: same pairing anchored 24h EARLIER (prior-day window)
        # — does a bounce raise the odds vs an arbitrary moment?
        chits = 0
        for tok, created in sel:
            lst = bt.get(tok, [])
            try:
                t0 = datetime.strptime(created, "%Y-%m-%d %H:%M:%S")
                a = (t0 - timedelta(hours=24)).strftime("%Y-%m-%d %H:%M:%S")
                b = t0.strftime("%Y-%m-%d %H:%M:%S")
            except ValueError:
                continue
            i = bisect.bisect_left(lst, a)
            if i < len(lst) and lst[i][:19] <= b:
                chits += 1
        print(f"{bucket_of(lo):>9} {len(sel):>5} {100.0*hits/len(sel):>11.1f}%"
              f"   control(prior-24h) {100.0*chits/len(sel):>5.1f}%")
    print("\nC. breakdown events (rs-s-broken) outcomes:")
    bd = {}
    for tok, direc, created, pnl in broken:
        bd.setdefault(direc, []).append(pnl)
    for direc, vals in sorted(bd.items()):
        vals_s = sorted(vals)
        print(f"  {direc:>6} n={len(vals):>5} win%={100.0*sum(1 for v in vals if v>0)/len(vals):>5.1f} "
              f"avg={sum(vals)/len(vals):+.3f} med={vals_s[len(vals_s)//2]:+.3f}")
    # time-split for C (regime dependence, plan item15)
    print("  C by era:")
    for era_lo, era_hi, name in (("2026-10-07", "2026-11-05", "early"),
                                 ("2026-11-05", "2026-11-21", "recent")):
        vals = [p for tok, direc, created, p in broken
                if era_lo <= created < era_hi]
        if len(vals) >= 5:
            print(f"    {name} {era_lo}..: n={len(vals)} "
                  f"win%={100.0*sum(1 for v in vals if v>0)/len(vals):.1f} "
                  f"avg={sum(vals)/len(vals):+.3f}")


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
    if "--part4" in sys.argv or "--trades" in sys.argv:
        part4()
    print("\nnote: overlapping episodes (n = levels, not independent trades) "
          "— read block splits; single 30-90d window, one asset (plan §8 G1).")


if __name__ == "__main__":
    main()
