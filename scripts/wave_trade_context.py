#!/usr/bin/env python3
"""
wave_trade_context.py — Analyze trades in context of wave periods.

Specifically looks at how trades align with wave peaks/troughs and
whether wave frequency changes predict trade outcomes.
"""

import sys
import os
import sqlite3
import json
import numpy as np
from datetime import datetime, timedelta
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paths import CANDLES_DB, TRADES_JSON


def get_trade_data() -> list:
    """Get all closed trades from trades.json."""
    with open(TRADES_JSON) as f:
        data = json.load(f)
    return data.get('closed', [])


def get_candles(token: str, timeframe: str = '1h', 
                start_ts: int = None, end_ts: int = None) -> list:
    """Fetch candle data for a time range."""
    db = sqlite3.connect(CANDLES_DB)
    db.row_factory = sqlite3.Row
    
    table = f'candles_{timeframe}'
    query = f'''
        SELECT ts, open, high, low, close, volume
        FROM {table}
        WHERE token = ?
    '''
    params = [token]
    
    if start_ts:
        query += ' AND ts >= ?'
        params.append(start_ts)
    if end_ts:
        query += ' AND ts <= ?'
        params.append(end_ts)
    
    query += ' ORDER BY ts ASC'
    rows = db.execute(query, params).fetchall()
    db.close()
    return rows


def find_peaks_troughs(prices: np.ndarray, window: int = 3) -> list:
    """Find local peaks and troughs."""
    extrema = []
    n = len(prices)
    
    for i in range(window, n - window):
        if all(prices[i] >= prices[i-j] for j in range(1, window+1)) and \
           all(prices[i] >= prices[i+j] for j in range(1, window+1)):
            extrema.append((i, prices[i], 'peak'))
        elif all(prices[i] <= prices[i-j] for j in range(1, window+1)) and \
             all(prices[i] <= prices[i+j] for j in range(1, window+1)):
            extrema.append((i, prices[i], 'trough'))
    
    return extrema


def analyze_trade_in_wave_context(trade: dict, token: str = 'ZRO') -> dict:
    """
    Analyze a single trade in the context of wave patterns.
    
    Returns analysis of:
    - Where in the wave cycle the trade was entered
    - Wave characteristics at time of entry
    - Whether wave frequency was changing
    """
    # Parse trade times
    entry_time = datetime.fromisoformat(trade['opened'])
    exit_time = datetime.fromisoformat(trade['closed'])
    entry_price = trade['entry']
    exit_price = trade['exit']
    direction = trade['direction']
    
    # Get candle data around the trade (48h before to 12h after)
    start_ts = int((entry_time - timedelta(hours=48)).timestamp())
    end_ts = int((exit_time + timedelta(hours=12)).timestamp())
    
    candles = get_candles(token, '1h', start_ts, end_ts)
    if not candles:
        return {'error': 'No candle data found'}
    
    timestamps = np.array([c['ts'] for c in candles])
    closes = np.array([c['close'] for c in candles])
    highs = np.array([c['high'] for c in candles])
    lows = np.array([c['low'] for c in candles])
    
    # Find extrema
    extrema = find_peaks_troughs(closes, window=3)
    
    # Find nearest peak/trough before entry
    entry_ts = int(entry_time.timestamp())
    peaks_before = [(i, p, t) for i, p, t in extrema if t == 'peak' and timestamps[i] <= entry_ts]
    troughs_before = [(i, p, t) for i, p, t in extrema if t == 'trough' and timestamps[i] <= entry_ts]
    
    # Determine position in wave
    last_peak = peaks_before[-1] if peaks_before else None
    last_trough = troughs_before[-1] if troughs_before else None
    
    wave_position = 'unknown'
    time_since_peak = None
    time_since_trough = None
    price_from_peak = None
    price_from_trough = None
    
    if last_peak and last_trough:
        peak_idx, peak_price, _ = last_peak
        trough_idx, trough_price, _ = last_trough
        
        time_since_peak = (entry_ts - timestamps[peak_idx]) / 3600  # hours
        time_since_trough = (entry_ts - timestamps[trough_idx]) / 3600
        price_from_peak = ((entry_price - peak_price) / peak_price) * 100
        price_from_trough = ((entry_price - trough_price) / trough_price) * 100
        
        # Determine wave position
        if time_since_peak < time_since_trough:
            # Closer to peak - potential top
            if price_from_peak > -2:  # Within 2% of peak
                wave_position = 'near_peak'
            else:
                wave_position = 'post_peak_declining'
        else:
            # Closer to trough - potential bottom
            if price_from_trough < 2:  # Within 2% of trough
                wave_position = 'near_trough'
            else:
                wave_position = 'post_trough_rising'
    
    # Calculate wave frequency around trade
    # Look at extrema in the 24h window around entry
    window_start = entry_ts - 12 * 3600
    window_end = entry_ts + 12 * 3600
    window_extrema = [(i, p, t) for i, p, t in extrema 
                      if window_start <= timestamps[i] <= window_end]
    
    # Calculate local period
    local_periods = []
    for j in range(1, len(window_extrema)):
        idx1, _, _ = window_extrema[j-1]
        idx2, _, _ = window_extrema[j]
        period_hours = (timestamps[idx2] - timestamps[idx1]) / 3600
        local_periods.append(period_hours)
    
    avg_local_period = np.mean(local_periods) if local_periods else None
    
    # Calculate broader frequency (last 7 days)
    week_start = entry_ts - 7 * 24 * 3600
    week_extrema = [(i, p, t) for i, p, t in extrema if timestamps[i] >= week_start]
    week_periods = []
    for j in range(1, len(week_extrema)):
        idx1, _, _ = week_extrema[j-1]
        idx2, _, _ = week_extrema[j]
        period_hours = (timestamps[idx2] - timestamps[idx1]) / 3600
        week_periods.append(period_hours)
    
    avg_week_period = np.mean(week_periods) if week_periods else None
    
    # Detect if frequency is changing
    freq_change = None
    if avg_local_period and avg_week_period:
        change_pct = ((avg_local_period - avg_week_period) / avg_week_period) * 100
        freq_change = {
            'local_avg_hours': round(avg_local_period, 2),
            'weekly_avg_hours': round(avg_week_period, 2),
            'change_pct': round(change_pct, 1),
            'direction': 'accelerating' if change_pct < -10 else 'decelerating' if change_pct > 10 else 'stable'
        }
    
    # Trade outcome analysis
    trade_duration = (exit_time - entry_time).total_seconds() / 3600
    pnl_pct = trade['pnl_pct']
    
    # Was the trade aligned with the wave?
    aligned_with_wave = False
    alignment_reason = ''
    
    if direction == 'SHORT':
        if wave_position in ['near_peak', 'post_peak_declining']:
            aligned_with_wave = True
            alignment_reason = f'SHORT near wave peak/decline phase'
        else:
            alignment_reason = f'SHORT against wave ({wave_position})'
    else:  # LONG
        if wave_position in ['near_trough', 'post_trough_rising']:
            aligned_with_wave = True
            alignment_reason = f'LONG near wave trough/rising phase'
        else:
            alignment_reason = f'LONG against wave ({wave_position})'
    
    return {
        'trade': {
            'entry_time': entry_time.isoformat(),
            'exit_time': exit_time.isoformat(),
            'entry_price': entry_price,
            'exit_price': exit_price,
            'direction': direction,
            'pnl_pct': pnl_pct,
            'duration_hours': round(trade_duration, 2)
        },
        'wave_context': {
            'position': wave_position,
            'time_since_peak_hours': round(time_since_peak, 2) if time_since_peak else None,
            'time_since_trough_hours': round(time_since_trough, 2) if time_since_trough else None,
            'price_from_peak_pct': round(price_from_peak, 4) if price_from_peak else None,
            'price_from_trough_pct': round(price_from_trough, 4) if price_from_trough else None,
            'local_extrema_count': len(window_extrema),
            'local_avg_period_hours': round(avg_local_period, 2) if avg_local_period else None,
            'weekly_avg_period_hours': round(avg_week_period, 2) if avg_week_period else None
        },
        'frequency_analysis': freq_change,
        'wave_alignment': {
            'aligned': aligned_with_wave,
            'reason': alignment_reason
        }
    }


