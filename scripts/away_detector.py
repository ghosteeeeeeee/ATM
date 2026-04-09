#!/usr/bin/env python3
"""
away_detector.py — Self-Initiative Mode for Hermes

Runs every 5 minutes via cron.
If T has been away > 20 minutes AND there are unblocked agent-owned tasks:
→ Spawn a subagent to work on the highest-priority task.
→ Log everything to /root/.hermes/logs/away_detector.log.

Usage:
    python3 away_detector.py                    # dry run (just checks + logs)
    python3 away_detector.py --execute          # actually spawn subagent
    python3 away_detector.py --update-ts        # update last_message timestamp
"""

import json
import os
import re
import sys
import time
import fcntl
import subprocess
from datetime import datetime, timezone

# ── Config ──────────────────────────────────────────────────────────────────
AWAY_FILE       = '/root/.hermes/data/last_user_message_at.json'
DEBOUNCE_FILE   = '/root/.hermes/data/self_init_last_run.json'
TASKS_FILE      = '/root/.hermes/brain/TASKS.md'
PROJECTS_FILE   = '/root/.hermes/brain/PROJECTS.md'
LOG_FILE        = '/root/.hermes/logs/away_detector.log'
PIPELINE_HB     = '/root/.hermes/data/pipeline_heartbeat.json'
HL_STATUS_FILE  = '/root/.hermes/data/hype_live_trading.json'
DEBOUNCE_HOURS  = 2   # Don't re-spawn if we ran < 2h ago
AWAY_THRESHOLD  = 20  # minutes
# ────────────────────────────────────────────────────────────────────────────

from datetime import datetime, timezone
LOG_STAMP = lambda: datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')


def log(msg):
    stamp = LOG_STAMP()
    line  = f"[{stamp}] {msg}"
    print(line)
    with open(LOG_FILE, 'a') as f:
        f.write(line + '\n')


def load_json(path, default=None):
    try:
        with open(path) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default if default is not None else {}


def save_json(path, data):
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)


def is_t_away():
    """Return True if T has been silent for > AWAY_THRESHOLD minutes."""
    if not os.path.exists(AWAY_FILE):
        return False
    data = load_json(AWAY_FILE)
    ts = data.get('timestamp', 0)
    if ts == 0:
        return False
    elapsed = time.time() - ts
    log(f"Last user message: {elapsed/60:.1f} min ago (threshold={AWAY_THRESHOLD} min)")
    return elapsed > (AWAY_THRESHOLD * 60)


def is_pipeline_healthy():
    """Return True if pipeline log shows a recent run (< 15 min old)."""
    LOG_FILE_PATH = '/root/.hermes/logs/pipeline.log'
    if not os.path.exists(LOG_FILE_PATH):
        log("  pipeline.log missing — assuming OK")
        return True
    try:
        # Read last few lines of pipeline.log
        with open(LOG_FILE_PATH, 'rb') as f:
            f.seek(0, 2)  # EOF
            f.seek(max(0, f.tell() - 4096))
            tail = f.read().decode('utf-8', errors='ignore')
        lines = tail.strip().split('\n')
        for line in reversed(lines):
            if 'Decider Done' in line or 'Running decider-run' in line:
                m = re.search(r'\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\]', line)
                if m:
                    try:
                        log_ts = datetime.strptime(m.group(1) + '+0000', '%Y-%m-%d %H:%M:%S%z')
                        now_ts = datetime.now(timezone.utc)
                        age_sec = (now_ts - log_ts).total_seconds()
                        if age_sec > 900:
                            log(f"  ⚠️ Pipeline log stale: {age_sec/60:.1f} min old")
                            return False
                        return True
                    except ValueError:
                        pass
        log("  Could not parse pipeline log timestamp — assuming OK")
        return True
    except Exception as e:
        log(f"  Error reading pipeline log: {e} — assuming OK")
        return True


