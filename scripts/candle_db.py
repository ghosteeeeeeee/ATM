#!/usr/bin/env python3
"""
candle_db.py — Local SQLite store for Binance OHLCV candles.
Avoids repeated API calls, enables historical queries, and feeds MACD/timeframe analysis.

Tables:
  candles_1m   — 1-minute OHLCV (for aggregation into any higher TF)
  candles_15m  — 15-minute aggregated candles
  candles_1h   — 1-hour candles
  candles_4h   — 4-hour candles
  tokens       — token metadata (last_update, active flag)

Each row: token, timestamp, open, high, low, close, volume
Primary key: (token, timestamp, timeframe)
"""

import sqlite3
import time
import os
from datetime import datetime, timedelta
from typing import Optional

DB_PATH = '/root/.hermes/data/candles.db'

# ── Schema ──────────────────────────────────────────────────────────────────

SCHEMA = """
CREATE TABLE IF NOT EXISTS candles_1m (
    token    TEXT NOT NULL,
    ts       INTEGER NOT NULL,   -- Unix timestamp (seconds)
    open     REAL NOT NULL,
    high     REAL NOT NULL,
    low      REAL NOT NULL,
    close    REAL NOT NULL,
    volume   REAL NOT NULL,
    PRIMARY KEY (token, ts)
);

CREATE TABLE IF NOT EXISTS candles_15m (
    token    TEXT NOT NULL,
    ts       INTEGER NOT NULL,
    open     REAL NOT NULL,
    high     REAL NOT NULL,
    low      REAL NOT NULL,
    close    REAL NOT NULL,
    volume   REAL NOT NULL,
    PRIMARY KEY (token, ts)
);

CREATE TABLE IF NOT EXISTS candles_1h (
    token    TEXT NOT NULL,
    ts       INTEGER NOT NULL,
    open     REAL NOT NULL,
    high     REAL NOT NULL,
    low      REAL NOT NULL,
    close    REAL NOT NULL,
    volume   REAL NOT NULL,
    PRIMARY KEY (token, ts)
);

CREATE TABLE IF NOT EXISTS candles_4h (
    token    TEXT NOT NULL,
    ts       INTEGER NOT NULL,
    open     REAL NOT NULL,
    high     REAL NOT NULL,
    low      REAL NOT NULL,
    close    REAL NOT NULL,
    volume   REAL NOT NULL,
    PRIMARY KEY (token, ts)
);

CREATE TABLE IF NOT EXISTS tokens (
    token        TEXT PRIMARY KEY,
    last_update  INTEGER,        -- Unix timestamp of last API fetch
    active       INTEGER DEFAULT 1
);

CREATE INDEX IF NOT EXISTS idx_candles_1m_ts   ON candles_1m(token, ts DESC);
CREATE INDEX IF NOT EXISTS idx_candles_15m_ts  ON candles_15m(token, ts DESC);
CREATE INDEX IF NOT EXISTS idx_candles_1h_ts    ON candles_1h(token, ts DESC);
CREATE INDEX IF NOT EXISTS idx_candles_4h_ts     ON candles_4h(token, ts DESC);
"""


# ── DB helpers ────────────────────────────────────────────────────────────────

