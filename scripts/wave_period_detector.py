#!/usr/bin/env python3
"""
wave_period_detector.py — Detect and analyze wave periods/periodicity.

Focuses on:
1. Finding peaks and troughs in price data
2. Calculating time periods between them (periodicity)
3. Detecting when wave frequency is changing
4. Identifying regular vs irregular wave patterns

This complements wave_backtest.py which focuses on MACD-based strategies.
"""

import sys
import os
import sqlite3
import json
import numpy as np
from datetime import datetime, timedelta
from collections import defaultdict
import argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paths import CANDLES_DB


def get_candles(token: str, timeframe: str = '1h', lookback: int = 720) -> list:
    """Fetch candle data."""
    db = sqlite3.connect(CANDLES_DB)
    db.row_factory = sqlite3.Row
    
    table = f'candles_{timeframe}'
    rows = db.execute(f'''
        SELECT ts, open, high, low, close, volume
        FROM {table}
        WHERE token = ?
        ORDER BY ts DESC
        LIMIT ?
    ''', (token, lookback)).fetchall()
    
    db.close()
    return list(reversed(rows))


def filter_data_gaps(candles: list, max_gap_hours: float = 48.0) -> list:
    """
    Remove candles that are part of data gaps (missing data stretches).

    A gap is detected when the time between consecutive candles exceeds max_gap_hours.
    Candles within the gap are removed to avoid false extrema detection.

    Args:
        candles: List of candle dicts with 'ts' field
        max_gap_hours: Maximum allowed gap between candles in hours

    Returns:
        Filtered list of candles with gaps removed
    """
    if not candles or len(candles) < 2:
        return candles

    max_gap_seconds = max_gap_hours * 3600
    filtered = [candles[0]]

    for i in range(1, len(candles)):
        gap = candles[i]['ts'] - candles[i-1]['ts']
        if gap <= max_gap_seconds:
            filtered.append(candles[i])
        # else: skip this candle (it's in a gap region)

    return filtered


def find_peaks_troughs(prices: np.ndarray, window: int = 3) -> list:
    """
    Find local peaks and troughs using sliding window.
    
    Args:
        prices: Array of price values
        window: Number of candles on each side to compare
        
    Returns:
        List of (index, price, type) where type is 'peak' or 'trough'
    """
    extrema = []
    n = len(prices)
    
    for i in range(window, n - window):
        # Check if local maximum (peak) — strict > to avoid flat-price bias
        if all(prices[i] > prices[i-j] for j in range(1, window+1)) and \
           all(prices[i] > prices[i+j] for j in range(1, window+1)):
            extrema.append((i, prices[i], 'peak'))

        # Check if local minimum (trough) — strict < to avoid flat-price bias
        elif all(prices[i] < prices[i-j] for j in range(1, window+1)) and \
             all(prices[i] < prices[i+j] for j in range(1, window+1)):
            extrema.append((i, prices[i], 'trough'))
    
    return extrema


def calculate_wave_periods(extrema: list, timestamps: np.ndarray) -> dict:
    """
    Calculate time periods between consecutive peaks and troughs.
    
    Returns detailed period analysis.
    """
    if len(extrema) < 2:
        return {'error': 'Insufficient extrema'}
    
    periods = []
    for i in range(1, len(extrema)):
        idx1, price1, type1 = extrema[i-1]
        idx2, price2, type2 = extrema[i]
        
        # Time difference in seconds
        time_diff = timestamps[idx2] - timestamps[idx1]
        # Price difference
        price_diff = price2 - price1
        # Amplitude (percentage move)
        amplitude = (price_diff / price1) * 100
        
        periods.append({
            'from_idx': idx1,
            'to_idx': idx2,
            'from_time': datetime.fromtimestamp(timestamps[idx1]),
            'to_time': datetime.fromtimestamp(timestamps[idx2]),
            'from_price': price1,
            'to_price': price2,
            'from_type': type1,
            'to_type': type2,
            'period_hours': time_diff / 3600,
            'period_days': time_diff / 86400,
            'amplitude_pct': amplitude,
            'direction': 'up' if price_diff > 0 else 'down'
        })
    
    # Calculate statistics
    period_hours = [p['period_hours'] for p in periods]
    amplitudes = [abs(p['amplitude_pct']) for p in periods]
    
    return {
        'periods': periods,
        'stats': {
            'count': len(periods),
            'avg_period_hours': np.mean(period_hours),
            'std_period_hours': np.std(period_hours),
            'median_period_hours': np.median(period_hours),
            'min_period_hours': min(period_hours),
            'max_period_hours': max(period_hours),
            'avg_amplitude_pct': np.mean(amplitudes),
            'std_amplitude_pct': np.std(amplitudes),
            'peaks': sum(1 for e in extrema if e[2] == 'peak'),
            'troughs': sum(1 for e in extrema if e[2] == 'trough')
        }
    }


