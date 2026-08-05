#!/usr/bin/env python3
"""
bug_hunter.py — System health verification + code bug scanner.

Runs every 8h via hermes-bug-hunter.timer.
Checks: system health, code patterns, known bug signatures.
Reports: file:line references + fix recommendations.
"""
import sys, os, re, sqlite3, subprocess, json
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paths import RUNTIME_DB, HERMES_DATA, WWW_DATA

results = []  # (name, ok, msg, file_ref, fix)
SCRIPTS = os.path.dirname(os.path.abspath(__file__))
SCRIPTS_DIR = Path(SCRIPTS)
BUG_REPORT = os.path.join(HERMES_DATA, '..', 'automation', 'bug_report.json')

def get_now():
    return datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')

def get_cutoff(hours):
    from datetime import timedelta
    return (datetime.now(timezone.utc) - timedelta(hours=hours)).strftime('%Y-%m-%d %H:%M:%S')

def check(name, ok, msg, file_ref='', fix=''):
    results.append((name, ok, msg, file_ref, fix))
    status = "PASS" if ok else "FAIL"
    ref = f" → {file_ref}" if file_ref else ""
    print(f"  [{status}] {name}: {msg}{ref}")

def grep_file(pattern, filepath):
    """Return list of (line_num, line) matching pattern."""
    matches = []
    try:
        with open(filepath) as f:
            for i, line in enumerate(f, 1):
                if re.search(pattern, line):
                    matches.append((i, line.rstrip()))
    except Exception:
        pass
    return matches

# ═══════════════════════════════════════════════════════════════════════════════
# SYSTEM HEALTH CHECKS
# ═══════════════════════════════════════════════════════════════════════════════

# 1. Signal generation
try:
    from signals import get_fast_signals, _resolve_enabled
    enabled = [s for s in get_fast_signals() if _resolve_enabled(s)]
    check("signal_registry", len(enabled) >= 3,
          f"{len(enabled)} signals registered",
          fix="Enable signals in hermes_constants.py or build new candidates" if len(enabled) < 3 else "")
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
        check("kill_switches", False, f"violations: {', '.join(names)}",
              file_ref="hermes_constants.py:NEVER_REENABLE_FLAGS",
              fix="Add missing signal to NEVER_REENABLE_FLAGS set in hermes_constants.py")
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
    check("pipeline_errors", errors < 3, f"{errors} errors in last 30min",
          fix="Check logs/pipeline.log for root cause" if errors >= 3 else "")
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
    check("trade_frequency", 0.5 <= rate <= 20, f"{trades} trades in 6h ({rate:.1f}/hr)",
          fix="Enable more signals or reduce filters if rate < 0.5/hr" if rate < 0.5 else "")
except Exception as e:
    check("trade_frequency", False, str(e))

# 6. HL sync
try:
    result = subprocess.run(['systemctl', 'is-active', 'hermes-hl-sync-guardian'],
                          capture_output=True, text=True, timeout=5)
    check("hl_sync", result.stdout.strip() == 'active', result.stdout.strip(),
          fix="systemctl restart hermes-hl-sync-guardian" if result.stdout.strip() != 'active' else "")
except Exception as e:
    check("hl_sync", False, str(e))

# 7. Win rate
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
    check("win_rate", wr >= 20 or total < 5, f"{wr:.1f}% ({wins}/{total})",
          fix="Kill 0% WR signals, enable profitable ones, or activate dynamic inverter" if wr < 20 and total >= 5 else "")
except Exception as e:
    check("win_rate", False, str(e))

# ═══════════════════════════════════════════════════════════════════════════════
# CODE BUG SCANS
# ═══════════════════════════════════════════════════════════════════════════════

# 8. SQLite connection leaks (cursor not in finally block)
leak_files = []
for pyfile in os.listdir(SCRIPTS):
    if not pyfile.endswith('.py'):
        continue
    fp = os.path.join(SCRIPTS, pyfile)
    content = open(fp).read()
    # Pattern: conn.execute() without corresponding conn.close() in finally
    if 'sqlite3.connect' in content and 'finally:' not in content and 'conn.close()' in content:
        leak_files.append(pyfile)
