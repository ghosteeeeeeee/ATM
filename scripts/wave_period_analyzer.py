#!/usr/bin/env python3
"""
wave_period_analyzer.py — Detect and analyze wave periods/periodicity in price data.

Identifies peaks and troughs, calculates time between them, and detects
when the wave pattern/frequency is changing.

Usage:
  python3 wave_period_analyzer.py [token] [--timeframe 1h] [--lookback 720] [--visualize]
"""

import sys
import os
import sqlite3
import json
import argparse
import numpy as np
from datetime import datetime, timedelta
from collections import defaultdict

# Add scripts directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paths import CANDLES_DB


def get_candles(token: str, timeframe: str = '1h', lookback: int = 720) -> list:
    """Fetch candle data from the database."""
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
    # Reverse to chronological order
    return list(reversed(rows))


def find_peaks_troughs(prices: np.ndarray, window: int = 5) -> list:
    """
    Find local peaks and troughs using a sliding window.
    
    Args:
        prices: Array of price values (close prices)
        window: Number of candles on each side to compare
        
    Returns:
        List of (index, price, type) where type is 'peak' or 'trough'
    """
    extrema = []
    n = len(prices)
    
    for i in range(window, n - window):
        # Check if local maximum (peak)
        if all(prices[i] >= prices[i-j] for j in range(1, window+1)) and \
           all(prices[i] >= prices[i+j] for j in range(1, window+1)):
            extrema.append((i, prices[i], 'peak'))
        
        # Check if local minimum (trough)
        elif all(prices[i] <= prices[i-j] for j in range(1, window+1)) and \
             all(prices[i] <= prices[i+j] for j in range(1, window+1)):
            extrema.append((i, prices[i], 'trough'))
    
    return extrema


def calculate_periods(extrema: list, timestamps: np.ndarray) -> dict:
    """
    Calculate time periods between consecutive peaks and troughs.
    
    Returns:
        Dictionary with period information
    """
    if len(extrema) < 2:
        return {}
    
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
    
    return {
        'periods': periods,
        'avg_period_hours': np.mean([p['period_hours'] for p in periods]),
        'std_period_hours': np.std([p['period_hours'] for p in periods]),
        'avg_amplitude_pct': np.mean([abs(p['amplitude_pct']) for p in periods]),
        'total_extrema': len(extrema),
        'peaks': sum(1 for e in extrema if e[2] == 'peak'),
        'troughs': sum(1 for e in extrema if e[2] == 'trough')
    }


def detect_frequency_change(periods: list, window: int = 5) -> list:
    """
    Detect significant changes in wave frequency/period.
    
    Uses a rolling window to compare recent periods against historical average.
    
    Args:
        periods: List of period dictionaries
        window: Number of periods to use for rolling comparison
        
    Returns:
        List of detected frequency changes with timestamps and magnitudes
    """
    if len(periods) < window * 2:
        return []
    
    changes = []
    
    for i in range(window, len(periods)):
        # Recent window
        recent = periods[i-window:i]
        # Historical window (before recent)
        historical = periods[max(0, i-window*2):i-window]
        
        if not historical:
            continue
        
        recent_avg = np.mean([p['period_hours'] for p in recent])
        hist_avg = np.mean([p['period_hours'] for p in historical])
        
        # Calculate change magnitude (percentage)
        if hist_avg > 0:
            change_pct = ((recent_avg - hist_avg) / hist_avg) * 100
        else:
            change_pct = 0
        
        # Detect significant change (>20% or >2 hours)
        if abs(change_pct) > 20 or abs(recent_avg - hist_avg) > 2:
            changes.append({
                'time': periods[i]['to_time'],
                'recent_avg_hours': recent_avg,
                'historical_avg_hours': hist_avg,
                'change_pct': change_pct,
                'direction': 'faster' if change_pct < 0 else 'slower',
                'magnitude': 'significant' if abs(change_pct) > 30 else 'moderate'
            })
    
    return changes


