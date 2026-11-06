#!/usr/bin/env python3
"""
backtest_atr60_momentum.py — ATR(14) 1m threshold-cross + momentum direction event study.

Thesis (CEO observation, 2026-11-06): On the BTC 1m chart, when ATR(14) crosses
up through ~$60, the subsequent move tends to be BIG and in the direction of the
obvious momentum (MACD or RSI). BTC printed a ~6% long and a ~6% short in the
prior 24-48h, both preceded by ATR expansion.

ATR definition pinned to match a chart indicator whose only input is "length=14":
  TradingView built-in ATR = RMA (Wilder smoothing) of True Range, period 14,
  seeded with SMA of the first 14 TRs.  TR = max(h-l, |h-pc|, |l-pc|).

Event  : ATR_prev < T <= ATR_now  (cross UP through threshold T, default 60 USD)
Direction at event close:
  macd  : MACD(12,26,9) histogram > 0 -> LONG, < 0 -> SHORT   (1m closes)
  rsi   : RSI(14) Wilder > 50 -> LONG, < 50 -> SHORT          (1m closes)
  agree : both agree -> trade that direction; else skipped (counted separately)

Primary sample = DECLUSTERED events (hysteresis re-arm: ATR must fall below
T*0.9 before another cross counts) — raw crosses oscillate around T and would
inflate n.

Outcomes measured from the event bar CLOSE, ts-based horizon lookup:
  - direction-aligned return at 15m/30m/1h/2h/4h/8h/12h/24h
  - MFE / MAE (direction-aligned) over 4h and 24h
  - first-touch +/-1/2/3% (direction-aligned) within 24h
  - |move| regardless of direction (tests the "bigger move" claim)
Baseline = every 60th minute, same direction rule, same horizons.

Run: python3 scripts/backtest_atr60_momentum.py [--coin BTC] [--threshold 60]
"""
import os
import sys
import sqlite3
import argparse
import random

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paths import HERMES_DATA

DB = os.path.join(HERMES_DATA, 'candles.db')

HORIZONS = [15, 30, 60, 120, 240, 480, 720, 1440]  # minutes
PCT_TARGETS = [1.0, 2.0, 3.0]  # direction-aligned first-touch % within 24h


# ── data ─────────────────────────────────────────────────────────────────────
def load_candles(token):
    conn = None
    try:
        conn = sqlite3.connect(DB, timeout=10)
        rows = conn.execute(
            "SELECT ts, open, high, low, close FROM candles_1m "
            "WHERE token = ? ORDER BY ts ASC", (token.upper(),)
        ).fetchall()
        return rows
    finally:
        if conn:
            conn.close()


# ── indicators (exact definitions, no smoothing shortcuts) ──────────────────
def tv_atr(h, l, c, period=14):
    """TradingView ATR: RMA(Wilder) of True Range, seeded with SMA(period)."""
    n = len(c)
    res = [None] * n
    if n < period + 1:
        return res
    trs = []
    for i in range(1, n):
        trs.append(max(h[i] - l[i], abs(h[i] - c[i - 1]), abs(l[i] - c[i - 1])))
    atr = sum(trs[:period]) / period
    res[period] = atr  # first ATR lands on bar `period` (uses bars 1..period)
    for i in range(period, len(trs)):
        atr = (atr * (period - 1) + trs[i]) / period
        res[i + 1] = atr
    return res


def sma_atr(h, l, c, period=14):
    """Alternative definition: simple average of last `period` TRs (NOT Wilder)."""
    n = len(c)
    res = [None] * n
    if n < period + 1:
        return res
    trs = [max(h[i] - l[i], abs(h[i] - c[i - 1]), abs(l[i] - c[i - 1]))
           for i in range(1, n)]
    for i in range(period - 1, len(trs)):
        res[i + 1] = sum(trs[i - period + 1:i + 1]) / period
    return res


_ATR_MODE = 'wilder'  # 'wilder' (TradingView/TA-Lib) or 'sma' (set by --atr-sm)


def _calc_atr(h, l, c, period=14):
    if _ATR_MODE == 'sma':
        return sma_atr(h, l, c, period)
    return tv_atr(h, l, c, period)


def ema(series, period):
    k = 2.0 / (period + 1)
    out = [None] * len(series)
    if len(series) < period:
        return out
    seed = sum(series[:period]) / period
    out[period - 1] = seed
    prev = seed
    for i in range(period, len(series)):
        prev = series[i] * k + prev * (1 - k)
        out[i] = prev
    return out


def tv_macd_hist(c, fast=12, slow=26, sig=9):
    """MACD histogram = macd_line - signal_line (EMA fast - EMA slow, EMA9 signal)."""
    n = len(c)
    out = [None] * n
    ef = ema(c, fast)
    es = ema(c, slow)
    macd = [None] * n
    for i in range(n):
        if ef[i] is not None and es[i] is not None:
            macd[i] = ef[i] - es[i]
    # signal EMA over the non-None tail of macd
    start = next((i for i in range(n) if macd[i] is not None), None)
    if start is None:
        return out
    tail = macd[start:]
    esig = ema(tail, sig)
    for j, v in enumerate(esig):
        if v is not None and macd[start + j] is not None:
            out[start + j] = macd[start + j] - v
    return out


def tv_rsi(c, period=14):
    """TradingView RSI: Wilder smoothing of gains/losses, seeded with SMA(period)."""
    n = len(c)
    out = [None] * n
    if n < period + 1:
        return out
    gains, losses = [], []
    for i in range(1, n):
        d = c[i] - c[i - 1]
        gains.append(max(d, 0.0))
        losses.append(max(-d, 0.0))
    ag = sum(gains[:period]) / period
    al = sum(losses[:period]) / period
    out[period] = 100.0 if al == 0 else 100.0 - 100.0 / (1 + ag / al)
    for i in range(period, len(gains)):
        ag = (ag * (period - 1) + gains[i]) / period
        al = (al * (period - 1) + losses[i]) / period
        out[i + 1] = 100.0 if al == 0 else 100.0 - 100.0 / (1 + ag / al)
    return out


# ── event detection ─────────────────────────────────────────────────────────
def find_events(atr, ts, threshold, hysteresis=0.9, cooldown_min=0):
    """Cross UP through threshold. Hysteresis: re-arm only after ATR < T*hy."""
    events = []
    armed = True
    last_ev = -10**18
    for i in range(1, len(atr)):
        a0, a1 = atr[i - 1], atr[i]
        if a0 is None or a1 is None:
            continue
        if armed and a0 < threshold <= a1:
            if ts[i] - last_ev >= cooldown_min * 60:
                events.append(i)
                last_ev = ts[i]
                armed = False
        if not armed and a1 < threshold * hysteresis:
            armed = True
    return events


def direction_at(i, macd_hist, rsi):
    """Return (macd_dir, rsi_dir) each in {+1 LONG, -1 SHORT, 0 flat/unknown}."""
    m = 0
    if macd_hist[i] is not None:
        m = 1 if macd_hist[i] > 0 else (-1 if macd_hist[i] < 0 else 0)
    r = 0
    if rsi[i] is not None:
        r = 1 if rsi[i] > 50 else (-1 if rsi[i] < 50 else 0)
    return m, r


# ── outcome measurement ─────────────────────────────────────────────────────
def build_ts_index(ts):
    return {t: i for i, t in enumerate(ts)}


def outcomes(i, direction, closes, ts, idx_map, horizon_max=1440):
    """Direction-aligned forward stats from bar i close."""
    t0 = ts[i]
    p0 = closes[i]
    fwd = {}          # horizon -> dir-aligned %
    absfwd = {}       # horizon -> |%| regardless of direction
    for h in HORIZONS:
        target = t0 + h * 60
        j = idx_map.get(target)
        if j is None:  # gap: nearest bar within ±60s, must be AFTER entry bar
            for off in (60, -60):
                jj = idx_map.get(target + off)
                if jj is not None and jj > i:
                    j = jj
                    break
        if j is None:
            continue
        pct = (closes[j] / p0 - 1.0) * 100.0
        fwd[h] = pct * direction
        absfwd[h] = abs(pct)
    # MFE / MAE over 4h and 24h (walk by ts window)
    mfe = {}
    mae = {}
    for h in (240, 1440):
        end = t0 + h * 60
        best = 0.0   # direction-aligned best
        worst = 0.0  # direction-aligned worst (negative)
        j = i + 1
        while j < len(ts) and ts[j] <= end:
            pct = (closes[j] / p0 - 1.0) * 100.0 * direction
            if pct > best:
                best = pct
            if pct < worst:
                worst = pct
            j += 1
        mfe[h] = best
        mae[h] = worst
    # first-touch +/- X% direction-aligned within 24h
    end = t0 + 1440 * 60
    touch = {x: None for x in PCT_TARGETS}  # +1 hit (target in dir), -1 hit (wrong way)
    j = i + 1
    remaining = set(PCT_TARGETS)
    while j < len(ts) and ts[j] <= end and remaining:
        pct = (closes[j] / p0 - 1.0) * 100.0 * direction
        for x in list(remaining):
            if pct >= x:
                touch[x] = 1
                remaining.discard(x)
            elif pct <= -x:
                touch[x] = -1
                remaining.discard(x)
        j += 1
    return fwd, absfwd, mfe, mae, touch


