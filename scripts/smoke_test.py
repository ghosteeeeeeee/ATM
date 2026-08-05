#!/usr/bin/env python3
"""
Hermes Pipeline Smoke Test
Runs quick sanity checks on pipeline health after a step or on-demand.
Exit 0 = all clear, exit 1 = problem detected.

Usage:
  python3 smoke_test.py              # full suite
  python3 smoke_test.py --target <script_name>   # targeted check(s) for one script
  python3 smoke_test.py --changed-since <mins>  # check scripts modified in last N minutes
  python3 smoke_test.py --critical               # only critical (pipeline down, prices stale)
  python3 smoke_test.py --heal                  # run checks + auto-heal via minimax AI
"""

import argparse
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
import sqlite3
from paths import *  # single source of truth for paths

HERMES_DIR = Path("/root/.hermes")
SCRIPTS_DIR = HERMES_DIR / "scripts"
DATA_DIR = Path("/var/www/hermes/data")
LOG_DIR = HERMES_DIR / "logs"
BRAIN_DB = HERMES_DIR / "brain" / "associative_memory.db"
PIPELINE_LOG = LOG_DIR / "pipeline.log"
ERROR_LOG = LOG_DIR / "pipeline.err.log"
HYPES_LIVE = DATA_DIR / "hype_live_trading.json"
AUTH_JSON = HERMES_DIR / "auth.json"

SCRIPT_CHECK_MAP = {
    "signal_gen.py":              ["pipeline_errors", "price_data_fresh", "signal_db", "stale_locks"],
    "ai_decider.py":              ["hotset_exists", "signal_db", "pipeline_errors", "stale_locks"],
    "decider_run.py":             ["pipeline_errors", "signal_db", "hotset_exists", "stale_locks"],
    "position_manager.py":        ["pipeline_errors", "postgres_trades", "signal_db"],
    "hl-sync-guardian.py":        ["postgres_trades", "signal_db"],
    "live-decider.py":            ["pipeline_errors", "hotset_exists", "signal_db", "live_mode", "stale_locks"],
    "price_collector.py":          ["price_data_fresh", "stale_locks"],
    "candle_predictor.py":        ["pipeline_errors", "postgres_trades", "stale_locks"],
    "hebbian_engine.py":          ["brain_db", "hebbian_network", "stale_locks"],
    "hebbian_session_learner.py": ["brain_db", "hebbian_network", "stale_locks"],
    "smoke_test.py":              ["pipeline_errors", "price_data_fresh", "signal_db", "brain_db", "postgres_trades", "stale_locks"],
    "run_pipeline.py":            ["pipeline_errors", "pipeline_not_stuck", "no_flapping", "stale_locks"],
    "wasp.py":                    ["pipeline_errors", "postgres_trades", "signal_db", "hotset_exists"],
    "archive-signals.py":         ["signal_db", "pipeline_errors"],
    "hotset.json":                ["hotset_exists"],
    "prices.json":                ["price_data_fresh"],
    "hype_live_trading.json":     ["live_mode"],
    "_secrets.py":               ["postgres_trades"],
    "profit_monster.py":          ["profit_monster_fires", "postgres_trades"],
    "pump_hunter.py":             ["pump_hunter_log", "pump_hunter_positions"],
}

CRITICAL_CHECKS = ["pipeline_errors", "pipeline_not_stuck", "price_data_fresh", "signal_db", "stale_locks"]


# ----------------------------------------------------------------------
# LLM Integration — minimax for AI-assisted healing
# ----------------------------------------------------------------------

def _get_minimax_client():
    """Build minimax OpenAI-compatible client from auth.json."""
    try:
        with open(AUTH_JSON) as f:
            auth = json.load(f)
        creds = (auth.get("credential_pool", {}) or {}).get("minimax", [])
        if not creds:
            return None
        token = creds[0].get("access_token", "")
        if not token:
            return None
        from openai import OpenAI
        return OpenAI(api_key=token, base_url="https://api.minimax.io/v1")
    except Exception:
        return None


def _call_minimax(system_prompt: str, user_prompt: str, max_tokens=800) -> str:
    """Call minimax MiniMax-M2 model. Returns content or empty string on failure."""
    client = _get_minimax_client()
    if not client:
        return ""
    try:
        resp = client.chat.completions.create(
            model="MiniMax-M2",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=max_tokens
        )
        return resp.choices[0].message.content or ""
    except Exception:
        return ""


# ----------------------------------------------------------------------
# Built-in fix functions
# ----------------------------------------------------------------------

def _fix_pipeline_stuck():
    lock = Path("/tmp/hermes-pipeline.lock")
    if lock.exists():
        age = time.time() - lock.stat().st_mtime
        if age > 600:
            lock.unlink()
            return True, f"Removed stale lock ({age/60:.0f}min old)"
    return False, "No stuck lock found"


# Known lock files written by Hermes scripts — check all for staleness
HERMES_LOCKS = {
    "/tmp/hermes-pipeline.lock":      600,   # 10 min
    "/tmp/hermes-guardian.lock":      600,
    "/root/.hermes/locks/ai_decider.lock": 600,
    "/tmp/ai-decider.lock":           600,
    "/tmp/hermes-decider.lock":       600,
}

