#!/usr/bin/env python3
"""
price_collector.py — fetches all Hyperliquid prices and stores to SQLite.

Single fetch: HL allMids → local SQLite (price_history + latest_prices)
Then for active tokens: Binance 1m/1h/4h candles → local candles.db

Cron: * * * * * python3 /root/.hermes/scripts/price_collector.py

Architecture rule: All price reads MUST route to local SQLite first.
External API calls (HL allMids, Binance candles) are WRITE-ONLY into local DB.
"""
import sys, os, json, time, sqlite3
sys.path.insert(0, os.path.dirname(__file__))
import requests
from paths import *
from signal_schema import (
    init_db, STATIC_DB, RUNTIME_DB,
    upsert_prices_from_allMids,
)
import hype_cache as hc
from hyperliquid_exchange import is_delisted as _is_delisted, _info_rate_limit

STATIC = STATIC_DB
init_db()  # Ensure tables exist

API = 'https://api.hyperliquid.xyz/info'
TTL_FILE = PRICES_FILE
BATCH_SIZE = 500  # Hyperliquid universe ~500 tokens

# ── Candle DB (multi-TF candles for macd_rules, zero API calls during signal_gen) ──
CANDLE_PROGRESS_FILE = '/root/.hermes/data/candle_seed_progress.json'
CANDLE_TOKENS_FILE = '/root/.hermes/data/candle_universe_tokens.json'


