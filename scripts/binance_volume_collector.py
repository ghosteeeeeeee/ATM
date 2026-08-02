#!/usr/bin/env python3
"""
binance_volume_collector.py — Test script to pull OHLCV from Binance for all
171 tokens that exist on both Hyperliquid and Binance.

Writes to /root/.hermes/data/binance_test.db — completely separate from
production candles.db.

Architecture:
  - No systemd wiring yet — run manually or via cron while testing
  - Target: pull every 60s, write 1m + 5m klines
  - 171 tokens × 2 intervals = 342 requests @ ~0.01s each ≈ 3-4s total with concurrency

Rate math:
  - Binance limit: 1200 weight/min
  - Each klines(limit=2) = 1 weight
  - 342 req/min × 1 weight = 342 weight/min = 28% of limit
"""
import sys, os, time, sqlite3, json, concurrent.futures
sys.path.insert(0, os.path.dirname(__file__))

import requests
from datetime import datetime

# ── Paths ──────────────────────────────────────────────────────────────────────
TEST_DB   = '/root/.hermes/data/binance_test.db'
STATEFILE = '/root/.hermes/data/binance_collector_state.json'

# ── Binance tokens (171 that exist on both HL + Binance) ─────────────────────
# Verified 2026-04-30: fresh HL universe check against Binance klines API
# 59 tokens are NOT on Binance (meme coins, HL-only) — see NOT_ON_BINANCE below
BINANCE_TOKENS = sorted([
    '0G','2Z','AIXBT','APT','ASTER','AI','ANIME','ACE','ADA','AAVE',
    'ALGO','APE','ALT','AR','ATOM','AVNT','ARB','BABY','BERA','BADGER',
    'AVAX','BLUR','BCH','ARK','AXS','BNB','BANANA','BNT','BLZ','BTC',
    'CAKE','BOME','BIGTIME','BIO','CHIP','CATI','CRV','CFX','CELO','COMP',
    'DOT','DASH','DOGE','ETH','EIGEN','DYDX','DYM','ENS','ENA','ETHFI',
    'CYBER','FET','ETC','FTM','GAS','GMX','FOGO','FTT','GMT','GALA',
    'FIL','FXS','HYPER','HEMI','ILV','JUP','HBAR','HMSTR','IMX','INIT',
    'INJ','IO','IOTA','ICP','JTO','LAYER','KAITO','LDO','LINK','LTC',
    'MATIC','LOOM','LISTA','LIT','MAV','MANTA','LINEA','MEME','ME','MET',
    'MINA','NEO','NIL','MORPHO','MKR','NXPC','MOVE','NTRN','NEAR','NOT',
    'OM','OP','ORDI','OGN','ONDO','PAXG','OMNI','PENGU','PENDLE','POLYX',
    'PIXEL','PNUT','PEOPLE','POL','RDNT','RNDR','PROVE','RENDER','RESOLV','REQ',
    'PYTH','REZ','S','PUMP','SAGA','RSR','SCR','SEI','SAND','RUNE',
    'SNX','STRK','STRAX','SOPH','SUI','SKY','SOL','SUSHI','SUPER','SYRUP',
    'TIA','STG','TON','STX','TAO','TRX','USTC','TNSR','TRB','UMA',
    'TRUMP','TST','TURBO','UNI','XPL','XAI','WIF','ZEC','WLD','VIRTUAL',
    'YGG','WCT','USUAL','XRP','XMR','WLFI','W','ZK','XLM','ZEN',
    'ZRO',
])

# Tokens confirmed NOT on Binance (59) — volume cannot be sourced from Binance
# These are mostly meme coins, HL-only listings, or recently launched tokens
NOT_ON_BINANCE = sorted([
    'AERO','AI16Z','APEX','AZTEC','BLAST','BRETT','BSV','CANTO','CC',
    'CHILLGUY','DOOD','FARTCOIN','FRIEND','GOAT','GRASS','GRIFFAIN','HPOS',
    'HYPE','IP','JELLY','KAS','LAUNCHCOIN','MAVIA','MEGA','MELANIA','MERL',
    'MEW','MNT','MON','MOODENG','MYRO','NEIROETH','NFTI','ORBS','OX',
    'PANDORA','POPCAT','PROMPT','PURR','RLB','SHIA','SKR','SPX','STABLE',
    'STBL','UNIBOT','VINE','VVV','YZY','ZEREBRO','ZETA','ZORA',
    'kBONK','kDOGS','kFLOKI','kLUNC','kNEIRO','kPEPE','kSHIB',
])

# ── Schema ────────────────────────────────────────────────────────────────────
SCHEMA = """
CREATE TABLE IF NOT EXISTS candles_1m (
    token    TEXT NOT NULL,
    ts       INTEGER NOT NULL,  -- open time in seconds
    open     REAL NOT NULL,
    high     REAL NOT NULL,
    low      REAL NOT NULL,
    close    REAL NOT NULL,
    volume   REAL NOT NULL,
    is_closed INTEGER DEFAULT 1,
    PRIMARY KEY (token, ts)
);

CREATE TABLE IF NOT EXISTS candles_5m (
    token    TEXT NOT NULL,
    ts       INTEGER NOT NULL,
    open     REAL NOT NULL,
    high     REAL NOT NULL,
    low      REAL NOT NULL,
    close    REAL NOT NULL,
    volume   REAL NOT NULL,
    is_closed INTEGER DEFAULT 1,
    PRIMARY KEY (token, ts)
);

CREATE INDEX IF NOT EXISTS idx_1m_ts   ON candles_1m(token, ts DESC);
CREATE INDEX IF NOT EXISTS idx_5m_ts   ON candles_5m(token, ts DESC);
"""