# Key trading systemd timers that should be running
# Format: (timer_name, is_critical, description)
TRADING_TIMERS = [
    ("hermes-pipeline.timer",              True,  "Pipeline — 1 min cycle"),
    ("hermes-hl-sync-guardian.timer",     True,  "Guardian — live trading reconciliation"),
    ("hermes-price-collector.timer",       True,  "Price collection"),
    ("hermes-self-close-watcher.timer",   True,  "ATR self-close monitoring"),
    ("hermes-hype-paper-sync.timer",       True,  "HL ↔ paper position sync"),
    ("hermes-away-detector.timer",         False, "T absence detection → self-init"),
    ("hermes-context-compactor.timer",     False, "CONTEXT.md compaction (30 min)"),
    ("hermes-brain-sync.timer",            False, "Brain memory sync (hourly)"),
    ("hermes-git-release.timer",          False, "Auto git commit + release (daily)"),
    ("hermes-wasp.timer",                  False, "System health & anomaly detection"),
    ("hermes-smoke-test.timer",            False, "Scheduled smoke tests"),
    ("hermes-pump-hunter.timer",           True,  "Pump hunter vol explosion executor"),
]

# ----------------------------------------------------------------------
# Key trading systemd services (sibling to timer) that should be running.
# NOTE (2026-07-13): Only include services that should be PERSISTENTLY active.
# Type=oneshot services (like hermes-pump-hunter.service) exit cleanly after
# each tick — the TIMER is what should be active, not the service. Including
# them here triggers false "inactive" alarms. The pump-hunter timer is still
# checked in TRADING_TIMERS above.
# ----------------------------------------------------------------------
TRADING_SERVICES = [
    # ("hermes-pump-hunter.service",  True,  "Pump hunter vol explosion executor"),  # Type=oneshot — checked via timer
]

def _fix_stale_locks():
    """Remove all stale Hermes lock files."""
    removed = []
    for lock_path, max_age in HERMES_LOCKS.items():
        p = Path(lock_path)
        if p.exists():
            age = time.time() - p.stat().st_mtime
            if age > max_age:
                try:
                    p.unlink()
                    removed.append(lock_path)
                except Exception:
                    pass
    if removed:
        return True, f"Removed stale locks: {', '.join(removed)}"
    return False, "No stale locks found"


def _fix_price_stale():
    r = subprocess.run(
        ["sudo", "systemctl", "restart", "hermes-price-collector.service"],
        capture_output=True, timeout=15
    )
    if r.returncode == 0:
        return True, "price_collector restarted"
    return False, f"Failed: {r.stderr.decode()}"


def _fix_hotset_stale():
    r = subprocess.run(
        ["sudo", "systemctl", "restart", "hermes-ai-decider.service"],
        capture_output=True, timeout=15
    )
    if r.returncode == 0:
        return True, "ai_decider restarted"
    return False, "Failed to restart ai_decider"


def _fix_pipeline_errors():
    r = subprocess.run(
        ["sudo", "systemctl", "restart", "hermes-pipeline.service"],
        capture_output=True, timeout=20
    )
    if r.returncode == 0:
        return True, "Pipeline restarted"
    return False, "Failed to restart pipeline"


def _fix_postgres_trades():
    r = subprocess.run(
        ["sudo", "systemctl", "restart", "postgresql"],
        capture_output=True, timeout=20
    )
    if r.returncode == 0:
        return True, "postgresql restarted"
    return False, "Failed to restart postgresql"


HEAL_MAP = {
    "pipeline_not_stuck": (_fix_pipeline_stuck, True),
    "stale_locks":        (_fix_stale_locks, True),
    "price_data_fresh":   (_fix_price_stale, True),
    "signal_db":          (None, False),   # signals live in PG — no local fix
    "hotset_exists":      (_fix_hotset_stale, True),
    "pipeline_errors":    (_fix_pipeline_errors, True),
    "no_flapping":       (None, False),   # human required
    "postgres_trades":   (_fix_postgres_trades, True),
    # read-only — no heal
    "brain_db":           (None, False),
    "live_mode":         (None, False),
    "hebbian_network":   (None, False),
}


# ----------------------------------------------------------------------
# Individual checks
# ----------------------------------------------------------------------

def check_pipeline_log_errors(n=200):
    """Tail the last N lines of pipeline.log via subprocess (avoids loading 1+ GB files).

    Note (2026-07-13): was reading entire file with read_text().splitlines() which
    takes >60s on the 1.3 GB pipeline.log. Now uses `tail -n N` which streams the
    tail regardless of file size.
    """
    if not PIPELINE_LOG.exists():
        return True, "pipeline.log not found"
    try:
        r = subprocess.run(
            ["tail", "-n", str(n), str(PIPELINE_LOG)],
            capture_output=True, text=True, timeout=10
        )
        if r.returncode != 0:
            return False, f"tail failed: {r.stderr.strip()}"
        lines = r.stdout.splitlines()
        errors = [l for l in lines if "ERROR" in l or "CRITICAL" in l]
        if errors:
            return False, f"Pipeline errors: {errors[-1][:200]}"
        return True, "no errors"
    except subprocess.TimeoutExpired:
        return False, "tail timed out (>10s on pipeline.log)"
    except Exception as e:
        return False, f"pipeline log check error: {e}"


