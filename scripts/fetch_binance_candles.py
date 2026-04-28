#!/usr/bin/env python3
"""
fetch_binance_candles.py

Fetches historical candle data from Binance and inserts it into
/root/.hermes/data/candles.db for tokens that are light on data.

Usage:
  python3 fetch_binance_candles.py --interval 1m --fetch      # 1m candles (default)
  python3 fetch_binance_candles.py --interval 5m --fetch      # 5m candles
  python3 fetch_binance_candles.py --tokens BTC ETH SOL       # specific tokens only
  python3 fetch_binance_candles.py --interval 5m --tokens BTC ETH --fetch
"""

import sys
import os
import time
import json
import sqlite3
import requests
import math
from datetime import datetime, timezone
from typing import Optional

CANDLES_DB = '/root/.hermes/data/candles.db'
BINANCE_BASE = 'https://api.binance.com/api/v3'
REQUEST_DELAY = 0.05  # 50ms between requests (Binance rate limit: 1200/min)


# ── HL token → Binance symbol mapping ──────────────────────────────────────────
HL_TO_BINANCE = {
    'AAVE': 'AAVEUSDT', 'ACE': 'ACEUSDT', 'ADA': 'ADAUSDT',
    'AGLD': 'AGLDUSDT', 'AGTB': 'AGTBUSDT', 'AI': 'AIUSDT',
    'AIXBT': 'AIXBTUSDT', 'ALGO': 'ALGOUSDT', 'ALT': 'ALTUSDT',
    'ANIME': 'ANIMEUSDT', 'APE': 'APEUSDT', 'APT': 'APTUSDT',
    'AR': 'ARUSDT', 'ARB': 'ARBUSDT', 'ARK': 'ARKUSDT',
    'ASTER': 'ASTERUSDT', 'ATOM': 'ATOMUSDT', 'AVAX': 'AVAXUSDT',
    'AVNT': 'AVNTUSDT', 'AXS': 'AXSUSDT', 'BADGER': 'BADGERUSDT',
    'BANANA': 'BANANAUSDT', 'BCH': 'BCHUSDT', 'BICO': 'BICOUSDT',
    'BLUR': 'BLURUSDT', 'BLZ': 'BLZUSDT', 'BNB': 'BNBUSDT',
    'BNT': 'BNTUSDT', 'BOME': 'BOMEUSDT', 'BSV': 'BSVUSDT',
    'BTC': 'BTCUSDT', 'BTT': 'BTTUSDT', 'CAKE': 'CAKEUSDT',
    'CATI': 'CATIUSDT', 'CELO': 'CELOUSDT', 'CFX': 'CFXUSDT',
    'CHZ': 'CHZUSDT', 'CKB': 'CKBUSDT', 'COMP': 'COMPUSDT',
    'COS': 'COSUSDT', 'CR': 'CRUSDT', 'CRV': 'CRVUSDT',
    'CYBER': 'CYBERUSDT', 'DASH': 'DASHUSDT', 'DENT': 'DENTUSDT',
    'DGB': 'DGBUSDT', 'DOGE': 'DOGEUSDT', 'DOT': 'DOTUSDT',
    'DUSK': 'DUSKUSDT', 'DYDX': 'DYDXUSDT', 'DYM': 'DYMUSDT',
    'EDU': 'EDUUSDT', 'EGLD': 'EGLDUSDT', 'EIGEN': 'EIGENUSDT',
    'ENA': 'ENAUSDT', 'ENJ': 'ENJUSDT', 'ENS': 'ENSUSDT',
    'ETC': 'ETCUSDT', 'ETH': 'ETHUSDT', 'ETHFI': 'ETHFIUSDT',
    'FET': 'FETUSDT', 'FIL': 'FILUSDT', 'FLOKI': 'FLOKIUSDT',
    'FOGO': 'FOGOUSDT', 'FOR': 'FORUSDT', 'FTM': 'FTMUSDT',
    'FTT': 'FTTUSDT', 'FUN': 'FUNUSDT', 'FXS': 'FXSUSDT',
    'GALA': 'GALAUSDT', 'GAS': 'GASUSDT', 'GFT': 'GFTUSDT',
    'GLM': 'GLMUSDT', 'GNO': 'GNOUSDT', 'GRASS': 'GRASSUSDT',
    'GRT': 'GRTUSDT', 'GTO': 'GTOUSDT', 'HARD': 'HARDUSDT',
    'HBAR': 'HBARUSDT', 'HIFI': 'HIFIUSDT', 'HIGH': 'HIGHUSDT',
    'HYPE': 'HYPEUSDT', 'ICP': 'ICPUSDT', 'ICX': 'ICXUSDT',
    'IDEX': 'IDEXUSDT', 'IMX': 'IMXUSDT', 'INJ': 'INJUSDT',
    'IO': 'IOUSDT', 'IOTA': 'IOTAUSDT', 'IOU': 'IOUUSDT',
    'JASMY': 'JASMYUSDT', 'JTO': 'JTOUSDT', 'JUP': 'JUPUSDT',
    'KAITO': 'KAITOUSDT', 'KAS': 'KASUSDT', 'KAVA': 'KAVAUSDT',
    'KDA': 'KDAUSDT', 'KEY': 'KEYUSDT', 'KLAY': 'KLAYUSDT',
    'LDO': 'LDOUSDT', 'LEVER': 'LEVERUSDT', 'LINA': 'LINAUSDT',
    'LINK': 'LINKUSDT', 'LIT': 'LITUSDT', 'LOKA': 'LOKAUSDT',
    'LOOM': 'LOOMUSDT', 'LRC': 'LRCUSDT', 'LTO': 'LTOUSDT',
    'LUNA': 'LUNAUSDT', 'MAV': 'MAVUSDT', 'MAGIC': 'MAGICUSDT',
    'MANA': 'MANAUSDT', 'MANTA': 'MANTAUSDT', 'MASK': 'MASKUSDT',
    'MATIC': 'MATICUSDT', 'MAV': 'MAVUSDT', 'ME': 'MEUSDT',
    'MET': 'METUSDT', 'MINA': 'MINAUSDT', 'MKR': 'MKRUSDT',
    'MOB': 'MOBUSDT', 'MORPHO': 'MORPHOUSDT', 'MOVE': 'MOVEUSDT',
    'NEO': 'NEOUSDT', 'NEAR': 'NEARUSDT', 'NIL': 'NILOUSDT',
    'NTRN': 'NTRNUSDT', 'NUM': 'NUMUSDT', 'O': 'OASUSDT',
    'OG': 'OGUSDT', 'OMG': 'OMUSDT', 'OMNI': 'OMNIUSDT',
    'ONDO': 'ONDOUSDT', 'OP': 'OPUSDT', 'OXT': 'OXTUSDT',
    'PAXG': 'PAXGUSDT', 'PEPE': 'PEPEUSDT', 'PERP': 'PERPUSDT',
    'PEOPLE': 'PEOPLEUSDT', 'PENDLE': 'PENDLEUSDT', 'PENGU': 'PENGUUSDT',
    'PHB': 'PHBUSDT', 'PIXEL': 'PIXELUSDT', 'POL': 'POLUSDT',
    'POLS': 'POLSUSDT', 'POLYX': 'POLYXUSDT', 'POND': 'PONDUSDT',
    'POPCAT': 'POPCATUSDT', 'POWR': 'POWRUSDT', 'PRO': 'PROUSDT',
    'PROVE': 'PROVEUSDT', 'PYTH': 'PYTHUSDT', 'QTUM': 'QTUMUSDT',
    'R': 'RETHUSDT', 'RDNT': 'RDNTUSDT', 'RE2': 'RE2USDT',
    'REZ': 'REZUSDT', 'RENDER': 'RENDERUSDT', 'REQ': 'REQUSDT',
    'RIF': 'RIFUSDT', 'RNDR': 'RNDRUSDT', 'RNO': 'RNOUSDT',
    'RON': 'RONUSDT', 'RSR': 'RSRUSDT', 'RUNE': 'RUNEUSDT',
    'SAGA': 'SAGAUSDT', 'SAND': 'SANDUSDT', 'SC': 'SCUSDT',
    'SCRT': 'SCRTUSDT', 'SFP': 'SFPUSDT', 'SHEZ': 'SHEZUSDT',
    'SKL': 'SKLUSDT', 'SLP': 'SLPUSDT', 'SLERF': 'SLERFUSDT',
    'SOL': 'SOLUSDT', 'SPELL': 'SPELLUSDT', 'SSV': 'SSVUSDT',
    'STG': 'STGUSDT', 'STORJ': 'STORJUSDT', 'STRAX': 'STRAXUSDT',
    'STX': 'STXUSDT', 'SUI': 'SUIUSDT', 'SUN': 'SUNUSDT',
    'SUPER': 'SUPERUSDT', 'SUSHI': 'SUSHIUSDT', 'SWELL': 'SWELLUSDT',
    'SXP': 'SXPUSDT', 'SYN': 'SYNUSDT', 'TIA': 'TIAUSDT',
    'TNSR': 'TNSRUSDT', 'TON': 'TONUSDT', 'TRB': 'TRBUSDT',
    'TRX': 'TRXUSDT', 'TST': 'TSTUSDT', 'TURBO': 'TURBOUSDT',
    'TVK': 'TVKUSDT', 'UMA': 'UMAUSDT', 'UNFI': 'UNFIUSDT',
    'UNI': 'UNIUSDT', 'USUAL': 'USUALUSDT', 'UTK': 'UTKUSDT',
    'VANA': 'VANAUSDT', 'VD': 'VDUSDT', 'VET': 'VETUSDT',
    'VIC': 'VICUSDT', 'VIDT': 'VIDTUSDT', 'VIRTUAL': 'VIRTUALUSDT',
    'VOXEL': 'VOXELUSDT', 'VTHO': 'VTHOUSDT', 'W': 'WUSDT',
    'WAVES': 'WAVESUSDT', 'WAXP': 'WAXPUSDT', 'WCT': 'WCTUSDT',
    'WIF': 'WIFUSDT', 'WLD': 'WLDUSDT', 'WOO': 'WOOUSDT',
    'XAI': 'XAIUSDT', 'XEM': 'XEMUSDT', 'XLM': 'XLMUSDT',
    'XNO': 'XNOUSDT', 'XRP': 'XRPUSDT', 'XTZ': 'XTZUSDT',
    'XVS': 'XVSUSDT', 'YFI': 'YFIUSDT', 'YGG': 'YGGUSDT',
    'ZEC': 'ZECUSDT', 'ZEN': 'ZENUSDT', 'ZK': 'ZKUSDT',
    'ZRO': 'ZROUSDT', 'ZRX': 'ZRXUSDT',
}

