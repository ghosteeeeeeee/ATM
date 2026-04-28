#!/usr/bin/env python3
"""
Backtest: ADX+DI Crossover vs MACD Acceleration signals on Hermes candles.
Tests trend-following approaches against candles.db (170 tokens, ~96 days).
"""

import sqlite3
import math
import statistics
from datetime import datetime

DB = '/root/.hermes/data/candles.db'

# ── Standard ADX+DI computation (Wilder) ──────────────────────────────────────

def compute_adx_di(hlc_rows, period=14):
    """
    Compute ADX, +DI, -DI from list of (timestamp, open, high, low, close).
    Returns (adx, plus_di, minus_di, direction) or None if insufficient data.
    """
    if len(hlc_rows) < period * 2:
        return None

    tr_list, plus_dm, minus_dm = [], [], []
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

    def wilder_smooth(values, period):
        alpha = 1.0 / period
        smoothed = [sum(values[:period])]
        for v in values[period:]:
            smoothed.append(smoothed[-1] * (1 - alpha) + v)
        return smoothed

    tr_smooth = wilder_smooth(tr_list, period)
    plus_smooth = wilder_smooth(plus_dm, period)
    minus_smooth = wilder_smooth(minus_dm, period)

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

    adx_series = [sum(dx_list[:period]) / period]
    alpha = 1.0 / period
    for dx in dx_list[period:]:
        adx_series.append(adx_series[-1] * (1 - alpha) + dx)

    n = len(tr_smooth)
    plus_di = (plus_smooth[n-1] / tr_smooth[n-1]) * 100 if tr_smooth[n-1] > 0 else 0
    minus_di = (minus_smooth[n-1] / tr_smooth[n-1]) * 100 if tr_smooth[n-1] > 0 else 0

    direction = 'LONG' if plus_di > minus_di else 'SHORT'
    return (round(adx_series[-1], 2), round(plus_di, 2), round(minus_di, 2), direction)


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
    MACD histogram acceleration: slope of histogram over lookback period.
    Positive = bullish momentum building. Negative = bearish.
    """
    if len(hist_list) < lookback + 1:
        return 0.0
    recent = hist_list[-lookback-1:]
    return (recent[-1] - recent[0]) / (lookback + 1)


# ── On-demand ADX (for efficiency: only compute at crossover points) ───────────

def compute_adx_at(highs, lows, closes, idx, period=14, window=200):
    """Compute ADX at a specific candle index only."""
    start = max(1, idx - window)
    h = highs[start:idx]
    l = lows[start:idx]
    c = closes[start:idx]
    return compute_adx_di_from_arrays(h, l, c, period)


def compute_adx_di_from_arrays(highs, lows, closes, period=14):
    """Compute ADX from arrays of highs/lows/closes."""
    if len(closes) < period * 2:
        return None
    tr_list, plus_dm, minus_dm = [], [], []
    for i in range(1, len(closes)):
        tr = max(highs[i] - lows[i], abs(highs[i] - closes[i-1]), abs(lows[i] - closes[i-1]))
        up = highs[i] - highs[i-1]
        dn = lows[i-1] - lows[i]
        plus_dm.append(up if up > dn and up > 0 else 0)
        minus_dm.append(dn if dn > up and dn > 0 else 0)
        tr_list.append(tr)
    if len(tr_list) < period:
        return None

    def w(v, p):
        a = 1.0 / p
        s = [sum(v[:p])]
        for val in v[p:]:
            s.append(s[-1] * (1 - a) + val)
        return s

    tr_s = w(tr_list, period)
    p_s = w(plus_dm, period)
    m_s = w(minus_dm, period)
    dx = [abs((p_s[i] / tr_s[i] * 100 if tr_s[i] > 0 else 0) -
              (m_s[i] / tr_s[i] * 100 if tr_s[i] > 0 else 0)) /
          ((p_s[i] / tr_s[i] * 100 if tr_s[i] > 0 else 0) +
           (m_s[i] / tr_s[i] * 100 if tr_s[i] > 0 else 0)) * 100
          if (p_s[i] + m_s[i]) > 0 else 0
          for i in range(len(tr_s))]
    adx_s = [sum(dx[:period]) / period]
    a = 1.0 / period
    for d in dx[period:]:
        adx_s.append(adx_s[-1] * (1 - a) + d)
    n = len(tr_s)
    pdi = (p_s[n-1] / tr_s[n-1] * 100) if tr_s[n-1] > 0 else 0
    mdi = (m_s[n-1] / tr_s[n-1] * 100) if tr_s[n-1] > 0 else 0
    return adx_s[-1], pdi, mdi


# ── Main backtest ─────────────────────────────────────────────────────────────

def main():
    print(f"{'='*70}")
    print("BACKTEST: Trend-Following Signals — ADX+DI vs MACD Acceleration")
    print(f"{'='*70}")

    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT DISTINCT token FROM candles_1h ORDER BY token")
    tokens = [r[0] for r in c.fetchall()]
    conn.close()

    print(f"Tokens: {len(tokens)} | Period: ~96 days (2026-01-13 to 2026-04-19)")
    print()

    # ── ADX+DI ────────────────────────────────────────────────────────────────
    print(f"{'─'*70}")
    print("ADX+DI BACKTEST")
    print(f"{'─'*70}")

    adx_long, adx_short = [], []
    for token in tokens:
        conn = sqlite3.connect(DB)
        c = conn.cursor()
        c.execute("SELECT ts, open, high, low, close FROM candles_1h WHERE token=? ORDER BY ts", (token,))
        rows = c.fetchall()
        conn.close()
        if len(rows) < 200:
            continue

        closes = [r[4] for r in rows]
        highs = [r[2] for r in rows]
        lows = [r[3] for r in rows]

        for forward in [4, 8, 24]:
            adx_data = {}
            for i in range(50, len(closes)):
                adx_data[i] = compute_adx_di_from_arrays(highs[:i], lows[:i], closes[:i], 14)

            for i in range(50, len(closes) - forward):
                if adx_data.get(i) is None:
                    continue
                adx, pdi, mdi = adx_data[i]
                if adx < 20:
                    continue

                # Check ADX rising
                if adx_data.get(i-3) is None:
                    continue
                if adx <= adx_data[i-3][0]:
                    continue

                if pdi > mdi:
                    ret = (closes[i+forward] - closes[i]) / closes[i]
                    adx_long.append(ret)
                else:
                    ret = (closes[i] - closes[i+forward]) / closes[i]
                    adx_short.append(ret)

    print(f"\n  LONG: n={len(adx_long)}")
    for fh, data in [(4, adx_long[:len(adx_long)//3*1]), (8, adx_long[len(adx_long)//3*1:len(adx_long)//3*2]), (24, adx_long[len(adx_long)//3*2:])]:
        if data:
            wr = sum(1 for r in data if r > 0) / len(data) * 100
            avg = statistics.mean(data) * 100
            print(f"    @{fh}h: n={len(data)} WR={wr:.1f}% Avg={avg:+.3f}%")
    print(f"  SHORT: n={len(adx_short)}")
    for fh, data in [(4, adx_short[:len(adx_short)//3*1]), (8, adx_short[len(adx_short)//3*1:len(adx_short)//3*2]), (24, adx_short[len(adx_short)//3*2:])]:
        if data:
            wr = sum(1 for r in data if r > 0) / len(data) * 100
            avg = statistics.mean(data) * 100
            print(f"    @{fh}h: n={len(data)} WR={wr:.1f}% Avg={avg:+.3f}%")

    # ── MACD Acceleration ────────────────────────────────────────────────────
    print(f"\n{'─'*70}")
    print("MACD ACCELERATION BACKTEST (12/26/9)")
    print(f"{'─'*70}")

    FAST, SLOW, SIG = 12, 26, 9

    for label, forward, fast, slow, sig, lab in [
        ("MACD 12/26/9 @4h", 4, 12, 26, 9, 4),
        ("MACD 12/26/9 @8h", 8, 12, 26, 9, 4),
        ("MACD 12/26/9 @24h", 24, 12, 26, 9, 4),
        ("MACD 8/21/9 @8h", 8, 8, 21, 9, 4),
    ]:
        long_rets, short_rets = [], []

        for token in tokens:
            conn = sqlite3.connect(DB)
            c = conn.cursor()
            c.execute("SELECT ts, open, high, low, close FROM candles_1h WHERE token=? ORDER BY ts", (token,))
            rows = c.fetchall()
            conn.close()
            if len(rows) < slow + sig + lab + 10:
                continue

            closes = [r[4] for r in rows]

            # Build MACD histogram history
            macd_data = {}
            for i in range(slow + sig, len(closes)):
                r = compute_macd(closes[:i], fast, slow, sig)
                if r:
                    macd_data[i] = r[2][-1]

            for i in range(slow + sig + 1, len(closes) - forward):
                if i not in macd_data or i-1 not in macd_data:
                    continue
                h_now = macd_data[i]
                h_prev = macd_data[i-1]

                # Acceleration
                accel_keys = [i - k for k in range(1, lab + 1)]
                if any(k not in macd_data for k in accel_keys):
                    continue
                accel = (h_now - macd_data[accel_keys[-1]]) / (lab + 1)

                if h_prev <= 0 < h_now and accel > 0:
                    long_rets.append((closes[i+forward] - closes[i]) / closes[i])
                elif h_prev >= 0 > h_now and accel < 0:
                    short_rets.append((closes[i] - closes[i+forward]) / closes[i])

        lw = sum(1 for r in long_rets if r > 0) / max(len(long_rets), 1) * 100
        la = statistics.mean(long_rets) * 100 if long_rets else 0
        sw = sum(1 for r in short_rets if r > 0) / max(len(short_rets), 1) * 100
        sa = statistics.mean(short_rets) * 100 if short_rets else 0
        print(f"  {label}: LONG n={len(long_rets)} WR={lw:.1f}% Avg={la:+.3f}% | SHORT n={len(short_rets)} WR={sw:.1f}% Avg={sa:+.3f}%")

    print(f"\n{'─'*70}")
    print("Baseline: z-score mean-reversion SHORT WR=59% @4h Avg=+0.09%")
    print(f"{'='*70}")


if __name__ == '__main__':
    main()
