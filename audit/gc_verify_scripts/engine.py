#!/usr/bin/env python3
"""Counterfactual engine — independent implementation.
Loads events.json, coalesces episodes, computes direction-aware forward
returns from candles.db, multiple market baselines, overlap, and stats.
Writes episode records to /tmp/gaudit/episodes.json for downstream checks.
"""
import json, sqlite3, math, sys
import numpy as np
from datetime import datetime, timezone

CANDLES = '/root/.hermes/data/candles.db'
WIN_START = int(datetime(2026, 10, 2, 20, 0, tzinfo=timezone.utc).timestamp())
WIN_END = int(datetime(2026, 10, 8, 23, 2, tzinfo=timezone.utc).timestamp())
FWD_PAD = 8 * 3600 + 600

H = {'30m': 6, '1h': 12, '4h': 48, '8h': 96}
EPISODE_GAP = 3600

def coalesce(events, gap):
    by = {}
    for ts, g, tok, d in events:
        by.setdefault((g, tok, d), []).append(ts)
    eps = []
    for (g, tok, d), tss in by.items():
        tss.sort()
        start = last = tss[0]
        for ts in tss[1:]:
            if ts - last > gap:
                eps.append((start, g, tok, d))
                start = ts
            last = ts
        eps.append((start, g, tok, d))
    eps.sort()
    return eps

def load_candles(tokens):
    conn = sqlite3.connect(CANDLES)
    out = {}
    try:
        cur = conn.cursor()
        for tok in tokens:
            rows = cur.execute(
                "SELECT ts, open, high, low, close FROM candles_5m "
                "WHERE token=? AND is_closed=1 AND ts>=? AND ts<=? ORDER BY ts",
                (tok, WIN_START - 3600, WIN_END + FWD_PAD)).fetchall()
            if len(rows) > 100:
                a = np.array(rows, dtype=np.float64)
                out[tok] = a
    finally:
        conn.close()
    return out

