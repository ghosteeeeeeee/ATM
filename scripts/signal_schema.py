#!/usr/bin/env python3
"""Signal Schema - Dual-database architecture for Hermes trading system.

STATIC DB  (/root/.hermes/data/signals_hermes.db)   — backfill data, git-tracked
RUNTIME DB (/root/.hermes/data/signals_hermes_runtime.db) — signals, decisions, local state
"""
import sqlite3, time, json, os
from datetime import datetime

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
    rc.execute('CREATE INDEX IF NOT EXISTS idx_sig_decision ON signals(decision)')
    rc.execute('CREATE INDEX IF NOT EXISTS idx_sig_token ON signals(token)')
    rc.execute('CREATE INDEX IF NOT EXISTS idx_sig_created ON signals(created_at)')
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
        )""")
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
    """Add a new signal. Skips if same token+direction+source in last 30 min."""
    conn = _get_conn(_runtime())
    c = conn.cursor()
    try:
        c.execute('''
            SELECT 1 FROM signals
            WHERE token=? AND direction=? AND source=?
            AND created_at > datetime('now', '-30 minutes') LIMIT 1
        ''', (token.upper(), direction.upper(), source))
        if c.fetchone():
            conn.close()
            return None
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
    conn = _get_conn(_runtime(), row_factory=True)
    c = conn.cursor()
    c.execute('''
        SELECT * FROM signals
        WHERE decision='PENDING'
        AND created_at > datetime('now','-'||?||' hours')
        ORDER BY confidence DESC LIMIT ?
    ''', (hours, limit))
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]

get_pending_signals_as_dict = get_pending_signals  # alias

def get_confluence_signals(hours=24):
    conn = _get_conn(_runtime(), row_factory=True)
    c = conn.cursor()
    c.execute('''
        SELECT token, direction, COUNT(*) as count, AVG(confidence) as avg_conf,
               MAX(confidence) as max_conf,
               GROUP_CONCAT(DISTINCT signal_type) as types, MAX(price) as price
        FROM signals
        WHERE decision='PENDING'
        AND created_at > datetime('now','-'||?||' hours')
        GROUP BY token, direction, leverage
        ORDER BY avg_conf DESC
    ''', (hours,))
    results = []
    for r in c.fetchall():
        d = dict(r)
        mult = 1.5 if d['count'] >= 3 else 1.25 if d['count'] == 2 else 1.0
        d['final_confidence'] = min(99, d['avg_conf'] * mult)
        if d.get('types'):
            d['signal_types'] = d['types'].split(',')
        results.append(d)
    conn.close()
    return sorted(results, key=lambda x: x['final_confidence'], reverse=True)

def update_signal_decision(token, direction, decision, reason=None):
    conn = _get_conn(_runtime())
    c = conn.cursor()
    c.execute('''
        UPDATE signals
        SET decision=?, executed=CASE WHEN ?='EXECUTED' THEN 1 ELSE executed END,
            updated_at=CURRENT_TIMESTAMP
        WHERE token=*** AND direction=? AND decision IN ('PENDING', 'APPROVED')
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
    conn = _get_conn(_runtime(), row_factory=True)
    c = conn.cursor()
    c.execute('''
        SELECT token, direction, COUNT(*) as count, AVG(confidence) as avg_conf,
               MAX(confidence) as max_conf,
               GROUP_CONCAT(DISTINCT signal_type) as types,
               MAX(price) as price, MAX(leverage) as leverage
        FROM signals
        WHERE decision='APPROVED' AND executed=0
        AND created_at > datetime('now','-'||?||' hours')
        GROUP BY token, direction, leverage
        ORDER BY avg_conf DESC
    ''', (hours,))
    results = []
    for r in c.fetchall():
        d = dict(r)
        mult = 1.5 if d['count'] >= 3 else 1.25 if d['count'] == 2 else 1.0
        d['final_confidence'] = min(99, d['avg_conf'] * mult)
        if d.get('types'):
            d['signal_types'] = d['types'].split(',')
        results.append(d)
    conn.close()
    return results

def mark_signal_processed(token, decision):
    """Mark signals as processed. Only sets executed=1 for non-APPROVED decisions.
    APPROVED signals keep executed=0 so decider-run can pick them up."""
    conn = _get_conn(_runtime())
    c = conn.cursor()
    try:
        # Only mark executed=1 for SKIPPED/WAIT/FAILED, NOT for APPROVED
        if decision == 'APPROVED':
            c.execute('''
                UPDATE signals
                SET decision=?, updated_at=CURRENT_TIMESTAMP
                WHERE token=? AND executed IN (0, 1)
            ''', (decision, token.upper()))
        else:
            c.execute('''
                UPDATE signals
                SET decision=?, executed=1, updated_at=CURRENT_TIMESTAMP
                WHERE token=? AND executed IN (0, 1)
            ''', (decision, token.upper()))
        conn.commit()
        return c.rowcount
    except Exception as e:
        conn.close()
        return 0

def mark_signal_approved(token, decision):
    """Approve a signal WITHOUT marking it executed. decider-run handles execution."""
    conn = _get_conn(_runtime())
    c = conn.cursor()
    try:
        c.execute('''
            UPDATE signals
            SET decision=?, updated_at=CURRENT_TIMESTAMP
            WHERE token=? AND decision='PENDING'
        ''', (decision, token.upper()))
        conn.commit()
        return c.rowcount
    except Exception as e:
        conn.close()
        return 0

# ── Price History & Indicators (static DB) ────────────────────────────────────
def get_price_history(token, lookback_minutes=60*24):
    conn = _get_conn(_static())
    c = conn.cursor()
    cutoff = int(time.time()) - (lookback_minutes * 60)
    c.execute('''
        SELECT timestamp, price FROM price_history
        WHERE token=? AND timestamp>?
        ORDER BY timestamp ASC
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
    try:
        with open(COOLDOWN_FILE) as f:
            data = json.load(f)
        key = token.upper()
        if direction:
            key = f"{key}:{direction.upper()}"
        if key in data and data[key] > time.time():
            return data[key]
    except: pass
    return None

def set_cooldown(token, direction=None, hours=1):
    try:
        try:
            with open(COOLDOWN_FILE) as f:
                data = json.load(f)
        except:
            data = {}
        key = token.upper()
        if direction:
            key = f"{key}:{direction.upper()}"
        data[key] = time.time() + (hours * 3600)
        with open(COOLDOWN_FILE, 'w') as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f'Cooldown write error: {e}')

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
