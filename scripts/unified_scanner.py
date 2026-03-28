#!/usr/bin/env python3
"""
Unified Scanner - Signal Generation Only
This script generates signals only. Execution is handled by decider-run.py.
"""
import sys, subprocess, requests, json, os
sys.path.insert(0, '/root/.openclaw/workspace/scripts')
sys.path.insert(0, '/root/.hermes/scripts')
from signal_schema import add_signal, get_confluence_signals, get_pending_signals as schema_get_pending
from tokens import SOLANA_ONLY_TOKENS, HYPERLIQUID_TOKENS, HYPERLIQUID_EXCLUDE, PREFER_HYPERLIQUID_TOKENS, is_solana_only, is_hyperliquid, get_token_chain, can_short
import psycopg2

LOG_FILE = '/root/.hermes/logs/unified-scanner.log'

# ============================================
# Hyperliquid Tokens Cache
# ============================================
_HYPERLIQUID_TOKENS_CACHE = None
_HYPERLIQUID_TOKENS_EXPIRY = 0

def get_hyperliquid_tokens():
    global _HYPERLIQUID_TOKENS_CACHE, _HYPERLIQUID_TOKENS_EXPIRY
    import time
    now = time.time()
    # Cache for 5 minutes
    if _HYPERLIQUID_TOKENS_CACHE is not None and (now - _HYPERLIQUID_TOKENS_EXPIRY) < 300:
        return _HYPERLIQUID_TOKENS_CACHE
    try:
        r = requests.post('https://api.hyperliquid.xyz/info', json={'type':'meta'}, timeout=30)
        _HYPERLIQUID_TOKENS_CACHE = {x['name'] for x in r.json().get('universe', [])}
        _HYPERLIQUID_TOKENS_EXPIRY = now
        return _HYPERLIQUID_TOKENS_CACHE
    except Exception as e:
        if _HYPERLIQUID_TOKENS_CACHE is None or len(_HYPERLIQUID_TOKENS_CACHE) < 100:
            _HYPERLIQUID_TOKENS_CACHE = set(HYPERLIQUID_TOKENS)
        return _HYPERLIQUID_TOKENS_CACHE

# ============================================
# Constants
# ============================================
MIN_PRICE = 0.0001
MIN_VOLUME = 500000
MIN_VOLUME_SOL = 100000
MAX_HYPE = 5
MAX_SOL = 5
MAX_TOTAL = 10
HYPERLIQUID_MAX_LEVERAGE = {}

# ============================================
# Logging
# ============================================
def log(msg):
    print(msg)
    try:
        os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
        with open(LOG_FILE, 'a') as f:
            f.write(f"{msg}\n")
    except: pass

# ============================================
# Price & Indicator Fetching
# ============================================
def get_cached_prices():
    """Fetch all prices from Hyperliquid public API. Falls back to cache."""
    try:
        r = requests.post('https://api.hyperliquid.xyz/info', json={'type':'allMids'}, timeout=10)
        if r.ok:
            all_data = r.json()
            # Use ALL tokens from Hyperliquid response (not a hardcoded subset)
            fresh = {k: float(v) for k, v in all_data.items() if v and float(v) > 0}
            if fresh:
                # Cache locally
                os.makedirs('/root/.hermes/data', exist_ok=True)
                with open('/root/.hermes/data/prices.json', 'w') as f:
                    json.dump(fresh, f)
                return fresh
    except Exception as e:
        log(f'get_cached_prices API error: {e}')

    # Fallback to local cache
    try:
        with open('/root/.hermes/data/prices.json') as f:
            return json.load(f)
    except:
        return {}

def get_cached_indicators():
    try:
        with open('/root/.openclaw/workspace/data/indicators.json') as f:
            return json.load(f)
    except:
        return {}

def get_fear():
    try:
        return int(requests.get('https://api.alternative.me/fng/?limit=1', timeout=5).json()['data'][0]['value'])
    except:
        return None

