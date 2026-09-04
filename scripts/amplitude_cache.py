#!/usr/bin/env python3
"""
amplitude_cache.py — Rolling amplitude cache for all tokens.

Computes amplitude percentiles (P50, P75, P90, P95) from 1h candles.
Feeds into dynamic SL/TP, position sizing, and signal confidence.

Usage:
    python3 amplitude_cache.py              # rebuild cache
    python3 amplitude_cache.py --get SOL    # query cached data
    python3 amplitude_cache.py --summary    # print all tokens

Cache file: data/amplitude_cache.json (refreshed hourly by systemd timer)
"""

import sys, os, json, time, sqlite3
import numpy as np
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paths import HERMES_DATA, CANDLES_DB
from hermes_constants import AMP_CLASS_LOW_MAX, AMP_CLASS_MED_MAX, TOKEN_AMP_CLASS

CACHE_FILE = os.path.join(HERMES_DATA, 'amplitude_cache.json')
LOOKBACK_CANDLES = 720  # 30 days of 1h candles
WAVE_WINDOW = 3         # extrema detection window (matches wave_classifier.py)


def get_candles(token, timeframe='1h', lookback=LOOKBACK_CANDLES):
    db = sqlite3.connect(CANDLES_DB)
    db.row_factory = sqlite3.Row
    rows = db.execute(f'''
        SELECT ts, open, high, low, close, volume
        FROM candles_{timeframe}
        WHERE token = ?
        ORDER BY ts DESC
        LIMIT ?
    ''', (token, lookback)).fetchall()
    db.close()
    return list(reversed(rows))


def filter_data_gaps(candles, max_gap_hours=48.0):
    if not candles or len(candles) < 2:
        return candles
    max_gap_s = max_gap_hours * 3600
    filtered = [candles[0]]
    for i in range(1, len(candles)):
        if candles[i]['ts'] - candles[i-1]['ts'] <= max_gap_s:
            filtered.append(candles[i])
    return filtered


def find_peaks_troughs(prices, window=WAVE_WINDOW):
    extrema = []
    for i in range(window, len(prices) - window):
        left = prices[i - window:i]
        right = prices[i + 1:i + window + 1]
        if prices[i] > max(left) and prices[i] > max(right):
            extrema.append((i, 'peak'))
        elif prices[i] < min(left) and prices[i] < min(right):
            extrema.append((i, 'trough'))
    return extrema


def compute_amplitudes(candles):
    if len(candles) < 20:
        return []
    closes = np.array([c['close'] for c in candles])
    timestamps = np.array([c['ts'] for c in candles])
    extrema = find_peaks_troughs(closes)

    amplitudes = []
    for i in range(1, len(extrema)):
        idx_prev, type_prev = extrema[i - 1]
        idx_curr, type_curr = extrema[i]
        if type_prev != type_curr:
            p1 = closes[idx_prev]
            p2 = closes[idx_curr]
            if p1 > 0:
                amp = abs(p2 - p1) / p1 * 100
                hours = (timestamps[idx_curr] - timestamps[idx_prev]) / 3600
                amplitudes.append({
                    'amplitude_pct': round(amp, 4),
                    'period_hours': round(hours, 2),
                    'from_ts': int(timestamps[idx_prev]),
                    'to_ts': int(timestamps[idx_curr]),
                })
    return amplitudes


def classify_amplitude(avg_amp):
    if avg_amp > AMP_CLASS_MED_MAX:
        return 'HIGH_AMP'
    elif avg_amp > AMP_CLASS_LOW_MAX:
        return 'MED_AMP'
    return 'LOW_AMP'


def compute_token_amplitude(token):
    try:
        candles = get_candles(token)
        candles = filter_data_gaps(candles)
        if len(candles) < 50:
            return None

        amplitudes = compute_amplitudes(candles)
        if not amplitudes:
            return None

        amps = [a['amplitude_pct'] for a in amplitudes]
        periods = [a['period_hours'] for a in amplitudes]

        # Amplitude percentiles
        arr = np.array(amps)
        p50 = float(np.percentile(arr, 50))
        p75 = float(np.percentile(arr, 75))
        p90 = float(np.percentile(arr, 90))
        p95 = float(np.percentile(arr, 95))
        avg_amp = float(np.mean(arr))

        # Period stats
        period_arr = np.array(periods)
        avg_period = float(np.mean(period_arr))
        period_cv = float(np.std(period_arr) / avg_period) if avg_period > 0 else 0

        # Wave count
        short_waves = sum(1 for p in periods if p < 2)
        medium_waves = sum(1 for p in periods if 2 <= p < 8)
        long_waves = sum(1 for p in periods if p >= 8)
        total = len(periods)

        amp_class = TOKEN_AMP_CLASS.get(token, classify_amplitude(avg_amp))

        return {
            'token': token,
            'amp_class': amp_class,
            'avg_amp': round(avg_amp, 4),
            'p50_amp': round(p50, 4),
            'p75_amp': round(p75, 4),
            'p90_amp': round(p90, 4),
            'p95_amp': round(p95, 4),
            'max_amp': round(float(np.max(arr)), 4),
            'avg_period': round(avg_period, 2),
            'period_cv': round(period_cv, 2),
            'total_waves': total,
            'short_pct': round(short_waves / total * 100, 1) if total else 0,
            'medium_pct': round(medium_waves / total * 100, 1) if total else 0,
            'long_pct': round(long_waves / total * 100, 1) if total else 0,
            'wave_count': len(amplitudes),
        }
    except Exception as e:
        print(f"  {token}: error — {e}")
        return None