def check_pipeline_not_stuck():
    """Check if the pipeline lock indicates a stuck pipeline.

    NOTE (2026-07-13): hermes-pipeline is driven by hermes-pipeline.timer
    (Type=oneshot) — each tick spawns a fresh python process that exits cleanly.
    The lock file written by the previous run is ORPHANED DEBRIS if the timer is
    still firing fresh "Pipeline done" lines. Only treat as stuck if BOTH:
      (a) lock is old, AND
      (b) the pipeline.log shows no recent "Pipeline done" lines (timer dead)
    """
    lock = Path("/tmp/hermes-pipeline.lock")
    if not lock.exists():
        return True, "no lock"
    age = time.time() - lock.stat().st_mtime
    if age <= 600:
        return True, f"lock age: {age:.0f}s"

    # Old lock — check if pipeline is actually still firing
    # Accept either "Pipeline done" (end of cycle) or "Pipeline LIVE" (start of cycle).
    if PIPELINE_LOG.exists():
        try:
            r = subprocess.run(
                # 1000 lines covers ~15min — comfortably above the 5min cutoff.
                ["tail", "-n", "1000", str(PIPELINE_LOG)],
                capture_output=True, text=True, timeout=5
            )
            if r.returncode == 0:
                from datetime import datetime, timezone
                cutoff = time.time() - 300  # 5 min
                for line in r.stdout.splitlines():
                    if "Pipeline done" not in line and "Pipeline LIVE" not in line:
                        continue
                    try:
                        ts_str = line.split(']')[0].replace('[', '')
                        ts = datetime.strptime(ts_str, '%Y-%m-%d %H:%M:%S').timestamp()
                        if ts >= cutoff:
                            # Pipeline is alive — orphan lock from a prior crashed run
                            return True, f"lock is orphan debris ({age/60:.0f}min old, but pipeline active at {datetime.fromtimestamp(ts).strftime('%H:%M:%S')})"
                    except (ValueError, IndexError):
                        pass
        except subprocess.TimeoutExpired:
            pass

    # Lock is old AND no recent pipeline activity — truly stuck
    holders = _get_lock_holder_pid(str(lock))
    if holders:
        dead = [p for p in holders if not _pid_alive(p)]
        if dead:
            return False, f"Pipeline stuck ({age/60:.0f}min old lock, dead holders: {dead})"
        return True, f"lock held by live PID(s): {holders}"
    return False, f"Pipeline stuck ({age/60:.0f}min old lock, no holder, no recent pipeline activity)"


def _pid_alive(pid: int) -> bool:
    """Check if a process is alive."""
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def _get_lock_holder_pid(lock_path: str) -> list:
    """Return list of PIDs holding a lock (via lsof)."""
    try:
        r = subprocess.run(
            ['lsof', lock_path], capture_output=True, text=True, timeout=10
        )
        pids = []
        for line in r.stdout.splitlines()[1:]:  # skip header
            parts = line.split()
            if parts:
                try:
                    pids.append(int(parts[1]))
                except ValueError:
                    pass
        return pids
    except Exception:
        return []


def check_stale_locks():
    """Check all Hermes lock files. Fail if > threshold AND holder process is dead.

    FIX (2026-07-13): /tmp/hermes-pipeline.lock can be orphaned debris because
    hermes-pipeline is Type=oneshot (spawned fresh each tick by the timer).
    If pipeline.log shows recent "Pipeline done" lines, treat an old pipeline.lock
    as orphan debris rather than a real stale lock.
    """
    # Is the pipeline actually alive? Used to distinguish orphan lock from real stuck.
    # Accept either "Pipeline done" (end of cycle) or "Pipeline LIVE" (start of cycle).
    pipeline_alive = False
    if PIPELINE_LOG.exists():
        try:
            r = subprocess.run(
                # Pipeline runs every 1min and each cycle logs ~50-100 lines.
                # 1000 lines covers ~15min reliably — well above the 5min cutoff.
                ["tail", "-n", "1000", str(PIPELINE_LOG)],
                capture_output=True, text=True, timeout=5
            )
            if r.returncode == 0:
                from datetime import datetime, timezone
                cutoff = time.time() - 300  # 5 min
                for line in r.stdout.splitlines():
                    # "=== Pipeline done (LIVE) ===" — end of cycle
                    # "=== Pipeline LIVE (1m) ===" — start of cycle
                    if "Pipeline done" not in line and "Pipeline LIVE" not in line:
                        continue
                    try:
                        ts_str = line.split(']')[0].replace('[', '')
                        ts = datetime.strptime(ts_str, '%Y-%m-%d %H:%M:%S').timestamp()
                        if ts >= cutoff:
                            pipeline_alive = True
                            break
                    except (ValueError, IndexError):
                        pass
        except subprocess.TimeoutExpired:
            pass

    stale = []
    for lock_path, max_age in HERMES_LOCKS.items():
        p = Path(lock_path)
        if not p.exists():
            continue
        age = time.time() - p.stat().st_mtime
        if age <= max_age:
            continue

        # Special case: pipeline lock is known orphan debris if pipeline is alive
        if lock_path == "/tmp/hermes-pipeline.lock" and pipeline_alive:
            continue

        holders = _get_lock_holder_pid(lock_path)
        if not holders:
            stale.append(f"{lock_path} ({age/60:.0f}min, no holder)")
        else:
            dead = []
            for pid in holders:
                try:
                    os.kill(pid, 0)  # signal 0 = existence check
                except OSError:
                    dead.append(pid)
            if dead:
                stale.append(f"{lock_path} ({age/60:.0f}min, dead holders: {dead})")
            # else: lock is old but actively held — not stale
    if stale:
        return False, f"Stale locks: {', '.join(stale)}"
    return True, "all locks fresh"


