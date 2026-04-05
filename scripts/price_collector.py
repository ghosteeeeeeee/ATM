#!/usr/bin/env python3
"""
price_collector.py — fetches all Hyperliquid prices and stores to SQLite.
Run every minute via cron: * * * * * python3 /root/.hermes/scripts/price_collector.py
Stores: price_history(token, price, timestamp) and latest_prices(token, price, updated_at)
"""
import sys, os, json, time, sqlite3
sys.path.insert(0, os.path.dirname(__file__))
import requests
from signal_schema import init_db, STATIC_DB, RUNTIME_DB
import hype_cache as hc
from hyperliquid_exchange import is_delisted as _is_delisted
# price_history + latest_prices → static DB; signals → runtime DB
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
    """
    now = int(time.time())
    inserted = 0

    # Filter out delisted tokens at the source (before they enter SQLite)
    # universe may be passed directly, or we build from tokens via _is_delisted fallback
    delisted = set()
    if universe is not None:
        for coin in universe:
            if coin.get('isDelisted', False):
                delisted.add(coin['name'])
    else:
        # Fallback: check each token individually
        for tok in tokens:
            if _is_delisted(tok):
                delisted.add(tok)
    tokens = {k: v for k, v in tokens.items() if k not in delisted}
    prices = {k: v for k, v in prices.items() if k not in delisted}

    conn = sqlite3.connect(STATIC)
    c = conn.cursor()

    rows = [(tok, prices.get(tok), now) for tok in tokens if prices.get(tok)]
    if rows:
        c.executemany(
            'INSERT OR IGNORE INTO price_history(token, price, timestamp) VALUES(?, ?, ?)',
            rows
        )
        c.executemany(
            'INSERT OR REPLACE INTO latest_prices(token, price, updated_at, max_leverage) VALUES(?, ?, ?, ?)',
            [(tok, prices.get(tok), now, lev) for tok, lev in tokens.items() if prices.get(tok)]
        )
        inserted = len(rows)
        conn.commit()

    conn.close()

    # Cache JSON for other scripts
    os.makedirs('/root/.hermes/data', exist_ok=True)
    with open(TTL_FILE, 'w') as f:
        json.dump({'prices': prices, 'tokens': tokens, 'updated': now}, f)

    return inserted

def main():
    tokens, prices, universe = fetch_all_prices()
    if not prices:
        print('No prices fetched')
        return 1
    inserted = save_prices(tokens, prices, universe=universe)
    print(f'Collected {inserted} prices at {time.strftime("%H:%M:%S")}')

if __name__ == '__main__':
    main()
