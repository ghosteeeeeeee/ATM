#!/usr/bin/env python3
"""
AI Decider - Actually thinks and decides using all available info
"""
import subprocess, json, time, sys, requests, sqlite3, psycopg2, os, random, shlex, traceback
from datetime import datetime, timezone
import pandas as pd
sys.path.insert(0, '/root/.hermes/scripts')
from _secrets import BRAIN_DB_DICT

# Speed feature: speed percentile boosts compaction survival
try:
    from speed_tracker import SpeedTracker
    speed_tracker_ai = SpeedTracker()
except Exception as e:
    print(f"[ai-decider] SpeedTracker unavailable: {e}")
    speed_tracker_ai = None

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
sys.path.insert(0, '/root/.hermes/scripts')
from hermes_constants import SHORT_BLACKLIST, LONG_BLACKLIST

# ─── Source confidence weights ────────────────────────────────────────────────
# Single config for all signal source multipliers applied to raw confidence.
# > 1.0 = boost (trust more), < 1.0 = suppress (trust less).
# mtf_macd with hmacd- source = MACD crossovers = clearest trend signals = 1.2x.
# Other hmacd-* sources = weaker/secondary = 0.6x (penalize, don't trust alone).
# All others = 1.0 (neutral).
SOURCE_WEIGHTS = {
    'hmacd-mtf_macd': 1.2,   # MACD crossovers — strong trend confirmation
    'hmacd-default': 0.6,   # Other hmacd-derived signals — penalize
}
# Master map: (signal_type, source_prefix) -> weight
# Checked in order; first match wins. None = neutral 1.0.
SOURCE_WEIGHT_OVERRIDES = [
    ('mtf_macd',  'hmacd-',  1.2),   # hmacd- + mtf_macd = MACD crossover
    # All other hmacd-* sources (pct-hermes, etc.) fall through to default 0.6
]
DEFAULT_SOURCE_WEIGHT = 1.0

def _get_source_weight(stype, source):
    """Return confidence multiplier for (signal_type, source)."""
    if not source:
        return DEFAULT_SOURCE_WEIGHT
    # Check explicit overrides first
    for stype_pattern, source_prefix, weight in SOURCE_WEIGHT_OVERRIDES:
        if stype == stype_pattern and source.startswith(source_prefix):
            return weight
    # hmacd-* but not mtf_macd → penalize
    if source.startswith('hmacd-'):
        return SOURCE_WEIGHTS.get('hmacd-default', 0.6)
    return DEFAULT_SOURCE_WEIGHT

SIGNALS_DB = '/root/.hermes/data/signals_hermes_runtime.db'
AB_RESULTS_FILE = '/root/.hermes/data/ab-test-results.json'
AB_CACHE_FILE = '/root/.openclaw/workspace/data/ab-variant-cache.json'

# Hot-set failure tracking — persists across cycles so warnings keep appearing
_hot_set_failure_count = 0

# Lazy-load signal streak from position_manager (avoids circular import at module load)
_signal_streak_cache = {}  # key: (coin, direction, signal_type) -> {'streak': N, 'fetched_at': float}
_signal_streak_timestamps = {}  # key -> last-fetched timestamp (TTL per-key)
_STREAK_TTL = 300  # refresh streak data every 5 minutes

def _get_signal_streak(coin, direction, signal_type):
    """Get cached signal streak, refreshed every 5 minutes (per-key TTL)."""
    global _signal_streak_cache, _signal_streak_timestamps
    key = (coin.upper(), direction.upper(), (signal_type or '').lower())
    now = time.time()
    ts = _signal_streak_timestamps.get(key, 0)
    if key not in _signal_streak_cache or (now - ts) > _STREAK_TTL:
        try:
            sys.path.insert(0, '/root/.hermes/scripts')
            from position_manager import get_signal_streak as _gs
            _signal_streak_cache[key] = _gs(coin, direction, signal_type)
            _signal_streak_timestamps[key] = now
        except Exception:
            log(f'[ai-decider] WARNING: streak cache fetch failed for {coin} {direction} — using defaults')
            return {'streak': 0, 'multiplier': 1.0, 'win_rate_20': 0.5, 'n': 0}
    return _signal_streak_cache.get(key, {'streak': 0, 'multiplier': 1.0, 'win_rate_20': 0.5, 'n': 0})

def _load_signal_streaks_batch(rows):
    """Pre-load streaks for all signal_type keys in a batch of candidates.
    Respects TTL per-key (refreshes stale entries). Logs failures instead of silent pass."""
    global _signal_streak_cache, _signal_streak_timestamps
    now = time.time()
    loaded = 0
    skipped = 0
    try:
        sys.path.insert(0, '/root/.hermes/scripts')
        from position_manager import get_signal_streak as _gs
        for row in rows:
            sid, coin, direction, stype, conf, source, created = row
            key = (coin.upper(), direction.upper(), (stype or '').lower())
            ts = _signal_streak_timestamps.get(key, 0)
            if (now - ts) > _STREAK_TTL:
                _signal_streak_cache[key] = _gs(coin, direction, stype)
                _signal_streak_timestamps[key] = now
                loaded += 1
            else:
                skipped += 1
        if loaded > 0:
            print(f'[ai-decider] Streaks loaded: {loaded} fresh, {skipped} cached')
    except Exception as e:
        import traceback; traceback.print_exc()
        print(f'[ai-decider] WARNING: streak batch load failed: {e} — using defaults')

# In-memory cache for A/B variants per token+direction (cleared on restart)
_ab_variant_cache = {}

# ── Hot set tracker ────────────────────────────────────────────────────────────
# token -> {direction, compact_rounds, survival_score} for PENDING hot signals.
# Loaded once per ai_decider run, used to:
#   1. Auto-approve r2+ signals (proven by AI across multiple rounds)
#   2. Kill hot set signals when an opposite-direction signal flips the view
_hot_rounds = {}   # coin.upper() -> {direction, rounds, survival}

