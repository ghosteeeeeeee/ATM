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
from hermes_constants import SHORT_BLACKLIST, LONG_BLACKLIST, BROAD_MARKET_TOKENS
from candles_lock import acquire as _candles_lock_acquire, release as _candles_lock_release

# Combined blacklist — tokens that should never be stored (not tradeable or systematically losing)
# EXCEPT broad market tokens — they must always have fresh data for speed/volatility calculations
SKIP_TOKENS = (SHORT_BLACKLIST | LONG_BLACKLIST) - BROAD_MARKET_TOKENS

STATIC = STATIC_DB
init_db()  # Ensure tables exist

API = 'https://api.hyperliquid.xyz/info'
TTL_FILE = PRICES_FILE
BATCH_SIZE = 500  # Hyperliquid universe ~500 tokens

# ── Candle DB (multi-TF candles for macd_rules, zero API calls during signal_gen) ──
CANDLE_PROGRESS_FILE = '/root/.hermes/data/candle_seed_progress.json'
CANDLE_TOKENS_FILE = '/root/.hermes/data/candle_universe_tokens.json'

# ── BUG-048 (Option A, CEO-ratified 2026-10-09): fast 1m seeder ──
# 1m candles are refreshed with REAL Binance/HL OHLC at high frequency so the
# dead 1m tick aggregator (_aggregate_1m.py — kept alive for its 48h soak)
# is irrelevant. Separate progress file so the slow multi-TF cursor in
# CANDLE_TOKENS_FILE is never touched by the fast loop (and vice versa).
CANDLE_FAST_1M_FILE = '/root/.hermes/data/candle_fast_1m_progress.json'
FAST_1M_TOKENS_PER_RUN = 60   # CEO-set: 178 tokens / 60 per run = one full pass in 3 runs
                              # (~2-7 min at the observed 36-142s cadence). NOTE (review
                              # MEDIUM-3, measured live 2026-10-09): because of the <300s
                              # skip below, a token is usually skipped on its first revisit
                              # and re-fetched on its second — effective per-token refresh
                              # is ~6-13 min, NOT the 2-7 min pass time. Still ~3-4x better
                              # than the old 18-42 min rotation. Lower FAST_1M_MAX_AGE_S or
                              # raise this constant if <5 min per-token freshness is required.
FAST_1M_MAX_AGE_S = 300       # re-fetch 1m when newest candle is older than this...
                              # ...OR has volume=0 (a vol=0 "fresh" candle is fake tick-agg data)
FAST_1M_FETCH_LIMIT = 200     # Binance klines limit for 1m (matches the legacy slow-path fetch)
FAST_1M_TIME_BUDGET_S = 25    # hard wall-clock cap per run — guarantees the loop finishes well
                              # inside the ~36-142s effective timer cadence (no cadence blowup)
# Slow multi-TF backfill (BUG-048 split): owns 5m/15m/1h/4h ONLY — 1m was
# removed from its fetch list because the fast loop above owns 1m now.
# Keeping 1m in both loops would double API load for zero benefit.
SLOW_SEED_TOKENS_PER_RUN = 10  # (was local TOKENS_PER_RUN in _seed_universe_candles)
SLOW_SEED_TFS = [('5m', 100), ('15m', 100), ('1h', 100), ('4h', 100)]  # NO '1m' — fast loop owns it


def _init_candles_db():
    """Ensure candles.db has all required tables."""
    conn = sqlite3.connect(CANDLES_DB, timeout=30)
    conn.execute("PRAGMA busy_timeout=30000")
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


