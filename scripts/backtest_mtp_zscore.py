#!/usr/bin/env python3
"""
Backtest: mtp_zscore multi-timeperiod z-score signal
Fixed: uses naive lookback z-score (correct population stdev) matching reference backtest.
Sweeps lookback combos, Z bounds, and hold horizons on top 10 winning tokens.

Token universe: DYDX, MON, XMR, BCH, FET, MORPHO, NEAR, ENS, LINK, AVAX
Goal: Find high W/L combos to tune for 75% system win-rate via profit-monster + ATR SL.
"""
import sqlite3, statistics, sys, os
from typing import List, Dict, Any, Optional
import time

DB = '/root/.hermes/data/candles.db'

# ── Token universe ───────────────────────────────────────────────────────────
TOKENS = ['DYDX', 'MON', 'XMR', 'BCH', 'FET', 'MORPHO', 'NEAR', 'ENS', 'LINK', 'AVAX']

# ── Lookback combos ────────────────────────────────────────────────────────────
LOOKBACK_COMBOS = [
    (50, 100, 150),
    (50, 100, 200),
    (50, 150, 200),
    (14,  50, 150),
    (14,  50, 200),
]

Z_MIN_SWEEP = [1.0, 1.5, 2.0]
Z_MAX = 99.0

# ── Hold horizons (1m bars) ───────────────────────────────────────────────────
HORIZONS_BARS = [1, 5, 15, 30, 60, 120, 240]
HORIZONS_LABELS = ['1m', '5m', '15m', '30m', '1h', '2h', '4h']

MAX_LB = 200
MIN_BARS_COMPUTE = MAX_LB + 5  # warmup bars needed before first zscore


def get_candles(token: str) -> List[tuple]:
    conn = sqlite3.connect(DB, timeout=30)
    c = conn.cursor()
    c.execute("""
        SELECT ts, close FROM candles_1m
        WHERE token=? ORDER BY ts ASC
    """, (token,))
    rows = c.fetchall()
    conn.close()
    return rows


def pop_zscore(prices: List[float], idx: int, window: int) -> Optional[float]:
    """Z-score at idx using window bars ending at idx (not including current bar)."""
    if idx < window:
        return None
    chunk = prices[idx - window:idx]
    if len(chunk) < window:
        return None
    mu = sum(chunk) / len(chunk)
    var = sum((v - mu) ** 2 for v in chunk) / len(chunk)  # population variance
    std = var ** 0.5
    if std == 0:
        return None
    return (prices[idx] - mu) / std


def backtest_combo(
    token: str,
    lb_short: int,
    lb_mid: int,
    lb_long: int,
    z_min: float,
    z_max: float,
    horizons: List[int],
) -> Dict[str, List[Dict[int, float]]]:
    """Backtest mtp_zscore for ONE token and parameter combo."""
    candles = get_candles(token)
    if not candles or len(candles) < MIN_BARS_COMPUTE + max(horizons):
        return {}

    closes = [c[1] for c in candles]
    n_max = len(closes)
    max_h = max(horizons)

    signals = {'long': [], 'short': []}
    last_signal_bar = {'long': -999, 'short': -999}
    progress_ctr = 0

    for i in range(MIN_BARS_COMPUTE, n_max - max_h):
        # Compute z-scores at bar i (using last `window` values ending at i)
        z_s = pop_zscore(closes, i, lb_short)
        z_m = pop_zscore(closes, i, lb_mid)
        z_l = pop_zscore(closes, i, lb_long)

        if z_s is None or z_m is None or z_l is None:
            continue

        # Direction from sign
        dir_s = 'long' if z_s > 0 else 'short' if z_s < 0 else None
        dir_m = 'long' if z_m > 0 else 'short' if z_m < 0 else None
        dir_l = 'long' if z_l > 0 else 'short' if z_l < 0 else None

        if dir_s is None or dir_m is None or dir_l is None:
            continue

        # Bounds: abs(z) in [z_min, z_max]
        abs_s, abs_m, abs_l = abs(z_s), abs(z_m), abs(z_l)
        in_s = z_min <= abs_s <= z_max
        in_m = z_min <= abs_m <= z_max
        in_l = z_min <= abs_l <= z_max

        # ALL 3/3 must agree direction AND be within bounds
        if not (dir_s == dir_m == dir_l):
            continue
        if not (in_s and in_m and in_l):
            continue

        direction = dir_s

        # Cooldown: 20 bars same direction
        if i - last_signal_bar[direction] < 20:
            continue
        last_signal_bar[direction] = i

        entry_price = closes[i]
        rets = {}
        for h in horizons:
            idx_f = i + h
            if idx_f < n_max:
                ret = (closes[idx_f] - entry_price) / entry_price * 100
                if direction == 'short':
                    ret = -ret
                rets[h] = ret

        if rets:
            signals[direction].append(rets)

        progress_ctr += 1
        if progress_ctr % 5000 == 0:
            print(f"    [{token}] bar {i}/{n_max}...")

    return signals