def _load_hot_rounds():
    """
    Load hot signals based on review_count (ai-decider survival passes).

    A hot signal is one where ai-decider reviewed the same token/direction
    as PENDING at least 2 times without executing or hard-skipping it.
    review_count is incremented every time ai-decider marks a signal SKIPPED
    or WAIT (via mark_signal_processed in signal_schema.py).

    Also enriches with PENDING signal data (signal_ids, avg_conf, num_types).

    Returns:
        dict: coin.upper() -> {direction, rounds, signal_ids, avg_conf, num_types}
    """
    global _hot_rounds, _hot_set_failure_count  # BUG-11 fix: declare before use in except block
    _hot_rounds = {}
    try:
        conn = sqlite3.connect(SIGNALS_DB)
        c = conn.cursor()

        # FIX (2026-04-02): Also include tokens with rc>=1 EXPIRED signals.
        # When positions are full, strong signals get SKIPPED→EXPIRED.
        # rc=1 EXPIRED = reviewed once by AI, then expired (never reached rc=2).
        # IMPORTANT: We only include EXPIRED with rc>=1, not rc=0 — rc=0 EXPIRED
        # signals were NEVER reviewed by AI (just aged out of signal_gen), and
        # including them floods the hot set with tokens that never passed AI review.
        # review_count>=1 proves: "AI already looked at this token."
        c.execute("""
            SELECT token, direction, MAX(review_count) as rounds,
                   GROUP_CONCAT(DISTINCT signal_type) as types, source
            FROM signals
            WHERE (decision IN ('PENDING', 'APPROVED', 'WAIT')
                   OR (decision = 'EXPIRED' AND review_count >= 1))
              AND review_count >= 1
              AND created_at > datetime('now', '-3 hours')
              AND token || direction NOT IN (
                  SELECT token || direction FROM signals
                  WHERE decision = 'APPROVED' AND executed = 0
              )
            GROUP BY token, direction
            HAVING COUNT(*) >= 1
        """)
        rows = c.fetchall()

        for row in rows:
            t = row[0].upper()
            direction = row[1]
            rounds = row[2] or 0
            types_list = [x for x in (row[3] or '').split(',') if x]
            source = row[4] or 'unknown'

            # Get ALL non-executed signal IDs and quality metrics for this token+direction.
            # FIX (2026-04-01): Previously only queried decision='PENDING', so signals that
            # advanced to APPROVED or WAIT had their avg_conf/num_types computed from nothing
            # (defaulting to 50.0/0), causing them to fail the quality gate and stagnate.
            c.execute("""
                SELECT id, AVG(confidence) as avg_conf, COUNT(DISTINCT signal_type) as num_types
                FROM signals
                WHERE token=?? AND direction=? AND decision IN ('PENDING','APPROVED','WAIT') AND executed=0
            """, (t, direction))
            sig_row = c.fetchone()
            sig_id = sig_row[0] if sig_row else None
            avg_conf = sig_row[1] if sig_row else 50.0
            num_types = sig_row[2] if sig_row else len(types_list)
            ids_list = [sig_id] if sig_id else []

            # Get all signal IDs for this token+direction (for mark_signal_processed)
            c.execute("""
                SELECT id FROM signals
                WHERE token=?? AND direction=? AND decision IN ('PENDING','APPROVED','WAIT') AND executed=0
            """, (t, direction))
            ids_list = [r[0] for r in c.fetchall()]

            _hot_rounds[t] = {
                'direction': direction,
                'rounds': rounds,
                'signal_ids': ids_list,
                'avg_conf': avg_conf,
                'num_types': num_types,
                'source': source,
            }

        conn.close()
        # BUG-11 fix: reset failure count on successful load
        if _hot_set_failure_count > 0:
            print(f"[ai-decider] Hot set recovered after {_hot_set_failure_count} failure(s)")
        _hot_set_failure_count = 0
    except Exception as e:
        import traceback; traceback.print_exc()
        _hot_set_failure_count += 1
        # Only disable permanently after 10 consecutive failures
        if _hot_set_failure_count >= 10:
            print(f"[ai-decider] CRITICAL: _load_hot_rounds FAILED 10x — hot-set DISABLED. {e}")
        else:
            print(f"[ai-decider] _load_hot_rounds failed ({_hot_set_failure_count}/10): {e}")


def _kill_hot_signal(coin):
    """Kill a hot set signal (mark COMPACTED so it's removed from hot set immediately."""
    try:
        conn = sqlite3.connect(SIGNALS_DB)
        c = conn.cursor()
        c.execute("""
            UPDATE signals
            SET decision = 'COMPACTED', executed = 1,
                updated_at = CURRENT_TIMESTAMP
            WHERE token=?? AND decision IN ('PENDING','APPROVED') AND executed = 0
            LIMIT 1
        """, (token,))
        killed = c.rowcount
        conn.commit()
        conn.close()
        return killed
    except Exception:
        return 0

def _kill_pending_opposite(coin, hot_direction):
    """
    Kill PENDING signals in the OPPOSITE direction to the hot set.
    Hot direction has priority — newer signals in the wrong direction get killed.
    """
    opposite = 'SHORT' if hot_direction.upper() == 'LONG' else 'LONG'
    try:
        conn = sqlite3.connect(SIGNALS_DB)
        c = conn.cursor()
        c.execute("""
            UPDATE signals
            SET decision = 'COMPACTED', executed = 1,
                updated_at = CURRENT_TIMESTAMP
            WHERE token=?? AND direction=? AND decision='PENDING' AND executed=0
            LIMIT 5
        """, (coin.upper(), opposite))
        killed = c.rowcount
        conn.commit()
        conn.close()
        return killed
    except Exception:
        return 0

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
                    for coin, info in data.items():
                        if isinstance(info, dict) and 'price' in info:
                            prices[coin] = str(info['price'])
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

def get_cached_ab_variant(coin, direction, test_name):
    """Get cached A/B variant or select new one"""
    key = f"{coin}:{direction}"
    if key not in _ab_variant_cache:
        _ab_variant_cache[key] = {}
    
    if test_name not in _ab_variant_cache[key]:
        _ab_variant_cache[key][test_name] = select_ab_variant(test_name)
    
    return _ab_variant_cache[key][test_name]

