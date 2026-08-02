"""
run_guppy_signals.py — Guppy MMA Standalone Runner
==================================================
Systemd timer-driven scanner for guppy signals.
NO HL API calls for signal detection or exit monitoring — all local candles.db reads.

Kill switches:
  GUPPY_ENABLED (hermes_constants) — gates entire scanner (if False, exit silently)
  GUPPY_LIVE env var — gates real trade execution (mirror_open/mirror_close)
    GUPPY_LIVE=1 → live trades, GUPPY_LIVE=0/unset → dry run

Usage:
  python3 run_guppy_signals.py --scan        Scan for new signals
  python3 run_guppy_signals.py --monitor     Check exits for open positions
  python3 run_guppy_signals.py --status      Show open positions from tracker JSON
  python3 run_guppy_signals.py --close ALL   Emergency close all positions
  python3 run_guppy_signals.py --scan --live Force live mode (overrides GUPPY_LIVE env)
"""

import sys
import os
import json
import time
import math
from datetime import datetime
from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TRACK_FILE  = "/var/www/hermes/data/guppy-tracker.json"

# ── Try to load GUPPY_ENABLED from hermes_constants ────────────────────────
GUPPY_ENABLED = True  # default True, overridden by constants file
try:
    sys.path.insert(0, SCRIPT_DIR)
    from hermes_constants import GUPPY_ENABLED as _GE
    GUPPY_ENABLED = _GE
except Exception:
    pass

# ── Live mode: env var or --live flag ──────────────────────────────────────
GUPPY_LIVE_MODE = (
    os.environ.get('GUPPY_LIVE', '').lower() in ('1', 'true', 'yes')
    or '--live' in sys.argv
)
if not GUPPY_ENABLED:
    sys.exit(0)  # exit silently if disabled

# ── HL Exchange imports (only loaded when GUPPY_LIVE_MODE=True) ──────────────
# Deferred to avoid HL API deps during pure-local testing
HL_AVAILABLE = False
if GUPPY_LIVE_MODE:
    try:
        from hyperliquid_exchange import mirror_open, mirror_close
        from hermes_constants import LIVE_TRADING_ENABLED
        # Check if we can actually trade
        if os.environ.get('GUPPY_LIVE', '').lower() in ('1', 'true', 'yes'):
            GUPPY_LIVE_MODE = True
        else:
            GUPPY_LIVE_MODE = False  # --live flag present but GUPPY_LIVE env not set
        HL_AVAILABLE = True
    except Exception as e:
        print(f"[run_guppy] HL exchange not available: {e}")
        GUPPY_LIVE_MODE = False

# ── Import guppy detection engine ───────────────────────────────────────────
sys.path.insert(0, SCRIPT_DIR)
import guppy_signals as gs

from hermes_log import log
# ── Logging ─────────────────────────────────────────────────────────────────
def _write_json(data: dict):
    """Write guppy-tracker.json atomically."""
    d = os.path.dirname(TRACK_FILE)
    if d:
        os.makedirs(d, exist_ok=True)
    tmp = TRACK_FILE + f".{os.getpid()}.tmp"
    with open(tmp, 'w') as f:
        json.dump(data, f, indent=2)
    os.rename(tmp, TRACK_FILE)


def _load_json() -> dict:
    try:
        if os.path.exists(TRACK_FILE):
            with open(TRACK_FILE) as f:
                return json.load(f)
    except Exception:
        pass
    return {'positions': {}, 'closed': []}


def load_positions() -> dict:
    return _load_json().get('positions', {})


def save_all(data: dict):
    data['mode'] = 'LIVE' if GUPPY_LIVE_MODE else 'DRY'
    data['last_updated'] = datetime.now().isoformat()
    _write_json(data)


def get_tracker() -> dict:
    return _load_json()


# ── Position Management ─────────────────────────────────────────────────────

MAX_GUPPY_POSITIONS = 3


