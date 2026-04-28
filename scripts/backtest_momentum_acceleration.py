#!/usr/bin/env python3
"""
Backtest: Momentum Acceleration Signal
Theory: ROC acceleration (2nd derivative of price) predicts momentum continuation.
  - ROC rising (acceleration > 0) = momentum building → LONG
  - ROC falling (acceleration < 0) = momentum fading → exit/short
  - Volume confirmation = real vs fakeout

Compares:
  1. Simple ROC > 0 (baseline momentum)
  2. ROC > 0 AND acceleration > 0 (confirmed momentum)
  3. ROC crossing above threshold with rising acceleration (breakout momentum)
  4. ROC + acceleration + volume confirmation
"""
import sqlite3, statistics, sys, os
from typing import List, Tuple

DB = '/root/.hermes/data/candles.db'

TOKENS = ['BTC', 'ETH', 'AXS', 'IMX', 'SKY', 'TRB',
          'SOL', 'AVAX', 'MATIC', 'LINK', 'UNI', 'AAVE', 'MKR', 'SNX']

WINDOWS = [1, 2, 4, 6]  # 4h bars forward
ROC_PERIODS = [4, 8, 12]  # N-bar ROC lookback


def get_candles_4h_with_vol(token: str) -> List[Tuple[int, float, float]]:
    """Get 4h candles with volume. Returns (ts, close, volume)."""
    conn = sqlite3.connect(DB, timeout=10)
    c = conn.cursor()
    c.execute("""
        SELECT ts, close, volume FROM candles_4h
        WHERE token = ?
        ORDER BY ts ASC
    """, (token,))
    rows = c.fetchall()
    conn.close()
    return rows


def compute_roc(prices: List[float], period: int) -> List[float]:
    """Rate of Change: % change over N periods."""
    roc = []
    for i in range(len(prices)):
        if i < period:
            roc.append(None)
            continue
        change = (prices[i] - prices[i - period]) / prices[i - period]
        roc.append(change)
    return roc


def compute_acceleration(roc: List[float]) -> List[float]:
    """2nd derivative of price = acceleration of ROC."""
    accel = []
    for i in range(len(roc)):
        if i < 1 or roc[i] is None or roc[i-1] is None:
            accel.append(None)
            continue
        accel.append(roc[i] - roc[i-1])
    return accel


def compute_vol_ratio(volumes: List[float], period: int = 20) -> List[float]:
    """Current volume / 20-bar average volume."""
    ratios = []
    for i in range(len(volumes)):
        if i < period:
            ratios.append(1.0)
            continue
        avg = statistics.mean(volumes[i-period:i])
        ratios.append(volumes[i] / avg if avg > 0 else 1.0)
    return ratios


def backtest_signal(token: str, signal_type: str, forward_windows: List[int],
                    roc_thresh: float, accel_thresh: float, vol_thresh: float,
                    roc_period: int) -> dict:
    """
    Returns dict of window -> {returns, hits}
    signal_type:
      'roc_positive'   - simple: ROC > 0
      'roc_accel'      - ROC > thresh AND acceleration > 0
      'roc_cross'      - ROC crosses above thresh AND acceleration > 0
      'roc_accel_vol'  - ROC > thresh AND acceleration > 0 AND vol_ratio > thresh
    """
    candles = get_candles_4h_with_vol(token)
    if len(candles) < 100:
        return None

    closes = [c[1] for c in candles]
    volumes = [c[2] for c in candles]

    roc = compute_roc(closes, roc_period)
    accel = compute_acceleration(roc)
    vol_ratio = compute_vol_ratio(volumes)

    results_by_window = {w: {'returns': [], 'hits': []} for w in forward_windows}

    for i in range(len(candles) - max(forward_windows)):
        r = roc[i]
        a = accel[i]
        v = vol_ratio[i]
        if r is None or a is None:
            continue

        fired = False
        if signal_type == 'roc_positive':
            fired = r > roc_thresh
        elif signal_type == 'roc_accel':
            fired = r > roc_thresh and a > accel_thresh
        elif signal_type == 'roc_cross':
            # ROC crossed above threshold this bar (was below last bar)
            r_prev = roc[i-1] if i > 0 else None
            fired = (r_prev is not None and r_prev <= roc_thresh and r > roc_thresh) and a > accel_thresh
        elif signal_type == 'roc_accel_vol':
            fired = r > roc_thresh and a > accel_thresh and v > vol_thresh

        if fired:
            entry = closes[i]
            for w in forward_windows:
                ret = (closes[i + w] - entry) / entry
                results_by_window[w]['returns'].append(ret)
                results_by_window[w]['hits'].append(ret > 0)

    return results_by_window


