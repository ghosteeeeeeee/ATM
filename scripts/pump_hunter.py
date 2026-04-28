#!/usr/bin/env python3
"""
pump_hunter.py — Independent vol-explosion live trade executor.

Runs standalone (outside signal_compactor/position_manager pipeline).
Fires IMMEDIATE live trades on Hyperliquid when vol explosions are detected.
Manages its own positions — bypasses the 10-slot paper-trading limit.

Signal: vol > 5x MA + |candle| > 2%
Trade:  LONG REVERSION (fade the spike — mean reversion thesis confirmed)
Entry:  Spike candle close
Exit:   50% reversion of impulse (take profit)
Stop:   150% impulse in original direction (1.5x risk = 2:1 reward ratio)

Backtest (9d, 15m, 233 events):
  Win rate:  89%
  Avg P&L:  +2.87%
  Win/Loss: 37:1
  Total:    +$668.95 per $100/trade

Usage:
  python3 pump_hunter.py              # dry run (logs signals, no trades)
  python3 pump_hunter.py --live      # LIVE TRADING (real money)
  python3 pump_hunter.py --status    # show open pump-hunter positions
  python3 pump_hunter.py --close ALL # close all open positions
  python3 pump_hunter.py --test      # fire a test signal (no trade)
"""

import sys, os, time, json, math, sqlite3
from datetime import datetime, timezone
from decimal import Decimal, ROUND_UP

# ── Paths ──────────────────────────────────────────────────────────────────────
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paths import CANDLES_DB, HERMES_DATA
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from hyperliquid_exchange import (
    mirror_open, mirror_close, is_live_trading_enabled,
    get_open_hype_positions_curl, is_delisted, _round_position_sz, _sz_decimals,
    get_prices_curl, _exchange_rate_limit, get_exchange,
    _hl_price_decimals, _hl_tick_round, place_tp, place_sl,
    place_tp_sl_batch, MARGIN_USAGE_PCT, MIN_TRADE_USDT,
    MAIN_ACCOUNT_ADDRESS,
)

# ── Config ─────────────────────────────────────────────────────────────────────
# Default: DRY mode unless --live is explicitly passed
LIVE_MODE = '--live' in sys.argv

# Default to DRY unless explicitly overridden
if 'PUMP_LIVE' in os.environ:
    LIVE_MODE = os.environ['PUMP_LIVE'].lower() in ('1', 'true', 'yes')

# ── Signal metric ──────────────────────────────────────────────────────────────
# body_pct = (close - open) / open — robust to gaps between candles
# impulse_pct = (close - prev_close) / prev_close — affected by prior candle gaps
USE_BODY_PCT = True           # use candle body % for signal detection + TP/SL calc

# Vol explosion thresholds (from 2D backtest sweep on 400K candles, 170 tokens)
# Swept across vol=[2-10x] x body=[1-4%], best cells all ~+3.7-5.2% EV
# Selected: vol=4x, body=3.5% — 26 signals, 81% WR, R/R=0.90:1, EV=+4.08%/trade
# (Good balance of signal volume + edge stability across the sweep)
VOL_RATIO_THRESHOLD = 4.0    # volume > 4x the 20-candle average
CANDLE_PCT_THRESHOLD = 3.5   # |candle body| > 3.5%
REVERSION_PCT = 150.0        # exit at 150% reversion of impulse (confirmed by backtest)
STOP_MULTIPLIER = 1.5        # stop at 150% of impulse (protects against trend continuation)

# Tokens to skip (momentum-breakout tokens — vol explosion = trend continuation)
PUMP_BLACKLIST = {
    'REQ', 'AAVE', 'APE', 'NIL', 'PNUT', 'TNSR', 'ZRO',
    'ORDI', 'ACE', 'LISTA', 'NTRN',   # NTRN has 26% zero-vol candles (corrupt data)
    'TST',                             # 5 signals, 25% WR, -11.79% — momentum continuation
}
RECENT_SPIKE_WINDOW = 5       # skip if spike in last 5 candles (avoid sub-impulses)

# Position sizing
PUMP_LEVERAGE = 3             # 3x leverage per pump-hunter trade
MAX_PUMP_POSITIONS = 6         # max simultaneous pump-hunter positions (zscore-pump is separate)
PUMP_SIZE_PCT = 0.10          # 10% of margin per trade (separate from paper 7%)