def init_db():
    conn = sqlite3.connect(TEST_DB, timeout=30)
    conn.execute("PRAGMA journal_mode=WAL")
    for sql in SCHEMA.strip().split(';'):
        sql = sql.strip()
        if sql:
            conn.execute(sql)
    conn.commit()
    conn.close()

def _klines(token: str, interval: str, limit: int = 2):
    """Fetch klines from Binance. Returns list of candle dicts or empty list on failure."""
    # limit=2: last closed + current developing candle
    url = f"https://api.binance.com/api/v3/klines?symbol={token}USDT&interval={interval}&limit={limit}"
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code != 200:
            print(f"  [ERR] {token} {interval}: HTTP {resp.status_code}")
            return []
        klines = resp.json()
        return [
            {
                'ts':     int(k[0] / 1000),      # open time in seconds
                'open':   float(k[1]),
                'high':   float(k[2]),
                'low':    float(k[3]),
                'close':  float(k[4]),
                'volume': float(k[5]),
            }
            for k in klines
        ]
    except Exception as e:
        print(f"  [ERR] {token} {interval}: {e}")
        return []

def _determine_is_closed(ts: int, interval: str) -> int:
    """
    Determine if a candle at timestamp `ts` is closed.
    
    Binance klines: the candle with open_time=ts covers [ts, ts+interval).
    A candle is closed if its close_time < current_server_time.
    
    For 1m: ts % 60 == 0, interval = 60s
    For 5m: ts % 300 == 0, interval = 300s
    
    We can't get server time cheaply, so we check against local time:
    - Current minute boundary: if now_ts - ts > interval * 1.5, definitely closed
    - Current developing window: if now_ts - ts <= interval, likely still open
    """
    now_ts = int(time.time())
    if interval == '1m':
        interval_sec = 60
    elif interval == '5m':
        interval_sec = 300
    else:
        interval_sec = 300
    
    age = now_ts - ts
    if age > interval_sec:
        return 1   # closed
    else:
        return 0   # developing

def fetch_and_store():
    """Main fetch + store loop. Fetches 1m + 5m for all tokens concurrently."""
    start = time.time()
    
    conn = sqlite3.connect(TEST_DB, timeout=60)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    c = conn.cursor()
    
    # Track stats
    ok_tokens = []
    err_tokens = []
    
    intervals = ['1m', '5m']
    
    # Fetch all tokens concurrently (but limit workers to avoid overwhelming)
    with concurrent.futures.ThreadPoolExecutor(max_workers=30) as ex:
        futures = {}
        for token in BINANCE_TOKENS:
            for interval in intervals:
                fut = ex.submit(_klines, token, interval, 2)
                futures[fut] = (token, interval)
        
        for fut in concurrent.futures.as_completed(futures):
            token, interval = futures[fut]
            candles = fut.result()
            
            if not candles:
                if token not in err_tokens:
                    err_tokens.append(token)
                continue
            
            table = f'candles_{interval}'
            rows = []
            for cd in candles:
                is_closed = _determine_is_closed(cd['ts'], interval)
                rows.append((
                    token, cd['ts'], cd['open'], cd['high'],
                    cd['low'], cd['close'], cd['volume'], is_closed
                ))
            
            c.executemany(
                f"INSERT OR REPLACE INTO {table} "
                f"(token, ts, open, high, low, close, volume, is_closed) "
                f"VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                rows
            )
            
            if token not in ok_tokens:
                ok_tokens.append(token)
    
    conn.commit()
    
    elapsed = time.time() - start
    print(f"\n[binance_collector] {len(ok_tokens)}/{len(BINANCE_TOKENS)} tokens, "
          f"{len(err_tokens)} errors, {elapsed:.1f}s")
    if err_tokens:
        print(f"  Failed tokens: {err_tokens[:10]}{'...' if len(err_tokens) > 10 else ''}")
    
    conn.close()

def verify_chips():
    """Quick sanity check on CHIP candles."""
    conn = sqlite3.connect(TEST_DB, timeout=10)
    c = conn.cursor()
    now_ts = int(time.time())
    
    print("\n[verify] CHIP 1m candles (latest 5):")
    c.execute("SELECT ts, open, high, low, close, volume, is_closed FROM candles_1m WHERE token='CHIP' ORDER BY ts DESC LIMIT 5")
    for r in c.fetchall():
        age = now_ts - r[0]
        closed = "CLOSED" if r[6] == 1 else "DEV"
        print(f"  ts={r[0]} ({datetime.fromtimestamp(r[0]).strftime('%H:%M:%S')}) "
              f"age={age}s [{closed}] O={r[1]:.6f} H={r[2]:.6f} L={r[3]:.6f} C={r[4]:.6f} V={r[5]:.2f}")
    
    print("\n[verify] CHIP 5m candles (latest 5):")
    c.execute("SELECT ts, open, high, low, close, volume, is_closed FROM candles_5m WHERE token='CHIP' ORDER BY ts DESC LIMIT 5")
    for r in c.fetchall():
        age = now_ts - r[0]
        closed = "CLOSED" if r[6] == 1 else "DEV"
        print(f"  ts={r[0]} ({datetime.fromtimestamp(r[0]).strftime('%H:%M:%S')}) "
              f"age={age}s [{closed}] O={r[1]:.6f} H={r[2]:.6f} L={r[3]:.6f} C={r[4]:.6f} V={r[5]:.2f}")
    
    conn.close()

if __name__ == '__main__':
    init_db()
    fetch_and_store()
    verify_chips()