def check_price_data_fresh(max_age_sec=180):
    """Check price data freshness.

    FIX (2026-07-13): The legacy prices.json file is no longer written by the
    pipeline. Real price data lives in:
      - /var/www/hermes/data/hl_cache.json         (price_collector cache)
      - /root/.hermes/data/candles.db              (candle DB mtime)
      - /root/.hermes/data/signals_hermes.db       (signals/price DB mtime)

    Pass if ANY of these has been updated within the freshness window.
    """
    candidates = [
        # (path, kind) — kind just for the message string
        (DATA_DIR / "prices.json",         "prices.json"),
        (HERMES_DIR / "data" / "prices.json", "prices.json"),
        (DATA_DIR / "hl_cache.json",       "hl_cache.json"),
        (HERMES_DIR / "data" / "candles.db",      "candles.db"),
        (HERMES_DIR / "data" / "signals_hermes.db", "signals_hermes.db"),
    ]

    # Try timestamp-bearing files first (prices.json, hl_cache.json)
    for path, kind in candidates[:3]:
        if not path.exists():
            continue
        try:
            data = json.loads(path.read_text())
            ts = data.get("timestamp", data.get("updated", 0))
            if not ts:
                continue
            age = time.time() - ts
            if age > max_age_sec:
                return False, f"{kind} stale: {age:.0f}s old (threshold {max_age_sec}s)"
            return True, f"{kind} OK ({age:.0}s)"
        except Exception as e:
            return False, f"{kind} parse error: {e}"

    # Fall back to DB mtime — at least we know the writer is alive
    for path, kind in candidates[3:]:
        if path.exists():
            age = time.time() - path.stat().st_mtime
            if age > max_age_sec:
                return False, f"{kind} stale: {age:.0f}s old (no timestamp-bearing file found either)"
            return True, f"{kind} OK by mtime ({age:.0}s)"

    return False, "no price data source found — price_collector may be down"


def check_hotset_exists():
    hotset = DATA_DIR / "hotset.json"
    if not hotset.exists():
        alt = HERMES_DIR / "data" / "hotset.json"
        if alt.exists():
            hotset = alt
        else:
            return False, "hotset.json not found — ai_decider may be down"
    age = time.time() - hotset.stat().st_mtime
    if age > 780:
        return False, f"hotset.json stale ({age:.0f}s)"
    return True, f"hotset OK ({age:.0f}s)"


def check_signal_db():
    """Check signals via SQLite (primary) or PostgreSQL (fallback)."""
    import sqlite3
    signals_db = Path(RUNTIME_DB)

    # Primary: check SQLite file
    if signals_db.exists():
        try:
            conn = sqlite3.connect(str(signals_db))
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM signals")
            count = cur.fetchone()[0]
            conn.close()
            return True, f"signals SQLite OK ({count} rows)"
        except Exception:
            pass  # fall through to PG

    # Fallback: check PostgreSQL (Unix socket)
    try:
        import psycopg2
        from _secrets import BRAIN_HOST, BRAIN_PASSWORD
        conn = psycopg2.connect(
            host=BRAIN_HOST, dbname="brain", user="postgres",
            password=BRAIN_PASSWORD, connect_timeout=5
        )
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM signals")
        count = cur.fetchone()[0]
        conn.close()
        return True, f"signals PG OK ({count} rows)"
    except Exception as e:
        return False, f"signals DB down: {e}"


def check_brain_db():
    # Local var to avoid UnboundLocalError
    brain_db = BRAIN_DB
    if not brain_db.exists():
        alt = HERMES_DIR / "brain.db"
        if alt.exists():
            brain_db = alt
        if not brain_db.exists():
            return False, "brain.db not found"
    try:
        conn = sqlite3.connect(str(brain_db))
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM concept_nodes")
        count = cur.fetchone()[0]
        conn.close()
        return True, f"brain OK ({count} nodes)"
    except Exception as e:
        return False, f"brain.db error: {e}"


def check_postgres_trades():
    try:
        import psycopg2
        from _secrets import BRAIN_HOST, BRAIN_PASSWORD
        conn = psycopg2.connect(
            host=BRAIN_HOST, dbname="brain", user="postgres",
            password=BRAIN_PASSWORD, connect_timeout=5
        )
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM trades")
        count = cur.fetchone()[0]
        conn.close()
        return True, f"trades OK ({count})"
    except Exception as e:
        return False, f"postgres down: {e}"


def check_live_mode():
    if HYPES_LIVE.exists():
        try:
            data = json.loads(HYPES_LIVE.read_text())
            mode = data.get("mode", "unknown")
            return True, f"live_mode={mode}"
        except Exception:
            pass
    return True, "live_mode unknown"


def check_hebbian_network():
    sys.path.insert(0, str(SCRIPTS_DIR))
    # paths imported at module level
    try:
        from hebbian_engine import HebbianEngine
        h = HebbianEngine()
        stats = h.get_stats()
        node_count = stats.get("nodes", stats.get("node_count", 0))
        if node_count > 0:
            return True, f"hebbian OK ({node_count} nodes)"
        return False, "hebbian empty"
    except Exception as e:
        return False, f"hebbian error: {e}"