def detect_frequency_changes(periods: list, window: int = 5) -> list:
    """
    Detect significant changes in wave frequency/period.
    
    Uses rolling window to compare recent periods against historical.
    
    Args:
        periods: List of period dictionaries
        window: Number of periods for rolling comparison
        
    Returns:
        List of detected frequency changes
    """
    if len(periods) < window * 2:
        return []
    
    changes = []
    
    for i in range(window, len(periods)):
        # Recent window
        recent = periods[i-window:i]
        # Historical window
        historical = periods[max(0, i-window*2):i-window]
        
        if not historical:
            continue
        
        recent_avg = np.mean([p['period_hours'] for p in recent])
        hist_avg = np.mean([p['period_hours'] for p in historical])
        
        # Calculate change magnitude
        if hist_avg > 0:
            change_pct = ((recent_avg - hist_avg) / hist_avg) * 100
        else:
            change_pct = 0
        
        # Detect significant change (>20% or >2 hours)
        if abs(change_pct) > 20 or abs(recent_avg - hist_avg) > 2:
            changes.append({
                'time': periods[i]['to_time'],
                'period_idx': i,
                'recent_avg_hours': recent_avg,
                'historical_avg_hours': hist_avg,
                'change_pct': change_pct,
                'direction': 'faster' if change_pct < 0 else 'slower',
                'magnitude': 'significant' if abs(change_pct) > 30 else 'moderate'
            })
    
    return changes


def analyze_wave_pattern_consistency(periods: list) -> dict:
    """
    Analyze how consistent/regular the wave pattern is.
    
    Returns metrics on pattern regularity.
    """
    if not periods:
        return {'error': 'No periods to analyze'}
    
    period_hours = [p['period_hours'] for p in periods]
    amplitudes = [abs(p['amplitude_pct']) for p in periods]
    
    # Coefficient of variation (lower = more consistent)
    cv_period = np.std(period_hours) / np.mean(period_hours) if np.mean(period_hours) > 0 else float('inf')
    cv_amplitude = np.std(amplitudes) / np.mean(amplitudes) if np.mean(amplitudes) > 0 else float('inf')
    
    # Determine consistency level
    if cv_period < 0.2:
        period_consistency = 'very_high'
    elif cv_period < 0.4:
        period_consistency = 'high'
    elif cv_period < 0.6:
        period_consistency = 'medium'
    elif cv_period < 0.8:
        period_consistency = 'low'
    else:
        period_consistency = 'very_low'
    
    if cv_amplitude < 0.3:
        amplitude_consistency = 'very_high'
    elif cv_amplitude < 0.5:
        amplitude_consistency = 'high'
    elif cv_amplitude < 0.7:
        amplitude_consistency = 'medium'
    else:
        amplitude_consistency = 'low'
    
    # Check for cyclical patterns in period lengths
    # (e.g., short-long-short-long)
    if len(period_hours) >= 4:
        # Calculate autocorrelation at lag 1
        arr = np.array(period_hours)
        autocorr = np.corrcoef(arr[:-1], arr[1:])[0, 1]
    else:
        autocorr = 0
    
    return {
        'period_cv': cv_period,
        'amplitude_cv': cv_amplitude,
        'period_consistency': period_consistency,
        'amplitude_consistency': amplitude_consistency,
        'autocorrelation_lag1': autocorr,
        'has_cyclical_pattern': abs(autocorr) > 0.3
    }


