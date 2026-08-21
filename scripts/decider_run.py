#!/usr/bin/env python3
"""
decider_run.py — Execute approved signals via brain.py.
Respects hype_live_trading.json: paper=False (live by default).
Reads APPROVED signals, checks position limits, computes SL/TP, places trades.
Also processes delayed-entry signals from pending-delayed-entries.json.
"""
import sys, subprocess, sqlite3, time, os, json, random, psycopg2, fcntl
from typing import NamedTuple
sys.path.insert(0, '/root/.hermes/scripts')
from signal_schema import (init_db, get_approved_signals, get_pending_signals,
                           mark_signal_executed, cleanup_stale_approved,
                           update_signal_decision, validate_source)
from paths import *
# NOTE: legacy LLM-based compaction removed. Current pipeline uses:
#   signal_compactor.py (runs every 1 min via hermes-signal-compactor.timer) → writes hotset.json
#   decider_run.py (runs every 1 min via hermes-pipeline.timer) → reads hotset.json, executes trades
# get_regime is pre-computed in hotset.json by signal_compactor
from _secrets import BRAIN_DB_DICT
from position_manager import (get_position_count, is_position_open, enforce_max_positions,
                              get_trade_params, set_loss_cooldown,
                              is_wrong_side_risky)
from signal_schema import _is_loss_cooldown_active
from signal_gen import PUMP_SL_PCT, PUMP_TP_PCT
from hermes_constants import (
    SHORT_BLACKLIST, LONG_BLACKLIST, MAX_OPEN_POSITIONS, HOTSET_ENABLED,
    RS_DECIDER_MIN_TOUCHES, RS_DECIDER_ZBONUS_TOUCHES, RS_DECIDER_ZBONUS_ZSCORE,
    RS_DECIDER_CONF_PENALTY, RS_DECIDER_CONF_FLOOR,
    RS_TOUCH_HARD_CAP,
    TRAILING_ACTIVATION_PCT, TRAILING_DISTANCE_PCT,
    CONFLUENCE_REQUIRED,
    MOMENTUM_EXHAUSTION_THRESHOLD,
    SIGNAL_INVERSION_ENABLED, SIGNAL_INVERSION_MAP,
    DYNAMIC_INVERSION_ENABLED, INVERT_WR_THRESHOLD, INVERT_MIN_TRADES,
    INVERT_LOOKBACK_HOURS, INVERT_CACHE_TTL, INVERT_SIGNALS,
    DEAD_HOURS_ENABLED, DEAD_HOURS_START, DEAD_HOURS_END,
    DEAD_HOURS_SIGNALS, DEAD_HOURS_DEFAULT,
     CONTEXT_GATE_ENABLED, CONTEXT_GATE_LLM_ENABLED, CONTEXT_GATE_LLM_MODEL,
     CONTEXT_GATE_SPEED_MIN, CONTEXT_GATE_Z_COUNTER_TREND,
     CONTEXT_GATE_Z_RANGING, CONTEXT_GATE_RANGING_SPEED,
     CONTEXT_GATE_SPEED_CONFIRM, CONTEXT_GATE_CACHE_TTL,
     CONTEXT_GATE_LLM_TIMEOUT, CONTEXT_GATE_FAIL_OPEN,
    SIGNAL_FILTER_ENABLED, SIGNAL_FILTER_SPEED_MIN, SIGNAL_FILTER_NEUTRAL_SPEED_MIN, SIGNAL_FILTER_MOMENTUM_MIN,
    SIGNAL_FILTER_RSI_MIN, SIGNAL_FILTER_RSI_MAX,
    SIGNAL_FILTER_Z_MIN, SIGNAL_FILTER_Z_MAX,
    ZSCORE_ACCEL_ENABLED, ZSCORE_ACCEL_Z_THRESHOLD, ZSCORE_ACCEL_ACCEL_THRESHOLD,
    SIMILAR_SETUP_LOOKUP_ENABLED, SIMILAR_SETUP_MIN_SAMPLE,
    SIMILAR_SETUP_HARD_BLOCK_WR, SIMILAR_SETUP_HARD_BLOCK_MIN_N,
    SIMILAR_SETUP_PENALTY_40, SIMILAR_SETUP_PENALTY_30,
    SIMILAR_SETUP_RSI_BAND, SIMILAR_SETUP_CACHE_TTL,
    LLM_CONFIDENCE_PENALTY,
     TOKEN_WR_THRESHOLD, TOKEN_WR_MIN_SAMPLE,
     WRONG_SIDE_PENALTY, WRONG_SIDE_SKIP_THRESHOLD,
    HEBBIAN_BOOST_WR, HEBBIAN_BOOST_AMOUNT, HEBBIAN_BOOST_MIN_N,
    HEBBIAN_PENALTY_WR, HEBBIAN_PENALTY_AMOUNT, HEBBIAN_PENALTY_MIN_N,
    HEBBIAN_CACHE_TTL,
    HEBBIAN_GATE_ENABLED, HEBBIAN_AUTO_APPROVE_WR, HEBBIAN_AUTO_REJECT_WR,
    HEBBIAN_AUTO_MIN_N, HEBBIAN_AUTO_MIN_N_HIGH_CONF, HEBBIAN_HIGH_CONF_EXIT_RATIO,
    HEBBIAN_EXIT_PROFIT_BOOST, HEBBIAN_EXIT_SL_PENALTY,
    HEBBIAN_EXIT_SL_AUTO_REJECT_RATIO, HEBBIAN_EXIT_SL_AUTO_REJECT_MIN_N,
    HEBBIAN_COMBO_PART_BOOST, HEBBIAN_TOKEN_WR_BOOST, HEBBIAN_TOKEN_WR_MIN_N,
    HEBBIAN_TOKEN_WR_RATIO_HIGH, HEBBIAN_TOKEN_WR_RATIO_LOW,
    HEBBIAN_CIRCUIT_BREAKER_WR, HEBBIAN_CIRCUIT_BREAKER_N, HEBBIAN_CIRCUIT_BREAKER_COOLDOWN_SEC,
    TOKEN_SENTIMENT_ENABLED, TOKEN_SENTIMENT_K,
    TOKEN_SENTIMENT_SKIP_THRESHOLD, TOKEN_SENTIMENT_HARD_SKIP_THRESHOLD,
    TOKEN_SENTIMENT_BOOST_THRESHOLD, TOKEN_SENTIMENT_BOOST_AMOUNT,
)
from tokens import is_solana_only
from hermes_file_lock import FileLock
from hyperliquid_exchange import is_live_trading_enabled, is_delisted
import hype_cache as hc

# ── OPTION 1: Signal Direction Flip ──────────────────────────────────────
# Signal direction flip — disabled 2026-04-05 (flip test concluded)
# Previously enabled to test if signals were direction-inverted (WR 13.8%).
# KILL SWITCH: set to True to re-enable flip. Effect takes place on next pipeline run (~1 min).
_FLIP_SIGNALS = False

# ── Dynamic Signal Inversion (WR-based auto-invert) ────────────────────
# ponytail: single cache dict, per-process. TTL prevents DB hammering.
_dynamic_invert_cache = {}  # {signal_type: should_invert}
_dynamic_invert_ts = 0

def _should_dynamic_invert(source):
    """Check if a signal source should be dynamically inverted based on24h WR.

    Returns True if the signal's WR is below INVERT_WR_THRESHOLD with enough trades.
    Caches results for INVERT_CACHE_TTL seconds.
    """
    import time as _time
    global _dynamic_invert_cache, _dynamic_invert_ts

    if not DYNAMIC_INVERSION_ENABLED or not source:
        return False

    now = _time.time()
    if now - _dynamic_invert_ts > INVERT_CACHE_TTL:
        _dynamic_invert_cache = {}
        _dynamic_invert_ts = now

    if source in _dynamic_invert_cache:
        return _dynamic_invert_cache[source]

    # Query signal_outcomes for24h WR of this signal_type
    try:
        import sqlite3 as _sqlite3
        from paths import RUNTIME_DB
        conn = _sqlite3.connect(RUNTIME_DB, timeout=5)
        try:
            # LIKE handles both standalone ('zscore-rising+') and compound
            # ('zscore-rising+,tl_break_long') signal_type values
            row = conn.execute("""
                SELECT COUNT(*) as trades,
                       ROUND(CAST(SUM(is_win) AS FLOAT)/COUNT(*)*100, 1) as wr
                FROM signal_outcomes
                WHERE signal_type LIKE '%' || ? || '%'
                  AND created_at > datetime('now', '-' || ? || ' hours')
                  AND trade_id IS NOT NULL
            """, (source, INVERT_LOOKBACK_HOURS)).fetchone()
        finally:
            conn.close()

        if row and row[0] >= INVERT_MIN_TRADES and row[1] is not None and row[1] < INVERT_WR_THRESHOLD:
            _dynamic_invert_cache[source] = True
            return True
    except Exception:
        pass  # fail open — don't block trades on DB errors

    _dynamic_invert_cache[source] = False
    return False


def _apply_inversion(direction, source, token=''):
    """Apply static + dynamic signal inversion. Returns (new_direction, was_flipped)."""
    # 1) Static map (explicit overrides)
    if SIGNAL_INVERSION_ENABLED:
        for prefix, should_invert in SIGNAL_INVERSION_MAP.items():
            if should_invert and source and source.startswith(prefix):
                flipped = 'SHORT' if direction == 'LONG' else 'LONG'
                log(f'  [INVERT] {token} {source}: {direction} → {flipped} (static map)')
                return flipped, True

    # 2) Dynamic WR-based auto-invert
    if DYNAMIC_INVERSION_ENABLED and source:
        # Check each monitored signal type as a prefix match
        for sig_type in INVERT_SIGNALS:
            if source.startswith(sig_type) and _should_dynamic_invert(sig_type):
                flipped = 'SHORT' if direction == 'LONG' else 'LONG'
                log(f'  [INVERT] {token} {source}: {direction} → {flipped} (dynamic WR<{INVERT_WR_THRESHOLD}%)')
                return flipped, True

    # 3) Legacy global flip
    if _FLIP_SIGNALS:
        flipped = 'SHORT' if direction == 'LONG' else 'LONG'
        log(f'  [FLIP] {token} {direction} → {flipped} (legacy)')
        return flipped, True

    return direction, False


# ── ATR-based Dynamic Stop Loss ─────────────────────────────────────────
# ATR(14) from Hyperliquid 1h candles — cached per token for 5 min.
# SL = entry_price ± (k * ATR(14)) where k varies by volatility regime.
# This replaces fixed % SL which was too tight for volatile tokens (71.5%
# of losses had <1% adverse move — SL fired on noise).
#
# k multipliers (confirmed against hermes_constants.py ATR_K_LOW/NORMAL/HIGH_VOL):
#   LOW_VOLATILITY:    k=1.0  (SL ≈ 1× ATR — tight for low-vol tokens)
#   NORMAL_VOLATILITY: k=2.0  (SL ≈ 2× ATR — gives trade room to breathe)
#   HIGH_VOLATILITY:   k=2.5  (SL ≈ 2.5× ATR — tokens like TAO, SOL need room)
# Minimum SL guard: never tighter than sl_pct (A/B test value), use ATR if wider.


# ── Checkpoint & Event-log instrumentation ───────────────────────────────
try:
    from checkpoint_utils import checkpoint_write, checkpoint_read_last, detect_incomplete_run
except Exception:
    checkpoint_write = lambda *a, **k: ''
    checkpoint_read_last = detect_incomplete_run = lambda *a, **a2: None

try:
    from event_log import log_event, EVENT_TRADE_ENTERED, EVENT_TRADE_FAILED, EVENT_HOTSET_UPDATED
except Exception:
    log_event = lambda *a, **k: None

# Speed feature: speed-weighted hot set scoring
from hermes_constants import SPEED_HOTSET_WEIGHT as SPEED_WEIGHT
try:
    from speed_tracker import SpeedTracker
    speed_tracker_dr = SpeedTracker()
except Exception as e:
    print(f"[decider-run] SpeedTracker unavailable: {e}")
    speed_tracker_dr = None

# Hot-set discipline: track when signal_compactor last ran compaction.
# The hot-set is THE single gate for execution — it comes from signal_compactor output.
# signal_compactor.py runs every 1 min (hermes-signal-compactor.timer) and writes hotset.json.
# We track the last compaction timestamp to detect if the pipeline is stalled.
_HOTSET_LAST_UPDATED_FILE = HOTSET_META_FILE

def _get_hotset_last_updated():
    """Return Unix timestamp of last signal_compactor compaction, or 0 if never."""
    try:
        if os.path.exists(_HOTSET_LAST_UPDATED_FILE):
            with open(_HOTSET_LAST_UPDATED_FILE) as f:
                data = json.load(f)
            return data.get('last_compaction_ts', 0)
    except Exception:
        pass
    return 0


from hermes_constants import DEFAULT_TRADE_SIZE_USDT, HL_MIN_NOTIONAL_USDT, FAVORITES, FAVORITES_SIZE_MULT

from hermes_log import log
BRAIN_CMD       = '/root/.hermes/scripts/brain.py'
SERVER          = 'Hermes'
MAX_POS         = MAX_OPEN_POSITIONS
POSITION_SIZE_USD = DEFAULT_TRADE_SIZE_USDT   # FIX (2026-05-19): was hardcoded 50.0 — now from hermes_constants
LOG_FILE        = '/var/www/hermes/logs/signals.log'
DELAYED_FILE    = '/var/www/hermes/data/pending-delayed-entries.json'
AB_CONFIG_FILE  = '/root/.hermes/data/ab-test-config.json'
EPSILON         = 0.20   # 20% exploration rate

# Rate limit: cache last entry timestamp, refresh from DB every 5 minutes
_RATE_LIMIT_CACHE = {"last_entry": None, "cached_at": 0}
_RATE_LIMIT_TTL    = 300  # seconds

os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
os.makedirs(os.path.dirname(DELAYED_FILE), exist_ok=True)

# ─── Guardian Closing Marker Check ─────────────────────────────────────────────
# When guardian closes an orphan position, it writes a marker to this file BEFORE
# calling market_close. decider_run checks it before executing any trade for a
# token that guardian is actively closing. This prevents the race:
#   guardian closes orphan → signal_compactor approves new signal → dual execution.
_GUARDIAN_CLOSING_FILE = os.path.join(HERMES_DATA, 'guardian-closing-markers.json')

def _is_guardian_closing(token: str) -> bool:
    """Return True if guardian is currently closing this token (closing marker active)."""
    try:
        if os.path.exists(_GUARDIAN_CLOSING_FILE):
            with FileLock('guardian_closing'):
                with open(_GUARDIAN_CLOSING_FILE) as f:
                    data = json.load(f)
            return token.upper() in data.get('tokens', {})
    except Exception:
        pass
    return False

# ─── Direction Awareness ─────────────────────────────────────────────────────
# If a direction has < 50% win rate in recent history, pause it.
# This prevents the system from bleeding on a consistently losing direction.
_DIR_WR_CACHE = {}      # {(token, direction): (wr, count, timestamp)}
_DIR_WR_TTL    = 3600    # 1 hour

def _get_direction_wr(token: str, direction: str) -> tuple:
    """Return (win_rate_pct, trade_count) for a token+direction in last 7 days."""
    key = (token.upper(), direction.upper())
    now = time.time()
    if key in _DIR_WR_CACHE:
        cached_wr, cached_count, cached_at = _DIR_WR_CACHE[key]
        if now - cached_at < _DIR_WR_TTL:
            return cached_wr, cached_count

    try:
        conn = psycopg2.connect(**BRAIN_DB_DICT)
        cur = conn.cursor()
        cur.execute("""
            SELECT COUNT(*) as total,
                   SUM(CASE WHEN pnl_usdt > 0 THEN 1 ELSE 0 END) as wins
            FROM trades
            WHERE token=%s AND direction = %s
              AND status = 'closed'
              AND close_time >= NOW() - INTERVAL '7 days'
        """, (token.upper(), direction.upper()))
        row = cur.fetchone()
        cur.close(); conn.close()
        total = row[0] or 0
        wins = row[1] or 0
        wr = (wins / total * 100) if total >= 3 else 50.0  # need at least 3 trades to judge
        _DIR_WR_CACHE[key] = (wr, total, now)
        return wr, total
    except Exception:
        return 50.0, 0  # neutral if DB error


# ─── Per-token Leverage Cache ──────────────────────────────────────────────────
_LEVERAGE_CACHE = {}          # {token: {'leverage': int, 'cached_at': float}}
_LEVERAGE_CACHE_TTL = 3600   # 1 hour

def _update_decider_heartbeat():
    """Update pipeline heartbeat for decider-run."""
    import json
    hb_file = PIPELINE_HB_FILE
    try:
        with FileLock('pipeline_heartbeat'):
            data = {}
            if os.path.exists(hb_file):
                with open(hb_file) as f:
                    data = json.load(f)
            data['decider_run'] = {"timestamp": time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), "status": "ok"}
            with open(hb_file, 'w') as f:
                json.dump(data, f, indent=2)
    except Exception:
        pass  # never crash on heartbeat failures


def get_current_price(token):
    """Fetch current price — uses shared HL cache first, falls back to live."""
    import hype_cache as hc
    mids = hc.get_allMids()
    return float(mids.get(token, 0)) or None


def get_max_leverage(token: str) -> int:
    """
    Get max leverage for a token from Hyperliquid meta API.
    Cached for 1 hour to avoid rate limiting.
    Returns 1-50, capped at MAX_LEVERAGE (10).
    """
    token_upper = token.upper()
    now = time.time()

    if token_upper in _LEVERAGE_CACHE:
        cached = _LEVERAGE_CACHE[token_upper]
        if now - cached.get('cached_at', 0) < _LEVERAGE_CACHE_TTL:
            return cached['leverage']

    try:
        # Use shared cache (written by price_collector) instead of direct HL API call
        meta = hc.get_meta()
        for u in meta.get('universe', []):
            if u.get('name') == token_upper:
                max_lev = int(u.get('maxLeverage', 10))
                lev = min(max_lev, 10)  # cap at 10x
                _LEVERAGE_CACHE[token_upper] = {'leverage': lev, 'cached_at': now}
                return lev
    except Exception:
        pass

    # Cache negative (fetch failed) for 5 min to avoid hammering API
    _LEVERAGE_CACHE[token_upper] = {'leverage': 10, 'cached_at': now - _LEVERAGE_CACHE_TTL + 300}
    return 10  # fallback


# ─── Delayed Entry Processor ──────────────────────────────────────

def _load_delayed():
    """Load pending delayed entries."""
    try:
        with open(DELAYED_FILE) as f:
            data = json.load(f)
            # Support both {"pending": [...]} and [...] formats
            if isinstance(data, dict):
                return data.get('pending', [])
            return data if isinstance(data, list) else []
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def _save_delayed(entries):
    """Save pending delayed entries."""
    with FileLock('delayed_entries'):
        with open(DELAYED_FILE, 'w') as f:
            json.dump(entries, f, indent=2)


