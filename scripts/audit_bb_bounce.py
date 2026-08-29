#!/usr/bin/env python3
"""Independent audit of bb_bounce signal claims."""
import sqlite3
import math
import sys
import os
from datetime import datetime, timezone

sys.path.insert(0, '/root/.hermes/scripts')
from paths import RUNTIME_DB, CANDLES_DB

def get_all_bb_bounce_trades():
    """Get all bb_bounce trades (both LONG and SHORT)."""
    conn = sqlite3.connect(RUNTIME_DB)
    cur = conn.cursor()
    cur.execute("""
        SELECT token, direction, signal_type, is_win, pnl_pct, pnl_usdt, 
               confidence, created_at, closed_at, regime
        FROM signal_outcomes 
        WHERE signal_type LIKE '%bb_bounce%'
        ORDER BY created_at
    """)
    trades = cur.fetchall()
    conn.close()
    return trades

def get_candles_at_time(token, target_ts, lookback=100, timeframe='5m'):
    """Get candles from DB around a specific time."""
    conn = sqlite3.connect(CANDLES_DB)
    cur = conn.cursor()
    table = f'candles_{timeframe}'
    cur.execute(f"""
        SELECT ts, open, high, low, close, volume
        FROM {table}
        WHERE token = ? AND ts <= ?
        ORDER BY ts DESC
        LIMIT ?
    """, (token.upper(), target_ts, lookback))
    rows = cur.fetchall()
    conn.close()
    return list(reversed(rows))

def get_1m_candles_at_time(token, target_ts, lookback=60):
    """Get 1m candles around a specific time."""
    conn = sqlite3.connect(CANDLES_DB)
    cur = conn.cursor()
    cur.execute("""
        SELECT ts, open, high, low, close, volume
        FROM candles_1m
        WHERE token = ? AND ts <= ?
        ORDER BY ts DESC
        LIMIT ?
    """, (token.upper(), target_ts, lookback))
    rows = cur.fetchall()
    conn.close()
    return list(reversed(rows))

def compute_bb(closes, period=20, stddev=1.8):
    """Compute Bollinger Bands."""
    if len(closes) < period:
        return None, None, None, None
    middle = sum(closes[-period:]) / period
    variance = sum((c - middle) ** 2 for c in closes[-period:]) / period
    std = variance ** 0.5
    upper = middle + stddev * std
    lower = middle - stddev * std
    width = (upper - lower) / middle if middle > 0 else 0
    return middle, upper, lower, width

def compute_rsi(closes, period=14):
    """Compute RSI."""
    if len(closes) < period + 1:
        return None
    gains, losses = [], []
    for i in range(1, min(period + 1, len(closes))):
        delta = closes[-i] - closes[-i - 1]
        gains.append(max(delta, 0))
        losses.append(max(-delta, 0))
    avg_gain = sum(gains) / len(gains) if gains else 0
    avg_loss = sum(losses) / len(losses) if losses else 0.001
    rs = avg_gain / avg_loss if avg_loss > 0 else 100
    return 100 - (100 / (1 + rs))

def compute_velocity_15m(closes_1m):
    """Compute 15m velocity from 1m candles."""
    if len(closes_1m) < 5:
        return None
    closes = [c[4] for c in closes_1m]  # close prices
    if closes[0] <= 0:
        return None
    return (closes[-1] - closes[0]) / closes[0] * 100

def compute_velocity_5m(closes_1m):
    """Compute 5m velocity from 1m candles."""
    if len(closes_1m) < 2:
        return None
    closes = [c[4] for c in closes_1m]  # close prices
    if closes[0] <= 0:
        return None
    return (closes[-1] - closes[0]) / closes[0] * 100

def compute_momentum(closes, lookback=10):
    """Compute momentum (price change over lookback)."""
    if len(closes) < lookback:
        return None
    if closes[-lookback] <= 0:
        return None
    return (closes[-1] - closes[-lookback]) / closes[-lookback] * 100

def compute_5m_range(candles_5m):
    """Compute 5m candle range (high-low) as %."""
    if not candles_5m:
        return None
    ranges = []
    for c in candles_5m:
        if c[2] > 0:  # high > 0
            ranges.append((c[2] - c[3]) / c[2] * 100)  # (high - low) / high
    return sum(ranges) / len(ranges) if ranges else None

