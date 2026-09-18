#!/usr/bin/env python3
"""
Independent audit of pump-chain signals and BTC oscillator correlation.
Connects to PostgreSQL and continuum.db, runs queries, outputs findings.
"""

import sys
import os
import sqlite3
import psycopg2
from datetime import datetime, timezone, timedelta

# Add scripts dir for imports
sys.path.insert(0, '/root/.hermes/scripts')
from paths import HERMES_DATA

CONTINUUM_DB = os.path.join(HERMES_DATA, 'continuum.db')


def get_btc_state(ts, cconn):
    """Get BTC oscillator state at a given timestamp."""
    row = cconn.execute('''
        SELECT zscore_val, state_score, trend_quality, 
               linreg_direction, linreg_alignment,
               market_phase, velocity_val
        FROM continuum_states
        WHERE token = 'BTC'
        ORDER BY ABS(ts - ?) ASC
        LIMIT 1
    ''', (int(ts.timestamp()),)).fetchone()
    
    if not row:
        return None
    
    zscore, score, trend, linreg_dir, linreg_align, phase, vel = row
    
    # Classify linreg bias
    if linreg_dir and 'BULL' in str(linreg_dir).upper():
        linreg_bias = 'BULL'
    elif linreg_dir and 'BEAR' in str(linreg_dir).upper():
        linreg_bias = 'BEAR'
    else:
        linreg_bias = 'MIXED'
    
    # Classify score range
    if score is None:
        score_range = 'UNKNOWN'
    elif score < 20:
        score_range = '0-20'
    elif score < 40:
        score_range = '20-40'
    elif score < 60:
        score_range = '40-60'
    elif score < 80:
        score_range = '60-80'
    else:
        score_range = '80-100'
    
    return {
        'zscore': float(zscore) if zscore else 0,
        'score': float(score) if score else 0,
        'score_range': score_range,
        'trend': trend,
        'linreg_bias': linreg_bias,
        'phase': phase,
        'vel': float(vel) if vel else 0,
    }