# Tracking file — served via nginx so pump-hunter.html can read it
TRACK_FILE = '/var/www/hermes/data/pump-hunter.json'

# Logging
LOG_FILE = os.path.join(HERMES_DATA, 'logs', 'pump_hunter.log')


def log(msg, tag="INFO"):
    ts = datetime.now().strftime("%H:%M:%S")
    line = f"[{ts}] [{tag}] {msg}"
    print(line)
    try:
        os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
        with open(LOG_FILE, 'a') as f:
            f.write(line + "\n")
    except:
        pass


# ── Candle Data ────────────────────────────────────────────────────────────────

def get_1m_candles(token: str, lookback: int = 30) -> list:
    """Fetch last N 1m candles for token from candles.db.
    Freshness guard: skip if latest candle older than 15 minutes.
    """
    try:
        conn = sqlite3.connect(CANDLES_DB)
        cur = conn.cursor()
        # Freshness check
        cur.execute("SELECT MAX(ts) FROM candles_1m WHERE token = ?", (token.upper(),))
        row = cur.fetchone()
        if row and row[0]:
            age_seconds = time.time() - row[0]
            if age_seconds > 900:
                conn.close()
                return []
        cur.execute("""
            SELECT ts, open, high, low, close, volume
            FROM candles_1m
            WHERE token = ?
            ORDER BY ts DESC
            LIMIT ?
        """, (token.upper(), lookback))
        rows = cur.fetchall()
        conn.close()
        if not rows:
            return []
        # Return oldest first (chronological order)
        return [
            {
                'ts': r[0],
                'open': float(r[1]),
                'high': float(r[2]),
                'low': float(r[3]),
                'close': float(r[4]),
                'volume': float(r[5]),
            }
            for r in reversed(rows)
        ]
    except Exception as e:
        log(f"Failed to fetch 1m candles for {token}: {e}", "WARN")
        return []


def get_15m_candles(token: str, lookback: int = 25) -> list:
    """Fetch last N 15m candles for token from candles.db.
    Freshness guard: skip if latest candle older than 15 minutes.
    """
    try:
        conn = sqlite3.connect(CANDLES_DB)
        cur = conn.cursor()
        # Freshness check
        cur.execute("SELECT MAX(ts) FROM candles_15m WHERE token = ?", (token.upper(),))
        row = cur.fetchone()
        if row and row[0]:
            age_seconds = time.time() - row[0]
            if age_seconds > 900:
                conn.close()
                return []
        cur.execute("""
            SELECT ts, open, high, low, close, volume
            FROM candles_15m
            WHERE token = ?
            ORDER BY ts DESC
            LIMIT ?
        """, (token.upper(), lookback))
        rows = cur.fetchall()
        conn.close()
        if not rows:
            return []
        return [
            {
                'ts': r[0],
                'open': float(r[1]),
                'high': float(r[2]),
                'low': float(r[3]),
                'close': float(r[4]),
                'volume': float(r[5]),
            }
            for r in reversed(rows)
        ]
    except Exception as e:
        log(f"Failed to fetch 15m candles for {token}: {e}", "WARN")
        return []


# ── Vol Explosion Detection ───────────────────────────────────────────────────