def check_no_flapping():
    """Check pipeline for flapping (restarts > 3 times in 10 min).

    FIX (2026-04-12): Was counting ALL "START"/"pipeline" lines in the entire log
    (458K lines), triggering false positives. Fixed to count only actual pipeline
    cycle completions in the last 60 minutes by checking for "Pipeline done"
    patterns with timestamps.

    FIX (2026-07-13): Switched to `tail -n` via subprocess — pipeline.log is 1.3 GB,
    `read_text().splitlines()` takes >60s. Also tightened restarts counter to use a
    time window (last 60 min) instead of fixed last-5000-lines.
    """
    if not PIPELINE_LOG.exists():
        return True, "no pipeline.log"
    try:
        # Tail last ~5000 lines (covers last ~80min at normal pipeline cadence).
        # 5000 lines via `tail` is instant regardless of file size.
        r = subprocess.run(
            ["tail", "-n", "5000", str(PIPELINE_LOG)],
            capture_output=True, text=True, timeout=10
        )
        if r.returncode != 0:
            return True, "flapping check skipped (tail failed)"
        lines = r.stdout.splitlines()

        # Count actual pipeline completions in the tail window
        from datetime import datetime, timezone
        cutoff = time.time() - 3600  # last 60 min
        completions = 0
        for l in lines:
            if "Pipeline done" in l:
                try:
                    ts_str = l.split(']')[0].replace('[', '')
                    ts = datetime.strptime(ts_str, '%Y-%m-%d %H:%M:%S').timestamp()
                    if ts >= cutoff:
                        completions += 1
                except (ValueError, IndexError):
                    pass

        # Count restarts in tail window (last ~80min) — threshold scaled to window.
        # 1-cycle/min pipeline = ~80 cycles in 80min. Allow up to 5 actual restarts.
        restarts = sum(
            1 for l in lines
            if "restart" in l.lower() and "service" in l.lower()
        )

        # 1-cycle-per-minute pipeline = 60/min normal. Tail of 5000 lines covers
        # ~80min at 1/min. Allow up to 80 completions (small margin for catch-up).
        if completions > 80:
            return False, f"Pipeline flapping: {completions} cycles in last ~80min (>80 threshold)"
        if restarts > 5:
            return False, f"Pipeline flapping: {restarts} service restarts in tail (>5 threshold)"
        return True, f"pipeline stable ({completions} cycles, {restarts} restarts)"
    except subprocess.TimeoutExpired:
        return True, "flapping check skipped (tail timeout)"
    except Exception:
        return True, "flapping check unknown"


def check_profit_monster_fires():
    """Verify profit-monster log was written to recently."""
    log = Path("/root/.hermes/logs/profit_monster.log")
    if not log.exists():
        return False, "profit_monster.log not found"
    try:
        lines = log.read_text().splitlines()
        if not lines:
            return False, "profit_monster.log empty"
        last_line = lines[-1]
        m = re.search(r'\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\]', last_line)
        if not m:
            return False, f"cannot parse log timestamp: {last_line[:50]}"
        last_ts = datetime.strptime(m.group(1), "%Y-%m-%d %H:%M:%S")
        age_sec = (datetime.now() - last_ts).total_seconds()
        if age_sec > 1800:  # 30 min
            return False, f"profit-monster silent ({age_sec/60:.0f}min)"
        return True, f"profit-monster alive ({age_sec:.0f}s ago)"
    except Exception as e:
        return False, f"profit-monster check error: {e}"


def check_trading_timers():
    """Verify all key Hermes systemd timers are running (not expired)."""
    try:
        result = subprocess.run(
            ["systemctl", "list-timers", "--all", "-n", "200"],
            capture_output=True, text=True, timeout=20
        )
        if result.returncode != 0:
            return False, f"systemctl list-timers failed: {result.stderr.strip()}"
        output = result.stdout

        failed = []
        stale = []
        for timer_name, is_critical, desc in TRADING_TIMERS:
            # Check if this timer appears in the list
            for line in output.splitlines():
                if timer_name in line:
                    # Parse the "X ago" and "in Y" columns to detect if it's waiting or elapsed
                    # A timer with a timestamp in the past and no "X ago" or an "X ago" > 2x its interval
                    # is considered stale if its next scheduled time is also past
                    parts = line.split()
                    if len(parts) >= 3:
                        # The "in X" column tells us next run; "X ago" tells us last run
                        # If there's no "in" time, timer may be inactive/masked
                        # Check: is there a NEXT timestamp that is in the past?
                        # Format: "NEXT_TIME  X ago  LAST_TIME  X ago ago  TIMER_NAME"
                        try:
                            # Try to find if timer has a future scheduled time
                            # We check if it's masked (no NEXT time shown)
                            pass
                        except (ValueError, IndexError):
                            pass
                    break
            else:
                # Timer not found in output at all — could be masked or dead
                stale.append(f"{timer_name} (not in list)")

        # More reliable: check each timer individually with systemctl
        failed = []
        for timer_name, is_critical, desc in TRADING_TIMERS:
            r = subprocess.run(
                ["systemctl", "is-active", timer_name],
                capture_output=True, text=True, timeout=5
            )
            state = r.stdout.strip()
            if state != "active":
                failed.append(f"{timer_name}={state}")

        if failed:
            msg = ", ".join(failed)
            return False, f"inactive timers: {msg}"

        # Also check services
        svc_failed = []
        for svc_name, is_critical, desc in TRADING_SERVICES:
            r = subprocess.run(
                ["systemctl", "is-active", svc_name],
                capture_output=True, text=True, timeout=5
            )
            state = r.stdout.strip()
            if state != "active":
                svc_failed.append(f"{svc_name}={state}")

        if svc_failed:
            msg = ", ".join(svc_failed)
            return False, f"inactive services: {msg}"

        total = len(TRADING_TIMERS) + len(TRADING_SERVICES)
        return True, f"all {total} timers/services active"
    except subprocess.TimeoutExpired:
        return False, "systemctl timed out"
    except Exception as e:
        return False, f"timer check error: {e}"


