#!/usr/bin/env python3
"""
Backfill price_history with 1m candles from Binance for stale tokens.
Gap is the last ~48 hours. Fetches up to 1000 1m candles per request
(Binance limit), chains 3 requests per token to cover 48h.
Uses INSERT OR REPLACE so stale entries get overwritten.
"""
import sys, os, time, sqlite3, requests
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, os.path.dirname(__file__))
from hermes_constants import SHORT_BLACKLIST, LONG_BLACKLIST
from paths import STATIC_DB

BLACKLIST = set(SHORT_BLACKLIST) | set(LONG_BLACKLIST)
STATIC_DB = '/root/.hermes/data/signals_hermes.db'
LOOKBACK_MINUTES = 60 * 48  # 48 hours
BATCH_SIZE = 1000           # Binance 1m kline limit


def hl_to_binance(token: str) -> str:
    return f"{token}USDT"


def fetch_1m_klines(token: str) -> list:
    """Fetch 1m klines from Binance covering last 48h. Returns [(ts, close)]."""
    symbol = hl_to_binance(token)
    url = 'https://api.binance.com/api/v3/klines'
    all_klines = []

    # Binance 1m limit is 1000 per request; chain via endTime
    # Start from the most recent and work backwards
    end_time = int(time.time() * 1000)

    for _ in range(3):  # max 3 chained requests = 3000 candles = 50h
        params = {
            'symbol': symbol,
            'interval': '1m',
            'limit': BATCH_SIZE,
            'endTime': end_time
        }
        try:
            r = requests.get(url, params=params, timeout=10)
            if r.status_code != 200:
                break
            klines = r.json()
            if not klines:
                break
            # ts_ms -> ts_sec, close price
            for k in klines:
                all_klines.append((int(k[0] / 1000), float(k[4])))
            # Move window back
            end_time = klines[0][0] - 1  # 1ms before earliest candle
            if len(klines) < BATCH_SIZE:
                break
        except Exception as e:
            print(f'  [{token}] fetch error: {e}')
            break

    # Sort oldest first
    all_klines.sort(key=lambda x: x[0])
    return all_klines


def process_token(token: str) -> tuple:
    """Fetch and store 1m candles for one token. Returns (token, rows_inserted, status)."""
    klines = fetch_1m_klines(token)
    if not klines:
        return (token, 0, 'no_data')

    conn = sqlite3.connect(STATIC_DB)
    c = conn.cursor()
    rows = [(token, price, ts) for ts, price in klines]
    try:
        c.executemany(
            'INSERT OR REPLACE INTO price_history (token, price, timestamp) VALUES (?, ?, ?)',
            rows
        )
        conn.commit()
        inserted = len(rows)
    except Exception as e:
        inserted = 0
        print(f'  [{token}] DB error: {e}')
    finally:
        conn.close()

    return (token, inserted, 'ok')


def main():
    now = time.time()
    cutoff = int(now - 300)  # tokens with last update > 5min ago are stale

    # Get stale tokens from DB
    conn = sqlite3.connect(STATIC_DB)
    c = conn.cursor()
    c.execute('''
        SELECT token, MAX(timestamp) as max_ts
        FROM price_history
        GROUP BY token
        HAVING max_ts < ?
        ORDER BY max_ts ASC
    ''', (cutoff,))
    stale_tokens = [r[0] for r in c.fetchall()]
    conn.close()

    # Filter blacklist
    tokens_to_backfill = [t for t in stale_tokens if t not in BLACKLIST]
    skipped_blacklist = len(stale_tokens) - len(tokens_to_backfill)

    print(f'Stale tokens: {len(stale_tokens)} | Blacklisted (skip): {skipped_blacklist} | To backfill: {len(tokens_to_backfill)}')
    print(f'Fetching {LOOKBACK_MINUTES}h of 1m candles from Binance...')
    print()

    total_rows = 0
    failed = 0
    done = 0

    with ThreadPoolExecutor(max_workers=15) as ex:
        futures = {ex.submit(process_token, t): t for t in tokens_to_backfill}
        for f in as_completed(futures):
            done += 1
            token, inserted, status = f.result()
            if status == 'ok':
                total_rows += inserted
                age_days = (now - 1722000000) / 86400  # approx
                print(f'  [{done}/{len(tokens_to_backfill)}] {token}: {inserted} rows')
            else:
                failed += 1
                print(f'  [{done}/{len(tokens_to_backfill)}] {token}: FAILED ({status})')

    print()
    print(f'=== Done ===')
    print(f'Total rows inserted: {total_rows}')
    print(f'Failed tokens: {failed}')

    # Verify
    conn = sqlite3.connect(STATIC_DB)
    c = conn.cursor()
    c.execute('''
        SELECT token, MAX(timestamp) as max_ts, COUNT(*) as cnt
        FROM price_history
        GROUP BY token
        ORDER BY max_ts ASC
        LIMIT 10
    ''')
    print()
    print('Oldest tokens after backfill:')
    for r in c.fetchall():
        age_hr = (time.time() - r[1]) / 3600
        print(f'  {r[0]:12} | {r[2]:6}d rows | last={time.ctime(r[1])} ({age_hr:.1f}h ago)')
    c.execute('SELECT COUNT(*), MAX(timestamp) FROM price_history')
    total, mx = c.fetchone()
    c.execute('SELECT COUNT(DISTINCT token) FROM price_history')
    distinct = c.fetchone()[0]
    print(f'Total: {total} rows, {distinct} tokens, max_ts={time.ctime(mx)}')
    conn.close()


if __name__ == '__main__':
    main()
