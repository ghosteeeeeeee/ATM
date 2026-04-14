#!/usr/bin/env python3
"""
price_collector.py — fetches all Hyperliquid prices and stores to SQLite.

Single fetch: HL allMids → local SQLite (price_history + latest_prices)
Then for active tokens: Binance 1m candles → local SQLite (ohlcv_1m)

Cron: * * * * * python3 /root/.hermes/scripts/price_collector.py

Architecture rule: All price reads MUST route to local SQLite first.
External API calls (HL allMids, Binance candles) are WRITE-ONLY into local DB.
"""
import sys, os, json, time, sqlite3
sys.path.insert(0, os.path.dirname(__file__))
import requests
from signal_schema import (
    init_db, STATIC_DB, RUNTIME_DB,
    upsert_prices_from_allMids,
    fetch_binance_candles,
    get_ohlcv_1m,
)
import hype_cache as hc
from hyperliquid_exchange import is_delisted as _is_delisted, _info_rate_limit

STATIC = STATIC_DB
init_db()  # Ensure tables exist

API = 'https://api.hyperliquid.xyz/info'
TTL_FILE = '/root/.hermes/data/prices.json'
BATCH_SIZE = 500  # Hyperliquid universe ~500 tokens

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
        hotset_path = '/var/www/hermes/data/hotset.json'
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


def main():
    tokens, prices, universe = fetch_all_prices()
    if not prices:
        print('No prices fetched')
        return 1
    inserted = save_prices(tokens, prices, universe=universe)
    print(f'Collected {inserted} prices at {time.strftime("%H:%M:%S")}')

    # Seed 1m candles for active tokens via Binance
    active_tokens = _get_active_tokens()
    candles_done = 0
    for tok in sorted(active_tokens):
        # Skip non-tradeable / special tokens
        if not tok or tok.startswith('@') or len(tok) > 10:
            continue
        # Check if local DB already has recent candles (within 2 minutes)
        existing = get_ohlcv_1m(tok, lookback_minutes=2)
        if len(existing) >= 2:
            continue  # Already seeded recently
        result = fetch_binance_candles(tok, interval='1m', limit=240)
        if result:
            candles_done += 1
    if candles_done > 0:
        print(f'Seeded {candles_done} candle sets from Binance')

if __name__ == '__main__':
    main()