def analyze_all_zro_trades():
    """Analyze all ZRO trades in wave context."""
    trades = get_trade_data()
    zro_trades = [t for t in trades if t.get('coin') == 'ZRO']
    
    print("\n" + "="*80)
    print("ZRO TRADES IN WAVE CONTEXT")
    print("="*80)
    
    results = []
    for trade in zro_trades[-5:]:  # Last 5 trades
        analysis = analyze_trade_in_wave_context(trade)
        results.append(analysis)
        
        print("\n" + "-"*60)
        print(f"Trade: {trade['direction']} @ ${trade['entry']:.4f}")
        print(f"Time: {trade['opened'][:16]} → {trade['closed'][:16]}")
        print(f"PnL: {trade['pnl_pct']:.2f}%")
        
        wc = analysis['wave_context']
        print(f"\nWave Position: {wc['position']}")
        if wc['time_since_peak_hours'] is not None:
            print(f"  Time since peak: {wc['time_since_peak_hours']:.1f}h")
            print(f"  Price from peak: {wc['price_from_peak_pct']:.2f}%")
        if wc['time_since_trough_hours'] is not None:
            print(f"  Time since trough: {wc['time_since_trough_hours']:.1f}h")
            print(f"  Price from trough: {wc['price_from_trough_pct']:.2f}%")
        
        if analysis['frequency_analysis']:
            fa = analysis['frequency_analysis']
            print(f"\nFrequency Analysis:")
            print(f"  Local avg period: {fa['local_avg_hours']}h")
            print(f"  Weekly avg period: {fa['weekly_avg_hours']}h")
            print(f"  Change: {fa['change_pct']}% ({fa['direction']})")
        
        wa = analysis['wave_alignment']
        print(f"\nWave Alignment: {'✓ ALIGNED' if wa['aligned'] else '✗ AGAINST'}")
        print(f"  {wa['reason']}")
    
    return results


def main():
    results = analyze_all_zro_trades()
    
    # Summary statistics
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    
    aligned_trades = [r for r in results if r['wave_alignment']['aligned']]
    against_trades = [r for r in results if not r['wave_alignment']['aligned']]
    
    if aligned_trades:
        avg_pnl_aligned = np.mean([r['trade']['pnl_pct'] for r in aligned_trades])
        print(f"\nWave-Aligned Trades: {len(aligned_trades)}")
        print(f"  Average PnL: {avg_pnl_aligned:.2f}%")
    
    if against_trades:
        avg_pnl_against = np.mean([r['trade']['pnl_pct'] for r in against_trades])
        print(f"\nAgainst-Wave Trades: {len(against_trades)}")
        print(f"  Average PnL: {avg_pnl_against:.2f}%")
    
    # Frequency change correlation
    freq_changes = [r for r in results if r['frequency_analysis'] and 
                    r['frequency_analysis']['direction'] != 'stable']
    if freq_changes:
        print(f"\nTrades During Frequency Changes: {len(freq_changes)}")
        for r in freq_changes:
            fa = r['frequency_analysis']
            print(f"  {r['trade']['entry_time'][:16]} | {fa['direction']} | PnL: {r['trade']['pnl_pct']:.2f}%")


if __name__ == '__main__':
    main()