def analyze_zro_waves(token: str = 'ZRO', timeframe: str = '1h', 
                      lookback: int = 720, window: int = 5) -> dict:
    """
    Complete wave period analysis for a token.
    
    Returns comprehensive analysis results.
    """
    # Get candle data
    candles = get_candles(token, timeframe, lookback)
    if not candles:
        return {'error': f'No data found for {token}'}
    
    timestamps = np.array([c['ts'] for c in candles])
    closes = np.array([c['close'] for c in candles])
    highs = np.array([c['high'] for c in candles])
    lows = np.array([c['low'] for c in candles])
    
    # Find peaks and troughs on close prices
    extrema = find_peaks_troughs(closes, window=window)
    
    # Calculate periods
    period_data = calculate_periods(extrema, timestamps)
    
    # Detect frequency changes
    freq_changes = detect_frequency_change(period_data.get('periods', []))
    
    # Analyze recent trades (last 3 extrema)
    recent_extrema = extrema[-6:] if len(extrema) >= 6 else extrema
    recent_periods = period_data.get('periods', [])[-3:] if len(period_data.get('periods', [])) >= 3 else period_data.get('periods', [])
    
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
        'wave_statistics': {
            'total_peaks': period_data.get('peaks', 0),
            'total_troughs': period_data.get('troughs', 0),
            'avg_period_hours': round(period_data.get('avg_period_hours', 0), 2),
            'std_period_hours': round(period_data.get('std_period_hours', 0), 2),
            'avg_amplitude_pct': round(period_data.get('avg_amplitude_pct', 0), 4),
            'period_consistency': 'high' if period_data.get('std_period_hours', 0) < 2 else 
                                 'medium' if period_data.get('std_period_hours', 0) < 4 else 'low'
        },
        'recent_extrema': [{
            'time': datetime.fromtimestamp(timestamps[e[0]]).isoformat(),
            'price': e[1],
            'type': e[2]
        } for e in recent_extrema],
        'recent_periods': [{
            'from_time': p['from_time'].isoformat(),
            'to_time': p['to_time'].isoformat(),
            'period_hours': round(p['period_hours'], 2),
            'amplitude_pct': round(p['amplitude_pct'], 4),
            'direction': p['direction']
        } for p in recent_periods],
        'frequency_changes': [{
            'time': c['time'].isoformat(),
            'change_pct': round(c['change_pct'], 2),
            'direction': c['direction'],
            'magnitude': c['magnitude']
        } for c in freq_changes[-5:]],  # Last 5 changes
        'trading_signal': generate_trading_signal(period_data, freq_changes, extrema)
    }
    
    return results


def generate_trading_signal(period_data: dict, freq_changes: list, extrema: list) -> dict:
    """
    Generate a trading signal based on wave analysis.
    
    Returns signal with confidence and recommended action.
    """
    signal = {
        'action': 'HOLD',
        'confidence': 0.0,
        'reason': '',
        'wave_pattern': 'unknown'
    }
    
    if not period_data or not period_data.get('periods'):
        return signal
    
    periods = period_data['periods']
    avg_period = period_data['avg_period_hours']
    std_period = period_data['std_period_hours']
    
    # Determine wave pattern
    if std_period < 1.5:
        signal['wave_pattern'] = 'regular'
    elif std_period < 3:
        signal['wave_pattern'] = 'moderate_variation'
    else:
        signal['wave_pattern'] = 'irregular'
    
    # Check for recent frequency change
    if freq_changes:
        latest_change = freq_changes[-1]
        if latest_change['magnitude'] == 'significant':
            if latest_change['direction'] == 'faster':
                signal['action'] = 'WATCH'
                signal['confidence'] = 0.7
                signal['reason'] = f"Wave frequency accelerating ({latest_change['change_pct']:.1f}% faster)"
            else:
                signal['action'] = 'WATCH'
                signal['confidence'] = 0.7
                signal['reason'] = f"Wave frequency decelerating ({latest_change['change_pct']:.1f}% slower)"
    
    # Check current position in wave
    if extrema and len(extrema) >= 2:
        last_extremum = extrema[-1]
        if last_extremum[2] == 'peak':
            signal['action'] = 'CONSIDER_SHORT'
            signal['confidence'] = 0.6
            signal['reason'] = 'Recent peak detected, potential downward move'
        elif last_extremum[2] == 'trough':
            signal['action'] = 'CONSIDER_LONG'
            signal['confidence'] = 0.6
            signal['reason'] = 'Recent trough detected, potential upward move'
    
    return signal


