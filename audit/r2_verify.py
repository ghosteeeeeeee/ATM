#!/usr/bin/env python3
"""r2_verify.py — INDEPENDENT audit of claims R2a/R2b (round 2 of
backtest_atr60_momentum.py). Nothing is imported from the audited script.

Indicators via TA-Lib; events, direction rules, outcomes, baselines,
half split, and all statistics re-implemented here from the claim text.
Read-only DB access.

Output: audit/r2_verify_out.txt
"""
import sqlite3
import bisect
import random
from collections import defaultdict
import numpy as np
import talib

DB = 'file:/root/.hermes/data/candles.db?mode=ro'
CDB = 'file:/root/.hermes/data/continuum.db?mode=ro'
COINS = ['BTC', 'SOL', 'SUI', 'TAO', 'PUMP', 'GALA', 'GMX', 'IMX', 'SAND',
         'FOGO', 'COMP', 'DYM']
THR = 0.076
HYST = 0.9
HZ = (60, 240, 1440)
PASSES = {'5m': 300, '15m': 900, '1h': 3600}
OUT = []


def p(*a):
    s = ' '.join(str(x) for x in a)
    OUT.append(s)
    print(s, flush=True)


# ── data ──────────────────────────────────────────────────────────────────────
def load_1m(tok):
    conn = sqlite3.connect(DB, timeout=10)
    rows = conn.execute(
        "SELECT ts, high, low, close FROM candles_1m "
        "WHERE token = ? ORDER BY ts", (tok,)).fetchall()
    conn.close()
    ts = np.array([r[0] for r in rows], dtype=np.int64)
    hi = np.array([r[1] for r in rows], dtype=np.float64)
    lo = np.array([r[2] for r in rows], dtype=np.float64)
    cl = np.array([r[3] for r in rows], dtype=np.float64)
    return ts, hi, lo, cl


def load_htf(tok, table):
    conn = sqlite3.connect(DB, timeout=10)
    rows = conn.execute(
        f"SELECT ts, close FROM {table} WHERE token = ? ORDER BY ts",
        (tok,)).fetchall()
    conn.close()
    return (np.array([r[0] for r in rows], dtype=np.int64),
            np.array([r[1] for r in rows], dtype=np.float64))


# ── events: own implementation of stated definition ──────────────────────────
def find_events(ap, ts, thr=THR, hy=HYST):
    ev = []
    armed = True
    for i in range(1, len(ap)):
        a0, a1 = ap[i - 1], ap[i]
        if np.isnan(a0) or np.isnan(a1):
            continue
        if armed and a0 < thr <= a1:
            ev.append(i)
            armed = False
        if not armed and a1 < thr * hy:
            armed = True
    return ev


# ── forward returns ──────────────────────────────────────────────────────────
def horizon_lookup(ts, h):
    n = len(ts)
    ar = np.arange(n)
    tgt = ts + h * 60
    j = np.minimum(np.searchsorted(ts, tgt), n - 1)
    ok = (ts[j] == tgt)
    exact = ok.copy()
    t2 = tgt + 60
    j2 = np.minimum(np.searchsorted(ts, t2), n - 1)
    m2 = (~ok) & (ts[j2] == t2) & (j2 > ar)
    j = np.where(m2, j2, j)
    ok = ok | m2
    t3 = tgt - 60
    j3 = np.minimum(np.searchsorted(ts, t3), n - 1)
    m3 = (~ok) & (ts[j3] == t3) & (j3 > ar)
    j = np.where(m3, j3, j)
    ok = ok | m3
    return j, ok, exact


def build_returns(ts, cl, hzs=HZ, exact_only=False):
    n = len(ts)
    ar = np.arange(n)
    raw = {}
    fb = 0
    for h in hzs:
        j, ok, exact = horizon_lookup(ts, h)
        use = exact if exact_only else ok
        r = np.full(n, np.nan)
        r[use] = (cl[j[use]] / cl[ar[use]] - 1.0) * 100.0
        raw[h] = r
        if h == 1440:
            fb = int(np.sum(ok & ~exact))
    return raw, fb


# ── direction rules (vectorized; only completed HTF bars) ────────────────────
def sign_arr(x):
    return np.where(x > 0, 1, np.where(x < 0, -1, 0)).astype(np.int8)


def completed_k(hts, ts, iv, lag=0):
    """k = index of last HTF bar with bar_ts + iv <= ts - lag."""
    return np.searchsorted(hts, ts - lag - iv, side='right') - 1


def htf_ema_dir(hts, hcl, ts, iv, lag=0, guard=50):
    e20 = talib.EMA(hcl, 20)
    e50 = talib.EMA(hcl, 50)
    k = completed_k(hts, ts, iv, lag)
    kc = np.clip(k, 0, None)
    v = e20[kc] - e50[kc]
    d = np.zeros(len(ts), dtype=np.int8)
    valid = (k >= guard) & ~np.isnan(v)
    d[valid] = sign_arr(v[valid])
    return d


