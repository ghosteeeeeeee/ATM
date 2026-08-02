#!/usr/bin/env python3
"""
obs_dashboard.py — Real-time system metrics for observability.

Writes metrics to /var/www/hermes/data/obs_metrics.json every 5 minutes.
Can be served by nginx for a simple dashboard.

Run via: python3 scripts/obs_dashboard.py
Timer: hermes-obs-dashboard.timer (every 5min)
"""
import sys, os, json, sqlite3, time, tempfile
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paths import RUNTIME_DB, HERMES_DATA, WWW_DATA

METRICS_FILE = os.path.join(WWW_DATA, 'obs_metrics.json')

def get_trades_metrics():
    """Get today's trade metrics from signal_outcomes."""
    conn = sqlite3.connect(RUNTIME_DB)
    try:
        c = conn.cursor()
        c.execute("""
            SELECT COUNT(*) as total, SUM(is_win) as wins,
                   ROUND(SUM(pnl_pct), 2) as total_pnl,
                   ROUND(AVG(pnl_pct), 3) as avg_pnl
            FROM signal_outcomes
            WHERE trade_id IS NOT NULL
              AND created_at > datetime('now', '-24 hours')
        """)
        row = c.fetchone()
        total = row[0] or 0
        wins = row[1] or 0
        return {
            'total': total,
            'wins': wins,
            'losses': total - wins,
            'wr': round(wins/total*100, 1) if total > 0 else 0,
            'total_pnl': row[2] or 0,
            'avg_pnl': row[3] or 0,
        }
    except Exception:
        return {'total': 0, 'wins': 0, 'losses': 0, 'wr': 0, 'total_pnl': 0, 'avg_pnl': 0}
    finally:
        conn.close()

def get_signal_performance():
    """Get per-signal performance (24h, dedup)."""
    conn = sqlite3.connect(RUNTIME_DB)
    try:
        c = conn.cursor()
        c.execute("""
            SELECT signal_type, COUNT(*) as trades, SUM(is_win) as wins,
                   ROUND(CAST(SUM(is_win) AS FLOAT)/COUNT(*)*100, 1) as wr,
                   ROUND(SUM(pnl_pct), 2) as total_pnl
            FROM signal_outcomes
            WHERE trade_id IS NOT NULL
              AND created_at > datetime('now', '-24 hours')
            GROUP BY signal_type
            ORDER BY total_pnl DESC
        """)
        results = []
        for row in c.fetchall():
            results.append({
                'signal': row[0],
                'trades': row[1],
                'wins': row[2],
                'wr': row[3],
                'pnl': row[4],
            })
        return results
    except Exception:
        return []
    finally:
        conn.close()

def get_hotset_status():
    """Check hotset size."""
    try:
        hotset_file = os.path.join(WWW_DATA, 'hotset.json')
        with open(hotset_file) as f:
            data = json.load(f)
        return {
            'tokens': len(data.get('hotset', [])),
            'cycle': data.get('compaction_cycle', 0),
        }
    except Exception:
        return {'tokens': 0, 'cycle': 0}

def get_pipeline_health():
    """Check pipeline last run time."""
    try:
        # Check if pipeline service is active
        import subprocess
        result = subprocess.run(['systemctl', 'is-active', 'hermes-pipeline'],
                              capture_output=True, text=True, timeout=5)
        pipeline_active = result.stdout.strip() == 'active'

        # Check hl-sync
        result2 = subprocess.run(['systemctl', 'is-active', 'hermes-hl-sync-guardian'],
                               capture_output=True, text=True, timeout=5)
        hl_sync_active = result2.stdout.strip() == 'active'

        return {
            'pipeline_active': pipeline_active,
            'hl_sync_active': hl_sync_active,
        }
    except Exception:
        return {'pipeline_active': False, 'hl_sync_active': False}

def get_token_speed_summary():
    """Get token speed distribution."""
    conn = sqlite3.connect(RUNTIME_DB)
    try:
        c = conn.cursor()
        c.execute("""
            SELECT
                SUM(CASE WHEN speed_percentile >= 80 THEN 1 ELSE 0 END) as fast,
                SUM(CASE WHEN speed_percentile >= 50 AND speed_percentile < 80 THEN 1 ELSE 0 END) as mid,
                SUM(CASE WHEN speed_percentile < 50 THEN 1 ELSE 0 END) as slow
            FROM token_speeds
        """)
        row = c.fetchone()
        return {
            'fast': row[0] or 0,
            'mid': row[1] or 0,
            'slow': row[2] or 0,
        }
    except Exception:
        return {'fast': 0, 'mid': 0, 'slow': 0}
    finally:
        conn.close()

def get_recent_signals():
    """Get last 10 signals generated."""
    conn = sqlite3.connect(RUNTIME_DB)
    try:
        c = conn.cursor()
        c.execute("""
            SELECT source, token, direction, confidence, decision, created_at
            FROM signals
            WHERE created_at > datetime('now', '-1 hour')
            ORDER BY created_at DESC
            LIMIT 10
        """)
        results = []
        for row in c.fetchall():
            results.append({
                'source': row[0],
                'token': row[1],
                'direction': row[2],
                'confidence': row[3],
                'decision': row[4],
                'time': row[5],
            })
        return results
    except Exception:
        return []
    finally:
        conn.close()

def main():
    metrics = {
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'trades': get_trades_metrics(),
        'signals': get_signal_performance(),
        'hotset': get_hotset_status(),
        'pipeline': get_pipeline_health(),
        'speed': get_token_speed_summary(),
        'recent_signals': get_recent_signals(),
    }

    os.makedirs(os.path.dirname(METRICS_FILE), exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(METRICS_FILE), suffix='.tmp')
    try:
        with os.fdopen(fd, 'w') as f:
            json.dump(metrics, f, indent=2)
        os.replace(tmp, METRICS_FILE)
    except:
        os.unlink(tmp)
        raise

    print(f"[obs] Metrics written: {metrics['trades']['total']} trades, "
          f"{metrics['trades']['wr']}% WR, hotset={metrics['hotset']['tokens']}")

if __name__ == '__main__':
    main()
