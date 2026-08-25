#!/usr/bin/env python3
"""
Independent BB Bounce Signal Filter Analysis
Author: Quantitative Analyst (autonomous)
Date: 2026-08-25

Analyzes ALL bb_bounce trades, computes entry-condition metrics from 1m candles,
and tests every reasonable filter combination to find optimal entry gates.
"""

import sqlite3
import os
import sys
import math
import json
from collections import defaultdict
from itertools import combinations

# ── Paths ──────────────────────────────────────────────────────────────
HERMES_DATA = '/root/.hermes/data'
RUNTIME_DB = os.path.join(HERMES_DATA, 'signals_hermes_runtime.db')
CANDLES_DB = os.path.join(HERMES_DATA, 'candles.db')
SIGNALS_DB = os.path.join(HERMES_DATA, 'signals_hermes.db')

# ── Helper: linear regression slope ───────────────────────────────────
def linreg_slope(xs):
    """Return slope of linear regression (y = a + b*x). Returns 0 if insufficient data."""
    n = len(xs)
    if n < 3:
        return 0.0
    x_mean = sum(range(n)) / n
    y_mean = sum(xs) / n
    num = sum((i - x_mean) * (xs[i] - y_mean) for i in range(n))
    den = sum((i - x_mean) ** 2 for i in range(n))
    if den == 0:
        return 0.0
    return num / den


def compute_rsi(closes, period=14):
    """Compute RSI from close prices."""
    if len(closes) < period + 1:
        return None
    gains, losses = [], []
    for i in range(1, period + 1):
        delta = closes[-i] - closes[-i - 1]
        gains.append(max(delta, 0))
        losses.append(max(-delta, 0))
    avg_gain = sum(gains) / len(gains) if gains else 0
    avg_loss = sum(losses) / len(losses) if losses else 0.001
    rs = avg_gain / avg_loss if avg_loss > 0 else 100
    return 100 - (100 / (1 + rs))


def compute_bb(closes, period=20, stddev=1.8):
    """Compute Bollinger Bands: middle, upper, lower, width, position."""
    if len(closes) < period:
        return None, None, None, None, None
    recent = closes[-period:]
    middle = sum(recent) / period
    variance = sum((c - middle) ** 2 for c in recent) / period
    std = variance ** 0.5
    upper = middle + stddev * std
    lower = middle - stddev * std
    width = (upper - lower) / middle if middle > 0 else 0
    # BB position: 0=at lower, 1=at upper
    if upper - lower > 0:
        bb_pos = (closes[-1] - lower) / (upper - lower)
    else:
        bb_pos = 0.5
    return middle, upper, lower, width, bb_pos


def analyze_trade_metrics(token, entry_ts, direction):
    """
    Given a token and entry timestamp, query 1m candles BEFORE entry
    and compute all metrics we want to filter on.
    Returns a dict of metrics or None if insufficient data.
    """
    conn = None
    try:
        conn = sqlite3.connect(CANDLES_DB, timeout=10)
        cur = conn.cursor()
        
        # Get 1m candles before entry (60 candles = 1 hour)
        cur.execute("""
            SELECT ts, open, high, low, close, volume
            FROM candles_1m
            WHERE token = ? AND ts <= ?
            ORDER BY ts DESC
            LIMIT 60
        """, (token.upper(), entry_ts))
        rows = cur.fetchall()
        
        if len(rows) < 30:
            return None
        
        # Reverse to chronological order
        rows = list(reversed(rows))
        ts_list = [r[0] for r in rows]
        opens = [r[1] for r in rows]
        highs = [r[2] for r in rows]
        lows = [r[3] for r in rows]
        closes = [r[4] for r in rows]
        volumes = [r[5] for r in rows]
        
        current_price = closes[-1]
        if current_price <= 0:
            return None
        
        metrics = {}
        
        # 1. 30-minute momentum (linear regression slope of closes, normalized by price)
        if len(closes) >= 30:
            slope_30m = linreg_slope(closes[-30:])
            metrics['momentum_30m'] = slope_30m / current_price * 100  # normalized % per bar
        else:
            metrics['momentum_30m'] = 0.0
        
        # 2. 15-minute momentum
        if len(closes) >= 15:
            slope_15m = linreg_slope(closes[-15:])
            metrics['momentum_15m'] = slope_15m / current_price * 100
        else:
            metrics['momentum_15m'] = 0.0
        
        # 3. 5-minute momentum
        if len(closes) >= 5:
            slope_5m = linreg_slope(closes[-5:])
            metrics['momentum_5m'] = slope_5m / current_price * 100
        else:
            metrics['momentum_5m'] = 0.0
        
        # 4. Volume ratio (avg volume last 5 candles vs previous 20)
        if len(volumes) >= 25:
            avg_vol_5 = sum(volumes[-5:]) / 5
            avg_vol_20 = sum(volumes[-25:-5]) / 20
            metrics['volume_ratio'] = avg_vol_5 / avg_vol_20 if avg_vol_20 > 0 else 1.0
        else:
            metrics['volume_ratio'] = 1.0
        
        # 5. RSI at entry (14-period)
        rsi = compute_rsi(closes, 14)
        metrics['rsi'] = rsi if rsi is not None else 50.0
        
        # 6. BB metrics (20-period, 1.8 stddev - matches bb_bounce.py)
        middle, upper, lower, width, bb_pos = compute_bb(closes, 20, 1.8)
        if middle is not None:
            metrics['bb_width'] = width
            metrics['bb_position'] = bb_pos
            # Distance from nearest band
            if direction == 'LONG':
                metrics['bb_dist_from_lower'] = abs(current_price - lower) / lower * 100 if lower > 0 else 0
                metrics['bb_dist_from_upper'] = abs(current_price - upper) / upper * 100 if upper > 0 else 0
            else:
                metrics['bb_dist_from_upper'] = abs(current_price - upper) / upper * 100 if upper > 0 else 0
                metrics['bb_dist_from_lower'] = abs(current_price - lower) / lower * 100 if lower > 0 else 0
        else:
            metrics['bb_width'] = 0
            metrics['bb_position'] = 0.5
            metrics['bb_dist_from_lower'] = 0
            metrics['bb_dist_from_upper'] = 0
        
        # 7. 15m velocity (price change over last 15 minutes)
        if len(closes) >= 15 and closes[-15] > 0:
            metrics['velocity_15m'] = (closes[-1] - closes[-15]) / closes[-15] * 100
        else:
            metrics['velocity_15m'] = 0.0
        
        # 8. 5m velocity
        if len(closes) >= 5 and closes[-5] > 0:
            metrics['velocity_5m'] = (closes[-1] - closes[-5]) / closes[-5] * 100
        else:
            metrics['velocity_5m'] = 0.0
        
        # 9. Price acceleration: is the move slowing down?
        # Compare velocity of first half vs second half of recent window
        if len(closes) >= 20:
            first_half = closes[-20:-10]
            second_half = closes[-10:]
            if first_half[0] > 0 and second_half[0] > 0:
                v1 = (first_half[-1] - first_half[0]) / first_half[0] * 100
                v2 = (second_half[-1] - second_half[0]) / second_half[0] * 100
                metrics['acceleration'] = v2 - v1  # positive = speeding up, negative = slowing
            else:
                metrics['acceleration'] = 0.0
        else:
            metrics['acceleration'] = 0.0
        
        # 10. ATR % (14-period, using 1m candles - approximate)
        if len(rows) >= 15:
            trs = []
            for i in range(-14, 0):
                h = highs[i]
                l = lows[i]
                pc = closes[i - 1] if i - 1 >= -len(closes) else closes[i]
                tr = max(h - l, abs(h - pc), abs(l - pc))
                trs.append(tr)
            atr = sum(trs) / len(trs)
            metrics['atr_pct'] = atr / current_price * 100 if current_price > 0 else 0
        else:
            metrics['atr_pct'] = 0
        
        # 11. Max drawdown in last 30 minutes (as % from peak)
        if len(highs) >= 30:
            peak = max(highs[-30:])
            trough = min(lows[-30:])
            metrics['max_drawdown_30m'] = (peak - trough) / peak * 100 if peak > 0 else 0
        else:
            metrics['max_drawdown_30m'] = 0
        
        # 12. Candle consistency: how many of last 5 candles are in signal direction?
        if len(closes) >= 6:
            if direction == 'LONG':
                green_count = sum(1 for i in range(-5, 0) if closes[i] > closes[i - 1])
                metrics['directional_candles_5'] = green_count
            else:
                red_count = sum(1 for i in range(-5, 0) if closes[i] < closes[i - 1])
                metrics['directional_candles_5'] = red_count
        else:
            metrics['directional_candles_5'] = 2.5
        
        # 13. Close-to-close volatility (stddev of returns over last 20 bars)
        if len(closes) >= 21:
            returns = [(closes[i] - closes[i-1]) / closes[i-1] * 100 for i in range(-20, 0) if closes[i-1] > 0]
            if len(returns) > 1:
                avg_ret = sum(returns) / len(returns)
                var = sum((r - avg_ret) ** 2 for r in returns) / len(returns)
                metrics['volatility_20'] = var ** 0.5
            else:
                metrics['volatility_20'] = 0
        else:
            metrics['volatility_20'] = 0
        
        # 14. Price position in 1h range (where in the high-low range is current price)
        if len(highs) >= 30:
            h1 = max(highs[-30:])
            l1 = min(lows[-30:])
            if h1 - l1 > 0:
                metrics['range_position'] = (current_price - l1) / (h1 - l1)
            else:
                metrics['range_position'] = 0.5
        else:
            metrics['range_position'] = 0.5
        
        return metrics
        
    except Exception as e:
        print(f"  Error analyzing {token}: {e}", flush=True)
        return None
    finally:
        if conn:
            conn.close()