def analyze_trade(trade):
    """Analyze a single trade with reconstructed metrics."""
    token, direction, signal_type, is_win, pnl_pct, pnl_usdt, confidence, created_at, closed_at, regime = trade
    
    # Parse creation time
    try:
        created_dt = datetime.strptime(created_at, '%Y-%m-%d %H:%M:%S')
        target_ts = int(created_dt.timestamp())
    except:
        return None
    
    result = {
        'token': token,
        'direction': direction,
        'signal_type': signal_type,
        'is_win': is_win,
        'pnl_pct': pnl_pct,
        'pnl_usdt': pnl_usdt,
        'confidence': confidence,
        'created_at': created_at,
        'regime': regime,
    }
    
    # Get 5m candles
    candles_5m = get_candles_at_time(token, target_ts, lookback=100, timeframe='5m')
    if candles_5m and len(candles_5m) >= 30:
        closes_5m = [c[4] for c in candles_5m]
        middle, upper, lower, width = compute_bb(closes_5m)
        if width is not None:
            result['bb_width'] = width
            result['bb_middle'] = middle
            result['bb_upper'] = upper
            result['bb_lower'] = lower
            result['bb_range_pct'] = (upper - lower) / middle * 100 if middle > 0 else 0
        
        # 5m candle range (high-low spread)
        result['candle_range_5m'] = compute_5m_range(candles_5m)
        
        # Momentum from 5m candles
        result['momentum_5m'] = compute_momentum(closes_5m, lookback=10)
        
        # RSI
        result['rsi'] = compute_rsi(closes_5m)
    
    # Get 1m candles for velocity
    candles_1m = get_1m_candles_at_time(token, target_ts, lookback=60)
    if candles_1m:
        # 15m velocity (15 1m candles)
        vel_15m_candles = candles_1m[-15:] if len(candles_1m) >= 15 else candles_1m
        result['vel_15m'] = compute_velocity_15m(vel_15m_candles)
        
        # 5m velocity (5 1m candles)
        vel_5m_candles = candles_1m[-5:] if len(candles_1m) >= 5 else candles_1m
        result['vel_5m'] = compute_velocity_5m(vel_5m_candles)
        
        # Momentum from 1m
        closes_1m = [c[4] for c in candles_1m]
        result['momentum_1m'] = compute_momentum(closes_1m, lookback=10)
    
    return result

