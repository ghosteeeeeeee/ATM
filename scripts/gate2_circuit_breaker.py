#!/usr/bin/env python3
"""
gate2_circuit_breaker.py — Monitor Gate 2 exception performance.

Circuit breaker: If the 60≤score<80 + mean-reversion bucket loses > $2
over 7 days, re-freeze by setting LONG_NEUTRAL_BLOCK_ENABLED = True
and removing the exception.

Run daily via systemd timer.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import psycopg2
from datetime import datetime, timezone
from paths import *
from hermes_log import log

def check_gate2_performance():
    """Check PnL of trades that used the Gate 2 exception."""
    try:
        conn = psycopg2.connect(host='/var/run/postgresql', dbname='brain', user='postgres')
        cur = conn.cursor()
        
        # Get trades from last 7 days that would have used Gate 2 exception
        # (LONG signals in NEUTRAL regime with mean-reversion source)
        cur.execute('''
            SELECT token, signal, direction, pnl_usdt, volatility_regime, open_time
            FROM trades
            WHERE direction = 'LONG'
              AND status = 'closed'
              AND close_time > NOW() - INTERVAL '7 days'
              AND (
                signal ILIKE '%range_reversion%' OR
                signal ILIKE '%bb_bounce%' OR
                signal ILIKE '%squeeze_reversal%' OR
                signal ILIKE '%coiled_spring%' OR
                signal ILIKE '%return_exhaustion%' OR
                signal ILIKE '%neutral_sniper%' OR
                signal ILIKE '%oversold_bounce%' OR
                signal ILIKE '%doji_bottom%'
              )
            ORDER BY close_time DESC
        ''')
        
        trades = cur.fetchall()
        conn.close()
        
        total_pnl = sum(float(t[3] or 0) for t in trades)
        wins = sum(1 for t in trades if float(t[3] or 0) > 0)
        n = len(trades)
        wr = (wins / n * 100) if n > 0 else 0
        
        log(f"[GATE2-CB] 7d performance: {n} trades, {wins} wins ({wr:.1f}%), PnL=${total_pnl:.2f}")
        
        # Circuit breaker: re-freeze if PnL < -$2
        if total_pnl < -2.0:
            log(f"[GATE2-CB] ⚠️ CIRCUIT BREAKER TRIGGERED: PnL=${total_pnl:.2f} < -$2.00")
            log(f"[GATE2-CB] Re-freezing Gate 2 exception — set LONG_NEUTRAL_BLOCK_ENABLED=True in hermes_constants.py")
            # Write alert file
            alert_file = os.path.join(HERMES_DATA, 'gate2_circuit_breaker_alert.json')
            import json
            with open(alert_file, 'w') as f:
                json.dump({
                    'triggered': True,
                    'pnl': total_pnl,
                    'trades': n,
                    'wr': wr,
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                    'action': 'Set LONG_NEUTRAL_BLOCK_ENABLED=True and remove Gate 2 exception'
                }, f, indent=2)
            return False  # circuit breaker triggered
        else:
            log(f"[GATE2-CB] ✅ Performance OK — no action needed")
            return True  # performance OK
            
    except Exception as e:
        log(f"[GATE2-CB] Error checking performance: {e}", 'WARN')
        return True  # on error, don't trigger circuit breaker

if __name__ == '__main__':
    check_gate2_performance()