# ----------------------------------------------------------------------
# pump_hunter checks
# ----------------------------------------------------------------------

def check_pump_hunter_log(max_age_sec=600):
    """Verify pump_hunter log was written to recently (10 min threshold)."""
    log = Path("/root/.hermes/data/logs/pump_hunter.log")
    if not log.exists():
        return False, "pump_hunter.log not found"
    try:
        lines = log.read_text().splitlines()
        if not lines:
            return False, "pump_hunter.log empty"
        last_line = lines[-1]
        m = re.search(r'\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\]', last_line)
        if not m:
            # Fallback: [HH:MM:SS] same-day format — prepend today's date
            m2 = re.search(r'\[(\d{2}:\d{2}:\d{2})\]', last_line)
            if not m2:
                return False, f"cannot parse log timestamp: {last_line[:50]}"
            last_ts = datetime.strptime(
                f"{datetime.now().strftime('%Y-%m-%d')} {m2.group(1)}",
                "%Y-%m-%d %H:%M:%S"
            )
        else:
            last_ts = datetime.strptime(m.group(1), "%Y-%m-%d %H:%M:%S")
        age_sec = (datetime.now() - last_ts).total_seconds()
        if age_sec > max_age_sec:
            return False, f"pump_hunter silent ({age_sec/60:.0f}min > {max_age_sec/60:.0f}min)"
        return True, f"pump_hunter alive ({age_sec:.0f}s ago)"
    except Exception as e:
        return False, f"pump_hunter log check error: {e}"


def check_pump_hunter_positions():
    """Verify pump_hunter positions file is accessible (not stale/corrupted)."""
    positions_file = Path("/root/.hermes/data/pump_hunter_positions.json")
    if not positions_file.exists():
        return True, "no pump_hunter positions file (clean)"
    try:
        data = json.loads(positions_file.read_text())
        if not isinstance(data, dict):
            return False, f"pump_hunter_positions.json unexpected type: {type(data)}"
        positions = data.get("positions", data.get("open", []))
        if not positions:
            return True, "pump_hunter positions file clean (0 open)"
        return True, f"pump_hunter positions file OK ({len(positions)} open)"
    except Exception as e:
        return False, f"pump_hunter_positions.json error: {e}"


# ── New checks (system improvement) ────────────────────────────────────────────

def check_obs_metrics_fresh(max_age_sec=600):
    """Verify obs_dashboard metrics are recent (< 10min old)."""
    metrics_file = DATA_DIR / "obs_metrics.json"
    if not metrics_file.exists():
        return False, "obs_metrics.json missing — obs_dashboard not running"
    try:
        data = json.loads(metrics_file.read_text())
        ts = datetime.fromisoformat(data['timestamp'].replace('Z', '+00:00'))
        age_sec = (datetime.now(timezone.utc) - ts).total_seconds()
        if age_sec > max_age_sec:
            return False, f"obs_metrics stale ({age_sec/60:.0f}min > {max_age_sec/60:.0f}min)"
        return True, f"obs_metrics fresh ({age_sec:.0f}s ago)"
    except Exception as e:
        return False, f"obs_metrics error: {e}"


def check_signal_decay_detector(max_age_sec=28800):
    """Verify signal_decay_detector ran recently (< 8h)."""
    log_file = HERMES_DIR / "automation" / "decay_log.md"
    if not log_file.exists():
        return False, "decay_log.md missing — signal_decay_detector never ran"
    try:
        mtime = datetime.fromtimestamp(log_file.stat().st_mtime)
        age_sec = (datetime.now() - mtime).total_seconds()
        if age_sec > max_age_sec:
            return False, f"signal_decay_detector stale ({age_sec/3600:.1f}h > {max_age_sec/3600:.1f}h)"
        return True, f"signal_decay_detector ran ({age_sec/60:.0f}min ago)"
    except Exception as e:
        return False, f"signal_decay_detector check error: {e}"


def check_hl_sync_active():
    """Verify hl-sync-guardian is running."""
    try:
        result = subprocess.run(['systemctl', 'is-active', 'hermes-hl-sync-guardian'],
                              capture_output=True, text=True, timeout=5)
        if result.stdout.strip() == 'active':
            return True, "hl-sync-guardian active"
        return False, "hl-sync-guardian NOT active"
    except Exception as e:
        return False, f"hl-sync check error: {e}"


def check_kill_switches_working():
    """Verify disabled signals are NOT executing (check last 6h of signal_outcomes)."""
    try:
        conn = sqlite3.connect(str(RUNTIME_DB))
        c = conn.cursor()
        # Check for disabled signals that still executed
        c.execute("""
            SELECT signal_type, COUNT(*) as trades
            FROM signal_outcomes
            WHERE trade_id IS NOT NULL
              AND created_at > datetime('now', '-6 hours')
              AND signal_type IN ('inv-accel-300-', 'accel-300-vel+', 'accel-300-vel-',
                                  'bb-squeeze-', 'bb-squeeze+', 'tl_break_long', 'tl_break_short')
            GROUP BY signal_type
        """)
        violations = c.fetchall()
        conn.close()
        if violations:
            names = [f"{v[0]}({v[1]})" for v in violations]
            return False, f"kill switch violations: {', '.join(names)}"
        return True, "no disabled signals executing (6h)"
    except Exception as e:
        return False, f"kill switch check error: {e}"


