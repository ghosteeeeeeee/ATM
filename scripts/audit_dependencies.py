#!/usr/bin/env python3
"""Weekly dependency audit — checks for known vulnerabilities and incompatibilities."""

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
OUTPUT = DATA_DIR / "dependency_audit.json"


def run_pip_audit() -> list[dict]:
    """Run pip-audit if installed, return list of findings."""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip_audit", "--format=json", "--output=-"],
            capture_output=True, text=True, timeout=120
        )
        if result.returncode == 0:
            return json.loads(result.stdout).get("dependencies", [])
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return []


def run_pip_check() -> list[str]:
    """Run pip check, return list of incompatibility messages."""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "check"],
            capture_output=True, text=True, timeout=60
        )
        lines = [l.strip() for l in result.stdout.splitlines() if l.strip() and "No broken" not in l]
        return lines
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return []


def main():
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    audit_findings = run_pip_audit()
    broken_deps = run_pip_check()

    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "vulnerabilities": audit_findings,
        "broken_dependencies": broken_deps,
        "vuln_count": len(audit_findings),
        "broken_count": len(broken_deps),
    }

    OUTPUT.write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