# ── stats helpers ───────────────────────────────────────────────────────────
def mean(v):
    return sum(v) / len(v) if v else 0.0


def median(v):
    if not v:
        return 0.0
    s = sorted(v)
    n = len(s)
    return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2


def bootstrap_ci(v, rounds=4000, alpha=0.05, seed=7):
    if not v:
        return (0.0, 0.0)
    rng = random.Random(seed)
    n = len(v)
    means = []
    for _ in range(rounds):
        s = sum(v[rng.randrange(n)] for _ in range(n)) / n
        means.append(s)
    means.sort()
    lo = means[int(rounds * alpha / 2)]
    hi = means[int(rounds * (1 - alpha / 2))]
    return (lo, hi)


def binom_p_ge(k, n, p=0.5):
    """P(X >= k) for Binomial(n, p) — exact via log-space combinatorics."""
    if n == 0:
        return 1.0
    from math import comb
    return sum(comb(n, i) * p**i * (1 - p)**(n - i) for i in range(k, n + 1))


def pct(v):
    return 100.0 * v


# ── main study ──────────────────────────────────────────────────────────────
def run_coin(token, threshold, label=''):
    rows = load_candles(token)
    if len(rows) < 1000:
        print(f'{token}: only {len(rows)} candles — skip')
        return None
    ts = [r[0] for r in rows]
    h = [r[2] for r in rows]
    l = [r[3] for r in rows]
    c = [r[4] for r in rows]
    idx_map = build_ts_index(ts)

    atr = _calc_atr(h, l, c, 14)
    mhist = tv_macd_hist(c)
    rsi = tv_rsi(c)

    # price-normalized threshold (for cross-coin work): threshold in % of price
    atr_pct = [None if a is None else a / c[i] * 100.0 for i, a in enumerate(atr)]

    ev_raw = find_events(atr, ts, threshold, hysteresis=1.0)  # hyst=1.0 -> every raw cross
    ev_dec = find_events(atr, ts, threshold, hysteresis=0.9)

    result = {'token': token, 'threshold': threshold, 'n_raw': len(ev_raw), 'n_dec': len(ev_dec)}

    # baseline: every 60th bar with a determinable direction
    base_idx = [i for i in range(0, len(ts), 60)
                if mhist[i] is not None and rsi[i] is not None]

    def collect(events):
        rows_out = []
        skipped = 0
        for i in events:
            if i >= len(ts) - 15:
                continue
            m, r = direction_at(i, mhist, rsi)
            if m == 0 or r == 0:
                skipped += 1
                continue
            if m != r:
                skipped += 1
                continue
            d = m
            fwd, absfwd, mfe, mae, touch = outcomes(i, d, c, ts, idx_map)
            rows_out.append({'i': i, 'ts': ts[i], 'dir': d, 'fwd': fwd, 'abs': absfwd,
                             'mfe': mfe, 'mae': mae, 'touch': touch,
                             'atr': atr[i], 'atr_pct': atr_pct[i], 'rsi': rsi[i],
                             'mhist': mhist[i]})
        return rows_out, skipped

    ev_rows, ev_skip = collect(ev_dec)
    base_rows, base_skip = collect(base_idx)
    result['n_events'] = len(ev_rows)
    result['n_skipped'] = ev_skip
    result['n_baseline'] = len(base_rows)
    result['events'] = ev_rows
    result['baseline'] = base_rows
    return result


def print_report(res, threshold):
    ev, base = res['events'], res['baseline']
    tok = res['token']
    print('=' * 78)
    print(f"{tok}  ATR(14,1m) cross up through {threshold}  "
          f"[raw crosses={res['n_raw']}, declustered={res['n_dec']}, "
          f"tradeable={len(ev)}, skipped(no agree)={res['n_skipped']}]  "
          f"baseline n={len(base)}")
    if len(ev) < 5:
        print('  too few events — no conclusions')
        return
    print(f"  event ATR range: {min(e['atr'] for e in ev):.1f} - {max(e['atr'] for e in ev):.1f} USD")
    print(f"  LONG events: {sum(1 for e in ev if e['dir']==1)}   SHORT events: {sum(1 for e in ev if e['dir']==-1)}")

    hdr = f"{'horizon(n)':>12} | {'EV dir% mean':>13} {'med':>7} {'CI95':>16} {'WR>0%':>7} {'p2s':>8} | {'BASE dir% mean':>14} {'WR>0%':>7} | {'EV |move|%':>11} {'BASE |move|%':>13}"
    print(hdr)
    print('-' * len(hdr))
    for hz in HORIZONS:
        e = [e['fwd'][hz] for e in ev if hz in e['fwd']]
        b = [b['fwd'][hz] for b in base if hz in b['fwd']]
        ea = [e['abs'][hz] for e in ev if hz in e['abs']]
        ba = [b['abs'][hz] for b in base if hz in b['abs']]
        if not e:
            continue
        k = sum(1 for x in e if x > 0)
        n_e = len(e)
        p_up = binom_p_ge(k, n_e)            # P(X >= k)
        p_dn = binom_p_ge(n_e - k, n_e)      # P(X <= k), by symmetry of p=0.5
        p_two = min(1.0, 2 * min(p_up, p_dn))  # two-sided vs 50/50
        ci = bootstrap_ci(e)
        wr = pct(k / n_e)
        wr_b = pct(sum(1 for x in b if x > 0) / len(b)) if b else float('nan')
        print(f"{hz:>5}m n={n_e:<4} | {mean(e):>13.3f} {median(e):>7.3f} [{ci[0]:>6.3f},{ci[1]:>6.3f}] "
              f"{wr:>6.1f} {p_two:>8.2e} | {mean(b):>14.3f} {wr_b:>6.1f} | "
              f"{mean(ea):>11.3f} {mean(ba):>13.3f}")

    # MFE/MAE
    print('\n  direction-aligned excursion (event vs baseline):')
    for hz in (240, 1440):
        e_mfe = [e['mfe'][hz] for e in ev if hz in e['mfe']]
        e_mae = [e['mae'][hz] for e in ev if hz in e['mae']]
        b_mfe = [b['mfe'][hz] for b in base if hz in b['mfe']]
        b_mae = [b['mae'][hz] for b in base if hz in b['mae']]
        print(f"   {hz//60}h  MFE ev={mean(e_mfe):6.2f}% base={mean(b_mfe):6.2f}%   "
              f"MAE ev={mean(e_mae):6.2f}% base={mean(b_mae):6.2f}%")

    # first-touch within 24h
    print('\n  first-touch within 24h (direction-aligned):')
    print(f"   {'target':>8} | {'EV hit dir%':>11} {'EV wrong%':>10} {'EV none%':>9} | {'BASE hit%':>10} {'BASE wrong%':>11}")
    for x in PCT_TARGETS:
        eh = sum(1 for e in ev if e['touch'].get(x) == 1)
        ew = sum(1 for e in ev if e['touch'].get(x) == -1)
        en = sum(1 for e in ev if e['touch'].get(x) is None)
        bh = sum(1 for b in base if b['touch'].get(x) == 1)
        bw = sum(1 for b in base if b['touch'].get(x) == -1)
        n = len(ev)
        nb = len(base)
        print(f"   {x:>6}% | {pct(eh/n):>10.1f} {pct(ew/n):>9.1f} {pct(en/n):>8.1f} | "
              f"{pct(bh/nb):>9.1f} {pct(bw/nb):>10.1f}")