def clear_ab_cache(coin = None, direction=None):
    """Clear A/B cache - optionally for specific token"""
    if coin:
        key = f"{coin}:{direction or 'long'}"
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
    Select a variant for a given A/B test.
    Uses Thompson sampling from ab_utils (canonical implementation).
    Thompson sampling is superior to epsilon-greedy: it samples from posterior
    distributions rather than greedily picking the best-known option.
    """
    try:
        from ab_utils import get_ab_variant
        return get_ab_variant(test_name, direction='both')
    except Exception as e:
        log_error(f'select_ab_variant Thompson sampling failed: {e}')
        return None

def get_ab_params(coin, direction='long'):
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
    sl_test = get_cached_ab_variant(coin, direction, 'sl-distance-test')
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
    entry_test = get_cached_ab_variant(coin, direction, 'entry-timing-test')
    if entry_test:
        cfg = entry_test.get("config", {})
        result['entry_mode'] = cfg.get("entryMode", "immediate")
        result['pullback_pct'] = cfg.get("pullbackPct", 0.01)
        result['max_wait_minutes'] = cfg.get("maxWaitMinutes", 30)
        result['variant_id'] = entry_test.get('id', '')
        result['test_name'] = 'entry-timing-test'
        print(f"  [AB] Entry Mode: {result['entry_mode']} (variant: {entry_test.get('id')})")

    # ── Trailing Stop Test ─────────────────────────────────────────
    ts_test = get_cached_ab_variant(coin, direction, 'trailing-stop-test')
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

BRAIN_DB = f"host={BRAIN_DB_DICT['host']} dbname={BRAIN_DB_DICT['database']} user={BRAIN_DB_DICT['user']} password=***"

def get_learned_adjustments(coin, direction='long'):
    """
    Get learned pattern adjustments from brain.trade_patterns for a token/direction.
    
    Key fixes:
    - psycopg2 JSONB columns return Python dict (not JSON string) — no json.loads() needed.
      But the DB may contain legacy string values, so we handle both gracefully.
    - sample_count >= 1 (was >= 3, which blocked all patterns since most have count=1).
    - Token comparison is case-insensitive via UPPER().
    """
    try:
        conn = psycopg2.connect(BRAIN_DB)
        cur = conn.cursor()
        cur.execute("""
            SELECT pattern_name, confidence, adjustment, sample_count
            FROM trade_patterns
            WHERE UPPER(token) = UPPER(%s)
              AND (LOWER(side) = LOWER(%s) OR side = 'any')
              AND sample_count >= 1
            ORDER BY confidence DESC
            LIMIT 3
        """, (coin, direction))
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
            # psycopg2 JSONB returns dict; legacy strings are possible (handle both)
            raw_adj = p[2]
            if raw_adj is None:
                adj = {}
            elif isinstance(raw_adj, dict):
                adj = raw_adj
            else:
                try:
                    adj = json.loads(raw_adj) if isinstance(raw_adj, str) else {}
                except (json.JSONDecodeError, ValueError) as e:
                    log_error(f'get_learned_adjustments: json.loads failed for pattern {p[0]}: {e}')
                    adj = {}
            
            # Weight by confidence and sample_count
            conf_val = float(p[1] or 0.5)
            sample = int(p[3] or 1)
            weight = conf_val * min(sample, 10) / 10
            
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

def log_ab_trade_opened(coin, direction, tp_multiplier, sl_pct, risk_reward, tp_pct, sl_pct_display,
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
            "token": coin,
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

def record_ab_trade_closed(coin, pnl_pct, pnl_usdt):
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
            if entry.get("token") == coin and entry.get("event") == "opened" and "closed_at" not in entry:
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
# FIXED: ai_decider now reads from signals_hermes_runtime.db (Hermes's DB)
# signal_gen writes to runtime DB, not OpenClaw's signals.db
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

def log_signal(coin, direction, price, confidence, source):
    """Log signal to signals.log for signals.html display"""
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")
    with open(SIGNAL_LOG, "a") as f:
        f.write(f"{timestamp} SIGNAL: {coin} {direction.upper()} @ {price} ({confidence}%) [{source}]\n")

def cleanup_stale_signals():
    """Clean up stale signals on startup - prevents backlog"""
    try:
        conn_sqlite = sqlite3.connect(SIGNALS_DB)
        cur = conn_sqlite.cursor()
        
        # Get open tokens from PostgreSQL
        conn_pg = psycopg2.connect(**BRAIN_DB_DICT)
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
    """Get PENDING signals from signals_hermes_runtime.db.

    LIFO + confidence ordering: newest signals first, confidence breaks ties.
    Only signals within 15 minutes are returned (auto-expired older ones).
    Compacts the DB to top 20 signals on each call — AI picks which to keep
    based on freshness + confidence + agreement across indicators.
    """
    try:
        conn = sqlite3.connect(SIGNALS_DB)
        c = conn.cursor()

        # FIX (2026-04-02): Changed from 30 to 720 min (12 hours).
        # The 30-minute window was too short — signals were expiring before the
        # hot-set could review them. With 12h TTL, signals have ample time to
        # accumulate review_count through multiple ai-decider passes.
        c.execute("""
            UPDATE signals
            SET decision = 'EXPIRED', executed = 1, updated_at = CURRENT_TIMESTAMP
            WHERE decision = 'PENDING'
              AND created_at < datetime('now', '-720 minutes')
        """)
        expired = c.rowcount
        conn.commit()

        # ── RULE 3: PURGE — expire signals surviving too many compaction rounds ──
        # If a PENDING signal has survived 20+ compaction rounds, it's stuck.
        # It keeps accumulating survival_score but never gets acted on (wrong direction,
        # wrong regime, etc.). Force-expire it so new fresh signals can take its place.
        PURGE_THRESHOLD = 20  # compaction rounds
        c.execute("""
            UPDATE signals
            SET decision = 'EXPIRED', executed = 1,
                deescalation_reason = 'purge-surviving-signal',
                updated_at = CURRENT_TIMESTAMP
            WHERE decision = 'PENDING'
              AND compact_rounds >= ?
        """, (PURGE_THRESHOLD,))
        purged = c.rowcount
        if purged > 0:
            print(f"  [Compaction PURGE] {purged} PENDING signals expired (>={PURGE_THRESHOLD} compaction rounds survived)")

        # ── 2. AI-guided compaction: score and keep top 20 ─────────────────────
        # Score = recency_boost + confidence + confluence_bonus
        # recency_boost: newer signals get exponentially higher scores
        # confidence: direct bonus
        # confluence_bonus: tokens with multiple agreeing signal types get a boost
        c.execute("""
            SELECT id, token, direction, signal_type, confidence, source, created_at
            FROM signals
            WHERE decision = 'PENDING'
              AND executed = 0
              AND created_at > datetime('now', '-720 minutes')
        """)
        candidates = c.fetchall()

        # FIX (2026-04-02): Extended compaction window from 30min to 12h.
        # Previously signals older than 30min were invisible to the AI's hot-set
        # scoring — they'd never accumulate survival_score or reach review_count.
        # With 12h window, signals get proper review cycles (ai-decider runs ~every
        # 1min) before compaction decisions are made.
        # Always score all candidates — this increments compact_rounds for EVERY signal
        # each cycle, building their survival history so the hot set populates even
        # with <20 signals. With <=20 candidates, ALL survive (no compaction).
        # With >20, top 20 survive and rest are compacted (existing behavior).
        if candidates:
            # Pre-load signal streaks for all candidates (batched, single DB connection)
            _load_signal_streaks_batch(candidates)

            # Score each signal: confluence > confidence > survival_meta > streak > recency
            scored = []
            now_ts = time.time()
            now_str = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
            for row in candidates:
                sid, coin, direction, stype, conf, source, created = row

                # Fetch survival data from signal record
                c.execute("SELECT compact_rounds, survival_score FROM signals WHERE id = ?", (sid,))
                surv_row = c.fetchone()
                compact_rounds = surv_row[0] if surv_row else 0
                survival_meta = surv_row[1] if surv_row else 0.0

                # Confluence: base score from agreeing signal types
                agreeing = sum(1 for r in candidates
                               if r[1] == coin and r[2] == direction and r[3] != stype)
                base_confluence = 1.0 + min(agreeing, 2) * 0.5  # 1.0 to 2.0

                # Signal-type quality multiplier for confluence signals
                # conf-2s: weak (only 2 agreeing indicators, often noise)
                # conf-3s+: strong (3+ indicators = genuine confluence)
                # conf-4s+: very strong (rare, high conviction)
                if stype == 'confluence' and source and source.startswith('conf-'):
                    try:
                        n = int(source.split('-')[1].rstrip('s'))  # e.g. 'conf-2s' -> 2
                    except (ValueError, IndexError):
                        n = 2
                    if n == 2:
                        base_confluence *= 0.4   # 0.4 to 0.8 — penalize weak 2-signal confluence
                    elif n == 3:
                        base_confluence *= 1.1   # 1.1 to 2.2 — reward strong 3-signal
                    elif n >= 4:
                        base_confluence *= 1.4   # 1.4 to 2.8 — very rare, very strong
                confluence_score = base_confluence

                # Source confidence weight from centralized config
                source_weight = _get_source_weight(stype, source)

                # Confidence (scaled by source weight)
                conf_score = (conf / 100.0) * source_weight

                # Recency
                try:
                    created_dt = datetime.strptime(created, '%Y-%m-%d %H:%M:%S')
                    created_ts = created_dt.replace(tzinfo=timezone.utc).timestamp()
                    age_min = (now_ts - created_ts) / 60.0
                    recency_score = max(0.0, 1.0 + (0.3 * max(0, (5 - age_min) / 5)))
                except (ValueError, TypeError):
                    recency_score = 1.0

                # Signal quality streak (hot boost, cold suppress)
                streak = _get_signal_streak(coin, direction, stype)
                streak_mult = streak.get('multiplier', 1.0)

                # Survival meta: compounding bonus per round survived
                survival_bonus = min(1.0, compact_rounds * 0.2 + survival_meta * 0.3)
                survival_score_raw = 1.0 + survival_bonus

                # SPEED FEATURE: speed percentile boosts survival in compaction
                # Fast-moving tokens survive compaction longer — we want to be in movers.
                speed_score = 0.0
                if speed_tracker_ai is not None:
                    spd = speed_tracker_ai.get_token_speed(coin)
                    if spd:
                        speed_score = (spd.get('speed_percentile', 50.0) / 100.0) * 0.10

                # Score = confluence(5%) + confidence(40%) + survival(20%) + streak(20%) + recency(15%) + speed(10%)
                raw_score = (
                    confluence_score   * 0.05 +
                    conf_score         * 0.40 +
                    survival_score_raw * 0.20 +
                    streak_mult        * 0.20 +
                    recency_score      * 0.15 +
                    speed_score        * 0.10
                )
                scored.append({
                    'score': raw_score,
                    'raw': raw_score,
                    'survival_bonus': survival_bonus,
                    'streak_mult': streak_mult,
                    'confluence_score': confluence_score,
                    'conf_score': conf_score,
                    'source_weight': source_weight,
                    'recency_score': recency_score,
                    'speed_score': speed_score,
                    'compact_rounds': compact_rounds,
                    'survival_meta': survival_meta,
                    'sid': sid,
                    'token': coin,
                    'direction': direction,
                    'stype': stype,
                    'conf': conf,
                    'source': source,
                    'row': row,
                })

            # Sort and partition: top 20 survive, rest are compacted (only when >20)
            scored.sort(key=lambda x: -x['score'])
            keep_all = len(candidates) <= 20  # when few signals, ALL survive
            compacted_count = 0
            compact_round = int(time.time())
            keep_sids = {s['sid'] for s in scored[:20]}  # O(1) set for membership test

            # Update ALL signals: increment compact_rounds, update survival_score, record history
            for s in scored:
                new_survival = s['survival_meta'] + 0.5
                c.execute("""
                    UPDATE signals
                    SET compact_rounds = compact_rounds + 1,
                        survival_score = ?,
                        last_compact_at = ?,
                        review_count = COALESCE(review_count, 0) + 1
                    WHERE id = ?
                """, (round(new_survival, 3), now_str, s['sid']))

                # Record survival history for ALL signals (survived=1)
                c.execute("""
                    INSERT INTO signal_history
                        (token, direction, signal_type, compact_round, survived, score_before, score_after, reason)
                    VALUES (?, ?, ?, ?, 1, ?, ?, ?)
                """, (s['token'], s['direction'], s['stype'], compact_round,
                      round(s['raw'], 3), round(s['score'], 3),
                      f'survived_r{s["compact_rounds"]+1}_conf{s["conf"]:.0f}'))

            # Only compact (expire bottom signals) when we have >20 candidates
            # FIX (2026-04-02): Signals with confidence >= 85% are EXEMPT from compaction.
            # These are strong signals that have survived multiple AI review passes
            # and deserve a chance to reach APPROVED/execution. Compacting them
            # at 286 signals (avg 94% conf) was destroying good opportunities.
            EXEMPT_CONFIDENCE = 85
            if not keep_all:
                # Separate exempt signals from compactable ones
                exempt_sids = {s['sid'] for s in scored if s['conf'] >= EXEMPT_CONFIDENCE}
                compactable = [s for s in scored if s['sid'] not in exempt_sids]
                # Keep top 20 compactable signals, compact the rest
                keep_sids = {s['sid'] for s in compactable[:20]} | exempt_sids
                expire_ids = [s['sid'] for s in compactable[20:]]
                compacted_count = len(expire_ids)
                if expire_ids:
                    placeholders = ','.join(['?' for _ in expire_ids])
                    for s in compactable[20:]:
                        c.execute("""
                            INSERT INTO signal_history
                                (token, direction, signal_type, compact_round, survived, score_before, score_after, reason)
                            VALUES (?, ?, ?, ?, 0, ?, ?, ?)
                        """, (s['token'], s['direction'], s['stype'], compact_round,
                              round(s['raw'], 3), 0.0,
                              f'compacted_r{s["compact_rounds"]}_losing_conf{s["conf"]:.0f}'))
                    c.execute(f"""
                        UPDATE signals
                        SET decision = 'EXPIRED', executed = 1, updated_at = CURRENT_TIMESTAMP
                        WHERE id IN ({placeholders})
                    """, expire_ids)
                    if exempt_sids:
                        print(f"  [compaction] EXEMPT: {len(exempt_sids)} high-confidence signals protected from compaction (conf>={EXEMPT_CONFIDENCE}%)")

            conn.commit()

            # Log compaction activity
            if compacted_count > 0 or expired > 0:
                top = scored[0]
                print(f'  [compaction] kept={"all" if keep_all else "20"} expired_auto={expired} compacted={compacted_count} '
                      f'(top: {top["token"]}/{top["direction"]} r{top["compact_rounds"]+1}+, '
                      f'survival={top["survival_bonus"]:.2f} streak={top["streak_mult"]:.2f}x, '
                      f'speed={top["speed_score"]:.3f}, conf={top["conf_score"]:.0%})')

        # ── 3. Fetch top 20 LIFO + confidence ────────────────────────────────
        c.execute("""
            SELECT token, direction, signal_type, confidence, value, exchange, z_score_tier, z_score, compact_rounds, source
            FROM signals
            WHERE decision = 'PENDING'
              AND executed = 0
            ORDER BY created_at DESC, confidence DESC
            LIMIT 20
        """)
        rows = c.fetchall()
        conn.close()

        # Build hot set: tokens with signal_history survival data (hot signals first)
        hot_tokens = set(_hot_rounds.keys())

        signals = []
        hot_signals = []
        non_hot_signals = []
        for row in rows:
            coin, direction, stype, confidence, value, exchange, z_tier, z_score, compact_rounds, source = row
            # BUG-12 fix: validate source against whitelist before using in A/B routing/logging
            safe_source = validate_source(source) if source else 'unknown'
            sig = {
                "token": coin,
                "direction": direction.lower(),
                "entry": value if value else 0,
                "confidence": confidence,
                "signal_type": stype,
                "exchange": exchange if exchange else 'hyperliquid',
                "z_score_tier": z_tier,
                "z_score": z_score,
                "compact_rounds": compact_rounds or 0,
                "source": safe_source,  # BUG-12: validated source
            }
            if coin.upper() in hot_tokens:
                hot_signals.append(sig)
            else:
                non_hot_signals.append(sig)

        # Hot signals first, then the rest (hot = proven by AI across 2+ rounds)
        return hot_signals + non_hot_signals
    except Exception as e:
        import traceback; traceback.print_exc()
        log_error(f"get_pending_signals DB read error: {e}")
        return []

from signal_schema import mark_signal_processed, validate_source  # BUG-12: validate source against whitelist

def get_regime(coin):
    """Get 4h regime from regime_4h.json (primary) or momentum_cache (fallback).
    Returns (regime_str, confidence_int)."""
    # Primary: read from JSON file written by 4h_regime_scanner
    try:
        with open("/var/www/html/regime_4h.json") as f:
            data = json.load(f)
        if coin.upper() in data.get('regimes', {}):
            reg = data['regimes'][coin.upper()]
            return reg.get('regime', 'NEUTRAL'), reg.get('confidence', 0)
    except Exception as e:
        log_error(f'get_regime JSON: {e}')

    # Fallback: query momentum_cache in PostgreSQL brain DB directly
    # This covers tokens that the scanner scanned but didn't write to the JSON
    try:
        conn = psycopg2.connect(**BRAIN_DB_DICT)
        cur = conn.cursor()
        cur.execute("""
            SELECT regime_4h, updated_at FROM momentum_cache
            WHERE token = %s
            ORDER BY updated_at DESC LIMIT 1
        """, (coin.upper(),))
        row = cur.fetchone()
        cur.close()
        conn.close()
        if row and row[0]:
            # Map stored regime to confidence: HIGH if recent (<2h), MEDIUM if stale
            regime = row[0]
            updated_at = row[1]
            if updated_at:
                now = datetime.now(timezone.utc)
                # Handle both naive (local) and aware (UTC) datetimes
                if updated_at.tzinfo is None:
                    from datetime import timezone as tz_local
                    now = datetime.now(tz_local)
                age_seconds = (now - updated_at).total_seconds()
                confidence = 75 if age_seconds < 7200 else 40
            else:
                confidence = 50
            return regime, confidence
    except Exception as e:
        log_error(f'get_regime DB: {e}')

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
        
        for coin in tokens:
            match = re.search(rf'{coin}USDT.*z=([-+]?\d+\.?\d*)', content)
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

def get_prediction(coin):
    """Get latest LLM candle prediction for token with per-token accuracy"""
    try:
        conn = sqlite3.connect('/root/.hermes/data/predictions.db')
        cur = conn.cursor()
        cur.execute("""
            SELECT direction, confidence, correct
            FROM predictions
            WHERE token =  ?
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
    """Update current_price for all open trades using Hyperliquid prices"""
    try:
        conn = psycopg2.connect(**BRAIN_DB_DICT)
        cur = conn.cursor()
        
        # Get all open trades
        cur.execute("SELECT id, token FROM trades WHERE status = 'open' AND server='Hermes'")
        open_trades = cur.fetchall()
        
        if not open_trades:
            cur.close()
            conn.close()
            return
        
        # BUG-10 fix: fetch prices from Hyperliquid via hype_cache instead of Gate.io
        try:
            mids = hc.get_allMids()
        except Exception:
            mids = {}
        
        updated = 0
        for trade_id, coin in open_trades:
            # Hyperliquid uses just the token symbol (e.g. "BTC", not "BTC_USDT")
            if coin in mids:
                current_price = float(mids[coin])
                cur.execute("UPDATE trades SET current_price = %s, last_updated = NOW() WHERE id = %s", 
                          (current_price, trade_id))
                updated += 1
        
        conn.commit()
        cur.close()
        conn.close()
        if updated > 0:
            print(f"✅ Updated {updated} trade prices from Hyperliquid")
    except Exception as e:
        print(f"⚠️ Price update error: {e}")

