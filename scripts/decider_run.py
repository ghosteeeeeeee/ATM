#!/usr/bin/env python3
"""
decider_run.py — Execute approved signals via brain.py.
Respects hype_live_trading.json: paper=False (live by default).
Reads APPROVED signals, checks position limits, computes SL/TP, places trades.
Also processes delayed-entry signals from pending-delayed-entries.json.
"""
import sys, subprocess, sqlite3, time, os, json, requests, random, psycopg2, fcntl
sys.path.insert(0, '/root/.hermes/scripts')
from signal_schema import (init_db, get_approved_signals, get_pending_signals,
                           mark_signal_executed, cleanup_stale_approved,
                           update_signal_decision, validate_source)
from ai_decider import get_regime, _get_source_weight
from _secrets import BRAIN_DB_DICT
from position_manager import (get_position_count, is_position_open, enforce_max_positions,
                              get_trade_params, is_loss_cooldown_active, set_loss_cooldown,
                              _is_win_cooldown_active, is_wrong_side_risky)
from signal_gen import PUMP_SL_PCT, PUMP_TP_PCT
from hermes_constants import SHORT_BLACKLIST, LONG_BLACKLIST
from tokens import is_solana_only
from hermes_file_lock import FileLock
from hyperliquid_exchange import is_live_trading_enabled, is_delisted
import hype_cache as hc

# ── OPTION 1: Signal Direction Flip ──────────────────────────────────────
# Signal direction flip — disabled 2026-04-05 (flip test concluded)
# Previously enabled to test if signals were direction-inverted (WR 13.8%).
# KILL SWITCH: set to True to re-enable flip. Effect takes place on next pipeline run (~1 min).
_FLIP_SIGNALS = False

# ── ATR-based Dynamic Stop Loss ─────────────────────────────────────────
# ATR(14) from Hyperliquid 1h candles — cached per token for 5 min.
# SL = entry_price ± (k * ATR(14)) where k varies by volatility regime.
# This replaces fixed % SL which was too tight for volatile tokens (71.5%
# of losses had <1% adverse move — SL fired on noise).
#
# k multipliers:
#   LOW_VOLATILITY:    k=1.5  (SL ≈ 1.5× ATR, slightly wider than old 1.5% flat)
#   NORMAL_VOLATILITY: k=2.0  (SL ≈ 2× ATR — gives trade room to breathe)
#   HIGH_VOLATILITY:   k=2.5  (SL ≈ 2.5× ATR — tokens like TAO, SOL need room)
# Minimum SL guard: never tighter than sl_pct (A/B test value), use ATR if wider.
import time as _time

_ATR_CACHE = {}   # {(token, timeframe): (atr_value, timestamp)}
_ATR_TTL    = 300  # 5 minutes cache TTL

def _get_atr(token: str, period: int = 14, interval: str = '15m') -> float | None:
    """
    Fetch ATR(14) for token from Hyperliquid 15m candles.
    Returns ATR value in dollar terms (same unit as price), or None on failure.
    Cached per token for _ATR_TTL seconds.
    """
    cache_key = (token.upper(), interval)
    now = _time.time()
    if cache_key in _ATR_CACHE:
        atr_val, ts = _ATR_CACHE[cache_key]
        if now - ts < _ATR_TTL:
            return atr_val

    try:
        from hyperliquid.info import Info
        info = Info('https://api.hyperliquid.xyz', skip_ws=True)
        end_t = int(now * 1000)
        start_t = end_t - (15 * 60 * 1000 * (period + 5))  # period+5 × 15min windows
        candles = info.candles_snapshot(token.upper(), interval, start_t, end_t)
        if not candles or len(candles) < period + 1:
            return None

        # Compute True Range for each complete candle pair
        trs = []
        for i in range(1, min(period + 1, len(candles))):
            high = float(candles[i]['h'])
            low  = float(candles[i]['l'])
            prev_close = float(candles[i - 1]['c'])
            tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
            trs.append(tr)

        if not trs:
            return None
        atr = sum(trs) / len(trs)
        _ATR_CACHE[cache_key] = (atr, now)
        return atr
    except Exception as e:
        log(f'  [ATR] {token} fetch error: {e}')
        return None

def _atr_multiplier(token: str, atr_pct: float, override_k: float = None) -> float:
    """
    Return k multiplier for ATR-based SL.
    Self-calibrating based on actual ATR% (volatility):
      atr_pct < 1.0%  → LOW_VOLATILITY    → k=1.0 (tight SL for stable tokens)
      atr_pct 1-3%    → NORMAL_VOLATILITY → k=2.0
      atr_pct > 3%    → HIGH_VOLATILITY   → k=2.5 (wide SL for volatile tokens)
    """
    if override_k is not None:
        return override_k          # A/B test overrides volatility-based k
    if atr_pct < 0.01:
        return 1.0   # LOW_VOLATILITY: tight SL
    elif atr_pct > 0.03:
        return 2.5   # HIGH_VOLATILITY: wide SL
    else:
        return 2.0   # NORMAL_VOLATILITY: balanced

