#!/usr/bin/env python3
"""
Backtest: ADX+DI Crossover vs MACD Acceleration signals on Hermes candles.

Tests two trend-following approaches:
1. ADX+DI: +DI crosses above -DI with ADX confirming (>20, rising)
2. MACD Acceleration: MACD histogram accelerating in direction of trend

Uses candles.db (1h and 4h tables) — 170 tokens, ~96 days of data.
"""

import sqlite3
import math
import statistics
from datetime import datetime

DB = '/root/.hermes/data/candles.db'
MIN_CANDLES = 100  # minimum 1h candles needed

# ── Standard ADX+DI computation (Wilder) ──────────────────────────────────────

def compute_adx_di(hlc_rows, period=14):
    """
    Compute ADX, +DI, -DI from list of (timestamp, open, high, low, close).
    Returns (adx, plus_di, minus_di, direction) or None if insufficient data.
    Direction: 'LONG' if +DI > -DI else 'SHORT'.
    """
    if len(hlc_rows) < period * 2:
        return None

    # True Range and Directional Movement
    tr_list = []
    plus_dm = []
    minus_dm = []

    for i in range(1, len(hlc_rows)):
        _, _, h_prev, l_prev, c_prev = hlc_rows[i-1]
        _, o, h, l, c = hlc_rows[i]

        tr = max(h - l, abs(h - c_prev), abs(l - c_prev))
        up_move = h - h_prev
        down_move = l_prev - l

        plus = up_move if (up_move > down_move and up_move > 0) else 0
        minus = down_move if (down_move > up_move and down_move > 0) else 0

        tr_list.append(tr)
        plus_dm.append(plus)
        minus_dm.append(minus)

    if len(tr_list) < period:
        return None

    # Wilder smoothing
    def wilder_smooth(values, period):
        alpha = 1.0 / period
        smoothed = [sum(values[:period])]
        for v in values[period:]:
            smoothed.append(smoothed[-1] * (1 - alpha) + v)
        return smoothed

    tr_smooth = wilder_smooth(tr_list, period)
    plus_smooth = wilder_smooth(plus_dm, period)
    minus_smooth = wilder_smooth(minus_dm, period)

    # DX
    dx_list = []
    for i in range(len(tr_smooth)):
        if tr_smooth[i] == 0:
            dx_list.append(0)
        else:
            pdi = (plus_smooth[i] / tr_smooth[i]) * 100
            mdi = (minus_smooth[i] / tr_smooth[i]) * 100
            dx = abs(pdi - mdi) / (pdi + mdi) * 100 if (pdi + mdi) > 0 else 0
            dx_list.append(dx)

    if len(dx_list) < period:
        return None

    # ADX = Wilder EMA of DX
    adx_series = [sum(dx_list[:period]) / period]
    alpha = 1.0 / period
    for dx in dx_list[period:]:
        adx_series.append(adx_series[-1] * (1 - alpha) + dx)

    # Current values
    adx = adx_series[-1]
    n = len(tr_smooth)
    plus_di = (plus_smooth[n-1] / tr_smooth[n-1]) * 100 if tr_smooth[n-1] > 0 else 0
    minus_di = (minus_smooth[n-1] / tr_smooth[n-1]) * 100 if tr_smooth[n-1] > 0 else 0

    direction = 'LONG' if plus_di > minus_di else 'SHORT'
    return (round(adx, 2), round(plus_di, 2), round(minus_di, 2), direction)


def compute_macd(closes, fast=12, slow=26, signal=9):
    """MACD line, signal line, histogram. Returns (macd, signal_line, hist) or None."""
    if len(closes) < slow + signal:
        return None

    def ema(data, n):
        alpha = 2 / (n + 1)
        ema_val = sum(data[:n]) / n
        result = [ema_val]
        for v in data[n:]:
            ema_val = v * alpha + ema_val * (1 - alpha)
            result.append(ema_val)
        return result

    ema_fast = ema(closes, fast)
    ema_slow = ema(closes, slow)

    macd_line = [f - s for f, s in zip(ema_fast, ema_slow)]
    signal_line = ema(macd_line, signal)
    hist = [m - s for m, s in zip(macd_line, signal_line)]

    return (macd_line[-1], signal_line[-1], hist[-1])


def macd_acceleration(hist_list, lookback=4):
    """
    MACD histogram acceleration: is the histogram momentum increasing?
    Returns positive if histogram is becoming more positive (bullish momentum building).
    Returns negative if histogram is becoming more negative (bearish momentum building).
    """
    if len(hist_list) < lookback:
        return 0.0
    recent = hist_list[-lookback:]
    # Slope of histogram over lookback period
    delta = recent[-1] - recent[0]
    return delta / lookback


# ── Backtest logic ────────────────────────────────────────────────────────────

def load_1h_candles(token):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute(
        "SELECT ts, open, high, low, close FROM candles_1h WHERE token=? ORDER BY ts",
        (token,)
    )
    rows = c.fetchall()
    conn.close()
    return rows


