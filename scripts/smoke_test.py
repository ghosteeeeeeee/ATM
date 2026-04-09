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
    "signal_gen.py":              ["pipeline_errors", "price_data_fresh", "signal_db"],
    "ai_decider.py":              ["hotset_exists", "signal_db", "pipeline_errors"],
    "decider_run.py":             ["pipeline_errors", "signal_db", "hotset_exists"],
    "position_manager.py":        ["pipeline_errors", "postgres_trades", "signal_db"],
    "hl-sync-guardian.py":        ["postgres_trades", "signal_db"],
    "live-decider.py":            ["pipeline_errors", "hotset_exists", "signal_db", "live_mode"],
    "price_collector.py":          ["price_data_fresh"],
    "candle_predictor.py":        ["pipeline_errors", "postgres_trades"],
    "hebbian_engine.py":          ["brain_db", "hebbian_network"],
    "hebbian_session_learner.py": ["brain_db", "hebbian_network"],
    "smoke_test.py":              ["pipeline_errors", "price_data_fresh", "signal_db", "brain_db", "postgres_trades"],
    "run_pipeline.py":            ["pipeline_errors", "pipeline_not_stuck", "no_flapping"],
    "wasp.py":                    ["pipeline_errors", "postgres_trades", "signal_db", "hotset_exists"],
    "archive-signals.py":         ["signal_db", "pipeline_errors"],
    "hotset.json":                ["hotset_exists"],
    "prices.json":                ["price_data_fresh"],
    "hype_live_trading.json":     ["live_mode"],
    "_secrets.py":               ["postgres_trades"],
}

CRITICAL_CHECKS = ["pipeline_errors", "pipeline_not_stuck", "price_data_fresh", "signal_db"]


# ---------------------------------------------------------------------------
# LLM Integration — minimax for AI-assisted healing
# ---------------------------------------------------------------------------

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
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3,
            max_tokens=max_tokens
        )
        return resp.choices[0].message.content or ""
    except Exception:
        return ""


# ---------------------------------------------------------------------------
# Built-in fix functions
# ---------------------------------------------------------------------------

def _fix_pipeline_stuck():
    lock = Path("/tmp/hermes-pipeline.lock")
    if lock.exists():
        age = time.time() - lock.stat().st_mtime
        if age > 600:
            lock.unlink()
            return True, f"Removed stale lock ({age/60:.0f}min old)"
    return False, "No stuck lock found"


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


# ---------------------------------------------------------------------------
# Individual checks
# ---------------------------------------------------------------------------

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
        return True, f"prices OK ({age:.0f}s)"
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
                tables = [r[0] for r in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()]
                if 'signals' in tables:
                    count = conn.execute("SELECT COUNT(*) FROM signals").fetchone()[0]
                    conn.close()
                    return True, f"signals OK via SQLite ({count} records)"
                conn.close()
            except Exception as e:
                pass  # fall through to PG

    # Fallback: PostgreSQL (signals table may exist in some deployments)
    try:
        sys.path.insert(0, str(SCRIPTS_DIR))
        from _secrets import BRAIN_DB_DICT
        import psycopg2
        conn = psycopg2.connect(**BRAIN_DB_DICT)
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM signals")
        count = cur.fetchone()[0]
        conn.close()
        return True, f"signals OK via PostgreSQL ({count} records)"
    except Exception as e:
        return False, f"signals unreachable (SQLite empty, PG: {e})"


def check_brain_db():
    import sqlite3
    if not BRAIN_DB.exists():
        return False, "associative_memory.db missing"
    try:
        conn = sqlite3.connect(str(BRAIN_DB), timeout=5)
        nodes = conn.execute("SELECT COUNT(*) FROM concept_nodes").fetchone()[0]
        synapses = conn.execute("SELECT COUNT(*) FROM synapse_weights").fetchone()[0]
        conn.close()
        return True, f"brain DB OK ({nodes} nodes, {synapses} synapses)"
    except Exception as e:
        return False, f"brain DB error: {e}"