def get_macd(coin):
    """Compute MACD from price_history in signals_hermes.db (Python, no node needed).
    Returns dict with signal, histogram, trend, confidence.
    EMA periods: fast=12, slow=26, signal=9 (standard MACD).
    """
    import numpy as np
    if not coin or not coin.replace('_','').isalnum():
        return {}
    try:
        conn = sqlite3.connect('/root/.hermes/data/signals_hermes.db')
        df = pd.read_sql(
            "SELECT timestamp, price FROM price_history WHERE token=?? ORDER BY timestamp ASC",
            conn, params=(coin.upper(),))
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

def is_real_pump(coin, direction="long"):
    """Check if token is in a real pump.
    
    For SHORT signals: require volume > $5000 on Gate.io (confirm bearish move is real).
    For LONG signals: always allow — confluence LONGs are recovery/reversal plays,
                     they don't need a pump, they need oversold conditions.
    """
    # LONG signals: always allow (confluence LONGs are reversal plays, not pumps)
    if direction.lower() == "long":
        return True
    
    # SHORT signals: check volume on Gate.io
    try:
        r = requests.get(f"https://api.gateio.ws/api/v4/spot/tickers?currency_pair={coin}_USDT", timeout=5)
        if r.status_code == 200:
            data = r.json()
            if data:
                volume = float(data[0].get("quote_volume", 0))
                return volume > 5000
        return True  # Allow if Gate fails
    except Exception as e:
        log_error(f'is_real_pump: {e}')
        return True  # Allow if check fails

