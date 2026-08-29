#!/usr/bin/env python3
"""
backtest_ichimoku.py — Walk-forward backtest of the Ichimoku Cloud signal.

Reuses the Ichimoku computation from the signal file. Runs at each bar j
using only data through bar j (no look-ahead). Tests with and without the
Chikou filter.

Entry: next bar's close
Exit:  max 48 bars OR TK cross reversal OR -2% SL OR +4% TP
"""

import os
import sys
import sqlite3
from typing import List, Dict, Optional, Tuple

# ── Paths ────────────────────────────────────────────────────────────
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paths import HERMES_DATA

# ── Ichimoku parameters (from hermes_constants) ─────────────────────
TENKAN_PERIOD   = 9
KIJUN_PERIOD    = 26
SENKOU_B_PERIOD = 52
CLOUD_SHIFT     = 26
MIN_SEP_PCT     = 0.002   # 0.2% min separation from cloud

# ── Backtest parameters ──────────────────────────────────────────────
BARS            = 2160     # 90 days of 1h
HOLD_BARS       = 48       # 48h max hold
STOP_LOSS_PCT   = -0.02    # -2%
TAKE_PROFIT_PCT =  0.04    # +4%

TOKENS = [
    'BTC', 'ETH', 'SOL', 'AVAX', 'LINK', 'DOGE', 'ARB', 'SUI',
    'INJ', 'OP', 'WLD', 'SEI', 'TIA', 'PYTH', 'JUP', 'W', 'S',
    'TON', 'KPEPE', 'RENDER',
]

CANDLES_DB = os.path.join(HERMES_DATA, 'candles.db')


# ═══════════════════════════════════════════════════════════════════════
# Ichimoku computation (adapted from signal file for walk-forward)
# ═══════════════════════════════════════════════════════════════════════

def donchian_mid(highs, lows, period, idx):
    """Donchian midline at index idx: (high[period] + low[period]) / 2."""
    if idx < period - 1:
        return None
    wh = max(highs[idx - period + 1 : idx + 1])
    wl = min(lows[idx - period + 1 : idx + 1])
    return (wh + wl) / 2.0


def compute_ichimoku_at(highs, lows, closes, j):
    """
    Compute Ichimoku components at bar j using data 0..j only.
    Returns dict of values at bar j, or None if not enough data.
    """
    if j < max(TENKAN_PERIOD, KIJUN_PERIOD, SENKOU_B_PERIOD) - 1:
        return None

    tenkan = donchian_mid(highs, lows, TENKAN_PERIOD, j)
    kijun  = donchian_mid(highs, lows, KIJUN_PERIOD, j)

    # Senkou spans: shifted forward by CLOUD_SHIFT
    # senkou_a[j] was computed at bar j - CLOUD_SHIFT
    sa_idx = j - CLOUD_SHIFT
    sb_idx = j - CLOUD_SHIFT

    if sa_idx < 0 or sb_idx < 0:
        return None

    tenkan_at = donchian_mid(highs, lows, TENKAN_PERIOD, sa_idx)
    kijun_at  = donchian_mid(highs, lows, KIJUN_PERIOD, sa_idx)
    if tenkan_at is None or kijun_at is None:
        return None
    senkou_a = (tenkan_at + kijun_at) / 2.0
    senkou_b = donchian_mid(highs, lows, SENKOU_B_PERIOD, sb_idx)
    if senkou_b is None:
        return None

    cloud_top = max(senkou_a, senkou_b)
    cloud_bot = min(senkou_a, senkou_b)
    color = 'bullish' if senkou_a > senkou_b else 'bearish'

    return {
        'tenkan': tenkan,
        'kijun': kijun,
        'senkou_a': senkou_a,
        'senkou_b': senkou_b,
        'cloud_top': cloud_top,
        'cloud_bot': cloud_bot,
        'color': color,
    }