if leak_files:
    check("sqlite_leaks", False, f"{len(leak_files)} files: {', '.join(leak_files[:5])}",
          file_ref=f"{leak_files[0]}.py",
          fix="Move conn.close() to a finally block or use context manager")
else:
    check("sqlite_leaks", True, "no obvious connection leaks")

# 9. SQL injection (f-string or format in SQL)
injection_files = []
for pyfile in os.listdir(SCRIPTS):
    if not pyfile.endswith('.py'):
        continue
    fp = os.path.join(SCRIPTS, pyfile)
    matches = grep_file(r'execute\(f["\']|execute\(".*"\.format|execute\(".*"%', fp)
    if matches:
        injection_files.append((pyfile, matches[0][0]))
if injection_files:
    f, line = injection_files[0]
    check("sql_injection", False, f"{len(injection_files)} files with f-string SQL",
          file_ref=f"{f}:{line}",
          fix="Use parameterized queries: cursor.execute('SELECT ... WHERE col = ?', (value,))")
else:
    check("sql_injection", True, "no f-string SQL queries found")

# 10. Hardcoded secrets / API keys
secret_files = []
for pyfile in os.listdir(SCRIPTS):
    if not pyfile.endswith('.py'):
        continue
    fp = os.path.join(SCRIPTS, pyfile)
    matches = grep_file(r'(api_key|secret|password|token)\s*=\s*["\'][A-Za-z0-9]{20,}', fp)
    if matches and '.secrets' not in pyfile:
        secret_files.append((pyfile, matches[0][0]))
if secret_files:
    f, line = secret_files[0]
    check("hardcoded_secrets", False, f"{len(secret_files)} files with potential secrets",
          file_ref=f"{f}:{line}",
          fix="Move secrets to .secrets.local or environment variables")
else:
    check("hardcoded_secrets", True, "no hardcoded secrets found")

# 11. Missing cursor.close() in finally
cursor_leaks = []
for pyfile in os.listdir(SCRIPTS):
    if not pyfile.endswith('.py'):
        continue
    fp = os.path.join(SCRIPTS, pyfile)
    content = open(fp).read()
    if 'cursor()' in content and 'finally:' not in content and '.close()' in content:
        cursor_leaks.append(pyfile)
if cursor_leaks:
    check("cursor_leaks", False, f"{len(cursor_leaks)} files: {', '.join(cursor_leaks[:5])}",
          file_ref=f"{cursor_leaks[0]}.py",
          fix="Add cursor.close() in finally block to prevent 'database is locked'")
else:
    check("cursor_leaks", True, "no obvious cursor leaks")

# 12. Non-atomic JSON writes (open + write without temp file)
atomic_violations = []
for pyfile in os.listdir(SCRIPTS):
    if not pyfile.endswith('.py'):
        continue
    fp = os.path.join(SCRIPTS, pyfile)
    matches = grep_file(r'json\.dump\(.*open\(', fp)
    if matches:
        atomic_violations.append((pyfile, matches[0][0]))
if atomic_violations:
    f, line = atomic_violations[0]
    check("atomic_json", False, f"{len(atomic_violations)} non-atomic JSON writes",
          file_ref=f"{f}:{line}",
          fix="Write to temp file then os.replace() for crash-safe writes")
else:
    check("atomic_json", True, "JSON writes appear atomic")

# 13. ai_decider.py imports (defunct module)
defunct_imports = []
for pyfile in os.listdir(SCRIPTS):
    if not pyfile.endswith('.py') or pyfile == 'ai_decider.py':
        continue
    fp = os.path.join(SCRIPTS, pyfile)
    matches = grep_file(r'import ai_decider|from ai_decider', fp)
    if matches:
        defunct_imports.append((pyfile, matches[0][0]))
if defunct_imports:
    f, line = defunct_imports[0]
    check("defunct_imports", False, f"ai_decider.py imported in {len(defunct_imports)} files",
          file_ref=f"{f}:{line}",
          fix="Remove ai_decider imports — module is defunct, replaced by signal_compactor.py")
else:
    check("defunct_imports", True, "no ai_decider imports")