# ─── Thompson Sampling A/B Selection ───────────────────────────────────────────

def get_ab_variant(test_name: str, direction: str) -> dict:
    """
    Canonical A/B variant selection — delegates to ab_utils.get_ab_variant().
    This ensures Thompson sampling is used consistently everywhere.
    """
    from hermes_ab_utils import get_ab_variant as _get
    return _get(test_name, direction)



def _record_ab_trade_opened(token, direction, experiment, variant_id, test_name):
    """Record trade open in ab_results table."""
    if not experiment:
        return
    try:
        import psycopg2
        conn = psycopg2.connect(**BRAIN_DB_DICT)
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO ab_results (test_name, variant_id, trades, wins, losses,
                                    total_pnl_pct, total_pnl_usdt, updated_at)
            VALUES (%s, %s, 1, 0, 0, 0, 0, now())
            ON CONFLICT (test_name, variant_id)
            DO UPDATE SET
                trades = ab_results.trades + 1,
                updated_at = now()
        """, (test_name, variant_id))
        conn.commit()
        cur.close(); conn.close()
    except Exception as e:
        log(f'[AB] record opened error: {e}')


def get_ab_params_for_trade(direction: str) -> dict:
    """
    Get all A/B params for a trade using Thompson sampling (via ab_utils).
    Returns dict with sl_pct, trailing_activation, trailing_distance, experiment metadata.
    """
    # SL test
    sl_variant = get_ab_variant('sl-distance-test', direction)
    sl_pct = max(0.5, sl_variant.get('config', {}).get('slPct', 0.02))  # floor at 0.5%

    # Entry timing test
    entry_variant = get_ab_variant('entry-timing-test', direction)
    entry_mode = entry_variant.get('config', {}).get('entryMode', 'immediate')

    # Trailing stop test — ab_tests.json stores values like 0.5 (= 50%) or 1.0 (= 100%)
    # FIX (2026-04-02): old condition raw >= 1.0 never triggered for 0.5 → trailing = 50%!
    ts_variant = get_ab_variant('trailing-stop-test', direction)
    raw_act  = ts_variant.get('config', {}).get('trailingActivationPct', 0.01)
    raw_dist = ts_variant.get('config', {}).get('trailingDistancePct', 0.01)
    def _norm_pct(val, default=0.01):
        if val is None or val <= 0:
            return default
        if val > 0.01:   # value like 0.5 (= 50%) or 1.0 (= 100%) — divide by 100
            return val / 100.0
        return val        # already a small fraction like 0.005 (= 0.5%)
    trailing_activation = _norm_pct(raw_act)
    trailing_distance   = _norm_pct(raw_dist)
    trailing_phase2_dist = ts_variant.get('config', {}).get('trailingPhase2DistancePct')
    if trailing_phase2_dist is not None and trailing_phase2_dist > 1.0:
        trailing_phase2_dist = trailing_phase2_dist / 100.0

    # Experiment metadata
    experiments = []
    if sl_variant:
        experiments.append(('sl-distance-test', sl_variant.get('id', '')))
    if entry_variant:
        experiments.append(('entry-timing-test', entry_variant.get('id', '')))
    if ts_variant:
        experiments.append(('trailing-stop-test', ts_variant.get('id', '')))

    experiment_str = None
    if experiments:
        parts = [f'{t}:{v}' for t, v in experiments]
        experiment_str = '|'.join(parts)

    return {
        'sl_pct': sl_pct,
        'entry_mode': entry_mode,
        'trailing_activation': trailing_activation,
        'trailing_distance': trailing_distance,
        'trailing_phase2_dist': trailing_phase2_dist,
        'experiment': experiment_str,
        'sl_variant': sl_variant.get('id', '') if sl_variant else '',
        'entry_variant': entry_variant.get('id', '') if entry_variant else '',
        'ts_variant': ts_variant.get('id', '') if ts_variant else '',
    }


def process_delayed_entries(paper=False):
    """
    Check pending delayed-entry signals.
    For each: if pullback reached OR max_wait expired → execute or expire.
    Returns (executed, expired).
    """
    pending = _load_delayed()
    if not pending:
        return 0, 0

    executed = 0
    expired = 0
    still_pending = []

    for entry in pending:
        token = entry['token']
        direction  = entry['direction']
        source = entry.get('source', '')
        # ── Signal Inversion (static + dynamic) for delayed entries ───────
        direction, _ = _apply_inversion(direction, source, token)
        entry['direction'] = direction

        # ── Dead-Hours Filter for delayed entries ────────────────────────
        if DEAD_HOURS_ENABLED:
            import datetime as _dt
            _utc_hour = _dt.datetime.utcnow().hour
            if DEAD_HOURS_START <= _utc_hour < DEAD_HOURS_END:
                # Check if this signal is in the dead-hours block list
                _signal = entry.get('signal', '')
                _should_block = DEAD_HOURS_DEFAULT  # default behavior
                for prefix in DEAD_HOURS_SIGNALS:
                    if _signal.startswith(prefix):
                        _should_block = False  # allowlisted — don't block
                        break
                if _should_block:
                    log(f'⏰ DELAYED DEAD-HOURS: {token} {direction} blocked: {_utc_hour:02d}:XX UTC (signal={_signal})')
                    still_pending.append(entry)  # retry after dead hours end
                    continue

        sig_price = entry['signal_price']   # price when signal fired
        pullback   = entry.get('pullback_pct', 0.01)
        max_wait   = entry.get('max_wait_minutes', 30)
        sl_pct     = entry.get('sl_pct', 0.02)
        conf       = entry.get('confidence', 50)
        queued_at  = entry.get('queued_at', '')

        # Check expiry
        if queued_at:
            try:
                queued_time = time.mktime(time.strptime(queued_at, '%Y-%m-%dT%H:%M:%S.%f'))
            except ValueError:
                try:
                    queued_time = time.mktime(time.strptime(queued_at, '%Y-%m-%dT%H:%M:%S'))
                except ValueError:
                    queued_time = time.time()
            if time.time() - queued_time > max_wait * 60:
                log(f'⏰ DELAYED EXPIRED: {token} {direction} (waited {max_wait}min, no pullback)')
                expired += 1
                continue

        # Get current price
        cur_price = get_current_price(token)
        if not cur_price or cur_price <= 0:
            still_pending.append(entry)
            continue

        # Determine if pullback reached
        if direction.upper() == 'LONG':
            # Pullback = price dropped from sig_price
            drop_pct = (sig_price - cur_price) / sig_price
            triggered = drop_pct >= pullback
        else:
            # SHORT: pullback = price rose from sig_price
            rise_pct = (cur_price - sig_price) / sig_price
            triggered = rise_pct >= pullback

        if not triggered:
            still_pending.append(entry)
            continue

        # Pullback reached → execute trade
        log(f'🎯 DELAYED ENTRY: {token} {direction} @ ${cur_price:.6f} '
            f'(sig=${sig_price:.4f}, pullback={pullback*100:.1f}%)')

        # ATR SL/TP is set by position_manager on the first cycle (within 1 min of entry).
        # Passing sl=0, tp=0 defers to position_manager._collect_atr_updates().
        sl = 0
        tp = 0
        cmd_side = 'buy' if direction.upper() == 'LONG' else 'sell'

        experiment = entry.get('experiment', 'control')
        variant_id = entry.get('variant_id', '')
        test_name  = entry.get('test_name', '')

        exp_arg = []
        if experiment and experiment != 'control':
            exp_json = json.dumps({'test': test_name, 'variant': variant_id, 'experiment': experiment})
            exp_arg = ['--experiment', exp_json]

        _trade_size = POSITION_SIZE_USD * (FAVORITES_SIZE_MULT if token.upper() in FAVORITES else 1.0)

        cmd = ([sys.executable, BRAIN_CMD, 'trade', 'add',
                token, cmd_side, str(_trade_size), str(round(cur_price, 6)),
                '--exchange', 'Hyperliquid',
                '--strategy', 'delayed-entry',
                '--paper' if paper else '--real',
                '--sl', str(round(sl, 6)),
                '--target', str(round(tp, 6)),
                '--server', SERVER,
                '--signal', 'delayed-entry',
                '--confidence', str(round(conf, 1)),
                '--leverage', '5']
               + exp_arg)

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            if result.returncode == 0 and 'trade' in result.stdout.lower():
                log(f'  ✅ DELAYED ENTERED: {token} {direction}')
                executed += 1
            else:
                log(f'  ❌ DELAYED FAILED: {result.stderr.strip()[:80]}')
                still_pending.append(entry)  # keep for retry
        except Exception as e:
            log(f'  ❌ DELAYED ERROR: {e}')
            still_pending.append(entry)

    _save_delayed(still_pending)
    if expired > 0 or executed > 0:
        log(f'  Delayed entries: {executed} executed | {expired} expired | {len(still_pending)} still waiting')
    return executed, expired


# ─── Context Gate (Rule-Based + LLM) ─────────────────────────────
# Two-layer gate: rule-based (free, instant) → LLM (quota, 5-10 calls/hr).
# Only fires after ALL other filters pass — last gate before execute_trade.

_CTX_CACHE_FILE = '/dev/shm/hermes-ctx-gate-cache.json'

def _ctx_load_cache():
    """Load persistent LLM cache from tmpfs (shared across pipeline runs)."""
    try:
        with open(_CTX_CACHE_FILE, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def _ctx_save_cache(cache):
    """Save persistent LLM cache to tmpfs."""
    try:
        with open(_CTX_CACHE_FILE, 'w') as f:
            json.dump(cache, f)
    except Exception:
        pass

def _get_recent_prices(token, n=20):
    """Get last N close prices from get_price_history. Returns list of floats or empty."""
    try:
        from signal_schema import get_price_history
        rows = get_price_history(token, lookback_minutes=n)
        return [r[1] for r in rows[-n:]] if rows else []
    except Exception:
        return []

def _ctx_gate_get_speed(token):
    """Get speed percentile — same source as EXEC path (SpeedTracker).
    CEO 2026-08-02: was reading token_speeds DB and mapping is_stale→0 while
    EXEC used SpeedTracker live percentile → 27% vs 0% mismatch / false SKIP."""
    try:
        if speed_tracker_dr is not None:
            spd = speed_tracker_dr.get_token_speed(token)
            if spd is None:
                return None
            # Missing token returns default 50 — treat as unknown, not real speed
            if not speed_tracker_dr.get_all_speeds().get(token.upper()):
                return None
            return spd.get('speed_percentile')
        with sqlite3.connect(RUNTIME_DB) as conn:
            row = conn.execute(
                'SELECT speed_percentile FROM token_speeds WHERE upper(token) = ?',
                (token.upper(),)
            ).fetchone()
            return row[0] if row else None
    except Exception:
        return None

def _ctx_gate_get_zscore(token):
    """Compute z-score from price_history. Returns float or None."""
    try:
        prices = _get_recent_prices(token, 20)
        if not prices or len(prices) < 10:
            return None
        mean = sum(prices) / len(prices)
        variance = sum((p - mean) ** 2 for p in prices) / len(prices)
        std = variance ** 0.5
        if std == 0:
            return None
        return (prices[-1] - mean) / std
    except Exception:
        return None

def _ctx_gate_get_phase(token):
    """Get current market phase from token_speeds. Returns phase string or None."""
    try:
        from tpsl_utils import _get_current_phase
        return _get_current_phase(token)
    except Exception:
        return None

def _ctx_gate_get_momentum(token):
    """Get momentum_score and price_acceleration from speed tracker. Returns dict or None."""
    try:
        from speed_tracker import SpeedTracker
        st = SpeedTracker()
        spd = st.get_token_speed(token)
        if not spd:
            return None
        return {
            'momentum': spd.get('momentum_score', 50),
            'acceleration': spd.get('price_acceleration', 0),
            'wave_phase': spd.get('wave_phase', 'neutral'),
        }
    except Exception:
        return None

def _ctx_gate_get_market_context():
    """Get BTC and ETH z-scores for market context. Returns dict."""
    btc_z = _ctx_gate_get_zscore('BTC')
    eth_z = _ctx_gate_get_zscore('ETH')
    return {'btc_z': btc_z, 'eth_z': eth_z}

def rule_based_context_gate(token, direction, source, sig):
    """
    Free, instant gate. Returns (verdict, data):
      - ('GO', None)
      - ('SKIP', reason)
      - ('AMBIGUOUS', ctx_dict with speed, z_score, phase, momentum, accel, market)
    Note: FLIP was disabled 2026-08-01 — was inverting 31% of trades to wrong direction.
    """
    if not CONTEXT_GATE_ENABLED:
        return ('GO', None, 0)

    speed = _ctx_gate_get_speed(token)
    # Use signal z-score if available (from tl_break signal), otherwise compute from current prices
    z_score = sig.get('z_score') if isinstance(sig, dict) and sig.get('z_score') is not None else _ctx_gate_get_zscore(token)
    # FIX 2026-07-31: Use signal's phase/momentum when available, not speed_tracker
    # Signal metadata has the correct values at signal generation time.
    # Speed_tracker may have different values at execution time, causing wrong flips.
    if isinstance(sig, dict) and sig.get('signal_metadata'):
        try:
            meta = json.loads(sig['signal_metadata']) if isinstance(sig['signal_metadata'], str) else sig['signal_metadata']
            phase = meta.get('wave_phase') or _ctx_gate_get_phase(token)
            mom_data = {
                'momentum': meta.get('momentum_score', 50),
                'acceleration': meta.get('price_acceleration', 0),
                'wave_phase': meta.get('wave_phase', 'neutral'),
            }
        except Exception:
            phase = _ctx_gate_get_phase(token)
            mom_data = _ctx_gate_get_momentum(token)
    else:
        phase = _ctx_gate_get_phase(token)
        mom_data = _ctx_gate_get_momentum(token)
    market = _ctx_gate_get_market_context()

    momentum = mom_data.get('momentum', 50) if mom_data else 50
    accel = (mom_data.get('acceleration') or 0) if mom_data else 0
    wave_phase = mom_data.get('wave_phase', 'neutral') if mom_data else 'neutral'

    # Determine if this is a trend signal (not inv-accel)
    is_inv_accel = 'inv-accel' in (source or '')
    is_trend_signal = not is_inv_accel  # tl_break, accel-300, etc.

    # 1. Speed too low = no wave (surfing: whitewater) — AMBIGUOUS, not SKIP
    if speed is not None and speed < CONTEXT_GATE_SPEED_MIN:
        return ('AMBIGUOUS', f'speed {speed:.0f}% < {CONTEXT_GATE_SPEED_MIN}% (no wave)', 20)

    # 1b. Global signal filters (FIX 2026-07-31) — apply to ALL signals
    # Based on winning trade analysis: speed>50%, momentum>25, RSI 30-70, z neutral
    if SIGNAL_FILTER_ENABLED:
        # Speed filter: penalize when momentum is weak
        # CEO 2026-08-15: NEUTRAL regime override — relaxed speed threshold
        _regime = sig.get('volatility_regime') if isinstance(sig, dict) else None
        _speed_min = SIGNAL_FILTER_NEUTRAL_SPEED_MIN if _regime == 'NEUTRAL' else SIGNAL_FILTER_SPEED_MIN
        if speed is not None and speed < _speed_min:
            return ('AMBIGUOUS', f'speed {speed:.0f}% < {_speed_min:.0f}% (weak momentum, regime={_regime})', 15)

        # Momentum filter: penalize when trend is weak
        if momentum < SIGNAL_FILTER_MOMENTUM_MIN:
            return ('AMBIGUOUS', f'momentum {momentum:.0f} < {SIGNAL_FILTER_MOMENTUM_MIN} (weak trend)', 15)

        # RSI filter: penalize overbought/oversold entries
        rsi = sig.get('rsi_14') if isinstance(sig, dict) else None
        if rsi is not None:
            if direction == 'LONG' and rsi > SIGNAL_FILTER_RSI_MAX:
                return ('AMBIGUOUS', f'RSI {rsi:.1f} > {SIGNAL_FILTER_RSI_MAX} (overbought)', 10)
            if direction == 'SHORT' and rsi < SIGNAL_FILTER_RSI_MIN:
                return ('AMBIGUOUS', f'RSI {rsi:.1f} < {SIGNAL_FILTER_RSI_MIN} (oversold)', 10)

        # Z-score filter: penalize chasing entries (only when speed is low)
        # KEY INSIGHT: Extreme z + high speed = reversal (win), Extreme z + low speed = chasing (lose)
        if z_score is not None:
            _spd_str = f'{speed:.0f}' if speed is not None else '?'
            if direction == 'LONG' and z_score < SIGNAL_FILTER_Z_MIN and (speed is None or speed < SIGNAL_FILTER_SPEED_MIN):
                return ('AMBIGUOUS', f'z={z_score:.2f} < {SIGNAL_FILTER_Z_MIN} + speed={_spd_str}% (chasing downtrend)', 15)
            if direction == 'SHORT' and z_score > SIGNAL_FILTER_Z_MAX and (speed is None or speed < SIGNAL_FILTER_SPEED_MIN):
                return ('AMBIGUOUS', f'z={z_score:.2f} > {SIGNAL_FILTER_Z_MAX} + speed={_spd_str}% (chasing uptrend)', 15)

    # 1c. Z-Score + Acceleration alignment (surfing.md quadrants)
    # Hard block: misaligned direction = low WR (CEO backtested)
    # Aligned: LONG z>0 + accel>0 (76.4%), SHORT z<0 + accel<0 (63.3%)
    # Misaligned: LONG z<0 + accel<0 (24.7%), SHORT z>0 + accel>0 (23.8%)
    if ZSCORE_ACCEL_ENABLED and z_score is not None and accel is not None:
        if direction == 'LONG' and z_score < -ZSCORE_ACCEL_Z_THRESHOLD and accel < -ZSCORE_ACCEL_ACCEL_THRESHOLD:
            return ('SKIP', f'misaligned LONG: z={z_score:.2f} accel={accel:+.4f} (collapsing, wrong for LONG)', 0)
        if direction == 'SHORT' and z_score > ZSCORE_ACCEL_Z_THRESHOLD and accel > ZSCORE_ACCEL_ACCEL_THRESHOLD:
            return ('SKIP', f'misaligned SHORT: z={z_score:.2f} accel={accel:+.4f} (rising, wrong for SHORT)', 0)

    # 2. Clear setup: z + speed both strong → GO (no LLM needed)
    # But only if price history is fresh (< 5 min old)
    # GO conditions: speed >= 70% AND z strongly confirms direction:
    #   LONG + z < -1.0 (price below average = good entry for buying)
    #   SHORT + z > 1.0 (price above average = good entry for selling)
    # FLIP territory (NEVER GO): LONG + z > 1.0, SHORT + z < -1.0 (was 0.5 — too aggressive, normal market noise)
    if speed is not None and speed >= CONTEXT_GATE_SPEED_CONFIRM:
        if z_score is not None:
            # Check if z is in FLIP territory — if so, don't give GO
            in_flip_territory = (
                (direction == 'LONG' and z_score > 1.0) or
                (direction == 'SHORT' and z_score < -1.0)
            )
            if not in_flip_territory:
                # Check if z confirms direction (strong setup)
                z_confirms = (
                    (direction == 'LONG' and z_score < -1.0) or
                    (direction == 'SHORT' and z_score > 1.0)
                )
                if z_confirms:
                    # Strong setup — give GO
                    try:
                        import sqlite3 as _sqlite3
                        from paths import HERMES_DATA
                        _conn = _sqlite3.connect(f'{HERMES_DATA}/signals_hermes.db', timeout=5)
                        _cur = _conn.cursor()
                        _cur.execute("SELECT MAX(timestamp) FROM price_history WHERE token=?", (token,))
                        _row = _cur.fetchone()
                        _conn.close()
                        if _row and _row[0]:
                            import time as _time
                            _age = time.time() - _row[0]
                            if _age > 300:  # >5 min stale
                                return ('AMBIGUOUS', {'speed': speed, 'z_score': z_score, 'phase': phase,
                                                       'momentum': momentum, 'acceleration': accel,
                                                       'wave_phase': wave_phase, 'market': market,
                                                       'stale_price': True}, 0)
                    except Exception:
                        pass  # if we can't check, proceed with GO
                    return ('GO', None, 0)
                # z doesn't confirm (e.g., LONG with z between -0.5 and 0.5)
                # Fall through to LLM gate for ambiguous cases

    # 3. Counter-trend trap: z contradicts direction + low speed
    if z_score is not None and speed is not None:
        if abs(z_score) > CONTEXT_GATE_Z_COUNTER_TREND and speed < 50:
            if (direction == 'LONG' and z_score < -CONTEXT_GATE_Z_COUNTER_TREND) or \
               (direction == 'SHORT' and z_score > CONTEXT_GATE_Z_COUNTER_TREND):
                return ('SKIP', f'counter-trend trap: z={z_score:.2f}, speed={speed:.0f}%', 0)

    # 4. Ranging market + low speed = no clear wave
    if z_score is not None and speed is not None:
        if abs(z_score) < CONTEXT_GATE_Z_RANGING and speed < CONTEXT_GATE_RANGING_SPEED:
            return ('SKIP', f'ranging market: |z|={abs(z_score):.2f} < {CONTEXT_GATE_Z_RANGING}, speed={speed:.0f}%', 0)

    # 5. Wrong phase for signal type
    if phase and source:
        if 'accel-300' in source and 'inverse' not in source:
            if phase in ('exhaustion', 'extreme'):
                return ('SKIP', f'wrong phase: {phase} for accel-300 (wave cresting)', 0)
        if 'inverse' in source or 'inv-accel' in source:
            if phase in ('quiet', 'building'):
                return ('SKIP', f'wrong phase: {phase} for inv-accel (no reversal)', 0)

    # 6. FLIP: DISABLED 2026-08-01 — was flipping 31% of tl_break signals to wrong direction
    # Phase/z-score flips are net negative: signal generator already accounts for these.
    # tl_break_long (4.5% WR) and tl_break_short (5.6% WR) are already terrible;
    # flipping them to the opposite direction makes them worse (0% WR on flipped trades).
    # If re-enabling, gate on HIGH confidence signals only (conf >= 90) to limit damage.

    # 7. Momentum + acceleration cross-check (trend signals only)
    if is_trend_signal and momentum < 25:
        if direction == 'LONG' and accel < -0.005:
            return ('SKIP', f'weak momentum opposing LONG (mom={momentum:.0f}, accel={accel:+.4f})', 0)
        if direction == 'SHORT' and accel > 0.005:
            return ('SKIP', f'weak momentum opposing SHORT (mom={momentum:.0f}, accel={accel:+.4f})', 0)

    # Ambiguous — needs LLM
    ctx = {
        'speed': speed, 'z_score': z_score, 'phase': phase,
        'momentum': momentum, 'acceleration': accel, 'wave_phase': wave_phase,
        'market': market,
    }
    return ('AMBIGUOUS', ctx, 0)

def llm_context_gate(token, direction, source, sig, rule_result, setup=None, heb=None):
    """
    LLM fallback for ambiguous cases. Returns (verdict, reason):
      - ('GO', None): allow trade as-is
      - ('WARN', reason): confidence penalty (soft advisory, trade still executes)
      - ('NAY', reason): hard block (trade rejected)
      - ('FLIP', reason): reverse direction (e.g., LONG→SHORT)
    Rule-based gate is the primary hard blocker.
    Caches results for CONTEXT_GATE_CACHE_TTL seconds.
    """
    if not CONTEXT_GATE_LLM_ENABLED:
        return ('GO', None)  # LLM disabled → allow

    cache_key = f"{token}:{source}:{direction}"
    now = time.time()

    # Check persistent cache (shared across pipeline runs)
    cache = _ctx_load_cache()
    if cache_key in cache:
        cached = cache[cache_key]
        if now - cached['ts'] < CONTEXT_GATE_CACHE_TTL:
            return (cached['verdict'], None)

    # Build prompt with Hebbian recall data + market context
    ctx = rule_result if isinstance(rule_result, dict) else {}
    market = ctx.get('market', {})

    heb_section = ""
    if setup:
        heb_section += f"\nSimilar setup history: {setup.n} trades, WR={setup.win_rate*100:.0f}%, avg PnL={setup.avg_pnl:+.2f}%"
    if heb:
        wr_est, n, weight, concepts = heb[0], heb[1], heb[2], heb[3]
        exit_quality = heb[4] if len(heb) > 4 else None
        combo_parts = heb[5] if len(heb) > 5 else []
        is_token_specific = heb[6] if len(heb) > 6 else False
        wr_pct = wr_est * 100
        heb_section += f"\nHebbian estimate: WR={wr_pct:.0f}% (n={n}, weight={weight:.2f}, {'token-specific' if is_token_specific else 'aggregate'})"
        # Add exit-quality context
        if exit_quality and exit_quality['profit_n'] + exit_quality['sl_n'] >= 3:
            heb_section += f"\nExit quality: profit={exit_quality['profit_n']}T SL={exit_quality['sl_n']}T ratio={exit_quality['ratio']:.1f}"
        # Add combo-part context
        if combo_parts:
            parts_str = ', '.join(f'{p[0]}={p[1]*100:.0f}%' for p in combo_parts)
            heb_section += f"\nCombo parts: {parts_str}"
        # Add concept context for LLM
        if concepts:
            # Group concepts by type for readability
            concept_groups = {}
            for concept, label, cw, cn in concepts:
                if concept not in concept_groups:
                    concept_groups[concept] = {'weight': cw, 'count': cn}
            # Show top concepts by weight
            top_concepts = sorted(concept_groups.items(), key=lambda x: x[1]['weight'], reverse=True)[:8]
            if top_concepts:
                heb_section += "\nHistorical patterns:"
                for concept, data in top_concepts:
                    heb_section += f"\n  - {concept}: weight={data['weight']:.1f}, trades={data['count']}"
    if not heb_section:
        heb_section = "\nNo historical data available for this setup."

    prompt = f"""You are a crypto trading gate. Evaluate this signal and reply ONE of: GO, WARN, NAY, or FLIP.

