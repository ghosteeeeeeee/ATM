#!/usr/bin/env python3
"""
15m Regime Scanner
Reads 15m closed candles from local candles.db (primary), falls back to Binance.
Uses is_closed=1 to exclude the current developing candle from slope calculation.
Adds regime bias to signal weight calculation (faster response than 4h).
"""
import requests
import json
import sys
import time
import sqlite3
import psycopg2
from datetime import datetime
sys.path.insert(0, '/root/.hermes/scripts')
from _secrets import BRAIN_DB_DICT

from paths import *
INFO_URL = "https://api.hyperliquid.xyz/info"
OUTPUT_FILE = "/var/www/hermes/data/regime_15m.json"
STATIC_DB   = "/root/.hermes/data/signals_hermes.db"
CANDLES_DB  = "/root/.hermes/data/candles.db"
LOG_FILE = "/root/.hermes/logs/15m_regime.log"
BRAIN_DB = BRAIN_DB_DICT
CANDLE_TF = "15m"
CANDLE_TABLE = "candles_15m"
STALE_THRESHOLD_SECS = 300  # 5 min — if latest closed candle is older, use Binance

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")
    with open(LOG_FILE, "a") as f:
        f.write(f"[{datetime.now().isoformat()}] {msg}\n")

def fetch_candles_from_db(token, limit=16):
    """Read closed 15m candles from candles.db. Returns list of dicts or None if stale/missing."""
    try:
        conn = sqlite3.connect(CANDLES_DB)
        cur = conn.cursor()
        cur.execute(f"""
            SELECT ts, open, high, low, close, volume
            FROM {CANDLE_TABLE}
            WHERE token = ? AND is_closed = 1
            ORDER BY ts DESC
            LIMIT ?
        """, (token.upper(), limit))
        rows = cur.fetchall()
        conn.close()

        if not rows:
            return None

        # Check if data is stale (latest closed candle too old)
        latest_ts = rows[0][0]
        age = time.time() - latest_ts
        if age > STALE_THRESHOLD_SECS:
            log(f"  {token}: candles.db stale ({age:.0f}s old) — falling back to Binance")
            return None

        # Reverse to chronological order for slope calculation
        candles = []
        for r in reversed(rows):
            candles.append({
                'time': r[0],
                'open': float(r[1]),
                'high': float(r[2]),
                'low': float(r[3]),
                'close': float(r[4]),
                'volume': float(r[5])
            })
        return candles
    except Exception as e:
        log(f"  {token}: candles.db error ({e}) — falling back to Binance")
        return None

def fetch_candles_from_binance(token, limit=16):
    """Fetch 15m candles from Binance as fallback. Always drops developing candle."""
    try:
        symbol = f"{token}USDT"
        url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=15m&limit={limit + 1}"
        r = requests.get(url, timeout=10)
        if r.ok:
            data = r.json()
            # Drop the current developing candle (last entry) — not closed yet
            data = data[:-1]
            candles = []
            for c in data:
                candles.append({
                    'time': c[0] / 1000,
                    'open': float(c[1]),
                    'high': float(c[2]),
                    'low': float(c[3]),
                    'close': float(c[4]),
                    'volume': float(c[5])
                })
            return candles
    except Exception as e:
        log(f"  {token}: Binance error: {e}")
    return None

def fetch_candles(token, limit=16):
    """
    Fetch candles: candles.db primary (closed only), Binance fallback.
    Always excludes the developing candle from slope calculation.
    """
    # Try local DB first
    candles = fetch_candles_from_db(token, limit)
    if candles:
        return candles
    # Fallback to Binance
    return fetch_candles_from_binance(token, limit)

def calculate_slope(candles):
    """Calculate linear regression slope of close prices"""
    if not candles or len(candles) < 3:
        return None, 0

    closes = [c['close'] for c in candles]
    n = len(closes)

    x = list(range(n))
    x_mean = (n - 1) / 2
    y_mean = sum(closes) / n

    numerator = sum((x[i] - x_mean) * (closes[i] - y_mean) for i in range(n))
    denominator = sum((x[i] - x_mean) ** 2 for i in range(n))

    if denominator == 0:
        return 0, 0

    slope = numerator / denominator
    slope_pct = (slope / y_mean) * 100  # Normalize as percentage per candle

    return slope, slope_pct