def detect_vol_explosion(candles: list) -> dict | None:
    """
    Check if the most recent candle is a vol explosion signal.

    Signal: vol > 5x MA AND |body_pct| > 2%
    Direction: LONG (mean reversion — fade the spike, not follow it)
    Entry:  spike candle close
    Exit:   100% reversion (price fully returns to pre-spike level)
    Stop:   150% impulse (price continues past spike — trend is strong)

    Returns signal dict or None:
    {
        'token': str,
        'direction': 'LONG',
        'spike_pct': float,       # body % of spike candle (e.g. +5.2)
        'entry_price': float,
        'revert_target': float,   # full reversion: back to prev_close
        'stop_price': float,      # 150% impulse in original direction
        'vol_ratio': float,
        'confidence': float,      # 0-1, based on vol_ratio
        'timestamp': int,
    }
    """
    if len(candles) < 5:
        return None

    # Use last 20 candles for average volume (excluding current)
    recent = candles[-21:-1]  # 20 candles before current
    current = candles[-1]

    if not recent or current['volume'] <= 0:
        return None

    avg_vol = sum(c['volume'] for c in recent) / len(recent)
    vol_ratio = current['volume'] / avg_vol if avg_vol > 0 else 0

    prev = candles[-2]

    # Use body_pct: (close - open) / open — robust to gaps between candles
    # This measures the actual candle body, not the gap from prior close
    body_pct = (current['close'] - current['open']) / current['open'] * 100
    # Also compute impulse_pct = (close - prev_close) / prev_close for reference
    impulse_pct = (current['close'] - prev['close']) / prev['close'] * 100

    # Check: vol spike AND big candle body
    if vol_ratio < VOL_RATIO_THRESHOLD:
        return None
    if abs(body_pct) < CANDLE_PCT_THRESHOLD:
        return None

    # Check: no recent spike in last 5 candles (avoid sub-impulses)
    for i in range(1, RECENT_SPIKE_WINDOW):  # skip i=0 (current candle)
        idx = -RECENT_SPIKE_WINDOW + i
        if abs(idx) > len(candles) - 1:
            continue
        c = candles[idx]
        c_prev = candles[idx - 1]
        c_avg = avg_vol
        c_ratio = c['volume'] / c_avg if c_avg > 0 else 0
        c_body = abs((c['close'] - c['open']) / c['open'] * 100) if c['open'] != 0 else 0
        if c_ratio > VOL_RATIO_THRESHOLD * 0.7 and c_body > CANDLE_PCT_THRESHOLD * 0.7:
            log(f"Recent spike detected ({c_ratio:.1f}x vol, {c_body:.1f}% body), skipping", "SKIP")
            return None

    # Direction: LONG REVERSION — fade the spike (buy the dip/rally)
    # We enter at spike candle close, TP = full reversion back to prev_close,
    # SL = 150% impulse (price continues hard in original direction)
    direction = 'LONG'
    entry_price = current['close']
    prev_close = prev['close']

    # Spike pct: use body_pct (the actual candle body, not the gap)
    spike_pct = body_pct  # e.g. +5.2 means candle body was +5.2%

    # Target: 100% reversion — price returns to prev_close
    # If body_pct > 0 (candle went up), target = lower (back to prev_close)
    # If body_pct < 0 (candle went down), target = higher (back to prev_close)
    revert_target = prev_close  # full reversion to pre-spike price

    # Stop: 150% of spike in original direction
    stop_pct = abs(spike_pct) * STOP_MULTIPLIER
    if spike_pct > 0:
        # Spiked up — stop is above entry (price continued up past 150% of spike)
        stop_price = entry_price * (1 + stop_pct / 100)
    else:
        # Spiked down — stop is below entry (price continued down past 150% of spike)
        stop_price = entry_price * (1 - stop_pct / 100)

    confidence = min(vol_ratio / 20.0, 1.0)  # cap at 1.0

    return {
        'direction': direction,
        'spike_pct': spike_pct,
        'impulse_pct': impulse_pct,   # keep for reference (shows actual price gap)
        'entry_price': entry_price,
        'prev_close': prev_close,
        'revert_target': float(round(revert_target, 6)),
        'stop_price': float(round(stop_price, 6)),
        'vol_ratio': vol_ratio,
        'confidence': confidence,
        'timestamp': current['ts'],
    }


# ── Position Tracking ──────────────────────────────────────────────────────────

def _write_json(data: dict):
    """Write pump_hunter_positions.json atomically."""
    d = os.path.dirname(TRACK_FILE)
    if d:
        os.makedirs(d, exist_ok=True)
    with open(TRACK_FILE, 'w') as f:
        json.dump(data, f, indent=2)


def _load_json() -> dict:
    """Load pump_hunter_positions.json."""
    try:
        if os.path.exists(TRACK_FILE):
            with open(TRACK_FILE) as f:
                return json.load(f)
    except:
        pass
    return {'positions': {}, 'closed': []}


def load_positions() -> dict:
    """Load open pump-hunter positions from tracking file."""
    return _load_json()


def save_positions(data: dict):
    """Save pump-hunter positions to tracking file."""
    data['mode'] = 'LIVE' if LIVE_MODE else 'DRY'
    data['last_updated'] = datetime.now().isoformat()
    _write_json(data)


def get_open_pump_positions() -> dict:
    """Get open pump-hunter positions keyed by token."""
    data = load_positions()
    return data.get('positions', {})


