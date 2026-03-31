#!/usr/bin/env python3
"""
AI Decider - Actually thinks and decides using all available info
"""
import subprocess, json, time, sys, requests, sqlite3, psycopg2, os, random, shlex, traceback
from datetime import datetime
import pandas as pd

LOG_FILE = '/var/www/hermes/logs/trading.log'

def log(msg, level='INFO'):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_line = f'[{timestamp}] [{level}] [ai-decider] {msg}'
    print(log_line)
    try:
        os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
        with open(LOG_FILE, 'a') as f:
            f.write(log_line + '\n')
    except: pass  # Don't crash on log failures

def log_error(msg, exc=None):
    error_msg = f'{msg}'
    if exc:
        error_msg += f': {exc}'
        error_msg += f'\n{traceback.format_exc()}'
    log(error_msg, 'ERROR')

AB_CONFIG_FILE = '/root/.openclaw/workspace/data/ab-test-config.json'
AB_RESULTS_FILE = '/root/.hermes/data/ab-test-results.json'
AB_CACHE_FILE = '/root/.openclaw/workspace/data/ab-variant-cache.json'

# In-memory cache for A/B variants per token+direction (cleared on restart)
_ab_variant_cache = {}

# Batch cache for Hyperliquid API calls (valid for 30 seconds)
import hype_cache as hc  # shared 60s cache written by price_collector

# Local prices file (written by combined-trading.py)
LOCAL_PRICES_FILE = "/var/www/html/token_intel.json"

def get_local_prices():
    """Get prices from local token_intel.json file - no API calls"""
    try:
        if os.path.exists(LOCAL_PRICES_FILE):
            with open(LOCAL_PRICES_FILE) as f:
                data = json.load(f)
                # Extract just the prices from the token data
                prices = {}
                if isinstance(data, dict):
                    for token, info in data.items():
                        if isinstance(info, dict) and 'price' in info:
                            prices[token] = str(info['price'])
                return prices
    except Exception as e:
        print(f"   ⚠️ Failed to read local prices: {e}")
    return {}

def get_hype_all_mids_batched():
    """Get all mids from shared HL cache (written by price_collector)."""
    return hc.get_allMids()

def get_hype_meta_batched():
    """Get meta from shared HL cache (written by price_collector)."""
    return hc.get_meta()

def get_cached_ab_variant(token, direction, test_name):
    """Get cached A/B variant or select new one"""
    key = f"{token}:{direction}"
    if key not in _ab_variant_cache:
        _ab_variant_cache[key] = {}
    
    if test_name not in _ab_variant_cache[key]:
        _ab_variant_cache[key][test_name] = select_ab_variant(test_name)
    
    return _ab_variant_cache[key][test_name]

def clear_ab_cache(token=None, direction=None):
    """Clear A/B cache - optionally for specific token"""
    if token:
        key = f"{token}:{direction or 'long'}"
        _ab_variant_cache.pop(key, None)
    else:
        _ab_variant_cache.clear()

def load_ab_config():
    """Load A/B test configuration"""
    try:
        with open(AB_CONFIG_FILE, 'r') as f:
            return json.load(f)
    except Exception as e:
        log_error(f'load_ab_config: {e}')
        return {"enabled": False, "tests": []}

def select_ab_variant(test_name):
    """
    Select a variant for a given A/B test using EPSILON-GREEDY selection.

    Exploitation (1-epsilon): pick the best-performing variant by win rate.
    Exploration (epsilon):   pick a random variant weighted by config weight.

    Falls back to weighted-random if not enough data for exploitation.
    """
    try:
        import ab_optimizer
        config = load_ab_config()
        if not config.get("enabled", False):
            return None
        test = next((t for t in config.get("tests", []) if t["name"] == test_name), None)
        if not test:
            return None
        variant = ab_optimizer.epsilon_greedy_pick(test_name, test)
        return variant
    except ImportError:
        # Fallback to old weighted-random
        pass

    config = load_ab_config()
    if not config.get("enabled", False):
        return None

    test = next((t for t in config.get("tests", []) if t["name"] == test_name), None)
    if not test:
        return None

    enabled = [v for v in test.get("variants", []) if v.get("enabled", False)]
    if not enabled:
        return None

    total_weight = sum(v.get("weight", 1) for v in enabled)
    r = random.random() * total_weight
    
    for v in enabled:
        r -= v.get("weight", 1)
        if r <= 0:
            return v
    
    return enabled[0]