def get_zscore_signals(prices):
    sigs = []
    try:
        for line in open('/root/zscore/bnb-zscore.log').readlines()[-100:]:
            if 'SELL SIGNAL' in line:
                parts = line.split('SELL SIGNAL: ')[1].strip().split(' z=')
                if len(parts) == 2:
                    tok = parts[0].replace('USDT','')
                    try:
                        z = float(parts[1].split()[0])
                        if z < -2.0 and tok in prices:
                            sigs.append((tok, z, prices[tok], 'SHORT'))
                    except:
                        pass
            elif 'BUY SIGNAL' in line:
                parts = line.split('BUY SIGNAL: ')[1].strip().split(' z=')
                if len(parts) == 2:
                    tok = parts[0].replace('USDT','')
                    try:
                        z = float(parts[1].split()[0])
                        if z > 2.0 and tok in prices:
                            sigs.append((tok, z, prices[tok], 'LONG'))
                    except:
                        pass
    except:
        pass
    return sigs

def get_volume(token):
    """Get 24h volume from Binance"""
    try:
        r = requests.get(f'https://api.binance.com/api/v3/ticker/24hr?symbol={token}USDT', timeout=5)
        return float(r.json().get('quoteVolume', 0))
    except:
        return 0

# ============================================
# Validation
# ============================================
def get_token_exchange_with_validation(token):
    """Get appropriate exchange with validation"""
    token_upper = token.upper()
    
    if token_upper in HYPERLIQUID_EXCLUDE:
        return None
    
    if is_solana_only(token_upper):
        return 'raydium'
    
    hype_tokens = get_hyperliquid_tokens()
    if token_upper in hype_tokens:
        return 'hyperliquid'
    
    if is_solana_only(token_upper):
        return 'raydium'
    
    return None

def validate_token_on_exchange(token, exchange):
    """Validate token exists on exchange"""
    token_upper = token.upper()
    
    if exchange.lower() == 'hyperliquid':
        hype_tokens = get_hyperliquid_tokens()
        if token_upper not in hype_tokens:
            return False, f"Token {token_upper} not available on Hyperliquid"
    
    return True, None

# ============================================
# Leverage
# ============================================
HYPERLIQUID_MAX_LEVERAGE_EXPIRY = 0

def get_max_leverage(token, is_sol=False):
    """Get max leverage for token"""
    global HYPERLIQUID_MAX_LEVERAGE, HYPERLIQUID_MAX_LEVERAGE_EXPIRY
    import time
    now = time.time()
    if is_sol or token in SOLANA_ONLY_TOKENS:
        return 1
    # Cache for 5 minutes
    if HYPERLIQUID_MAX_LEVERAGE_EXPIRY and (now - HYPERLIQUID_MAX_LEVERAGE_EXPIRY) < 300:
        return HYPERLIQUID_MAX_LEVERAGE.get(token, 10)
    try:
        r = requests.post('https://api.hyperliquid.xyz/info', json={"type":"meta"}, timeout=30)
        HYPERLIQUID_MAX_LEVERAGE = {u["name"]: u.get("maxLeverage", 10) for u in r.json().get("universe", [])}
        HYPERLIQUID_MAX_LEVERAGE_EXPIRY = now
    except:
        pass
    return HYPERLIQUID_MAX_LEVERAGE.get(token, 10)

# ============================================
# Signal Generation
# ============================================
def get_gateio_rsi(token, period=14, interval='1h', limit=100):
    """Calculate RSI from Gate.io public candlestick API."""
    try:
        r = requests.get(
            'https://api.gateio.ws/api/v4/spot/candlesticks',
            params={'currency_pair': f'{token}_USDT', 'interval': interval, 'limit': limit},
            timeout=10
        )
        if r.ok:
            candles = r.json()
            if not candles or len(candles) < period + 1:
                return None
            closes = [float(c[2]) for c in reversed(candles[-period-1:])]
            deltas = [closes[i+1] - closes[i] for i in range(len(closes)-1)]
            gains = [d if d > 0 else 0 for d in deltas]
            losses = [-d if d < 0 else 0 for d in deltas]
            avg_gain = sum(gains) / period
            avg_loss = sum(losses) / period
            if avg_loss == 0:
                return 100
            rs = avg_gain / avg_loss
            return round(100 - (100 / (1 + rs)), 1)
    except:
        pass
    return None

