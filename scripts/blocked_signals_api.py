#!/usr/bin/env python3
"""Parse pipeline.log for recent blocked signals and write blocked_signals.json."""
import re
import json
import time
from datetime import datetime, timezone
from pathlib import Path

LOG_FILE = '/root/.hermes/logs/pipeline.log'
OUT_FILE = '/var/www/hermes/data/blocked_signals.json'

def parse_blocked_signals(limit_minutes=60):
    """Parse pipeline.log for BLOCKED entries in the last N minutes."""
    cutoff = time.time() - (limit_minutes * 60)
    blocked = []

    try:
        with open(LOG_FILE, 'r') as f:
            lines = f.readlines()

        # Pattern: [GATE-NAME] TOKEN DIRECTION BLOCKED — reason
        # or: [GATE-NAME] TOKEN DIRECTION: reason
        block_patterns = [
            r'\[([A-Z0-9-]+)\]\s+(\w+)\s+(LONG|SHORT)\s+BLOCKED\s*[—–-]\s*(.+)',
            r'\[([A-Z0-9-]+)\]\s+(\w+)\s+(LONG|SHORT):\s+(.+)',
            r'\[([A-Z0-9-]+)\]\s+(\w+)\s+(LONG|SHORT)\s+would block\s*[—–-]\s*(.+)',
        ]

        for line in reversed(lines):  # Most recent first
            if 'BLOCKED' not in line and 'would block' not in line.lower():
                continue

            # Parse timestamp
            ts_match = re.match(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', line)
            if not ts_match:
                continue

            ts_str = ts_match.group(1)
            ts = datetime.strptime(ts_str, '%Y-%m-%d %H:%M:%S')
            ts_epoch = ts.replace(tzinfo=timezone.utc).timestamp()

            if ts_epoch < cutoff:
                break  # Lines are in reverse chronological order

            # Extract gate name from bracket
            gate_match = re.search(r'\[([A-Z0-9_-]+)\]', line)
            gate_name = gate_match.group(1) if gate_match else 'UNKNOWN'

            # Try to extract token and direction
            token = ''
            direction = ''
            reason = line.strip()

            for pattern in block_patterns:
                m = re.search(pattern, line)
                if m:
                    gate_name = m.group(1)
                    token = m.group(2)
                    direction = m.group(3)
                    reason = m.group(4).strip()
                    break

            blocked.append({
                'gate': gate_name,
                'token': token,
                'direction': direction,
                'reason': reason,
                'time': ts_str,
            })

            if len(blocked) >= 100:  # Limit
                break

    except FileNotFoundError:
        pass

    return blocked

def main():
    blocked = parse_blocked_signals(limit_minutes=120)

    # Group by gate for summary
    gate_summary = {}
    for b in blocked:
        gate = b['gate']
        if gate not in gate_summary:
            gate_summary[gate] = {'count': 0, 'tokens': set()}
        gate_summary[gate]['count'] += 1
        if b['token']:
            gate_summary[gate]['tokens'].add(b['token'])

    # Convert sets to lists for JSON
    summary = {}
    for gate, data in gate_summary.items():
        summary[gate] = {
            'count': data['count'],
            'tokens': sorted(list(data['tokens']))[:10],  # Max 10 tokens
        }

    result = {
        'updated': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
        'blocked_count': len(blocked),
        'gate_summary': summary,
        'recent_blocks': blocked[:50],  # Last 50 blocks
    }

    with open(OUT_FILE, 'w') as f:
        json.dump(result, f, indent=2)

    print(f"Blocked signals: {len(blocked)} | Gates: {len(summary)}")

if __name__ == '__main__':
    main()