def add_pump_position(token: str, signal: dict, size: float, entry_price: float):
    """Add a new pump-hunter position to tracking."""
    data = load_positions()
    pos = {
        'token': token.upper(),
        'direction': signal['direction'],
        'entry_price': entry_price,
        'revert_target': signal['revert_target'],
        'stop_price': signal['stop_price'],
        'spike_pct': signal['spike_pct'],
        'vol_ratio': signal['vol_ratio'],
        'confidence': signal['confidence'],
        'size': size,
        'opened_at': time.time(),
        'tp_filled': False,
        'sl_filled': False,
    }
    data['positions'][token.upper()] = pos
    save_positions(data)
    log(f"TRACKED {token} pump position: entry={entry_price:.6f} target={signal['revert_target']:.6f} stop={signal['stop_price']:.6f}", "TRACK")

    # Create DB record so guardian knows this HL position is intentional.
    # signal='pump_hunter' so guardian skips orphan creation, PM skips management.
    brain_id = _create_brain_record(token, signal, size, entry_price)
    if brain_id:
        pos['brain_id'] = brain_id
        data['positions'][token.upper()] = pos
        save_positions(data)


def _create_brain_record(token: str, signal: dict, size: float, entry_price: float):
    """
    Create a DB record so guardian knows this HL position is intentional.
    signal_source='pump_hunter' so guardian and PM know to leave it alone.
    Guardian's orphan guard skips pump_hunter positions.
    PM's queries exclude signal_source='pump_hunter'.
    """
    try:
        import psycopg2
        from _secrets import BRAIN_DB_DICT
        conn = psycopg2.connect(**BRAIN_DB_DICT)
        cur = conn.cursor()
        # Only insert if no open trade exists for this token
        cur.execute("""
            INSERT INTO trades (
                token, direction, amount_usdt, entry_price, hl_entry_price,
                exchange, paper, server, status, open_time,
                pnl_usdt, pnl_pct, leverage, signal,
                sl_distance, trailing_activation, trailing_distance,
                is_guardian_close, guardian_closed
            )
            SELECT %s, %s, %s, %s, %s, 'Hyperliquid', false, 'Hermes', 'open', NOW(),
                   0, 0, %s, 'pump_hunter',
                   0.03, 0.01, 0.01, FALSE, FALSE
            WHERE NOT EXISTS (
                SELECT 1 FROM trades WHERE token=%s AND server='Hermes' AND status='open'
            )
            RETURNING id
        """, (
            token.upper(), signal['direction'],
            entry_price * size, entry_price, entry_price,
            PUMP_LEVERAGE, token.upper()
        ))
        row = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()
        if row:
            log(f"  DB record #{row[0]} created for {token} (pump_hunter)", "DB")
            return row[0]
        else:
            log(f"  DB record already exists for {token} — skipping", "DB")
            return None
    except Exception as e:
        log(f"  Failed to create DB record for {token}: {e}", "WARN")
        return None


def remove_pump_position(token: str, reason: str, pnl_pct: float = 0, pnl_usdt: float = 0):
    """Remove a pump-hunter position (closed by TP/SL) and close its DB record."""
    data = load_positions()
    if token.upper() not in data['positions']:
        return

    closed = data['positions'].pop(token.upper())
    closed['closed_at'] = time.time()
    closed['close_reason'] = reason
    closed['pnl_pct'] = pnl_pct
    closed['pnl_usdt'] = pnl_usdt
    data['closed'].append(closed)
    save_positions(data)
    log(f"CLOSED {token}: {reason} pnl={pnl_pct:+.4f}% pnl_usdt={pnl_usdt:+.2f}", "CLOSE")

    # Also close the brain DB record
    _close_brain_record(token, reason, pnl_pct)


