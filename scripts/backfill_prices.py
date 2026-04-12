#!/usr/bin/env python3
"""
Backfill 1h candles from Binance public API into price_history.
Maps Hyperliquid token names to Binance USDT pairs.
"""
import sqlite3, requests, time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

STATIC_DB = '/root/.hermes/data/signals_hermes.db'
LIMIT = 1000  # 1000 x 1h = ~41 days of history (needed for z-score calculation, requires 60+ rows)

def hl_to_binance(token: str) -> str:
    """Map Hyperliquid token → Binance symbol."""
    return f"{token}USDT"

def fetch_klines(token: str, lookback_hours: int = 1000) -> list:
    """Fetch 1h klines from Binance. Returns [(timestamp_sec, close_price)]."""
    symbol = hl_to_binance(token)
    url = 'https://api.binance.com/api/v3/klines'
    params = {'symbol': symbol, 'interval': '1h', 'limit': min(lookback_hours, 1000)}
    try:
        r = requests.get(url, params=params, timeout=10)
        if r.status_code != 200:
            return []
        data = r.json()
        return [(int(c[0] / 1000), float(c[4])) for c in data]  # ts_ms->sec, close
    except Exception:
        return []

def backfill_batch(tokens: list, workers: int = 30) -> dict:
    results = {}
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futures = {ex.submit(fetch_klines, t): t for t in tokens}
        done = 0
        for f in as_completed(futures):
            done += 1
            token = futures[f]
            try:
                results[token] = f.result()
            except:
                results[token] = []
            if done % 50 == 0:
                print(f'  Fetched {done}/{len(tokens)}...')
    return results

def main():
    conn = sqlite3.connect(STATIC_DB)
    c = conn.cursor()

    # Get all tokens from latest_prices
    c.execute('SELECT token FROM latest_prices')
    tokens = [r[0] for r in c.fetchall()]
    print(f'Backfilling {len(tokens)} tokens with {LIMIT}h of Binance 1h candles...')

    all_klines = backfill_batch(tokens, workers=30)

    total_rows = 0
    failed = 0
    for token, klines in all_klines.items():
        if not klines:
            failed += 1
            continue
        rows = [(token, price, ts) for ts, price in klines]
        c.executemany(
            'INSERT OR IGNORE INTO price_history(token, price, timestamp) VALUES (?, ?, ?)',
            rows
        )
        total_rows += len(rows)

    conn.commit()
    print(f'Done: {total_rows} rows inserted, {failed} tokens failed')

    # Verify
    c.execute('SELECT COUNT(*) FROM price_history')
    print(f'Total rows: {c.fetchone()[0]}')
    c.execute('SELECT token, COUNT(*) as n FROM price_history GROUP BY token ORDER BY n ASC LIMIT 5')
    print('Sample (lowest rows):')
    for r in c.fetchall():
        print(f'  {r[0]}: {r[1]} rows')

    conn.close()

if __name__ == '__main__':
    main()
