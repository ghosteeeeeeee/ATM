#!/usr/bin/env python3
"""Fix Unicode ellipsis corruption in OpenClaw indicator_calculator.py"""
import sys

path = '/root/.openclaw/workspace/scripts/indicator_calculator.py'

with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# Replace each ellipsis occurrence with correct Python code
replacements = [
    # Line 80: sorted_tokens = sorted(prices.keys(), key=...)
    ('sorted_tokens=sorted\u2026s(), key=lambda x: prices.get(x, 0) or 0, reverse=True)',
     'sorted_tokens=sorted(prices.keys(), key=lambda x: prices.get(x, 0) or 0, reverse=True)'),
    # Line 81: top_tokens = sorted_tokens[:50]
    ('top_tokens=sorted\u2026\u2026',
     'top_tokens=sorted_tokens[:50]'),
    # Line 84: all_tokens = list(set(top_tokens + SOL_PUMP_TOKENS))
    ('all_tokens=list(s\u2026\u2026kens + SOL_PUMP_TOKENS))',
     'all_tokens=list(set(top_tokens + SOL_PUMP_TOKENS))'),
]

for old, new in replacements:
    if old in content:
        content = content.replace(old, new)
        print(f'Replaced: {old[:50]}...')
    else:
        print(f'NOT FOUND: {old[:50]}...')

# Also fix the SOL_PUMP_TOKENS line if corrupted
if "SOL_PUMP_TOKENS=['MEME" in content:
    # Find the actual token - the file has 'MEME...OK' with ellipsis
    import re
    m = re.search(r"SOL_PUMP_TOKENS=\[(.*?)\]", content)
    if m:
        print(f'SOL_PUMP_TOKENS raw: {repr(m.group(1))}')

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

# Verify
with open(path) as f:
    lines = f.readlines()
print('\nVerification (lines 70-90):')
for i in range(69, 91):
    if i < len(lines):
        print(f'{i+1}: {lines[i].rstrip()}')
