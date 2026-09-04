#!/usr/bin/env python3
"""
continuum_api.py — Export continuum engine state as JSON for dashboard.

Writes to /var/www/hermes/data/continuum_data.json

Run after continuum_engine.py collects data.
"""
import sys, os, json, time, sqlite3
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(__file__))
from paths import HERMES_DATA, WWW_DATA
from continuum_engine import CONTINUUM_DB

def export():
    """Export continuum state to JSON."""
    os.makedirs(WWW_DATA, exist_ok=True)
    
    output = {
        'updated_at': int(time.time()),
        'updated_at_str': datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC'),
        'current': None,
        'history': [],
        'positions': [],
        'stats': {},
    }
    
    if not os.path.exists(CONTINUUM_DB):
        print(f"DB not found: {CONTINUUM_DB}")
        _write(output)
        return
    
    conn = sqlite3.connect(CONTINUUM_DB, timeout=10)
    conn.row_factory = sqlite3.Row
    
    try:
        # Current state (latest)
        cur = conn.execute(
            "SELECT * FROM continuum_states WHERE token='BTC' ORDER BY ts DESC LIMIT 1"
        )
        row = cur.fetchone()
        if row:
            output['current'] = _row_to_dict(row)
        
        # History (last 24 hours = ~2880 ticks at 30s intervals)
        cur = conn.execute(
            "SELECT * FROM continuum_states WHERE token='BTC' AND ts > ? ORDER BY ts",
            (int(time.time()) - 86400,)
        )
        output['history'] = [_row_to_dict(r) for r in cur.fetchall()]
        
        # Stats
        cur = conn.execute(
            "SELECT COUNT(*) as total, "
            "MAX(state_score) as max_score, MIN(state_score) as min_score, "
            "AVG(state_score) as avg_score "
            "FROM continuum_states WHERE token='BTC' AND ts > ?",
            (int(time.time()) - 86400,)
        )
        stats_row = cur.fetchone()
        if stats_row:
            output['stats'] = {
                'total_ticks': stats_row['total'],
                'max_score': round(stats_row['max_score'] or 0, 1),
                'min_score': round(stats_row['min_score'] or 0, 1),
                'avg_score': round(stats_row['avg_score'] or 0, 1),
            }
        
    except Exception as e:
        print(f"Error reading DB: {e}")
    finally:
        conn.close()
    
    # Load positions if file exists
    pos_file = os.path.join(HERMES_DATA, 'continuum_positions.json')
    if os.path.exists(pos_file):
        try:
            with open(pos_file) as f:
                output['positions'] = json.load(f)
        except:
            pass
    
    _write(output)
    print(f"Exported continuum data: {len(output['history'])} history entries")

def _row_to_dict(row):
    """Convert DB row to dict with human-readable fields."""
    d = dict(row)
    # Convert timestamp to readable
    if 'ts' in d:
        d['ts_str'] = datetime.fromtimestamp(d['ts'], tz=timezone.utc).strftime('%H:%M:%S')
    return d

def _write(data):
    """Write JSON to WWW_DATA."""
    path = os.path.join(WWW_DATA, 'continuum_data.json')
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)

if __name__ == '__main__':
    export()
