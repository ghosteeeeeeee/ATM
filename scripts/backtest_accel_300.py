#!/usr/bin/env python3
"""
backtest_accel_300.py — Param sweep backtest for accel-300- SHORT signal.

Replays 1m price history through the accel-300 detection logic with different
parameter sets. Simulates ATR-based SL exits. Reports win rate and P&L impact.
"""

import sys, os, sqlite3, math
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

PRICE_DB = '/root/.hermes/data/signals_hermes.db'
OUTCOMES_DB = '/root/.hermes/data/signals_hermes_runtime.db'

# ── EMA helper ──────────────────────────────────────────────────────────────

def ema_series(values, period):
    if len(values) < period:
        return [None] * len(values)
    k = 2.0 / (period + 1)
    result = [None] * (period - 1)
    val = sum(values[:period]) / period
    result.append(val)
    for v in values[period:]:
        val = v * k + val * (1 - k)
        result.append(val)
    return result

# ── ATR helper ──────────────────────────────────────────────────────────────

def compute_atr(closes, period=14):
    """Simple ATR from close prices (approximation using bar-to-bar changes)."""
    if len(closes) < period + 1:
        return None
    changes = [abs(closes[i] - closes[i-1]) for i in range(1, len(closes))]
    if len(changes) < period:
        return None
    atr = sum(changes[-period:]) / period
    return atr

def atr_sl_pct(atr, entry_price):
    """Compute SL% using ATR tier logic from tpsl_utils."""
    if atr is None or entry_price == 0:
        return 0.01  # fallback 1%
    atr_pct = atr / entry_price
    # Pick k based on tier
    if atr_pct < 0.01:
        k = 0.8
    elif atr_pct <= 0.015:
        k = 1.0
    else:
        k = 0.25
    sl_pct = k * atr_pct
    # Clamp
    sl_pct = max(0.01, min(0.025, sl_pct))
    return sl_pct

# ── Detection logic (replay) ───────────────────────────────────────────────

def detect_short(closes, params):
    """Replay accel-300- SHORT detection on a list of close prices.
    Returns list of (entry_idx, entry_price) tuples for signals that fired.
    """
    period = params['period']
    persistence = params['persistence']
    min_gap = params['min_gap']
    min_growth = params['min_growth']
    slope_pct = params['slope_pct']
    slope_window = params['slope_window']

    min_rows = period + max(persistence, 3)
    if len(closes) < min_rows:
        return []

    ema = ema_series(closes, period)
    gap_pcts = [
        None if e is None or e == 0 else (p - e) / e * 100.0
        for p, e in zip(closes, ema)
    ]

    signals = []
    cooldown_until = -1

    for idx in range(min_rows - 1, len(closes)):
        if idx <= cooldown_until:
            continue

        latest_ema = ema[idx]
        gap_now = gap_pcts[idx]
        if latest_ema is None or gap_now is None or closes[idx] == latest_ema:
            continue

        # SHORT: price below EMA
        if closes[idx] >= latest_ema:
            continue

        # Min gap
        if abs(gap_now) < min_gap:
            continue

        # Persistence: price below EMA for last N bars
        start = idx - persistence + 1
        if start < 0:
            continue
        persist_ok = True
        for j in range(start, idx + 1):
            if ema[j] is None or closes[j] >= ema[j]:
                persist_ok = False
                break
        if not persist_ok:
            continue

        # Gap growth: gap must be widening (more negative)
        growth_idx = idx - persistence
        if growth_idx < 0 or gap_pcts[growth_idx] is None:
            continue
        gap_then = gap_pcts[growth_idx]
        gap_growth = gap_now - gap_then
        if gap_growth >= -min_growth:
            continue

        # Gap velocity: must be <= 0.01 (downward or flat)
        if idx < 2:
            continue
        gap_prev = gap_pcts[idx - 1]
        if gap_prev is None:
            continue
        gap_velocity = gap_now - gap_prev
        if gap_velocity > 0.01:
            continue

        # Slope filter
        if slope_window >= 2 and idx >= slope_window - 1:
            chunk = closes[idx - slope_window + 1:idx + 1]
            x_mean = (slope_window - 1) / 2.0
            y_mean = sum(chunk) / slope_window
            denom = sum((i - x_mean) ** 2 for i in range(slope_window))
            if denom > 0 and y_mean != 0:
                numer = sum((i - x_mean) * (chunk[i] - y_mean) for i in range(slope_window))
                pct_slope = (numer / denom) / y_mean * 100.0
                if pct_slope >= -slope_pct:
                    continue

        # Position filter: don't SHORT at bottom 20% of 20-bar range
        range_lb = min(20, idx + 1)
        if range_lb >= 5:
            r_high = max(closes[idx - range_lb + 1:idx + 1])
            r_low = min(closes[idx - range_lb + 1:idx + 1])
            r_size = r_high - r_low
            if r_size > 0:
                pos = (closes[idx] - r_low) / r_size
                if pos < 0.20:
                    continue

        # Signal fires!
        signals.append((idx, closes[idx]))
        cooldown_until = idx + params.get('cooldown', 10)

    return signals