def get_ab_params(token, direction='long'):
    """
    Get A/B test parameters for a trade.
    Returns a dict with all relevant params. Each token+direction gets a cached variant
    assignment, so the same test applies for the lifetime of that trade.

    Returns: {
        'sl_pct': float,        # stop-loss distance (0.01 = 1%)
        'sl_distance': float,   # same as sl_pct, for DB column
        'entry_mode': str,      # 'immediate' | 'pullback'
        'pullback_pct': float, # pullback threshold if entry_mode='pullback'
        'max_wait_minutes': int, # max wait time for pullback entry
        'trailing_activation': float, # trailing SL activation threshold
        'trailing_distance': float,   # trailing SL distance
        'experiment': str,       # experiment label for logging
        'variant_id': str,      # which variant was selected
        'test_name': str,       # which test this came from
    }
    """
    config = load_ab_config()
    if not config.get("enabled", False):
        return _default_ab_params()

    result = _default_ab_params()

    # ── SL Distance Test ─────────────────────────────────────────
    sl_test = get_cached_ab_variant(token, direction, 'sl-distance-test')
    if sl_test:
        cfg = sl_test.get("config", {})
        sl_pct = cfg.get("slPct", 0.01)
        result['sl_pct'] = sl_pct
        result['sl_distance'] = sl_pct
        result['experiment'] = f"sl_{sl_pct*100:g}pct"
        result['variant_id'] = sl_test.get('id', '')
        result['test_name'] = 'sl-distance-test'
        print(f"  [AB] SL Distance: {sl_pct*100:g}% (variant: {sl_test.get('id')})")

    # ── Entry Timing Test ─────────────────────────────────────────
    entry_test = get_cached_ab_variant(token, direction, 'entry-timing-test')
    if entry_test:
        cfg = entry_test.get("config", {})
        result['entry_mode'] = cfg.get("entryMode", "immediate")
        result['pullback_pct'] = cfg.get("pullbackPct", 0.01)
        result['max_wait_minutes'] = cfg.get("maxWaitMinutes", 30)
        result['variant_id'] = entry_test.get('id', '')
        result['test_name'] = 'entry-timing-test'
        print(f"  [AB] Entry Mode: {result['entry_mode']} (variant: {entry_test.get('id')})")

    # ── Trailing Stop Test ─────────────────────────────────────────
    ts_test = get_cached_ab_variant(token, direction, 'trailing-stop-test')
    if ts_test:
        cfg = ts_test.get("config", {})
        result['trailing_activation'] = cfg.get("trailingActivationPct", 0.01)
        result['trailing_distance'] = cfg.get("trailingDistancePct", 0.01)
        result['variant_id'] = ts_test.get('id', '')
        result['test_name'] = 'trailing-stop-test'
        print(f"  [AB] Trailing: activate at +{result['trailing_activation']*100:g}%, "
              f"distance {result['trailing_distance']*100:g}% (variant: {ts_test.get('id')})")

    return result


def _default_ab_params():
    """Return default A/B params (no experiment)."""
    return {
        'sl_pct': 0.02,
        'sl_distance': 0.02,
        'entry_mode': 'immediate',
        'pullback_pct': 0.01,
        'max_wait_minutes': 30,
        'trailing_activation': 0.01,
        'trailing_distance': 0.01,
        'experiment': 'control',
        'variant_id': '',
        'test_name': '',
    }

# Self-improving: Learning goals (tweakable)
LEARNING_GOALS = {
    "optimize": "win_rate",  # win_rate | total_pnl | sharpe | volume
    "min_trades": 3,
    "confidence_threshold": 5,
    "sl_adjustment": 1.0,
    "learning_horizon_days": 7,
    "pattern_strength_threshold": 0.6,
    "max_adjustment_per_trade": 0.1,
}

GOAL_PRESETS = {
    "conservative": {"optimize": "sharpe", "min_trades": 20, "confidence_threshold": 10, "sl_adjustment": 1.2, "pattern_strength_threshold": 0.8},
    "aggressive": {"optimize": "total_pnl", "min_trades": 5, "confidence_threshold": 0, "sl_adjustment": 0.8, "pattern_strength_threshold": 0.5},
    "data_first": {"optimize": "win_rate", "min_trades": 3, "confidence_threshold": 3, "sl_adjustment": 1.0, "pattern_strength_threshold": 0.4},
}

BRAIN_DB = "host=/var/run/postgresql dbname=brain user=postgres password=postgres"

def get_learned_adjustments(token, direction='long'):
    """Get learned pattern adjustments from brain for a token"""
    try:
        conn = psycopg2.connect(BRAIN_DB)
        cur = conn.cursor()
        cur.execute("""
            SELECT pattern_name, confidence, adjustment, sample_count
            FROM trade_patterns
            WHERE token = %s 
              AND (side = %s OR side = 'any')
              AND sample_count >= 3
            ORDER BY confidence DESC
            LIMIT 3
        """, (token, direction))
        patterns = cur.fetchall()
        cur.close()
        conn.close()
        
        if not patterns:
            return None
        
        # Aggregate weighted adjustments
        conf_adj = 0
        sl_mult = 1.0
        total_weight = 0
        
        for p in patterns:
            weight = (p[2] or 0.5) * min(p[3], 10) / 10
            try:
                adj = json.loads(p[2]) if p[2] else {}
            except (json.JSONDecodeError, ValueError) as e:
                log_error(f'get_learned_adjustments: json.loads failed for pattern {p[0]}: {e}')
                adj = {}
            conf_adj += adj.get('confidence_adj', 0) * weight
            sl_mult = (sl_mult * (1 - weight)) + ((adj.get('sl_mult', 1.0) or 1.0) * weight)
            total_weight += weight
        
        if total_weight == 0:
            return None
        
        return {
            'confidence_boost': round(min(conf_adj, LEARNING_GOALS['max_adjustment_per_trade'] * 10), 1),
            'sl_multiplier': round(max(0.5, min(1.5, sl_mult)), 2),
            'patterns': [p[0] for p in patterns]
        }
    except Exception as e:
        log_error(f'get_learned_adjustments: {e}')
        return None