def _fetch_hl_candles(token: str, interval: str, limit: int = 200) -> list:
    """Fetch candles from Hyperliquid candleSnapshot — has volume for ALL HL tokens.
    DRIFT-007 fix: Binance fails for HL-only alts; HL API returns real volume in 'v'."""
    iv_ms = {'1m': 60000, '5m': 300000, '15m': 900000, '1h': 3600000, '4h': 14400000}.get(interval, 60000)
    now_ms = int(time.time() * 1000)
    start_ms = now_ms - limit * iv_ms
    payload = {'type': 'candleSnapshot', 'req': {'coin': token, 'interval': interval,
              'startTime': start_ms, 'endTime': now_ms}}
    try:
        resp = requests.post('https://api.hyperliquid.xyz/info', json=payload, timeout=10)
        if resp.status_code != 200:
            return []
        data = resp.json()
        if not isinstance(data, list):
            return []
        return [
            {'ts': int(c['t'] / 1000), 'open': float(c['o']), 'high': float(c['h']),
             'low': float(c['l']), 'close': float(c['c']), 'volume': float(c.get('v') or 0)}
            for c in data if c.get('o')
        ]
    except Exception as e:
        print(f'[_fetch_hl_candles] {token} {interval}: {e}')
        return []


def _store_candles(token: str, interval: str, candles: list):
    """Store candles to candles.db.

    FIX 2026-10-09 (BUG-048): guarded upsert instead of INSERT OR REPLACE —
    never let a flat volume=0 candle overwrite a real (volume>0) OHLC candle.
    Existing volume=0 rows ARE always overwritten (that is how fake tick-agg
    candles get healed); real candles only refresh against other real candles.
    Plain INSERT OR IGNORE was NOT used here on purpose: it would freeze the
    currently-open candle at its first partial snapshot forever (the seeder
    sees mid-minute OHLC), re-introducing the stale-candle class of BUG-048.
    is_closed=1 preserves the old "column DEFAULT 1" semantics of the REPLACE.
    """
    if not candles:
        return
    table = {'1m': 'candles_1m', '15m': 'candles_15m', '1h': 'candles_1h', '4h': 'candles_4h', '5m': 'candles_5m'}[interval]
    rows = [(token, cd['ts'], cd['open'], cd['high'], cd['low'], cd['close'], cd['volume']) for cd in candles]
    # ponytail: one retry — pipeline/1m-candle hold short write locks on candles.db
    for attempt in range(2):
        conn = sqlite3.connect(CANDLES_DB, timeout=30)
        try:
            conn.execute("PRAGMA busy_timeout=30000")
            conn.execute("PRAGMA journal_mode=WAL")
            c = conn.cursor()
            c.executemany(f"""
                INSERT INTO {table} (token, ts, open, high, low, close, volume, is_closed)
                VALUES (?, ?, ?, ?, ?, ?, ?, 1)
                ON CONFLICT(token, ts) DO UPDATE SET
                    open=excluded.open, high=excluded.high, low=excluded.low,
                    close=excluded.close, volume=excluded.volume, is_closed=1
                WHERE {table}.volume = 0 OR excluded.volume > 0
            """, rows)
            conn.commit()
            return
        except sqlite3.OperationalError as e:
            if attempt == 0:
                time.sleep(2)
                continue
            print(f'  [_store_candles] {token} {interval}: {e}')
            return
        finally:
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


def _get_fast_1m_progress():
    """Load or init the fast-1m loop's OWN token list + cursor.

    BUG-048: kept in a separate file from CANDLE_TOKENS_FILE so the fast and
    slow loops can never corrupt each other's cursor (the slow path's
    _save_candle_progress rewrites its whole file and would wipe a sibling key).
    """
    if os.path.exists(CANDLE_FAST_1M_FILE):
        try:
            with open(CANDLE_FAST_1M_FILE) as f:
                data = json.load(f)
            return data.get('tokens', []), data.get('cursor', 0)
        except Exception:
            pass
    return [], 0


def _save_fast_1m_progress(tokens: list, cursor: int):
    """Persist the fast-1m loop's universe token list + cursor."""
    with open(CANDLE_FAST_1M_FILE, 'w') as f:
        json.dump({'tokens': tokens, 'cursor': cursor, 'last_run': int(time.time())}, f)


def _universe_token_list(universe: list) -> list:
    """Sorted, deduped, tradeable coin list from the HL universe (shared by both seeders)."""
    return sorted(set(
        u['name'] for u in universe
        if u.get('name')
        and not u['name'].startswith('@')
        and len(u['name']) <= 10
        and not u.get('isDelisted', False)  # FIX: don't seed candles for delisted HL tokens
    ))