def check_postgres_trades():
    try:
        sys.path.insert(0, str(SCRIPTS_DIR))
        from _secrets import BRAIN_DB_DICT
        import psycopg2
        conn = psycopg2.connect(**BRAIN_DB_DICT)
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM trades WHERE server='Hermes'")
        count = cur.fetchone()[0]
        conn.close()
        return True, f"PostgreSQL OK ({count} total trades)"
    except Exception as e:
        return False, f"PostgreSQL error: {e}"


def check_live_mode_flags():
    try:
        flags = json.loads(HYPES_LIVE.read_text())
        live = flags.get("live_trading", False)
        if live:
            return True, "LIVE TRADING ENABLED"
        return True, "paper mode"
    except Exception:
        return True, "no flags"


def check_recent_restarts():
    log = PIPELINE_LOG.read_text() if PIPELINE_LOG.exists() else ""
    lines = log.splitlines()
    recent = [l for l in lines[-60:] if "Pipeline LIVE" in l or "Pipeline PAPER" in l]
    if len(recent) > 5:
        return False, f"Pipeline flapping: {len(recent)} runs in last 60 log lines"
    return True, f"run count OK ({len(recent)} runs)"


def check_hebbian_network():
    import sqlite3
    try:
        conn = sqlite3.connect(str(BRAIN_DB), timeout=5)
        nodes = conn.execute("SELECT COUNT(*) FROM concept_nodes").fetchone()[0]
        synapses = conn.execute("SELECT COUNT(*) FROM synapse_weights").fetchone()[0]
        conn.close()
        if nodes > 50000:
            return False, f"Hebbian explosion: {nodes} nodes — possible loop"
        if synapses > 500000:
            return False, f"Hebbian explosion: {synapses} synapses — possible loop"
        return True, f"hebbian OK ({nodes} nodes, {synapses} synapses)"
    except Exception as e:
        return True, f"hebbian check skipped: {e}"


CHECKS = [
    ("pipeline_errors",    check_pipeline_log_errors),
    ("pipeline_not_stuck", check_pipeline_not_stuck),
    ("price_data_fresh",   check_price_data_fresh),
    ("hotset_exists",      check_hotset_exists),
    ("signal_db",          check_signal_db),
    ("brain_db",           check_brain_db),
    ("postgres_trades",    check_postgres_trades),
    ("live_mode",          check_live_mode_flags),
    ("no_flapping",        check_recent_restarts),
    ("hebbian_network",     check_hebbian_network),
]


# ---------------------------------------------------------------------------
# Core run functions
# ---------------------------------------------------------------------------

def run_smoke_test(verbose=True, check_filter=None):
    """Run smoke checks. Returns (all_passed, results)."""
    checks_to_run = [(n, fn) for n, fn in CHECKS if check_filter is None or n in check_filter]

    results = []
    all_ok = True
    for name, fn in checks_to_run:
        try:
            ok, msg = fn()
            results.append((name, ok, msg))
            if not ok:
                all_ok = False
        except Exception as e:
            results.append((name, False, f"EXCEPTION: {e}"))
            all_ok = False

    if verbose:
        status = "PASS" if all_ok else "FAIL"
        print(f"[SMOKE TEST] {status}")
        for name, ok, msg in results:
            icon = "✅" if ok else "❌"
            print(f"  {icon} {name}: {msg}")

    return all_ok, results


