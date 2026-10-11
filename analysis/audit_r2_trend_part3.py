#!/usr/bin/env python3
"""Audit part 3: time-split robustness, CIs, z-tests vs baseline, token-subset checks."""
import math
import sqlite3
import sys
from collections import defaultdict

sys.path.insert(0, '/root/.hermes/scripts')
from paths import CANDLES_DB  # noqa: E402
sys.path.insert(0, '/root/.hermes/analysis')
from audit_r2_trend_timeframe import ols_params, BIG_MOVE  # noqa: E402

TABLES = {'candles_1h': 3600, 'candles_15m': 900, 'candles_5m': 300}


def load(table):
    conn = sqlite3.connect(CANDLES_DB)
    cur = conn.cursor()
    cur.execute(f"SELECT token, ts, high, low, close FROM {table} WHERE is_closed=1 ORDER BY token, ts")
    by_tok = defaultdict(list)
    for tok, ts, high, low, close in cur.fetchall():
        by_tok[tok].append((ts, high, low, close))
    conn.close()
    return by_tok


def signals_and_baseline(table, window, thresh, fwd):
    """Return (signal_ts_list, signal_big_list, base_ts_list, base_big_list) for LONG.
    Also SHORT. ts lists used for time-split."""
    by_tok = load(table)
    sig = {'LONG': ([], []), 'SHORT': ([], [])}
    base = {'LONG': ([], []), 'SHORT': ([], [])}
    for tok, rows in by_tok.items():
        m = len(rows)
        if m < window + fwd:
            continue
        closes = [r[3] for r in rows]
        highs = [r[1] for r in rows]
        lows = [r[2] for r in rows]
        tss = [r[0] for r in rows]
        for i in range(0, m - fwd):
            entry = closes[i]
            if entry <= 0:
                continue
            fh = max(highs[i + 1:i + 1 + fwd])
            fl = min(lows[i + 1:i + 1 + fwd])
            base['LONG'][0].append(tss[i])
            base['LONG'][1].append((fh - entry) / entry > BIG_MOVE)
            base['SHORT'][0].append(tss[i])
            base['SHORT'][1].append((entry - fl) / entry > BIG_MOVE)
            if i < window - 1:
                continue
            b, a, r2 = ols_params(closes[i - window + 1:i + 1])
            if r2 < thresh or b == 0:
                continue
            if b > 0:
                sig['LONG'][0].append(tss[i])
                sig['LONG'][1].append((fh - entry) / entry > BIG_MOVE)
            else:
                sig['SHORT'][0].append(tss[i])
                sig['SHORT'][1].append((entry - fl) / entry > BIG_MOVE)
    return sig, base


def rate(big):
    return sum(big) / len(big) if big else 0.0


def ztest(x1, n1, x2, n2):
    p = (x1 + x2) / (n1 + n2)
    se = math.sqrt(p * (1 - p) * (1 / n1 + 1 / n2))
    return (x1 / n1 - x2 / n2) / se if se > 0 else 0.0


def wilson(k, n, z=1.96):
    if n == 0:
        return (0, 0)
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return ((c - h) / d, (c + h) / d)


if __name__ == '__main__':
    configs = [
        ('candles_1h', 8, 0.5),
        ('candles_15m', 100, 0.6),
        ('candles_5m', 60, 0.5),
    ]
    for table, window, thresh in configs:
        fwd = 24
        sig, base = signals_and_baseline(table, window, thresh, fwd)
        all_ts = sorted(sig['LONG'][0] + sig['SHORT'][0])
        mid = all_ts[len(all_ts) // 2] if all_ts else 0
        print(f"\n=== {table} w={window} t={thresh} f={fwd} (signal-time midpoint split) ===")
        for d in ('LONG', 'SHORT'):
            ts_list, big_list = sig[d]
            bts, bbig = base[d]
            k, n = sum(big_list), len(big_list)
            kb, nb = sum(bbig), len(bbig)
            lo, hi = wilson(k, n)
            z = ztest(k, n, kb, nb)
            print(f" {d}: signal WR={k/n*100:.1f}% (n={n}, 95%CI [{lo*100:.1f},{hi*100:.1f}]) "
                  f"vs base {kb/nb*100:.1f}% (n={nb}) -> lift {k/n*100-kb/nb*100:+.1f}pp, z={z:.1f}")
            for name, sel in (('H1', lambda t: t <= mid), ('H2', lambda t: t > mid)):
                kk = sum(1 for t, bb in zip(ts_list, big_list) if sel(t) and bb)
                nn = sum(1 for t in ts_list if sel(t))
                if nn:
                    print(f"      {name}: WR={kk/nn*100:.1f}% (n={nn})")
            sys.stdout.flush()
        # tokens-table subset (TRB ETH BTC IMX SKY AXS POL)
        sub = {'TRB', 'ETH', 'BTC', 'IMX', 'SKY', 'AXS', 'POL'}
        by_tok = load(table)
        kk = nn = 0
        for tok in sub:
            rows = by_tok.get(tok, [])
            m = len(rows)
            closes = [r[3] for r in rows]
            highs = [r[1] for r in rows]
            for i in range(window - 1, m - fwd):
                b, a, r2 = ols_params(closes[i - window + 1:i + 1])
                if r2 >= thresh and b > 0:
                    entry = closes[i]
                    fh = max(highs[i + 1:i + 1 + fwd])
                    nn += 1
                    if (fh - entry) / entry > BIG_MOVE:
                        kk += 1
        if nn:
            print(f" tokens-table-7 subset LONG: WR={kk/nn*100:.1f}% (n={nn})")
