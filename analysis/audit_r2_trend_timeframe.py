#!/usr/bin/env python3
"""Independent audit backtest for r2-trend-timeframe-optimization plan claims.

Method (per audit spec):
  - Sliding OLS regression over `window` closes on each token's candles.
  - LONG signal when R^2 >= thresh AND slope > 0; SHORT when R^2 >= thresh AND slope < 0.
  - Big win: price moves > 2% in signal direction within next `fwd` bars (using highs/lows).
  - Entry = signal bar close. Requires a full forward window of closed candles.
  - Avg move computed several ways (MFE-based and close-to-close) since the plan does not define it.

Implementation: rolling sums to find candidates fast, then exact OLS (the given
function) to confirm near the threshold. Pure independent re-implementation.
"""
import json
import sqlite3
import sys
from collections import defaultdict

sys.path.insert(0, '/root/.hermes/scripts')
from paths import CANDLES_DB  # noqa: E402

BIG_MOVE = 0.02  # 2%


def ols_params(y_vals):
    n = len(y_vals)
    if n < 3:
        return 0.0, y_vals[-1] if y_vals else 0.0, 0.0
    x = list(range(n))
    xm = (n - 1) / 2.0
    ym = sum(y_vals) / n
    num = sum((xi - xm) * (yi - ym) for xi, yi in zip(x, y_vals))
    den = sum((xi - xm) ** 2 for xi in x)
    if den == 0:
        return 0.0, ym, 0.0
    b = num / den
    a = ym - b * xm
    ss_res = sum((yi - (b * xi + a)) ** 2 for xi, yi in zip(x, y_vals))
    ss_tot = sum((yi - ym) ** 2 for yi in y_vals)
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0.0
    return b, a, r2


def run_backtest(table, window, thresh, fwd, use_unclosed=False):
    conn = sqlite3.connect(CANDLES_DB)
    cur = conn.cursor()
    sql = f"SELECT token, ts, high, low, close FROM {table}"
    if not use_unclosed:
        sql += " WHERE is_closed=1"
    sql += " ORDER BY token, ts"
    cur.execute(sql)

    by_tok = defaultdict(list)
    for tok, ts, high, low, close in cur.fetchall():
        by_tok[tok].append((ts, high, low, close))
    conn.close()

    # rolling-sum params for candidate scan
    w = window
    sum_x = w * (w - 1) / 2.0
    sum_x2 = (w - 1) * w * (2 * w - 1) / 6.0
    den = sum_x2 - sum_x * sum_x / w

    signals = []  # (token, ts, direction, mfe_pct, c2c_pct)
    n_bars_scanned = 0
    EPS = 0.02  # recheck exactly when rolling r2 within EPS of threshold

    for tok, rows in by_tok.items():
        n = len(rows)
        if n < w + fwd:
            continue
        closes = [r[3] for r in rows]
        highs = [r[1] for r in rows]
        lows = [r[2] for r in rows]
        tss = [r[0] for r in rows]

        # initialize rolling sums for first window ending at i=w-1
        ys = closes[:w]
        sum_y = sum(ys)
        sum_y2 = sum(v * v for v in ys)
        s_xy = sum(k * v for k, v in enumerate(ys))  # x = 0..w-1
        old = list(ys)

        for i in range(w - 1, n - fwd):
            n_bars_scanned += 1
            if i > w - 1:
                y_old = old[0]
                y_new = closes[i]
                s_xy = s_xy - (sum_y - y_old) + (w - 1) * y_new
                sum_y = sum_y - y_old + y_new
                sum_y2 = sum_y2 - y_old * y_old + y_new * y_new
                old.pop(0)
                old.append(y_new)

            ss_tot = sum_y2 - sum_y * sum_y / w
            if ss_tot <= 0:
                continue
            num = s_xy - sum_x * sum_y / w
            b = num / den
            ss_res = sum_y2 - b * s_xy - (sum_y - b * sum_x) / w * sum_y
            r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0.0
            if r2 < thresh - EPS:
                continue

            # exact OLS confirmation
            b_e, a_e, r2_e = ols_params(closes[i - w + 1:i + 1])
            if r2_e < thresh:
                continue
            if b_e == 0:
                continue

            entry = closes[i]
            if entry <= 0:
                continue
            fwd_highs = highs[i + 1:i + 1 + fwd]
            fwd_lows = lows[i + 1:i + 1 + fwd]
            fwd_close = closes[i + fwd]

            if b_e > 0:  # LONG
                mfe = (max(fwd_highs) - entry) / entry
                c2c = (fwd_close - entry) / entry
                signals.append((tok, tss[i], 'LONG', mfe, c2c))
            else:  # SHORT
                mfe = (entry - min(fwd_lows)) / entry
                c2c = (entry - fwd_close) / entry
                signals.append((tok, tss[i], 'SHORT', mfe, c2c))

    return signals, n_bars_scanned, len(by_tok)


