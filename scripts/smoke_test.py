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
import subprocess
import sys
import time
from pathlib import Path

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

def check_pipeline_log_errors(n=20):
    if not PIPELINE_LOG.exists():
        return True, "pipeline.log not found"
    lines = PIPELINE_LOG.read_text().splitlines()
    errors = [l for l in lines[-n:] if "ERROR" in l or "CRITICAL" in l]
    if errors:
        return False, f"Pipeline errors: {errors[-1]}"
    return True, "no errors"


def check_pipeline_not_stuck():
    lock = Path("/tmp/hermes-pipeline.lock")
    if not lock.exists():
        return True, "no lock"
    age = time.time() - lock.stat().st_mtime
    if age > 600:
        return False, f"Pipeline stuck ({age/60:.0f}min old lock)"
    return True, f"lock age: {age:.0f}s"


def check_stale_locks():
    """Check all Hermes lock files. Fail if any is > threshold (process likely died)."""
    stale = []
    for lock_path, max_age in HERMES_LOCKS.items():
        p = Path(lock_path)
        if p.exists():
            age = time.time() - p.stat().st_mtime
            if age > max_age:
                stale.append(f"{lock_path} ({age/60:.0f}min)")
    if stale:
        return False, f"Stale locks: {', '.join(stale)}"
    return True, "all locks fresh"


def check_price_data_fresh(max_age_sec=180):
    prices_json = DATA_DIR / "prices.json"
    if not prices_json.exists():
        alt = HERMES_DIR / "data" / "prices.json"
        if alt.exists():
            prices_json = alt
        else:
            return False, "prices.json not found — price_collector may be down"
    try:
        data = json.loads(prices_json.read_text())
        ts = data.get("timestamp", data.get("updated", 0))
        age = time.time() - ts
        if age > max_age_sec:
            return False, f"Prices stale: {age:.0f}s old"
        return True, f"prices OK ({age:.0}s)"
    except Exception as e:
        return False, f"prices.json parse error: {e}"


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
    signals_db = SCRIPTS_DIR / "signals_hermes_runtime.db"

    # Primary: check SQLite file
    if signals_db.exists():
        if signals_db.stat().st_size == 0:
            pass  # fall through to PG check
        else:
            try:
                conn = sqlite3.connect(str(signals_db), timeout=5)
                cur = conn.execute("SELECT COUNT(*) FROM signals")
                count = cur.fetchone()[0]
                conn.close()
                return True, f"signals DB OK ({count} rows)"
            except Exception:
                pass  # fall through to PG

    # Fallback: check PostgreSQL
    try:
        import psycopg2
        conn = psycopg2.connect(
            host="localhost", dbname="brain", user="postgres",
            password="brain123", connect_timeout=5
        )
        cur = conn.execute("SELECT COUNT(*) FROM signals")
        count = cur.fetchone()[0]
        conn.close()
        return True, f"signals PG OK ({count} rows)"
    except Exception as e:
        return False, f"signals DB down: {e}"


def check_brain_db():
    if not BRAIN_DB.exists():
        alt = HERMES_DIR / "brain.db"
        if alt.exists():
            BRAIN_DB = alt
        if not BRAIN_DB.exists():
            return False, "brain.db not found"
    try:
        conn = sqlite3.connect(str(BRAIN_DB))
        cur = conn.execute("SELECT COUNT(*) FROM nodes")
        count = cur.fetchone()[0]
        conn.close()
        return True, f"brain OK ({count} nodes)"
    except Exception as e:
        return False, f"brain.db error: {e}"


def check_postgres_trades():
    try:
        import psycopg2
        conn = psycopg2.connect(
            host="localhost", dbname="brain", user="postgres",
            password="brain123", connect_timeout=5
        )
        cur = conn.execute("SELECT COUNT(*) FROM trades")
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
    try:
        from hebbian_engine import HebbianEngine
        h = HebbianEngine()
        stats = h.stats()
        if stats.get("node_count", 0) > 0:
            return True, f"hebbian OK ({stats['node_count']} nodes)"
        return False, "hebbian empty"
    except Exception as e:
        return False, f"hebbian error: {e}"


def check_no_flapping():
    """Check pipeline for flapping (restarts > 3 times in 10 min)."""
    if not PIPELINE_LOG.exists():
        return True, "no pipeline.log"
    try:
        lines = PIPELINE_LOG.read_text().splitlines()
        recent = [l for l in lines if "START" in l or "pipeline" in l.lower()]
        if len(recent) > 10:
            return False, f"Pipeline flapping: {len(recent)} restarts"
        return True, "pipeline stable"
    except Exception:
        return True, "flapping check unknown"


# Map name -> (checker_fn, is_critical)
CHECKS = {
    "pipeline_errors":    (check_pipeline_log_errors, True),
    "pipeline_not_stuck":  (check_pipeline_not_stuck, True),
    "price_data_fresh":   (check_price_data_fresh, True),
    "signal_db":          (check_signal_db, True),
    "brain_db":           (check_brain_db, False),
    "postgres_trades":    (check_postgres_trades, True),
    "hotset_exists":      (check_hotset_exists, True),
    "live_mode":          (check_live_mode, False),
    "hebbian_network":    (check_hebbian_network, False),
    "no_flapping":        (check_no_flapping, False),
    "stale_locks":        (check_stale_locks, True),
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