#!/usr/bin/env python3
"""
MTP-ZSCORE Full Universe Backtest — INCREMENTAL WRITE
Results written to JSON after every job so partial data survives timeout/kill.
"""
import sqlite3, sys, os, time, json
from multiprocessing import Pool, cpu_count

DB = '/root/.hermes/data/candles.db'
N_WORKERS = min(8, cpu_count())

sys.path.insert(0, '/root/.hermes/scripts')
from hermes_constants import SHORT_BLACKLIST, LONG_BLACKLIST

from hermes_log import log
# ── Z-score ─────────────────────────────────────────────────────────────
def pop_zscore(prices: list, idx: int, window: int):
    if idx < window:
        return None
    chunk = prices[idx - window:idx]
    if len(chunk) < window:
        return None
    mu  = sum(chunk) / len(chunk)
    var = sum((v - mu) ** 2 for v in chunk) / len(chunk)
    std = var ** 0.5
    if std == 0:
        return None
    return (prices[idx] - mu) / std

# ── Params ─────────────────────────────────────────────────────────────
LOOKBACK_COMBOS = [
    (14, 50, 150), (14, 50, 200),
    (50, 100, 150), (50, 100, 200), (50, 150, 200),
    (20, 60, 150), (20, 80, 200),
    (30, 60, 150), (30, 100, 200),
    (14, 100, 150),
]
Z_MIN_SWEEP     = [1.0, 1.5, 2.0]
Z_MAX           = 99.0
HORIZONS_BARS   = [1, 5, 15, 30, 60, 120, 240]
HORIZONS_LABELS = ['1m', '5m', '15m', '30m', '1h', '2h', '4h']
MAX_LB          = 200
MIN_BARS        = MAX_LB + 5
COOLDOWN_BARS   = 20

# ── Candle cache per process ────────────────────────────────────────────
_cache = {}

def get_candles(token: str):
    if token in _cache:
        return _cache[token]
    conn = sqlite3.connect(DB, timeout=30)
    c = conn.cursor()
    c.execute("SELECT ts, close FROM candles_1m WHERE token=? ORDER BY ts ASC", (token,))
    rows = [(r[0], r[1]) for r in c.fetchall()]
    conn.close()
    _cache[token] = rows
    return rows

def get_all_tokens() -> list:
    conn = sqlite3.connect(DB, timeout=30)
    c = conn.cursor()
    c.execute("SELECT DISTINCT token FROM candles_1m ORDER BY token")
    tokens = [r[0] for r in c.fetchall()]
    conn.close()
    blocked = SHORT_BLACKLIST | LONG_BLACKLIST
    return [t for t in tokens if t not in blocked]

def backtest_one_token(args):
    token, lb_s, lb_m, lb_l, z_min, z_max = args
    rows = get_candles(token)
    if not rows or len(rows) < MIN_BARS + max(HORIZONS_BARS):
        return []
    closes = [r[1] for r in rows]
    n_max  = len(closes)
    max_h  = max(HORIZONS_BARS)
    last_bar = {'long': -9999, 'short': -9999}
    results = []
    for i in range(MIN_BARS, n_max - max_h):
        z_s = pop_zscore(closes, i, lb_s)
        z_m = pop_zscore(closes, i, lb_m)
        z_l = pop_zscore(closes, i, lb_l)
        if z_s is None or z_m is None or z_l is None:
            continue
        dir_s = 'long' if z_s > 0 else 'short' if z_s < 0 else None
        dir_m = 'long' if z_m > 0 else 'short' if z_m < 0 else None
        dir_l = 'long' if z_l > 0 else 'short' if z_l < 0 else None
        if dir_s is None or dir_m is None or dir_l is None:
            continue
        if not (dir_s == dir_m == dir_l):
            continue
        abs_s, abs_m, abs_l = abs(z_s), abs(z_m), abs(z_l)
        if not (z_min <= abs_s <= z_max and z_min <= abs_m <= z_max and z_min <= abs_l <= z_max):
            continue
        direction = dir_s
        if i - last_bar[direction] < COOLDOWN_BARS:
            continue
        last_bar[direction] = i
        entry = closes[i]
        rets = {}
        for h in HORIZONS_BARS:
            idx_f = i + h
            if idx_f < n_max:
                ret = (closes[idx_f] - entry) / entry * 100
                if direction == 'short':
                    ret = -ret
                rets[h] = ret
        if rets:
            results.append((direction, rets))
    return results

