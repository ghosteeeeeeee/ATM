#!/usr/bin/env python3
"""
zscore_pump_hunter.py — Standalone z-score momentum live trade executor.

Runs independently of signal_gen/pipeline. Fires IMMEDIATE live trades on
Hyperliquid when z-score momentum signals fire. Manages its own positions.

Signal philosophy (momentum, NOT mean-reversion):
  +z > threshold  →  strong upward momentum, ride the move (LONG)
  -z < -threshold →  strong downward momentum, ride the move (SHORT)

Unlike pump_hunter's vol explosion (fade the spike), zscore_pump tracks momentum.
Both can run simultaneously — separate position tracking, separate timers.

Usage:
  python3 zscore_pump_hunter.py              # dry run
  python3 zscore_pump_hunter.py --live       # LIVE TRADING
  python3 zscore_pump_hunter.py --status     # show open positions
  python3 zscore_pump_hunter.py --close ALL  # close all positions
"""

import sys, os, time, json, math, statistics, sqlite3
from datetime import datetime, timezone
from decimal import Decimal, ROUND_UP

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paths import CANDLES_DB, HERMES_DATA
from hermes_constants import SHORT_BLACKLIST, LONG_BLACKLIST
from hyperliquid_exchange import (
    mirror_open, mirror_close, is_live_trading_enabled,
    get_open_hype_positions_curl, is_delisted, _sz_decimals,
    MARGIN_USAGE_PCT, MIN_TRADE_USDT,
    MAIN_ACCOUNT_ADDRESS,
    get_prices_curl,
)

# ── Mode ─────────────────────────────────────────────────────────────────────
LIVE_MODE = '--live' in sys.argv
if 'ZS_PUMP_LIVE' in os.environ:
    LIVE_MODE = os.environ['ZS_PUMP_LIVE'].lower() in ('1', 'true', 'yes')

# ── Paths ─────────────────────────────────────────────────────────────────────
TRACK_FILE = '/var/www/hermes/data/zscore-pump.json'
LOG_FILE   = os.path.join(HERMES_DATA, 'logs', 'zscore_pump_hunter.log')
TUNER_DB   = os.path.join(HERMES_DATA, 'zscore_momentum_tuner.db')

# ── Params (mirrors zscore_momentum.py defaults) ───────────────────────────────
DEFAULT_LOOKBACK    = 24
DEFAULT_THRESHOLD   = 2.0
MIN_SIGNALS_FOR_TUNED = 15

# ── Position sizing ───────────────────────────────────────────────────────────
ZS_PUMP_LEVERAGE      = 3
MAX_ZS_PUMP_POSITIONS = 3  # max simultaneous zscore-pump positions
ZS_PUMP_SIZE_PCT      = 0.10   # 10% of margin per trade

# ── Blacklist ─────────────────────────────────────────────────────────────────
ZS_PUMP_BLACKLIST = {}

# ─────────────────────────────────────────────────────────────────────────────
# Core z-score computation
# ─────────────────────────────────────────────────────────────────────────────

def compute_zscore(values):
    if len(values) < 2:
        return None
    mean = statistics.mean(values)
    std = statistics.stdev(values)
    if std == 0:
        return None
    return (values[-1] - mean) / std

# ─────────────────────────────────────────────────────────────────────────────
# Bulk price fetch (single query — mirrors zscore_momentum.py)
# ─────────────────────────────────────────────────────────────────────────────

def _get_all_token_prices(lookback_bars: int = 200) -> dict:
    """Fetch price history for all tokens from candles.db. Returns {token: [closes]}.
    Pre-loads all closes in one query for sweep speed. Oldest first."""
    try:
        conn = sqlite3.connect(CANDLES_DB, timeout=10)
        cur = conn.cursor()
        cur.execute("""
            SELECT token, close FROM candles_1m
            WHERE ts > (SELECT MAX(ts) FROM candles_1m) - ? * 60
            ORDER BY token, ts ASC
        """, (lookback_bars,))
        rows = cur.fetchall()
        conn.close()
        result = {}
        for token, close in rows:
            if token not in result:
                result[token] = []
            result[token].append(close)
        return result
    except Exception as e:
        log(f"get_all_token_prices error: {e}", "WARN")
        return {}