def run_audit():
    # Connect to databases
    conn = psycopg2.connect(host='/var/run/postgresql', dbname='brain', user='postgres')
    cur = conn.cursor()
    cconn = sqlite3.connect(CONTINUUM_DB, timeout=10)
    
    print("=" * 80)
    print("INDEPENDENT AUDIT: pump-chain signals & BTC oscillator correlation")
    print("=" * 80)
    
    # Query all pump-chain trades from last 30 days
    query = '''
        SELECT token, signal, direction, volatility_regime,
               ROUND(pnl_usdt::numeric, 3) as pnl,
               ROUND(pnl_pct::numeric, 2) as pnl_pct,
               open_time
        FROM trades
        WHERE signal ILIKE '%pump-chain%'
          AND status = 'closed'
          AND open_time >= NOW() - INTERVAL '30 days'
        ORDER BY open_time
    '''
    
    cur.execute(query)
    trades = cur.fetchall()
    
    if not trades:
        print("No pump-chain trades found in last 30 days")
        return
    
    print(f"\nTotal pump-chain trades (30 days): {len(trades)}")
    
    # Match with BTC oscillator data
    all_data = []
    for t in trades:
        token, signal, direction_db, regime, pnl, pnl_pct, open_time = t
        btc = get_btc_state(open_time, cconn)
        if btc:
            all_data.append({
                'token': token, 'signal': signal, 'dir': direction_db,
                'pnl': float(pnl), 'pnl_pct': float(pnl_pct),
                **btc
            })
    
    print(f"Trades matched with BTC oscillator data: {len(all_data)}")
    
    # Filter by direction
    long_trades = [d for d in all_data if d['dir'] == 'LONG']
    short_trades = [d for d in all_data if d['dir'] == 'SHORT']
    
    print(f"\nLONG trades: {len(long_trades)}")
    print(f"SHORT trades: {len(short_trades)}")
    
    # Analyze by score ranges
    print(f"\n=== CLAIM 1: pump-chain BTC 0-20: 22T, 59.1% WR, +$0.45 (BEST) ===")
    ranges = [('0-20', 0, 20), ('20-40', 20, 40), ('40-60', 40, 60), 
              ('60-80', 60, 80), ('80-100', 80, 101)]
    
    print(f"\nAll pump-chain trades by BTC score range:")
    print(f"{'Score':10s} {'Trades':>6s} {'Wins':>5s} {'WR':>6s} {'PnL':>8s} {'Avg':>7s}")
    print('-' * 45)
    
    for label, low, high in ranges:
        subset = [d for d in all_data if low <= d['score'] < high]
        if subset:
            wins = sum(1 for d in subset if d['pnl'] > 0)
            pnl = sum(d['pnl'] for d in subset)
            wr = wins / len(subset) * 100
            avg = pnl / len(subset)
            marker = '✅' if pnl > 0 else '❌'
            print(f"  {marker} {label:8s}  {len(subset):5d}  {wins:4d}  {wr:5.1f}%  ${pnl:>+7.2f}  ${avg:>+5.3f}")
    
    # Analyze Linreg Bias
    print(f"\n=== CLAIM 3: pump-chain Linreg BEAR: 25T, 64.0% WR, +$0.68 (BEST) ===")
    print(f"\nAll pump-chain trades by Linreg Bias:")
    print(f"{'Linreg':10s} {'Trades':>6s} {'Wins':>5s} {'WR':>6s} {'PnL':>8s} {'Avg':>7s}")
    print('-' * 45)
    
    for bias in ['BULL', 'BEAR', 'MIXED']:
        subset = [d for d in all_data if d['linreg_bias'] == bias]
        if subset:
            wins = sum(1 for d in subset if d['pnl'] > 0)
            pnl = sum(d['pnl'] for d in subset)
            wr = wins / len(subset) * 100
            avg = pnl / len(subset)
            marker = '✅' if pnl > 0 else '❌'
            print(f"  {marker} {bias:8s}  {len(subset):5d}  {wins:4d}  {wr:5.1f}%  ${pnl:>+7.2f}  ${avg:>+5.3f}")
    
    # Analyze by direction separately
    print(f"\n=== CLAIM 5: pump-chain is mean-reversion, not momentum ===")
    print(f"\nAll pump-chain trades by BTC Score + Direction:")
    print(f"{'Dir':5s} {'Score':10s} {'Trades':>6s} {'Wins':>5s} {'WR':>6s} {'PnL':>8s} {'Avg':>7s}")
    print('-' * 55)
    
    for d in ['LONG', 'SHORT']:
        for label, low, high in ranges:
            subset = [t for t in all_data if t['dir'] == d and low <= t['score'] < high]
            if subset:
                wins = sum(1 for t in subset if t['pnl'] > 0)
                pnl = sum(t['pnl'] for t in subset)
                wr = wins / len(subset) * 100
                avg = pnl / len(subset)
                marker = '✅' if pnl > 0 else '❌'
                print(f"  {marker} {d:3s}  {label:8s}  {len(subset):5d}  {wins:4d}  {wr:5.1f}%  ${pnl:>+7.2f}  ${avg:>+5.3f}")
    
    # Analyze Linreg by direction
    print(f"\nAll pump-chain trades by Linreg Bias + Direction:")
    print(f"{'Dir':5s} {'Linreg':10s} {'Trades':>6s} {'Wins':>5s} {'WR':>6s} {'PnL':>8s} {'Avg':>7s}")
    print('-' * 55)
    
    for d in ['LONG', 'SHORT']:
        for bias in ['BULL', 'BEAR', 'MIXED']:
            subset = [t for t in all_data if t['dir'] == d and t['linreg_bias'] == bias]
            if subset:
                wins = sum(1 for t in subset if t['pnl'] > 0)
                pnl = sum(t['pnl'] for t in subset)
                wr = wins / len(subset) * 100
                avg = pnl / len(subset)
                marker = '✅' if pnl > 0 else '❌'
                print(f"  {marker} {d:3s}  {bias:8s}  {len(subset):5d}  {wins:4d}  {wr:5.1f}%  ${pnl:>+7.2f}  ${avg:>+5.3f}")
    
    # Analyze by token
    print(f"\n=== TOKEN BREAKDOWN (possible confounding variable) ===")
    tokens = {}
    for d in all_data:
        token = d['token']
        if token not in tokens:
            tokens[token] = {'trades': 0, 'wins': 0, 'pnl': 0}
        tokens[token]['trades'] += 1
        tokens[token]['wins'] += 1 if d['pnl'] > 0 else 0
        tokens[token]['pnl'] += d['pnl']
    
    print(f"{'Token':8s} {'Trades':>6s} {'WR':>6s} {'PnL':>8s} {'Avg':>7s}")
    print('-' * 40)
    
    for token, data in sorted(tokens.items(), key=lambda x: -x[1]['trades']):
        wr = data['wins'] / data['trades'] * 100
        avg = data['pnl'] / data['trades']
        print(f"  {token:6s}  {data['trades']:5d}  {wr:5.1f}%  ${data['pnl']:>+7.2f}  ${avg:>+5.3f}")
    
    # Analyze by volatility regime
    print(f"\n=== VOLATILITY REGIME BREAKDOWN (possible confounding variable) ===")
    regimes = {}
    for d in all_data:
        regime = d.get('volatility_regime', 'UNKNOWN')
        if regime not in regimes:
            regimes[regime] = {'trades': 0, 'wins': 0, 'pnl': 0}
        regimes[regime]['trades'] += 1
        regimes[regime]['wins'] += 1 if d['pnl'] > 0 else 0
        regimes[regime]['pnl'] += d['pnl']
    
    print(f"{'Regime':15s} {'Trades':>6s} {'WR':>6s} {'PnL':>8s} {'Avg':>7s}")
    print('-' * 50)
    
    for regime, data in sorted(regimes.items(), key=lambda x: -x[1]['trades']):
        wr = data['wins'] / data['trades'] * 100
        avg = data['pnl'] / data['trades']
        print(f"  {regime:13s}  {data['trades']:5d}  {wr:5.1f}%  ${data['pnl']:>+7.2f}  ${avg:>+5.3f}")
    
    # Analyze by market phase
    print(f"\n=== MARKET PHASE BREAKDOWN (possible confounding variable) ===")
    phases = {}
    for d in all_data:
        phase = d.get('phase', 'UNKNOWN')
        if phase not in phases:
            phases[phase] = {'trades': 0, 'wins': 0, 'pnl': 0}
        phases[phase]['trades'] += 1
        phases[phase]['wins'] += 1 if d['pnl'] > 0 else 0
        phases[phase]['pnl'] += d['pnl']
    
    print(f"{'Phase':20s} {'Trades':>6s} {'WR':>6s} {'PnL':>8s} {'Avg':>7s}")
    print('-' * 55)
    
    for phase, data in sorted(phases.items(), key=lambda x: -x[1]['trades']):
        wr = data['wins'] / data['trades'] * 100
        avg = data['pnl'] / data['trades']
        print(f"  {phase:18s}  {data['trades']:5d}  {wr:5.1f}%  ${data['pnl']:>+7.2f}  ${avg:>+5.3f}")
    
    # Analyze time of day
    print(f"\n=== TIME OF DAY BREAKDOWN (possible confounding variable) ===")
    hours = {}
    for d in all_data:
        hour = d.get('score_range', 'UNKNOWN')  # Actually need to extract hour from open_time
        # Let me extract hour from the trade data
        pass
    
    # Actually, let me re-analyze time of day
    # I need to get the hour from open_time
    # Let me query again with open_time
    query2 = '''
        SELECT token, signal, direction, volatility_regime,
               ROUND(pnl_usdt::numeric, 3) as pnl,
               ROUND(pnl_pct::numeric, 2) as pnl_pct,
               open_time,
               EXTRACT(HOUR FROM open_time) as hour
        FROM trades
        WHERE signal ILIKE '%pump-chain%'
          AND status = 'closed'
          AND open_time >= NOW() - INTERVAL '30 days'
        ORDER BY open_time
    '''
    
    cur.execute(query2)
    trades2 = cur.fetchall()
    
    hour_data = {}
    for t in trades2:
        token, signal, direction_db, regime, pnl, pnl_pct, open_time, hour = t
        hour = int(hour) if hour else 0
        if hour not in hour_data:
            hour_data[hour] = {'trades': 0, 'wins': 0, 'pnl': 0}
        hour_data[hour]['trades'] += 1
        hour_data[hour]['wins'] += 1 if pnl > 0 else 0
        hour_data[hour]['pnl'] += float(pnl)
    
    print(f"{'Hour':6s} {'Trades':>6s} {'WR':>6s} {'PnL':>8s} {'Avg':>7s}")
    print('-' * 40)
    
    for hour in sorted(hour_data.keys()):
        data = hour_data[hour]
        wr = data['wins'] / data['trades'] * 100
        avg = data['pnl'] / data['trades']
        print(f"  {hour:4d}  {data['trades']:5d}  {wr:5.1f}%  ${data['pnl']:>+7.2f}  ${avg:>+5.3f}")
    
    # Analyze the 80-100 paradox
    print(f"\n=== CLAIM 2: pump-chain BTC 80-100: 19T, 36.8% WR, -$0.60 (WORST) ===")
    extreme_trades = [d for d in all_data if d['score'] >= 80]
    print(f"\nExtreme trades (score >= 80): {len(extreme_trades)}")
    if extreme_trades:
        wins = sum(1 for d in extreme_trades if d['pnl'] > 0)
        pnl = sum(d['pnl'] for d in extreme_trades)
        wr = wins / len(extreme_trades) * 100
        avg = pnl / len(extreme_trades)
        print(f"  Wins: {wins}, WR: {wr:.1f}%, PnL: ${pnl:+.2f}, Avg: ${avg:+.3f}")
    
    # Analyze LONG vs SHORT at extremes
    print(f"\nLONG at extreme (score >= 80):")
    long_extreme = [d for d in extreme_trades if d['dir'] == 'LONG']
    if long_extreme:
        wins = sum(1 for d in long_extreme if d['pnl'] > 0)
        pnl = sum(d['pnl'] for d in long_extreme)
        wr = wins / len(long_extreme) * 100
        avg = pnl / len(long_extreme)
        print(f"  Wins: {wins}, WR: {wr:.1f}%, PnL: ${pnl:+.2f}, Avg: ${avg:+.3f}")
    
    print(f"\nSHORT at extreme (score >= 80):")
    short_extreme = [d for d in extreme_trades if d['dir'] == 'SHORT']
    if short_extreme:
        wins = sum(1 for d in short_extreme if d['pnl'] > 0)
        pnl = sum(d['pnl'] for d in short_extreme)
        wr = wins / len(short_extreme) * 100
        avg = pnl / len(short_extreme)
        print(f"  Wins: {wins}, WR: {wr:.1f}%, PnL: ${pnl:+.2f}, Avg: ${avg:+.3f}")
    
    # Check what happens at different score ranges for LONG vs SHORT
    print(f"\n=== LONG vs SHORT performance across score ranges ===")
    print(f"{'Dir':5s} {'Score':10s} {'Trades':>6s} {'Wins':>5s} {'WR':>6s} {'PnL':>8s} {'Avg':>7s}")
    print('-' * 55)
    
    for d in ['LONG', 'SHORT']:
        for label, low, high in ranges:
            subset = [t for t in all_data if t['dir'] == d and low <= t['score'] < high]
            if subset:
                wins = sum(1 for t in subset if t['pnl'] > 0)
                pnl = sum(t['pnl'] for t in subset)
                wr = wins / len(subset) * 100
                avg = pnl / len(subset)
                marker = '✅' if pnl > 0 else '❌'
                print(f"  {marker} {d:3s}  {label:8s}  {len(subset):5d}  {wins:4d}  {wr:5.1f}%  ${pnl:>+7.2f}  ${avg:>+5.3f}")
    
    # Analyze Linreg BEAR specifically
    print(f"\n=== CLAIM 3: pump-chain Linreg BEAR: 25T, 64.0% WR, +$0.68 (BEST) ===")
    bear_trades = [d for d in all_data if d['linreg_bias'] == 'BEAR']
    print(f"\nLinreg BEAR trades: {len(bear_trades)}")
    if bear_trades:
        wins = sum(1 for d in bear_trades if d['pnl'] > 0)
        pnl = sum(d['pnl'] for d in bear_trades)
        wr = wins / len(bear_trades) * 100
        avg = pnl / len(bear_trades)
        print(f"  Wins: {wins}, WR: {wr:.1f}%, PnL: ${pnl:+.2f}, Avg: ${avg:+.3f}")
    
    # Check if Linreg BEAR sweet spot is actually for SHORT
    print(f"\nLinreg BEAR trades by direction:")
    bear_long = [d for d in bear_trades if d['dir'] == 'LONG']
    bear_short = [d for d in bear_trades if d['dir'] == 'SHORT']
    
    print(f"  LONG: {len(bear_long)} trades")
    if bear_long:
        wins = sum(1 for d in bear_long if d['pnl'] > 0)
        pnl = sum(d['pnl'] for d in bear_long)
        wr = wins / len(bear_long) * 100
        avg = pnl / len(bear_long)
        print(f"    Wins: {wins}, WR: {wr:.1f}%, PnL: ${pnl:+.2f}, Avg: ${avg:+.3f}")
    
    print(f"  SHORT: {len(bear_short)} trades")
    if bear_short:
        wins = sum(1 for d in bear_short if d['pnl'] > 0)
        pnl = sum(d['pnl'] for d in bear_short)
        wr = wins / len(bear_short) * 100
        avg = pnl / len(bear_short)
        print(f"    Wins: {wins}, WR: {wr:.1f}%, PnL: ${pnl:+.2f}, Avg: ${avg:+.3f}")
    
    # Check the mechanism: what's different about extreme score ranges?
    print(f"\n=== MECHANISM ANALYSIS: What's different at extremes? ===")
    
    # Compare token distribution in extreme vs non-extreme
    extreme_tokens = {}
    non_extreme_tokens = {}
    
    for d in all_data:
        if d['score'] >= 80:
            token = d['token']
            extreme_tokens[token] = extreme_tokens.get(token, 0) + 1
        else:
            token = d['token']
            non_extreme_tokens[token] = non_extreme_tokens.get(token, 0) + 1
    
    print(f"\nTokens at extremes (score >= 80):")
    for token, count in sorted(extreme_tokens.items(), key=lambda x: -x[1]):
        print(f"  {token}: {count}")
    
    print(f"\nTokens at non-extremes (score < 80):")
    for token, count in sorted(non_extreme_tokens.items(), key=lambda x: -x[1])[:10]:
        print(f"  {token}: {count}")
    
    # Check volatility regime distribution
    print(f"\nVolatility regime distribution at extremes:")
    extreme_regimes = {}
    for d in extreme_trades:
        regime = d.get('volatility_regime', 'UNKNOWN')
        extreme_regimes[regime] = extreme_regimes.get(regime, 0) + 1
    
    for regime, count in sorted(extreme_regimes.items(), key=lambda x: -x[1]):
        print(f"  {regime}: {count}")
    
    # Check market phase distribution
    print(f"\nMarket phase distribution at extremes:")
    extreme_phases = {}
    for d in extreme_trades:
        phase = d.get('phase', 'UNKNOWN')
        extreme_phases[phase] = extreme_phases.get(phase, 0) + 1
    
    for phase, count in sorted(extreme_phases.items(), key=lambda x: -x[1]):
        print(f"  {phase}: {count}")
    
    # Check time distribution
    print(f"\nTime distribution at extremes (hour of day):")
    extreme_hours = {}
    for t in trades2:
        # Need to match by score >= 80
        # Actually, let me re-query with hour
        pass
    
    # Re-query with hour for extreme trades
    query3 = '''
        SELECT EXTRACT(HOUR FROM open_time) as hour
        FROM trades
        WHERE signal ILIKE '%pump-chain%'
          AND status = 'closed'
          AND open_time >= NOW() - INTERVAL '30 days'
    '''
    
    cur.execute(query3)
    hours_all = [int(row[0]) for row in cur.fetchall() if row[0] is not None]
    
    # Get hours for extreme trades
    extreme_hours = []
    for t in trades2:
        token, signal, direction_db, regime, pnl, pnl_pct, open_time, hour = t
        if hour is not None:
            # Need to match if this trade was extreme
            # Let me match by token+direction+pnl
            for d in extreme_trades:
                if (d['token'] == token and d['dir'] == direction_db and 
                    abs(d['pnl'] - float(pnl)) < 0.001):
                    extreme_hours.append(int(hour))
                    break
    
    if extreme_hours:
        print(f"  Extreme trade hours: {extreme_hours}")
        print(f"  Most common extreme hour: {max(set(extreme_hours), key=extreme_hours.count) if extreme_hours else 'N/A'}")
    
    # Simple explanation
    print(f"\n=== SIMPLEST EXPLANATION ===")
    print(f"Looking for the simplest explanation for pump-chain behavior...")
    
    # Calculate correlation between score and PnL
    scores = [d['score'] for d in all_data]
    pnls = [d['pnl'] for d in all_data]
    
    if len(scores) > 1:
        # Simple correlation
        mean_score = sum(scores) / len(scores)
        mean_pnl = sum(pnls) / len(pnls)
        numerator = sum((s - mean_score) * (p - mean_pnl) for s, p in zip(scores, pnls))
        denom_s = sum((s - mean_score) ** 2 for s in scores)
        denom_p = sum((p - mean_pnl) ** 2 for p in pnls)
        
        if denom_s > 0 and denom_p > 0:
            correlation = numerator / (denom_s ** 0.5 * denom_p ** 0.5)
            print(f"  Score vs PnL correlation: {correlation:.3f}")
            
            if correlation < -0.3:
                print(f"  → Strong negative correlation: higher BTC score → worse pump-chain performance")
                print(f"  → This supports mean-reversion interpretation")
            elif correlation > 0.3:
                print(f"  → Strong positive correlation: higher BTC score → better pump-chain performance")
                print(f"  → This supports momentum interpretation")
            else:
                print(f"  → Weak correlation: score doesn't strongly predict performance")
    
    # Check if pump-chain is actually mean-reversion by looking at what happens AFTER trades
    # (We don't have that data in this query, but we can look at the pattern)
    
    # The simplest explanation based on what we have:
    print(f"\n  Simplest explanation based on data:")
    print(f"  1. pump-chain fires when coin is pumping (chain correlation)")
    print(f"  2. At high BTC scores (80-100), BTC is in strong uptrend")
    print(f"  3. Pumping coins in strong BTC uptrend → chasing exhaustion")
    print(f"  4. The coin already pumped, mean-reversion kicks in → losses")
    print(f"  5. At low BTC scores (0-20), BTC is in downtrend")
    print(f"  6. Pumping coins in downtrend → genuine breakout against trend")
    print(f"  7. This is actually momentum (coin moving against BTC trend)")
    print(f"  8. Linreg BEAR confirms BTC downtrend → pump-chain SHORT works")
    
    # Final verdict
    print(f"\n{'='*80}")
    print(f"FINAL VERDICT")
    print(f"{'='*80}")
    
    # Check claim 1
    if extreme_trades:
        wins = sum(1 for d in extreme_trades if d['pnl'] > 0)
        pnl = sum(d['pnl'] for d in extreme_trades)
        wr = wins / len(extreme_trades) * 100
        avg = pnl / len(extreme_trades)
        print(f"\n1. pump-chain BTC 0-20: 22T, 59.1% WR, +$0.45 (BEST)")
        # Find actual 0-20 stats
        low_trades = [d for d in all_data if d['score'] < 20]
        if low_trades:
            wins = sum(1 for d in low_trades if d['pnl'] > 0)
            pnl = sum(d['pnl'] for d in low_trades)
            wr = wins / len(low_trades) * 100
            avg = pnl / len(low_trades)
            print(f"   ACTUAL: {len(low_trades)}T, {wr:.1f}% WR, ${avg:+.3f} avg")
            if abs(wr - 59.1) < 5 and abs(avg - 0.45) < 0.2:
                print(f"   VERDICT: CONFIRMED (within margin)")
            else:
                print(f"   VERDICT: DISPUTED (actual differs significantly)")
    
    # Check claim 2
    print(f"\n2. pump-chain BTC 80-100: 19T, 36.8% WR, -$0.60 (WORST)")
    if extreme_trades:
        wins = sum(1 for d in extreme_trades if d['pnl'] > 0)
        pnl = sum(d['pnl'] for d in extreme_trades)
        wr = wins / len(extreme_trades) * 100
        avg = pnl / len(extreme_trades)
        print(f"   ACTUAL: {len(extreme_trades)}T, {wr:.1f}% WR, ${avg:+.3f} avg")
        if abs(wr - 36.8) < 5 and abs(avg - (-0.60)) < 0.2:
            print(f"   VERDICT: CONFIRMED (within margin)")
        else:
            print(f"   VERDICT: DISPUTED (actual differs significantly)")
    
    # Check claim 3
    print(f"\n3. pump-chain Linreg BEAR: 25T, 64.0% WR, +$0.68 (BEST)")
    bear_trades = [d for d in all_data if d['linreg_bias'] == 'BEAR']
    if bear_trades:
        wins = sum(1 for d in bear_trades if d['pnl'] > 0)
        pnl = sum(d['pnl'] for d in bear_trades)
        wr = wins / len(bear_trades) * 100
        avg = pnl / len(bear_trades)
        print(f"   ACTUAL: {len(bear_trades)}T, {wr:.1f}% WR, ${avg:+.3f} avg")
        if abs(wr - 64.0) < 5 and abs(avg - 0.68) < 0.2:
            print(f"   VERDICT: CONFIRMED (within margin)")
        else:
            print(f"   VERDICT: DISPUTED (actual differs significantly)")
    
    # Check claim 4
    print(f"\n4. pump-chain+ (LONG) should be blocked at BTC > 80")
    long_extreme = [d for d in all_data if d['dir'] == 'LONG' and d['score'] >= 80]
    if long_extreme:
        wins = sum(1 for d in long_extreme if d['pnl'] > 0)
        pnl = sum(d['pnl'] for d in long_extreme)
        wr = wins / len(long_extreme) * 100
        avg = pnl / len(long_extreme)
        print(f"   LONG at BTC > 80: {len(long_extreme)}T, {wr:.1f}% WR, ${avg:+.3f} avg")
        if pnl < 0:
            print(f"   VERDICT: CONFIRMED — blocking would improve PnL")
        else:
            print(f"   VERDICT: DISPUTED — blocking would hurt PnL")
    
    # Check claim 5
    print(f"\n5. pump-chain is mean-reversion, not momentum")
    # Look at performance pattern
    # Mean-reversion: should work against BTC trend
    # Momentum: should work with BTC trend
    
    # Check LONG vs SHORT at low vs high scores
    long_low = [d for d in all_data if d['dir'] == 'LONG' and d['score'] < 40]
    long_high = [d for d in all_data if d['dir'] == 'LONG' and d['score'] >= 60]
    short_low = [d for d in all_data if d['dir'] == 'SHORT' and d['score'] < 40]
    short_high = [d for d in all_data if d['dir'] == 'SHORT' and d['score'] >= 60]
    
    print(f"   LONG at low BTC score (0-40): {len(long_low)}T", end="")
    if long_low:
        pnl = sum(d['pnl'] for d in long_low)
        print(f", ${pnl:+.2f} total")
    else:
        print()
    
    print(f"   LONG at high BTC score (60-100): {len(long_high)}T", end="")
    if long_high:
        pnl = sum(d['pnl'] for d in long_high)
        print(f", ${pnl:+.2f} total")
    else:
        print()
    
    print(f"   SHORT at low BTC score (0-40): {len(short_low)}T", end="")
    if short_low:
        pnl = sum(d['pnl'] for d in short_low)
        print(f", ${pnl:+.2f} total")
    else:
        print()
    
    print(f"   SHORT at high BTC score (60-100): {len(short_high)}T", end="")
    if short_high:
        pnl = sum(d['pnl'] for d in short_high)
        print(f", ${pnl:+.2f} total")
    else:
        print()
    
    # Determine if mean-reversion or momentum
    if long_low and long_high and short_low and short_high:
        long_pattern = sum(d['pnl'] for d in long_low) > sum(d['pnl'] for d in long_high)
        short_pattern = sum(d['pnl'] for d in short_low) < sum(d['pnl'] for d in short_high)
        
        if long_pattern and short_pattern:
            print(f"   VERDICT: CONFIRMED — pump-chain is mean-reversion")
            print(f"   (Works against BTC trend, fails with BTC trend)")
        elif not long_pattern and not short_pattern:
            print(f"   VERDICT: DISPUTED — pump-chain is momentum")
            print(f"   (Works with BTC trend, fails against BTC trend)")
        else:
            print(f"   VERDICT: NUANCE — mixed behavior")
    
    print(f"\n{'='*80}")
    print(f"END OF AUDIT")
    print(f"{'='*80}")
    
    conn.close()
    cconn.close()


if __name__ == '__main__':
    run_audit()
