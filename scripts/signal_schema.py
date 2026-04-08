#!/usr/bin/env python3
"""Signal Schema - Dual-database architecture for Hermes trading system.

STATIC DB  (/root/.hermes/data/signals_hermes.db)   — backfill data, git-tracked
RUNTIME DB (/root/.hermes/data/signals_hermes_runtime.db) — signals, decisions, local state
"""
import sys
import sqlite3, time, json, os
from datetime import datetime, timedelta
import psycopg2
sys.path.insert(0, '/root/.hermes/scripts')
from _secrets import BRAIN_DB_DICT

# ── Database paths ────────────────────────────────────────────────────────────
HERMES_DATA = os.environ.get('HERMES_DATA_DIR', '/root/.hermes/data')
STATIC_DB   = os.path.join(HERMES_DATA, 'signals_hermes.db')
RUNTIME_DB  = os.path.join(HERMES_DATA, 'signals_hermes_runtime.db')

# Legacy path (deprecated — kept for migration reference only)
LEGACY_DB   = '/root/.openclaw/workspace/data/signals.db'  # noqa: F841

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
_migration_done = False

def _was_migration_done():
    """Check if legacy migration has already run (idempotent — safe to call on every init_db)."""
    try:
        sc = _get_conn(STATIC_DB)
        sc.execute("""
            CREATE TABLE IF NOT EXISTS _meta (key TEXT PRIMARY KEY, val TEXT)
        """)
        row = sc.execute("SELECT val FROM _meta WHERE key='migration_done'").fetchone()
        sc.close()
        return row is not None
    except Exception:
        return False

def _mark_migration_done():
    """Persist that legacy migration has completed."""
    try:
        sc = _get_conn(STATIC_DB)
        sc.execute("INSERT OR REPLACE INTO _meta VALUES ('migration_done','1')")
        sc.commit()
        sc.close()
    except Exception:
        pass