def run_smoke_test_with_heal(max_heal_attempts=2, check_filter=None, verbose=True):
    """
    Run smoke test, auto-heal failures using:
      1. Built-in fix functions (HEAL_MAP)
      2. Minimax AI for unmapped/unknown failures

    Returns (final_passed, results, heal_log).
    """
    heal_log = []
    attempt = 0
    all_ok = False

    while attempt <= max_heal_attempts:
        ok, results = run_smoke_test(verbose=(attempt == 0 and verbose), check_filter=check_filter)

        if ok:
            all_ok = True
            break

        failures = [(name, msg) for name, ok, msg in results if not ok]
        if not failures:
            break

        if attempt >= max_heal_attempts:
            if verbose:
                print(f"[SMOKE TEST] Max heal attempts ({max_heal_attempts}) reached")
            # Still failing after all heal attempts → alert T
            _alert_on_heal_failure(results, heal_log)
            break

        # Built-in fixes
        built_in = []
        for name, msg in failures:
            if name in HEAL_MAP:
                fix_fn, can_heal = HEAL_MAP[name]
                if can_heal and fix_fn is not None:
                    built_in.append((name, fix_fn))

        if verbose:
            print(f"[SMOKE TEST] Attempt {attempt+1}/{max_heal_attempts}: "
                  f"{len(built_in)} built-in heals + AI fallback")

        for name, fix_fn in built_in:
            try:
                success, fix_msg = fix_fn()
                heal_log.append({
                    "check": name, "attempt": attempt + 1, "method": "builtin",
                    "success": success, "message": fix_msg
                })
                if verbose:
                    icon = "✅" if success else "❌"
                    print(f"  {icon} heal [{name}] (builtin): {fix_msg}")
            except Exception as e:
                heal_log.append({
                    "check": name, "attempt": attempt + 1, "method": "builtin",
                    "success": False, "message": f"EXCEPTION: {e}"
                })
                if verbose:
                    print(f"  ❌ heal [{name}] (builtin): EXCEPTION {e}")

        # AI healing for remaining failures
        ai_failures = [
            (name, msg) for name, msg in failures
            if not any(n == name for n, _ in built_in)
        ]

        if ai_failures and attempt < max_heal_attempts:
            system_prompt = (
                "You are Hermes, a crypto trading system automation agent. "
                "You diagnose and fix infrastructure failures. "
                "You have shell access and systemd control on a Linux system. "
                "Be concise — describe the problem, the fix command, and any verification step."
            )
            failure_lines = "\n".join([f"- {n}: {m}" for n, m in ai_failures])
            user_prompt = (
                f"Smoke test failed on these checks:\n{failure_lines}\n\n"
                f"Hermes root: {HERMES_DIR}\nScripts: {SCRIPTS_DIR}\n"
                f"Data: {DATA_DIR}\nLogs: {LOG_DIR}\n\n"
                f"For each failure:\n"
                f"  1. Most likely root cause\n"
                f"  2. Exact command(s) to fix it\n"
                f"  3. How to verify\n\n"
                f"Only suggest safe infra commands (systemctl, python3 scripts/, rm -f /tmp/). "
                f"Do NOT suggest trade execution or strategy changes."
            )

            ai_response = _call_minimax(system_prompt, user_prompt)
            if ai_response:
                heal_log.append({
                    "check": ",".join(n for n, _ in ai_failures),
                    "attempt": attempt + 1, "method": "ai",
                    "success": True, "message": ai_response[:500]
                })
                if verbose:
                    print(f"  🧠 AI diagnostic:\n    {ai_response[:300]}")

                # Execute safe commands from AI response
                for line in ai_response.split("\n"):
                    line = line.strip().strip("`")
                    safe_starts = (
                        "sudo systemctl restart",
                        "sudo systemctl stop",
                        "sudo systemctl start",
                        "python3 /root/.hermes/scripts/",
                        "sudo rm -f /tmp/",
                    )
                    if any(line.startswith(p) for p in safe_starts):
                        r = subprocess.run(line, shell=True, capture_output=True, timeout=30)
                        heal_log.append({
                            "check": "ai_exec", "attempt": attempt + 1, "method": "ai_exec",
                            "success": r.returncode == 0, "message": f"ran: {line[:60]} → {r.returncode}"
                        })
                        if verbose:
                            icon = "✅" if r.returncode == 0 else "❌"
                            print(f"  {icon} ai_exec: {line[:70]}")

        time.sleep(5)
        attempt += 1

    return all_ok, results, heal_log