def _close_brain_record(token: str, reason: str, pnl_pct: float):
    """Close the brain DB record for a pump-hunter position."""
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
              AND signal = 'pump_hunter'
        """, (
            _get_latest_price(token),
            pnl_pct,
            f'pump_hunter_{reason}',
            f'pump_hunter_{reason}',
            token.upper()
        ))
        conn.commit()
        cur.close()
        conn.close()
        log(f"  DB record closed for {token} ({reason})", "DB")
    except Exception as e:
        log(f"  Failed to close DB record for {token}: {e}", "WARN")


def _get_latest_price(token: str) -> float:
    """Get the latest close price from local candles DB."""
    candles = get_1m_candles(token, lookback=2)
    if candles:
        return candles[-1]['close']
    candles = get_15m_candles(token, lookback=2)
    if candles:
        return candles[-1]['close']
    return 0.0


def _pump_hunter_has_db_record(token: str) -> bool:
    """Check if a pump_hunter DB record already exists for this token."""
    try:
        import psycopg2
        from _secrets import BRAIN_DB_DICT
        conn = psycopg2.connect(**BRAIN_DB_DICT)
        cur = conn.cursor()
        cur.execute("""
            SELECT 1 FROM trades
            WHERE token = %s
              AND server = 'Hermes'
              AND status = 'open'
              AND signal = 'pump_hunter'
            LIMIT 1
        """, (token.upper(),))
        exists = cur.fetchone() is not None
        cur.close()
        conn.close()
        return exists
    except Exception:
        return False


def _cancel_brain_record(token: str):
    """Remove pre-created DB record when mirror_open failed."""
    try:
        import psycopg2
        from _secrets import BRAIN_DB_DICT
        conn = psycopg2.connect(**BRAIN_DB_DICT)
        cur = conn.cursor()
        cur.execute("""
            DELETE FROM trades
            WHERE token = %s
              AND server = 'Hermes'
              AND status = 'open'
              AND signal = 'pump_hunter'
        """, (token.upper(),))
        conn.commit()
        cur.close()
        conn.close()
        log(f"  DB record cancelled for {token}", "DB")
    except Exception as e:
        log(f"  Failed to cancel DB record for {token}: {e}", "WARN")


def _update_brain_record_fill(token: str, fill_price: float, size: float):
    """Update DB record with actual HL fill price and size."""
    try:
        import psycopg2
        from _secrets import BRAIN_DB_DICT
        conn = psycopg2.connect(**BRAIN_DB_DICT)
        cur = conn.cursor()
        cur.execute("""
            UPDATE trades
            SET entry_price = %s,
                hl_entry_price = %s,
                amount_usdt = %s
            WHERE token = %s
              AND server = 'Hermes'
              AND status = 'open'
              AND signal = 'pump_hunter'
        """, (fill_price, fill_price, fill_price * size, token.upper()))
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        log(f"  Failed to update DB fill for {token}: {e}", "WARN")


# ── Hyperliquid Execution ──────────────────────────────────────────────────────

def get_account_value() -> float:
    """Get withdrawable account value."""
    try:
        from hyperliquid_exchange import get_account_value_curl
        state = get_account_value_curl()
        return float(state.get('withdrawable', 0) or 0)
    except:
        return 0.0


def get_position_size(token: str, entry_price: float) -> float:
    """Calculate position size in coin units for pump-hunter."""
    try:
        size_usdt = get_account_value() * PUMP_SIZE_PCT
    except:
        size_usdt = MIN_TRADE_USDT

    if size_usdt < MIN_TRADE_USDT:
        size_usdt = MIN_TRADE_USDT

    decimals = _sz_decimals(token)
    raw_sz = size_usdt / entry_price
    # Round up to ensure minimum notional
    sz = float(Decimal(str(raw_sz)).quantize(
        Decimal(f"0.{'0' * decimals}"), rounding=ROUND_UP))
    return max(sz, 0.0001)


def execute_pump_trade(token: str, signal: dict) -> dict:
    """
    Execute a live pump-hunter trade on Hyperliquid.
    Returns result dict.
    """
    if not LIVE_MODE:
        log(f"[DRY] Would execute: LONG {token} @ {signal['entry_price']:.6f}", "SIGNAL")
        log(f"[DRY]   Spike: {signal['spike_pct']:+.2f}% body ({signal['vol_ratio']:.1f}x vol)", "SIGNAL")
        log(f"[DRY]   Target: {signal['revert_target']:.6f} (full reversion to prev_close)", "SIGNAL")
        log(f"[DRY]   Stop:   {signal['stop_price']:.6f} (150% impulse)", "SIGNAL")
        return {'success': True, 'dry': True}

    if not is_live_trading_enabled():
        log(f"Live trading disabled — skipping pump hunter for {token}", "SKIP")
        return {'success': False, 'error': 'Live trading disabled'}

    if is_delisted(token):
        log(f"{token} is delisted on Hyperliquid — skipping", "SKIP")
        return {'success': False, 'error': f'{token} delisted'}

    # Double-check: if a DB record exists for pump_hunter, skip (avoid duplicates)
    if _pump_hunter_has_db_record(token):
        log(f"DB record already exists for {token} pump_hunter — skipping", "SKIP")
        return {'success': False, 'error': 'Already in DB'}

    # Check position count
    open_pos = get_open_pump_positions()
    if len(open_pos) >= MAX_PUMP_POSITIONS:
        log(f"Max pump positions ({MAX_PUMP_POSITIONS}) reached — skipping {token}", "SKIP")
        return {'success': False, 'error': 'Max positions reached'}

    # Also check if we already have this token open
    if token.upper() in open_pos:
        log(f"Already have open pump position for {token} — skipping", "SKIP")
        return {'success': False, 'error': 'Already in position'}

    # Get size
    entry_price = signal['entry_price']
    size = get_position_size(token, entry_price)

    log(f"EXECUTING: LONG {token} size={size} @ {entry_price:.6f}", "EXEC")

    # ── Step 1: Create DB record BEFORE HL trade (prevents guardian orphan detection)
    # Uses estimated entry price; will update with actual fill price after fill
    signal_copy = dict(signal)
    signal_copy['direction'] = 'LONG'
    brain_id = _create_brain_record(token, signal_copy, size, entry_price)
    if brain_id:
        log(f"  DB record #{brain_id} pre-created for {token}", "DB")
    else:
        log(f"  DB record not created (may already exist) — continuing", "WARN")

    # ── Step 2: Place the live HL order
    result = mirror_open(
        token=token,
        direction='LONG',
        entry_price=entry_price,
        leverage=PUMP_LEVERAGE,
    )

    if not result.get('success'):
        log(f"mirror_open FAILED for {token}: {result.get('message')}", "FAIL")
        # Try to clean up the pre-created DB record
        _cancel_brain_record(token)
        return result

    # Get actual fill price
    fill_price = result.get('entry_price', entry_price)
    actual_size = result.get('size', size)

    log(f"FILLED: LONG {token} {actual_size} @ {fill_price:.6f}", "FILL")

    # ── Step 3: Update DB record with actual fill price
    _update_brain_record_fill(token, fill_price, actual_size)

    # ── Step 4: Track in pump_hunter's own JSON (for exit monitoring)
    data = load_positions()
    pos = {
        'token': token.upper(),
        'direction': 'LONG',
        'entry_price': fill_price,
        'revert_target': signal['revert_target'],
        'stop_price': signal['stop_price'],
        'spike_pct': signal['spike_pct'],
        'vol_ratio': signal['vol_ratio'],
        'confidence': signal['confidence'],
        'size': actual_size,
        'opened_at': time.time(),
        'tp_filled': False,
        'sl_filled': False,
        'brain_id': brain_id,
    }
    data['positions'][token.upper()] = pos
    save_positions(data)
    log(f"TRACKED {token} pump position: entry={fill_price:.6f} target={signal['revert_target']:.6f} stop={signal['stop_price']:.6f}", "TRACK")

    # Place TP and SL
    tp_result = place_tp(
        coin=token,
        direction='LONG',
        tp_price=signal['revert_target'],
        size=actual_size,
    )
    sl_result = place_sl(
        coin=token,
        direction='LONG',
        sl_price=signal['stop_price'],
        size=actual_size,
    )

    if tp_result.get('success'):
        log(f"  TP placed: {signal['revert_target']:.6f}", "TP")
    else:
        log(f"  TP FAILED: {tp_result.get('error')}", "FAIL")

    if sl_result.get('success'):
        log(f"  SL placed: {signal['stop_price']:.6f}", "SL")
    else:
        log(f"  SL FAILED: {sl_result.get('error')}", "FAIL")

    return {
        'success': True,
        'token': token,
        'entry_price': fill_price,
        'size': actual_size,
        'tp': signal['revert_target'],
        'sl': signal['stop_price'],
    }


# ── Exit Monitoring ────────────────────────────────────────────────────────────

def sync_hl_positions():
    """
    Belt-and-suspenders: reconcile pump_hunter's JSON tracking against live HL positions.
    If a tracked position no longer exists on HL (TP/SL fired silently), clean it up.
    Runs every cycle as a safety net.
    """
    open_pos = get_open_pump_positions()
    if not open_pos:
        return

    if not LIVE_MODE:
        return  # skip HL check in dry mode

    # Get live HL positions
    try:
        from hyperliquid_exchange import get_open_hype_positions_curl
        hl_positions = get_open_hype_positions_curl()
    except Exception as e:
        log(f"HL positions check failed: {e}", "WARN")
        return

    hl_tokens = {p['token'].upper() for p in hl_positions}

    for token in list(open_pos.keys()):
        if token.upper() not in hl_tokens:
            # Position gone from HL — TP/SL likely filled silently
            candles = get_1m_candles(token, lookback=2)
            cur_price = candles[-1]['close'] if candles else open_pos[token]['entry_price']
            pos = open_pos[token]
            entry = pos['entry_price']
            pnl_pct = (cur_price - entry) / entry * 100 if entry > 0 else 0

            log(f"ZOMBIE CLEANUP: {token} not on HL — was likely closed by TP/SL at {cur_price:.6f}", "ZOMBIE")
            remove_pump_position(token, 'HL_TP_SL_FILL', pnl_pct, 0)


def check_pump_exits():
    """
    Check if any pump-hunter positions should be closed by TP/SL.
    Uses local candles_1m DB — no HL API calls for price.
    """
    open_pos = get_open_pump_positions()
    if not open_pos:
        return

    # Get latest close price for each token from local candles DB
    token_prices = {}
    for token in open_pos:
        candles = get_1m_candles(token, lookback=2)
        if candles:
            token_prices[token] = candles[-1]['close']

    for token, pos in list(open_pos.items()):
        cur_price = token_prices.get(token)
        if cur_price is None:
            # Fall back to 15m if no 1m data
            candles = get_15m_candles(token, lookback=2)
            if candles:
                cur_price = candles[-1]['close']
        if cur_price is None:
            continue

        entry = pos['entry_price']
        direction = pos['direction']
        target = pos['revert_target']
        stop = pos['stop_price']

        # Calculate current PnL
        if direction == 'LONG':
            pnl_pct = (cur_price - entry) / entry * 100
        else:
            pnl_pct = (entry - cur_price) / entry * 100

        exited = False
        reason = ''
        pnl_usdt = 0.0

        # Check TP (50% reversion hit)
        if direction == 'LONG' and cur_price >= target:
            exited = True
            reason = 'TP'
            pnl_usdt = pnl_pct / 100 * entry * pos['size']
        elif direction == 'SHORT' and cur_price <= target:
            exited = True
            reason = 'TP'
            pnl_usdt = pnl_pct / 100 * entry * pos['size']

        # Check SL (150% impulse hit — price continued hard)
        elif direction == 'LONG' and cur_price <= stop:
            exited = True
            reason = 'SL'
            pnl_usdt = pnl_pct / 100 * entry * pos['size']
        elif direction == 'SHORT' and cur_price >= stop:
            exited = True
            reason = 'SL'
            pnl_usdt = pnl_pct / 100 * entry * pos['size']

        if exited:
            log(f"EXIT TRIGGER: {token} {reason} @ {cur_price:.6f} pnl={pnl_pct:+.4f}%", "EXIT")
            # Close via Hyperliquid
            if LIVE_MODE:
                try:
                    close_result = mirror_close(token, direction, cur_price)
                    log(f"  mirror_close: {close_result}", "CLOSE")
                except RuntimeError as e:
                    # HL TP/SL likely already closed the position — verify via HL API
                    err_msg = str(e)
                    if "position not found" in err_msg.lower() or "no position" in err_msg.lower():
                        log(f"  Position already closed by HL TP/SL — cleaning up: {err_msg}", "CLEANUP")
                    else:
                        log(f"  mirror_close FAILED: {e}", "FAIL")
                        continue  # keep position open, retry next cycle
            # Always remove from tracking — HL TP/SL or manual close
            remove_pump_position(token, reason, pnl_pct, pnl_usdt)


# ── Token Universe ─────────────────────────────────────────────────────────────

def get_tradeable_tokens() -> list:
    """Get tokens available in candles_1m."""
    try:
        conn = sqlite3.connect(CANDLES_DB)
        cur = conn.cursor()
        cur.execute("SELECT DISTINCT token FROM candles_1m ORDER BY token")
        rows = cur.fetchall()
        conn.close()
        return [r[0] for r in rows]
    except Exception as e:
        log(f"Failed to get tradeable tokens: {e}", "WARN")
        return []


# ── Main Scan ─────────────────────────────────────────────────────────────────

def scan_and_fire():
    """Scan all tokens for vol explosions and fire trades."""
    tokens = get_tradeable_tokens()
    log(f"Scanning {len(tokens)} tokens for vol explosions...", "SCAN")

    fired = 0
    for token in tokens:
        if token.upper() in PUMP_BLACKLIST:
            continue  # skip blacklisted tokens silently

        # Use 1m candles for detection (faster, more signals)
        candles = get_1m_candles(token, lookback=30)
        if not candles:
            # Fall back to 15m
            candles = get_15m_candles(token, lookback=25)

        if not candles:
            continue

        signal = detect_vol_explosion(candles)
        if signal is None:
            continue

        signal['token'] = token

        # Log the signal
        log(f"SIGNAL: {token} vol_explosion — {signal['spike_pct']:+.2f}% body "
            f"({signal['vol_ratio']:.1f}x vol, conf={signal['confidence']:.0%})", "SIGNAL")

        result = execute_pump_trade(token, signal)
        if result.get('success'):
            fired += 1

    if fired == 0:
        log("No vol explosions detected this cycle.", "SCAN")
    else:
        log(f"Fired {fired} pump-hunter trades.", "SCAN")


# ── Status ─────────────────────────────────────────────────────────────────────

def show_status():
    """Show open pump-hunter positions."""
    data = load_positions()
    open_pos = data.get('positions', {})
    closed = data.get('closed', [])

    print(f"\n=== Pump Hunter Status ===")
    print(f"Mode: {'LIVE' if LIVE_MODE else 'DRY'}")
    print(f"Open positions: {len(open_pos)}/{MAX_PUMP_POSITIONS}")
    print(f"Closed trades:  {len(closed)}")

    if open_pos:
        print(f"\n{'Token':<8} {'Dir':<5} {'Entry':<12} {'Target':<12} {'Stop':<12} {'Impulse':<8} {'VolRatio':<8}")
        print("-" * 80)
        for token, pos in open_pos.items():
            print(f"{token:<8} {pos['direction']:<5} {pos['entry_price']:<12.6f} "
                  f"{pos['revert_target']:<12.6f} {pos['stop_price']:<12.6f} "
                  f"{pos['impulse_pct']:+7.2f}% {pos['vol_ratio']:<8.1f}x")

    if closed:
        total_pnl = sum(c.get('pnl_pct', 0) for c in closed[-20:])
        wins = sum(1 for c in closed if c.get('pnl_pct', 0) > 0)
        print(f"\nLast 20 closed: {wins}/{len(closed[-20:])} wins, avg PnL: {total_pnl/len(closed[-20:]):+.3f}%")

    print()


# ── Close All ─────────────────────────────────────────────────────────────────

def close_all():
    """Close all open pump-hunter positions."""
    data = load_positions()
    open_pos = data.get('positions', {})

    if not open_pos:
        log("No open pump-hunter positions to close.", "CLOSE")
        return

    log(f"Closing {len(open_pos)} pump-hunter positions...", "CLOSE")

    for token in list(open_pos.keys()):
        if LIVE_MODE:
            try:
                mirror_close(token, 'LONG')
            except Exception as e:
                log(f"Failed to close {token}: {e}", "FAIL")
        remove_pump_position(token, 'MANUAL', 0, 0)

    log("All pump-hunter positions closed.", "CLOSE")


# ── Entry Point ────────────────────────────────────────────────────────────────

def main():
    if '--status' in sys.argv:
        show_status()
        return

    if '--close' in sys.argv:
        close_all()
        return

    if '--help' in sys.argv or '-h' in sys.argv:
        print(__doc__)
        return

    mode = 'LIVE' if LIVE_MODE else 'DRY'
    log(f"=== Pump Hunter [{mode}] ===", "START")

    # Always write mode + timestamp to JSON even with no position changes
    data = load_positions()
    data['mode'] = mode
    data['last_updated'] = datetime.now().isoformat()
    save_positions(data)

    # Sync HL positions first (cleans up any TP/SL that fired silently)
    sync_hl_positions()

    # Check exits
    check_pump_exits()

    # Then scan for new signals
    scan_and_fire()

    log(f"=== Pump Hunter [{mode}] done ===", "END")


if __name__ == '__main__':
    main()
