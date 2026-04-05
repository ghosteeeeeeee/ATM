-- migrate_add_workflow_state.sql
-- Adds workflow_state column to trades table in PostgreSQL brain DB.
-- Safe migration: ADD COLUMN with DEFAULT — no data loss, no table lock.

BEGIN;

-- Add workflow_state column if it doesn't exist
ALTER TABLE trades ADD COLUMN IF NOT EXISTS workflow_state VARCHAR(32) DEFAULT 'IDLE';

-- Add workflow_updated_at column if it doesn't exist
ALTER TABLE trades ADD COLUMN IF NOT EXISTS workflow_updated_at TIMESTAMP DEFAULT NOW();

-- Set default workflow_state for existing open positions
UPDATE trades
SET workflow_state = 'POSITION_OPEN'
WHERE status = 'open' AND (workflow_state IS NULL OR workflow_state = 'IDLE');

-- Set workflow_updated_at for existing rows that have a state
UPDATE trades
SET workflow_updated_at = NOW()
WHERE workflow_updated_at IS NULL;

COMMIT;

-- Verify:
-- SELECT id, status, workflow_state, workflow_updated_at FROM trades LIMIT 10;