def sweep_thresholds(token):
    print('\n' + '=' * 78)
    print(f'THRESHOLD SWEEP ({token}) — declustered events, direction=MACD&RSI agree')
    print(f"{'T':>6} {'n':>5} | {'4h dir%':>9} {'4h WR%':>7} {'4h CI95':>18} | "
          f"{'24h dir%':>9} {'24h WR%':>7} {'24h CI95':>18} | {'24h |move|%':>11}")
    rows = load_candles(token)
    ts = [r[0] for r in rows]
    hh = [r[2] for r in rows]
    ll = [r[3] for r in rows]
    cc = [r[4] for r in rows]
    idx_map = build_ts_index(ts)
    atr = _calc_atr(hh, ll, cc, 14)
    mhist = tv_macd_hist(cc)
    rsi = tv_rsi(cc)
    for T in (40, 50, 60, 70, 80, 100):
        evs = find_events(atr, ts, T, hysteresis=0.9)
        f4, f24, a24 = [], [], []
        for i in evs:
            if i >= len(ts) - 15:
                continue
            m, r = direction_at(i, mhist, rsi)
            if m == 0 or r == 0 or m != r:
                continue
            fwd, absfwd, _, _, _ = outcomes(i, m, cc, ts, idx_map)
            if 240 in fwd:
                f4.append(fwd[240])
            if 1440 in fwd:
                f24.append(fwd[1440])
                a24.append(absfwd[1440])
        if not f24:
            print(f'{T:>6} {0:>5}  no events')
            continue
        k4 = sum(1 for x in f4 if x > 0)
        k24 = sum(1 for x in f24 if x > 0)
        ci4 = bootstrap_ci(f4, rounds=2000)
        ci24 = bootstrap_ci(f24, rounds=2000)
        print(f'{T:>6} {len(f24):>5} | {mean(f4):>9.3f} {pct(k4/len(f4)):>7.1f} '
              f'[{ci4[0]:>7.3f},{ci4[1]:>7.3f}] | {mean(f24):>9.3f} {pct(k24/len(f24)):>7.1f} '
              f'[{ci24[0]:>7.3f},{ci24[1]:>7.3f}] | {mean(a24):>11.3f}')


def time_split(token, threshold):
    print('\n' + '=' * 78)
    print(f'TIME SPLIT OOS ({token}, T={threshold}) — in-sample = first 15 days')
    res = run_coin(token, threshold)
    if not res or not res['events']:
        print('  no events')
        return
    ev = res['events']
    mid_ts = ev[0]['ts'] + 15 * 86400
    ins = [e for e in ev if e['ts'] < mid_ts]
    oos = [e for e in ev if e['ts'] >= mid_ts]
    for name, grp in (('IN (d1-15)', ins), ('OOS (d16-30)', oos)):
        if len(grp) < 3:
            print(f'  {name}: n={len(grp)} too few')
            continue
        f4 = [e['fwd'][240] for e in grp if 240 in e['fwd']]
        f24 = [e['fwd'][1440] for e in grp if 1440 in e['fwd']]
        k = sum(1 for x in f24 if x > 0)
        ci = bootstrap_ci(f24, rounds=2000)
        print(f'  {name}: n={len(grp)}  4h dir% mean={mean(f4):6.3f}  '
              f'24h dir% mean={mean(f24):6.3f} WR={pct(k/len(f24)):5.1f}% CI95=[{ci[0]:.3f},{ci[1]:.3f}]')


def _dir_variant(name, i, c, ts, mhist, rsi, ev_map, ret15=None):
    """Direction rules under test. Returns +1/-1/0 (0 = skip)."""
    if name == 'agree':
        m, r = direction_at(i, mhist, rsi)
        return m if m == r else 0
    if name == 'macd':
        if mhist[i] is None:
            return 0
        return 1 if mhist[i] > 0 else (-1 if mhist[i] < 0 else 0)
    if name == 'rsi50':
        if rsi[i] is None:
            return 0
        return 1 if rsi[i] > 50 else (-1 if rsi[i] < 50 else 0)
    if name == 'rsi_ext':
        if rsi[i] is None:
            return 0
        if rsi[i] >= 60:
            return 1
        if rsi[i] <= 40:
            return -1
        return 0
    if name == 'ret15':
        r = ret15[i]
        if r is None:
            return 0
        return 1 if r > 0 else (-1 if r < 0 else 0)
    raise ValueError(name)


def direction_variants(token, threshold):
    """Sensitivity: does the direction rule / entry timing change the answer?"""
    print('\n' + '=' * 78)
    print(f'DIRECTION-VARIANT SENSITIVITY ({token}, T={threshold}, declustered events)')
    rows = load_candles(token)
    ts = [r[0] for r in rows]
    hh = [r[2] for r in rows]
    ll = [r[3] for r in rows]
    cc = [r[4] for r in rows]
    idx_map = build_ts_index(ts)
    atr = _calc_atr(hh, ll, cc, 14)
    mhist = tv_macd_hist(cc)
    rsi = tv_rsi(cc)
    ret15 = [None] * len(cc)
    for i in range(15, len(cc)):
        ret15[i] = (cc[i] / cc[i - 15] - 1.0) * 100.0

    evs = [i for i in find_events(atr, ts, threshold, hysteresis=0.9)
           if i < len(ts) - 15]

    variants = [
        ('agree', 0), ('agree', 5), ('agree', 15),
        ('macd', 0), ('macd', 5), ('macd', 15),
        ('rsi50', 0), ('rsi50', 15),
        ('rsi_ext', 0), ('rsi_ext', 15),
        ('ret15', 0), ('ret15', 15),
    ]
    print(f"{'variant':>14} {'delay':>6} {'n':>4} | {'4h dir%':>9} {'4h WR%':>7} | "
          f"{'24h dir%':>9} {'24h WR%':>7} {'24h CI95':>18} | "
          f"{'3% dir/wrong':>13}")
    for vname, delay in variants:
        f4, f24, t3h, t3w = [], [], 0, 0
        n = 0
        for i in evs:
            j = i + delay
            if j >= len(ts):
                continue
            d = _dir_variant(vname, j, cc, ts, mhist, rsi, None, ret15)
            if d == 0:
                continue
            # entry at bar j close, outcome from there
            fwd, absfwd, mfe, mae, touch = outcomes(j, d, cc, ts, idx_map)
            n += 1
            if 240 in fwd:
                f4.append(fwd[240])
            if 1440 in fwd:
                f24.append(fwd[1440])
            if touch.get(3.0) == 1:
                t3h += 1
            elif touch.get(3.0) == -1:
                t3w += 1
        if not f24:
            print(f'{vname:>14} {delay:>6} {n:>4}  no events')
            continue
        k4 = sum(1 for x in f4 if x > 0)
        k24 = sum(1 for x in f24 if x > 0)
        ci = bootstrap_ci(f24, rounds=2000)
        print(f'{vname:>14} {delay:>6} {n:>4} | {mean(f4):>9.3f} {pct(k4/len(f4)):>7.1f} | '
              f'{mean(f24):>9.3f} {pct(k24/len(f24)):>7.1f} '
              f'[{ci[0]:>7.3f},{ci[1]:>7.3f}] | {t3h:>6}/{t3w:<6}')