def add_position(token: str, signal: dict, entry_price: float, size: float = 0.5):
    """Add a new guppy position to tracker."""
    data = _load_json()

    if len(data.get('positions', {})) >= MAX_GUPPY_POSITIONS:
        log(f"Max positions reached ({MAX_GUPPY_POSITIONS}), skipping {token}", "SKIP")
        return False

    if token.upper() in data.get('positions', {}):
        log(f"{token} already open, skipping", "SKIP")
        return False

    pos = {
        'token':        token.upper(),
        'direction':    signal['direction'],  # 'LONG' or 'SHORT'
        'entry_price':  entry_price,
        'fast_mid':     signal.get('fast_mid', 0),
        'fast_high':    signal.get('fast_high', 0),
        'fast_low':     signal.get('fast_low', 0),
        'slow_mid':     signal.get('slow_mid', 0),
        'confidence':    signal.get('confidence', 0),
        'source':       signal.get('source', 'guppy+'),
        'size':         size,
        'opened_at':    time.time(),
        'pnl_pct':      0.0,
    }
    data.setdefault('positions', {})[token.upper()] = pos
    save_all(data)
    log(f"TRACKED {token} guppy {signal['direction']}: entry={entry_price:.4f} conf={signal.get('confidence',0):.2f}", "TRACK")
    return True


def remove_position(token: str, reason: str, exit_price: float, pnl_pct: float = 0.0):
    """Close and remove a guppy position from tracker."""
    data = _load_json()
    token = token.upper()

    if token not in data.get('positions', {}):
        return

    closed = data['positions'].pop(token)
    closed['closed_at']    = time.time()
    closed['close_reason'] = reason
    closed['exit_price']   = exit_price
    closed['pnl_pct']      = pnl_pct
    data.setdefault('closed', []).append(closed)
    save_all(data)
    log(f"CLOSED {token}: {reason} exit={exit_price:.4f} pnl={pnl_pct:+.4f}%", "CLOSE")


def close_all_positions(reason: str = "manual_close"):
    """Emergency close all open guppy positions."""
    data = _load_json()
    positions = data.get('positions', {})
    if not positions:
        log("No open positions to close.", "INFO")
        return

    for token in list(positions.keys()):
        pos = positions[token]
        cur_price = _get_current_price(token)

        # Live close if enabled
        if GUPPY_LIVE_MODE and HL_AVAILABLE:
            try:
                result = mirror_close(token, pos['direction'])
                log(f"mirror_close({token}): {result}", "CLOSE")
            except Exception as e:
                log(f"mirror_close FAILED for {token}: {e}", "FAIL")

        remove_position(token, reason, cur_price or pos.get('entry_price', 0), 0.0)

    log(f"Emergency closed {len(positions)} position(s)", "CLOSE")


# ── Price Fetching (local only) ─────────────────────────────────────────────

def _get_current_price(token: str) -> float:
    """Get latest close price from candles.db (no HL API)."""
    rows = gs.get_candles(token, lookback=3, interval="1m")
    if rows:
        return rows[-1][4]
    return None


# ── Brain DB (deferred — needs psycopg2 + _secrets) ────────────────────────

def _create_brain_record(token: str, direction: str, signal: dict, size: float, entry_price: float):
    """
    Create DB record so guardian/PM know to skip guppy positions.
    Deferred: requires psycopg2 + _secrets (only loaded in live mode).
    """
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
                   0, 0, 10, 'guppy',
                   0.01, 0.005, 0.005, FALSE, FALSE
            WHERE NOT EXISTS (
                SELECT 1 FROM trades WHERE token=%s AND server='Hermes' AND status='open'
            )
            RETURNING id
        """, (
            token.upper(), direction,
            entry_price * size, entry_price, entry_price,
            token.upper()
        ))
        row = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()
        if row:
            log(f"  DB record #{row[0]} created for {token} (guppy)", "DB")
            return row[0]
        return None
    except Exception as e:
        log(f"  Failed to create DB record for {token}: {e}", "WARN")
        return None


def _close_brain_record(token: str, reason: str, pnl_pct: float):
    """Close the brain DB record for a guppy position."""
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
              AND signal = 'guppy'
        """, (
            _get_current_price(token) or 0,
            pnl_pct,
            f'guppy_{reason}',
            reason,
            token.upper()
        ))
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        log(f"  Failed to close DB record for {token}: {e}", "WARN")


# ── Core Scanning ───────────────────────────────────────────────────────────