def generate_wave_trading_signals(extrema: list, periods: list, 
                                   freq_changes: list, pattern: dict) -> dict:
    """
    Generate trading signals based on wave analysis.
    
    Returns actionable signals with confidence levels.
    """
    signal = {
        'action': 'HOLD',
        'confidence': 0.0,
        'reason': '',
        'wave_state': 'unknown',
        'entry_zone': None
    }
    
    if not extrema or not periods:
        return signal
    
    # Current wave state
    last_extremum = extrema[-1]
    last_price = last_extremum[1]
    last_type = last_extremum[2]
    last_time = datetime.fromtimestamp(0)  # placeholder
    
    # Find timestamp of last extrema
    for idx, price, t in extrema:
        if price == last_price and t == last_type:
            # This is approximate - we'd need the actual timestamp array
            break
    
    # Analyze recent period trend
    recent_periods = periods[-5:] if len(periods) >= 5 else periods
    recent_avg = np.mean([p['period_hours'] for p in recent_periods])
    
    # Check for frequency change signal
    if freq_changes:
        latest_change = freq_changes[-1]
        
        if latest_change['magnitude'] == 'significant':
            if latest_change['direction'] == 'faster':
                signal['wave_state'] = 'accelerating'
                signal['confidence'] = 0.7
                # Faster waves often precede breakouts
                signal['action'] = 'PREPARE_FOR_BREAKOUT'
                signal['reason'] = f"Wave frequency accelerating ({latest_change['change_pct']:.1f}% faster)"
            else:
                signal['wave_state'] = 'decelerating'
                signal['confidence'] = 0.7
                # Slower waves often precede consolidation or reversals
                signal['action'] = 'WATCH_FOR_REVERSAL'
                signal['reason'] = f"Wave frequency decelerating ({latest_change['change_pct']:.1f}% slower)"
    
    # Pattern-based signals
    if pattern.get('period_consistency') in ['very_high', 'high']:
        # Regular waves - trade the pattern
        if last_type == 'peak':
            signal['action'] = 'CONSIDER_SHORT'
            signal['confidence'] = 0.6
            signal['entry_zone'] = 'near_peak'
            signal['reason'] = 'Regular wave pattern: short near peak'
        elif last_type == 'trough':
            signal['action'] = 'CONSIDER_LONG'
            signal['confidence'] = 0.6
            signal['entry_zone'] = 'near_trough'
            signal['reason'] = 'Regular wave pattern: long near trough'
    
    elif pattern.get('period_consistency') in ['low', 'very_low']:
        # Irregular waves - reduce position size or stay out
        signal['action'] = 'REDUCE_EXPOSURE'
        signal['confidence'] = 0.8
        signal['reason'] = 'Irregular wave pattern - high uncertainty'
    
    return signal


def print_wave_analysis(token: str, timeframe: str, extrema: list, 
                        period_data: dict, freq_changes: list, 
                        pattern: dict, signal: dict):
    """Pretty print the complete wave analysis."""
    stats = period_data.get('stats', {})
    
    print("\n" + "="*80)
    print(f"WAVE PERIOD ANALYSIS: {token} ({timeframe})")
    print("="*80)
    
    print(f"\n{'─'*40}")
    print("EXTREMA DETECTED")
    print(f"{'─'*40}")
    print(f"  Total Peaks: {stats.get('peaks', 0)}")
    print(f"  Total Troughs: {stats.get('troughs', 0)}")
    
    print(f"\n{'─'*40}")
    print("PERIOD STATISTICS")
    print(f"{'─'*40}")
    print(f"  Average Period: {stats.get('avg_period_hours', 0):.2f} hours ({stats.get('avg_period_hours', 0)/24:.2f} days)")
    print(f"  Period Std Dev: {stats.get('std_period_hours', 0):.2f} hours")
    print(f"  Period Range: {stats.get('min_period_hours', 0):.2f} - {stats.get('max_period_hours', 0):.2f} hours")
    print(f"  Average Amplitude: {stats.get('avg_amplitude_pct', 0):.4f}%")
    
    print(f"\n{'─'*40}")
    print("PATTERN CONSISTENCY")
    print(f"{'─'*40}")
    print(f"  Period Consistency: {pattern.get('period_consistency', 'unknown')}")
    print(f"  Amplitude Consistency: {pattern.get('amplitude_consistency', 'unknown')}")
    print(f"  Autocorrelation (lag 1): {pattern.get('autocorrelation_lag1', 0):.3f}")
    print(f"  Has Cyclical Pattern: {'Yes' if pattern.get('has_cyclical_pattern') else 'No'}")
    
    print(f"\n{'─'*40}")
    print("RECENT EXTREMA (Last 6)")
    print(f"{'─'*40}")
    for e in extrema[-6:]:
        icon = '▲' if e[2] == 'peak' else '▼'
        # Find timestamp (approximate from index)
        print(f"  {icon} Price: ${e[1]:.4f}")
    
    if freq_changes:
        print(f"\n{'─'*40}")
        print("FREQUENCY CHANGES DETECTED")
        print(f"{'─'*40}")
        for c in freq_changes[-5:]:
            print(f"  ⚡ {c['time']} | {c['direction'].upper()} | {c['change_pct']:.1f}% | {c['magnitude']}")
    
    print(f"\n{'─'*40}")
    print("TRADING SIGNAL")
    print(f"{'─'*40}")
    print(f"  Action: {signal['action']}")
    print(f"  Confidence: {signal['confidence']:.2f}")
    print(f"  Wave State: {signal['wave_state']}")
    print(f"  Entry Zone: {signal.get('entry_zone', 'N/A')}")
    print(f"  Reason: {signal['reason']}")
    
    print("\n" + "="*80)


