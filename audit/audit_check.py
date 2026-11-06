#!/usr/bin/env python3
"""
audit_check.py — INDEPENDENT verification of backtest_atr60_momentum.py claims.

Written from scratch by the auditor. Does NOT import or re-run the original
script. All indicators, event detection, outcomes, and statistics are
re-implemented here; bootstrap uses a different seed; extra robustness
(alternative declustering, block bootstrap, circular-shift null, ATR-matched
baseline, next-bar entry) is added to hunt for artifacts.

Data source: pinned npz snapshots in /root/.hermes/audit/snap_*.npz
(the live candles.db is a rolling 30d window and drifts every minute).
"""
import json
import math
import numpy as np
from scipy import stats
import talib

AUD = '/root/.hermes/audit'
HORIZONS = [15, 30, 60, 120, 240, 480, 720, 1440]
SEED = 20261106  # different from the original's seed=7 / seed=11

L = []  # report lines


def P(*a):
    s = ' '.join(str(x) for x in a)
    L.append(s)
    print(s)


# ── data ─────────────────────────────────────────────────────────────────────
def load(tok):
    d = np.load(f'{AUD}/snap_{tok}.npz')['data']
    ts = d[:, 0].astype(np.int64)
    o, h, l, c, v = d[:, 1], d[:, 2], d[:, 3], d[:, 4], d[:, 5]
    return ts, o, h, l, c, v


# ── indicators (my own implementation) ───────────────────────────────────────
def atr_wilder(h, l, c, period=14):
    """Wilder/RMA ATR seeded with SMA of first `period` True Ranges.
    TR[0] undefined (no prev close); TR[i] for i>=1."""
    n = len(c)
    atr = np.full(n, np.nan)
    if n < period + 1:
        return atr
    pc = np.empty(n)
    pc[0] = np.nan
    pc[1:] = c[:-1]
    tr = np.fmax(h - l, np.fmax(np.abs(h - pc), np.abs(l - pc)))
    atr[period] = np.nanmean(tr[1:period + 1])
    for i in range(period + 1, n):
        atr[i] = (atr[i - 1] * (period - 1) + tr[i]) / period
    return atr, tr


def atr_sma(h, l, c, period=14):
    """SMA-of-TR ATR (the alternative definition under test in claim 8)."""
    n = len(c)
    atr = np.full(n, np.nan)
    pc = np.empty(n)
    pc[0] = np.nan
    pc[1:] = c[:-1]
    tr = np.fmax(h - l, np.fmax(np.abs(h - pc), np.abs(l - pc)))
    for i in range(period, n):
        atr[i] = np.nanmean(tr[i - period + 1:i + 1])
    return atr


def rsi_wilder(c, period=14):
    n = len(c)
    out = np.full(n, np.nan)
    if n < period + 1:
        return out
    d = np.diff(c)
    g = np.maximum(d, 0.0)
    ls = np.maximum(-d, 0.0)
    ag = g[:period].mean()
    al = ls[:period].mean()
    out[period] = 100.0 if al == 0 else 100.0 - 100.0 / (1.0 + ag / al)
    for i in range(period, len(g)):
        ag = (ag * (period - 1) + g[i]) / period
        al = (al * (period - 1) + ls[i]) / period
        out[i + 1] = 100.0 if al == 0 else 100.0 - 100.0 / (1.0 + ag / al)
    return out


def ema_sma_seed(x, period):
    """EMA seeded with SMA of first `period` values (TA-Lib convention)."""
    n = len(x)
    out = np.full(n, np.nan)
    if n < period:
        return out
    k = 2.0 / (period + 1)
    out[period - 1] = x[:period].mean()
    prev = out[period - 1]
    for i in range(period, n):
        prev = x[i] * k + prev * (1 - k)
        out[i] = prev
    return out


def macd_hist(c, fast=12, slow=26, sig=9):
    ef = ema_sma_seed(c, fast)
    es = ema_sma_seed(c, slow)
    line = ef - es
    out = np.full(len(c), np.nan)
    first = slow - 1  # first index where both EMAs exist
    tail = line[first:]
    esig = ema_sma_seed(tail, sig)
    out[first:] = line[first:] - esig
    out[:first] = np.nan
    # signal only valid where esig valid
    out[first:first + sig - 1] = np.nan
    return out


# ── event detection ──────────────────────────────────────────────────────────
def raw_crossings(atr, T):
    """Pure definition: prev < T <= current (nan-safe)."""
    a0 = atr[:-1]
    a1 = atr[1:]
    idx = np.where((a0 < T) & (a1 >= T))[0] + 1
    return idx.astype(int)


