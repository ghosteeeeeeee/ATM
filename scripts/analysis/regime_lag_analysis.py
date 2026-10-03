#!/usr/bin/env python3
"""Regime lag analysis: continuum bias vs actual BTC forward returns."""
import sqlite3, os, sys, json
sys.path.insert(0, '/root/.hermes/scripts')
from paths import HERMES_DATA, CANDLES_DB

CONT_DB = os.path.join(HERMES_DATA, 'continuum.db')

def load_continuum():
    conn = sqlite3.connect(CONT_DB)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("""
        SELECT ts, state_score, linreg_direction, linreg_alignment
        FROM continuum_states WHERE token='BTC' ORDER BY ts
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def load_1h_candles():
    conn = sqlite3.connect(CANDLES_DB)
    rows = conn.execute("""
        SELECT ts, close FROM candles_1h WHERE token='BTC' AND is_closed=1 ORDER BY ts
    """).fetchall()
    conn.close()
    return {int(r[0]): float(r[1]) for r in rows}

def bias_from_row(r):
    d = r['linreg_direction']
    a = r['linreg_alignment'] or 0.0
    dm = {'BULL':1.0,'LEAN_BULL':0.5,'NEUTRAL':0.0,'LEAN_BEAR':-0.5,'BEAR':-1.0}
    score = r['state_score'] or 50.0
    # trend_bias from score with dead zone
    if score >= 55: tb = min(1.0,(score-55)/45.0)
    elif score <= 45: tb = max(-1.0,(score-45)/45.0)
    else: tb = 0.0
    lb = dm.get(d,0.0)*a
    return tb, lb

def main():
    cont = load_continuum()
    candles = load_1h_candles()
    ts_list = sorted(candles.keys())

    # Build hourly close series (1h grid)
    import bisect
    cts = ts_list
    cvals = [candles[t] for t in cts]

    def price_at_or_after(ts):
        i = bisect.bisect_left(cts, ts)
        if i >= len(cts):
            return None
        return cvals[i]

    def price_at_or_before(ts):
        i = bisect.bisect_right(cts, ts) - 1
        if i < 0:
            return None
        return cvals[i]

    # Hourly-sampled continuum (one sample per hour, latest within hour)
    hourly = {}
    for r in cont:
        h = r['ts'] // 3600 * 3600
        hourly[h] = r  # latest per hour wins (rows in ts order)

    # For each hour with continuum AND enough future candles: forward returns vs bias
    # Lag correlation: trend_bias(t) vs fwd return over [t, t+L]
    lag_hours = [1, 2, 4, 6, 12, 24]
    n = len(hourly)
    print(f"Hourly continuum samples: {n}, 1h candles: {len(cts)}")

    for L in lag_hours:
        rows = []
        for h, r in hourly.items():
            p0 = price_at_or_before(h + 3600)   # close of hour h (candle ending ~h+3600)
            p1 = price_at_or_before(h + 3600 + L*3600)
            if p0 is None or p1 is None:
                continue
            fwd = (p1 - p0) / p0 * 100.0
            tb, lb = bias_from_row(r)
            rows.append((tb, lb, fwd))
        if not rows:
            continue
        N = len(rows)
        # Pearson correlation
        def pearson(xs, ys):
            mx = sum(xs)/len(xs); my = sum(ys)/len(ys)
            num = sum((x-mx)*(y-my) for x,y in zip(xs,ys))
            dx = sum((x-mx)**2 for x in xs)**0.5
            dy = sum((y-my)**2 for y in ys)**0.5
            return num/(dx*dy) if dx and dy else 0.0
        ct = pearson([r[0] for r in rows], [r[2] for r in rows])
        cl = pearson([r[1] for r in rows], [r[2] for r in rows])
        # Hit rate: does sign(bias) match sign(fwd)?
        valid_t = [(r[0], r[2]) for r in rows if abs(r[0]) > 0.05]
        valid_l = [(r[1], r[2]) for r in rows if abs(r[1]) > 0.05]
        hit_t = sum(1 for b,f in valid_t if (b>0)==(f>0))/len(valid_t)*100 if valid_t else 0
        hit_l = sum(1 for b,f in valid_l if (b>0)==(f>0))/len(valid_l)*100 if valid_l else 0
        avg_fwd = sum(r[2] for r in rows)/N
        print(f"L={L:2d}h: N={N:4d} corr(score_bias)={ct:+.3f} corr(linreg_bias)={cl:+.3f} "
              f"hit%_score={hit_t:5.1f}({len(valid_t)}) hit%_linreg={hit_l:5.1f}({len(valid_l)}) avg_fwd={avg_fwd:+.3f}%")

    # Direction flip rate: how often does linreg_direction change per day?
    dirs = [(r['ts'], r['linreg_direction']) for r in cont]
    flips = 0
    day_flips = {}
    for i in range(1, len(dirs)):
        if dirs[i][1] != dirs[i-1][1]:
            flips += 1
            d = dirs[i][0] // 86400
            day_flips[d] = day_flips.get(d, 0) + 1
    days = len(set(r['ts']//86400 for r in cont))
    print(f"\nlinreg_direction flips: {flips} over {days} days = {flips/days:.1f}/day")
    # Score flips across dead-zone boundaries (55/45)
    score_zones = []
    for r in cont:
        s = r['state_score'] or 50
        z = 1 if s >= 55 else (-1 if s <= 45 else 0)
        score_zones.append((r['ts'], z))
    zf = sum(1 for i in range(1,len(score_zones)) if score_zones[i][1] != score_zones[i-1][1])
    print(f"score-zone flips (bull/bear/neutral): {zf} over {days} days = {zf/days:.1f}/day")

    # How long is BTC in each score zone per day (sampled)?
    from collections import Counter
    zc = Counter(z for _, z in score_zones)
    tot = sum(zc.values())
    print(f"score zone time share: bull={zc[1]/tot*100:.0f}% neutral={zc[0]/tot*100:.0f}% bear={zc[-1]/tot*100:.0f}%")

    # Detection lag for the 3 big moves: Sep 18 (+6.2% day), Sep 21 (+7.2%), Sep 23 (high 87224)
    events = [("Sep18 rally start", 1791000000, 1790500000)]  # placeholder
    # Use actual known timestamps: compute from candles
    # Find daily returns
    daily = {}
    for t, c in zip(cts, cvals):
        d = t // 86400
        if d not in daily:
            daily[d] = {'o': None, 'c': None}
        if daily[d]['o'] is None:
            daily[d]['o'] = c
        daily[d]['c'] = c
    print("\nDaily moves vs continuum avg score (last 21 days):")
    for d in sorted(daily)[-21:]:
        dr = (daily[d]['c']-daily[d]['o'])/daily[d]['o']*100
        # continuum samples that day
        day_rows = [r for r in cont if r['ts']//86400 == d]
        if not day_rows:
            continue
        scores = [r['state_score'] for r in day_rows if r['state_score'] is not None]
        avg_s = sum(scores)/len(scores) if scores else 50
        bull = sum(1 for r in day_rows if r['linreg_direction'] in ('BULL','LEAN_BULL'))
        bear = sum(1 for r in day_rows if r['linreg_direction'] in ('BEAR','LEAN_BEAR'))
        print(f"  {d}: btc_daily={dr:+.2f}%  cont_avg={avg_s:.1f}  bull_ticks={bull} bear_ticks={bear}")

if __name__ == '__main__':
    main()