def run_adx_backtest(token, adx_period=14, adx_threshold=20, use_4h_confirm=True):
    """
    Fire LONG when +DI > -DI and ADX > threshold (and rising).
    Fire SHORT when -DI > +DI and ADX > threshold (and rising).
    Returns list of (ts, direction, adx, strength_score) for each signal.
    """
    candles = load_1h_candles(token)
    if len(candles) < 200:
        return []

    signals = []

    # Compute rolling ADX
    hlc_rows = [(r[0], r[1], r[2], r[3], r[4]) for r in candles]  # ts, open, high, low, close

    # We need a longer window for ADX computation
    for i in range(50, len(hlc_rows)):
        window = hlc_rows[max(0, i-200):i]
        result = compute_adx_di(window, period=adx_period)
        if result is None:
            continue

        adx, plus_di, minus_di, direction = result

        if adx < adx_threshold:
            continue

        # Check if ADX is rising (trend strengthening) — compare to 3 bars ago
        # Need to recompute for earlier window to get ADX history
        window_prev = hlc_rows[max(0, i-203):i-3]
        result_prev = compute_adx_di(window_prev, period=adx_period) if len(window_prev) > 50 else None
        adx_prev = result_prev[0] if result_prev else 0

        if adx <= adx_prev:
            continue  # ADX not rising — skip

        # ADX rising + crossover confirmed
        signals.append((hlc_rows[i][0], direction, adx, adx - adx_prev))

    return signals


def run_macd_backtest(token, fast=12, slow=26, signal=9, min_hist=0.0001, hist_accel_threshold=0.00001):
    """
    Fire when MACD histogram crosses zero (momentum shift) AND histogram is accelerating.
    LONG: histogram crosses above 0 AND acceleration > threshold
    SHORT: histogram crosses below 0 AND acceleration > threshold
    """
    candles = load_1h_candles(token)
    if len(candles) < slow + signal + 10:
        return []

    closes = [r[4] for r in candles]
    signals = []

    # Compute MACD for all windows
    macd_results = []
    for i in range(slow + signal, len(closes)):
        window = closes[:i]
        result = compute_macd(window, fast, slow, signal)
        if result:
            macd_results.append((i, result))
        else:
            macd_results.append((i, None))

    # Build histogram history
    hist_window = []
    for idx, (i, result) in enumerate(macd_results):
        if result is None:
            hist_window.append(0)
            macd_results[idx] = (i, (0, 0, 0))
        else:
            hist_window.append(result[2])

        if len(hist_window) > 20:
            hist_window.pop(0)

        # Check for crossover
        if len(hist_window) < 5:
            continue

        hist_now = hist_window[-1]
        hist_prev = hist_window[-2]

        if abs(hist_now) < min_hist:
            continue  # Too small to act on

        accel = macd_acceleration(hist_window)
        if abs(accel) < hist_accel_threshold:
            continue  # Not accelerating enough

        if hist_prev <= 0 < hist_now and accel > hist_accel_threshold:
            direction = 'LONG'
        elif hist_prev >= 0 > hist_now and accel < -hist_accel_threshold:
            direction = 'SHORT'
        else:
            continue

        ts = candles[i][0]
        signals.append((ts, direction, hist_now, accel))

    return signals