def htf_direction_variants(token, threshold):
    """Direction from HIGHER timeframe 'obvious trend' instead of 1m oscillator."""
    print('\n' + '=' * 78)
    print(f'HTF-DIRECTION VARIANTS ({token}, T={threshold})')
    rows = load_candles(token)
    ts = [r[0] for r in rows]
    hh = [r[2] for r in rows]
    ll = [r[3] for r in rows]
    cc = [r[4] for r in rows]
    idx_map = build_ts_index(ts)
    atr = _calc_atr(hh, ll, cc, 14)
    mhist = tv_macd_hist(cc)
    rsi = tv_rsi(cc)

    # 15m aggregates (non-overlapping, using 1m closes)
    # direction proxies computed on 1m arrays then sampled at event time
    def ema_dir(period_up, period_dn):
        ef = ema(cc, period_up)
        es = ema(cc, period_dn)
        out = [None] * len(cc)
        for i in range(len(cc)):
            if ef[i] is not None and es[i] is not None:
                out[i] = 1 if ef[i] > es[i] else -1
        return out

    ema_fast_slow = ema_dir(20, 50)          # 1m EMA20 vs EMA50 (short trend)
    ret60 = [None] * len(cc)
    for i in range(60, len(cc)):
        ret60[i] = (cc[i] / cc[i - 60] - 1.0) * 100.0
    ret240 = [None] * len(cc)
    for i in range(240, len(cc)):
        ret240[i] = (cc[i] / cc[i - 240] - 1.0) * 100.0

    # 15m MACD hist: resample closes every 15 bars then MACD
    c15 = cc[::15]
    mh15 = tv_macd_hist(c15)
    mh15_at_1m = [None] * len(cc)
    for k, v in enumerate(mh15):
        if v is not None and k * 15 < len(cc):
            mh15_at_1m[k * 15] = v
    # forward-fill
    last = None
    for i in range(len(cc)):
        if mh15_at_1m[i] is not None:
            last = mh15_at_1m[i]
        else:
            mh15_at_1m[i] = last

    evs = [i for i in find_events(atr, ts, threshold, hysteresis=0.9)
           if i < len(ts) - 15]

    rules = [
        ('ema20/50', lambda i: ema_fast_slow[i] or 0),
        ('ret60', lambda i: (1 if (ret60[i] or 0) > 0 else (-1 if (ret60[i] or 0) < 0 else 0))),
        ('ret240', lambda i: (1 if (ret240[i] or 0) > 0 else (-1 if (ret240[i] or 0) < 0 else 0))),
        ('macd15m', lambda i: (1 if (mh15_at_1m[i] or 0) > 0 else (-1 if (mh15_at_1m[i] or 0) < 0 else 0))),
        ('1m_agree', lambda i: (lambda m, r: m if m == r else 0)(*direction_at(i, mhist, rsi))),
    ]
    print(f"{'rule':>10} {'n':>4} | {'4h dir%':>9} {'4h WR%':>7} | {'24h dir%':>9} {'24h WR%':>7} "
          f"{'24h CI95':>18} | {'3% dir/wrong':>13}")
    for rname, fn in rules:
        f4, f24, t3h, t3w, n = [], [], 0, 0, 0
        for i in evs:
            d = fn(i)
            if d == 0:
                continue
            fwd, _, _, _, touch = outcomes(i, d, cc, ts, idx_map)
            n += 1
            if 240 in fwd:
                f4.append(fwd[240])
            if 1440 in fwd:
                f24.append(fwd[1440])
            if touch.get(3.0) == 1:
                t3h += 1
            elif touch.get(3.0) == -1:
                t3w += 1
        if not f24:
            print(f'{rname:>10} {n:>4}  no events')
            continue
        k4 = sum(1 for x in f4 if x > 0)
        k24 = sum(1 for x in f24 if x > 0)
        ci = bootstrap_ci(f24, rounds=2000)
        print(f'{rname:>10} {n:>4} | {mean(f4):>9.3f} {pct(k4/len(f4)):>7.1f} | '
              f'{mean(f24):>9.3f} {pct(k24/len(f24)):>7.1f} '
              f'[{ci[0]:>7.3f},{ci[1]:>7.3f}] | {t3h:>6}/{t3w:<6}')


def move_size_test(token, threshold):
    """Direct test of the 'bigger move' claim: event |move| vs baseline |move|."""
    print('\n' + '=' * 78)
    print(f'MOVE-SIZE TEST ({token}, T={threshold}) — is the move after a cross BIGGER?')
    res = run_coin(token, threshold)
    if not res:
        return
    ev, base = res['events'], res['baseline']
    rng = random.Random(11)
    for hz in (60, 240, 1440):
        e = [x['abs'][hz] for x in ev if hz in x['abs']]
        b = [x['abs'][hz] for x in base if hz in x['abs']]
        if not e or not b:
            continue
        diff = mean(e) - mean(b)
        # bootstrap the DIFFERENCE
        rounds = 3000
        ds = []
        for _ in range(rounds):
            se = sum(e[rng.randrange(len(e))] for _ in range(len(e))) / len(e)
            sb = sum(b[rng.randrange(len(b))] for _ in range(len(b))) / len(b)
            ds.append(se - sb)
        ds.sort()
        lo, hi = ds[int(rounds * 0.025)], ds[int(rounds * 0.975)]
        # 3% touch rate comparison
        eh = sum(1 for x in ev if x['touch'].get(3.0) is not None)
        bh = sum(1 for x in base if x['touch'].get(3.0) is not None)
        print(f'  {hz:>5}m |mean|move| ev={mean(e):.3f}% base={mean(b):.3f}% diff={diff:+.3f}% '
              f'CI95=[{lo:+.3f},{hi:+.3f}]  n={len(e)}/{len(b)}')
    eh = sum(1 for x in ev if x['touch'].get(3.0) is not None)
    bh = sum(1 for x in base if x['touch'].get(3.0) is not None)
    print(f'  >=3% move within 24h: ev {eh}/{len(ev)} ({pct(eh/len(ev)):.1f}%) vs '
          f'base {bh}/{len(base)} ({pct(bh/len(base)):.1f}%)')
    # direction of the big moves
    ev3 = [x for x in ev if x['touch'].get(3.0) is not None]
    in_dir = sum(1 for x in ev3 if x['touch'][3.0] == 1)
    if ev3:
        from math import comb
        n = len(ev3)
        p = sum(comb(n, i) for i in range(in_dir, n + 1)) / 2**n
        print(f'  direction of those big moves: {in_dir}/{n} in momentum direction '
              f'(binom one-sided p={p:.4f})')
    base3 = [x for x in base if x['touch'].get(3.0) is not None]
    in_dir_b = sum(1 for x in base3 if x['touch'][3.0] == 1)
    if base3:
        print(f'  baseline big-move direction: {in_dir_b}/{len(base3)} '
              f'({pct(in_dir_b/len(base3)):.1f}% in direction rule)')


def cross_coin(token, threshold_pct):
    """Same study on another coin with ATR threshold in PERCENT of price."""
    print('\n' + '=' * 78)
    print(f'CROSS-COIN: {token}  ATR% cross up through {threshold_pct:.4f}%')
    rows = load_candles(token)
    if len(rows) < 1000:
        print('  insufficient data')
        return
    ts = [r[0] for r in rows]
    hh = [r[2] for r in rows]
    ll = [r[3] for r in rows]
    cc = [r[4] for r in rows]
    idx_map = build_ts_index(ts)
    atr = _calc_atr(hh, ll, cc, 14)
    atrp = [None if a is None else a / cc[i] * 100.0 for i, a in enumerate(atr)]
    mhist = tv_macd_hist(cc)
    rsi = tv_rsi(cc)
    evs = find_events(atrp, ts, threshold_pct, hysteresis=0.9)
    f4, f24, t3h, t3w, n = [], [], 0, 0, 0
    for i in evs:
        if i >= len(ts) - 15:
            continue
        m, r = direction_at(i, mhist, rsi)
        if m == 0 or r == 0 or m != r:
            continue
        fwd, _, _, _, touch = outcomes(i, m, cc, ts, idx_map)
        n += 1
        if 240 in fwd:
            f4.append(fwd[240])
        if 1440 in fwd:
            f24.append(fwd[1440])
        if touch.get(3.0) == 1:
            t3h += 1
        elif touch.get(3.0) == -1:
            t3w += 1
    if n < 5:
        print(f'  only {n} tradeable events — skip')
        return
    k4 = sum(1 for x in f4 if x > 0)
    k24 = sum(1 for x in f24 if x > 0) if f24 else 0
    ci = bootstrap_ci(f24, rounds=2000) if f24 else (0, 0)
    print(f'  events={n} | 4h dir% mean={mean(f4):+.3f} WR={pct(k4/len(f4)):.1f}% | '
          f'24h dir% mean={mean(f24) if f24 else 0:+.3f} '
          f'WR={pct(k24/len(f24)) if f24 else 0:.1f}% CI95=[{ci[0]:.3f},{ci[1]:.3f}] | '
          f'3% dir/wrong={t3h}/{t3w}')