def print_analysis(results: dict):
    """Pretty print the analysis results."""
    print("\n" + "="*70)
    print(f"WAVE PERIOD ANALYSIS: {results['token']}")
    print("="*70)
    
    print(f"\nData Range: {results['data_range']['start']} to {results['data_range']['end']}")
    print(f"Candles Analyzed: {results['data_range']['candles']}")
    
    stats = results['wave_statistics']
    print(f"\n{'─'*40}")
    print("WAVE STATISTICS")
    print(f"{'─'*40}")
    print(f"Total Peaks: {stats['total_peaks']}")
    print(f"Total Troughs: {stats['total_troughs']}")
    print(f"Average Period: {stats['avg_period_hours']:.2f} hours ({stats['avg_period_hours']/24:.2f} days)")
    print(f"Period Std Dev: {stats['std_period_hours']:.2f} hours")
    print(f"Average Amplitude: {stats['avg_amplitude_pct']:.4f}%")
    print(f"Pattern Consistency: {stats['period_consistency']}")
    
    print(f"\n{'─'*40}")
    print("RECENT EXTREMA (Last 6)")
    print(f"{'─'*40}")
    for e in results['recent_extrema']:
        icon = '▲' if e['type'] == 'peak' else '▼'
        print(f"  {icon} {e['time'][:16]} | ${e['price']:.4f}")
    
    print(f"\n{'─'*40}")
    print("RECENT PERIODS")
    print(f"{'─'*40}")
    for p in results['recent_periods']:
        print(f"  {p['from_time'][:16]} → {p['to_time'][:16]}")
        print(f"    Period: {p['period_hours']:.2f}h | Amplitude: {p['amplitude_pct']:.4f}% | Direction: {p['direction']}")
    
    if results['frequency_changes']:
        print(f"\n{'─'*40}")
        print("FREQUENCY CHANGES DETECTED")
        print(f"{'─'*40}")
        for c in results['frequency_changes']:
            print(f"  ⚡ {c['time'][:16]} | {c['direction'].upper()} | {c['change_pct']:.1f}% | {c['magnitude']}")
    
    signal = results['trading_signal']
    print(f"\n{'─'*40}")
    print("TRADING SIGNAL")
    print(f"{'─'*40}")
    print(f"  Action: {signal['action']}")
    print(f"  Confidence: {signal['confidence']:.2f}")
    print(f"  Wave Pattern: {signal['wave_pattern']}")
    print(f"  Reason: {signal['reason']}")
    
    print("\n" + "="*70)


def main():
    parser = argparse.ArgumentParser(description='Analyze wave periods in price data')
    parser.add_argument('token', nargs='?', default='ZRO', help='Token to analyze (default: ZRO)')
    parser.add_argument('--timeframe', default='1h', help='Candle timeframe (default: 1h)')
    parser.add_argument('--lookback', type=int, default=720, help='Number of candles to analyze (default: 720)')
    parser.add_argument('--window', type=int, default=5, help='Extrema detection window (default: 5)')
    parser.add_argument('--json', action='store_true', help='Output as JSON')
    
    args = parser.parse_args()
    
    results = analyze_zro_waves(
        token=args.token,
        timeframe=args.timeframe,
        lookback=args.lookback,
        window=args.window
    )
    
    if args.json:
        print(json.dumps(results, indent=2, default=str))
    else:
        print_analysis(results)


if __name__ == '__main__':
    main()
