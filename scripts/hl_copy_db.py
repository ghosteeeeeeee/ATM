#!/usr/bin/env python3
"""
HL Copy Trading Database Schema
Creates and manages the SQLite database for tracking traders and copies.
"""
import sqlite3
import os
from paths import HL_COPY_DB

def get_db():
    """Get database connection with WAL mode."""
    conn = sqlite3.connect(HL_COPY_DB, timeout=10)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Create all tables if they don't exist."""
    conn = get_db()
    try:
        c = conn.cursor()
        
        # Tracked traders
        c.execute("""
            CREATE TABLE IF NOT EXISTS traders (
                wallet TEXT PRIMARY KEY,
                alias TEXT,
                pnl_all_time REAL DEFAULT 0,
                pnl_30d REAL DEFAULT 0,
                win_rate REAL DEFAULT 0,
                trade_count INTEGER DEFAULT 0,
                volume_30d REAL DEFAULT 0,
                avg_hold_hours REAL DEFAULT 0,
                max_drawdown REAL DEFAULT 0,
                score REAL DEFAULT 0,
                pattern TEXT,
                last_updated INTEGER,
                active INTEGER DEFAULT 1
            )
        """)
        
        # All fills from tracked traders
        c.execute("""
            CREATE TABLE IF NOT EXISTS trader_fills (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                wallet TEXT NOT NULL,
                coin TEXT NOT NULL,
                side TEXT NOT NULL,
                px REAL NOT NULL,
                sz REAL NOT NULL,
                time INTEGER NOT NULL,
                closed_pnl REAL DEFAULT 0,
                is_open INTEGER NOT NULL,
                copied INTEGER DEFAULT 0,
                copy_time INTEGER,
                FOREIGN KEY (wallet) REFERENCES traders(wallet),
                UNIQUE(wallet, coin, time, side)
            )
        """)
        
        # Current positions of tracked traders
        c.execute("""
            CREATE TABLE IF NOT EXISTS trader_positions (
                wallet TEXT NOT NULL,
                coin TEXT NOT NULL,
                sz REAL NOT NULL,
                entry_px REAL NOT NULL,
                unrealized_pnl REAL DEFAULT 0,
                leverage REAL DEFAULT 1,
                liquidation_px REAL,
                last_updated INTEGER,
                PRIMARY KEY (wallet, coin),
                FOREIGN KEY (wallet) REFERENCES traders(wallet)
            )
        """)
        
        # Our copy trades (paper or live)
        c.execute("""
            CREATE TABLE IF NOT EXISTS copy_trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                trader_wallet TEXT NOT NULL,
                coin TEXT NOT NULL,
                side TEXT NOT NULL,
                px REAL NOT NULL,
                sz REAL NOT NULL,
                time INTEGER NOT NULL,
                pnl REAL DEFAULT 0,
                status TEXT DEFAULT 'open',
                mode TEXT DEFAULT 'paper',
                FOREIGN KEY (trader_wallet) REFERENCES traders(wallet)
            )
        """)
        
        # Performance tracking
        c.execute("""
            CREATE TABLE IF NOT EXISTS copy_performance (
                timestamp INTEGER PRIMARY KEY,
                trader_pnl REAL DEFAULT 0,
                our_pnl REAL DEFAULT 0,
                divergence_pct REAL DEFAULT 0,
                trades_copied INTEGER DEFAULT 0,
                trades_failed INTEGER DEFAULT 0
            )
        """)
        
        # Copy trade performance tracking
        c.execute("""
            CREATE TABLE IF NOT EXISTS trader_performance (
                wallet TEXT NOT NULL,
                trade_id INTEGER,
                token TEXT NOT NULL,
                direction TEXT NOT NULL,
                signal_time INTEGER,
                entry_price REAL,
                exit_price REAL,
                pnl_usdt REAL DEFAULT 0,
                pnl_pct REAL DEFAULT 0,
                status TEXT DEFAULT 'open',
                close_reason TEXT,
                created_at INTEGER,
                closed_at INTEGER,
                PRIMARY KEY (wallet, trade_id)
            )
        """)

        # Indexes for faster queries
        c.execute("CREATE INDEX IF NOT EXISTS idx_fills_wallet ON trader_fills(wallet)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_fills_time ON trader_fills(time)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_positions_wallet ON trader_positions(wallet)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_trades_time ON copy_trades(time)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_perf_wallet_coin_status ON trader_performance(wallet, token, status)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_perf_trade_id ON trader_performance(trade_id)")

        # Add copy performance columns to traders table (idempotent)
        for col, default in [
            ('copy_weight', '1.0'),
            ('copy_trades', '0'),
            ('copy_wins', '0'),
            ('copy_pnl', '0.0'),
        ]:
            try:
                c.execute(f"ALTER TABLE traders ADD COLUMN {col} REAL DEFAULT {default}")
            except sqlite3.OperationalError:
                pass  # column already exists

        conn.commit()
    finally:
        conn.close()
    print(f"[hl_copy_db] Initialized database at {HL_COPY_DB}")

if __name__ == "__main__":
    init_db()
