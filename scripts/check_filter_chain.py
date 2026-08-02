import sqlite3
conn = sqlite3.connect('/root/.hermes/data/signals_hermes_runtime.db')
c = conn.cursor()

# Get all tokens from compactor query
c.execute("""
    SELECT token, direction, MAX(signal_type) AS signal_type,
           MAX(confidence) AS confidence,
           GROUP_CONCAT(DISTINCT source) AS merged_source,
           COUNT(DISTINCT source) as src_count,
           MAX(created_at) AS created_at
    FROM signals
    WHERE decision = 'PENDING'
      AND executed = 0
      AND created_at > datetime('now', '-240 minutes')
      AND confidence >= 60
      AND token NOT LIKE '@%'
    GROUP BY token, direction
    HAVING COUNT(DISTINCT source) >= 1
    ORDER BY confidence DESC
    LIMIT 150
""")
rows = c.fetchall()
print(f'Compactor query: {len(rows)} total pairs\n')

# Check what filters would block each
from signal_gen import SHORT_BLACKLIST, LONG_BLACKLIST
import sys
sys.path.insert(0, '/root/.hermes/scripts')
from tokens import is_solana_only
from hyperliquid_exchange import is_delisted

print('Checking each token against filters:')
for r in rows:
    token, direction = r[0], r[1]
    src = r[4]
    
    blocked = None
    
    # Check blacklist
    if direction == 'SHORT' and token in SHORT_BLACKLIST:
        blocked = f'SHORT_BLACKLIST'
    elif direction == 'LONG' and token in LONG_BLACKLIST:
        blocked = f'LONG_BLACKLIST'
    elif is_solana_only(token):
        blocked = 'Solana-only'
    elif is_delisted(token):
        blocked = 'delisted'
    
    print(f'  {token} {direction}: conf={r[3]} src={str(src)[:40]} → {blocked or "OK"}')