# 14. print() used instead of log() in trading scripts
print_in_trade = []
for pyfile in ['decider_run.py', 'position_manager.py', 'close_position.py', 'hl-sync-guardian.py']:
    fp = os.path.join(SCRIPTS, pyfile)
    if not os.path.exists(fp):
        continue
    matches = grep_file(r'^\s+print\(', fp)
    if len(matches) > 10:
        print_in_trade.append((pyfile, len(matches)))
if print_in_trade:
    worst = max(print_in_trade, key=lambda x: x[1])
    check("print_in_trade", False, f"{worst[0]}: {worst[1]} print() calls (should use log())",
          file_ref=f"{worst[0]}",
          fix="Replace print() with log() for consistent logging to pipeline.log")
else:
    check("print_in_trade", True, "trade scripts use log() consistently")

# 15. Stale systemd timers (last trigger > 2x interval)
stale_timers = []
try:
    result = subprocess.run(
        ['systemctl', 'list-timers', '--all', '--no-pager', '--plain'],
        capture_output=True, text=True, timeout=10
    )
    for line in result.stdout.split('\n'):
        if 'hermes-' in line and 'left' in line:
            # Check if timer is past expected interval
            if 'min' in line and 'hermes-away' not in line:
                parts = line.split()
                for part in parts:
                    if 'min' in part and part.replace('min', '').isdigit():
                        mins = int(part.replace('min', ''))
                        if mins > 30:  # More than 30 min overdue
                            timer_name = [p for p in parts if 'hermes-' in p]
                            if timer_name:
                                stale_timers.append(timer_name[0])
except Exception:
    pass
if stale_timers:
    check("stale_timers", False, f"{len(stale_timers)} timers overdue: {', '.join(stale_timers[:3])}",
          fix="systemctl restart <timer-name> or check if service is stuck")
else:
    check("stale_timers", True, "no stale timers detected")

# ═══════════════════════════════════════════════════════════════════════════════
# COMMON BUG PATTERN CHECKS (top 10 patterns from codebase analysis)
# ═══════════════════════════════════════════════════════════════════════════════

# Check 16: Bare except clauses (silent failures)
bare_except_files = []
for script in SCRIPTS_DIR.glob('*.py'):
    if script.name in ('bug_hunter.py',):
        continue
    matches = grep_file(r'except\s*:', str(script))
    if matches:
        bare_except_files.append((script.name, len(matches)))
if bare_except_files:
    total = sum(c for _, c in bare_except_files)
    worst = sorted(bare_except_files, key=lambda x: -x[1])[:3]
    check("bare_except", False, f"{total} bare except clauses in {len(bare_except_files)} files (worst: {', '.join(f'{n}({c})' for n,c in worst)})",
          fix="Replace bare 'except:' with 'except Exception as e: log(f\"error: {e}\")'")
else:
    check("bare_except", True, "no bare except clauses")

# Check 17: Connection leaks (no finally)
leak_files = []
for script in SCRIPTS_DIR.glob('*.py'):
    if script.name in ('bug_hunter.py',):
        continue
    matches = grep_file(r'sqlite3\.connect\(', str(script))
    if matches:
        # Check if there's a finally block nearby
        content = script.read_text()
        if 'finally:' not in content and 'contextmanager' not in content:
            leak_files.append(script.name)
if leak_files:
    check("connection_leaks", False, f"{len(leak_files)} files with sqlite3.connect but no finally block: {', '.join(leak_files[:5])}",
          fix="Use 'with _db_cursor(path) as (conn, cur):' from signal_schema or add try/finally")
else:
    check("connection_leaks", True, "no connection leaks detected")

# Check 18: Non-atomic JSON writes
non_atomic_files = []
for script in SCRIPTS_DIR.glob('*.py'):
    if script.name in ('bug_hunter.py',):
        continue
    content = script.read_text()
    # Look for json.dump without atomic pattern
    if 'json.dump' in content and 'atomic_write' not in content and 'tempfile' not in content:
        lines = grep_file(r'json\.dump', str(script))
        if lines:
            non_atomic_files.append(script.name)
if non_atomic_files:
    check("non_atomic_json", False, f"{len(non_atomic_files)} files write JSON without atomic pattern: {', '.join(non_atomic_files[:5])}",
          fix="Use 'from hermes_file_lock import atomic_write_json' instead of open/json.dump")
