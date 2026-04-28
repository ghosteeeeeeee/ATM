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
from paths import *
# NOTE: ai_decider.py is legacy (LLM-based compaction). The current pipeline uses:
#   signal_compactor.py (runs every 1 min via hermes-signal-compactor.timer) → writes hotset.json
#   decider_run.py (runs every 1 min via hermes-pipeline.timer) → reads hotset.json, executes trades
# get_regime from ai_decider is unused — regime is pre-computed in hotset.json by signal_compactor
from _secrets import BRAIN_DB_DICT
from position_manager import (get_position_count, is_position_open, enforce_max_positions,
                              get_trade_params, set_loss_cooldown,
                              is_wrong_side_risky)
from signal_schema import _is_loss_cooldown_active
from signal_gen import PUMP_SL_PCT, PUMP_TP_PCT
from hermes_constants import SHORT_BLACKLIST, LONG_BLACKLIST, MAX_OPEN_POSITIONS
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
# k multipliers (confirmed against hermes_constants.py ATR_K_LOW/NORMAL/HIGH_VOL):
#   LOW_VOLATILITY:    k=1.0  (SL ≈ 1× ATR — tight for low-vol tokens)
#   NORMAL_VOLATILITY: k=2.0  (SL ≈ 2× ATR — gives trade room to breathe)
#   HIGH_VOLATILITY:   k=2.5  (SL ≈ 2.5× ATR — tokens like TAO, SOL need room)
# Minimum SL guard: never tighter than sl_pct (A/B test value), use ATR if wider.
import time as _time


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

def _set_hotset_last_updated():
    """Called by signal_compactor after each compaction run."""
    try:
        with FileLock('hotset_last_updated'):
            with open(_HOTSET_LAST_UPDATED_FILE, 'w') as f:
                json.dump({'last_compaction_ts': time.time()}, f)
    except Exception:
        pass