def check_trailing_stops_exists():
    """Verify trailing_stops.json exists (symlink or file)."""
    ts_file = HERMES_DIR / "data" / "trailing_stops.json"
    if ts_file.exists():
        return True, "trailing_stops.json exists"
    # Check www location
    ts_www = DATA_DIR / "trailing_stops.json"
    if ts_www.exists():
        return True, "trailing_stops.json exists (www only — missing symlink)"
    return False, "trailing_stops.json MISSING"


def check_new_signals_generating():
    """Verify pct_hermes, vel_hermes, fast_momentum are generating signals."""
    try:
        conn = sqlite3.connect(str(RUNTIME_DB))
        c = conn.cursor()
        c.execute("""
            SELECT source, COUNT(*) as cnt
            FROM signals
            WHERE created_at > datetime('now', '-1 hour')
              AND source IN ('pct-hermes+', 'pct-hermes-', 'vel-hermes+', 'vel-hermes-',
                             'fast-momentum+', 'fast-momentum-')
            GROUP BY source
        """)
        results = c.fetchall()
        conn.close()
        if results:
            parts = [f"{r[0]}({r[1]})" for r in results]
            return True, f"new signals generating: {', '.join(parts)}"
        return True, "no new signals in last hour (may be normal)"
    except Exception as e:
        return False, f"new signals check error: {e}"


def check_pattern_scanner_sources():
    """Verify pattern_scanner uses pattern-specific sources."""
    try:
        conn = sqlite3.connect(str(RUNTIME_DB))
        c = conn.cursor()
        c.execute("""
            SELECT source, COUNT(*) as cnt
            FROM signals
            WHERE created_at > datetime('now', '-24 hours')
              AND source LIKE 'pattern_%'
            GROUP BY source
        """)
        results = c.fetchall()
        conn.close()
        if results:
            has_specific = any(r[0] != 'pattern_scanner' for r in results)
            if has_specific:
                parts = [f"{r[0]}({r[1]})" for r in results]
                return True, f"pattern sources OK: {', '.join(parts)}"
            return False, "pattern_scanner still using generic source"
        return True, "no pattern signals in 24h (check later)"
    except Exception as e:
        return False, f"pattern source check error: {e}"


def check_token_speed_tracker():
    """Verify token speed tracker has recent data."""
    try:
        conn = sqlite3.connect(str(RUNTIME_DB))
        c = conn.cursor()
        c.execute("SELECT COUNT(*), MAX(updated_at) FROM token_speeds")
        row = c.fetchone()
        conn.close()
        count = row[0] or 0
        last_update = row[1]
        if count < 50:
            return False, f"speed_tracker low: {count} tokens"
        if last_update:
            try:
                update_dt = datetime.fromisoformat(last_update)
                age = (datetime.now() - update_dt).total_seconds()
                if age > 3600:
                    return False, f"speed_tracker stale ({age/60:.0f}min ago)"
            except Exception:
                pass  # can't parse timestamp, skip age check
        return True, f"speed_tracker OK ({count} tokens)"
    except Exception as e:
        return False, f"speed_tracker check error: {e}"


def check_ceo_timer():
    """Verify CEO timer is running."""
    try:
        result = subprocess.run(['systemctl', 'is-active', 'hermes-ceo.timer'],
                              capture_output=True, text=True, timeout=5)
        if result.stdout.strip() == 'active':
            return True, "CEO timer active"
        return False, "CEO timer NOT active"
    except Exception as e:
        return False, f"CEO timer check error: {e}"


def check_openmemory_accessible():
    """Verify OpenMemory MCP server is responding."""
    try:
        result = subprocess.run(['systemctl', 'is-active', 'hermes-coding-mcp'],
                              capture_output=True, text=True, timeout=5)
        if result.stdout.strip() == 'active':
            return True, "OpenMemory MCP active"
        return False, "OpenMemory MCP NOT active"
    except Exception as e:
        return False, f"OpenMemory check error: {e}"


def check_pipeline_step_timings():
    """Verify pipeline steps complete within reasonable time (< 60s each)."""
    try:
        # Check last pipeline run duration from journal
        result = subprocess.run(
            ['journalctl', '-u', 'hermes-pipeline', '--since', '30 min ago', '--no-pager'],
            capture_output=True, text=True, timeout=10
        )
        output = result.stdout
        # Find "Pipeline done" lines and extract duration
        durations = re.findall(r'Consumed (\d+\.\d+)s CPU time', output)
        if durations:
            max_dur = max(float(d) for d in durations)
            if max_dur > 60:
                return False, f"pipeline step slow ({max_dur:.1f}s > 60s)"
            return True, f"pipeline steps OK (max {max_dur:.1f}s)"
        return True, "no pipeline runs in last 30min"
    except Exception as e:
        return False, f"pipeline timing check error: {e}"


def check_trade_frequency():
    """Verify trade frequency is reasonable (1-20 trades/hr)."""
    try:
        conn = sqlite3.connect(str(RUNTIME_DB))
        c = conn.cursor()
        c.execute("""
            SELECT COUNT(*) FROM signal_outcomes
            WHERE trade_id IS NOT NULL
              AND created_at > datetime('now', '-1 hour')
        """)
        trades = c.fetchone()[0] or 0
        conn.close()
        if trades > 20:
            return False, f"overtrading: {trades} trades/hr (> 20)"
        if trades == 0:
            return True, f"0 trades/hr (may be normal during quiet market)"
        return True, f"trade frequency OK ({trades}/hr)"
    except Exception as e:
        return False, f"trade frequency check error: {e}"