def init_db():
    """Initialize both static and runtime DBs with proper schemas."""
    global _init_done, _migration_done
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
    sc.execute("""
        CREATE TABLE IF NOT EXISTS ohlcv_1m (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            token TEXT NOT NULL,
            open_time INTEGER NOT NULL,
            open REAL NOT NULL,
            high REAL NOT NULL,
            low REAL NOT NULL,
            close REAL NOT NULL,
            volume REAL NOT NULL,
            close_time INTEGER NOT NULL,
            updated_at INTEGER NOT NULL,
            UNIQUE(token, open_time)
        )""")
    sc.execute('CREATE INDEX IF NOT EXISTS idx_ohlcv_token_time ON ohlcv_1m(token, open_time)')
    sc.execute('CREATE INDEX IF NOT EXISTS idx_ohlcv_ts ON ohlcv_1m(open_time)')
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
    try:
        rc.execute("ALTER TABLE signals ADD COLUMN review_count INTEGER DEFAULT 0")
    except Exception:
        pass  # column may already exist
    try:
        rc.execute("ALTER TABLE signals ADD COLUMN rejected_at TEXT")
    except Exception:
        pass  # column may already exist
    try:
        rc.execute("ALTER TABLE signals ADD COLUMN rejection_reason TEXT")
    except Exception:
        pass  # column may already exist
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
    rc.execute("CREATE INDEX IF NOT EXISTS idx_sighist_token ON signal_history(token, direction)")
    rc.execute("CREATE INDEX IF NOT EXISTS idx_sh_round ON signal_history(compact_round)")

    # ── Token Speeds (speed_tracker.py persistence) ───────────────────────────
    # Updated every pipeline run from speed_tracker.py
    # Used by position_manager, decider-run, ai_decider, and signal_gen
    rc.execute("""
        CREATE TABLE IF NOT EXISTS token_speeds (
            token TEXT PRIMARY KEY,
            price_velocity_5m REAL DEFAULT 0,
            price_velocity_15m REAL DEFAULT 0,
            price_acceleration REAL DEFAULT 0,
            speed_percentile REAL DEFAULT 50,
            is_stale INTEGER DEFAULT 0,
            last_move_at TEXT,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    rc.execute("CREATE INDEX IF NOT EXISTS idx_tokspd_updated ON token_speeds(updated_at)")

    rc.commit()
    rc.close()
    # ── Migrate legacy backfill data to static DB (once, persisted) ──
    global _migration_done
    if _migration_done or _was_migration_done():
        _migration_done = True
    elif os.path.exists(LEGACY_DB) and os.path.getsize(LEGACY_DB) > 0:
        sc = _get_conn(STATIC_DB)
        leg = _get_conn(LEGACY_DB)
        lc = leg.cursor()
        # Guard: only migrate if LEGACY_DB actually has price_history table
        lc.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='price_history'")
        if not lc.fetchone():
            leg.close()
            sc.close()
        else:
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
        _migration_done = True
        _mark_migration_done()
    else:
        _migration_done = True
        _mark_migration_done()
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
    """Add a new signal. ONE row per token+direction (all signal_types merged).

    FIX (2026-04-05): Changed from merge-by-token+direction+signal_type to
    merge-by-token+direction. All signal_types for the same token+direction now
    consolidate into ONE row with:
    - signal_types column: comma-separated list of all contributing types
    - confidence: max of all contributing signals
    - source: comma-separated list of all sources
    - confluence bonus: +5% per distinct signal_type (max +20%)

    This eliminates duplicate rows and ensures one-row-per-token-direction from birth.

    MINIMUM CONFIDENCE FLOOR: Signals with confidence below 50 are silently rejected.
    The AI decider requires ≥50% confidence to execute. Individual signals below this
    threshold generate noise without ever reaching execution — they just create WAIT
    records. This floor prevents signal spam from low-quality indicators."""
    # ── Minimum confidence floor ─────────────────────────────────────────────
    MIN_CONFIDENCE_FLOOR = 50
    if confidence < MIN_CONFIDENCE_FLOOR:
        return None  # Silently skip low-confidence signals

    # ── HOTSET_BLOCKLIST guard — block at source ───────────────────────────
    # Import lazily to avoid circular deps
    try:
        from hermes_constants import HOTSET_BLOCKLIST
        if token.upper() in HOTSET_BLOCKLIST:
            return None  # Silently skip blocklisted tokens
    except ImportError:
        pass  # hermes_constants may not be available in all contexts
    # ─────────────────────────────────────────────────────────────────────────
    conn = _get_conn(_runtime())
    c = conn.cursor()
    try:
        token = token.upper()
        direction = direction.upper()

        # ── CONFLICT GUARD ─────────────────────────────────────────────────────
        # Before writing any new signal, expire any OPPOSITE-direction signals
        # for this token (both PENDING and APPROVED). This prevents a new signal
        # from creating an opposite direction that survives alongside the existing one.
        opp_dir = 'SHORT' if direction == 'LONG' else 'LONG'
        c.execute('''
            UPDATE signals
            SET decision='EXPIRED', executed=1, updated_at=CURRENT_TIMESTAMP
            WHERE token=? AND direction=? AND executed=0
              AND decision IN ('PENDING', 'APPROVED')
              AND created_at > datetime('now', '-3 hours')
        ''', (token, opp_dir))
        if c.rowcount > 0:
            print(f'  🗑️ [CONFLICT-GUARD] expired {c.rowcount} {opp_dir} signals for {token} (new: {direction})')

        # ── MERGE by token+direction (not token+direction+signal_type) ─────────
        # Check for existing PENDING signal for same token+direction in last 30 min
        c.execute('''
            SELECT id, source, signal_types, confidence,
                   z_score, z_score_tier, rsi_14, macd_value, macd_signal, macd_hist
            FROM signals
            WHERE token=? AND direction=? AND executed=0 AND decision='PENDING'
              AND created_at > datetime('now', '-30 minutes')
            LIMIT 1
        ''', (token, direction))
        existing = c.fetchone()
        if existing:
            sig_id, existing_source, existing_types, existing_conf = existing[0], existing[1], existing[2], existing[3]
            existing_z = existing[4]; existing_z_tier = existing[5]
            existing_rsi = existing[6]; existing_macd = existing[7]
            existing_sig = existing[8]; existing_hist = existing[9]

            # Build merged sources
            old_srcs = set(existing_source.split(',')) if existing_source else set()
            new_srcs = set(source.split(',')) if source else set()
            all_srcs = old_srcs | new_srcs
            merged_sources = ','.join(sorted(all_srcs))

            # Build merged signal_types
            old_types = set(existing_types.split(',')) if existing_types else set()
            new_types = {signal_type}
            all_types = old_types | new_types
            merged_types = ','.join(sorted(all_types))
            num_types = len(all_types)

            num_srcs_gained = len(new_srcs - old_srcs)

            if confidence < existing_conf:
                decay = (existing_conf - confidence) * 0.4
                new_conf = max(existing_conf - decay + (num_srcs_gained * 1.0), min(existing_conf, confidence))
                new_conf = max(1, min(99, new_conf))
            else:
                new_conf = max(existing_conf, confidence)
                if num_srcs_gained > 0:
                    new_conf = min(100, new_conf + min(num_srcs_gained, 2))
                # Confluence bonus: +5% per new distinct signal_type
                if num_types > 1:
                    new_conf = min(100, new_conf + min(5 * num_types, 20))

            # Keep most recent indicator values (update to latest)
            c.execute('''
                UPDATE signals SET
                    confidence=?, source=?, signal_types=?,
                    z_score=?, z_score_tier=?, rsi_14=?,
                    macd_value=?, macd_signal=?, macd_hist=?,
                    updated_at=CURRENT_TIMESTAMP
                WHERE id=?
            ''', (new_conf, merged_sources, merged_types,
                  z_score, z_score_tier, rsi_14,
                  macd_value, macd_signal, macd_hist,
                  sig_id))
            conn.commit()
            conn.close()
            return sig_id

        # No existing — insert new
        # Reset hot_cycle_count so a new signal doesn't inherit stuck signal's history
        c.execute("""
            UPDATE signals
            SET hot_cycle_count = 0
            WHERE token=? AND direction=?
              AND decision IN ('PENDING', 'APPROVED', 'WAIT')
              AND executed = 0
        """, (token, direction))

        c.execute('''
            INSERT INTO signals
            (token, direction, signal_type, source, signal_types, confidence, value, price,
             exchange, timeframe, z_score, z_score_tier, momentum_state,
             rsi_14, macd_value, macd_signal, macd_hist, decision, executed, leverage,
             hot_cycle_count, counter_detected)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'PENDING', 0, ?, 0, 0)
        ''', (token, direction, signal_type, source, signal_type,
              confidence, value, price, exchange, timeframe,
              z_score, z_score_tier, momentum_state,
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

def expire_pending_signals(minutes=60):
    """Expire stale PENDING and APPROVED signals. Called every signal_gen run
    to prevent the queue from accumulating stale signals.

    PENDING: cleared if older than 60 minutes — new signals will regenerate if conditions persist.

    APPROVED: cleared if older than 30 minutes AND not executed.
    This is critical: auto-approved signals (from confluence ≥90% or hot-set r1)
    accumulate when positions are full. After 30 minutes without execution, they're
    blocking hot-set signals from auto-approving for the same token. Stale APPROVED
    entries need to be released so fresh signals can take their place.

    FIX (2026-04-02): Added APPROVED expiry. Previously 476 APPROVED signals were
    stuck in queue, blocking hot-set overrides for MINA/BIO/SUSHI/TURBO. Also changed
    PENDING from 15min to 60min to allow review_count to accumulate for hot-set."""
    conn = _get_conn(_runtime())
    c = conn.cursor()

    # Expire stale PENDING signals
    # FIX (2026-04-03): NEVER expire signals that survived ai_decider compaction (rc>=1).
    # Signals with review_count>=1 or compact_rounds>=1 are protected from time-based expiry.
    # They survive via ai_decider's compaction discipline and are only expired when
    # compact_rounds >= 20 (forced expire by ai_decider compaction logic).
    c.execute("""
        UPDATE signals
        SET decision = 'EXPIRED'
        WHERE decision = 'PENDING'
          AND created_at < datetime('now', ?)
          AND executed = 0
          AND (review_count IS NULL OR review_count = 0)
          AND (compact_rounds IS NULL OR compact_rounds = 0)
    """, (f'-{minutes} minutes',))
    pending_expired = c.rowcount

    # Expire stale APPROVED signals (not executed, too old)
    # These block hot-set signals from auto-approving for the same token.
    # FIX (2026-04-02): Was updated_at — touched on every read, never expired.
    # Now uses created_at so APPROVED signals clear 30 min after approval.
    c.execute("""
        UPDATE signals
        SET decision = 'EXPIRED', executed = 1
        WHERE decision = 'APPROVED'
          AND executed = 0
          AND created_at < datetime('now', '-30 minutes')
    """)
    approved_expired = c.rowcount

    conn.commit()
    c.close()
    total_expired = pending_expired + approved_expired
    if total_expired > 0:
        print(f'  [Signal Expiry] Cleared {pending_expired} PENDING + {approved_expired} APPROVED ({minutes}min PENDING / 30min APPROVED)')
    return total_expired


def get_confluence_signals(hours=24, min_signals=2, signal_types=None):
    """Return tokens where ≥min_signals PENDING signal types agree (Hermes-only).
    Used by ai_decider / decider-run. Boosts confidence by 1.25x (2 signals)
    or 1.5x (3+ signals).

    FIX (2026-04-05): After the add_signal merge-by-token+direction fix,
    PENDING rows are now ONE per token+direction with all signal_types in the
    signal_types column. This function detects that and uses the column directly.
    Legacy rows (NULL signal_types) fall back to GROUP BY COUNT approach."""
    conn = _get_conn(_runtime(), row_factory=True)
    c = conn.cursor()

    st_list = list(signal_types) if signal_types else []

    # New approach (2026-04-05+): signal_types column is pre-populated by add_signal.
    # Count types by splitting the comma-separated signal_types column.
    # SQLite: use xml_table trick or simple string manipulation.
    # Safer: use a subquery that counts commas + 1.
    new_query = f"""
        SELECT
            token, direction,
            signal_types,
            -- Count types in signal_types column: number of commas + 1
            (LENGTH(signal_types) - LENGTH(REPLACE(signal_types, ',', '')) + 1) as num_types,
            confidence as avg_conf,
            confidence as max_conf,
            signal_type as types,       -- legacy compat: single type
            source as all_sources,
            price,
            z_score,
            rsi_14,
            1 as use_merged
        FROM signals
        WHERE decision='PENDING'
          AND signal_types IS NOT NULL AND signal_types != ''
          AND created_at > datetime('now','-'||?||' hours')
    """
    # Legacy approach: GROUP BY for rows without signal_types
    legacy_select = f"""
        SELECT token, direction,
               COUNT(DISTINCT signal_type) as num_types,
               COUNT(*) as total_rows,
               AVG(confidence) as avg_conf,
               MAX(confidence) as max_conf,
               GROUP_CONCAT(DISTINCT signal_type) as types,
               GROUP_CONCAT(DISTINCT source) as all_sources,
               MAX(price) as price,
               MAX(z_score) as z_score,
               MAX(rsi_14) as rsi_14,
               0 as use_merged
        FROM signals
        WHERE decision='PENDING'
          AND (signal_types IS NULL OR signal_types = '')
          AND created_at > datetime('now','-'||?||' hours')
        GROUP BY token, direction
    """

    params = (hours,) + tuple(st_list) if st_list else (hours,)
    legacy_params = params

    if st_list:
        st_placeholder = " AND signal_type IN (" + ",".join(["?" for _ in st_list]) + ")"
        new_query += st_placeholder
        legacy_select += st_placeholder
        params = (hours,) + tuple(st_list)
        legacy_params = params

    new_query += f"\nUNION ALL\n{legacy_select}"

    try:
        c.execute(new_query, params + legacy_params)
        results_raw = c.fetchall()
    except Exception as e:
        # Fallback: legacy GROUP BY only
        conn.close()
        return _get_confluence_signals_legacy(hours, min_signals, signal_types)

    results = []
    for r in c.fetchall():
        d = dict(r)
        num_types = d.get('num_types', 1) or 1
        mult = 1.5 if num_types >= 3 else 1.25 if num_types == 2 else 1.0
        avg_conf = d.get('avg_conf', 0) or 0
        d['final_confidence'] = min(99, avg_conf * mult)
        d['num_agreeing'] = num_types
        # Parse signal_types from column
        st_col = d.get('signal_types', '')
        if st_col:
            d['signal_types_list'] = [t.strip() for t in st_col.split(',') if t.strip()]
            d['signal_types'] = d['signal_types_list']
        else:
            types_str = d.get('types', '')
            d['signal_types'] = types_str.split(',') if types_str else []
        # Legacy compat
        all_srcs = d.get('all_sources', '')
        if all_srcs:
            d['hermes_sources'] = sorted(all_srcs.split(','))
        top_source = all_srcs.split(',')[0] if all_srcs else ''
        d['source'] = validate_source(top_source) if top_source else 'unknown'
        if num_types >= min_signals:
            results.append(d)

    conn.close()
    return sorted(results, key=lambda x: x['final_confidence'], reverse=True)


def _get_confluence_signals_legacy(hours=24, min_signals=2, signal_types=None):
    """Fallback for legacy rows without signal_types column populated."""
    conn = _get_conn(_runtime(), row_factory=True)
    c = conn.cursor()
    st_list = list(signal_types) if signal_types else []
    hermes_select = """
        SELECT token, direction, signal_type, source, confidence, price,
               z_score, rsi_14, macd_hist
        FROM signals
        WHERE decision='PENDING'
          AND (signal_types IS NULL OR signal_types = '')
          AND created_at > datetime('now','-'||?||' hours')
    """
    if st_list:
        hermes_select += " AND signal_type IN (" + ",".join(["?" for _ in st_list]) + ")"
    params = (hours,) + tuple(st_list) if st_list else (hours,)
    query = f"""
        WITH all_signals AS ({hermes_select})
        SELECT token, direction,
               COUNT(DISTINCT signal_type) as num_types,
               COUNT(*) as total_rows,
               AVG(confidence) as avg_conf,
               MAX(confidence) as max_conf,
               GROUP_CONCAT(DISTINCT signal_type) as types,
               GROUP_CONCAT(DISTINCT source) as all_sources,
               MAX(price) as price,
               MAX(z_score) as z_score,
               MAX(rsi_14) as rsi_14
        FROM all_signals
        GROUP BY token, direction
        HAVING COUNT(DISTINCT signal_type) >= ?
        ORDER BY avg_conf DESC
    """
    c.execute(query, params + (min_signals,))
    results = []
    for r in c.fetchall():
        d = dict(r)
        mult = 1.5 if d['num_types'] >= 3 else 1.25 if d['num_types'] == 2 else 1.0
        d['final_confidence'] = min(99, d['avg_conf'] * mult)
        d['num_agreeing'] = d['num_types']
        if d.get('types'):
            d['signal_types'] = d['types'].split(',')
        if d.get('all_sources'):
            d['hermes_sources'] = sorted(d['all_sources'].split(','))
        top_source = d.get('all_sources', '').split(',')[0] if d.get('all_sources') else ''
        d['source'] = validate_source(top_source) if top_source else 'unknown'
        results.append(d)
    conn.close()
    return sorted(results, key=lambda x: x['final_confidence'], reverse=True)


def add_confluence_signal(token, direction, confidence, num_signals, price, z_score=None, rsi_14=None, macd_hist=None):
    """Add a confluence signal (when ≥2 indicator signals agree on same token+direction).
    Confidence is pre-boosted by caller (1.25x for 2 signals, 1.5x for 3+)."""
    # FIX (2026-04-05): Defensive block — conf-1s is not confluence. Single-source
    # signals should use their own signal type (hmacd-, counter-), not confluence.
    if num_signals < 2:
        print(f"[add_confluence_signal] REJECTED {token} {direction} conf-{num_signals}s — requires ≥2 signals")
        return None
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

# BUG-26 fix: approved source whitelist — prevents malformed source fields
# from routing to unintended A/B variants in get_ab_params().
ALLOWED_SIGNAL_SOURCES = frozenset({
    # Confluence sources
    'conf-1s', 'conf-2s', 'conf-3s', 'conf-4s', 'conf-5s',
    'fallback-conf-2s', 'fallback-conf-3s', 'fallback-conf-4s', 'fallback-conf-5s',
    # Indicator sources
    'rsi-local', 'rsi-confluence', 'macd-local', 'macd-confluence',
    'momentum', 'momentum-mtf', 'zscore-local', 'zscore-confluence',
    # Multi-timeframe
    'mtf-rsi', 'mtf-macd', 'mtf-momentum',
    # FIX (2026-04-05): Add hmacd sources — these are valid indicator sources used by
    # hot-set auto-approval. Without these, all hot-set signals are blocked as 'unknown'.
    # The hmacd-* sources come from merged signals where source='hmacd-,hzscore,...'
    # (comma-separated list of sources). The individual components are valid signals.
    'hmacd-', 'hmacd-mtf_macd', 'hmacd-mtf_zscore', 'hmacd-default',
    'hzscore', 'pct-hermes', 'vel-hermes', 'rsi-hermes',
    'counter-hermes', 'counter-mtf_macd', 'counter-mtf_zscore',
    # Merged indicator sources (comma-separated from GROUP_CONCAT)
    'hmacd-,hzscore', 'hmacd-,hzscore,pct-hermes', 'hmacd-,hzscore,vel-hermes',
    'hmacd-,pct-hermes', 'hmacd-,vel-hermes',
    'hzscore,pct-hermes', 'hzscore,vel-hermes',
    'mtf_macd,hzscore', 'mtf_macd,pct-hermes',
    'rsi-confluence,hzscore', 'rsi-confluence,pct-hermes',
    # Standard signal types used throughout the system
    'mtf_macd', 'mtf_zscore', 'mtf_rsi', 'mtf_momentum',
    'percentile_rank', 'velocity', 'rsi_local', 'macd_local',
    'macd_crossover', 'rsi_confluence', 'macd_confluence', 'zscore_confluence',
    # Pump modes
    'pump-momentum', 'pump-rsi', 'pump-confluence',
    # Legacy
    'hot-set', 'ai-decider', 'r1', 'r2', 'r3',
})


def validate_source(source: str) -> str:
    """
    BUG-12 fix: Validate source against whitelist.
    Returns the original source if valid, 'unknown' if not.
    Prevents malformed signals from routing to unintended A/B variants.

    FIX: Also handles merged indicator sources (comma-separated) like 'hmacd-,hzscore,pct-hermes'.
    Validates each component against the whitelist or accepts hmacd-* prefix patterns.
    """
    if not source:
        return 'unknown'
    if source in ALLOWED_SIGNAL_SOURCES:
        return source
    # Handle merged indicator sources (comma-separated list of indicators)
    if ',' in source:
        components = [c.strip() for c in source.split(',') if c.strip()]
        # All components must be valid individually
        for comp in components:
            if comp not in ALLOWED_SIGNAL_SOURCES:
                # Allow hmacd-* style prefixes as valid merged components
                if not any(comp.startswith(prefix) for prefix in
                           ['hmacd-', 'mtf_', 'counter-', 'pct-', 'vel-', 'rsi-', 'hzscore']):
                    return 'unknown'
        return source  # Valid merged source
    return 'unknown'


def update_signal_decision(token, direction, decision, reason=None, signal_id=None):
    """
    BUG-26 fix: Added optional signal_id parameter for atomic claim.

    When signal_id is provided, updates only that specific signal
    (UPDATE WHERE id=? AND executed=0) — prevents double-execution
    when multiple scripts run the same minute.

    When signal_id is None, falls back to legacy behavior:
    updates ALL matching token+direction signals (for backward compat).
    """
    conn = _get_conn(_runtime())
    c = conn.cursor()
    if signal_id is not None:
        # Atomic claim: only update the specific signal row
        c.execute('''
            UPDATE signals
            SET decision=?, executed=CASE WHEN ?='EXECUTED' THEN 1 ELSE executed END,
                updated_at=CURRENT_TIMESTAMP
            WHERE id=? AND executed=0
        ''', (decision, decision, signal_id))
    else:
        # Legacy: update all matching token+direction
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

def mark_signal_executed(token, direction, signal_id=None):
    """
    BUG-26 fix: accepts optional signal_id for atomic claim.
    When signal_id is provided, marks only that specific signal.
    """
    return update_signal_decision(token, direction, 'EXECUTED', signal_id=signal_id)

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

    # BUG-26 fix: select id so callers can do atomic claim with signal_id
    c.execute('''
        SELECT id, token, direction,
               COUNT(*) as count,
               AVG(confidence) as avg_conf,
               MAX(confidence) as max_conf,
               MIN(confidence) as min_conf,
               GROUP_CONCAT(DISTINCT signal_type) as types,
               MAX(source) as source,
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
        # BUG-26 fix: extract id from result for atomic claim
        sig_id = d.pop('id', None)
        # FIX: source field from MAX(source) aggregation — needed by decider-run
        # to route merged indicator signals (e.g. 'hmacd-,hzscore') to brain.py
        d['source'] = d.get('source', None)
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
        d['signal_id'] = sig_id  # BUG-26: pass to decider for atomic claim
        results.append(d)

    conn.close()
    return sorted(results, key=lambda x: x['final_confidence'], reverse=True)

def mark_signal_processed(token, decision, signal_ids=None, decision_reason=None):
    """
    Mark signals as processed with optional reason.

    Args:
        token: token symbol
        decision: APPROVED, SKIPPED, FAILED, EXPIRED, WAIT
        signal_ids: optional list of specific signal IDs to update.
                    If None, updates ALL PENDING signals for token (legacy behavior).
        decision_reason: optional human-readable reason string. ALWAYS pass this
                         so the decision audit trail is complete. The DB must never
                         have NULL reasons for SKIPPED/WAIT decisions.
    """
    conn = _get_conn(_runtime())
    c = conn.cursor()
    try:
        tok = token.upper()
        reason = decision_reason or f'processed-{decision.lower()}'
        increment_rc = decision in ('SKIPPED', 'WAIT')

        if signal_ids:
            # Targeted update: only specific IDs
            placeholders = ','.join(['?' for _ in signal_ids])
            params = (decision, reason) + tuple(signal_ids)
            if decision == 'APPROVED':
                c.execute(f'''
                    UPDATE signals
                    SET decision=?, decision_reason=?, executed=0, updated_at=CURRENT_TIMESTAMP
                    WHERE id IN ({placeholders}) AND executed IN (0, 1)
                ''', params)
            elif increment_rc:
                c.execute(f'''
                    UPDATE signals
                    SET decision=?, decision_reason=?, executed=1,
                        review_count = COALESCE(review_count, 0) + 1,
                        updated_at=CURRENT_TIMESTAMP
                    WHERE id IN ({placeholders}) AND executed IN (0, 1)
                ''', params)
            else:
                c.execute(f'''
                    UPDATE signals
                    SET decision=?, decision_reason=?, executed=1, updated_at=CURRENT_TIMESTAMP
                    WHERE id IN ({placeholders}) AND executed IN (0, 1)
                ''', params)
        else:
            # Legacy: update ALL PENDING for token (use with caution)
            params_approved = (decision, tok)
            params_other = (decision, reason, tok)
            if decision == 'APPROVED':
                c.execute('''
                    UPDATE signals
                    SET decision=?, executed=0, updated_at=CURRENT_TIMESTAMP
                    WHERE token=? AND executed IN (0, 1)
                ''', params_approved)
            elif increment_rc:
                c.execute('''
                    UPDATE signals
                    SET decision=?, decision_reason=?, executed=1,
                        review_count = COALESCE(review_count, 0) + 1,
                        updated_at=CURRENT_TIMESTAMP
                    WHERE token=? AND executed IN (0, 1)
                ''', params_other)
            else:
                c.execute('''
                    UPDATE signals
                    SET decision=?, decision_reason=?, executed=1, updated_at=CURRENT_TIMESTAMP
                    WHERE token=? AND executed IN (0, 1)
                ''', params_other)
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
COOLDOWN_FILE = '/root/.hermes/data/signal-cooldowns.json'

def get_cooldown(token, direction=None):
    # Primary: PostgreSQL (durable). Fallback: JSON file.
    key = token.upper()
    if direction:
        key = "%s:%s" % (key, direction.upper())
    try:
        conn = psycopg2.connect(**BRAIN_DB_DICT)
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
        conn = psycopg2.connect(**BRAIN_DB_DICT)
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

def update_signal_review_count(signal_id: int) -> None:
    """Increment review_count for a signal (used for hot set tracking)."""
    conn = _get_conn(_runtime())
    c = conn.cursor()
    try:
        c.execute(
            "UPDATE signals SET review_count = COALESCE(review_count, 0) + 1 WHERE id = ?",
            (signal_id,)
        )
        conn.commit()
    finally:
        conn.close()

# ── Trade Workflow State (PostgreSQL brain DB) ──────────────────────────────

WORKFLOW_STATES = ('IDLE', 'POSITION_OPEN', 'CLOSE_PENDING', 'ERROR_RECOVERY')


def update_trade_workflow_state(trade_id: int, state: str) -> bool:
    """
    Update the workflow_state column for a trade in the PostgreSQL brain DB.

    Valid states: IDLE | POSITION_OPEN | CLOSE_PENDING | ERROR_RECOVERY
    """
    if state not in WORKFLOW_STATES:
        print(f'[signal_schema] Invalid workflow_state: {state}')
        return False
    try:
        conn = psycopg2.connect(**BRAIN_DB_DICT)
        cur = conn.cursor()
        cur.execute("""
            UPDATE trades
            SET workflow_state = %s, workflow_updated_at = NOW()
            WHERE id = %s
        """, (state, trade_id))
        conn.commit()
        rows = cur.rowcount
        cur.close()
        conn.close()
        if rows == 0:
            print(f'[signal_schema] update_trade_workflow_state: trade {trade_id} not found')
            return False
        return True
    except Exception as e:
        print(f'[signal_schema] update_trade_workflow_state error: {e}')
        return False


def get_trade_workflow_state(trade_id: int) -> str | None:
    """Return the current workflow_state for a trade, or None if not found."""
    try:
        conn = psycopg2.connect(**BRAIN_DB_DICT)
        cur = conn.cursor()
        cur.execute("""
            SELECT workflow_state FROM trades WHERE id = %s
        """, (trade_id,))
        row = cur.fetchone()
        cur.close()
        conn.close()
        return row[0] if row else None
    except Exception as e:
        print(f'[signal_schema] get_trade_workflow_state error: {e}')
        return None


def get_db():
    return _get_conn(_runtime(), row_factory=True)


# ══════════════════════════════════════════════════════════════════════════════
#  Price Architecture — Local DB First
#
#  RULE: All price reads MUST route to local SQLite first.
#        The local DB is seeded by price_collector.py (every minute via cron).
#        All external API calls (HL allMids, Binance candles) are WRITE-ONLY
#        into the local DB — no script should ever read price from an API
#        directly when the local DB has the data.
#
#  Single source of truth for prices: local SQLite (signals_hermes.db)
#  • latest_prices   → current price (upserted every minute by price_collector)
#  • price_history   → historical price series (used for RSI, z-score, etc.)
#  • ohlcv_1m        → 1-minute OHLCV candles (written by fetch_binance_candles)
# ══════════════════════════════════════════════════════════════════════════════


def upsert_prices_from_allMids(allMids: dict, tokens: dict = None) -> int:
    """
    Write latest prices from HL allMids into local SQLite.
    Seeds both latest_prices (current) and price_history (time series).

    This is called by price_collector.py on every run.
    Any script that fetches allMids should call this afterward.

    Args:
        allMids:  {token_symbol: price_string} from hc.get_allMids()
        tokens:   {token_symbol: max_leverage} from HL meta universe

    Returns:
        Number of rows inserted into price_history.
    """
    if not allMids:
        return 0
    now = int(time.time())
    conn = _get_conn(STATIC_DB)
    c = conn.cursor()
    rows = 0
    for sym, price_str in allMids.items():
        # SAFETY: reject @XXX numeric coin IDs — Hyperliquid allMids returns these for
        # some coins instead of proper symbol names. They must never enter SQLite.
        if sym.startswith('@'):
            continue
        try:
            price = float(price_str)
            if price <= 0:
                continue
            lev = tokens.get(sym, 10) if tokens else 10
            # latest_prices: upsert
            c.execute(
                'INSERT OR REPLACE INTO latest_prices(token, price, updated_at, max_leverage) VALUES(?, ?, ?, ?)',
                (sym.upper(), price, now, lev)
            )
            # price_history: insert (one row per tick for historical series)
            c.execute(
                'INSERT OR IGNORE INTO price_history(token, price, timestamp) VALUES(?, ?, ?)',
                (sym.upper(), price, now)
            )
            rows += 1
        except (ValueError, TypeError):
            continue
    conn.commit()
    conn.close()
    return rows


def fetch_binance_candles(symbol: str, interval: str = '1m', limit: int = 240) -> list:
    """
    Fetch OHLCV candles from Binance public API (no auth required).
    Writes results to local ohlcv_1m table in SQLite.

    Binance symbol format: 'IMXUSDT' (base + quote)
    HL symbol format:      'IMX'    (base only)

    Args:
        symbol:    Binance symbol e.g. 'IMXUSDT' or HL symbol e.g. 'IMX'
        interval:  '1m', '5m', '15m', '1h', '4h', '1d'
        limit:     Number of candles to fetch (max 1000 for Binance)

    Returns:
        List of candle dicts: [{open_time, open, high, low, close, volume}, ...]
    """
    import requests as _requests

    # Convert HL symbol to Binance format if needed
    if not symbol.endswith('USDT'):
        symbol = symbol.upper() + 'USDT'

    url = 'https://api.binance.com/api/v3/klines'
    params = {'symbol': symbol, 'interval': interval, 'limit': min(limit, 1000)}
    try:
        resp = _requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        raw = resp.json()
    except Exception as e:
        print(f'[fetch_binance_candles] {symbol}: {e}')
        return []

    now = int(time.time())
    conn = _get_conn(STATIC_DB)
    c = conn.cursor()
    candles = []
    for k in raw:
        # Binance kline format:
        # [open_time, open, high, low, close, volume, close_time, ...]
        try:
            ot = int(k[0])
            ct = int(k[6])
            o, h, l, c_, v = float(k[1]), float(k[2]), float(k[3]), float(k[4]), float(k[5])
            # Derive HL symbol (strip USDT suffix)
            hl_sym = symbol.replace('USDT', '').upper()
            c.execute("""
                INSERT OR REPLACE INTO ohlcv_1m
                (token, open_time, open, high, low, close, volume, close_time, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (hl_sym, ot, o, h, l, c_, v, ct, now))
            candles.append({
                'token': hl_sym,
                'open_time': ot,
                'open': o,
                'high': h,
                'low': l,
                'close': c_,
                'volume': v,
                'close_time': ct,
            })
        except (ValueError, TypeError):
            continue
    conn.commit()
    conn.close()
    if candles:
        print(f'[fetch_binance_candles] {symbol} → {len(candles)} candles written '
              f'({interval}, {candles[0]["open_time"]} → {candles[-1]["open_time"]})')
    return candles


def get_ohlcv_1m(token: str, lookback_minutes: int = 60) -> list:
    """
    Read 1m OHLCV candles from local SQLite.
    Returns candles sorted oldest → newest.

    ALL price reads must route here (local DB first).
    Only falls back to live Binance fetch if local DB is empty or stale.

    Args:
        token:           HL symbol e.g. 'IMX'
        lookback_minutes: how far back to read (default: last 60 minutes)

    Returns:
        List of candle dicts: [{open_time, open, high, low, close, volume}, ...]
    """
    cutoff = int(time.time()) - (lookback_minutes * 60)
    conn = _get_conn(STATIC_DB)
    c = conn.cursor()
    c.execute("""
        SELECT open_time, open, high, low, close, volume
        FROM ohlcv_1m
        WHERE token=? AND open_time > ?
        ORDER BY open_time ASC
    """, (token.upper(), cutoff))
    rows = c.fetchall()
    conn.close()
    return [
        {'open_time': r[0], 'open': r[1], 'high': r[2], 'low': r[3], 'close': r[4], 'volume': r[5]}
        for r in rows
    ]


def get_latest_price(token: str) -> float | None:
    """
    Read current price for a token from local SQLite latest_prices table.

    ALL price reads MUST use this (local DB first).
    """
    conn = _get_conn(STATIC_DB)
    c = conn.cursor()
    c.execute('SELECT price FROM latest_prices WHERE token=?', (token.upper(),))
    row = c.fetchone()
    conn.close()
    return row[0] if row else None


def get_price_history(token: str, lookback_minutes: int = 60*24) -> list:
    """
    Read historical price series from local SQLite price_history table.

    ALL price reads for historical analysis (RSI, z-score, etc.) MUST use this.
    """
    conn = _get_conn(STATIC_DB)
    c = conn.cursor()
    cutoff = int(time.time()) - (lookback_minutes * 60)
    c.execute("""
        SELECT timestamp, price FROM price_history
        WHERE token=? AND timestamp>?
        ORDER BY timestamp ASC
        LIMIT 2000
    """, (token.upper(), cutoff))
    rows = c.fetchall()
    conn.close()
    return rows


def get_all_latest_prices() -> dict:
    """
    Read all current prices from local SQLite latest_prices table.

    ALL bulk price reads MUST use this (local DB first).
    """
    conn = _get_conn(STATIC_DB)
    c = conn.cursor()
    c.execute('SELECT token, price FROM latest_prices')
    rows = c.fetchall()
    conn.close()
    return {r[0]: {'price': r[1]} for r in rows}