def detect_at_bar(highs, lows, closes, j, use_chikou=True):
    """
    Detect Ichimoku signal at bar j using data 0..j.
    Walk-forward safe: no future data used.
    
    Chikou interpretation (walk-forward safe):
      For LONG: closes[j] > closes[j - CLOUD_SHIFT] (current price > price 26 bars ago)
      For SHORT: closes[j] < closes[j - CLOUD_SHIFT]
    """
    ich = compute_ichimoku_at(highs, lows, closes, j)
    if ich is None:
        return None

    tenkan = ich['tenkan']
    kijun  = ich['kijun']
    price  = closes[j]
    cloud_t = ich['cloud_top']
    cloud_b = ich['cloud_bot']
    color  = ich['color']

    if tenkan is None or kijun is None:
        return None

    # ── LONG ──────────────────────────────────────────────────────────
    if tenkan > kijun and price > cloud_t and color == 'bullish':
        sep = (price - cloud_t) / cloud_t if cloud_t > 0 else 0
        if sep < MIN_SEP_PCT:
            return None

        # Chikou confirmation (walk-forward): current price vs price 26 bars ago
        if use_chikou:
            if j < CLOUD_SHIFT:
                return None
            if closes[j] <= closes[j - CLOUD_SHIFT]:
                return None

        # TK cross in last 3 bars?
        tk_cross = False
        for k in range(1, min(4, j + 1)):
            t_prev = donchian_mid(highs, lows, TENKAN_PERIOD, j - k)
            k_prev = donchian_mid(highs, lows, KIJUN_PERIOD, j - k)
            if t_prev is not None and k_prev is not None and t_prev <= k_prev:
                tk_cross = True
                break

        return {
            'direction': 'LONG',
            'bar': j,
            'price': price,
            'tenkan': tenkan,
            'kijun': kijun,
            'cloud_top': cloud_t,
            'cloud_bot': cloud_b,
            'cloud_color': color,
            'separation_pct': round(sep * 100, 3),
            'tk_cross': tk_cross,
        }

    # ── SHORT ─────────────────────────────────────────────────────────
    if tenkan < kijun and price < cloud_b and color == 'bearish':
        sep = (cloud_b - price) / cloud_b if cloud_b > 0 else 0
        if sep < MIN_SEP_PCT:
            return None

        if use_chikou:
            if j < CLOUD_SHIFT:
                return None
            if closes[j] >= closes[j - CLOUD_SHIFT]:
                return None

        tk_cross = False
        for k in range(1, min(4, j + 1)):
            t_prev = donchian_mid(highs, lows, TENKAN_PERIOD, j - k)
            k_prev = donchian_mid(highs, lows, KIJUN_PERIOD, j - k)
            if t_prev is not None and k_prev is not None and t_prev >= k_prev:
                tk_cross = True
                break

        return {
            'direction': 'SHORT',
            'bar': j,
            'price': price,
            'tenkan': tenkan,
            'kijun': kijun,
            'cloud_top': cloud_t,
            'cloud_bot': cloud_b,
            'cloud_color': color,
            'separation_pct': round(sep * 100, 3),
            'tk_cross': tk_cross,
        }

    return None


# ═══════════════════════════════════════════════════════════════════════
# Data loading
# ═══════════════════════════════════════════════════════════════════════

def load_candles(token: str, limit: int) -> Tuple[list, list, list, list]:
    """Load 1h candles for a token. Returns (opens, highs, lows, closes) oldest-first."""
    conn = None
    try:
        conn = sqlite3.connect(CANDLES_DB, timeout=10)
        c = conn.cursor()
        c.execute("""
            SELECT open, high, low, close FROM candles_1h
            WHERE token = ? ORDER BY ts DESC LIMIT ?
        """, (token.upper(), limit))
        rows = c.fetchall()
        if not rows:
            return [], [], [], []
        rows.reverse()
        opens  = [r[0] for r in rows]
        highs  = [r[1] for r in rows]
        lows   = [r[2] for r in rows]
        closes = [r[3] for r in rows]
        return opens, highs, lows, closes
    except Exception as e:
        print(f"  Error loading {token}: {e}")
        return [], [], [], []
    finally:
        if conn:
            conn.close()


# ═══════════════════════════════════════════════════════════════════════
# Trade simulation
# ═══════════════════════════════════════════════════════════════════════

def simulate_trade(highs, lows, closes, entry_bar, direction):
    """
    Simulate a trade from entry_bar+1 (next bar's close).
    Exit conditions (in priority order checked each bar):
      1. Stop loss: -2%
      2. Take profit: +4%
      3. TK cross reversal
      4. Max hold: 48 bars
    Returns dict with trade results.
    """
    n = len(closes)
    entry_idx = entry_bar + 1
    if entry_idx >= n:
        return None

    entry_price = closes[entry_idx]
    if entry_price <= 0:
        return None

    exit_idx = None
    exit_reason = None

    for bar in range(entry_idx + 1, min(entry_idx + HOLD_BARS + 1, n)):
        current_price = closes[bar]
        raw_pnl = (current_price - entry_price) / entry_price
        # For SHORT trades, profit is when price drops (invert sign)
        pnl_pct = -raw_pnl if direction == 'SHORT' else raw_pnl

        # Check stop loss
        if pnl_pct <= STOP_LOSS_PCT:
            exit_idx = bar
            exit_reason = 'stop_loss'
            break

        # Check take profit
        if pnl_pct >= TAKE_PROFIT_PCT:
            exit_idx = bar
            exit_reason = 'take_profit'
            break

        # Check TK cross reversal
        ich = compute_ichimoku_at(highs, lows, closes, bar)
        if ich is not None:
            tenkan = ich['tenkan']
            kijun = ich['kijun']
            if tenkan is not None and kijun is not None:
                if direction == 'LONG' and tenkan < kijun:
                    exit_idx = bar
                    exit_reason = 'tk_cross'
                    break
                elif direction == 'SHORT' and tenkan > kijun:
                    exit_idx = bar
                    exit_reason = 'tk_cross'
                    break

    # If no exit triggered, exit at max hold
    if exit_idx is None:
        exit_idx = min(entry_idx + HOLD_BARS, n - 1)
        exit_reason = 'max_hold'

    exit_price = closes[exit_idx]
    raw_pnl = (exit_price - entry_price) / entry_price
    pnl_pct = -raw_pnl if direction == 'SHORT' else raw_pnl

    return {
        'entry_bar': entry_idx,
        'exit_bar': exit_idx,
        'entry_price': entry_price,
        'exit_price': exit_price,
        'pnl_pct': pnl_pct,
        'hold_bars': exit_idx - entry_idx,
        'exit_reason': exit_reason,
    }