def _fetch_real_candles(token: str, tf: str, limit: int) -> list:
    """Fetch real API candles for one TF — Binance first, HL fallback (DRIFT-007).
    Binance fails for HL-only alts; HL candleSnapshot has volume for all HL tokens.
    Returns [] only when both sources return nothing."""
    candles = _fetch_binance_candles(token, tf, limit)
    if not candles or all(cd.get('volume', 0) == 0 for cd in candles):
        _hl = _fetch_hl_candles(token, tf, limit)
        if _hl:
            candles = _hl
    return candles


def _seed_fast_1m(universe: list):
    """
    BUG-048 fast 1m seeder (CEO Option A) — refreshes 1m candles for a large
    slice of the universe EVERY cycle with REAL Binance/HL OHLC, making the
    dead 1m tick aggregator irrelevant.

    Runs INSIDE main()'s candles lock — must NEVER re-acquire it (deadlock).
    Own cursor in CANDLE_FAST_1M_FILE; the slow multi-TF rotation is untouched.
    Skip-if-fresh: only re-fetch a token when its newest 1m candle is older
    than FAST_1M_MAX_AGE_S OR has volume=0 (a vol=0 "fresh" candle is fake).
    """
    all_tokens = _universe_token_list(universe)
    if not all_tokens:
        return

    _init_candles_db()  # self-sufficient — runs before the slow path that usually inits

    saved_tokens, cursor = _get_fast_1m_progress()

    # If universe changed significantly, reset (same policy as the slow path)
    if set(saved_tokens) != set(all_tokens):
        saved_tokens = all_tokens
        cursor = 0
        _save_fast_1m_progress(saved_tokens, cursor)
        print(f'[candle_seed_1m] Universe changed — reset fast cursor to 0 ({len(saved_tokens)} tokens)')

    conn = None
    checked = 0
    refreshed = 0
    deadline = time.time() + FAST_1M_TIME_BUDGET_S
    try:
        conn = sqlite3.connect(CANDLES_DB, timeout=10)
        conn.execute("PRAGMA busy_timeout=30000")
        for _ in range(FAST_1M_TOKENS_PER_RUN):
            idx = cursor % len(saved_tokens)
            token = saved_tokens[idx]
            try:
                # Skip-if-fresh: newest 1m candle < FAST_1M_MAX_AGE_S old AND volume > 0.
                # A vol=0 "fresh" candle means fake tick-agg data — always re-fetch (BUG-048).
                row = conn.execute(
                    "SELECT ts, volume FROM candles_1m WHERE token=? ORDER BY ts DESC LIMIT 1",
                    (token,)
                ).fetchone()
                if row and row[0] is not None and (int(time.time()) - row[0]) < FAST_1M_MAX_AGE_S \
                   and (row[1] or 0) > 0:
                    cursor += 1
                    checked += 1
                    continue  # fresh REAL candle — skip

                # Wall-clock guard: stop before fetching, do NOT advance the cursor
                # past this token — the next cycle resumes exactly here.
                if time.time() > deadline:
                    print(f'  [candle_seed_1m] Time budget ({FAST_1M_TIME_BUDGET_S}s) hit after '
                          f'{checked} tokens — resuming at cursor={cursor} next cycle')
                    break

                candles = _fetch_real_candles(token, '1m', FAST_1M_FETCH_LIMIT)
                if candles:
                    _store_candles(token, '1m', candles)  # guarded upsert — vol=0 can never downgrade real OHLC
                    refreshed += 1
                cursor += 1
                checked += 1
            except Exception as e:
                # Self-review fix (fc55eff0 review MEDIUM-1): ONE poisoned token must
                # never wedge the whole rotation. _store_candles only catches
                # sqlite3.OperationalError, so e.g. a NaN OHLC value -> IntegrityError
                # would park the cursor on this token forever (the whole 1m seeder
                # would silently stop behind a single 'non-fatal' log line).
                # Log, advance past the bad token, keep the rotation alive.
                print(f'  [candle_seed_1m] {token}: unexpected error — advancing past: {e}')
                cursor += 1
                checked += 1
    finally:
        if conn is not None:
            conn.close()
        _save_fast_1m_progress(saved_tokens, cursor)

    print(f'[candle_seed_1m] Refreshed {refreshed}/{checked} tokens this run '
          f'(cursor={cursor % len(saved_tokens)}/{len(saved_tokens)})')


