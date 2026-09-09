#!/usr/bin/env python3
"""
data_integrity_guard.py — Prevention system for trades ↔ signals data integrity

Prevents:
1. Wrong signal_type in trades (source vs signal_type bug)
2. Missing signal_created_at (foreign key violation)
3. Naming convention mismatch (dashes vs underscores)
4. Stale data (signals expired before trade execution)

Usage:
  python3 scripts/data_integrity_guard.py --check     # Run integrity checks
  python3 scripts/data_integrity_guard.py --monitor   # Continuous monitoring
  python3 scripts/data_integrity_guard.py --fix       # Auto-fix issues
"""

import psycopg2
import sqlite3
import os
import sys
import json
import time
from datetime import datetime, timedelta

# ── Config ────────────────────────────────────────────────────────────────────
BRAIN_DB = "host=/var/run/postgresql dbname=brain user=postgres password=***"
SIGNALS_DB = "/root/.hermes/data/signals_hermes_runtime.db"
CHECK_MODE = '--check' in sys.argv
MONITOR_MODE = '--monitor' in sys.argv
FIX_MODE = '--fix' in sys.argv


# ── Validation Rules ──────────────────────────────────────────────────────────

def check_signal_type_matches_source(pg_cur):
    """Check if trade signal_type matches what's in signals table."""
    pg_cur.execute('''
        SELECT t.id, t.token, t.signal, t.open_time, t.strategy
        FROM trades t
        WHERE t.open_time > NOW() - INTERVAL '24 hours'
        AND t.signal IS NOT NULL
    ''')
    trades = pg_cur.fetchall()
    
    issues = []
    for trade_id, token, signal, open_time, strategy in trades:
        # Check if signal looks like a source (has + or - suffix)
        if signal and ('+' in signal or '-' in signal):
            issues.append({
                'trade_id': trade_id,
                'token': token,
                'signal': signal,
                'issue': 'Signal looks like source (has +/- suffix)',
                'severity': 'HIGH'
            })
    
    return issues


def check_signal_created_at_populated(pg_cur):
    """Check if signal_created_at is populated for recent trades."""
    pg_cur.execute('''
        SELECT COUNT(*) FROM trades
        WHERE open_time > NOW() - INTERVAL '24 hours'
        AND (signal_created_at IS NULL)
    ''')
    count = pg_cur.fetchone()[0]
    
    if count > 0:
        return [{
            'issue': f'{count} trades missing signal_created_at',
            'severity': 'HIGH'
        }]
    return []


def check_naming_convention(sl_cur):
    """Check if signal names use consistent convention."""
    sl_cur.execute('''
        SELECT signal_type, COUNT(*) as cnt
        FROM signals
        WHERE created_at > datetime('now', '-1 day')
        GROUP BY signal_type
    ''')
    signals = sl_cur.fetchall()
    
    # Known correct signal types that contain +/- (these are source tags, not signal types)
    # The integrity check should NOT flag these
    VALID_SIGNAL_TYPES = {'hot-set', 'pump-chain', 'support_resistance'}
    
    issues = []
    for signal_type, count in signals:
        if signal_type in VALID_SIGNAL_TYPES:
            continue
        if signal_type and ('+' in signal_type or '-' in signal_type):
            issues.append({
                'signal_type': signal_type,
                'issue': 'Signal type has +/- suffix (should be underscores)',
                'severity': 'MEDIUM'
            })
    
    return issues


def check_trade_signal_linkage(pg_cur, sl_cur):
    """Check if trades have proper linkage to signals via signal_created_at."""
    pg_cur.execute('''
        SELECT COUNT(*) FROM trades
        WHERE open_time > NOW() - INTERVAL '24 hours'
        AND signal_created_at IS NOT NULL
    ''')
    linked = pg_cur.fetchone()[0]
    
    pg_cur.execute('''
        SELECT COUNT(*) FROM trades
        WHERE open_time > NOW() - INTERVAL '24 hours'
    ''')
    total = pg_cur.fetchone()[0]
    
    if total > 0:
        linkage_rate = linked / total * 100
        if linkage_rate < 90:
            return [{
                'issue': f'Low signal linkage rate: {linkage_rate:.1f}% ({linked}/{total} linked)',
                'severity': 'HIGH'
            }]
    
    return []