def _compute_dynamic_sl(token: str, direction: str, entry_price: float,
                        current_price: float,
                        sl_pct_fallback: float = 0.015,
                        override_k: float = None) -> float:
    """
    Compute dynamic SL using ATR(14).
    ATR-based SL replaces the fixed % SL. k multiplier is self-calibrating
    based on ATR% (volatility) — wider stops for volatile tokens.

    override_k: if provided (from A/B test atr-sl-test), use it directly
    instead of the volatility-based k table.

    Minimum ATR% floor: if ATR/price < 0.75%, the token is too stable for
    ATR-based SL (e.g. BTC at $95k has $409 ATR = 0.43% = too tight).
    In that case, use max(ATR-based, 1.5% fixed) to ensure meaningful protection.

    Maximum: cap SL distance at 5% to avoid absurdly wide stops on any token.

    BUG-FIX: ATR distance is now computed from current_price (not entry_price),
    which is the correct volatility-based stop placement.
    """
    MIN_ATR_PCT = 0.010   # 1.0% — below this, fall back to fixed %
    MAX_SL_PCT  = 0.05     # 5% — never wider than this

    atr = _get_atr(token)
    if atr is None:
        # Fall back to fixed % SL
        if direction == 'LONG':
            return entry_price * (1 - sl_pct_fallback)
        else:
            return entry_price * (1 + sl_pct_fallback)

    # BUG-FIX: use current_price for ATR% calculation (not entry_price)
    atr_pct = atr / current_price
    k = _atr_multiplier(token, atr_pct, override_k=override_k)
    atr_distance = k * atr

    # Apply minimum ATR% floor — don't let low-vol tokens get razor SLs
    effective_sl_pct = max(atr_distance / current_price, MIN_ATR_PCT)
    # Apply maximum cap
    effective_sl_pct = min(effective_sl_pct, MAX_SL_PCT)

    # BUG-FIX: SL distance is from current_price, not entry_price
    if direction == 'LONG':
        sl = current_price * (1 - effective_sl_pct)
    else:
        sl = current_price * (1 + effective_sl_pct)

    log(f'  [ATR] {token} {direction}: entry={entry_price}, cur={current_price}, ATR={atr:.6f} ({atr_pct*100:.2f}%), '
        f'k={k}, dist={atr_distance:.6f}, effective={effective_sl_pct*100:.2f}%, SL={sl:.6f}')
    return sl

def _compute_dynamic_tp(token: str, direction: str, entry_price: float,
                        current_price: float,
                         tp_pct_fallback: float = 0.05,
                         override_k: float = None) -> float:
    """
    Compute dynamic TP using ATR(14) — parallel to _compute_dynamic_sl().
    TP = current_price ± (k_tp * ATR(14)) where k_tp = 2.5 × k_SL.
    With new k table: <1%→k=1.0, 1-3%→k=2.0, >3%→k=2.5.

    k_tp multipliers (k_tp = 2.5 × k_SL):
      LOW_VOLATILITY:    k_tp=2.5   (2.5× 1.0)
      NORMAL_VOLATILITY: k_tp=5.0   (2.5× 2.0)
      HIGH_VOLATILITY:   k_tp=6.25  (2.5× 2.5)
    Minimum TP% floor: never tighter than tp_pct_fallback (default 5%).
    Maximum TP cap: never wider than 15% to avoid absurdly wide targets.

    BUG-FIX: ATR distance is now computed from current_price (not entry_price),
    which is the correct volatility-based TP placement.
    """
    MIN_TP_PCT = 0.015    # 1.5% — below this, fall back to fixed %
    MAX_TP_PCT = 0.15    # 15% — never tighter than this

    atr = _get_atr(token)
    if atr is None:
        # Fall back to fixed % TP
        if direction == 'LONG':
            return entry_price * (1 + tp_pct_fallback)
        else:
            return entry_price * (1 - tp_pct_fallback)

    # BUG-FIX: use current_price for ATR% calculation (not entry_price)
    atr_pct = atr / current_price
    atr_pct_val = atr_pct  # for clarity

    # k_tp = 2.5× the SL k multiplier (k_tp = 2.5 × k_SL)
    # With new k table: <1%→k=1.0, 1-3%→k=2.0, >3%→k=2.5
    if override_k is not None:
        k_tp = override_k * 2.5
    elif atr_pct_val < 0.01:
        k_tp = 2.5    # 2.5 × 1.0 (LOW_VOL)
    elif atr_pct_val > 0.03:
        k_tp = 6.25   # 2.5 × 2.5 (HIGH_VOL)
    else:
        k_tp = 5.0    # 2.5 × 2.0 (NORMAL_VOL)

    atr_distance_tp = k_tp * atr

    # Apply minimum TP% floor — don't let low-vol tokens get razor TPs
    effective_tp_pct = max(atr_distance_tp / current_price, MIN_TP_PCT)
    # Apply maximum cap
    effective_tp_pct = min(effective_tp_pct, MAX_TP_PCT)

    # BUG-FIX: TP distance is from current_price, not entry_price
    if direction == 'LONG':
        tp = current_price * (1 + effective_tp_pct)
    else:
        tp = current_price * (1 - effective_tp_pct)

    log(f'  [ATR-TP] {token} {direction}: entry={entry_price}, cur={current_price}, ATR={atr:.6f} ({atr_pct_val*100:.2f}%), '
        f'k_tp={k_tp}, dist={atr_distance_tp:.6f}, effective={effective_tp_pct*100:.2f}%, TP={tp:.6f}')
    return tp

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
SPEED_WEIGHT = 0.15  # 15% of total hot-set score comes from speed percentile
try:
    from speed_tracker import SpeedTracker
    speed_tracker_dr = SpeedTracker()
except Exception as e:
    print(f"[decider-run] SpeedTracker unavailable: {e}")
    speed_tracker_dr = None

# Hot-set discipline: track when ai_decider last ran compaction
# The hot-set is THE single gate for execution — it must come from ai_decider output.
# decider-run runs every 1 min but ai_decider only runs every 10 min.
# We gate new approvals on ai_decider having run recently.
_HOTSET_LAST_UPDATED_FILE = '/var/www/hermes/data/hotset_last_updated.json'

def _get_hotset_last_updated():
    """Return Unix timestamp of last ai_decider compaction, or 0 if never."""
    try:
        if os.path.exists(_HOTSET_LAST_UPDATED_FILE):
            with open(_HOTSET_LAST_UPDATED_FILE) as f:
                data = json.load(f)
            return data.get('last_compaction_ts', 0)
    except Exception:
        pass
    return 0