def get_gateio_signals(prices):
    """Generate signals from Gate.io RSI. Returns (token, direction, confidence, rsi, price)."""
    tokens = ['BTC', 'ETH', 'SOL', 'XRP', 'ADA', 'AVAX', 'LINK', 'DOGE', 'DOT',
              'UNI', 'ATOM', 'FIL', 'APT', 'ARB', 'OP', 'NEAR', 'TIA', 'SUI']
    signals = []
    for tok in tokens:
        if tok not in prices or prices[tok] <= 0:
            continue
        if not get_token_exchange_with_validation(tok):
            continue
        rsi = get_gateio_rsi(tok)
        if rsi and rsi < 35:
            signals.append((tok, 'LONG', min(85, 70 + (35 - rsi) * 2), rsi, prices[tok]))
        elif rsi and rsi > 65:
            signals.append((tok, 'SHORT', min(85, 70 + (rsi - 65) * 2), rsi, prices[tok]))
    return signals

def add_all_signals():
    """Add all signals to database"""
    prices = get_cached_prices()
    indicators = get_cached_indicators()
    fear = get_fear()
    
    # Fear - BTC LONG when extreme fear
    if fear and fear <= 25 and 'BTC' in prices:
        add_signal('BTC', 'LONG', 'fear', 'fear-greed', 85 if fear <= 20 else 70,
                   exchange='hyperliquid', value=fear, price=prices.get('BTC'), timeframe='daily')
        log(f"Added fear: BTC LONG")
    
    # Gate.io RSI signals (public API, no auth)
    gate_signals = get_gateio_signals(prices)
    for tok, direction, conf, rsi_val, p in gate_signals[:10]:
        exchange = get_token_exchange_with_validation(tok)
        if exchange:
            add_signal(tok, direction, 'rsi', 'gateio-rsi', conf,
                       exchange=exchange, value=rsi_val, price=p, rsi_14=rsi_val, timeframe='1h')

    # Z-Score signals
    for tok, z, p, d in get_zscore_signals(prices)[:10]:
        exchange = get_token_exchange_with_validation(tok)
        if exchange:
            add_signal(tok, d, 'z_score', 'zscore-v9', min(90, 70+abs(z)*5),
                       exchange=exchange, value=z, price=p, z_score=z, timeframe='1h')
    
    # Multi-timeframe RSI signals
    for tok, data in indicators.items():
        rsi_oversold = data.get('mtf_rsi_oversold', 0)
        rsi_overbought = data.get('mtf_rsi_overbought', 0)
        
        exchange = get_token_exchange_with_validation(tok)
        if not exchange:
            continue
        
        if rsi_oversold >= 2:
            add_signal(tok, 'LONG', 'rsi', 'mtf-rsi-oversold', min(85, 60+rsi_oversold*10),
                       exchange=exchange, value=rsi_oversold, price=data.get('price'),
                       rsi_14=data.get('rsi_14'), timeframe='4h+1h+15m')
        elif rsi_overbought >= 2:
            add_signal(tok, 'SHORT', 'rsi', 'mtf-rsi-overbought', min(85, 60+rsi_overbought*10),
                       exchange=exchange, value=rsi_overbought, price=data.get('price'),
                       rsi_14=data.get('rsi_14'), timeframe='4h+1h+15m')
    
    # MTF-MACD signals
    for tok, data in indicators.items():
        mt_bullish = data.get('mt_tf_bullish', 0)
        mt_bearish = data.get('mt_tf_bearish', 0)
        
        exchange = get_token_exchange_with_validation(tok)
        if not exchange:
            continue
        
        if mt_bullish >= 3:
            add_signal(tok, 'LONG', 'mtf_macd', 'mtf-macd-bullish', min(95, 70+mt_bullish*10),
                       exchange=exchange, value=mt_bullish, price=data.get('price'),
                       timeframe='4h+1h+15m')
        elif mt_bearish >= 3:
            add_signal(tok, 'SHORT', 'mtf_macd', 'mtf-macd-bearish', min(95, 70+mt_bearish*10),
                       exchange=exchange, value=mt_bearish, price=data.get('price'),
                       timeframe='4h+1h+15m')