def entry_timing(token, threshold):
    """Direction fixed AT the cross; vary only WHEN we enter. Isolates entry timing."""
    print('\n' + '=' * 78)
    print(f'ENTRY-TIMING ({token}, T={threshold}) — direction fixed at cross bar')
    rows = load_candles(token)
    ts = [r[0] for r in rows]
    hh = [r[2] for r in rows]
    ll = [r[3] for r in rows]
    cc = [r[4] for r in rows]
    idx_map = build_ts_index(ts)
    atr = _calc_atr(hh, ll, cc, 14)
    mhist = tv_macd_hist(cc)
    rsi = tv_rsi(cc)
    evs = [i for i in find_events(atr, ts, threshold, hysteresis=0.9)
           if i < len(ts) - 15]

    def fwd_from(entry_i, d):
        return outcomes(entry_i, d, cc, ts, idx_map)

    def pullback_entry(i, d, k_atr=0.5, max_bars=60):
        """First bar whose low retraces k*ATR against direction from event close."""
        p0 = cc[i]
        a = atr[i] or 0
        lvl = p0 - d * k_atr * a  # long: below entry; short: above entry
        for j in range(i + 1, min(i + 1 + max_bars, len(cc))):
            if (d == 1 and ll[j] <= lvl) or (d == -1 and hh[j] >= lvl):
                return j
        return None

    schemes = [
        ('at_cross_close', lambda i, d: i),
        ('delay_5', lambda i, d: i + 5),
        ('delay_15', lambda i, d: i + 15),
        ('delay_30', lambda i, d: i + 30),
        ('pullback_0.5ATR', None),  # special
        ('pullback_1.0ATR', None),
    ]
    print(f"{'scheme':>17} {'n':>4} {'filled':>6} | {'15m dir%':>9} {'4h dir%':>9} {'4h WR%':>7} | "
          f"{'24h dir%':>9} {'24h WR%':>7} {'24h CI95':>18}")
    for sname, fn in schemes:
        f15, f4, f24 = [], [], []
        n = filled = 0
        for i in evs:
            m, r = direction_at(i, mhist, rsi)
            if m == 0 or r == 0 or m != r:
                continue
            d = m
            if sname.startswith('pullback'):
                k = 0.5 if '0.5' in sname else 1.0
                j = pullback_entry(i, d, k_atr=k)
                if j is None:
                    continue
            else:
                j = fn(i, d)
                if j >= len(ts):
                    continue
            n += 1
            fwd, _, _, _, _ = fwd_from(j, d)
            filled += 1
            if 15 in fwd:
                f15.append(fwd[15])
            if 240 in fwd:
                f4.append(fwd[240])
            if 1440 in fwd:
                f24.append(fwd[1440])
        if not f4:
            print(f'{sname:>17} {n:>4} {filled:>6}  no fills')
            continue
        k4 = sum(1 for x in f4 if x > 0)
        k24 = sum(1 for x in f24 if x > 0) if f24 else 0
        ci = bootstrap_ci(f24, rounds=2000) if f24 else (0, 0)
        print(f'{sname:>17} {n:>4} {filled:>6} | {mean(f15):>9.3f} {mean(f4):>9.3f} '
              f'{pct(k4/len(f4)):>7.1f} | {mean(f24) if f24 else 0:>9.3f} '
              f'{pct(k24/len(f24)) if f24 else 0:>7.1f} [{ci[0]:>7.3f},{ci[1]:>7.3f}]')


def fresh_expansion(token, threshold):
    """Only the FIRST cross after a quiet stretch (no ATR>=T in prior Q hours).
    Natural reading of 'whenever ATR crosses 60': quiet -> expansion, not chop."""
    print('\n' + '=' * 78)
    print(f'FRESH-EXPANSION TEST ({token}, T={threshold})')
    rows = load_candles(token)
    ts = [r[0] for r in rows]
    hh = [r[2] for r in rows]
    ll = [r[3] for r in rows]
    cc = [r[4] for r in rows]
    idx_map = build_ts_index(ts)
    atr = _calc_atr(hh, ll, cc, 14)
    mhist = tv_macd_hist(cc)
    rsi = tv_rsi(cc)

    def fresh_events(quiet_hours):
        q = quiet_hours * 3600
        out = []
        last_above = None  # ts of last bar with ATR >= T
        armed = True
        for i in range(1, len(atr)):
            a0, a1 = atr[i - 1], atr[i]
            if a0 is None or a1 is None:
                continue
            if a1 >= threshold:
                if armed and a0 < threshold <= a1:
                    if last_above is None or (ts[i] - last_above) >= q:
                        out.append(i)
                    armed = False
                last_above = ts[i]
            else:
                if a1 < threshold * 0.9:
                    armed = True
        return out

    for qh in (4, 12, 24):
        evs = [i for i in fresh_events(qh) if i < len(ts) - 15]
        f4, f24, t3h, t3w, n = [], [], 0, 0, 0
        for i in evs:
            m, r = direction_at(i, mhist, rsi)
            if m == 0 or r == 0 or m != r:
                continue
            fwd, _, _, _, touch = outcomes(i, m, cc, ts, idx_map)
            n += 1
            if 240 in fwd:
                f4.append(fwd[240])
            if 1440 in fwd:
                f24.append(fwd[1440])
            if touch.get(3.0) == 1:
                t3h += 1
            elif touch.get(3.0) == -1:
                t3w += 1
        if n < 3:
            print(f'  quiet>={qh}h: n={n} too few')
            continue
        k4 = sum(1 for x in f4 if x > 0)
        k24 = sum(1 for x in f24 if x > 0) if f24 else 0
        ci = bootstrap_ci(f24, rounds=2000) if f24 else (0, 0)
        print(f'  quiet>={qh:>2}h: n={n:>3} | 4h dir%={mean(f4):+.3f} WR={pct(k4/len(f4)):5.1f}% | '
              f'24h dir%={mean(f24) if f24 else 0:+.3f} WR={pct(k24/len(f24)) if f24 else 0:5.1f}% '
              f'CI95=[{ci[0]:+.3f},{ci[1]:+.3f}] | 3% dir/wrong={t3h}/{t3w}')


def _load_htf(token, table, interval_s):
    """Completed higher-timeframe bars (ts, open, high, low, close)."""
    conn = None
    try:
        conn = sqlite3.connect(DB, timeout=10)
        rows = conn.execute(
            f"SELECT ts, open, high, low, close FROM {table} "
            f"WHERE token = ? ORDER BY ts ASC", (token.upper(),)
        ).fetchall()
        return rows, interval_s
    finally:
        if conn:
            conn.close()


def _last_completed_idx(hts, interval_s, t):
    """Index of last bar fully completed before time t (bar_ts + interval <= t)."""
    import bisect
    # bars with ts <= t - interval are completed
    k = bisect.bisect_right(hts, t - interval_s) - 1
    return k


