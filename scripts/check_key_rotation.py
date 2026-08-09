#!/usr/bin/env python3
"""Weekly API key rotation check — alerts if secrets file exceeds 90 days."""

import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

HERMES_ROOT = Path(__file__).resolve().parent.parent
SECRETS_FILE = HERMES_ROOT / ".secrets.local"
ENV_FILE = HERMES_ROOT / ".env"
OUTPUT = HERMES_ROOT / "data" / "key_rotation_status.json"
ROTATION_THRESHOLD_DAYS = 90


def check_file(path: Path) -> dict:
    if not path.exists():
        return {
            "exists": False,
            "age_days": None,
            "status": "MISSING",
            "last_modified": None,
        }
    mtime = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
    age = (datetime.now(timezone.utc) - mtime).days
    return {
        "exists": True,
        "age_days": age,
        "last_modified": mtime.isoformat(),
        "status": "AGING" if age > ROTATION_THRESHOLD_DAYS else "OK",
    }


def main():
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    secrets_status = check_file(SECRETS_FILE)
    env_status = check_file(ENV_FILE)

    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "threshold_days": ROTATION_THRESHOLD_DAYS,
        "secrets_local": secrets_status,
        "env": env_status,
        "alert": any(
            s["status"] == "AGING" or s["status"] == "MISSING"
            for s in (secrets_status, env_status)
        ),
    }

    OUTPUT.write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))

    if report["alert"]:
        print(
            f"\n⚠️  Key rotation needed: secrets older than {ROTATION_THRESHOLD_DAYS} days",
            flush=True,
        )


if __name__ == "__main__":
    main()