def check_signal_win_rate():
    """Verify overall win rate is above 20% (24h)."""
    try:
        conn = sqlite3.connect(str(RUNTIME_DB))
        c = conn.cursor()
        c.execute("""
            SELECT COUNT(*), SUM(is_win) FROM signal_outcomes
            WHERE trade_id IS NOT NULL
              AND created_at > datetime('now', '-24 hours')
        """)
        row = c.fetchone()
        conn.close()
        total = row[0] or 0
        wins = row[1] or 0
        if total < 5:
            return True, f"insufficient trades ({total}) for WR check"
        wr = wins / total * 100
        if wr < 20:
            return False, f"low win rate: {wr:.1f}% ({wins}/{total})"
        return True, f"win rate OK: {wr:.1f}% ({wins}/{total})"
    except Exception as e:
        return False, f"win rate check error: {e}"


# Map name -> (checker_fn, is_critical)
CHECKS = {
    "pipeline_errors":        (check_pipeline_log_errors, True),
    "pipeline_not_stuck":     (check_pipeline_not_stuck, True),
    "price_data_fresh":      (check_price_data_fresh, True),
    "signal_db":             (check_signal_db, True),
    "brain_db":              (check_brain_db, False),
    "postgres_trades":       (check_postgres_trades, True),
    "hotset_exists":         (check_hotset_exists, True),
    "live_mode":             (check_live_mode, False),
    "hebbian_network":       (check_hebbian_network, False),
    "no_flapping":           (check_no_flapping, False),
    "stale_locks":           (check_stale_locks, True),
    "profit_monster_fires":  (check_profit_monster_fires, False),
    "pump_hunter_log":       (check_pump_hunter_log, True),
    "pump_hunter_positions":  (check_pump_hunter_positions, True),
    "trading_timers":        (check_trading_timers, True),
    # New checks (system improvement)
    "obs_metrics_fresh":     (check_obs_metrics_fresh, False),
    "signal_decay_detector": (check_signal_decay_detector, False),
    "hl_sync_active":        (check_hl_sync_active, True),
    "kill_switches_working": (check_kill_switches_working, True),
    "trailing_stops_exists": (check_trailing_stops_exists, True),
    "new_signals_generating": (check_new_signals_generating, False),
    "pattern_scanner_sources": (check_pattern_scanner_sources, False),
    "token_speed_tracker":   (check_token_speed_tracker, False),
    "ceo_timer":             (check_ceo_timer, False),
    "openmemory_accessible": (check_openmemory_accessible, False),
    "pipeline_step_timings": (check_pipeline_step_timings, False),
    "trade_frequency":       (check_trade_frequency, False),
    "signal_win_rate":       (check_signal_win_rate, False),
}


# ----------------------------------------------------------------------
# Runner
# ----------------------------------------------------------------------

def run_checks(target_names=None, heal=False, verbose=False):
    """Run checks. If heal=True, apply fixes for failed checks."""
    results = []
    for name in (target_names or CHECKS.keys()):
        if name not in CHECKS:
            print(f"Unknown check: {name}")
            continue
        checker, is_critical = CHECKS[name]
        try:
            ok, msg = checker()
        except Exception as e:
            ok, msg = False, f"exception: {e}"
        results.append((name, ok, msg, is_critical))
        status = "PASS" if ok else "FAIL"
        print(f"  [{status}] {name}: {msg}")
        if not ok and heal:
            fixer, can_heal = HEAL_MAP.get(name, (None, False))
            if fixer and can_heal:
                ok2, msg2 = fixer()
                print(f"         healed: {msg2}")
                results[-1] = (name, ok2, msg2, is_critical)
    failed = [r for r in results if not r[1] and r[3]]
    return 0 if not failed else 1


def main():
    parser = argparse.ArgumentParser(description="Hermes smoke test")
    parser.add_argument("--target", help="Run checks for a specific script")
    parser.add_argument("--changed-since", type=int, metavar="MINS", help="Scripts changed in last N minutes")
    parser.add_argument("--critical", action="store_true", help="Critical checks only")
    parser.add_argument("--heal", action="store_true", help="Auto-heal failed checks")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()

    targets = None
    if args.target:
        if args.target not in SCRIPT_CHECK_MAP:
            print(f"Unknown target: {args.target}")
            print(f"Available: {', '.join(SCRIPT_CHECK_MAP.keys())}")
            sys.exit(1)
        targets = SCRIPT_CHECK_MAP[args.target]
    elif args.changed_since:
        cutoff = time.time() - args.changed_since * 60
        targets = []
        for script, checks in SCRIPT_CHECK_MAP.items():
            p = SCRIPTS_DIR / script
            if p.exists() and p.stat().st_mtime > cutoff:
                targets.extend(checks)
        targets = sorted(set(targets))
        print(f"Changed scripts → checks: {targets}")
    elif args.critical:
        targets = CRITICAL_CHECKS

    exit_code = run_checks(targets, heal=args.heal, verbose=args.verbose)

    if exit_code == 0:
        print("\nAll checks passed.")
    else:
        print("\nSome checks FAILED.")
    sys.exit(exit_code)


if __name__ == "__main__":
    main()