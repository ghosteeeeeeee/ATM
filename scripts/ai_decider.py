#!/usr/bin/env python3
"""
AI Decider - Actually thinks and decides using all available info
"""
import subprocess, json, time, sys, requests, sqlite3, psycopg2, os, random, shlex, traceback, math
from datetime import datetime, timezone

# W&B decision audit logging — audit trail of every hot-set decision
try:
    import wandb
    _wandb_available = True
except ImportError:
    _wandb_available = False
    def _noop(*a, **k): pass
    wandb = type('obj', (), {'init': _noop, 'log': _noop, 'finish': _noop, 'config': type('obj', (), {'update': _noop})()})()
import pandas as pd
sys.path.insert(0, '/root/.hermes/scripts')
from _secrets import BRAIN_DB_DICT

# Speed feature: speed percentile boosts compaction survival
# Lazy-load to avoid 10s+ import penalty in decider-run.py (which only imports
# get_regime, not the pipeline functions). SpeedTracker.update() is called
# explicitly inside compact_signals() only when needed.
try:
    from speed_tracker import SpeedTracker
    _speed_tracker_ai = None
    def _get_speed_tracker():
        global _speed_tracker_ai
        if _speed_tracker_ai is None:
            _speed_tracker_ai = SpeedTracker()
        return _speed_tracker_ai
    speed_tracker_ai = _get_speed_tracker
except Exception as e:
    print(f"[ai-decider] SpeedTracker unavailable: {e}")
    speed_tracker_ai = lambda: None

# Token budget enforcement
_MAX_TOKENS_PER_RUN=10000    # hard cap per ai_decider invocation
_DAILY_TOKEN_BUDGET=1200000  # daily cap (1.2M — supports ai_decider + 2x compaction/day)
_DAILY_TOKENS_USED = 0
_DAILY_BUDGET_FILE = '/root/.hermes/data/ai_decider_daily_tokens.json'

# Event log integration
try:
    from event_log import log_event
except Exception:
    log_event = lambda *a, **k: None

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

def _check_token_budget(estimated_tokens: int) -> bool:
    """Check if estimated_tokens would exceed daily or per-run budget. Returns True to proceed, False to skip."""
    global _DAILY_TOKENS_USED
    today = datetime.now().strftime('%Y-%m-%d')
    try:
        if os.path.exists(_DAILY_BUDGET_FILE):
            with open(_DAILY_BUDGET_FILE, 'r') as f:
                data = json.load(f)
            if data.get('date') != today:
                # New day — reset counter
                _DAILY_TOKENS_USED = 0
                data = {'date': today, 'used': 0}
            else:
                _DAILY_TOKENS_USED = data.get('used', 0)
    except Exception:
        _DAILY_TOKENS_USED = 0

    # Per-run check
    if estimated_tokens > _MAX_TOKENS_PER_RUN:
        print(f"[BUDGET] Blocked call: {estimated_tokens} > {_MAX_TOKENS_PER_RUN} per-run limit")
        log_event('BUDGET_EXCEEDED', {'reason': 'per_run_limit', 'estimated': estimated_tokens, 'limit': _MAX_TOKENS_PER_RUN}, 'WARN')
        return False

    # Daily budget check
    if (_DAILY_TOKENS_USED + estimated_tokens) > _DAILY_TOKEN_BUDGET:
        print(f"[BUDGET] Blocked call: {_DAILY_TOKENS_USED} + {estimated_tokens} > {_DAILY_TOKEN_BUDGET} daily limit")
        log_event('BUDGET_EXCEEDED', {'reason': 'daily_limit', 'estimated': estimated_tokens, 'used': _DAILY_TOKENS_USED, 'limit': _DAILY_TOKEN_BUDGET}, 'WARN')
        return False

    return True

def _record_token_usage(tokens_used: int):
    """Record tokens used and persist to daily budget file."""
    global _DAILY_TOKENS_USED
    _DAILY_TOKENS_USED += tokens_used
    today = datetime.now().strftime('%Y-%m-%d')
    try:
        os.makedirs(os.path.dirname(_DAILY_BUDGET_FILE), exist_ok=True)
        with open(_DAILY_BUDGET_FILE, 'w') as f:
            json.dump({'date': today, 'used': _DAILY_TOKENS_USED}, f)
    except Exception as e:
        print(f"[BUDGET] Failed to write token usage: {e}")

AB_CONFIG_FILE = '/root/.hermes/data/ab-test-config.json'
sys.path.insert(0, '/root/.hermes/scripts')
from hermes_constants import SHORT_BLACKLIST, LONG_BLACKLIST
from tokens import is_solana_only
from hyperliquid_exchange import is_delisted

# ─── Source confidence weights ────────────────────────────────────────────────
# Single config for all signal source multipliers applied to raw confidence.
# > 1.0 = boost (trust more), < 1.0 = suppress (trust less).
# mtf_macd with hmacd- source = MACD crossovers = clearest trend signals = 1.0 (neutral).
# Dialed back from 1.2 — was dominating compaction and pushing other signal types out.
# Other hmacd-* sources = weaker/secondary = 0.6x (penalize, don't trust alone).
# All others = 1.0 (neutral).
SOURCE_WEIGHTS = {
    'hmacd-mtf_macd': 1.0,   # MACD crossovers — neutral weight (was 1.2)
    'hmacd-default': 0.6,   # Other hmacd-derived signals — penalize
}
# Master map: (signal_type, source_prefix) -> weight
# Checked in order; first match wins. None = neutral 1.0.
SOURCE_WEIGHT_OVERRIDES = [
    ('mtf_macd',  'hmacd-',  1.0),   # hmacd- + mtf_macd = MACD crossover (was 1.2)
    # hzscore signals get suppressed — noisy, often fires against trend
    ('mtf_zscore', 'hzscore', 0.5),
    # All other hmacd-* sources (pct-hermes, etc.) fall through to default 0.6
    # Pattern signals: 1.25× multiplier — independent primary signals, need to
    # bubble up so T can observe their performance vs mtf_macd in hot-set
    ('pattern_flag',   'pattern_scanner', 1.25),
    ('pattern_hns',   'pattern_scanner', 1.25),
    ('pattern_wyckoff','pattern_scanner', 1.25),
    ('pattern_elliot', 'pattern_scanner', 1.25),
    ('pattern_micro_flag', 'pattern_scanner', 1.0),   # micro flags get 1.0× — lower weight until proven
]
DEFAULT_SOURCE_WEIGHT = 1.0

# ── Performance Calibration (WR-Based Auto-Multiplier) ──────────────────────
# Applies to ALL signal types. After PERF_CAL_MIN_TRADES samples, WR drives weight.
# WR > 55% → multiplier 1.5×  |  WR 45-55% → keep 1.25×  |  WR 40-45% → 0.75×  |  WR < 40% → disable

PERF_CAL_MIN_TRADES = 15   # min closed trades before adjusting a signal type's weight
PERF_CAL_MAX_WEIGHT = 1.5  # cap on boost multiplier
PERF_CAL_MIN_WEIGHT = 0.0  # below this = exclude from hot-set entirely

# Map composite signal_type values (from signal_outcomes) to source categories
# so we can calibrate the same way across related signal types.
SIGNAL_TYPE_CATEGORY_MAP = {
    # Pattern scanner sources
    'pattern_flag':    'pattern_scanner',
    'pattern_hns':     'pattern_scanner',
    'pattern_wyckoff': 'pattern_scanner',
    'pattern_elliot':  'pattern_scanner',
    'pattern_micro_flag': 'pattern_scanner',  # micro flags tracked separately for now
    # Momentum / MTF sources
    'mtf_macd':  'mtf_macd',
    'hmacd-,hzscore':              'hmacd-momentum',
    'hmacd-,hzscore,pct-hermes':   'hmacd-momentum',
    'hmacd-,hzscore,pct-hermes,rsi-hermes': 'hmacd-momentum',
    'hmacd-,hzscore,pct-hermes,vel-hermes': 'hmacd-momentum',
    # Confluence sources
    'conf-1s':  'confluence',
    'conf-2s':  'confluence',
    'conf-3s':  'confluence',
    'conf-4s':  'confluence',
    'conf-5s':  'confluence',
    'conf-6s':  'confluence',
    'conf-7s':  'confluence',
    'conf-8s':  'confluence',
    'conf-9s':  'confluence',
    'conf-10s': 'confluence',
    # Decider / speed-review
    'decider':        'decider',
    'speed-review':   'speed-review',
    # Reconciliation
    'hl_reconcile':   'hl_reconcile',
}