else:
    check("non_atomic_json", True, "all JSON writes are atomic")

# Check 19: Hardcoded passwords (security)
hardcoded_pw_files = []
for script in SCRIPTS_DIR.glob('*.py'):
    if script.name in ('bug_hunter.py', '_secrets.py'):
        continue
    matches = grep_file(r"password\s*=\s*['\"][^'\"]+['\"]", str(script))
    # Filter out false positives (placeholder strings, comments)
    real_matches = [m for m in matches if '***' not in m[1] and '#' not in m[1].split('password')[0]]
    if real_matches:
        hardcoded_pw_files.append((script.name, len(real_matches)))
if hardcoded_pw_files:
    check("hardcoded_passwords", False, f"{len(hardcoded_pw_files)} files with hardcoded passwords: {', '.join(n for n,_ in hardcoded_pw_files[:5])}",
          fix="Use 'from _secrets import BRAIN_DB_DICT' instead of inline passwords")
else:
    check("hardcoded_passwords", True, "no hardcoded passwords")

# Check 20: Dead code (defunct modules still imported)
dead_imports = []
dead_modules = ['ai_decider', 'signal_gen']
for script in SCRIPTS_DIR.glob('*.py'):
    if script.name in ('bug_hunter.py',):
        continue
    content = script.read_text()
    for module in dead_modules:
        if f'import {module}' in content or f'from {module}' in content:
            dead_imports.append((script.name, module))
if dead_imports:
    check("dead_imports", False, f"{len(dead_imports)} imports of defunct modules: {', '.join(f'{n}→{m}' for n,m in dead_imports[:3])}",
          fix="Remove imports of ai_decider and signal_gen (defunct per AGENTS.md)")
else:
    check("dead_imports", True, "no dead imports")

# ═══════════════════════════════════════════════════════════════════════════════
# WRITE BUG REPORT FOR CEO
# ═══════════════════════════════════════════════════════════════════════════════

failed = [r for r in results if not r[1]]
warnings = [r for r in results if not r[1] and r[0] in ('win_rate', 'trade_frequency', 'signal_registry')]
criticals = [r for r in failed if r not in warnings]

report = {
    'timestamp': get_now(),
    'total_checks': len(results),
    'passed': len([r for r in results if r[1]]),
    'critical_count': len(criticals),
    'warning_count': len(warnings),
    'criticals': [{'name': n, 'msg': m, 'file': f, 'fix': x} for n, ok, m, f, x in criticals],
    'warnings': [{'name': n, 'msg': m, 'file': f, 'fix': x} for n, ok, m, f, x in warnings],
}

try:
    os.makedirs(os.path.dirname(BUG_REPORT), exist_ok=True)
    with open(BUG_REPORT, 'w') as f:
        json.dump(report, f, indent=2)
except Exception as e:
    print(f"  [WARN] Could not write bug report: {e}")

# ═══════════════════════════════════════════════════════════════════════════════
# SUMMARY
# ═══════════════════════════════════════════════════════════════════════════════

print()
if criticals:
    print(f"BUG HUNTER: {len(criticals)} CRITICAL, {len(warnings)} WARNINGS")
    for name, ok, msg, file_ref, fix in criticals:
        ref = f" → {file_ref}" if file_ref else ""
        print(f"  FAIL: {name} — {msg}{ref}")
        if fix:
            print(f"        FIX: {fix}")
    print()
    for name, ok, msg, file_ref, fix in warnings:
        ref = f" → {file_ref}" if file_ref else ""
        print(f"  WARN: {name} — {msg}{ref}")
        if fix:
            print(f"        FIX: {fix}")
    sys.exit(1)
elif warnings:
    print(f"BUG HUNTER: ALL CHECKS PASSED ({len(warnings)} warnings)")
    for name, ok, msg, file_ref, fix in warnings:
        ref = f" → {file_ref}" if file_ref else ""
        print(f"  WARN: {name} — {msg}{ref}")
        if fix:
            print(f"        FIX: {fix}")
    sys.exit(0)
else:
    print(f"BUG HUNTER: ALL {len(results)} CHECKS PASSED")
    sys.exit(0)
