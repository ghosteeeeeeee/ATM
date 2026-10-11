#!/usr/bin/env python3
"""Audit part 2: base rates (unconditional move stats), close-peak avg move for signals,
per-token win-rate distributions, and threshold sensitivity for the 15m table."""
import sqlite3
import sys
from collections import defaultdict

sys.path.insert(0, '/root/.hermes/scripts')
from paths import CANDLES_DB  # noqa: E402
sys.path.insert(0, '/root/.hermes/analysis')
from audit_r2_trend_timeframe import ols_params, BIG_MOVE  # noqa: E402

TF_SEC = {'candles_1h': 3600, 'candles_15m': 900, 'candles_5m': 300}


def load(table):
    conn = sqlite3.connect(CANDLES_DB)
    cur = conn.cursor()
    cur.execute(f"SELECT token, ts, high, low, close FROM {table} WHERE is_closed=1 ORDER BY token, ts")
    by_tok = defaultdict(list)
    for row in cur.fetchall():
        by_tok[row[0]].append(row[1:])
    conn.close()
    return by_tok


def base_rates(table, fwd):
    """Unconditional: every bar with full fwd window. High/low-based big-move rates."""
    by_tok = load(table)
    n = bigL = bigS = 0
    sum_mfeL = sum_mfeS = 0.0
    for tok, rows in by_tok.items():
        m = len(rows)
        if m < fwd + 1:
            continue
        for i in range(0, m - fwd):
            entry = rows[i][3]
            if entry <= 0:
                continue
            fh = max(r[1] for r in rows[i + 1:i + 1 + fwd])
            fl = min(r[2] for r in rows[i + 1:i + 1 + fwd])
            n += 1
            if (fh - entry) / entry > BIG_MOVE:
                bigL += 1
            if (entry - fl) / entry > BIG_MOVE:
                bigS += 1
            sum_mfeL += (fh - entry) / entry
            sum_mfeS += (entry - fl) / entry
    return {
        'bars': n,
        'base_bigmove_long_pct': round(bigL / n * 100, 1),
        'base_bigmove_short_pct': round(bigS / n * 100, 1),
        'base_avg_mfe_long_pct': round(sum_mfeL / n * 100, 2),
        'base_avg_mfe_short_pct': round(sum_mfeS / n * 100, 2),
    }


def signal_details(table, window, thresh, fwd):
    """Per-token signal stats incl. close-peak variant; returns aggregate + per-token list."""
    by_tok = load(table)
    per_tok = {}
    agg = {'n': 0, 'big': 0, 'mfe_sum': 0.0, 'c2c_sum': 0.0, 'peakc_sum': 0.0, 'big_peakc': 0}
    for tok, rows in by_tok.items():
        m = len(rows)
        if m < window + fwd:
            continue
        closes = [r[3] for r in rows]
        highs = [r[1] for r in rows]
        lows = [r[2] for r in rows]
        c = {'n': 0, 'big': 0, 'mfe_sum': 0.0, 'c2c_sum': 0.0, 'peakc_sum': 0.0, 'big_peakc': 0}
        for i in range(window - 1, m - fwd):
            b, a, r2 = ols_params(closes[i - window + 1:i + 1])
            if r2 < thresh or b <= 0:  # LONG only
                continue
            entry = closes[i]
            fh = max(highs[i + 1:i + 1 + fwd])
            fc = max(closes[i + 1:i + 1 + fwd])
            endc = closes[i + fwd]
            c['n'] += 1
            if (fh - entry) / entry > BIG_MOVE:
                c['big'] += 1
            if (fc - entry) / entry > BIG_MOVE:
                c['big_peakc'] += 1
            c['mfe_sum'] += (fh - entry) / entry
            c['peakc_sum'] += (fc - entry) / entry
            c['c2c_sum'] += (endc - entry) / entry
        if c['n'] >= 20:  # only meaningful samples in distribution
            per_tok[tok] = c
        for k in agg:
            agg[k] += c[k]
    return agg, per_tok


if __name__ == '__main__':
    print('==== UNCONDITIONAL BASE RATES (all bars, fwd=24) ====')
    for table in ('candles_1h', 'candles_15m', 'candles_5m'):
        print(table, base_rates(table, 24))
        sys.stdout.flush()

    print()
    print('==== SIGNAL DETAIL (LONG) ====')
    for table, window, thresh in (('candles_1h', 8, 0.5), ('candles_15m', 100, 0.6), ('candles_5m', 60, 0.5)):
        agg, per_tok = signal_details(table, window, thresh, 24)
        n = agg['n']
        print(f"\n{table} w={window} t={thresh} LONG: n={n}")
        print(f"  bigwin high-based: {agg['big']/n*100:.1f}%  avg MFE: {agg['mfe_sum']/n*100:.2f}%")
        print(f"  bigwin close-peak: {agg['big_peakc']/n*100:.1f}%  avg peak-close move: {agg['peakc_sum']/n*100:.2f}%  avg c2c: {agg['c2c_sum']/n*100:.2f}%")
        wrs = sorted(((c['big'] / c['n'] * 100, tok, c['n']) for tok, c in per_tok.items()), reverse=True)
        n50 = sum(1 for w, _, _ in wrs if w >= 50.0)
        print(f"  per-token WR distribution: tokens={len(wrs)}, >=50% WR: {n50}, median: {wrs[len(wrs)//2][0]:.1f}%")
        print(f"  top5: {[(t, f'{w:.0f}%', f'n={n_}') for w, t, n_ in wrs[:5]]}")
        print(f"  bottom5: {[(t, f'{w:.0f}%', f'n={n_}') for w, t, n_ in wrs[-5:]]}")
        # what n-weighted WR for top-k tokens by signal count?
        by_n = sorted(((c['big'] / c['n'] * 100, tok, c['n']) for tok, c in per_tok.items()), key=lambda x: -x[2])
        top20 = by_n[:20]
        tot_n = sum(x[2] for x in top20)
        wr20 = sum(x[0] / 100 * x[2] for x in top20) / tot_n * 100
        print(f"  top-20 tokens by signal count: n={tot_n}, WR={wr20:.1f}%")
        sys.stdout.flush()

    print()
    print('==== 15m THRESHOLD SENSITIVITY (LONG, w=100, fwd=24) — plan claims t0.5=43.5%, t0.6=50.3%, t0.7=49.3% ====')
    for thresh in (0.5, 0.6, 0.7):
        agg, _ = signal_details('candles_15m', 100, thresh, 24)
        n = agg['n']
        print(f"  t={thresh}: n={n}  bigwin_high={agg['big']/n*100:.1f}%  avgMFE={agg['mfe_sum']/n*100:.2f}%  bigwin_closepeak={agg['big_peakc']/n*100:.1f}%  avgPeakClose={agg['peakc_sum']/n*100:.2f}%")
        sys.stdout.flush()
