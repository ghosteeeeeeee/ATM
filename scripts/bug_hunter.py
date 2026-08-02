#!/usr/bin/env python3
"""
bug_hunter.py — Quick system health verification.

Runs every 8h via hermes-bug-hunter.timer.
Checks: signals, kill switches, pipeline, hotset, trade frequency, new signals.
"""
import sys, os, sqlite3, subprocess, json
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paths import RUNTIME_DB, HERMES_DATA, WWW_DATA

results = []

def get_now():
    return datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')

def get_cutoff(hours):
    from datetime import timedelta
    return (datetime.now(timezone.utc) - timedelta(hours=hours)).strftime('%Y-%m-%d %H:%M:%S')

def check(name, ok, msg):
    results.append((name, ok, msg))
    status = "PASS" if ok else "FAIL"
    print(f"  [{status}] {name}: {msg}")

# 1. Signal generation
try:
    from signals import get_fast_signals, _resolve_enabled
    enabled = [s for s in get_fast_signals() if _resolve_enabled(s)]
    check("signal_registry", len(enabled) >= 3, f"{len(enabled)} signals registered")
except Exception as e:
    check("signal_registry", False, str(e))

# 2. Kill switch violations
try:
    conn = sqlite3.connect(str(RUNTIME_DB))
    c = conn.cursor()
    c.execute("""
        SELECT signal_type, COUNT(*) FROM signal_outcomes
        WHERE trade_id IS NOT NULL
          AND created_at > ?
          AND signal_type IN ('inv-accel-300-', 'accel-300-vel+', 'bb-squeeze-')
        GROUP BY signal_type
    """, (get_cutoff(6),))
    violations = c.fetchall()
    conn.close()
    if violations:
        names = [f"{v[0]}({v[1]})" for v in violations]
        check("kill_switches", False, f"violations: {', '.join(names)}")
    else:
        check("kill_switches", True, "no disabled signals executing (6h)")
except Exception as e:
    check("kill_switches", False, str(e))

# 3. Pipeline errors
try:
    result = subprocess.run(
        ['journalctl', '-u', 'hermes-pipeline', '--since', '30 min ago', '--no-pager'],
        capture_output=True, text=True, timeout=10
    )
    errors = result.stdout.count('ERROR')
    check("pipeline_errors", errors < 3, f"{errors} errors in last 30min")
except Exception as e:
    check("pipeline_errors", False, str(e))

# 4. Hotset
try:
    hotset_file = os.path.join(WWW_DATA, 'hotset.json')
    with open(hotset_file) as f:
        data = json.load(f)
    tokens = len(data.get('hotset', []))
    check("hotset", True, f"{tokens} tokens in hotset")
except Exception as e:
    check("hotset", False, str(e))

# 5. Trade frequency
try:
    conn = sqlite3.connect(str(RUNTIME_DB))
    c = conn.cursor()
    c.execute("""
        SELECT COUNT(*) FROM signal_outcomes
        WHERE trade_id IS NOT NULL
          AND created_at > ?
    """, (get_cutoff(6),))
    trades = c.fetchone()[0] or 0
    conn.close()
    rate = trades / 6
    check("trade_frequency", 0.5 <= rate <= 20, f"{trades} trades in 6h ({rate:.1f}/hr)")
except Exception as e:
    check("trade_frequency", False, str(e))

# 6. New signals
try:
    conn = sqlite3.connect(str(RUNTIME_DB))
    c = conn.cursor()
    c.execute("""
        SELECT source, COUNT(*) FROM signals
        WHERE created_at > ?
          AND source IN ('pct-hermes+', 'pct-hermes-', 'vel-hermes+', 'vel-hermes-',
                         'fast-momentum+', 'fast-momentum-')
        GROUP BY source
    """, (get_cutoff(1),))
    new_signals = c.fetchall()
    conn.close()
    total = sum(r[1] for r in new_signals)
    check("new_signals", True, f"{total} signals in last hour")
except Exception as e:
    check("new_signals", False, str(e))

# 7. HL sync
try:
    result = subprocess.run(['systemctl', 'is-active', 'hermes-hl-sync-guardian'],
                          capture_output=True, text=True, timeout=5)
    check("hl_sync", result.stdout.strip() == 'active', result.stdout.strip())
except Exception as e:
    check("hl_sync", False, str(e))

# 8. Win rate
try:
    conn = sqlite3.connect(str(RUNTIME_DB))
    c = conn.cursor()
    c.execute("""
        SELECT COUNT(*), SUM(is_win) FROM signal_outcomes
        WHERE trade_id IS NOT NULL
          AND created_at > ?
    """, (get_cutoff(24),))
    row = c.fetchone()
    conn.close()
    total = row[0] or 0
    wins = row[1] or 0
    wr = wins/total*100 if total > 0 else 0
    check("win_rate", wr >= 20 or total < 5, f"{wr:.1f}% ({wins}/{total})")
except Exception as e:
    check("win_rate", False, str(e))

# Summary
print()
failed = [r for r in results if not r[1]]
if failed:
    print(f"BUG HUNTER: {len(failed)} FAILURES")
    for name, ok, msg in failed:
        print(f"  FAIL: {name} — {msg}")
    sys.exit(1)
else:
    print(f"BUG HUNTER: ALL {len(results)} CHECKS PASSED")
    sys.exit(0)