def build_cache():
    tokens = list(TOKEN_AMP_CLASS.keys())
    cache = {'updated_at': int(time.time()), 'tokens': {}}

    for token in tokens:
        data = compute_token_amplitude(token)
        if data:
            cache['tokens'][token] = data
            print(f"  {token:8s} | {data['amp_class']:8s} | avg={data['avg_amp']:.2f}% "
                  f"p50={data['p50_amp']:.2f}% p90={data['p90_amp']:.2f}% "
                  f"| period={data['avg_period']:.1f}h waves={data['total_waves']}")
        else:
            print(f"  {token:8s} | SKIP (insufficient data)")

    os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
    with open(CACHE_FILE, 'w') as f:
        json.dump(cache, f, indent=2)
    print(f"\nCache written: {CACHE_FILE} ({len(cache['tokens'])} tokens)")
    return cache


def load_cache():
    try:
        with open(CACHE_FILE) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def get_cached(token):
    cache = load_cache()
    if not cache:
        return None
    return cache.get('tokens', {}).get(token.upper())


def get_avg_amplitude(token):
    data = get_cached(token)
    return data['avg_amp'] if data else 2.0  # default MED_AMP


def get_dynamic_sl(token, direction, entry_price, leverage=5.0):
    from hermes_constants import AMPLITUDE_SL_MULT, AMPLITUDE_MAX_PORTFOLIO_LOSS
    data = get_cached(token)
    if not data:
        return entry_price * (0.97 if direction == 'LONG' else 1.03)  # 3% fallback

    amp = data['avg_amp']
    mult = AMPLITUDE_SL_MULT.get(data['amp_class'], 1.25)
    sl_pct = amp * mult / 100

    portfolio_loss = sl_pct * leverage
    if portfolio_loss > AMPLITUDE_MAX_PORTFOLIO_LOSS:
        sl_pct = AMPLITUDE_MAX_PORTFOLIO_LOSS / leverage

    if direction == 'LONG':
        return entry_price * (1 - sl_pct)
    else:
        return entry_price * (1 + sl_pct)


def print_summary():
    cache = load_cache()
    if not cache:
        print("No cache found. Run: python3 amplitude_cache.py")
        return
    print(f"Amplitude Cache — updated {datetime.fromtimestamp(cache['updated_at'], tz=timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"{'Token':8s} {'Class':8s} {'Avg':>6s} {'P50':>6s} {'P75':>6s} {'P90':>6s} {'P95':>6s} {'Period':>7s} {'Waves':>5s}")
    print("-" * 72)
    for token, d in sorted(cache['tokens'].items()):
        print(f"{token:8s} {d['amp_class']:8s} {d['avg_amp']:5.2f}% {d['p50_amp']:5.2f}% "
              f"{d['p75_amp']:5.2f}% {d['p90_amp']:5.2f}% {d['p95_amp']:5.2f}% "
              f"{d['avg_period']:5.1f}h {d['total_waves']:5d}")


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Amplitude cache')
    parser.add_argument('--get', help='Get cached data for token')
    parser.add_argument('--summary', action='store_true', help='Print summary')
    parser.add_argument('--sl', nargs=3, metavar=('TOKEN', 'DIRECTION', 'PRICE'),
                        help='Compute dynamic SL')
    args = parser.parse_args()

    if args.get:
        data = get_cached(args.get)
        if data:
            print(json.dumps(data, indent=2))
        else:
            print(f"No data for {args.get}")
    elif args.summary:
        print_summary()
    elif args.sl:
        token, direction, price = args.sl
        sl = get_dynamic_sl(token, direction, float(price))
        data = get_cached(token)
        amp = data['avg_amp'] if data else 2.0
        print(f"{token} {direction} entry=${price} → SL=${sl:.4f} (amp={amp:.2f}%)")
    else:
        build_cache()