def htf_macd_dir(hts, hcl, ts, iv, lag=0, guard=30):
    _, _, mh = talib.MACD(hcl, 12, 26, 9)
    k = completed_k(hts, ts, iv, lag)
    kc = np.clip(k, 0, None)
    v = mh[kc]
    d = np.zeros(len(ts), dtype=np.int8)
    valid = (k >= guard) & ~np.isnan(v)
    d[valid] = sign_arr(v[valid])
    return d


def htf_slope_dir(hts, hcl, ts, iv, sn, lag=0):
    k = completed_k(hts, ts, iv, lag)
    kc = np.clip(k, sn, None)
    with np.errstate(invalid='ignore', divide='ignore'):
        r = hcl[kc] / hcl[kc - sn] - 1.0
    d = np.zeros(len(ts), dtype=np.int8)
    valid = (k >= sn) & ~np.isnan(r)
    d[valid] = sign_arr(r[valid])
    return d


def agree(a, b):
    return np.where((a == b) & (a != 0), a, 0).astype(np.int8)


# ── collection ───────────────────────────────────────────────────────────────
def collect(store, coin_store, rname, half, kind, sel, d, raw, days, tok):
    for i in sel:
        dv = int(d[i])
        if dv == 0:
            continue
        for h in HZ:
            v = raw[h][i]
            if np.isnan(v):
                continue
            val = float(v) * dv
            store[(rname, half, kind, h)].append((tok, int(days[i]), val))
            coin_store[(rname, half, kind, h, tok)].append(val)