GO = allow trade as-is (high confidence, z confirms direction)
WARN = caution (reduced confidence, trade still executes)
NAY = block this trade (hard reject — do not enter)
FLIP = reverse direction (e.g., LONG→SHORT or SHORT→LONG)

=== TRADE CANDIDATE ===
Token: {token}
Direction: {direction}
Signal: {source}

=== MARKET STATE ===
Speed: {ctx.get('speed', 'N/A')}%
Z-Score: {ctx.get('z_score', 'N/A')}
Phase: {ctx.get('wave_phase', ctx.get('phase', 'N/A'))}
Momentum: {ctx.get('momentum', 'N/A')}
Acceleration: {ctx.get('acceleration', 'N/A')}

=== MARKET CONTEXT ===
BTC Z-Score: {market.get('btc_z', 'N/A')}
ETH Z-Score: {market.get('eth_z', 'N/A')}
{heb_section}

CRITERIA (be decisive!):

GO (strong confidence):
- Speed > 70% AND z confirms direction (LONG: z < -0.5, SHORT: z > 0.5)
- Clear trend signal with strong momentum

WARN (cautious):
- Speed 20-70% (moderate momentum)
- Z-score is neutral (-0.5 to 0.5)
- Hebbian WR 30-50% with limited data

NAY (hard block):
- Dead hours (03:00-08:00 UTC) for non-inv-accel signals
- Historical WR < 30% with 5+ trades for this setup
- Z-score extreme AND speed low: |z| > 1.5 AND speed < 30
- LONG with z > 1.5 AND speed < 40 (overbought + no momentum)
- SHORT with z < -1.5 AND speed < 40 (oversold + no momentum)

FLIP (reverse direction):
- LONG with z > 0.7 (overbought → flip to SHORT)
- SHORT with z < -0.7 (oversold → flip to LONG)
- Momentum < 25 with acceleration opposing direction

DEFAULT: If uncertain, reply NAY (better to miss a trade than lose money).

