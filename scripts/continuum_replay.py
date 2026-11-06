#!/usr/bin/env python3
"""
continuum_replay.py — Reconstruct continuum score history for ANY token.

The production ContinuumEngine only ever runs for BTC (continuum.db is BTC-only).
This script replays the EXACT compute_states() pipeline — including its stateful
hysteresis, EMA300 duration tracking, and score smoothing — over historical
candles for any token, serving candles from memory instead of live DB reads.

Nothing is written to continuum.db: the DB init is disabled and save_state() is
never called; results go to continuum_replay.db.

Usage:
  python3 continuum_replay.py --token BTC --validate   # replay BTC, compare vs recorded
  python3 continuum_replay.py --token SOL              # replay one coin
  python3 continuum_replay.py --all                    # replay the 12 study coins

Output table (data/continuum_replay.db):
  continuum_replay(token TEXT, ts INTEGER, score REAL, price REAL,
                   PRIMARY KEY(token, ts))
"""
import argparse
import contextlib
import io
import os
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paths import HERMES_DATA, CANDLES_DB

import continuum_engine as ce
from continuum_engine import ContinuumEngine

REPLAY_DB = os.path.join(HERMES_DATA, 'continuum_replay.db')

STUDY_COINS = ['BTC', 'SOL', 'SUI', 'TAO', 'PUMP', 'GALA', 'GMX',
               'IMX', 'SAND', 'FOGO', 'COMP', 'DYM']
HTF = (('5m', 300), ('15m', 900), ('1h', 3600))


class ReplayEngine(ContinuumEngine):
    """ContinuumEngine with memory-backed candle reads and no DB."""

    def __init__(self, token, mem):
        self._mem = mem
        super().__init__(token)

    def _init_db(self):
        self.db = None  # never touch continuum.db

    def _read_candles(self, timeframe, limit=400):
        assert timeframe in ('1m', '5m', '15m', '1h', '4h')
        return self._mem.get(timeframe, [])[-limit:]

    def _read_live_price(self):
        return None  # historical replay: no live price


def _load_candles(token, table):
    conn = None
    try:
        conn = sqlite3.connect(CANDLES_DB, timeout=10)
        rows = conn.execute(
            f"SELECT ts, open, high, low, close, volume FROM {table} "
            f"WHERE token = ? ORDER BY ts ASC", (token.upper(),)
        ).fetchall()
        return [{'ts': int(r[0]), 'open': float(r[1]), 'high': float(r[2]),
                 'low': float(r[3]), 'close': float(r[4]),
                 'volume': float(r[5])} for r in rows]
    finally:
        if conn:
            conn.close()


def replay(token, warmup=500):
    """Replay continuum compute_states over the token's full 1m history.
    Returns list of (ts, score, price) oldest-first."""
    import bisect
    m1 = _load_candles(token, 'candles_1m')
    if len(m1) < warmup + 100:
        print(f'{token}: only {len(m1)} 1m candles — skip')
        return []
    htf = {}
    hts = {}
    for tf, iv in HTF:
        arr = _load_candles(token, f'candles_{tf}')
        htf[tf] = arr
        hts[tf] = [c['ts'] for c in arr]

    mem = {'1m': []}
    eng = ReplayEngine(token, mem)
    out = []
    # suppress engine prints (phase changes, read errors)
    with contextlib.redirect_stdout(io.StringIO()):
        for k in range(warmup, len(m1)):
            t = m1[k]['ts']
            mem['1m'] = m1[max(0, k - 399):k + 1]
            for tf, iv in HTF:
                n_done = bisect.bisect_right(hts[tf], t - iv)
                mem[tf] = htf[tf][max(0, n_done - 50):n_done]
            try:
                st = eng.compute_states('1m')
            except Exception:
                st = None
            if st is not None:
                out.append((t, float(st.state_score), float(st.price)))
    return out