def _set_hotset_last_updated():
    """Called by ai_decider after each compaction run."""
    try:
        with FileLock('hotset_last_updated'):
            with open(_HOTSET_LAST_UPDATED_FILE, 'w') as f:
                json.dump({'last_compaction_ts': time.time()}, f)
    except Exception:
        pass

BRAIN_CMD       = '/root/.hermes/scripts/brain.py'
SERVER          = 'Hermes'
MAX_POS         = 10
POSITION_SIZE_USD = 50.0   # $50 actual capital per trade
LOG_FILE        = '/var/www/hermes/logs/signals.log'
DELAYED_FILE    = '/var/www/hermes/data/pending-delayed-entries.json'
AB_CONFIG_FILE  = '/root/.hermes/data/ab-test-config.json'
EPSILON         = 0.20   # 20% exploration rate

# Rate limit: cache last entry timestamp, refresh from DB every 5 minutes
_RATE_LIMIT_CACHE = {"last_entry": None, "cached_at": 0}
_RATE_LIMIT_TTL    = 300  # seconds

os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
os.makedirs(os.path.dirname(DELAYED_FILE), exist_ok=True)

# ─── Direction Awareness ─────────────────────────────────────────────────────
# If a direction has < 50% win rate in recent history, pause it.
# This prevents the system from bleeding on a consistently losing direction.
_DIR_WR_CACHE = {}      # {(token, direction): (wr, count, timestamp)}
_DIR_WR_TTL    = 3600    # 1 hour

def _get_direction_wr(token: str, direction: str) -> tuple:
    """Return (win_rate_pct, trade_count) for a token+direction in last 7 days."""
    import time
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
            WHERE token=? AND direction = %s
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

def log(msg):
    ts = time.strftime('%Y-%m-%d %H:%M:%S')
    line = f'{ts} {msg}'
    print(line)
    try:
        with open(LOG_FILE, 'a') as f:
            f.write(line + '\n')
    except:
        pass


def _update_decider_heartbeat():
    """Update pipeline heartbeat for decider-run."""
    import json
    hb_file = '/var/www/hermes/data/pipeline_heartbeat.json'
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
    import time
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

def _load_ab_config():
    try:
        with open(AB_CONFIG_FILE) as f:
            return json.load(f)
    except Exception:
        return {'enabled': False, 'tests': []}


def get_ab_variant(test_name: str, direction: str) -> dict:
    """
    Canonical A/B variant selection — delegates to ab_utils.get_ab_variant().
    This ensures Thompson sampling is used consistently everywhere.
    """
    from hermes_ab_utils import get_ab_variant as _get
    return _get(test_name, direction)