def ai_decide(coin, direction, entry, conf, prices, market_z, macd_data, pred_str="", z_score_tier=None, z_score=None):
    """Send prompt to AI to make actual decision"""
    
    current = prices.get(coin, entry)
    macd = macd_data.get("signal", "N/A")
    macd_conf = macd_data.get("confidence", "N/A")
    
    # Get regime data
    regime, regime_conf = get_regime(coin)
    
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

TOKEN: {coin}
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
        
                # HARD BLOCK: If market regime is against the trade direction, skip it entirely
                # Regime must align with direction (or be NEUTRAL) to proceed
                if decision != "wait" and regime != "NEUTRAL" and regime_conf > 50:
                    if (regime == "LONG_BIAS" and decision == "short") or \
                       (regime == "SHORT_BIAS" and decision == "long"):
                        # Fighting the regime — hard block
                        decision = "wait"
                        confidence = 0
                    elif (regime == "LONG_BIAS" and decision == "long") or \
                         (regime == "SHORT_BIAS" and decision == "short"):
                        # Aligned with regime — small boost
                        regime_bonus = min(10, (regime_conf - 50) // 5)
                        confidence = min(100, confidence + regime_bonus)
        
        return decision, confidence, result[:500]
    except Exception as e:
        print(f"AI decision failed: {e}")
        # Fallback to rule-based
        return direction, abs(conf) * 30, "Fallback to rules"

def execute_trade(coin, direction, entry, conf, atr, exchange='hyperliquid', learned=None):
    """
    DEPRECATED — all trade execution is handled exclusively by decider-run.py.
    This stub prevents import errors only.
    """
    return False

try:
    pending = get_pending_signals()
except:
    pending = []

# Load hot set rounds and apply flip detection BEFORE reviewing signals
_load_hot_rounds()

# ── DE-ESCALATION PROTOCOL (2026-04-02) ─────────────────────────────────────
# Hot set signals can get stuck in APPROVED but never executed (positions full,
# blacklisted, opposite position open). Without de-escalation they stay in the
# hot set forever, blocking new signals. This protocol forces them out.
#
# Rules:
# 1. DE-ESCALATE: hot set APPROVED signals not executed after 5 cycles → back to PENDING
# 2. COUNTER-SIGNAL: new PENDING signal opposite to open position → skip with reason
# 3. PURGE: any PENDING signal surviving 20+ compaction rounds → force-expire
#
# De-escalation counter is tracked in hot_cycle_count column (reset on any new signal).
conn_deesc = sqlite3.connect(SIGNALS_DB)
cur_deesc = conn_deesc.cursor()
now_str = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')

# RULE 1 — DE-ESCALATE stale hot-set APPROVED signals back to PENDING
# If a hot-set signal was approved but not executed after 5+ cycles, it gets
# de-escalated so new signals can enter the hot set pipeline for that token.
DEESCALATE_THRESHOLD = 5  # cycles without execution before de-escalation
cur_deesc.execute("""
    UPDATE signals
    SET decision = 'PENDING',
        executed = 0,
        deescalation_reason = 'deescalated-hot-set',
        hot_cycle_count = 0,
        updated_at = ?
    WHERE decision = 'APPROVED'
      AND executed = 0
      AND hot_cycle_count >= ?
      AND hot_cycle_count > 0
""", (now_str, DEESCALATE_THRESHOLD))
deesc_count = cur_deesc.rowcount
if deesc_count > 0:
    print(f"   🔻 DEESCALATED {deesc_count} stale hot-set APPROVED → PENDING (>{DEESCALATE_THRESHOLD} cycles)")

# RULE 2 — COUNTER-SIGNAL DETECTION
# For every PENDING signal, check if there's an open position in the OPPOSITE direction.
# This catches when the market is moving against an open trade and a counter-signal fires.
# Counter-signals are skipped, not acted on (position management handles exits).
# Build a set of open token+direction pairs from brain DB for fast lookup.
open_positions = {}  # token_upper -> direction_upper
try:
    import psycopg2
    conn_pg = psycopg2.connect(**BRAIN_DB_DICT)
    cur_pg = conn_pg.cursor()
    cur_pg.execute("SELECT token, direction FROM trades WHERE status = 'open'")
    for (tok, d) in cur_pg.fetchall():
        open_positions[tok.upper()] = d.upper()
    conn_pg.close()
except Exception as e:
    log_error(f"counter-signal DB fetch failed: {e}")

counter_killed = 0
for s in pending:
    tok = (s.get('coin') or '').upper()
    sig_dir = (s.get('direction') or '').upper()
    if tok in open_positions:
        open_dir = open_positions[tok]
        if sig_dir != open_dir and sig_dir in ('LONG', 'SHORT'):
            # Counter-signal: opposite direction to open position
            # Mark it so we can track it, then skip it
            cur_deesc.execute("""
                UPDATE signals
                SET decision = 'SKIPPED',
                    counter_detected = 1,
                    deescalation_reason = 'counter-signal-opposite-open',
                    updated_at = ?
                WHERE token=??
                  AND direction = ?
                  AND decision = 'PENDING'
            """, (now_str, tok, sig_dir))
            processed_this_run.add(f"{tok}:{sig_dir}")  # BUG-3 fix: dedup counter-killed signals
            counter_killed += 1
conn_deesc.commit()
if counter_killed > 0:
    print(f"   🚫 COUNTER-SIGNAL: {counter_killed} PENDING signals skipped (opposite open position)")

# RULE 3 — HOT SET ENTRY TRACKING: increment hot_cycle_count for all hot set APPROVED
# Track how many cycles each hot-set APPROVED signal has gone without executing.
# Reset counter when a new signal arrives for the same token (conditions changed).
cur_deesc.execute("""
    UPDATE signals
    SET hot_cycle_count = hot_cycle_count + 1,
        last_hot_at = ?
    WHERE decision = 'APPROVED'
      AND executed = 0
      AND hot_cycle_count >= 0
""", (now_str,))
conn_deesc.commit()
conn_deesc.close()

# HOT SET FLIP KILL (existing logic — keep it, runs after de-escalation above)
for s in pending:
    tok = (s.get('coin') or '').upper()
    sig_dir = (s.get('direction') or '').upper()
    if tok in _hot_rounds:
        hot_dir = _hot_rounds[tok]['direction'].upper()
        if sig_dir != hot_dir and sig_dir in ('LONG', 'SHORT'):
            killed = _kill_pending_opposite(tok, hot_dir)
            if killed:
                print(f"   🔥 FLIP KILL: {tok} {hot_dir} hot set kept — killed {sig_dir} PENDING")
            else:
                print(f"   🔥 HOT KEEP:  {tok} {hot_dir} hot set survived PENDING {sig_dir}")

print(f"=== AI Decider: {len(pending)} pending | Open: {get_open()}/{MAX_OPEN} | Hot: {len(_hot_rounds)} | Counter: {counter_killed} | Deesc: {deesc_count} ===")

# Get market context once
market_z = get_market_zscore()
prices = get_prices()
update_trade_prices()  # Update current_price for all open trades
print(f"Market: Z-Score={market_z}, BTC=${prices.get('BTC','N/A')}")

processed_this_run = set()  # token+direction already reviewed this run

# ── Confluence auto-approval: ≥90% confluence signals skip AI review ───────────
# FIX (2026-04-02): Raised from 75% to 90%. Previously too many single-source
# confluence signals were auto-approved at 75-85% confidence, bypassing the hot
# set entirely. The hot set exists to add +10% hot-bonus confidence to signals that
# survived review — we should let it do its job instead of auto-approving prematurely.
# Any token already in _hot_rounds is also skipped here — hot set handles those.
CONFLUENCE_THRESHOLD = 90
for s in pending:
    if s.get('signal_type') == 'confluence' and s.get('confidence', 0) >= CONFLUENCE_THRESHOLD:
        t = (s.get('coin') or '').upper()
        direction = (s.get('direction') or '').upper()
        key = f"{t}:{direction}"
        if key in processed_this_run:
            continue
        # Skip if token is in hot set — hot set has its own auto-approval logic
        # with confidence bonuses. Don't bypass it with a premature confluence approve.
        if t in _hot_rounds:
            print(f"   ⏸️ [CONF-AUTO] {t}: in hot set (r{_hot_rounds[t]['rounds']}) — letting hot set handle")
            continue
        if is_token_open(t):
            print(f"   ⏸️ [CONF-AUTO] {t}: already open")
            mark_signal_processed(t, 'SKIPPED', decision_reason='confluence-auto-position-open')
        else:
            ok = mark_signal_processed(t, 'APPROVED')
            if ok:
                print(f"   ✅ [CONF-AUTO] {t} {direction} conf={s.get('confidence'):.0f}% — auto-approved (confluence ≥90%)")
                log_signal(t, direction, s.get('entry', 0), s.get('confidence', 0), f"conf-auto-{s.get('source','')}")
            else:
                mark_signal_processed(t, 'FAILED', decision_reason='confluence-auto-approval-failed')
        processed_this_run.add(key)

for s in pending:
    t = s.get("token")
    direction = s.get("direction", "long")

    # Skip if already reviewed this run (signal still PENDING means ai_decider
    # marked it WAIT/SKIPPED — don't re-review, it'll stay PENDING forever)
    key = f"{t}:{direction}"
    if key in processed_this_run:
        continue
    processed_this_run.add(key)  # mark reviewed regardless of outcome

    entry = float(s.get("entry", 0))  # Ensure entry is float
    conf = s.get("confidence", 0)
    atr = s.get("atr", s.get("atrPercent", 2))
    
    # Get exchange from signal
    exchange = s.get("exchange")
    if exchange is None:
        print(f"❌ {t}: Cannot determine valid exchange - token not available on any supported exchange")
        mark_signal_processed(t, 'SKIPPED', decision_reason='exchange-unavailable')
        continue
    
    # SHORT_BLACKLIST and LONG_BLACKLIST are imported from hermes_constants at module level
    
    if direction.lower() == "short" and t.upper() in SHORT_BLACKLIST:
        print(f"   🚫 {t}: BLACKLISTED - skipping SHORT completely (0-20% WR historically)")
        log_signal(t, direction, entry, s.get('confidence', 0), f"SKIPPED-blacklist-{exchange}")
        mark_signal_processed(t, 'SKIPPED', decision_reason=f'blacklist-short-{exchange}')
        continue
    
    if direction.lower() == "long" and t.upper() in LONG_BLACKLIST:
        print(f"   🚫 {t}: BLACKLISTED - skipping LONG (poor performance)")
        log_signal(t, direction, entry, s.get("confidence", 0), f"SKIPPED-blacklist-{exchange}")
        mark_signal_processed(t, 'SKIPPED', decision_reason=f'blacklist-long')
        continue

    # FIX (2026-04-02): Block STABLE/STBL tokens. These are illiquid, error-prone
    # tokens that appear in HL data but frequently generate bad signals.
    # STABLE incident: confluence 99% signal, wrong direction, cascade massacre.
    if t.upper() in ('STABLE', 'STBL'):
        print(f"   🚫 {t}: BLOCKED — illiquid/non-standard token (2026-04-02 incident)")
        log_signal(t, direction, entry, s.get("confidence", 0), "SKIPPED-stable-block")
        mark_signal_processed(t, 'SKIPPED', decision_reason='blocked-illiquid-token')
        continue
    
    # Check open slots
    if get_open() >= MAX_OPEN:
        print(f"⏸️ {t}: max trades reached")
        log_signal(t, direction, entry, conf, f"SKIPPED-max-{exchange}")
        continue
    # ── Hot set: r1+ auto-approval ──────────────────────────────────────────
    hot = _hot_rounds.get(t.upper())
    if hot and hot['rounds'] >= 1:
        # Proven by AI across 1+ review round — skip AI review, auto-approve
        # FIX (2026-04-01): Lowered from r2+ to r1+ — signals were expiring before
        # reaching r2 due to 15-min TTL, and many legitimate signals stay WAIT
        # (AI needs more data) instead of going straight to EXEC.

        # Quality gate: require 1+ distinct signal types and avg_conf >= 40%
        # FIX (2026-04-02): Was < 2 types. Lowered to allow single-source hmacd signals
        # through. avg_conf >= 40% is the real quality filter — it measures conviction.
        num_types = hot.get('num_types', 0)
        avg_conf = hot.get('avg_conf', 0)
        if num_types < 1 or avg_conf < 40:
            avg_conf_str = f"{avg_conf:.0f}%" if avg_conf is not None else "N/A"
            print(f"   ⏸️ 🔥 r{hot['rounds']} {t} [{hot.get('source','?')}]: quality gate failed (types={num_types}, avg_conf={avg_conf_str})")
            log_signal(t, direction, entry, conf, f"hot-gate-fail-{exchange}")
            mark_signal_processed(t, 'SKIPPED', hot.get('signal_ids'), decision_reason='hot-set-quality-gate')
            processed_this_run.add(key)
            continue

        if is_token_open(t):
            print(f"   ⏸️ 🔥 HOT r{hot['rounds']} {t} [{hot.get('source','?')}]: already has open position")
            log_signal(t, direction, entry, conf, f"SKIPPED-open-{exchange}")
            mark_signal_processed(t, 'SKIPPED', hot.get('signal_ids'), decision_reason='hot-set-position-open')
            processed_this_run.add(key)
            continue

        # Blacklist double-check
        if direction.lower() == "short" and t.upper() in SHORT_BLACKLIST:
            print(f"   🚫 🔥 HOT r{hot['rounds']} {t}: BLACKLISTED — skipping SHORT")
            log_signal(t, direction, entry, conf, f"SKIPPED-blacklist-{exchange}")
            mark_signal_processed(t, 'SKIPPED', hot.get('signal_ids'), decision_reason='hot-set-blacklist')
            processed_this_run.add(key)
            continue

        # Targeted update: only specific signal IDs
        ok = mark_signal_processed(t, 'APPROVED', hot.get('signal_ids'))
        if ok:
            # Remove from hot_rounds so it won't be re-processed
            del _hot_rounds[t.upper()]
            # Quality-aware confidence boost
            diversity_bonus = min(20, num_types * 5)
            hot_bonus = min(20, hot['rounds'] * 5)
            final_conf = min(99, round(avg_conf + diversity_bonus + hot_bonus))
            print(f"   ✅🔥 AUTO-APPROVED r{hot['rounds']} {t} [{hot.get('source','?')}] {direction} "
                  f"conf={final_conf}% (+{hot_bonus}% hot +{diversity_bonus}% diversity, "
                  f"types={num_types}, avg={avg_conf:.0f}%)")
            log_signal(t, direction, entry, final_conf, f"hot-set-r{hot['rounds']}-{exchange}")
        else:
            print(f"   ❌🔥 HOT r{hot['rounds']} {t}: failed to record approval")
            log_signal(t, direction, entry, conf, f"FAILED-hot-{exchange}")
            mark_signal_processed(t, 'FAILED', hot.get('signal_ids'), decision_reason='hot-set-approval-failed')
        processed_this_run.add(key)
        continue

    # 2. Check if SOL token but signal says short (SOL tokens can only go long)
    if exchange == "raydium" and direction.lower() == "short":
        print(f"⏸️ {t}: SOL tokens can only go LONG on Raydium")
        log_signal(t, direction, entry, conf, "SKIPPED-sol-short")
        mark_signal_processed(t, 'SKIPPED', decision_reason='sol-short-unsupported')
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
    sl_mult = 1.0
    if learned:
        old_conf = ai_conf
        ai_conf = int(ai_conf + learned.get('confidence_boost', 0))
        sl_mult = learned.get('sl_multiplier', 1.0)
        print(f"   🧠 LEARNED: +{learned.get('confidence_boost', 0)}% conf, SL_mult={sl_mult:.2f} (patterns: {', '.join(learned.get('patterns', []))})")
    
    # Persist sl_multiplier on the signal row so decider-run can apply it
    try:
        from signal_schema import _get_conn, RUNTIME_DB
        conn_s = _get_conn(RUNTIME_DB)
        cur_s = conn_s.cursor()
        cur_s.execute('''
            UPDATE signals 
            SET learned_sl_multiplier = ?, updated_at = datetime('now')
            WHERE token=?? AND direction=? AND decision='APPROVED' AND executed=0
        ''', (sl_mult, t, direction))
        conn_s.commit()
        conn_s.close()
    except Exception as e:
        log_error(f'learned_sl_multiplier persist error: {e}')
    
    # Execute if AI says go (prompt enforces ≥50% confidence threshold)
    if decision != "wait" and ai_conf >= 50:
        # Only trade real pumps, not slow grind (LONG always allowed — reversal plays)
        if not is_real_pump(t, direction):
            print(f"   ⏸️ SKIPPED - No pump momentum (need >3% 24h + volume)")
            log_signal(t, direction, entry, conf, f"SKIPPED-{exchange}")
            mark_signal_processed(t, 'SKIPPED', decision_reason='no-pump-momentum')
        elif is_token_open(t):
            print(f"   ⏸️ SKIPPED - {t} already has open position")
            log_signal(t, direction, entry, conf, f"SKIPPED-open-{exchange}")
            mark_signal_processed(t, 'SKIPPED', decision_reason='position-already-open')
        else:
            # Record approval
            ok = mark_signal_processed(t, 'APPROVED')
            if ok:
                print(f"   ✅ APPROVED: {t} {decision.upper()} — decider-run will execute")
                log_signal(t, decision, entry, ai_conf, exchange)
            else:
                print(f"   ❌ Failed to record approval")
                log_signal(t, decision, entry, ai_conf, f"FAILED-{exchange}")
                mark_signal_processed(t, 'FAILED', decision_reason='approval-record-failed')
    else:
        print(f"   ⏸️ AI said WAIT")
        log_signal(t, direction, entry, ai_conf, f"WAIT-{exchange}")
        mark_signal_processed(t, 'WAIT', decision_reason=f'ai-wait-{decision}')


# ── Pipeline heartbeat ─────────────────────────────────────────────────────────
def _update_heartbeat_ai(stage: str):
    """Update pipeline heartbeat."""
    import json, time as _time, os as _os
    hb_file = '/var/www/hermes/data/pipeline_heartbeat.json'
    try:
        data = {}
        if _os.path.exists(hb_file):
            with open(hb_file) as f:
                data = json.load(f)
        data[stage] = {"timestamp": _time.strftime('%Y-%m-%dT%H:%M:%SZ', _time.gmtime()), "status": "ok"}
        with open(hb_file, 'w') as f:
            json.dump(data, f, indent=2)
    except Exception:
        pass  # never crash on heartbeat failures


# Don't write back to pending-signals.json - we read from signals.db now
print(f"\n=== Done: {len(pending)} signals processed ===")

# Pipeline heartbeat
_update_heartbeat_ai('ai_decider')

# Release lock
release_lock()