# Tokens NOT on Binance (or likely missing)
NOT_ON_BINANCE = {
    '0G', '2Z', 'AI16Z', 'AST', 'BABY', 'BB', 'BCUT', 'BINO',
    'BIT', 'BLK', 'BLOCK', 'BR', 'BSW', 'CATI', 'CHILL', 'CHRP',
    'COCOS', 'COW', 'CQT', 'CREAM', 'CRON', 'CVC', 'CVX',
    'DAR', 'DATA', 'DEGO', 'DEXT', 'DOG', 'DOP', 'DRIFT', 'DXY',
    'DXGM', 'ECO', 'EPIK', 'EPX', 'ERN', 'ETN', 'FIDA', 'FIO',
    'FORT', 'FORTH', 'FUN', 'G', 'GAIA', 'GNO', 'GNS', 'GODS',
    'GRPH', 'GVM', 'HFT', 'HMT', 'HMSTR', 'HSF', 'HYD', 'ILV',
    'ION', 'IOTX', 'IVN', 'JAS', 'JEX', 'JUV', 'KAIA', 'KALM',
    'KCODE', 'KMON', 'KNC', 'KNF', 'KP3R', 'LCX', 'LINA', 'LINA',
    'LOKA', 'LSK', 'LX', 'MERL', 'MIR', 'MKR', 'MNA', 'MUBARAK',
    'MX', 'NEON', 'NEXA', 'NFP', 'NTRN', 'NUB', 'O', 'OX', 'PAXG',
    'PC', 'PEAQ', 'PHV', 'PLUME', 'PMP', 'POKER', 'POL', 'PRCL',
    'PRO', 'QUICK', 'RARE', 'RBLK', 'RETH', 'RING', 'RION', 'RNDR',
    'RON', 'RPL', 'SAIL', 'SCRT', 'SD', 'SDAO', 'SEND', 'SERAPH',
    'SEX', 'SHEZ', 'SHP', 'SLF', 'SLN', 'SLOTH', 'SNX', 'SNT',
    'SOV', 'SRM', 'STT', 'STX', 'SUI', 'SUSHI', 'SYN', 'TAO',
    'TH', 'TNSR', 'TOMI', 'TORN', 'TRIBE', 'TRI', 'TRUMP', 'TRU',
    'TRY', 'TURBO', 'TVK', 'UFT', 'ULK', 'UNI', 'USDC', 'USDT',
    'vela', 'VINU', 'VINEW', 'VISTA', 'VTHO', 'W', 'WAL', 'WCT',
    'WLD', 'WLFI', 'WNT', 'WPP', 'X', 'X2Y2', 'XAI', 'XBG', 'XCN',
    'XDE', 'XEN', 'XETA', 'XPL', 'YGG', 'YFII', 'ZA', 'ZCN', 'ZE',
    'ZIG', 'ZORA', 'ZZ',
}