def _get_token_latest_price(token: str) -> float:
    """Get latest close price for a single token from live HL API."""
    try:
        prices = get_prices_curl([token])
        return float(prices[token]['close']) if token in prices and 'close' in prices[token] else 0.0
    except Exception:
        return 0.0
# ─────────────────────────────────────────────────────────────────────────────
# Token params from tuner DB
# ─────────────────────────────────────────────────────────────────────────────

_cached_params = None
_tradeable_tokens = None  # set of tradeable tokens (built once per process)

def _build_tradeable_set():
    """Build the set of tradeable tokens once per process via one API call."""
    global _tradeable_tokens
    if _tradeable_tokens is not None:
        return
    try:
        from hyperliquid_exchange import get_tradeable_tokens as _gtt
        _tradeable_tokens = _gtt()  # set of tradeable tokens
    except Exception:
        _tradeable_tokens = set()

def is_token_tradeable(token: str) -> bool:
    """Check if token is tradeable (not delisted). Uses cached set."""
    _build_tradeable_set()
    if _tradeable_tokens is None:
        # fallback to per-token check
        try:
            return not is_delisted(token)
        except Exception:
            return False
    return token.upper() in _tradeable_tokens

def _load_token_params_cached():
    global _cached_params
    if _cached_params is not None:
        return _cached_params
    try:
        conn = sqlite3.connect(TUNER_DB, timeout=5)
        cur = conn.cursor()
        cur.execute("SELECT token, lookback, threshold, win_rate, signal_count FROM token_best_zscore_config")
        rows = cur.fetchall()
        conn.close()
        _cached_params = {
            r[0]: {'lookback': r[1], 'threshold': r[2], 'win_rate': r[3], 'signal_count': r[4]}
            for r in rows
        }
        return _cached_params
    except Exception:
        _cached_params = {}
        return _cached_params

# ─────────────────────────────────────────────────────────────────────────────
# Position tracking
# ─────────────────────────────────────────────────────────────────────────────

def _write_json(data: dict):
    os.makedirs(os.path.dirname(TRACK_FILE), exist_ok=True)
    with open(TRACK_FILE, 'w') as f:
        json.dump(data, f, indent=2)

def _load_json() -> dict:
    try:
        if os.path.exists(TRACK_FILE):
            with open(TRACK_FILE) as f:
                return json.load(f)
    except Exception:
        pass
    return {'positions': {}, 'closed': []}

def load_positions() -> dict:
    return _load_json()

def get_open_zs_positions() -> dict:
    data = load_positions()
    return data.get('positions', {})

def add_zs_position(token: str, direction: str, signal: dict, size: float, entry_price: float):
    data = load_positions()
    pos = {
        'token': token.upper(),
        'direction': direction,
        'entry_price': entry_price,
        'signal_source': 'zscore_pump',
        'z_score': signal.get('z_score', 0),
        'lookback': signal.get('lookback', DEFAULT_LOOKBACK),
        'threshold': signal.get('threshold', DEFAULT_THRESHOLD),
        'size': size,
        'opened_at': time.time(),
        'signal_source': 'zscore_pump',
        'stop_pct': 3.0,
        'tp_pct': 2.0,
    }
    # Compute stop_price and revert_target from pct-based stops
    stop_pct = pos['stop_pct'] / 100.0
    tp_pct   = pos['tp_pct']   / 100.0
    if direction == 'LONG':
        pos['stop_price']    = round(entry_price * (1 - stop_pct), 8)
        pos['revert_target'] = round(entry_price * (1 + tp_pct),   8)
    else:  # SHORT
        pos['stop_price']    = round(entry_price * (1 + stop_pct), 8)
        pos['revert_target'] = round(entry_price * (1 - tp_pct),   8)

    data['positions'][token.upper()] = pos
    _write_json(data)
    log(f"ZS_TRACKED {token} {direction}: entry={entry_price:.6f} z={signal.get('z_score', 0):+.2f}", "TRACK")
    _create_brain_record(token, direction, signal, size, entry_price)

