#!/usr/bin/env python3
"""Signal parameter version tracking."""

import json
import os
import sys
from datetime import datetime, timezone

VERSIONS_FILE = '/root/.hermes/data/signal_versions.json'


def _load():
    if os.path.exists(VERSIONS_FILE):
        with open(VERSIONS_FILE) as f:
            return json.load(f)
    return {}


def _save(data):
    os.makedirs(os.path.dirname(VERSIONS_FILE), exist_ok=True)
    with open(VERSIONS_FILE, 'w') as f:
        json.dump(data, f, indent=2)


def log_version(signal, params, metrics=None, changed_by='unknown', reason=''):
    data = _load()
    if signal not in data:
        data[signal] = {'versions': [], 'current_version': 0}

    entry = data[signal]
    ver = entry['current_version'] + 1
    entry['versions'].append({
        'version': ver,
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'params': params,
        'metrics': metrics or {},
        'changed_by': changed_by,
        'reason': reason,
        'prev_version': entry['current_version'] if entry['current_version'] > 0 else None,
    })
    entry['current_version'] = ver
    _save(data)
    return ver


def get_current_version(signal):
    data = _load()
    entry = data.get(signal)
    if not entry or not entry['versions']:
        return None
    return entry['versions'][-1]


def get_version_history(signal):
    data = _load()
    return data.get(signal, {}).get('versions', [])


def rollback(signal, target_version):
    data = _load()
    entry = data.get(signal)
    if not entry:
        return None
    for v in entry['versions']:
        if v['version'] == target_version:
            return v
    return None


def list_signals():
    data = _load()
    return {sig: v['current_version'] for sig, v in data.items()}


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: signal_version.py <command> [args]")
        print("Commands: log <signal> <params_json> [--by X] [--reason Y]")
        print("          current <signal>")
        print("          history <signal>")
        print("          list")
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == 'log' and len(sys.argv) >= 4:
        sig = sys.argv[2]
        params = json.loads(sys.argv[3])
        by = 'unknown'
        reason = ''
        for i, arg in enumerate(sys.argv[4:], 4):
            if arg == '--by' and i + 1 < len(sys.argv):
                by = sys.argv[i + 1]
            elif arg == '--reason' and i + 1 < len(sys.argv):
                reason = sys.argv[i + 1]
        ver = log_version(sig, params, changed_by=by, reason=reason)
        print(f"Logged {sig} v{ver}")
    elif cmd == 'current' and len(sys.argv) >= 3:
        v = get_current_version(sys.argv[2])
        print(json.dumps(v, indent=2) if v else "No version found")
    elif cmd == 'history' and len(sys.argv) >= 3:
        for v in get_version_history(sys.argv[2]):
            print(f"v{v['version']}: {v['timestamp']} by {v['changed_by']} — {v.get('reason', '')}")
    elif cmd == 'list':
        for sig, ver in list_signals().items():
            print(f"{sig}: v{ver}")
    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)
