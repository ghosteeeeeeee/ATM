#!/usr/bin/env python3
"""Signal Schema - Dual-database architecture for Hermes trading system.

STATIC DB  (/root/.hermes/data/signals_hermes.db)   — backfill data, git-tracked
RUNTIME DB (/root/.hermes/data/signals_hermes_runtime.db) — signals, decisions, local state
"""
import sqlite3, time, json, os
from datetime import datetime, timedelta
import psycopg2

# ── Database paths ────────────────────────────────────────────────────────────
HERMES_DATA = os.environ.get('HERMES_DATA_DIR', '/root/.hermes/data')
STATIC_DB   = os.path.join(HERMES_DATA, 'signals_hermes.db')
RUNTIME_DB  = os.path.join(HERMES_DATA, 'signals_hermes_runtime.db')

# Legacy path — fall back to it if new DBs don't exist yet
LEGACY_DB   = '/root/.openclaw/workspace/data/signals.db'

def _get_conn(path, row_factory=False):
    conn = sqlite3.connect(path, timeout=30)
    if row_factory:
        conn.row_factory = sqlite3.Row
    return conn

def _static():
    if os.path.exists(STATIC_DB):
        return STATIC_DB
    return LEGACY_DB  # Fallback for migration period

def _runtime():
    return RUNTIME_DB