def _get_ab_variant_for_test(test_name: str, direction: str) -> dict:
    """
    Pick variant for a test using epsilon-greedy.
    Exploitation: best win_rate from ab_results.
    Exploration: weighted random from config.
    """
    cfg = _load_ab_config()
    if not cfg.get('enabled', False):
        return {}

    test = next((t for t in cfg.get('tests', []) if t['name'] == test_name), None)
    if not test:
        return {}

    # Try exploitation — read from ab_results
    try:
        import psycopg2
        conn = psycopg2.connect(**BRAIN_DB_DICT)
        cur = conn.cursor()
        cur.execute("""
            SELECT variant_id, win_rate_pct
            FROM ab_results
            WHERE test_name=%s AND trades >= 5
            ORDER BY win_rate_pct DESC
            LIMIT 1
        """, (test_name,))
        row = cur.fetchone()
        cur.close(); conn.close()
        exploit_vid = row[0] if row else None
    except Exception:
        exploit_vid = None

    if random.random() < EPSILON and exploit_vid:
        # Exploitation — use best variant
        for v in test.get('variants', []):
            if v.get('id') == exploit_vid:
                log(f'  [AB] EXPLOIT: {test_name} → {v["id"]} (win_rate={row[1]:.0f}%)')
                return v

    # Exploration — weighted random
    variants = [v for v in test.get('variants', []) if v.get('enabled', True)]
    if not variants:
        return {}
    total = sum(v.get('weight', 1) for v in variants)
    if total <= 0:
        # All weights are zero — fallback to first variant to avoid random.uniform(0,0)
        chosen = variants[0]
        log(f'  [AB] EXPLORE: {test_name} → {chosen["id"]} (all weights 0, fallback to first)')
        return chosen
    r = random.uniform(0, total)
    for v in variants:
        r -= v.get('weight', 1)
        if r <= 0:
            log(f'  [AB] EXPLORE: {test_name} → {v["id"]} (random)')
            return v
    return variants[0]



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
        token = entry['token'];
        direction  = entry['direction']
        # ── OPTION 1: Flip delayed entries too ─────────────────────────────
        if _FLIP_SIGNALS:
            direction = 'SHORT' if direction == 'LONG' else 'LONG'
            entry['direction'] = direction  # persist flipped direction
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

        # Delayed entry uses the same ATR-based SL and TP as normal entry
        # cur_price is both entry price (execution price) and current price
        sl = _compute_dynamic_sl(token, direction.upper(), cur_price, cur_price, sl_pct_val)
        tp = _compute_dynamic_tp(token, direction.upper(), cur_price, cur_price)
        cmd_side = 'buy' if direction.upper() == 'LONG' else 'sell'

        experiment = entry.get('experiment', 'control')
        variant_id = entry.get('variant_id', '')
        test_name  = entry.get('test_name', '')

        exp_arg = []
        if experiment and experiment != 'control':
            exp_json = json.dumps({'test': test_name, 'variant': variant_id, 'experiment': experiment})
            exp_arg = ['--experiment', exp_json]

        cmd = ([sys.executable, BRAIN_CMD, 'trade', 'add',
                token, cmd_side, str(POSITION_SIZE_USD), str(round(cur_price, 6)),
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
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
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


# ─── Trade Execution ──────────────────────────────────────────────

def execute_trade(token, direction, price, confidence, source,
                  leverage=10, paper=False, sl_pct=0.02,
                  trailing_activation=0.01, trailing_distance=0.01,
                  trailing_phase2_dist=None,
                  experiment=None, variant_id=None, test_name=None,
                  live_trading=False, flipped=False):
    """Execute a trade via brain.py. Returns (success, trade_id_or_msg)."""
    cmd_side = direction.lower()  # long or short

    # ── Pump Mode ─────────────────────────────────────────────
    # Spike/pump trades: tight SL/TP, NO trailing. Enter fast, exit fast.
    is_pump = 'pump-' in (source or '')

    if is_pump:
        sl_pct_val = PUMP_SL_PCT    # 1.5% SL
        tp_pct_val = PUMP_TP_PCT    # 2.5% TP
        trailing_activation = 0      # disable trailing
        trailing_distance   = 0
        log(f'  [PUMP MODE] {token} {direction} — SL={PUMP_SL_PCT*100:.1f}% TP={PUMP_TP_PCT*100:.1f}% NO trailing')
    else:
        sl_pct_val = float(sl_pct)  # sl_pct is already a fraction (0.01 = 1%)
        tp_pct_val = 0.05                 # 5% TP

    # ── Dynamic ATR-based SL ───────────────────────────────────────────────
    # Uses ATR(14) × k multiplier instead of fixed %. Falls back to sl_pct
    # if ATR is unavailable. Passes the MORE PROTECTIVE (tighter) of the two.
    # Uses price (signal price) as current_price proxy since trade executes immediately.
    sl = _compute_dynamic_sl(token, direction, price, price, sl_pct_val)

    if direction == 'LONG':
        tp = price * (1 + tp_pct_val)
    else:
        tp = price * (1 - tp_pct_val)

    # Sanity check: SL must provide real protection
    if direction == 'LONG' and sl >= price:
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

    cmd = [sys.executable, BRAIN_CMD, 'trade', 'add',
           token, cmd_side, str(POSITION_SIZE_USD), str(round(price, 6)),
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

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            for line in result.stdout.split('\n'):
                if 'trade #' in line.lower():
                    tid = line.lower().split('trade #')[1].split()[0]
                    if tid == 'none':
                        return False, f'brain.py rejected: conf-1s or HOTSET_BLOCKLIST blocked (output: {result.stdout.strip()[:80]})'
                    # Add traded coin to candle predictor watch list
                    try:
                        from candle_predictor import add_to_watch_list
                        add_to_watch_list(token)
                    except Exception as e:
                        log(f"[WARN] could not add {token} to candle watch list: {e}")
                    return True, f'trade #{tid}'
            return True, result.stdout.strip()[:80]
        else:
            return False, result.stderr.strip()[:80]
    except Exception as e:
        return False, str(e)[:80]


def close_position(token, reason):
    """Close an open position directly via brain.py.
    Does NOT overwrite entry_price — leaves it intact.
    exit_price and PnL will be filled in by hl-sync-guardian (via HL fill data)
    or by brain.py close_trade() if called from there.
    """
    try:
        import psycopg2
        conn = psycopg2.connect(**BRAIN_DB_DICT)
        cur = conn.cursor()
        # Read entry_price so we don't accidentally null it
        cur.execute("""
            UPDATE trades
            SET status='closed', close_time=NOW(),
                close_reason=%s
            WHERE server=%s AND token=%s AND status='open'
            RETURNING id, entry_price
        """, (reason, SERVER, token))
        row = cur.fetchone()
        conn.commit()
        cur.close(); conn.close()
        if row:
            log(f'CLOSED: {token} {reason} (trade #{row[0]}), entry={row[1]}')
            return True
        return False
    except Exception as e:
        log(f'CLOSE ERROR: {token} — {e}')
        return False


# ─── Hot-Set Auto-Approver (runs every minute in decider-run) ─────
# Per-token failure tracking for back-to-back cooldown
_HOTSET_FAILURE_FILE = '/var/www/hermes/data/hotset-failures.json'

# Rate limit: max 3 new hot-set approvals per minute (NEW RULE)
_HOTSET_APPROVAL_RATE_FILE = '/var/www/hermes/data/hotset-approval-rate.json'

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
            return 0, now  # new window
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
    """
    import time
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
    
    # Check if opposite direction has failures (to allow opposite signals through)
    opp_count = opp_failures.get('count', 0)
    opp_last = opp_failures.get('last', 0)
    if opp_count >= 2 and (now - opp_last) < COOLDOWN_SECS:
        return False, f'opposite {opp_direction} in cooldown ({opp_count} failures) — allowing {direction}'
    
    return False, ''

def _run_hot_set():
    """
    HOT-SET DISCIPLINE (SPEED FEATURE) — SOLE SOURCE OF TRUTH:
    The hot-set is THE single gate for execution. This function reads the
    canonical hot-set from /var/www/hermes/data/hotset.json (written by ai_decider
    after each compaction). Only signals in this JSON can be approved.

    If hotset.json doesn't exist or is stale (>11 min old), we block new approvals
    and only manage existing positions. This enforces the discipline that every
    approved signal must have survived ai_decider's compaction.

    Approves: conf-3s+ >= 65%, hmacd- (weight-based threshold), conf-2s >= 65%.
    Hot-set thresholds use centralized _get_source_weight() from ai-decider:
      mtf_macd + hmacd- = 1.2x → threshold 65/1.2 = 54% (boosted)
      pct-hermes + hmacd- = 0.6x → threshold 65/0.6 = 108% → effectively never

    Wave quality filter (SPEED FEATURE):
    - Counter-trend trap: PENALIZE stale tokens where regime disagrees with z-score direction
    - Speed boost: tokens with speed_percentile >= 80 get 20% easier entry threshold
    - Back-to-back failure cooldown: 2+ same-direction failures → block for 1hr
    """
    import sqlite3, os, time as _time, json as _json

    SIGNALS_DB = '/root/.hermes/data/signals_hermes_runtime.db'
    if not os.path.exists(SIGNALS_DB):
        return 0

    conn = sqlite3.connect(SIGNALS_DB)
    c = conn.cursor()
    now_str = _time.strftime('%Y-%m-%d %H:%M:%S')
    approved_count = 0

    # ── HOT-SET DISCIPLINE: Read canonical hot-set from JSON ─────────────────
    # hotset.json is written by ai_decider after each compaction.
    # It is the SOLE source of truth for what tokens are in the hot-set.
    hotset_file = '/var/www/hermes/data/hotset.json'
    if not os.path.exists(hotset_file):
        log('  🧊 [HOT-SET] hotset.json missing — ai_decider has not run yet')
        conn.close()
        return 0

    try:
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
    age = _time.time() - hotset_ts
    if age > 660:  # 11 minutes
        log(f'  🧊 [HOT-SET] hotset.json stale ({age:.0f}s) — blocking new approvals')
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

        # Iterate over canonical hot-set from JSON (SOLE source of truth)
        for hot_sig in hotset:
            token = hot_sig.get('token', '').upper()
            direction = hot_sig.get('direction', '').upper()
            rounds = hot_sig.get('review_count', 0)
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

            # FIX (2026-04-05): Defense-in-depth. is_solana_only tokens can't be traded
            # on Hyperliquid. ai_decider.py also checks this, but decider-run is the final gate.
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
            if _wave == 'neutral' and speed_tracker_dr is not None:
                spd = speed_tracker_dr.get_token_speed(token)
                if spd:
                    _wave = spd.get('wave_phase', 'neutral')
                    _overext = spd.get('is_overextended', False)
                    _momentum = spd.get('momentum_score', 50.0)
                    _vel = spd.get('price_velocity_5m', 0.0)

            # BLOCK overextended tokens: velocity has moved too far from the 15m
            # baseline. Example: vel_5m > +3% means price ripped up too fast — reversal
            # is more likely than continuation. Entering here is catching the top.
            # Exception: bottoming + LONG is always allowed (the bounce IS the reversal).
            if _overext and not (_wave == 'bottoming' and direction == 'LONG'):
                log(f'  🌊 [HOT-SET] {token} {direction} BLOCKED: overextended '
                    f'(vel={_vel:+.2f}%, phase={_wave})')
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

            effective_conf = float(sig_conf) * wave_mult
            confidence = effective_conf  # BUG FIX (2026-04-10): was never initialized; penalties now apply to this
            reason_suffix = f'+{wave_tag}'

            # ── COUNTER-TREND TRAP FILTER ────────────────────────────────────
            # If the token's own z-score contradicts the direction AND we're in
            # the corresponding regime → PENALIZE (not block). Strong signals survive.
            trap_penalty, trap_reason = _check_counter_trend_trap(token, direction)
            if trap_penalty > 0:
                confidence -= trap_penalty
                if confidence < 55:
                    log(f'  🧊 [HOT-SET] {token} {direction} BLOCKED: {trap_reason} '
                        f'(counter-trend trap penalty={trap_penalty}, conf below threshold)')
                    _record_hotset_failure(token, direction, failures)
                    continue
                log(f'  🧊 [HOT-SET] {token} {direction} penalized {trap_penalty}pts: {trap_reason} (conf now {confidence:.0f}%)')

            # Regime check for ALL signal types. Counter-regime → PENALIZE (not block).
            # Strong signals with high enough confidence get through after penalty.
            # Regime-aligned signals get through untouched.
            try:
                regime, regime_conf = get_regime(token)
                if regime != 'NEUTRAL' and regime_conf > 50:
                    if (regime == 'LONG_BIAS' and direction == 'SHORT') or \
                       (regime == 'SHORT_BIAS' and direction == 'LONG'):
                        # PENALTY not block: scale penalty with regime confidence (max 30 pts)
                        penalty = min(int(regime_conf * 0.4), 30)
                        confidence -= penalty
                        if confidence < 55:
                            log(f'  🧊 [HOT-SET] {token} {direction} penalized {penalty}pts below threshold: regime={regime} ({regime_conf:.0f}%) fights direction')
                            _record_hotset_failure(token, direction, failures)
                            continue
                        log(f'  🧊 [HOT-SET] {token} {direction} penalized {penalty}pts for counter-regime (conf now {confidence:.0f}%)')
            except Exception as e:
                log(f'  ⚠️ [HOT-SET] {token} regime check error: {e}')

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
                        # Price at local bottom but SHORT direction — PENALIZE unless momentum is low
                        if _momentum not in ('bottoming', 'neutral'):
                            confidence -= 20
                            if confidence < 55:
                                log(f'  📍 [HOT-SET] {token} {direction} BLOCKED: token regime tier={_z_tier}(z={_z:+.2f}) fights direction (momentum={_momentum})')
                                _record_hotset_failure(token, direction, failures)
                                continue
                            log(f'  📍 [HOT-SET] {token} {direction} penalized 20pts: tier={_z_tier}+SHORT+momentum={_momentum} (conf now {confidence:.0f}%)')
                    elif _z_tier == 'falling' and direction == 'LONG':
                        # Price at local top but LONG direction — PENALIZE unless bottoming
                        if _momentum != 'bottoming':
                            confidence -= 20
                            if confidence < 55:
                                log(f'  📍 [HOT-SET] {token} {direction} BLOCKED: token regime tier={_z_tier}(z={_z:+.2f}) fights direction (momentum={_momentum})')
                                _record_hotset_failure(token, direction, failures)
                                continue
                            log(f'  📍 [HOT-SET] {token} {direction} penalized 20pts: tier={_z_tier}+LONG+momentum={_momentum} (conf now {confidence:.0f}%)')

            # Signal-type specific approval logic
            if sig_type == 'confluence':
                try:
                    num_src = int((sig_src or 'conf-1s').split('-')[1].rstrip('s'))
                except (ValueError, IndexError):
                    num_src = 1
                # FIX (2026-04-05): conf-1s = single-source = too weak, hard ban
                if num_src < 2:
                    log(f'  🚫 [HOT-SET] {token} {direction} BLOCKED: conf-1s (single-source, min 2 required)')
                    _record_hotset_failure(token, direction, failures)
                    continue
                # FIX (2026-04-05): speed=0% = stale token, hard ban
                spd = speed_tracker_dr.get_token_speed(token) if speed_tracker_dr else None
                sp = spd.get('speed_percentile', 50.0) if spd else 50.0
                if sp == 0:
                    log(f'  🚫 [HOT-SET] {token} {direction} BLOCKED: speed=0% (stale token)')
                    _record_hotset_failure(token, direction, failures)
                    continue
                # Use penalized confidence for threshold comparison (BUG FIX 2026-04-10)
                base_threshold = 65
                if num_src >= 3:
                    should_approve = confidence >= base_threshold
                    reason = f'hot-conf-{num_src}s @{sig_conf:.0f}%{reason_suffix}'
                else:
                    should_approve = confidence >= base_threshold
                    reason = f'hot-conf-{num_src}s @{sig_conf:.0f}%{reason_suffix}'
            elif sig_src and sig_src.startswith('hmacd-'):
                # FIX (2026-04-05): speed=0% = stale token, hard ban
                spd2 = speed_tracker_dr.get_token_speed(token) if speed_tracker_dr else None
                sp2 = spd2.get('speed_percentile', 50.0) if spd2 else 50.0
                if sp2 == 0:
                    log(f'  🚫 [HOT-SET] {token} {direction} BLOCKED: speed=0% (stale token)')
                    _record_hotset_failure(token, direction, failures)
                    continue
                # Apply centralized source weight from ai-decider
                sw = _get_source_weight(sig_type, sig_src)
                threshold = min(99, 65.0 / sw)
                should_approve = confidence >= threshold  # BUG FIX: was effective_conf (penalties now apply)
                reason = f'hot-hmacd @{sig_conf:.0f}%[{sw:.1f}x]{reason_suffix}'
            else:
                # Any other signal type (mtf_macd, mtf_zscore, percentile_rank, etc.)
                # must also pass speed=0% ban; use base 65% threshold on penalized confidence
                spd3 = speed_tracker_dr.get_token_speed(token) if speed_tracker_dr else None
                sp3 = spd3.get('speed_percentile', 50.0) if spd3 else 50.0
                if sp3 == 0:
                    log(f'  🚫 [HOT-SET] {token} {direction} BLOCKED: speed=0% (stale token)')
                    _record_hotset_failure(token, direction, failures)
                    continue
                should_approve = confidence >= 65  # BUG FIX: was missing entirely (inherited prev branch value)
                reason = f'hot-other @{sig_conf:.0f}%{reason_suffix}'

            if should_approve:
                # Rate limit check: only 3 new approvals per minute
                rate_count, rate_window = _get_hotset_approval_rate()
                if rate_count >= 3:
                    log(f'  🚫 [HOT-SET] Rate limit reached ({rate_count}/3) — {token} {direction} queued for next window')
                    break  # stop approving more; next cycle will pick up
                c.execute("""
                    UPDATE signals SET decision='APPROVED', updated_at=?
                    WHERE id=? AND executed=0
                """, (now_str, sig_id))
                conn.commit()
                approved_count += 1
                _increment_hotset_approval_rate(rate_count + 1, rate_window)
                log(f'  🔥 [HOT-SET] {token} {direction} {reason} (survived r{rounds}) [{rate_count+1}/3]')
                # ── Hotset checkpoint & event ─────────────────────────────
                try:
                    checkpoint_write('hotset_built', {'approved_count': approved_count + 1, 'hotset_size': len(hotset)})
                    log_event(EVENT_HOTSET_UPDATED, {'approved_count': approved_count + 1, 'hotset_size': len(hotset)})
                except Exception as e:
                    pass  # never crash pipeline
    except Exception as e:
        import traceback; traceback.print_exc()
        log(f'HOT-SET error: {e}')
    finally:
        conn.close()

    return approved_count

def _record_hotset_failure(token: str, direction: str, failures: dict):
    """Record a failed trade for back-to-back cooldown tracking."""
    import time
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


def _check_counter_trend_trap(token: str, direction: str) -> tuple:
    """
    SPEED FEATURE: Counter-trend trap detection.
    PENALTY not block: strong signals survive despite counter-trend setup.

    Returns (penalty: int, reason: str) — penalty=0 means no counter-trend penalty.
    Only penalized if: is_stale=True AND z_score direction contradicts regime.
    """
    if speed_tracker_dr is None:
        return 0, ''

    spd = speed_tracker_dr.get_token_speed(token)
    if not spd or not spd.get('is_stale'):
        return 0, ''

    z_score = _get_token_zscore(token)
    regime, regime_conf = get_regime(token)

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
        now = _time.time()
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
            gap = (datetime.datetime.now() - row[0].replace(tzinfo=None)).total_seconds()
            if gap < 15:
                log(f'SKIP: Rate limit — last entry {gap:.0f}s ago (min 15s gap)')
                return 0, 0
    except Exception as e:
        import traceback; traceback.print_exc()
        log(f'Rate limit check failed (DB error): {e} — proceeding without rate limit', 'WARN')

    # Get approved signals
    # Clean up stale approvals before fetching (expire anything >1h old)
    stale = cleanup_stale_approved(hours=1)
    if stale > 0:
        log(f'Expired {stale} stale approved signals (>1h old)')

    approved = get_approved_signals(hours=24)
    log(f'Approved signals: {len(approved)}')

    # ── HOT-SET DISCIPLINE: NO BYPASS ─────────────────────────────────────
    # Every entry comes from the hot-set. The >=95% confluence fallback has been
    # removed — signals that haven't survived ai_decider compaction do NOT execute.
    # If approved is empty, we wait for the next ai_decider run to populate the hot-set.
    # This is the "no shortcuts" rule from surfing.md.

    # ── Confidence floor: reject signals below 65% ──────────────────────────
    # Raised from 70% on 2026-04-02. The _run_hot_set() approver runs every minute
    # (not every 10min like ai-decider) and approves at 65%+ for hot confluence signals.
    # 65% is the floor for any signal reaching execution — hot-set tokens that survived
    # AI review at this level are pre-qualified. Individual RSI/MACD below 65% are blocked.
    MIN_EXEC_CONFIDENCE = 65
    approved = [s for s in approved if s.get('final_confidence', 0) >= MIN_EXEC_CONFIDENCE]
    if not approved:
        log(f'No signals above {MIN_EXEC_CONFIDENCE}% confidence — skipping execution')
        return 0, 0

    # ── Multi-factor execution ranking ─────────────────────────────────────────
    # Sort approved signals by execution score: higher = better trade candidate.
    # Score = confidence × speed_mult × z_mult
    #   speed_mult: 1.0 + (speed_pctl/100 × 0.15)  → fast movers get priority
    #   z_mult:     1.0 + (|z_score|/10 × 0.10)     → further from mean = stronger signal
    # This ensures we execute the BEST signal first when slots are limited.
    def _exec_score(sig):
        conf = sig.get('final_confidence', 0)
        tok = sig.get('token', '').upper()
        z = sig.get('z_score') or 0.0
        spd = speed_tracker_dr.get_token_speed(tok) if speed_tracker_dr else None
        sp = spd.get('speed_percentile', 50.0) if spd else 50.0
        speed_mult = 1.0 + (sp / 100.0 * 0.15)
        z_mult = 1.0 + (abs(z) / 10.0 * 0.10)
        return conf * speed_mult * z_mult

    scored = sorted(approved, key=_exec_score, reverse=True)
    entered = 0
    skipped = 0

    for i, sig in enumerate(scored):
        # BUG-26: extract signal_id for atomic claim BEFORE any trade execution.
        # This prevents double-execution when multiple scripts run same minute.
        sig_id = sig.get('signal_id')
        token = sig.get('token', '').upper()
        direction = sig['direction']
        confidence = sig['final_confidence']
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
                mark_signal_executed(token, direction)
                skipped += 1
                continue
        if price > 1_000_000 or price < 0.00001:
            log(f'SKIP: {token} price {price} out of absolute bounds [$0.00001-$1_000_000]')
            mark_signal_executed(token, direction)
            skipped += 1
            continue

        # Check if already open
        if is_position_open(token):
            log(f'SKIP: {token} already open')
            mark_signal_executed(token, direction)
            skipped += 1
            continue

        # ── Counter-trend trap guard at execution time ───────────────────
        # Even if _run_hot_set() passed this signal, re-check at execution time.
        # Conditions may have changed (z-score moved, speed changed).
        trap_blocked, trap_reason = _check_counter_trend_trap(token, direction)
        if trap_blocked:
            log(f'  🧊 [EXEC-BLOCK] {token} {direction}: {trap_reason}')
            mark_signal_executed(token, direction)
            skipped += 1
            continue

        # ── Regime filter for approved signals (same as HOT-SET, 2026-04-05) ─
        # Approved signals bypass HOT-SET regime check — close that gap here.
        # Full coverage: is_delisted + blindspot + NEUTRAL + weak_conf + counter-regime
        try:
            # Case 0: Not tradeable on Hyperliquid (hard blocklist + HL universe check)
            if is_delisted(token):
                log(f'  🧊 [EXEC-BLOCK] {token} {direction} blocked: not tradeable on Hyperliquid')
                mark_signal_executed(token, direction)
                skipped += 1
                continue
            regime, regime_conf = get_regime(token)
            # Case 1: blindspot — token not in regime data
            if regime is None or regime == 'NOT_IN_JSON':
                log(f'  🧊 [EXEC-BLOCK] {token} {direction} blocked: regime blindspot (not in regime_4h.json)')
                mark_signal_executed(token, direction)
                skipped += 1
                continue
            # Case 2: NEUTRAL regime — should wait, not execute
            if regime == 'NEUTRAL' and regime_conf > 60:
                log(f'  🧊 [EXEC-BLOCK] {token} {direction} blocked: NEUTRAL regime ({regime_conf:.0f}%)')
                mark_signal_executed(token, direction)
                skipped += 1
                continue
            # Case 3: weak confidence — not enough regime conviction
            if regime_conf < 50:
                log(f'  🧊 [EXEC-BLOCK] {token} {direction} blocked: weak regime conf ({regime_conf:.0f}% < 50%)')
                mark_signal_executed(token, direction)
                skipped += 1
                continue
            # Case 4: counter-regime — fighting the trend → PENALIZE not block
            if (regime == 'LONG_BIAS' and direction == 'SHORT') or \
               (regime == 'SHORT_BIAS' and direction == 'LONG'):
                penalty = min(int(regime_conf * 0.4), 30)
                confidence -= penalty
                if confidence < MIN_EXEC_CONFIDENCE:
                    log(f'  🧊 [EXEC-BLOCK] {token} {direction} penalized {penalty}pts below exec threshold: counter-regime ({regime} {regime_conf:.0f}%)')
                    mark_signal_executed(token, direction)
                    skipped += 1
                    continue
                log(f'  🧊 [EXEC-BLOCK] {token} {direction} penalized {penalty}pts for counter-regime (conf now {confidence:.0f}%)')
        except Exception as e:
            log(f'  ⚠️ [EXEC-BLOCK] {token} regime check error: {e}')

        # FIX (2026-04-05): conf-1s = single-source, too weak — hard ban on approved signals too.
        # Only block conf-1s (true single-source confluence). Merged signals with 1 type
        # (count=1) have legitimate sources like 'mtf_macd', 'hzscore' — don't block those.
        # Block conf-1s, conf-2s etc. (not 'hzscore' or 'hmacd-').
        sig_src = sig.get('source', '') or ''
        if sig_src.startswith('conf-') or sig_src.endswith('s'):
            # It's a confluence source (conf-1s, conf-2s, fallback-conf-3s, etc.)
            if sig_src == 'conf-1s' or sig_src.startswith('conf-1s'):
                log(f'  🚫 [EXEC-BLOCK] {token} {direction} blocked: {sig_src} (single-source, min 2 required)')
                mark_signal_executed(token, direction)
                skipped += 1
                continue

        # FIX (2026-04-05): speed=0% = stale token — hard ban
        sp_exec = speed_tracker_dr.get_token_speed(token) if speed_tracker_dr else None
        sp_exec_val = sp_exec.get('speed_percentile', 50.0) if sp_exec else 50.0
        if sp_exec_val == 0:
            log(f'  🚫 [EXEC-BLOCK] {token} {direction} blocked: speed=0% (stale token)')
            mark_signal_executed(token, direction)
            skipped += 1
            continue

        # Check loss cooldown — block same direction after a loss
        if is_loss_cooldown_active(token, direction):
            log(f'SKIP: {token} {direction} in loss cooldown')
            skipped += 1
            continue

        # Check win cooldown — block same direction after a win (prevents re-entry loop)
        if _is_win_cooldown_active(token, direction):
            log(f'SKIP: {token} {direction} in win cooldown')
            skipped += 1
            continue

        # ── Wrong-Side Learning ───────────────────────────────────
        # If this token+direction has a history of wrong-side entries (>3x avg counter-move >1.5%),
        # penalize confidence by 15 pts. If below threshold after penalty, skip.
        is_risky, risk_reason = is_wrong_side_risky(token, direction, confidence)
        if is_risky:
            adjusted_conf = confidence - 15
            if adjusted_conf < 55:  # below new threshold
                log(f'SKIP: {token} {direction} {risk_reason} (conf {confidence:.0f}% -> {adjusted_conf:.0f}%)')
                skipped += 1
                continue
            log(f'WARN: {token} {direction} {risk_reason} (conf {confidence:.0f}% -> {adjusted_conf:.0f}%)')
            confidence = adjusted_conf

        # ── Direction Awareness ───────────────────────────────────
        # Skip LONG/SHORT if it has < 50% win rate in recent history (min 3 trades)
        wr, wr_count = _get_direction_wr(token, direction)
        if wr < 50 and wr_count >= 3:
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

        # ATR-based SL and TP (same formula used throughout)
        # Uses price (signal price) as current_price proxy since trade executes immediately.
        sl = _compute_dynamic_sl(token, direction, price, price, sl_pct)
        tp = _compute_dynamic_tp(token, direction, price, price)

        # Recalculate speed_pctl for logging (sp was from _exec_score scope)
        sig_spd = speed_tracker_dr.get_token_speed(token) if speed_tracker_dr else None
        sp_now = sig_spd.get('speed_percentile', 50.0) if sig_spd else 50.0
        log(f'EXEC: {token} {direction} @ ${price:.6f} conf={confidence:.0f}% '
            f'SL=${sl:.4f} TP=${tp:.4f} [{source}] '
            f'[SL={sl_pct:.1f}% trail={trailing_activation*100:.1f}%/{trailing_distance*100:.1f}%]'
            f'[spd={sp_now:.0f}%]')

        if dry_run:
            log(f'  → [DRY-RUN] Would enter {token} {direction}')
            mark_signal_executed(token, direction)
            entered += 1
            # Don't increment open_count in dry-run — no real position opened
            continue

        # Get per-token leverage from Hyperliquid
        lev = get_max_leverage(token)
        lev = min(lev, 5)   # hard cap at 5x (safer for all directions)

        # BUG-26 fix: claim signal atomically BEFORE brain.py call.
        # This prevents double-execution when multiple scripts run same minute.
        # Use signal_id if available, else fall back to legacy token+direction match.
        claimed = mark_signal_executed(token, direction, signal_id=sig_id)
        if sig_id is not None and claimed == 0:
            # Signal already claimed by another process — skip this one
            log(f'SKIP: {token} {direction} — signal {sig_id} already claimed (executed by another runner)')
            skipped += 1
            continue

        # ── OPTION 1: Flip signal direction before trading ───────────────
        # See INCIDENT_WR_FAILURE.md — test if signals are direction-inverted
        flipped_direction = None
        if _FLIP_SIGNALS:
            flipped_direction = 'SHORT' if direction == 'LONG' else 'LONG'
            log(f'  [FLIP] {token} {direction} → {flipped_direction} (WR incident fix)')
            direction = flipped_direction

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
            live_trading=not paper, flipped=bool(flipped_direction))

        if success:
            log(f'  → ENTERED: {token} {direction} ({msg})')
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
                    from signal_schema import _get_conn, _runtime
                    conn = _get_conn(_runtime())
                    conn.execute(
                        "UPDATE signals SET executed=0, decision='APPROVED', updated_at=CURRENT_TIMESTAMP WHERE id=?",
                        (sig_id,))
                    conn.commit()
                    conn.close()
                    log(f'  → ROLLED BACK signal {sig_id} (trade failed: {msg[:60]})')
                except Exception as rb_e:
                    log(f'  → rollback warning for signal {sig_id}: {rb_e}')
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