def decluster(atr, T, hyst):
    """Re-arm only after ATR falls below T*hyst (their rule when hyst=0.9)."""
    ev = []
    armed = True
    for i in range(1, len(atr)):
        a0, a1 = atr[i - 1], atr[i]
        if np.isnan(a0) or np.isnan(a1):
            continue
        if armed and a0 < T <= a1:
            ev.append(i)
            armed = False
        if (not armed) and a1 < T * hyst:
            armed = True
    return np.array(ev, dtype=int)


def cooldown_events(atr, T, min_bars):
    """Alternative declustering: every raw cross, but at most one per min_bars."""
    raw = raw_crossings(atr, T)
    ev = []
    last = -10 ** 9
    for i in raw:
        if i - last >= min_bars:
            ev.append(i)
            last = i
    return np.array(ev, dtype=int)


# ── direction ────────────────────────────────────────────────────────────────
def directions(mh, rsi, idx):
    m = np.where(mh[idx] > 0, 1, np.where(mh[idx] < 0, -1, 0))
    r = np.where(rsi[idx] > 50, 1, np.where(rsi[idx] < 50, -1, 0))
    return m, r


# ── outcomes ─────────────────────────────────────────────────────────────────
def build_index(ts):
    return {int(t): i for i, t in enumerate(ts)}


def fwd_returns(ts, c, idx_map, i, h_list=HORIZONS, exact_only=False):
    """Forward return % from bar i close to the bar whose ts == ts[i]+h*60.
    exact_only=True -> drop when the exact ts is missing (gap handling)."""
    t0 = int(ts[i])
    p0 = c[i]
    out = {}
    for h in h_list:
        tgt = t0 + h * 60
        j = idx_map.get(tgt)
        if j is None:
            if exact_only:
                continue
            # replicate the original's fallback for comparison
            j = idx_map.get(tgt + 60)
            if j is None:
                j = idx_map.get(tgt - 60)
            if j is None:
                continue
        out[h] = (c[j] / p0 - 1.0) * 100.0
    return out


def first_touch3(ts, c, i, direction, window_s=1440 * 60):
    """First touch of +/-3% (direction-aligned) within window, close-based.
    Returns +1 (hit in direction), -1 (wrong way), None."""
    t0 = int(ts[i])
    p0 = c[i]
    end = t0 + window_s
    j = i + 1
    while j < len(ts) and ts[j] <= end:
        pct = (c[j] / p0 - 1.0) * 100.0 * direction
        if pct >= 3.0:
            return 1
        if pct <= -3.0:
            return -1
        j += 1
    return None


def first_touch3_wick(ts, h, l, c, i, direction, window_s=1440 * 60):
    """Same but using intrabar high/low (wick) touch — stricter definition."""
    t0 = int(ts[i])
    p0 = c[i]
    end = t0 + window_s
    j = i + 1
    while j < len(ts) and ts[j] <= end:
        up = (h[j] / p0 - 1.0) * 100.0 * direction
        dn = (l[j] / p0 - 1.0) * 100.0 * direction
        if up >= 3.0 and dn <= -3.0:
            # both inside same bar: ambiguous, use close
            cl = (c[j] / p0 - 1.0) * 100.0 * direction
            return 1 if cl >= 3.0 else -1
        if up >= 3.0:
            return 1
        if dn <= -3.0:
            return -1
        j += 1
    return None