def calculate_r2(candles, slope):
    """Calculate R-squared for confidence"""
    if not candles or len(candles) < 3:
        return 0

    closes = [c['close'] for c in candles]
    n = len(closes)
    y_mean = sum(closes) / n

    x = list(range(n))
    x_mean = (n - 1) / 2

    y_pred = [y_mean + slope * (x[i] - x_mean) for i in range(n)]

    ss_res = sum((closes[i] - y_pred[i]) ** 2 for i in range(n))
    ss_tot = sum((closes[i] - y_mean) ** 2 for i in range(n))

    if ss_tot == 0:
        return 0

    r2 = 1 - (ss_res / ss_tot)
    return max(0, r2)

def determine_regime(slope_pct, r2):
    """Determine regime based on slope and confidence.
    Symmetric thresholds — asset-agnostic.
    """
    if slope_pct > 0.35 and r2 > 0.5:
        return "LONG_BIAS", min(95, 50 + r2 * 45 + slope_pct * 20)
    elif slope_pct < -0.35 and r2 > 0.5:
        return "SHORT_BIAS", min(95, 50 + r2 * 45 + abs(slope_pct) * 20)
    elif abs(slope_pct) < 0.20:
        return "NEUTRAL", min(70, 50 + (1 - abs(slope_pct)/0.20) * 20)
    elif slope_pct > 0 and r2 > 0.4:
        return "LONG_BIAS", 45 + r2 * 20
    elif slope_pct < 0 and r2 > 0.4:
        return "SHORT_BIAS", 45 + r2 * 20
    else:
        return "NEUTRAL", 40 + r2 * 15

def get_tokens_to_scan():
    """Get tokens from open trades, recent signals, and focus list"""
    tokens = set()

    # Get from open trades
    try:
        conn = psycopg2.connect(**BRAIN_DB_DICT)
        cur = conn.cursor()
        cur.execute("SELECT DISTINCT token FROM trades WHERE status = 'open'")
        for row in cur.fetchall():
            if row[0]:
                tokens.add(row[0])
        conn.close()
    except Exception as e:
        log(f"DB error: {e}")

    # Get from signal files
    for fname in ["/var/www/html/signals.json", "/root/.hermes/data/signals.json"]:
        try:
            with open(fname) as f:
                data = json.load(f)
                if isinstance(data, list):
                    for sig in data:
                        if 'token' in sig:
                            tokens.add(sig['token'])
                        elif 'symbol' in sig:
                            tokens.add(sig['symbol'].replace('USDT', ''))
        except:
            pass

    focus_tokens = [
        'SOL', 'BTC', 'ETH', 'WIF', 'PEPE', 'VIRTUAL', 'FARTCOIN', 'MELANIA', 'POPCAT', 'GOAT',
        'AXS', 'TRB', 'SKY', 'VVV', 'ZORA', 'SAGA', 'GMX', 'ALGO', 'IOTA', 'TRX',
        'HYPE', 'WCT', 'BONK', 'FWOG', 'CHILL', 'MUMU', 'PNUT', 'AERO',
        'AEVO', 'ALT', 'APT', 'ARB', 'ATOM', 'AVAX', 'BLUR', 'BNB', 'CRV', 'DOGE',
        'FIL', 'FTM', 'GRT', 'ICP', 'INJ', 'LDO', 'LINK', 'LTC', 'MATIC', 'NEAR', 'OP',
        'ORDI', 'RENDER', 'RUNE', 'SAND', 'SEI', 'SHIB', 'SUI', 'TIA', 'TON', 'UNI',
        'XRP', 'NIL', 'MOVE', 'IMX', 'ASTER', 'SOPH', 'GALA', 'MEW', 'MON', 'BIGTIME',
    ]
    for t in focus_tokens:
        tokens.add(t)

    # Also pull from live signals SQLite DB
    for sig_db in [RUNTIME_DB,
                   '/root/.hermes/data/signals.db',
                   '/root/.hermes/data/signals_hermes.db']:
        try:
            sc = sqlite3.connect(sig_db)
            cu = sc.cursor()
            cu.execute("SELECT DISTINCT token FROM signals WHERE token NOT LIKE '@%' LIMIT 100")
            for row in cu.fetchall():
                if row[0]:
                    tokens.add(row[0])
            sc.close()
        except Exception:
            pass

    focus_set = set(focus_tokens)
    priority_tokens = list(focus_set) + [t for t in tokens if t not in focus_set]
    return priority_tokens

