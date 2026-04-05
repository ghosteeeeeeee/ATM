#!/usr/bin/env python3
"""Run the workflow_state column migration on the PostgreSQL brain DB."""
import sys
sys.path.insert(0, '/root/.hermes/scripts')

import psycopg2
from _secrets import BRAIN_DB_DICT

def main():
    conn = psycopg2.connect(**BRAIN_DB_DICT)
    cur = conn.cursor()

    # Check if columns exist
    cur.execute("""
        SELECT column_name FROM information_schema.columns
        WHERE table_name='trades' AND column_name IN ('workflow_state','workflow_updated_at')
    """)
    existing = [r[0] for r in cur.fetchall()]
    print('Existing workflow columns:', existing)

    if 'workflow_state' not in existing:
        cur.execute("ALTER TABLE trades ADD COLUMN workflow_state VARCHAR(32) DEFAULT 'IDLE'")
        print('Added workflow_state column')
    else:
        print('workflow_state already exists, skipping')

    if 'workflow_updated_at' not in existing:
        cur.execute('ALTER TABLE trades ADD COLUMN workflow_updated_at TIMESTAMP DEFAULT NOW()')
        print('Added workflow_updated_at column')
    else:
        print('workflow_updated_at already exists, skipping')

    conn.commit()

    # Verify
    cur.execute("""
        SELECT column_name, data_type, column_default
        FROM information_schema.columns
        WHERE table_name='trades' AND column_name IN ('workflow_state','workflow_updated_at')
    """)
    rows = cur.fetchall()
    print('\nVerification:')
    for r in rows:
        print(f'  {r[0]}: {r[1]} default={r[2]}')

    cur.close()
    conn.close()
    print('\nMigration complete.')

if __name__ == '__main__':
    main()
