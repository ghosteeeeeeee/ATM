import re

with open('/tmp/CONTEXT.md.original') as f:
    content = f.read()

qs_pattern = r'(## Quick Status\n```\n).*?(\n```\n)'
match = re.search(qs_pattern, content, flags=re.DOTALL)
if match:
    print('MATCH FOUND')
    print('Group 1 (repr):', repr(match.group(1)))
    print('Group 2 (repr):', repr(match.group(2)))
    print('Matched span:', match.span())
else:
    print('NO MATCH')

# Now test replacement
quick_status = "PIPELINE: ERROR | WASP: unknown\nLIVE: ON | POS: 10\nREGIME: UNKNOWN\nUpdated: 2026-04-08 07:26 UTC"
qs_replacement = r'\1' + quick_status + r'\2'
new_content = re.sub(qs_pattern, qs_replacement, content, flags=re.DOTALL)
print('\n--- Replacement test (first 500 chars) ---')
print(repr(new_content[:500]))