def _init_candles_db():
    """Ensure candles.db has all required tables."""
    conn = sqlite3.connect(CANDLES_DB, timeout=30)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS candles_1m (
            token TEXT NOT NULL, ts INTEGER NOT NULL,
            open REAL, high REAL, low REAL, close REAL, volume REAL,
            is_closed INTEGER DEFAULT 1,
            PRIMARY KEY (token, ts)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS candles_15m (
            token TEXT NOT NULL, ts INTEGER NOT NULL,
            open REAL, high REAL, low REAL, close REAL, volume REAL,
            is_closed INTEGER DEFAULT 1,
            PRIMARY KEY (token, ts)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS candles_1h (
            token TEXT NOT NULL, ts INTEGER NOT NULL,
            open REAL, high REAL, low REAL, close REAL, volume REAL,
            is_closed INTEGER DEFAULT 1,
            PRIMARY KEY (token, ts)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS candles_4h (
            token TEXT NOT NULL, ts INTEGER NOT NULL,
            open REAL, high REAL, low REAL, close REAL, volume REAL,
            is_closed INTEGER DEFAULT 1,
            PRIMARY KEY (token, ts)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS candles_5m (
            token TEXT NOT NULL, ts INTEGER NOT NULL,
            open REAL, high REAL, low REAL, close REAL, volume REAL,
            is_closed INTEGER DEFAULT 1,
            PRIMARY KEY (token, ts)
        )
    """)
    for tf in ['1m', '15m', '1h', '4h', '5m']:
        conn.execute(f"CREATE INDEX IF NOT EXISTS idx_candles_{tf}_ts ON candles_{tf}(token, ts DESC)")
    conn.commit()
    conn.close()


def _fetch_binance_candles(token: str, interval: str, limit: int = 500) -> list:
    """Fetch candles from Binance and return as dicts."""
    url = f"https://api.binance.com/api/v3/klines?symbol={token}USDT&interval={interval}&limit={limit}"
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code != 200:
            return []
        klines = resp.json()
        return [
            {'ts': int(k[0] / 1000), 'open': float(k[1]), 'high': float(k[2]),
             'low': float(k[3]), 'close': float(k[4]), 'volume': float(k[5])}
            for k in klines
        ]
    except Exception as e:
        print(f'[_fetch_binance_candles] {token} {interval}: {e}')
        return []


def _store_candles(token: str, interval: str, candles: list):
    """Store candles to candles.db."""
    if not candles:
        return
    table = {'1m': 'candles_1m', '15m': 'candles_15m', '1h': 'candles_1h', '4h': 'candles_4h', '5m': 'candles_5m'}[interval]
    conn = sqlite3.connect(CANDLES_DB, timeout=30)
    conn.execute("PRAGMA journal_mode=WAL")
    c = conn.cursor()
    rows = [(token, cd['ts'], cd['open'], cd['high'], cd['low'], cd['close'], cd['volume']) for cd in candles]
    c.executemany(f"INSERT OR REPLACE INTO {table} (token, ts, open, high, low, close, volume) VALUES (?, ?, ?, ?, ?, ?, ?)", rows)
    conn.commit()
    conn.close()


def _get_candle_progress():
    """Load or init the universe token list + cursor."""
    if os.path.exists(CANDLE_TOKENS_FILE):
        try:
            with open(CANDLE_TOKENS_FILE) as f:
                data = json.load(f)
            return data.get('tokens', []), data.get('cursor', 0), data.get('last_run', 0)
        except Exception:
            pass
    return [], 0, 0


def _save_candle_progress(tokens: list, cursor: int):
    """Persist universe token list + cursor."""
    with open(CANDLE_TOKENS_FILE, 'w') as f:
        json.dump({'tokens': tokens, 'cursor': cursor, 'last_run': int(time.time())}, f)


def _seed_universe_candles(universe: list):
    """
    Seed multi-TF candles for the full universe — 1 token per run, all 3 TFs.
    Tracks progress in a JSON file so each run picks up where we left off.
    """
    _init_candles_db()

    all_tokens = sorted(set(
        u['name'] for u in universe
        if u.get('name') and not u['name'].startswith('@') and len(u['name']) <= 10
    ))

    saved_tokens, cursor, last_run = _get_candle_progress()

    # If universe changed significantly, reset
    if set(saved_tokens) != set(all_tokens):
        all_tokens_set = sorted(all_tokens)
        cursor = 0
        _save_candle_progress(all_tokens_set, cursor)
        print(f'[candle_seed] Universe changed — reset cursor to 0 ({len(all_tokens_set)} tokens)')
        saved_tokens = all_tokens_set

    if not saved_tokens:
        return

    # How many tokens to seed this run (rate-limit friendly)
    TOKENS_PER_RUN = 2

    seeded = 0
    for _ in range(TOKENS_PER_RUN):
        idx = cursor % len(saved_tokens)
        token = saved_tokens[idx]

        # Check if we already have recent 4h candles (within 2 hours)
        conn = sqlite3.connect(CANDLES_DB, timeout=10)
        conn.execute("PRAGMA journal_mode=WAL")
        c = conn.cursor()
        c.execute("SELECT MAX(ts) FROM candles_4h WHERE token=?", (token,))
        row = c.fetchone()
        conn.close()
        if row and row[0] and (int(time.time()) - row[0]) < 7200:
            cursor += 1
            continue  # Already fresh, skip

        # Fetch all 4 TFs for this token
        intervals = {'1m': 1000, '5m': 500, '15m': 500, '1h': 500, '4h': 200}
        for interval, limit in intervals.items():
            candles = _fetch_binance_candles(token, interval, limit)
            if candles:
                _store_candles(token, interval, candles)

        seeded += 1
        cursor += 1

    _save_candle_progress(saved_tokens, cursor)
    if seeded > 0:
        print(f'[candle_seed] Seeded {seeded}/{TOKENS_PER_RUN} tokens this run '
              f'(cursor={cursor}/{len(saved_tokens)})')


def fetch_all_prices():
    """Fetch full token universe + allMids from Hyperliquid.
    Writes shared HL cache (for other scripts) then returns tokens + prices + universe.
    """
    # Try to read from shared HL cache first (written by last price_collector run)
    cached = hc._read()
    if cached.get("allMids") and cached.get("meta"):
        mids = cached["allMids"]
        universe = cached["meta"].get("universe", [])
        tokens={u['name']: u.get('maxLeverage', 10) for u in universe if mids.get(u['name'])}
        prices = {k: float(v) for k, v in mids.items() if v}
        if tokens:
            # Freshen the cache in background (non-blocking)
            hc.fetch_and_cache()
            return tokens, prices, universe

    # Cache miss or stale — do fresh fetch + write cache
    headers = {'Content-Type': 'application/json'}
    try:
        r1 = requests.post(API, json={'type': 'meta'}, headers=headers, timeout=30)
        r1.raise_for_status()
        universe = r1.json().get('universe', [])

        r2 = requests.post(API, json={'type': 'allMids'}, headers=headers, timeout=30)
        r2.raise_for_status()
        mids = r2.json()

        tokens={u['name']: u.get('maxLeverage', 10) for u in universe if mids.get(u['name'])}
        prices = {k: float(v) for k, v in mids.items() if v}

        # Write shared cache for other scripts
        hc.fetch_and_cache()

        return tokens, prices, universe
    except Exception as e:
        print(f'fetch_all_prices error: {e}')
        # Last resort: try to read whatever is in cache
        cached = hc._read()
        if cached.get("allMids"):
            mids = cached["allMids"]
            universe = cached["meta"].get("universe", []) if cached.get("meta") else []
            tokens={u['name']: u.get('maxLeverage', 10) for u in universe if mids.get(u['name'])}
            prices = {k: float(v) for k, v in mids.items() if v}
            return tokens, prices, universe
        return {}, {}, []

def save_prices(tokens, prices, universe=None):
    """Save to SQLite + JSON cache. Returns rows inserted.

    Filters out delisted tokens before writing — prices never enter the system
    for tokens that are halted/delisted on Hyperliquid.

    Architecture: delegates to upsert_prices_from_allMids() which writes to
    both latest_prices (current) and price_history (time series) in one pass.
    """
    # Filter out delisted tokens at the source (before they enter SQLite)
    delisted = set()
    if universe is not None:
        for coin in universe:
            if coin.get('isDelisted', False):
                delisted.add(coin['name'])
    else:
        for tok in tokens:
            if _is_delisted(tok):
                delisted.add(tok)
    tokens_clean={k: v for k, v in tokens.items() if k not in delisted}
    # FIX: Only store prices for tokens that exist in tokens_clean (i.e., universe tokens).
    # Hyperliquid's allMids returns ~542 entries: 230 named coins + 306 @XXX numeric IDs.
    # @XXX entries are invalid coin identifiers — never store them in SQLite.
    prices_clean={k: v for k, v in prices.items() if k not in delisted and k in tokens_clean}

    # Write all prices to local SQLite via upsert_prices_from_allMids
    inserted = upsert_prices_from_allMids(prices_clean, tokens_clean)

    # Cache JSON for other scripts
    now = int(time.time())
    os.makedirs('/root/.hermes/data', exist_ok=True)
    with open(TTL_FILE, 'w') as f:
        json.dump({'prices': prices_clean, 'tokens': tokens_clean, 'updated': now}, f)

    return inserted

def _get_active_tokens() -> set:
    """Gather tokens that need candle data: hot-set + open positions."""
    active = set()

    # Hot-set tokens
    try:
        import json as _json
        hotset_path = HOTSET_FILE
        if os.path.exists(hotset_path):
            with open(hotset_path) as f:
                d = _json.load(f)
            hotset = d.get('hotset', d) if isinstance(d, dict) else d
            for item in hotset:
                token = item.get('token', item.get('symbol', ''))
                if token:
                    active.add(token.upper())
    except Exception:
        pass

    # Open positions from brain DB
    try:
        import psycopg2 as _pg
        conn = _pg.connect(host='/var/run/postgresql', dbname='brain', user='postgres')
        cur = conn.cursor()
        cur.execute("SELECT DISTINCT token FROM trades WHERE status = 'OPEN'")
        for (tok,) in cur.fetchall():
            active.add(tok.upper())
        conn.close()
    except Exception:
        pass

    return active


def _aggregate_tf(ph_conn, candle_conn, tf_seconds: int, table: str):
    """
    Aggregate price_history (signals_hermes.db) into a candles table (candles.db).

    Self-healing design:
    - Per-token last_computed derived from candles.db itself (MAX ts WHERE is_closed=1 per token).
      This avoids the global-MAX bug where one token's newer closed candle blocked fill of ALL
      other tokens' older closed windows.
    - ALL closed windows per-token that aren't yet is_closed=1 are filled.
      This catches up on any missed pipeline runs.
    - Developing candle is always written for the open window if >= 2 bars,
      so signals always have the freshest available data.

    Args:
        ph_conn: SQLite connection to signals_hermes.db (has price_history table)
        candle_conn: SQLite connection to candles.db (has candles_15m/1h/4h tables)
        tf_seconds: window size in seconds (900=15m, 3600=1h, 14400=4h)
        table: candles table name e.g. 'candles_15m'

    Returns:
        int: last window_ts that was successfully written (closed window)
    """
    ph_cur = ph_conn.cursor()
    candle_cur = candle_conn.cursor()

    # Build per-token last_computed dict from candles.db.
    # We read it into Python rather than a temp table to avoid cross-connection issues
    # (signals_hermes.db has no candles_* tables — those live in candles.db).
    candle_cur.execute(f"""
        SELECT token, MAX(ts) FROM {table}
        WHERE is_closed = 1
        GROUP BY token
    """)
    last_computed_dict = {row[0]: row[1] for row in candle_cur.fetchall()}

    # Build first_dev: earliest is_closed=0 window per token (None = all windows closed)
    candle_cur.execute(f"""
        SELECT token, MIN(ts) FROM {table}
        WHERE is_closed = 0
        GROUP BY token
    """)
    first_dev = {row[0]: row[1] for row in candle_cur.fetchall()}

    # Compute last_closed_boundary per token:
    # The MAX(is_closed=1) may have been overwritten by a developing candle,
    # so scan backward from the first developing candle to find the last
    # contiguous is_closed=1 window.
    last_closed_dict = {}
    for token in set(list(last_computed_dict.keys()) + list(first_dev.keys())):
        dev_ts = first_dev.get(token)  # None if no developing candle
        lc = last_computed_dict.get(token, 0)
        if not lc:
            last_closed_dict[token] = 0
            continue

        if dev_ts is None:
            # All windows are closed — use the last one
            last_closed_dict[token] = lc
            continue

        # Find the last contiguous is_closed=1 window before dev_ts
        t = dev_ts - tf_seconds  # candidate window before first dev
        while t > lc:
            t -= tf_seconds
        t += tf_seconds  # step forward to the highest valid closed window
        last_closed_dict[token] = t

    # Use MAX(price_history.timestamp) as the clock — not time.time()
    # This ensures correct window boundaries even with NTP drift
    clock_row = ph_cur.execute(
        "SELECT MAX(timestamp) FROM price_history"
    ).fetchone()
    if not clock_row or not clock_row[0]:
        return 0
    now = clock_row[0]

    # Current open window (the one still building)
    current_window = (now // tf_seconds) * tf_seconds

    # The most recently closed window
    last_closed = current_window - tf_seconds

    # Aggregate closed windows per-token using their individual last_closed_boundary.
    # We track last_computed_dict (the raw MAX is_closed=1 per token) and
    # last_closed_dict (last_computed - tf_seconds, safe from developing candle corruption).
    # The fill queries all windows from last_closed_boundary + tf onward,
    # then INSERT OR REPLACE marks them is_closed=1.
    # Tokens with no prior candles have last_closed_boundary = -tf_seconds (start from epoch).
    filled = 0
    for token, token_last_closed in last_closed_dict.items():
        # Skip tokens with no last_closed_boundary
        if token_last_closed is None or token_last_closed <= 0:
            continue
        # Skip if no windows to fill
        if token_last_closed >= last_closed:
            continue

        ph_cur.execute(f"""
            WITH windowed AS (
                SELECT
                    ((timestamp / {tf_seconds}) * {tf_seconds}) AS window_ts,
                    MIN(timestamp) AS first_ts,
                    MAX(timestamp) AS last_ts,
                    MIN(price) AS low,
                    MAX(price) AS high,
                    COUNT(*) AS bar_count
                FROM price_history
                WHERE token = :token
                  AND timestamp > :token_last_closed
                  AND timestamp <= :last_closed
                GROUP BY window_ts
            )
            SELECT window_ts, first_ts, last_ts, low, high, bar_count
            FROM windowed
            WHERE bar_count >= 4
            ORDER BY window_ts
        """, {'token': token, 'token_last_closed': token_last_closed, 'last_closed': last_closed})

        for (window_ts, first_ts, last_ts, low, high, bar_count) in ph_cur.fetchall():
            # Get open (first price in window) and close (last price in window)
            open_row = ph_cur.execute(
                "SELECT price FROM price_history WHERE token=? AND timestamp=? LIMIT 1",
                (token, first_ts)
            ).fetchone()
            close_row = ph_cur.execute(
                "SELECT price FROM price_history WHERE token=? AND timestamp=? LIMIT 1",
                (token, last_ts)
            ).fetchone()
            if open_row and close_row:
                candle_cur.execute(f"""
                    INSERT OR REPLACE INTO {table}
                        (token, ts, open, high, low, close, volume, is_closed)
                    VALUES (?, ?, ?, ?, ?, ?, 0, 1)
                """, (token, window_ts, open_row[0], high, low, close_row[0]))
                filled += 1

    # Write developing candle for the open window if >= 2 bars available
    dev_rows = ph_cur.execute(f"""
        WITH windowed AS (
            SELECT
                token,
                ((timestamp / {tf_seconds}) * {tf_seconds}) AS window_ts,
                price, timestamp,
                ROW_NUMBER() OVER (
                    PARTITION BY token, ((timestamp / {tf_seconds}) * {tf_seconds})
                    ORDER BY timestamp
                ) AS rn,
                COUNT(*) OVER (
                    PARTITION BY token, ((timestamp / {tf_seconds}) * {tf_seconds})
                ) AS cnt
            FROM price_history
            WHERE ((timestamp / {tf_seconds}) * {tf_seconds}) = {current_window}
        ),
        agg AS (
            SELECT token,
                MIN(price) AS low,
                MAX(price) AS high,
                MAX(cnt) AS bar_count
            FROM windowed GROUP BY token
        ),
        first_last AS (
            SELECT w.token, w.price AS close_price
            FROM windowed w
            INNER JOIN (
                SELECT token, MAX(timestamp) AS max_ts
                FROM windowed GROUP BY token
            ) f ON w.token = f.token AND w.timestamp = f.max_ts
        )
        SELECT
            a.token,
            (SELECT price FROM windowed WHERE token=a.token AND window_ts={current_window} AND rn=1 LIMIT 1) AS open_price,
            a.high, a.low, f.close_price, a.bar_count
        FROM agg a
        JOIN first_last f ON a.token = f.token
        WHERE a.bar_count >= 2
    """).fetchall()

    # Write developing candle for the open window if >= 2 bars available.
    # Only write if this window is not already closed in candles.db.
    # INSERT OR REPLACE would overwrite is_closed=1 with is_closed=0 otherwise.
    for (token, open_px, high, low, close_px, bar_count) in dev_rows:
        exists = candle_cur.execute(
            f"SELECT is_closed FROM {table} WHERE token=? AND ts=?",
            (token, current_window)
        ).fetchone()
        if exists and exists[0] == 1:
            continue  # window already closed — do not overwrite with is_closed=0
        candle_cur.execute(f"""
            INSERT OR REPLACE INTO {table}
                (token, ts, open, high, low, close, volume, is_closed)
            VALUES (?, ?, ?, ?, ?, ?, 0, 0)
        """, (token, current_window, open_px, high, low, close_px))

    candle_conn.commit()
    return last_closed


def main():
    # Prevent overlapping runs — exit if another instance is already running
    lockfile = '/root/.hermes/data/price_collector.lock'
    try:
        import fcntl
        fd = open(lockfile, 'w')
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except (IOError, OSError):
        print('Already running — skipping this cycle')
        return 0

    tokens, prices, universe = fetch_all_prices()
    if not prices:
        print('No prices fetched')
        return 1
    inserted = save_prices(tokens, prices, universe=universe)
    print(f'Collected {inserted} prices at {time.strftime("%H:%M:%S")}')

    # Aggregate candles from price_history (signals_hermes.db) into candles.db
    ph_conn = sqlite3.connect(STATIC_DB, timeout=30)
    ph_conn.execute("PRAGMA journal_mode=WAL")
    candle_conn = sqlite3.connect(CANDLES_DB, timeout=60)
    candle_conn.execute("PRAGMA journal_mode=WAL")
    candle_conn.execute("PRAGMA synchronous=NORMAL")

    for tf_sec, table in [(300, 'candles_5m'), (900, 'candles_15m'), (3600, 'candles_1h'), (14400, 'candles_4h')]:
        try:
            last = _aggregate_tf(ph_conn, candle_conn, tf_sec, table)
            dt = time.strftime('%H:%M:%S', time.localtime(last)) if last else 'N/A'
            print(f'  {table}: last closed window {last} ({dt})')
        except Exception as e:
            print(f'  {table}: aggregation error: {e}')

    ph_conn.close()
    candle_conn.close()

    # Seed multi-TF candles for universe tokens (2 tokens per run, 3 TFs each)
    # This populates candles.db so macd_rules has local data with zero API calls
    _seed_universe_candles(universe)

if __name__ == '__main__':
    main()