def is_live_trading_enabled():
    """Return True if hype_live_trading.json has live_trading=true."""
    if not os.path.exists(HL_STATUS_FILE):
        return True  # assume live if file missing
    data = load_json(HL_STATUS_FILE)
    return data.get('live_trading', False)


def get_debounce_ts():
    data = load_json(DEBOUNCE_FILE, {})
    return data.get('last_run_ts', 0)


def set_debounce_ts():
    save_json(DEBOUNCE_FILE, {'last_run_ts': time.time()})


def parse_task_priority(tasks_md):
    """
    Parse TASKS.md and return highest-priority unblocked agent-owned task.
    Returns (task_line, task_content) or (None, None).
    """
    # Find the ## Priority Tasks section
    lines = tasks_md.split('\n')
    in_priority = False
    candidates = []

    for i, line in enumerate(lines):
        if line.strip() == '## Priority Tasks':
            in_priority = True
            continue
        if line.startswith('## ') and in_priority:
            break  # hit next section
        if in_priority and line.startswith('### [ ]'):
            # Unchecked queued task
            content_lines = [line]
            j = i + 1
            while j < len(lines) and lines[j].startswith('**'):
                content_lines.append(lines[j])
                j += 1
            full = '\n'.join(content_lines)

            # Check if Agent-owned
            owner = 'Agent'
            for cl in content_lines:
                if cl.startswith('**Owner:**'):
                    owner = cl.split('**Owner:**')[1].strip().split(' ')[0]
                if 'Blocked' in cl or 'blocked' in cl:
                    owner = 'T'  # blocked on T

            is_agent = owner == 'Agent'
            is_tbd   = 'TBD' in full

            # Check if already in_progress elsewhere
            already_active = '(IN PROGRESS)' in full or '🚧' in full

            if (is_agent or is_tbd) and not already_active:
                # Extract task name
                name = line.replace('### [ ]', '').strip()
                candidates.append((name, full))

    return candidates


def pick_task():
    """Read TASKS.md, return best task for self-init run."""
    try:
        with open(TASKS_FILE) as f:
            content = f.read()
    except FileNotFoundError:
        log(f"  TASKS.md not found at {TASKS_FILE}")
        return None

    candidates = parse_task_priority(content)
    if not candidates:
        log("  No unblocked agent-owned tasks found in TASKS.md")
        return None

    # Pick first (highest priority) candidate
    name, full = candidates[0]
    log(f"  Selected task: {name}")

    # Extract reference for context
    ref = ''
    for line in full.split('\n'):
        if line.startswith('**Reference:**'):
            ref = line.replace('**Reference:**', '').strip()
        if line.startswith('**What:**'):
            ref += ' | ' + line.replace('**What:**', '').strip()

    return {'name': name, 'detail': ref, 'raw': full[:500]}


def build_subagent_context(task):
    """Build context string for the subagent."""
    ctx = f"""
SELF-INITIATIVE RUN — {LOG_STAMP()}

You are running autonomously because T has been away > 20 minutes.
DO NOT fire any live trades. Work on research, analysis, and PM tasks only.

=== Current System State ===
Pipeline: {'healthy' if is_pipeline_healthy() else 'STALE — investigate before starting'}
Live trading: {'ENABLED' if is_live_trading_enabled() else 'DISABLED (paper only)'}

=== Your Task ===
Task: {task.get('name')}
Detail: {task.get('detail')}
Full: {task.get('raw')}

=== Constraints ===
- Do NOT execute any trades (paper or live)
- Do NOT change live trading flags (hype_live_trading.json, _FLIP_SIGNALS, etc.)
- Do NOT modify max positions or leverage
- If system appears jeopardized → stop immediately, log what happened
- Update trading.md with findings (append under ## SELF-INIT RUN header)
- Update DECISIONS.md / PROJECTS.md / TASKS.md as needed

=== Files to reference ===
- /root/.hermes/brain/trading.md
- /root/.hermes/brain/PROJECTS.md
- /root/.hermes/brain/TASKS.md
- /root/.hermes/brain/DECISIONS.md
- /root/.hermes/data/signals_hermes_runtime.db
- /root/.hermes/logs/pipeline.log

Report back: what you found, what you did, PM files changed, what T should review.
"""
    return ctx