BRAIN_CMD       = '/root/.hermes/scripts/brain.py'
SERVER          = 'Hermes'
MAX_POS         = MAX_OPEN_POSITIONS
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
        # A/B TEST DISABLED (2026-04-17) — ATR handles SL/TP via position_manager.
        # position_manager._collect_atr_updates() sets dynamic ATR-based SL/TP within 1 min.
        sl_pct_val = 0.0  # defer to ATR
        tp_pct_val = 0.0  # defer to ATR

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
            log(f'  ⛔ DUPLICATE ENTRY BLOCKED: {token} {direction} already open (#{dup_id}, pnl={float(dup_pnl or 0):.3f}%) — skipping')
            return False, f'duplicate_entry_blocked token={token} direction={direction} existing_id={dup_id}'
    except Exception as dup_err:
        log(f'  [WARN] Duplicate-entry guard DB check failed for {token}: {dup_err}', 'WARN')
        # Don't block on DB errors — proceed with the trade

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            for line in result.stdout.split('\n'):
                if 'trade #' in line.lower():
                    tid = line.lower().split('trade #')[1].split()[0]
                    if tid == 'none':
                        return False, f'brain.py rejected: conf-1s or blacklist blocked (output: {result.stdout.strip()[:80]})'

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

    FIX (2026-04-22): Record loss cooldown in BOTH stores so the same direction
    cannot immediately re-enter. Counter-signals/manual closes should block
    re-entry to prevent immediate whipsaw in the opposite direction.
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
            RETURNING id, entry_price, direction
        """, (reason, SERVER, token))
        row = cur.fetchone()
        conn.commit()
        cur.close(); conn.close()
        if row:
            trade_id, entry_price_val, trade_dir = row
            log(f'CLOSED: {token} {reason} (trade #{trade_id}), entry={entry_price_val}')
            # Record cooldown for the direction that was closed so the same direction
            # cannot immediately re-enter — but only on LOSS (FIX 2026-04-23: was
            # writing cooldown on EVERY close regardless of outcome, flooding PG with
            # 200+ active cooldowns and blocking all signals from entering hot-set).
            if trade_dir and 'loss' in reason.lower():
                try:
                    from position_manager import set_loss_cooldown
                    set_loss_cooldown(token, trade_dir)
                except Exception as cd_err:
                    log(f'loss cooldown error: {cd_err}')
                try:
                    from signal_schema import set_cooldown
                    set_cooldown(token.upper(), trade_dir.upper(), hours=1)
                except Exception as pg_err:
                    log(f'PostgreSQL cooldown error: {pg_err}', 'WARN')
            return True
        return False
    except Exception as e:
        log(f'CLOSE ERROR: {token} — {e}')
        return False


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
    now_str = _time.strftime('%Y-%m-%d %H:%M:%S')
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
    age = _time.time() - hotset_ts
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
    # removed — signals that haven't survived signal_compactor compaction do NOT execute.
    # If approved is empty, we wait for the next signal_compactor run to populate the hot-set.
    # This is the "no shortcuts" rule from surfing.md.

    # ── Confidence floor: reject signals below 50% ──────────────────────────
    # Lowered from 65% on 2026-04-11 — signals were being generated at 59-65% conf
    # but 100% blocked at execution gate, causing empty hotset and pipeline stall.
    # 50% is still a meaningful quality floor for pre-qualified hot-set tokens.
    MIN_EXEC_CONFIDENCE = 50
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

        # ── Surfing gate: skip if signal hasn't survived enough hot-set cycles ──
        # hot_rounds comes from get_approved_signals() (signal_schema.py line 1012)
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
        sig_type = sig.get('signal_type', '') or ''
        if sig_type == 'oc_pending':
            log(f'  🚫 [EXEC-BLOCK] {token} {direction} blocked: oc_pending signal (must survive hot-set compaction)')
            skipped += 1
            continue

        # ── Counter-trend trap guard at execution time ───────────────────
        # Even if _run_hot_set() passed this signal, re-check at execution time.
        # Conditions may have changed (z-score moved, speed changed).
        # Use hotset.json lookup for pre-computed regime (avoids redundant get_regime() call).
        _exec_regime, _exec_regime_conf = _hotset_regime.get(token, ('NEUTRAL', 0))
        trap_blocked, trap_reason = _check_counter_trend_trap(token, direction, _exec_regime, _exec_regime_conf)
        if trap_blocked:
            log(f'  🧊 [EXEC-BLOCK] {token} {direction}: {trap_reason}')
            if sig_id:
                mark_signal_executed(token, direction, 'SKIPPED', signal_id=sig_id)
            skipped += 1
            continue

        # ── Regime filter for approved signals (same as HOT-SET, 2026-04-05) ─
        # Approved signals bypass HOT-SET regime check — close that gap here.
        # Full coverage: is_delisted + blindspot + NEUTRAL + weak_conf + counter-regime
        try:
            # Case 0: Not tradeable on Hyperliquid (hard blocklist + HL universe check)
            if is_delisted(token):
                log(f'  🧊 [EXEC-BLOCK] {token} {direction} blocked: not tradeable on Hyperliquid')
                if sig_id:
                    mark_signal_executed(token, direction, 'SKIPPED', signal_id=sig_id)
                skipped += 1
                continue
            # Regime from hotset.json (pre-computed by signal_compactor — no ai_decider call)
            # _hotset_regime is built at lines ~1316-1324 from hotset.json per token
            regime, regime_conf = _hotset_regime.get(token, ('NEUTRAL', 0))
            # Case 1: blindspot — token not in regime data
            if regime is None or regime == 'NOT_IN_JSON':
                log(f'  🧊 [EXEC-BLOCK] {token} {direction} blocked: regime blindspot (not in regime_4h.json)')
                if sig_id:
                    mark_signal_executed(token, direction, 'SKIPPED', signal_id=sig_id)
                skipped += 1
                continue
            # Case 2: NEUTRAL regime — de-escalate gracefully, don't hard-block
            # Signal stays in pipeline to compete when/if regime becomes directional
            if regime == 'NEUTRAL' and regime_conf > 60:
                log(f'  📉 [DEESC] {token} {direction} de-escalated: NEUTRAL regime ({regime_conf:.0f}%)')
                # Don't mark_executed — let it survive and be reconsidered
                skipped += 1
                continue
            # Case 3: REMOVED (2026-04-17) — weak regime confidence should NOT block
            # execution of hot-set signals. If a signal survived signal_compactor compaction
            # and entered the hot-set, it's already been vetted. The regime_conf is
            # advisory — survival_score decay handles the fade. Blocking at execution
            # time prevents hot-set signals from ever trading. Let them execute.
            # Case 4: counter-regime — fighting the trend → PENALIZE lightly
            # Reduced 2026-04-17: was regime_conf*0.4 (30pt max) — too aggressive, blocked all
            # counter-regime signals during LONG_BIAS. New: regime_conf*0.15 (15pt max).
            # At 80% regime conf: old=30pts, new=12pts. A 77% signal survives at 65%.
            if (regime == 'LONG_BIAS' and direction == 'SHORT') or \
               (regime == 'SHORT_BIAS' and direction == 'LONG'):
                penalty = min(int(regime_conf * 0.15), 15)
                confidence -= penalty
                if confidence < MIN_EXEC_CONFIDENCE:
                    # De-escalate: don't execute this cycle, but keep signal alive
                    log(f'  📉 [DEESC] {token} {direction} counter-regime penalized {penalty}pts below exec threshold ({confidence:.0f}% < {MIN_EXEC_CONFIDENCE}%) — kept alive for organic de-escalation')
                    skipped += 1
                    continue
                log(f'  📉 [DEESC] {token} {direction} penalized {penalty}pts for counter-regime (conf now {confidence:.0f}%)')
        except Exception as e:
            log(f'  ⚠️ [EXEC-BLOCK] {token} regime check error: {e}')

        # conf-1s = single-source, too weak — hard ban. conf-2s+ are real confluence.
        # NOTE: hzscore and hmacd- also end in 's' but pass through because the
        # inner check only blocks conf-1s variants. This is intentional.
        sig_src = sig.get('source', '') or ''
        if sig_src.startswith('conf-') or sig_src.endswith('s'):
            # It's a confluence source (conf-1s, conf-2s, fallback-conf-3s, etc.)
            if sig_src == 'conf-1s' or sig_src.startswith('conf-1s'):
                log(f'  🚫 [EXEC-BLOCK] {token} {direction} blocked: {sig_src} (single-source, min 2 required)')
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
                    from signal_schema import rollback_signal_executed
                    rolled = rollback_signal_executed(token, direction, signal_id=sig_id)
                    if rolled:
                        log(f'  🔁 SIGNAL ROLLED BACK: {token} {direction} (sig#{sig_id}) — stays in hot-set for retry')
                    else:
                        log(f'  ⚠️ ROLLBACK FAILED: sig#{sig_id} already claimed by another process')
                except Exception as rb_e:
                    log(f'  ⚠️ ROLLBACK ERROR for sig#{sig_id}: {rb_e}')
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
