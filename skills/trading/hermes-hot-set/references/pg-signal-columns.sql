-- Add signal indicator columns to brain.trades for atomic trade+signal capture
-- Run once against PostgreSQL brain DB
-- Connection: psql -h /var/run/postgresql -d brain -U postgres

ALTER TABLE trades ADD COLUMN IF NOT EXISTS signal_z_score REAL;
ALTER TABLE trades ADD COLUMN IF NOT EXISTS signal_rsi_14 REAL;
ALTER TABLE trades ADD COLUMN IF NOT EXISTS signal_macd_hist REAL;
ALTER TABLE trades ADD COLUMN IF NOT EXISTS signal_macd_value REAL;
ALTER TABLE trades ADD COLUMN IF NOT EXISTS signal_macd_signal REAL;
ALTER TABLE trades ADD COLUMN IF NOT EXISTS signal_momentum_state TEXT;
ALTER TABLE trades ADD COLUMN IF NOT EXISTS signal_z_score_tier TEXT;
ALTER TABLE trades ADD COLUMN IF NOT EXISTS signal_decision TEXT;
ALTER TABLE trades ADD COLUMN IF NOT EXISTS signal_leverage INTEGER;
ALTER TABLE trades ADD COLUMN IF NOT EXISTS signal_created_at TIMESTAMPTZ;
ALTER TABLE trades ADD COLUMN IF NOT EXISTS test_sl_variant TEXT;
ALTER TABLE trades ADD COLUMN IF NOT EXISTS test_timing_variant TEXT;
ALTER TABLE trades ADD COLUMN IF NOT EXISTS test_trailing_variant TEXT;

-- Verify
SELECT column_name, data_type FROM information_schema.columns
  WHERE table_name = 'trades'
    AND column_name LIKE 'signal_%'
    OR column_name LIKE 'test_%'
  ORDER BY column_name;