def htf_trend_study(token, threshold, interval='1h', threshold_pct=None):
    """CEO hypothesis (2026-11-06): direction comes from the ESTABLISHED
    higher-timeframe trend; the ATR spike only ACCELERATES that move.

    Direction rules from completed 1h/4h bars only (no lookahead), compared
    against the 1m-oscillator direction that already failed."""
    print('\n' + '=' * 78)
    print(f'HTF-ESTABLISHED-TREND STUDY ({token}, T={threshold}, trend TF={interval})')

    rows = load_candles(token)
    ts = [r[0] for r in rows]
    hh = [r[2] for r in rows]
    ll = [r[3] for r in rows]
    cc = [r[4] for r in rows]
    idx_map = build_ts_index(ts)
    atr = _calc_atr(hh, ll, cc, 14)
    m1 = tv_macd_hist(cc)
    r1 = tv_rsi(cc)
    thr_used = threshold
    if threshold_pct is not None:
        atr = [(a / cc[i] * 100.0) if a is not None else None
               for i, a in enumerate(atr)]
        thr_used = threshold_pct

    hrows, iv = _load_htf(token, f'candles_{interval}',
                          {'5m': 300, '15m': 900, '1h': 3600, '4h': 14400}[interval])
    hts = [r[0] for r in hrows]
    hc = [r[4] for r in hrows]
    if len(hc) < 60:
        print(f'  only {len(hc)} {interval} bars — skip')
        return
    # precompute indicators over full HTF series (each index uses only past bars)
    e20 = ema(hc, 20)
    e50 = ema(hc, 50)
    mh = tv_macd_hist(hc)

    def htf_dir(t):
        """Established trend direction at time t: +1/-1/0 from completed bars."""
        k = _last_completed_idx(hts, iv, t)
        if k < 50:
            return 0
        if e20[k] is None or e50[k] is None:
            return 0
        return 1 if e20[k] > e50[k] else -1

    def htf_dir_macd(t):
        k = _last_completed_idx(hts, iv, t)
        if k < 30 or mh[k] is None:
            return 0
        return 1 if mh[k] > 0 else (-1 if mh[k] < 0 else 0)

    slope_n = max(6, int(3600 / iv))  # ~1 hour of trend slope

    def htf_dir_slope(t):
        k = _last_completed_idx(hts, iv, t)
        if k < slope_n:
            return 0
        r = (hc[k] / hc[k - slope_n] - 1.0) * 100.0
        return 1 if r > 0 else (-1 if r < 0 else 0)

    # 4h trend rule (always from candles_4h)
    h4, _ = _load_htf(token, 'candles_4h', 14400)
    h4ts = [r[0] for r in h4]
    h4c = [r[4] for r in h4]
    e20_4 = ema(h4c, 20)
    e50_4 = ema(h4c, 50)

    def htf4_dir(t):
        k = _last_completed_idx(h4ts, 14400, t)
        if k < 50 or e20_4[k] is None or e50_4[k] is None:
            return 0
        return 1 if e20_4[k] > e50_4[k] else -1

    evs = [i for i in find_events(atr, ts, thr_used, hysteresis=0.9)
           if i < len(ts) - 15]
    base = [i for i in range(0, len(ts), 60) if i < len(ts) - 15]

    rules = [
        (f'ema_{interval}', htf_dir),
        (f'macd_{interval}', htf_dir_macd),
        (f'slope{slope_n}_{interval}', htf_dir_slope),
    ]
    if interval != '4h':
        rules.append(('ema_4h', htf4_dir))
        rules.append((f'{interval}+4h agree',
                      lambda t: (lambda a, b: a if a == b else 0)(htf_dir(t), htf4_dir(t))))

    HZ = [15, 30, 60, 120, 240, 480, 1440]
    print(f"{'rule':>26} {'n':>4} | {'15m WR':>7} {'1h dir%':>8} {'1h WR':>7} | "
          f"{'4h dir%':>8} {'4h WR':>7} {'4h CI95':>18} | {'24h WR':>7} | "
          f"{'with-trend 1h':>13} {'counter 1h':>11}")

    for rname, fn in rules:
        ev_vals = {h: [] for h in HZ}
        base_vals = {h: [] for h in HZ}
        with_t, counter_t = [], []
        n_ev = n_base = 0
        for i in evs:
            d = fn(ts[i])
            if d == 0:
                continue
            fwd, _, _, _, _ = outcomes(i, d, cc, ts, idx_map)
            n_ev += 1
            for h in HZ:
                if h in fwd:
                    ev_vals[h].append(fwd[h])
            # with-trend vs counter-trend split by 1m momentum at spike
            m, r = direction_at(i, m1, r1)
            if m == d:
                if 60 in fwd:
                    with_t.append(fwd[60])
            elif m == -d:
                if 60 in fwd:
                    counter_t.append(fwd[60])
        for i in base:
            d = fn(ts[i])
            if d == 0:
                continue
            fwd, _, _, _, _ = outcomes(i, d, cc, ts, idx_map)
            n_base += 1
            for h in HZ:
                if h in fwd:
                    base_vals[h].append(fwd[h])
        if n_ev < 5:
            print(f'{rname:>26} {n_ev:>4}  too few')
            continue
        def wr(v):
            return pct(sum(1 for x in v if x > 0) / len(v)) if v else float('nan')
        def mn(v):
            return mean(v) if v else 0.0
        ci240 = bootstrap_ci(ev_vals[240], rounds=2000) if ev_vals[240] else (0, 0)
        wt = mean(with_t) if with_t else 0.0
        ct = mean(counter_t) if counter_t else 0.0
        print(f'{rname:>26} {n_ev:>4} | {wr(ev_vals[15]):>7.1f} {mn(ev_vals[60]):>8.3f} '
              f'{wr(ev_vals[60]):>7.1f} | {mn(ev_vals[240]):>8.3f} {wr(ev_vals[240]):>7.1f} '
              f'[{ci240[0]:>7.3f},{ci240[1]:>7.3f}] | {wr(ev_vals[1440]):>7.1f} | '
              f'{wt:>13.3f} {ct:>11.3f}  (n {len(with_t)}/{len(counter_t)})')

    # Strict CEO rule: established 1h trend AND 1m spike momentum AGREE
    print(f'\n  STRICT (CEO) rule: {interval} established trend AND 1m MACD/RSI at spike agree:')
    for hz in HZ:
        ev_v, base_v = [], []
        n = 0
        for i in evs:
            d = htf_dir(ts[i])
            m, r = direction_at(i, m1, r1)
            if d == 0 or m == 0 or m != d or r != d:
                continue
            fwd, _, _, _, _ = outcomes(i, d, cc, ts, idx_map)
            n += 1
            if hz in fwd:
                ev_v.append(fwd[hz])
        for i in base:
            d = htf_dir(ts[i])
            m, r = direction_at(i, m1, r1)
            if d == 0 or m == 0 or m != d or r != d:
                continue
            fwd, _, _, _, _ = outcomes(i, d, cc, ts, idx_map)
            if hz in fwd:
                base_v.append(fwd[hz])
        if not ev_v:
            continue
        k = sum(1 for x in ev_v if x > 0)
        ci = bootstrap_ci(ev_v, rounds=2000)
        bwr = pct(sum(1 for x in base_v if x > 0) / len(base_v)) if base_v else float('nan')
        print(f'    {hz:>5}m n={len(ev_v):>3} dir% mean={mean(ev_v):+7.3f} WR={pct(k/len(ev_v)):5.1f}% '
              f'CI=[{ci[0]:+6.3f},{ci[1]:+6.3f}] | base n={len(base_v):>4} WR={bwr:5.1f}%')


def _trend_rule_builders(token, interval):
    """Direction rule callables from COMPLETED bars of `interval` candles.
    Returns (rules, htf_dir) where rules = [(name, fn(t)->+1/-1/0), ...]."""
    iv = {'5m': 300, '15m': 900, '1h': 3600, '4h': 14400}[interval]
    hrows, _ = _load_htf(token, f'candles_{interval}', iv)
    hts = [r[0] for r in hrows]
    hc = [r[4] for r in hrows]
    if len(hc) < 60:
        return None, None
    e20 = ema(hc, 20)
    e50 = ema(hc, 50)
    mh = tv_macd_hist(hc)
    slope_n = max(6, int(3600 / iv))

    def htf_dir(t):
        k = _last_completed_idx(hts, iv, t)
        if k < 50 or e20[k] is None or e50[k] is None:
            return 0
        return 1 if e20[k] > e50[k] else -1

    def macd_dir(t):
        k = _last_completed_idx(hts, iv, t)
        if k < 30 or mh[k] is None:
            return 0
        return 1 if mh[k] > 0 else (-1 if mh[k] < 0 else 0)

    def slope_dir(t):
        k = _last_completed_idx(hts, iv, t)
        if k < slope_n:
            return 0
        r = (hc[k] / hc[k - slope_n] - 1.0) * 100.0
        return 1 if r > 0 else (-1 if r < 0 else 0)

    # 4h context rule
    h4, _ = _load_htf(token, 'candles_4h', 14400)
    h4ts = [r[0] for r in h4]
    h4c = [r[4] for r in h4]
    e20_4 = ema(h4c, 20)
    e50_4 = ema(h4c, 50)

    def dir4(t):
        k = _last_completed_idx(h4ts, 14400, t)
        if k < 50 or e20_4[k] is None or e50_4[k] is None:
            return 0
        return 1 if e20_4[k] > e50_4[k] else -1

    rules = [
        (f'ema_{interval}', htf_dir),
        (f'macd_{interval}', macd_dir),
        (f'slope{slope_n}_{interval}', slope_dir),
    ]
    if interval != '4h':
        rules.append(('ema_4h', dir4))
        rules.append((f'{interval}+4h agree',
                      lambda t: (lambda a, b: a if a == b else 0)(htf_dir(t), dir4(t))))
    return rules, htf_dir


CONTINUUM_DB = None  # set lazily from paths


def _continuum_rules(token):
    """Continuum-score direction rules (CEO 2026-11-06: <50 short, >50 long).
    Returns ([(name, fn), ...] or None, score_fn). History from continuum.db."""
    global CONTINUUM_DB
    try:
        from paths import HERMES_DATA as _HD
        if CONTINUUM_DB is None:
            CONTINUUM_DB = os.path.join(_HD, 'continuum.db')
        if not os.path.exists(CONTINUUM_DB):
            return None, None
        conn = None
        try:
            conn = sqlite3.connect(CONTINUUM_DB, timeout=10)
            rows = conn.execute(
                "SELECT ts, state_score FROM continuum_states "
                "WHERE token = ? AND state_score IS NOT NULL ORDER BY ts ASC",
                (token.upper(),)).fetchall()
        finally:
            if conn:
                conn.close()
        if len(rows) < 1000:
            return None, None
        import bisect
        cts = [r[0] for r in rows]
        cs = [r[1] for r in rows]

        def score_at(t):
            k = bisect.bisect_right(cts, t) - 1
            return cs[k] if k >= 0 else None

        def cont50(t):
            s = score_at(t)
            if s is None:
                return 0
            return 1 if s >= 50 else -1

        def cont55(t):
            s = score_at(t)
            if s is None:
                return 0
            if s >= 55:
                return 1
            if s <= 45:
                return -1
            return 0

        return [('cont_50', cont50), ('cont_55', cont55)], score_at
    except Exception:
        return None, None


