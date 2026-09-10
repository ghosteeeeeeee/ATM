#!/usr/bin/env python3
"""
Volatility Breakdown — Signal Performance by Regime

Analyze how a signal performs across different volatility regimes.
Usage: python3 volatility_breakdown.py <signal_source>
Example: python3 volatility_breakdown.py pullback-entry+
"""

import sys
import os
import sqlite3

# Add scripts to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'scripts'))

def volatility_breakdown(signal_source, days=30):
    """
    Generate volatility regime breakdown for a signal.
    
    Args:
        signal_source: Signal source string (e.g., 'pullback-entry+', 'bb-bounce-short')
        days: Number of days to look back (default: 30)
    
    Returns:
        str: Formatted breakdown table
    """
    try:
        import psycopg2
        conn = psycopg2.connect(host='/var/run/postgresql', database='brain',
                                user='postgres', connect_timeout=5)
    except Exception as e:
        return f"Error connecting to database: {e}"
    
    cur = conn.cursor()
    
    # Query trades for the signal
    query = """
        SELECT 
            volatility_regime,
            COUNT(*) as total,
            SUM(CASE WHEN pnl_usdt > 0 THEN 1 ELSE 0 END) as wins,
            SUM(CASE WHEN pnl_usdt <= 0 THEN 1 ELSE 0 END) as losses,
            SUM(pnl_usdt) as total_pnl
        FROM trades 
        WHERE signal LIKE %s 
          AND close_time IS NOT NULL
          AND volatility_regime IS NOT NULL
          AND volatility_regime != ''
        GROUP BY volatility_regime
        ORDER BY 
            CASE volatility_regime 
                WHEN 'EXTREME' THEN 1
                WHEN 'HIGH' THEN 2
                WHEN 'NORMAL' THEN 3
                WHEN 'FLAT' THEN 4
                ELSE 5
            END
    """
    
    cur.execute(query, (f'%{signal_source}%',))
    results = cur.fetchall()
    
    # Also get total
    total_query = """
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN pnl_usdt > 0 THEN 1 ELSE 0 END) as wins,
            SUM(pnl_usdt) as total_pnl
        FROM trades 
        WHERE signal LIKE %s 
          AND close_time IS NOT NULL
          AND volatility_regime IS NOT NULL
          AND volatility_regime != ''
    """
    cur.execute(total_query, (f'%{signal_source}%',))
    total = cur.fetchone()
    
    conn.close()
    
    if not results:
        return f"No trades found for signal '{signal_source}' with volatility regime data"
    
    # Format output
    lines = []
    lines.append(f"Volatility Breakdown: {signal_source}")
    lines.append("=" * 50)
    lines.append("")
    lines.append("By Regime:")
    lines.append("")
    lines.append(f"{'Regime':<10} {'WR':<15} {'PnL':>10}")
    lines.append("-" * 40)
    
    for regime, total_trades, wins, losses, pnl in results:
        wr = (wins / total_trades * 100) if total_trades > 0 else 0
        pnl_str = f"${pnl:+.2f}" if pnl else "—"
        wr_str = f"{wr:.0f}% ({wins}W/{losses}L)" if total_trades > 0 else "(no trades)"
        lines.append(f"{regime:<10} {wr_str:<15} {pnl_str:>10}")
    
    lines.append("-" * 40)
    
    if total and total[0] > 0:
        total_wr = (total[1] / total[0] * 100) if total[0] > 0 else 0
        total_pnl = total[2] if total[2] else 0
        lines.append(f"Total: {total_wr:.0f}% WR ({total[1]}W/{total[0]-total[1]}L), ${total_pnl:+.2f}")
        
        # Find worst regime
        worst_regime = min(results, key=lambda x: (x[2]/x[1] if x[1] > 0 else 0))
        worst_wr = (worst_regime[2] / worst_regime[1] * 100) if worst_regime[1] > 0 else 0
        lines.append(f"\nKey insight: The signal performs worst in {worst_regime[0]} ({worst_wr:.0f}% WR).")
    
    return "\n".join(lines)


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python3 volatility_breakdown.py <signal_source>")
        print("Example: python3 volatility_breakdown.py pullback-entry+")
        sys.exit(1)
    
    signal_source = sys.argv[1]
    result = volatility_breakdown(signal_source)
    print(result)