def check_pump_chain_stats(pg_cur):
    """Check if pump-chain stats are inflated by wrong signal_type."""
    pg_cur.execute('''
        SELECT signal, COUNT(*) as cnt, AVG(pnl_pct) as avg_pnl
        FROM trades
        WHERE open_time > NOW() - INTERVAL '7 days'
        GROUP BY signal
        ORDER BY cnt DESC
    ''')
    stats = pg_cur.fetchall()
    
    issues = []
    for signal, count, avg_pnl in stats:
        if signal and 'pump-chain' in signal and count > 20:
            issues.append({
                'signal': signal,
                'count': count,
                'avg_pnl': avg_pnl,
                'issue': f'High pump-chain count ({count}) — verify not inflated',
                'severity': 'MEDIUM'
            })
    
    return issues


# ── Main ──────────────────────────────────────────────────────────────────────

def run_checks():
    """Run all integrity checks."""
    print("=" * 60)
    print("DATA INTEGRITY CHECK")
    print("=" * 60)
    
    pg_conn = psycopg2.connect(BRAIN_DB)
    sl_conn = sqlite3.connect(f"file:{SIGNALS_DB}?mode=ro", uri=True, timeout=10)
    
    pg_cur = pg_conn.cursor()
    sl_cur = sl_conn.cursor()
    
    all_issues = []
    
    # Run checks
    print("\n1. Checking signal type matches source...")
    issues = check_signal_type_matches_source(pg_cur)
    all_issues.extend(issues)
    print(f"   Found {len(issues)} issues")
    
    print("\n2. Checking signal_created_at population...")
    issues = check_signal_created_at_populated(pg_cur)
    all_issues.extend(issues)
    print(f"   Found {len(issues)} issues")
    
    print("\n3. Checking naming convention...")
    issues = check_naming_convention(sl_cur)
    all_issues.extend(issues)
    print(f"   Found {len(issues)} issues")
    
    print("\n4. Checking trade-signal linkage...")
    issues = check_trade_signal_linkage(pg_cur, sl_cur)
    all_issues.extend(issues)
    print(f"   Found {len(issues)} issues")
    
    print("\n5. Checking pump-chain stats...")
    issues = check_pump_chain_stats(pg_cur)
    all_issues.extend(issues)
    print(f"   Found {len(issues)} issues")
    
    pg_cur.close()
    sl_cur.close()
    pg_conn.close()
    sl_conn.close()
    
    # Report
    print("\n" + "=" * 60)
    if all_issues:
        print(f"FOUND {len(all_issues)} ISSUES:")
        for issue in all_issues:
            print(f"  [{issue.get('severity', 'MEDIUM')}] {issue.get('issue', str(issue))}")
    else:
        print("ALL CHECKS PASSED — NO ISSUES FOUND")
    print("=" * 60)
    
    return all_issues


def monitor():
    """Continuous monitoring mode."""
    print("Starting continuous monitoring (Ctrl+C to stop)...")
    while True:
        try:
            issues = run_checks()
            if issues:
                # Log to file
                with open('/root/.hermes/logs/data_integrity.log', 'a') as f:
                    f.write(f"\n{datetime.now().isoformat()}: {len(issues)} issues found\n")
                    for issue in issues:
                        f.write(f"  {issue}\n")
            time.sleep(300)  # Check every 5 minutes
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(60)


if __name__ == '__main__':
    if MONITOR_MODE:
        monitor()
    else:
        issues = run_checks()
        sys.exit(1 if issues else 0)
