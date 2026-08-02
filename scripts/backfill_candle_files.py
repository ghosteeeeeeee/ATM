#!/usr/bin/env python3
"""
Back-fill candle JSON files to target counts by fetching older data from Binance.
Files are sorted ascending (oldest first). Existing data is preserved; missing
older candles are prepended.

Usage:
    python3 backfill_candle_files.py [--dry-run]
    python3 backfill_candle_files.py --token BTC,ETH  (specific tokens only)

Candle targets (per timeframe):
    15m: 1000 candles (~10 days) — trimmer keeps most recent 1000
    1h:   500 candles (~21 days) — trimmer keeps most recent 500
    4h:   500 candles (~83 days) — trimmer keeps most recent 500 (enough for MTF backtest)
"""
import json, os, sys, glob, argparse, time, functools, requests

CANDLES_DIR = '/root/.hermes/data/candles'
BINANCE_BASE = 'https://api.binance.com/api/v3/klines'

TARGETS = {
    '15m': 1000,
    '1h':  500,
    '4h':  500,
}

@functools.lru_cache(maxsize=8)
def _cached_request(url):
    for attempt in range(3):
        try:
            resp = requests.get(url, timeout=20)
            resp.raise_for_status()
            return resp.json()
        except Exception:
            if attempt < 2:
                time.sleep(2 ** attempt)
            continue
    return None


def fetch_klines_backward(symbol, interval, needed, current_oldest_ts_ms):
    """
    Fetch klines from Binance going BACKWARD from current_oldest_ts_ms.
    Returns list of {O,H,L,C,V,T} dicts in ASCENDING order (oldest first).
    """
    ms_per_candle = {
        '15m': 15 * 60 * 1000,
        '1h':  3600 * 1000,
        '4h':  4 * 3600 * 1000,
    }[interval]

    limit = 1000
    all_klines = []
    current_end = current_oldest_ts_ms - 1  # fetch strictly older than current oldest

    max_pages = 6
    for _ in range(max_pages):
        url = (f'{BINANCE_BASE}?symbol={symbol}&interval={interval}'
               f'&limit={limit}&endTime={current_end}')
        batch = _cached_request(url)
        if not batch:
            break

        parsed = []
        for k in batch:
            t = int(k[0])
            if t >= current_oldest_ts_ms:
                continue  # skip overlap with existing
            parsed.append({'O': float(k[1]), 'H': float(k[2]), 'L': float(k[3]),
                           'C': float(k[4]), 'V': float(k[5]), 'T': t})

        if not parsed:
            break

        all_klines.extend(parsed)
        current_end = parsed[0]['T'] - ms_per_candle  # next page before oldest in batch

        if len(all_klines) >= needed:
            break

    # Respect Binance rate limits: sleep between pages
    time.sleep(0.25)
    all_klines.sort(key=lambda c: c['T'])
    return all_klines[:needed]


def backfill_symbol(symbol, dry_run=False):
    symbol = symbol.upper()
    total_added = 0
    refreshed_files = 0

    for tf in ['15m', '1h', '4h']:
        path = f'{CANDLES_DIR}/{symbol}_{tf}.json'
        target = TARGETS[tf]

        try:
            with open(path) as f:
                existing = json.load(f)
        except (json.JSONDecodeError, OSError):
            existing = []

        n = len(existing)
        if n >= target:
            continue

        needed = target - n

        if not existing:
            # No file — can't backfill, would need full fetch (skip, let MTF tuner handle)
            print(f'  [SKIP] {symbol}_{tf}: no existing file')
            continue

        current_oldest_ts = min(int(c['T']) for c in existing)
        klines = fetch_klines_backward(f'{symbol}USDT', tf, needed, current_oldest_ts)

        if not klines:
            print(f'  [WARN] {symbol}_{tf}: Binance returned no older data (n={n}, need={needed})')
            continue

        merged = klines + existing

        if dry_run:
            print(f'  [DRY]  {symbol}_{tf}: {n} + {len(klines)} = {len(merged)} (target {target})')
        else:
            tmp = path + '.tmp'
            with open(tmp, 'w') as f:
                json.dump(merged, f)
            os.replace(tmp, path)
            print(f'  [FILL] {symbol}_{tf}: {n} + {len(klines)} = {len(merged)} (target {target})')
            total_added += len(klines)
            refreshed_files += 1

    return total_added, refreshed_files


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--token', default='')
    args = parser.parse_args()

    files = glob.glob(f'{CANDLES_DIR}/*.json')
    symbols = sorted(set(
        os.path.basename(f).replace('_15m.json','').replace('_1h.json','').replace('_4h.json','')
        for f in files
    ))

    if args.token:
        requested = [s.strip().upper() for s in args.token.split(',')]
        symbols = [s for s in symbols if s in requested]

    print(f'Candle back-fill — targets: 15m={TARGETS["15m"]}, 1h={TARGETS["1h"]}, 4h={TARGETS["4h"]}')
    print(f'{"[DRY RUN] " if args.dry_run else ""}{len(symbols)} symbols: {symbols}\n')

    total_added = 0
    for sym in symbols:
        added, refreshed = backfill_symbol(sym, dry_run=args.dry_run)
        total_added += added

    print(f'\nDone. Total rows added: {total_added}')

if __name__ == '__main__':
    main()