Reply only GO, WARN, NAY, or FLIP:"""

    try:
        import subprocess as _sp
        import shutil as _sh
        _oc = _sh.which('opencode') or '/root/.opencode/bin/opencode'
        result = _sp.run(
            [_oc, 'run', prompt, '-m', CONTEXT_GATE_LLM_MODEL],
            capture_output=True, text=True, timeout=CONTEXT_GATE_LLM_TIMEOUT
        )
        response = (result.stdout or '').strip().upper()
        # Parse verdict: GO, WARN, NAY (FLIP disabled 2026-08-01 — was inverting 31% of trades)
        if 'NAY' in response:
            verdict = 'NAY'
        elif 'GO' in response and 'WARN' not in response:
            verdict = 'GO'
        else:
            verdict = 'WARN'  # default to WARN for ambiguous responses

        # Cache it (persistent across pipeline runs)
        cache[cache_key] = {'verdict': verdict, 'ts': now}
        _ctx_save_cache(cache)
        return (verdict, None)

    except Exception as e:
        log(f'  ⚠️ [CTX-GATE] LLM failed for {token}: {e}')
        if CONTEXT_GATE_FAIL_OPEN:
            return ('GO', None)  # fail-open: don't block good setups
        return ('SKIP', 'LLM failed, fail-closed')

class SetupStats(NamedTuple):
    """Historical stats for similar setups. Field names prevent tuple-shape bugs."""
    n: int
    win_rate: float       # 0.0-1.0
    avg_pnl: float        # signed pct

_setup_lookup_cache = {}  # cache_key → SetupStats, expiry_ts

def similar_setup_lookup(token, source, direction, rsi=None, z_tier=None):
    """Query PostgreSQL for past trades with same signal+direction+similar conditions.
    Returns SetupStats(n, win_rate, avg_pnl) or None. Fail-open on error."""
    if not SIMILAR_SETUP_LOOKUP_ENABLED:
        return None
    cache_key = f"{token}:{source}:{direction}:{rsi or ''}:{z_tier or ''}"
    now = time.time()
    cached = _setup_lookup_cache.get(cache_key)
    if cached and now - cached[1] < SIMILAR_SETUP_CACHE_TTL:
        return cached[0]
    try:
        conn = psycopg2.connect(**BRAIN_DB_DICT)
        try:
            c = conn.cursor()
            c.execute("""
                SELECT COUNT(*) AS n,
                       AVG(CASE WHEN pnl_pct > 0 THEN 1.0 ELSE 0.0 END) AS wr,
                       AVG(pnl_pct) AS avg_pnl
                FROM trades
                WHERE close_time IS NOT NULL
                    AND signal = %s AND direction = %s
                    AND (%s IS NULL OR signal_z_score_tier = %s)
                    AND (%s IS NULL OR signal_rsi_14 IS NULL OR signal_rsi_14 BETWEEN %s AND %s)
            """, (source, direction, z_tier, z_tier, rsi,
                  (rsi or 0) - SIMILAR_SETUP_RSI_BAND, (rsi or 100) + SIMILAR_SETUP_RSI_BAND))
            row = c.fetchone()
            n, wr, avg_pnl = row[0], row[1], row[2]
        finally:
            conn.close()
        if n and n >= SIMILAR_SETUP_MIN_SAMPLE:
            stats = SetupStats(n=int(n), win_rate=float(wr), avg_pnl=float(avg_pnl or 0))
            _setup_lookup_cache[cache_key] = (stats, now)
            return stats
    except Exception as e:
        log(f'  [SETUP-RECALL] {token} {source} {direction} lookup failed: {e}')
    return None

_hebbian_cache = {}  # cache_key → (wr, n, weight, concepts, exit_quality, combo_parts, expiry, is_token_specific, token_wr)

# ── Hebbian circuit breaker + audit logging ──────────────────────────────
_GATE_STATS_FILE = '/root/.hermes/data/hebbian_gate_stats.json'

def _load_gate_stats():
    try:
        with open(_GATE_STATS_FILE) as f:
            return json.load(f)
    except Exception:
        return {'auto_decisions': [], 'disabled_until': None}

def _save_gate_stats(stats):
    import tempfile
    fd, tmp = None, None
    try:
        fd, tmp = tempfile.mkstemp(dir='/root/.hermes/data', suffix='.tmp')
        with os.fdopen(fd, 'w') as f:
            fd = None  # fdopen takes ownership
            json.dump(stats, f, indent=2)
        os.replace(tmp, _GATE_STATS_FILE)
        tmp = None  # replace succeeded, nothing to clean up
    except Exception:
        if fd is not None:
            try: os.close(fd)
            except Exception: pass
        if tmp is not None:
            try: os.unlink(tmp)
            except Exception: pass

def _log_auto_decision(token, signal, direction, decision, wr_est, n, conf_adj):
    """Log auto-decision for audit trail."""
    from datetime import datetime, timezone
    stats = _load_gate_stats()
    stats['auto_decisions'].append({
        'ts': datetime.now(timezone.utc).isoformat(),
        'token': token, 'signal': signal, 'direction': direction,
        'decision': decision, 'wr_est': round(wr_est, 3), 'n': n,
        'conf_adj': conf_adj, 'actual': None,
    })
    # Keep last 200 entries
    if len(stats['auto_decisions']) > 200:
        stats['auto_decisions'] = stats['auto_decisions'][-200:]
    _save_gate_stats(stats)

def _check_circuit_breaker():
    """Check if circuit breaker should disable the gate."""
    stats = _load_gate_stats()
    # Check if cooldown is active
    if stats.get('disabled_until'):
        from datetime import datetime as _dt, timezone as _tz
        try:
            disabled_until = _dt.fromisoformat(stats['disabled_until'])
            if _dt.now(_tz) < disabled_until:
                return True  # still disabled
            else:
                stats['disabled_until'] = None
                _save_gate_stats(stats)
        except Exception:
            stats['disabled_until'] = None
            _save_gate_stats(stats)
    # Check accuracy over last N auto-decisions
    recent = [d for d in stats.get('auto_decisions', []) if d.get('actual') is not None]
    if len(recent) >= HEBBIAN_CIRCUIT_BREAKER_N:
        last_n = recent[-HEBBIAN_CIRCUIT_BREAKER_N:]
        wins = sum(1 for d in last_n if d['actual'] == True)
        wr = wins / len(last_n)
        if wr < HEBBIAN_CIRCUIT_BREAKER_WR:
            from datetime import datetime as _dt, timezone as _tz, timedelta
            cooldown = timedelta(seconds=HEBBIAN_CIRCUIT_BREAKER_COOLDOWN_SEC)
            stats['disabled_until'] = (_dt.now(_tz) + cooldown).isoformat()
            _save_gate_stats(stats)
            log(f'  [HEBBIAN-GATE] CIRCUIT BREAKER TRIPPED: WR={wr:.0%} over {len(last_n)} auto-decisions. Disabled for {HEBBIAN_CIRCUIT_BREAKER_COOLDOWN_SEC//3600}h')
            return True
    return False

def hebbian_trade_boost(token, signal):
    """Estimate historical win rate from Hebbian memory for (token, signal) pair.
    Returns (wr, n, weight, concepts, exit_quality, combo_parts, is_token_specific, token_wr) or None.
    Fail-open. 10min cache.
    is_token_specific = True if data is from token↔signal, False if from direction↔signal fallback.
    token_wr = token-level WR estimate or None."""
    from hebbian_engine import HebbianEngine
    cache_key = f"{token}:{signal}"
    now = time.time()
    cached = _hebbian_cache.get(cache_key)
    if cached and now - cached[6] < HEBBIAN_CACHE_TTL:
        if cached[0] is None:
            return None
        return (cached[0], cached[1], cached[2], cached[3], cached[4], cached[5], cached[7], cached[8])
    try:
        engine = HebbianEngine()
        # Try decayed WR first (time-weighted, recent trades count more)
        result = engine.decayed_wr_estimate(token, signal)
        is_token_specific = True
        if not result:
            # Fallback to standard WR estimate
            result = engine.wr_estimate(token, signal)
        if not result:
            # Fallback to direction-agnostic lookup
            direction = 'LONG' if '+' in (signal or '') else 'SHORT' if '-' in (signal or '') else None
            if direction:
                result = engine.decayed_wr_estimate(direction, signal)
                is_token_specific = False
                if not result:
                    result = engine.wr_estimate(direction, signal)
        recall = engine.recall(token, k=20)
        concepts = [(c, l, w, n) for c, l, w, n in recall
                    if l == 'concept' and c not in ('SHORT_BIAS', 'LONG_BIAS', 'NEUTRAL',
                                                     'APPROVED', 'HOT_APPROVED', 'WAIT', 'SKIPPED')]
        exit_quality = engine.exit_quality_score(signal) if signal else None
        combo_parts = engine.combo_part_wr(token, signal) if signal else []
        token_wr = engine.token_overall_wr(token)
    except Exception:
        return None
    if result is None:
        _hebbian_cache[cache_key] = (None, None, None, [], None, None, now, None, None)
        return None
    wr, n, weight = result
    _hebbian_cache[cache_key] = (wr, n, weight, concepts, exit_quality, combo_parts, now, is_token_specific, token_wr)
    return (wr, n, weight, concepts, exit_quality, combo_parts, is_token_specific, token_wr)

def context_gate(token, direction, source, sig):
    """
    Main entry point. Volatility gate → Rule-based → similar setup → LLM.
    Returns (verdict, reason_or_data, penalty):
      - ('GO', None, 0): pass through
      - ('SKIP', reason, 0): hard block (no penalty, trade blocked)
      - ('FLIP', {'new_dir': str, 'reason': str}, 0): flip direction
      - ('WARN', reason, penalty_pts): soft advisory, trade executes with reduced confidence
    """
    if not CONTEXT_GATE_ENABLED:
        return ('GO', None, 0)

    # ── Volatility Gate (surfing analogy) ─────────────────────────────────
    # FLAT (<0.48% ATR): no wave to surf — skip
    # EXTREME (>1.5% ATR): storm — skip
    # NORMAL (0.48-1.0%): sweet spot — standard SL
    # HIGH (1.0-1.5%): big waves — wider SL
    try:
        from volatility_gate import should_trade, get_atr_pct, get_sl_multiplier
        vol_result, vol_regime = should_trade(token, signal=source)
        atr_pct = get_atr_pct(token)
        atr_str = f'{atr_pct:.4f}%' if atr_pct is not None else 'N/A'
        log(f'  [VOL-GATE] {token}: ATR={atr_str} regime={vol_regime}')
        if vol_result == 'SKIP':
            return ('SKIP', f'volatility gate: {vol_regime} (ATR={atr_str})', 0)
        # Store regime in sig for downstream use (SL/TP adjustment)
        if isinstance(sig, dict):
            sig['volatility_regime'] = vol_regime
            sig['sl_multiplier'] = get_sl_multiplier(atr_pct) if atr_pct else 1.0
    except Exception as e:
        log(f'  [VOL-GATE] {token}: error {e} (fail-open)')

    verdict, ctx, _ = rule_based_context_gate(token, direction, source, sig)

    if verdict == 'SKIP':
        return ('SKIP', ctx, 0)
    if verdict == 'FLIP':
        return ('FLIP', ctx, 0)  # ctx = {'new_dir': ..., 'reason': ...}

    # CEO FIX 2026-08-10: similar_setup_lookup runs ALWAYS, even on GO path.
    # Bad historical WR should override strong speed/z-score.
    rsi = sig.get('rsi_14') if isinstance(sig, dict) else None
    z_tier = sig.get('z_score_tier') if isinstance(sig, dict) else None
    setup = similar_setup_lookup(token, source, direction, rsi, z_tier)
    if setup:
        wr_pct = setup.win_rate * 100
        log(f'  [SETUP-RECALL] {token} {source} {direction}: n={setup.n} WR={wr_pct:.0f}%')
        if setup.n >= SIMILAR_SETUP_HARD_BLOCK_MIN_N and wr_pct < SIMILAR_SETUP_HARD_BLOCK_WR:
            return ('SKIP', f'similar setup: n={setup.n} WR={wr_pct:.0f}% < {SIMILAR_SETUP_HARD_BLOCK_WR}% (hard block)', 0)
        if wr_pct < 50 and setup.n >= SIMILAR_SETUP_MIN_SAMPLE:
            penalty = SIMILAR_SETUP_PENALTY_30 if wr_pct < 40 else SIMILAR_SETUP_PENALTY_40
            log(f'  [SETUP-RECALL] {token}: WR={wr_pct:.0f}% → confidence penalty -{penalty} (advisory)')
            return ('WARN', f'similar setup: n={setup.n} WR={wr_pct:.0f}% → -{penalty} confidence', penalty)

    if verdict == 'GO':
        return ('GO', None, 0)

    # Token sentiment (Hebbian Phase 3a — chronic loser filter) — AMBIGUOUS, not SKIP
    if TOKEN_SENTIMENT_ENABLED:
        try:
            from hebbian_engine import HebbianEngine
            _eng = HebbianEngine()
            sentiment = _eng.token_sentiment(token, k=TOKEN_SENTIMENT_K)
            if sentiment != 0.0:
                log(f'  [TOKEN-SENTIMENT] {token}: sentiment={sentiment:.2f}')
                if sentiment <= TOKEN_SENTIMENT_HARD_SKIP_THRESHOLD:
                    return ('AMBIGUOUS', f'token sentiment {sentiment:.2f} <= {TOKEN_SENTIMENT_HARD_SKIP_THRESHOLD} (chronic loser)', 25)
                if sentiment <= TOKEN_SENTIMENT_SKIP_THRESHOLD:
                    return ('AMBIGUOUS', f'token sentiment {sentiment:.2f} <= {TOKEN_SENTIMENT_SKIP_THRESHOLD} (negative history)', 15)
                if sentiment >= TOKEN_SENTIMENT_BOOST_THRESHOLD:
                    log(f'  [TOKEN-SENTIMENT] boost: +{TOKEN_SENTIMENT_BOOST_AMOUNT} confidence (positive sentiment)')
                    return ('WARN', f'token sentiment {sentiment:.2f} >= {TOKEN_SENTIMENT_BOOST_THRESHOLD}', -TOKEN_SENTIMENT_BOOST_AMOUNT)
        except Exception as e:
            log(f'  [TOKEN-SENTIMENT] {token}: error {e} (fail-open)')

    # Hebbian WR estimate (brain.db token ↔ signal weight)
    # Check circuit breaker first
    heb = None
    if HEBBIAN_GATE_ENABLED and _check_circuit_breaker():
        log(f'  [HEBBIAN-GATE] DISABLED (circuit breaker active)')
    else:
        heb = hebbian_trade_boost(token, source)
        if heb:
            wr_est, n, weight, concepts, exit_quality, combo_parts, is_token_specific, token_wr = heb
            wr_pct = wr_est * 100
            data_src = 'token-specific' if is_token_specific else 'direction-agg'
            log(f'  [HEBBIAN] {token} {source}: est WR={wr_pct:.0f}% (n={n}, weight={weight:.2f}, {data_src})')

            # ── Exit-quality enrichment ──────────────────────────────────
            exit_boost = 0
            if exit_quality:
                eq = exit_quality
                if eq['profit_n'] >= 3 and eq['ratio'] > 2.0:
                    exit_boost = HEBBIAN_EXIT_PROFIT_BOOST
                    log(f'  [HEBBIAN] exit-quality: profit dominant (ratio={eq["ratio"]:.1f}) → +{exit_boost}')
                elif eq['sl_n'] >= 3 and eq['ratio'] < 0.5:
                    exit_boost = -HEBBIAN_EXIT_SL_PENALTY
                    log(f'  [HEBBIAN] exit-quality: SL dominant (ratio={eq["ratio"]:.1f}) → {exit_boost}')

            # ── Combo-part enrichment ────────────────────────────────────
            combo_boost = 0
            if combo_parts and len(combo_parts) >= 2:
                all_high = all(cp[1] >= HEBBIAN_BOOST_WR for cp in combo_parts)
                any_low = any(cp[1] <= HEBBIAN_PENALTY_WR for cp in combo_parts if cp[2] >= 3)
                if all_high:
                    combo_boost = HEBBIAN_COMBO_PART_BOOST
                    log(f'  [HEBBIAN] combo-parts: all high WR → +{combo_boost}')
                elif any_low:
                    combo_boost = -HEBBIAN_COMBO_PART_BOOST
                    log(f'  [HEBBIAN] combo-parts: one low WR → {combo_boost}')

            # ── Token overall WR boost ───────────────────────────────────
            token_wr_boost = 0
            if token_wr and token_wr['profit_n'] + token_wr['sl_n'] >= HEBBIAN_TOKEN_WR_MIN_N:
                if token_wr['ratio'] > HEBBIAN_TOKEN_WR_RATIO_HIGH:
                    token_wr_boost = HEBBIAN_TOKEN_WR_BOOST
                    log(f'  [HEBBIAN] token WR: profitable (ratio={token_wr["ratio"]:.1f}) → +{token_wr_boost}')
                elif token_wr['ratio'] < HEBBIAN_TOKEN_WR_RATIO_LOW:
                    token_wr_boost = -HEBBIAN_TOKEN_WR_BOOST
                    log(f'  [HEBBIAN] token WR: losing (ratio={token_wr["ratio"]:.1f}) → {token_wr_boost}')

            # ── Existing boost/penalty logic (soft advisories) ───────────
            if n >= HEBBIAN_BOOST_MIN_N and wr_est >= HEBBIAN_BOOST_WR:
                log(f'  [HEBBIAN] boost: +{HEBBIAN_BOOST_AMOUNT} confidence (high WR history)')
                return ('WARN', f'hebbian boost: est WR={wr_pct:.0f}% (n={n})', -HEBBIAN_BOOST_AMOUNT)
            if n >= HEBBIAN_PENALTY_MIN_N and wr_est <= HEBBIAN_PENALTY_WR:
                log(f'  [HEBBIAN] penalty: -{HEBBIAN_PENALTY_AMOUNT} confidence (low WR history)')
                return ('WARN', f'hebbian penalty: est WR={wr_pct:.0f}% (n={n})', HEBBIAN_PENALTY_AMOUNT)

            # ── Exit-sl auto-reject (regardless of WR) ───────────────────
            if is_token_specific and exit_quality:
                eq = exit_quality
                if eq['sl_n'] >= HEBBIAN_EXIT_SL_AUTO_REJECT_MIN_N and eq['ratio'] < HEBBIAN_EXIT_SL_AUTO_REJECT_RATIO:
                    log(f'  [HEBBIAN-GATE] AUTO-REJECT: exit_sl dominant (ratio={eq["ratio"]:.2f}, sl_n={eq["sl_n"]})')
                    _log_auto_decision(token, source, direction, 'AUTO-REJECT', wr_est, n, exit_boost + combo_boost + token_wr_boost)
                    return ('SKIP', f'hebbian auto-reject: SL dominant (ratio={eq["ratio"]:.2f})', 0)

            # ── Autonomous gate — tiered min-n ────────────────────────────────
            if HEBBIAN_GATE_ENABLED and is_token_specific:
                total_conf_adj = exit_boost + combo_boost + token_wr_boost

                # Path A: tiered min-n
                is_high_conf = (exit_quality and exit_quality['ratio'] > HEBBIAN_HIGH_CONF_EXIT_RATIO and exit_quality['profit_n'] >= 3)
                min_n = HEBBIAN_AUTO_MIN_N_HIGH_CONF if is_high_conf else HEBBIAN_AUTO_MIN_N
                if n >= min_n:
                    if wr_est >= HEBBIAN_AUTO_APPROVE_WR and total_conf_adj >= 0:
                        log(f'  [HEBBIAN-GATE] AUTO-APPROVE (n-based): WR={wr_pct:.0f}% n={n} (min={min_n}) exit={exit_boost} combo={combo_boost} token={token_wr_boost}')
                        _log_auto_decision(token, source, direction, 'AUTO-APPROVE', wr_est, n, total_conf_adj)
                        return ('GO', f'hebbian auto-approve: WR={wr_pct:.0f}% (n={n})', total_conf_adj)
                    if wr_est <= HEBBIAN_AUTO_REJECT_WR and exit_boost <= 0:
                        log(f'  [HEBBIAN-GATE] AUTO-REJECT (n-based): WR={wr_pct:.0f}% n={n} (min={min_n}) exit={exit_boost} combo={combo_boost} token={token_wr_boost}')
                        _log_auto_decision(token, source, direction, 'AUTO-REJECT', wr_est, n, total_conf_adj)
                        return ('SKIP', f'hebbian auto-reject: WR={wr_pct:.0f}% (n={n})', 0)

                # ponytail: composite scoring removed — it bypassed HEBBIAN_AUTO_MIN_N,
                # rubber-stamping n=1-2 trades. Path A (n-based) enforces min_n=5.
                if total_conf_adj != 0:
                    log(f'  [HEBBIAN-GATE] uncertain: WR={wr_pct:.0f}% → adj={total_conf_adj}, escalate to LLM')

    # Still ambiguous → LLM (soft advisory or hard block)
    verdict, reason = llm_context_gate(token, direction, source, sig, ctx, setup=setup, heb=heb)
    if verdict == 'WARN':
        log(f'  [CTX-GATE] {token}: LLM WARN → confidence penalty -{LLM_CONFIDENCE_PENALTY}')
        return ('WARN', f'LLM advisory: {LLM_CONFIDENCE_PENALTY} confidence penalty', LLM_CONFIDENCE_PENALTY)
    if verdict == 'NAY':
        log(f'  [CTX-GATE] {token}: LLM NAY → confidence penalty -{LLM_CONFIDENCE_PENALTY}')
        return ('WARN', f'LLM rejected: {reason or "setup is actively harmful"}', LLM_CONFIDENCE_PENALTY)
    # FLIP disabled 2026-08-01 — LLM FLIP was inverting 31% of trades to wrong direction
    if verdict == 'FLIP':
        log(f'  [CTX-GATE] {token}: LLM FLIP ignored (disabled) → treating as WARN')
        return ('WARN', f'LLM FLIP disabled: {reason or "setup uncertain"}', LLM_CONFIDENCE_PENALTY)
    return (verdict, reason, 0)


# ─── Trade Execution ──────────────────────────────────────────────

def execute_trade(token, direction, price, confidence, source,
                  leverage=10, paper=False, sl_pct=0.02,
                  trailing_activation=TRAILING_ACTIVATION_PCT, trailing_distance=TRAILING_DISTANCE_PCT,
                  trailing_phase2_dist=None,
                  experiment=None, variant_id=None, test_name=None,
                  live_trading=False, flipped=False, regime=None,
                  # ── Signal indicator fields (from hotset at entry) ──
                  signal_z_score=None, signal_rsi_14=None,
                  signal_macd_hist=None, signal_momentum_state=None,
                  signal_z_score_tier=None, signal_decision=None,
                  test_sl_variant=None, test_timing_variant=None,
                  test_trailing_variant=None,
                  signal_metadata=None):  # JSON dict of all signal values for future-proof capture
    """Execute a trade via brain.py. Returns (success, trade_id_or_msg)."""
    cmd_side = direction.lower()  # long or short

    # ── Pump Mode ─────────────────────────────────────────────
    # Spike/pump trades: tight SL/TP, NO trailing. Enter fast, exit fast.
    is_pump = 'pump-' in (source or '')

    # Default values for non-pump trades (avoid UnboundLocalError)
    sl = 0.0
    tp = 0.0
    sl_pct_val = 0.0
    tp_pct_val = 0.0

    if is_pump:
        sl_pct_val = PUMP_SL_PCT    # 1.5% SL
        tp_pct_val = PUMP_TP_PCT    # 2.5% TP
        trailing_activation = 0      # disable trailing
        trailing_distance   = 0
        log(f'  [PUMP MODE] {token} {direction} — SL={PUMP_SL_PCT*100:.1f}% TP={PUMP_TP_PCT*100:.1f}% NO trailing')
    else:
        sl_pct_val = float(sl_pct)  # sl_pct is already a fraction (0.01 = 1%)

    # ── ATR SL/TP ─────────────────────────────────────────────
    # ATR-based SL/TP is handled by position_manager every 1 min.
    # Decider_run passes sl=0, tp=0 to defer to position_manager._collect_atr_updates().
    if is_pump:
        # Pump mode: tight fixed SL/TP, NO trailing. Enter fast, exit fast.
        if direction == 'LONG':
            sl = round(price * (1 - PUMP_SL_PCT), 8)
            tp = round(price * (1 + PUMP_TP_PCT), 8)
        else:
            sl = round(price * (1 + PUMP_SL_PCT), 8)
            tp = round(price * (1 - PUMP_TP_PCT), 8)
    else:
        # Set initial SL/TP at trade open to eliminate the 60s zero-SL window.
        # Use CURRENT market price (not signal price) — signal may be stale.
        from hermes_constants import ATR_SL_MIN_INIT, ATR_TP_MIN
        _live_price = get_current_price(token) or price
        price = _live_price  # use live price for entry, not stale signal price
        if direction == 'LONG':
            sl = round(_live_price * (1 - ATR_SL_MIN_INIT), 8)
            tp = round(_live_price * (1 + ATR_TP_MIN), 8)
        else:
            sl = round(_live_price * (1 + ATR_SL_MIN_INIT), 8)
            tp = round(_live_price * (1 - ATR_TP_MIN), 8)
        sl_pct_val = ATR_SL_MIN_INIT
        tp_pct_val = ATR_TP_MIN
        log(f'  [INIT-SL] {token} {direction} — SL={sl:.6f} ({ATR_SL_MIN_INIT*100:.1f}%) TP={tp:.6f} ({ATR_TP_MIN*100:.1f}%) live_price={_live_price:.6f}')

    # Sanity check: SL must provide real protection (only when sl > 0)
    if sl > 0 and direction == 'LONG' and sl >= price:
        sl = price * 0.99
        log(f'  [WARN] SL sanity check triggered for LONG {token}, reset to 1%')
    elif direction == 'SHORT' and sl <= price:
        sl = price * 1.01
        log(f'  [WARN] SL sanity check triggered for SHORT {token}, reset to 1%')

    # Build experiment JSON for brain.py
    import json as _json
    exp_json = None
    if experiment and variant_id and test_name:
        exp_json = _json.dumps({'experiment': experiment, 'variant_id': variant_id, 'test_name': test_name})

    # --paper when live_trading=False, --real when live_trading=True
    paper_flag = '--paper' if not live_trading else '--real'

    _trade_size = POSITION_SIZE_USD * (FAVORITES_SIZE_MULT if token.upper() in FAVORITES else 1.0)

    cmd = [sys.executable, BRAIN_CMD, 'trade', 'add',
           token, cmd_side, str(_trade_size), str(round(price, 6)),
           '--exchange', 'Hyperliquid',
           '--strategy', f'Hermes-{source}',
           paper_flag,
           '--sl', str(round(sl, 6)),
           '--target', str(round(tp, 6)),
           '--server', SERVER,
           '--signal', source,
           '--confidence', str(round(confidence, 1)),
           '--leverage', str(leverage),
           '--sl-distance', str(sl_pct_val),
           '--trailing-threshold', str(trailing_activation),
           '--trailing-distance', str(trailing_distance)]
    if trailing_phase2_dist is not None:
        cmd += ['--trailing-phase2', str(trailing_phase2_dist)]
    if exp_json:
        cmd += ['--experiment', exp_json]
    if flipped:
        cmd += ['--flipped']
    # ── Signal indicator fields (from hotset at entry) ──
    if signal_z_score is not None:
        cmd += ['--signal-z-score', str(signal_z_score)]
    if signal_rsi_14 is not None:
        cmd += ['--signal-rsi-14', str(signal_rsi_14)]
    if signal_macd_hist is not None:
        cmd += ['--signal-macd-hist', str(signal_macd_hist)]
    if signal_momentum_state is not None:
        cmd += ['--signal-momentum-state', str(signal_momentum_state)]
    if signal_z_score_tier is not None:
        cmd += ['--signal-z-score-tier', str(signal_z_score_tier)]
    if signal_decision is not None:
        cmd += ['--signal-decision', str(signal_decision)]
    if test_sl_variant is not None:
        cmd += ['--test-sl-variant', str(test_sl_variant)]
    if test_timing_variant is not None:
        cmd += ['--test-timing-variant', str(test_timing_variant)]
    if test_trailing_variant is not None:
        cmd += ['--test-trailing-variant', str(test_trailing_variant)]
    if signal_metadata is not None:
        import json as _json
        cmd += ['--signal-metadata-json', _json.dumps(signal_metadata)]
    if regime is not None:
        cmd += ['--regime', str(regime)]

    # ── Duplicate-entry guard ───────────────────────────────────────────────
    # FIX (2026-04-14): If there's already an open trade for this token+direction
    # (in DB or on HL), skip. Prevents the system from opening multiple positions
    # on the same token and diluting capital across entries.
    from psycopg2 import connect as pg_connect
    try:
        _dup_conn = pg_connect(host='/var/run/postgresql', database='brain', user='postgres')
        _dup_cur = _dup_conn.cursor()
        _dup_cur.execute(
            "SELECT id, pnl_pct FROM trades WHERE server='Hermes' AND token=%s AND direction=%s AND status='open' LIMIT 1",
            (token.upper(), direction.upper()))
        _dup_row = _dup_cur.fetchone()
        _dup_cur.close(); _dup_conn.close()
        if _dup_row:
            dup_id, dup_pnl = _dup_row
            log(f'  ⛔ DUPLICATE ENTRY BLOCKED in PostgreSQL: {token} {direction} already open (#{dup_id}, pnl={float(dup_pnl or 0):.3f}%) — skipping')
            return False, f'duplicate_entry_blocked token={token} direction={direction} existing_id={dup_id}'
        else:
            log(f'  ✔ PostgreSQL duplicate check passed: no open trade for {token} {direction}')
    except Exception as dup_err:
        log(f'  [WARN] Duplicate-entry guard DB check failed for {token}: {dup_err}')
        # Don't block on DB errors — proceed with the trade

    try:
        log(f'  [brain.py] EXEC: {" ".join(cmd[:8])}... [{paper_flag}]')
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        log(f'  [brain.py] RC={result.returncode} stdout={result.stdout[:200] if result.stdout else "(empty)"}')
        if result.returncode == 0:
            import re
            # Bug-14 fix: use regex instead of fragile substring split.
            # brain.py outputs "✅ trade #123" on success, "trade #None" on rejection.
            trade_match = re.search(r'trade\s*#\s*(\S+)', result.stdout, re.IGNORECASE)
            if trade_match:
                tid = trade_match.group(1)
                if tid == 'none':
                    return False, f'brain.py rejected: conf-1s or blacklist blocked (output: {result.stdout.strip()[:80]})'
                # FIX (2026-05-19): Only mark signal EXECUTED after brain.py actually
                # confirmed the DB INSERT succeeded. brain.py prints "✅ trade #N"
                # to stdout on success. If brain.py exits with RC=0 but no 'trade #'
                # in stdout (e.g. INSERT failed silently), treat as failure — do NOT
                # mark signal EXECUTED, let decider_run retry next cycle.
                # MARKER: Write token to recently-opened file so guardian skips orphan creation
                try:
                    _marker_path = os.path.join(HERMES_DATA, 'guardian_recently_opened.json')
                    import json as _j
                    _marker = {}
                    if os.path.exists(_marker_path):
                        _marker = json.loads(open(_marker_path).read())
                    _marker[token.upper()] = time.time()
                    # Prune entries older than 60s
                    _marker = {k: v for k, v in _marker.items() if time.time() - v < 60}
                    with open(_marker_path, 'w') as _f:
                        json.dump(_marker, _f)
                except Exception:
                    pass  # non-fatal
                return True, f'trade #{tid}'
            # RC=0 but no 'trade #' found in stdout — DB INSERT may have failed silently.
            # Do NOT mark signal EXECUTED — return failure so decider_run retries.
            log(f'  [brain.py] ⚠️ RC=0 but no trade ID in stdout — treating as failure. stdout={result.stdout[:100]}')
            return False, f'brain.py RC=0 but no trade ID in stdout'
        else:
            log(f'  [brain.py] ❌ FAILED: stderr={result.stderr.strip()[:200] if result.stderr else "(empty)"}')
            return False, result.stderr.strip()[:80]
    except Exception as e:
        return False, str(e)[:80]


# ─── Hot-Set Auto-Approver (runs every minute in decider-run) ─────
# Per-token failure tracking for back-to-back cooldown
_HOTSET_FAILURE_FILE = HOTSET_FAILURES_FILE

# Rate limit: max 3 new hot-set approvals per minute (NEW RULE)
_HOTSET_APPROVAL_RATE_FILE = HOTSET_APPROVAL_FILE

def _get_hotset_approval_rate() -> tuple:
    """Return (count, window_start_ts). Resets if window expired (>60s)."""
    try:
        if os.path.exists(_HOTSET_APPROVAL_RATE_FILE):
            with open(_HOTSET_APPROVAL_RATE_FILE) as f:
                data = json.load(f)
        else:
            return 0, 0
        count = data.get('count', 0)
        window_start = data.get('window_start', 0)
        now = time.time()
        if now - window_start > 60:
            _increment_hotset_approval_rate(0, now)  # reset to disk
            return 0, now
        return count, window_start
    except Exception:
        return 0, time.time()

def _increment_hotset_approval_rate(count: int, window_start: float):
    """Save updated approval rate counter."""
    try:
        with FileLock('hotset_approval_rate'):
            with open(_HOTSET_APPROVAL_RATE_FILE, 'w') as f:
                json.dump({'count': count, 'window_start': window_start}, f)
    except Exception:
        pass

def _load_hotset_failures():
    """Load per-direction failure counts. {TOKEN: {'LONG': {'count': N, 'last': ts}, 'SHORT': {...}}}"""
    try:
        with open(_HOTSET_FAILURE_FILE) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def _save_hotset_failures(data):
    try:
        with FileLock('hotset_failures'):
            try:
                with open(_HOTSET_FAILURE_FILE) as f:
                    existing = json.load(f)
            except (FileNotFoundError, json.JSONDecodeError):
                existing = {}
            existing.update(data)
            with open(_HOTSET_FAILURE_FILE, 'w') as f:
                json.dump(existing, f)
    except Exception as e:
        print(f"Save hotset failures error: {e}")

def _check_hotset_cooldown(token: str, direction: str, failures: dict) -> tuple:
    """
    Returns (blocked: bool, reason: str) for back-to-back failure cooldown.

    Rule: If 2+ same-direction trades failed recently, block that direction for 1hr.
    Only allow opposite-direction trades from hot-set during cooldown.
    Resets failure count after cooldown expires so tokens aren't permanently blocked.
    """
    token = token.upper()
    now = time.time()
    # Cooldown: 1 hour = 3600 seconds
    COOLDOWN_SECS = 3600
    
    token_failures = failures.get(token, {})
    dir_failures = token_failures.get(direction, {})
    opp_direction = 'SHORT' if direction == 'LONG' else 'LONG'
    opp_failures = token_failures.get(opp_direction, {})
    
    # Check if this direction is in cooldown (2+ failures within 1hr)
    dir_count = dir_failures.get('count', 0)
    dir_last = dir_failures.get('last', 0)
    if dir_count >= 2 and (now - dir_last) < COOLDOWN_SECS:
        remaining = int(COOLDOWN_SECS - (now - dir_last))
        return True, f'{direction} in cooldown ({remaining}s left, {dir_count} failures)'
    
    # Reset failure count after cooldown expires
    if dir_count >= 2 and (now - dir_last) >= COOLDOWN_SECS:
        dir_failures['count'] = 0
        dir_failures['last'] = 0
        failures[token][direction] = dir_failures
        _save_hotset_failures(failures)
    
    # Check if opposite direction has failures (to allow opposite signals through)
    opp_count = opp_failures.get('count', 0)
    opp_last = opp_failures.get('last', 0)
    if opp_count >= 2 and (now - opp_last) < COOLDOWN_SECS:
        return False, f'opposite {opp_direction} in cooldown ({opp_count} failures) — allowing {direction}'
    
    return False, ''

def _run_hot_set():
    """
    READ-ONLY hot-set enforcer (defunct approval logic — signal_compactor.py is the sole
    APPROVAL authority as of 2026-04-16).
    
    This function runs every 1 min via decider_run.main() but is now READ-ONLY.
    It enforces hot-set eligibility (blacklist, cooldown, position, overextended checks)
    against tokens in hotset.json, but NEVER writes APPROVED to the DB.
    
    decider_run.main() picks the best APPROVED signals for execution using
    the survival_rounds + confidence ranking from signal_compactor's output.
    
    If hotset.json is stale (>20 min old), all tokens are blocked — decider_run
    will not execute any trades until the next compaction cycle.
    """
    import sqlite3, os, time as _time, json as _json

    SIGNALS_DB = RUNTIME_DB
    if not os.path.exists(SIGNALS_DB):
        return 0

    conn = sqlite3.connect(SIGNALS_DB)
    c = conn.cursor()
    now_str = time.strftime('%Y-%m-%d %H:%M:%S')
    approved_count = 0

    # ── HOT-SET DISCIPLINE: Read canonical hot-set from JSON ─────────────────
    # hotset.json is written by signal_compactor.py after each compaction (every 1 min).
    # It is the SOLE source of truth for what tokens are in the hot-set.
    hotset_file = HOTSET_FILE
    if not os.path.exists(hotset_file):
        log('  🧊 [HOT-SET] hotset.json missing — signal_compactor may not have run yet')
        conn.close()
        return 0

    try:
        with FileLock('hotset_json'):
            with open(hotset_file) as f:
                hotset_data = _json.load(f)
    except Exception as e:
        log(f'  🧊 [HOT-SET] failed to read hotset.json: {e}')
        conn.close()
        return 0

    hotset = hotset_data.get('hotset', [])
    if not hotset:
        log('  🧊 [HOT-SET] hotset.json is empty — no signals survived compaction')
        conn.close()
        return 0

    hotset_ts = hotset_data.get('timestamp', 0)
    age = time.time() - hotset_ts
    # signal_compactor runs every 1 min, so hotset should be <1 min old normally.
    # 20 min threshold accounts for pipeline delays if signal_compactor is slow
    # or temporarily paused. If hotset is older than 20 min, something is wrong.
    if age > 1200:
        log(f'  🧊 [HOT-SET] hotset.json stale ({age/60:.1f}m > 20m) — blocking new approvals')
        conn.close()
        return 0

    log(f'  🔥 [HOT-SET] {len(hotset)} tokens in hot-set (age={age:.0f}s)')

    # NEW RULE (2026-04-05): max 3 new approvals per minute — prevent flooding
    rate_count, rate_window = _get_hotset_approval_rate()
    if rate_count >= 3:
        log(f'  🚫 [HOT-SET] Rate limit: 3 approvals already this minute — skipping')
        conn.close()
        return 0
    log(f'  ⚡ [HOT-SET] Approval rate: {rate_count}/3 this minute')

    try:
        # Load hot-set failure tracking
        failures = _load_hotset_failures()

        # SPEED FEATURE: update speed tracker once per hot-set run (<2s)
        if speed_tracker_dr is not None:
            speed_tracker_dr.update()

        # ── HOT-SET ITERATION ORDER: survival rounds first ────────────────────────
        # Tokens that survived more compaction cycles have proven themselves against
        # market volatility. Approve them FIRST so rate limits don't block veterans.
        # Secondary sort: confidence desc (proven quality)
        hotset_sorted = sorted(hotset,
            key=lambda s: (-s.get('survival_round', 0), -s.get('confidence', 0)))
        _order = [f"{s['token']}(r{s.get('survival_round', 0)})" for s in hotset_sorted[:10]]
        log(f'  🔥 [HOT-SET] iteration order: {_order}...')

        # Iterate over canonical hot-set from JSON (SOLE source of truth)
        for hot_sig in hotset_sorted:
            token = hot_sig.get('token', '').upper()
            direction = hot_sig.get('direction', '').upper()
            rounds = hot_sig.get('survival_round', 0)  # use survival_round for iteration priority
            z_score = hot_sig.get('z_score', 0.0) or 0.0

            if not token or not direction:
                continue

            # SAFETY: blacklist filter (defense-in-depth — hotset.json should already be clean)
            if direction == 'SHORT' and token in SHORT_BLACKLIST:
                log(f'  🚫 [HOT-SET] {token} SHORT BLOCKED — in SHORT_BLACKLIST')
                continue
            if direction == 'LONG' and token in LONG_BLACKLIST:
                log(f'  🚫 [HOT-SET] {token} LONG BLOCKED — in LONG_BLACKLIST')
                continue

            # Defense-in-depth. is_solana_only tokens can't be traded
            # on Hyperliquid. decider-run is the final gate.
            if is_solana_only(token):
                log(f'  🚫 [HOT-SET] {token} BLOCKED — Solana-only (not on Hyperliquid)')
                continue

            # Back-to-back failure cooldown check (2+ failures in 1hr → block for 1hr)
            blocked, reason = _check_hotset_cooldown(token, direction, failures)
            if blocked:
                log(f'  🚫 [HOT-SET] {token} {direction} BLOCKED — {reason}')
                continue

            if is_position_open(token) or get_position_count() >= MAX_POS:
                continue

            # Check: is this token+direction already APPROVED (don't double-approve)?
            c.execute("""
                SELECT 1 FROM signals
                WHERE token=? AND direction=? AND decision='APPROVED' AND executed=0
                LIMIT 1
            """, (token, direction))
            if c.fetchone():
                continue

            # Find best PENDING signal for this token+direction
            c.execute("""
                SELECT id, signal_type, source, confidence
                FROM signals
                WHERE token=? AND direction=? AND decision IN ('PENDING','WAIT') AND executed=0
                ORDER BY CASE WHEN signal_type='confluence' THEN 0 ELSE 1 END, confidence DESC
                LIMIT 1
            """, (token, direction))
            best = c.fetchone()
            if not best:
                continue

            sig_id, sig_type, sig_src, sig_conf = best
            should_approve, reason = False, ''
            reason_suffix = ''

            # ── ZSCORE-PUMP INTEGRITY GATE ─────────────────────────────────────
            # If zscore-pump appears in sig_src but z_score is effectively 0 or None,
            # the zscore-pump signal was either rejected or got wiped by a merge bug.
            # Treat this as RS-only — apply a confidence penalty. If it drops below
            # the approval threshold, block the trade.
            # (This is the second line of defense; signal_schema.py COALESCE fix is first.)
            if 'zscore-pump' in sig_src and abs(z_score) < 0.1:
                conf_penalty = 12
                sig_conf -= conf_penalty
                log(f'  📭 [ZSCORE-GATE] {token} {direction}: zscore-pump in source '
                    f'but z={z_score:.3f} → penalty {conf_penalty}pt (conf {sig_conf+conf_penalty:.0f}%→{sig_conf:.0f}%)')
                if sig_conf < 55:
                    log(f'  🚫 [ZSCORE-GATE] {token} {direction} BLOCKED: zscore-pump '
                        f'failed/invalid (effective conf={sig_conf:.0f}% < 55)')
                    _record_hotset_failure(token, direction, failures)
                    continue

            # ── RS TOUCH COUNT GATE (FIX 3, 2026-05-21) ─────────────────────────
            # Parse touch count from sig_src (format: rs-s<N> or rs-r<N>)
            # Low-touch levels (weak support) correlate with losing trades.
            # Apply penalty or block accordingly.
            import re
            touch_match = re.search(r'rs-[sr](\d+)', sig_src or '')
            if touch_match:
                rs_touches = int(touch_match.group(1))
                # Hard cap: levels touched too many times are exhausted/trampled — block at decider
                if RS_TOUCH_HARD_CAP and rs_touches > RS_TOUCH_HARD_CAP:
                    log(f'  🚫 [TOUCH-CAP] {token} {direction}: rs_touches={rs_touches} > {RS_TOUCH_HARD_CAP} '
                        f'→ blocked (level is exhausted/trampled)')
                    _record_hotset_failure(token, direction, failures)
                    continue
                # Z-score bonus: strong momentum (|z| > threshold) compensates for weaker level
                min_touches = RS_DECIDER_ZBONUS_TOUCHES if abs(z_score) >= RS_DECIDER_ZBONUS_ZSCORE else RS_DECIDER_MIN_TOUCHES
                if rs_touches < min_touches:
                    sig_conf -= RS_DECIDER_CONF_PENALTY
                    log(f'  📉 [TOUCH-GATE] {token} {direction}: rs_touches={rs_touches} < {min_touches} '
                        f'→ -{RS_DECIDER_CONF_PENALTY}pt penalty (conf {sig_conf+RS_DECIDER_CONF_PENALTY:.0f}%→{sig_conf:.0f}%)')
                    if sig_conf < RS_DECIDER_CONF_FLOOR:
                        log(f'  🚫 [TOUCH-GATE] {token} {direction} BLOCKED: weak level '
                            f'(touches={rs_touches}, effective conf={sig_conf:.0f}% < {RS_DECIDER_CONF_FLOOR})')
                        _record_hotset_failure(token, direction, failures)
                        continue

            # ── WAVE-AWARENESS FILTER (SPEED FEATURE, 2026-04-03) ─────────────
            # Entry philosophy:
            #   accelerating + LONG  → ride the wave up (mild boost)
            #   decelerating + SHORT → ride the reversal down (mild boost)
            #   bottoming   + LONG  → BEST: catching the reversal bounce
            #   falling     + SHORT → BEST: continuing momentum
            #   counter to wave phase → hard to enter (threshold goes up)
            #   overextended → BLOCK: wave has peaked, reversal is imminent
            #
            # Use hotset.json data if available (enriched at compaction time),
            # fall back to speed_tracker_dr for runtime freshness.
            _wave = hot_sig.get('wave_phase', 'neutral')
            _overext = hot_sig.get('is_overextended', False)
            _momentum = hot_sig.get('momentum_score', 50.0)
            _vel = hot_sig.get('price_velocity_5m', 0.0)
            _speed_pctl = hot_sig.get('speed_percentile', 50.0)
            if _wave == 'neutral' and speed_tracker_dr is not None:
                spd = speed_tracker_dr.get_token_speed(token)
                if spd:
                    _wave = spd.get('wave_phase', 'neutral')
                    _overext = spd.get('is_overextended', False)
                    _momentum = spd.get('momentum_score', 50.0)
                    _vel = spd.get('price_velocity_5m', 0.0)
                    _speed_pctl = spd.get('speed_percentile', 50.0)

            # Regime from hotset.json (enriched by signal_compactor at compaction time).
            # This avoids expensive get_regime() calls per token per cycle.
            _regime = hot_sig.get('regime', 'NEUTRAL')
            _regime_conf = hot_sig.get('regime_conf', 0)

            # BLOCK overextended tokens: velocity has moved too far from the 15m
            # baseline. Example: vel_5m > +3% means price ripped up too fast — reversal
            # is more likely than continuation. Entering here is catching the top.
            # Exception: bottoming + LONG is always allowed (the bounce IS the reversal).
            if _overext and not (_wave == 'bottoming' and direction == 'LONG'):
                log(f'  🌊 [HOT-SET] {token} {direction} BLOCKED: overextended '
                    f'(vel={_vel:+.2f}%, phase={_wave})')
                _record_hotset_failure(token, direction, failures)
                continue

            # ── MOMENTUM EXHAUSTION FILTER ────────────────────────────────────────
            # If price has already moved >0.5% in 30m, don't enter — catching the top.
            # This catches cases where overextended (3% threshold) doesn't trigger
            # but price has still run too far. Example: SKR +0.8% in 1hr → bad entry.
            # Exception: bottoming + LONG or falling + SHORT (the move IS the signal).
            _chg_30m = hot_sig.get('price_change_30m', 0.0) or 0.0
            if abs(_chg_30m) > MOMENTUM_EXHAUSTION_THRESHOLD:
                if direction == 'LONG' and _chg_30m > 0:
                    log(f'  ⚡ [HOT-SET] {token} {direction} BLOCKED: momentum exhausted '
                        f'(30m move={_chg_30m:+.2f}% > +{MOMENTUM_EXHAUSTION_THRESHOLD}%)')
                    _record_hotset_failure(token, direction, failures)
                    continue
                elif direction == 'SHORT' and _chg_30m < 0:
                    log(f'  ⚡ [HOT-SET] {token} {direction} BLOCKED: momentum exhausted '
                        f'(30m move={_chg_30m:+.2f}% < -{MOMENTUM_EXHAUSTION_THRESHOLD}%)')
                    _record_hotset_failure(token, direction, failures)
                    continue

            # Compute direction-wave alignment multiplier (affects threshold)
            # > 1.0 = easier entry, < 1.0 = harder entry
            ALIGN_BOOST   = 1.15   # bottoming+direction, accelerating+direction
            NEUTRAL_BOOST = 1.00   # no wave conviction
            COUNTER_PENALTY = 0.88  # counter to wave phase — be patient

            if _wave == 'bottoming' and direction == 'LONG':
                wave_mult = ALIGN_BOOST
                wave_tag = f'🌱 bottoming@{_momentum:.0f}'
            elif _wave == 'accelerating' and direction == 'LONG':
                wave_mult = 1.10
                wave_tag = f'⬆️ accelerating@{_vel:+.2f}%'
            elif _wave == 'decelerating' and direction == 'SHORT':
                wave_mult = ALIGN_BOOST
                wave_tag = f'⬇️ decelerating@{_vel:+.2f}%'
            elif _wave == 'falling' and direction == 'SHORT':
                wave_mult = 1.10
                wave_tag = f'🔻 falling@{_vel:+.2f}%'
            elif _wave in ('accelerating', 'decelerating') and direction == 'SHORT':
                wave_mult = COUNTER_PENALTY
                wave_tag = f'⬆️ counter@{_vel:+.2f}%'
            elif _wave in ('accelerating', 'decelerating') and direction == 'LONG':
                wave_mult = COUNTER_PENALTY
                wave_tag = f'⬇️ counter@{_vel:+.2f}%'
            elif _wave == 'bottoming' and direction == 'SHORT':
                wave_mult = 0.70  # very hard — catching a falling knife
                wave_tag = f'🌱 counter@{_momentum:.0f}'
            elif _wave == 'falling' and direction == 'LONG':
                wave_mult = 0.70  # very hard — fighting strong down momentum
                wave_tag = f'🔻 counter@{_vel:+.2f}%'
            else:
                wave_mult = NEUTRAL_BOOST
                wave_tag = f'~ neutral@{_momentum:.0f}'

            # SPEED FEATURE: add speed_percentile contribution to effective confidence.
            # Formula: speed_factor = (speed_pctl - 50) / 100 → pctl 100 = +0.50, pctl 0 = -0.50
            # Speed pts = speed_factor × SPEED_WEIGHT × sig_conf
            # pctl 100: +0.50 × 0.15 × 80 = +6.0 pts boost
            # pctl 0:   -0.50 × 0.15 × 80 = -6.0 pts penalty
            # pctl 50:   0.0 × 0.15 × 80 = 0 pts (neutral)
            speed_factor = (_speed_pctl - 50.0) / 100.0
            speed_pts = speed_factor * SPEED_WEIGHT * float(sig_conf)
            speed_tag = f' spd@{_speed_pctl:.0f}({speed_pts:+.1f})'

            effective_conf = float(sig_conf) * wave_mult + speed_pts
            confidence = effective_conf  # BUG FIX (2026-04-10): was never initialized; penalties now apply to this
            reason_suffix = f'+{wave_tag}{speed_tag}'

            # ── COUNTER-TREND TRAP FILTER ────────────────────────────────────
            # If the token's own z-score contradicts the direction AND we're in
            # the corresponding regime → PENALIZE (not block). Strong signals survive.
            trap_penalty, trap_reason = _check_counter_trend_trap(token, direction, _regime, _regime_conf)
            if trap_penalty > 0:
                confidence -= trap_penalty
                if confidence < 55:
                    log(f'  🧊 [HOT-SET] {token} {direction} BLOCKED: {trap_reason} '
                        f'(counter-trend trap penalty={trap_penalty}, conf below threshold)')
                    _record_hotset_failure(token, direction, failures)
                    continue
                log(f'  🧊 [HOT-SET] {token} {direction} penalized {trap_penalty}pts: {trap_reason} (conf now {confidence:.0f}%)')

            # ── REGIME ESCALATION / DE-ESCALATION PROTOCOL ──────────────────────────
            #
            # Counter-regime signals are NEVER hard-blocked. They earn their place
            # through survival. The gradient does all the work:
            #
            #   • Regime penalty = regime_conf × 0.4, capped at 30 pts
            #   • Escalation: +survival_rounds × 2 pts of penalty forgiveness
            #     (each compaction round survived = proven against regime headwinds)
            #   • Effective_conf = base_conf - penalty + escalation_bonus
            #
            # GRADUAL FADE: As regime_conf rises, penalty grows proportionally.
            # Counter-regime signals naturally sink in the execution order.
            # GRACEFUL ENTRY: New counter-regime signals enter with their base conf
            # minus penalty. If regime is weak (conf < 60), penalty is small (≤24pts).
            # Regime check: counter-trend signals are allowed but de-escalated.
            # Both directions can coexist when the regime is unclear.
            #
            # Regime from hotset.json (enriched by signal_compactor at compaction time).
            # Per-coin regime was looked up once at compaction time — no per-token
            # get_regime() calls needed here.
            _regime = hot_sig.get('regime', 'NEUTRAL')
            _regime_conf = hot_sig.get('regime_conf', 0)
            _survival_rounds = hot_sig.get('survival_round', hot_sig.get('rounds', 1))
            if _regime not in ('NEUTRAL', '') and _regime_conf > 50:
                if (_regime in ('LONG_BIAS', 'LONG') and direction == 'SHORT') or \
                   (_regime in ('SHORT_BIAS', 'SHORT') and direction == 'LONG'):
                    # Base penalty: scales with regime strength, max 30 pts
                    penalty = min(int(_regime_conf * 0.4), 30)
                    # Escalation bonus: each survival round partially forgives penalty
                    # A signal that's survived 3 rounds against a 95% regime has proven
                    # it can hold — reward that with +6 pts back
                    escalation = min(_survival_rounds * 2, 10)
                    effective_penalty = max(penalty - escalation, 0)
                    confidence -= effective_penalty
                    if effective_penalty > 0:
                        log(f'  🧊 [REGIME] {token} {direction}: {penalty}pt penalty → -{escalation}pt survival bonus = {effective_penalty}net (conf {hot_sig["confidence"]:.0f}%→{confidence:.0f}%, regime={_regime} {_regime_conf:.0f}%, rounds={_survival_rounds})')
            # ── NEUTRAL MARKET PENALTY ─────────────────────────────────────────────
            # No regime conviction = no market edge. Apply a mild flat penalty
            # to ensure only the strongest signals (high base conf + good wave/speed)
            # survive. Milder than counter-regime penalty (max 30pt) since the
            # compactor already applied 0.5x reg_mult at scoring stage.
            elif _regime == 'NEUTRAL':
                neutral_penalty = 10  # flat 10 pts — enough to filter weak entries
                # Survival round forgiveness: each round proves the signal holds in
                # directionless market, reduce penalty by 2 pts (cap at 6)
                neutral_escalation = min(_survival_rounds * 2, 6)
                effective_neutral = max(neutral_penalty - neutral_escalation, 0)
                confidence -= effective_neutral
                if effective_neutral > 0:
                    log(f'  🌐 [NEUTRAL] {token} {direction}: -{neutral_penalty}pt → -{neutral_escalation}pt survival = {effective_neutral}net (conf {hot_sig["confidence"]:.0f}%→{confidence:.0f}%)')

            # ── TOKEN-LEVEL REGIME CHECK (z_score_tier) ──────────────────
            # z_direction = 'rising' = local bottom → LONG ideal, SHORT penalized
            # z_direction = 'falling' = local top → SHORT ideal, LONG penalized
            # Neutral zone → let market regime decide (no penalty here)
            _z_tier = (hot_sig.get('z_score_tier') or '').lower()
            _z = hot_sig.get('z_score', 0.0)
            if _z_tier and _z is not None:
                if _z_tier == 'rising' and direction == 'LONG':
                    pass  # ideal — no penalty
                elif _z_tier == 'falling' and direction == 'SHORT':
                    pass  # ideal — no penalty
                elif _z_tier == 'neutral':
                    pass  # neutral zone — let market regime handle it
                elif _z_tier == 'rising' and direction == 'SHORT':
                    # Price at local bottom but SHORT direction — PENALIZE
                    # Graceful de-escalation: penalty is applied, signal fades naturally
                    if _momentum not in ('bottoming', 'neutral'):
                        extra_penalty = 20
                        escalation = min(_survival_rounds * 2, 10)
                        effective_extra = max(extra_penalty - escalation, 0)
                        confidence -= effective_extra
                        log(f'  📍 [Z-SCORE] {token} {direction}: {extra_penalty}pt z-penalty → -{escalation}pt survival bonus = {effective_extra}net (conf now {confidence:.0f}%, tier={_z_tier}, momentum={_momentum})')
                elif _z_tier == 'falling' and direction == 'LONG':
                    # Price at local top but LONG direction — PENALIZE
                    # Graceful de-escalation: penalty is applied, signal fades naturally
                    if _momentum != 'bottoming':
                        extra_penalty = 20
                        escalation = min(_survival_rounds * 2, 10)
                        effective_extra = max(extra_penalty - escalation, 0)
                        confidence -= effective_extra
                        log(f'  📍 [Z-SCORE] {token} {direction}: {extra_penalty}pt z-penalty → -{escalation}pt survival bonus = {effective_extra}net (conf now {confidence:.0f}%, tier={_z_tier}, momentum={_momentum})')

            # ── SINGLE-SOURCE hzscore FILTER ────────────────────────────────────
            # hzscore is combo-only, never solo. Must have pct-hermes (or vel-hermes)
            # merged to pass. source='hzscore' = bare hzscore, no confluence → block.
            if sig_src == 'hzscore':
                log(f'  🚫 [HOT-SET] {token} {direction} BLOCKED: hzscore (combo-only, no confluence)')
                _record_hotset_failure(token, direction, failures)
                continue

            # APPROVAL IS NOW THE SOLE RESPONSIBILITY OF signal_compactor.py (every 5 min).
            # _run_hot_set() is READ-ONLY here — it enforces hot-set eligibility
            # (blacklist, cooldown, position checks) but never writes APPROVED.
            # decider_run.main() picks the best APPROVED signals for execution
            # based on survival rounds + confidence, using the ranking step below.
    except Exception as e:
        import traceback; traceback.print_exc()
        log(f'HOT-SET error: {e}')
    finally:
        conn.close()

    # READ-ONLY: never writes APPROVED — signal_compactor.py is sole approval authority.
    return 0

def _record_hotset_failure(token: str, direction: str, failures: dict):
    """Record a failed trade for back-to-back cooldown tracking."""
    now = time.time()
    if token not in failures:
        failures[token] = {'LONG': {'count': 0, 'last': 0}, 'SHORT': {'count': 0, 'last': 0}}
    dir_data = failures[token].setdefault(direction, {'count': 0, 'last': 0})
    dir_data['count'] = dir_data.get('count', 0) + 1
    dir_data['last'] = now
    _save_hotset_failures(failures)


def _get_token_zscore(token: str) -> float:
    """
    Get z-score for a token from signal_gen's zscore computation.
    Returns 0.0 if unavailable.
    """
    try:
        from signal_gen import get_tf_zscores
        zscores = get_tf_zscores(token)
        if zscores:
            # Use the 1h z-score as the primary; fall back to shortest available
            for tf in ('1h', '15m', '5m', '4h'):
                if tf in zscores:
                    z, _ = zscores[tf]
                    return z if z is not None else 0.0
    except Exception:
        pass
    return 0.0


def _check_counter_trend_trap(token: str, direction: str, regime: str = 'NEUTRAL', regime_conf: float = 0) -> tuple:
    """
    SPEED FEATURE: Counter-trend trap detection.
    PENALTY not block: strong signals survive despite counter-trend setup.

    Returns (penalty: int, reason: str) — penalty=0 means no counter-trend penalty.
    Only penalized if: is_stale=True AND z_score direction contradicts regime.

    Args:
        token, direction: trade parameters
        regime: pre-computed per-coin regime from hotset.json (avoids get_regime() call)
        regime_conf: pre-computed regime confidence from hotset.json
    """
    if speed_tracker_dr is None:
        return 0, ''

    spd = speed_tracker_dr.get_token_speed(token)
    if not spd or not spd.get('is_stale'):
        return 0, ''

    z_score = _get_token_zscore(token)

    if regime_conf < 60:
        return 0, ''

    # Counter-trend trap: stale token near bottom of range trying to go SHORT
    # (z<0 = price near local bottom, but regime says SHORT = catching falling knife)
    if regime in ('SHORT_BIAS', 'SHORT') and z_score < 0:
        penalty = min(int(regime_conf * 0.4), 30)
        return penalty, f'counter_trend_trap: stale+z<0+short_regime(z={z_score:+.2f})'
    if regime in ('LONG_BIAS', 'LONG') and z_score > 0:
        penalty = min(int(regime_conf * 0.4), 30)
        return penalty, f'counter_trend_trap: stale+z>0+long_regime(z={z_score:+.2f})'

    return 0, ''


# ─── Volume Cache Warm-Up ────────────────────────────────────────────────────────
def _warmup_volume_cache():
    """
    Pre-fetch HL volume data for all tokens with open positions.
    Runs in a background thread — does NOT block decider-run pipeline.
    Writes to the shared volume_cache.json so position_manager reads it
    warm on the same pipeline cycle.
    """
    import threading

    def _background_warmup():
        try:
            from position_manager import (
                _fetch_volume_data, _load_volume_cache, _save_volume_cache,
                VOLUME_CACHE_FILE, VOLUME_CACHE_TTL
            )
            import time as _time
        except Exception as e:
            print(f"[Volume Warmup] import failed: {e}")
            return

        try:
            conn = psycopg2.connect(**BRAIN_DB_DICT)
            cur = conn.cursor()
            cur.execute("SELECT DISTINCT token FROM trades WHERE status = 'open' AND server = 'Hermes'")
            open_tokens = [r[0].upper() for r in cur.fetchall()]
            conn.close()
        except Exception as e:
            print(f"[Volume Warmup] failed to get open tokens: {e}")
            return

        if not open_tokens:
            return

        cache = _load_volume_cache()
        now = time.time()
        fresh_tokens = [t for t in open_tokens
                        if cache.get(t) and (now - cache[t].get("ts", 0)) < VOLUME_CACHE_TTL]
        tokens_to_fetch = [t for t in open_tokens if t not in fresh_tokens]
        if not tokens_to_fetch:
            return  # all already fresh

        fetched = errors = 0
        for token in tokens_to_fetch:
            try:
                data = _fetch_volume_data(token)
                if data:
                    cache[token] = data
                    fetched += 1
                else:
                    errors += 1
            except Exception:
                errors += 1

        if cache:
            _save_volume_cache(cache)
        print(f"[Volume Warmup] {fetched} fetched, {errors} errors ({len(open_tokens)} open tokens)")

    t = threading.Thread(target=_background_warmup, daemon=True)
    t.start()
    # Don't join — let it run in background while pipeline proceeds


# ─── Main Run ────────────────────────────────────────────────────

def run(dry_run=False):
    paper = not is_live_trading_enabled()
    mode = "LIVE" if not paper else "PAPER"
    log(f'=== Decider Run ({mode}) ===')
    init_db()

    # ── Warm-up volume cache ────────────────────────────────────────────────
    # Volume data is now seeded lazily inside position_manager on first call —
    # the cache file is shared across both scripts so it's already warm by the
    # time position_manager checks it. No blocking import or threading needed.

    # ── Checkpoint recovery ───────────────────────────────────────────────
    try:
        incomplete = detect_incomplete_run()
        if incomplete:
            print(f'[RECOVERY] Detected incomplete run from {incomplete.get("ts")}')
            last = checkpoint_read_last('trade_pending')
            if last:
                print(f'[RECOVERY] Last trade: {last.get("token")} {last.get("direction")}')
            checkpoint_write('decider_recovery_complete', {'workflow_state': 'IDLE'})
    except Exception as e:
        print(f'[RECOVERY] Check failed: {e}')

    # Run hot-set auto-approver every minute
    _run_hot_set()

    # Process delayed-entry signals first
    de_exec, de_exp = process_delayed_entries(paper=paper)

    # Check position count
    open_count = get_position_count()
    log(f'Open positions: {open_count}/{MAX_POS}')

    # ── Rate limit: minimum 15 seconds between new entries ─────────
    try:
        conn_rate = psycopg2.connect(**BRAIN_DB_DICT)
        c_rate = conn_rate.cursor()
        c_rate.execute("SELECT open_time FROM trades WHERE status='open' ORDER BY open_time DESC LIMIT 1")
        row = c_rate.fetchone()
        conn_rate.close()
        if row and row[0]:
            import datetime
            # DB column is timestamp without time zone (naive). Localize as UTC
            # so subtraction with timezone-aware now() works correctly.
            ts = row[0].replace(tzinfo=datetime.timezone.utc) if row[0].tzinfo is None else row[0]
            gap = (datetime.datetime.now(datetime.timezone.utc) - ts).total_seconds()
            if gap < 15:
                log(f'SKIP: Rate limit — last entry {gap:.0f}s ago (min 15s gap)')
                return 0, 0
    except Exception as e:
        import traceback; traceback.print_exc()
        log(f'Rate limit check failed (DB error): {e} — proceeding without rate limit')

    # Get approved signals
    # Clean up stale approvals before fetching (expire anything >1h old)
    stale = cleanup_stale_approved(hours=1)
    if stale > 0:
        log(f'Expired {stale} stale approved signals (>1h old)')

    approved = get_approved_signals(hours=24)
    log(f'Approved signals: {len(approved)}')

    # ── HOT-SET DISCIPLINE: NO BYPASS ─────────────────────────────────────
    # Every entry comes from the hot-set. The >=95% confluence fallback has been
    # removed — signals that haven't survived signal_compactor compaction do NOT execute.
    # If approved is empty, we wait for the next signal_compactor run to populate the hot-set.
    # This is the "no shortcuts" rule from surfing.md.

    # ── Confidence floor: reject signals below 50% ──────────────────────────
    # Lowered from 65% on 2026-04-11 — signals were being generated at 59-65% conf
    # but 100% blocked at execution gate, causing empty hotset and pipeline stall.
    # 50% is still a meaningful quality floor for pre-qualified hot-set tokens.
    MIN_EXEC_CONFIDENCE = 50

    # ── HOTSET_ENABLED bypass ──────────────────────────────────────────────
    # When HOTSET_ENABLED=False, skip the hot-set gate entirely.
    # Any PENDING signal passing blacklist/cooldown/regime checks can execute
    # immediately — no survival_rounds or hot-set compaction required.
    if not HOTSET_ENABLED:
        # Pull best PENDING signal per token+direction (skip APPROVED/hot-set gate)
        pending = get_pending_signals(hours=24)
        pending = [s for s in pending if s.get('confidence', 0) >= MIN_EXEC_CONFIDENCE]
        # Normalize pending signals to match approved signal schema (final_confidence)
        for s in pending:
            s['final_confidence'] = s.get('confidence', 0)
            s['source'] = s.get('source', 'bypass')
        # Score by confidence (no survival round filter)
        pending_sorted = sorted(pending, key=lambda s: s.get('final_confidence', 0), reverse=True)
        log(f'[HOTSET-BYPASS] {len(pending_sorted)} pending signals eligible (no hot-set gate)')
        # Reuse the same approved processing loop by substituting pending as approved
        approved = pending_sorted
    # Surfing gate: require signal to survive N hot-set cycles before executing.
    # Cycle 1: signal appears in hot-set for the FIRST time as APPROVED → survival_rounds=1
    # Cycle 2+: signal reappears as APPROVED → survival_rounds=2 → NOW eligible
    # Setting to 1 = signal must have survived at least 1 hot-set cycle (the "prove it" gate).
    # The original value of 2 was unachievable on first-pass signals.
    MIN_SURVIVAL_ROUNDS = 1
    approved = [s for s in approved if s.get('final_confidence', 0) >= MIN_EXEC_CONFIDENCE]
    if not approved:
        log(f'No signals above {MIN_EXEC_CONFIDENCE}% confidence — skipping execution')
        return 0, 0

    # ── Multi-factor execution ranking ─────────────────────────────────────────
    # PRIMARY: survival rounds — signals that survived more hot-set compaction cycles
    # have proven themselves against market volatility. Execute veterans first.
    # Secondary: final_confidence (includes hot_bonus = min(20, hot_rounds * 5)
    # Speed and z are NOT used here — they would incorrectly prioritize fresh high-speed
    # signals over proven survivors.
    def _exec_score(sig):
        conf = sig.get('final_confidence', 0)
        rounds = sig.get('hot_rounds', 0)  # survival rounds from DB (0 if never hot-set)
        # PRIMARY: survival rounds — most battle-tested signals execute first.
        # Secondary: confidence — higher quality within same round-tier.
        return (rounds, conf)  # rounds-first, confidence tiebreak

    # Override scoring for bypass mode: pure confidence sort (no hot-set rounds bias)
    if not HOTSET_ENABLED:
        def _exec_score(sig):
            return sig.get('final_confidence', 0)

    scored = sorted(approved, key=_exec_score, reverse=True)

    # Pre-build regime lookup from hotset.json for execution block.
    # signal_compactor writes regime+regime_conf to hotset.json at compaction time.
    _hotset_regime = {}
    try:
        import json as _json
        _hf_path = HOTSET_FILE
        with open(_hf_path) as _hf:
            for _s in _json.load(_hf).get('hotset', []):
                _hotset_regime[_s['token'].upper()] = (_s.get('regime', 'NEUTRAL'), _s.get('regime_conf', 0))
    except Exception:
        pass

    # Load current hot-set for execution gate check
    # NOTE: hot-set is reloaded on EACH iteration inside the loop, not once
    # at the top. This prevents a race where signal_compactor runs mid-loop
    # and writes a new hot-set that could allow previously-blocked tokens through.
    _current_hotset = []
    _hot_tokens = set()
    _hotset_regime = {}
    try:
        with open(HOTSET_FILE) as _hf:
            _hs_data = _json.load(_hf)
            _current_hotset = _hs_data.get('hotset', [])
            _hot_tokens = {_t['token'].upper() for _t in _current_hotset}
            for _s in _current_hotset:
                _hotset_regime[_s['token'].upper()] = (_s.get('regime', 'NEUTRAL'), _s.get('regime_conf', 0))
    except Exception:
        pass

    entered = 0
    skipped = 0
    _processed_tokens_this_run = set()
    _regime = 'NEUTRAL'  # default — overridden per-token in hotset loop above

    for i, sig in enumerate(scored):
        # Re-load hot-set on each iteration — prevents race with signal_compactor
        # running mid-loop and updating hotset.json between signals
        try:
            with open(HOTSET_FILE) as _hf:
                _hs_data = _json.load(_hf)
                _current_hotset = _hs_data.get('hotset', [])
                _hot_tokens = {_t['token'].upper() for _t in _current_hotset}
                for _s in _current_hotset:
                    _hotset_regime[_s['token'].upper()] = (_s.get('regime', 'NEUTRAL'), _s.get('regime_conf', 0))
        except Exception:
            pass

        # ── DEBUG: Log every signal disposition ─────────────────────────────────
        sig_id = sig.get('signal_id')
        token = sig.get('token', '').upper()
        direction = sig['direction']
        confidence = sig.get('final_confidence')
        source = sig.get('source', '')
        in_hotset = token in _hot_tokens
        log(f"[DECIDER-LOOP] #{i+1} {token} {direction} conf={confidence} hotset={'YES' if in_hotset else 'NO'} src={source[:60]}")
        # HOT-SET DISCIPLINE: execution REQUIRES token to be in hotset.json.
        # signal_compactor is the sole approval authority — signals not in hotset
        # have not passed compaction and must NOT execute.
        if not in_hotset:
            log(f'  🚫 [EXEC-BLOCK] {token} {direction} NOT in hot-set — bypass attempt blocked')
            if sig_id:
                mark_signal_executed(token, direction, 'SKIPPED', signal_id=sig_id)
            skipped += 1
            continue

        # BUG-FIX (2026-05-15): Skip if this token was already processed in this pipeline run.
        # Hot-set can have duplicate token+direction entries via signal_compactor.
        # PostgreSQL duplicate check reads pre-run state — two approved signals for the same
        # token in the same run would both pass. This set tracks tokens processed in THIS run.
        if token in _processed_tokens_this_run:
            log(f'  [SKIP] {token} {direction} — already processed in this pipeline run')
            if sig_id:
                mark_signal_executed(token, direction, 'SKIPPED', signal_id=sig_id)
            skipped += 1
            continue
        _processed_tokens_this_run.add(token)

        # BUG-26: extract signal_id for atomic claim BEFORE any trade execution.
        # This prevents double-execution when multiple scripts run same minute.
        sig_id = sig.get('signal_id')

        # ── Layer 3: Kill-Switch Execution Gate ────────────────────────────────
        # This is the FINAL gate before execution — even if a signal survived
        # add_signal() (Layer 2), it gets stopped here if its *_ENABLED flag is False.
        try:
            from hermes_constants import (
                PCT_HERMES_ENABLED, PCT_HERMES_PLUS_ENABLED, PCT_HERMES_MINUS_ENABLED,
                VEL_HERMES_ENABLED, VEL_HERMES_PLUS_ENABLED, VEL_HERMES_MINUS_ENABLED,
                HZSCORE_ENABLED, HZSCORE_PLUS_ENABLED, HZSCORE_MINUS_ENABLED,
                HMACD_ENABLED, HMACD_PLUS_ENABLED, HMACD_MINUS_ENABLED,
                MTF_MOMENTUM_ENABLED, MTF_MOMENTUM_PLUS_ENABLED, MTF_MOMENTUM_MINUS_ENABLED,
                PHASE_ACCEL_ENABLED, PHASE_ACCEL_PLUS_ENABLED, PHASE_ACCEL_MINUS_ENABLED,
                FAST_MOMENTUM_ENABLED, FAST_MOMENTUM_PLUS_ENABLED, FAST_MOMENTUM_MINUS_ENABLED,
                RS_ENABLED, GAP_300_ENABLED, GAP_300_PLUS_ENABLED, GAP_300_MINUS_ENABLED,
                MA_CROSS_ENABLED, MA_CROSS_PLUS_ENABLED, MA_CROSS_MINUS_ENABLED,
                MA_CROSS_5M_ENABLED, MA_CROSS_5M_PLUS_ENABLED, MA_CROSS_5M_MINUS_ENABLED,
                HH_HL_ENABLED, GUPPY_ENABLED, MACD_ACCEL_ENABLED,
                TREND_PURITY_ENABLED, EMA9_SMA20_ENABLED,
                R2_REV_ENABLED, R2_TREND_ENABLED,
                VOLUME_HL_ENABLED, MA300_CANDLE_ENABLED,
                ATR_COMPRESSION_ENABLED, EXHAUSTION_ENABLED,
                BB_BOUNCE_ENABLED,
            )
            _skip_signal = False
            _components = source.split(',')
            for _comp in _components:
                if _comp == 'pct-hermes+' and not PCT_HERMES_PLUS_ENABLED:
                    log(f'  SKIP {token} {direction}: PCT_HERMES_PLUS_ENABLED=False')
                    skipped += 1; _skip_signal = True; break
                if _comp == 'pct-hermes-' and not PCT_HERMES_MINUS_ENABLED:
                    log(f'  SKIP {token} {direction}: PCT_HERMES_MINUS_ENABLED=False')
                    skipped += 1; _skip_signal = True; break
                if _comp == 'pct-hermes' and not PCT_HERMES_ENABLED:
                    log(f'  SKIP {token} {direction}: PCT_HERMES_ENABLED=False')
                    skipped += 1; _skip_signal = True; break
                if _comp == 'vel-hermes+' and not VEL_HERMES_PLUS_ENABLED:
                    log(f'  SKIP {token} {direction}: VEL_HERMES_PLUS_ENABLED=False')
                    skipped += 1; _skip_signal = True; break
                if _comp == 'vel-hermes-' and not VEL_HERMES_MINUS_ENABLED:
                    log(f'  SKIP {token} {direction}: VEL_HERMES_MINUS_ENABLED=False')
                    skipped += 1; _skip_signal = True; break
                if _comp == 'hzscore+' and not HZSCORE_PLUS_ENABLED:
                    log(f'  SKIP {token} {direction}: HZSCORE_PLUS_ENABLED=False')
                    skipped += 1; _skip_signal = True; break
                if _comp == 'hzscore-' and not HZSCORE_MINUS_ENABLED:
                    log(f'  SKIP {token} {direction}: HZSCORE_MINUS_ENABLED=False')
                    skipped += 1; _skip_signal = True; break
                if _comp == 'hmacd+' and not HMACD_PLUS_ENABLED:
                    skipped += 1; _skip_signal = True; break
                if _comp == 'hmacd-' and not HMACD_MINUS_ENABLED:
                    skipped += 1; _skip_signal = True; break
                if _comp in ('gap-300+', 'gap300-5m+') and not GAP_300_PLUS_ENABLED:
                    log(f'  SKIP {token} {direction}: GAP_300_PLUS_ENABLED=False')
                    skipped += 1; _skip_signal = True; break
                if _comp in ('gap-300-', 'gap300-5m-') and not GAP_300_MINUS_ENABLED:
                    log(f'  SKIP {token} {direction}: GAP_300_MINUS_ENABLED=False')
                    skipped += 1; _skip_signal = True; break
                if _comp == 'ma_cross+' and not MA_CROSS_PLUS_ENABLED:
                    log(f'  SKIP {token} {direction}: MA_CROSS_PLUS_ENABLED=False')
                    skipped += 1; _skip_signal = True; break
                if _comp == 'ma_cross-' and not MA_CROSS_MINUS_ENABLED:
                    log(f'  SKIP {token} {direction}: MA_CROSS_MINUS_ENABLED=False')
                    skipped += 1; _skip_signal = True; break
                if _comp == 'ma_cross_5m+' and not MA_CROSS_5M_PLUS_ENABLED:
                    log(f'  SKIP {token} {direction}: MA_CROSS_5M_PLUS_ENABLED=False')
                    skipped += 1; _skip_signal = True; break
                if _comp == 'ma_cross_5m-' and not MA_CROSS_5M_MINUS_ENABLED:
                    log(f'  SKIP {token} {direction}: MA_CROSS_5M_MINUS_ENABLED=False')
                    skipped += 1; _skip_signal = True; break
                if _comp == 'r2_rev' and not R2_REV_ENABLED:
                    log(f'  SKIP {token} {direction}: R2_REV_ENABLED=False')
                    skipped += 1; _skip_signal = True; break
                if _comp == 'fast-momentum-' and not FAST_MOMENTUM_MINUS_ENABLED:
                    log(f'  SKIP {token} {direction}: FAST_MOMENTUM_MINUS_ENABLED=False')
                    skipped += 1; _skip_signal = True; break
                if _comp == 'bb_bounce' and not BB_BOUNCE_ENABLED:
                    log(f'  SKIP {token} {direction}: BB_BOUNCE_ENABLED=False')
                    skipped += 1; _skip_signal = True; break
        except ImportError:
            pass  # hermes_constants not available — skip gate

        if _skip_signal:
            continue
        price = sig.get('price') or get_current_price(token)

        if not price:
            log(f'SKIP: {token} — no price available')
            skipped += 1
            continue

        # ── Pre-execution price sanity check ─────────────────────────────
        # Guard against corrupted/stale signal prices (>5x from cached)
        # or out-of-bounds absolute values to prevent bad fills.
        cached = get_current_price(token)
        if cached and cached > 0 and price > 0:
            ratio = price / cached
            if ratio > 5:
                log(f'SKIP: {token} SUSPICIOUS PRICE {price} vs cached {cached} (ratio {ratio:.2f}x) — skipping')
                if sig_id:
                    mark_signal_executed(token, direction, 'SKIPPED', signal_id=sig_id)
                skipped += 1
                continue

        if price > 1_000_000 or price < 0.00001:
            log(f'SKIP: {token} price {price} out of absolute bounds [$0.00001-$1 000 000]')
            if sig_id:
                mark_signal_executed(token, direction, 'SKIPPED', signal_id=sig_id)
            skipped += 1
            continue

        # Check if already open
        if is_position_open(token):
            log(f'SKIP: {token} already open')
            if sig_id:
                mark_signal_executed(token, direction, 'SKIPPED', signal_id=sig_id)
            skipped += 1
            continue

        # ── Guardian closing race-condition gate ───────────────────────────────
        # Guardian writes a marker before closing an orphan position. The marker
        # stays active while HL fills propagate (up to ~15s). decider_run checks
        # it here to avoid executing a new signal while guardian is closing the
        # same token — which would result in dual positions on HL.
        if _is_guardian_closing(token):
            log(f'SKIP: {token} — guardian closing in progress (race guard)')
            if sig_id:
                mark_signal_executed(token, direction, 'SKIPPED', signal_id=sig_id)
            skipped += 1
            continue

        # ── Surfing gate: skip if signal hasn't survived enough hot-set cycles ──
        # hot_rounds comes from get_approved_signals() (signal_schema.py line 1012)
        # HOTSET_ENABLED=False bypasses this gate entirely
        if HOTSET_ENABLED:
            sig_survival_rounds = sig.get('hot_rounds', 0)
            if sig_survival_rounds < MIN_SURVIVAL_ROUNDS:
                log(f'SKIP SURF: {token} {direction} — survival_rounds={sig_survival_rounds} < {MIN_SURVIVAL_ROUNDS} (wave still building)')
                skipped += 1
                continue

        # ── OC Signal Block (2026-04-23) ──────────────────────────────────────────
        # oc_pending signals must survive signal_compactor hot-set compaction.
        # They are NOT auto-approved here — they go through the same survival
        # rounds check as all other signals. This prevents OC from bypassing
        # the hot-set discipline by writing directly to the signal DB.
        # Leave as PENDING so they continue competing in compaction cycles.
        # HOTSET_ENABLED=False bypasses OC block — any signal can execute
        sig_type = sig.get('signal_type', '') or ''
        if HOTSET_ENABLED and sig_type == 'oc_pending':
            log(f'  🚫 [EXEC-BLOCK] {token} {direction} blocked: oc_pending signal (must survive hot-set compaction)')
            skipped += 1
            continue

        # ── Counter-trend trap guard — DISABLED 2026-05-11 ─────────────────
        # 1m LR regime is too noisy for execution gating (100-candle window too volatile).
        # Was causing false SHORT_BIAS → blocking LONG signals incorrectly.
        # _exec_regime, _exec_regime_conf = _get_regime_1m(token)
        # trap_blocked, trap_reason = _check_counter_trend_trap(token, direction, _exec_regime, _exec_regime_conf)
        # if trap_blocked:
        #     log(f'  🧊 [EXEC-BLOCK] {token} {direction}: {trap_reason}')
        #     if sig_id:
        #         mark_signal_executed(token, direction, 'SKIPPED', signal_id=sig_id)
        #     skipped += 1
        #     continue

        # ── Regime filter for approved signals — DISABLED 2026-05-11 ───────────
        # 1m LR (100 candles) is too noisy — produces false SHORT_BIAS during neutral
        # markets, blocks valid LONG signals. Regime check was adding confusion on top
        # of the WR gate. Hot-set signals are already vetted by signal_compactor.
        # Disabling entirely to let WR gate do its job cleanly.
        # try:
        #     if is_delisted(token):
        #         log(f'  🧊 [EXEC-BLOCK] {token} {direction} blocked: not tradeable on Hyperliquid')
        #         if sig_id:
        #             mark_signal_executed(token, direction, 'SKIPPED', signal_id=sig_id)
        #         skipped += 1
        #         continue
        #     regime, regime_conf = _get_regime_1m(token)
        #     if regime is None or regime == 'NOT_IN_JSON':
        #         log(f'  🧊 [EXEC-BLOCK] {token} {direction} blocked: regime blindspot')
        #         if sig_id:
        #             mark_signal_executed(token, direction, 'SKIPPED', signal_id=sig_id)
        #         skipped += 1
        #         continue
        #     if regime == 'NEUTRAL' and regime_conf > 60:
        #         log(f'  📉 [DEESC] {token} {direction} de-escalated: NEUTRAL regime ({regime_conf:.0f}%)')
        #         skipped += 1
        #         continue
        #     if (regime == 'LONG_BIAS' and direction == 'SHORT') or \
        #        (regime == 'SHORT_BIAS' and direction == 'LONG'):
        #         penalty = min(int(regime_conf * 0.15), 15)
        #         confidence -= penalty
        #         if confidence < MIN_EXEC_CONFIDENCE:
        #             log(f'  📉 [DEESC] {token} {direction} counter-regime penalized {penalty}pts below exec threshold ({confidence:.0f}% < {MIN_EXEC_CONFIDENCE}%)')
        #             skipped += 1
        #             continue
        #         log(f'  📉 [DEESC] {token} {direction} penalized {penalty}pts for counter-regime (conf now {confidence:.0f}%)')
        # except Exception as e:
        #     log(f'  ⚠️ [EXEC-BLOCK] {token} regime check error: {e}')

        # conf-1s = single-source, too weak — hard ban. conf-2s+ are real confluence.
        # NOTE: hzscore and hmacd- also end in 's' but pass through because the
        # inner check only blocks conf-1s variants. This is intentional.
        sig_src = sig.get('source', '') or ''
        if CONFLUENCE_REQUIRED and (sig_src.startswith('conf-') or sig_src.endswith('s')):
            # It's a confluence source (conf-1s, conf-2s, fallback-conf-3s, etc.)
            if sig_src == 'conf-1s' or sig_src.startswith('conf-1s'):
                log(f'  🚫 [EXEC-BLOCK] {token} {direction} blocked: {sig_src} (single-source, min 2 required)')
                if sig_id:
                    mark_signal_executed(token, direction, 'SKIPPED', signal_id=sig_id)
                skipped += 1
                continue
        elif not CONFLUENCE_REQUIRED and (sig_src.startswith('conf-') or sig_src.endswith('s')):
            if sig_src == 'conf-1s' or sig_src.startswith('conf-1s'):
                log(f'  ➡️  [EXEC-ALLOW] {token} {direction} single-source allowed (CONFLUENCE_REQUIRED=False): {sig_src}')

        # ── Dead-Hours Entry Filter ─────────────────────────────────────
        # Block entries during low-liquidity hours (whitewater, no wave).
        # Surfing principle: "You can't force a wave — you read it, position yourself."
        # Data: inv-accel signals have ~17% WR during dead hours vs ~35% active.
        # accel-300- performs fine during dead hours (50% WR) — not blocked.
        if DEAD_HOURS_ENABLED:
            import datetime as _dt
            _utc_hour = _dt.datetime.utcnow().hour
            if DEAD_HOURS_START <= _utc_hour < DEAD_HOURS_END:
                # Check if this signal is in the dead-hours block list
                _should_block = DEAD_HOURS_DEFAULT  # default behavior
                for prefix in DEAD_HOURS_SIGNALS:
                    if source.startswith(prefix):
                        _should_block = False  # allowlisted signal — don't block
                        break
                if _should_block:
                    log(f'  🚫 [DEAD-HOURS] {token} {direction} blocked: {_utc_hour:02d}:XX UTC (signal={source}, dead hours {DEAD_HOURS_START:02d}-{DEAD_HOURS_END:02d})')
                    if sig_id:
                        mark_signal_executed(token, direction, 'SKIPPED', signal_id=sig_id)
                    skipped += 1
                    continue

        # FIX (2026-04-05): speed=0% = stale token — hard ban
        sp_exec = speed_tracker_dr.get_token_speed(token) if speed_tracker_dr else None
        sp_exec_val = sp_exec.get('speed_percentile', 50.0) if sp_exec else 50.0
        if sp_exec_val == 0:
            log(f'  🚫 [EXEC-BLOCK] {token} {direction} blocked: speed=0% (stale token)')
            if sig_id:
                mark_signal_executed(token, direction, 'SKIPPED', signal_id=sig_id)
            skipped += 1
            continue

        # Check loss cooldown — block same direction after a loss
        # FIX (2026-04-23): Use _is_loss_cooldown_active from signal_schema (JSON-only)
        # instead of position_manager.is_loss_cooldown_active (which also checks PostgreSQL
        # signal_cooldowns). The PostgreSQL table has 188 rows including expired cooldowns
        # that never get cleaned up, causing ALL hot-set signals to be blocked every cycle.
        # signal_compactor.py already uses the JSON-only variant — decider_run must match.
        if _is_loss_cooldown_active(token, direction):
            log(f'SKIP: {token} {direction} in loss cooldown')
            skipped += 1
            continue

        # ── Wrong-Side Learning ───────────────────────────────────
        # Softened 2026-08-03: penalty -15→-10, skip threshold 55→50.
        # Was blocking too many hot-set candidates. MIN_EXEC_CONFIDENCE=50
        # handles the final cutoff; this gate just adds a softer penalty.
        is_risky, risk_reason = is_wrong_side_risky(token, direction, confidence)
        if is_risky:
            adjusted_conf = confidence - WRONG_SIDE_PENALTY
            if adjusted_conf < WRONG_SIDE_SKIP_THRESHOLD:
                log(f'SKIP: {token} {direction} {risk_reason} (conf {confidence:.0f}% -> {adjusted_conf:.0f}%)')
                skipped += 1
                continue
            log(f'WARN: {token} {direction} {risk_reason} (conf {confidence:.0f}% -> {adjusted_conf:.0f}%)')
            confidence = adjusted_conf

        # ── Direction Awareness ───────────────────────────────────
        # Skip LONG/SHORT if it has < TOKEN_WR_THRESHOLD% win rate in recent history (min TOKEN_WR_MIN_SAMPLE trades)
        wr, wr_count = _get_direction_wr(token, direction)
        if wr < TOKEN_WR_THRESHOLD and wr_count >= TOKEN_WR_MIN_SAMPLE:
            log(f'SKIP: {token} {direction} WR={wr:.0f}% ({wr_count} trades) — direction paused')
            skipped += 1
            continue

        # Per-token regime check is handled by ai-decider.get_regime()
        # which reads from PostgreSQL momentum_cache — per-token regime filter only.
        # No aggregate market-wide block here.

        # Check position limit
        if open_count >= MAX_POS:
            log(f'SKIP: Max positions reached ({MAX_POS})')
            break

        # BUG-12 fix: validate source against whitelist before routing to A/B params
        # FIX: Use actual source from DB if available (e.g. 'hmacd-,hzscore' from merged signals)
        raw_source = sig.get('source') or f'conf-{sig.get("count", sig.get("num_signals", 1))}s'
        source = validate_source(raw_source)
        if source == 'unknown':
            log(f'SKIP: {token} — unknown source "{raw_source}" (not in whitelist)')
            skipped += 1
            continue

        # ── Epsilon-greedy A/B variant selection ──────────────────
        ab = get_ab_params_for_trade(direction)
        sl_pct = ab['sl_pct']
        trailing_activation = ab['trailing_activation']
        trailing_distance  = ab['trailing_distance']
        trailing_phase2    = ab.get('trailing_phase2_dist')
        experiment = ab['experiment']
        sl_variant = ab.get('sl_variant', '')
        ts_variant = ab.get('ts_variant', '')

        # A/B TEST DISABLED (2026-04-17) — ATR-based SL/TP managed by position_manager.
        # ATR populates within 1 min of entry via _collect_atr_updates().
        sl = 0
        tp = 0

        # Recalculate speed_pctl for logging (sp was from _exec_score scope)
        sig_spd = speed_tracker_dr.get_token_speed(token) if speed_tracker_dr else None
        sp_now = sig_spd.get('speed_percentile', 50.0) if sig_spd else 50.0
        log(f'EXEC: {token} {direction} @ ${price:.6f} conf={confidence:.0f}% '
            f'SL=${sl:.4f} TP=${tp:.4f} [{source}] '
            f'[SL={sl_pct:.1f}% trail={trailing_activation*100:.1f}%/{trailing_distance*100:.1f}%]'
            f'[spd={sp_now:.0f}%]')

        # ── Signal Inversion (static + dynamic, BEFORE context gate) ─────
        direction, _flipped = _apply_inversion(direction, source, token)
        flipped_direction = direction if _flipped else None

        # ── Z-Score Freshness Check (CRITICAL: prevent stale signal execution) ──
        # If z-score direction has flipped since signal generation, skip the trade.
        # This prevents SHORT signals firing when z is rising, and vice versa.
        if sig and isinstance(sig, dict) and sig.get('z_score') is not None:
            sig_z = sig.get('z_score', 0)
            cur_z = _ctx_gate_get_zscore(token)
            if cur_z is not None:
                # Direction flip: signal said SHORT (z<0) but now z>0, or vice versa
                if direction == 'SHORT' and cur_z > 0.5 and sig_z < 0:
                    log(f'  🚫 [Z-FLIP] {token} SHORT blocked: z flipped from {sig_z:+.2f} to {cur_z:+.2f}')
                    if sig_id:
                        mark_signal_executed(token, direction, 'SKIPPED', signal_id=sig_id)
                    skipped += 1
                    continue
                if direction == 'LONG' and cur_z < -0.5 and sig_z > 0:
                    log(f'  🚫 [Z-FLIP] {token} LONG blocked: z flipped from {sig_z:+.2f} to {cur_z:+.2f}')
                    if sig_id:
                        mark_signal_executed(token, direction, 'SKIPPED', signal_id=sig_id)
                    skipped += 1
                    continue

        # ── Context Gate (last gate before execution) ────────────
        # Rule-based handles ~80% (free). LLM only for ambiguous (5-10 calls/hr).
        # Rule-based = hard block (SKIP) or FLIP (direction change). LLM/similar setup = soft advisory (WARN → confidence penalty).
        ctx_verdict, ctx_reason, ctx_penalty = context_gate(token, direction, source, sig)
        if ctx_verdict == 'SKIP':
            log(f'  🚫 [CTX-GATE] {token} {direction} blocked: {ctx_reason}')
            if sig_id:
                mark_signal_executed(token, direction, 'SKIPPED', signal_id=sig_id)
            skipped += 1
            continue
        if ctx_verdict == 'FLIP':
            new_dir = ctx_reason.get('new_dir', direction)
            flip_reason = ctx_reason.get('reason', 'phase flip')
            log(f'  🔄 [CTX-GATE] {token} {direction} → {new_dir}: {flip_reason}')
            direction = new_dir
        elif ctx_verdict == 'WARN' and ctx_penalty:
            confidence = max(confidence - ctx_penalty, 0)
            log(f'  ⚠️ [CTX-GATE] {token} {direction} WARN: {ctx_reason} (conf → {confidence:.0f}%)')
        elif ctx_verdict == 'GO' and ctx_penalty:
            confidence = max(min(confidence + ctx_penalty, 100), 0)
            log(f'  ✅ [CTX-GATE] {token} {direction} GO (hebbian adj {ctx_penalty:+d}): {ctx_reason} (conf → {confidence:.0f}%)')
        else:
            log(f'  ✅ [CTX-GATE] {token} {direction} passed: {ctx_reason or "rule-based GO"}')

        if dry_run:
            log(f'  → [DRY-RUN] Would enter {token} {direction}')
            # Don't mark executed in dry-run — nothing is real
            entered += 1
            # Don't increment open_count in dry-run — no real position opened
            continue

        # Get per-token leverage from Hyperliquid
        lev = get_max_leverage(token)
        lev = min(lev, 5)   # hard cap at 5x (safer for all directions)

        # BUG-26 fix: claim signal atomically BEFORE brain.py call.
        # This prevents double-execution when multiple scripts run same minute.
        # Use signal_id if available, else fall back to legacy token+direction match.
        log(f'  → mark_signal_executed(token={token}, direction={direction}, signal_id={sig_id}) — atomic claim')
        claimed = mark_signal_executed(token, direction, signal_id=sig_id)
        log(f'  ← mark_signal_executed returned: {claimed} (0=failed/already-claimed, 1=success)')
        if sig_id is not None and claimed == 0:
            # Signal already claimed by another process — skip this one
            log(f'SKIP: {token} {direction} — signal {sig_id} already claimed (executed by another runner) [executed=1 in DB]')
            skipped += 1
            continue

        elif sig_id is None:
            # Legacy hot-set format (no signal_id): fallback claim via token+direction.
            # Two cases:
            #   claimed=1: this process won the fallback race, proceed to brain.py
            #   claimed=0: another process already claimed via a valid sig_id — skip
            # BUG-FIX (2026-05-20): Without this check, sig_id=None + claimed=0 proceeds
            # to brain.py anyway, opening an HL position with no valid signal claim.
            # This creates phantom orphans — HL position opened, DB INSERT fails (already
            # claimed by another process), HL rollback succeeds but signal is stuck.
            if claimed == 0:
                log(f'SKIP: {token} {direction} — sig_id=None but claimed=0, another process with valid sig_id already owns this token+direction slot')
                skipped += 1
                continue
            log(f'  ⚠️ sig_id=None for {token} {direction} — legacy hot-set format, proceeding via token+direction fallback claim')
        
        # ── Trade pending checkpoint ───────────────────────────────────
        try:
            checkpoint_write('trade_pending', {'token': token, 'direction': direction, 'original_direction': flipped_direction})
        except Exception:
            pass

        success, msg = execute_trade(
            token, direction, price, confidence, source,
            leverage=lev, paper=paper, sl_pct=sl_pct,
            trailing_activation=trailing_activation, trailing_distance=trailing_distance,
            trailing_phase2_dist=trailing_phase2,
            experiment=experiment, variant_id=ab.get('sl_variant', ''), test_name='sl-distance-test',
            live_trading=not paper, flipped=bool(flipped_direction), regime=_regime,
            # Signal indicator fields captured from hotset at entry time
            signal_z_score=sig.get('z_score'),
            signal_rsi_14=sig.get('rsi_14'),
            signal_macd_hist=sig.get('macd_hist'),
            signal_momentum_state=sig.get('momentum_state'),
            signal_z_score_tier=sig.get('z_score_tier'),
            signal_decision=sig.get('decision'),
            # A/B test variant tags
            test_sl_variant=ab.get('sl_variant'),
            test_timing_variant=ab.get('entry_variant'),
            test_trailing_variant=ab.get('ts_variant'),
            # JSONB catch-all: all signal indicator values at entry time
            # sig.get() returns a JSON string from hotset.json — deserialize to dict
            # before passing to execute_trade() which will re-serialize via json.dumps()
            signal_metadata=(json.loads(sig.get('signal_metadata'))
                             if sig.get('signal_metadata') else None),
        )

        if success:
            log(f'  → ENTERED: {token} {direction} ({msg})')
            # ── POST-TRADE SL CORRECTION ────────────────────────────────────────
            # If fill price differs from signal price (slippage, context gate flip),
            # the INIT-SL may be on the wrong side. Correct it using actual fill.
            try:
                from hermes_constants import ATR_SL_MIN_INIT
                from psycopg2 import connect as _pg_fix
                _pg = _pg_fix(host='/var/run/postgresql', database='brain', user='postgres')
                _cur = _pg.cursor()
                _cur.execute(
                    "SELECT id, entry_price, hl_entry_price, stop_loss, direction FROM trades "
                    "WHERE token=%s AND direction=%s AND status='open' ORDER BY id DESC LIMIT 1",
                    (token.upper(), direction.upper()))
                _row = _cur.fetchone()
                if _row:
                    _tid, _entry, _hl_entry, _sl, _dir = _row
                    _actual = float(_hl_entry or _entry)
                    _sl_val = float(_sl or 0)
                    if _actual > 0 and _sl_val > 0:
                        if _dir == 'LONG' and _sl_val >= _actual:
                            # SL above entry for LONG — wrong side, fix it
                            _new_sl = round(_actual * (1 - ATR_SL_MIN_INIT), 8)
                            _cur.execute("UPDATE trades SET stop_loss=%s WHERE id=%s", (_new_sl, _tid))
                            _pg.commit()
                            log(f'  [SL-FIX] {token} LONG: SL was {_sl_val:.6f} (above entry {_actual:.6f}), fixed to {_new_sl:.6f}')
                        elif _dir == 'SHORT' and _sl_val <= _actual:
                            # SL below entry for SHORT — wrong side, fix it
                            _new_sl = round(_actual * (1 + ATR_SL_MIN_INIT), 8)
                            _cur.execute("UPDATE trades SET stop_loss=%s WHERE id=%s", (_new_sl, _tid))
                            _pg.commit()
                            log(f'  [SL-FIX] {token} SHORT: SL was {_sl_val:.6f} (below entry {_actual:.6f}), fixed to {_new_sl:.6f}')
                _cur.close(); _pg.close()
            except Exception as sl_fix_err:
                log(f'  [SL-FIX] Post-trade SL correction failed for {token}: {sl_fix_err}')
            # BUG-26 fix: mark_signal_executed was already called atomically above (before brain.py).
            # Record in ab_results — all three experiments
            _record_ab_trade_opened(token, direction, experiment, ab.get('sl_variant', ''), 'sl-distance-test')
            _record_ab_trade_opened(token, direction, experiment, ab.get('entry_variant', ''), 'entry-timing-test')
            _record_ab_trade_opened(token, direction, experiment, ab.get('ts_variant', ''), 'trailing-stop-test')
            entered += 1
            open_count += 1
            # ── Trade entered event ─────────────────────────────────────
            try:
                log_event(EVENT_TRADE_ENTERED, {'token': token, 'direction': direction, 'price': price, 'confidence': confidence})
            except Exception:
                pass
        else:
            # BUG-26 fix: rollback the atomic claim since trade failed.
            # Revert executed=0 so the signal can be picked up on next run.
            if sig_id:
                try:
                    from signal_schema import rollback_signal_executed
                    rolled = rollback_signal_executed(token, direction, signal_id=sig_id)
                    if rolled:
                        log(f'  🔁 SIGNAL ROLLED BACK: {token} {direction} (sig#{sig_id}) — stays in hot-set for retry')
                    else:
                        log(f'  ⚠️ ROLLBACK FAILED: sig#{sig_id} already claimed by another process')
                except Exception as rb_e:
                    log(f'  ⚠️ ROLLBACK ERROR for sig#{sig_id}: {rb_e}')
            else:
                # [FIX-BUG1] sig_id=None (legacy hot-set without signal_id):
                # Try token+direction fallback rollback so signal isn't stuck permanently.
                # Log CRITICAL since this is a gap that could orphan HL positions.
                log(f'  ⚠️ sig_id=None for {token} {direction} — attempting token+direction fallback rollback', 'WARN')
                try:
                    from signal_schema import rollback_signal_executed
                    rolled = rollback_signal_executed(token, direction, signal_id=None)
                    if rolled:
                        log(f'  🔁 SIGNAL ROLLED BACK (token+direction fallback): {token} {direction} — stays in hot-set for retry')
                    else:
                        log(f'  ⚠️ FALLBACK ROLLBACK FAILED: {token} {direction} — signal may be stuck, manual check needed', 'FAIL')
                except Exception as rb_e:
                    log(f'  ⚠️ FALLBACK ROLLBACK ERROR for {token} {direction}: {rb_e}', 'FAIL')
            log(f'  → FAILED: {msg}')
            # ── Trade failed event ───────────────────────────────────────
            try:
                log_event(EVENT_TRADE_FAILED, {'token': token, 'reason': str(msg)[:200]})
            except Exception:
                pass

    log(f'=== Decider Done: {entered} entered | {skipped} skipped '
        f'| {de_exec} delayed exec | {de_exp} delayed expired '
        f'(open: {open_count}/{MAX_POS})')

    # ── Pipeline heartbeat ─────────────────────────────────────────────────────
    _update_decider_heartbeat()

    return entered, skipped


if __name__ == '__main__':
    dry = '--dry-run' in sys.argv
    run(dry_run=dry)