def continuum_study(token='BTC', threshold=60.0, flip=False, half=None):
    """CEO add-on: continuum score as direction for the ATR↑60 event study.
    flip=True inverts it (CEO 2026-11-06: 'previous move was OVER when the new
    ATR spike occurred' → mean-revert against the score). Full horizons,
    event vs random vs ATR-state baselines, optional OOS half."""
    print('\n' + '=' * 78)
    print(f'CONTINUUM DIRECTION STUDY ({token}, T={threshold}, '
          f'flip={flip}, half={half})')
    rows = load_candles(token)
    ts = [r[0] for r in rows]
    hh = [r[2] for r in rows]
    ll = [r[3] for r in rows]
    cc = [r[4] for r in rows]
    idx_map = build_ts_index(ts)
    atr = _calc_atr(hh, ll, cc, 14)
    m1 = tv_macd_hist(cc)
    r1 = tv_rsi(cc)
    cont_rules, score_at = _continuum_rules(token)
    if not cont_rules:
        print('  no continuum history for token — skip')
        return

    # 1h EMA trend for combos
    hrows, iv = _load_htf(token, 'candles_1h', 3600)
    hts = [r[0] for r in hrows]
    hc = [r[4] for r in hrows]
    e20 = ema(hc, 20)
    e50 = ema(hc, 50)

    def ema1h(t):
        k = _last_completed_idx(hts, iv, t)
        if k < 50 or e20[k] is None or e50[k] is None:
            return 0
        return 1 if e20[k] > e50[k] else -1

    evs = [i for i in find_events(atr, ts, threshold, hysteresis=0.9)
           if i < len(ts) - 15]
    base_idx = [i for i in range(0, len(ts), 60) if i < len(ts) - 15]
    mid_t = (ts[0] + ts[-1]) / 2.0
    if half in ('first', 'second'):
        evs = [i for i in evs
               if (ts[i] < mid_t) == (half == 'first')]
        base_idx = [i for i in base_idx
                    if (ts[i] < mid_t) == (half == 'first')]
    ev_set = set(evs)
    state_idx = []
    last_s = -10**18
    for i in range(len(ts) - 15):
        if half in ('first', 'second'):
            if not ((ts[i] < mid_t) == (half == 'first')):
                continue
        if (atr[i] is not None and atr[i] >= threshold
                and i not in ev_set and ts[i] - last_s >= 3600):
            state_idx.append(i)
            last_s = ts[i]  # audit B1 fix: hourly spacing must actually advance

    _d50 = dict(cont_rules)['cont_50']
    _d55 = dict(cont_rules)['cont_55']
    _sfx = '_flip' if flip else ''
    if flip:
        f50 = lambda t: -_d50(t)
        f55 = lambda t: -_d55(t)
    else:
        f50, f55 = _d50, _d55
    rules = [
        ('cont_50' + _sfx, f50),
        ('cont_55' + _sfx, f55),
        ('cont55' + _sfx + '+1m agree', f55),  # +1m macd/rsi agree
        ('cont55' + _sfx + '+1h agree',
         lambda t: (lambda a, b: a if a == b else 0)(f55(t), ema1h(t))),
    ]
    HZ = [15, 30, 60, 120, 240, 480, 1440]

    def collect(idx_list, rule_fn, need_1m=False):
        out = {h: [] for h in HZ}
        for i in idx_list:
            d = rule_fn(ts[i])
            if need_1m:
                m, r = direction_at(i, m1, r1)
                if d == 0 or m == 0 or m != d or r != d:
                    continue
            if d == 0:
                continue
            fwd, _, _, _, _ = outcomes(i, d, cc, ts, idx_map)
            for h in HZ:
                if h in fwd:
                    out[h].append(fwd[h])
        return out

    rng = random.Random(77)

    def diff_ci(a, b, seed):
        r = random.Random(seed)
        rounds = 2000
        ds = []
        for _ in range(rounds):
            sa = sum(a[r.randrange(len(a))] for _ in range(len(a))) / len(a) if a else 0
            sb = sum(b[r.randrange(len(b))] for _ in range(len(b))) / len(b) if b else 0
            ds.append(sa - sb)
        ds.sort()
        return ds[int(rounds * 0.025)], ds[int(rounds * 0.975)]

    print(f"{'rule':>16} {'hz':>5} {'n':>4} {'ev mean':>8} {'ev WR':>7} | "
          f"{'state mean':>10} {'rand mean':>9} | {'ev-state':>9} {'CI95':>18}")
    for rname, rfn in rules:
        need_1m = rname.endswith('1m agree')
        for h in HZ:
            e = collect(evs, rfn, need_1m).get(h, [])
            if len(e) < 20:
                continue
            s = collect(state_idx, rfn, need_1m).get(h, [])
            b = collect(base_idx, rfn, need_1m).get(h, [])
            k = sum(1 for x in e if x > 0)
            lo, hi = diff_ci(e, s, 77) if s else (0, 0)
            d = (mean(e) - mean(s)) if s else 0.0
            print(f'{rname:>16} {h:>5} {len(e):>4} {mean(e):>+8.3f} '
                  f'{pct(k / len(e)):>6.1f}% | {mean(s) if s else 0:>+10.3f} '
                  f'{mean(b) if b else 0:>+9.3f} | {d:>+9.3f} '
                  f'[{lo:>+7.3f},{hi:>+7.3f}]')