def spawn_subagent(task):
    """Spawn a background subagent to work on the task."""
    ctx = build_subagent_context(task)

    log(f"  Spawning subagent for: {task.get('name')}")
    log(f"  Context: {task.get('detail', '')[:100]}")

    cmd = [
        'python3', '-c',
        f"""
import subprocess, json, sys
result = subprocess.run(
    ['{sys.executable}', '-m', 'hermes_tools', 'delegate_task',
     '--goal', {json.dumps(f"Self-init task: {task.get('name')}")},
     '--context', {json.dumps(ctx)},
     '--toolsets', 'terminal,file'],
    capture_output=True, text=True, timeout=300
)
print(result.stdout[-2000:] if result.stdout else 'no stdout')
print(result.stderr[-500:] if result.stderr else 'no stderr', file=sys.stderr)
"""
    ]

    # Write to a background job script so we don't block
    bg_script = f'/root/.hermes/logs/self_init_{int(time.time())}.sh'
    with open(bg_script, 'w') as f:
        f.write('#!/bin/bash\n')
        f.write(f'echo "SELF-INIT START {LOG_STAMP()}" >> /root/.hermes/logs/away_detector.log\n')
        f.write(f'echo "Task: {task.get("name")}" >> /root/.hermes/logs/away_detector.log\n')
        f.write(f'exit 0\n')

    os.chmod(bg_script, 0o755)

    # Use nohup + redirect — fire and forget
    with open(f'/root/.hermes/logs/self_init_{int(time.time())}.out', 'w') as out:
        subprocess.Popen(
            ['nohup', 'python3', '-c', cmd[2]],
            stdout=out, stderr=subprocess.STDOUT,
            cwd='/root/.hermes'
        )

    set_debounce_ts()
    log(f"  Subagent spawned (pid tracked via bg script)")


LOCK_FILE = '/root/.hermes/logs/away_detector.lock'


def acquire_lock():
    """Open lock file and acquire exclusive non-blocking lock.
    Returns the open file handle if we got it, None if another instance holds it.
    Lock is auto-released when process exits or handle is closed."""
    try:
        lock_fd = open(LOCK_FILE, 'w')
        fcntl.flock(lock_fd.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        lock_fd.write(str(os.getpid()))
        lock_fd.flush()
        return lock_fd
    except (IOError, OSError):
        return None


def main():
    log("=== away_detector run ===")

    lock_fd = acquire_lock()
    if lock_fd is None:
        log("  Another instance already running — exiting")
        return

    # Update timestamp if --update-ts flag
    if '--update-ts' in sys.argv:
        save_json(AWAY_FILE, {'timestamp': time.time(), 'updated_by': 'away_detector'})
        log("Timestamp updated")
        return

    # Check away status
    if not is_t_away():
        log("T is present — no self-init run")
        return

    log("T is AWAY — checking pipeline health")
    if not is_pipeline_healthy():
        log("Pipeline unhealthy — skipping self-init to avoid disruption")
        return

    # Check debounce
    last_run = get_debounce_ts()
    if last_run > 0 and (time.time() - last_run) < (DEBOUNCE_HOURS * 3600):
        elapsed = (time.time() - last_run) / 3600
        log(f"Debounce active — last ran {elapsed:.1f}h ago (threshold={DEBOUNCE_HOURS}h)")
        return

    # Pick task
    task = pick_task()
    if task is None:
        log("No suitable task found")
        return

    # Execute or dry-run
    if '--execute' in sys.argv:
        spawn_subagent(task)
    else:
        log(f"[DRY RUN] Would spawn subagent for: {task.get('name')}")
        log(f"  Detail: {task.get('detail', '')[:120]}")
        log("  Pass --execute to actually spawn")


if __name__ == '__main__':
    main()