# ── statistics ───────────────────────────────────────────────────────────────
def boot_diff(a, b, seed=SEED, rounds=20000):
    """Percentile bootstrap CI for mean(a)-mean(b), unpaired, my own seed."""
    rng = np.random.default_rng(seed)
    a = np.asarray(a, float)
    b = np.asarray(b, float)
    if len(a) == 0 or len(b) == 0:
        return (np.nan, np.nan)
    # chunk to bound memory
    out = np.empty(rounds)
    cs = max(10, int(8e6 // max(len(a), len(b))))
    pos = 0
    while pos < rounds:
        k = min(cs, rounds - pos)
        ma = a[rng.integers(0, len(a), (k, len(a)))].mean(1)
        mb = b[rng.integers(0, len(b), (k, len(b)))].mean(1)
        out[pos:pos + k] = ma - mb
        pos += k
    return (np.percentile(out, 2.5), np.percentile(out, 97.5))


def boot_mean(v, seed=SEED, rounds=20000):
    rng = np.random.default_rng(seed)
    v = np.asarray(v, float)
    if len(v) == 0:
        return (np.nan, np.nan)
    out = np.empty(rounds)
    cs = 2000
    pos = 0
    while pos < rounds:
        k = min(cs, rounds - pos)
        out[pos:pos + k] = v[rng.integers(0, len(v), (k, len(v)))].mean(1)
        pos += k
    return (np.percentile(out, 2.5), np.percentile(out, 97.5))


def perm_diff_p(a, b, seed=SEED, rounds=20000):
    """Two-sided permutation test on difference of means (label shuffle)."""
    rng = np.random.default_rng(seed)
    a = np.asarray(a, float)
    b = np.asarray(b, float)
    obs = a.mean() - b.mean()
    pool = np.concatenate([a, b])
    n = len(a)
    ge = 0
    for _ in range(rounds):
        rng.shuffle(pool)
        d = pool[:n].mean() - pool[n:].mean()
        if abs(d) >= abs(obs):
            ge += 1
    return (ge + 1) / (rounds + 1)


def circular_shift_p(R, ev_idx, base_idx, seed=SEED, rounds=5000):
    """Null: event times are irrelevant -> circularly shift the event indicator
    series, preserving event clustering/serial structure, and recompute
    mean(R at shifted events) - mean(R at baseline)."""
    rng = np.random.default_rng(seed)
    n = len(R)
    ok = ~np.isnan(R)
    obs_idx = ev_idx[ok[ev_idx]]
    base_ok = base_idx[ok[base_idx]]
    if len(obs_idx) == 0 or len(base_ok) == 0:
        return np.nan
    obs = R[obs_idx].mean() - R[base_ok].mean()
    ge = 0
    done = 0
    while done < rounds:
        k = int(rng.integers(1, n))
        si = (ev_idx + k) % n
        si = si[ok[si]]
        if len(si) < len(ev_idx) * 0.8:
            continue
        d = R[si].mean() - R[base_ok].mean()
        if abs(d) >= abs(obs):
            ge += 1
        done += 1
    return (ge + 1) / (rounds + 1)


def dayblock_boot_diff(ev_ts, ev_v, base_ts, base_v, seed=SEED, rounds=10000):
    """Cluster (day) block bootstrap: resample calendar days with replacement,
    keeping all events/baselines inside chosen days. Handles serial dependence."""
    rng = np.random.default_rng(seed)
    days_e = (np.asarray(ev_ts) // 86400).astype(int)
    days_b = (np.asarray(base_ts) // 86400).astype(int)
    uniq = np.union1d(np.unique(days_e), np.unique(days_b))
    ed = {d: np.where(days_e == d)[0] for d in np.unique(days_e)}
    bd = {d: np.where(days_b == d)[0] for d in np.unique(days_b)}
    ev_v = np.asarray(ev_v, float)
    base_v = np.asarray(base_v, float)
    out = np.empty(rounds)
    for r in range(rounds):
        pick = rng.choice(uniq, size=len(uniq), replace=True)
        ei = np.concatenate([ed[d] for d in pick if d in ed]) if any(d in ed for d in pick) else np.array([], int)
        bi = np.concatenate([bd[d] for d in pick if d in bd]) if any(d in bd for d in pick) else np.array([], int)
        out[r] = (ev_v[ei].mean() if len(ei) else np.nan) - (base_v[bi].mean() if len(bi) else np.nan)
    out = out[~np.isnan(out)]
    return (np.percentile(out, 2.5), np.percentile(out, 97.5))


# ══════════════════════════════════════════════════════════════════════════════
def main():
    meta = json.load(open(f'{AUD}/snapshot_meta.json'))
    P('=' * 90)
    P('INDEPENDENT AUDIT — snapshot:', meta['snapshot_utc'])
    P('=' * 90)

    ts, o, h, l, c, v = load('BTC')
    n = len(ts)
    import datetime as dt
    P(f"\n[CLAIM 1] BTC bars n={n}  "
      f"{dt.datetime.fromtimestamp(int(ts[0]), dt.UTC):%Y-%m-%d %H:%M} -> "
      f"{dt.datetime.fromtimestamp(int(ts[-1]), dt.UTC):%Y-%m-%d %H:%M} UTC")
    gaps = np.diff(ts)
    ng = np.where(gaps != 60)[0]
    P(f"  gap count(!=60s)={len(ng)} sizes={[int(gaps[i]) for i in ng]} "
      f"pos={[dt.datetime.fromtimestamp(int(ts[i]), dt.UTC).isoformat() for i in ng]}")
    P(f"  claim window 2026-10-07 04:35 -> 2026-11-06 04:34: "
      f"{'MATCH' if meta['BTC']['min_iso'].startswith('2026-10-07T04:35') else 'NO MATCH (rolling window drift)'}")

    # ── indicators + parity (claim 8) ──────────────────────────────────────
    atr, tr = atr_wilder(h, l, c, 14)
    rsi = rsi_wilder(c, 14)
    mh = macd_hist(c, 12, 26, 9)

    t_atr = talib.ATR(h, l, c, 14)
    t_rsi = talib.RSI(c, 14)
    _, t_sig, t_hist = talib.MACD(c, 12, 26, 9)

    both = ~np.isnan(atr) & ~np.isnan(t_atr)
    P(f"\n[CLAIM 8 parity] ATR: first_valid mine={int(np.argmax(~np.isnan(atr)))} "
      f"talib={int(np.argmax(~np.isnan(t_atr)))} max|diff|={np.nanmax(np.abs(atr[both]-t_atr[both])):.3e}")
    both = ~np.isnan(rsi) & ~np.isnan(t_rsi)
    P(f"  RSI: first_valid mine={int(np.argmax(~np.isnan(rsi)))} "
      f"talib={int(np.argmax(~np.isnan(t_rsi)))} max|diff|={np.nanmax(np.abs(rsi[both]-t_rsi[both])):.3e}")
    both = ~np.isnan(mh) & ~np.isnan(t_hist)
    tail = both.copy(); tail[:100] = False
    P(f"  MACD hist: first_valid mine={int(np.argmax(~np.isnan(mh)))} "
      f"talib={int(np.argmax(~np.isnan(t_hist)))} "
      f"max|diff| all={np.nanmax(np.abs(mh[both]-t_hist[both])):.3e} "
      f"after bar100={np.nanmax(np.abs(mh[tail]-t_hist[tail])):.3e}")

    # ── claim 2: crossings ────────────────────────────────────────────────
    T = 60.0
    raw = raw_crossings(atr, T)
    dec = decluster(atr, T, 0.9)
    P(f"\n[CLAIM 2] raw crossings (prev<60<=cur) = {len(raw)}   (claim 201)")
    P(f"  declustered hyst=0.9 (re-arm <54) = {len(dec)}   (claim 109)")

    # alternative declustering rules
    alt = {
        'hyst0.95(<57)': decluster(atr, T, 0.95),
        'hyst0.833(<50)': decluster(atr, T, 50.0 / 60.0),
        'cooldown60bar': cooldown_events(atr, T, 60),
        'cooldown180bar': cooldown_events(atr, T, 180),
    }
    P('  alternative declustering: ' + ', '.join(f'{k}={len(v)}' for k, v in alt.items()))

    # SMA-ATR variant (claim 8)
    atr_s = atr_sma(h, l, c, 14)
    raw_s = raw_crossings(atr_s, T)
    inter = np.intersect1d(raw, raw_s)
    union = np.union1d(raw, raw_s)
    P(f"[CLAIM 8 SMA-ATR] raw crossings={len(raw_s)} (claim 277); "
      f"overlap |A∩B|={len(inter)}  jaccard={len(inter)/len(union):.3f}  "
      f"vs_wilder={len(inter)/len(raw):.3f}  vs_sma={len(inter)/len(raw_s):.3f}  (claim '28%')")

    # ── claim 3: direction ────────────────────────────────────────────────
    idx_map = build_index(ts)
    keep = dec[dec < n - 15]
    dropped_tail = len(dec) - len(keep)
    m, r = directions(mh, rsi, keep)
    agree = (m == r) & (m != 0)
    ev_i = keep[agree]
    skipped = len(keep) - len(ev_i)
    P(f"\n[CLAIM 3] declustered={len(dec)}  dropped(last 15 bars)={dropped_tail}  "
      f"tradeable={len(ev_i)}  skipped={skipped}  "
      f"LONG={(m[agree]==1).sum()} SHORT={(m[agree]==-1).sum()}   "
      f"(claim 95/14/48/47; skipped components: "
      f"disagree={int(((m!=r)&(m!=0)&(r!=0)).sum())} flat={int(((m==0)|(r==0)).sum())})")

    # ═══ CLAIM 4: volatility ═════════════════════════════════════════════
    P('\n[CLAIM 4] mean |forward return| event vs baseline (every-60th-bar, direction-filtered)')
    base_all = np.array([i for i in range(0, n, 60)])
    bm, br = directions(mh, rsi, base_all)
    base_i = base_all[((bm == br) & (bm != 0)) & (base_all < n - 15)]
    P(f'  baseline bars (every 60th, agree-filtered) n={len(base_i)}   (claim 510; raw every-60th={len(base_all)})')

    def abs_fwd(idxs, hz, exact=False):
        vals, keep = [], []
        for i in idxs:
            f = fwd_returns(ts, c, idx_map, i, [hz], exact_only=exact)
            if hz in f:
                vals.append(abs(f[hz]))
                keep.append(i)
        return np.array(vals), np.array(keep, dtype=int)

    P('  [baseline phase sensitivity] baseline = indices %60==k, for each k=0..59')
    phase_means = {60: [], 240: [], 1440: []}
    for k in range(60):
        bi_k = np.array([i for i in range(k, n, 60) if i < n - 15])
        for hz in (60, 240, 1440):
            bk, _ = abs_fwd(bi_k, hz)
            if len(bk):
                phase_means[hz].append(bk.mean())
    for hz in (60, 240, 1440):
        pm = np.array(phase_means[hz])
        P(f'    hz={hz:>5}m baseline mean across 60 grid phases: '
          f'min={pm.min():.4f} p25={np.percentile(pm,25):.4f} mean={pm.mean():.4f} '
          f'p75={np.percentile(pm,75):.4f} max={pm.max():.4f}')

    for hz in (60, 240, 1440):
        ev_a, ev_keep = abs_fwd(ev_i, hz)
        ba, b_keep = abs_fwd(base_i, hz)
        lo, hi = boot_diff(ev_a, ba, seed=SEED, rounds=20000)
        blo, bhi = dayblock_boot_diff(ts[ev_keep], ev_a, ts[b_keep], ba, seed=SEED + 1, rounds=5000)
        pperm = perm_diff_p(ev_a, ba, seed=SEED + 2, rounds=20000)
        pcirc = circular_shift_p(np.abs(np.array([
            fwd_returns(ts, c, idx_map, i, [hz]).get(hz, np.nan) for i in range(n)])),
            ev_i, base_i, seed=SEED + 3, rounds=4000)
        P(f'  {hz:>5}m: ev={ev_a.mean():.4f}% (n={len(ev_a)})  '
          f'base={ba.mean():.4f}% (n={len(ba)})  diff={ev_a.mean()-ba.mean():+.4f}  '
          f'boot95=[{lo:+.4f},{hi:+.4f}]  dayblock95=[{blo:+.4f},{bhi:+.4f}]  '
          f'perm_p={pperm:.4f}  circshift_p={pcirc:.4f}')

    # robustness: all declustered events (no direction filter)
    P('  robustness — all declustered events (no MACD/RSI filter):')
    for hz in (60, 240, 1440):
        ev_a, _ = abs_fwd(keep, hz)
        ba, _ = abs_fwd(base_i, hz)
        lo, hi = boot_diff(ev_a, ba, seed=SEED + 5, rounds=20000)
        P(f'    {hz:>5}m: ev={ev_a.mean():.4f}% (n={len(ev_a)}) base={ba.mean():.4f}% '
          f'diff={ev_a.mean()-ba.mean():+.4f} boot95=[{lo:+.4f},{hi:+.4f}]')

    # robustness: ATR-matched baseline (every 60th bar with ATR>=60, no cross needed)
    P('  robustness — ATR-matched baseline (every 60th bar where ATR>=60 at that bar):')
    amatched = np.array([i for i in base_all if i < n - 15 and not np.isnan(atr[i]) and atr[i] >= 60])
    P(f'    n={len(amatched)} (vs events n={len(ev_i)})')
    for hz in (60, 240, 1440):
        ev_a, _ = abs_fwd(ev_i, hz)
        ba, _ = abs_fwd(amatched, hz)
        if len(ba) == 0:
            continue
        lo, hi = boot_diff(ev_a, ba, seed=SEED + 6, rounds=20000)
        P(f'    {hz:>5}m: ev={ev_a.mean():.4f}%  atr>=60 base={ba.mean():.4f}%  '
          f'diff={ev_a.mean()-ba.mean():+.4f} boot95=[{lo:+.4f},{hi:+.4f}]')

    # robustness: unfiltered baseline (all every-60th bars, no direction filter)
    P('  robustness — baseline with NO direction filter:')
    bf = np.array([i for i in base_all if i < n - 15])
    for hz in (60, 240, 1440):
        ev_a, _ = abs_fwd(ev_i, hz)
        ba, _ = abs_fwd(bf, hz)
        lo, hi = boot_diff(ev_a, ba, seed=SEED + 7, rounds=20000)
        P(f'    {hz:>5}m: ev={ev_a.mean():.4f}%  base={ba.mean():.4f}% (n={len(ba)})  '
          f'diff={ev_a.mean()-ba.mean():+.4f} boot95=[{lo:+.4f},{hi:+.4f}]')

    # robustness: huge baseline = ALL bars (removes grid-phase noise)
    P('  robustness — baseline = EVERY bar (n=42792, no grid):')
    allbars = np.arange(n - 15)
    for hz in (60, 240, 1440):
        ev_a, _ = abs_fwd(ev_i, hz)
        ba, _ = abs_fwd(allbars, hz)
        lo, hi = boot_diff(ev_a, ba, seed=SEED + 12, rounds=6000)
        P(f'    {hz:>5}m: ev={ev_a.mean():.4f}%  all-bars base={ba.mean():.4f}% (n={len(ba)})  '
          f'diff={ev_a.mean()-ba.mean():+.4f} boot95=[{lo:+.4f},{hi:+.4f}]')

    # robustness: alternative declustering rules -> volatility result
    P('  robustness — alternative declustering (60m |move| ev vs every-60th base):')
    for name, eidx in list(alt.items()) + [('hyst0.9(theirs)', dec)]:
        eidx = eidx[eidx < n - 15]
        mm, rr = directions(mh, rsi, eidx)
        eidx2 = eidx[(mm == rr) & (mm != 0)]
        if len(eidx2) < 3:
            P(f'    {name}: n={len(eidx2)} too few')
            continue
        row = []
        for hz in (60, 240):
            ev_a, _ = abs_fwd(eidx2, hz)
            ba, _ = abs_fwd(base_i, hz)
            lo, hi = boot_diff(ev_a, ba, seed=SEED + 8, rounds=10000)
            row.append(f'{hz}m ev={ev_a.mean():.3f} base={ba.mean():.3f} d={ev_a.mean()-ba.mean():+.3f}[{lo:+.3f},{hi:+.3f}]')
        P(f'    {name}: n={len(eidx2)} | ' + ' | '.join(row))

    # ═══ CLAIM 5: directional edge ═══════════════════════════════════════
    P('\n[CLAIM 5] direction-aligned forward return for the tradeable events')
    P(f'  first raw crossing bar index={raw[0]} last={raw[-1]} (n={n}); '
      f'MACD hist first valid=33 -> all events past indicator warmup')
    edays = (ts[ev_i] // 86400)
    uniq, cnts = np.unique(edays, return_counts=True)
    P(f'  event clustering: {len(uniq)} distinct days, max events/day={cnts.max()}, '
      f'mean={cnts.mean():.1f}')
    for hz in HORIZONS:
        vals = []
        for i in ev_i:
            f = fwd_returns(ts, c, idx_map, i, [hz])
            if hz in f:
                d = 1 if mh[i] > 0 else -1  # agreed direction (MACD==RSI for all ev_i)
                vals.append(f[hz] * d)
        vals = np.array(vals)
        k = int((vals > 0).sum())
        nn = len(vals)
        bt = stats.binomtest(k, nn, 0.5, alternative='two-sided')
        lo, hi = boot_mean(vals, seed=SEED + 9, rounds=20000)
        P(f'  {hz:>5}m: n={nn} mean={vals.mean():+.4f}% WR={100*k/nn:.1f}% ({k}/{nn}) '
          f'binom two-sided p={bt.pvalue:.4g}  boot95=[{lo:+.4f},{hi:+.4f}]')

    # entry timing robustness: enter at NEXT bar close instead of event bar close
    P('  robustness — enter at next bar close (signal bar close = fill at same close in original):')
    for hz in (15, 60, 240, 1440):
        vals = []
        for i in ev_i:
            if i + 1 >= n:
                continue
            d = 1 if mh[i] > 0 else -1
            p0 = c[i + 1]
            t1 = int(ts[i + 1]) + hz * 60
            j = idx_map.get(t1)
            if j is None:
                continue
            vals.append((c[j] / p0 - 1.0) * 100.0 * d)
        vals = np.array(vals)
        k = int((vals > 0).sum())
        lo, hi = boot_mean(vals, seed=SEED + 10, rounds=20000)
        P(f'    {hz:>5}m: n={len(vals)} mean={vals.mean():+.4f}% WR={100*k/len(vals):.1f}% '
          f'boot95=[{lo:+.4f},{hi:+.4f}]')

    # ═══ CLAIM 6: >=3% move within 24h ══════════════════════════════════
    P('\n[CLAIM 6] first touch of +/-3% within 24h (direction-aligned, close-based)')
    ev_touch = [first_touch3(ts, c, i, 1 if mh[i] > 0 else -1) for i in ev_i]
    base_touch = [first_touch3(ts, c, i, 1 if mh[i] > 0 else -1) for i in base_i]
    eh = sum(1 for x in ev_touch if x is not None)
    bh = sum(1 for x in base_touch if x is not None)
    edir = sum(1 for x in ev_touch if x == 1)
    bdir = sum(1 for x in base_touch if x == 1)
    P(f'  events: {eh}/{len(ev_i)} ({100*eh/len(ev_i):.1f}%)  (claim 18/95=18.9%)')
    P(f'  baseline: {bh}/{len(base_i)} ({100*bh/len(base_i):.1f}%)  (claim 80/510=15.7%)')
    p_ev = stats.binomtest(edir, eh, 0.5, alternative='greater').pvalue if eh else float('nan')
    P(f'  event big-moves in direction: {edir}/{eh} one-sided binom p={p_ev:.4f}  (claim 14/18 p=0.0154)')
    P(f'  baseline big-moves in direction: {bdir}/{bh} ({100*bdir/bh:.1f}%)  (claim 41/80=51.2%)')
    if eh and bh:
        odds, pf = stats.fisher_exact([[edir, eh - edir], [bdir, bh - bdir]], alternative='greater')
        P(f'  Fisher exact (event vs baseline in-direction): one-sided p={pf:.4f}  (proper comparison test)')
        # rate comparison
        pr = stats.fisher_exact([[eh, len(ev_i) - eh], [bh, len(base_i) - bh]], alternative='two-sided')
        P(f'  Fisher exact (big-move RATE ev vs base): two-sided p={pr[1]:.4f}')
    # wick-based variant
    ev_touch_w = [first_touch3_wick(ts, h, l, c, i, 1 if mh[i] > 0 else -1) for i in ev_i]
    base_touch_w = [first_touch3_wick(ts, h, l, c, i, 1 if mh[i] > 0 else -1) for i in base_i]
    ehw = sum(1 for x in ev_touch_w if x is not None)
    bhw = sum(1 for x in base_touch_w if x is not None)
    edirw = sum(1 for x in ev_touch_w if x == 1)
    bdirw = sum(1 for x in base_touch_w if x == 1)
    P(f'  wick-based: events {ehw}/{len(ev_i)} ({100*ehw/len(ev_i):.1f}%) in-dir {edirw}/{ehw} | '
      f'baseline {bhw}/{len(base_i)} ({100*bhw/len(base_i):.1f}%) in-dir {bdirw}/{bhw}')

    # ═══ CLAIM 7: cross-coin ═════════════════════════════════════════════
    P('\n[CLAIM 7] cross-coin with ATR% threshold (claim says 0.076%, script default 0.077%)')
    coins = ['SOL', 'SUI', 'TAO', 'PUMP', 'GALA', 'GMX', 'IMX', 'SAND']
    claimed = {'SOL': (49, 47), 'SUI': (40, 46), 'TAO': (54, 46), 'PUMP': (2, 5),
               'GALA': (128, 121), 'GMX': (206, 186), 'IMX': (145, 133), 'SAND': (48, 42)}
    for pct_thr in (0.076, 0.077):
        P(f'  --- threshold {pct_thr}% ---')
        pool_in, pool_out = 0, 0
        for tok in coins:
            cts, co, ch, cl, cc, cv = load(tok)
            cn = len(cc)
            catr, _ = atr_wilder(ch, cl, cc, 14)
            catrp = catr / cc * 100.0
            cmh = macd_hist(cc)
            crsi = rsi_wilder(cc)
            cidx = build_index(cts)
            cev = decluster(catrp, pct_thr, 0.9)
            cev = cev[cev < cn - 15]
            cm, cr = directions(cmh, crsi, cev)
            cev = cev[(cm == cr) & (cm != 0)]
            t3h = t3w = 0
            f24 = []
            for i in cev:
                d = 1 if cmh[i] > 0 else -1
                t = first_touch3(cts, cc, i, d)
                if t == 1:
                    t3h += 1
                elif t == -1:
                    t3w += 1
                f = fwd_returns(cts, cc, cidx, i, [1440])
                if 1440 in f:
                    f24.append(f[1440] * d)
            f24 = np.array(f24)
            ci = boot_mean(f24, seed=SEED + 11, rounds=10000) if len(f24) else (np.nan, np.nan)
            cl_ = claimed[tok]
            match = 'OK' if (t3h, t3w) == cl_ else f'claim={cl_}'
            flat = int(((ch == cl) & (cl == cc) & (cc == co)).sum())
            P(f'    {tok:>5}: ev={len(cev):>4} 3%dir/wrong={t3h}/{t3w} {match} | '
              f'24h dir mean={f24.mean() if len(f24) else float("nan"):+.3f}% n={len(f24)} '
              f'CI95=[{ci[0]:+.3f},{ci[1]:+.3f}] {">>CI includes 0" if (ci[0] <= 0 <= ci[1]) else "!! CI EXCLUDES 0"} | '
              f'flat_bars={flat} ({100*flat/cn:.0f}%)')
            pool_in += t3h
            pool_out += t3w
        P(f'    POOLED: {pool_in}/{pool_in+pool_out} = {100*pool_in/(pool_in+pool_out):.1f}% in-dir '
          f'(claim 672/1298 = 51.8%)')
        pb = stats.binomtest(pool_in, pool_in + pool_out, 0.5, alternative='greater').pvalue
        P(f'    pooled one-sided binom p={pb:.4f}')

    # ═══ extras: gap/survivorship audit ═════════════════════════════════
    P('\n[SURVIVORSHIP / GAP AUDIT]')
    P(f'  events in last 15 bars (silently dropped by original): '
      f'{int((dec >= n - 15).sum())} of {len(dec)}')
    for hz in (15, 60, 240, 1440):
        ev_ok = sum(1 for i in ev_i if hz in fwd_returns(ts, c, idx_map, i, [hz], exact_only=True))
        ba_ok = sum(1 for i in base_i if hz in fwd_returns(ts, c, idx_map, i, [hz], exact_only=True))
        ev_fb = sum(1 for i in ev_i if hz in fwd_returns(ts, c, idx_map, i, [hz], exact_only=False))
        P(f'  hz={hz:>5}m: events resolvable exact={ev_ok}/{len(ev_i)} with-fallback={ev_fb} | '
          f'baseline exact={ba_ok}/{len(base_i)}')
    # does any event sit on the last bar before the gap?
    gi = np.where(np.diff(ts) != 60)[0]
    if len(gi):
        g0 = int(gi[0])
        near = [int(i) for i in ev_i if abs(int(i) - g0) < 1500]
        P(f'  gap at index {g0}; tradeable events within +/-1500 bars of gap: {near}')
        # 0%-return artifact check: events whose t0+60m falls inside gap
        for hz in (60, 1440):
            art = []
            for i in ev_i:
                tgt = int(ts[i]) + hz * 60
                if int(ts[g0]) < tgt < int(ts[g0 + 1]):
                    j = idx_map.get(tgt - 60)
                    if j is not None and j == i:
                        art.append((int(i), hz))
            P(f'  horizon {hz}m falling in gap with fallback landing back on event bar (0% return): {art}')
    # baseline bars that coincide with event bars
    overlap = np.intersect1d(ev_i, base_i)
    P(f'  bars that are BOTH event and baseline: {len(overlap)} -> {list(map(int, overlap[:10]))}')
    # baseline bars inside +/-1440 bars of an event (overlapping windows)
    evset = set(map(int, ev_i))
    close_to_ev = sum(1 for b in base_i if any(abs(int(b) - e) <= 1440 for e in ev_i))
    P(f'  baseline bars within 1440 bars of some event (overlapping outcome windows): {close_to_ev}/{len(base_i)}')

    # ═══ multiple comparisons tally ══════════════════════════════════════
    P('\n[MULTIPLE COMPARISONS] original script tests: 6 thresholds x 12 direction variants x '
      '5 HTF rules x 6 entry schemes x 3 quiet settings x 8 horizons x 3 touch targets x 9 coins')
    P('  Bonferroni on claim-6 p=0.0154 with just 4 sibling tests: '
      f'{min(1.0, 0.0154*4):.4f}; with 8: {min(1.0,0.0154*8):.4f}; with 50: {min(1.0,0.0154*50):.3f}')
    P(f'  claim-5 15m p=4.25e-04 -> Bonferroni x8 horizons = {min(1.0,4.25e-4*8):.2e} (still significant, NEGATIVE edge)')

    out = '\n'.join(L)
    open(f'{AUD}/audit_report.txt', 'w').write(out)
    P(f'\n[written] {AUD}/audit_report.txt')


if __name__ == '__main__':
    main()
