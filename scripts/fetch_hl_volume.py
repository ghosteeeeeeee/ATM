#!/usr/bin/env python3
"""
fetch_hl_volume.py — Fetch OHLCV volume data for Hyperliquid-only tokens.

Uses _hl_info() from hyperliquid_exchange for rate limiting (1s gap between
/cache reads) — prevents 429s from concurrent processes.

Usage:
    python3 fetch_hl_volume.py              # fill all tokens with volume=0
    python3 fetch_hl_volume.py --token HYPE # fill specific token
    python3 fetch_hl_volume.py --dry-run    # show what would be fetched
"""
import sys
import os
import time
import sqlite3
import argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paths import CANDLES_DB, HL_CACHE_FILE
from hyperliquid_exchange import _hl_info

# Rate limiting: use _hl_info() which enforces 2s gap between /info calls
RATE_LIMIT_DELAY = 1.0  # 1s between tokens (rate limiter handles per-call gap)
MAX_TOKENS_PER_RUN = 50  # limit per run to avoid long execution


def get_hl_tokens() -> set:
    """Get set of tokens with active markets on Hyperliquid (from allMids cache).
    Returns BOTH original case and uppercase for matching."""
    try:
        with open(HL_CACHE_FILE) as f:
            data = json.load(f)
        # Use allMids — only tokens with active trading pairs
        all_mids = data.get('allMids', {})
        # Return both original and uppercase for case-insensitive matching
        tokens = set()
        for k in all_mids.keys():
            if k and not k.startswith('@') and not k.startswith('#'):
                tokens.add(k)
                tokens.add(k.upper())
        return tokens
    except Exception as e:
        print(f'[hl-volume] WARNING: Could not load HL tokens from cache: {e}')
        return set()


def get_tokens_without_volume():
    """Find tokens in candles_1m that have volume=0, filtered to HL-only tokens."""
    hl_tokens = get_hl_tokens()
    if not hl_tokens:
        print('[hl-volume] WARNING: Could not load HL token universe from cache')

    conn = sqlite3.connect(CANDLES_DB, timeout=10)
    try:
        c = conn.cursor()
        c.execute("""
            SELECT token, COUNT(*) as cnt
            FROM candles_1m
            WHERE volume = 0 OR volume IS NULL
            GROUP BY token
            ORDER BY cnt DESC
        """)
        rows = c.fetchall()
        tokens = [(r[0], r[1]) for r in rows]

        # Filter to HL-only tokens (skip non-existent tokens like KBONK, KFLOKI)
        if hl_tokens:
            before = len(tokens)
            tokens = [(t, c) for t, c in tokens if t.upper() in hl_tokens]
            skipped = before - len(tokens)
            if skipped:
                print(f'[hl-volume] Filtered {skipped} non-HL tokens → {len(tokens)} HL tokens')

        return tokens
    finally:
        conn.close()


import json


def fetch_hl_candles(token: str, timeframe: str = '1m', limit: int = 100):
    """Fetch OHLCV candles from Hyperliquid via _hl_info() (rate-limited).

    Uses the global rate limiter to prevent 429s.
    Tries uppercase token first, then original DB name (for k-prefix tokens).
    """
    # Calculate time range
    end_time = int(time.time() * 1000)
    tf_ms = {'1m': 60000, '5m': 300000, '15m': 900000}[timeframe]
    start_time = end_time - (limit * tf_ms)

    # Try uppercase first, then original DB name (for k-prefix tokens like kPEPE)
    for token_variant in [token.upper(), token]:
        try:
            result = _hl_info({
                "type": "candlesSnapshot",
                "coin": token_variant,
                "interval": timeframe,
                "startTime": start_time,
                "endTime": end_time,
            })
            if result and isinstance(result, list):
                return [
                    {
                        'ts': int(c['t'] / 1000),
                        'open': float(c['o']),
                        'high': float(c['h']),
                        'low': float(c['l']),
                        'close': float(c['c']),
                        'volume': float(c['v']),
                    }
                    for c in result
                ]
        except Exception:
            continue

    print(f'[fetch_hl_candles] {token}: not found on Hyperliquid')
    return []


def store_candles(token: str, interval: str, candles: list):
    """Store candles to candles.db (only fill gaps where volume=0)."""
    if not candles:
        return 0
    table = {'1m': 'candles_1m', '5m': 'candles_5m', '15m': 'candles_15m'}[interval]
    conn = sqlite3.connect(CANDLES_DB, timeout=30)
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        c = conn.cursor()

        # Only store candles where volume=0 in existing data (don't overwrite good data)
        stored = 0
        for cd in candles:
            c.execute(f"SELECT volume FROM {table} WHERE token=? AND ts=?", (token, cd['ts']))
            existing = c.fetchone()
            if existing is None or (existing[0] is not None and existing[0] == 0):
                c.execute(
                    f"INSERT OR REPLACE INTO {table} (token, ts, open, high, low, close, volume) "
                    f"VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (token, cd['ts'], cd['open'], cd['high'], cd['low'], cd['close'], cd['volume'])
                )
                stored += 1

        conn.commit()
        return stored
    finally:
        conn.close()


def fill_volume_gaps(token: str, dry_run: bool = False):
    """Fill volume gaps for a single token."""
    # Fetch 1m candles
    candles_1m = fetch_hl_candles(token, '1m', 100)
    if not candles_1m:
        return 0

    if dry_run:
        has_vol = sum(1 for c in candles_1m if c['volume'] > 0)
        print(f'  {token}: {len(candles_1m)} candles, {has_vol} with volume')
        return len(candles_1m)

    # Store 1m candles (will overwrite volume=0 rows)
    stored = store_candles(token, '1m', candles_1m)

    # Fetch 5m candles too — _hl_info() already enforces 1s rate limit gap
    candles_5m = fetch_hl_candles(token, '5m', 100)
    if candles_5m:
        store_candles(token, '5m', candles_5m)

    return stored


def main():
    parser = argparse.ArgumentParser(description='Fill volume gaps for HL-only tokens')
    parser.add_argument('--token', help='Specific token to fill')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be fetched')
    parser.add_argument('--limit', type=int, default=MAX_TOKENS_PER_RUN, help='Max tokens per run')
    args = parser.parse_args()

    if args.token:
        tokens = [(args.token.upper(), 0)]
    else:
        tokens = get_tokens_without_volume()

    if not tokens:
        print('No tokens with volume=0 found')
        return

    print(f'Tokens needing volume: {len(tokens)}')
    tokens = tokens[:args.limit]

    total_stored = 0
    for i, (token, cnt) in enumerate(tokens):
        print(f'[{i+1}/{len(tokens)}] {token} ({cnt} rows with volume=0)...', end=' ')
        stored = fill_volume_gaps(token, args.dry_run)
        total_stored += stored
        print(f'stored={stored}')

        if i < len(tokens) - 1:
            time.sleep(RATE_LIMIT_DELAY)

    print(f'\nDone. Total rows stored: {total_stored}')


if __name__ == '__main__':
    main()
