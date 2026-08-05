#!/usr/bin/env python3
"""
Context Gate Analyzer — Analyze a single trade and test context gate decisions.
Usage: python3 analyze_trade.py <TOKEN> <DIRECTION> <SIGNAL> <ENTRY_TIME>
"""
import sys, os, sqlite3, statistics, datetime

sys.path.insert(0, '/root/.hermes/scripts')

def analyze_trade(token, direction, signal, entry_time_str):
    """Analyze a single trade and test context gate decisions."""
    
    # Parse entry time
    entry_time = datetime.datetime.strptime(entry_time_str, '%Y-%m-%d %H:%M:%S')
    entry_ts = int(entry_time.timestamp())
    
    # Get z-score at entry time
    conn = sqlite3.connect('/root/.hermes/data/signals_hermes.db')
    cur = conn.cursor()
    cur.execute('''
        SELECT timestamp, price FROM price_history 
        WHERE token = ? AND timestamp <= ?
        ORDER BY timestamp DESC
        LIMIT 100
    ''', (token, entry_ts))
    
    rows = cur.fetchall()
    if not rows:
        print(f'{token}: no price data before entry')
        return
    
    prices = [r[1] for r in rows]
    if len(prices) < 20:
        print(f'{token}: insufficient price data')
        return
    
    recent_20 = prices[:20]
    mean = statistics.mean(recent_20)
    stdev = statistics.stdev(recent_20)
    z_score = (recent_20[-1] - mean) / stdev if stdev > 0 else 0
    
    conn.close()
    
    # Get context gate data
    from decider_run import _ctx_gate_get_speed, _ctx_gate_get_phase, _ctx_gate_get_momentum, _ctx_gate_get_market_context, hebbian_trade_boost
    
    speed = _ctx_gate_get_speed(token)
    phase = _ctx_gate_get_phase(token)
    mom_data = _ctx_gate_get_momentum(token)
    market = _ctx_gate_get_market_context()
    heb = hebbian_trade_boost(token, signal)
    
    # Run context gate
    from decider_run import context_gate
    sig = {'z_score': z_score}
    verdict, reason, penalty = context_gate(token, direction, signal, sig)
    
    # Check if FLIP would have triggered
    flip = False
    new_dir = direction
    if direction == 'LONG' and z_score > 0.5:
        flip = True
        new_dir = 'SHORT'
    elif direction == 'SHORT' and z_score < -0.5:
        flip = True
        new_dir = 'LONG'
    
    # Print results
    print(f'=== {token} {direction} ({signal}) ===')
    print(f'Entry Time: {entry_time_str}')
    print(f'Z-Score at entry: {z_score:+.2f}')
    print(f'Speed: {speed}%')
    print(f'Phase: {phase}')
    print(f'Momentum: {mom_data}')
    print(f'Market: {market}')
    print()
    
    if heb:
        wr, n, weight, concepts = heb
        print(f'Hebbian WR: {wr*100:.0f}% (n={n}, weight={weight:.2f})')
        if concepts:
            print(f'Hebbian Concepts:')
            for concept, label, cw, cn in concepts[:5]:
                print(f'  {concept}: weight={cw:.1f}, trades={cn}')
    else:
        print('Hebbian: No data')
    print()
    
    print(f'Context Gate Verdict: {verdict}')
    print(f'Reason: {reason}')
    print(f'Confidence Penalty: {penalty}')
    print()
    
    print(f'Flip Triggered: {flip}')
    if flip:
        print(f'New Direction: {new_dir}')
    print()

if __name__ == '__main__':
    if len(sys.argv) < 5:
        print('Usage: python3 analyze_trade.py <TOKEN> <DIRECTION> <SIGNAL> <ENTRY_TIME>')
        print('Example: python3 analyze_trade.py TNSR LONG tl_break_long "2026-07-29 20:30:00"')
        sys.exit(1)
    
    token = sys.argv[1].upper()
    direction = sys.argv[1].upper()
    signal = sys.argv[3]
    entry_time_str = sys.argv[4]
    
    analyze_trade(token, direction, signal, entry_time_str)