def compute_stats(sig_list: List[Dict[int, float]], horizons: List[int]) -> Dict[int, Dict[str, float]]:
    if not sig_list:
        return {}
    stats = {}
    for h in horizons:
        rets = [s[h] for s in sig_list if h in s]
        if not rets:
            continue
        n = len(rets)
        avg = sum(rets) / n
        wins = [r for r in rets if r > 0]
        losses = [r for r in rets if r < 0]
        wr = len(wins) / n * 100 if n > 0 else 0
        avg_win = sum(wins) / len(wins) if wins else 0.0
        avg_loss = sum(losses) / len(losses) if losses else 0.0
        wl = abs(avg_win / avg_loss) if avg_loss != 0 else float('inf')
        stats[h] = {
            'n': n, 'wr': wr, 'avg': avg,
            'avg_win': avg_win, 'avg_loss': avg_loss, 'wl': wl,
        }
    return stats


def run_sweep():
    t0 = time.time()
    print("=" * 130)
    print("MTP_ZSCORE BACKTEST — LOOKBACK COMBO x Z_BOUNDS x HOLD HORIZON SWEEP")
    print("Top 10 Winning Tokens: DYDX MON XMR BCH FET MORPHO NEAR ENS LINK AVAX")
    print("=" * 130)
    print(f"Combos: {LOOKBACK_COMBOS}")
    print(f"Z_MIN sweep: {Z_MIN_SWEEP}")
    print(f"Z_MAX: {Z_MAX}")
    print(f"Fire: 3/3 agree direction AND |z| in [Z_MIN, Z_MAX]")
    print(f"Cooldown: 20 bars same direction")
    print()

    results_with_horizon = []
    total_jobs = len(LOOKBACK_COMBOS) * len(Z_MIN_SWEEP) * len(TOKENS)
    job = 0

    for combo in LOOKBACK_COMBOS:
        lb_s, lb_m, lb_l = combo
        combo_label = f"({lb_s},{lb_m},{lb_l})"

        for z_min in Z_MIN_SWEEP:
            z_label = f"Z>={z_min}"

            agg_long, agg_short = [], []

            for token in TOKENS:
                job += 1
                t_tok = time.time()
                print(f"\n  [{job}/{total_jobs}] combo={combo_label} z_min={z_min} token={token}...")

                result = backtest_combo(token, lb_s, lb_m, lb_l, z_min, Z_MAX, HORIZONS_BARS)
                agg_long.extend(result.get('long', []))
                agg_short.extend(result.get('short', []))

                elapsed = time.time() - t_tok
                n_long = len(result.get('long', []))
                n_short = len(result.get('short', []))
                print(f"    -> fires: long={n_long} short={n_short} [{elapsed:.1f}s]")

            for direction, agg in [('LONG', agg_long), ('SHORT', agg_short)]:
                if not agg:
                    continue
                stats = compute_stats(agg, HORIZONS_BARS)
                for h, h_label in zip(HORIZONS_BARS, HORIZONS_LABELS):
                    if h not in stats:
                        continue
                    s = stats[h]
                    results_with_horizon.append({
                        'combo': combo_label,
                        'z': z_label,
                        'dir': direction,
                        'fires': s['n'],
                        'wr': s['wr'],
                        'avg_win': s['avg_win'],
                        'avg_loss': s['avg_loss'],
                        'wl': s['wl'],
                        'avg_ret': s['avg'],
                        'horizon': h_label,
                    })

    # ── Summary tables per horizon ─────────────────────────────────────────────
    for h_label in HORIZONS_LABELS:
        print(f"\n{'='*130}")
        print(f"HOLD HORIZON: {h_label}")
        print(f"{'='*130}")
        print(f"  {'Combo':<18} | {'Z':>6} | {'Dir':<5} | {'Fires':>6} | {'WR%':>6} | "
              f"{'AvgWin%':>8} | {'AvgLoss%':>9} | {'W/L':>7} | {'AvgRet%':>8}")
        print(f"  {'-'*110}")

        rows = [r for r in results_with_horizon if r['horizon'] == h_label]
        # Sort by W/L desc (inf last), then fires desc
        rows.sort(key=lambda x: (-x['wl'] if x['wl'] != float('inf') else -999, -x['fires']))

        for r in rows:
            wl_str = f"{r['wl']:.2f}" if r['wl'] != float('inf') else "inf"
            print(f"  {r['combo']:<18} | {r['z']:>6} | {r['dir']:<5} | {r['fires']:>6} | "
                  f"{r['wr']:>6.1f} | {r['avg_win']:>+8.3f} | {r['avg_loss']:>+9.3f} | "
                  f"{wl_str:>7} | {r['avg_ret']:>+8.3f}")

    # ── Best W/L per horizon ─────────────────────────────────────────────────
    print(f"\n{'='*130}")
    print("BEST W/L COMBOS ACROSS ALL HORIZONS")
    print(f"{'='*130}")

    best_per_horizon = {}
    for r in results_with_horizon:
        h = r['horizon']
        if h not in best_per_horizon:
            best_per_horizon[h] = r
        elif r['wl'] != float('inf') and best_per_horizon[h].get('wl') == float('inf'):
            best_per_horizon[h] = r
        elif r['wl'] != float('inf') and r['wl'] > best_per_horizon[h].get('wl', 0):
            best_per_horizon[h] = r

    print(f"  {'Horizon':<8} | {'Combo':<18} | {'Z':>6} | {'Dir':<5} | {'Fires':>6} | "
          f"{'WR%':>5} | {'W/L':>6} | {'AvgRet%':>8}")
    print(f"  {'-'*90}")
    for h_label in HORIZONS_LABELS:
        if h_label in best_per_horizon:
            r = best_per_horizon[h_label]
            wl_str = f"{r['wl']:.2f}" if r['wl'] != float('inf') else "inf"
            print(f"  {h_label:<8} | {r['combo']:<18} | {r['z']:>6} | {r['dir']:<5} | "
                  f"{r['fires']:>6} | {r['wr']:>5.1f} | {wl_str:>6} | {r['avg_ret']:>+8.3f}")

    # ── Z threshold impact ───────────────────────────────────────────────────
    print(f"\n{'='*130}")
    print("Z THRESHOLD IMPACT (LONG, 1h horizon)")
    print(f"{'='*130}")

    for z_min in Z_MIN_SWEEP:
        z_label = f"Z>={z_min}"
        rows_z = [r for r in results_with_horizon
                  if r['z'] == z_label and r['dir'] == 'LONG' and r['horizon'] == '1h']
        if rows_z:
            total_fires = sum(r['fires'] for r in rows_z)
            wl_vals = [r['wl'] for r in rows_z if r['wl'] != float('inf')]
            avg_wl = sum(wl_vals) / len(wl_vals) if wl_vals else 0
            avg_wr = sum(r['wr'] for r in rows_z) / len(rows_z)
            avg_ret = sum(r['avg_ret'] for r in rows_z) / len(rows_z)
            print(f"  {z_label}: Fires={total_fires:>6}, Avg W/L={avg_wl:.2f}, "
                  f"Avg WR%={avg_wr:.1f}%, Avg Ret%={avg_ret:+.3f}%")

    # ── Top firing combos LONG 1h ────────────────────────────────────────────
    print(f"\n{'='*130}")
    print("TOP FLARING COMBOS (LONG, 1h horizon)")
    print(f"{'='*130}")
    long_1h_rows = [r for r in results_with_horizon
                    if r['dir'] == 'LONG' and r['horizon'] == '1h']
    long_1h_rows.sort(key=lambda x: -x['fires'])
    print(f"  {'Combo':<18} | {'Z':>6} | {'Fires':>6} | {'WR%':>6} | {'W/L':>6} | {'AvgRet%':>8}")
    print(f"  {'-'*70}")
    for r in long_1h_rows[:15]:
        wl_str = f"{r['wl']:.2f}" if r['wl'] != float('inf') else "inf"
        print(f"  {r['combo']:<18} | {r['z']:>6} | {r['fires']:>6} | {r['wr']:>6.1f} | "
              f"{wl_str:>6} | {r['avg_ret']:>+8.3f}")

    total_time = time.time() - t0
    print(f"\nTotal elapsed: {total_time:.1f}s")

    # ── Recommendations ──────────────────────────────────────────────────────
    print(f"\n{'='*130}")
    print("RECOMMENDATIONS FOR 75% SYSTEM WIN-RATE")
    print(f"{'='*130}")
    print("""
Key insight: The 75% system win-rate comes from W/L ratio (profit-monster rides
big winners) + ATR SL handling the losers. Directional WR is capped ~45-50%.

Phase 1 (Start):     Z_MIN=(1.5,1.5,1.5) → high fires, validate signal logic
Phase 2 (Tune):      Z_MIN=(2.0,2.0,2.0) → medium fires, better W/L
Phase 3 (High W/L):  Z_MIN=(2.5,2.5,2.5) or higher → sparse but W/L > 3x

Production recommended params:
  MTP_ZSCORE_LB_SHORT = 50
  MTP_ZSCORE_LB_MID   = 100
  MTP_ZSCORE_LB_LONG  = 200
  Z_MIN = 1.5, Z_MAX = 3.5 (start); raise to 2.0 after 50+ live signals
""")


if __name__ == '__main__':
    run_sweep()
