#!/usr/bin/env python3
"""Reproduce the ORIGINAL audit's exact parsing to confirm claim 1 counts:
48,287 block lines / 38 gates / 5,427 episodes / 5,286 covered / 82-83 tokens."""
import re
from datetime import datetime, timezone

LOG = '/root/.hermes/logs/pipeline.log'
BLOCK_RE = re.compile(
    r'^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}).*?'
    r'(?:🚫|🔒|🚧|🌊|🎯|⏱️|🛡️|🚨|⚠️)\s+\[([A-Za-z0-9_-]+)\]\s+'
    r'([A-Z0-9]{2,12})\s+(LONG|SHORT)\b',
)
COLON_RE = re.compile(
    r'^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}).*?'
    r'(?:🚫|🔒|🚧|🌊|🎯|⏱️|🛡️|🚨|⚠️)\s+\[([A-Za-z0-9_-]+)\]\s+'
    r'([A-Z0-9]{2,12}):\s+(LONG|SHORT)\b',
)
EXCLUDE_GATE = {'CONFLUENCE-DEBUG'}
EXCLUDE_SUBSTR = ('WOULD BLOCK', 'SKIPPED', ' shadow', 'SHADOW')
LOG_START = datetime(2026, 10, 2, 20, 0, tzinfo=timezone.utc).timestamp()
LOG_END = datetime(2026, 10, 8, 23, 2, tzinfo=timezone.utc).timestamp()

events = []
skipped = 0
with open(LOG, 'r', errors='replace') as f:
    for line in f:
        if 'BLOCKED' not in line and 'blocked' not in line:
            continue
        if any(s in line for s in EXCLUDE_SUBSTR):
            skipped += 1
            continue
        m = BLOCK_RE.match(line) or COLON_RE.match(line)
        if not m:
            continue
        ts_s, gate, token, direction = m.groups()
        if gate in EXCLUDE_GATE:
            continue
        ts = datetime.strptime(ts_s, '%Y-%m-%d %H:%M:%S').replace(tzinfo=timezone.utc).timestamp()
        if ts < LOG_START or ts > LOG_END:
            continue
        events.append((ts, gate, token, direction))

by = {}
for ts, g, tok, d in events:
    by.setdefault((g, tok, d), []).append(ts)
episodes = []
for (g, tok, d), tss in by.items():
    tss.sort()
    start = last = tss[0]
    for ts in tss[1:]:
        if ts - last > 3600:
            episodes.append((start, g, tok, d))
            start = ts
        last = ts
    episodes.append((start, g, tok, d))
tokens = sorted({e[2] for e in episodes})
print(f"raw block lines parsed: {len(events):,} (their claim 48,287)")
print(f"gates: {len(by and {g for _, g, _, _ in events})} (their claim ~38)")
print(f"episodes: {len(episodes):,} (their claim 5,427)")
print(f"distinct tokens in episodes: {len(tokens)}")
print(f"tokens: {tokens}")