def analyze_wave_periods(token: str, timeframe: str = '1h', 
                         lookback: int = 720, window: int = 3) -> dict:
    """
    Complete wave period analysis.
    
    Returns comprehensive analysis results.
    """
    # Get candle data
    candles = get_candles(token, timeframe, lookback)
    if not candles:
        return {'error': f'No data found for {token}'}

    # Filter data gaps (>48h gaps cause false extrema)
    original_count = len(candles)
    candles = filter_data_gaps(candles, max_gap_hours=48.0)
    gaps_removed = original_count - len(candles)

    timestamps = np.array([c['ts'] for c in candles])
    closes = np.array([c['close'] for c in candles])
    
    # Find extrema
    extrema = find_peaks_troughs(closes, window=window)
    
    if len(extrema) < 3:
        return {'error': f'Insufficient extrema found ({len(extrema)})'}
    
    # Calculate periods
    period_data = calculate_wave_periods(extrema, timestamps)
    
    if 'error' in period_data:
        return period_data
    
    # Detect frequency changes
    freq_changes = detect_frequency_changes(period_data['periods'])
    
    # Analyze pattern consistency
    pattern = analyze_wave_pattern_consistency(period_data['periods'])
    
    # Generate trading signal
    signal = generate_wave_trading_signals(extrema, period_data['periods'], 
                                           freq_changes, pattern)
    
    # Compile results
    results = {
        'token': token,
        'timeframe': timeframe,
        'analysis_time': datetime.now().isoformat(),
        'data_range': {
            'start': datetime.fromtimestamp(timestamps[0]).isoformat(),
            'end': datetime.fromtimestamp(timestamps[-1]).isoformat(),
            'candles': len(candles)
        },
        'extrema': [{
            'time': datetime.fromtimestamp(timestamps[e[0]]).isoformat(),
            'price': e[1],
            'type': e[2]
        } for e in extrema],
        'period_stats': period_data['stats'],
        'periods': [{
            'from_time': p['from_time'].isoformat(),
            'to_time': p['to_time'].isoformat(),
            'period_hours': round(p['period_hours'], 2),
            'amplitude_pct': round(p['amplitude_pct'], 4),
            'direction': p['direction']
        } for p in period_data['periods']],
        'frequency_changes': [{
            'time': c['time'].isoformat(),
            'change_pct': round(c['change_pct'], 1),
            'direction': c['direction'],
            'magnitude': c['magnitude']
        } for c in freq_changes],
        'pattern_consistency': pattern,
        'trading_signal': signal
    }
    
    return results


def main():
    parser = argparse.ArgumentParser(description='Analyze wave periods in price data')
    parser.add_argument('token', nargs='?', default='ZRO', help='Token to analyze')
    parser.add_argument('--timeframe', default='1h', help='Candle timeframe')
    parser.add_argument('--lookback', type=int, default=720, help='Candles to analyze')
    parser.add_argument('--window', type=int, default=3, help='Extrema detection window')
    parser.add_argument('--json', action='store_true', help='Output as JSON')
    
    args = parser.parse_args()
    
    results = analyze_wave_periods(
        token=args.token,
        timeframe=args.timeframe,
        lookback=args.lookback,
        window=args.window
    )
    
    if args.json:
        print(json.dumps(results, indent=2, default=str))
    else:
        if 'error' in results:
            print(f"Error: {results['error']}")
        else:
            # For pretty print, we need extrema in original format
            candles = get_candles(args.token, args.timeframe, args.lookback)
            timestamps = np.array([c['ts'] for c in candles])
            closes = np.array([c['close'] for c in candles])
            extrema = find_peaks_troughs(closes, window=args.window)
            
            print_wave_analysis(
                token=args.token,
                timeframe=args.timeframe,
                extrema=extrema,
                period_data={'stats': results['period_stats'], 'periods': results['periods']},
                freq_changes=results['frequency_changes'],
                pattern=results['pattern_consistency'],
                signal=results['trading_signal']
            )


if __name__ == '__main__':
    main()