# ── Load price data ─────────────────────────────────────────────────────────

def load_prices(token):
    conn = sqlite3.connect(PRICE_DB, timeout=10)
    c = conn.cursor()
    c.execute("""
        SELECT timestamp, price FROM price_history
        WHERE token = ?
        ORDER BY timestamp ASC
    """, (token.upper(),))
    rows = c.fetchall()
    conn.close()
    return [{'timestamp': r[0], 'price': r[1]} for r in rows]

# ── Get actual trade outcomes for comparison ────────────────────────────────

def get_actual_outcomes():
    conn = sqlite3.connect(OUTCOMES_DB, timeout=10)
    c = conn.cursor()
    c.execute("""
        SELECT token, created_at, closed_at, is_win, pnl_pct, pnl_usdt, confidence
        FROM signal_outcomes
        WHERE signal_type LIKE '%accel-300%' AND direction='SHORT' AND trade_id IS NOT NULL
        ORDER BY created_at
    """)
    rows = c.fetchall()
    conn.close()
    return rows

# ── Main backtest ───────────────────────────────────────────────────────────

PARAM_SETS = {
    'baseline': {
        'period': 300, 'persistence': 7, 'min_gap': 0.35,
        'min_growth': 0.10, 'slope_pct': 0.0005, 'slope_window': 20,
        'cooldown': 10,
    },
    'A_strict_slope': {
        'period': 300, 'persistence': 7, 'min_gap': 0.35,
        'min_growth': 0.10, 'slope_pct': 0.002, 'slope_window': 20,
        'cooldown': 10,
    },
    'B_big_gap': {
        'period': 300, 'persistence': 7, 'min_gap': 0.50,
        'min_growth': 0.10, 'slope_pct': 0.0005, 'slope_window': 20,
        'cooldown': 10,
    },
    'C_more_persist': {
        'period': 300, 'persistence': 10, 'min_gap': 0.35,
        'min_growth': 0.10, 'slope_pct': 0.0005, 'slope_window': 20,
        'cooldown': 10,
    },
    'D_fresher': {
        'period': 300, 'persistence': 7, 'min_gap': 0.35,
        'min_growth': 0.10, 'slope_pct': 0.0005, 'slope_window': 20,
        'cooldown': 10,
    },
    'E_all_tight': {
        'period': 300, 'persistence': 10, 'min_gap': 0.50,
        'min_growth': 0.15, 'slope_pct': 0.002, 'slope_window': 20,
        'cooldown': 10,
    },
    'F_slope_001': {
        'period': 300, 'persistence': 7, 'min_gap': 0.35,
        'min_growth': 0.10, 'slope_pct': 0.001, 'slope_window': 20,
        'cooldown': 10,
    },
    'G_slope_003': {
        'period': 300, 'persistence': 7, 'min_gap': 0.35,
        'min_growth': 0.10, 'slope_pct': 0.003, 'slope_window': 20,
        'cooldown': 10,
    },
    'H_persist9_gap04': {
        'period': 300, 'persistence': 9, 'min_gap': 0.40,
        'min_growth': 0.10, 'slope_pct': 0.001, 'slope_window': 20,
        'cooldown': 10,
    },
}


def simulate_trade(closes, entry_idx, entry_price, direction='SHORT'):
    """Simulate a trade from entry. Uses ATR-based SL. Returns (pnl_pct, exit_idx)."""
    # Compute ATR at entry
    atr = compute_atr(closes[:entry_idx + 1], period=14)
    sl_pct = atr_sl_pct(atr, entry_price)

    # Simulate forward from entry
    for i in range(entry_idx + 1, len(closes)):
        price = closes[i]
        if direction == 'SHORT':
            # SL hit: price rises above entry by sl_pct
            if price >= entry_price * (1 + sl_pct):
                return -sl_pct, i
            # TP at 2x SL (take profit)
            if price <= entry_price * (1 - 2 * sl_pct):
                return 2 * sl_pct, i
        else:
            if price <= entry_price * (1 - sl_pct):
                return -sl_pct, i
            if price >= entry_price * (1 + 2 * sl_pct):
                return 2 * sl_pct, i

    # Trade still open at end of data — assume breakeven
    return 0.0, len(closes) - 1


