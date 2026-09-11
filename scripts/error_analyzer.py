#!/usr/bin/env python3
"""
Error Pattern Analyzer: scans pipeline logs for recurring errors and alerts on patterns.

Data source: journalctl (hermes-pipeline.service) + pipeline.log
Output: data/error_patterns.json + alerts to automation/error_alerts.md
Timer: every 1 hour (hermes-error-analyzer.timer)

Usage:
  python3 error_analyzer.py           # Full run: scan → detect → alert
  python3 error_analyzer.py --dry     # Dry run: show what would alert
"""

import sys, os, re, json, subprocess
from datetime import datetime, timezone, timedelta
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

DRY_RUN = '--dry' in sys.argv
PATTERNS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'error_patterns.json')
ALERT_LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'automation', 'error_alerts.md')

REPEAT_THRESHOLD = 3     # same error >3 times → alert
NEW_ERROR_THRESHOLD = 1  # new error type → alert


def log(msg):
    ts = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
    line = f"[{ts}] {msg}"
    print(line)


def scan_journalctl():
    """Scan last hour of hermes-pipeline journal for errors."""
    try:
        result = subprocess.run(
            ['journalctl', '--since', '1 hour ago', '-u', 'hermes-pipeline.service',
             '--no-pager', '-q'],
            capture_output=True, text=True, timeout=30
        )
        lines = result.stdout.strip().split('\n') if result.stdout.strip() else []
    except Exception:
        lines = []

    errors = []
    for line in lines:
        if re.search(r'error|fail|traceback|exception|timed out|crash', line, re.IGNORECASE):
            # Normalize: strip PID, timestamps, hostname for pattern matching
            normalized = re.sub(r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}', 'TS', line)
            normalized = re.sub(r'python3\[\d+\]', 'python3[PID]', normalized)
            normalized = re.sub(r'Tokyo\s+', '', normalized)
            errors.append(normalized.strip())
    return errors


def scan_pipeline_log():
    """Scan last hour of pipeline.log for errors."""
    log_path = '/root/.hermes/logs/pipeline.log'
    if not os.path.exists(log_path):
        return []

    errors = []
    try:
        # Read only the last 50KB of the file (≈ last 1-2 hours)
        with open(log_path, 'rb') as f:
            f.seek(0, 2)
            size = f.tell()
            f.seek(max(0, size - 50_000))
            lines = f.read().decode('utf-8', errors='replace').splitlines()

        for line in lines:
            if re.search(r'\bERROR\b|\bFAIL\b|\bWARN\b.*(?:error|fail|timeout)', line, re.IGNORECASE):
                # Only include lines with recent timestamps (today)
                if '2026-08-02' in line or '2026-08-03' in line:
                    normalized = re.sub(r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}', 'TS', line)
                    errors.append(normalized.strip())
    except Exception:
        pass
    return errors


def classify_errors(errors):
    """Group errors by pattern and count occurrences."""
    patterns = Counter()
    for err in errors:
        # Collapse severity words first (before generic uppercase collapse)
        key = re.sub(r'\b(ERROR|FAIL|WARN|CRASH|EXCEPTION|TRACEBACK)\b', 'SEV', err, flags=re.IGNORECASE)
        # Collapse numbers/tokens/IDs to wildcards for grouping
        key = re.sub(r'0x[0-9a-fA-F]+', 'HEX', key)
        key = re.sub(r'\b\d+\b', 'N', key)
        key = re.sub(r'\b[A-Z]{3,6}\b', 'TOK', key)  # collapse token names
        patterns[key] += 1
    return patterns


def load_known_patterns():
    """Load previously seen error patterns."""
    if os.path.exists(PATTERNS_FILE):
        try:
            with open(PATTERNS_FILE) as f:
                return json.load(f)
        except Exception:
            pass
    return {'known': {}, 'last_run': None}


def save_known_patterns(data):
    os.makedirs(os.path.dirname(PATTERNS_FILE), exist_ok=True)
    with open(PATTERNS_FILE, 'w') as f:
        json.dump(data, f, indent=2)


def detect_alerts(current_patterns, known):
    """Compare current patterns against known, return alerts."""
    alerts = []
    known_errors = known.get('known', {})

    for pattern, count in current_patterns.items():
        if count >= REPEAT_THRESHOLD:
            prev_count = known_errors.get(pattern, {}).get('count', 0)
            if prev_count < REPEAT_THRESHOLD:
                alerts.append({
                    'type': 'repeated',
                    'pattern': pattern,
                    'count': count,
                    'msg': f'Repeated error ({count}x): {pattern[:120]}',
                })
        elif count >= NEW_ERROR_THRESHOLD and pattern not in known_errors:
            alerts.append({
                'type': 'new',
                'pattern': pattern,
                'count': count,
                'msg': f'New error pattern: {pattern[:120]}',
            })
    return alerts


def write_alerts(alerts):
    """Append alerts to error_alerts.md."""
    if not alerts:
        return
    os.makedirs(os.path.dirname(ALERT_LOG), exist_ok=True)
    ts = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
    with open(ALERT_LOG, 'a') as f:
        f.write(f"\n## Error Alerts — {ts}\n")
        for a in alerts:
            f.write(f"- **{a['type'].upper()}** ({a['count']}x): `{a['pattern'][:200]}`\n")


def main():
    log(f"{'[DRY RUN] ' if DRY_RUN else ''}=== Error Pattern Analyzer ===")

    # Scan both sources
    journal_errors = scan_journalctl()
    log_errors = scan_pipeline_log()
    all_errors = journal_errors + log_errors
    log(f"Scanned: {len(journal_errors)} journal + {len(log_errors)} log = {len(all_errors)} errors")

    if not all_errors:
        log("No errors in last hour — clean")
        known = load_known_patterns()
        known['last_run'] = datetime.now(timezone.utc).isoformat()
        save_known_patterns(known)
        return

    # Classify
    patterns = classify_errors(all_errors)
    log(f"Classified into {len(patterns)} patterns")
    for pat, count in patterns.most_common(5):
        log(f"  {count}x: {pat[:100]}")

    # Detect
    known = load_known_patterns()
    alerts = detect_alerts(patterns, known)
    log(f"{len(alerts)} alerts")

    if alerts and not DRY_RUN:
        write_alerts(alerts)
        for a in alerts:
            log(f"  ALERT: {a['msg']}")

    # Update known patterns
    for pat, count in patterns.items():
        known['known'][pat] = {
            'count': count,
            'last_seen': datetime.now(timezone.utc).isoformat(),
        }
    known['last_run'] = datetime.now(timezone.utc).isoformat()
    # Prune patterns not seen in 7 days
    cutoff = datetime.now(timezone.utc) - timedelta(days=7)
    known['known'] = {
        p: v for p, v in known['known'].items()
        if datetime.fromisoformat(v['last_seen']) > cutoff
    }
    save_known_patterns(known)

    log("Done")


if __name__ == '__main__':
    main()