# ── Init both DBs ─────────────────────────────────────────────────────────────
_init_done = False
def init_db():
    """Initialize both static and runtime DBs with proper schemas."""
    global _init_done
    if _init_done:
        return
    os.makedirs(HERMES_DATA, exist_ok=True)

    # ── Static DB ──
    sc = _get_conn(STATIC_DB)
    sc.execute("""
        CREATE TABLE IF NOT EXISTS price_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            token TEXT NOT NULL,
            price REAL NOT NULL,
            timestamp INTEGER NOT NULL,
            UNIQUE(token, timestamp)
        )""")
    sc.execute('CREATE INDEX IF NOT EXISTS idx_ph_token ON price_history(token)')
    sc.execute('CREATE INDEX IF NOT EXISTS idx_ph_ts ON price_history(timestamp)')
    sc.execute("""
        CREATE TABLE IF NOT EXISTS latest_prices (
            token TEXT PRIMARY KEY,
            price REAL NOT NULL,
            updated_at INTEGER NOT NULL,
            max_leverage INTEGER DEFAULT 10
        )""")
    sc.execute("""
        CREATE TABLE IF NOT EXISTS regime_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            regime TEXT NOT NULL,
            broad_z REAL NOT NULL,
            long_mult REAL NOT NULL,
            short_mult REAL NOT NULL,
            timestamp INTEGER NOT NULL
        )""")
    sc.commit()
    sc.close()

    # ── Runtime DB ──
    rc = _get_conn(RUNTIME_DB)
    rc.execute("""
        CREATE TABLE IF NOT EXISTS signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            token TEXT NOT NULL,
            direction TEXT NOT NULL,
            signal_type TEXT NOT NULL,
            source TEXT,
            confidence REAL NOT NULL,
            value REAL, price REAL,
            exchange TEXT DEFAULT 'hyperliquid',
            timeframe TEXT DEFAULT '1h',
            decision TEXT DEFAULT 'PENDING',
            decision_reason TEXT,
            executed INTEGER DEFAULT 0,
            z_score REAL, z_score_tier TEXT,
            momentum_state TEXT,
            rsi_14 REAL, macd_value REAL,
            macd_signal REAL, macd_hist REAL,
            leverage INTEGER DEFAULT 10,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )""")
    # Add columns for hot-set signal tracking (compact_rounds, survival_score).
    # Safe to run on every init — ADD COLUMN is idempotent if column exists.
    # SQLite 3.35+ supports IF NOT EXISTS; fallback to try/except for older versions.
    try:
        rc.execute("ALTER TABLE signals ADD COLUMN IF NOT EXISTS compact_rounds INTEGER DEFAULT 0")
    except Exception:
        try:
            rc.execute("ALTER TABLE signals ADD COLUMN compact_rounds INTEGER DEFAULT 0")
        except Exception:
            pass  # column already exists
    try:
        rc.execute("ALTER TABLE signals ADD COLUMN IF NOT EXISTS survival_score REAL DEFAULT 0")
    except Exception:
        try:
            rc.execute("ALTER TABLE signals ADD COLUMN survival_score REAL DEFAULT 0")
        except Exception:
            pass
    try:
        rc.execute("ALTER TABLE signals ADD COLUMN last_compact_at TEXT")
    except Exception:
        try:
            rc.execute("ALTER TABLE signals ADD COLUMN last_compact_at TEXT")
        except Exception:
            pass
    try:
        rc.execute("ALTER TABLE signals ADD COLUMN IF NOT EXISTS learned_sl_multiplier REAL DEFAULT 1.0")
    except Exception:
        try:
            rc.execute("ALTER TABLE signals ADD COLUMN learned_sl_multiplier REAL DEFAULT 1.0")
        except Exception:
            pass
    rc.execute('CREATE INDEX IF NOT EXISTS idx_sig_decision ON signals(decision)')
    rc.execute('CREATE INDEX IF NOT EXISTS idx_sig_token ON signals(token)')
    rc.execute('CREATE INDEX IF NOT EXISTS idx_sig_created ON signals(created_at)')

    # ── Signal History (compaction tracking for self-learning) ───────────────
    # ai-decider.py writes to this table during signal compaction.
    # Without it, all INSERT INTO signal_history calls silently fail.
    rc.execute("""
        CREATE TABLE IF NOT EXISTS signal_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            token TEXT NOT NULL,
            direction TEXT NOT NULL,
            signal_type TEXT NOT NULL,
            compact_round INTEGER NOT NULL,
            survived INTEGER NOT NULL,
            score_before REAL,
            score_after REAL,
            reason TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    rc.execute('CREATE INDEX IF NOT EXISTS idx_sh_token ON signal_history(token)')
    rc.execute('CREATE INDEX IF NOT EXISTS idx_sh_round ON signal_history(compact_round)')
    rc.execute("""
        CREATE TABLE IF NOT EXISTS momentum_cache (
            token TEXT PRIMARY KEY,
            phase TEXT, percentile_long REAL, percentile_short REAL,
            velocity REAL, avg_z REAL, z_direction TEXT,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )""")
    rc.execute("""
        CREATE TABLE IF NOT EXISTS token_intel (
            token TEXT PRIMARY KEY,
            exchange TEXT, max_leverage INTEGER, base_position_size REAL,
            open_positions INTEGER DEFAULT 0,
            last_signal_at TEXT,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )""")
    rc.execute("""
        CREATE TABLE IF NOT EXISTS cooldown_tracker (
            token TEXT NOT NULL,
            direction TEXT NOT NULL,
            expires_at INTEGER NOT NULL,
            PRIMARY KEY(token, direction)
        )""")
    rc.execute("""
        CREATE TABLE IF NOT EXISTS decisions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            token TEXT NOT NULL, direction TEXT NOT NULL,
            confidence REAL NOT NULL, entry_price REAL, exchange TEXT,
            decision TEXT NOT NULL, reason TEXT,
            server TEXT DEFAULT 'Hermes',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    # signal_history table — stores compacted signal lifecycle for AI learning
    rc.execute("""
        CREATE TABLE IF NOT EXISTS signal_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            token TEXT NOT NULL,
            direction TEXT NOT NULL,
            signal_type TEXT NOT NULL,
            compact_round INTEGER NOT NULL,
            survived INTEGER NOT NULL,
            score_before REAL,
            score_after REAL,
            reason TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    rc.execute("CREATE INDEX IF NOT EXISTS idx_sighist_token ON signal_history(token, direction)")
    rc.commit()
    rc.close()
    # ── Migrate legacy backfill data to static DB ──
    if os.path.exists(LEGACY_DB) and os.path.getsize(LEGACY_DB) > 0:
        sc = _get_conn(STATIC_DB)
        leg = _get_conn(LEGACY_DB)
        lc = leg.cursor()
        lc.execute('SELECT COUNT(*) FROM price_history')
        before = sc.execute('SELECT COUNT(*) FROM price_history').fetchone()[0]
        sc.execute('ATTACH DATABASE ? AS leg', (LEGACY_DB,))
        sc.execute('''
            INSERT OR IGNORE INTO price_history(token, price, timestamp)
            SELECT token, price, timestamp FROM leg.price_history
        ''')
        sc.commit()
        sc.execute('DETACH DATABASE leg')
        after = sc.execute('SELECT COUNT(*) FROM price_history').fetchone()[0]
        sc.close()
        leg.close()
        if after > before:
            print(f'DB migration: +{after - before} rows migrated to {STATIC_DB}')
    else:
        print('No legacy DB to migrate')

    # Auto-load backfill seed if static DB is empty
    seed_path = os.path.join(os.path.dirname(__file__), '..', 'seed', 'signals_hermes.sql')
    if os.path.exists(seed_path):
        sc = _get_conn(STATIC_DB)
        count = sc.execute('SELECT COUNT(*) FROM price_history').fetchone()[0]
        if count == 0:
            print(f'Loading backfill seed from {seed_path} ...')
            with open(seed_path) as f:
                sc.executescript(f.read())
            sc.commit()
            new_count = sc.execute('SELECT COUNT(*) FROM price_history').fetchone()[0]
            print(f'Seed loaded: {new_count} rows')
        else:
            print(f'Static DB already has {count} price_history rows')
        sc.close()
    else:
        print(f'No seed file at {seed_path}')

    _init_done = True

# ── Signals (runtime DB) ──────────────────────────────────────────────────────
def add_signal(token, direction, signal_type, source, confidence, value=None, price=None,
               exchange='hyperliquid', timeframe='1h', z_score=None, z_score_tier=None,
               momentum_state=None, rsi_14=None, macd_value=None, macd_signal=None,
               macd_hist=None, leverage=None, **kwargs):
    """Add a new signal. Combines with existing PENDING signal for same token+direction+signal_type
    within 30 min — takes max confidence, merges sources list.
    
    KEY FIX: Only merges signals with the SAME signal_type. Different signal_types
    (e.g. 'rsi_confluence' vs 'macd_confluence') always create SEPARATE rows so that
    get_confluence_signals() can detect them as distinct agreeing indicators."""
    conn = _get_conn(_runtime())
    c = conn.cursor()
    try:
        # Check for existing PENDING signal for SAME token+direction+signal_type in last 30 min
        # Only merge identical signal_type so that RSI+MACD create distinct rows → confluence detection works
        c.execute('''
            SELECT id, source, confidence FROM signals
            WHERE token=? AND direction=? AND signal_type=? AND executed=0 AND decision='PENDING'
            AND created_at > datetime('now', '-30 minutes')
            LIMIT 1
        ''', (token.upper(), direction.upper(), signal_type))
        existing = c.fetchone()
        if existing:
            sig_id, existing_source, existing_conf = existing
            old_sources = set(existing_source.split('+'))
            new_sources_set = set(source.split('+'))
            all_sources = old_sources | new_sources_set
            new_sources = '+'.join(sorted(all_sources))
            num_sources_gained = len(new_sources_set - old_sources)

            if confidence < existing_conf:
                # Declining confidence: penalize. Reduce by 40% of the drop + credit for new sources.
                decay = (existing_conf - confidence) * 0.4
                new_conf = max(existing_conf - decay + (num_sources_gained * 1.0), min(existing_conf, confidence))
                new_conf = max(1, min(99, new_conf))
            else:
                # Rising or equal confidence: boost for new sources, take max
                new_conf = max(existing_conf, confidence)
                if num_sources_gained > 0:
                    new_conf = min(100, new_conf + num_sources_gained)

            c.execute('''
                UPDATE signals SET confidence=?, source=?, updated_at=CURRENT_TIMESTAMP
                WHERE id=?
            ''', (new_conf, new_sources, sig_id))
            conn.commit()
            conn.close()
            return sig_id  # return existing signal id (updated)
        # No existing — insert new
        c.execute('''
            INSERT INTO signals
            (token, direction, signal_type, source, confidence, value, price,
             exchange, timeframe, z_score, z_score_tier, momentum_state,
             rsi_14, macd_value, macd_signal, macd_hist, decision, executed, leverage)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'PENDING', 0, ?)
        ''', (token.upper(), direction.upper(), signal_type, source, confidence, value,
              price, exchange, timeframe, z_score, z_score_tier, momentum_state,
              rsi_14, macd_value, macd_signal, macd_hist, leverage))
        conn.commit()
        sid = c.lastrowid
        conn.close()
        return sid
    except Exception as e:
        conn.close()
        print(f'add_signal error: {e}')
        return None

def get_pending_signals(hours=24, limit=50):
    """Get PENDING signals, sorted LIFO + confidence.
    
    NOTE: This function is used by signal_gen.py for confluence detection.
    For ai-decider.py decisioning, use get_pending_signals() in ai-decider.py
    which has 15-min expiry + AI-guided compaction built in.
    This function is kept for backward compat with a slightly different query path.
    """
    conn = _get_conn(_runtime(), row_factory=True)
    c = conn.cursor()
    c.execute('''
        SELECT * FROM signals
        WHERE decision='PENDING'
        AND executed=0
        AND created_at > datetime('now','-'||?||' hours')
        ORDER BY created_at DESC, confidence DESC LIMIT ?
    ''', (hours, limit))
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]

get_pending_signals_as_dict = get_pending_signals  # alias

def expire_pending_signals(minutes=15):
    """Expire PENDING signals older than `minutes`. Called every signal_gen run
    to prevent the queue from accumulating stale signals. Signals that haven't
    been acted on within the window are cleared — the next signal generation
    cycle will create fresh ones if the conditions still exist."""
    conn = _get_conn(_runtime())
    c = conn.cursor()
    c.execute("""
        UPDATE signals
        SET decision = 'EXPIRED'
        WHERE decision = 'PENDING'
          AND created_at < datetime('now', ?)
          AND executed = 0
    """, (f'-{minutes} minutes',))
    conn.commit()
    expired = c.rowcount
    c.close()
    if expired > 0:
        print(f'  [Signal Expiry] Cleared {expired} stale PENDING signals (>15 min old)')
    return expired


def get_confluence_signals(hours=24, min_signals=2, signal_types=None):
    """Return tokens where ≥min_signals PENDING signal types agree.
    Used by ai_decider / decider-run. Boosts confidence by 1.25x (2 signals)
    or 1.5x (3+ signals).

    Sources signals from BOTH Hermes runtime DB AND OpenClaw's signals.db.
    OpenClaw's multi-timeframe (mtf-*) signals are included via ATTACH so
    they can combine with Hermes RSI/MACD signals in confluence detection.

    Args:
        signal_types: optional list of signal_type strings to filter.
                      e.g. ['rsi_confluence', 'macd_confluence'] to exclude 'momentum'.
    """
    conn = _get_conn(_runtime(), row_factory=True)
    c = conn.cursor()

    # Attach OpenClaw's signals.db so we can query both DBs together.
    # OpenClaw signals have source='mtf-*' and signal_type='mtf_macd'.
    # Hermes signals have source='mtf-*' and signal_type='momentum'.
    if os.path.exists(LEGACY_DB):
        try:
            c.execute(f"ATTACH DATABASE ? AS oc", (LEGACY_DB,))
        except sqlite3.IntegrityError:
            pass  # Already attached — safe to ignore
        except sqlite3.OperationalError as e:
            if "already exists" not in str(e):
                print(f"WARNING: Could not attach {LEGACY_DB}: {e}")
        except Exception as e:
            print(f"WARNING: Unexpected error attaching {LEGACY_DB}: {e}")

    # Build dynamic WHERE clause for signal_type filter
    if signal_types:
        st_list = list(signal_types)
        type_filter = "AND signal_type IN (" + ",".join(["?" for _ in st_list]) + ")"
        params = (hours,) + tuple(st_list) + (hours,) + tuple(st_list) + (min_signals,)
    else:
        type_filter = ""
        params = (hours, hours, min_signals)

    # Query both DBs using UNION ALL. Use GROUP_CONCAT to track which
    # DB each signal came from (oc_ vs Hermes) for study logging.
    query = f"""
        WITH all_signals AS (
            SELECT token, direction, signal_type, source, confidence, price,
                   z_score, rsi_14, macd_hist,
                   'hermes' as db_source
            FROM signals
            WHERE decision='PENDING'
            AND created_at > datetime('now','-'||?||' hours')
            {"AND signal_type IN (" + ",".join(["?" for _ in st_list]) + ")" if signal_types else ""}
            UNION ALL
            SELECT token, direction, signal_type, source, confidence, price,
                   z_score, rsi_14, macd_hist,
                   'openclaw' as db_source
            FROM oc.signals
            WHERE decision='PENDING'
            AND created_at > datetime('now','-'||?||' hours')
            {"AND signal_type IN (" + ",".join(["?" for _ in st_list]) + ")" if signal_types else ""}
        )
        SELECT token, direction,
               COUNT(DISTINCT signal_type) as num_types,
               COUNT(*) as total_rows,
               AVG(confidence) as avg_conf,
               MAX(confidence) as max_conf,
               GROUP_CONCAT(DISTINCT signal_type) as types,
               GROUP_CONCAT(DISTINCT db_source) as db_sources,
               GROUP_CONCAT(DISTINCT source) as all_sources,
               MAX(price) as price,
               MAX(z_score) as z_score,
               MAX(rsi_14) as rsi_14
        FROM all_signals
        GROUP BY token, direction
        HAVING COUNT(DISTINCT signal_type) >= ?
        ORDER BY avg_conf DESC
    """
    c.execute(query, params)
    results = []
    for r in c.fetchall():
        d = dict(r)
        mult = 1.5 if d['num_types'] >= 3 else 1.25 if d['num_types'] == 2 else 1.0
        d['final_confidence'] = min(99, d['avg_conf'] * mult)
        d['num_agreeing'] = d['num_types']
        if d.get('types'):
            d['signal_types'] = d['types'].split(',')
        # Track OpenClaw vs Hermes sources for study logging
        if d.get('all_sources'):
            all_srcs = d['all_sources'].split(',')
            d['openclaw_sources'] = sorted(s for s in all_srcs if s.startswith('mtf-'))
            d['hermes_sources']   = sorted(s for s in all_srcs if not s.startswith('mtf-'))
        if d.get('db_sources'):
            d['has_openclaw'] = 'openclaw' in d['db_sources']
            d['has_hermes']   = 'hermes'   in d['db_sources']
        results.append(d)
    conn.close()
    return sorted(results, key=lambda x: x['final_confidence'], reverse=True)


def add_confluence_signal(token, direction, confidence, num_signals, price, z_score=None, rsi_14=None, macd_hist=None):
    """Add a confluence signal (when ≥2 indicator signals agree on same token+direction).
    Confidence is pre-boosted by caller (1.25x for 2 signals, 1.5x for 3+)."""
    return add_signal(
        token=token.upper(), direction=direction.upper(),
        signal_type='confluence',
        source=f'conf-{num_signals}s',
        confidence=confidence,
        value=confidence,
        price=price,
        exchange='hyperliquid',
        timeframe='multi',
        z_score=z_score,
        rsi_14=rsi_14,
        macd_hist=macd_hist,
    )

def update_signal_decision(token, direction, decision, reason=None):
    conn = _get_conn(_runtime())
    c = conn.cursor()
    c.execute('''
        UPDATE signals
        SET decision=?, executed=CASE WHEN ?='EXECUTED' THEN 1 ELSE executed END,
            updated_at=CURRENT_TIMESTAMP
        WHERE token=? AND direction=? AND decision IN ('PENDING', 'APPROVED')
        AND executed=0
    ''', (decision, decision, token.upper(), direction.upper()))
    conn.commit()
    count = c.rowcount
    conn.close()
    return count

def mark_signal_executed(token, direction):
    return update_signal_decision(token, direction, 'EXECUTED')

def approve_signal(token, direction, leverage=None):
    conn = _get_conn(_runtime())
    c = conn.cursor()
    try:
        if leverage is not None:
            c.execute("""
                UPDATE signals SET decision='APPROVED', leverage=?
                WHERE token=? AND direction=? AND decision='PENDING'
            """, (leverage, token.upper(), direction.upper()))
        else:
            c.execute("""
                UPDATE signals SET decision='APPROVED'
                WHERE token=? AND direction=? AND decision='PENDING'
            """, (token.upper(), direction.upper()))
        conn.commit()
        return True
    finally:
        conn.close()

def get_approved_signals(hours=24):
    """
    Get approved signals for execution.

    Quality scoring:
    - Base: max confidence (not avg — avoids low-confidence noise dragging down strong signals)
    - Diversity bonus: +5% per distinct signal_type present (max +20%)
    - Only consider individual signals >= 25% confidence
    - Hot-set bonus: signals with compact_rounds > 0 get +10% base (proven by market)
    """
    conn = _get_conn(_runtime(), row_factory=True)
    c = conn.cursor()

    # Attach OpenClaw DB for hot-set compact_rounds lookup
    if os.path.exists(LEGACY_DB):
        try:
            c.execute(f"ATTACH DATABASE ? AS oc", (LEGACY_DB,))
        except sqlite3.IntegrityError:
            pass  # Already attached — safe to ignore
        except sqlite3.OperationalError as e:
            if "already exists" not in str(e):
                print(f"WARNING: Could not attach {LEGACY_DB}: {e}")
        except Exception as e:
            print(f"WARNING: Unexpected error attaching {LEGACY_DB}: {e}")

    c.execute('''
        SELECT token, direction,
               COUNT(*) as count,
               AVG(confidence) as avg_conf,
               MAX(confidence) as max_conf,
               MIN(confidence) as min_conf,
               GROUP_CONCAT(DISTINCT signal_type) as types,
               MAX(price) as price,
               MAX(leverage) as leverage,
               MAX(COALESCE(
                   (SELECT compact_rounds FROM signals s2
                    WHERE s2.token=signals.token
                      AND s2.direction = signals.direction
                      AND s2.decision = 'APPROVED'
                      AND s2.executed = 0
                    ORDER BY compact_rounds DESC LIMIT 1), 0
               )) as hot_rounds,
               MAX(COALESCE(
                   (SELECT learned_sl_multiplier FROM signals s3
                    WHERE s3.token=signals.token
                      AND s3.direction = signals.direction
                      AND s3.decision = 'APPROVED'
                      AND s3.executed = 0
                    ORDER BY created_at DESC LIMIT 1), 1.0
               )) as learned_sl_multiplier
        FROM signals
        WHERE decision='APPROVED' AND executed=0
          AND created_at > datetime('now','-'||?||' hours')
          AND confidence >= 25   -- filter noise
        GROUP BY token, direction
        ORDER BY count DESC, max_conf DESC
    ''', (hours,))

    results = []
    for r in c.fetchall():
        d = dict(r)
        types = d.get('types', '').split(',') if d.get('types') else []
        # Filter types (remove empty strings)
        types = [t for t in types if t]
        num_types = len(types)

        # Quality base: weight strongest signals more
        # penalize if min_conf is very low compared to max
        min_c = d.get('min_conf', 0) or 0
        max_c = d.get('max_conf', 0) or 0
        range_ratio = (max_c - min_c) / max_c if max_c > 0 else 0

        # Base score = weighted average favoring higher confs
        # (simple avg penalized if range_ratio is high)
        quality_penalty = range_ratio * 0.3  # up to 30% penalty for mixed quality
        base = d.get('avg_conf', 0) * (1 - quality_penalty)

        # Diversity bonus: distinct strong types add signal
        diversity_bonus = min(20, num_types * 5)

        # Hot-set bonus: signals proven by market cycles
        hot_rounds = d.get('hot_rounds', 0) or 0
        hot_bonus = min(20, hot_rounds * 5)

        final_conf = min(99, base + diversity_bonus + hot_bonus)
        d['final_confidence'] = round(final_conf, 1)
        d['signal_types'] = types
        d['hot_rounds'] = hot_rounds
        results.append(d)

    conn.close()
    return sorted(results, key=lambda x: x['final_confidence'], reverse=True)

def mark_signal_processed(token, decision, signal_ids=None):
    """
    Mark signals as processed.

    Args:
        token: token symbol
        decision: APPROVED, SKIPPED, FAILED, EXPIRED, WAIT
        signal_ids: optional list of specific signal IDs to update.
                    If None, updates ALL PENDING signals for token (legacy behavior).
                    IMPORTANT: always include direction for safety.
    """
    conn = _get_conn(_runtime())
    c = conn.cursor()
    try:
        tok = token.upper()
        if signal_ids:
            # Targeted update: only specific IDs
            placeholders = ','.join(['?' for _ in signal_ids])
            if decision == 'APPROVED':
                c.execute(f'''
                    UPDATE signals
                    SET decision=?, executed=0, updated_at=CURRENT_TIMESTAMP
                    WHERE id IN ({placeholders}) AND executed IN (0, 1)
                ''', (decision,) + tuple(signal_ids))
            else:
                c.execute(f'''
                    UPDATE signals
                    SET decision=?, executed=1, updated_at=CURRENT_TIMESTAMP
                    WHERE id IN ({placeholders}) AND executed IN (0, 1)
                ''', (decision,) + tuple(signal_ids))
        else:
            # Legacy: update ALL PENDING for token (use with caution)
            if decision == 'APPROVED':
                c.execute('''
                    UPDATE signals
                    SET decision=?, executed=0, updated_at=CURRENT_TIMESTAMP
                    WHERE token=? AND executed IN (0, 1)
                ''', (decision, tok))
            else:
                c.execute('''
                    UPDATE signals
                    SET decision=?, executed=1, updated_at=CURRENT_TIMESTAMP
                    WHERE token=? AND executed IN (0, 1)
                ''', (decision, tok))
        conn.commit()
        return c.rowcount
    except Exception as e:
        conn.rollback()
        return 0
    finally:
        conn.close()


def cleanup_stale_approved(hours=1):
    """
    Mark APPROVED-but-not-executed signals as EXPIRED if older than `hours`.
    Prevents stale approvals from polluting get_approved_signals and wasting slots.
    Returns count of expired signals.
    """
    conn = _get_conn(_runtime())
    c = conn.cursor()
    try:
        c.execute('''
            UPDATE signals
            SET decision='EXPIRED', executed=1, updated_at=CURRENT_TIMESTAMP
            WHERE decision='APPROVED'
              AND executed=0
              AND created_at <= datetime('now', '-'||?||' hours')
        ''', (hours,))
        conn.commit()
        expired = c.rowcount
        return expired
    except Exception:
        conn.rollback()
        return 0
    finally:
        conn.close()


# ── Price History & Indicators (static DB) ────────────────────────────────────
def get_price_history(token, lookback_minutes=60*24):
    conn = _get_conn(_static())
    c = conn.cursor()
    cutoff = int(time.time()) - (lookback_minutes * 60)
    c.execute('''
        SELECT timestamp, price FROM price_history
        WHERE token=? AND timestamp>?
        ORDER BY timestamp ASC
        LIMIT 2000
    ''', (token.upper(), cutoff))
    rows = c.fetchall()
    conn.close()
    return rows

def get_latest_price(token):
    conn = _get_conn(_static())
    c = conn.cursor()
    c.execute('SELECT price FROM latest_prices WHERE token=?', (token.upper(),))
    row = c.fetchone()
    conn.close()
    return row[0] if row else None

def get_all_latest_prices():
    conn = _get_conn(_static())
    c = conn.cursor()
    c.execute('SELECT token, price FROM latest_prices')
    rows = c.fetchall()
    conn.close()
    return {r[0]: {'price': r[1]} for r in rows}

def compute_rsi(token, period=14, lookback_minutes=60*24):
    rows = get_price_history(token, lookback_minutes)
    if len(rows) < period + 2:
        return None
    closes = [r[1] for r in rows]
    deltas = [closes[i+1] - closes[i] for i in range(len(closes)-1)]
    gains  = [d if d > 0 else 0 for d in deltas]
    losses = [-d if d < 0 else 0 for d in deltas]
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    for i in range(period, len(deltas)):
        avg_gain = (avg_gain * (period-1) + gains[i]) / period
        avg_loss = (avg_loss * (period-1) + losses[i]) / period
    if avg_loss == 0:
        return 100.0
    return round(100 - (100 / (1 + avg_gain / avg_loss)), 2)

def compute_zscore(token, lookback_minutes=60*4):
    rows = get_price_history(token, lookback_minutes)
    if len(rows) < 20:
        return None
    prices = [r[1] for r in rows]
    import statistics
    mean = statistics.mean(prices)
    stdev = statistics.stdev(prices)
    if stdev == 0:
        return None
    return round((prices[-1] - mean) / stdev, 3)

def compute_macd(token, fast=12, slow=26, signal=9, lookback_minutes=60*24):
    rows = get_price_history(token, lookback_minutes)
    if len(rows) < slow + signal:
        return None
    closes = [r[1] for r in rows]

    def ema(data, period):
        if len(data) < period:
            return None
        k = 2 / (period + 1)
        ema_val = sum(data[:period]) / period
        for price in data[period:]:
            ema_val = price * k + ema_val * (1 - k)
        return ema_val

    ef = ema(closes, fast)
    es = ema(closes, slow)
    if ef is None or es is None:
        return None
    macd_line = ef - es
    macd_vals = []
    for i in range(slow, len(closes)):
        efa = ema(closes[:i+1], fast)
        esa = ema(closes[:i+1], slow)
        if efa and esa:
            macd_vals.append(efa - esa)
    if len(macd_vals) < signal:
        return None
    sig = ema(macd_vals, signal)
    if sig is None:
        return None
    return {'macd': round(macd_line, 6), 'signal': round(sig, 6), 'histogram': round(macd_line - sig, 6)}

def compute_all_indicators(token):
    rsi  = compute_rsi(token)
    z    = compute_zscore(token)
    macd = compute_macd(token)
    price = get_latest_price(token)
    return {
        'token': token, 'price': price,
        'rsi_14': rsi, 'zscore': z,
        'macd': macd.get('macd') if macd else None,
        'macd_signal': macd.get('signal') if macd else None,
        'macd_histogram': macd.get('histogram') if macd else None,
    }

def get_rsi_signals_from_db(threshold_low=35, threshold_high=65, min_history_minutes=60*4):
    prices = get_all_latest_prices()
    signals = []
    for token, data in prices.items():
        if not data.get('price') or data['price'] <= 0:
            continue
        rsi = compute_rsi(token, lookback_minutes=min_history_minutes)
        if rsi and rsi < threshold_low:
            signals.append({
                'token': token, 'direction': 'LONG', 'signal_type': 'rsi',
                'source': 'rsi-local', 'confidence': min(85, 70+(threshold_low-rsi)*1.5),
                'value': rsi, 'price': data['price']})
        elif rsi and rsi > threshold_high:
            signals.append({
                'token': token, 'direction': 'SHORT', 'signal_type': 'rsi',
                'source': 'rsi-local', 'confidence': min(85, 70+(rsi-threshold_high)*1.5),
                'value': rsi, 'price': data['price']})
    return signals

def get_zscore_signals_from_db(z_threshold=2.0, min_history_minutes=60*4):
    prices = get_all_latest_prices()
    signals = []
    for token, data in prices.items():
        if not data.get('price') or data['price'] <= 0:
            continue
        z = compute_zscore(token, lookback_minutes=min_history_minutes)
        if z is not None and abs(z) >= z_threshold:
            direction = 'SHORT' if z > 0 else 'LONG'
            signals.append({
                'token': token, 'direction': direction, 'signal_type': 'zscore',
                'source': 'zscore-local', 'confidence': min(88, 65+abs(z)*8),
                'value': z, 'price': data['price']})
    return signals

def get_macd_signals_from_db(min_history_minutes=60*24):
    prices = get_all_latest_prices()
    signals = []
    for token, data in prices.items():
        if not data.get('price') or data['price'] <= 0:
            continue
        macd = compute_macd(token, lookback_minutes=min_history_minutes)
        if macd:
            h = macd['histogram']
            direction = 'LONG' if h > 0 else 'SHORT'
            signals.append({
                'token': token, 'direction': direction, 'signal_type': 'macd',
                'source': 'macd-local', 'confidence': min(82, 65+abs(h)*200),
                'value': h, 'price': data['price']})
    return signals

def price_age_minutes(token):
    conn = _get_conn(_static())
    c = conn.cursor()
    c.execute('SELECT updated_at FROM latest_prices WHERE token=?', (token.upper(),))
    row = c.fetchone()
    conn.close()
    if not row:
        return 999
    try:
        return (time.time() - row[0]) / 60
    except:
        return 999

# ── Cooldowns ─────────────────────────────────────────────────────────────────
COOLDOWN_FILE = '/root/.openclaw/workspace/data/signal-cooldowns.json'

def get_cooldown(token, direction=None):
    # Primary: PostgreSQL (durable). Fallback: JSON file.
    key = token.upper()
    if direction:
        key = "%s:%s" % (key, direction.upper())
    try:
        conn = psycopg2.connect(host='/var/run/postgresql', dbname='brain', user='postgres', password='***')
        cur = conn.cursor()
        cur.execute(
            "SELECT expires_at FROM signal_cooldowns WHERE token=%s AND expires_at > NOW()",
            (key,))
        row = cur.fetchone()
        conn.close()
        if row:
            return True
    except Exception:
        pass
    # Fallback: JSON file
    try:
        with open(COOLDOWN_FILE) as f:
            data = json.load(f)
        if key in data and data[key] > time.time():
            return data[key]
    except:
        pass
    return None

def set_cooldown(token, direction=None, hours=1):
    # Primary: PostgreSQL (durable). Fallback: JSON file.
    key = token.upper()
    if direction:
        key = "%s:%s" % (key, direction.upper())
    expires = datetime.now() + timedelta(hours=hours)
    try:
        conn = psycopg2.connect(host='/var/run/postgresql', dbname='brain', user='postgres', password='postgres')
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO signal_cooldowns (token, expires_at, reason, direction) "
            "VALUES (%s, %s, 'signal', %s) "
            "ON CONFLICT (token, direction) DO UPDATE SET expires_at = %s",
            (key, expires, direction, expires))
        conn.commit()
        conn.close()
        return
    except Exception as e:
        print(f"[signal_schema] set_cooldown PostgreSQL failed: {e} — falling back to JSON file")
    # Fallback: JSON file
    try:
        try:
            with open(COOLDOWN_FILE) as f:
                data = json.load(f)
        except:
            data = {}
        data[key] = time.time() + (hours * 3600)
        with open(COOLDOWN_FILE, 'w') as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f'[signal_schema] set_cooldown fallback (JSON) failed: {e} — cooldown may not persist')

def clear_cooldown(token, direction=None):
    try:
        with open(COOLDOWN_FILE) as f:
            data = json.load(f)
        key = token.upper()
        if direction:
            key = f"{key}:{direction.upper()}"
        data.pop(key, None)
        with open(COOLDOWN_FILE, 'w') as f:
            json.dump(data, f)
    except: pass

# ── Legacy DB_PATH alias (for any scripts still referencing it) ───────────────
DB_PATH = RUNTIME_DB  # backwards compat alias

def get_db():
    return _get_conn(_runtime(), row_factory=True)