def pooled_ceo(interval, threshold_pct, coins, half=None):
    """CEO hypothesis pooled across coins: established `interval` trend direction
    after an ATR-expansion spike. Pooled event bootstrap + per-coin sign test.
    half: None | 'first' | 'second' (OOS time split, each coin's own midpoint)."""
    print('\n' + '=' * 78)
    print(f'POOLED CEO STUDY (trend TF={interval}, ATR% cross {threshold_pct}%, '
          f'{len(coins)} coins, half={half})')
    HZ = [60, 240, 1440]
    store = {}   # (rule, hz) -> values ; (rule, coin, hz) -> values
    coin_means = {}  # (rule, coin, hz) -> mean
    for ck in coins:
        rows = load_candles(ck)
        if len(rows) < 1000:
            continue
        ts = [r[0] for r in rows]
        hh = [r[2] for r in rows]
        ll = [r[3] for r in rows]
        cc = [r[4] for r in rows]
        idx_map = build_ts_index(ts)
        atr = _calc_atr(hh, ll, cc, 14)
        ap = [(a / cc[i] * 100.0) if a is not None else None for i, a in enumerate(atr)]
        m1 = tv_macd_hist(cc)
        r1 = tv_rsi(cc)
        built, htf_dir = _trend_rule_builders(ck, interval)
        if built is None:
            continue
        evs = [i for i in find_events(ap, ts, threshold_pct, hysteresis=0.9)
               if i < len(ts) - 15]
        base_idx = [i for i in range(0, len(ts), 60) if i < len(ts) - 15]
        if half in ('first', 'second'):
            mid_t = (ts[0] + ts[-1]) / 2.0
            def _in_half(i, _m=mid_t):
                return (ts[i] < _m) if half == 'first' else (ts[i] >= _m)
            evs = [i for i in evs if _in_half(i)]
            base_idx = [i for i in base_idx if _in_half(i)]
        # continuum-score direction rules (BTC history in continuum.db)
        cont_rules, _ = _continuum_rules(ck)
        if cont_rules:
            built = list(built) + cont_rules

        def _collect(idx_list, tag_suffix=''):
            for rname, fn in built:
                for i in idx_list:
                    d = fn(ts[i])
                    if d == 0:
                        continue
                    fwd, _, _, _, _ = outcomes(i, d, cc, ts, idx_map)
                    for hz in HZ:
                        if hz in fwd:
                            store.setdefault((rname + tag_suffix, hz), []).append(fwd[hz])
                            coin_means.setdefault((rname + tag_suffix, ck, hz), []).append(fwd[hz])
            # STRICT: established trend AND 1m MACD/RSI at spike agree
            for i in idx_list:
                d = htf_dir(ts[i])
                m, r = direction_at(i, m1, r1)
                if d == 0 or m == 0 or m != d or r != d:
                    continue
                fwd, _, _, _, _ = outcomes(i, d, cc, ts, idx_map)
                for hz in HZ:
                    if hz in fwd:
                        store.setdefault(('STRICT' + tag_suffix, hz), []).append(fwd[hz])
                        coin_means.setdefault(('STRICT' + tag_suffix, ck, hz), []).append(fwd[hz])

        _collect(evs, '')       # events
        _collect(base_idx, '|base')  # baseline: same rule, random hourly times
        # ATR-STATE baseline: high-ATR minutes that are NOT crossing (audit control)
        ev_set = set(evs)
        mid_t = (ts[0] + ts[-1]) / 2.0
        state_idx = []
        last_s = -10**18
        for i in range(len(ts) - 15):
            if half in ('first', 'second'):
                if not ((ts[i] < mid_t) if half == 'first' else (ts[i] >= mid_t)):
                    continue
            if (ap[i] is not None and ap[i] >= threshold_pct
                    and i not in ev_set and ts[i] - last_s >= 3600):
                state_idx.append(i)
                last_s = ts[i]
        _collect(state_idx, '|state')

    from math import comb
    event_rules = sorted({k[0] for k in store if not k[0].endswith('|base')
                          and not k[0].endswith('|state')})
    print(f"{'rule':>18} {'hz':>5} {'n':>5} {'ev mean':>8} {'ev WR':>7} | "
          f"{'state mean':>10} {'st WR':>7} | {'ev-state diff':>14} {'CI95':>18} | "
          f"{'ev-rand diff':>13} | {'coins+/−':>9} {'sign-p':>7}")
    rng2 = random.Random(31)
    for rname in event_rules:
        def _diff_ci(a, bb, seed):
            r = random.Random(seed)
            rounds = 2000
            ds = []
            for _ in range(rounds):
                sa = sum(a[r.randrange(len(a))] for _ in range(len(a))) / len(a)
                sb = sum(bb[r.randrange(len(bb))] for _ in range(len(bb))) / len(bb)
                ds.append(sa - sb)
            ds.sort()
            return (mean(a) - mean(bb),
                    ds[int(rounds * 0.025)], ds[int(rounds * 0.975)])

        for hz in HZ:
            v = store.get((rname, hz))
            b = store.get((rname + '|base', hz))
            s = store.get((rname + '|state', hz))
            if not v or len(v) < 50 or not b or not s or len(s) < 30:
                continue
            d_s, lo_s, hi_s = _diff_ci(v, s, 31)
            d_r, lo_r, hi_r = _diff_ci(v, b, 32)
            # per-coin event vs state
            pos = neg = 0
            for ck in coins:
                cm = coin_means.get((rname, ck, hz))
                cs = coin_means.get((rname + '|state', ck, hz))
                if not cm or not cs:
                    continue
                if mean(cm) > mean(cs):
                    pos += 1
                elif mean(cm) < mean(cs):
                    neg += 1
            n_c = pos + neg
            sp = (sum(comb(n_c, i) for i in range(pos, n_c + 1)) / 2**n_c
                  if n_c else 1.0)
            k = sum(1 for x in v if x > 0)
            ks = sum(1 for x in s if x > 0)
            print(f'{rname:>18} {hz:>5} {len(v):>5} {mean(v):>+8.3f} '
                  f'{pct(k / len(v)):>6.1f}% | {mean(s):>+10.3f} '
                  f'{pct(ks / len(s)):>6.1f}% | {d_s:>+14.3f} '
                  f'[{lo_s:>+7.3f},{hi_s:>+7.3f}] | {d_r:>+13.3f} '
                  f'[{lo_r:>+6.3f},{hi_r:>+6.3f}] | {pos:>4} / {neg:<4} {sp:>7.3f}')


def recent_case_study(token, threshold, days=3):
    """Show every event in the last `days` days: direction + what happened next."""
    print('\n' + '=' * 78)
    print(f'RECENT CASE STUDY ({token}, last {days}d, T={threshold})')
    rows = load_candles(token)
    ts = [r[0] for r in rows]
    hh = [r[2] for r in rows]
    ll = [r[3] for r in rows]
    cc = [r[4] for r in rows]
    idx_map = build_ts_index(ts)
    atr = _calc_atr(hh, ll, cc, 14)
    mhist = tv_macd_hist(cc)
    rsi = tv_rsi(cc)
    cutoff = ts[-1] - days * 86400
    evs = [i for i in find_events(atr, ts, threshold, hysteresis=0.9) if ts[i] >= cutoff]
    import datetime
    for i in evs:
        m, r = direction_at(i, mhist, rsi)
        d = m if m == r else 0
        fwd, absfwd, mfe, mae, touch = outcomes(i, d or 1, cc, ts, idx_map)
        dname = {1: 'LONG ', -1: 'SHORT', 0: 'SKIP '}[d]
        print(f"  {datetime.datetime.fromtimestamp(ts[i], datetime.UTC):%m-%d %H:%M} "
              f"ATR={atr[i]:6.1f} RSI={rsi[i]:5.1f} macd_hist={mhist[i]:+.2f} -> {dname} "
              f"| 1h {fwd.get(60, float('nan')):+6.2f}%  4h {fwd.get(240, float('nan')):+6.2f}% "
              f"24h {fwd.get(1440, float('nan')):+6.2f}%  "
              f"4h MFE {mfe.get(240, 0):+5.2f}/MAE {mae.get(240, 0):+5.2f}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--coin', default='BTC')
    ap.add_argument('--threshold', type=float, default=60.0)
    ap.add_argument('--sweep', action='store_true')
    ap.add_argument('--split', action='store_true')
    ap.add_argument('--recent', action='store_true')
    ap.add_argument('--variants', action='store_true')
    ap.add_argument('--htf', action='store_true')
    ap.add_argument('--movesize', action='store_true')
    ap.add_argument('--entry', action='store_true')
    ap.add_argument('--fresh', action='store_true')
    ap.add_argument('--ceo', nargs='?', const='1h', default=None,
                    help='CEO hypothesis study; optional trend TF (5m/15m/1h/4h), default 1h')
    ap.add_argument('--use-pct', action='store_true',
                    help='treat threshold as ATR% of price (with --pct) instead of USD')
    ap.add_argument('--pooled', action='store_true',
                    help='pooled cross-coin CEO study across trend TFs 5m/15m/1h')
    ap.add_argument('--half', choices=['first', 'second'], default=None,
                    help='OOS time split for --pooled (each coin midpoint)')
    ap.add_argument('--cont', action='store_true',
                    help='continuum-score direction study (<50 short >50 long)')
    ap.add_argument('--cont-flip', action='store_true',
                    help='FLIPPED continuum direction (mean-revert vs score)')
    ap.add_argument('--atr-sm', action='store_true',
                    help='use SMA-of-TR ATR instead of Wilder/RMA (definition sensitivity)')
    ap.add_argument('--coins', default='', help='comma list for cross-coin ATR%% study')
    ap.add_argument('--pct', type=float, default=0.076, help='ATR%% threshold for cross-coin')
    args = ap.parse_args()
    global _ATR_MODE
    if args.atr_sm:
        _ATR_MODE = 'sma'

    res = run_coin(args.coin, args.threshold)
    if res:
        print_report(res, args.threshold)
    if args.sweep:
        sweep_thresholds(args.coin)
    if args.split:
        time_split(args.coin, args.threshold)
    if args.variants:
        direction_variants(args.coin, args.threshold)
    if args.htf:
        htf_direction_variants(args.coin, args.threshold)
    if args.movesize:
        move_size_test(args.coin, args.threshold)
    if args.entry:
        entry_timing(args.coin, args.threshold)
    if args.fresh:
        fresh_expansion(args.coin, args.threshold)
    if args.ceo:
        htf_trend_study(args.coin, args.threshold, interval=args.ceo,
                        threshold_pct=(args.pct if args.use_pct else None))
    if args.pooled:
        default_coins = ['BTC', 'SOL', 'SUI', 'TAO', 'PUMP', 'GALA', 'GMX',
                         'IMX', 'SAND', 'FOGO', 'COMP', 'DYM']
        coin_list = ([c.strip() for c in args.coins.split(',') if c.strip()]
                     if args.coins else default_coins)
        for tf in ('5m', '15m', '1h'):
            pooled_ceo(tf, args.pct, coin_list, half=args.half)
    if args.cont:
        continuum_study(args.coin, args.threshold, flip=False, half=args.half)
    if args.cont_flip:
        continuum_study(args.coin, args.threshold, flip=True, half=args.half)
    if args.coins:
        for c in args.coins.split(','):
            cross_coin(c.strip(), args.pct)
    if args.recent:
        recent_case_study(args.coin, args.threshold)


if __name__ == '__main__':
    main()
