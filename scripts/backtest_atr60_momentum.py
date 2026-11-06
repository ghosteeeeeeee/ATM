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
        if j is None:  # gap: nearest within 90s
            j = idx_map.get(target + 60) or idx_map.get(target - 60)
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

    hdr = f"{'horizon':>8} | {'EV dir% mean':>13} {'med':>7} {'CI95':>16} {'WR>0%':>7} {'p2s':>8} | {'BASE dir% mean':>14} {'WR>0%':>7} | {'EV |move|%':>11} {'BASE |move|%':>13}"
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
        p_dn = binom_p_ge(n_e - k + 1, n_e)  # P(X <= k)
        p_two = min(1.0, 2 * min(p_up, p_dn))  # two-sided vs 50/50
        ci = bootstrap_ci(e)
        wr = pct(k / n_e)
        wr_b = pct(sum(1 for x in b if x > 0) / len(b)) if b else float('nan')
        print(f"{hz:>6}m | {mean(e):>13.3f} {median(e):>7.3f} [{ci[0]:>6.3f},{ci[1]:>6.3f}] "
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
    ap.add_argument('--atr-sm', action='store_true',
                    help='use SMA-of-TR ATR instead of Wilder/RMA (definition sensitivity)')
    ap.add_argument('--coins', default='', help='comma list for cross-coin ATR%% study')
    ap.add_argument('--pct', type=float, default=0.077, help='ATR%% threshold for cross-coin')
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
    if args.coins:
        for c in args.coins.split(','):
            cross_coin(c.strip(), args.pct)
    if args.recent:
        recent_case_study(args.coin, args.threshold)


if __name__ == '__main__':
    main()