# ═══════════════════════════════════════════════════════════════════════
# Backtest engine
# ═══════════════════════════════════════════════════════════════════════

def run_backtest(use_chikou=True):
    """Run the full backtest. Returns stats dict."""
    label = "WITH Chikou" if use_chikou else "WITHOUT Chikou"

    all_trades = {'LONG': [], 'SHORT': []}
    total_signals = 0

    # Minimum bars needed before we can start detecting
    min_start = SENKOU_B_PERIOD + CLOUD_SHIFT  # 52 + 26 = 78

    for token in TOKENS:
        opens, highs, lows, closes = load_candles(token, BARS + 50)  # extra buffer
        n = len(closes)
        if n < min_start + 100:
            print(f"  {token}: only {n} bars, skipping")
            continue

        # Use exactly BARS from the end
        if n > BARS:
            opens  = opens[-BARS:]
            highs  = highs[-BARS:]
            lows   = lows[-BARS:]
            closes = closes[-BARS:]
            n = BARS

        token_signals = 0

        # Walk forward from min_start to n-2 (need next bar for entry)
        for j in range(min_start, n - 1):
            sig = detect_at_bar(highs, lows, closes, j, use_chikou=use_chikou)
            if sig is None:
                continue

            # Skip if same direction signal already active (simple cooldown: 48 bars)
            direction = sig['direction']
            if all_trades[direction]:
                last_exit = all_trades[direction][-1]['exit_bar']
                if j - last_exit < 48:
                    continue

            trade = simulate_trade(highs, lows, closes, j, direction)
            if trade is None:
                continue

            trade['token'] = token
            trade['signal_bar'] = j
            trade['signal'] = sig
            all_trades[direction].append(trade)
            token_signals += 1
            total_signals += 1

        if token_signals > 0:
            print(f"  {token:8s}: {token_signals} signals")

    return compute_stats(all_trades, label)


def compute_stats(all_trades, label):
    """Compute aggregate stats from trade lists."""
    stats = {}
    for direction in ['LONG', 'SHORT']:
        trades = all_trades[direction]
        if not trades:
            stats[direction] = {
                'count': 0,
                'wins': 0,
                'losses': 0,
                'win_rate': 0,
                'avg_pnl': 0,
                'total_pnl': 0,
                'best_pnl': 0,
                'worst_pnl': 0,
                'avg_hold': 0,
                'exit_reasons': {},
            }
            continue

        pnls = [t['pnl_pct'] for t in trades]
        wins = sum(1 for p in pnls if p > 0)
        losses = len(pnls) - wins
        exit_reasons = {}
        for t in trades:
            r = t['exit_reason']
            exit_reasons[r] = exit_reasons.get(r, 0) + 1

        stats[direction] = {
            'count': len(trades),
            'wins': wins,
            'losses': losses,
            'win_rate': round(wins / len(trades) * 100, 1),
            'avg_pnl': round(sum(pnls) / len(pnls) * 100, 3),
            'total_pnl': round(sum(pnls) * 100, 3),
            'best_pnl': round(max(pnls) * 100, 3),
            'worst_pnl': round(min(pnls) * 100, 3),
            'avg_hold': round(sum(t['hold_bars'] for t in trades) / len(trades), 1),
            'exit_reasons': exit_reasons,
        }

    # Combined
    all_flat = all_trades['LONG'] + all_trades['SHORT']
    if all_flat:
        pnls = [t['pnl_pct'] for t in all_flat]
        wins = sum(1 for p in pnls if p > 0)
        stats['COMBINED'] = {
            'count': len(all_flat),
            'wins': wins,
            'losses': len(all_flat) - wins,
            'win_rate': round(wins / len(all_flat) * 100, 1),
            'avg_pnl': round(sum(pnls) / len(pnls) * 100, 3),
            'total_pnl': round(sum(pnls) * 100, 3),
            'best_pnl': round(max(pnls) * 100, 3),
            'worst_pnl': round(min(pnls) * 100, 3),
            'avg_hold': round(sum(t['hold_bars'] for t in all_flat) / len(all_flat), 1),
        }
    else:
        stats['COMBINED'] = {'count': 0}

    return stats