def evaluate_signals(token, signals, direction, forward_hours=[4, 8, 24]):
    """
    For each signal, check if price moved in the expected direction
    over the next forward_hours.
    Returns dict: {hours: (hit_rate, avg_return, n_signals)}
    """
    candles = load_1h_candles(token)
    if not candles:
        return {}

    close_map = {r[0]: r[4] for r in candles}

    results = {h: [] for h in forward_hours}

    for ts, sig_dir, *_ in signals:
        if sig_dir != direction:
            continue

        # Find candle index
        idx_map = {r[0]: i for i, r in enumerate(candles)}
        if ts not in idx_map:
            continue
        i = idx_map[ts]

        entry_price = candles[i][4]

        for fh in forward_hours:
            future_i = i + fh
            if future_i >= len(candles):
                continue
            exit_price = candles[future_i][4]

            if direction == 'LONG':
                ret = (exit_price - entry_price) / entry_price
            else:
                ret = (entry_price - exit_price) / entry_price

            results[fh].append(ret)

    return results


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print(f"{'='*70}")
    print("BACKTEST: Trend-Following Signals — ADX+DI vs MACD Acceleration")
    print(f"{'='*70}")

    # Load token list
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT DISTINCT token FROM candles_1h ORDER BY token")
    tokens = [r[0] for r in c.fetchall()]
    conn.close()

    print(f"Tokens: {len(tokens)} | Period: ~96 days (2026-01-13 to 2026-04-19)")
    print()

    # ── ADX+DI Backtest ────────────────────────────────────────────────────
    print(f"{'─'*70}")
    print("ADX+DI BACKTEST")
    print(f"{'─'*70}")

    adx_results = {4: [], 8: [], 24: []}
    adx_long = []
    adx_short = []

    for token in tokens:
        signals = run_adx_backtest(token, adx_period=14, adx_threshold=20)
        for direction in ['LONG', 'SHORT']:
            ev = evaluate_signals(token, signals, direction, [4, 8, 24])
            for fh, data in ev.items():
                if data:
                    if direction == 'LONG':
                        adx_long.extend(data)
                    else:
                        adx_short.extend(data)
                    adx_results[fh].extend(data)

    print(f"\n  LONG signals: {len(adx_long)} | SHORT signals: {len(adx_short)}")
    print(f"\n  ADX+DI All Directions:")
    for fh in [4, 8, 24]:
        data = adx_results[fh]
        if not data:
            print(f"    {fh}h: no data")
            continue
        hits = sum(1 for r in data if r > 0)
        wr = hits / len(data) * 100
        avg = statistics.mean(data) * 100
        print(f"    {fh}h: n={len(data):4d}  WR={wr:5.1f}%  Avg={avg:+.3f}%")

    print(f"\n  ADX+DI LONG only:")
    for fh in [4, 8, 24]:
        data = adx_long
        if not data:
            print(f"    {fh}h: no data")
            continue
        hits = sum(1 for r in data if r > 0)
        wr = hits / len(data) * 100
        avg = statistics.mean(data) * 100
        print(f"    {fh}h: n={len(data):4d}  WR={wr:5.1f}%  Avg={avg:+.3f}%")

    print(f"\n  ADX+DI SHORT only:")
    for fh in [4, 8, 24]:
        data = adx_short
        if not data:
            print(f"    {fh}h: no data")
            continue
        hits = sum(1 for r in data if r > 0)
        wr = hits / len(data) * 100
        avg = statistics.mean(data) * 100
        print(f"    {fh}h: n={len(data):4d}  WR={wr:5.1f}%  Avg={avg:+.3f}%")

    # ── MACD Acceleration Backtest ───────────────────────────────────────────
    print(f"\n{'─'*70}")
    print("MACD ACCELERATION BACKTEST")
    print(f"{'─'*70}")

    macd_results = {4: [], 8: [], 24: []}
    macd_long = []
    macd_short = []

    for token in tokens:
        signals = run_macd_backtest(token)
        for direction in ['LONG', 'SHORT']:
            ev = evaluate_signals(token, signals, direction, [4, 8, 24])
            for fh, data in ev.items():
                if data:
                    if direction == 'LONG':
                        macd_long.extend(data)
                    else:
                        macd_short.extend(data)
                    macd_results[fh].extend(data)

    print(f"\n  LONG signals: {len(macd_long)} | SHORT signals: {len(macd_short)}")
    print(f"\n  MACD Accel All Directions:")
    for fh in [4, 8, 24]:
        data = macd_results[fh]
        if not data:
            print(f"    {fh}h: no data")
            continue
        hits = sum(1 for r in data if r > 0)
        wr = hits / len(data) * 100
        avg = statistics.mean(data) * 100
        print(f"    {fh}h: n={len(data):4d}  WR={wr:5.1f}%  Avg={avg:+.3f}%")

    print(f"\n  MACD Accel LONG only:")
    for fh in [4, 8, 24]:
        data = macd_long
        if not data:
            print(f"    {fh}h: no data")
            continue
        hits = sum(1 for r in data if r > 0)
        wr = hits / len(data) * 100
        avg = statistics.mean(data) * 100
        print(f"    {fh}h: n={len(data):4d}  WR={wr:5.1f}%  Avg={avg:+.3f}%")

    print(f"\n  MACD Accel SHORT only:")
    for fh in [4, 8, 24]:
        data = macd_short
        if not data:
            print(f"    {fh}h: no data")
            continue
        hits = sum(1 for r in data if r > 0)
        wr = hits / len(data) * 100
        avg = statistics.mean(data) * 100
        print(f"    {fh}h: n={len(data):4d}  WR={wr:5.1f}%  Avg={avg:+.3f}%")

    # ── Compare vs baseline (random) ─────────────────────────────────────────
    print(f"\n{'─'*70}")
    print("BASELINE COMPARISON")
    print(f"{'─'*70}")
    print("  Random guess (50/50): WR=50.0%")
    print(f"  Z-score mean-reversion at z=2 (from prior backtest):")
    print(f"    SHORT: WR=59.0% @ 4h, Avg=+0.09%")
    print(f"    LONG:  WR=54.2% @ 4h, Avg=+0.03%")

    print(f"\n{'='*70}")
    print("INTERPRETATION GUIDE:")
    print("  WR > 50% = better than random")
    print("  WR > 55% = meaningful edge")
    print("  Avg > 0 = profitable on average per signal")
    print("  Higher n = more signals (more opportunities but dilute quality)")
    print(f"{'='*70}")


if __name__ == '__main__':
    main()