def get_conn(path: str = DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(path, timeout=30)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    return conn

def init_db():
    with get_conn() as conn:
        conn.executescript(SCHEMA)

def _tf_table(tf: str) -> str:
    return {'1m': 'candles_1m', '15m': 'candles_15m', '1h': 'candles_1h', '4h': 'candles_4h'}[tf]

def _tf_minutes(tf: str) -> int:
    return {'1m': 1, '15m': 15, '1h': 60, '4h': 240}[tf]


# ── Fetch from Binance + store ────────────────────────────────────────────────

def fetch_and_store(token: str, tf: str = '1m', limit: int = 500) -> int:
    """
    Fetch `limit` candles from Binance for token/timeframe, store to local DB.
    Returns number of candles stored (0 = no new data or error).
    """
    interval_map = {'1m': '1m', '15m': '15m', '1h': '1h', '4h': '4h'}
    binance_tf = interval_map[tf]
    table = _tf_table(tf)

    url = f"https://api.binance.com/api/v3/klines?symbol={token}USDT&interval={binance_tf}&limit={limit}"
    try:
        import requests
        resp = requests.get(url, timeout=10)
        if resp.status_code != 200:
            return 0
        klines = resp.json()
    except Exception as e:
        print(f"[candle_db] {token} {tf} fetch error: {e}")
        return 0

    if not klines:
        return 0

    rows = [
        (token, int(k[0] / 1000), float(k[1]), float(k[2]), float(k[3]), float(k[4]), float(k[5]))
        for k in klines
    ]

    with get_conn() as conn:
        c = conn.cursor()
        # Upsert: insert or replace on conflict
        c.executemany(
            f"INSERT OR REPLACE INTO {table} (token, ts, open, high, low, close, volume) VALUES (?, ?, ?, ?, ?, ?, ?)",
            rows
        )
        # Update token metadata
        c.execute(
            "INSERT OR REPLACE INTO tokens (token, last_update, active) VALUES (?, ?, 1)",
            (token, int(time.time()))
        )
        conn.commit()
        return len(rows)


def fetch_and_store_all_tf(token: str, limits: dict = None) -> dict:
    """
    Fetch all timeframes for a token in one call.
    Returns dict of {tf: rows_stored}.
    """
    if limits is None:
        limits = {'1m': 500, '15m': 500, '1h': 500, '4h': 500}
    results = {}
    for tf, limit in limits.items():
        results[tf] = fetch_and_store(token, tf, limit)
    return results


# ── Read candles ──────────────────────────────────────────────────────────────

def get_candles(token: str, tf: str = '1h', lookback_minutes: int = None, lookback_rows: int = 500) -> list:
    """
    Read candles from local DB.
    Pass lookback_minutes OR lookback_rows (lookback_rows takes precedence).
    Returns list of (ts, open, high, low, close, volume) sorted oldest→newest.
    """
    table = _tf_table(tf)
    rows = lookback_rows
    ts_cutoff = None

    if lookback_minutes is not None:
        ts_cutoff = int(time.time() * 1000) - lookback_minutes * 60 * 1000
        rows = None  # use ts_cutoff instead

    with get_conn() as conn:
        conn.row_factory = sqlite3.Row
        c = conn.cursor()

        if ts_cutoff is not None:
            c.execute(
                f"SELECT ts, open, high, low, close, volume FROM {table} "
                f"WHERE token=? AND ts >= ? ORDER BY ts ASC",
                (token, ts_cutoff // 1000)
            )
        else:
            c.execute(
                f"SELECT ts, open, high, low, close, volume FROM {table} "
                f"WHERE token=? ORDER BY ts DESC LIMIT ?",
                (token, rows)
            )
            rows_data = c.fetchall()
            rows_data.reverse()
            return rows_data

        rows_data = c.fetchall()
        return [tuple(r) for r in rows_data]


def get_latest_price(token: str, tf: str = '1m') -> Optional[float]:
    """Return the most recent close price for a token."""
    table = _tf_table(tf)
    with get_conn() as conn:
        c = conn.cursor()
        c.execute(f"SELECT close FROM {table} WHERE token=? ORDER BY ts DESC LIMIT 1", (token,))
        row = c.fetchone()
        return float(row[0]) if row else None


def get_last_ts(token: str, tf: str) -> Optional[int]:
    """Return the Unix timestamp of the most recent candle for token/tf."""
    table = _tf_table(tf)
    with get_conn() as conn:
        c = conn.cursor()
        c.execute(f"SELECT ts FROM {table} WHERE token=? ORDER BY ts DESC LIMIT 1", (token,))
        row = c.fetchone()
        return int(row[0]) if row else None


# ── Aggregate 1m → higher TFs ────────────────────────────────────────────────

def aggregate_1m_to_tf(token: str, target_tf: str, lookback_minutes: int = 60 * 24 * 3) -> list:
    """
    Aggregate 1m candles from local DB into a higher timeframe.
    Returns list of (ts, open, high, low, close, volume) for target_tf.
    ts = bucket start (Unix seconds).
    """
    if target_tf == '1m':
        return get_candles(token, '1m', lookback_minutes=lookback_minutes)

    tf_minutes = _tf_minutes(target_tf)
    tf_seconds = tf_minutes * 60

    rows_1m = get_candles(token, '1m', lookback_minutes=lookback_minutes)
    if not rows_1m:
        return []

    buckets = {}
    for ts, o, h, l, c, v in rows_1m:
        bucket_ts = (ts // tf_seconds) * tf_seconds
        if bucket_ts not in buckets:
            buckets[bucket_ts] = [o, h, l, c, v]
        else:
            buckets[bucket_ts][0] = o  # open = first of bucket
            buckets[bucket_ts][1] = max(buckets[bucket_ts][1], h)
            buckets[bucket_ts][2] = min(buckets[bucket_ts][2], l)
            buckets[bucket_ts][3] = c  # close = last of bucket
            buckets[bucket_ts][4] += v

    result = [(ts, b[0], b[1], b[2], b[3], b[4]) for ts, b in sorted(buckets.items())]
    return result


# ── Cascade direction detection ───────────────────────────────────────────────

def detect_cascade_direction(tf_states: dict) -> dict:
    """
    Given a dict of {tf_name: macd_state} — e.g. {'15m': MACDState, '1h': MACDState, '4h': MACDState}:
    Detect the cascade direction.

    Key insight: smaller TFs lead the reversal. A true bullish cascade:
      - 15m flips to bullish FIRST (macd > signal AND hist > 0)
      - 1h follows
      - 4h confirms

    Bearish cascade: 15m flips first, 1h follows, 4h confirms.

    Returns:
      cascade_active: bool  — True if smaller TFs are flipped and larger TFs still pending
      cascade_direction: 'LONG' | 'SHORT' | None
      lead_tf: str  — the smallest TF that flipped first
      confirmation_count: int  — how many TFs have followed (0-2)
      reversal_score: float  — 0.0 to 1.0 (how complete the cascade is)
    """
    TF_ORDER = ['15m', '1h', '4h']

    # Score each TF for bullish/bearish
    bullish_count = 0
    bearish_count = 0
    neutral_count = 0

    tf_bullish = {}
    tf_bearish = {}

    for tf in TF_ORDER:
        if tf not in tf_states:
            continue
        s = tf_states[tf]
        if s is None:
            neutral_count += 1
            continue

        is_bull = s.macd_above_signal and s.histogram_positive
        is_bear = not s.macd_above_signal and not s.histogram_positive

        tf_bullish[tf] = is_bull
        tf_bearish[tf] = is_bear

        if is_bull:
            bullish_count += 1
        elif is_bear:
            bearish_count += 1
        else:
            neutral_count += 1

    total = bullish_count + bearish_count + neutral_count
    if total == 0:
        return {
            'cascade_active': False, 'cascade_direction': None,
            'lead_tf': None, 'confirmation_count': 0, 'reversal_score': 0.0,
            'tf_bullish': {}, 'tf_bearish': {}
        }

    # Determine cascade direction
    if bullish_count > bearish_count and bullish_count >= 2:
        cascade_dir = 'LONG'
    elif bearish_count > bullish_count and bearish_count >= 2:
        cascade_dir = 'SHORT'
    else:
        cascade_dir = None

    # Find the lead TF (smallest timeframe that's bullish/bearish)
    lead_tf = None
    for tf in TF_ORDER:
        if tf in tf_bullish and tf_bullish[tf]:
            lead_tf = tf
            break
        if tf in tf_bearish and tf_bearish[tf]:
            lead_tf = tf
            break

    # Count how many larger TFs have followed the lead
    if lead_tf is not None and cascade_dir is not None:
        lead_idx = TF_ORDER.index(lead_tf)
        confirmed = 0
        is_target_bull = cascade_dir == 'LONG'
        for i in range(lead_idx + 1, len(TF_ORDER)):
            check_tf = TF_ORDER[i]
            if check_tf in tf_states and tf_states[check_tf] is not None:
                s = tf_states[check_tf]
                if is_target_bull:
                    if s.macd_above_signal and s.histogram_positive:
                        confirmed += 1
                else:
                    if not s.macd_above_signal and not s.histogram_positive:
                        confirmed += 1
        confirmation_count = confirmed
        reversal_score = confirmation_count / 2.0  # 0.0, 0.5, 1.0
    else:
        confirmation_count = 0
        reversal_score = 0.0

    # Cascade is ACTIVE when:
    # 1. Lead TF (15m or 1h) has flipped in a direction
    # 2. At least 1 larger TF hasn't followed yet (still in old direction)
    lead_idx = TF_ORDER.index(lead_tf) if lead_tf else -1
    cascade_active = False

    if lead_idx >= 0 and cascade_dir is not None:
        is_target_bull = cascade_dir == 'LONG'
        # Check if at least one larger TF hasn't followed yet
        for i in range(lead_idx + 1, len(TF_ORDER)):
            check_tf = TF_ORDER[i]
            if check_tf in tf_states and tf_states[check_tf] is not None:
                s = tf_states[check_tf]
                larger_is_bull = s.macd_above_signal and s.histogram_positive
                larger_is_bear = not s.macd_above_signal and not s.histogram_positive
                # If larger TF is still in opposite direction → cascade still propagating
                if is_target_bull and larger_is_bear:
                    cascade_active = True
                elif not is_target_bull and larger_is_bull:
                    cascade_active = True

    return {
        'cascade_active': cascade_active,
        'cascade_direction': cascade_dir,
        'lead_tf': lead_tf,
        'confirmation_count': confirmation_count,
        'reversal_score': reversal_score,
        'bullish_count': bullish_count,
        'bearish_count': bearish_count,
        'tf_bullish': tf_bullish,
        'tf_bearish': tf_bearish,
    }


# ── CLI ──────────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    import sys, pprint

    init_db()

    if len(sys.argv) < 2:
        print("Usage: python3 candle_db.py <TOKEN> [TOKEN ...]")
        print("       python3 candle_db.py --fetch <TOKEN>   # fetch + store all TFs")
        print("       python3 candle_db.py --read <TOKEN> [tf=1h] [rows=100]")
        print("       python3 candle_db.py --cascade <TOKEN> # show cascade state")
        sys.exit(1)

    if sys.argv[1] == '--fetch':
        token = sys.argv[2].upper() if len(sys.argv) > 2 else 'BTC'
        results = fetch_and_store_all_tf(token)
        print(f"Fetched {token}: {results}")
    elif sys.argv[1] == '--read':
        token = sys.argv[2].upper() if len(sys.argv) > 2 else 'BTC'
        tf = sys.argv[3] if len(sys.argv) > 3 else '1h'
        rows = get_candles(token, tf, lookback_rows=20)
        print(f"{token} {tf} last {len(rows)} candles:")
        for r in rows[-5:]:
            dt = datetime.fromtimestamp(r[0]).strftime('%Y-%m-%d %H:%M')
            print(f"  {dt} O={r[1]:.6f} H={r[2]:.6f} L={r[3]:.6f} C={r[4]:.6f} V={r[5]:.2f}")
    elif sys.argv[1] == '--cascade':
        token = sys.argv[2].upper() if len(sys.argv) > 2 else 'BTC'
        from macd_rules import compute_macd_state
        states = {}
        for tf in ['15m', '1h', '4h']:
            # Use local DB candles for MACD computation
            from macd_rules import compute_macd_state as _cms
            # For MTF, we need to fetch that TF's candles
            candles = get_candles(token, tf, lookback_rows=40)
            if candles:
                # Build candle dicts for compute_macd_state
                import requests
                tf_min = {'15m': 15, '1h': 60, '4h': 240}[tf]
                url = f"https://api.binance.com/api/v3/klines?symbol={token}USDT&interval={tf}&limit=40"
                resp = requests.get(url, timeout=10)
                klines = resp.json()
                candle_dicts = [
                    {'open': float(k[1]), 'high': float(k[2]),
                     'low': float(k[3]), 'close': float(k[4]), 'volume': float(k[5])}
                    for k in klines
                ]
                states[tf] = _cms(token, candle_dicts)
            else:
                states[tf] = None
        result = detect_cascade_direction(states)
        print(f"{token} cascade state:")
        pprint.pprint(result)
    else:
        token = sys.argv[1].upper()
        results = fetch_and_store_all_tf(token)
        print(f"Stored {token}: {results}")
        print(f"Latest prices:")
        for tf in ['1m', '15m', '1h', '4h']:
            p = get_latest_price(token, tf)
            print(f"  {tf}: {p}")