def main():
    print("=" * 80)
    print("INDEPENDENT AUDIT: BB_BOUNCE SIGNAL CLAIMS")
    print("=" * 80)
    
    trades = get_all_bb_bounce_trades()
    print(f"\nTotal bb_bounce trades found: {len(trades)}")
    
    # Analyze all trades
    analyses = []
    for trade in trades:
        result = analyze_trade(trade)
        if result:
            analyses.append(result)
    
    print(f"Successfully analyzed: {len(analyses)}")
    
    # Filter to pure bb_bounce signals only (not combos)
    pure_bb = [a for a in analyses if a['signal_type'] in ('bb_bounce', 'bb_bounce+')]
    pure_short = [a for a in analyses if a['signal_type'] in ('bb-bounce-short',)]
    
    print(f"\n{'='*80}")
    print("CLAIM 1: Velocity data source fix improved WR from 63.8% to 66.8%")
    print("=" * 80)
    
    # Count wins/losses
    total = len(pure_bb) + len(pure_short)
    wins = sum(1 for a in pure_bb if a['is_win']) + sum(1 for a in pure_short if a['is_win'])
    wr = 100.0 * wins / total if total > 0 else 0
    print(f"Overall: {total} trades, {wins} wins, {wr:.1f}% WR")
    
    # Split by signal type
    bb_long = [a for a in analyses if a['direction'] == 'LONG']
    bb_short = [a for a in analyses if a['direction'] == 'SHORT']
    
    long_wins = sum(1 for a in bb_long if a['is_win'])
    short_wins = sum(1 for a in bb_short if a['is_win'])
    
    print(f"\nLONG trades: {len(bb_long)} total, {long_wins} wins, {100.0*long_wins/len(bb_long):.1f}% WR")
    print(f"SHORT trades: {len(bb_short)} total, {short_wins} wins, {100.0*short_wins/len(bb_short):.1f}% WR")
    
    print(f"\n{'='*80}")
    print("CLAIM 2: Momentum filter (-0.005 for LONG, +0.005 for SHORT) improves WR to 75-91%")
    print("=" * 80)
    
    # Test momentum filter
    for label, trades_subset, direction, threshold in [
        ("LONG momentum > -0.005", bb_long, 'LONG', -0.005),
        ("SHORT momentum < 0.005", bb_short, 'SHORT', 0.005)
    ]:
        filtered = []
        for a in trades_subset:
            mom = a.get('momentum_5m')
            if mom is not None:
                if direction == 'LONG' and mom > threshold:
                    filtered.append(a)
                elif direction == 'SHORT' and mom < threshold:
                    filtered.append(a)
        
        if filtered:
            filtered_wins = sum(1 for a in filtered if a['is_win'])
            filtered_wr = 100.0 * filtered_wins / len(filtered)
            print(f"{label}: {len(filtered)}/{len(trades_subset)} trades survive, {filtered_wins} wins, {filtered_wr:.1f}% WR")
        else:
            print(f"{label}: No trades survive filter")
    
    print(f"\n{'='*80}")
    print("CLAIM 3: BB width >= 0.5% filter improves WR to 75%")
    print("=" * 80)
    
    # Test BB width filter
    bb_width_filtered = [a for a in analyses if a.get('bb_width') is not None and a['bb_width'] >= 0.005]  # 0.5% as fraction
    if bb_width_filtered:
        width_wins = sum(1 for a in bb_width_filtered if a['is_win'])
        width_wr = 100.0 * width_wins / len(bb_width_filtered)
        print(f"BB width >= 0.5%: {len(bb_width_filtered)}/{len(analyses)} trades survive, {width_wins} wins, {width_wr:.1f}% WR")
    else:
        print("No trades have BB width data")
    
    # Also test as percentage (0.5% = 0.005 as fraction)
    bb_width_filtered_pct = [a for a in analyses if a.get('bb_range_pct') is not None and a['bb_range_pct'] >= 0.5]
    if bb_width_filtered_pct:
        width_wins_pct = sum(1 for a in bb_width_filtered_pct if a['is_win'])
        width_wr_pct = 100.0 * width_wins_pct / len(bb_width_filtered_pct)
        print(f"BB range >= 0.5%: {len(bb_width_filtered_pct)}/{len(analyses)} trades survive, {width_wins_pct} wins, {width_wr_pct:.1f}% WR")
    
    print(f"\n{'='*80}")
    print("CLAIM 4: 5m candle range >= 0.15% filter improves WR to 62.5%")
    print("=" * 80)
    
    range_filtered = [a for a in analyses if a.get('candle_range_5m') is not None and a['candle_range_5m'] >= 0.15]
    if range_filtered:
        range_wins = sum(1 for a in range_filtered if a['is_win'])
        range_wr = 100.0 * range_wins / len(range_filtered)
        print(f"5m range >= 0.15%: {len(range_filtered)}/{len(analyses)} trades survive, {range_wins} wins, {range_wr:.1f}% WR")
    else:
        print("No trades have 5m range data")
    
    print(f"\n{'='*80}")
    print("CLAIM 5: Root cause is velocity gate fires at detection time, not execution time")
    print("=" * 80)
    
    # Analyze velocity at entry time for losing trades
    losers = [a for a in analyses if not a['is_win']]
    print(f"\nLosing trades: {len(losers)}")
    print("\nLosing trades with velocity data:")
    for a in losers:
        vel_15m = a.get('vel_15m')
        vel_5m = a.get('vel_5m')
        mom = a.get('momentum_5m')
        if vel_15m is not None or vel_5m is not None:
            v15 = f"{vel_15m:+.4f}" if vel_15m is not None else "N/A"
            v5 = f"{vel_5m:+.4f}" if vel_5m is not None else "N/A"
            m = f"{mom:+.4f}" if mom is not None else "N/A"
            print(f"  {a['token']:6s} {a['direction']:5s} {a['signal_type']:20s} "
                  f"vel_15m={v15}% vel_5m={v5}% mom={m}% "
                  f"pnl={a['pnl_pct']:+.3f}%")
    
    print(f"\n{'='*80}")
    print("CLAIM 6: All 6+ losing trades share 'falling knife' (LONG) or 'rising knife' (SHORT) pattern")
    print("=" * 80)
    
    falling_knife = 0
    rising_knife = 0
    
    print("\nDetailed analysis of losing trades:")
    for a in losers:
        vel_15m = a.get('vel_15m')
        mom = a.get('momentum_5m')
        
        pattern = "UNKNOWN"
        if a['direction'] == 'LONG' and vel_15m is not None and vel_15m < 0:
            pattern = "FALLING KNIFE"
            falling_knife += 1
        elif a['direction'] == 'SHORT' and vel_15m is not None and vel_15m > 0:
            pattern = "RISING KNIFE"
            rising_knife += 1
        
        v15 = f"{vel_15m:>8.4f}" if vel_15m is not None else "     N/A"
        m = f"{mom:>8.4f}" if mom is not None else "     N/A"
        print(f"  {a['token']:6s} {a['direction']:5s} {a['signal_type']:20s} "
              f"pattern={pattern:15s} vel_15m={v15} "
              f"mom={m} pnl={a['pnl_pct']:+.3f}%")
    
    print(f"\nFalling knife (LONG losers with negative vel): {falling_knife}/{len([a for a in losers if a['direction'] == 'LONG'])}")
    print(f"Rising knife (SHORT losers with positive vel): {rising_knife}/{len([a for a in losers if a['direction'] == 'SHORT'])}")
    
    # Additional analysis
    print(f"\n{'='*80}")
    print("ADDITIONAL ANALYSIS: Filter combinations")
    print("=" * 80)
    
    # Combined filter: vel_15m > -0.005 for LONG, vel_15m < 0.005 for SHORT
    combined_winners = 0
    combined_total = 0
    for a in analyses:
        vel_15m = a.get('vel_15m')
        if vel_15m is None:
            continue
        
        if a['direction'] == 'LONG' and vel_15m > -0.005:
            combined_total += 1
            if a['is_win']:
                combined_winners += 1
        elif a['direction'] == 'SHORT' and vel_15m < 0.005:
            combined_total += 1
            if a['is_win']:
                combined_winners += 1
    
    if combined_total > 0:
        print(f"Velocity filter (LONG > -0.005%, SHORT < 0.005%): {combined_total}/{len(analyses)} trades survive, {combined_winners} wins, {100.0*combined_winners/combined_total:.1f}% WR")
    
    # BB width + momentum
    bb_mom_winners = 0
    bb_mom_total = 0
    for a in analyses:
        bb_width = a.get('bb_range_pct')
        mom = a.get('momentum_5m')
        if bb_width is None or mom is None:
            continue
        
        if a['direction'] == 'LONG' and bb_width >= 0.5 and mom > -0.005:
            bb_mom_total += 1
            if a['is_win']:
                bb_mom_winners += 1
        elif a['direction'] == 'SHORT' and bb_width >= 0.5 and mom < 0.005:
            bb_mom_total += 1
            if a['is_win']:
                bb_mom_winners += 1
    
    if bb_mom_total > 0:
        print(f"BB width + momentum: {bb_mom_total}/{len(analyses)} trades survive, {bb_mom_winners} wins, {100.0*bb_mom_winners/bb_mom_total:.1f}% WR")
    
    # Print raw data for verification
    print(f"\n{'='*80}")
    print("RAW DATA FOR VERIFICATION")
    print("=" * 80)
    print(f"{'Token':6s} {'Dir':5s} {'Type':20s} {'Win':3s} {'PnL%':>8s} {'Conf':>5s} {'Vel15m':>8s} {'Vel5m':>8s} {'Mom5m':>8s} {'BB_W%':>8s} {'CandR':>8s} {'RSI':>6s}")
    for a in analyses:
        v15 = a.get('vel_15m')
        v5 = a.get('vel_5m')
        mom = a.get('momentum_5m')
        bb = a.get('bb_range_pct')
        cr = a.get('candle_range_5m')
        rsi = a.get('rsi')
        
        v15s = f"{v15:+8.4f}" if v15 is not None else "     N/A"
        v5s = f"{v5:+8.4f}" if v5 is not None else "     N/A"
        moms = f"{mom:+8.4f}" if mom is not None else "     N/A"
        bbs = f"{bb:8.4f}" if bb is not None else "     N/A"
        crs = f"{cr:8.4f}" if cr is not None else "     N/A"
        rsis = f"{rsi:6.2f}" if rsi is not None else "   N/A"
        
        print(f"{a['token']:6s} {a['direction']:5s} {a['signal_type']:20s} "
              f"{'W' if a['is_win'] else 'L':3s} "
              f"{a['pnl_pct']:+8.4f} "
              f"{a['confidence']:5.0f} "
              f"{v15s} {v5s} {moms} {bbs} {crs} {rsis}")

if __name__ == '__main__':
    main()