def _create_brain_record(token: str, direction: str, signal: dict, size: float, entry_price: float):
    try:
        import psycopg2
        from _secrets import BRAIN_DB_DICT
        conn = psycopg2.connect(**BRAIN_DB_DICT)
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO trades (
                token, direction, amount_usdt, entry_price, hl_entry_price,
                exchange, paper, server, status, open_time,
                pnl_usdt, pnl_pct, leverage, signal,
                sl_distance, trailing_activation, trailing_distance,
                is_guardian_close, guardian_closed
            )
            SELECT %s, %s, %s, %s, %s, 'Hyperliquid', false, 'Hermes', 'open', NOW(),
                   0, 0, %s, 'zscore_pump',
                   0.03, 0.01, 0.01, FALSE, FALSE
            WHERE NOT EXISTS (
                SELECT 1 FROM trades WHERE token=%s AND server='Hermes' AND status='open'
            )
            RETURNING id
        """, (
            token.upper(), direction,
            entry_price * size, entry_price, entry_price,
            ZS_PUMP_LEVERAGE, token.upper()
        ))
        row = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()
        if row:
            log(f"  DB record #{row[0]} created for {token} (zscore_pump)", "DB")
    except Exception as e:
        log(f"  Failed to create DB record for {token}: {e}", "WARN")

def remove_zs_position(token: str, reason: str, pnl_pct: float = 0, pnl_usdt: float = 0):
    data = load_positions()
    if token.upper() not in data['positions']:
        return
    closed = data['positions'].pop(token.upper())
    closed['closed_at'] = time.time()
    closed['close_reason'] = reason
    closed['pnl_pct'] = pnl_pct
    closed['pnl_usdt'] = pnl_usdt
    data['closed'].append(closed)
    _write_json(data)
    log(f"ZS_CLOSED {token}: {reason} pnl={pnl_pct:+.4f}%", "CLOSE")
    _close_brain_record(token, reason, pnl_pct)

def _close_brain_record(token: str, reason: str, pnl_pct: float):
    try:
        import psycopg2
        from _secrets import BRAIN_DB_DICT
        conn = psycopg2.connect(**BRAIN_DB_DICT)
        cur = conn.cursor()
        cur.execute("""
            UPDATE trades
            SET status = 'closed',
                close_time = NOW(),
                exit_price = %s,
                pnl_pct = %s,
                exit_reason = %s,
                close_reason = %s
            WHERE token = %s
              AND server = 'Hermes'
              AND status = 'open'
              AND signal = 'zscore_pump'
        """, (
            _get_token_latest_price(token),
            pnl_pct,
            f'zscore_pump_{reason}',
            f'zscore_pump_{reason}',
            token.upper()
        ))
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        log(f"  Failed to close DB record for {token}: {e}", "WARN")

# ─────────────────────────────────────────────────────────────────────────────
# Execution
# ─────────────────────────────────────────────────────────────────────────────

def get_account_value() -> float:
    try:
        from hyperliquid_exchange import get_account_value_curl
        state = get_account_value_curl()
        return float(state.get('withdrawable', 0) or 0)
    except Exception:
        return 0.0

def get_position_size(token: str, entry_price: float, account_value: float = None) -> float:
    try:
        if account_value is None or account_value <= 0:
            size_usdt = get_account_value() * ZS_PUMP_SIZE_PCT
        else:
            size_usdt = account_value * ZS_PUMP_SIZE_PCT
    except Exception:
        size_usdt = MIN_TRADE_USDT
    if size_usdt < MIN_TRADE_USDT:
        size_usdt = MIN_TRADE_USDT
    decimals = _sz_decimals(token)
    raw_sz = size_usdt / entry_price
    sz = float(Decimal(str(raw_sz)).quantize(
        Decimal(f"0.{'0' * decimals}"), rounding=ROUND_UP))
    return max(sz, 0.0001)

def execute_zscore_trade(token: str, direction: str, signal: dict, account_value: float = None) -> dict:
    if not LIVE_MODE:
        log(f"[DRY] Would execute: {direction} {token} @ {signal['entry_price']:.6f}", "SIGNAL")
        log(f"[DRY]   z={signal.get('z_score', 0):+.2f} lookback={signal.get('lookback', 0)}", "SIGNAL")
        return {'success': True, 'dry': True}

    if not is_live_trading_enabled():
        log(f"Live trading disabled — skipping zscore pump for {token}", "SKIP")
        return {'success': False, 'error': 'Live trading disabled'}

    entry_price = signal['entry_price']
    size = get_position_size(token, entry_price, account_value)
    if size <= 0:
        return {'success': False, 'error': 'Position size too small'}

    try:
        res = mirror_open(
            token=token.upper(),
            direction=direction,
            entry_price=entry_price,
        )
        if res and res.get('success'):
            log(f"ZS_OPEN {direction} {token}: {res.get('size')} @ {res.get('entry_price', entry_price):.6f} z={signal.get('z_score', 0):+.2f}", "EXEC")
            return {'success': True}
        else:
            err = res.get('message', 'unknown') if res else 'no response'
            log(f"ZS_FAIL {direction} {token}: {err}", "FAIL")
            return {'success': False, 'error': err}
    except Exception as e:
        log(f"ZS_EXCEPT {direction} {token}: {e}", "EXCEPT")
        return {'success': False, 'error': str(e)}

# ─────────────────────────────────────────────────────────────────────────────
# Logging
# ─────────────────────────────────────────────────────────────────────────────

def log(msg, tag="INFO"):
    ts = datetime.now().strftime("%H:%M:%S")
    line = f"[{ts}] [{tag}] {msg}"
    print(line)
    try:
        os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
        with open(LOG_FILE, 'a') as f:
            f.write(line + "\n")
    except Exception:
        pass

# ─────────────────────────────────────────────────────────────────────────────
# Z-score momentum detection (single token)
# ─────────────────────────────────────────────────────────────────────────────

def detect_zscore_momentum(token: str, closes: list, latest_price: float) -> dict | None:
    """
    Check if token has a z-score momentum signal given pre-fetched price history.
    closes: list of close prices in chronological order (oldest first).
    latest_price: most recent close price.
    """
    if not closes or latest_price <= 0:
        return None

    token_params = _load_token_params_cached()
    p = token_params.get(token.upper())
    tok_signal_count = p.get('signal_count', 0) if p else 0

    if p is None or tok_signal_count < MIN_SIGNALS_FOR_TUNED:
        lookback = DEFAULT_LOOKBACK
        threshold = DEFAULT_THRESHOLD
        confidence = 80.0
    else:
        lookback = p.get('lookback', DEFAULT_LOOKBACK)
        threshold = p.get('threshold', DEFAULT_THRESHOLD)
        wr = p.get('win_rate', 50.0)
        confidence = min(95.0, max(80.0, wr))

    if len(closes) < lookback + 2:
        return None

    chunk = closes[-lookback:]
    z = compute_zscore(chunk)
    if z is None:
        return None

    if abs(z) < threshold:
        return None

    direction = 'LONG' if z > 0 else 'SHORT'
    entry_price = latest_price

    if direction == 'LONG':
        stop_price = entry_price * 0.97
        tp_price = entry_price * 1.02
    else:
        stop_price = entry_price * 1.03
        tp_price = entry_price * 0.98

    return {
        'token': token.upper(),
        'direction': direction,
        'z_score': round(z, 3),
        'lookback': lookback,
        'threshold': threshold,
        'confidence': confidence,
        'entry_price': entry_price,
        'stop_price': stop_price,
        'tp_price': tp_price,
        'sl_pct': 3.0,
        'tp_pct': 2.0,
        'timestamp': int(time.time()),
    }

# ─────────────────────────────────────────────────────────────────────────────
# Scan and fire
# ─────────────────────────────────────────────────────────────────────────────

def scan_and_fire():
    """Scan tokens for z-score momentum signals and fire trades.
    Uses bulk price fetch from candles.db (mirrors zscore_momentum.py)."""
    global _delist_cache
    _delist_cache = {}  # reset per-cycle cache

    # Cache account value once per cycle (avoid per-signal API call)
    account_value = None
    if LIVE_MODE and is_live_trading_enabled():
        account_value = get_account_value()

    # Bulk fetch: {token: [closes_chronological]}
    all_prices = _get_all_token_prices(lookback_bars=DEFAULT_LOOKBACK * 4)
    if not all_prices:
        log("No price data available from candles.db", "WARN")
        return

    open_pos = get_open_zs_positions()
    if len(open_pos) >= MAX_ZS_PUMP_POSITIONS:
        log(f"At cap ({MAX_ZS_PUMP_POSITIONS}/{MAX_ZS_PUMP_POSITIONS}) — skipping scan", "SKIP")
        return
    log(f"Scanning {len(all_prices)} tokens for z-score momentum...", "SCAN")

    fired = 0
    for token, closes in all_prices.items():
        if token.startswith('@'):
            continue
        if token.upper() in ZS_PUMP_BLACKLIST:
            continue
        if token.upper() in open_pos:
            continue
        if not is_token_tradeable(token):
            continue

        latest_price = closes[-1] if closes else 0.0
        signal = detect_zscore_momentum(token, closes, latest_price)
        if signal is None:
            continue

        # Additional blacklist check on direction
        if signal['direction'] == 'SHORT' and token.upper() in SHORT_BLACKLIST:
            continue
        if signal['direction'] == 'LONG' and token.upper() in LONG_BLACKLIST:
            continue

        log(f"ZS_SIGNAL: {token} {signal['direction']} z={signal['z_score']:+.2f} "
            f"(lookback={signal['lookback']}, conf={signal['confidence']:.0f}%)", "SIGNAL")

        result = execute_zscore_trade(token, signal['direction'], signal, account_value)
        if result.get('success') and not result.get('dry'):
            sz = get_position_size(token, signal['entry_price'], account_value)
            add_zs_position(token, signal['direction'], signal, sz, signal['entry_price'])
            fired += 1

    if fired == 0:
        log("No z-score momentum signals this cycle.", "SCAN")
    else:
        log(f"Fired {fired} zscore_pump trades.", "SCAN")

# ─────────────────────────────────────────────────────────────────────────────
# Position monitoring + close conditions
# ─────────────────────────────────────────────────────────────────────────────

def _get_zscore_at_bar(token: str, lookback: int) -> float | None:
    """Compute current z-score for a token given its lookback window."""
    try:
        conn = sqlite3.connect(CANDLES_DB, timeout=5)
        cur = conn.cursor()
        cur.execute("""
            SELECT close FROM candles_1m
            WHERE token=? AND ts > (SELECT MAX(ts) FROM candles_1m WHERE token=?) - ? * 60
            ORDER BY ts ASC
        """, (token, token, lookback))
        rows = cur.fetchall()
        conn.close()
        if len(rows) < lookback:
            return None
        closes = [float(r[0]) for r in rows[-lookback:]]
        return compute_zscore(closes)
    except Exception:
        return None

def check_and_close_positions():
    """Check open positions for SL/TP hits via HL position status OR zscore crosses 0."""
    open_pos = get_open_zs_positions()
    if not open_pos:
        return

    # Always check zscore crosses (works in dry AND live)
    for token, pos in list(open_pos.items()):
        lookback = pos.get('lookback', DEFAULT_LOOKBACK)
        curr_z = _get_zscore_at_bar(token, lookback)
        if curr_z is None:
            continue

        direction = pos['direction']
        entry_z = pos.get('z_score', 0)

        # ZS crosses 0 exit: LONG exits when zscore goes <= 0, SHORT exits when >= 0
        should_exit = (direction == 'LONG' and curr_z <= 0 and entry_z > 0) or \
                      (direction == 'SHORT' and curr_z >= 0 and entry_z < 0)

        if not should_exit:
            continue

        entry_price = pos['entry_price']
        curr_price = _get_token_latest_price(token)
        if direction == 'LONG':
            pnl_pct = (curr_price - entry_price) / entry_price * 100
        else:
            pnl_pct = (entry_price - curr_price) / entry_price * 100
        pnl_usdt = pnl_pct / 100 * pos['size'] * entry_price

        log(f"ZS_CROSS0 {token}: z={curr_z:+.3f} pnl={pnl_pct:+.3f}%", "MONITOR")
        remove_zs_position(token, 'ZS_CROSS', pnl_pct, pnl_usdt)

        if LIVE_MODE:
            try:
                mirror_close(token, direction)
            except Exception as e:
                log(f"Failed to close {token} after ZS cross: {e}", "WARN")
        continue  # skip HL check for this token (already closed)

    if not LIVE_MODE:
        return

    # Check price-based SL/TP for remaining open positions
    for token, pos in list(open_pos.items()):
        direction = pos['direction']
        entry_price = pos['entry_price']
        curr_price = _get_token_latest_price(token)
        stop_price = pos.get('stop_price', entry_price * (0.97 if direction == 'LONG' else 1.03))
        tp_price = pos.get('tp_price', entry_price * (1.02 if direction == 'LONG' else 0.98))

        tp_hit = (direction == 'LONG' and curr_price >= tp_price) or \
                 (direction == 'SHORT' and curr_price <= tp_price)
        sl_hit = (direction == 'LONG' and curr_price <= stop_price) or \
                 (direction == 'SHORT' and curr_price >= stop_price)

        if not tp_hit and not sl_hit:
            continue

        reason = 'TP' if tp_hit else 'SL'
        pnl_pct = (curr_price - entry_price) / entry_price * 100 if direction == 'LONG' \
                 else (entry_price - curr_price) / entry_price * 100
        pnl_usdt = pnl_pct / 100 * pos['size'] * entry_price

        log(f"ZS_PRICE_CLOSE {token}: {reason} @ {curr_price:.6f} pnl={pnl_pct:+.3f}%", "MONITOR")
        remove_zs_position(token, reason, pnl_pct, pnl_usdt)

        if LIVE_MODE:
            try:
                mirror_close(token, direction)
            except Exception as e:
                log(f"Failed to close {token} after {reason}: {e}", "WARN")

def show_status():
    data = load_positions()
    open_pos = data.get('positions', {})
    closed = data.get('closed', [])

    print(f"\n=== ZScore Pump Hunter Status ===")
    print(f"Mode: {'LIVE' if LIVE_MODE else 'DRY'}")
    print(f"Open positions: {len(open_pos)}/{MAX_ZS_PUMP_POSITIONS}")
    print(f"Closed trades:  {len(closed)}")

    if open_pos:
        print(f"\n{'Token':<8} {'Dir':<5} {'Entry':<12} {'Z-score':<8} {'Lookback':<8}")
        print("-" * 55)
        for token, pos in open_pos.items():
            print(f"{token:<8} {pos['direction']:<5} {pos['entry_price']:<12.6f} "
                  f"{pos['z_score']:<+8.2f} {pos['lookback']:<8}")

    if closed:
        last20 = closed[-20:]
        wins = sum(1 for c in last20 if c.get('pnl_pct', 0) > 0)
        total_pnl = sum(c.get('pnl_pct', 0) for c in last20)
        print(f"\nLast 20 closed: {wins}/{len(last20)} wins, avg PnL: {total_pnl/len(last20):+.3f}%")
    print()

def close_all():
    data = load_positions()
    open_pos = data.get('positions', {})

    if not open_pos:
        log("No open zscore_pump positions to close.", "CLOSE")
        return

    log(f"Closing {len(open_pos)} zscore_pump positions...", "CLOSE")
    for token in list(open_pos.keys()):
        if LIVE_MODE:
            try:
                mirror_close(token, open_pos[token]['direction'])
            except Exception as e:
                log(f"Failed to close {token}: {e}", "FAIL")
        remove_zs_position(token, 'MANUAL', 0, 0)

    log("All zscore_pump positions closed.", "CLOSE")

# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────

def main():
    if '--status' in sys.argv:
        show_status()
        return
    if '--close' in sys.argv:
        close_all()
        return

    log(f"ZScore Pump Hunter starting... ({'LIVE' if LIVE_MODE else 'DRY'} mode)", "START")
    scan_and_fire()
    check_and_close_positions()
    log("ZScore Pump Hunter cycle complete.", "DONE")

if __name__ == '__main__':
    main()
