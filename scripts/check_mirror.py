#!/usr/bin/env python3
import sys
sys.path.insert(0, '/root/.hermes/scripts')

with open('/root/.hermes/logs/pipeline.log') as f:
    lines = f.readlines()

# Look for brain.py output (trade # in stdout) and mirror lines
check_tokens = ['TRX', 'REQ', 'NTRN', 'CATI', 'ILV', 'YGG', 'CYBER', 'LISTA', 'VINE']
print("=== Lines with 'trade #' (brain.py stdout) ===")
for i, line in enumerate(lines):
    if 'trade #' in line.lower() and 'ENTERED' not in line:
        print(f"  L{i}: {line.strip()}")

print("\n=== Lines with 'HYPE' or 'mirror' or 'mirror_open' (after trades) ===")
# Find all lines near ENTERED for these tokens
for tok in check_tokens:
    for i, line in enumerate(lines):
        if f'ENTERED: {tok}' in line:
            ts = line[:20]
            # Check next 20 lines for HYPE/mirror
            for j in range(i+1, min(i+20, len(lines))):
                l2 = lines[j].strip()
                if any(k in l2.lower() for k in ['hype', 'mirror', 'failed', 'success', 'live trading']):
                    print(f"  [{tok}] L{j}: {l2}")

print("\n=== Full brain.py mirror open calls (search whole log) ===")
for line in lines:
    if 'mirror_open' in line or ('trade #' in line.lower() and '✓' in line):
        print(f"  {line.strip()}")