def summarize(signals, label=''):
    out = {}
    for d in ('LONG', 'SHORT', 'COMBINED'):
        sel = signals if d == 'COMBINED' else [s for s in signals if s[2] == d]
        n = len(sel)
        if n == 0:
            out[d] = {'n': 0}
            continue
        big = sum(1 for s in sel if s[3] > BIG_MOVE)
        avg_mfe = sum(s[3] for s in sel) / n * 100
        avg_c2c = sum(s[4] for s in sel) / n * 100
        big_c2c = sum(1 for s in sel if s[4] > BIG_MOVE)
        out[d] = {
            'n': n,
            'bigwin_mfe_pct': round(big / n * 100, 1),
            'avg_move_mfe_pct': round(avg_mfe, 2),
            'bigwin_c2c_pct': round(big_c2c / n * 100, 1),
            'avg_move_c2c_pct': round(avg_c2c, 2),
        }
    return out


def nonoverlap_variant(signals, fwd):
    """After a signal on a token, ignore further signals for `fwd` bars (same direction pool, per token)."""
    kept = []
    last_ts = {}
    for s in sorted(signals, key=lambda x: (x[0], x[1])):
        tok, ts, d, mfe, c2c = s
        lt = last_ts.get(tok)
        if lt is not None and ts - lt < fwd * TF_SEC[TABLE]:
            continue
        last_ts[tok] = ts
        kept.append(s)
    return kept


def rising_edge_variant(signals):
    """Count only the first bar of each qualifying streak per token+direction."""
    kept = []
    prev = {}
    for s in sorted(signals, key=lambda x: (x[0], x[1])):
        tok, ts, d, mfe, c2c = s
        key = (tok, d)
        gap_ok = key not in prev or (ts - prev[key]) > TF_SEC[TABLE]
        if gap_ok:
            kept.append(s)
        prev[key] = ts
    return kept


if __name__ == '__main__':
    configs = [
        ('candles_1h', 8, 0.5, 24),
        ('candles_15m', 100, 0.6, 24),
        ('candles_5m', 60, 0.5, 24),
    ]
    TF_SEC = {'candles_1h': 3600, 'candles_15m': 900, 'candles_5m': 300}
    results = {}
    for TABLE, window, thresh, fwd in configs:
        TF = TF_SEC[TABLE]
        sigs, n_bars, n_tok = run_backtest(TABLE, window, thresh, fwd)
        res = {
            'table': TABLE, 'window': window, 'thresh': thresh, 'fwd': fwd,
            'tokens': n_tok, 'bars_scanned': n_bars,
            'primary': summarize(sigs),
            'nonoverlap': summarize(nonoverlap_variant(sigs, fwd)),
            'rising_edge': summarize(rising_edge_variant(sigs)),
        }
        results[f'{TABLE}_w{window}_t{thresh}'] = res
        print(f"\n=== {TABLE} window={window} thresh={thresh} fwd={fwd} ===")
        print(f"tokens={n_tok} bars_scanned={n_bars}")
        for variant in ('primary', 'nonoverlap', 'rising_edge'):
            print(f" -- {variant}:")
            for d, m in res[variant].items():
                print(f"    {d:8s} {m}")
        sys.stdout.flush()

    with open('/root/.hermes/data/audit_r2_trend_timeframes_results.json', 'w') as f:
        json.dump(results, f, indent=2)
    print("\nSaved to /root/.hermes/data/audit_r2_trend_timeframes_results.json")