def save(token, series):
    conn = None
    try:
        conn = sqlite3.connect(REPLAY_DB, timeout=10)
        conn.execute("""CREATE TABLE IF NOT EXISTS continuum_replay(
            token TEXT NOT NULL, ts INTEGER NOT NULL,
            score REAL, price REAL,
            PRIMARY KEY(token, ts))""")
        conn.executemany(
            "INSERT OR REPLACE INTO continuum_replay VALUES (?,?,?,?)",
            [(token.upper(), t, s, p) for t, s, p in series])
        conn.commit()
    finally:
        if conn:
            conn.close()


def validate(token='BTC'):
    """Replay BTC and compare against recorded continuum.db scores (nearest ts
    within 60s). Reports Pearson/Spearman + sign agreement vs the 50 line."""
    series = replay(token)
    if not series:
        return
    conn = sqlite3.connect(os.path.join(HERMES_DATA, 'continuum.db'))
    rec = conn.execute(
        "SELECT ts, state_score FROM continuum_states "
        "WHERE token=? AND state_score IS NOT NULL", (token.upper(),)
    ).fetchall()
    conn.close()
    if not rec:
        print('no recorded scores to validate against')
        return
    import bisect
    rec_ts = sorted(t for t, s in rec)
    rec_map = dict(rec)
    pairs = []
    for t, s, _p in series:
        i = bisect.bisect_left(rec_ts, t)
        best = None
        for j in (i - 1, i):
            if 0 <= j < len(rec_ts) and abs(rec_ts[j] - t) <= 60:
                best = rec_ts[j]
                break
        if best is not None:
            pairs.append((s, rec_map[best]))
    if len(pairs) < 100:
        print(f'only {len(pairs)} matched pairs — cannot validate')
        return
    n = len(pairs)
    xs = [p[0] for p in pairs]
    ys = [p[1] for p in pairs]
    mx, my = sum(xs) / n, sum(ys) / n
    sxy = sum((a - mx) * (b - my) for a, b in pairs)
    sxx = sum((a - mx) ** 2 for a in xs)
    syy = sum((b - my) ** 2 for b in ys)
    pearson = sxy / ((sxx * syy) ** 0.5) if sxx * syy > 0 else 0.0
    # Spearman via rank (average ties approximated by sort order)
    def rank(v):
        order = sorted(range(len(v)), key=lambda i: v[i])
        r = [0.0] * len(v)
        i = 0
        while i < len(order):
            j = i
            while j + 1 < len(order) and v[order[j + 1]] == v[order[i]]:
                j += 1
            avg = (i + j) / 2 + 1
            for k in range(i, j + 1):
                r[order[k]] = avg
            i = j + 1
        return r
    rx, ry = rank(xs), rank(ys)
    n2 = n
    mx2, my2 = sum(rx) / n2, sum(ry) / n2
    sxy2 = sum((a - mx2) * (b - my2) for a, b in zip(rx, ry))
    sxx2 = sum((a - mx2) ** 2 for a in rx)
    syy2 = sum((b - my2) ** 2 for b in ry)
    spearman = sxy2 / ((sxx2 * syy2) ** 0.5) if sxx2 * syy2 > 0 else 0.0
    agree = sum(1 for a, b in pairs if (a >= 50) == (b >= 50))
    mae = sum(abs(a - b) for a, b in pairs) / n
    print(f'VALIDATION {token}: n={n} pairs')
    print(f'  Pearson={pearson:.4f}  Spearman={spearman:.4f}  '
          f'MAE={mae:.2f} pts  sign(50) agreement={100.0 * agree / n:.1f}%')
    print(f'  replay range [{min(xs):.1f},{max(xs):.1f}] vs '
          f'recorded [{min(ys):.1f},{max(ys):.1f}]')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--token', default='BTC')
    ap.add_argument('--validate', action='store_true')
    ap.add_argument('--all', action='store_true')
    args = ap.parse_args()
    if args.validate:
        validate(args.token)
        return
    tokens = STUDY_COINS if args.all else [args.token]
    for tk in tokens:
        series = replay(tk)
        if series:
            save(tk, series)
            print(f'{tk}: {len(series)} scores '
                  f'({series[0][0]} -> {series[-1][0]}) saved')


if __name__ == '__main__':
    main()
