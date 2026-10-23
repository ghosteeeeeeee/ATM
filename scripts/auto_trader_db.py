#!/usr/bin/env python3
"""
auto_trader_db — data layer for the autonomous BTC loop (spec v2).

One DB, everything tracked: decisions, orders, shadow hypotheticals,
attribution, bounded self-tuning log, events. Scorecard = SQL views.

Phase 0 (shadow): all writes are journals — zero live effect.
"""
import os
import sqlite3
import time
import json
from paths import HERMES_DATA

DB_PATH = os.path.join(HERMES_DATA, 'auto_trader.db')

SCHEMA = """
CREATE TABLE IF NOT EXISTS decisions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts REAL NOT NULL,
    cycle_id TEXT,
    price REAL,
    regime_state TEXT,
    flips_24h INTEGER,
    structure_json TEXT,
    score_long REAL,
    score_short REAL,
    score_adj_best TEXT,
    decision TEXT,
    reasons_json TEXT,
    mode TEXT
);
CREATE TABLE IF NOT EXISTS orders_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    decision_id INTEGER,
    ts REAL NOT NULL,
    order_id TEXT,
    leg TEXT,
    trigger REAL,
    sl REAL,
    tp REAL,
    size REAL,
    leverage INTEGER,
    action TEXT,
    trade_id TEXT
);
CREATE TABLE IF NOT EXISTS hypotheticals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id TEXT UNIQUE,
    ts_armed REAL NOT NULL,
    direction TEXT,
    trigger REAL,
    sl REAL,
    tp REAL,
    size REAL,
    status TEXT DEFAULT 'armed',
    ts_hit REAL,
    ts_closed REAL,
    exit_price REAL,
    pnl_pct REAL,
    pnl_usdt REAL,
    regime_at_entry TEXT
);
CREATE TABLE IF NOT EXISTS attribution (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trade_id TEXT UNIQUE,
    ts_closed REAL NOT NULL,
    direction TEXT,
    regime_at_entry TEXT,
    entry_quality TEXT,
    planned_rr REAL,
    real_rr REAL,
    pnl_pct REAL,
    pnl_usdt REAL,
    exit_reason TEXT,
    won INTEGER,
    lesson_tags TEXT
);
CREATE TABLE IF NOT EXISTS self_tuning (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts REAL NOT NULL,
    parameter TEXT,
    old_value REAL,
    new_value REAL,
    bound TEXT,
    reason TEXT
);
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts REAL NOT NULL,
    level TEXT,
    message TEXT
);
CREATE INDEX IF NOT EXISTS idx_hypo_status ON hypotheticals(status);
CREATE INDEX IF NOT EXISTS idx_attr_trade ON attribution(trade_id);
"""

VIEWS = """
CREATE VIEW IF NOT EXISTS scorecard AS
SELECT
    COUNT(*) AS n,
    SUM(CASE WHEN won=1 THEN 1 ELSE 0 END) AS wins,
    ROUND(100.0*SUM(CASE WHEN won=1 THEN 1 ELSE 0 END)/NULLIF(COUNT(*),0), 1) AS wr,
    ROUND(SUM(pnl_usdt), 3) AS pnl_usdt,
    ROUND(AVG(pnl_pct), 3) AS avg_pnl_pct,
    ROUND(AVG(planned_rr), 2) AS avg_planned_rr,
    ROUND(AVG(real_rr), 2) AS avg_real_rr
FROM attribution;
CREATE VIEW IF NOT EXISTS scorecard_by_regime AS
SELECT regime_at_entry, COUNT(*) AS n,
    SUM(CASE WHEN won=1 THEN 1 ELSE 0 END) AS wins,
    ROUND(100.0*SUM(CASE WHEN won=1 THEN 1 ELSE 0 END)/NULLIF(COUNT(*),0),1) AS wr,
    ROUND(SUM(pnl_usdt), 3) AS pnl_usdt
FROM attribution GROUP BY regime_at_entry;
CREATE VIEW IF NOT EXISTS scorecard_by_direction AS
SELECT direction, COUNT(*) AS n,
    SUM(CASE WHEN won=1 THEN 1 ELSE 0 END) AS wins,
    ROUND(100.0*SUM(CASE WHEN won=1 THEN 1 ELSE 0 END)/NULLIF(COUNT(*),0),1) AS wr,
    ROUND(SUM(pnl_usdt), 3) AS pnl_usdt
FROM attribution GROUP BY direction;
"""


def connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = connect()
    try:
        conn.executescript(SCHEMA)
        conn.executescript(VIEWS)
        # Migration for pre-UNIQUE DBs (phase 0 data): dedupe by trade_id
        # (keep newest — the BUG-A double-attribution rows), then enforce.
        cur = conn.cursor()
        cur.execute("DELETE FROM attribution WHERE id NOT IN "
                    "(SELECT MAX(id) FROM attribution GROUP BY trade_id)")
        cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_attr_unique "
                    "ON attribution(trade_id)")
        # One-time backfill: rows resolved BEFORE the R:R fix get planned/real
        # R:R from their hypothetical's armed levels (slip = 0.12% of trigger,
        # 150pt floor per skill). CORRELATED form (bug_hunter fix: the old
        # UPDATE...FROM self-join with unqualified attribution refs stamped
        # EVERY row with one pair's values — production corruption event).
        # Unqualified trade_id/direction in WHERE/SET resolve against the
        # UPDATE target row; the join matches per-row on 'shadow:'||order_id.
        cur.execute("""
            UPDATE attribution SET
              planned_rr = CASE WHEN attribution.direction='long'
                THEN ROUND((h.tp - h.trigger) / NULLIF(h.trigger - h.sl, 0), 2)
                ELSE ROUND((h.trigger - h.tp) / NULLIF(h.sl - h.trigger, 0), 2) END,
              real_rr = CASE WHEN attribution.direction='long'
                THEN ROUND((h.tp - h.trigger) / NULLIF(h.trigger - h.sl + MAX(h.trigger*0.0012, 150), 0), 2)
                ELSE ROUND((h.trigger - h.tp) / NULLIF(h.sl - h.trigger + MAX(h.trigger*0.0012, 150), 0), 2) END
            FROM hypotheticals h
            WHERE attribution.trade_id = 'shadow:' || h.order_id
              AND attribution.planned_rr IS NULL
              AND h.trigger IS NOT NULL AND h.sl IS NOT NULL AND h.tp IS NOT NULL
        """)
        # Trigger-direction column: continuation mapping (skill §12 FIXED)
        # fires long ABOVE / short BELOW, but legs armed before the flip were
        # fade-style (long below / short above). Column + backfill preserves
        # correct hit-tracking for both generations.
        try:
            cur.execute("ALTER TABLE hypotheticals ADD COLUMN trigger_dir TEXT")
        except sqlite3.OperationalError:
            pass  # column exists
        cur.execute("UPDATE hypotheticals SET trigger_dir='below' "
                    "WHERE direction='long' AND trigger_dir IS NULL")
        cur.execute("UPDATE hypotheticals SET trigger_dir='above' "
                    "WHERE direction='short' AND trigger_dir IS NULL")
        conn.commit()
    finally:
        conn.close()


def _exec(sql, params=(), fetch=None):
    conn = connect()
    try:
        cur = conn.cursor()
        cur.execute(sql, params)
        result = None
        if fetch == 'one':
            result = cur.fetchone()
        elif fetch == 'all':
            result = cur.fetchall()
        conn.commit()
        return result
    finally:
        conn.close()


def record_decision(d):
    """d: dict with regime/structure/scores/decision/reasons/mode/price/cycle_id.
    Returns lastrowid from the SAME connection (E1: was 0 from a fresh conn)."""
    conn = connect()
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO decisions (ts, cycle_id, price, regime_state, flips_24h, "
            "structure_json, score_long, score_short, score_adj_best, decision, "
            "reasons_json, mode) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (time.time(), d.get('cycle_id'), d.get('price'), d.get('regime_state'),
             d.get('flips_24h'), json.dumps(d.get('structure', {})),
             d.get('score_long'), d.get('score_short'), d.get('score_adj_best'),
             d.get('decision'), json.dumps(d.get('reasons', [])), d.get('mode')))
        rowid = cur.lastrowid
        conn.commit()
        return rowid
    finally:
        conn.close()


