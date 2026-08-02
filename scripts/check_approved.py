import sqlite3
conn = sqlite3.connect('/root/.hermes/data/signals_hermes_runtime.db')
conn.row_factory = sqlite3.Row
c = conn.cursor()
c.execute('''
    SELECT token, direction, compact_rounds, hot_cycle_count, executed,
           GROUP_CONCAT(DISTINCT source) as sources,
           MAX(COALESCE(effective_confidence, confidence)) as conf
    FROM signals
    WHERE decision="APPROVED" AND executed=0
    GROUP BY token, direction
    ORDER BY conf DESC
''')
print('APPROVED signals:')
for r in c.fetchall():
    print(f'  {r["token"]:10} {r["direction"]:5} cr={r["compact_rounds"]} hcc={r["hot_cycle_count"]} conf={r["conf"]} src={str(r["sources"])[:35]}')