def compute_stats(sig_list, horizons):
    if not sig_list:
        return {}
    stats = {}
    for h in horizons:
        rets = [s[h] for s in sig_list if h in s]
        if not rets:
            continue
        n    = len(rets)
        avg  = sum(rets) / n
        wins    = [r for r in rets if r > 0]
        losses  = [r for r in rets if r < 0]
        wr      = len(wins) / n * 100 if n > 0 else 0
        avg_win  = sum(wins)   / len(wins)   if wins   else 0.0
        avg_loss = sum(losses)  / len(losses) if losses else 0.0
        wl = abs(avg_win / avg_loss) if avg_loss != 0 else float('inf')
        stats[h] = {'n': n, 'wr': wr, 'avg': avg,
                    'avg_win': avg_win, 'avg_loss': avg_loss, 'wl': wl}
    return stats

LOG_PATH   = '/root/.hermes/data/mtp_zscore_backtest.log'
RESULT_PATH = '/root/.hermes/data/mtp_zscore_backtest_raw.json'

def save_partial(results):
    with open(RESULT_PATH, 'w') as f:
        json.dump(results, f)

def run_sweep():
    global _cache
    t0     = time.time()
    tokens = get_all_tokens()
    jobs   = [(c, z) for c in LOOKBACK_COMBOS for z in Z_MIN_SWEEP]
    total  = len(jobs)

    log(f"MTP_ZSCORE BACKTEST | {len(tokens)} tokens | {total} jobs | {N_WORKERS} workers")
    log("=" * 120)

    all_results = []

    with Pool(N_WORKERS) as pool:
        for job_idx, (combo, z_min) in enumerate(jobs):
            lb_s, lb_m, lb_l = combo
            combo_label = f"({lb_s},{lb_m},{lb_l})"
            z_label     = f"Z>={z_min}"
            tasks = [(t, lb_s, lb_m, lb_l, z_min, Z_MAX) for t in tokens]

            agg_long, agg_short = [], []
            for results in pool.imap(backtest_one_token, tasks):
                for direction, rets in results:
                    if direction == 'long':
                        agg_long.append(rets)
                    else:
                        agg_short.append(rets)

            for direction, agg in [('LONG', agg_long), ('SHORT', agg_short)]:
                if not agg:
                    continue
                stats = compute_stats(agg, HORIZONS_BARS)
                for h, h_label in zip(HORIZONS_BARS, HORIZONS_LABELS):
                    if h not in stats:
                        continue
                    s = stats[h]
                    all_results.append({
                        'combo': combo_label, 'z': z_label, 'dir': direction,
                        'fires': s['n'], 'wr': s['wr'],
                        'avg_win': s['avg_win'], 'avg_loss': s['avg_loss'],
                        'wl': s['wl'], 'avg_ret': s['avg'],
                        'horizon': h_label,
                    })

            elapsed = time.time() - t0
            log(f"  [{job_idx+1:02d}/{total}] {combo_label} {z_label} | "
                f"L={len(agg_long):5d} S={len(agg_short):5d} | t={elapsed:.0f}s")

            # Save after every job so partial data survives kill/timeout
            save_partial(all_results)

    total_time = time.time() - t0
    log(f"\nTotal time: {total_time:.0f}s | Results: {len(all_results)} rows")
    log(f"Output: {RESULT_PATH}")

    # ── Summary tables ──────────────────────────────────────────────────
    for h_label in HORIZONS_LABELS:
        log(f"\n{'='*130}")
        log(f"HOLD HORIZON: {h_label}")
        log(f"{'='*130}")
        log(f"  {'Combo':<20} | {'Z':>6} | {'Dir':<5} | {'Fires':>6} | {'WR%':>6} | "
            f"{'AvgWin%':>8} | {'AvgLoss%':>9} | {'W/L':>7} | {'AvgRet%':>8}")
        log(f"  {'-'*115}")
        rows = sorted([r for r in all_results if r['horizon'] == h_label],
                      key=lambda x: (-x['wr'], -x['fires']))
        for r in rows:
            wl = f"{r['wl']:.2f}" if r['wl'] != float('inf') else "inf"
            log(f"  {r['combo']:<20} | {r['z']:>6} | {r['dir']:<5} | "
                f"{r['fires']:>6} | {r['wr']:>6.1f} | {r['avg_win']:>+8.3f} | "
                f"{r['avg_loss']:>+9.3f} | {wl:>7} | {r['avg_ret']:>+8.3f}")

    # ── Top 5 by WR per horizon ───────────────────────────────────────
    log(f"\n{'='*130}")
    log("TOP 5 COMBOS BY WR AT EACH HORIZON (min 50 fires)")
    for h_label in HORIZONS_LABELS:
        rows = sorted([r for r in all_results
                       if r['horizon'] == h_label and r['fires'] >= 50],
                      key=lambda x: (-x['wr'], -x['fires']))[:5]
        if not rows:
            continue
        log(f"\n  {h_label}:")
        log(f"  {'Combo':<20} | {'Z':>6} | {'Dir':<5} | {'Fires':>6} | {'WR%':>6} | {'W/L':>7} | {'AvgRet%':>8}")
        log(f"  {'-'*80}")
        for r in rows:
            wl = f"{r['wl']:.2f}" if r['wl'] != float('inf') else "inf"
            log(f"  {r['combo']:<20} | {r['z']:>6} | {r['dir']:<5} | "
                f"{r['fires']:>6} | {r['wr']:>6.1f} | {wl:>7} | {r['avg_ret']:>+8.3f}")

    # ── Best LONG + SHORT ─────────────────────────────────────────────
    log(f"\n{'='*130}")
    log("BEST LONG + SHORT COMBOS (min 30 fires)")
    for direction in ['LONG', 'SHORT']:
        rows = sorted([r for r in all_results
                       if r['dir'] == direction and r['fires'] >= 30],
                      key=lambda x: (-x['wr'], -x['fires']))[:10]
        log(f"\n  {direction}:")
        log(f"  {'Combo':<20} | {'Z':>6} | {'Horizon':>7} | {'Fires':>6} | {'WR%':>6} | {'W/L':>7} | {'AvgRet%':>8}")
        log(f"  {'-'*85}")
        for r in rows:
            wl = f"{r['wl']:.2f}" if r['wl'] != float('inf') else "inf"
            log(f"  {r['combo']:<20} | {r['z']:>6} | {r['horizon']:>7} | "
                f"{r['fires']:>6} | {r['wr']:>6.1f} | {wl:>7} | {r['avg_ret']:>+8.3f}")

    # ── Z threshold impact ─────────────────────────────────────────────
    log(f"\n{'='*130}")
    log("Z THRESHOLD IMPACT (ALL COMBOS AGGREGATED)")
    for direction in ['LONG', 'SHORT']:
        log(f"\n  {direction}:")
        log(f"  {'Z':>6} | {'Horizon':>7} | {'Fires':>10} | {'WR%':>6} | {'W/L':>7} | {'AvgRet%':>8}")
        log(f"  {'-'*68}")
        for z_min in Z_MIN_SWEEP:
            for h_label in HORIZONS_LABELS:
                rows = [r for r in all_results
                        if r['z'] == f"Z>={z_min}" and r['dir'] == direction
                        and r['horizon'] == h_label]
                if not rows:
                    continue
                total_fires = sum(r['fires'] for r in rows)
                if total_fires == 0:
                    continue
                avg_wr  = sum(r['wr']  * r['fires'] for r in rows) / total_fires
                wl_vals = [r['wl'] for r in rows if r['wl'] != float('inf')]
                avg_wl  = sum(wl_vals) / len(wl_vals) if wl_vals else 0
                avg_ret = sum(r['avg_ret'] * r['fires'] for r in rows) / total_fires
                wl_str  = f"{avg_wl:.2f}" if wl_vals else "inf"
                log(f"  {f'Z>={z_min}':>6} | {h_label:>7} | {total_fires:>10} | "
                    f"{avg_wr:>6.1f} | {wl_str:>7} | {avg_ret:>+8.3f}")

    # ── 60%+ WR candidates ────────────────────────────────────────────
    log(f"\n{'='*130}")
    log("PARAM COMBOS WITH 60%+ WR (min 20 fires)")
    log(f"{'='*130}")
    log(f"  {'Combo':<20} | {'Z':>6} | {'Dir':<5} | {'Horizon':>7} | {'Fires':>6} | {'WR%':>6} | {'W/L':>7} | {'AvgRet%':>8}")
    log(f"  {'-'*95}")
    candidates = sorted([r for r in all_results if r['wr'] >= 60 and r['fires'] >= 20],
                        key=lambda x: (-x['wr'], -x['fires']))
    for r in candidates[:30]:
        wl = f"{r['wl']:.2f}" if r['wl'] != float('inf') else "inf"
        log(f"  {r['combo']:<20} | {r['z']:>6} | {r['dir']:<5} | {r['horizon']:>7} | "
            f"{r['fires']:>6} | {r['wr']:>6.1f} | {wl:>7} | {r['avg_ret']:>+8.3f}")
    if not candidates:
        log("  (none found)")
    log(f"\nDONE. Total time: {total_time:.0f}s")

if __name__ == '__main__':
    run_sweep()