# Tokens to scan (None = scan all available in candles_1m)
SCAN_TOKENS = None  # None = auto-detect from candles.db

# Signal threshold
MIN_SIGNAL_CONFIDENCE = 0.60


def scan_for_signals() -> list:
    """
    Scan configured tokens for guppy signals.
    Returns list of (token, signal_dict) for signals that pass threshold.
    """
    tokens = SCAN_TOKENS
    if tokens is None:
        tokens = gs.get_available_tokens(interval="1m")
        log(f"Auto-detected {len(tokens)} tokens in candles_1m", "SCAN")

    log(f"Scanning {len(tokens)} tokens for guppy signals (live={GUPPY_LIVE_MODE})...", "SCAN")

    results = []
    for token in tokens:
        rows = gs.get_candles(token, lookback=gs.DEFAULT_LOOKBACK, interval="1m")
        if not rows:
            continue

        sig = gs.detect_guppy_signal(rows)
        if sig is None:
            continue

        if sig['confidence'] < MIN_SIGNAL_CONFIDENCE:
            log(f"  {token}: conf={sig['confidence']:.2f} below threshold {MIN_SIGNAL_CONFIDENCE}", "SKIP")
            continue

        results.append((token, sig))
        log(f"  SIGNAL {token}: {sig['signal']} conf={sig['confidence']:.2f} "
            f"sep={sig['separation']:.3f}% squeeze={sig['squeeze']} "
            f"vol={sig['volume_confirm']}", "SIGNAL")

    return results


def check_exits() -> list:
    """
    Check all open guppy positions for exit conditions.
    Returns list of (token, pos, exit_info) for positions that should close.
    """
    data = _load_json()
    positions = data.get('positions', {})

    if not positions:
        return []

    exits = []
    for token, pos in list(positions.items()):
        rows = gs.get_candles(token, lookback=gs.DEFAULT_LOOKBACK, interval="1m")
        if not rows:
            continue

        exit_check = gs.detect_guppy_exit(rows, pos['direction'])
        if exit_check['exit']:
            exits.append((token, pos, exit_check))
            log(f"  EXIT {token}: {exit_check['reason']} "
                f"price={exit_check['price']:.4f} signal={exit_check['signal_price']:.4f}", "EXIT")
        else:
            # Update current price and pnl
            cur_price = rows[-1][4]
            if cur_price:
                pnl = (cur_price - pos['entry_price']) / pos['entry_price'] * 100.0
                if pos['direction'] == 'SHORT':
                    pnl = -pnl
                pos['cur_price'] = cur_price
                pos['pnl_pct'] = round(pnl, 4)

    if exits:
        # Remove exited positions from tracker
        for token, pos, exit_info in exits:
            del data['positions'][token]
        data.setdefault('closed', [])
        save_all(data)

    # Always save to refresh current prices even if no exits
    if not exits and positions:
        save_all(data)

    return exits


# ── Trade Execution ─────────────────────────────────────────────────────────

def execute_open(token: str, signal: dict, entry_price: float, size: float = 0.5):
    """Execute a guppy signal — open position."""
    direction = signal['direction']

    if not GUPPY_LIVE_MODE:
        log(f"[DRY] Would open {token} {direction} @ {entry_price:.4f} size={size}", "EXEC")
        add_position(token, signal, entry_price, size)
        return

    # Live mode
    try:
        result = mirror_open(token, direction, entry_price, leverage=10)
        if result.get('success'):
            log(f"mirror_open({token}): success", "EXEC")
            add_position(token, signal, entry_price, size)
            _create_brain_record(token, direction, signal, size, entry_price)
        else:
            log(f"mirror_open FAILED for {token}: {result.get('message')}", "FAIL")
    except Exception as e:
        log(f"mirror_open EXCEPTION for {token}: {e}", "FAIL")


