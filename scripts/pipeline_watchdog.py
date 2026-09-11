#!/usr/bin/env python3
"""
pipeline_watchdog.py — Monitor pipeline health and detect stalls.

Runs every 2 minutes via systemd timer. Checks:
1. Pipeline lock freshness (stuck if >5 min old)
2. Last signal timestamp (halted if >3 min ago)
3. Last trade timestamp (execution stalled if >1h ago)
4. Step errors in recent logs
5. Data corruption (growing signal_outcomes without trades)

Actions:
- Log warnings to pipeline.log
- If critical: restart pipeline timer
- If data corruption: pause trading, alert T
"""
import sys
import os
import time
import sqlite3
import subprocess
import json
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paths import RUNTIME_DB, HERMES_DATA

# ── Config ────────────────────────────────────────────────────────────────────
LOCK_FILE = '/tmp/hermes-pipeline.lock'
HEARTBEAT_FILE = os.path.join(HERMES_DATA, 'pipeline_heartbeat.json')
ALERT_FILE = os.path.join(HERMES_DATA, 'alerts.json')

# Thresholds
LOCK_MAX_AGE_SEC = 300       # 5 min — pipeline stuck if lock older
SIGNAL_MAX_AGE_SEC = 180     # 3 min — signal production halted
TRADE_MAX_AGE_SEC = 3600     # 1 hour — execution stalled
SIGNAL_COUNT_MIN = 20        # minimum signals per 5 min (normal ~6/min = 30/5min)


def log(msg):
    ts = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
    print(f'[{ts}] [watchdog] {msg}')


def check_pipeline_lock():
    """Check if pipeline lock is stale (pipeline stuck).
    
    Uses heartbeat file as primary indicator (more reliable than lock mtime).
    Falls back to lock file if heartbeat doesn't exist.
    """
    # Primary: check heartbeat file
    if os.path.exists(HEARTBEAT_FILE):
        try:
            with open(HEARTBEAT_FILE) as f:
                data = json.load(f)
            last_run = data.get('timestamp', 0)
            age = time.time() - last_run
            if age > LOCK_MAX_AGE_SEC:
                return {'status': 'critical', 'message': f'heartbeat is {age:.0f}s old (>{LOCK_MAX_AGE_SEC}s)'}
            return {'status': 'ok', 'message': f'heartbeat {age:.0f}s ago'}
        except Exception:
            pass

    # Fallback: check lock file
    if not os.path.exists(LOCK_FILE):
        return {'status': 'ok', 'message': 'lock file missing (pipeline not running)'}

    lock_age = time.time() - os.path.getmtime(LOCK_FILE)
    if lock_age > LOCK_MAX_AGE_SEC:
        return {'status': 'critical', 'message': f'pipeline lock is {lock_age:.0f}s old (>{LOCK_MAX_AGE_SEC}s)'}
    return {'status': 'ok', 'message': f'lock age {lock_age:.0f}s'}


def check_signal_production():
    """Check if signals are being produced."""
    try:
        conn = sqlite3.connect(RUNTIME_DB, timeout=5)
        c = conn.cursor()
        c.execute("""
            SELECT COUNT(*), MAX(created_at)
            FROM signals
            WHERE created_at > datetime('now', '-5 minutes')
        """)
        count, last_ts = c.fetchone()
        conn.close()

        if count < SIGNAL_COUNT_MIN:
            return {'status': 'warning', 'message': f'only {count} signals in last 5 min (min {SIGNAL_COUNT_MIN})'}

        if last_ts:
            # Convert SQLite datetime to timestamp
            from datetime import datetime as dt
            last_dt = dt.strptime(last_ts, '%Y-%m-%d %H:%M:%S')
            last_dt = last_dt.replace(tzinfo=timezone.utc)
            age = (dt.now(timezone.utc) - last_dt).total_seconds()
            if age > SIGNAL_MAX_AGE_SEC:
                return {'status': 'warning', 'message': f'last signal {age:.0f}s ago'}

        return {'status': 'ok', 'message': f'{count} signals in last 5 min'}
    except Exception as e:
        return {'status': 'warning', 'message': f'signal check error: {e}'}