def print_stats(stats, label):
    """Pretty-print stats."""
    print(f"\n{'='*65}")
    print(f"  ICHIMOKU BACKTEST RESULTS — {label}")
    print(f"{'='*65}")
    print(f"  Parameters: Tenkan={TENKAN_PERIOD}, Kijun={KIJUN_PERIOD}, "
          f"SenkouB={SENKOU_B_PERIOD}, CloudShift={CLOUD_SHIFT}")
    print(f"  Entry: next bar close | Hold: {HOLD_BARS}h max | "
          f"SL: {STOP_LOSS_PCT*100:.0f}% | TP: {TAKE_PROFIT_PCT*100:.0f}%")
    print(f"  Tokens: {len(TOKENS)} | Data: {BARS} bars (90 days, 1h)")
    print(f"{'='*65}")

    for direction in ['LONG', 'SHORT', 'COMBINED']:
        s = stats[direction]
        if s['count'] == 0:
            print(f"\n  {direction}: No signals")
            continue

        print(f"\n  {direction}:")
        print(f"    Signals:    {s['count']}")
        print(f"    Wins:       {s['wins']}  |  Losses: {s['losses']}")
        print(f"    Win Rate:   {s['win_rate']}%")
        print(f"    Avg PnL:    {s['avg_pnl']:+.3f}%")
        print(f"    Total PnL:  {s['total_pnl']:+.3f}%")
        print(f"    Best:       {s['best_pnl']:+.3f}%")
        print(f"    Worst:      {s['worst_pnl']:+.3f}%")
        print(f"    Avg Hold:   {s['avg_hold']:.1f} bars")
        if 'exit_reasons' in s and s['exit_reasons']:
            reasons = s['exit_reasons']
            parts = [f"{k}: {v}" for k, v in sorted(reasons.items())]
            print(f"    Exits:      {', '.join(parts)}")

    print(f"\n{'='*65}")


# ═══════════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════════

if __name__ == '__main__':
    print("=" * 65)
    print("  ICHIMOKU CLOUD SIGNAL — WALK-FORWARD BACKTEST")
    print("=" * 65)
    print(f"  Tokens: {', '.join(TOKENS)}")
    print(f"  Data:   {BARS} bars of 1h candles (~90 days)")
    print(f"  SL: {STOP_LOSS_PCT*100:.0f}%  |  TP: {TAKE_PROFIT_PCT*100:.0f}%  |  Max hold: {HOLD_BARS}h")
    print()

    # Run WITH Chikou filter
    print("[1/2] Running backtest WITH Chikou filter...")
    stats_with = run_backtest(use_chikou=True)
    print_stats(stats_with, "WITH Chikou Filter")

    # Run WITHOUT Chikou filter
    print("\n[2/2] Running backtest WITHOUT Chikou filter...")
    stats_without = run_backtest(use_chikou=False)
    print_stats(stats_without, "WITHOUT Chikou Filter")

    # ── Comparison ────────────────────────────────────────────────────
    print(f"\n{'='*65}")
    print("  CHIKOU FILTER IMPACT COMPARISON")
    print(f"{'='*65}")
    for direction in ['LONG', 'SHORT', 'COMBINED']:
        w = stats_with[direction]
        wo = stats_without[direction]
        if w['count'] == 0 and wo['count'] == 0:
            print(f"\n  {direction}: No data")
            continue
        print(f"\n  {direction}:")
        print(f"    {'Metric':<16} {'With Chikou':>14} {'Without':>14} {'Delta':>14}")
        print(f"    {'-'*58}")
        if w['count'] > 0 and wo['count'] > 0:
            for metric, key in [('Signals', 'count'), ('Win Rate', 'win_rate'),
                                 ('Avg PnL', 'avg_pnl'), ('Total PnL', 'total_pnl')]:
                wv = w[key]
                wov = wo[key]
                delta = wv - wov
                print(f"    {metric:<16} {wv:>13} {wov:>13} {delta:>+13}")
        else:
            print(f"    With: {w['count']} signals | Without: {wo['count']} signals")

    print(f"\n{'='*65}")
    print("  Backtest complete.")
    print(f"{'='*65}")