def main():
    data = json.load(open('/tmp/gaudit/events.json'))
    events = [tuple(e) for e in data['events']]
    print(f"events: {len(events):,}")
    eps = coalesce(events, EPISODE_GAP)
    print(f"episodes(60min gap): {len(eps):,}")
    for gap, name in ((1800, '30min'), (7200, '120min')):
        print(f"episodes({name} gap): {len(coalesce(events, gap)):,}")

    tokens = sorted({e[2] for e in eps})
    candles = load_candles(tokens)
    print(f"distinct tokens in events: {len(tokens)}; with candles: {len(candles)}")
    missing = [t for t in tokens if t not in candles]
    print(f"missing tokens: {missing[:40]}")

    # per-token index: ts -> row idx
    idx = {t: {int(r[0]): i for i, r in enumerate(rows)} for t, rows in candles.items()}
    # per-token forward arrays (vectorized): for each n compute fwd% at each index
    fwd = {}   # token -> {n: np.array of (close[i+n]/open[i]-1)*100 aligned to rows idx}
    mfe = {}
    mae = {}
    for t, a in candles.items():
        o = a[:, 1]; h = a[:, 2]; l = a[:, 3]; c = a[:, 4]
        fwd[t] = {}
        for name, n in H.items():
            f = np.full(len(a), np.nan)
            if len(a) > n:
                f[:-n] = (c[n:] / o[:-n] - 1.0) * 100.0
            fwd[t][name] = f
        # 4h MFE/MAE via rolling max/min over 49 candles
        W = 49
        m4 = np.full(len(a), np.nan); n4 = np.full(len(a), np.nan)
        if len(a) >= W:
            hm = np.lib.stride_tricks.sliding_window_view(h, W).max(axis=1)
            lm = np.lib.stride_tricks.sliding_window_view(l, W).min(axis=1)
            m4[:len(a) - W + 1] = (hm / o[:len(a) - W + 1] - 1.0) * 100.0
            n4[:len(a) - W + 1] = (1.0 - lm / o[:len(a) - W + 1]) * 100.0
        mfe[t] = m4   # LONG MFE
        mae[t] = n4   # SHORT MFE == LONG MAE magnitude

    # market baseline per bucket per horizon: cross-sectional mean & median (unsigned)
    buckets = sorted({(int(e[0]) + 299) // 300 * 300 for e in eps})
    bidx = {b: i for i, b in enumerate(buckets)}
    mkt_mean = {name: dict() for name in H}
    mkt_med = {name: dict() for name in H}
    mkt_n = dict()
    for b in buckets:
        vals = {name: [] for name in H}
        for t, rows in candles.items():
            i = idx[t].get(b)
            if i is None:
                continue
            for name in H:
                v = fwd[t][name][i]
                if not math.isnan(v):
                    vals[name].append(v)
        mkt_n[b] = len(vals['4h'])
        for name in H:
            if len(vals[name]) >= 20:
                mkt_mean[name][b] = float(np.mean(vals[name]))
                mkt_med[name][b] = float(np.median(vals[name]))
    # BTC forward (unsigned) per bucket
    btc_fwd = {name: dict() for name in H}
    if 'BTC' in candles:
        for b, i in idx['BTC'].items():
            for name in H:
                v = fwd['BTC'][name][i]
                if not math.isnan(v):
                    btc_fwd[name][b] = float(v)
    # market drift summary
    for name in H:
        mv = np.array([mkt_mean[name][b] for b in buckets if b in mkt_mean[name]])
        print(f"market mean fwd {name:3}: n_buckets={len(mv)} mean={mv.mean():+.4f}% med={np.median(mv):+.4f}%")
    # MFE market baseline (claim 5)
    all_mfe = []
    for t, a in candles.items():
        m = mfe[t]
        sel = m[~np.isnan(m)]
        # only within window (entry bucket in window)
        ts = a[:, 0].astype(np.int64)
        mask = (ts >= WIN_START) & (ts <= WIN_END) & ~np.isnan(m)
        all_mfe.append(m[mask])
    all_mfe = np.concatenate(all_mfe)
    print(f"MARKET LONG MFE(4h): pairs={len(all_mfe):,} mean={all_mfe.mean():.3f}% med={np.median(all_mfe):.3f}% "
          f"share>=2%={np.mean(all_mfe >= 2.0)*100:.1f}% share>=5%={np.mean(all_mfe >= 5.0)*100:.1f}%")

    # build episode records
    recs = []
    for ts, g, tok, d in eps:
        rows = candles.get(tok)
        if rows is None:
            continue
        i = idx[tok].get(int(ts + 299) // 300 * 300) if (int(ts) % 300) else idx[tok].get(int(ts))
        # first candle with ts >= block ts:
        i2 = int(np.searchsorted(rows[:, 0], ts, side='left'))
        if i2 >= len(rows):
            continue
        if i2 + 48 >= len(rows):   # 4h forward needed (same censoring as the audit)
            continue
        b = int(rows[i2, 0])
        o = rows[i2, 1]
        sgn = 1.0 if d == 'LONG' else -1.0
        rec = {'ts': int(ts), 'gate': g, 'token': tok, 'dir': d, 'bucket': b, 'idx': i2}
        ok = True
        for name in H:
            f = fwd[tok][name][i2]
            if math.isnan(f):
                if name == '8h':
                    rec[name] = None
                    continue
                ok = False
                break
            signed = sgn * f
            rec[name] = signed
            mm = mkt_mean[name].get(b)
            md = mkt_med[name].get(b)
            bf = btc_fwd[name].get(b)
            rec[f'ex_{name}'] = signed - mm if mm is not None else None               # audit's formula
            rec[f'exn_{name}'] = signed - (mm if d == 'LONG' else -mm) if mm is not None else None  # market-neutral
            rec[f'exm_{name}'] = signed - (md if d == 'LONG' else -md) if md is not None else None
            rec[f'exb_{name}'] = signed - (bf if d == 'LONG' else -bf) if bf is not None else None
        if not ok:
            continue
        rec['mfe'] = float(mfe[tok][i2]) if not math.isnan(mfe[tok][i2]) else None
        rec['sfe'] = float(mfe[tok][i2] if d == 'LONG' else mae[tok][i2])  # direction-aware favorable excursion
        # lag-1 entry robustness: enter at OPEN of the NEXT candle (5-10 min later)
        if i2 + 1 + 48 < len(rows):
            b1 = int(rows[i2 + 1, 0])
            f1 = fwd[tok]['4h'][i2 + 1]
            mm1 = mkt_mean['4h'].get(b1)
            if not math.isnan(f1) and mm1 is not None:
                rec['ex_4h_lag1'] = sgn * f1 - mm1
            else:
                rec['ex_4h_lag1'] = None
        else:
            rec['ex_4h_lag1'] = None
        recs.append(rec)
    print(f"episodes with full 8h forward coverage: {len(recs):,}")
    # market SHORT MFE baseline (direction-aware comparison for SHORT gates)
    all_smfe = []
    for t, a in candles.items():
        m = mae[t]  # (1 - min_low/o): favorable excursion for SHORT
        ts = a[:, 0].astype(np.int64)
        mask = (ts >= WIN_START) & (ts <= WIN_END) & ~np.isnan(m)
        all_smfe.append(m[mask])
    all_smfe = np.concatenate(all_smfe)
    print(f"MARKET SHORT MFE(4h): pairs={len(all_smfe):,} mean={all_smfe.mean():.3f}% "
          f"share>=2%={np.mean(all_smfe >= 2.0)*100:.1f}%")
    json.dump({'recs': recs,
               'mkt_mean': {k: {str(b): v for b, v in d.items()} for k, d in mkt_mean.items()},
               'mkt_med': {k: {str(b): v for b, v in d.items()} for k, d in mkt_med.items()},
               'btc_fwd': {k: {str(b): v for b, v in d.items()} for k, d in btc_fwd.items()},
               'mkt_n_min': min(mkt_n.values()), 'mkt_n_max': max(mkt_n.values()),
               'mfe_market_mean': float(all_mfe.mean()),
               'mfe_market_share2': float(np.mean(all_mfe >= 2.0) * 100),
               'smfe_market_mean': float(all_smfe.mean()),
               'smfe_market_share2': float(np.mean(all_smfe >= 2.0) * 100)},
              open('/tmp/gaudit/episodes.json', 'w'))

if __name__ == '__main__':
    main()
