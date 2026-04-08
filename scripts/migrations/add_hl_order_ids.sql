-- Migration: Add hl_sl_order_id and hl_tp_order_id columns to trades table
-- Purpose: Track Hyperliquid SL/TP order IDs for cancel/replace operations
-- Date: 2026-04-08

ALTER TABLE trades ADD COLUMN IF NOT EXISTS hl_sl_order_id BIGINT NULL;
ALTER TABLE trades ADD COLUMN IF NOT EXISTS hl_tp_order_id BIGINT NULL;

-- Add index for faster lookups during reconciliation
CREATE INDEX IF NOT EXISTS idx_trades_hl_order_ids ON trades (hl_sl_order_id, hl_tp_order_id) WHERE hl_sl_order_id IS NOT NULL OR hl_tp_order_id IS NOT NULL;
