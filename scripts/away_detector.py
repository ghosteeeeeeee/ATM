#!/usr/bin/env python3
"""
away_detector.py — Self-Initiative Mode for Hermes

Runs every 15 minutes via systemd timer.
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

from paths import *
# ── Config ──────────────────────────────────────────────────────────────────
AWAY_FILE       = '/root/.hermes/data/last_user_message_at.json'
DEBOUNCE_FILE   = '/root/.hermes/data/self_init_last_run.json'
LOG_FILE        = '/root/.hermes/logs/away_detector.log'
PIPELINE_HB     = PIPELINE_HB_FILE
DEBOUNCE_HOURS  = 4.0   # 4h between CEO calls (matches hermes-ceo.timer interval)
AWAY_THRESHOLD  = 20    # minutes
# ────────────────────────────────────────────────────────────────────────────

from hermes_log import log
LOG_STAMP = lambda: datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')


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
    """Return True if live trading is enabled.

    FIX (2026-05-20): Was reading hype_live_trading.json directly, causing
    split-brain with hyperliquid_exchange.is_live_trading_enabled() (which uses
    hermes_constants.LIVE_TRADING_ENABLED). Now delegates to the canonical source.
    """
    from hyperliquid_exchange import is_live_trading_enabled as _hle
    return _hle()


def get_debounce_ts():
    data = load_json(DEBOUNCE_FILE, {})
    return data.get('last_run_ts', 0)


def set_debounce_ts():
    save_json(DEBOUNCE_FILE, {'last_run_ts': time.time()})


def call_ceo():
    """Call CEO via systemd service with away-mode prompt."""
    log(f"  Calling CEO (away mode)...")

    # Write away prompt to a temp file for the CEO to read
    away_prompt = '/root/.hermes/automation/ceo/ceo_away_prompt.md'
    if not os.path.exists(away_prompt):
        log(f"  CEO away prompt not found: {away_prompt}")
        return

    # Trigger CEO service — it runs run_ceo.sh which calls opencode
    # The CEO service starts opencode as foreground, so the server is available
    try:
        # Use systemctl start (non-blocking for oneshot services)
        result = subprocess.run(
            ['systemctl', 'start', 'hermes-ceo.service'],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            set_debounce_ts()
            log(f"  CEO service triggered successfully")
        else:
            log(f"  CEO service trigger failed: {result.stderr}")
    except subprocess.TimeoutExpired:
        # Service started but hasn't finished yet — that's OK for oneshot
        set_debounce_ts()
        log(f"  CEO service started (running in background)")
    except Exception as e:
        log(f"  CEO service trigger error: {e}")


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
        log("Pipeline unhealthy — skipping CEO call to avoid disruption")
        return

    # Check debounce (15 min between CEO calls)
    last_run = get_debounce_ts()
    if last_run > 0 and (time.time() - last_run) < (DEBOUNCE_HOURS * 3600):
        elapsed = (time.time() - last_run) / 60
        log(f"Debounce active — last CEO call {elapsed:.0f}min ago (min interval={DEBOUNCE_HOURS*60:.0f}min)")
        return

    # Execute or dry-run
    if '--execute' in sys.argv:
        call_ceo()
    else:
        log(f"[DRY RUN] Would call CEO (away mode)")
        log(f"  Pass --execute to actually call")


if __name__ == '__main__':
    main()