# Category-level WR thresholds → multiplier
def _wr_to_multiplier(wr: float) -> float:
    if wr is None:
        return 1.0  # neutral when no data
    if wr >= 55.0:
        return 1.5
    elif wr >= 45.0:
        return 1.25
    elif wr >= 40.0:
        return 0.75
    else:
        return 0.0  # disable — losing signal type


def get_signal_type_stats(conn=None) -> dict:
    """
    Query signal_outcomes for per-signal-type win rate stats.
    Returns dict: {signal_type: {n, wins, wr, avg_pnl, category, multiplier}}
    """
    import sqlite3, os
    if conn is None:
        db = '/root/.hermes/data/signals_hermes_runtime.db'
        conn = sqlite3.connect(db, timeout=5)
    c = conn.cursor()
    c.execute("""
        SELECT signal_type, COUNT(*) as n,
               SUM(is_win) as wins,
               ROUND(100.0*SUM(is_win)/COUNT(*), 1) as wr,
               ROUND(AVG(pnl_pct), 3) as avg_pnl
        FROM signal_outcomes
        GROUP BY signal_type
        ORDER BY n DESC
    """)
    rows = c.fetchall()
    stats = {}
    for row in rows:
        sig_type, n, wins, wr, avg_pnl = row
        category = SIGNAL_TYPE_CATEGORY_MAP.get(sig_type, 'other')
        multiplier = _wr_to_multiplier(wr) if n >= PERF_CAL_MIN_TRADES else None
        stats[sig_type] = {
            'n': n, 'wins': wins, 'wr': wr, 'avg_pnl': avg_pnl,
            'category': category, 'multiplier': multiplier,
            'calibrated': n >= PERF_CAL_MIN_TRADES
        }
    conn.close()
    return stats


def get_calibration_summary() -> str:
    """Human-readable calibration report for all signal types with enough data."""
    stats = get_signal_type_stats()
    lines = ['=== Signal Type Calibration Report ===']
    lines.append(f'(min trades before calibration: {PERF_CAL_MIN_TRADES})')
    lines.append(f'{"signal_type":35s} {"n":4s} {"WR%":6s} {"mult":5s} {"calibrated":9s}  category')
    lines.append('-'*70)
    for sig_type, s in sorted(stats.items(), key=lambda x: -x[1]['n']):
        n = s['n']
        wr = f"{s['wr']:.1f}%" if s['wr'] else 'N/A'
        if s['calibrated']:
            mult = f"{s['multiplier']:.2f}×"
            cal = 'YES'
        else:
            mult = f"1.00×"  # neutral until enough data
            cal = f"NO({n}/{PERF_CAL_MIN_TRADES})"
        lines.append(f'{sig_type:35s} {n:4d} {wr:6s} {mult:5s} {cal:9s}  {s["category"]}')
    return '\n'.join(lines)


# Per-category aggregated stats (for SOURCE_WEIGHT_OVERRIDES auto-tuning)
def get_category_multipliers() -> dict:
    """
    Aggregate per-signal-type stats into category multipliers.
    Returns: {category: (multiplier, calibrated)}
    """
    stats = get_signal_type_stats()
    # Group by category
    cat_stats = {}
    for sig_type, s in stats.items():
        cat = s['category']
        if cat not in cat_stats:
            cat_stats[cat] = []
        if s['calibrated']:
            cat_stats[cat].append((s['wr'], s['n']))

    # Compute weighted average WR per category
    result = {}
    for cat, samples in cat_stats.items():
        total_n = sum(n for _, n in samples)
        weighted_wr = sum(wr * n for wr, n in samples) / total_n if total_n > 0 else None
        result[cat] = (_wr_to_multiplier(weighted_wr), True)

    # Add uncalibrated categories with neutral weight
    ALL_CATS = {'pattern_scanner', 'mtf_macd', 'hmacd-momentum', 'confluence', 'decider', 'speed-review', 'hl_reconcile', 'other'}
    for cat in ALL_CATS:
        if cat not in result:
            result[cat] = (1.0, False)

    return result


def _get_source_weight(stype, source):
    """
    Return confidence multiplier for (signal_type, source).

    Two-layer system:
    1. Explicit SOURCE_WEIGHT_OVERRIDES (hardcoded baselines, e.g. patterns start at 1.25)
    2. WR-based calibration from signal_outcomes — overrides baseline when enough data

    Calibration rules (applied to ALL signal types after PERF_CAL_MIN_TRADES samples):
      WR >= 55%  → 1.5×  (boost winning signals)
      WR 45-55%  → 1.25× (keep baseline)
      WR 40-45%  → 0.75× (suppress losing signals)
      WR < 40%   → 0.0×  (disable — exclude from hot-set)
    """
    if not source:
        return DEFAULT_SOURCE_WEIGHT

    # Layer 1: explicit overrides (pattern signals start at 1.25× baseline)
    for stype_pattern, source_prefix, weight in SOURCE_WEIGHT_OVERRIDES:
        if stype == stype_pattern and source.startswith(source_prefix):
            base_weight = weight
            break
    else:
        # hmacd-* but not mtf_macd → penalize baseline
        if source.startswith('hmacd-'):
            # Specific combo hmacd-,hzscore,pct-hermes is noisy — suppress hard
            if 'pct-hermes' in source and 'hzscore' in source:
                base_weight = 0.4   # combo with pct-hermes + hzscore = very noisy
            else:
                base_weight = SOURCE_WEIGHTS.get('hmacd-default', 0.6)
        else:
            base_weight = DEFAULT_SOURCE_WEIGHT

    # Layer 2: WR-based calibration — override baseline if enough data
    # Uses category-level calibration to smooth across related signal types
    category = None
    for sig_type, cat in SIGNAL_TYPE_CATEGORY_MAP.items():
        if sig_type == stype or (source.startswith('pattern_') and cat == 'pattern_scanner'):
            category = cat
            break
    if category is None:
        category = 'other'

    cat_mults = get_category_multipliers()
    if category in cat_mults:
        calibrated_mult, is_calibrated = cat_mults[category]
        if is_calibrated and calibrated_mult != 1.0:
            # Calibrated value overrides baseline
            return calibrated_mult

    return base_weight