def _seed_universe_candles(universe: list):
    """
    Seed multi-TF candles for the full universe — SLOW path (BUG-048 split):
    owns 5m/15m/1h/4h backfill ONLY. 1m was removed from the fetch list —
    _seed_fast_1m() owns 1m now (60 tokens/run with real OHLC).
    Tracks progress in a JSON file so each run picks up where we left off.
    """
    _init_candles_db()

    all_tokens = _universe_token_list(universe)

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
    # FIX 2026-10-05: raised 2->10 — 76/82 tokens had flat 1m candles (O=H=L=C) from
    # aggregator overwrite bug. Need faster cycling to re-fetch real OHLC. ~40 API
    # calls per run (10 tokens x 4 TFs) is well within Binance/HL rate limits.
    # FIX 2026-10-09 (BUG-048): 10 tokens x 4 TFs — '1m' dropped from the TF list;
    # the fast loop (_seed_fast_1m) owns 1m now. Do NOT add 1m back here.
    TOKENS_PER_RUN = SLOW_SEED_TOKENS_PER_RUN

    seeded = 0
    for _ in range(TOKENS_PER_RUN):
        idx = cursor % len(saved_tokens)
        token = saved_tokens[idx]

        # Check if we already have recent candles (1m within 5 min, 4h within 2 hours)
        # DRIFT-007: also require non-zero volume — zero-vol "fresh" candles block HL backfill
        conn = sqlite3.connect(CANDLES_DB, timeout=10)
        conn.execute("PRAGMA busy_timeout=30000")
        conn.execute("PRAGMA journal_mode=WAL")
        c = conn.cursor()
        c.execute("SELECT MAX(ts) FROM candles_1m WHERE token=?", (token,))
        row_1m = c.fetchone()
        c.execute("SELECT MAX(ts) FROM candles_4h WHERE token=?", (token,))
        row_4h = c.fetchone()
        _has_vol = True
        if row_1m and row_1m[0] and (int(time.time()) - row_1m[0]) < 300:
            c.execute("SELECT volume FROM candles_1m WHERE token=? ORDER BY ts DESC LIMIT 1", (token,))
            _vol_row = c.fetchone()
            _has_vol = bool(_vol_row and _vol_row[0] and _vol_row[0] > 0)
        conn.close()
        now = int(time.time())
        # Skip if 1m is fresh (<5 min) AND 4h is fresh (<2 hours) AND has real volume
        if (row_1m and row_1m[0] and (now - row_1m[0]) < 300 and
            row_4h and row_4h[0] and (now - row_4h[0]) < 7200 and
            _has_vol):
            cursor += 1
            continue  # Already fresh with volume, skip

        # Fetch 5m, 15m, 1h, 4h candles — Binance first, HL fallback.
        # DRIFT-007: Binance fails for HL-only alts; HL candleSnapshot has volume for all.
        # FIX 2026-10-05 (bug_hunter HIGH): added 15m — was never fetched, so candles_15m
        # was 100% zero-volume from _aggregate_tf, breaking 15m volume signals.
        # FIX 2026-10-09 (BUG-048): 1m removed — owned by _seed_fast_1m() now.
        for tf, limit in SLOW_SEED_TFS:
            candles = _fetch_real_candles(token, tf, limit)
            if candles:
                _store_candles(token, tf, candles)

        seeded += 1
        cursor += 1

    _save_candle_progress(saved_tokens, cursor)
    if seeded > 0:
        print(f'[candle_seed] Seeded {seeded}/{TOKENS_PER_RUN} tokens this run '
              f'(cursor={cursor}/{len(saved_tokens)})')

    # Always fetch BTC 1m candles (needed for continuum engine — fresh EVERY cycle;
    # the fast loop only reaches BTC once per full rotation, so keep this)
    btc_1m = _fetch_binance_candles('BTC', '1m', 200)
    if not btc_1m:
        btc_1m = _fetch_hl_candles('BTC', '1m', 200)
    if btc_1m:
        _store_candles('BTC', '1m', btc_1m)


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
    # Use _hl_info() for rate limiting (prevents 429s from concurrent processes)
    from hyperliquid_exchange import _hl_info
    try:
        meta_result = _hl_info({"type": "meta"})
        universe = meta_result.get('universe', []) if meta_result else []

        mids_result = _hl_info({"type": "allMids"})
        mids = mids_result if mids_result else {}

        tokens={u['name']: u.get('maxLeverage', 10) for u in universe if mids.get(u['name'])}
        prices = {k: float(v) for k, v in mids.items() if v}

        # Write shared cache directly from fetched data (avoids redundant 2nd fetch)
        hc._write({
            "allMids": mids,
            "meta": meta_result,
            "_ts": time.time(),
            "_errors": []
        })

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
    tokens_clean={k: v for k, v in tokens.items() if k not in delisted and k not in SKIP_TOKENS}
    # FIX: Only store prices for tokens that exist in tokens_clean (i.e., universe tokens).
    # Hyperliquid's allMids returns ~542 entries: 230 named coins + 306 @XXX numeric IDs.
    # @XXX entries are invalid coin identifiers — never store them in SQLite.
    prices_clean={k: v for k, v in prices.items() if k not in delisted and k not in SKIP_TOKENS and k in tokens_clean}

    # Count skipped for logging
    skipped = len(prices) - len(prices_clean)
    if skipped > 0:
        print(f'  [price_collector] Skipped {skipped} blacklisted tokens (not storing to DB)')

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
        # t is now <= lc — this IS the last closed window
        # Do NOT add tf here — that would skip the window that needs closing
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
    # then the guarded upsert (FIX 2026-10-09 BUG-048) marks them is_closed=1
    # WITHOUT ever overwriting real API candles (volume>0).
    # Tokens with no prior candles have last_closed_boundary = -tf_seconds (start from epoch).
    # Skip blacklisted tokens — reduces ~79 tokens × 5 queries × 4 TFs per run
    # EXCEPT broad market tokens — they must always have fresh candle data
    skip = (SHORT_BLACKLIST | LONG_BLACKLIST) - BROAD_MARKET_TOKENS
    last_closed_dict = {k: v for k, v in last_closed_dict.items() if k not in skip}

    filled = 0
    for token, token_last_closed in last_closed_dict.items():
        # Tokens with no prior closed candles start from beginning of price_history
        if token_last_closed is None or token_last_closed <= 0:
            token_last_closed = 0  # will fill all windows from epoch
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
                # FIX 2026-10-09 (BUG-048): guarded upsert instead of INSERT OR REPLACE —
                # the aggregator was overwriting API-fetched OHLC candles (from
                # price_collector's seeder) with flat tick-aggregated data (O=H=L=C,
                # volume=0). Same bug class fixed for 1m on 2026-10-05. Measured live
                # damage: 27.8% volume=0 on 4h, 11.4% on 1h over 24h. price_history
                # ticks are ~155s apart, so few ticks per window = no range. Only fill
                # GAPS and tick-agg (volume=0) rows — NEVER overwrite real API candles
                # (volume>0). The WHERE clause (instead of plain INSERT OR IGNORE) is
                # deliberate: plain OR IGNORE can never upgrade an existing is_closed=0
                # developing row (BUG-048 root cause (b): 230,827 stuck rows in
                # candles_1m, is_closed=1 count=0 all-time). The volume=0 guard lets
                # the aggregator close its own developing windows while still leaving
                # real API candles untouched.
                candle_cur.execute(f"""
                    INSERT INTO {table}
                        (token, ts, open, high, low, close, volume, is_closed)
                    VALUES (?, ?, ?, ?, ?, ?, 0, 1)
                    ON CONFLICT(token, ts) DO UPDATE SET
                        open=excluded.open, high=excluded.high, low=excluded.low,
                        close=excluded.close, is_closed=1
                    WHERE {table}.volume = 0
                """, (token, window_ts, open_row[0], high, low, close_row[0]))
                filled += 1

    # Write developing candle for the open window if >= 2 bars available
    prev_window = current_window - tf_seconds
    dev_rows = ph_cur.execute(f"""
        WITH windowed AS (
            SELECT
                token,
                :current_window AS window_ts,
                price, timestamp,
                ROW_NUMBER() OVER (
                    PARTITION BY token
                    ORDER BY timestamp
                ) AS rn,
                COUNT(*) OVER (
                    PARTITION BY token
                ) AS cnt
        FROM price_history
            WHERE timestamp > :prev_window
              AND timestamp <= :current_window
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
            (SELECT price FROM windowed WHERE token=a.token AND window_ts=:current_window AND rn=1 LIMIT 1) AS open_price,
            a.high, a.low, f.close_price, a.bar_count
        FROM agg a
        JOIN first_last f ON a.token = f.token
        WHERE a.bar_count >= 2
    """, {'current_window': current_window, 'prev_window': prev_window}).fetchall()

    # Filter out blacklisted tokens for developing candle phase too
    dev_rows = [row for row in dev_rows if row[0] not in skip]

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

    # Prune old candles to prevent table bloat (keep 30d — FIX 2026-10-04: was 72h)
    # 30d ≈ 1.4M rows — trivial for SQLite. Enables 5m-based audits/backtests.
    if table == 'candles_5m':
        _prune_window = 2592000  # 30 days in seconds
        # Prune old closed candles
        candle_cur.execute(f"""
            DELETE FROM {table} WHERE is_closed = 1 AND ts < ?
        """, (last_closed - _prune_window,))
        if candle_cur.rowcount > 0:
            print(f'  [{table}] Pruned {candle_cur.rowcount} old closed candles')
        # Prune old developing candles (stale from past runs)
        candle_cur.execute(f"""
            DELETE FROM {table} WHERE is_closed = 0 AND ts < ?
        """, (last_closed - _prune_window,))
        if candle_cur.rowcount > 0:
            print(f'  [{table}] Pruned {candle_cur.rowcount} old developing candles')

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
    # THEN update prices.json so the timestamp reflects post-aggregation freshness
    # ponytail: serialize vs _aggregate_1m — both hold long write txns on candles.db
    _lock_fd = _candles_lock_acquire(timeout_s=90)
    try:
        ph_conn = sqlite3.connect(STATIC_DB, timeout=30)
        ph_conn.execute("PRAGMA journal_mode=WAL")
        candle_conn = sqlite3.connect(CANDLES_DB, timeout=60)
        candle_conn.execute("PRAGMA busy_timeout=60000")
        candle_conn.execute("PRAGMA journal_mode=WAL")
        candle_conn.execute("PRAGMA synchronous=NORMAL")

        for tf_sec, table in [(300, 'candles_5m'), (900, 'candles_15m'), (3600, 'candles_1h'), (14400, 'candles_4h')]:
            try:
                last = _aggregate_tf(ph_conn, candle_conn, tf_sec, table)
                dt = time.strftime('%H:%M:%S', time.localtime(last)) if last else 'N/A'
                print(f'  {table}: last closed window {last} ({dt})')
            except Exception as e:
                print(f'  {table}: aggregation error: {e}')

        # ponytail: truncate WAL after writers release so disk doesn't balloon
        try:
            candle_conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        except Exception as e:
            print(f'  wal_checkpoint: {e}')
        ph_conn.close()
        candle_conn.close()

        # candles now updated — timestamp already reflects post-aggregation freshness
        # save_prices() removed — was redundant second write, doubled DB time
        # ponytail: seeder is best-effort — never fail the cycle after prices are saved
        # BUG-048 (Option A): fast 1m seeder FIRST (1m is the latency-critical path).
        # Runs inside the candles lock already held here — do NOT re-acquire it.
        try:
            _seed_fast_1m(universe)
        except Exception as e:
            print(f'  [candle_seed_1m] skipped (non-fatal): {e}')
        try:
            _seed_universe_candles(universe)  # slow multi-TF backfill (5m/15m/1h/4h only — 1m removed, BUG-048)
        except Exception as e:
            print(f'  [candle_seed] skipped (non-fatal): {e}')
    finally:
        _candles_lock_release(_lock_fd)

if __name__ == '__main__':
    main()
