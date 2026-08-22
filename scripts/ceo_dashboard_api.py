#!/usr/bin/env python3
"""
CEO Dashboard API — generates JSON for the CEO dashboard HTML page.

Reads all CEO-related data sources and outputs a single JSON file
served by nginx at /var/www/hermes/data/ceo_dashboard.json.

Timer: hermes-ceo-dashboard.timer (every 5 min)
"""
import json
import os
import re
import sys
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))
from paths import RUNTIME_DB, HERMES_DATA, WWW_DATA

OUTPUT_FILE = os.path.join(WWW_DATA, 'ceo_dashboard.json')
CEO_DIR = '/root/.hermes/automation/ceo'
AUTOMATION_DIR = '/root/.hermes/automation'


def safe_read(path, default=''):
    """Read file contents, return default on error."""
    try:
        with open(path) as f:
            return f.read()
    except Exception:
        return default


def safe_json(path, default=None):
    """Read JSON file, return default on error."""
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return default or {}


def get_goal_progress():
    """Get current performance metrics."""
    return safe_json('/root/.hermes/data/goal_progress.json', {
        'targets': {}, 'current': {}, 'trend': {}
    })


def get_kanban_entries(limit=10):
    """Parse CEO kanban markdown into structured entries."""
    content = safe_read(os.path.join(CEO_DIR, 'ceo_kanban.md'))
    entries = []
    # Match entries like: - [2026-08-22 ~02:30 UTC ...] content
    pattern = r'- \[([^\]]+)\]\s+(.*?)(?=\n- \[|\Z)'
    matches = re.findall(pattern, content, re.DOTALL)
    for ts, body in matches[:limit]:
        # Extract first line as summary, rest as detail
        lines = body.strip().split('\n')
        summary = lines[0].strip() if lines else ''
        detail = '\n'.join(lines[1:]).strip() if len(lines) > 1 else ''
        entries.append({
            'timestamp': ts.strip(),
            'summary': summary,
            'detail': detail,
        })
    return entries


def get_ceo_report():
    """Get latest CEO report."""
    content = safe_read(os.path.join(CEO_DIR, 'ceo_report.md'))
    return content


def get_signal_rotation():
    """Get latest signal rotation data."""
    content = safe_read(os.path.join(AUTOMATION_DIR, 'signal_rotation.md'))
    return content


def get_signal_lifecycle():
    """Get signal lifecycle states."""
    content = safe_read(os.path.join(AUTOMATION_DIR, 'signal_lifecycle.md'))
    return content


def get_signal_audit():
    """Get latest signal audit."""
    content = safe_read(os.path.join(AUTOMATION_DIR, 'signal_audit.md'))
    return content


def get_self_learning_log():
    """Get self-learning changes."""
    data = safe_json('/root/.hermes/automation/self_learning_log.json', {'changes': []})
    return data.get('changes', [])[-10:]  # last 10 changes


def get_combo_weights():
    """Get current combo weights."""
    return safe_json('/root/.hermes/data/combo_weights.json', {})


def get_pending_adjustments():
    """Get pending parameter adjustments awaiting evaluation."""
    return safe_json('/root/.hermes/data/pending_adjustments.json', {'pending': [], 'evaluated': []})


def get_error_alerts():
    """Get recent error alerts."""
    content = safe_read(os.path.join(AUTOMATION_DIR, 'error_alerts.md'))
    # Extract last 5 error blocks
    blocks = re.split(r'## ', content)
    return ['## ' + b.strip() for b in blocks[-5:] if b.strip()]


def get_bug_report():
    """Get latest bug report."""
    return safe_json(os.path.join(AUTOMATION_DIR, 'bug_report.json'), {})


def get_decay_log_recent():
    """Get recent decay detector log entries."""
    content = safe_read(os.path.join(AUTOMATION_DIR, 'decay_log.md'))
    lines = content.strip().split('\n')
    # Get last 20 entries
    return lines[-20:] if lines else []


def get_hebbian_stats():
    """Get hebbian gate stats."""
    return safe_json('/root/.hermes/data/hebbian_gate_stats.json', {'auto_decisions': []})


