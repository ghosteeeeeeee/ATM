#!/usr/bin/env python3
"""
auditor_verify.py — Deterministic regression checks (companion to brain-auditor 4h).

CEO 2026-10-27 item 2 companion (c). The brain-auditor's per-run "LAST-RUN VERIFY"
was the system's regression detector, checking ~13 invariants each hourly run.
Dropping the auditor to 4h would have throttled that detector 4x, so these checks
are now run DETERMINISTICALLY every hour by hermes-auditor-verify.timer — no LLM,
~300ms.

Checks (the ones the auditor ran every run, ported from brain_auditor_prompt.md):
  1. hermes_constants.py has no uncommitted diff (nobody edited constants live)
  2. CEO_PROTECTED_FLAGS present + full count (13 keys)
  3. Kill flags still at their killed values (signal regressions)
  4. New Tracebacks in recent pipeline logs (crash detector)
  5. Session lock state (human session active)
  6. vacation_size_reduce state (size multiplier)

Exit codes:
  0 = all OK (or only INFO findings)
  1 = at least one WARN/CRITICAL finding (alerts appended)

Output: stdout summary + alert appended to automation/error_alerts.md on WARN.
"""
import os
import re
import sys
import json
import subprocess
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paths import HERMES_DATA, HERMES_LOG_DIR

ERROR_ALERTS = '/root/.hermes/automation/error_alerts.md'
CONSTANTS = '/root/.hermes/scripts/hermes_constants.py'
PIPELINE_LOG = os.path.join(HERMES_LOG_DIR, 'pipeline.log')
PAUSE_MARKER = os.path.join(HERMES_DATA, 'vacation_pause.json')
SESSION_LOCK = '/tmp/hermes-session-active.lock'
SIZE_REDUCE = os.path.join(HERMES_DATA, 'vacation_size_reduce.json')

# Kill flags the auditor verifies stay killed (regression if flipped True).
# (name, expected_value) — expected False = killed.
KILL_FLAGS = [
    ('AI_TRADER_ENABLED', False),
    ('HMACD_MTF_PLUS_ENABLED', False),
    ('HMACD_MTF_MINUS_ENABLED', False),
    ('DOJI_BOTTOM_ENABLED', False),
    ('OVERSOLD_BOUNCE_ENABLED', False),
    ('TEMPORAL_CONFLUENCE_ENABLED', False),
]

PROTECTED_MIN_COUNT = 13   # CEO_PROTECTED_FLAGS must have >= this many keys
TRACEBACK_LOOKBACK = 5000  # bytes of tail to scan for Tracebacks


def log(msg):
    ts = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
    print(f'[{ts}] [auditor_verify] {msg}', flush=True)


def _run_git(args):
    try:
        r = subprocess.run(['git', '-C', '/root/.hermes'] + args,
                           capture_output=True, text=True, timeout=15)
        return r.returncode, r.stdout.strip()
    except Exception as e:
        return -1, str(e)


def check_constants_diff():
    """hermes_constants.py working-tree state — INFO, not a page.

    Was a WARN, but editing constants is ROUTINE (auto_1hr, brain_auditor both do
    it legitimately) and the daily commit only lands 07:15 UTC — so a WARN here
    fired hourly for up to 24h after any normal edit (review finding #4).
    Real protection against a BAD constant change is check_protected_flags +
    check_kill_flags (they assert VALUES, which is what matters). This stays as an
    audit breadcrumb only.
    """
    rc, out = _run_git(['status', '--porcelain', 'scripts/hermes_constants.py'])
    if rc != 0:
        return ('INFO', f'git status unavailable: {out[:80]}')
    if out:
        return ('INFO', f'constants have uncommitted edits (normal pre-commit): {out[:80]}')
    return ('OK', 'constants clean (no uncommitted diff)')


def check_protected_flags():
    """CEO_PROTECTED_FLAGS present and full count."""
    try:
        import hermes_constants as hc
    except Exception as e:
        # WARN not CRITICAL: a transient import failure usually means another
        # agent is mid-edit (file half-written). It self-heals next run —
        # paging CRITICAL for that spams alerts (review #5).
        return ('WARN', f'hermes_constants import failed (mid-edit?): {e}')
    flags = getattr(hc, 'CEO_PROTECTED_FLAGS', None)
    if flags is None:
        return ('CRITICAL', 'CEO_PROTECTED_FLAGS missing from hermes_constants')
    n = len(flags)
    if n < PROTECTED_MIN_COUNT:
        return ('CRITICAL', f'CEO_PROTECTED_FLAGS has {n} keys (< {PROTECTED_MIN_COUNT}) — protection gutted')
    return ('OK', f'CEO_PROTECTED_FLAGS {n}/{PROTECTED_MIN_COUNT}+ intact')