def find_changed_scripts(since_minutes=30):
    """Find scripts/data-files modified in the last N minutes."""
    now = time.time()
    cutoff = now - (since_minutes * 60)
    changed = []
    for script in SCRIPT_CHECK_MAP:
        for base in [SCRIPTS_DIR, DATA_DIR, HERMES_DIR / "data", HERMES_DIR]:
            path = base / script
            if path.exists() and path.stat().st_mtime > cutoff:
                changed.append(script)
                break
    return changed


AUTH_JSON = HERMES_DIR / "auth.json"


def _send_telegram_alert(message: str, max_len=4000):
    """Send alert via Telegram bot. Silently fails if not configured."""
    try:
        with open(AUTH_JSON) as f:
            auth = json.load(f)
        tele = (auth.get("notifications", {}) or {}).get("telegram", {})
        token = tele.get("bot_token", "")
        chat_id = tele.get("chat_id", "")
        if not token or not chat_id:
            return False
        import urllib.request
        msg = urllib.parse.quote(message[:max_len])
        urllib.request.urlopen(
            f"https://api.telegram.org/bot{token}/sendMessage?chat_id={chat_id}&text={msg}",
            timeout=10
        )
        return True
    except Exception:
        return False


def _alert_on_heal_failure(results, heal_log):
    """If smoke test still failing after heal attempts, alert T via Telegram."""
    failures = [(name, msg) for name, ok, msg in results if not ok]
    if not failures:
        return
    lines = "\n".join([f"❌ {n}: {msg}" for n, msg in failures])
    msg = (
        f"🚨 Hermes Smoke Test FAILURE (unhealed)\n"
        f"{lines}\n"
        f"Heal attempts: {len(heal_log)}\n"
        f"Run: python3 /root/.hermes/scripts/smoke_test.py --critical --heal"
    )
    _send_telegram_alert(msg)


def _log_heal_results(heal_log):
    try:
        log_path = LOG_DIR / "smoke_heal.log"
        entry = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "heal_attempts": heal_log
        }
        with open(log_path, "a") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception:
        pass


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Hermes Smoke Test")
    parser.add_argument("--target", metavar="SCRIPT",
                       help="Run targeted checks for a specific script")
    parser.add_argument("--changed-since", metavar="MINS", type=int, default=None,
                       help="Check scripts modified in the last N minutes")
    parser.add_argument("--critical", action="store_true",
                       help="Run only critical checks")
    parser.add_argument("--heal", action="store_true",
                       help="Auto-heal failures using built-in fixes + minimax AI")
    args = parser.parse_args()

    # Build check filter from --target or --changed-since
    check_filter = None
    if args.target:
        checks = set(SCRIPT_CHECK_MAP.get(args.target, []))
        if not checks:
            print(f"[SMOKE TEST] No checks mapped for '{args.target}'")
            sys.exit(1)
        check_filter = checks
    elif args.changed_since is not None:
        changed = find_changed_scripts(args.changed_since)
        if changed:
            all_checks = set()
            for script in changed:
                all_checks.update(SCRIPT_CHECK_MAP.get(script, []))
            check_filter = all_checks
        elif not args.heal:
            print("[SMOKE TEST] No recent changes detected")
            sys.exit(0)
    elif args.critical:
        check_filter = set(CRITICAL_CHECKS)

    if args.heal:
        ok, _, heal_log = run_smoke_test_with_heal(
            max_heal_attempts=2, check_filter=check_filter, verbose=True
        )
        if heal_log:
            _log_heal_results(heal_log)
        sys.exit(0 if ok else 1)
    else:
        ok, _ = run_smoke_test(verbose=True, check_filter=check_filter)
        sys.exit(0 if ok else 1)