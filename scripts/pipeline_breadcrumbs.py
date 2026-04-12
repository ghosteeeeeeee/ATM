#!/usr/bin/env python3
"""
pipeline_breadcrumbs.py — ERR breadcrumb logger for Hermes pipeline steps.

Each step writes its entry/exit to brain/pipeline_steps.json.
If a step crashes, its FAIL entry stays as a witness.
On next startup, clear_stale_breadcrumbs() wipes any stale FAILs so they don't
pollute the next cycle's view.

Usage:
    from pipeline_breadcrumbs import log_start, log_success, log_fail, clear_stale

    log_start("signal_gen")
    try:
        ...  # step work
        log_success("signal_gen")
    except Exception as e:
        log_fail("signal_gen", str(e))
        raise
"""

import json, os, time
from filelock import FileLock

_BREADCRUMB_FILE = '/root/.hermes/brain/pipeline_steps.json'
_GLOBAL_LOCK = 'pipeline_breadcrumbs'


def _read() -> dict:
    if os.path.exists(_BREADCRUMB_FILE):
        try:
            with open(_BREADCRUMB_FILE) as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def _write(data: dict):
    os.makedirs(os.path.dirname(_BREADCRUMB_FILE), exist_ok=True)
    with FileLock(_GLOBAL_LOCK, timeout=5):
        with open(_BREADCRUMB_FILE, 'w') as f:
            json.dump(data, f, indent=2)


def log_start(step: str):
    """Record that a step has started."""
    try:
        data = _read()
        data[step] = {"event": "START", "ts": time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}
        _write(data)
    except Exception:
        pass  # never crash on breadcrumb failures


def log_success(step: str):
    """Record that a step completed successfully."""
    try:
        data = _read()
        data[step] = {"event": "SUCCESS", "ts": time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}
        _write(data)
    except Exception:
        pass


def log_fail(step: str, error: str = ""):
    """Record that a step failed with an error message."""
    try:
        data = _read()
        data[step] = {
            "event": "FAIL",
            "ts": time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
            "error": str(error)[:500]
        }
        _write(data)
    except Exception:
        pass


def clear_stale():
    """
    Call at pipeline startup to clear any FAIL entries left over from a
    previous crashed cycle. START/SUCCESS entries are also cleared since they
    belong to a previous cycle.
    """
    try:
        data = _read()
        if data:
            stale = {k: v for k, v in data.items() if v.get('event') in ('START', 'SUCCESS', 'FAIL')}
            if stale:
                for k in stale:
                    del data[k]
                _write(data)
    except Exception:
        pass


def get_breadcrumbs() -> dict:
    """Return the current breadcrumb state for inspection."""
    return _read()


if __name__ == '__main__':
    import sys
    if len(sys.argv) < 2:
        print("Usage: pipeline_breadcrumbs.py [start|success|fail|clear|show] [step] [error]")
        print()
        print("  pipeline_breadcrumbs.py start  signal_gen")
        print("  pipeline_breadcrumbs.py success ai_decider")
        print("  pipeline_breadcrumbs.py fail   signal_gen 'some error'")
        print("  pipeline_breadcrumbs.py clear")
        print("  pipeline_breadcrumbs.py show")
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == 'start' and len(sys.argv) >= 3:
        log_start(sys.argv[2])
        print(f"START: {sys.argv[2]}")
    elif cmd == 'success' and len(sys.argv) >= 3:
        log_success(sys.argv[2])
        print(f"SUCCESS: {sys.argv[2]}")
    elif cmd == 'fail' and len(sys.argv) >= 3:
        err = sys.argv[3] if len(sys.argv) >= 4 else ""
        log_fail(sys.argv[2], err)
        print(f"FAIL: {sys.argv[2]} — {err}")
    elif cmd == 'clear':
        clear_stale()
        print("Cleared stale breadcrumbs")
    elif cmd == 'show':
        print(json.dumps(get_breadcrumbs(), indent=2))