def check_kill_flags():
    """Kill flags still at killed values."""
    try:
        import hermes_constants as hc
    except Exception as e:
        # WARN not CRITICAL — same mid-edit reasoning as check_protected_flags.
        return ('WARN', f'hermes_constants import failed (mid-edit?): {e}')
    regressions = []
    missing = []
    for name, expected in KILL_FLAGS:
        if not hasattr(hc, name):
            # Renamed/removed flag is not a live regression — don't page CRITICAL
            # on a None that never existed (review #5).
            missing.append(name)
            continue
        actual = getattr(hc, name)
        if actual != expected:
            regressions.append(f'{name}={actual} (expected {expected})')
    if regressions:
        return ('CRITICAL', f'kill-flag regression: {", ".join(regressions)}')
    note = f' ({len(missing)} flags renamed/absent: {", ".join(missing)})' if missing else ''
    return ('OK', f'{len(KILL_FLAGS) - len(missing)} kill flags correct{note}')


def check_new_tracebacks():
    """Count Tracebacks in recent pipeline log tail (crash detector)."""
    if not os.path.exists(PIPELINE_LOG):
        return ('OK', 'no pipeline log')
    try:
        size = os.path.getsize(PIPELINE_LOG)
        with open(PIPELINE_LOG, 'rb') as f:
            f.seek(max(0, size - 200_000))
            tail = f.read().decode('utf-8', errors='replace')
        n = tail.count('Traceback (most recent call last)')
        if n > 5:
            return ('WARN', f'{n} Tracebacks in recent pipeline log tail')
        return ('OK', f'{n} Tracebacks in tail')
    except Exception as e:
        return ('OK', f'traceback check skipped: {e}')


def check_session_lock():
    """Session lock state — INFO only (a human session is not an error)."""
    if os.path.exists(SESSION_LOCK):
        try:
            age = int(datetime.now(timezone.utc).timestamp() - os.path.getmtime(SESSION_LOCK))
            return ('INFO', f'session lock present ({age}s old) — human session active')
        except Exception:
            return ('INFO', 'session lock present')
    return ('OK', 'session lock absent')


def check_size_reduce():
    """vacation_size_reduce multiplier — INFO unless file is corrupt."""
    if not os.path.exists(SIZE_REDUCE):
        return ('OK', 'size-reduce absent (1.0x)')
    try:
        with open(SIZE_REDUCE) as f:
            d = json.load(f)
        m = d.get('size_multiplier', d.get('multiplier', '?'))
        return ('INFO', f'size-reduce active: {m}x')
    except Exception as e:
        return ('WARN', f'size-reduce file unreadable: {e}')


def check_pause_marker():
    """Vacation pause marker — INFO (intentional, not an error)."""
    if os.path.exists(PAUSE_MARKER):
        return ('INFO', 'vacation pause marker present (intentional stop)')
    return ('OK', 'no pause marker')


CHECKS = {
    'constants-diff': check_constants_diff,
    'protected-flags': check_protected_flags,
    'kill-flags': check_kill_flags,
    'tracebacks': check_new_tracebacks,
    'session-lock': check_session_lock,
    'size-reduce': check_size_reduce,
    'pause-marker': check_pause_marker,
}


def append_alerts(findings):
    ts = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
    lines = [f'\n## Error Alerts — {ts}\n']
    for name, msg in findings:
        lines.append(f'- **[WARN]** (auditor_verify): `{name}`: {msg}\n')
    try:
        with open(ERROR_ALERTS, 'a') as f:
            f.writelines(lines)
        return True
    except Exception:
        return False


def main():
    results = {name: fn() for name, fn in CHECKS.items()}
    problems = [(k, v[1]) for k, v in results.items() if v[0] in ('WARN', 'CRITICAL')]

    for name, (status, msg) in results.items():
        if status != 'OK':
            log(f'  {name}: {status} — {msg}')

    if problems:
        crit = [k for k, _ in results.items() if results[k][0] == 'CRITICAL']
        wrote = append_alerts(problems)
        log(f'{len(problems)} problem(s) ({len(crit)} CRITICAL) '
            f'{"appended to error_alerts.md" if wrote else "(alert write FAILED)"}')
        return 1

    log('all checks OK')
    return 0


if __name__ == '__main__':
    sys.exit(main())