def run_sweep(tokens=None):
    """Run param sweep across all tokens with price data."""
    # Get tokens from actual outcomes
    outcomes = get_actual_outcomes()
    if tokens is None:
        tokens = list(set(r[0] for r in outcomes))

    print(f"Running backtest on {len(tokens)} tokens...")
    print(f"Actual outcomes: {len(outcomes)} trades")

    # Load price data
    price_data = {}
    for token in tokens:
        prices = load_prices(token)
        if prices and len(prices) > 310:  # need 300+ for EMA warmup
            price_data[token] = [p['price'] for p in prices]

    print(f"Tokens with sufficient price data: {len(price_data)}")

    results = {}
    for name, params in PARAM_SETS.items():
        all_trades = []
        for token, closes in price_data.items():
            signals = detect_short(closes, params)
            for entry_idx, entry_price in signals:
                pnl, exit_idx = simulate_trade(closes, entry_idx, entry_price)
                ts = None
                # Try to get timestamp
                all_trades.append({
                    'token': token,
                    'entry_idx': entry_idx,
                    'entry_price': entry_price,
                    'pnl_pct': pnl,
                    'is_win': pnl > 0,
                })

        n = len(all_trades)
        wins = sum(1 for t in all_trades if t['is_win'])
        wr = (wins / n * 100) if n > 0 else 0
        total_pnl = sum(t['pnl_pct'] for t in all_trades)
        avg_win = sum(t['pnl_pct'] for t in all_trades if t['is_win']) / max(1, wins)
        losses = [t for t in all_trades if not t['is_win']]
        avg_loss = sum(t['pnl_pct'] for t in losses) / max(1, len(losses))

        results[name] = {
            'trades': n, 'wins': wins, 'losses': len(losses),
            'wr': wr, 'total_pnl': total_pnl,
            'avg_win': avg_win, 'avg_loss': avg_loss,
            'trade_list': all_trades,
        }

    return results


def print_results(results):
    print("\n" + "=" * 90)
    print(f"{'Set':<20} {'Trades':>7} {'Wins':>5} {'Losses':>7} {'WR%':>6} {'TotPnL':>8} {'AvgWin':>8} {'AvgLoss':>8}")
    print("=" * 90)

    baseline = results.get('baseline', {})
    for name, r in results.items():
        delta_wr = r['wr'] - baseline.get('wr', 0) if baseline else 0
        delta_pnl = r['total_pnl'] - baseline.get('total_pnl', 0) if baseline else 0
        wr_str = f"{r['wr']:.1f}%"
        pnl_str = f"{r['total_pnl']:+.3f}%"
        aw_str = f"{r['avg_win']:+.3f}%" if r['avg_win'] else '--'
        al_str = f"{r['avg_loss']:+.3f}%" if r['avg_loss'] else '--'

        marker = ''
        if name != 'baseline':
            if delta_wr > 0 and delta_pnl > 0:
                marker = ' ✓✓'
            elif delta_wr > 0:
                marker = ' ✓wr'
            elif delta_pnl > 0:
                marker = ' ✓pnl'

        print(f"{name:<20} {r['trades']:>7} {r['wins']:>5} {r['losses']:>7} {wr_str:>6} {pnl_str:>8} {aw_str:>8} {al_str:>8}{marker}")

    print("=" * 90)

    # Show per-token breakdown for baseline vs best
    if 'baseline' in results:
        bl_trades = {(t['token'], t['entry_idx']): t for t in results['baseline']['trade_list']}
        # Find best non-baseline set
        best_name = max(
            [(n, r) for n, r in results.items() if n != 'baseline'],
            key=lambda x: x[1]['total_pnl']
        )[0]
        best_trades = {(t['token'], t['entry_idx']): t for t in results[best_name]['trade_list']}

        print(f"\nBaseline vs {best_name} — trade-level comparison:")
        print(f"{'Token':<10} {'Entry':>8} {'BL PnL':>8} {'Best PnL':>9} {'Changed':>8}")
        print("-" * 50)

        all_keys = set(bl_trades.keys()) | set(best_trades.keys())
        for key in sorted(all_keys):
            bl = bl_trades.get(key)
            bt = best_trades.get(key)
            bl_pnl = f"{bl['pnl_pct']:+.3f}%" if bl else 'N/A'
            bt_pnl = f"{bt['pnl_pct']:+.3f}%" if bt else 'N/A'
            changed = ''
            if bl and bt:
                if bl['is_win'] != bt['is_win']:
                    changed = 'FLIP'
            elif bl and not bt:
                changed = 'KILLED'
            elif not bl and bt:
                changed = 'NEW'
            print(f"{key[0]:<10} {key[1]:>8} {bl_pnl:>8} {bt_pnl:>9} {changed:>8}")


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--tokens', nargs='*', help='Specific tokens to test')
    parser.add_argument('--verbose', '-v', action='store_true')
    args = parser.parse_args()

    results = run_sweep(tokens=args.tokens)
    print_results(results)
