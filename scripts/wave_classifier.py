#!/usr/bin/env python3
"""Classify wave patterns across tokens."""

import sys, os
import numpy as np
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from wave_period_detector import get_candles, find_peaks_troughs, calculate_wave_periods

tokens = ['BTC', 'ETH', 'SOL', 'LINK', 'ARB', 'ZRO', 'TRUMP', 'WIF', 'HYPE', 'DOGE',
          'SUI', 'AAVE', 'ONDO', 'WLD', 'TURBO', 'POPCAT', 'SPX', 'KAS', 'XRP', 'FET']

print('=' * 120)
print('WAVE PATTERN CLASSIFICATION — MULTI-TOKEN SCAN')
print('=' * 120)

classifications = []

for token in tokens:
    try:
        candles = get_candles(token, '1h', 720)
        timestamps = np.array([c['ts'] for c in candles])
        closes = np.array([c['close'] for c in candles])

        extrema = find_peaks_troughs(closes, window=3)
        period_data = calculate_wave_periods(extrema, timestamps)

        if 'error' in period_data:
            continue

        periods = period_data['periods']
        period_hours = [p['period_hours'] for p in periods]
        amplitudes = [abs(p['amplitude_pct']) for p in periods]

        avg_period = np.mean(period_hours)
        std_period = np.std(period_hours)
        avg_amp = np.mean(amplitudes)

        fast_pct = sum(1 for p in period_hours if p < 2) / len(period_hours) * 100
        medium_pct = sum(1 for p in period_hours if 2 <= p < 8) / len(period_hours) * 100
        slow_pct = sum(1 for p in period_hours if p >= 8) / len(period_hours) * 100

        # Classify pattern
        if fast_pct > 60:
            pattern = 'HIGH_FREQ_OSCILLATOR'
            desc = 'Fast 1-2h waves, high-frequency noise'
        elif medium_pct > 60:
            pattern = 'MEDIUM_FREQ_TREND'
            desc = 'Steady 4-8h waves, trend-rideable'
        elif fast_pct > 40 and medium_pct > 40:
            pattern = 'BIMODAL'
            desc = 'Mixed fast/slow, regime-dependent'
        elif slow_pct > 40:
            pattern = 'LOW_FREQ_SWINGER'
            desc = 'Slow 8h+ waves, position trades'
        elif std_period / avg_period > 1.5:
            pattern = 'CHAOTIC'
            desc = 'High variability, unpredictable'
        else:
            pattern = 'TRANSITIONAL'
            desc = 'No clear dominant frequency'

        # Amplitude
        if avg_amp > 2.5:
            amp_class = 'HIGH_AMP'
        elif avg_amp > 1.5:
            amp_class = 'MED_AMP'
        else:
            amp_class = 'LOW_AMP'

        classifications.append({
            'token': token, 'pattern': pattern, 'desc': desc,
            'amp_class': amp_class, 'avg_period': avg_period,
            'std_period': std_period, 'fast_pct': fast_pct,
            'medium_pct': medium_pct, 'slow_pct': slow_pct,
            'avg_amp': avg_amp, 'total_periods': len(periods)
        })

        print(f"  {token:8s} | {pattern:22s} | {amp_class:8s} | Avg: {avg_period:5.2f}h | "
              f"CV: {std_period/avg_period:.2f} | Fast: {fast_pct:5.1f}% | Med: {medium_pct:5.1f}% | "
              f"Slow: {slow_pct:5.1f}% | Amp: {avg_amp:.4f}%")

    except Exception as e:
        print(f"  {token:8s} | Error: {e}")

# ── Summary ──
print()
print('=' * 120)
print('PATTERN BUCKETS')
print('=' * 120)

pattern_counts = Counter(c['pattern'] for c in classifications)
amp_counts = Counter(c['amp_class'] for c in classifications)

print()
print('Wave Frequency Buckets:')
for pattern, count in pattern_counts.most_common():
    tokens_list = [c['token'] for c in classifications if c['pattern'] == pattern]
    print(f"  {pattern:22s}: {count:2d} tokens — {', '.join(tokens_list)}")

print()
print('Amplitude Buckets:')
for amp_class, count in amp_counts.most_common():
    tokens_list = [c['token'] for c in classifications if c['amp_class'] == amp_class]
    print(f"  {amp_class:8s}: {count:2d} tokens — {', '.join(tokens_list)}")

# ── Cross-classification matrix ──
print()
print('=' * 120)
print('CROSS-CLASSIFICATION MATRIX (Pattern × Amplitude)')
print('=' * 120)

combos = Counter((c['pattern'], c['amp_class']) for c in classifications)
for (pat, amp), count in sorted(combos.items()):
    tokens_list = [c['token'] for c in classifications if c['pattern'] == pat and c['amp_class'] == amp]
    print(f"  {pat:22s} × {amp:8s} = {count:2d} — {', '.join(tokens_list)}")