def main():
    print("=" * 100)
    print("MOMENTUM ACCELERATION BACKTEST")
    print("=" * 100)

    SIGNAL_CONFIGS = [
        # (name, roc_thresh, accel_thresh, vol_thresh)
        ('roc_positive',    0.0,   0.0,    0.0),   # baseline: any positive ROC
        ('roc_accel',       0.0,   0.001,  0.0),   # ROC > 0 AND accel > 0
        ('roc_accel',       0.02,  0.001,  0.0),   # ROC > 2% AND accel > 0
        ('roc_accel',       0.05,  0.001,  0.0),   # ROC > 5% AND accel > 0
        ('roc_cross',       0.0,   0.001,  0.0),   # ROC crossing > 0 with accel
        ('roc_cross',       0.02,  0.001,  0.0),   # ROC crossing > 2% with accel
        ('roc_accel_vol',   0.0,   0.001,  1.5),   # + volume confirmation
        ('roc_accel_vol',   0.02,  0.001,  1.5),   # + volume
        ('roc_accel_vol',   0.05,  0.001,  1.5),   # + volume
    ]

    print("\n" + "=" * 100)
    print("LONG SIGNALS (positive ROC = price going up)")
    print("=" * 100)
    print(f"{'Signal':<20} {'Thresh':<10} {'N':>6} "
          "| {'4h Ret%':>10} {'8h Ret%':>10} {'16h Ret%':>10} {'24h Ret%':>10} "
          "| {'4h Hit%':>8} {'8h Hit%':>8} {'16h Hit%':>8} {'24h Hit%':>8}")
    print("-" * 120)

    for roc_period in [4, 8]:
        agg_all = {s[0]: {w: {'rets': [], 'hits': []} for w in WINDOWS} for s in SIGNAL_CONFIGS}

        for token in TOKENS:
            for sc in SIGNAL_CONFIGS:
                name, rt, at, vt = sc
                results = backtest_signal(token, name, WINDOWS, rt, at, vt, roc_period)
                if not results:
                    continue
                for w in WINDOWS:
                    agg_all[name][w]['rets'].extend(results[w]['returns'])
                    agg_all[name][w]['hits'].extend(results[w]['hits'])

        print(f"\n--- ROC Period = {roc_period} bars ({roc_period*4}h lookback) ---")
        for sc in SIGNAL_CONFIGS:
            name, rt, at, vt = sc
            thresh_str = f"ROC>{rt:.0%}" + (f" Accel>{at}" if at > 0 else "") + (f" Vol>{vt}x" if vt > 0 else "")
            n = len(agg_all[name][1]['rets'])
            if n < 10:
                continue

            def fmt(w):
                rets = agg_all[name][w]['rets']
                hits = agg_all[name][w]['hits']
                if not rets:
                    return f"{'N/A':>10} {'N/A':>8}"
                return f"{statistics.mean(rets)*100:>+10.2f} {statistics.mean(hits)*100:>8.1f}"

            print(f"{name:<20} {thresh_str:<10} {n:>6} | " + " ".join(fmt(w) for w in WINDOWS))

    # Now test SHORT side: ROC < 0 (price going down) → momentum continuing SHORT
    print("\n\n" + "=" * 100)
    print("SHORT SIGNALS (negative ROC = price going down → momentum SHORT)")
    print("=" * 100)
    print(f"{'Signal':<20} {'Thresh':<10} {'N':>6} "
          "| {'4h Ret%':>10} {'8h Ret%':>10} {'16h Ret%':>10} {'24h Ret%':>10} "
          "| {'4h Hit%':>8} {'8h Hit%':>8} {'16h Hit%':>8} {'24h Hit%':>8}")
    print("-" * 120)

    def backtest_short(token: str, signal_type: str, forward_windows: List[int],
                       roc_thresh: float, accel_thresh: float, vol_thresh: float,
                       roc_period: int) -> dict:
        """Short: ROC < 0 with acceleration going more negative = continuing down."""
        candles = get_candles_4h_with_vol(token)
        if len(candles) < 100:
            return None

        closes = [c[1] for c in candles]
        volumes = [c[2] for c in candles]

        roc = compute_roc(closes, roc_period)
        accel = compute_acceleration(roc)
        vol_ratio = compute_vol_ratio(volumes)

        results_by_window = {w: {'returns': [], 'hits': []} for w in forward_windows}

        for i in range(len(candles) - max(forward_windows)):
            r = roc[i]
            a = accel[i]
            v = vol_ratio[i]
            if r is None or a is None:
                continue

            fired = False
            if signal_type == 'roc_positive':  # reuse: negative ROC for SHORT
                fired = r < -roc_thresh
            elif signal_type == 'roc_accel':
                fired = r < -roc_thresh and a < -accel_thresh  # accel going more negative
            elif signal_type == 'roc_cross':
                r_prev = roc[i-1] if i > 0 else None
                fired = (r_prev is not None and r_prev >= -roc_thresh and r < -roc_thresh) and a < -accel_thresh
            elif signal_type == 'roc_accel_vol':
                fired = r < -roc_thresh and a < -accel_thresh and v > vol_thresh

            if fired:
                entry = closes[i]
                for w in forward_windows:
                    # SHORT return = -(price change)
                    ret = -(closes[i + w] - entry) / entry
                    results_by_window[w]['returns'].append(ret)
                    results_by_window[w]['hits'].append(ret > 0)

        return results_by_window

    agg_short = {s[0]: {w: {'rets': [], 'hits': []} for w in WINDOWS} for s in SIGNAL_CONFIGS}

    for token in TOKENS:
        for sc in SIGNAL_CONFIGS:
            name, rt, at, vt = sc
            results = backtest_short(token, name, WINDOWS, rt, at, vt, roc_period)
            if not results:
                continue
            for w in WINDOWS:
                agg_short[name][w]['rets'].extend(results[w]['returns'])
                agg_short[name][w]['hits'].extend(results[w]['hits'])

    for roc_period in [4, 8]:
        print(f"\n--- ROC Period = {roc_period} bars ({roc_period*4}h lookback) ---")
        for sc in SIGNAL_CONFIGS:
            name, rt, at, vt = sc
            thresh_str = f"ROC<{-rt:.0%}" + (f" Accel<{-at}" if at > 0 else "") + (f" Vol>{vt}x" if vt > 0 else "")
            n = len(agg_short[name][1]['rets'])
            if n < 10:
                continue

            def fmt_s(w):
                rets = agg_short[name][w]['rets']
                hits = agg_short[name][w]['hits']
                if not rets:
                    return f"{'N/A':>10} {'N/A':>8}"
                return f"{statistics.mean(rets)*100:>+10.2f} {statistics.mean(hits)*100:>8.1f}"

            print(f"{name:<20} {thresh_str:<10} {n:>6} | " + " ".join(fmt_s(w) for w in WINDOWS))

    # Per-token breakdown for best signal
    print("\n\n" + "=" * 100)
    print("PER-TOKEN: roc_accel (ROC>2% + accel>0) vs roc_accel_vol (ROC>2% + accel>0 + vol>1.5x)")
    print("=" * 100)

    best_sig = 'roc_accel'
    best_thresh = 0.02

    print(f"\nLONG | Token | N | 4h Ret% | 4h Hit% | N | 4h Ret% | 4h Hit%")
    print(f"{'Signal':<15} {'Token':<8} | {'roc_accel':>5} {'roc_accel+vol':>5} | {'roc_accel':>8} {'roc_accel+vol':>8} | {'roc_accel':>8} {'roc_accel+vol':>8}")
    print("-" * 80)

    for token in TOKENS:
        candles = get_candles_4h_with_vol(token)
        if len(candles) < 100:
            continue

        closes = [c[1] for c in candles]
        volumes = [c[2] for c in candles]
        roc = compute_roc(closes, 4)
        accel = compute_acceleration(roc)
        vol_ratio = compute_vol_ratio(volumes)

        rets_basic, rets_vol = [], []
        rets_basic4, rets_vol4 = [], []

        for i in range(len(candles) - max(WINDOWS)):
            r = roc[i]
            a = accel[i]
            v = vol_ratio[i]
            if r is None or a is None:
                continue
            entry = closes[i]

            # basic: ROC > 2% AND accel > 0
            if r > 0.02 and a > 0.001:
                ret = (closes[i+1] - entry) / entry
                rets_basic.append(ret)
                rets_basic4.append((closes[i+4] - entry) / entry)

            # vol: ROC > 2% AND accel > 0 AND vol > 1.5x
            if r > 0.02 and a > 0.001 and v > 1.5:
                ret = (closes[i+1] - entry) / entry
                rets_vol.append(ret)
                rets_vol4.append((closes[i+4] - entry) / entry)

        n1, n2 = len(rets_basic), len(rets_vol)
        if n1 < 3 and n2 < 3:
            continue

        r1 = f"{statistics.mean(rets_basic)*100:>+7.2f}%" if rets_basic else "   N/A  "
        r2 = f"{statistics.mean(rets_vol)*100:>+7.2f}%" if rets_vol else "   N/A  "
        h1 = f"{statistics.mean(rets_basic)*100:>7.1f}%" if rets_basic else "   N/A  "
        h2 = f"{statistics.mean(rets_vol)*100:>7.1f}%" if rets_vol else "   N/A  "
        print(f"{'roc_accel':<15} {token:<8} | {n1:>5} {r1:<8} {h1:<8} | {n2:>5} {r2:<8} {h2:<8}")

    # Acceleration-only signal: no ROC level, just ACCELERATION direction
    print("\n\n" + "=" * 100)
    print("PURE ACCELERATION: acceleration crossing above 0 (no ROC threshold)")
    print("(Acceleration changing from negative to positive = momentum igniting)")
    print("=" * 100)
    print(f"{'Token':<8} {'Dir':<5} {'N':>5} | {'4h Ret%':>10} {'8h Ret%':>10} {'16h Ret%':>10} {'24h Ret%':>10} | {'4h Hit%':>8} {'8h Hit%':>8} {'16h Hit%':>8} {'24h Hit%':>8}")
    print("-" * 100)

    agg_pure = {d: {w: {'rets': [], 'hits': []} for w in WINDOWS}
                for d in ['long', 'short']}

    for token in TOKENS:
        candles = get_candles_4h_with_vol(token)
        if len(candles) < 100:
            continue

        closes = [c[1] for c in candles]
        volumes = [c[2] for c in candles]
        roc = compute_roc(closes, 4)
        accel = compute_acceleration(roc)

        for i in range(len(candles) - max(WINDOWS)):
            a = accel[i]
            a_prev = accel[i-1] if i > 0 else None
            if a is None or a_prev is None:
                continue

            entry = closes[i]

            # Acceleration CROSSING above 0: momentum igniting LONG
            if a_prev <= 0 and a > 0:
                for w in WINDOWS:
                    ret = (closes[i+w] - entry) / entry
                    agg_pure['long'][w]['rets'].append(ret)
                    agg_pure['long'][w]['hits'].append(ret > 0)

            # Acceleration CROSSING below 0: momentum reversing SHORT
            if a_prev >= 0 and a < 0:
                for w in WINDOWS:
                    ret = -(closes[i+w] - entry) / entry
                    agg_pure['short'][w]['rets'].append(ret)
                    agg_pure['short'][w]['hits'].append(ret > 0)

    for direction in ['long', 'short']:
        n = len(agg_pure[direction][1]['rets'])
        if n < 10:
            continue

        def fmt_p(w):
            rets = agg_pure[direction][w]['rets']
            hits = agg_pure[direction][w]['hits']
            if not rets:
                return f"{'N/A':>10} {'N/A':>8}"
            return f"{statistics.mean(rets)*100:>+10.2f} {statistics.mean(hits)*100:>8.1f}"

        print(f"{'PURE_ACCEL':<8} {direction:<5} {n:>5} | " + " ".join(fmt_p(w) for w in WINDOWS))

if __name__ == '__main__':
    main()
