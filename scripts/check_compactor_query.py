import sqlite3
conn = sqlite3.connect('/root/.hermes/data/signals_hermes_runtime.db')
c = conn.cursor()
# Check what the compactor query sees with 240-min window
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
    LIMIT 10
""")
rows = c.fetchall()
print(f'Compactor query (240min, conf>=60): {len(rows)} pairs')
for r in rows:
    print(f'  {r[0]} {r[1]} conf={r[3]} src={str(r[4])[:60]} src_count={r[6]}')

# Also check with 180 min
c.execute("""
    SELECT COUNT(*)
    FROM signals
    WHERE decision = 'PENDING'
      AND executed = 0
      AND created_at > datetime('now', '-240 minutes')
      AND confidence >= 60
      AND token NOT LIKE '@%'
""")
print(f'\nTotal PENDING signals in window: {c.fetchone()[0]}')

# Check decision distribution
c.execute("""
    SELECT decision, COUNT(*)
    FROM signals
    WHERE created_at > datetime('now', '-240 minutes')
    GROUP BY decision
""")
print('\nDecision distribution (last 240min):')
for row in c.fetchall():
    print(f'  {row[0]}: {row[1]}')