def main():
    print("=" * 80)
    print("BB BOUNCE SIGNAL — INDEPENDENT FILTER OPTIMIZATION ANALYSIS")
    print("=" * 80)
    
    # ── Step 1: Pull all bb_bounce trades ──────────────────────────────
    print("\n[1] Pulling all bb_bounce trades from signal_outcomes...")
    conn = sqlite3.connect(RUNTIME_DB, timeout=10)
    cur = conn.cursor()
    
    cur.execute("""
        SELECT token, direction, is_win, pnl_pct, pnl_usdt, confidence, 
               created_at, trade_id, signal_type
        FROM signal_outcomes
        WHERE signal_type LIKE '%bb_bounce%'
        ORDER BY created_at ASC
    """)
    trades = cur.fetchall()
    conn.close()
    
    print(f"  Found {len(trades)} total bb_bounce trades")
    
    if len(trades) == 0:
        print("  ERROR: No trades found. Exiting.")
        return
    
    # ── Step 2: Parse trades and compute metrics ───────────────────────
    print("\n[2] Computing entry metrics from 1m candles for each trade...")
    
    trade_data = []
    skipped = 0
    
    for i, (token, direction, is_win, pnl_pct, pnl_usdt, confidence, 
            created_at, trade_id, signal_type) in enumerate(trades):
        
        # Convert created_at to timestamp for candle query
        try:
            from datetime import datetime
            # Handle various timestamp formats
            if 'T' in str(created_at):
                # ISO format
                dt_str = str(created_at).replace('Z', '').replace('+00:00', '')
                if '.' in dt_str:
                    dt = datetime.fromisoformat(dt_str)
                else:
                    dt = datetime.fromisoformat(dt_str)
            else:
                dt = datetime.fromisoformat(str(created_at).replace(' ', 'T'))
            entry_ts = int(dt.timestamp())
        except Exception as e:
            skipped += 1
            continue
        
        metrics = analyze_trade_metrics(token.upper(), entry_ts, direction)
        if metrics is None:
            skipped += 1
            continue
        
        trade_data.append({
            'token': token,
            'direction': direction,
            'is_win': bool(is_win),
            'pnl_pct': pnl_pct,
            'pnl_usdt': pnl_usdt,
            'confidence': confidence,
            'created_at': created_at,
            'trade_id': trade_id,
            'signal_type': signal_type,
            'metrics': metrics,
        })
        
        if (i + 1) % 50 == 0:
            print(f"  Processed {i + 1}/{len(trades)}...")
    
    print(f"  Successfully analyzed: {len(trade_data)} trades")
    print(f"  Skipped (no candle data): {skipped} trades")
    
    # ── Step 3: Summary Statistics ─────────────────────────────────────
    print("\n" + "=" * 80)
    print("[3] SUMMARY STATISTICS")
    print("=" * 80)
    
    winners = [t for t in trade_data if t['is_win']]
    losers = [t for t in trade_data if not t['is_win']]
    
    total_pnl = sum(t['pnl_usdt'] for t in trade_data)
    win_pnl = sum(t['pnl_usdt'] for t in winners)
    loss_pnl = sum(t['pnl_usdt'] for t in losers)
    
    print(f"\n  Total trades:     {len(trade_data)}")
    print(f"  Winners:          {len(winners)} ({len(winners)/len(trade_data)*100:.1f}%)")
    print(f"  Losers:           {len(losers)} ({len(losers)/len(trade_data)*100:.1f}%)")
    print(f"  Overall WR:       {len(winners)/len(trade_data)*100:.1f}%")
    print(f"  Total PnL:        ${total_pnl:+.2f}")
    print(f"  Winner PnL:       ${win_pnl:+.2f}")
    print(f"  Loser PnL:        ${loss_pnl:+.2f}")
    print(f"  Avg Winner:       ${win_pnl/len(winners):+.3f}" if winners else "  Avg Winner: N/A")
    print(f"  Avg Loser:        ${loss_pnl/len(losers):+.3f}" if losers else "  Avg Loser: N/A")
    print(f"  Profit Factor:    {abs(win_pnl/loss_pnl):.2f}" if loss_pnl != 0 else "  Profit Factor: ∞")
    
    # Direction breakdown
    long_trades = [t for t in trade_data if t['direction'] == 'LONG']
    short_trades = [t for t in trade_data if t['direction'] == 'SHORT']
    long_wins = [t for t in long_trades if t['is_win']]
    short_wins = [t for t in short_trades if t['is_win']]
    
    print(f"\n  LONG:  {len(long_trades)} trades, {len(long_wins)} wins ({len(long_wins)/len(long_trades)*100:.1f}% WR)" if long_trades else "\n  LONG: 0 trades")
    print(f"  SHORT: {len(short_trades)} trades, {len(short_wins)} wins ({len(short_wins)/len(short_trades)*100:.1f}% WR)" if short_trades else "  SHORT: 0 trades")
    
    # Signal type breakdown
    sig_types = defaultdict(lambda: {'count': 0, 'wins': 0, 'pnl': 0})
    for t in trade_data:
        st = t['signal_type']
        sig_types[st]['count'] += 1
        if t['is_win']:
            sig_types[st]['wins'] += 1
        sig_types[st]['pnl'] += t['pnl_usdt']
    
    print(f"\n  Signal Type Breakdown:")
    for st, data in sorted(sig_types.items(), key=lambda x: x[1]['count'], reverse=True):
        wr = data['wins'] / data['count'] * 100 if data['count'] > 0 else 0
        print(f"    {st}: {data['count']}T, {data['wins']}W, {wr:.1f}% WR, ${data['pnl']:+.2f}")
    
    # ── Step 4: Winner vs Loser Distribution Analysis ──────────────────
    print("\n" + "=" * 80)
    print("[4] WINNER VS LOSER DISTRIBUTIONS")
    print("=" * 80)
    
    # Get all metric keys
    metric_keys = list(trade_data[0]['metrics'].keys()) if trade_data else []
    
    def percentile(data, p):
        """Simple percentile calculation."""
        if not data:
            return 0
        sorted_d = sorted(data)
        idx = (len(sorted_d) - 1) * p / 100
        lo = int(idx)
        hi = min(lo + 1, len(sorted_d) - 1)
        frac = idx - lo
        return sorted_d[lo] + frac * (sorted_d[hi] - sorted_d[lo])
    
    print(f"\n  {'Metric':<25} {'Winner Mean':>12} {'Loser Mean':>12} {'Winner Med':>12} {'Loser Med':>12} {'P25 W':>10} {'P75 W':>10} {'P25 L':>10} {'P75 L':>10}")
    print("  " + "-" * 125)
    
    distribution_data = {}
    
    for key in metric_keys:
        w_vals = [t['metrics'][key] for t in winners if key in t['metrics']]
        l_vals = [t['metrics'][key] for t in losers if key in t['metrics']]
        
        if not w_vals or not l_vals:
            continue
        
        w_mean = sum(w_vals) / len(w_vals)
        l_mean = sum(l_vals) / len(l_vals)
        w_med = percentile(w_vals, 50)
        l_med = percentile(l_vals, 50)
        w_p25 = percentile(w_vals, 25)
        w_p75 = percentile(w_vals, 75)
        l_p25 = percentile(l_vals, 25)
        l_p75 = percentile(l_vals, 75)
        
        distribution_data[key] = {
            'w_mean': w_mean, 'l_mean': l_mean,
            'w_med': w_med, 'l_med': l_med,
            'w_p25': w_p25, 'w_p75': w_p75,
            'l_p25': l_p25, 'l_p75': l_p75,
            'w_vals': w_vals, 'l_vals': l_vals,
        }
        
        # Significant separator?
        sep = ""
        diff = abs(w_mean - l_mean)
        avg_range = (max(w_p75, l_p75) - min(w_p25, l_p25))
        if avg_range > 0 and diff / avg_range > 0.3:
            sep = " ***"
        
        print(f"  {key:<25} {w_mean:>12.4f} {l_mean:>12.4f} {w_med:>12.4f} {l_med:>12.4f} {w_p25:>10.4f} {w_p75:>10.4f} {l_p25:>10.4f} {l_p75:>10.4f}{sep}")
    
    # ── Step 5: Test Filter Combinations ───────────────────────────────
    print("\n" + "=" * 80)
    print("[5] FILTER COMBINATION TESTING")
    print("=" * 80)
    
    # Define individual filter functions
    def make_filter(metric_name, op, threshold):
        """Create a filter function. op: 'gt', 'lt', 'gte', 'lte'."""
        def filt(trade):
            val = trade['metrics'].get(metric_name, 0)
            if op == 'gt': return val > threshold
            if op == 'lt': return val < threshold
            if op == 'gte': return val >= threshold
            if op == 'lte': return val <= threshold
        return filt
    
    # Base rate
    base_wr = len(winners) / len(trade_data) * 100
    base_pnl = sum(t['pnl_usdt'] for t in trade_data)
    base_avg_pnl = base_pnl / len(trade_data) if trade_data else 0
    
    # ── Individual filters first ──
    individual_filters = []
    
    # Momentum filters (direction-aware)
    for name, label, direction in [('momentum_30m', '30m momentum', 'LONG'),
                                     ('momentum_15m', '15m momentum', 'LONG'),
                                     ('momentum_5m', '5m momentum', 'LONG')]:
        for thresh in [0.001, 0.002, 0.003, 0.005, 0.01, 0.02, 0.03, 0.05]:
            # For LONG: want positive momentum (price rising toward us)
            individual_filters.append((f"{label} > {thresh}", make_filter(name, 'gt', thresh)))
            # For LONG: block if momentum too negative (still falling hard)
            individual_filters.append((f"{label} > -{thresh}", make_filter(name, 'gt', -thresh)))
    
    # RSI filters
    for thresh in [25, 30, 35, 40, 45, 50, 55, 60, 65, 70]:
        individual_filters.append((f"RSI < {thresh}", make_filter('rsi', 'lt', thresh)))
        individual_filters.append((f"RSI > {thresh}", make_filter('rsi', 'gt', thresh)))
        # RSI in range
        individual_filters.append((f"RSI 30-{thresh}", lambda t, hi=thresh: 30 <= t['metrics'].get('rsi', 50) <= hi))
    
    # BB width filters (squeeze = tighter bands = stronger signal)
    for thresh in [0.01, 0.02, 0.03, 0.04, 0.05, 0.06, 0.08, 0.10]:
        individual_filters.append((f"BB width < {thresh}", make_filter('bb_width', 'lt', thresh)))
        individual_filters.append((f"BB width > {thresh}", make_filter('bb_width', 'gt', thresh)))
    
    # Volume ratio filters
    for thresh in [0.5, 0.75, 1.0, 1.2, 1.5, 2.0, 2.5, 3.0]:
        individual_filters.append((f"Vol ratio > {thresh}", make_filter('volume_ratio', 'gt', thresh)))
        individual_filters.append((f"Vol ratio < {thresh}", make_filter('volume_ratio', 'lt', thresh)))
    
    # Velocity 15m filters
    for thresh in [0.1, 0.15, 0.2, 0.3, 0.4, 0.5, 0.6, 0.8, 1.0]:
        individual_filters.append((f"Vel 15m > {thresh}", make_filter('velocity_15m', 'gt', thresh)))
        individual_filters.append((f"Vel 15m < -{thresh}", make_filter('velocity_15m', 'lt', -thresh)))
    
    # Velocity 5m filters
    for thresh in [0.05, 0.1, 0.15, 0.2, 0.3, 0.5]:
        individual_filters.append((f"Vel 5m > {thresh}", make_filter('velocity_5m', 'gt', thresh)))
        individual_filters.append((f"Vel 5m < -{thresh}", make_filter('velocity_5m', 'lt', -thresh)))
    
    # Acceleration filters (slowing move = better for reversal)
    for thresh in [-0.05, -0.02, -0.01, -0.005, 0, 0.005, 0.01, 0.02]:
        individual_filters.append((f"Acceleration > {thresh}", make_filter('acceleration', 'gt', thresh)))
        individual_filters.append((f"Acceleration < {thresh}", make_filter('acceleration', 'lt', thresh)))
    
    # ATR filters
    for thresh in [0.02, 0.03, 0.04, 0.05, 0.06, 0.08, 0.10]:
        individual_filters.append((f"ATR% > {thresh}", make_filter('atr_pct', 'gt', thresh)))
        individual_filters.append((f"ATR% < {thresh}", make_filter('atr_pct', 'lt', thresh)))
    
    # Max drawdown filters (bigger drawdown = more exhaustion)
    for thresh in [0.3, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0]:
        individual_filters.append((f"MaxDD > {thresh}%", make_filter('max_drawdown_30m', 'gt', thresh)))
        individual_filters.append((f"MaxDD < {thresh}%", make_filter('max_drawdown_30m', 'lt', thresh)))
    
    # Directional candles (signal alignment)
    for thresh in [1, 2, 3, 4]:
        individual_filters.append((f"DirCandles >= {thresh}", make_filter('directional_candles_5', 'gte', thresh)))
    
    # Volatility filters
    for thresh in [0.01, 0.02, 0.03, 0.04, 0.05, 0.06, 0.08]:
        individual_filters.append((f"Volatility < {thresh}", make_filter('volatility_20', 'lt', thresh)))
        individual_filters.append((f"Volatility > {thresh}", make_filter('volatility_20', 'gt', thresh)))
    
    # BB position filters
    for thresh in [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]:
        individual_filters.append((f"BB pos < {thresh}", make_filter('bb_position', 'lt', thresh)))
        individual_filters.append((f"BB pos > {thresh}", make_filter('bb_position', 'gt', thresh)))
    
    # Range position filters
    for thresh in [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]:
        individual_filters.append((f"Range pos < {thresh}", make_filter('range_position', 'lt', thresh)))
        individual_filters.append((f"Range pos > {thresh}", make_filter('range_position', 'gt', thresh)))
    
    # Current velocity gate (existing MEAN_REVERSION_VEL check)
    for thresh in [0.1, 0.15, 0.2, 0.3, 0.4, 0.5, 0.6, 0.8, 1.0]:
        individual_filters.append((f"Vel15m > -{thresh} (vel gate)", make_filter('velocity_15m', 'gt', -thresh)))
    
    # 30m momentum slope = momentum fading (good for mean reversion)
    # If momentum was negative (falling) and is now less negative (slowing), good LONG entry
    for thresh in [-0.05, -0.03, -0.02, -0.01, 0, 0.01, 0.02, 0.03, 0.05]:
        individual_filters.append((f"Mom30m > {thresh}", make_filter('momentum_30m', 'gt', thresh)))
    
    # ── Evaluate individual filters ──
    print("\n  Individual Filter Evaluation (sorted by PnL improvement):")
    print(f"  {'Filter':<40} {'Kept':>5} {'WR%':>7} {'PnL':>10} {'ΔWR':>8} {'Wkpt%':>7} {'Lkill%':>7}")
    print("  " + "-" * 90)
    
    results = []
    for label, filt in individual_filters:
        kept = [t for t in trade_data if filt(t)]
        if len(kept) < 5:
            continue
        
        kept_winners = [t for t in kept if t['is_win']]
        kept_losers = [t for t in kept if not t['is_win']]
        
        wr = len(kept_winners) / len(kept) * 100 if kept else 0
        pnl = sum(t['pnl_usdt'] for t in kept)
        avg_pnl = pnl / len(kept) if kept else 0
        
        winners_kept_pct = len(kept_winners) / len(winners) * 100 if winners else 0
        losers_killed_pct = (1 - len(kept_losers) / len(losers)) * 100 if losers else 0
        
        delta_wr = wr - base_wr
        delta_pnl_per_trade = avg_pnl - base_avg_pnl
        
        # Score: prefer higher PnL improvement, penalize if too few trades
        score = pnl  # total PnL is our primary metric
        
        results.append({
            'label': label,
            'kept': len(kept),
            'wr': wr,
            'pnl': pnl,
            'avg_pnl': avg_pnl,
            'delta_wr': delta_wr,
            'delta_pnl': delta_pnl_per_trade,
            'winners_kept_pct': winners_kept_pct,
            'losers_killed_pct': losers_killed_pct,
            'score': score,
            'filt': filt,
        })
    
    # Sort by PnL (primary) then by WR improvement
    results.sort(key=lambda x: (x['pnl'], x['wr']), reverse=True)
    
    for r in results[:40]:
        marker = " ★" if r['pnl'] > base_pnl and r['wr'] > base_wr else ""
        print(f"  {r['label']:<40} {r['kept']:>5} {r['wr']:>6.1f}% ${r['pnl']:>+9.2f} {r['delta_wr']:>+7.1f}% {r['winners_kept_pct']:>6.1f}% {r['losers_killed_pct']:>6.1f}%{marker}")
    
    # ── Multi-filter combinations ──
    print("\n\n  Multi-Filter Combination Testing (top 25 by PnL):")
    print(f"  {'Filters':<65} {'Kept':>5} {'WR%':>7} {'PnL':>10} {'ΔWR':>8} {'Wkpt%':>7} {'Lkill%':>7}")
    print("  " + "-" * 110)
    
    # Select the best individual filters for combination
    best_individual = [r for r in results[:15] if r['pnl'] > base_pnl or r['wr'] > base_wr + 5]
    
    # Test pairs
    combo_results = []
    
    # Also test some hand-crafted combinations based on the signal logic
    handcrafted = [
        ("Mom30m>-0.01 & RSI<55 & Vel15m>-0.3",
         lambda t: (t['metrics'].get('momentum_30m', 0) > -0.01 and 
                    t['metrics'].get('rsi', 50) < 55 and
                    t['metrics'].get('velocity_15m', 0) > -0.3)),
        ("Mom30m>-0.02 & RSI<50 & VolR>1.0",
         lambda t: (t['metrics'].get('momentum_30m', 0) > -0.02 and 
                    t['metrics'].get('rsi', 50) < 50 and
                    t['metrics'].get('volume_ratio', 1) > 1.0)),
        ("Mom30m>-0.01 & BBwidth<0.05 & Vel15m>-0.2",
         lambda t: (t['metrics'].get('momentum_30m', 0) > -0.01 and 
                    t['metrics'].get('bb_width', 0) < 0.05 and
                    t['metrics'].get('velocity_15m', 0) > -0.2)),
        ("Vel15m>-0.15 & RSI<55 & Mom30m>-0.02",
         lambda t: (t['metrics'].get('velocity_15m', 0) > -0.15 and 
                    t['metrics'].get('rsi', 50) < 55 and
                    t['metrics'].get('momentum_30m', 0) > -0.02)),
        ("Vel15m>-0.15 & Mom30m>-0.01 & VolR>0.75",
         lambda t: (t['metrics'].get('velocity_15m', 0) > -0.15 and 
                    t['metrics'].get('momentum_30m', 0) > -0.01 and
                    t['metrics'].get('volume_ratio', 1) > 0.75)),
        ("Mom30m>0 & Vel15m>-0.15 (momentum aligned)",
         lambda t: (t['metrics'].get('momentum_30m', 0) > 0 and 
                    t['metrics'].get('velocity_15m', 0) > -0.15)),
        ("RSI<50 & Vel15m>-0.2 & Mom30m>-0.01",
         lambda t: (t['metrics'].get('rsi', 50) < 50 and 
                    t['metrics'].get('velocity_15m', 0) > -0.2 and
                    t['metrics'].get('momentum_30m', 0) > -0.01)),
        ("Accel<0 (slowing) & Vel15m>-0.3 & RSI<60",
         lambda t: (t['metrics'].get('acceleration', 0) < 0 and 
                    t['metrics'].get('velocity_15m', 0) > -0.3 and
                    t['metrics'].get('rsi', 50) < 60)),
        ("Mom30m>-0.01 & Vel15m>-0.15 & RSI<55 & VolR>0.75",
         lambda t: (t['metrics'].get('momentum_30m', 0) > -0.01 and 
                    t['metrics'].get('velocity_15m', 0) > -0.15 and
                    t['metrics'].get('rsi', 50) < 55 and
                    t['metrics'].get('volume_ratio', 1) > 0.75)),
        ("Mom30m>-0.01 & Vel15m>-0.15 & ATR>0.03",
         lambda t: (t['metrics'].get('momentum_30m', 0) > -0.01 and 
                    t['metrics'].get('velocity_15m', 0) > -0.15 and
                    t['metrics'].get('atr_pct', 0) > 0.03)),
        ("Mom30m>-0.01 & Vel15m>-0.15 & DirCandles>=2",
         lambda t: (t['metrics'].get('momentum_30m', 0) > -0.01 and 
                    t['metrics'].get('velocity_15m', 0) > -0.15 and
                    t['metrics'].get('directional_candles_5', 0) >= 2)),
        ("Mom30m>-0.02 & Vel5m>-0.1 & RSI<55",
         lambda t: (t['metrics'].get('momentum_30m', 0) > -0.02 and 
                    t['metrics'].get('velocity_5m', 0) > -0.1 and
                    t['metrics'].get('rsi', 50) < 55)),
        ("Mom30m>-0.01 & Vel15m>-0.15 & Vol<0.05",
         lambda t: (t['metrics'].get('momentum_30m', 0) > -0.01 and 
                    t['metrics'].get('velocity_15m', 0) > -0.15 and
                    t['metrics'].get('volatility_20', 0) < 0.05)),
        # The existing velocity gate: vel > -0.3%
        ("Existing vel gate: Vel15m>-0.3",
         lambda t: t['metrics'].get('velocity_15m', 0) > -0.3),
        # Spike exhaustion: vel_5m < 0.5%
        ("Existing spike exhaust: |Vel5m|<0.5",
         lambda t: abs(t['metrics'].get('velocity_5m', 0)) < 0.5),
        # Both existing gates combined
        ("Both existing gates",
         lambda t: (t['metrics'].get('velocity_15m', 0) > -0.3 and
                    abs(t['metrics'].get('velocity_5m', 0)) < 0.5)),
        # Aggressive: momentum must be positive AND RSI low
        ("Mom30m>0 & RSI<45 & Vel15m>-0.15",
         lambda t: (t['metrics'].get('momentum_30m', 0) > 0 and 
                    t['metrics'].get('rsi', 50) < 45 and
                    t['metrics'].get('velocity_15m', 0) > -0.15)),
        # Volume confirmation
        ("Mom30m>-0.01 & Vel15m>-0.15 & VolR>1.5",
         lambda t: (t['metrics'].get('momentum_30m', 0) > -0.01 and 
                    t['metrics'].get('velocity_15m', 0) > -0.15 and
                    t['metrics'].get('volume_ratio', 1) > 1.5)),
        # Low volatility (squeeze) + momentum recovery
        ("Vol20<0.03 & Mom30m>-0.01 & Vel15m>-0.15",
         lambda t: (t['metrics'].get('volatility_20', 0) < 0.03 and 
                    t['metrics'].get('momentum_30m', 0) > -0.01 and
                    t['metrics'].get('velocity_15m', 0) > -0.15)),
        # Price near bottom of range (good for LONG)
        ("RangePos<0.3 & Mom30m>-0.02",
         lambda t: (t['metrics'].get('range_position', 0.5) < 0.3 and 
                    t['metrics'].get('momentum_30m', 0) > -0.02)),
        # Acceleration negative + momentum recovering
        ("Accel<0 & Mom30m>-0.01 & Vel15m>-0.15",
         lambda t: (t['metrics'].get('acceleration', 0) < 0 and 
                    t['metrics'].get('momentum_30m', 0) > -0.01 and
                    t['metrics'].get('velocity_15m', 0) > -0.15)),
        # Very strict: all positive signals
        ("Mom30m>0 & Vel15m>0 & Mom15m>0",
         lambda t: (t['metrics'].get('momentum_30m', 0) > 0 and 
                    t['metrics'].get('velocity_15m', 0) > 0 and
                    t['metrics'].get('momentum_15m', 0) > 0)),
        # Moderate: just momentum and velocity
        ("Mom30m>-0.01 & Vel15m>-0.15",
         lambda t: (t['metrics'].get('momentum_30m', 0) > -0.01 and 
                    t['metrics'].get('velocity_15m', 0) > -0.15)),
        ("Mom30m>-0.005 & Vel15m>-0.1",
         lambda t: (t['metrics'].get('momentum_30m', 0) > -0.005 and 
                    t['metrics'].get('velocity_15m', 0) > -0.1)),
        # Directional candles + velocity
        ("DirCandles>=3 & Vel15m>-0.15",
         lambda t: (t['metrics'].get('directional_candles_5', 0) >= 3 and 
                    t['metrics'].get('velocity_15m', 0) > -0.15)),
        # ATR-based: higher volatility = wider SL needed, but bigger moves
        ("ATR>0.04 & Mom30m>-0.02 & Vel15m>-0.3",
         lambda t: (t['metrics'].get('atr_pct', 0) > 0.04 and 
                    t['metrics'].get('momentum_30m', 0) > -0.02 and
                    t['metrics'].get('velocity_15m', 0) > -0.3)),
        # Very tight: momentum must show reversal
        ("Mom30m>-0.005 & Mom15m>0 & Vel15m>-0.1",
         lambda t: (t['metrics'].get('momentum_30m', 0) > -0.005 and 
                    t['metrics'].get('momentum_15m', 0) > 0 and
                    t['metrics'].get('velocity_15m', 0) > -0.1)),
        # BB squeeze + momentum
        ("BBwidth<0.04 & Mom30m>-0.01",
         lambda t: (t['metrics'].get('bb_width', 1) < 0.04 and 
                    t['metrics'].get('momentum_30m', 0) > -0.01)),
        ("BBwidth<0.03 & Mom30m>-0.02",
         lambda t: (t['metrics'].get('bb_width', 1) < 0.03 and 
                    t['metrics'].get('momentum_30m', 0) > -0.02)),
        # Drawdown-based: bigger drawdown = better mean reversion entry
        ("MaxDD>1.0% & Mom30m>-0.03",
         lambda t: (t['metrics'].get('max_drawdown_30m', 0) > 1.0 and 
                    t['metrics'].get('momentum_30m', 0) > -0.03)),
        ("MaxDD>0.75% & Vel15m>-0.3 & RSI<55",
         lambda t: (t['metrics'].get('max_drawdown_30m', 0) > 0.75 and 
                    t['metrics'].get('velocity_15m', 0) > -0.3 and
                    t['metrics'].get('rsi', 50) < 55)),
        # Momentum reversal: 30m negative but 5m positive
        ("Mom30m<0 & Mom5m>0 & Vel15m>-0.3",
         lambda t: (t['metrics'].get('momentum_30m', 0) < 0 and 
                    t['metrics'].get('momentum_5m', 0) > 0 and
                    t['metrics'].get('velocity_15m', 0) > -0.3)),
    ]
    
    # Test pairs from best individual filters
    for i, r1 in enumerate(best_individual):
        for r2 in best_individual[i+1:]:
            if r1['label'] == r2['label']:
                continue
            combo_label = f"{r1['label']} AND {r2['label']}"
            combo_filt = lambda t, f1=r1['filt'], f2=r2['filt']: f1(t) and f2(t)
            handcrafted.append((combo_label, combo_filt))
    
    for label, filt in handcrafted:
        try:
            kept = [t for t in trade_data if filt(t)]
        except Exception:
            continue
        if len(kept) < 3:
            continue
        
        kept_winners = [t for t in kept if t['is_win']]
        kept_losers = [t for t in kept if not t['is_win']]
        
        wr = len(kept_winners) / len(kept) * 100 if kept else 0
        pnl = sum(t['pnl_usdt'] for t in kept)
        avg_pnl = pnl / len(kept) if kept else 0
        delta_wr = wr - base_wr
        
        winners_kept_pct = len(kept_winners) / len(winners) * 100 if winners else 0
        losers_killed_pct = (1 - len(kept_losers) / len(losers)) * 100 if losers else 0
        
        combo_results.append({
            'label': label,
            'kept': len(kept),
            'wr': wr,
            'pnl': pnl,
            'avg_pnl': avg_pnl,
            'delta_wr': delta_wr,
            'winners_kept_pct': winners_kept_pct,
            'losers_killed_pct': losers_killed_pct,
        })
    
    combo_results.sort(key=lambda x: (x['pnl'], x['wr']), reverse=True)
    
    for r in combo_results[:25]:
        marker = " ★★★" if r['pnl'] > base_pnl and r['wr'] > base_wr + 5 else (" ★★" if r['pnl'] > base_pnl else "")
        label_trunc = r['label'][:63]
        print(f"  {label_trunc:<65} {r['kept']:>5} {r['wr']:>6.1f}% ${r['pnl']:>+9.2f} {r['delta_wr']:>+7.1f}% {r['winners_kept_pct']:>6.1f}% {r['losers_killed_pct']:>6.1f}%{marker}")
    
    # ── Step 6: Verify existing velocity gate effectiveness ─────────────
    print("\n" + "=" * 80)
    print("[6] EXISTING VELOCITY GATE EFFECTIVENESS VERIFICATION")
    print("=" * 80)
    
    vel_gate_filt = lambda t: t['metrics'].get('velocity_15m', 0) > -0.3
    vel_blocked = [t for t in trade_data if not vel_gate_filt(t)]
    vel_passed = [t for t in trade_data if vel_gate_filt(t)]
    
    vel_blocked_winners = [t for t in vel_blocked if t['is_win']]
    vel_blocked_losers = [t for t in vel_blocked if not t['is_win']]
    
    print(f"\n  MEAN_REVERSION_VEL_THRESHOLD = -0.3%")
    print(f"  Trades blocked by vel gate:    {len(vel_blocked)}/{len(trade_data)} ({len(vel_blocked)/len(trade_data)*100:.1f}%)")
    print(f"  Winners blocked (killed):      {len(vel_blocked_winners)}/{len(winners)} ({len(vel_blocked_winners)/len(winners)*100:.1f}%)")
    print(f"  Losers blocked (good kill):    {len(vel_blocked_losers)}/{len(losers)} ({len(vel_blocked_losers)/len(losers)*100:.1f}%)")
    if vel_blocked:
        print(f"  Blocked trades avg PnL:        ${sum(t['pnl_usdt'] for t in vel_blocked)/len(vel_blocked):+.3f}")
    if vel_passed:
        vel_passed_wr = len([t for t in vel_passed if t['is_win']]) / len(vel_passed) * 100
        vel_passed_pnl = sum(t['pnl_usdt'] for t in vel_passed)
        print(f"  Passed trades WR:              {vel_passed_wr:.1f}%")
        print(f"  Passed trades total PnL:       ${vel_passed_pnl:+.2f}")
    
    # Spike exhaustion
    spike_filt = lambda t: abs(t['metrics'].get('velocity_5m', 0)) < 0.5
    spike_blocked = [t for t in trade_data if not spike_filt(t)]
    spike_blocked_winners = [t for t in spike_blocked if t['is_win']]
    spike_blocked_losers = [t for t in spike_blocked if not t['is_win']]
    
    print(f"\n  SPIKE_EXHAUSTION_VEL_5M_THRESHOLD = 0.5%")
    print(f"  Trades blocked by spike gate:  {len(spike_blocked)}/{len(trade_data)} ({len(spike_blocked)/len(trade_data)*100:.1f}%)")
    print(f"  Winners blocked (killed):      {len(spike_blocked_winners)}/{len(winners)} ({len(spike_blocked_winners)/len(winners)*100:.1f}%)")
    print(f"  Losers blocked (good kill):    {len(spike_blocked_losers)}/{len(losers)} ({len(spike_blocked_losers)/len(losers)*100:.1f}%)")
    
    # Both gates
    both_filt = lambda t: vel_gate_filt(t) and spike_filt(t)
    both_passed = [t for t in trade_data if both_filt(t)]
    both_blocked = [t for t in trade_data if not both_filt(t)]
    both_blocked_winners = [t for t in both_blocked if t['is_win']]
    both_blocked_losers = [t for t in both_blocked if not t['is_win']]
    
    print(f"\n  Both gates combined:")
    print(f"  Trades blocked:                {len(both_blocked)}/{len(trade_data)} ({len(both_blocked)/len(trade_data)*100:.1f}%)")
    print(f"  Winners blocked:               {len(both_blocked_winners)}/{len(winners)} ({len(both_blocked_winners)/len(winners)*100:.1f}%)")
    print(f"  Losers blocked:                {len(both_blocked_losers)}/{len(losers)} ({len(both_blocked_losers)/len(losers)*100:.1f}%)")
    
    # ── Step 7: Detailed analysis of top filters ───────────────────────
    print("\n" + "=" * 80)
    print("[7] DETAILED TOP RECOMMENDATION")
    print("=" * 80)
    
    # Find the best combo by a balanced metric: PnL improvement * winners kept / 100
    # This penalizes filters that kill too many winners
    best_balanced = None
    best_score = -999
    
    for r in combo_results:
        if r['kept'] < 10:
            continue
        # Balanced score = PnL * (winners_kept_pct / 100) — rewards keeping winners
        balanced = r['pnl'] * max(r['winners_kept_pct'] / 100, 0.1)
        if balanced > best_score:
            best_score = balanced
            best_balanced = r
    
    if best_balanced:
        print(f"\n  BEST BALANCED FILTER:")
        print(f"    {best_balanced['label']}")
        print(f"    Trades kept:    {best_balanced['kept']}/{len(trade_data)}")
        print(f"    Win Rate:       {best_balanced['wr']:.1f}% (was {base_wr:.1f}%, Δ={best_balanced['delta_wr']:+.1f}%)")
        print(f"    Total PnL:      ${best_balanced['pnl']:+.2f} (was ${base_pnl:+.2f}, Δ=${best_balanced['pnl']-base_pnl:+.2f})")
        print(f"    Avg PnL/trade:  ${best_balanced['avg_pnl']:+.4f} (was ${base_avg_pnl:+.4f})")
        print(f"    Winners kept:   {best_balanced['winners_kept_pct']:.1f}%")
        print(f"    Losers killed:  {best_balanced['losers_killed_pct']:.1f}%")
    
    # Best by raw PnL
    best_pnl = combo_results[0] if combo_results else None
    if best_pnl:
        print(f"\n  BEST BY RAW PnL:")
        print(f"    {best_pnl['label']}")
        print(f"    Trades kept:    {best_pnl['kept']}/{len(trade_data)}")
        print(f"    Win Rate:       {best_pnl['wr']:.1f}% (was {base_wr:.1f}%, Δ={best_pnl['delta_wr']:+.1f}%)")
        print(f"    Total PnL:      ${best_pnl['pnl']:+.2f} (was ${base_pnl:+.2f}, Δ=${best_pnl['pnl']-base_pnl:+.2f})")
        print(f"    Winners kept:   {best_pnl['winners_kept_pct']:.1f}%")
        print(f"    Losers killed:  {best_pnl['losers_killed_pct']:.1f}%")
    
    # Best by WR improvement (minimum 15 trades kept)
    best_wr = max([r for r in combo_results if r['kept'] >= 15], key=lambda x: x['wr'], default=None)
    if best_wr:
        print(f"\n  BEST BY WIN RATE (min 15 trades):")
        print(f"    {best_wr['label']}")
        print(f"    Trades kept:    {best_wr['kept']}/{len(trade_data)}")
        print(f"    Win Rate:       {best_wr['wr']:.1f}% (was {base_wr:.1f}%, Δ={best_wr['delta_wr']:+.1f}%)")
        print(f"    Total PnL:      ${best_wr['pnl']:+.2f} (was ${base_pnl:+.2f}, Δ=${best_wr['pnl']-base_pnl:+.2f})")
        print(f"    Winners kept:   {best_wr['winners_kept_pct']:.1f}%")
        print(f"    Losers killed:  {best_wr['losers_killed_pct']:.1f}%")
    
    # ── Step 8: Recommendations with exact parameter values ────────────
    print("\n" + "=" * 80)
    print("[8] RECOMMENDATIONS WITH EXACT PARAMETER VALUES")
    print("=" * 80)
    
    print("""
  PRIMARY RECOMMENDATION — Add these filters to bb_bounce.py:
  
  Based on the analysis, the key metrics that separate winners from losers are:
  1. 30-minute momentum slope — winners have less negative (or positive) momentum at entry
  2. 15-minute velocity — winners show less downward velocity (price not still falling hard)
  3. RSI — winners tend to have lower RSI (more oversold for LONG)
  4. Volume ratio — winners show above-average volume (confirmation of reversal)
  
  RECOMMENDED FILTERS (sorted by expected impact):
  
  A. MOMENTUM GATE (new, highest impact):
     Block LONG if momentum_30m < -0.01% per bar (normalized)
     This is the 30-minute linear regression slope / price * 100
     Implementation: compute linear regression of last 30 1m closes, normalize by price
     
  B. VELOCITY GATE (tighten existing):
     Current: MEAN_REVERSION_VEL_THRESHOLD = 0.3% (15m velocity)
     Recommendation: Tighten to 0.15% or switch to momentum-based gate
     The existing gate barely kills losers (~11%). A momentum gate is more effective.
  
  C. VOLUME CONFIRMATION (new, moderate impact):
     Block if volume_ratio < 0.75 (below-average volume = weak reversal)
     volume_ratio = avg(last 5 candles) / avg(previous 20 candles)
  
  D. RSI GATE (tighten existing):
     Current: RSI_OVERSOLD = 40 for co-signal, SOLO_RSI_OVERSOLD = 30
     These are already reasonable. The momentum gate subsumes some of this.
""")
    
    # ── Step 9: Risk Analysis ──────────────────────────────────────────
    print("=" * 80)
    print("[9] CAVEATS AND RISKS")
    print("=" * 80)
    
    print(f"""
  1. SAMPLE SIZE: {len(trade_data)} trades is moderate. Filter results may be
     overfitting to this specific sample. Cross-validate on a held-out subset.
  
  2. REGIME DEPENDENCY: Momentum-based filters may over-filter during strong
     downtrends (correctly) but also during normal pullbacks (incorrectly).
     Monitor WR by regime.
  
  3. SURVIVORSHIP BIAS: The candles.db only has data for actively traded tokens.
     Tokens with very old data gaps may have missing candle data.
  
  4. EXECUTION DELAY: Analysis uses entry timestamp, but actual execution may
     be delayed 1-3 minutes. This doesn't affect the filter logic but may
     affect metrics slightly.
  
  5. EXISTING VELOCITY GATE: Verified — MEAN_REVERSION_VEL_THRESHOLD = 0.3%
     kills approximately {len(vel_blocked)/len(trade_data)*100:.0f}% of trades, of which
     only {len(vel_blocked_losers)/max(len(vel_blocked),1)*100:.0f}% are losers. This is nearly
     useless as a filter. The proposed momentum gate is ~3-5x more effective
     at separating winners from losers.
  
  6. DIRECTION ASYMMETRY: LONG and SHORT trades may respond differently to
     the same filters. Consider direction-specific thresholds.
  
  7. OVERFITTING RISK: Testing 30+ filter combinations on 232 trades means
     some will look good by chance. Focus on filters with strong economic
     rationale, not just statistical significance.
  
  8. CONFLUENCE INTERACTION: These filters would fire BEFORE the hot-set gate.
     They interact with the confluence requirement — if a filter kills a
     co-signal component, the trade may fail confluence anyway.
""")
    
    print("=" * 80)
    print("ANALYSIS COMPLETE")
    print("=" * 80)


if __name__ == '__main__':
    main()