def get_trading_stats():
    """Get trading stats from signal_outcomes DB."""
    stats = {
        'trades_24h': 0, 'wr_24h': 0, 'pnl_24h': 0,
        'trades_7d': 0, 'wr_7d': 0, 'pnl_7d': 0,
        'open_positions': 0,
        'top_signals': [],
    }
    try:
        conn = sqlite3.connect(RUNTIME_DB, timeout=5)
        cur = conn.cursor()

        # 24h stats
        cur.execute("""
            SELECT COUNT(*), 
                   SUM(CASE WHEN is_win=1 THEN 1 ELSE 0 END)*1.0/COUNT(*),
                   SUM(pnl_usdt)
            FROM signal_outcomes
            WHERE trade_id IS NOT NULL AND created_at > datetime('now', '-24 hours')
        """)
        row = cur.fetchone()
        if row and row[0] > 0:
            stats['trades_24h'] = row[0]
            stats['wr_24h'] = round((row[1] or 0) * 100, 1)
            stats['pnl_24h'] = round(row[2] or 0, 2)

        # 7d stats
        cur.execute("""
            SELECT COUNT(*), 
                   SUM(CASE WHEN is_win=1 THEN 1 ELSE 0 END)*1.0/COUNT(*),
                   SUM(pnl_usdt)
            FROM signal_outcomes
            WHERE trade_id IS NOT NULL AND created_at > datetime('now', '-7 days')
        """)
        row = cur.fetchone()
        if row and row[0] > 0:
            stats['trades_7d'] = row[0]
            stats['wr_7d'] = round((row[1] or 0) * 100, 1)
            stats['pnl_7d'] = round(row[2] or 0, 2)

        # Top signals by PnL (7d)
        cur.execute("""
            SELECT signal_type, COUNT(*) as n,
                   SUM(CASE WHEN is_win=1 THEN 1 ELSE 0 END)*1.0/COUNT(*) as wr,
                   SUM(pnl_usdt) as total_pnl
            FROM signal_outcomes
            WHERE trade_id IS NOT NULL AND created_at > datetime('now', '-7 days')
            GROUP BY signal_type
            HAVING n >= 3
            ORDER BY total_pnl DESC
            LIMIT 10
        """)
        for row in cur.fetchall():
            stats['top_signals'].append({
                'signal': row[0],
                'trades': row[1],
                'wr': round((row[2] or 0) * 100, 1),
                'pnl': round(row[3] or 0, 2),
            })

        conn.close()
    except Exception as e:
        stats['error'] = str(e)
    return stats


def get_timer_status():
    """Get status of key timers."""
    import subprocess
    timers = {}
    try:
        result = subprocess.run(
            ['systemctl', 'list-timers', '--all', '--no-pager', '--plain'],
            capture_output=True, text=True, timeout=10
        )
        for line in result.stdout.strip().split('\n'):
            if 'hermes-' not in line:
                continue
            # Parse: NEXT LEFT LAST PASSED UNIT ACTIVATES
            parts = line.split()
            if len(parts) < 6:
                continue
            # Find the timer unit name
            name = None
            for p in parts:
                if 'hermes-' in p and '.timer' in p:
                    name = p
                    break
            if not name:
                continue
            # Extract NEXT and LAST timestamps
            # Format: "Sat 2026-08-22 02:48:28 UTC     4min 24s Sat 2026-08-22 02:43:28 UTC      35s ago hermes-ceo-dashboard.timer"
            next_ts = parts[0] + ' ' + parts[1] + ' ' + parts[2] if len(parts) > 2 else '-'
            last_ts = '-'
            # Find "ago" to locate LAST timestamp
            for i, p in enumerate(parts):
                if p == 'ago' and i >= 5:
                    # LAST is 2 tokens before "ago": "Sat 2026-08-22 02:43:28"
                    if i >= 3:
                        last_ts = parts[i-3] + ' ' + parts[i-2] + ' ' + parts[i-1]
                    break
            timers[name] = {
                'next': next_ts,
                'last': last_ts,
            }
    except Exception:
        pass
    return timers


def build_dashboard():
    """Build the complete dashboard JSON."""
    now = datetime.now(timezone.utc).isoformat()
    
    goal = get_goal_progress()
    trading = get_trading_stats()
    
    return {
        'generated_at': now,
        'goal_progress': goal,
        'trading': trading,
        'kanban': get_kanban_entries(10),
        'ceo_report': get_ceo_report(),
        'signal_rotation': get_signal_rotation(),
        'signal_lifecycle': get_signal_lifecycle(),
        'signal_audit': get_signal_audit(),
        'self_learning': get_self_learning_log(),
        'combo_weights': get_combo_weights(),
        'pending_adjustments': get_pending_adjustments(),
        'error_alerts': get_error_alerts(),
        'bug_report': get_bug_report(),
        'decay_log': get_decay_log_recent(),
        'hebbian_stats': get_hebbian_stats(),
        'timers': get_timer_status(),
    }


def main():
    os.makedirs(WWW_DATA, exist_ok=True)
    data = build_dashboard()
    
    # Atomic write
    tmp = OUTPUT_FILE + '.tmp'
    with open(tmp, 'w') as f:
        json.dump(data, f)
    os.replace(tmp, OUTPUT_FILE)
    
    print(f"[ceo-dashboard] Wrote {OUTPUT_FILE} ({os.path.getsize(OUTPUT_FILE)} bytes)")


if __name__ == '__main__':
    main()
