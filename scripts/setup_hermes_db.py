#!/usr/bin/env python3
"""
Create Hermes dual-database architecture:
  signals_hermes.db       — static backfill, git-tracked
  signals_hermes_runtime.db — runtime data, local only

Also migrates backfill data from legacy DB.
"""
import sqlite3, os

HERMES_DATA = '/root/.hermes/data'
STATIC = f'{HERMES_DATA}/signals_hermes.db'
RUNTIME = f'{HERMES_DATA}/signals_hermes_runtime.db'
LEGACY = '/root/.openclaw/workspace/data/signals.db'
os.makedirs(HERMES_DATA, exist_ok=True)

# ── Static DB: backfill tables only ─────────────────────────────────────────
conn = sqlite3.connect(STATIC)
c = conn.cursor()

c.execute("""
CREATE TABLE IF NOT EXISTS price_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    token TEXT NOT NULL,
    price REAL NOT NULL,
    timestamp INTEGER NOT NULL,
    UNIQUE(token, timestamp)
)""")
c.execute('CREATE INDEX IF NOT EXISTS idx_ph_token ON price_history(token)')
c.execute('CREATE INDEX IF NOT EXISTS idx_ph_ts ON price_history(timestamp)')

c.execute("""
CREATE TABLE IF NOT EXISTS latest_prices (
    token TEXT PRIMARY KEY,
    price REAL NOT NULL,
    updated_at INTEGER NOT NULL
)""")

c.execute("""
CREATE TABLE IF NOT EXISTS regime_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    regime TEXT NOT NULL,
    broad_z REAL NOT NULL,
    long_mult REAL NOT NULL,
    short_mult REAL NOT NULL,
    timestamp INTEGER NOT NULL
)""")

conn.commit()
print(f'Created static DB: {STATIC}')

# ── Runtime DB: volatile tables only ───────────────────────────────────────
conn2 = sqlite3.connect(RUNTIME)
c2 = conn2.cursor()

c2.execute("""
CREATE TABLE IF NOT EXISTS signals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    token TEXT NOT NULL,
    direction TEXT NOT NULL,
    signal_type TEXT NOT NULL,
    source TEXT,
    confidence REAL NOT NULL,
    value REAL,
    price REAL,
    exchange TEXT DEFAULT 'hyperliquid',
    timeframe TEXT DEFAULT '1h',
    decision TEXT DEFAULT 'PENDING',
    decision_reason TEXT,
    executed INTEGER DEFAULT 0,
    z_score REAL,
    z_score_tier TEXT,
    momentum_state TEXT,
    rsi_14 REAL,
    macd_value REAL,
    macd_signal REAL,
    macd_hist REAL,
    leverage INTEGER,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
)""")
c2.execute('CREATE INDEX IF NOT EXISTS idx_sig_token ON signals(token)')
c2.execute('CREATE INDEX IF NOT EXISTS idx_sig_decision ON signals(decision)')

c2.execute("""
CREATE TABLE IF NOT EXISTS momentum_cache (
    token TEXT PRIMARY KEY,
    phase TEXT,
    percentile_long REAL,
    percentile_short REAL,
    velocity REAL,
    avg_z REAL,
    z_direction TEXT,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
)""")

c2.execute("""
CREATE TABLE IF NOT EXISTS token_intel (
    token TEXT PRIMARY KEY,
    exchange TEXT,
    max_leverage INTEGER,
    base_position_size REAL,
    open_positions INTEGER DEFAULT 0,
    last_signal_at TEXT,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
)""")

c2.execute("""
CREATE TABLE IF NOT EXISTS cooldown_tracker (
    token TEXT NOT NULL,
    direction TEXT NOT NULL,
    expires_at INTEGER NOT NULL,
    PRIMARY KEY(token, direction)
)""")

c2.execute("""
CREATE TABLE IF NOT EXISTS decisions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    token TEXT NOT NULL,
    direction TEXT NOT NULL,
    confidence REAL NOT NULL,
    entry_price REAL,
    exchange TEXT,
    decision TEXT NOT NULL,
    reason TEXT,
    server TEXT DEFAULT 'Hermes',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
)""")

conn2.commit()
print(f'Created runtime DB: {RUNTIME}')

# ── Migrate backfill data from legacy → static ───────────────────────────────
if os.path.exists(LEGACY):
    c.execute('SELECT COUNT(*) FROM price_history')
    before = c.fetchone()[0]

    c.execute('ATTACH DATABASE ? AS leg', (LEGACY,))
    c.execute('INSERT OR IGNORE INTO price_history(token, price, timestamp) SELECT token, price, timestamp FROM leg.price_history')
    conn.commit()
    c.execute('DETACH DATABASE leg')

    c.execute('SELECT COUNT(*) FROM price_history')
    after = c.fetchone()[0]
    print(f'Backfill migrated: +{after - before} rows (now {after} total)')

    c.execute('SELECT token, COUNT(*) as n FROM price_history GROUP BY token ORDER BY n ASC LIMIT 5')
    print('Lowest-row tokens:')
    for r in c.fetchall():
        print(f'  {r[0]}: {r[1]} rows')
else:
    print(f'Legacy DB not found at {LEGACY}')

conn.close()
conn2.close()
print('Done.')
