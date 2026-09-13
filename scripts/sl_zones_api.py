#!/usr/bin/env python3
"""
sl_zones_api.py — SL Zone Dashboard API

Generates JSON data for the SL zone visualization dashboard.
Writes to /var/www/hermes/data/sl_zones.json

Part of the SL Memory S/R System (v2.0)
"""

import os, sys, json, time
from datetime import datetime, timezone

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPTS_DIR)

from paths import HERMES_DATA
from hermes_log import log

WWW_DATA = '/var/www/hermes/data'
os.makedirs(WWW_DATA, exist_ok=True)


def get_all_zones():
    """Get zones for all tokens."""
    from sl_zones import get_sl_zones, get_all_zones as _get_all_zones
    
    all_zones = _get_all_zones(lookback_days=30)
    
    result = {}
    for key, zones in all_zones.items():
        token, direction = key.rsplit('_', 1)
        result[key] = {
            'token': token,
            'direction': direction,
            'zones': [z.to_dict() for z in zones],
        }
    
    return result


def get_active_positions():
    """Get open positions and check if they're near zones."""
    import psycopg2
    from sl_zones import zone_aware_exit_check
    
    conn = psycopg2.connect(host='/var/run/postgresql', dbname='brain', user='postgres')
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT token, direction, entry_price, stop_loss, pnl_pct, current_price, signal
            FROM trades
            WHERE status = 'open'
            ORDER BY open_time DESC
        """)
        
        positions = []
        for row in cur.fetchall():
            token, direction, entry, sl, pnl_pct, current, signal = row
            if not current or current <= 0:
                continue
            
            # Check zone proximity
            try:
                # Get ATR
                import sqlite3
                conn_atr = sqlite3.connect(f'{HERMES_DATA}/candles.db', timeout=5)
                cur_atr = conn_atr.cursor()
                cur_atr.execute("""
                    SELECT open, high, low, close FROM candles_1h
                    WHERE token = ? AND is_closed = 1
                    ORDER BY ts DESC LIMIT 20
                """, (token.upper(),))
                rows = cur_atr.fetchall()
                cur_atr.close()
                conn_atr.close()
                
                atr = 0
                if len(rows) >= 15:
                    trs = []
                    for i in range(1, len(rows)):
                        h, l, pc = rows[i][1], rows[i][2], rows[i-1][3]
                        trs.append(max(h - l, abs(h - pc), abs(l - pc)))
                    atr = sum(trs[-14:]) / 14
                
                exit_check = zone_aware_exit_check(token, direction, current, atr)
                zone_status = exit_check['action']
                zone_reason = exit_check['reason']
            except Exception:
                zone_status = 'unknown'
                zone_reason = 'Could not check zones'
            
            positions.append({
                'token': token,
                'direction': direction,
                'entry_price': float(entry) if entry else 0,
                'stop_loss': float(sl) if sl else 0,
                'current_price': float(current) if current else 0,
                'pnl_pct': float(pnl_pct) if pnl_pct else 0,
                'signal': signal or '',
                'zone_status': zone_status,
                'zone_reason': zone_reason,
            })
        
        return positions
    finally:
        conn.close()


def get_zone_summary():
    """Get summary stats for the dashboard."""
    import psycopg2
    
    conn = psycopg2.connect(host='/var/run/postgresql', dbname='brain', user='postgres')
    try:
        cur = conn.cursor()
        
        # Total SL hits
        cur.execute("SELECT COUNT(*) FROM sl_memory")
        total_hits = cur.fetchone()[0]
        
        # Hits in last 24h
        cur.execute("""
            SELECT COUNT(*) FROM sl_memory
            WHERE hit_time > NOW() - INTERVAL '24 hours'
        """)
        hits_24h = cur.fetchone()[0]
        
        # Tokens tracked
        cur.execute("SELECT COUNT(DISTINCT token) FROM sl_memory")
        tokens_tracked = cur.fetchone()[0]
        
        # Strongest zones (3+ hits)
        cur.execute("""
            SELECT token, direction, 
                   ROUND(initial_sl::numeric, 2) as sl_level,
                   COUNT(*) as hits,
                   MIN(hit_time) as first_hit,
                   MAX(hit_time) as last_hit
            FROM sl_memory
            GROUP BY token, direction, ROUND(initial_sl::numeric, 2)
            HAVING COUNT(*) >= 3
            ORDER BY hits DESC
            LIMIT 20
        """)
        strong_zones = []
        for row in cur.fetchall():
            strong_zones.append({
                'token': row[0],
                'direction': row[1],
                'sl_level': float(row[2]),
                'hits': row[3],
                'first_hit': row[4].isoformat() if row[4] else None,
                'last_hit': row[5].isoformat() if row[5] else None,
            })
        
        return {
            'total_hits': total_hits,
            'hits_24h': hits_24h,
            'tokens_tracked': tokens_tracked,
            'strong_zones': strong_zones,
            'generated_at': datetime.now(timezone.utc).isoformat(),
        }
    finally:
        conn.close()


def generate_dashboard_data():
    """Generate complete dashboard data."""
    log("[SL-ZONES-API] Generating dashboard data")
    
    start = time.time()
    
    zones = get_all_zones()
    positions = get_active_positions()
    summary = get_zone_summary()
    
    data = {
        'zones': zones,
        'positions': positions,
        'summary': summary,
        'generated_at': datetime.now(timezone.utc).isoformat(),
    }
    
    # Write to JSON
    output_path = os.path.join(WWW_DATA, 'sl_zones.json')
    with open(output_path, 'w') as f:
        json.dump(data, f, indent=2, default=str)
    
    elapsed = time.time() - start
    log(f"[SL-ZONES-API] Dashboard data written in {elapsed:.1f}s — {len(zones)} tokens, {len(positions)} positions")
    
    return data


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='SL Zone Dashboard API')
    parser.add_argument('--json', action='store_true', help='Print JSON to stdout')
    args = parser.parse_args()
    
    data = generate_dashboard_data()
    
    if args.json:
        print(json.dumps(data, indent=2, default=str))
    else:
        print(f"✅ Dashboard data written to {WWW_DATA}/sl_zones.json")
        print(f"   Tokens: {data['summary']['tokens_tracked']}")
        print(f"   Total SL hits: {data['summary']['total_hits']}")
        print(f"   Hits in 24h: {data['summary']['hits_24h']}")
        print(f"   Strong zones: {len(data['summary']['strong_zones'])}")
        print(f"   Active positions: {len(data['positions'])}")