def get_binance_symbol(token: str) -> Optional[str]:
    """Map HL token to Binance symbol."""
    if token in HL_TO_BINANCE:
        return HL_TO_BINANCE[token]
    if token in NOT_ON_BINANCE:
        return None
    return token.upper() + 'USDT'


def fetch_binance_klines(symbol: str, interval='1m', limit=1500,
                         start_time_ms: int = None, end_time_ms: int = None) -> list:
    """Fetch klines from Binance. All times in milliseconds."""
    url = f'{BINANCE_BASE}/klines'
    params = {'symbol': symbol, 'interval': interval, 'limit': limit}
    if start_time_ms:
        params['startTime'] = int(start_time_ms)
    if end_time_ms:
        params['endTime'] = int(end_time_ms)

    for attempt in range(3):
        try:
            resp = requests.get(url, params=params, timeout=15)
            if resp.status_code == 429:
                wait = (attempt + 1) * 10
                print(f"    Rate limited — sleeping {wait}s then retrying ({attempt+1}/3)")
                time.sleep(wait)
                continue
            resp.raise_for_status()
            data = resp.json()
            if not isinstance(data, list):
                return []
            return data
        except Exception as e:
            print(f"    ERROR fetching {symbol}: {e}")
            return []
    return []


def get_db_max_ts(token: str, table: str = 'candles_1m') -> Optional[int]:
    """Get latest ts (seconds) in DB for a token."""
    try:
        conn = sqlite3.connect(CANDLES_DB)
        cur = conn.cursor()
        cur.execute(f'SELECT MAX(ts) FROM {table} WHERE token=?', (token.upper(),))
        row = cur.fetchone()
        conn.close()
        return row[0] if row and row[0] else None
    except:
        return None