SIGNALS_DB = '/root/.hermes/data/signals_hermes_runtime.db'
AB_RESULTS_FILE = '/root/.hermes/data/ab-test-results.json'
AB_CACHE_FILE = '/root/.hermes/data/ab-variant-cache.json'

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
              AND (token, direction) NOT IN (
                  SELECT token, direction FROM signals
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
                WHERE token=? AND direction=? AND decision IN ('PENDING','APPROVED','WAIT') AND executed=0
            """, (t, direction))
            sig_row = c.fetchone()
            sig_id = sig_row[0] if sig_row else None
            avg_conf = sig_row[1] if sig_row else 50.0
            num_types = sig_row[2] if sig_row else len(types_list)
            ids_list = [sig_id] if sig_id else []

            # Get all signal IDs for this token+direction (for mark_signal_processed)
            c.execute("""
                SELECT id FROM signals
                WHERE token=? AND direction=? AND decision IN ('PENDING','APPROVED','WAIT') AND executed=0
            """, (t, direction))
            ids_list = [r[0] for r in c.fetchall()]

            # ── HOT-SET SAFETY FILTERS ────────────────────────────────────────────────
            # CRITICAL (2026-04-04): Filter blacklisted tokens BEFORE adding to hotset.
            # These tokens have systematic losses and must NEVER be in the hotset.
            if direction.upper() == 'SHORT' and t in SHORT_BLACKLIST:
                print(f"   🚫 [HOTSET-FILTER] {t}: SHORT blocked — in SHORT_BLACKLIST")
                continue
            if direction.upper() == 'LONG' and t in LONG_BLACKLIST:
                print(f"   🚫 [HOTSET-FILTER] {t}: LONG blocked — in LONG_BLACKLIST")
                continue
            # CRITICAL (2026-04-04): Filter Solana-only tokens — not tradeable on Hyperliquid
            if is_solana_only(t):
                print(f"   🚫 [HOTSET-FILTER] {t}: blocked — Solana-only (not on Hyperliquid)")
                continue

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


def _kill_hot_signal(token):
    """Kill a hot set signal (mark COMPACTED so it's removed from hot set immediately."""
    try:
        conn = sqlite3.connect(SIGNALS_DB)
        c = conn.cursor()
        c.execute("""
            UPDATE signals
            SET decision = 'COMPACTED', executed = 1,
                updated_at = CURRENT_TIMESTAMP
            WHERE token=? AND decision IN ('PENDING','APPROVED') AND executed = 0
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
            WHERE token=? AND direction=? AND decision='PENDING' AND executed=0
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
        from hermes_ab_utils import get_ab_variant
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

                # ── Also write to ab-tests.jsonl for the dashboard ─────────────
                try:
                    from hermes_ab_utils import record_ab_outcome
                    record_ab_outcome(
                        test_name,
                        variant_id,
                        "win" if is_win else "loss",
                        metric_value=round(pnl_pct, 4)
                    )
                except Exception as ab_e:
                    log(f'record_ab_trade_closed ab_utils error: {ab_e}', 'WARN')

                break

        with open(AB_RESULTS_FILE, 'w') as f:
            json.dump(results[-1000:], f, indent=2)
    except Exception as e:
        log_error(f'record_ab_trade_closed: {e}')

PENDING = "/root/.hermes/data/pending-signals.json"
# ai_decider reads from signals_hermes_runtime.db (Hermes's DB)
# signal_gen writes to runtime DB
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
    """Count open PAPER trades only — live HL trades should not constrain paper trading."""
    try:
        conn = psycopg2.connect(BRAIN_DB)
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM trades WHERE status='open' AND server='Hermes' AND paper=true")
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

# ─────────────────────────────────────────────────────────────────────────────
# LLM-BASED HOT-SET COMPACTION (2026-04-08)
# Replaces Python scoring algorithm with MiniMax-M2 ranking
# ─────────────────────────────────────────────────────────────────────────────

def _do_compaction_llm():
    """
    Replace Python scoring with LLM-based ranking of top 20 signals.
    
    Every 10 mins:
      1. QUERY: All PENDING/APPROVED signals from last 10 mins (no rc filter)
      2. LLM RANK: Feed to MiniMax-M2 with max_tokens=4000
      3. PARSE: Strip thinking block, extract top 20 TOKEN DIR CONF REASON lines
      4. WRITE HOT-SET: hotset.json with survival_round (increment or 1)
      5. UPDATE DB: APPROVED for top 20, REJECTED for others
    """
    import re as _re
    
    conn = sqlite3.connect(SIGNALS_DB)
    c = conn.cursor()
    
    # STEP 1: Query signals from last 30 mins (wider window to catch signals
    # generated in the 10-min steps, since signal_gen only fires 2x/hour)
    # Include PENDING/APPROVED signals that haven't been executed yet.
    c.execute("""
        SELECT token, direction, signal_type, confidence, source, created_at,
               compact_rounds, survival_score, z_score_tier, z_score
        FROM signals
        WHERE decision IN ('PENDING', 'APPROVED')
          AND executed = 0
          AND created_at > datetime('now', '-30 minutes')
          AND token NOT LIKE '@%'
        ORDER BY confidence DESC
        LIMIT 100
    """)
    signals = c.fetchall()
    
    if not signals:
        conn.close()
        print("  [LLM-compaction] No signals in last 30 mins — skipping")
        return
    
    print(f"  [LLM-compaction] Ranking {len(signals)} signals with MiniMax-M2...")
    
    # Load current hot-set for HOT SURVIVORS context
    prev_hotset = {}
    try:
        with open('/var/www/hermes/data/hotset.json') as _hf:
            _hdata = json.load(_hf)
            for s in _hdata.get('hotset', []):
                prev_hotset[f"{s['token']}:{s['direction']}"] = s
    except Exception:
        pass
    
    # Build HOT SURVIVORS context — include staleness info so LLM can penalize old entries
    # Format: TOKEN(D/S,CONF%,AGE_h) where AGE_h is hours since last signal
    if prev_hotset:
        survivor_parts = []
        for key, s in prev_hotset.items():
            conf = s.get('confidence', 0)
            age_h = (time.time() - s.get('timestamp', 0)) / 3600
            survivor_parts.append(f"{s['token']}({s['direction'][0]},{conf:.0f}%,{age_h:.1f}h)")
        hot_survivors_str = "HOT SURVIVORS (with age): " + " ".join(survivor_parts[:20])
    else:
        hot_survivors_str = "HOT SURVIVORS: (none — first run)"
    
    # Build SIGNALS list for prompt — include ALL signals (fresh + stale from prev hotset)
    # The LLM will decide which survive based on fresh conviction + staleness penalty
    signal_lines = []
    for idx, row in enumerate(signals):
        token, direction, stype, conf, source, created = row[0], row[1], row[2], row[3], row[4], row[5]
        # Format created time as HH:MM:SS and compute age in hours
        try:
            created_t = datetime.strptime(created, '%Y-%m-%d %H:%M:%S')
            time_str = created_t.strftime('%H:%M:%S')
            age_h = (datetime.now() - created_t).total_seconds() / 3600
        except Exception:
            time_str = created[-8:] if len(created) >= 8 else created
            age_h = 0
        signal_lines.append(f"[{idx}] {token} | {direction} | conf={conf:.0f}% | age={age_h:.1f}h | src={source}")
    
    # BLACKLIST string
    BLACKLIST_STR = "SUI FET SPX ARK TON ONDO CRV RUNE AR NXPC DASH ARB TRUMP LDO NEAR APT CELO SEI ACE"
    
    # Dynamically read market regime to build adaptive RULES
    _market_regime = "NEUTRAL"
    try:
        import os
        _regime_path = '/var/www/html/regime_4h.json'
        if os.path.exists(_regime_path):
            with open(_regime_path) as _rf:
                _rd = json.load(_rf)
            _market_regime = _rd.get('aggregate', {}).get('overall', 'NEUTRAL')
    except Exception:
        pass
    
    if _market_regime == 'LONG_BIAS':
        _bias_rules = "prefer LONG when close, penalize SHORT vs hot LONG -15%, no SHORT on"
        _bias_note = "LONG_BIAS market"
    elif _market_regime == 'SHORT_BIAS':
        _bias_rules = "prefer SHORT when close, penalize LONG vs hot SHORT -15%, no LONG on"
        _bias_note = "SHORT_BIAS market"
    else:
        _bias_rules = "prefer higher-confidence signal when close, no directional bias"
        _bias_note = "NEUTRAL market"
    
    # Build prompt — WINNING STRUCTURE: blank lines + QA framing + OUT: on its own line
    # Testing proved: MiniMax needs explicit "Question:/Answer:" framing + blank lines to output structured data
    prompt = f"""\
{hot_survivors_str}
SIGNALS: {' '.join(signal_lines)}
RULES: reject conf<70, penalize stale signals (>0.5h old) by -20% confidence, penalize tokens with no fresh signal in >1h, no SHORT on blacklist: {BLACKLIST_STR}, dedupe

Question: which tokens pass all filters?

Answer (TOKEN DIR CONF, one per line):
OUT:
"""
    
    # STEP 2: Call MiniMax-M2 with max_tokens=4000 (CRITICAL: 4000 not 3000)
    # MiniMax-M2 uses full max_tokens for BOTH reasoning + output.
    # With max_tokens=3000, reasoning uses 2999 leaving 1 output token.
    try:
        _auth_path = '/root/.hermes/auth.json'
        with open(_auth_path) as _f:
            _auth = json.load(_f)
        _creds = (_auth.get('credential_pool', {}) or {}).get('minimax', [])
        if not _creds:
            raise RuntimeError("no minimax credentials")
        _minimax_token = _creds[0].get('access_token', '')
        
        if not _check_token_budget(4000):
            print("[LLM-compaction] Token budget exceeded — skipping")
            conn.close()
            return
        
        from openai import OpenAI
        _client = OpenAI(api_key=_minimax_token, base_url='https://api.minimax.io/v1')
        _resp = _client.chat.completions.create(
            model="MiniMax-M2",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=4000
        )
        raw = _resp.choices[0].message.content
        
        # Record token usage
        try:
            _usage = _resp.usage
            _output_tokens = getattr(_usage, 'completion_tokens', 0) or len(raw.split()) * 1.3
            _record_token_usage(int(2000 + _output_tokens))
        except Exception:
            _record_token_usage(4000)
        
        print(f"  [LLM-compaction] LLM response received ({len(raw)} chars)")
        
    except Exception as _e:
        print(f"  [LLM-compaction] FAILED: {_e}")
        conn.close()
        return
    
    # STEP 3: Extract content from after the think block
    # MiniMax-M2 output format: <think> [reasoning]  [actual output] 
    # The <think> block ends with </think>. The actual output (if any) comes AFTER </think>.
    # Use </think> as the delimiter — it reliably marks the end of the thinking block.
    content = raw.strip() if raw else ""
    marker = '</think>'
    idx = content.rfind(marker)
    if idx >= 0:
        # Take content AFTER the  marker (the actual trading output)
        content = content[idx + len(marker):].strip()
    
    # FALLBACK: if content is empty but raw contains OUT: lines,
    # extract directly from raw (MiniMax sometimes puts OUT: inside think block)
    if not content or 'OUT:' not in content:
        _raw_upper = raw.upper()
        _out_marker_pos = _raw_upper.rfind('OUT:')
        if _out_marker_pos >= 0:
            # Take everything from OUT: to end of raw
            content = raw[_out_marker_pos:].strip()
            print(f"  [LLM-compaction] OUT: found inside think block — using raw fallback ({len(content)} chars)")
    
    # Debug: print first 500 chars of content
    print(f"  [LLM-compaction] Content preview: {content[:500]}")
    # DEBUG: write full content to temp file for inspection
    with open('/tmp/llm_compaction_content.txt', 'w') as _dbg:
        _dbg.write(f"RAW ({len(raw)} chars):\n{raw}\n\n---EXTRACTED ({len(content)} chars):\n{content}\n")
    
    if not content:
        print(f"  [LLM-compaction] Empty LLM output — using fallback scorer")
        parsed = []  # Will trigger the FALLBACK at "if not parsed:"
    
    # Build a set of valid tokens from our signals for strict parsing
    valid_tokens = {row[0].upper() for row in signals}  # token column from signals
    valid_confs = {row[3]: row[0].upper() for row in signals}  # conf -> token mapping
    
    # STEP 4: Parse OUT lines — format: TOKEN DIR CONF REASON
    # Each line: "LAYER LONG 91 strong momentum alignment"
    parsed = []
    for line in content.split('\n'):
        line = line.strip()
        if not line:
            continue
        # Skip header/rule lines and think markers
        if line.startswith(('HOT ', 'SIGNALS', 'RULES:', 'OUT:', '---', '<think>')):
            continue
        # Skip lines that are clearly not output lines (don't contain any LONG/SHORT)
        if 'LONG' not in line and 'SHORT' not in line:
            continue
        
        # Parse: TOKEN DIR CONF REASON
        # Token can be alphanumeric, dir is LONG/SHORT, conf is number, rest is reason
        parts = line.split()
        if len(parts) < 3:
            continue
        
        # First part = token (uppercase alphanumeric)
        token = parts[0].upper()
        
        # Second part = direction
        direction = parts[1].upper()
        if direction not in ('LONG', 'SHORT'):
            # Try to find LONG/SHORT in parts
            for d in ('LONG', 'SHORT'):
                if d in parts:
                    direction = d
                    break
            else:
                continue
        
        # Find confidence: first numeric in parts after direction (strip % suffix)
        conf = None
        reason_parts = []
        for i, p in enumerate(parts[2:], start=2):
            # Strip trailing % if present
            p_clean = p.rstrip('%')
            try:
                conf = float(p_clean)
                reason_parts = parts[i+1:]
                break
            except ValueError:
                reason_parts.append(p)
        
        if conf is None:
            continue
        
        reason = ' '.join(reason_parts) if reason_parts else 'no reason'
        
        # Only include tokens that are in our actual signal list (not hallucinated)
        # RECOVERY: If token is *** or not valid, try to recover by matching direction+confidence
        if token == '***' or token not in valid_tokens:
            recovered_token = None
            for row in signals:
                sig_token, sig_dir, _, sig_conf = row[0], row[1], row[2], row[3]
                if sig_dir.upper() == direction.upper() and abs(sig_conf - conf) < 5:
                    recovered_token = sig_token
                    break
            if recovered_token:
                token = recovered_token
                print(f"  [LLM-compaction] Recovered token *** -> {token} via direction+confidence match")
            else:
                # Couldn't recover - skip this line
                continue
        
        parsed.append({
            'token': token,
            'direction': direction,
            'confidence': conf,
            'reason': reason,
        })
    
    print(f"  [LLM-compaction] Parsed {len(parsed)} ranked signals")

    if not parsed:
        # FALLBACK: Use algorithm scoring when LLM produces no valid tokens
        # REQUIREMENT: tokens must have real confidence >65% to survive without hot survivor boost
        print(f"  [LLM-compaction] FALLBACK: Using algorithm scoring")
        scored = []
        for row in signals:
            token, direction, stype, conf, source, created = row[0], row[1], row[2], row[3], row[4], row[5]
            cr = row[6]  # compact_rounds
            if direction.upper() == 'SHORT' and token in SHORT_BLACKLIST:
                continue
            if direction.upper() == 'LONG' and token in LONG_BLACKLIST:
                continue
            if is_solana_only(token):
                continue
            if is_delisted(token):
                continue
            # Compute age of signal
            try:
                created_t = datetime.strptime(created, '%Y-%m-%d %H:%M:%S')
                age_h = (datetime.now() - created_t).total_seconds() / 3600
            except Exception:
                age_h = 999
            # Staleness penalty: -20% per hour of age (max -40%)
            staleness_penalty = max(0, 1.0 - (age_h * 0.2))
            # Hot survivor boost: only if compact_rounds > 0 AND age < 1h
            if cr > 0 and age_h < 1.0:
                survival_bonus = 1.0 + (cr * 0.15)
            else:
                survival_bonus = 1.0
            # Regime bias (SHORT_BIAS): SHORT gets +15%, LONG gets -15%
            regime_bonus = 1.15 if direction.upper() == 'SHORT' and _market_regime == 'SHORT_BIAS' else (
                           0.85 if direction.upper() == 'LONG' and _market_regime == 'SHORT_BIAS' else 1.0)
            score = conf * survival_bonus * staleness_penalty * regime_bonus
            scored.append((token, direction, conf, score, age_h))
        scored.sort(key=lambda x: x[3], reverse=True)
        # Only keep tokens with score >= 65 (real conviction required)
        top20_scored = [(s[0], s[1], s[2], s[3]) for s in scored if s[3] >= 65][:20]
        parsed = [
            {'token': s[0], 'direction': s[1], 'confidence': s[2], 'reason': f'fallback score={s[3]:.0f}'}
            for s in top20_scored
        ] if top20_scored else []
        print(f"  [LLM-compaction] Fallback: {len(parsed)} signals above 65% threshold")
    else:
        print(f"  [LLM-compaction] Top parsed: {parsed[:5]}")
    
    # Deduplicate LLM output by token+direction before building top20
    _seen_keys = set()
    _parsed_deduped = []
    for s in parsed:
        key = f"{s['token']}:{s['direction']}"
        if key not in _seen_keys:
            _seen_keys.add(key)
            _parsed_deduped.append(s)
    parsed = _parsed_deduped
    
    # STEP 5: Get previous hot-set for survival_round tracking
    prev_hotset = {}
    try:
        with open('/var/www/hermes/data/hotset.json') as _hf:
            _hdata = json.load(_hf)
            for s in _hdata.get('hotset', []):
                prev_hotset[f"{s['token']}:{s['direction']}"] = s
    except Exception:
        pass
    
    # Build top-20 set and track survival_rounds
    top20 = parsed[:20]
    top20_keys = {f"{s['token']}:{s['direction']}" for s in top20}
    
    # Determine survival_round for each token
    # For tokens that were in previous hotset: survival_round + 1
    # For new tokens: survival_round = 1
    hotset_entries = []
    for s in top20:
        key = f"{s['token']}:{s['direction']}"
        prev = prev_hotset.get(key, {})
        if prev:
            new_sr = (prev.get('survival_round', 0)) + 1
        else:
            new_sr = 1
        hotset_entries.append({
            'token': s['token'],
            'direction': s['direction'],
            'confidence': s['confidence'],
            'reason': s['reason'],
            'survival_round': new_sr,
        })
    
    # STEP 6: Update signal decisions in DB
    # Top 20 → APPROVED, increment compact_rounds
    # Others → REJECTED + rejected_at
    
    # Get all candidate signal IDs grouped by token+direction
    c.execute("""
        SELECT id, token, direction FROM signals
        WHERE decision IN ('PENDING', 'APPROVED')
          AND executed = 0
          AND created_at > datetime('now', '-10 minutes')
          AND token NOT LIKE '@%'
    """)
    all_sig_ids = c.fetchall()
    
    approved_ids = []
    rejected_ids = []
    
    for sid, tok, d in all_sig_ids:
        key = f"{tok.upper()}:{d.upper()}"
        if key in top20_keys:
            approved_ids.append(sid)
        else:
            rejected_ids.append(sid)
    
    # Update APPROVED
    if approved_ids:
        placeholders = ','.join(['?' for _ in approved_ids])
        c.execute(f"""
            UPDATE signals
            SET decision = 'APPROVED',
                compact_rounds = COALESCE(compact_rounds, 0) + 1,
                updated_at = CURRENT_TIMESTAMP
            WHERE id IN ({placeholders})
        """, approved_ids)
        print(f"  [LLM-compaction] APPROVED {len(approved_ids)} signals")
    
    # Update REJECTED
    if rejected_ids:
        placeholders = ','.join(['?' for _ in rejected_ids])
        c.execute(f"""
            UPDATE signals
            SET decision = 'REJECTED',
                rejected_at = CURRENT_TIMESTAMP,
                rejection_reason = 'llm_compaction_not_in_top20',
                updated_at = CURRENT_TIMESTAMP
            WHERE id IN ({placeholders})
        """, rejected_ids)
        print(f"  [LLM-compaction] REJECTED {len(rejected_ids)} signals")
    
    conn.commit()
    conn.close()
    
    # STEP 7: Write hotset.json with survival_round
    # Track compaction_cycle
    _prev_cycle = 0
    try:
        if os.path.exists('/var/www/hermes/data/hotset.json'):
            with open('/var/www/hermes/data/hotset.json') as _pf:
                _prev_data = json.load(_pf)
                _prev_cycle = _prev_data.get('compaction_cycle', 0)
    except Exception:
        pass
    _compaction_cycle = _prev_cycle + 1
    
    # Enrich with speed data if available
    _speed_cache = {}
    try:
        if speed_tracker_ai is not None:
            _speed_cache = speed_tracker_ai().get_all_speeds()
    except Exception:
        pass
    
    # Deduplicate by token+direction before safety filters
    _seen_keys = set()
    _hotset_deduped = []
    for entry in hotset_entries:
        key = f"{entry['token']}:{entry['direction']}"
        if key not in _seen_keys:
            _seen_keys.add(key)
            _hotset_deduped.append(entry)
    hotset_entries = _hotset_deduped
    
    # Apply safety filters and write final hot-set
    hotset_final = []
    
    for entry in hotset_entries:
        tkn = entry['token']
        direction = entry['direction']
        
        # Safety: blacklist filter
        if direction.upper() == 'SHORT' and tkn in SHORT_BLACKLIST:
            print(f"  🚫 [HOTSET-FILTER] {tkn}: SHORT blocked — SHORT_BLACKLIST")
            continue
        if direction.upper() == 'LONG' and tkn in LONG_BLACKLIST:
            print(f"  🚫 [HOTSET-FILTER] {tkn}: LONG blocked — LONG_BLACKLIST")
            continue
        # Solana-only filter
        if is_solana_only(tkn):
            print(f"  🚫 [HOTSET-FILTER] {tkn}: blocked — Solana-only")
            continue
        # Delisted filter
        if is_delisted(tkn):
            print(f"  🚫 [HOTSET-FILTER] {tkn}: blocked — delisted")
            continue
        
        spd = _speed_cache.get(tkn, {})
        # Get z_score and signal source from the original signal entry
        sig_entry = next((s for s in signals if s[0] == tkn and s[1].upper() == direction.upper()), None)
        z_val = sig_entry[9] if sig_entry else 0  # z_score column (index 9)
        src_val = sig_entry[4] if sig_entry else ''  # source column (index 4)
        hotset_final.append({
            'token': tkn,
            'direction': direction,
            'confidence': entry['confidence'],
            'reason': entry['reason'],
            'source': src_val,
            'z_score': z_val,
            'compact_rounds': entry.get('compact_rounds', 1),
            'survival_score': entry.get('survival_score', 0.0),
            'survival_round': entry['survival_round'],
            'wave_phase': spd.get('wave_phase', 'neutral'),
            'is_overextended': spd.get('is_overextended', False),
            'price_acceleration': spd.get('price_acceleration', 0.0),
            'momentum_score': spd.get('momentum_score', 50.0),
            'speed_percentile': spd.get('speed_percentile', 50.0),
        })
    
    # Cap at 20
    if len(hotset_final) > 20:
        hotset_final = hotset_final[:20]
    
    with open('/var/www/hermes/data/hotset.json', 'w') as _f:
        json.dump({
            'hotset': hotset_final,
            'compaction_cycle': _compaction_cycle,
            'timestamp': time.time()
        }, _f, indent=2)
    
    print(f"  [LLM-compaction] Wrote hotset.json with {len(hotset_final)} tokens (cycle={_compaction_cycle})")
    
    # Update pipeline heartbeat
    try:
        _hotset_ts_file = '/var/www/hermes/data/hotset_last_updated.json'
        with open(_hotset_ts_file, 'w') as _f:
            json.dump({'last_compaction_ts': time.time()}, _f)
    except Exception:
        pass


# ── END LLM COMPACTION ─────────────────────────────────────────────────────────


def get_pending_signals():
    """
    Get PENDING signals from signals_hermes_runtime.db.

    FIX (2026-04-08): Uses LLM-based compaction instead of Python scoring.
    Every 10 mins the LLM ranks signals and top 20 survive.
    """
    try:
        conn = sqlite3.connect(SIGNALS_DB)
        c = conn.cursor()

        # Run LLM-based compaction (replaces Python scoring)
        _do_compaction_llm()

        # After compaction, fetch signals for the main loop
        # (The LLM already updated decisions to APPROVED/REJECTED)
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
                "source": safe_source,
            }
            if coin.upper() in hot_tokens:
                hot_signals.append(sig)
            else:
                non_hot_signals.append(sig)

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
        with open('/root/.hermes/data/zscore_exports/latest_signals.txt', 'r') as f:
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

def get_prediction(token):
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


def get_open_trade_details():
    """Fetch open trades with entry price, direction, and SL info for batch review."""
    try:
        conn = psycopg2.connect(**BRAIN_DB_DICT)
        cur = conn.cursor()
        # Get trade details including entry_price and SL if stored
        cur.execute("""
            SELECT token, direction, entry_price,
                   COALESCE(stop_loss, 0) as stop_loss,
                   COALESCE(current_price, entry_price) as current_price,
                   status, pnl_pct, updated_at
            FROM trades
            WHERE status = 'open' AND server='Hermes'
            ORDER BY open_time DESC
        """)
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return [
            {
                'token': r[0],
                'direction': r[1],
                'entry': float(r[2]) if r[2] else 0,
                'sl': float(r[3]) if r[3] else 0,
                'current': float(r[4]) if r[4] else 0,
                'pnl_pct': float(r[6]) if r[6] else 0,
                'updated_at': r[7],
            }
            for r in rows
        ]
    except Exception as e:
        log_error(f'get_open_trade_details: {e}')
        return []


def ai_decide_batch(signals, market_z, prices):
    """Batch decision-maker: one Minimax call for ALL pending signals + open trade monitoring.

    Args:
        signals: list of pending signal dicts from get_pending_signals()
        market_z: market z-score string
        prices: dict of token -> current price

    Returns:
        dict: {f"{token}:{direction}": {'decision': 'long'/'short'/'wait', 'confidence': int, 'reason': str},
               '_open_trades': [{'token': x, 'alert': 'SL_VIOLATION'/'HARD_SL'/'CLOSE', 'reason': str}, ...]}
    """
    import re as _re

    open_trades = get_open_trade_details()
    regime_cache = {s['token'].upper(): get_regime(s['token']) for s in signals}
    fear_greed = get_fear()

    # ── Build open trades section ────────────────────────────────────────────
    open_trades_section = ""
    if open_trades:
        open_lines = ["=== OPEN TRADES (Monitor for SL violations) ==="]
        for t in open_trades:
            entry = t['entry']
            current = t['current']
            sl = t['sl']
            direction = t['direction'].upper()
            pnl = t['pnl_pct']

            # Compute distance to SL
            if entry > 0 and sl > 0:
                if direction == 'LONG':
                    dist_to_sl = (entry - sl) / entry * 100
                    dist_pnl = (current - entry) / entry * 100
                else:
                    dist_to_sl = (sl - entry) / entry * 100
                    dist_pnl = (entry - current) / entry * 100
            else:
                dist_to_sl = 0
                dist_pnl = 0

            open_lines.append(
                f"- {t['token']} {direction}: entry=${entry:.4f}, current=${current:.4f}, "
                f"SL=${sl:.4f} ({dist_to_sl:.1f}% away), PnL={pnl:+.2f}%"
            )
        open_trades_section = "\n".join(open_lines)
    else:
        open_trades_section = "=== OPEN TRADES: None ==="

    # ── Build signals section ───────────────────────────────────────────────
    if not signals:
        signals_section = "=== PENDING SIGNALS: None ==="
    else:
        sig_lines = ["=== PENDING SIGNALS (approve/reject/close) ==="]
        for i, s in enumerate(signals, 1):
            token = s.get('token', '?')
            direction = s.get('direction', 'long').upper()
            conf = s.get('confidence', 0)
            entry = s.get('entry', prices.get(token, 0)) or prices.get(token, 0)
            regime_val, regime_conf = regime_cache.get(token.upper(), ('NEUTRAL', 0))
            z_tier = s.get('z_score_tier', 'N/A')
            z_val = s.get('z_score', 0)
            source = s.get('source', 'unknown')
            exchange = s.get('exchange', 'hyperliquid')

            sig_lines.append(
                f"[{i}] {token} | {direction} | conf={conf:.0f}% | entry=${entry:.4f} | "
                f"regime={regime_val}({(regime_conf or 0):.0f}%) | z={z_tier}({(z_val or 0):+.2f}) | src={source}"
            )
        signals_section = "\n".join(sig_lines)

    # ── Assemble batch prompt ─────────────────────────────────────────────────
    prompt = f"""You are a crypto trading command center. Review ALL pending signals AND open trades in ONE pass.

{open_trades_section}

{signals_section}

=== GLOBAL CONTEXT ===
Market Z-Score: {market_z}
Fear & Greed: {fear_greed}

=== YOUR TASKS ===

1. OPEN TRADES — Check each for:
   - SL_VIOLATION: price has moved >80% of distance to SL (high risk)
   - HARD_SL: price at or beyond SL level (CLOSE THE TRADE)
   - REGIME_BREAK: market regime shifted against the trade direction
   - HOLD: trade is fine

2. PENDING SIGNALS — For each, decide:
   - DECIDE: [TOKEN] [DIRECTION] [CONF] [REASON]
   Example: DECIDE: BTC LONG 75 The momentum is bullish and aligned with regime
   If you want to REJECT: DECIDE: BTC LONG 0 Low confidence and counter-regime

=== HARD RULES ===
- BLACKLISTED TOKENS for SHORT: SUI FET SPX ARK TON ONDO CRV RUNE AR NXPC DASH ARB TRUMP LDO NEAR APT CELO SEI ACE
- DIRECTION BIAS: LONGS outperform SHORTS historically. When uncertain, favor LONG.
- CONFIDENCE THRESHOLD: reject signals with raw confidence < 50% (always WAIT on low confidence)
- EXECUTE thresholds: AI confidence ≥ 50% AND aligned with momentum → EXECUTE
- Regime contradiction: if regime strongly opposes direction (conf>55%) → WAIT
- HARD SL rule: NEVER let a losing trade run. If current price has crossed SL → CLOSE immediately

=== OUTPUT FORMAT ===
First, list each open trade action on its own line:
  ACTION: [TOKEN] [CLOSE/SL_VIOLATION/HOLD] [REASON]

Then list each signal decision:
  DECIDE: [TOKEN] [LONG/SHORT/WAIT] [CONFIDENCE] [REASON]

End with:
  SUMMARY: [N] trades to close, [N] signals approved, [N] signals rejected
"""

    # ── Fire ONE Minimax call ─────────────────────────────────────────────────
    try:
        import os, json as _json
        from openai import OpenAI as _OpenAI

        _auth_path = '/root/.hermes/auth.json'
        with open(_auth_path) as _f:
            _auth = _json.load(_f)
        _creds = (_auth.get('credential_pool', {}) or {}).get('minimax', [])
        _token = _creds[0].get('access_token', '') if _creds else ''
        if not _token:
            raise RuntimeError("no minimax token")

        if not _check_token_budget(6000):
            print("[ai_decider-batch] Token budget exceeded, returning all WAIT")
            _record_token_usage(0)  # record the call even though we skipped
            log_event('BATCH_BUDGET_EXCEEDED', {'n_signals': len(signals)})
            _result = {f"{s['token']}:{s['direction']}": {'decision': 'wait', 'confidence': 0, 'reason': 'budget_exceeded'}
                       for s in signals}
            _result['_open_trades'] = []
            return _result

        _client = _OpenAI(api_key=_token, base_url='https://api.minimax.io/v1')
        _resp = _client.chat.completions.create(
            model="MiniMax-M2",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=4000
        )
        result = _resp.choices[0].message.content
        # Record token usage
        try:
            _usage = _resp.usage
            _out = getattr(_usage, 'completion_tokens', 0) or len(result.split()) * 1.3
            _record_token_usage(int(3000 + _out))
            log_event('API_CALL', {'tokens_used': int(3000 + _out), 'model': 'MiniMax-M2-batch'})
        except Exception:
            _record_token_usage(6000)
            log_event('API_CALL', {'tokens_used': 6000, 'model': 'MiniMax-M2-batch'})

    except Exception as _mm_err:
        # QWEN IS OUT — no unsupervised decisions. Return all WAIT.
        print(f"[ai_decider-batch] ⚠️ MINIMAX FAILED ({_mm_err}) — qwen fallback BLOCKED. All WAIT.")
        _record_token_usage(0)  # record the failed API call attempt
        log_event('MINIMAX_FAILED_BATCH', {
            'error': str(_mm_err),
            'n_signals': len(signals),
            'n_open_trades': len(open_trades),
            'action': 'BLOCKED_qwen-WAIT_all'
        }, level='WARN')
        # Telegram alert
        try:
            with open('/root/.hermes/auth.json') as _f:
                _auth = _json.load(_f)
            _telegram = (_auth.get('notifications', {}) or {}).get('telegram', {})
            _tele_token = _telegram.get('bot_token', '')
            _tele_chat = _telegram.get('chat_id', '')
            if _tele_token and _tele_chat:
                import urllib.request
                _msg = urllib.parse.quote(
                    f"⚠️ ai_decider BATCH MODE — MINIMAX DOWN\n"
                    f"qwen blocked. {len(signals)} signals=WAIT, {len(open_trades)} open trades unmonitored.\n"
                    f"Check Minimax API ASAP."
                )
                urllib.request.urlopen(
                    f"https://api.telegram.org/bot{_tele_token}/sendMessage?chat_id={_tele_chat}&text={_msg}",
                    timeout=5
                )
        except Exception:
            pass
        _result = {f"{s['token']}:{s['direction']}": {'decision': 'wait', 'confidence': 0, 'reason': 'minimax_failed'}
                   for s in signals}
        _result['_open_trades'] = []
        return _result

    # ── Parse batch response ─────────────────────────────────────────────────
    decisions = {}
    open_trade_alerts = []

    lines = result.split('\n')
    for line in lines:
        line = line.strip()
        # Open trade actions
        if line.startswith('ACTION:'):
            parts = line.split(None, 3)
            if len(parts) >= 3:
                token = parts[1]
                action = parts[2].upper()
                reason = parts[3] if len(parts) > 3 else ''
                if action in ('CLOSE', 'SL_VIOLATION', 'HARD_SL'):
                    open_trade_alerts.append({'token': token, 'alert': action, 'reason': reason})
        # Signal decisions
        elif line.startswith('DECIDE:'):
            parts = line.split(None, 4)
            if len(parts) >= 4:
                token = parts[1]
                direction = parts[2].upper()
                try:
                    confidence = int(min(100, max(0, float(parts[3]))))
                except (ValueError, IndexError):
                    confidence = 0
                reason = parts[4] if len(parts) > 4 else ''
                decisions[f"{token}:{direction}"] = {
                    'decision': direction.lower() if direction in ('LONG', 'SHORT') else 'wait',
                    'confidence': confidence,
                    'reason': reason[:200]
                }
                # HARD BLOCK: regime must align with direction (same logic as ai_decide())
                regime_val, regime_conf = regime_cache.get(token.upper(), ('NEUTRAL', 0))
                d = decisions[f"{token}:{direction}"]
                if d['decision'] != 'wait' and regime_val != 'NEUTRAL' and regime_conf > 50:
                    if (regime_val == 'LONG_BIAS' and d['decision'] == 'short') or \
                       (regime_val == 'SHORT_BIAS' and d['decision'] == 'long'):
                        d['decision'] = 'wait'
                        d['confidence'] = 0
                        d['reason'] = f'REGIME_BLOCK: {regime_val}({regime_conf}%) opposes {d["decision"]}'

    decisions['_open_trades'] = open_trade_alerts
    return decisions


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
            "SELECT timestamp, price FROM price_history WHERE token=? ORDER BY timestamp ASC",
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
    
    # Use minimax (OpenAI-compatible API) for AI decision
    try:
        import os, json as _json
        from openai import OpenAI

        # Load minimax credentials from auth.json
        _auth_path = '/root/.hermes/auth.json'
        _minimax_token = None
        _minimax_url = 'https://api.minimax.io/v1'
        try:
            with open(_auth_path) as _f:
                _auth = _json.load(_f)
            _creds = (_auth.get('credential_pool', {}) or {}).get('minimax', [])
            if _creds and isinstance(_creds, list):
                _minimax_token = _creds[0].get('access_token', '')
        except Exception:
            pass

        if not _minimax_token:
            raise RuntimeError("no minimax token")

        # Token budget check — estimate ~4000 tokens per call (prompt + completion)
        if not _check_token_budget(4000):
            print("[ai_decider] Token budget exceeded, skipping LLM call")
            return direction, abs(conf) * 30, "Budget exceeded"

        try:
            _client = OpenAI(api_key=_minimax_token, base_url=_minimax_url)
            _resp = _client.chat.completions.create(
                model="MiniMax-M2",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=4000
            )
            result = _resp.choices[0].message.content
            # Record token usage: estimate ~2000 prompt + actual output tokens
            try:
                _usage = _resp.usage
                _output_tokens = getattr(_usage, 'completion_tokens', 0) or len(result.split()) * 1.3
                _record_token_usage(int(2000 + _output_tokens))
                log_event('API_CALL', {'tokens_used': int(2000 + _output_tokens), 'model': 'MiniMax-M2'})
            except Exception:
                _record_token_usage(4000)  # fallback estimate
                log_event('API_CALL', {'tokens_used': 4000, 'model': 'MiniMax-M2'})
        except Exception as _mm_err:
            # QWEN IS OUT — no unsupervised decisions. Return WAIT and alert.
            print(f"[ai_decider] ⚠️ MINIMAX FAILED ({_mm_err}) — qwen fallback BLOCKED. Returning WAIT.")
            log_event('MINIMAX_FAILED', {
                'error': str(_mm_err),
                'coin': coin,
                'direction': direction,
                'action': 'BLOCKED_qwen_fallback-WAIT_returned'
            }, level='WARN')
            # Send Telegram alert if configured
            try:
                import os, json as _json
                _auth_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'auth.json')
                with open(_auth_path) as _f:
                    _auth = _json.load(_f)
                _telegram = (_auth.get('notifications', {}) or {}).get('telegram', {})
                _token = _telegram.get('bot_token')
                _chat_id = _telegram.get('chat_id')
                if _token and _chat_id:
                    import urllib.request
                    _msg = urllib.parse.quote(f"⚠️ ai_decider MINIMAX DOWN — qwen fallback blocked. {coin} {direction} = WAIT. Check Minimax API.")
                    urllib.request.urlopen(
                        f"https://api.telegram.org/bot{_token}/sendMessage?chat_id={_chat_id}&text={_msg}",
                        timeout=5
                    )
            except Exception:
                pass  # Never crash on alert failure
            return "wait", 0, "minimax_failed-blocked-qwen"
        
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

if __name__ == '__main__':
    try:
        pending = get_pending_signals()
    except:
        pending = []

    # Load hot set rounds and apply flip detection BEFORE reviewing signals
    _load_hot_rounds()

    # ── W&B Decision Audit Logging ─────────────────────────────────────────────
    _wandb_run = None
    _wandb_cycle = 0
    _pending_before = len(pending)  # capture once at top of run
    _n_pattern_signals = sum(1 for s in pending if s.get('signal_type', '').startswith('pattern_'))

    def _log_wandb(decision, token, direction, confidence, is_hot, is_pattern, reason=''):
        """Log a hot-set decision to W&B."""
        global _wandb_cycle
        if not _wandb_available or _wandb_run is None:
            return
        _wandb_cycle += 1
        # Per-token speed percentile (best-effort)
        spd_pct = 50.0
        if speed_tracker_ai is not None:
            try:
                spd = speed_tracker_ai().get_token_speed(token)
                if spd:
                    spd_pct = spd.get('speed_percentile', 50.0)
            except Exception:
                pass
        # Regime at decision time
        regime_val = 'NEUTRAL'
        try:
            regime_val, _ = get_regime(token)
        except Exception:
            pass
        wandb.log({
            'timestamp': datetime.utcnow().isoformat(),
            'cycle': _wandb_cycle,
            'regime': regime_val,
            'hotset_size': _pending_before,
            'top_token': token,
            'direction': direction.upper(),
            'top_score': confidence,
            'decision': decision.upper(),
            'is_hot_auto': is_hot,
            'is_pattern': is_pattern,
            'speed_percentile': spd_pct,
            'n_signals_total': _pending_before,
            'n_pattern_signals': _n_pattern_signals,
            'reason': str(reason)[:200],
        }, step=_wandb_cycle)
        # Local JSON backup — always saved regardless of W&B sync
        try:
            import json, os
            os.makedirs('/root/.hermes/wandb-local', exist_ok=True)
            with open('/root/.hermes/wandb-local/decisions.jsonl', 'a') as f:
                f.write(json.dumps({
                    'timestamp': datetime.utcnow().isoformat(),
                    'cycle': _wandb_cycle,
                    'regime': regime_val,
                    'hotset_size': _pending_before,
                    'top_token': token,
                    'direction': direction.upper(),
                    'top_score': confidence,
                    'decision': decision.upper(),
                    'is_hot_auto': is_hot,
                    'is_pattern': is_pattern,
                    'speed_percentile': spd_pct,
                    'n_signals_total': _pending_before,
                    'n_pattern_signals': _n_pattern_signals,
                    'reason': str(reason)[:200],
                }) + '\n')
        except Exception:
            pass

    if _wandb_available:
        try:
            _wandb_run = wandb.init(
                project='hermes-ai',
                name=datetime.utcnow().strftime('%Y-%m-%d-%H%M%S'),
                mode='offline',
                config={
                    'min_trades': PERF_CAL_MIN_TRADES,
                    'perf_cal_min': PERF_CAL_MIN_TRADES,
                    'perf_cal_max': PERF_CAL_MAX_WEIGHT,
                    'daily_token_budget': _DAILY_TOKEN_BUDGET,
                    'max_open': MAX_OPEN,
                    'exempt_confidence': 85,
                    'purge_threshold': 5,
                },
                settings=wandb.Settings(anonymous='allow'),
            )
            print(f"[wandb] Decision audit logging started: {_wandb_run.url if hasattr(_wandb_run, 'url') else 'run-id'}")
        except Exception as e:
            print(f"[wandb] Init failed: {e}")
            _wandb_run = None

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
        tok = (s.get('token') or '').upper()
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
                    WHERE token=?
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
        tok = (s.get('token') or '').upper()
        sig_dir = (s.get('direction') or '').upper()
        if tok in _hot_rounds:
            hot_dir = _hot_rounds[tok]['direction'].upper()
            if sig_dir != hot_dir and sig_dir in ('LONG', 'SHORT'):
                killed = _kill_pending_opposite(tok, hot_dir)
                if killed:
                    print(f"   🔥 FLIP KILL: {tok} {hot_dir} hot set kept — killed {sig_dir} PENDING")
                else:
                    print(f"   🔥 HOT KEEP:  {tok} {hot_dir} hot set survived PENDING {sig_dir}")

    print(f"=== AI Decider: {len(pending)} pending | Paper Open: {get_open()}/{MAX_OPEN} | Hot: {len(_hot_rounds)} | Counter: {counter_killed} | Deesc: {deesc_count} ===")

    # Get market context once
    market_z = get_market_zscore()
    prices = get_prices()
    update_trade_prices()  # Update current_price for all open trades
    print(f"Market: Z-Score={market_z}, BTC=${prices.get('BTC','N/A')}")

    # ── BATCH MODE: one Minimax call for ALL signals + open trade monitoring ──
    # Only call if there are non-hot signals to review (hot signals auto-approve)
    non_hot_signals = [s for s in pending
                       if s.get('token', '').upper() not in _hot_rounds
                       or _hot_rounds.get(s.get('token', '').upper(), {}).get('rounds', 0) < 1]
    if non_hot_signals:
        print(f"[batch] Sending {len(non_hot_signals)} signals + open trades to Minimax in ONE call...")
        batch_decisions = ai_decide_batch(non_hot_signals, market_z, prices)
        # Log open trade alerts if any
        open_alerts = batch_decisions.get('_open_trades', [])
        if open_alerts:
            for alert in open_alerts:
                print(f"  🚨 OPEN TRADE ALERT: {alert['token']} → {alert['alert']}: {alert['reason']}")
                log_event('OPEN_TRADE_ALERT', alert, level='WARN')
    else:
        batch_decisions = {}

    processed_this_run = set()  # token+direction already reviewed this run

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
            _log_wandb('SKIPPED', t, direction, conf, False,
                       s.get('signal_type', '').startswith('pattern_'),
                       'blacklist-short')
            continue
    
        if direction.lower() == "long" and t.upper() in LONG_BLACKLIST:
            print(f"   🚫 {t}: BLACKLISTED - skipping LONG (poor performance)")
            log_signal(t, direction, entry, s.get("confidence", 0), f"SKIPPED-blacklist-{exchange}")
            mark_signal_processed(t, 'SKIPPED', decision_reason=f'blacklist-long')
            _log_wandb('SKIPPED', t, direction, conf, False,
                       s.get('signal_type', '').startswith('pattern_'),
                       'blacklist-long')
            continue

        # FIX (2026-04-02): Block STABLE/STBL tokens. These are illiquid, error-prone
        # tokens that appear in HL data but frequently generate bad signals.
        # STABLE incident: confluence 99% signal, wrong direction, cascade massacre.
        if t.upper() in ('STABLE', 'STBL'):
            print(f"   🚫 {t}: BLOCKED — illiquid/non-standard token (2026-04-02 incident)")
            log_signal(t, direction, entry, s.get('confidence', 0), "SKIPPED-stable-block")
            mark_signal_processed(t, 'SKIPPED', decision_reason='blocked-illiquid-token')
            _log_wandb('SKIPPED', t, direction, conf, False,
                       s.get('signal_type', '').startswith('pattern_'),
                       'stable-block')
            continue

        # FIX (2026-04-05): Solana-only tokens (Raydium) are NOT tradeable on Hyperliquid.
        # This check was ONLY in the hot-set building path (line ~231) but was MISSING
        # from the execution path. KAS SHORT was executed at 14:25 despite being Solana-only.
        # Defense-in-depth: check here AND in decider-run.py line ~754.
        if is_solana_only(t):
            print(f"   🚫 {t}: BLOCKED — Solana-only token (not on Hyperliquid)")
            log_signal(t, direction, entry, s.get('confidence', 0), f"SKIPPED-solana-only-{exchange}")
            mark_signal_processed(t, 'SKIPPED', decision_reason=f'solana-only-{exchange}')
            _log_wandb('SKIPPED', t, direction, conf, False,
                       s.get('signal_type', '').startswith('pattern_'),
                       'solana-only')
            continue

        # Check open PAPER slots only — live HL trades should not block paper trading.
        # is_token_open() below handles per-token dedup regardless of paper/live.
        if get_open() >= MAX_OPEN:
            print(f"⏸️ {t}: max paper trades reached ({get_open()}/{MAX_OPEN})")
            log_signal(t, direction, entry, conf, f"SKIPPED-max-{exchange}")
            _log_wandb('SKIPPED', t, direction, conf, False,
                       s.get('signal_type', '').startswith('pattern_'),
                       'max-open-slots')
            continue
        # ── Hot set: r1+ auto-approval ──────────────────────────────────────────
        hot = _hot_rounds.get(t.upper())
        if hot and hot['rounds'] >= 1:
            # Proven by AI across 1+ review round — skip AI review, auto-approve
            # FIX (2026-04-01): Lowered from r2+ to r1+ — signals were expiring before
            # reaching r2 due to 15-min TTL, and many legitimate signals stay WAIT
            # (AI needs more data) instead of going straight to EXEC.

            # Quality gate: require 1+ distinct signal types and avg_conf >= 80%
            # FIX (2026-04-05): Raised from 40% → 80% because hot-set now has 20+ tokens.
            # With more tokens competing for 10 slots, we need higher conviction to avoid
            # low-confidence noise from filling our portfolio and blocking real signals.
            num_types = hot.get('num_types', 0)
            avg_conf = hot.get('avg_conf', 0)
            if num_types < 1 or avg_conf < 80:
                avg_conf_str = f"{avg_conf:.0f}%" if avg_conf is not None else "N/A"
                print(f"   ⏸️ 🔥 r{hot['rounds']} {t} [{hot.get('source','?')}]: quality gate failed (types={num_types}, avg_conf={avg_conf_str})")
                log_signal(t, direction, entry, conf, f"hot-gate-fail-{exchange}")
                mark_signal_processed(t, 'SKIPPED', hot.get('signal_ids'), decision_reason='hot-set-quality-gate')
                processed_this_run.add(key)
                _log_wandb('HOT_SKIPPED', t, direction, avg_conf, True,
                           (hot.get('source') or '').startswith('pattern_scanner'),
                           f'hot-quality-gate-types{num_types}-conf{avg_conf_str}')
                continue

            if is_token_open(t):
                print(f"   ⏸️ 🔥 HOT r{hot['rounds']} {t} [{hot.get('source','?')}]: already has open position")
                log_signal(t, direction, entry, conf, f"SKIPPED-open-{exchange}")
                mark_signal_processed(t, 'SKIPPED', hot.get('signal_ids'), decision_reason='hot-set-position-open')
                processed_this_run.add(key)
                _log_wandb('HOT_SKIPPED', t, direction, avg_conf, True,
                           (hot.get('source') or '').startswith('pattern_scanner'),
                           'hot-position-open')
                continue

            # Blacklist double-check
            if direction.lower() == "short" and t.upper() in SHORT_BLACKLIST:
                print(f"   🚫 🔥 HOT r{hot['rounds']} {t}: BLACKLISTED — skipping SHORT")
                log_signal(t, direction, entry, conf, f"SKIPPED-blacklist-{exchange}")
                mark_signal_processed(t, 'SKIPPED', hot.get('signal_ids'), decision_reason='hot-set-blacklist')
                processed_this_run.add(key)
                _log_wandb('HOT_SKIPPED', t, direction, avg_conf, True,
                           (hot.get('source') or '').startswith('pattern_scanner'),
                           'hot-blacklist')
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
                _log_wandb('HOT_APPROVED', t, direction, final_conf, True,
                           t.upper().startswith('PATTERN_') or (hot.get('source') or '').startswith('pattern_'),
                           f'hot-r{hot["rounds"]}-auto-approved')
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
    LLM CANDLE PREDICTION (for reference — low weight):
    - Predicted Direction: {prediction['direction']} ({prediction['confidence']}% confidence)
    - Model Historical Accuracy: {prediction['accuracy']}%
    {token_info}
    IMPORTANT: The candle predictor is unreliable (35% accuracy, 0% in last 24h).
    Treat its predictions as weak signal at best. Primary trust: momentum signal + MACD + RSI.
    """""
    
        # Get z-score tier from signal
        z_tier = s.get('z_score_tier')
        z = s.get('z_score')
        if z_tier:
            print(f"   📊 Z-Score Tier: {z_tier} (z={z:.2f})")

        # ── Use batch decision if available (single Minimax call for all non-hot signals) ──
        batch_key = f"{t}:{direction.upper()}"
        if batch_key in batch_decisions:
            bd = batch_decisions[batch_key]
            decision = bd['decision']
            ai_conf = bd['confidence']
            reason = bd.get('reason', 'batch-decision')
            print(f"\n🤖 BATCH DECISION: {t} {direction} → {decision.upper()} (conf: {ai_conf}%)")
            print(f"   Reason: {reason[:100]}...")
        else:
            # Fall back to individual call (hot signals, edge cases)
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
                WHERE token=? AND direction=? AND decision='APPROVED' AND executed=0
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
                _log_wandb('SKIPPED', t, direction, ai_conf, False,
                           s.get('signal_type', '').startswith('pattern_'),
                           'no-pump-momentum')
            elif is_token_open(t):
                print(f"   ⏸️ SKIPPED - {t} already has open position")
                log_signal(t, direction, entry, conf, f"SKIPPED-open-{exchange}")
                mark_signal_processed(t, 'SKIPPED', decision_reason='position-already-open')
                _log_wandb('SKIPPED', t, direction, ai_conf, False,
                           s.get('signal_type', '').startswith('pattern_'),
                           'position-already-open')
            else:
                # Record approval
                ok = mark_signal_processed(t, 'APPROVED')
                if ok:
                    print(f"   ✅ APPROVED: {t} {decision.upper()} — decider-run will execute")
                    log_signal(t, decision, entry, ai_conf, exchange)
                    _log_wandb('APPROVED', t, direction, ai_conf, False,
                               s.get('signal_type', '').startswith('pattern_'),
                               f'ai-reviewed-{reason[:80]}')
                else:
                    print(f"   ❌ Failed to record approval")
                    log_signal(t, decision, entry, ai_conf, f"FAILED-{exchange}")
                    mark_signal_processed(t, 'FAILED', decision_reason='approval-record-failed')
        else:
            print(f"   ⏸️ AI said WAIT")
            log_signal(t, direction, entry, ai_conf, f"WAIT-{exchange}")
            mark_signal_processed(t, 'WAIT', decision_reason=f'ai-wait-{decision}')
            _log_wandb('WAIT', t, direction, ai_conf, False,
                       s.get('signal_type', '').startswith('pattern_'),
                       f'ai-wait-{reason[:80]}')


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

    # W&B: close run
    if _wandb_available and _wandb_run is not None:
        try:
            wandb.finish()
            print(f"[wandb] Decision audit run finished ({_wandb_cycle} cycles logged)")
        except Exception as e:
            print(f"[wandb] finish error: {e}")

    # Release lock
    release_lock()