# ── per-coin pipeline ────────────────────────────────────────────────────────
def process_coin(tok, store, coin_store):
    ts, hi, lo, cl = load_1m(tok)
    n = len(ts)
    atr = talib.ATR(hi, lo, cl, 14)
    ap = atr / cl * 100.0
    days = (ts // 86400).astype(np.int64)

    _, _, m1 = talib.MACD(cl, 12, 26, 9)
    r1 = talib.RSI(cl, 14)
    m1s = np.zeros(n, dtype=np.int8)
    ok1 = ~np.isnan(m1)
    m1s[ok1] = sign_arr(m1[ok1])
    r1s = np.zeros(n, dtype=np.int8)
    okr = ~np.isnan(r1)
    r1s[okr] = np.where(r1[okr] > 50, 1, np.where(r1[okr] < 50, -1, 0))

    raw, fb = build_returns(ts, cl)

    ev_all = [i for i in find_events(ap, ts) if i < n - 15]
    ev_set = set(ev_all)
    base_all = [i for i in range(0, n, 60) if i < n - 15]

    mid = (ts[0] + ts[-1]) / 2.0
    halves = {'full': np.ones(n, bool), 'first': ts < mid, 'second': ts >= mid}

    def state_for(mask):
        out, last_s = [], -10**18
        for i in range(n - 15):
            if not mask[i]:
                continue
            if (not np.isnan(ap[i]) and ap[i] >= THR and i not in ev_set
                    and ts[i] - last_s >= 3600):
                out.append(i)
                last_s = ts[i]
        return out

    states = {h: state_for(m) for h, m in halves.items()}

    ha = np.array([i for i in range(n - 15)
                   if not np.isnan(ap[i]) and ap[i] >= THR], dtype=np.int64)

    htf = {tf: load_htf(tok, f'candles_{tf}') for tf in PASSES}
    h4ts, h4cl = load_htf(tok, 'candles_4h')

    rules = {}
    strict_pass = {}
    for tf, iv in PASSES.items():
        hts, hcl = htf[tf]
        sn = max(6, int(3600 / iv))
        d_ema = htf_ema_dir(hts, hcl, ts, iv)
        d_macd = htf_macd_dir(hts, hcl, ts, iv)
        d_slope = htf_slope_dir(hts, hcl, ts, iv, sn)
        d4 = htf_ema_dir(h4ts, h4cl, ts, 14400)
        rules[f'ema_{tf}'] = d_ema
        rules[f'macd_{tf}'] = d_macd
        rules[f'slope{sn}_{tf}'] = d_slope
        rules[f'ema_4h'] = d4
        rules[f'{tf}+4h agree'] = agree(d_ema, d4)
        st = np.where((d_ema != 0) & (m1s == d_ema) & (r1s == d_ema),
                      d_ema, 0).astype(np.int8)
        rules[f'STRICT@{tf}'] = st
        strict_pass[tf] = st

    meta = dict(ts=ts, cl=cl, days=days, ap=ap, atr=atr, mid=mid,
                ev_all=ev_all, base_all=base_all, states=states, ha=ha,
                raw=raw, fb=fb, n=n, start=int(ts[0]), end=int(ts[-1]))

    for half, mask in halves.items():
        for kind, idxs in (('ev', ev_all), ('base', base_all),
                           ('state', states[half])):
            sel = [i for i in idxs if mask[i]]
            for rname, d in rules.items():
                collect(store, coin_store, rname, half, kind, sel, d,
                        raw, days, tok)
            # script-style 'STRICT' key: concatenation of the 3 passes
            for tf in PASSES:
                collect(store, coin_store, 'STRICT', half, kind, sel,
                        strict_pass[tf], raw, days, tok)
    return meta, rules


# ── statistics (numpy-accelerated) ───────────────────────────────────────────
def iid_boot_diff(a, b, rounds=2000, seed=777):
    rng = np.random.default_rng(seed)
    a = np.asarray(a, dtype=np.float64)
    b = np.asarray(b, dtype=np.float64)
    na, nb = len(a), len(b)
    ds = np.empty(rounds)
    for lo in range(0, rounds, 250):
        r = min(250, rounds - lo)
        sa = a[rng.integers(0, na, size=(r, na))].mean(axis=1)
        sb = b[rng.integers(0, nb, size=(r, nb))].mean(axis=1)
        ds[lo:lo + r] = sa - sb
    ds.sort()
    return float(ds[int(rounds * 0.025)]), float(ds[int(rounds * 0.975)])


def _day_arrays(recs):
    by = defaultdict(lambda: [0.0, 0])
    for (_, day, v) in recs:
        e = by[day]
        e[0] += v
        e[1] += 1
    return by


def day_cluster_diff(a, b, rounds=4000, seed=999):
    """Cluster bootstrap over UTC days (preserves within-day clustering and
    cross-coin correlation): resample days with replacement, pool all obs."""
    rng = random.Random(seed)
    ba, bb = _day_arrays(a), _day_arrays(b)
    days = sorted(set(ba) | set(bb))
    nd = len(days)
    sa = np.array([ba.get(d, (0.0, 0))[0] for d in days])
    ca = np.array([ba.get(d, (0.0, 0))[1] for d in days], dtype=np.float64)
    sb = np.array([bb.get(d, (0.0, 0))[0] for d in days])
    cb = np.array([bb.get(d, (0.0, 0))[1] for d in days], dtype=np.float64)
    ds = []
    for _ in range(rounds):
        idx = [rng.randrange(nd) for _ in range(nd)]
        xa, xb = ca[idx].sum(), cb[idx].sum()
        if xa == 0 or xb == 0:
            continue
        ds.append(sa[idx].sum() / xa - sb[idx].sum() / xb)
    ds.sort()
    m = len(ds)
    return float(ds[int(m * 0.025)]), float(ds[int(m * 0.975)])


def day_signflip(a, b, iters=20000, seed=1234):
    """Day-paired statistic D_d = mean(ev|day d) - mean(state|day d) over days
    with both; null = random sign flips of D_d."""
    rng = random.Random(seed)
    ba, bb = _day_arrays(a), _day_arrays(b)
    days = sorted(set(ba) & set(bb))
    if not days:
        return float('nan'), 0, 1.0, 1.0
    D = np.array([ba[d][0] / ba[d][1] - bb[d][0] / bb[d][1] for d in days])
    obs = float(D.mean())
    ge = ge2 = 0
    for _ in range(iters):
        sgn = np.array([1.0 if rng.random() < 0.5 else -1.0 for _ in D])
        s = float((D * sgn).mean())
        if s >= obs:
            ge += 1
        if abs(s) >= abs(obs):
            ge2 += 1
    return obs, len(days), (ge + 1) / (iters + 1), (ge2 + 1) / (iters + 1)


def circ_shift_time(ev_recs, st_recs, metas, d_arrays, iters=4000, seed=4242):
    """Common-delta circular TIME shift of event times across all coins
    (preserves cross-coin alignment and event clustering). Null statistic =
    shifted pooled ev mean - fixed pooled state mean."""
    rng = random.Random(seed)
    smean = np.mean([v for (_, _, v) in st_recs])
    obs = np.mean([v for (_, _, v) in ev_recs]) - smean
    ev_ts = {}
    for ck in COINS:
        meta = metas[ck]
        ev_ts[ck] = meta['ts'][np.array(meta['ev_all'], dtype=np.int64)]
    Ws = {ck: metas[ck]['end'] - metas[ck]['start'] for ck in COINS}
    minW = min(Ws.values())
    ge = 0
    for _ in range(iters):
        delta = rng.randrange(86400, minW - 86400, 60)
        chunks = []
        for ck in COINS:
            meta = metas[ck]
            ts = meta['ts']
            n = meta['n']
            start, W = meta['start'], Ws[ck]
            t = ev_ts[ck]
            tp = start + ((t - start + delta) % W)
            j = np.minimum(np.searchsorted(ts, tp), n - 1)
            valid = (ts[j] == tp) & (j < n - 15)
            d = d_arrays[ck][j]
            valid &= (d != 0)
            v = meta['raw'][1440][j]
            valid &= ~np.isnan(v)
            if valid.any():
                chunks.append(v[valid] * d[valid])
        if not chunks:
            continue
        vals = np.concatenate(chunks)
        if vals.mean() - smean >= obs:
            ge += 1
    return float(obs), (ge + 1) / (iters + 1)


def circ_shift_ha(ev_recs, st_recs, metas, rules_by_coin, rname,
                  iters=4000, seed=555):
    """Circular shift of the event pattern WITHIN each coin's high-ATR bar
    sequence: preserves conditioning on ATR>=thr and event clustering.
    Per-coin offsets. Null = shifted pooled ev mean - fixed state mean."""
    rng = random.Random(seed)
    smean = np.mean([v for (_, _, v) in st_recs])
    obs = np.mean([v for (_, _, v) in ev_recs]) - smean
    ev_pos, ha_arr = {}, {}
    for ck in COINS:
        meta = metas[ck]
        ha = meta['ha']
        pos_of = {int(b): i for i, b in enumerate(ha)}
        ev_pos[ck] = np.array([pos_of[i] for i in meta['ev_all']],
                              dtype=np.int64)
        ha_arr[ck] = ha
    ge = 0
    for _ in range(iters):
        chunks = []
        for ck in COINS:
            meta = metas[ck]
            m = len(ha_arr[ck])
            if m == 0:
                continue
            k = rng.randrange(1, m)
            j = ha_arr[ck][(ev_pos[ck] + k) % m]
            j = j[j < meta['n'] - 15]
            d = rules_by_coin[ck][rname][j]
            valid = d != 0
            v = meta['raw'][1440][j]
            valid &= ~np.isnan(v)
            if valid.any():
                chunks.append(v[valid] * d[valid])
        if not chunks:
            continue
        vals = np.concatenate(chunks)
        if vals.mean() - smean >= obs:
            ge += 1
    return float(obs), (ge + 1) / (iters + 1)


# ── reporting ────────────────────────────────────────────────────────────────
def mean(x):
    return sum(x) / len(x) if x else float('nan')


def wr(x):
    return 100.0 * sum(1 for v in x if v > 0) / len(x) if x else float('nan')


def rule_row(name, half, store, coin_store, coins, day_ci=True):
    ev = store.get((name, half, 'ev', 1440), [])
    st = store.get((name, half, 'state', 1440), [])
    bs = store.get((name, half, 'base', 1440), [])
    if len(ev) < 50 or len(st) < 30:
        return None
    evv = [v for (_, _, v) in ev]
    stv = [v for (_, _, v) in st]
    d = mean(evv) - mean(stv)
    ci = iid_boot_diff(evv, stv, 2000, 31)
    dci = day_cluster_diff(ev, st, 3000, 999) if day_ci else (float('nan'),) * 2
    from math import comb
    pos = neg = 0
    for ck in coins:
        cm = coin_store.get((name, half, 'ev', 1440, ck))
        cs = coin_store.get((name, half, 'state', 1440, ck))
        if not cm or not cs:
            continue
        if mean(cm) > mean(cs):
            pos += 1
        elif mean(cm) < mean(cs):
            neg += 1
    nc = pos + neg
    sp = (sum(comb(nc, i) for i in range(pos, nc + 1)) / 2**nc) if nc else 1.0
    p(f'{name:>16} {str(half):>6} n={len(evv):>5} ev={mean(evv):+7.3f} '
      f'WR={wr(evv):5.1f}% | st n={len(stv):>5} {mean(stv):+7.3f} '
      f'WR={wr(stv):5.1f}% | base n={len(bs):>4} '
      f'{mean([v for _, _, v in bs]):+7.3f} | diff={d:+7.3f} '
      f'iid[{ci[0]:+6.3f},{ci[1]:+6.3f}] day[{dci[0]:+6.3f},'
      f'{dci[1]:+6.3f}] | {pos}/{neg} p={sp:.3f}')
    return dict(name=name, half=half, n=len(evv), ev=mean(evv),
                st=mean(stv), diff=d, iid=ci, day=dci, pos=pos, neg=neg, sp=sp)


# ═════════════════════════════════════════════════════════════════════════════
def main():
    store = defaultdict(list)
    coin_store = defaultdict(list)
    metas, rules_by_coin = {}, {}

    p('=' * 100)
    p('INDEPENDENT R2 VERIFICATION — talib indicators, own events/rules/stats')
    p('=' * 100)
    for ck in COINS:
        meta, rules = process_coin(ck, store, coin_store)
        metas[ck] = meta
        rules_by_coin[ck] = rules
        ts = meta['ts']
        ngap = int(np.sum(np.diff(ts) != 60))
        p(f'{ck:5s} n={meta["n"]:6d} ev={len(meta["ev_all"]):4d} '
          f'base={len(meta["base_all"]):4d} '
          f'state={len(meta["states"]["full"]):4d} ha={len(meta["ha"]):6d} '
          f'gaps!={ngap} fb1440={meta["fb"]}')

    p('\n--- events per half (own-midpoint split) ---')
    for ck in COINS:
        m = metas[ck]
        nf = sum(1 for i in m['ev_all'] if m['ts'][i] < m['mid'])
        p(f'  {ck:5s} first={nf:4d} second={len(m["ev_all"]) - nf:4d}')

    # ── (a) full window ──────────────────────────────────────────────────────
    p('\n' + '=' * 100)
    p('(a) FULL-WINDOW pooled ev-state @1440m — claim vs my recompute')
    p('=' * 100)
    claim_full = {
        '15m+4h agree': (0.773, 0.548, 1.009, '10/2', 2198),
        'ema_15m': (0.462, 0.283, 0.637, '10/2', None),
        'ema_1h': (0.548, 0.372, 0.722, '10/2', None),
        'macd_1h': (0.574, 0.393, 0.747, '10/2', None),
        'slope6_1h': (0.381, 0.203, 0.557, '10/2', None),
        'STRICT@15m': (0.413, 0.134, 0.684, '9/3', None),
        'macd_5m': (-0.177, -0.352, 0.005, '3/9', None),
    }
    order = ['15m+4h agree', 'ema_15m', 'ema_1h', 'macd_1h', 'slope6_1h',
             'STRICT@15m', 'STRICT', 'macd_5m', 'ema_5m', 'macd_15m',
             'slope6_15m', 'slope12_5m', 'ema_4h', '1h+4h agree',
             '5m+4h agree']
    for rname in order:
        r = rule_row(rname, 'full', store, coin_store, COINS)
        if r:
            c = claim_full.get(rname)
            if c:
                extra = f', claim n={c[4]}' if c[4] else ''
                p(f'    ^ CLAIM diff={c[0]:+.3f} CI[{c[1]:+.3f},'
                  f'{c[2]:+.3f}] signs {c[3]}{extra} | mine diff='
                  f'{r["diff"]:+.3f} signs {r["pos"]}/{r["neg"]} n={r["n"]}')

    p('\n--- per-coin ev vs state @1440m (full) ---')
    for rname in ('15m+4h agree', 'ema_15m', 'macd_1h'):
        p(f'  rule {rname}:')
        for ck in COINS:
            ev = coin_store.get((rname, 'full', 'ev', 1440, ck), [])
            st = coin_store.get((rname, 'full', 'state', 1440, ck), [])
            if not ev or not st:
                p(f'    {ck:5s} ev n={len(ev)} st n={len(st)} missing')
                continue
            d = mean(ev) - mean(st)
            p(f'    {ck:5s} ev n={len(ev):4d} {mean(ev):+7.3f} '
              f'WR={wr(ev):5.1f} | st n={len(st):4d} {mean(st):+7.3f} '
              f'WR={wr(st):5.1f} | diff {d:+7.3f} {"+" if d > 0 else "-"}')

    # ── (b) halves ───────────────────────────────────────────────────────────
    p('\n' + '=' * 100)
    p('(b) OOS SPLIT @1440m — claim vs my recompute')
    p('=' * 100)
    claim_half = {
        ('15m+4h agree', 'first'): (0.493, 0.133, 0.855),
        ('macd_1h', 'first'): (0.632, 0.371, 0.893),
        ('slope6_1h', 'first'): (0.335, 0.091, 0.599),
        ('ema_15m', 'first'): (0.302, 0.037, 0.562),
        ('15m+4h agree', 'second'): (0.961, 0.648, 1.272),
        ('macd_1h', 'second'): (0.528, 0.290, 0.783),
        ('slope6_1h', 'second'): (0.446, 0.210, 0.691),
        ('ema_15m', 'second'): (0.648, 0.415, 0.888),
        ('macd_5m', 'second'): (-0.253, -0.499, -0.014),
    }
    for half in ('first', 'second'):
        p(f'  --- {half} half ---')
        for rname in ('15m+4h agree', 'ema_15m', 'ema_1h', 'macd_1h',
                      'slope6_1h', 'STRICT@15m', 'macd_5m', 'ema_4h'):
            r = rule_row(rname, half, store, coin_store, COINS)
            if r:
                c = claim_half.get((rname, half))
                if c:
                    p(f'    ^ CLAIM diff={c[0]:+.3f} CI[{c[1]:+.3f},'
                      f'{c[2]:+.3f}] | mine {r["diff"]:+.3f} iid'
                      f'[{r["iid"][0]:+.3f},{r["iid"][1]:+.3f}]')

    # ── horizons ─────────────────────────────────────────────────────────────
    p('\n' + '=' * 100)
    p('pooled ev-state diff @60m / @240m (full window)')
    p('=' * 100)
    for hz in (60, 240):
        p(f'  --- hz={hz}m ---')
        for rname in order:
            ev = store.get((rname, 'full', 'ev', hz), [])
            st = store.get((rname, 'full', 'state', hz), [])
            if len(ev) < 50 or len(st) < 30:
                continue
            evv = [v for (_, _, v) in ev]
            stv = [v for (_, _, v) in st]
            d = mean(evv) - mean(stv)
            ci = iid_boot_diff(evv, stv, 2000, 31)
            p(f'  {rname:>16} n={len(evv):>5} ev={mean(evv):+7.3f} '
              f'st={mean(stv):+7.3f} diff={d:+7.3f} iid[{ci[0]:+6.3f},'
              f'{ci[1]:+6.3f}]')

    # ── (G) nulls ────────────────────────────────────────────────────────────
    p('\n' + '=' * 100)
    p('(G) NULL TESTS — 15m+4h agree, full window, 1440m, ev vs state')
    p('=' * 100)
    rname = '15m+4h agree'
    ev = store[(rname, 'full', 'ev', 1440)]
    st = store[(rname, 'full', 'state', 1440)]
    evv = [v for (_, _, v) in ev]
    stv = [v for (_, _, v) in st]
    obs = mean(evv) - mean(stv)
    p(f'  observed pooled diff = {obs:+.4f} | ev n={len(evv)} mean '
      f'{mean(evv):+.4f} WR {wr(evv):.1f}% | state n={len(stv)} mean '
      f'{mean(stv):+.4f} WR {wr(stv):.1f}%')
    ci = iid_boot_diff(evv, stv, 4000, 777)
    p(f'  iid event bootstrap 95% CI (claim method)      [{ci[0]:+.4f},'
      f'{ci[1]:+.4f}]')
    dci = day_cluster_diff(ev, st, 5000, 999)
    p(f'  DAY-CLUSTER bootstrap 95% CI (30 UTC-day clusters, cross-coin '
      f'kept)  [{dci[0]:+.4f},{dci[1]:+.4f}]')
    obs_d, nd, p1, p2 = day_signflip(ev, st, 20000, 1234)
    p(f'  day-paired sign-flip: mean day diff={obs_d:+.4f} days={nd} '
      f'p(one-sided)={p1:.4f} p(two-sided)={p2:.4f}')
    d_arrays = {ck: rules_by_coin[ck]['15m+4h agree'] for ck in COINS}
    o2, pcs = circ_shift_time(ev, st, metas, d_arrays, iters=4000, seed=4242)
    p(f'  circular TIME-shift null (common delta, 4000 iters): '
      f'p(one-sided)={pcs:.4f} [obs={o2:+.4f}]')
    o3, pcs2 = circ_shift_ha(ev, st, metas, rules_by_coin, rname,
                             iters=4000, seed=555)
    p(f'  circular shift WITHIN high-ATR sequence (per-coin, 4000 iters): '
      f'p(one-sided)={pcs2:.4f} [obs={o3:+.4f}]')
    for half in ('first', 'second'):
        e2 = store.get((rname, half, 'ev', 1440), [])
        s2 = store.get((rname, half, 'state', 1440), [])
        if not e2 or not s2:
            continue
        dci2 = day_cluster_diff(e2, s2, 5000, 1099)
        o4, n4, q1, q2 = day_signflip(e2, s2, 20000, 4321)
        p(f'  [{half}] day-cluster CI [{dci2[0]:+.4f},{dci2[1]:+.4f}] '
          f'sign-flip p(one)={q1:.4f} p(two)={q2:.4f} days={n4} '
          f'mean-day-diff={o4:+.4f}')

    # ── sensitivities ────────────────────────────────────────────────────────
    p('\n' + '=' * 100)
    p('SENSITIVITY (1) exact-ts outcomes only (no +/-60s gap fallback)')
    p('=' * 100)
    store2, coin2 = defaultdict(list), defaultdict(list)
    for ck in COINS:
        meta = metas[ck]
        rawe, _ = build_returns(meta['ts'], meta['cl'], exact_only=True)
        ts, days, n = meta['ts'], meta['days'], meta['n']
        halves = {'full': np.ones(n, bool), 'first': ts < meta['mid'],
                  'second': ts >= meta['mid']}
        for half, mask in halves.items():
            for kind, idxs in (('ev', meta['ev_all']),
                               ('base', meta['base_all']),
                               ('state', meta['states'][half])):
                sel = [i for i in idxs if mask[i]]
                for rname_, d in rules_by_coin[ck].items():
                    collect(store2, coin2, rname_, half, kind, sel, d,
                            rawe, days, ck)
        # pooled STRICT (script-style)
        st_pass = {tf: rules_by_coin[ck][f'STRICT@{tf}'] for tf in PASSES}
        for half, mask in halves.items():
            for kind, idxs in (('ev', meta['ev_all']),
                               ('base', meta['base_all']),
                               ('state', meta['states'][half])):
                sel = [i for i in idxs if mask[i]]
                for tf in PASSES:
                    collect(store2, coin2, 'STRICT', half, kind, sel,
                            st_pass[tf], rawe, days, ck)
    for rname_ in ('15m+4h agree', 'ema_15m', 'macd_1h'):
        evx = store2.get((rname_, 'full', 'ev', 1440), [])
        stx = store2.get((rname_, 'full', 'state', 1440), [])
        if not evx or not stx:
            continue
        evv2 = [v for (_, _, v) in evx]
        stv2 = [v for (_, _, v) in stx]
        p(f'  {rname_:>16} n={len(evv2)} ev={mean(evv2):+.3f} '
          f'st={mean(stv2):+.3f} diff={mean(evv2) - mean(stv2):+.3f}')

    p('\n' + '=' * 100)
    p('SENSITIVITY (2) HTF bar completed by ENTRY time (ts+60) vs claim '
      'convention (bar end <= ts)')
    p('=' * 100)
    alt = alt_convention(metas)
    for rname_, v in alt.items():
        p(f'  {rname_:>16} diff={v:+.3f}')

    # ── (c) R2b ──────────────────────────────────────────────────────────────
    continuum_study()

    with open('/root/.hermes/audit/r2_verify_out.txt', 'w') as f:
        f.write('\n'.join(OUT) + '\n')
    print('\n[written] /root/.hermes/audit/r2_verify_out.txt')


def alt_convention(metas):
    store, coin_store = defaultdict(list), defaultdict(list)
    for ck in COINS:
        meta = metas[ck]
        ts, days, n = meta['ts'], meta['days'], meta['n']
        halves = {'full': np.ones(n, bool), 'first': ts < meta['mid'],
                  'second': ts >= meta['mid']}
        htf = {tf: load_htf(ck, f'candles_{tf}') for tf in PASSES}
        h4ts, h4cl = load_htf(ck, 'candles_4h')
        rules = {}
        for tf, iv in PASSES.items():
            hts, hcl = htf[tf]
            sn = max(6, int(3600 / iv))
            d_ema = htf_ema_dir(hts, hcl, ts, iv, lag=-60)
            d4 = htf_ema_dir(h4ts, h4cl, ts, 14400, lag=-60)
            rules[f'ema_{tf}'] = d_ema
            rules[f'{tf}+4h agree'] = agree(d_ema, d4)
            rules[f'macd_{tf}'] = htf_macd_dir(hts, hcl, ts, iv, lag=-60)
            rules[f'slope{sn}_{tf}'] = htf_slope_dir(hts, hcl, ts, iv, sn,
                                                      lag=-60)
        for half, mask in halves.items():
            for kind, idxs in (('ev', meta['ev_all']),
                               ('base', meta['base_all']),
                               ('state', meta['states'][half])):
                sel = [i for i in idxs if mask[i]]
                for rname_, d in rules.items():
                    collect(store, coin_store, rname_, half, kind, sel, d,
                            meta['raw'], days, ck)
    out = {}
    for rname_ in ('15m+4h agree', 'ema_15m', 'macd_1h', 'slope6_1h',
                   'macd_5m'):
        ev = store.get((rname_, 'full', 'ev', 1440), [])
        st = store.get((rname_, 'full', 'state', 1440), [])
        if not ev or not st:
            continue
        out[rname_] = (mean([v for (_, _, v) in ev])
                       - mean([v for (_, _, v) in st]))
    return out


# ── R2b continuum ────────────────────────────────────────────────────────────
def continuum_study():
    p('\n' + '=' * 100)
    p('(c) R2b CONTINUUM (BTC, ATR USD $60 declustered events, 24h)')
    p('=' * 100)
    ts, hi, lo, cl = load_1m('BTC')
    n = len(ts)
    atr = talib.ATR(hi, lo, cl, 14)
    ev_all = [i for i in find_events(atr, ts, thr=60.0) if i < n - 15]
    p(f'  BTC declustered ATR>$60 events: {len(ev_all)} | window '
      f'{int(ts[0])} -> {int(ts[-1])}')

    conn = sqlite3.connect(CDB, timeout=10)
    rows = conn.execute(
        "SELECT ts, state_score FROM continuum_states WHERE token='BTC' "
        "AND state_score IS NOT NULL ORDER BY ts").fetchall()
    conn.close()
    cts = np.array([r[0] for r in rows], dtype=np.int64)
    csc = np.array([r[1] for r in rows], dtype=np.float64)
    p(f'  continuum rows={len(cts)} span {int(cts[0])} -> {int(cts[-1])}')

    def score_at(t):
        k = bisect.bisect_right(cts, t) - 1
        return (float(csc[k]), int(cts[k])) if k >= 0 else (None, None)

    raw, fb = build_returns(ts, cl)

    stales = []
    for i in ev_all:
        s, sts = score_at(int(ts[i]))
        if s is not None:
            stales.append(int(ts[i]) - sts)
    stales.sort()
    p(f'  score staleness at events: median={stales[len(stales)//2]}s '
      f'p90={stales[int(len(stales)*0.9)]}s max={stales[-1]}s n={len(stales)}')

    hts, hcl = load_htf('BTC', 'candles_1h')
    e20_1h = talib.EMA(hcl, 20)
    e50_1h = talib.EMA(hcl, 50)

    def ema1h(t):
        k = int(np.searchsorted(hts, t - 3600, side='right')) - 1
        if k < 50:
            return 0
        return 1 if e20_1h[k] > e50_1h[k] else -1

    def cont50(t):
        s, _ = score_at(t)
        return 0 if s is None else (1 if s >= 50 else -1)

    def cont50_entry(t):
        s, _ = score_at(t + 60)
        return 0 if s is None else (1 if s >= 50 else -1)

    def cont55(t):
        s, _ = score_at(t)
        if s is None:
            return 0
        if s >= 55:
            return 1
        if s <= 45:
            return -1
        return 0

    def cont55_1h(t):
        a = cont55(t)
        b = ema1h(t)
        return a if (a != 0 and a == b) else 0

    variants = [('cont_50', cont50), ('cont_50@entry', cont50_entry),
                ('cont_55', cont55), ('cont55+1h-agree', cont55_1h)]

    base_all = [i for i in range(0, n, 60) if i < n - 15]
    ev_set = set(ev_all)
    # script's state baseline (BUG: last_s never updated -> ALL high-ATR bars)
    state_buggy = [i for i in range(n - 15)
                   if not np.isnan(atr[i]) and atr[i] >= 60.0
                   and i not in ev_set]
    state_hourly = []
    last_s = -10**18
    for i in range(n - 15):
        if (not np.isnan(atr[i]) and atr[i] >= 60.0 and i not in ev_set
                and ts[i] - last_s >= 3600):
            state_hourly.append(i)
            last_s = ts[i]
    p(f'  baselines: hourly-grid={len(base_all)} state_buggy(all high-ATR '
      f'bars)={len(state_buggy)} state_hourly={len(state_hourly)}')

    for vname, fn in variants:
        evv, evx = [], []
        dirs = [fn(int(ts[i])) for i in range(n - 15)]
        for i in ev_all:
            d = dirs[i]
            if d == 0 or np.isnan(raw[1440][i]):
                continue
            evv.append(float(raw[1440][i]) * d)
        if len(evv) < 10:
            p(f'  {vname:>18}: n={len(evv)} too few')
            continue
        # exact-ts-only events
        rawx, _ = build_returns(ts, cl, exact_only=True)
        for i in ev_all:
            d = dirs[i]
            if d == 0 or np.isnan(rawx[1440][i]):
                continue
            evx.append(float(rawx[1440][i]) * d)

        def vals(idxs):
            return [float(raw[1440][i]) * dirs[i] for i in idxs
                    if dirs[i] != 0 and not np.isnan(raw[1440][i])]

        sb, sh, bb = vals(state_buggy), vals(state_hourly), vals(base_all)
        ci_b = iid_boot_diff(evv, sb, 2000, 77) if sb else (float('nan'),) * 2
        ci_h = iid_boot_diff(evv, sh, 2000, 78) if sh else (float('nan'),) * 2
        p(f'  {vname:>18}: ev n={len(evv):4d} WR={wr(evv):5.1f}% '
          f'mean={mean(evv):+7.3f} | base n={len(bb):4d} WR={wr(bb):5.1f}% '
          f'mean={mean(bb):+7.3f} | state_buggy n={len(sb):5d} WR='
          f'{wr(sb):5.1f}% mean={mean(sb):+7.3f} diff={mean(evv)-mean(sb):+7.3f}'
          f' CI[{ci_b[0]:+.3f},{ci_b[1]:+.3f}]')
        p(f'  {"":>18}   state_hourly n={len(sh):4d} WR={wr(sh):5.1f}% '
          f'mean={mean(sh):+7.3f} diff={mean(evv)-mean(sh):+7.3f} '
          f'CI[{ci_h[0]:+.3f},{ci_h[1]:+.3f}] | exact-ts ev: n={len(evx)} '
          f'WR={wr(evx):.1f}% mean={mean(evx):+.3f}')

    p(f'  BTC window return {(cl[-1]/cl[0]-1)*100:+.2f}% '
      f'(first={cl[0]:.0f} last={cl[-1]:.0f})')
    sc = [s for s, _ in (score_at(int(ts[i])) for i in ev_all) if s is not None]
    p(f'  score at events: mean={mean(sc):.1f} frac>=50='
      f'{100.0*sum(1 for s in sc if s >= 50)/len(sc):.1f}% | all-bars '
      f'frac>=50={100.0*np.mean(csc >= 50):.1f}%')
    hourly = list(range(0, n, 60))
    hv = [float(raw[1440][i]) * cont50(int(ts[i])) for i in hourly
          if cont50(int(ts[i])) != 0 and not np.isnan(raw[1440][i])]
    p(f'  cont_50 on hourly grid (all times): n={len(hv)} WR={wr(hv):.1f}% '
      f'mean={mean(hv):+.3f}')
    d55 = [cont55(int(ts[i])) for i in hourly]
    p(f'  cont55 hourly grid: long={sum(1 for x in d55 if x == 1)} '
      f'short={sum(1 for x in d55 if x == -1)} '
      f'flat={sum(1 for x in d55 if x == 0)}')


if __name__ == '__main__':
    main()
