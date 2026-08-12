#!/usr/bin/env python3
"""
coin_tracker_schema.py — Schema for per-coin intelligence tracking.

DB: /root/.hermes/data/coin_tracker.db

Architecture:
  - _meta: global state
  - _coin_registry: master list of all tracked coins
  - coin_{SYMBOL}: per-coin event history (price, volume, indicators, health)
  - agg_scores: latest composite scores for all coins
"""
import sqlite3, os, time
from paths import HERMES_DATA

COIN_TRACKER_DB = os.path.join(HERMES_DATA, 'coin_tracker.db')

_INIT_DONE = False

def _conn(path=None):
    """Get a connection with WAL mode and foreign keys."""
    conn = sqlite3.connect(path or COIN_TRACKER_DB, timeout=30)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.row_factory = sqlite3.Row
    return conn

def _table_name(symbol):
    """Convert symbol to safe table name. BTC -> coin_BTC"""
    safe = ''.join(c for c in symbol if c.isalnum() or c == '_')
    return f'coin_{safe}'

def init_db():
    """Initialize coin_tracker.db. Idempotent — safe to call on every run."""
    global _INIT_DONE
    if _INIT_DONE:
        return
    os.makedirs(HERMES_DATA, exist_ok=True)

    conn = _conn()
    cur = conn.cursor()

    # ── Global metadata ──
    cur.execute("""
        CREATE TABLE IF NOT EXISTS _meta (
            key TEXT PRIMARY KEY,
            val TEXT,
            updated_at INTEGER
        )
    """)

    # ── Coin registry ──
    cur.execute("""
        CREATE TABLE IF NOT EXISTS _coin_registry (
            symbol TEXT PRIMARY KEY,
            name TEXT,
            first_seen INTEGER,
            last_seen INTEGER,
            status TEXT DEFAULT 'active',
            health TEXT DEFAULT 'unknown',
            health_score REAL DEFAULT 0,
            last_signal TEXT,
            signal_count_24h INTEGER DEFAULT 0,
            win_rate REAL,
            total_trades INTEGER DEFAULT 0,
            avg_spread_bps REAL,
            max_leverage INTEGER,
            decimals INTEGER
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_registry_health ON _coin_registry(health)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_registry_score ON _coin_registry(health_score DESC)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_registry_status ON _coin_registry(status)")

    # ── Composite scores (latest per coin) ──
    cur.execute("""
        CREATE TABLE IF NOT EXISTS agg_scores (
            symbol TEXT PRIMARY KEY,
            ts INTEGER,
            health TEXT,
            score REAL,
            momentum REAL,
            volume REAL,
            volatility REAL,
            spread REAL,
            signals REAL,
            regime REAL,
            composite REAL
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_scores_composite ON agg_scores(composite DESC)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_scores_health ON agg_scores(health)")

    conn.commit()
    conn.close()
    _INIT_DONE = True

def ensure_coin_table(symbol):
    """Create per-coin table if it doesn't exist. Returns table name."""
    table = _table_name(symbol)
    conn = _conn()
    conn.execute(f"""
        CREATE TABLE IF NOT EXISTS {table} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts INTEGER NOT NULL,
            event_type TEXT NOT NULL,
            price REAL,
            bid REAL,
            ask REAL,
            spread_bps REAL,
            vol_1m REAL,
            vol_5m REAL,
            vol_1h REAL,
            vol_24h REAL,
            rsi_14 REAL,
            macd_hist REAL,
            ema_9 REAL,
            ema_20 REAL,
            ema_50 REAL,
            atr_14 REAL,
            health TEXT,
            health_score REAL,
            signal_type TEXT,
            signal_confidence REAL,
            regime TEXT,
            notes TEXT
        )
    """)
    conn.execute(f"CREATE INDEX IF NOT EXISTS idx_{table}_ts ON {table}(ts)")
    conn.execute(f"CREATE INDEX IF NOT EXISTS idx_{table}_health ON {table}(health)")
    conn.execute(f"CREATE INDEX IF NOT EXISTS idx_{table}_event ON {table}(event_type)")
    conn.commit()
    conn.close()
    return table

def upsert_registry(symbol, name=None, max_leverage=None, decimals=None):
    """Add or update coin in registry. Idempotent."""
    conn = _conn()
    now = int(time.time())
    conn.execute("""
        INSERT INTO _coin_registry (symbol, name, first_seen, last_seen, max_leverage, decimals)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(symbol) DO UPDATE SET
            last_seen = excluded.last_seen,
            name = COALESCE(excluded.name, _coin_registry.name),
            max_leverage = COALESCE(excluded.max_leverage, _coin_registry.max_leverage),
            decimals = COALESCE(excluded.decimals, _coin_registry.decimals)
    """, (symbol, name, now, now, max_leverage, decimals))
    conn.commit()
    conn.close()

def write_event(symbol, event_type, ts=None, **kwargs):
    """Write an event to a coin's table. Auto-creates table if needed."""
    table = ensure_coin_table(symbol)
    ts = ts or int(time.time())

    allowed = {
        'price', 'bid', 'ask', 'spread_bps',
        'vol_1m', 'vol_5m', 'vol_1h', 'vol_24h',
        'rsi_14', 'macd_hist', 'ema_9', 'ema_20', 'ema_50', 'atr_14',
        'health', 'health_score',
        'signal_type', 'signal_confidence',
        'regime', 'notes'
    }
    cols = {k: v for k, v in kwargs.items() if k in allowed and v is not None}
    cols['ts'] = ts
    cols['event_type'] = event_type

    placeholders = ', '.join(['?'] * len(cols))
    col_names = ', '.join(cols.keys())

    conn = _conn()
    conn.execute(f"INSERT INTO {table} ({col_names}) VALUES ({placeholders})", list(cols.values()))
    conn.commit()
    conn.close()

def write_score(symbol, ts, health, score, momentum, volume, volatility, spread, signals, regime, composite):
    """Write composite score for a coin. Upserts into agg_scores."""
    conn = _conn()
    conn.execute("""
        INSERT INTO agg_scores (symbol, ts, health, score, momentum, volume, volatility, spread, signals, regime, composite)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(symbol) DO UPDATE SET
            ts = excluded.ts,
            health = excluded.health,
            score = excluded.score,
            momentum = excluded.momentum,
            volume = excluded.volume,
            volatility = excluded.volatility,
            spread = excluded.spread,
            signals = excluded.signals,
            regime = excluded.regime,
            composite = excluded.composite
    """, (symbol, ts, health, score, momentum, volume, volatility, spread, signals, regime, composite))
    conn.commit()
    conn.close()

def update_registry_health(symbol, health, health_score):
    """Update health state in registry."""
    conn = _conn()
    conn.execute("""
        UPDATE _coin_registry SET health = ?, health_score = ?, last_seen = ?
        WHERE symbol = ?
    """, (health, health_score, int(time.time()), symbol))
    conn.commit()
    conn.close()

def get_all_coins():
    """Return all coins from registry as list of dicts."""
    conn = _conn()
    rows = conn.execute("SELECT * FROM _coin_registry ORDER BY health_score DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_scores(limit=None):
    """Return all scores sorted by composite DESC."""
    conn = _conn()
    q = "SELECT * FROM agg_scores ORDER BY composite DESC"
    if limit:
        q += f" LIMIT {limit}"
    rows = conn.execute(q).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_coin_events(symbol, hours=24, event_type=None):
    """Return recent events for a coin."""
    table = _table_name(symbol)
    conn = _conn()
    cutoff = int(time.time()) - (hours * 3600)
    q = f"SELECT * FROM {table} WHERE ts > ?"
    params = [cutoff]
    if event_type:
        q += " AND event_type = ?"
        params.append(event_type)
    q += " ORDER BY ts DESC"
    rows = conn.execute(q, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_coin_latest(symbol):
    """Return the latest event for a coin."""
    table = _table_name(symbol)
    conn = _conn()
    try:
        row = conn.execute(f"SELECT * FROM {table} ORDER BY ts DESC LIMIT 1").fetchone()
    except Exception:
        row = None
    conn.close()
    return dict(row) if row else None

def get_coin_candles(symbol, hours=24):
    """Return price history for charting (ts, price, volume, health, signal_type)."""
    table = _table_name(symbol)
    conn = _conn()
    cutoff = int(time.time()) - (hours * 3600)
    try:
        rows = conn.execute(
            f"SELECT ts, price, vol_1m, health, signal_type, health_score FROM {table} WHERE ts > ? AND price IS NOT NULL ORDER BY ts",
            [cutoff]
        ).fetchall()
    except Exception:
        rows = []
    conn.close()
    return [dict(r) for r in rows]

def get_registry_stats():
    """Return summary stats for the dashboard header."""
    conn = _conn()
    total = conn.execute("SELECT COUNT(*) FROM _coin_registry").fetchone()[0]
    by_health = {}
    for row in conn.execute("SELECT health, COUNT(*) as cnt FROM _coin_registry GROUP BY health"):
        by_health[row['health']] = row['cnt']
    avg_score = conn.execute("SELECT AVG(health_score) FROM _coin_registry").fetchone()[0] or 0
    conn.close()
    return {
        'total': total,
        'by_health': by_health,
        'avg_score': round(avg_score, 1),
    }

def prune_old_events(days=30):
    """Delete events older than N days from all per-coin tables."""
    conn = _conn()
    cutoff = int(time.time()) - (days * 86400)
    # Get all coin tables
    tables = [r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'coin_%' AND name != '_coin_registry'"
    ).fetchall()]
    total_deleted = 0
    for table in tables:
        cur = conn.execute(f"DELETE FROM {table} WHERE ts < ?", [cutoff])
        total_deleted += cur.rowcount
    conn.commit()
    conn.close()
    return total_deleted

def set_meta(key, val):
    """Set a metadata value."""
    conn = _conn()
    conn.execute(
        "INSERT INTO _meta (key, val, updated_at) VALUES (?, ?, ?) ON CONFLICT(key) DO UPDATE SET val=excluded.val, updated_at=excluded.updated_at",
        (key, val, int(time.time()))
    )
    conn.commit()
    conn.close()

def get_meta(key):
    """Get a metadata value."""
    conn = _conn()
    row = conn.execute("SELECT val FROM _meta WHERE key=?", [key]).fetchone()
    conn.close()
    return row['val'] if row else None
