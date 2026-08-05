#!/usr/bin/env python3
"""
Test Context Gate — Test context gate with custom parameters.
Usage: python3 test_gate.py <TOKEN> <DIRECTION> <SIGNAL> [Z_SCORE]
"""
import sys, os

sys.path.insert(0, '/root/.hermes/scripts')

def test_gate(token, direction, signal, z_score=None):
    """Test context gate with custom parameters."""
    
    from decider_run import context_gate
    
    sig = {'z_score': z_score} if z_score is not None else {}
    
    print(f'=== {token} {direction} ({signal}) — CONTEXT GATE TEST ===')
    if z_score is not None:
        print(f'Z-Score (custom): {z_score:+.2f}')
    print()
    
    verdict, reason, penalty = context_gate(token, direction, signal, sig)
    
    print(f'Verdict: {verdict}')
    print(f'Reason: {reason}')
    print(f'Penalty: {penalty}')
    print()
    
    # Check FLIP
    flip = False
    new_dir = direction
    if z_score is not None:
        if direction == 'LONG' and z_score > 0.5:
            flip = True
            new_dir = 'SHORT'
        elif direction == 'SHORT' and z_score < -0.5:
            flip = True
            new_dir = 'LONG'
    
    print(f'Flip Triggered: {flip}')
    if flip:
        print(f'New Direction: {new_dir}')

if __name__ == '__main__':
    if len(sys.argv) < 4:
        print('Usage: python3 test_gate.py <TOKEN> <DIRECTION> <SIGNAL> [Z_SCORE]')
        print('Example: python3 test_gate.py UNI LONG tl_break_long 1.15')
        sys.exit(1)
    
    token = sys.argv[1].upper()
    direction = sys.argv[2].upper()
    signal = sys.argv[3]
    z_score = float(sys.argv[4]) if len(sys.argv) > 4 else None
    
    test_gate(token, direction, signal, z_score)