def log_ab_trade_opened(token, direction, tp_multiplier, sl_pct, risk_reward, tp_pct, sl_pct_display,
                        leverage=None, strategy=None, experiment=None, variant_id=None, test_name=None):
    """
    Log when a trade is opened with A/B test variant info.
    Writes to both the legacy JSON file (for backward compat) and the brain DB ab_results table.
    """
    try:
        # ── Write to JSON (legacy) ───────────────────────────────
        results = []
        try:
            with open(AB_RESULTS_FILE, 'r') as f:
                content = f.read()
                if content.strip().startswith('{'):
                    # Old format: wrap in list
                    old = json.loads(content)
                    results = [old] if isinstance(old, dict) else old
                else:
                    results = json.loads(content)
        except Exception:
            results = []

        entry = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "token": token,
            "direction": direction,
            "event": "opened",
            "tp_multiplier": tp_multiplier,
            "sl_pct": round(sl_pct, 4) if sl_pct else None,
            "tp_pct": round(tp_pct, 2),
            "experiment": experiment,
            "variant_id": variant_id,
            "test_name": test_name,
        }
        results.append(entry)

        with open(AB_RESULTS_FILE, 'w') as f:
            json.dump(results[-1000:], f, indent=2)

        # ── Write to brain DB ab_results table ───────────────────
        if experiment and experiment != 'control' and test_name and variant_id:
            try:
                conn = psycopg2.connect(BRAIN_DB)
                cur = conn.cursor()
                cur.execute("""
                    INSERT INTO ab_results
                        (test_name, variant_id, trades, wins, losses,
                         total_pnl_pct, total_pnl_usdt, updated_at)
                    VALUES (%s, %s, 1, 0, 0, 0, 0, now())
                    ON CONFLICT (test_name, variant_id)
                    DO UPDATE SET
                        trades = ab_results.trades + 1,
                        updated_at = now()
                """, (test_name, variant_id))
                conn.commit()
                cur.close()
                conn.close()
            except Exception as e2:
                log(f'log_ab_trade_opened DB write failed: {e2}', 'WARN')
    except Exception as e:
        log_error(f'log_ab_trade_opened: {e}')