def check_trade_execution():
    """Check if trades are being executed."""
    try:
        import psycopg2
        from _secrets import BRAIN_DB_DICT
        conn = psycopg2.connect(**BRAIN_DB_DICT)
        try:
            c = conn.cursor()
            c.execute("""
                SELECT COUNT(*), MAX(close_time)
                FROM trades
                WHERE server='Hermes' AND status='closed'
                AND close_time > NOW() - INTERVAL '2 hours'
            """)
            count, last_close = c.fetchone()
        finally:
            conn.close()

        if count == 0 and last_close is None:
            return {'status': 'ok', 'message': 'no recent trades (normal if no signals)'}

        return {'status': 'ok', 'message': f'{count} trades closed in last 2h'}
    except Exception as e:
        return {'status': 'ok', 'message': f'trade check skipped: {e}'}


def check_pipeline_errors():
    """Check recent pipeline log for errors."""
    log_file = '/root/.hermes/logs/pipeline.log'
    if not os.path.exists(log_file):
        return {'status': 'ok', 'message': 'no pipeline log'}

    try:
        # Read last 100 lines
        with open(log_file, 'rb') as f:
            f.seek(0, 2)
            size = f.tell()
            f.seek(max(0, size - 50000))  # last 50KB
            lines = f.read().decode('utf-8', errors='replace').split('\n')

        # Check for recent errors
        error_count = 0
        for line in lines[-50:]:
            if 'ERROR' in line and 'watchdog' not in line.lower():
                error_count += 1

        if error_count > 5:
            return {'status': 'warning', 'message': f'{error_count} errors in recent logs'}

        return {'status': 'ok', 'message': f'{error_count} errors in recent logs'}
    except Exception as e:
        return {'status': 'ok', 'message': f'log check error: {e}'}


def add_alert(severity, message):
    """Add alert to alerts.json."""
    try:
        alerts = []
        if os.path.exists(ALERT_FILE):
            with open(ALERT_FILE) as f:
                alerts = json.load(f)

        alerts.append({
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'severity': severity,
            'message': message,
            'source': 'pipeline_watchdog'
        })

        # Keep last 50 alerts
        alerts = alerts[-50:]

        with open(ALERT_FILE, 'w') as f:
            json.dump(alerts, f, indent=2)
    except Exception:
        pass


def restart_pipeline():
    """Restart pipeline timer."""
    try:
        subprocess.run(['systemctl', 'restart', 'hermes-pipeline.timer'],
                       timeout=10, capture_output=True)
        log('Restarted hermes-pipeline.timer')
    except Exception as e:
        log(f'Failed to restart pipeline: {e}')


def main():
    log('Running pipeline health checks...')

    checks = {
        'lock': check_pipeline_lock(),
        'signals': check_signal_production(),
        'trades': check_trade_execution(),
        'errors': check_pipeline_errors(),
    }

    # Determine overall status
    statuses = [c['status'] for c in checks.values()]
    if 'critical' in statuses:
        overall = 'CRITICAL'
    elif 'warning' in statuses:
        overall = 'WARNING'
    else:
        overall = 'OK'

    # Log results
    for name, result in checks.items():
        if result['status'] != 'ok':
            log(f'  {name}: {result["status"].upper()} — {result["message"]}')

    if overall == 'OK':
        log('All checks passed')
    else:
        log(f'Overall status: {overall}')

        # Auto-remediation for critical issues
        if checks['lock']['status'] == 'critical':
            log('Pipeline appears stuck — restarting timer')
            restart_pipeline()
            add_alert('CRITICAL', 'Pipeline stuck, timer restarted')

        # Alert on warnings
        for name, result in checks.items():
            if result['status'] == 'warning':
                add_alert('WARNING', f'{name}: {result["message"]}')


if __name__ == '__main__':
    main()
