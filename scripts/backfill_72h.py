#!/usr/bin/env python3
"""
Backfill 72h of 1h candles from Binance into price_history.
Public API — no auth, no rate limits for klines.
72h at 1h = 72 candles per token = 1 API call (Binance returns up to 1000).
"""
import sqlite3, requests
from concurrent.futures import ThreadPoolExecutor, as_completed

STATIC_DB = '/root/.hermes/data/signals_hermes.db'
LOOKBACK_HOURS = 72
WORKERS = 15  # Binance allows this on public klines

def hl_to_binance(token: str) -> str:
    return f"{token}USDT"

def fetch_klines(token: str) -> list:
    """Fetch 1h klines from Binance. Returns [(timestamp_sec, close)]."""
    symbol = hl_to_binance(token)
    try:
        r = requests.get(
            'https://api.binance.com/api/v3/klines',
            params={'symbol': symbol, 'interval': '1h', 'limit': 1000},
            timeout=15
        )
        if r.status_code != 200:
            return []
        data = r.json()
        if not isinstance(data, list):
            return []
        return [(int(c[0] / 1000), float(c[4])) for c in data]
    except Exception:
        return []

def main():
    # Load all tokens
    conn_r = sqlite3.connect(STATIC_DB, timeout=30)
    cur = conn_r.cursor()
    cur.execute('SELECT token FROM latest_prices')
    tokens = [r[0] for r in cur.fetchall()]
    conn_r.close()
    print(f'Backfilling {len(tokens)} tokens × {LOOKBACK_HOURS}h of Binance 1h candles...')

    # Fetch all concurrently
    klines_map = {}
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        futures = {ex.submit(fetch_klines, t): t for t in tokens}
        done = 0
        for f in as_completed(futures):
            done += 1
            token = futures[f]
            try:
                klines_map[token] = f.result()
            except:
                klines_map[token] = []
            if done % 50 == 0:
                print(f'  Fetched {done}/{len(tokens)}...')
            if done == len(tokens):
                print(f'  Fetched {done}/{len(tokens)} — writing to DB...')

    # Write all to DB in main thread
    conn_w = sqlite3.connect(STATIC_DB, timeout=60)
    cur = conn_w.cursor()
    total_rows, failed = 0, 0

    for token, klines in klines_map.items():
        if not klines:
            failed += 1
            continue
        rows = [(token, price, ts) for ts, price in klines]
        cur.executemany(
            'INSERT OR IGNORE INTO price_history(token, price, timestamp) VALUES (?, ?, ?)',
            rows
        )
        total_rows += len(rows)

    conn_w.commit()

    # Stats
    cur.execute('SELECT COUNT(*) FROM price_history')
    print(f'Total rows: {cur.fetchone()[0]}')
    cur.execute('SELECT token, COUNT(*) as n FROM price_history GROUP BY token ORDER BY n ASC LIMIT 5')
    print('Lowest-row tokens:')
    for r in cur.fetchall():
        print(f'  {r[0]}: {r[1]} rows')
    conn_w.close()
    print(f'\nDone: {total_rows} rows inserted, {failed} tokens failed')

if __name__ == '__main__':
    main()
