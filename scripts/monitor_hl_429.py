#!/usr/bin/env python3
"""
monitor_hl_429.py — Check for HL API 429 errors and report findings.
Runs every 30 minutes for 3 hours after rate limit fix deployment.
Logs results to /root/.hermes/logs/hl_429_monitor.log
"""
import subprocess
import time
import json
import os

LOG_FILE = "/root/.hermes/logs/hl_429_monitor.log"
STATUS_FILE = "/root/.hermes/data/hl_429_monitor_status.json"
FIX_DEPLOYED_AT = 1787499800  # Approx 15:44 UTC Aug 23 2026
MONITOR_UNTIL = FIX_DEPLOYED_AT + (3 * 3600)  # 3 hours after deploy

def run(cmd):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
    return r.stdout.strip()

def check():
    now = int(time.time())
    ts = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime(now))

    if now > MONITOR_UNTIL:
        print(f"[{ts}] Monitor window expired (3h after fix). Stopping.")
        return "expired"

    # Count 429s since last check (30 min window)
    recent_429s = run(
        "journalctl --since '30 minutes ago' --no-pager 2>/dev/null "
        "| grep -i '429' | grep -v 'UFW\\|kernel\\|audit\\|openclaw\\|gateway' | wc -l"
    )

    # Get details of any 429s
    details = run(
        "journalctl --since '30 minutes ago' --no-pager 2>/dev/null "
        "| grep 'hyperliquid.*429\\|ClientError.*429' | head -5"
    )

    # Check rate limiter is active
    rate_state = run("cat /var/www/hermes/data/hype_info_rate.json 2>/dev/null")
    rate_ok = False
    if rate_state:
        try:
            data = json.loads(rate_state)
            age = now - data.get("last_call", 0)
            rate_ok = age < 120  # should be < 2 min old
        except Exception:
            pass

    # Check price collector health
    pc_errors = run(
        "journalctl -u hermes-price-collector.service --since '30 minutes ago' --no-pager 2>/dev/null "
        "| grep -i 'error\\|429\\|rate.limit' | wc -l"
    )

    count = int(recent_429s) if recent_429s.strip().isdigit() else 0
    pc_err = int(pc_errors) if pc_errors.strip().isdigit() else 0

    status = "OK" if count == 0 else f"ALERT: {count} 429s"
    rate_status = "ACTIVE" if rate_ok else "STALE"

    report = (
        f"[{ts}] {status} | Rate limiter: {rate_status} | "
        f"PC errors: {pc_err} | 429 count: {count}"
    )
    print(report)

    if details:
        print(f"  Details: {details[:500]}")

    # Write status file for dashboard
    with open(STATUS_FILE, 'w') as f:
        json.dump({
            "timestamp": now,
            "ts": ts,
            "count_429": count,
            "rate_limiter": rate_status,
            "pc_errors": pc_err,
            "status": "ok" if count == 0 else "alert",
        }, f)

    # Append to log
    with open(LOG_FILE, 'a') as f:
        f.write(report + "\n")

    return "ok" if count == 0 else "alert"

if __name__ == "__main__":
    result = check()
    if result == "expired":
        exit(0)
    exit(0 if result == "ok" else 1)
