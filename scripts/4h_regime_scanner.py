#!/usr/bin/env python3
"""
4h Regime Scanner
Fetches 4h candles for tokens and calculates price momentum slope
Adds regime bias to signal weight calculation
"""
import requests
import json
import sys
import time
import psycopg2
from datetime import datetime
sys.path.insert(0, '/root/.hermes/scripts')
from _secrets import BRAIN_DB_DICT

INFO_URL = "https://api.hyperliquid.xyz/info"
OUTPUT_FILE = "/var/www/html/regime_4h.json"
STATIC_DB   = "/root/.hermes/data/signals_hermes.db"
LOG_FILE = "/root/.openclaw/workspace/logs/4h_regime.log"
BRAIN_DB = BRAIN_DB_DICT

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")
    with open(LOG_FILE, "a") as f:
        f.write(f"[{datetime.now().isoformat()}] {msg}\n")

def fetch_candles(token, interval="4h", limit=6):
    """Fetch 4h candles from Hyperliquid"""
    try:
        # Hyperliquid uses 1h intervals, so we get more and filter
        # Actually, let's use Binance for broader token support
        # Try Hyperliquid first
        payload = {
            "type": "candleSnapshot",
            "req": {
                "coin": token,
                "interval": interval,
                "num": limit
            }
        }
        r = requests.post(INFO_URL, json=payload, timeout=15)
        if r.ok:
            data = r.json()
            if data and len(data) > 0:
                # Convert to OHLCV format
                candles = []
                for c in data:  # Hyperliquid returns [time, open, high, low, close, volume]
                    candles.append({
                        'time': c[0],
                        'open': float(c[1]),
                        'high': float(c[2]),
                        'low': float(c[3]),
                        'close': float(c[4]),
                        'volume': float(c[5])
                    })
                return candles
    except Exception as e:
        log(f"Hyperliquid error for {token}: {e}")
    
    # Fallback to Binance
    try:
        symbol = f"{token}USDT"
        url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
        r = requests.get(url, timeout=10)
        if r.ok:
            data = r.json()
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
        log(f"Binance error for {token}: {e}")
    
    return None

def calculate_slope(candles):
    """Calculate linear regression slope of close prices"""
    if not candles or len(candles) < 3:
        return None, 0
    
    closes = [c['close'] for c in candles]
    n = len(closes)
    
    # Simple linear regression
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
    
    # Calculate predicted values
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
    """Determine regime based on slope and confidence"""
    # Slope thresholds (% per 4h candle)
    # 0.5% per candle = ~3% over 6 candles = strong momentum
    
    if slope_pct > 0.3 and r2 > 0.5:
        return "LONG_BIAS", min(95, 50 + r2 * 45 + slope_pct * 20)
    elif slope_pct < -0.3 and r2 > 0.5:
        return "SHORT_BIAS", min(95, 50 + r2 * 45 + abs(slope_pct) * 20)
    elif abs(slope_pct) < 0.15:
        return "NEUTRAL", min(70, 50 + (1 - abs(slope_pct)/0.15) * 20)
    elif slope_pct > 0:
        return "LONG_BIAS", 45 + r2 * 20
    else:
        return "SHORT_BIAS", 45 + r2 * 20

def get_tokens_to_scan():
    """Get tokens from open trades and recent signals"""
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
    for fname in ["/var/www/html/signals.json", "/root/.openclaw/workspace/data/signals.json"]:
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
    
    # Always include focus tokens (they are valid crypto symbols)
    focus_tokens = ['SOL', 'BTC', 'ETH', 'WIF', 'PEPE', 'VIRTUAL', 'FARTCOIN', 'MELANIA', 'POPCAT', 'GOAT']
    for t in focus_tokens:
        tokens.add(t)
    
    return list(tokens)[:30]  # Limit to 30 tokens

def scan_token(token):
    """Scan a single token and return regime data"""
    candles = fetch_candles(token, limit=6)
    if not candles:
        return None
    
    slope, slope_pct = calculate_slope(candles)
    if slope is None:
        return None
    
    r2 = calculate_r2(candles, slope)
    regime, confidence = determine_regime(slope_pct, r2)
    
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
        'change_6_candles': round(total_change, 2),
        'candles': len(candles)
    }

def calculate_weight_adjustment(regime, side):
    """Calculate weight multiplier based on regime alignment"""
    if regime == "NEUTRAL":
        return 1.0
    
    if regime == "LONG_BIAS":
        if side == "long":
            return 1.2  # Bonus for aligned direction
        else:
            return 0.8  # Penalty for fighting trend
    
    if regime == "SHORT_BIAS":
        if side == "short":
            return 1.2
        else:
            return 0.8
    
    return 1.0

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
            # Map regime to trend (simplified)
            trend = 'uptrend' if slope_pct > 0.1 else 'downtrend' if slope_pct < -0.1 else 'ranging'
            cur.execute("""
                INSERT INTO momentum_cache (token, slope_4h, regime_4h, trend, updated_at)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (token) DO UPDATE SET
                    slope_4h = EXCLUDED.slope_4h,
                    regime_4h = EXCLUDED.regime_4h,
                    trend = EXCLUDED.trend,
                    updated_at = EXCLUDED.updated_at
            """, (token, slope_pct, regime, trend, now))
        conn.commit()
        cur.close()
        conn.close()
        log(f"Brain momentum_cache: wrote {len(results)} tokens")
    except Exception as e:
        log(f"Brain momentum_cache write error: {e}")

def main():
    log("=== 4h Regime Scanner Started ===")
    
    tokens = get_tokens_to_scan()
    log(f"Scanning {len(tokens)} tokens")
    
    results = {}
    for token in tokens:
        result = scan_token(token)
        if result:
            results[token] = result
            log(f"  {token}: {result['regime']} ({result['confidence']}%) - slope: {result['slope_pct']}%")
    
    # Calculate aggregate bias
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
    
    # Save to file
    with open(OUTPUT_FILE, "w") as f:
        json.dump(output, f, indent=2)
    
    # Write per-token regime to PostgreSQL brain momentum_cache
    write_to_brain_cache(results)
    
    # Also write aggregate regime to static DB (wasp.py checks this table)
    try:
        import sqlite3
        n = len(results) or 1
        broad_z = (short_count - long_count) / n  # -1 to +1
        if aggregate['overall'] == 'LONG_BIAS':
            long_mult, short_mult = 1.2, 0.8
        elif aggregate['overall'] == 'SHORT_BIAS':
            long_mult, short_mult = 0.8, 1.2
        else:
            long_mult, short_mult = 1.0, 1.0
        sc = sqlite3.connect(STATIC_DB)
        sc.execute("""
            INSERT INTO regime_log (regime, broad_z, long_mult, short_mult, timestamp)
            VALUES (?, ?, ?, ?, ?)
        """, (aggregate['overall'], round(broad_z, 3), long_mult, short_mult, int(time.time())))
        sc.commit()
        sc.close()
    except Exception as e:
        log(f"DB write error: {e}")
    
    log(f"Overall market bias: {aggregate['overall']} ({long_count}L/{short_count}S/{neutral_count}N)")
    print(json.dumps(output, indent=2))

if __name__ == "__main__":
    main()