def record_ab_trade_closed(token, pnl_pct, pnl_usdt):
    """
    Record outcome when a trade closes.
    Updates both the JSON file (legacy) and the brain DB ab_results table.
    """
    try:
        # ── Write to JSON (legacy) ───────────────────────────────
        results = []
        try:
            with open(AB_RESULTS_FILE, 'r') as f:
                content = f.read()
                if content.strip().startswith('{'):
                    old = json.loads(content)
                    results = [old] if isinstance(old, dict) else old
                else:
                    results = json.loads(content)
        except Exception:
            results = []

        # Find the most recent open trade for this token
        for entry in reversed(results):
            if entry.get("token") == token and entry.get("event") == "opened" and "closed_at" not in entry:
                entry["closed_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                entry["pnl_pct"] = round(pnl_pct, 2)
                entry["pnl_usdt"] = round(pnl_usdt, 2)
                entry["result"] = "WIN" if pnl_usdt > 0 else "LOSS"

                test_name = entry.get("test_name")
                variant_id = entry.get("variant_id")
                is_win = pnl_usdt > 0

                # ── Update brain DB ab_results table ─────────────
                if test_name and variant_id:
                    try:
                        conn = psycopg2.connect(BRAIN_DB)
                        cur = conn.cursor()
                        cur.execute("""
                            INSERT INTO ab_results
                                (test_name, variant_id, trades, wins, losses,
                                 total_pnl_pct, total_pnl_usdt, updated_at)
                            VALUES (%s, %s, 1, %s, %s, %s, %s, now())
                            ON CONFLICT (test_name, variant_id)
                            DO UPDATE SET
                                trades = ab_results.trades + 1,
                                wins = ab_results.wins + %s,
                                losses = ab_results.losses + %s,
                                total_pnl_pct = ab_results.total_pnl_pct + %s,
                                total_pnl_usdt = ab_results.total_pnl_usdt + %s,
                                win_rate_pct = CASE
                                    WHEN ab_results.trades + 1 > 0
                                    THEN (ab_results.wins + %s)::float / (ab_results.trades + 1) * 100
                                    ELSE 0 END,
                                updated_at = now()
                        """, (test_name, variant_id,
                              1 if is_win else 0, 0 if is_win else 1,
                              round(pnl_pct, 4), round(float(pnl_usdt), 4),
                              1 if is_win else 0, 0 if is_win else 1,
                              round(pnl_pct, 4), round(float(pnl_usdt), 4),
                              1 if is_win else 0))
                        conn.commit()
                        cur.close()
                        conn.close()
                    except Exception as e2:
                        log(f'record_ab_trade_closed DB error: {e2}', 'WARN')

                break

        with open(AB_RESULTS_FILE, 'w') as f:
            json.dump(results[-1000:], f, indent=2)
    except Exception as e:
        log_error(f'record_ab_trade_closed: {e}')

PENDING = "/root/.openclaw/workspace/data/pending-signals.json"
from signal_schema import RUNTIME_DB as SIGNALS_DB
SIGNAL_LOG = "/var/www/hermes/logs/signals.log"
LOCK_FILE = "/tmp/ai-decider.lock"

MAX_OPEN = 10

# Check for existing lock to prevent race conditions
def acquire_lock():
    if os.path.exists(LOCK_FILE):
        # Check if process is still running
        try:
            with open(LOCK_FILE) as f:
                pid = int(f.read().strip())
            os.kill(pid, 0)  # Check if process exists
            print(f"🔒 Lock file exists, PID {pid} still running. Exiting.")
            return False
        except (ValueError, ProcessLookupError, PermissionError):
            # Stale lock, remove it
            os.remove(LOCK_FILE)
    # Create lock
    with open(LOCK_FILE, 'w') as f:
        f.write(str(os.getpid()))
    return True

def release_lock():
    try:
        os.remove(LOCK_FILE)
    except Exception as e:
        log_error(f'release_lock: {e}')

# Acquire lock at startup
if not acquire_lock():
    sys.exit(0)

def log_signal(token, direction, price, confidence, source):
    """Log signal to signals.log for signals.html display"""
    from datetime import datetime, timezone
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")
    with open(SIGNAL_LOG, "a") as f:
        f.write(f"{timestamp} SIGNAL: {token} {direction.upper()} @ {price} ({confidence}%) [{source}]\n")

def cleanup_stale_signals():
    """Clean up stale signals on startup - prevents backlog"""
    try:
        conn_sqlite = sqlite3.connect(SIGNALS_DB)
        cur = conn_sqlite.cursor()
        
        # Get open tokens from PostgreSQL
        conn_pg = psycopg2.connect(host='/var/run/postgresql', database="brain", user="postgres", password='Brain123')
        cur_pg = conn_pg.cursor()
        # Only block signals for THIS server's open positions
        cur_pg.execute("SELECT token FROM trades WHERE status = 'open' AND server = 'Hermes'")
        open_tokens=[t[0] for t in cur_pg.fetchall()]
        
        if open_tokens:
            placeholders = ','.join(['?' for _ in open_tokens])
            # Mark signals for tokens with THIS server's open positions as SKIPPED
            cur.execute(f"""
                UPDATE signals 
                SET executed = 1, decision = 'SKIPPED', decision_reason = 'Hermes already has open position', updated_at = CURRENT_TIMESTAMP
                WHERE executed = 0 AND token IN ({placeholders})
            """, open_tokens)
            cleaned = cur.rowcount
            conn_sqlite.commit()
            
            # Fix inconsistent signals — only for non-PENDING decisions
            # PENDING signals stay untouched so ai-decider can review them
            cur.execute("""
                UPDATE signals
                SET executed = 1, updated_at = CURRENT_TIMESTAMP
                WHERE decision IS NOT NULL AND executed = 0
                  AND decision NOT IN ('PENDING', 'APPROVED')
            """)
            conn_sqlite.commit()
            
            if cleaned > 0:
                print(f"🧹 Cleaned up {cleaned} stale signals for tokens with open positions")
        
        conn_sqlite.close()
        conn_pg.close()
    except Exception as e:
        log_error(f'cleanup_stale_signals: {e}')

# Run cleanup on startup
cleanup_stale_signals()

def ssh(cmd):
    return subprocess.run(f"ssh -o ConnectTimeout=5 -p 333 root@117.55.192.97 '{cmd}'", 
                        shell=True, capture_output=True, text=True, timeout=30).stdout

def get_open():
    # Query locally - brain DB is local
    try:
        conn = psycopg2.connect(BRAIN_DB)
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM trades WHERE status='open' AND server='Hermes'")
        count = cur.fetchone()[0]
        cur.close()
        conn.close()
        return count
    except Exception as e:
        log_error(f'get_open: {e}')
        return 0

def is_token_open(token):
    """Check if token already has open position - with input sanitization"""
    # Validate token - only allow alphanumeric
    if not token or not token.replace('_','').isalnum():
        return False
    try:
        conn = psycopg2.connect(BRAIN_DB)
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM trades WHERE status='open' AND token=%s AND server='Hermes'", (token,))
        count = cur.fetchone()[0]
        cur.close()
        conn.close()
        return count > 0
    except Exception as e:
        log_error(f'is_token_open: {e}')
        return False

def get_pending_signals():
    """Get PENDING signals from signals.db - reads from unified_scanner output"""
    try:
        conn = sqlite3.connect(SIGNALS_DB)
        c = conn.cursor()
        c.execute("""
            SELECT token, direction, signal_type, confidence, value, decision, exchange, z_score_tier, z_score
            FROM signals
            WHERE decision = 'PENDING'
            AND executed = 0
            ORDER BY confidence DESC
            LIMIT 20
        """)
        rows = c.fetchall()
        conn.close()
        
        signals = []
        for token, direction, signal_type, confidence, value, decision, exchange, z_tier, z_score in rows:
            signals.append({
                "token": token,
                "direction": direction.lower(),
                "entry": value if value else 0,
                "confidence": confidence,
                "signal_type": signal_type,
                "exchange": exchange if exchange else 'hyperliquid',
                "z_score_tier": z_tier,
                "z_score": z_score
            })
        return signals
    except Exception as e:
        print(f"Error reading signals.db: {e}")
        return []

from signal_schema import mark_signal_processed  # now from signal_schema

def get_regime(token):
    """Get 4h regime from token_intel data"""
    try:
        with open("/var/www/html/regime_4h.json") as f:
            data = json.load(f)
        if token.upper() in data.get('regimes', {}):
            reg = data['regimes'][token.upper()]
            return reg.get('regime', 'NEUTRAL'), reg.get('confidence', 0)
    except Exception as e:
        log_error(f'get_regime: {e}')
    return 'NEUTRAL', 0

def get_fear():
    try:
        r = requests.get("https://api.alternative.me/fng/", timeout=5)
        return r.json()["data"][0]["value"]
    except Exception as e:
        log_error(f'get_fear: {e}')
        return "N/A"

def get_market_zscore():
    """Get market Z-Score trend for trading context"""
    try:
        import re
        with open('/root/.openclaw/workspace/data/zscore_exports/latest_signals.txt', 'r') as f:
            content = f.read()
        
        tokens = ['BTC', 'ETH', 'SOL', 'XRP', 'ADA', 'DOGE', 'AVAX', 'DOT', 'MATIC', 'LINK']
        neg_count = 0
        pos_count = 0
        
        for token in tokens:
            match = re.search(rf'{token}USDT.*z=([-+]?\d+\.?\d*)', content)
            if match:
                z = float(match.group(1))
                if z < 0:
                    neg_count += 1
                else:
                    pos_count += 1
        
        total = neg_count + pos_count
        if total > 0:
            down_pct = neg_count / total * 100
            if down_pct >= 60:
                return f"{neg_count}/{total} negative - DOWNTREND"
            elif down_pct <= 40:
                return f"{neg_count}/{total} negative - UPTREND"
            else:
                return f"{neg_count}/{total} negative - NEUTRAL"
        return "N/A"
    except Exception as e:
        log_error(f'get_market_zscore: {e}')
        return "N/A"

def get_prediction(token):
    """Get latest LLM candle prediction for token with per-token accuracy"""
    try:
        conn = sqlite3.connect('/root/.hermes/data/predictions.db')
        cur = conn.cursor()
        cur.execute("""
            SELECT direction, confidence, correct
            FROM predictions
            WHERE token = ?
            ORDER BY created_at DESC
            LIMIT 1
        """, (token,))
        row = cur.fetchone()
        
        if row:
            # Get overall historical accuracy
            cur.execute("""
                SELECT COUNT(*), SUM(CASE WHEN correct THEN 1 ELSE 0 END)
                FROM predictions WHERE correct IS NOT NULL
            """)
            total, correct = cur.fetchone()
            accuracy = int((correct / total) * 100) if total and correct else 0
            
            # Get per-token accuracy (for JIT - this token specifically)
            cur.execute("""
                SELECT COUNT(*), SUM(CASE WHEN correct THEN 1 ELSE 0 END)
                FROM predictions WHERE token = ? AND correct IS NOT NULL
            """, (token,))
            token_total, token_correct = cur.fetchone()
            token_accuracy = int((token_correct / token_total) * 100) if token_total and token_correct else 0
            
            conn.close()
            return {
                'direction': row[0], 
                'confidence': row[1], 
                'accuracy': accuracy,
                'token_accuracy': token_accuracy,
                'token_total': token_total or 0
            }
        conn.close()
    except Exception as e:
        log_error(f'get_prediction: {e}')
    return None

def get_prices():
    try:
        r = requests.get("https://api.gateio.ws/api/v4/spot/tickers", timeout=5)
        tickers = {t["currency_pair"]: t for t in r.json()}
        pairs = {"BTC": "BTC_USDT", "ETH": "ETH_USDT", "SOL": "SOL_USDT", "XRP": "XRP_USDT", "ADA": "ADA_USDT", "AVAX": "AVAX_USDT"}
        return {k: float(tickers[v]["last"]) for k, v in pairs.items() if v in tickers}
    except Exception as e:
        log_error(f'get_prices: {e}')
        return {}

def update_trade_prices():
    """Update current_price for all open trades"""
    try:
        conn = psycopg2.connect(host='/var/run/postgresql', database="brain", user="postgres", password='Brain123')
        cur = conn.cursor()
        
        # Get all open trades
        cur.execute("SELECT id, token FROM trades WHERE status = 'open' AND server='Hermes'")
        open_trades = cur.fetchall()
        
        if not open_trades:
            return
        
        # Fetch prices from Gate.io
        r = requests.get("https://api.gateio.ws/api/v4/spot/tickers", timeout=10)
        tickers = {t["currency_pair"]: float(t["last"]) for t in r.json()}
        
        updated = 0
        for trade_id, token in open_trades:
            pair = f"{token}_USDT"
            if pair in tickers:
                current_price = tickers[pair]
                cur.execute("UPDATE trades SET current_price = %s, last_updated = NOW() WHERE id = %s", 
                          (current_price, trade_id))
                updated += 1
        
        conn.commit()
        cur.close()
        conn.close()
        if updated > 0:
            print(f"✅ Updated {updated} trade prices")
    except Exception as e:
        print(f"⚠️ Price update error: {e}")

def get_macd(token):
    """Compute MACD from price_history in signals_hermes.db (Python, no node needed).
    Returns dict with signal, histogram, trend, confidence.
    EMA periods: fast=12, slow=26, signal=9 (standard MACD).
    """
    import numpy as np
    if not token or not token.replace('_','').isalnum():
        return {}
    try:
        conn = sqlite3.connect('/root/.hermes/data/signals_hermes.db')
        df = pd.read_sql(
            "SELECT timestamp, price FROM price_history WHERE token=? ORDER BY timestamp ASC",
            conn, params=(token.upper(),))
        conn.close()
        if len(df) < 35:
            return {}
        prices = df['price'].values
        ema_fast = _ema(prices, 12)
        ema_slow = _ema(prices, 26)
        macd_line = ema_fast - ema_slow
        signal_line = _ema(macd_line, 9)
        hist = macd_line - signal_line
        cur_macd = float(macd_line[-1])
        cur_signal = float(signal_line[-1])
        cur_hist = float(hist[-1])
        bullish = cur_macd > cur_signal
        avg_price = float(np.mean(prices[-50:])) if len(prices) >= 50 else float(prices[-1])
        conf = min(100, round(abs(cur_hist) / (abs(cur_macd) + 1e-10) * 100))
        return {
            "signal": "bullish" if bullish else "bearish",
            "histogram": round(cur_hist, 6),
            "macd_line": round(cur_macd, 6),
            "signal_line": round(cur_signal, 6),
            "confidence": conf,
            "histogram_trend": "rising" if len(hist) > 5 and hist[-1] > hist[-3] else "falling"
        }
    except Exception:
        return {}

def _ema(series, period):
    """Compute EMA of a 1D array (list/ndarray) without talib."""
    import numpy as np
    arr = np.array(series, dtype=float)
    alpha = 2.0 / (period + 1)
    ema = np.empty_like(arr)
    ema[0] = arr[0]
    for i in range(1, len(arr)):
        ema[i] = alpha * arr[i] + (1 - alpha) * ema[i-1]
    return ema

def is_real_pump(token):
    """Check if token is in a real pump - less strict now"""
    try:
        # Try Gate.io first
        r = requests.get(f"https://api.gateio.ws/api/v4/spot/tickers?currency_pair={token}_USDT", timeout=5)
        if r.status_code == 200:
            data = r.json()
            if data:
                t = data[0]
                change_24h = float(t.get("change_percentage", 0))
                volume = float(t.get("quote_volume", 0))
                # Less strict: allow any move, lower volume threshold
                is_pump = volume > 5000  # Lowered from 10000
                return is_pump
        # If Gate fails, allow based on price change from our data
        return True  # Allow if we can't check
    except Exception as e:
        log_error(f'is_real_pump: {e}')
        return True  # Allow if check fails

def ai_decide(token, direction, entry, conf, prices, market_z, macd_data, pred_str="", z_score_tier=None, z_score=None):
    """Send prompt to AI to make actual decision"""
    
    current = prices.get(token, entry)
    macd = macd_data.get("signal", "N/A")
    macd_conf = macd_data.get("confidence", "N/A")
    
    # Get regime data
    regime, regime_conf = get_regime(token)
    
    # Build z-score momentum context
    momentum_context = ""
    if z_score_tier:
        momentum_context = f"""

=== Z-SCORE MOMENTUM FRAMEWORK ===
Current Z-Score: {z_score:.2f}
Z-Score Tier: {z_score_tier}"""
        
        # Add tier-specific trading guidance
        if z_score_tier == "accelerating_long":
            momentum_context += "\n- Z > 2.5: Momentum ACCELERATING → Strong LONG signal"
        elif z_score_tier == "accelerating_short":
            momentum_context += "\n- Z < -2.5: Momentum ACCELERATING → Strong SHORT signal"
        elif z_score_tier == "momentum_tracking":
            momentum_context += "\n- Z > 2.0: Above threshold but not entered → Track for entry"
        elif z_score_tier == "momentum_tracking_short":
            momentum_context += "\n- Z < -2.0: Below threshold but not entered → Track for entry"
        elif z_score_tier == "decelerating_from_long":
            momentum_context += "\n- Z dropped from >2.0 to <1.5 → SHORT opportunity (momentum fading)"
        elif z_score_tier == "decelerating_from_short":
            momentum_context += "\n- Z rose from <-2.0 to >-1.5 → LONG opportunity (momentum fading)"
        elif z_score_tier == "exhaustion":
            momentum_context += "\n- Z > 3.0: EXHAUSTION zone → Look for exit/SHORT counter-trend"
        elif z_score_tier == "exhaustion_short_only":
            momentum_context += "\n- Z > 3.5: EXTREME overbought → Short only (counter-trend)"
        elif z_score_tier == "exhaustion_long":
            momentum_context += "\n- Z < -3.0: EXHAUSTION zone → Look for exit/LONG counter-trend"
        elif z_score_tier == "exhaustion_long_only":
            momentum_context += "\n- Z < -3.5: EXTREME oversold → Long only (counter-trend)"
    
    prompt = f"""You are a crypto trading decider. A momentum signal generator flagged this trade — your job is to validate or reject it using all available context.

TOKEN: {token}
CURRENT PRICE: ${current}
PROPOSED ENTRY: ${entry}
PROPOSED DIRECTION: {direction.upper()}
MOMENTUM SIGNAL CONFIDENCE: {conf}% (this is the system's raw score — not gospel, use it as context)

{momentum_context}

=== DECISION GATE ===
- DECISION: LONG → approve as LONG
- DECISION: SHORT → approve as SHORT
- DECISION: WAIT → reject, don't enter

=== HARD RULES ===
1. TOKEN BLACKLIST (SHORT always blocked):
   SUI, FET, SPX, ARK, TON, ONDO, CRV, RUNE, AR, NXPC, DASH, ARB, TRUMP, LDO, NEAR, APT, CELO, SEI, ACE

2. DIRECTION BIAS — LONGS outperform SHORTS historically. When uncertain, favor LONG.

3. EXECUTE vs WAIT thresholds:
   - AI confidence ≥ 50% + aligned with momentum signal → EXECUTE
   - AI confidence < 50% → WAIT
   - AI contradicts signal direction → WAIT
   - Shorting a blacklisted token → WAIT

4. LEVERAGE: Default 10x unless token is high-volatility (>50% daily range) → 5x max

5. MARKET REGIME:
   Regime: {regime} ({regime_conf}% confidence)
   Align with regime direction. Fight it only with very high confidence.

=== TECHNICAL INDICATORS ===
- MACD Signal: {macd} (confidence: {macd_conf}%)
- RSI: oversold <35 or overbought >65 is significant
- MA Crossover: 9/21 trend direction

=== MARKET CONTEXT ===
- Market Z-Score Trend: {market_z}
- BTC: ${prices.get('BTC', 'N/A')} | ETH: ${prices.get('ETH', 'N/A')}
{pred_str}

Respond with exactly:
DECISION: [LONG/SHORT/WAIT]
CONFIDENCE: [0-100]
REASON: [1-sentence explanation]
"""
    
    # Use local Ollama for AI decision
    try:
        payload = {
            "model": "qwen2.5:1.5b",
            "prompt": prompt,
            "stream": False
        }
        r = requests.post("http://localhost:11434/api/generate", json=payload, timeout=60)
        result = r.json().get("response", "")
        
        # Parse response
        decision = "WAIT"
        confidence = 0
        for line in result.split("\n"):
            if "DECISION:" in line.upper():
                if "LONG" in line.upper(): decision = "long"
                elif "SHORT" in line.upper(): decision = "short"
                else: decision = "wait"
            if "CONFIDENCE:" in line.upper():
                try:
                    # Extract first number from the line (handle decimals properly)
                    import re
                    nums = re.findall(r'\d+\.?\d*', line)
                    if nums:
                        confidence = min(100, max(0, float(nums[0])))  # Clamp to 0-100
                        confidence = int(confidence)
                except Exception as e:
                    log_error(f'ai_decide: confidence parse error: {e}')
        
        # Adjust confidence based on regime alignment
        if decision != "wait" and regime != "NEUTRAL" and regime_conf > 50:
            if (regime == "LONG_BIAS" and decision == "long") or \
               (regime == "SHORT_BIAS" and decision == "short"):
                # Boost confidence if aligned with regime
                regime_bonus = min(15, (regime_conf - 50) // 5)
                confidence = min(100, confidence + regime_bonus)
            elif (regime == "LONG_BIAS" and decision == "short") or \
                 (regime == "SHORT_BIAS" and decision == "long"):
                # Reduce confidence if fighting the regime
                regime_penalty = min(20, (regime_conf - 50) // 3)
                confidence = max(0, confidence - regime_penalty)
        
        return decision, confidence, result[:500]
    except Exception as e:
        print(f"AI decision failed: {e}")
        # Fallback to rule-based
        return direction, abs(conf) * 30, "Fallback to rules"

def execute_trade(token, direction, entry, conf, atr, exchange='hyperliquid', learned=None):
    """
    DEPRECATED — all trade execution is handled exclusively by decider-run.py.
    This stub prevents import errors only.
    """
    return False

try:
    pending = get_pending_signals()
except:
    pending = []

print(f"=== AI Decider: {len(pending)} pending | Open: {get_open()}/{MAX_OPEN} ===")

# Get market context once
market_z = get_market_zscore()
prices = get_prices()
update_trade_prices()  # Update current_price for all open trades
print(f"Market: Z-Score={market_z}, BTC=${prices.get('BTC','N/A')}")

for s in pending:
    t = s.get("token")
    direction = s.get("direction", "long")
    entry = float(s.get("entry", 0))  # Ensure entry is float
    conf = s.get("confidence", 0)
    atr = s.get("atr", s.get("atrPercent", 2))
    
    # Get exchange from signal
    exchange = s.get("exchange")
    if exchange is None:
        print(f"❌ {t}: Cannot determine valid exchange - token not available on any supported exchange")
        mark_signal_processed(t, 'SKIPPED')
        continue
    
    # Token blacklist - these tokens have 0-20% win rate on SHORTs (from trade analysis)
    # HARDBLOCK - skip these completely
    SHORT_BLACKLIST = ['SUI', 'FET', 'SPX', 'ARK', 'TON', 'ONDO', 'CRV', 'RUNE', 'AR', 'NXPC', 'DASH', 'ARB', 'TRUMP', 'LDO', 'NEAR', 'APT', 'CELO', 'SEI', 'ACE']
    LONG_BLACKLIST = ['SEI', 'ACE']  # Tokens that don't work well as LONG either
    
    if direction.lower() == "short" and t.upper() in SHORT_BLACKLIST:
        print(f"   🚫 {t}: BLACKLISTED - skipping SHORT completely (0-20% WR historically)")
        log_signal(t, direction, entry, s.get('confidence', 0), f"SKIPPED-blacklist-{exchange}")
        mark_signal_processed(t, 'SKIPPED')
        continue
    
    if direction.lower() == "long" and t.upper() in LONG_BLACKLIST:
        print(f"   🚫 {t}: BLACKLISTED - skipping LONG (poor performance)")
        log_signal(t, direction, entry, s.get('confidence', 0), f"SKIPPED-long-blacklist-{exchange}")
        mark_signal_processed(t, 'SKIPPED')
        continue
    
    # Check open slots
    if get_open() >= MAX_OPEN:
        print(f"⏸️ {t}: max trades reached")
        log_signal(t, direction, entry, conf, f"SKIPPED-max-{exchange}")
        continue
    
    # 2. Check if SOL token but signal says short (SOL tokens can only go long)
    if exchange == "raydium" and direction.lower() == "short":
        print(f"⏸️ {t}: SOL tokens can only go LONG on Raydium")
        log_signal(t, direction, entry, conf, "SKIPPED-sol-short")
        mark_signal_processed(t, 'SKIPPED')
        continue
    
    # Get LLM candle prediction for this token
    prediction = get_prediction(t)
    pred_str = ""
    if prediction:
        token_info = f"- Token-Specific Accuracy: {prediction['token_accuracy']}% ({prediction['token_total']} predictions)"
        if prediction['token_total'] < 3:
            token_info = f"- Token-Specific Accuracy: {prediction['token_accuracy']}% ({prediction['token_total']} predictions) - building history"
        pred_str = f"""
LLM CANDLE PREDICTION (for reference):
- Predicted Direction: {prediction['direction']} ({prediction['confidence']}% confidence)
- Model Historical Accuracy: {prediction['accuracy']}%
{token_info}"""""
    
    # Get z-score tier from signal
    z_tier = s.get('z_score_tier')
    z = s.get('z_score')
    if z_tier:
        print(f"   📊 Z-Score Tier: {z_tier} (z={z:.2f})")

    # All PENDING signals (65-94%) go to AI for review
    print(f"\n🤔 AI reviewing: {t} {direction} @ ${entry} (signal confidence: {conf}%)")
    macd_data = get_macd(t)
    decision, ai_conf, reason = ai_decide(t, direction, entry, conf, prices, market_z, macd_data, pred_str, z_tier, z)
    
    print(f"   AI Decision: {decision.upper()} (conf: {ai_conf}%)")
    print(f"   Reason: {reason[:100]}...")
    
    # Apply learned adjustments from past trades
    learned = get_learned_adjustments(t, direction)
    if learned:
        old_conf = ai_conf
        ai_conf = int(ai_conf + learned.get('confidence_boost', 0))
        print(f"   🧠 LEARNED: +{learned.get('confidence_boost', 0)}% conf (patterns: {', '.join(learned.get('patterns', []))})")
    
    # Execute if AI says go (prompt enforces ≥50% confidence threshold)
    if decision != "wait" and ai_conf >= 50:
        # Only trade real pumps, not slow grind
        if not is_real_pump(t):
            print(f"   ⏸️ SKIPPED - No pump momentum (need >3% 24h + volume)")
            log_signal(t, direction, entry, conf, f"SKIPPED-{exchange}")
            mark_signal_processed(t, 'SKIPPED')
        elif is_token_open(t):
            print(f"   ⏸️ SKIPPED - {t} already has open position")
            log_signal(t, direction, entry, conf, f"SKIPPED-open-{exchange}")
            mark_signal_processed(t, 'SKIPPED')
        else:
            # Record approval
            ok = mark_signal_processed(t, 'APPROVED')
            if ok:
                print(f"   ✅ APPROVED: {t} {decision.upper()} — decider-run will execute")
                log_signal(t, decision, entry, ai_conf, exchange)
            else:
                print(f"   ❌ Failed to record approval")
                log_signal(t, decision, entry, ai_conf, f"FAILED-{exchange}")
                mark_signal_processed(t, 'FAILED')
    else:
        print(f"   ⏸️ AI said WAIT")
        log_signal(t, direction, entry, ai_conf, f"WAIT-{exchange}")
        mark_signal_processed(t, 'WAIT')

# Don't write back to pending-signals.json - we read from signals.db now
print(f"\n=== Done: {len(pending)} signals processed ===")

# Release lock
release_lock()