def scan_token(token):
    """Scan a single token and return regime data"""
    candles = fetch_candles(token, limit=16)
    if not candles:
        return None

    slope, slope_pct = calculate_slope(candles)
    if slope is None:
        return None

    r2 = calculate_r2(candles, slope)
    regime, confidence = determine_regime(slope_pct, r2)

    # Use last closed candle for current_price (candles are already closed-only from DB)
    current_price = candles[-1]['close']
    start_price = candles[0]['open']
    total_change = ((current_price - start_price) / start_price) * 100

    return {
        'token': token,
        'regime': regime,
        'confidence': round(confidence, 1),
        'slope_pct': round(slope_pct, 3),
        'r2': round(r2, 3),
        'current_price': current_price,
        'change_16_candles': round(total_change, 2),
        'candles': len(candles)
    }

def write_to_brain_cache(results):
    """Write per-token regime data to PostgreSQL momentum_cache (brain DB)"""
    if not results:
        return
    try:
        conn = psycopg2.connect(**BRAIN_DB)
        cur = conn.cursor()
        now = datetime.now()
        for token, r in results.items():
            regime = r.get('regime', 'NEUTRAL')
            slope_pct = r.get('slope_pct', 0)
            trend = 'uptrend' if slope_pct > 0.1 else 'downtrend' if slope_pct < -0.1 else 'ranging'
            cur.execute("""
                INSERT INTO momentum_cache (token, slope_15m, regime_15m, trend, updated_at)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (token) DO UPDATE SET
                    slope_15m = EXCLUDED.slope_15m,
                    regime_15m = EXCLUDED.regime_15m,
                    trend = EXCLUDED.trend,
                    updated_at = EXCLUDED.updated_at
            """, (token, slope_pct, regime, trend, now))
        conn.commit()
        cur.close()
        conn.close()
        log(f"Brain momentum_cache: wrote {len(results)} tokens (15m)")
    except Exception as e:
        log(f"Brain momentum_cache write error: {e}")

def main():
    log("=== 15m Regime Scanner Started ===")

    tokens = get_tokens_to_scan()
    log(f"Scanning {len(tokens)} tokens")

    results = {}
    for token in tokens:
        result = scan_token(token)
        if result:
            results[token] = result
            log(f"  {token}: {result['regime']} ({result['confidence']}%) - slope: {result['slope_pct']}%")

    long_count = sum(1 for r in results.values() if r['regime'] == "LONG_BIAS")
    short_count = sum(1 for r in results.values() if r['regime'] == "SHORT_BIAS")
    neutral_count = sum(1 for r in results.values() if r['regime'] == "NEUTRAL")

    aggregate = {
        'long_bias': long_count,
        'short_bias': short_count,
        'neutral': neutral_count,
        'overall': 'LONG_BIAS' if long_count > short_count + 2 else 'SHORT_BIAS' if short_count > long_count + 2 else 'NEUTRAL'
    }

    output = {
        'timestamp': datetime.now().isoformat(),
        'tokens_scanned': len(results),
        'aggregate': aggregate,
        'regimes': results
    }

    # Save to hermes data dir (signal_compactor reads this)
    with open(OUTPUT_FILE, "w") as f:
        json.dump(output, f, indent=2)
    log(f"Wrote {OUTPUT_FILE}")

    # Write per-token regime to PostgreSQL brain momentum_cache
    write_to_brain_cache(results)

    log(f"Overall market bias: {aggregate['overall']} ({long_count}L/{short_count}S/{neutral_count}N)")
    print(json.dumps(output, indent=2))

if __name__ == "__main__":
    main()