def get_db_count(token: str, table: str = 'candles_1m') -> int:
    """Get candle count in DB for a token."""
    try:
        conn = sqlite3.connect(CANDLES_DB)
        cur = conn.cursor()
        cur.execute(f'SELECT COUNT(*) FROM {table} WHERE token=?', (token.upper(),))
        row = cur.fetchone()
        conn.close()
        return row[0] if row else 0
    except:
        return 0


def insert_candles(token: str, candles: list, table: str = 'candles_1m') -> int:
    """
    Insert candles into candles_1m.
    Binance returns [ts_ms, O, H, L, C, V, ...]
    DB stores ts in SECONDS (not ms) to match existing format.
    Returns rows actually inserted (not already existing).
    """
    if not candles:
        return 0
    inserted = 0
    try:
        conn = sqlite3.connect(CANDLES_DB)
        cur = conn.cursor()
        for c in candles:
            ts_sec = int(c[0] // 1000)   # ms → sec
            open_, high, low, close, volume = float(c[1]), float(c[2]), float(c[3]), float(c[4]), float(c[5])
            cur.execute(f'''
                INSERT OR IGNORE INTO {table}
                (token, ts, open, high, low, close, volume)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (token.upper(), ts_sec, open_, high, low, close, volume))
            if cur.rowcount > 0:
                inserted += 1
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print(f"    ERROR inserting {token}: {e}")
    return inserted


def main():
    dry_run = '--fetch' not in sys.argv
    specific_tokens = None
    interval = '1m'
    if '--tokens' in sys.argv:
        idx = sys.argv.index('--tokens')
        specific_tokens = [t.upper() for t in sys.argv[idx+1:]]
    if '--interval' in sys.argv:
        idx = sys.argv.index('--interval')
        interval = sys.argv[idx+1]

    TARGET_CANDLES = {'1m': 20000, '5m': 4000}.get(interval, 20000)
    TARGET_TABLE = f'candles_{interval}'

    # Allow --days override (e.g. --days 30 for 30 days back)
    DAYS_BACK = 14
    if '--days' in sys.argv:
        idx = sys.argv.index('--days')
        DAYS_BACK = int(sys.argv[idx + 1])
    TWO_WEEKS_MS = DAYS_BACK * 24 * 3600 * 1000

    print(f"{'DRY RUN' if dry_run else 'LIVE FETCH'} — Binance candle backfill")
    print(f"Target: ~{DAYS_BACK} days of {interval} candles per token → {TARGET_TABLE}")
    print()

    # Get all tokens in our candles.db
    conn = sqlite3.connect(CANDLES_DB)
    cur = conn.cursor()
    cur.execute('SELECT DISTINCT token FROM candles_1m ORDER BY token')
    db_tokens = [r[0] for r in cur.fetchall()]
    conn.close()

    NOW_MS = int(datetime.now(timezone.utc).timestamp() * 1000)
    MS_PER_CANDLE = {'1m': 60_000, '5m': 300_000}.get(interval, 60_000)

    # Allow --start-date to override the default 14-day window
    # e.g. --start-date 2025-01-01 fetches from Jan 2025 to now
    start_date_override = None
    if '--start-date' in sys.argv:
        idx = sys.argv.index('--start-date')
        date_str = sys.argv[idx + 1]
        start_date_override = datetime.strptime(date_str, '%Y-%m-%d').replace(tzinfo=timezone.utc)
        print(f"Historical date range: {date_str} → today ({datetime.now(timezone.utc).strftime('%Y-%m-%d')})")
        print()

    tokens_needing_data = []
    tokens_skipped = []
    tokens_on_binance = []

    for token in db_tokens:
        if specific_tokens and token.upper() not in specific_tokens:
            continue
        symbol = get_binance_symbol(token)
        if not symbol:
            tokens_skipped.append(token)
            continue
        tokens_on_binance.append((token, symbol))

    print(f"Tokens in DB: {len(db_tokens)}")
    print(f"Known Binance symbols: {len(tokens_on_binance)}")
    print(f"Skipped (not on Binance): {len(tokens_skipped)}: {', '.join(sorted(tokens_skipped[:10]))}{'...' if len(tokens_skipped) > 10 else ''}")
    print()

    # Build fetch plan
    fetch_plan = []
    for token, symbol in tokens_on_binance:
        count = get_db_count(token, TARGET_TABLE)
        max_ts = get_db_max_ts(token, TARGET_TABLE)

        # Skip if already enough data AND no historical override
        if count >= TARGET_CANDLES and not start_date_override:
            tokens_skipped.append(f"{token} (enough data: {count})")
            continue

        if max_ts:
            if start_date_override:
                start_ms = int(start_date_override.timestamp() * 1000)
            else:
                start_ms = (max_ts + MS_PER_CANDLE) * 1000
        else:
            if start_date_override:
                start_ms = int(start_date_override.timestamp() * 1000)
            else:
                start_ms = NOW_MS - TWO_WEEKS_MS

        fetch_plan.append({
            'token': token,
            'symbol': symbol,
            'db_count': count,
            'start_ms': start_ms,
            'need_more': TARGET_CANDLES - count,
        })

    # Sort by most needing data first
    fetch_plan.sort(key=lambda x: x['db_count'])

    print(f"Tokens needing data: {len(fetch_plan)}")
    print()

    if dry_run:
        print("Tokens to fetch (dry run):")
        for item in fetch_plan[:30]:
            start_dt = datetime.fromtimestamp(item['start_ms']/1000, tz=timezone.utc).strftime('%Y-%m-%d')
            print(f"  {item['token']:<10} {item['symbol']:<15} db={item['db_count']:6d} need ~{item['need_more']:6d} from {start_dt}")
        if len(fetch_plan) > 30:
            print(f"  ... and {len(fetch_plan)-30} more")
        print(f"\nDRY RUN — run with --fetch to actually insert data.")
        return

    print(f"Fetching {len(fetch_plan)} tokens from Binance...")
    total_inserted = 0
    total_fetched = 0

    for item in fetch_plan:
        token = item['token']
        symbol = item['symbol']
        start_ms = item['start_ms']
        end_ms = NOW_MS

        start_dt = datetime.fromtimestamp(start_ms/1000, tz=timezone.utc).strftime('%Y-%m-%d %H:%M')
        print(f"\n{token} ({symbol}) — from {start_dt}")

        chunk_size = 1500
        binance_limit = 1000  # Binance max per request
        current_ms = start_ms
        fetched = 0
        inserted = 0
        loops = 0

        while current_ms < end_ms:
            loops += 1
            if loops > 200:
                print(f"    Safety stop at 200 chunks")
                break

            # Don't fetch more than binance_limit at a time
            chunk_end = min(current_ms + binance_limit * MS_PER_CANDLE, end_ms)

            candles = fetch_binance_klines(
                symbol,
                interval=interval,
                limit=binance_limit,
                start_time_ms=current_ms,
                end_time_ms=chunk_end,
            )

            if not candles:
                print(f"    No data returned (loop {loops})")
                break

            n = insert_candles(token, candles, TARGET_TABLE)
            fetched += len(candles)
            inserted += n

            last_ts_sec = int(candles[-1][0] // 1000)
            last_dt = datetime.fromtimestamp(last_ts_sec, tz=timezone.utc).strftime('%m-%d %H:%M')
            print(f"    loop {loops}: got {len(candles)} candles, {n} new, last={last_dt}")

            if len(candles) < binance_limit:
                break  # no more data

            current_ms = int(candles[-1][0]) + MS_PER_CANDLE

            time.sleep(REQUEST_DELAY)  # rate limit

        total_fetched += fetched
        total_inserted += inserted
        new_count = get_db_count(token, TARGET_TABLE)
        print(f"  → {token}: fetched={fetched}, inserted={inserted}, total={new_count}")

    print(f"\n{'='*60}")
    print(f"Done.")
    print(f"Total candles fetched:  {total_fetched}")
    print(f"Total new rows inserted: {total_inserted}")


if __name__ == '__main__':
    main()