def record_order(decision_id, leg, o, action, size, leverage):
    _exec(
        "INSERT INTO orders_log (decision_id, ts, order_id, leg, trigger, sl, tp, "
        "size, leverage, action) VALUES (?,?,?,?,?,?,?,?,?,?)",
        (decision_id, time.time(), o.get('order_id'), leg, o.get('trigger'),
         o.get('sl'), o.get('tp'), size, leverage, action))


def upsert_hypothetical(o, regime_at_entry, size):
    """One per order_id (UNIQUE). Shadow paper-tracking.
    o may carry trigger_dir ('above'/'below') — which side of the trigger
    price must cross to fire; required for hit-tracking after the §12
    continuation mapping flip."""
    conn = connect()
    try:
        cur = conn.cursor()
        cur.execute("SELECT id, status FROM hypotheticals WHERE order_id=?", (o['order_id'],))
        row = cur.fetchone()
        if row:
            return row['id']  # already tracked — never re-arm (one-shot)
        cur.execute(
            "INSERT INTO hypotheticals (order_id, ts_armed, direction, trigger, sl, tp, "
            "size, regime_at_entry, trigger_dir) VALUES (?,?,?,?,?,?,?,?,?)",
            (o['order_id'], time.time(), o['direction'], o['trigger'],
             o['sl'], o['tp'], size, regime_at_entry, o.get('trigger_dir')))
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def get_hypotheticals(status):
    return _exec("SELECT * FROM hypotheticals WHERE status=? ORDER BY ts_armed",
                 (status,), fetch='all')


def update_hypothetical(order_id, **fields):
    sets = ', '.join(f"{k}=?" for k in fields)
    _exec(f"UPDATE hypotheticals SET {sets} WHERE order_id=?",
          (*fields.values(), order_id))


def record_attribution(a):
    """INSERT OR IGNORE — trade_id is UNIQUE (BUG A: exactly one row per
    resolution; hit-time rows removed)."""
    _exec(
        "INSERT OR IGNORE INTO attribution (trade_id, ts_closed, direction, "
        "regime_at_entry, entry_quality, planned_rr, real_rr, pnl_pct, pnl_usdt, "
        "exit_reason, won, lesson_tags) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
        (a.get('trade_id'), a.get('ts_closed', time.time()), a.get('direction'),
         a.get('regime_at_entry'), a.get('entry_quality'), a.get('planned_rr'),
         a.get('real_rr'), a.get('pnl_pct'), a.get('pnl_usdt'),
         a.get('exit_reason'), 1 if a.get('won') else 0,
         json.dumps(a.get('lesson_tags', []))))


def record_self_tune(parameter, old_value, new_value, bound, reason):
    _exec("INSERT INTO self_tuning (ts, parameter, old_value, new_value, bound, reason) "
          "VALUES (?,?,?,?,?,?)",
          (time.time(), parameter, old_value, new_value, bound, reason))


def log_event(level, message):
    _exec("INSERT INTO events (ts, level, message) VALUES (?,?,?)",
          (time.time(), level, message))


def get_scorecard():
    row = _exec("SELECT * FROM scorecard", fetch='one')
    return dict(row) if row else {}


def get_scorecard_by_regime():
    return [dict(r) for r in _exec("SELECT * FROM scorecard_by_regime", fetch='all')]


def get_scorecard_by_direction():
    return [dict(r) for r in _exec("SELECT * FROM scorecard_by_direction", fetch='all')]


def recent_decisions(limit=10):
    return [dict(r) for r in _exec(
        "SELECT * FROM decisions ORDER BY ts DESC LIMIT ?", (limit,), fetch='all')]


def recent_attribution(limit=10):
    return [dict(r) for r in _exec(
        "SELECT * FROM attribution ORDER BY ts_closed DESC LIMIT ?", (limit,), fetch='all')]


def recent_self_tuning(limit=5):
    return [dict(r) for r in _exec(
        "SELECT * FROM self_tuning ORDER BY ts DESC LIMIT ?", (limit,), fetch='all')]


def recent_events(limit=10):
    return [dict(r) for r in _exec(
        "SELECT * FROM events ORDER BY ts DESC LIMIT ?", (limit,), fetch='all')]


if __name__ == '__main__':
    init_db()
    print(f"auto_trader.db initialized at {DB_PATH}")