def get_pending_hype_signals():
    """Get pending signals for Hyperliquid"""
    import sqlite3
    from signal_schema import RUNTIME_DB; DB_PATH = RUNTIME_DB
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        SELECT token, direction, source, confidence, value, price
        FROM signals 
        WHERE decision = 'PENDING' 
        AND exchange = 'hyperliquid'
        ORDER BY confidence DESC
        LIMIT 20
    ''')
    results = c.fetchall()
    conn.close()
    return results

def is_sol_token(token):
    """Check if token is Solana-only"""
    return is_solana_only(token)

def get_token_exchange(token):
    """Get exchange for token"""
    if is_sol_token(token):
        return 'raydium'
    return 'hyperliquid'

def get_open_trades():
    """Get current open trades count by type"""
    try:
        conn = psycopg2.connect(host='/var/run/postgresql', database='brain', user='postgres', password='Brain123')
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM trades WHERE status = 'open' AND server='Hermes'")
        total = cur.fetchone()[0]
        cur.execute("SELECT token FROM trades WHERE status = 'open' AND server='Hermes'")
        tokens = [row[0] for row in cur.fetchall()]
        sol_count = sum(1 for t in tokens if t in SOLANA_ONLY_TOKENS)
        hype_count = total - sol_count
        conn.close()
        return {'total': total, 'hype': hype_count, 'sol': sol_count, 'tokens': tokens}
    except Exception as e:
        print(f"Error: {e}")
        return {'total': 999, 'hype': 999, 'sol': 999}

# ============================================
# Sync to JSON (for backward compatibility)
# ============================================
def sync_signals_to_json():
    """Sync signals from DB to JSON file for backward compatibility"""
    from signal_schema import get_pending_signals
    
    signals = get_pending_signals(50)
    pending = []
    for s in signals:
        pending.append({
            "token": s.get("token"),
            "direction": "long" if s.get("direction", "").upper() == "LONG" else "short",
            "entry": float(s.get("price", 0.01)),
            "confidence": float(s.get("confidence", 50)),
            "atrPercent": 2.0,
            "source": s.get("source", ""),
            "created_at": str(s.get("created_at", ""))
        })
    
    with open("/root/.openclaw/workspace/data/pending-signals.json", "w") as f:
        json.dump({"pending_signals": pending}, f, indent=2)
    
    print(f"Synced {len(pending)} signals to pending-signals.json")
    return len(pending)

# ============================================
# Main Run
# ============================================
def run():
    """Run scanner - generates signals only"""
    log("=== Unified Scanner: Signal Generation ===")
    
    # Add signals
    add_all_signals()
    
    prices = get_cached_prices()
    fear = get_fear()
    log(f"Prices: {len(prices)}, Fear: {fear}")
    
    # Get pending signals
    pending = get_pending_hype_signals()
    log(f"Pending Hyperliquid signals: {len(pending)}")
    
    # Get confluence
    conf = get_confluence_signals(1)
    open_pos = get_open_trades()
    log(f"Open: {open_pos['total']}/10 (Hype: {open_pos['hype']}/{MAX_HYPE}, SOL: {open_pos['sol']}/{MAX_SOL})")
    
    # Log confluence signals for decider
    for sig in conf:
        tok = sig['token']
        is_sol = is_sol_token(tok)
        
        # Skip if at limit
        if open_pos['total'] >= MAX_TOTAL:
            break
        
        if is_sol:
            if open_pos['sol'] >= MAX_SOL:
                continue
        else:
            if open_pos['hype'] >= MAX_HYPE:
                continue
        
        direction = sig['direction']
        conf_score = sig.get('final_confidence', sig.get('max_confidence', 50))
        
        # Solana only LONG
        if is_sol and direction.upper() == 'SHORT':
            continue
        
        # Skip if already open
        if tok in open_pos.get('tokens', []):
            continue
        
        # Short only on Hyperliquid
        if direction == "SHORT" and is_sol:
            continue
        
        log(f"📊 Confluence: {tok} {direction} ({conf_score:.0f}%)")
    
    # Sync to JSON for backward compat
    sync_signals_to_json()
    
    log("=== Done ===")

if __name__ == "__main__":
    run()