def execute_close(token: str, pos: dict, exit_info: dict):
    """Execute an exit for a guppy position."""
    reason   = exit_info['reason']
    exit_price = exit_info['price']
    pnl_pct  = ((exit_price - pos['entry_price']) / pos['entry_price']) * 100.0
    if pos['direction'] == 'SHORT':
        pnl_pct = -pnl_pct

    if not GUPPY_LIVE_MODE:
        log(f"[DRY] Would close {token} {pos['direction']} @ {exit_price:.4f} pnl={pnl_pct:+.4f}%", "EXEC")
        remove_position(token, reason, exit_price, pnl_pct)
        return

    try:
        result = mirror_close(token, pos['direction'])
        if result.get('success') or result.get('closed', False):
            log(f"mirror_close({token}): success", "EXEC")
            remove_position(token, reason, exit_price, pnl_pct)
            _close_brain_record(token, reason, pnl_pct)
        else:
            log(f"mirror_close FAILED for {token}: {result.get('message')}", "FAIL")
    except Exception as e:
        log(f"mirror_close EXCEPTION for {token}: {e}", "FAIL")


# ── Commands ───────────────────────────────────────────────────────────────

def cmd_scan():
    """Scan for new signals and open positions."""
    log(f"=== GUPPY SCAN (mode={'LIVE' if GUPPY_LIVE_MODE else 'DRY'}) ===", "START")

    signals = scan_for_signals()
    opened = 0

    for token, sig in signals:
        entry_price = _get_current_price(token)
        if entry_price is None:
            continue

        # Check if already open
        positions = load_positions()
        if token.upper() in positions:
            continue

        execute_open(token, sig, entry_price)
        opened += 1

    log(f"Scan complete: {len(signals)} signals found, {opened} positions opened", "DONE")


def cmd_monitor():
    """Check exits for open positions."""
    log(f"=== GUPPY MONITOR (mode={'LIVE' if GUPPY_LIVE_MODE else 'DRY'}) ===", "START")

    exits = check_exits()

    for token, pos, exit_info in exits:
        execute_close(token, pos, exit_info)

    if not exits:
        positions = load_positions()
        log(f"Monitor complete: {len(positions)} position(s) open, no exits triggered", "DONE")
    else:
        log(f"Monitor complete: {len(exits)} position(s) closed", "DONE")


def cmd_status():
    """Show current open positions from tracker JSON."""
    data = _load_json()
    positions = data.get('positions', {})
    closed    = data.get('closed', [])

    log(f"=== GUPPY STATUS (mode={'LIVE' if GUPPY_LIVE_MODE else 'DRY'}) ===", "STATUS")
    log(f"Open positions: {len(positions)}", "STATUS")
    for token, pos in positions.items():
        log(f"  {token}: {pos['direction']} entry={pos['entry_price']:.4f} "
            f"cur={pos.get('cur_price', '?')} pnl={pos.get('pnl_pct', 0):+.3f}% "
            f"conf={pos.get('confidence', 0):.2f} opened={datetime.fromtimestamp(pos['opened_at']).strftime('%H:%M:%S')}", "STATUS")

    log(f"Recently closed: {len(closed)}", "STATUS")
    for c in closed[-5:]:
        log(f"  {c['token']}: {c['direction']} exit={c.get('exit_price','?')} "
            f"pnl={c.get('pnl_pct', 0):+.4f}% reason={c.get('close_reason', '?')}", "STATUS")


def cmd_close_all():
    """Emergency close all guppy positions."""
    log("=== GUPPY EMERGENCY CLOSE ===", "CLOSE")
    close_all_positions(reason="manual_close")
    log("Emergency close complete", "DONE")


# ── Main ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: run_guppy_signals.py [--scan|--monitor|--status|--close ALL] [--live]")
        print("  --scan     Scan for new signals")
        print("  --monitor  Check exits for open positions")
        print("  --status   Show open positions")
        print("  --close ALL  Emergency close all positions")
        print("  --live     Enable live trading (set GUPPY_LIVE=1 env var for systemd)")
        sys.exit(1)

    cmd = sys.argv[1].lower()

    if cmd == "--scan":
        cmd_scan()
    elif cmd == "--monitor":
        cmd_monitor()
    elif cmd == "--status":
        cmd_status()
    elif cmd == "--close" and len(sys.argv) > 2 and sys.argv[2].upper() == "ALL":
        cmd_close_all()
    else:
        print(f"Unknown command: {' '.join(sys.argv[1:])}")
        sys.exit(1)
