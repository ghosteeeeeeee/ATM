#!/usr/bin/env python3
"""
hl-sync-guardian.py — Continuous watchdog that keeps HL positions in sync with paper DB.

Runs as a background daemon. Every 60s:
  1. Fetch live HL positions
  2. Fetch paper DB open trades (exchange = 'Hyperliquid')
  3. Reconcile: if HL position exists but no paper trade → CREATE paper trade first, then close (orphan recovery)
  4. Reconcile: if paper trade exists but no HL position → mirror paper→HL (paper orphans)
  5. Sync HL realized PnL back to paper trades
  6. Close missing DB trades (position no longer on HL)
  7. Log sync status

Migrated from combined-trading.py:
  - get_copied_trades() / save_copied_trades() — tracks paper→HL mirrors
  - reconcile_hype_to_paper() — HL→paper reconciliation (key fix: creates paper trade before orphan close)
  - sync_pnl_from_hype() — syncs HL realized PnL to brain.trades
  - get_token_intel() — provides token data to ai-decider (simplified)
  - record_entry_features() / record_exit_features() — feature logging
  - close_orphan_paper_trades() — paper→HL mirroring
"""
import sys, time, json, subprocess, argparse, os, re, fcntl
sys.path.insert(0, '/root/.hermes/scripts')
from _secrets import BRAIN_DB_DICT
from hermes_file_lock import FileLock

# Non-HL tokens that appear in HL data but are not tradeable (phantom positions)
# Pruned 2026-04-02: removed WIF, BONK, PYTH, JTO, MNGO, APTOS, RAY (these ARE tradeable)
HL_TOKEN_BLOCKLIST = frozenset({'PANDORA', 'JELLY', 'FRIEND', 'FTM', 'CANTO', 'MANTA',
    'LOOM', 'SRM', 'SAGE', 'SAMO', 'DUST', 'HNT', 'STABLE', 'STBL'})

def _is_token_tradeable(token: str) -> bool:
    """Check if token is on HL blocklist (non-tradeable phantom tokens).
    Uses shared hype_cache instead of direct HL API call."""
    if token.upper() in HL_TOKEN_BLOCKLIST:
        return False
    # Verify via shared cache (written by price_collector)
    try:
        import hype_cache as hc
        mids = hc.get_allMids()
        if token not in mids:
            return False
    except:
        pass
    return True


# Clean up heartbeat on normal exit
import atexit
def _cleanup_guardian():
    global _LOCK_ACQUIRED
    _LOCK_ACQUIRED = False
    try:
        if os.path.exists(_HEARTBEAT_FILE):
            os.unlink(_HEARTBEAT_FILE)
    except Exception:
        pass
    try:
        if _lock_fd is not None:
            fcntl.flock(_lock_fd, fcntl.LOCK_UN)
            os.close(_lock_fd)
    except Exception:
        pass

atexit.register(_cleanup_guardian)

# ── Process lock: prevent multiple guardian instances ───────────────────────
# Uses a heartbeat file instead of simple flock — allows stale lock detection
# so a standby guardian can take over if the primary dies unexpectedly.
_LOCK_FILE = '/tmp/hermes-guardian.lock'
_HEARTBEAT_FILE = '/tmp/hermes-guardian-heartbeat.json'
_LOCK_ACQUIRED = False

def _is_primary_alive():
    """Check if the primary guardian process is still alive by reading its PID from heartbeat."""
    try:
        with open(_HEARTBEAT_FILE) as f:
            hb = json.load(f)
        pid = hb.get('pid')
        if pid is None:
            return True  # No PID yet, assume we're primary
        import os
        try:
            os.kill(pid, 0)
            return True  # Process alive
        except OSError:
            return False  # Process dead
    except (FileNotFoundError, json.JSONDecodeError):
        return True  # No heartbeat file — we're primary

def _write_heartbeat():
    """Write heartbeat with PID so other guardians can detect if we're alive."""
    try:
        with open(_HEARTBEAT_FILE, 'w') as f:
            json.dump({'pid': os.getpid(), 'started': time.strftime('%Y-%m-%d %H:%M:%S'), 'beat': time.time()})
    except Exception:
        pass

def _acquire_lock_with_heartbeat():
    """Acquire lock using flock + heartbeat file for stale lock detection."""
    global _LOCK_ACQUIRED
    import os

    _lock_fd = os.open(_LOCK_FILE, os.O_CREAT | os.O_RDWR, 0o644)
    try:
        fcntl.flock(_lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        _LOCK_ACQUIRED = True
    except (IOError, OSError):
        os.close(_lock_fd)
        _lock_fd = None
        if not _is_primary_alive():
            log('[WARN] Primary guardian dead — taking over lock', 'WARN')
            _lock_fd = os.open(_LOCK_FILE, os.O_CREAT | os.O_RDWR, 0o644)
            try:
                fcntl.flock(_lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                _LOCK_ACQUIRED = True
            except (IOError, OSError):
                os.close(_lock_fd)
                _lock_fd = None
                print('[FATAL] Could not acquire guardian lock — exiting')
                sys.exit(1)
        else:
            print('[FATAL] Guardian already running — exiting')
            sys.exit(1)

    _write_heartbeat()

    import threading
    def heartbeat_loop():
        while _LOCK_ACQUIRED:
            _write_heartbeat()
            time.sleep(30)
    hb_thread = threading.Thread(target=heartbeat_loop, daemon=True)
    hb_thread.start()

    return _lock_fd

_lock_fd = _acquire_lock_with_heartbeat()
sys.path.insert(0, '/root/.hermes/scripts')

from hermes_ab_utils import get_cached_ab_variant
from hermes_constants import SHORT_BLACKLIST, LONG_BLACKLIST
from hyperliquid_exchange import (
    get_open_hype_positions_curl, get_exchange, get_realized_pnl,
    get_trade_history, is_live_trading_enabled, mirror_open, hype_coin,
    is_delisted, replace_sl, replace_tp, place_tp_sl_batch, _hl_price_decimals,
    cancel_all_open_orders,
)

import json  # for json.dumps in penalty recording

# ── Instrumented checkpoint + event logging ──────────────────────────────────
try:
    from checkpoint_utils import checkpoint_write, checkpoint_read_last, detect_incomplete_run
except Exception:
    checkpoint_write = lambda *a, **k: ''
    checkpoint_read_last = detect_incomplete_run = lambda *a, **a2: None

try:
    from event_log import log_event, EVENT_POSITION_OPEN, EVENT_POSITION_CLOSED, EVENT_CHECKPOINT_RECOVERY
except Exception:
    log_event = lambda *a, **k: None

DRY = False  # Default is LIVE. Use --dry flag (not --apply) for dry-run mode.
# NOTE: systemd service runs WITHOUT --apply by default — set DRY=False here to enable guardian closes.
# Override with --apply flag if you need temporary dry-run without changing this file.
INTERVAL = 60  # seconds between checks
# BUG-FIX: CUT_LOSER_THRESHOLD was used on line ~901 before being defined at ~918 inside
# the same function → UnboundLocalError at runtime. Now defined at module scope.
CUT_LOSER_THRESHOLD = -5.0
MAX_CONSECUTIVE_FAILURES = 5
# BUG-5: Configurable slippage for guardian market closes (was hardcoded 0.01).
# 0.005 = 0.5% — conservative for liquid markets, safe for illiquid tokens.
CLOSE_SLIPPAGE = 0.005
LOG_FILE = '/root/.hermes/logs/sync-guardian.log'
DATA_DIR = '/root/.hermes/data'
COPIED_TRADES_FILE = os.path.join(DATA_DIR, 'copied-trades-state.json')

# FIX (2026-04-01): Persistent reconciliation state — prevents guardian from creating
# duplicate trade records when the same HL position is seen across multiple guardian cycles.
# Key: token.upper() -> {trade_id, entry_px, direction, reconciled_at}
# When guardian reconciles an HL position, record it here.
# Next cycle: if HL pos exists AND token is in reconciled state with a live trade_id,
# DO NOT create a new record — the existing one is the source of truth.
_RECONCILED_STATE_FILE = os.path.join(DATA_DIR, 'reconciled-hl-positions.json')

def _load_reconciled_state():
    """Load persisted reconciled state from disk."""
    try:
        with open(_RECONCILED_STATE_FILE) as f:
            return json.load(f)
    except:
        return {}

def _save_reconciled_state(state):
    """Persist reconciled state to disk, pruning entries older than 24 hours."""
    try:
        # Prune stale entries (not updated in >24h — position was closed and forgotten)
        cutoff = time.time() - 86400  # 24 hours ago
        pruned = 0
        cleaned = {}
        for tok, entry in state.items():
            reconciled_at_str = entry.get('reconciled_at', '')
            if reconciled_at_str:
                try:
                    entry_ts = time.mktime(time.strptime(reconciled_at_str, '%Y-%m-%d %H:%M:%S'))
                    if entry_ts < cutoff:
                        pruned += 1
                        continue
                except (ValueError, TypeError):
                    pass  # malformed timestamp — keep entry
            cleaned[tok] = entry
        if pruned > 0:
            log(f'  [STALE-CLEANUP] removed {pruned} stale reconciled entries (>24h old)')
        with FileLock('reconciled_state'):
            with open(_RECONCILED_STATE_FILE, 'w') as f:
                json.dump(cleaned, f)
    except Exception as e:
        log(f'  Warning: could not save reconciled state: {e}', 'WARN')

def _mark_hl_reconciled(token, trade_id, entry_px, direction):
    """Record that an HL position has been reconciled to a specific trade_id."""
    state = _load_reconciled_state()
    state[token.upper()] = {
        'trade_id': trade_id,
        'entry_px': entry_px,
        'direction': direction,
        'reconciled_at': time.strftime('%Y-%m-%d %H:%M:%S')
    }
    _save_reconciled_state(state)

def _get_reconciled_trade_id(token):
    """Get the trade_id that was reconciled for this HL position, or None."""
    state = _load_reconciled_state()
    return state.get(token.upper(), {}).get('trade_id')

def _clear_reconciled_token(token):
    """Clear reconciled state when an HL position is gone (closed on HL)."""
    state = _load_reconciled_state()
    if token.upper() in state:
        del state[token.upper()]
        _save_reconciled_state(state)

# ── Pending orphan close retry state ─────────────────────────────────────────
# When market_close fails (rate-limited), we record the token here so the next
# cycle can immediately retry the close without waiting INTERVAL seconds.
_PENDING_RETRY_FILE = os.path.join(DATA_DIR, 'guardian-pending-retry.json')

# ── Missing Tracking (fix for 429 rate-limit false positives) ─────────────────
# When HL returns 429, real positions may be invisible for 1 cycle.
# We track which tokens have been "missing from HL" for consecutive cycles.
# A paper=False trade is only closed as HL_CLOSED after 2+ consecutive missing cycles.
# A single 429-induced invisible cycle will not close the trade.
_MISSING_TRACKING_FILE = os.path.join(DATA_DIR, 'guardian-missing-tracking.json')

def _load_missing_tracking():
    """Load {token: {'cycles': N, 'first_seen': timestamp}} for tokens missing from HL."""
    try:
        with open(_MISSING_TRACKING_FILE) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def _save_missing_tracking(state):
    """Persist missing tracking state."""
    try:
        with FileLock('missing_tracking'):
            with open(_MISSING_TRACKING_FILE, 'w') as f:
                json.dump(state, f, indent=2)
    except Exception as e:
        log(f'  Warning: could not save missing tracking: {e}', 'WARN')

def _load_pending_retry():
    """Load set of tokens pending orphan close retry."""
    try:
        with open(_PENDING_RETRY_FILE) as f:
            data = json.load(f)
        return set(data.get('tokens', []))
    except (FileNotFoundError, json.JSONDecodeError):
        return set()

def _save_pending_retry(tokens: list):
    """Save tokens that need orphan close retry."""
    with FileLock('pending_retry'):
        with open(_PENDING_RETRY_FILE, 'w') as f:
            json.dump({'tokens': list(tokens), 'saved_at': time.strftime('%Y-%m-%d %H:%M:%S')}, f)

def _clear_pending_retry(tokens: list):
    """Remove tokens from pending retry set after successful close."""
    pending = _load_pending_retry()
    for t in tokens:
        pending.discard(t.upper())
    with FileLock('pending_retry'):
        with open(_PENDING_RETRY_FILE, 'w') as f:
            json.dump({'tokens': list(pending), 'saved_at': time.strftime('%Y-%m-%d %H:%M:%S')}, f)

def _retry_phantom_close_fills():
    """
    FIX (2026-04-14): PHANTOM_CLOSE trades have exit_price=0 because HL fills
    hadn't propagated when the guardian first closed them. On each guardian cycle,
    try to find the real HL fill price and backfill the trade record.

    Uses _get_fills_cached which has a 5-min TTL — if HL fills have propagated
    by the next guardian cycle (up to 60s later), they will be in the cache
    and this will update exit_price at zero API cost.

    Only processes up to 5 PHANTOM_CLOSE trades per cycle to avoid slow cycles.
    """
    import psycopg2  # local import like other functions in this file
    from _secrets import BRAIN_DB_DICT
    try:
        conn = psycopg2.connect(**BRAIN_DB)
        cur = conn.cursor()
        # Find PHANTOM_CLOSE trades with exit_price=0 that haven't been retried
        # recently (don't retry same trade every cycle — wait at least 60s between attempts)
        cur.execute('''
            SELECT id, token, direction, entry_price, pnl_pct,
                   EXTRACT(EPOCH FROM (NOW() - close_time)) as age_seconds
            FROM trades
            WHERE server = 'Hermes'
              AND status = 'closed'
              AND close_reason = 'PHANTOM_CLOSE'
              AND exit_price = 0
            ORDER BY close_time ASC
            LIMIT 5
        ''')
        phantom_trades = cur.fetchall()
        if not phantom_trades:
            return

        log(f'PHANTOM_CLOSE backfill: found {len(phantom_trades)} trades to retry', 'INFO')
        updated = 0
        for trade_row in phantom_trades:
            trade_id, token, direction, entry_price, pnl_pct, age_seconds = trade_row
            if age_seconds < 60:
                # Already retried recently, skip
                continue

            # Try to get HL fill price
            window_end = int(time.time() * 1000)
            window_start = window_end - 300_000  # 5 min lookback
            fills = _get_fills_cached(token.upper(), window_start, window_end)
            close_fills = [f for f in fills
                         if f['coin'].upper() == token.upper() and f.get('side') == 'B']

            if close_fills:
                total_sz = sum(f['sz'] for f in close_fills)
                wavg_exit = sum(f['px'] * f['sz'] for f in close_fills) / total_sz
                # Recalculate pnl_pct from real HL data
                entry_px = float(entry_price)
                pnl_pct = ((wavg_exit - entry_px) / entry_px) * 100
                # Round to 6 decimal places
                pnl_pct = round(pnl_pct, 6)

                cur.execute('''
                    UPDATE trades
                    SET exit_price = %s,
                        pnl_pct = %s,
                        close_reason = 'phantom_close_filled',
                        close_time = NOW()
                    WHERE id = %s
                      AND exit_price = 0
                ''', (wavg_exit, pnl_pct, trade_id))
                conn.commit()
                updated += 1
                log(f'  {token} PHANTOM_CLOSE backfilled: exit={wavg_exit:.4f} pnl={pnl_pct:.3f}%', 'PASS')
            else:
                log(f'  {token} PHANTOM_CLOSE: no HL fill yet (age={age_seconds:.0f}s) — will retry next cycle', 'WARN')

        log(f'PHANTOM_CLOSE backfill complete: {updated}/{len(phantom_trades)} updated', 'INFO')
        conn.close()
    except Exception as e:
        log(f'PHANTOM_CLOSE backfill error: {e}', 'FAIL')


# ── BUG-4/15: Persistent closed-trade dedup set ─────────────────────────────────
_CLOSED_SET_FILE = os.path.join(DATA_DIR, 'guardian-closed-set.json')
_KILL_SWITCH_FILE = os.path.join(DATA_DIR, 'guardian_kill_switch.json')

# ── BUG-FIX B7: Manual close kill switch ─────────────────────────────────────
# T can tell guardian "I manually closed this token" by adding it to this file.
# Guardian will NOT close that token — it will treat it as an orphan HL close.
def _load_kill_switch() -> set:
    """Load set of tokens T has manually closed (guardian will skip these)."""
    try:
        with open(_KILL_SWITCH_FILE) as f:
            data = json.load(f)
            return set(data.get('closed', []))
    except (FileNotFoundError, json.JSONDecodeError):
        return set()

def _is_token_killed(token: str) -> bool:
    """Check if token is in the manual kill switch (T closed it manually)."""
    return token.upper() in _load_kill_switch()

def _add_to_kill_switch(token: str):
    """Add a token to the kill switch. Call this when T manually closes a token."""
    try:
        with FileLock('kill_switch'):
            ks = _load_kill_switch()
            ks.add(token.upper())
            with open(_KILL_SWITCH_FILE, 'w') as f:
                json.dump({'description': 'Guardian kill switch — tokens in closed list will NOT be closed by guardian', 'closed': sorted(ks)}, f, indent=2)
        log(f'Kill switch: added {token.upper()}', 'INFO')
    except Exception as e:
        log(f'Kill switch write error: {e}', 'FAIL')

def _remove_from_kill_switch(token: str):
    """Remove a token from the kill switch (e.g., when re-entering the position)."""
    try:
        ks = _load_kill_switch()
        ks.discard(token.upper())
        with open(_KILL_SWITCH_FILE, 'w') as f:
            json.dump({'description': 'Guardian kill switch', 'closed': sorted(ks)}, f, indent=2)
    except Exception:
        pass


def _load_closed_set() -> set:
    """Load persisted closed-trade IDs from disk."""
    try:
        with open(_CLOSED_SET_FILE) as f:
            data = json.load(f)
        return set(int(x) for x in data)  # BUG-6 fix: return integers to match _close_paper_trade_db trade_id type
    except:
        return set()


def _save_closed_set():
    """Persist closed-trade IDs to disk for crash-restart dedup."""
    try:
        with FileLock('closed_trade_ids'):
            with open(_CLOSED_SET_FILE, 'w') as f:
                json.dump(list(_CLOSED_THIS_CYCLE), f)
    except Exception as e:
        log(f'  Warning: could not save closed set: {e}', 'WARN')

# Deduplication: track trade IDs closed this cycle to prevent duplicate closes.
# Both record_closed_trade() (Step 6) and _close_paper_trade_db() (Steps 7-8)
# may fire for the same trade. Once a trade_id is closed this cycle, skip re-closes.
_CLOSED_THIS_CYCLE=_load_closed_set()  # loaded from disk for crash-restart dedup
_CLOSED_HL_COINS=set()  # tokens where HL position was closed this cycle

# Ensure data dir exists
os.makedirs(DATA_DIR, exist_ok=True)


def log(msg, level='INFO'):
    # Logs to stdout only — systemd service redirects stdout to sync-guardian.log
    # via StandardOutput=append:. Direct file writes removed to prevent doubling.
    ts = time.strftime('%Y-%m-%d %H:%M:%S')
    print(f'[{ts}] [{level}] {msg}', flush=True)  # flush=True for immediate write via systemd


# ─── Copied Trades State (migrated from combined-trading.py) ──────────────────

def get_copied_trades():
    """
    Returns dict with 'copied' and 'closed' lists.
    Handles corrupt/bad-state files (was crashing with [] instead of dict).
    State file: /root/.hermes/data/copied-trades-state.json
    """
    try:
        with open(COPIED_TRADES_FILE) as f:
            data = json.load(f)
        if not isinstance(data, dict):
            data = {"copied": [], "closed": []}
            save_copied_trades(data)
        return data
    except (FileNotFoundError, json.JSONDecodeError):
        return {"copied": [], "closed": []}


def save_copied_trades(state):
    """Save copied trades state to JSON file."""
    with FileLock('copied_trades'):
        with open(COPIED_TRADES_FILE, 'w') as f:
            json.dump(state, f)


# ─── DB Helpers ────────────────────────────────────────────────────────────────

def get_db_connection():
    """Get a psycopg2 connection to the brain DB."""
    import psycopg2
    try:
        return psycopg2.connect(**BRAIN_DB_DICT)
    except Exception as e:
        log(f'DB connection error: {e}', 'FAIL')
        return None


def get_db_open_trades():
    """Get open trades from paper DB where exchange = Hyperliquid. Includes 'id' for Step 8."""
    r = subprocess.run([
        'psql', '-U', 'postgres', '-d', 'brain', '-t', '-c',
        "SELECT id, token, direction, entry_price, leverage, amount_usdt, paper FROM trades WHERE status = 'open' AND exchange = 'Hyperliquid'"
    ], capture_output=True, text=True, timeout=10)
    if r.returncode != 0:
        log(f'get_db_open_trades FAILED: {r.stderr}', 'FAIL')
        return []
    trades = []
    for line in r.stdout.strip().splitlines():
        if '|' in line:
            parts = [p.strip() for p in line.split('|')]
            if len(parts) >= 5:
                trades.append({
                    'id': int(parts[0]) if parts[0] else None,
                    'token': parts[1],
                    'direction': parts[2],
                    'entry_price': float(parts[3]) if parts[3] else 0,
                    'leverage': float(parts[4]) if parts[4] else 1,
                    'amount_usdt': float(parts[5]) if parts[5] else 50,
                    'paper': parts[6].lower() == 't' if len(parts) > 6 else True,
                    'status': 'open',   # SQL already filters status='open'; added for reconcile_tp_sl filter
                })
    return trades


def get_all_open_trades():
    """Get ALL open trades (paper and real) from DB."""
    r = subprocess.run([
        'psql', '-U', 'postgres', '-d', 'brain', '-t', '-c',
        "SELECT token, direction, entry_price, leverage, amount_usdt, paper FROM trades WHERE status = 'open'"
    ], capture_output=True, text=True, timeout=10)
    if r.returncode != 0:
        log(f'get_all_open_trades FAILED: {r.stderr}', 'FAIL')
        return []
    trades = []
    for line in r.stdout.strip().splitlines():
        if '|' in line:
            parts = [p.strip() for p in line.split('|')]
            if len(parts) >= 4:
                trades.append({
                    'token': parts[0],
                    'direction': parts[1],
                    'entry_price': float(parts[2]) if parts[2] else 0,
                    'leverage': float(parts[3]) if parts[3] else 1,
                    'amount_usdt': float(parts[4]) if len(parts) > 4 and parts[4] else 50,
                    'paper': parts[5].lower() == 't' if len(parts) > 5 else True,
                })
    return trades


# ─── Brain.py Integration (add_trade equivalent) ───────────────────────────────

def add_orphan_trade(token: str, direction: str, entry_price: float,
                      amount_usdt: float, leverage: int,
                      stop_loss: float = None, target: float = None) -> int:
    """
    Create a paper trade in the brain DB (equivalent to brain.py add_trade).
    Returns the new trade_id, or None if creation failed.
    This is used for orphan recovery: create the paper trade first, then close it.

    FIX: Uses atomic INSERT with NOT EXISTS to prevent race-condition duplicates
    when guardian and pipeline run simultaneously.
    """
    if DRY:
        log(f'  [DRY] Would add_orphan_trade: {token} {direction} @ {entry_price} x{leverage}', 'WARN')
        return None

    conn = get_db_connection()
    if conn is None:
        return None
    try:
        cur = conn.cursor()
        # Atomic: INSERT only if no open trade exists for this token.
        # Eliminates race condition between SELECT-then-INSERT.
        cur.execute("""
            INSERT INTO trades (token, direction, amount_usdt, entry_price,
                exchange, paper, stop_loss, target, server, status, open_time,
                pnl_usdt, pnl_pct, leverage, sl_distance, trailing_activation, trailing_distance)
            SELECT %s, %s, %s, %s, 'Hyperliquid', true, %s, %s, 'Hermes', 'open', NOW(),
                   0, 0, %s, 0.03, 0.01, 0.01
            WHERE NOT EXISTS (
                SELECT 1 FROM trades WHERE token=%s AND server='Hermes' AND status='open'
            )
            RETURNING id
        """, (token, direction, amount_usdt, entry_price,
              stop_loss, target, leverage, token))
        row = cur.fetchone()
        if row is None:
            # No row returned = INSERT was skipped (open trade already exists)
            cur.close()
            conn.close()
            log(f'  {token} already has an open trade in DB — skipping add', 'WARN')
            return None

        trade_id = row[0]
        conn.commit()
        cur.close()
        conn.close()
        log(f'  Created orphan recovery trade #{trade_id}: {token} {direction} @ {entry_price} x{leverage}', 'PASS')
        return trade_id
    except Exception as e:
        try:
            conn.rollback()
            conn.close()
        except:
            pass
        log(f'  add_orphan_trade FAILED for {token}: {e}', 'FAIL')
        return None


# ─── HL Closing ────────────────────────────────────────────────────────────────

def close_position_hl(coin: str, reason: str) -> bool:
    """Close a position on HL. Returns True on success."""
    if DRY:
        log(f'  [DRY] Would close {coin} ({reason})', 'WARN')
        return True

    try:
        exchange = get_exchange()
        result = exchange.market_close(coin=coin, slippage=CLOSE_SLIPPAGE)

        # Defensive: handle None, non-dict, or unexpected result structures
        if result is None:
            log(f'  ❌ {coin}: market_close returned None (rate-limited?)', 'FAIL')
            return False
        if not isinstance(result, dict):
            log(f'  ❌ {coin}: market_close returned {type(result).__name__}: {str(result)[:100]}', 'FAIL')
            return False

        # Try expected path: response.data.statuses
        response_data = result.get('response')
        if isinstance(response_data, dict):
            statuses = response_data.get('data', {}).get('statuses', [])
        else:
            # Unexpected: log it as a warning but treat as success (HL filled it)
            log(f'  ⚠️ {coin}: unexpected result structure: {str(result)[:200]}', 'WARN')
            return True

        if statuses is None:
            statuses = []
        for s in statuses:
            if isinstance(s, dict) and 'error' in s:
                log(f'  ❌ {coin}: {s["error"]}', 'FAIL')
                return False
        log(f'  ✅ {coin} closed ({reason})', 'PASS')
        return True
    except Exception as e:
        log(f'  ❌ {coin}: EXCEPTION {e}', 'FAIL')
        return False


# ── In-memory fill cache — prevents duplicate get_trade_history calls ───────────
# Key: (token, window_start_ms, window_end_ms) → list of fills
# Keeps fills for 5 minutes to avoid re-fetching same window
_FILL_CACHE = {}          # {(tok, w_start, w_end): {'fills': [...], 'fetched_at': timestamp}}
_FILL_CACHE_TTL = 300      # Keep cached fills for 5 minutes
_MAX_API_CALLS_PER_CYCLE = 3  # Conservative rate-limit guard

def _get_fills_cached(token: str, window_start_ms: int, window_end_ms: int):
    """
    Fetch HL fills with in-memory caching and rate-limit protection.
    Returns list of fill dicts (same as get_trade_history).
    Uses cached fills if already fetched within last 5 min.
    Limits to _MAX_API_CALLS_PER_CYCLE actual API calls per guardian cycle.
    """
    cache_key = (token.upper(), window_start_ms, window_end_ms)
    now = time.time()

    # Check cache first
    if cache_key in _FILL_CACHE:
        cached = _FILL_CACHE[cache_key]
        if now - cached['fetched_at'] < _FILL_CACHE_TTL:
            return cached['fills']  # Cache hit

    # Check rate limit guard
    cycle_key = f"_cycle_{int(now // 60)}"  # New cycle every 60s
    if not hasattr(_get_fills_cached, '_call_count'):
        _get_fills_cached._call_count = {}
    count = _get_fills_cached._call_count.get(cycle_key, 0)

    if count >= _MAX_API_CALLS_PER_CYCLE:
        log(f'  [RATE-LIMIT] get_trade_history called {count}x this cycle — using fallback', 'WARN')
        return []

    # Fetch from HL
    _get_fills_cached._call_count[cycle_key] = count + 1
    try:
        fills = get_trade_history(window_start_ms, window_end_ms)
        _FILL_CACHE[cache_key] = {'fills': fills, 'fetched_at': now}
        return fills
    except Exception as e:
        log(f'  [RATE-LIMIT] get_trade_history failed: {e}', 'WARN')
        return []


def _poll_hl_fills_for_close(token: str, close_start_ms: int):
    """
    Poll get_trade_history() up to 3 times with 5s delay to get actual HL fill data
    for a recently-closed position.
    Returns (hl_exit_price, realized_pnl) or (0.0, None) if no fills found.
    Returns (wavg_exit, float) for breakeven or losing/winning trades.

    FIX (2026-04-14): Now uses _get_fills_cached to consolidate API calls and
    prevent duplicate get_trade_history calls within the same guardian cycle.
    """
    for attempt in range(3):
        time.sleep(5)
        window_end = int(time.time() * 1000)
        fills = _get_fills_cached(token, close_start_ms, window_end)
        token_closes = [f for f in fills
                        if f['coin'].upper() == token.upper() and f.get('side') == 'B']
        if token_closes:
            total_sz = sum(f['sz'] for f in token_closes)
            wavg_exit = sum(f['px'] * f['sz'] for f in token_closes) / total_sz
            realized_pnl = sum(f['closed_pnl'] for f in token_closes)
            return wavg_exit, realized_pnl
        log(f'  Fill poll attempt {attempt+1}/3 — no close fills yet for {token}', 'WARN')
    log(f'  No HL close fills found for {token} after 3 polls', 'FAIL')
    return 0.0, None  # None = no data found, distinguish from breakeven (0.0)


def _wait_for_position_closed(token: str, timeout: int = 15) -> bool:
    """
    BUG-2 fix: Wait for a position to actually disappear from HL /info.
    Returns True if position is gone (closed/filled), False if still open.
    Polls every 2s for up to 'timeout' seconds.
    """
    deadline = time.time() + timeout
    while time.time() < deadline:
        time.sleep(2)
        try:
            positions = get_open_hype_positions_curl()
            if token not in positions:
                log(f'  [FILL CONFIRMED] {token} position closed on HL')
                return True
            log(f'  [FILL WAIT] {token} still on HL, retrying...', 'WARN')
        except Exception as e:
            log(f'  [FILL WAIT] Error checking HL positions: {e}', 'WARN')
    log(f'  [FILL TIMEOUT] {token} still on HL after {timeout}s — proceeding anyway', 'FAIL')
    return False


def _get_hl_exit_price(token: str, fallback: float = 0.0) -> float:
    """
    Attempt to get the actual HL fill price for a recently-closed position.
    Polls trade history up to 3 times with 5s delay using _get_fills_cached.
    Returns the weighted-average close-fill price, or fallback if no fills found.
    Only considers side='B' (close) fills — not entry fills (side='A').

    FIX (2026-04-14): Uses _get_fills_cached to avoid duplicate API calls.
    If no fills found after 3 attempts (15s), falls back to provided fallback.
    """
    for attempt in range(3):
        time.sleep(5)
        window_end = int(time.time() * 1000)
        window_start = window_end - 300_000  # 5 min lookback
        fills = _get_fills_cached(token, window_start, window_end)
        # Only use close fills (side='B'), not entry fills (side='A')
        token_closes = [f for f in fills
                       if f['coin'].upper() == token.upper() and f.get('side') == 'B']
        if token_closes:
            total_sz = sum(f['sz'] for f in token_closes)
            wavg = sum(f['px'] * f['sz'] for f in token_closes) / total_sz
            log(f'  HL exit price for {token}: {wavg:.4f} (from {len(token_closes)} close fills)')
            return wavg
    log(f'  ⚠️ guardian_missing {token}: using estimated exit price (HL fill not available)', 'WARN')
    return fallback


def record_closed_trade(token: str, direction: str, entry_px: float, exit_px: float,
                        pnl_pct: float, lev: float, amount: float, reason: str,
                        use_hl_fills: bool = True):
    """
    DEPRECATED — Orphan HL positions are now handled by _close_orphan_paper_trade_by_id
    which does an UPDATE (not INSERT) to avoid duplicate trade records.
    This function is kept for backward compatibility but does nothing.
    """
    log(f'  record_closed_trade() is deprecated — orphan closes now use '
        f'_close_orphan_paper_trade_by_id (UPDATE not INSERT)', 'WARN')


# ─── Reconcile HL→Paper (migrated from combined-trading.py) ───────────────────

def reconcile_hype_to_paper(hl_pos, prices):
    """
    Two-way reconciliation: Update paper trades with real HL entry prices.
    
    RULE 3 (from combined-trading.py): When position exists in BOTH (HL + Paper):
    - HL data is sole source of truth
    - Update DB: entry_price, stop_loss, target, leverage, amount, side
    - Overwrite any mismatched paper data

    Also handles the key orphan fix: if HL position exists but no paper trade,
    create the paper trade FIRST using HL entry data, then close it.
    This prevents the KAITO/WLFI/FARTCOIN orphan problem where trades were
    closed on HL without being recorded in the paper DB.
    """
    conn = get_db_connection()
    if conn is None:
        return 0
    updated = 0
    updated_tokens = []

    try:
        cur = conn.cursor()

        for coin, pos_data in hl_pos.items():
            entry_px = float(pos_data.get('entry_px', 0))
            sz = float(pos_data.get('size', 0))
            if entry_px == 0 or sz == 0:
                continue

            direction = pos_data.get('direction', 'LONG')
            lev = float(pos_data.get('leverage', 1)) or 1

            # Calculate SL/TP defaults
            sl_pct = 0.02
            tp_pct = 0.05
            if direction == 'SHORT':
                # SHORT: SL above entry (price rises = bad), TP below entry (price falls = good)
                sl_price = round(entry_px * (1 + sl_pct), 8)
                tp_price = round(entry_px * (1 - tp_pct), 8)
            else:
                # LONG: SL below entry (price drops = bad), TP above entry (price rises = good)
                sl_price = round(entry_px * (1 - sl_pct), 8)
                tp_price = round(entry_px * (1 + tp_pct), 8)

            # Find paper trade for this token
            cur.execute("""
                SELECT id, entry_price, direction, stop_loss, target, leverage, amount_usdt
                FROM trades
                WHERE token=%s AND status = 'open' AND exchange = 'Hyperliquid'
                LIMIT 1
            """, (coin,))
            row = cur.fetchone()

            if row:
                # RULE 3: HL is truth — update paper trade with HL data
                trade_id, paper_entry, paper_direction, paper_sl, paper_tp, paper_lev, paper_amt = row
                needs_update = False
                update_fields = []
                update_values = []

                # Entry price
                if paper_entry and abs(float(entry_px) - float(paper_entry)) / float(paper_entry) > 0.001:
                    needs_update = True
                    update_fields.append("entry_price = %s")
                    update_values.append(entry_px)
                    log(f'  🔄 {coin} entry: ${paper_entry:.4f} → ${entry_px:.4f}')

                # Side
                if paper_direction != direction:
                    needs_update = True
                    update_fields.append("direction = %s")
                    update_values.append(direction)
                    log(f'  🔄 {coin} side: {paper_direction} → {direction}')

                # Leverage
                if paper_lev and int(paper_lev) != int(lev):
                    needs_update = True
                    update_fields.append("leverage = %s")
                    update_values.append(int(lev))
                    log(f'  🔄 {coin} leverage: {paper_lev}x → {lev}x')

                # Stop loss
                if sl_price and (not paper_sl or abs(sl_price - float(paper_sl)) / float(paper_sl) > 0.001):
                    needs_update = True
                    update_fields.append("stop_loss = %s")
                    update_values.append(sl_price)
                    log(f'  🔄 {coin} SL: {paper_sl} → {sl_price}')

                # Target
                if tp_price and (not paper_tp or abs(tp_price - float(paper_tp)) / float(paper_tp) > 0.001):
                    needs_update = True
                    update_fields.append("target = %s")
                    update_values.append(tp_price)
                    log(f'  🔄 {coin} TP: {paper_tp} → {tp_price}')

                if needs_update:
                    update_values.append(trade_id)
                    cur.execute(
                        f"UPDATE trades SET {', '.join(update_fields)} WHERE id = %s",
                        update_values
                    )
                    updated += 1
                    updated_tokens.append(coin)
            else:
                # KEY FIX: Orphan HL position — check if already reconciled first.
                # FIX (2026-04-01): Previously guardian would create a new record each cycle
                # because _CLOSED_THIS_CYCLE cleared between cycles while copied_state persisted.
                # Solution: use persistent _reconciled_state to track token→trade_id mapping.
                reconciled_id = _get_reconciled_trade_id(coin)
                if reconciled_id:
                    # Already reconciled this HL position to a specific trade_id.
                    # HL is source of truth — update that existing record instead of creating new.
                    log(f'  ✅ {coin} already reconciled to trade #{reconciled_id} — updating', 'PASS')
                    # Update entry price / direction / leverage from HL
                    try:
                        conn_upd = get_db_connection()
                        cur_upd = conn_upd.cursor()
                        cur_upd.execute("""
                            UPDATE trades SET entry_price=%s, direction=%s, leverage=%s,
                                stop_loss=%s, target=%s
                            WHERE id=%s AND status='open'
                        """, (entry_px, direction, int(lev), sl_price, tp_price, reconciled_id))
                        conn_upd.commit()
                        cur_upd.close()
                        conn_upd.close()
                    except Exception as upd_err:
                        log(f'  Update reconciled trade failed: {upd_err}', 'WARN')
                    continue  # Don't create new record, don't add to updated_tokens

                log(f'  ⚠️ Orphan HL position: {coin} — creating paper trade before close', 'WARN')

                # ── Orphan detected checkpoint ─────────────────────────────────────
                try:
                    checkpoint_write('orphan_detected', {
                        'token': coin, 'trade_id': trade_id if 'trade_id' in dir() else None,
                        'workflow_state': 'ERROR_RECOVERY'
                    })
                except Exception:
                    pass

                # FIX (2026-04-02): Check if token is tradeable before creating orphan trade.
                # Previously _is_token_tradeable() was not called here, allowing blocked tokens
                # (e.g. STBL) to be created as phantom paper trades.
                if not _is_token_tradeable(coin):
                    log(f'  🚫 {coin} on blocklist or not tradeable — skipping orphan creation', 'WARN')
                    continue

                # Calculate approximate position USD value
                # Size is in contracts, price in USD per token
                curr_price = prices.get(coin) if prices else entry_px
                position_usd = abs(sz) * entry_px
                amount_usdt = min(position_usd, 20.0)  # cap at $20

                # Get realized PnL from HL for accurate entry data
                start_ms = int(time.time() * 1000) - 86400000  # look back 24h
                realized = get_realized_pnl(coin, start_ms)
                hl_entry = realized.get('entry_price', entry_px)
                if hl_entry == 0:
                    hl_entry = entry_px

                # Create paper trade
                # FIX (2026-04-05): entry_price and amount_usdt were SWAPPED in the call.
                # add_orphan_trade signature: (token, direction, entry_price, amount_usdt, leverage, ...)
                # This caused entry_price to receive amount_usdt (~$10 for BTC) and amount_usdt
                # to receive hl_entry (~$67K for BTC), corrupting all PnL calculations.
                trade_id = add_orphan_trade(
                    coin, direction, hl_entry, amount_usdt, lev, sl_price, tp_price
                )
                if trade_id:
                    _mark_hl_reconciled(coin, trade_id, hl_entry, direction)

                # KEY FIX: Actually close the orphan HL position after creating the paper trade.
                # Previously, add_orphan_trade() was called but the HL position was never closed.
                # This left real money at risk on Hyperliquid.
                # FIX (2026-04-04): Add to _CLOSED_HL_COINS BEFORE close to prevent race with Step 6.
                # FIX (2026-04-12): If market_close returns None (rate-limited or HL silent failure),
                # do NOT mark as copied. Schedule a retry: leave DB open, mark as pending_retry in
                # reconciled state so the next cycle immediately retries the close without waiting 60s.
                pending_retry_tokens = []
                if trade_id and not DRY:
                    _CLOSED_HL_COINS.add(coin.upper())  # Prevent Step 6 double-close (move before close)
                    close_result = close_position_hl(coin, f"orphan_recovery_trade_{trade_id}")
                    if close_result:
                        log(f'  Orphan {coin} HL position closed via market order', 'PASS')
                        # Mark as copied only after confirmed close
                        copied_state = get_copied_trades()
                        copied_state['copied'].append(str(trade_id))
                        save_copied_trades(copied_state)
                        log(f'  Orphan {coin} marked as copied (trade #{trade_id})', 'WARN')
                        # Immediately poll for fills and close the DB orphan trade
                        time.sleep(6)
                        _close_orphan_paper_trade_by_id(
                            trade_id, coin, direction, entry_px, lev,
                            'guardian_orphan'
                        )
                    else:
                        log(f'  ⚠️ Orphan {coin} market_close failed (trade #{trade_id}) — will retry next cycle', 'WARN')
                        _CLOSED_HL_COINS.discard(coin.upper())  # Remove from closed set on failure
                        # Mark pending retry so next cycle knows to immediately retry
                        pending_retry_tokens.append(coin.upper())
                        # DO NOT mark as copied — orphan trade stays open in DB for retry
                elif DRY:
                    log(f'  [DRY] Would mark orphan {coin} as copied', 'WARN')

                # Save pending retry tokens so next cycle can immediately retry closes without waiting
                if pending_retry_tokens and not DRY:
                    try:
                        _save_pending_retry(pending_retry_tokens)
                    except Exception as e:
                        log(f'  Could not save pending retry tokens: {e}', 'WARN')

        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        try:
            conn.rollback()
            conn.close()
        except:
            pass
        log(f'  reconcile_hype_to_paper error: {e}', 'FAIL')

    if updated > 0:
        log(f'  Reconciled {updated} paper trades from HL: {updated_tokens}')
    return updated


# ─── Sync PnL from HL (migrated from combined-trading.py) ──────────────────────


# ─── Flip Trade Logic ─────────────────────────────────────────────────────────

def _check_and_execute_flip(trade: dict, pnl_pct: float, prices: dict):
    """
    Check if trade should be flipped based on A/B test config and PnL thresholds.
    - Soft SL (1% loss): arm the flip (ready to trigger on next check)
    - Hard SL (2% loss): execute the flip immediately (close + open opposite)
    Uses flip-trade-strategy A/B test to determine behavior.
    """
    if DRY:
        return

    from hyperliquid_exchange import place_order, get_open_hype_positions_curl

    token = trade['token']
    direction = trade['direction']
    trade_id = trade['id']
    lev = float(trade.get('leverage') or 10)
    amount = float(trade.get('amount_usdt') or 50)
    entry_px = float(trade.get('entry_price') or prices.get(token, 0))

    # Get flip A/B variant
    flip_cfg = get_cached_ab_variant(token, direction, 'flip-trade-strategy')

    # Fallback defaults when flip config is missing/empty.
    # If flip config is not configured, apply sensible defaults so flip still works.
    if not flip_cfg or not flip_cfg.get('config'):
        flip_cfg = {
            'id': 'default-fallback',
            'config': {
                'flipOnSoftSL': True,   # arm flip at -1% loss
                'flipOnHardSL': True,   # execute flip at -2% loss
                'flipTrailing': False,
                'flipTrailingActivation': 0.005,
                'flipTrailingDistance': 0.005,
            }
        }

    cfg = flip_cfg.get('config', {})
    flip_on_soft = cfg.get('flipOnSoftSL', False)
    flip_on_hard = cfg.get('flipOnHardSL', False)
    flip_trailing = cfg.get('flipTrailing', False)
    trail_act = cfg.get('flipTrailingActivation', 0.005)
    trail_dist = cfg.get('flipTrailingDistance', 0.005)
    variant_id = flip_cfg.get('id', 'unknown')

    # Thresholds
    SOFT_SL = -1.0   # 1% loss → arm flip
    HARD_SL = -2.0   # 2% loss → execute flip

    conn = get_db_connection()
    if conn is None:
        return

    try:
        cur = conn.cursor()

        # Check current flip state
        cur.execute("SELECT flip_armed FROM trades WHERE id=%s", (trade_id,))
        row = cur.fetchone()
        flip_armed = bool(row[0]) if row else False

        if pnl_pct <= HARD_SL and flip_on_hard:
            # HARD SL HIT — execute flip
            opposite = 'SHORT' if direction == 'LONG' else 'LONG'
            sz = round(amount / (prices.get(token, entry_px) or entry_px), 4)

            log(f'  [FLIP] HARD SL hit on {token} trade#{trade_id} | PnL={pnl_pct:.2f}% | variant={variant_id}', 'WARN')
            log(f'  [FLIP] Closing {direction} → opening {opposite} | sz={sz} | lev={lev}', 'WARN')

            # Close current position
            from hyperliquid_exchange import close_position
            close_result = close_position(token)

            # BUG-3 fix: Wait for HL fill confirmation before opening opposite.
            # sleep(3) was unreliable — use _wait_for_position_closed() instead.
            # Retry close once if it failed or hasn't filled yet.
            if not close_result.get('success'):
                log(f'  [FLIP] Close order failed: {close_result.get("error", "unknown")} — retrying once', 'WARN')
                close_result = close_position(token)

            filled = _wait_for_position_closed(token, timeout=15)
            if not filled:
                log(f'  [FLIP] FATAL: {token} still on HL after 2 close attempts — not opening opposite', 'FAIL')
                return  # Do NOT open opposite position while original is still open

            # Verify token is tradeable on HL before opening (use cache)
            try:
                import hype_cache as hc
                mids_check = hc.get_allMids()
                if token not in mids_check:
                    log(f'  [FLIP] SKIP: {token} not tradeable on HL (not in all_mids)', 'FAIL')
                    return
            except Exception as mid_err:
                log(f'  [FLIP] Could not verify HL token list: {mid_err}', 'WARN')

            # Open opposite position
            flip_side = 'BUY' if opposite == 'LONG' else 'SELL'
            open_result = place_order(token, flip_side, sz, price=None,
                                      order_type='Market', tif='Gtc')

            if open_result.get('success'):
                # BUG-8/13 fix: look up actual regime from momentum_cache instead of 'unknown'.
                flip_intel = get_token_intel(token)
                # BUG-8 fix: use numeric encoding for regime (BULL=1, BEAR=-1, unknown=0)
                # BUG-9 fix: added LONG_BIAS/SHORT_BIAS/NEUTRAL
                _REGIME_MAP = {'BULL': 1, 'bull': 1, 'BEAR': -1, 'bear': -1, 'LONG_BIAS': 1, 'SHORT_BIAS': -1, 'NEUTRAL': 0}
                flip_regime_4h = _REGIME_MAP.get(str(flip_intel.get('regime_4h', 'unknown')), 0)
                flip_regime_1h = _REGIME_MAP.get(str(flip_intel.get('regime_1h', 'unknown')), 0)
                flip_regime_15m = _REGIME_MAP.get(str(flip_intel.get('regime_15m', 'unknown')), 0)

                # FIX (2026-04-02): read SL/TP from A/B test config instead of hardcoding -2.0/-4.0
                sl_ab_cfg = get_cached_ab_variant(token, opposite, 'sl-distance-test')
                sl_pct = 2.0  # default fallback
                tp_pct = 4.0  # default fallback (2x risk:reward)
                if sl_ab_cfg and sl_ab_cfg.get('config', {}).get('slPct'):
                    sl_pct = float(sl_ab_cfg['config']['slPct'])
                    tp_pct = sl_pct * 2  # standard 2:1 risk:reward ratio
                log(f'  [FLIP] Using SL={sl_pct}% TP={tp_pct}% (from sl-distance-test A/B)', 'INFO')

                # Record flipped trade
                trail_act_val = float(trail_act) if flip_trailing else None
                trail_dist_val = float(trail_dist) if flip_trailing else None
                cur.execute("""
                    INSERT INTO trades (token, direction, entry_price, leverage,
                        amount_usdt, exchange, status, paper,
                        entry_regime_4h, entry_regime_1h, entry_regime_15m,
                        stop_loss, target, trailing_activation, trailing_distance,
                        flip_armed, flip_variant, flipped_from_trade, created_at)
                    VALUES (%s, %s, %s, %s, %s, 'Hyperliquid', 'open', FALSE,
                        %s, %s, %s, %s, %s, %s, %s,
                        FALSE, %s, %s, NOW())
                """, (
                    token, opposite,
                    prices.get(token, entry_px),
                    lev, amount, flip_regime_4h, flip_regime_1h, flip_regime_15m,
                    -sl_pct, -tp_pct, trail_act_val, trail_dist_val,
                    variant_id, trade_id
                ))

                # Mark guardian_closed so Step 8 won't re-process this trade
                cur.execute("""
                    UPDATE trades SET status='closed', close_reason='CASCADE_FLIP',
                        exit_reason='flipped_hard_sl', flip_variant=%s,
                        guardian_closed=TRUE
                    WHERE id=%s
                """, (variant_id, trade_id))

                log(f'  [FLIP] Done: opened trade #{trade_id} opposite direction', 'INFO')
            else:
                log(f'  [FLIP] FAILED: {open_result.get("error")}', 'FAIL')

        elif SOFT_SL <= pnl_pct < 0 and flip_on_soft and not flip_armed:
            # SOFT SL HIT — arm the flip for next cycle
            cur.execute("UPDATE trades SET flip_armed=TRUE WHERE id=%s", (trade_id,))
            log(f'  [FLIP] {token} armed for flip (soft SL {pnl_pct:.2f}%) | variant={variant_id}', 'WARN')

        elif flip_armed and pnl_pct > 0:
            # Recovered from soft SL — disarm
            cur.execute("UPDATE trades SET flip_armed=FALSE WHERE id=%s", (trade_id,))
            log(f'  [FLIP] {token} disarmed (recovered to {pnl_pct:.2f}%)', 'INFO')

        conn.commit()
        cur.close()
        conn.close()

    except Exception as e:
        try:
            conn.rollback()
            conn.close()
        except:
            pass
        log(f'  [FLIP] error: {e}', 'FAIL')


def sync_pnl_from_hype(prices):
    """
    Sync HL unrealized PnL to paper trades.
    Uses HL's margin-based calculation (matches HL UI PnL display).
    """
    conn = get_db_connection()
    if conn is None:
        return

    try:
        cur = conn.cursor()

        # Get HL positions with unrealized PnL
        try:
            hl_pos = get_open_hype_positions_curl()
        except Exception as e:
            log(f'  sync_pnl_from_hype: failed to fetch HL positions: {e}', 'FAIL')
            conn.close()
            return

        if not hl_pos:
            conn.close()
            return

        # Update each open trade with HL's PnL data
        cur.execute("""
            SELECT id, token, amount_usdt, leverage, entry_price, direction
            FROM trades
            WHERE status='open' AND exchange='Hyperliquid'
        """)

        updated = 0
        for row in cur.fetchall():
            trade_id, token, amount, lev, entry, direction = row
            if token in hl_pos:
                pos_data = hl_pos[token]
                unrealized_pnl = float(pos_data.get('unrealizedPnl', 0))
                entry_price_hl = float(pos_data.get('entryPrice', entry) or entry)
                curr_price_hl = float(pos_data.get('currentPrice', prices.get(token, entry)) or prices.get(token, entry) or entry)

                if unrealized_pnl != 0:
                    # BUG-29 fix: use unrealized_pnl for display fields, but do NOT store
                    # it in hype_pnl_usdt (that's reserved for REALIZED PnL from HL fills).
                    # Storing unrealized in hype_pnl_usdt caused massive PnL overstatements
                    # (e.g. unrealized +$50 became $50 realized even on paper losses).
                    pnl_usdt = round(unrealized_pnl, 4)  # unrealized PnL from HL /account summary
                    # BUG-6 fix: use UNLEVERAGED pnl_pct (entry-based, not margin-based).
                    # OLD: leveraged pnl_pct = (unrealized_pnl / margin) * 100 — inconsistent
                    #   across leverage levels and with _close_paper_trade_db formula.
                    # NEW: unleveraged pnl_pct = (exit - entry) / entry * 100, same as
                    #   _close_paper_trade_db. This is the "raw" market return, not
                    #   amplified by leverage. Comparable across all leverage levels.
                    if entry_price_hl and entry_price_hl > 0 and curr_price_hl and curr_price_hl > 0:
                        if direction and direction.upper() == 'SHORT':
                            pnl_pct = round((entry_price_hl - curr_price_hl) / entry_price_hl * 100, 4)
                        else:
                            pnl_pct = round((curr_price_hl - entry_price_hl) / entry_price_hl * 100, 4)
                    else:
                        # Fallback to HL unrealized pnl_pct (leveraged but better than nothing)
                        pnl_pct = round(unrealized_pnl / float(amount or 50) * 100, 4)

                    cur.execute("""
                        UPDATE trades SET pnl_usdt = %s, pnl_pct = %s,
                            current_price = %s
                        WHERE id = %s
                    """, (pnl_usdt, pnl_pct,
                          prices.get(token, entry) if prices else entry,
                          trade_id))

                    # Check flip trade triggers (A/B tested: soft SL arm / hard SL flip)
                    _check_and_execute_flip(
                        {'id': trade_id, 'token': token, 'direction': direction,
                         'leverage': lev, 'amount_usdt': amount},
                        pnl_pct, prices)

                    # ── Stale Trade Rotation (2026-04-05) ────────────────────────────────
                    # If trade hasn't moved >1% in 15min AND a faster hot-set token exists
                    # → close stale trade, let ai_decider refill from hot-set.
                    # Runs after flip check; skipped for trades already being cut (<-5%).
                    # BUG-FIX: CUT_LOSER_THRESHOLD was referenced before definition (line 918
                    # defined it after line 901's use → UnboundLocalError. Moved to module-level
                    # constant. Also guard: skip if flip_armed (docstring contract).
                    if pnl_pct > CUT_LOSER_THRESHOLD:
                        # Check flip_armed before rotating — don't override a pending flip
                        cur.execute("SELECT flip_armed FROM trades WHERE id=%s", (trade_id,))
                        flip_row = cur.fetchone()
                        flip_armed = bool(flip_row[0]) if flip_row else False
                        if flip_armed:
                            log(f'  [STALE-ROTATION] {token} flip_armed — skipping rotation', 'INFO')
                        else:
                            try:
                                _check_stale_rotation(
                                    {'id': trade_id, 'token': token, 'direction': direction,
                                     'leverage': lev, 'amount_usdt': amount, 'entry_price': entry},
                                    pnl_pct, prices, conn, cur)
                            except Exception as stale_err:
                                log(f'  [STALE-ROTATION] {token} error: {stale_err}', 'WARN')

                    updated += 1
                    # Cut-loser: emergency exit at -5% loss
                    # This runs AFTER flip check, so flip has priority over hard cut
                    # ── Cut-loser: BUG-2/3/28 fix ────────────────────────────────────────
                    # IMPORTANT: close_position() sends order but does NOT wait for fill.
                    # BUG-2 old: marked DB closed BEFORE HL confirmed fill. Fix: wait first.
                    # BUG-3: flip order placed without verifying close succeeded. Fix: verify.
                    # BUG-28: no retry on failure. Fix: retry once, then alert.
                    # NOTE: CUT_LOSER_THRESHOLD moved to module scope (line 74) — was causing
                    # UnboundLocalError when used at line 904 before local def at line 931.
                    if pnl_pct <= CUT_LOSER_THRESHOLD:
                        log(f'  [CUT-LOSER] {token} PnL={pnl_pct:.2f}% <= {CUT_LOSER_THRESHOLD}% — closing', 'FAIL')
                        from hyperliquid_exchange import close_position

                        # Retry close up to 2 times on failure
                        closed_ok = False
                        for attempt in range(2):
                            close_result = close_position(token)
                            if close_result.get('success'):
                                filled = _wait_for_position_closed(token, timeout=15)
                                if filled:
                                    closed_ok = True
                                    break
                                # Still on HL — retry close
                                log(f'  [CUT-LOSER] Retry {attempt+2}/2: {token} still open on HL', 'WARN')
                            else:
                                log(f'  [CUT-LOSER] Attempt {attempt+1}/2 failed: {close_result.get("error", "unknown")}', 'WARN')

                        if not closed_ok:
                            log(f'  [CUT-LOSER] FATAL: could not close {token} after 2 attempts — trade remains open!', 'FAIL')
                        else:
                            # Only mark DB closed AFTER fill confirmed on HL
                            try:
                                conn_cut = get_db_connection()
                                if conn_cut:
                                    cur_cut = conn_cut.cursor()
                                    cur_cut.execute(
                                        "UPDATE trades SET guardian_closed=TRUE, status='closed', "
                                        "close_reason='CUT_LOSER', exit_reason='CUT_LOSER_PNL' "
                                        "WHERE id=%s AND status='open'",
                                        (trade_id,))
                                    conn_cut.commit()
                                    cur_cut.close()
                                    conn_cut.close()
                                    log(f'  [CUT-LOSER] DB updated for {token} trade #{trade_id}', 'PASS')
                            except Exception as cut_err:
                                log(f'  Cut-loser DB update error: {cut_err}', 'FAIL')
                        continue  # Skip flip check — already closing

        conn.commit()
        cur.close()
        conn.close()

        if updated > 0:
            log(f'  Synced PnL from HL for {updated} positions')

    except Exception as e:
        try:
            conn.rollback()
            conn.close()
        except:
            pass
        log(f'  sync_pnl_from_hype error: {e}', 'FAIL')


# ─── Stale Trade Rotation (2026-04-05) ───────────────────────────────────────

def _check_stale_rotation(trade: dict, pnl_pct: float, prices: dict,
                           db_conn, db_cur):
    """
    Stale Trade Rotation: close trades whose price has been flat (velocity near 0)
    if a faster hot-set token is available.

    Rule: if an open trade's price_velocity_5m indicates stasis
    AND hot-set contains a token with higher speed_percentile and same direction
    → close the stale trade, let ai_decider refill from hot-set.

    Guards:
    - Skips trades already in cut-loser territory (<-5%) — caller enforces this
    - Skips trades with flip_armed=True — caller enforces this
    - Skips DRY mode
    - Rate-limited: max 1 rotation per 3 minutes per token

    BUG-FIXES applied:
    - Threshold: was 1.0%, now 0.2% — aligned with speed_tracker STALE_VELOCITY_5M.
      The price_velocity_5m field uses 0.2% as the noise floor; 1.0% was too loose.
    - Direction: was ignoring hot-set direction (hd variable extracted but never used).
      Now filters candidates to same-direction entries only.
    - SHORT staleness: was using abs(velocity) so +0.5% and -0.5% both = stale.
      For SHORT, only positive velocity (price rising) and flat are stale.
      For LONG, only negative velocity (price falling) and flat are stale.
    - updated_at: was loaded but never checked. Now verifies data age < 15 min.
    - is_stale from DB: now respected as a fast-path skip before recalculating.
    """
    if DRY:
        return

    import json as _json, time as _time, sqlite3 as _sqlite3

    token = trade['token']
    trade_id = trade['id']
    entry_px = float(trade.get('entry_price') or 0)
    direction = trade.get('direction', 'SHORT')
    direction_upper = direction.upper()

    # 0.2% matches speed_tracker.py STALE_VELOCITY_5M — the noise floor for 5m velocity.
    # Using 1.0% here was 5x too loose and inconsistent with how is_stale is computed.
    STALE_VEL_PCT = 0.2
    STALE_AGE_SEC = 15 * 60   # 15 minutes
    RATE_LIMIT_SEC = 180      # 3 min cooldown between rotations

    # ── 1. Load speed data from runtime signals DB ──────────────────────────────
    db_path = '/root/.hermes/data/signals_hermes_runtime.db'
    if not os.path.exists(db_path):
        return

    speed_data = {}
    try:
        conn_s = _sqlite3.connect(db_path, timeout=5)
        c_s = conn_s.cursor()
        c_s.execute("""
            SELECT token, speed_percentile, price_velocity_5m, is_stale, updated_at
            FROM token_speeds
            WHERE token=?
        """, (token,))
        row = c_s.fetchone()
        if row:
            speed_data = {
                'token': row[0],
                'speed_percentile': row[1] or 50,
                'price_velocity_5m': row[2] or 0,
                'is_stale': bool(row[3]),
                'updated_at': row[4],
            }
        conn_s.close()
    except Exception as e:
        log(f'  [STALE-ROTATION] {token} speed query failed: {e}', 'WARN')
        return

    if not speed_data:
        return

    # ── 1b. Check data freshness ───────────────────────────────────────────────
    # BUG-FIX: updated_at was loaded but never used — could act on stale data
    if speed_data.get('updated_at'):
        age_sec = _time.time() - speed_data['updated_at']
        if age_sec > STALE_AGE_SEC:
            log(f'  [STALE-ROTATION] {token} speed data is {age_sec:.0f}s old — skipping', 'WARN')
            return

    signed_vel = speed_data.get('price_velocity_5m', 0) or 0  # signed velocity
    sp = speed_data.get('speed_percentile', 50) or 50

    # ── 2. Check if this trade is stale ───────────────────────────────────────
    # Respect the DB-computed is_stale as a fast path (uses correct 0.2% threshold).
    # Then apply direction-specific logic:
    #   SHORT: stale if price not falling enough (vel >= -STALE_VEL_PCT means flat or rising)
    #   LONG:  stale if price not rising enough (vel <= +STALE_VEL_PCT means flat or falling)
    # BUG-FIX: was using abs(signed_vel) so both +0.5% and -0.5% registered as stale,
    # treating a SHORT in profit (-0.5%) as stale when it should not be.
    if direction_upper == 'SHORT':
        # For SHORT: negative velocity = price fell = good (NOT stale)
        # stale if vel >= -0.2% (price is flat or rising)
        is_stale = signed_vel >= -STALE_VEL_PCT
    else:
        # For LONG: positive velocity = price rose = good (NOT stale)
        # stale if vel <= +0.2% (price is flat or falling)
        is_stale = signed_vel <= STALE_VEL_PCT

    if not is_stale:
        return  # Trade is moving fine

    # ── 3. Load hot-set and find a faster replacement ──────────────────────────
    hotset_path = '/var/www/hermes/data/hotset.json'
    if not os.path.exists(hotset_path):
        return

    try:
        with open(hotset_path) as f:
            hs = _json.load(f)
        hotset = hs.get('hotset', [])
    except Exception as e:
        log(f'  [STALE-ROTATION] hotset.json load error: {e}', 'WARN')
        return

    # Find tokens in hot-set with higher speed than this trade's token
    # Exclude: same token, opposite direction (conflicts), tokens already have open positions
    # BUG-FIX: hd (hot-set direction) was extracted but never checked — now enforced
    db_cur.execute("SELECT token, direction FROM trades WHERE status='open' AND exchange='Hyperliquid'")
    open_by_dir = {}
    for r in db_cur.fetchall():
        open_by_dir.setdefault(r[0].upper(), set()).add(r[1].upper())

    candidates = []
    for h in hotset:
        ht = h['token'].upper()
        hd = h.get('direction', 'SHORT').upper()
        if ht == token.upper():
            continue  # same token
        # BUG-FIX: skip if this token already has an open position in the SAME direction
        if token.upper() in open_by_dir and hd in open_by_dir[token.upper()]:
            continue  # already has open position in this direction
        if hd != direction_upper:
            continue  # BUG-FIX: opposite direction — don't replace SHORT with LONG or vice versa
        # Get speed for this hot-set token
        try:
            conn_hs = _sqlite3.connect(db_path, timeout=5)
            c_hs = conn_hs.cursor()
            c_hs.execute("SELECT speed_percentile, price_velocity_5m FROM token_speeds WHERE token=?", (ht,))
            hr = c_hs.fetchone()
            conn_hs.close()
            if hr:
                hs_sp = hr[0] or 50
                hs_vel = abs(hr[1] or 0)
                if hs_sp > sp and hs_vel >= STALE_VEL_PCT:
                    candidates.append({
                        'token': ht, 'direction': hd,
                        'speed_percentile': hs_sp,
                        'velocity_5m': hs_vel,
                        'confidence': h.get('confidence', 80),
                    })
        except:
            pass

    if not candidates:
        return  # No faster replacement available

    # Sort by speed_percentile descending
    candidates.sort(key=lambda x: -x['speed_percentile'])
    best = candidates[0]

    # ── 4. Rate-limit: don't rotate same token more than once per 3 min ─────────
    rate_file = '/root/.hermes/data/stale-rotation-rate.json'
    try:
        rate_data = {}
        if os.path.exists(rate_file):
            with open(rate_file) as f:
                rate_data = _json.load(f)
        last_rot = rate_data.get(token, 0)
        if _time.time() - last_rot < RATE_LIMIT_SEC:
            return  # still in cooldown
    except:
        pass

    # ── 5. Execute the rotation ────────────────────────────────────────────────
    log(f'  [STALE-ROTATION] {token} {direction} stale (vel={signed_vel:.2f}%, sp={sp:.0f}) → '
        f'closing for {best["token"]} {best["direction"]} (sp={best["speed_percentile"]:.0f}%, vel={best["velocity_5m"]:.2f}%)',
        'WARN')

    from hyperliquid_exchange import close_position

    close_result = close_position(token)
    if not close_result.get('success'):
        log(f'  [STALE-ROTATION] {token} close failed: {close_result.get("error")}', 'FAIL')
        return

    filled = _wait_for_position_closed(token, timeout=15)
    if not filled:
        log(f'  [STALE-ROTATION] {token} NOT closed after 15s — aborting rotation', 'FAIL')
        return

    # Mark trade as closed in DB
    try:
        db_cur.execute("""
            UPDATE trades SET status='closed', guardian_closed=TRUE,
                close_reason='STALE_ROTATION', exit_reason='STALE_ROTATION_VELOCITY_LOW',
                pnl_pct=%s, current_price=%s
            WHERE id=%s AND status='open'
        """, (pnl_pct, prices.get(token, entry_px), trade_id))
        db_conn.commit()
        log(f'  [STALE-ROTATION] {token} trade #{trade_id} closed (stale)', 'PASS')
    except Exception as db_err:
        log(f'  [STALE-ROTATION] DB update error: {db_err}', 'FAIL')

    # Update rate limit
    try:
        rate_data[token] = _time.time()
        with open(rate_file, 'w') as f:
            _json.dump(rate_data, f)
    except:
        pass

    log(f'  [STALE-ROTATION] Replaced {token} → {best["token"]} ({best["direction"]}) '
        f'conf={best["confidence"]:.0f}% sp={best["speed_percentile"]:.0f}%', 'INFO')


# ─── Token Intel (simplified from combined-trading.py) ───────────────────────

def get_token_intel(token: str) -> dict:
    """
    Simplified token intel: reads from brain DB momentum cache.
    Returns the same dict structure as combined-trading's get_token_intel().
    """
    conn = get_db_connection()
    if conn is None:
        return {}

    try:
        cur = conn.cursor()
        # Check for momentum_cache data in the brain DB
        cur.execute("""
            SELECT rsi_14, macd_hist, atr_14, bb_position, slope_4h, regime_4h, trend
            FROM momentum_cache
            WHERE token=%s
            ORDER BY updated_at DESC LIMIT 1
        """, (token,))
        row = cur.fetchone()
        conn.close()

        if row and row[0] is not None:
            return {
                'rsi_14': float(row[0]) if row[0] else None,
                'macd_hist': float(row[1]) if row[1] else None,
                'atr_14': float(row[2]) if row[2] else None,
                'bb_position': float(row[3]) if row[3] else None,
                'slope_4h': float(row[4]) if row[4] else None,
                'regime_4h': row[5] if row[5] else None,
                'trend': row[6] if row[6] else None,
            }
    except Exception as e:
        try:
            conn.close()
        except:
            pass
        # momentum_cache table might not exist — return empty
        pass

    return {}


# ─── Feature Logging (migrated from combined-trading.py) ──────────────────────

def record_entry_features(trade_id: int, token: str):
    """
    Record technical indicators at trade entry.
    Updates brain.trades with entry_rsi_14, entry_macd_hist, etc.
    """
    intel = get_token_intel(token)
    if not intel or not any(intel.values()):
        return False

    conn = get_db_connection()
    if conn is None:
        return False

    try:
        cur = conn.cursor()
        cur.execute("""
            UPDATE trades SET
                entry_rsi_14 = %s,
                entry_macd_hist = %s,
                entry_atr_14 = %s,
                entry_bb_position = %s,
                entry_slope_4h = %s,
                entry_regime_4h = %s,
                entry_trend = %s,
                features_recorded = TRUE,
                predicted_return = %s
            WHERE id = %s
        """, (
            intel.get('rsi_14'),
            intel.get('macd_hist'),
            intel.get('atr_14'),
            intel.get('bb_position'),
            intel.get('slope_4h'),
            intel.get('regime_4h'),
            intel.get('trend'),
            0.0,  # predicted_return: was writing regime string; numeric value TBD
            trade_id
        ))
        conn.commit()
        cur.close()
        conn.close()
        log(f'  Feature entry: {token} trade #{trade_id} — regime={intel.get("regime_4h")}, trend={intel.get("trend")}')
        return True
    except Exception as e:
        try:
            conn.rollback()
            conn.close()
        except:
            pass
        log(f'  record_entry_features error: {e}', 'FAIL')
        return False


def record_exit_features(trade_id: int, exit_price: float, exit_reason: str):
    """
    Record exit details and calculate actual vs predicted return.
    """
    conn = get_db_connection()
    if conn is None:
        return

    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT entry_price, direction, entry_regime_4h, leverage
            FROM trades WHERE id = %s
        """, (trade_id,))
        row = cur.fetchone()

        if not row:
            conn.close()
            return

        entry_price, direction, regime, leverage = row
        if entry_price is None:
            conn.close()
            return
        entry_price = float(entry_price)
        leverage = float(leverage) if leverage else 10

        if direction == 'LONG':
            actual_return = ((exit_price - entry_price) / entry_price) * 100 * leverage
        else:
            actual_return = ((entry_price - exit_price) / entry_price) * 100 * leverage

        cur.execute("""
            UPDATE trades SET
                exit_reason = %s,
                actual_return = %s
            WHERE id = %s
        """, (exit_reason, round(actual_return, 4), trade_id))
        conn.commit()
        cur.close()
        conn.close()
        log(f'  Feature exit: trade #{trade_id} {exit_reason} actual_return={actual_return:.2f}% regime={regime}')
    except Exception as e:
        try:
            conn.rollback()
            conn.close()
        except:
            pass
        log(f'  record_exit_features error: {e}', 'FAIL')


# ─── Mirror Paper → HL (migrated from combined-trading.py) ────────────────────

def close_orphan_paper_trades(hl_pos, prices):
    """
    Handle paper trades that don't have corresponding HL position.
    If room exists on HL → mirror the paper trade.
    If at max positions → close the paper trade.

    Quality filter: only sync top 5 paper trades by confidence.
    """
    conn = get_db_connection()
    if conn is None:
        return 0

    try:
        cur = conn.cursor()

        # Get top 5 paper trades by confidence (quality filter from combined-trading.py)
        cur.execute("""
            SELECT id, token, direction, entry_price, leverage, amount_usdt, confidence
            FROM trades
            WHERE status = 'open' AND paper = true AND exchange = 'Hyperliquid'
            ORDER BY confidence DESC NULLS LAST, open_time ASC
            LIMIT 5
        """)
        top_trades = {str(row[0]): row for row in cur.fetchall()}
        log(f'  Quality filter: syncing top {len(top_trades)} paper trades to HL')
        conn.close()

        added_count = 0
        closed_count = 0
        MAX_HYPE_POSITIONS = 5

        # Count current HL positions
        hype_count = len([p for p in hl_pos.values() if float(p.get('size', 0)) != 0])

        # ── Paper=True path: mirror hot-set trades to HL ────────────────
        conn2 = get_db_connection()
        cur2 = conn2.cursor()
        cur2.execute("""
            SELECT id, token, direction, entry_price, leverage, amount_usdt
            FROM trades
            WHERE status = 'open' AND paper = true AND exchange = 'Hyperliquid'
        """)
        all_paper_trades = cur2.fetchall()

        for row in all_paper_trades:
            trade_id, token, direction, entry, lev, amount = row
            trade_id_str = str(trade_id)

            # Get copied trades state
            copied_state = get_copied_trades()
            copied_ids = [str(x) for x in copied_state.get('copied', [])]

            # Already copied to HL?
            if trade_id_str in copied_ids:
                # Verify HL position still exists
                if token in hl_pos and float(hl_pos[token].get('size', 0)) != 0:
                    log(f'  ✅ {token} verified on HL (copied trade #{trade_id})')
                else:
                    # HL position not yet registered — wait before assuming missing.
                    # Race: paper trade created, HL order submitted, but HL hasn't confirmed yet.
                    # Retry up to 6 times with 5s delay = 30s total (was 3×5s=15s).
                    registered = False
                    for retry in range(6):
                        time.sleep(5)
                        try:
                            hl_pos_retry = get_open_hype_positions_curl()
                            if token in hl_pos_retry and float(hl_pos_retry[token].get('size', 0)) != 0:
                                log(f'  ✅ {token} verified on HL after {retry+1} retries')
                                registered = True
                                break
                        except Exception as e:
                            log(f'  ⚠️ Retry {retry+1} failed for {token}: {e}', 'WARN')
                    if not registered:
                        log(f'  ⚠️ {token} copied but no HL position after retries — closing paper', 'WARN')
                        _close_paper_trade_db(trade_id, token, prices.get(token, entry), 'ORPHAN_PAPER')
                        closed_count += 1
                    # Remove from copied list
                    try:
                        copied_state['copied'].remove(trade_id_str)
                        copied_state['closed'].append(trade_id_str)
                        save_copied_trades(copied_state)
                    except:
                        pass
                continue

            # Not copied yet — check if HL has this position
            if token in hl_pos:
                continue  # Position exists, will be reconciled

            # No HL position — try to mirror
            curr_price = prices.get(token) if prices else None
            if not curr_price:
                continue

            lev_int = int(lev) if lev else 10
            amount_float = float(amount) if amount else 20

            if hype_count >= MAX_HYPE_POSITIONS:
                # At max — close the paper trade
                log(f'  At max positions ({MAX_HYPE_POSITIONS}), closing paper: {token}', 'WARN')
                _close_paper_trade_db(trade_id, token, curr_price, 'MAX_POSITIONS')
                closed_count += 1
                continue

            # Mirror paper trade to HL — HOT-SET ONLY (blacklist-aware)
            ht = hype_coin(token)
            try:
                conn_s = sqlite3.connect('/root/.hermes/data/signals_hermes_runtime.db')
                cur_s = conn_s.cursor()
                cur_s.execute("SELECT 1 FROM signals WHERE token=? AND hot_cycle_count>=1 LIMIT 1", (ht,))
                in_hot = cur_s.fetchone() is not None
                conn_s.close()
            except Exception:
                in_hot = False  # Fail open on DB errors
            blocked = (direction.upper() == 'SHORT' and ht.upper() in SHORT_BLACKLIST) or \
                      (direction.upper() == 'LONG' and ht.upper() in LONG_BLACKLIST)
            if not in_hot:
                log(f'  {token}: NOT in hot-set — paper only, live mirror blocked', 'WARN')
            elif blocked:
                bl = 'SHORT_BLACKLIST' if direction.upper() == 'SHORT' else 'LONG_BLACKLIST'
                log(f'  {token}: on {bl} ({direction}) — closing paper trade', 'WARN')
                _close_paper_trade_db(trade_id, token, curr_price, 'HOTSET_BLOCKED')
            elif not DRY and is_live_trading_enabled():
                try:
                    result = mirror_open(ht, direction, float(curr_price), leverage=lev_int)
                    if result.get('success'):
                        # Mark as copied
                        copied_state['copied'].append(trade_id_str)
                        save_copied_trades(copied_state)
                        log(f'  Mirrored {token} to HL: {direction} @ {curr_price}', 'PASS')
                        hype_count += 1
                        added_count += 1
                    else:
                        log(f'  Mirror failed for {token}: {result.get("message")}', 'WARN')
                except Exception as me:
                    log(f'  Mirror error for {token}: {me}', 'WARN')
            elif DRY:
                log(f'  [DRY] Would mirror {token} {direction} @ {curr_price} x{lev_int}', 'WARN')
                hype_count += 1
                added_count += 1

        conn2.close()

        # ── Paper=False path: place missing real trades on HL immediately ──
        # These trades were created with paper=False (live) but never reached HL.
        # Mirror them now. Skip if already in copied (guardian crashed after placing).
        conn3 = get_db_connection()
        cur3 = conn3.cursor()
        cur3.execute("""
            SELECT id, token, direction, entry_price, leverage, amount_usdt
            FROM trades
            WHERE status = 'open' AND paper = false AND exchange = 'Hyperliquid'
        """)
        live_missing = cur3.fetchall()
        conn3.close()

        for row in live_missing:
            trade_id, token, direction, entry, lev, amount = row
            trade_id_str = str(trade_id)
            if token in hl_pos and float(hl_pos[token].get('size', 0)) != 0:
                continue  # On HL — reconciled by Step 3
            if hype_count >= MAX_HYPE_POSITIONS:
                log(f'  [LIVE-MISS] {token}: max positions — cannot mirror', 'WARN')
                continue
            if not is_live_trading_enabled():
                # FIX (2026-04-14): Live trading is off. Don't leave phantom paper trades —
                # delete them so they don't get closed as phantom HL_CLOSED later.
                try:
                    conn_del = get_db_connection()
                    cur_del = conn_del.cursor()
                    cur_del.execute(
                        "DELETE FROM trades WHERE id=%s AND paper=false AND status='open'",
                        (trade_id,))
                    conn_del.commit()
                    cur_del.close(); conn_del.close()
                    log(f'  [LIVE-MISS] Deleted phantom paper trade #{trade_id} ({token}) — live trading is OFF', 'WARN')
                except Exception as del_err:
                    log(f'  [LIVE-MISS] Failed to delete phantom trade #{trade_id}: {del_err}', 'WARN')
                continue
            curr_price = prices.get(token) if prices else None
            if not curr_price:
                log(f'  [LIVE-MISS] {token}: no price — cannot mirror', 'WARN')
                continue
            lev_int = int(lev) if lev else 10
            ht = hype_coin(token)
            try:
                result = mirror_open(ht, direction, float(curr_price), leverage=lev_int)
                if result and result.get('success'):
                    hype_count += 1
                    log(f'  [LIVE-MISS] Mirrored {token} {direction} @ {curr_price} → {result}', 'PASS')
                else:
                    # FIX (2026-04-14): mirror_open failed — delete the phantom paper trade
                    # so guardian doesn't later close it as HL_CLOSED.
                    msg = result.get('message', str(result)) if result else 'unknown'
                    log(f'  [LIVE-MISS] Mirror failed for {token}: {msg} — deleting phantom', 'WARN')
                    try:
                        conn_del = get_db_connection()
                        cur_del = conn_del.cursor()
                        cur_del.execute(
                            "DELETE FROM trades WHERE id=%s AND paper=false AND status='open'",
                            (trade_id,))
                        conn_del.commit()
                        cur_del.close(); conn_del.close()
                        log(f'  [LIVE-MISS] Deleted phantom paper trade #{trade_id} ({token})', 'WARN')
                    except Exception as del_err:
                        log(f'  [LIVE-MISS] Failed to delete phantom trade #{trade_id}: {del_err}', 'WARN')
            except Exception as me:
                log(f'  [LIVE-MISS] Mirror error for {token}: {me}', 'WARN')

        if added_count > 0 or closed_count > 0:
            log(f'  Paper→HL mirror: {added_count} added, {closed_count} closed')

        return added_count

    except Exception as e:
        try:
            conn.rollback()
            conn.close()
        except:
            pass
        log(f'  close_orphan_paper_trades error: {e}', 'FAIL')
        return 0


def _close_paper_trade_db(trade_id, token, exit_price, reason):
    """Close a paper trade in the DB without touching HL. Idempotent — checks status='open'.
    Calculates pnl_usdt and pnl_pct from entry_price stored in DB.

    BUG-FIX B7: Kill switch — if token is in kill switch, skip the close.
    BUG-FIX B6: Standardized reason vocabulary:
        ORPHAN_PAPER   = paper has no HL position
        MAX_POSITIONS  = at max HL positions
        HOTSET_BLOCKED = token on hot-set blocklist
        CUT_LOSER      = cut loser triggered
        STALE_ROTATION = stale rotation
        CASCADE_FLIP   = cascade flip
        MANUAL_CLOSE   = T manually closed via kill switch
    """
    # BUG-FIX B7: Kill switch check — skip if T manually closed this token
    if _is_token_killed(token):
        log(f'  Kill switch: skipping close for {token} ({reason})', 'INFO')
        return
    if DRY:
        log(f'  [DRY] Would close paper trade #{trade_id} ({reason})', 'WARN')
        return
    if trade_id in _CLOSED_THIS_CYCLE:
        log(f'  Dedup: trade #{trade_id} already closed this cycle, skipping', 'WARN')
        return
    _CLOSED_THIS_CYCLE.add(trade_id)
    _save_closed_set()  # BUG-4: persist so crash/restart doesn't lose dedup

    conn = get_db_connection()
    if conn is None:
        return
    try:
        cur = conn.cursor()
        # Look up entry price, direction, amount, and leverage for PnL calc
        cur.execute(
            "SELECT entry_price, direction, amount_usdt, leverage FROM trades WHERE id=%s AND status='open'",
            (trade_id,))
        row = cur.fetchone()
        if not row:
            log(f'  Dedup: trade #{trade_id} ({token}) already closed, skipping', 'WARN')
            cur.close(); conn.close()
            return

        entry_price, direction, amount_usdt, leverage = row

        # FIX (2026-04-05): Sanity-check entry_price against current market price.
        # If entry_price is <10% or >10x current market, the entry was corrupted (e.g.
        # add_orphan_trade swapped entry_price and amount_usdt, causing ep=~$10 for BTC).
        # This is separate from the PnL>1000% check which validates exit price via HL PnL.
        # When entry is corrupted, use current market price as entry to get a realistic close.
        try:
            curr_mkt = float(exit_price)  # exit_price is already validated as current mkt price
            ep_f = float(entry_price)
            if ep_f > 0 and curr_mkt > 0:
                ratio = ep_f / curr_mkt
                if ratio < 0.1 or ratio > 10:
                    log(f'  ⚠️ {token} entry_price {ep_f:.4f} is {ratio:.4f}x market price '
                        f'{curr_mkt:.4f} — corrupted (swap bug?). Using market price as entry.', 'WARN')
                    entry_price = curr_mkt
        except Exception as ep_err:
            log(f'  Entry price sanity check failed: {ep_err}', 'WARN')

        # BUG-25 fix: sanity-check exit price against entry + market price.
        # If exit price is >20% different from current market, something is wrong.
        # Reject the HL fill and fall back to current market price.
        # NOTE: prices not available in Step8 scope — removed inline check.
        # exit_price already validated by _get_hl_exit_price() caller.
        if not entry_price or not exit_price or exit_price <= 0:
            log(f'  Skipping trade #{trade_id} ({token}): missing entry/exit price', 'WARN')
            cur.close(); conn.close()
            return

        amount_usdt = float(amount_usdt or 50)
        leverage = float(leverage or 1)

        # ── Try HL ground truth first ───────────────────────────────────
        hype_pnl_usdt = None
        try:
            # FIX (2026-04-14): Use _get_fills_cached instead of direct get_trade_history
            # to consolidate API calls and respect rate limits.
            window_end = int(time.time() * 1000)
            window_start = window_end - 300_000
            fills = _get_fills_cached(token, window_start, window_end)
            token_fills = [f for f in fills if f['coin'].upper() == token.upper()]
            close_fills = [f for f in token_fills if f.get('side') == 'B']
            if close_fills:
                hype_pnl_usdt = round(sum(f.get('closed_pnl', 0) or 0 for f in close_fills), 6)
                log(f'  {token} HL realized_pnl: {hype_pnl_usdt:+.4f}')
        except Exception as hl_err:
            log(f'  {token} HL PnL fetch failed (using calc): {hl_err}', 'WARN')

        # Calculate PnL
        if direction and direction.upper() == 'SHORT':
            pnl_pct = round((float(entry_price) - exit_price) / float(entry_price) * 100, 4)
        else:
            pnl_pct = round((exit_price - float(entry_price)) / float(entry_price) * 100, 4)
        pnl_usdt = round(pnl_pct / 100 * amount_usdt, 4)

        # Use HL ground truth if available
        if hype_pnl_usdt is not None and hype_pnl_usdt != 0:
            hype_pnl_pct = round(hype_pnl_usdt / amount_usdt * 100, 4)
            final_pnl_usdt = round(hype_pnl_usdt, 4)
            final_pnl_pct = hype_pnl_pct
        else:
            final_pnl_usdt = pnl_usdt
            final_pnl_pct = pnl_pct

        # FIX (2026-04-04): Sanity-check PnL before committing.
        # If exit price from cache is corrupted (>1000% or <-99%), reject the close
        # and fall back to a zero PnL close at entry price instead of corrupting DB.
        if abs(final_pnl_pct) > 1000:
            log(f'  ⚠️ {token} PnL {final_pnl_pct:+.2f}% suspicious — cache price may be corrupted. '
                f'Setting pnl=0 to prevent DB corruption. entry={entry_price} exit={exit_price}', 'WARN')
            final_pnl_usdt = 0.0
            final_pnl_pct = 0.0
            exit_price = entry_price  # close at entry = no loss/no win

        cur.execute("""
            UPDATE trades SET status = 'closed', exit_price = %s,
                pnl_pct = %s, pnl_usdt = %s,
                close_time = NOW(), close_reason = %s, exit_reason = %s,
                is_guardian_close = TRUE, guardian_reason = %s,
                hype_realized_pnl_usdt = %s, hype_realized_pnl_pct = %s
            WHERE id = %s AND status = 'open'
        """, (exit_price, final_pnl_pct, final_pnl_usdt, reason, reason, reason,
              hype_pnl_usdt, final_pnl_pct if hype_pnl_usdt is not None else None,
              trade_id))
        # Verify the UPDATE actually hit a row — if 0, trade was already closed
        if cur.rowcount == 0:
            log(f'  Dedup: trade #{trade_id} ({token}) already closed, skipping', 'WARN')
            conn.rollback()
        else:
            conn.commit()
            log(f'  Closed paper trade #{trade_id} ({reason}): {token} @ {exit_price} '
                f'pnl={final_pnl_pct:+.4f}% ({final_pnl_usdt:+.2f})', 'PASS')
            # FIX (2026-04-01): Clear reconciled state so token can be re-reconciled on next open.
            _clear_reconciled_token(token)
        cur.close()
        conn.close()
    except Exception as e:
        try:
            conn.rollback()
            conn.close()
        except:
            pass
        log(f'  _close_paper_trade_db error: {e}', 'FAIL')


def _close_orphan_paper_trade_by_id(trade_id, token, direction, entry_px, lev, reason):
    """
    Close a specific orphan paper trade by ID using actual HL fill data.
    Looks up the HL exit price + realized PnL, then updates the trade and
    records signal_outcomes + self-correction (flip+penalty on loss).

    This replaces the old approach of calling record_closed_trade() which
    INSERTS a new row (creating duplicates) instead of updating the existing orphan.
    """
    if DRY:
        log(f'  [DRY] Would _close_orphan_paper_trade_by_id #{trade_id} ({reason})', 'WARN')
        return

    from hyperliquid_exchange import get_trade_history
    import time as _time

    # BUG-16 fix: look back 300s (was 120s) — guardian sleeps 6s after HL close,
    # but HL fills can take up to 5 min to appear in user_fills_by_time.
    close_start_ms = int(_time.time() * 1000) - 300000
    hl_exit_px, realized_pnl = _poll_hl_fills_for_close(token, close_start_ms)

    if hl_exit_px == 0.0:
        log(f'  No HL fill for {token} trade #{trade_id}, will retry next cycle', 'WARN')
        return

    # Look up amount_usdt and leverage from DB (don't use hardcoded 20.0)
    conn_lookup = get_db_connection()
    amount_usdt = 50.0
    lev = 1
    if conn_lookup:
        try:
            cl = conn_lookup.cursor()
            cl.execute("SELECT amount_usdt, leverage FROM trades WHERE id=%s", (trade_id,))
            row = cl.fetchone()
            if row:
                amount_usdt = float(row[0] or 50)
                lev = float(row[1] or 1)
            cl.close()
        except:
            pass
        finally:
            conn_lookup.close()

    # Calculate PnL — prefer HL realized_pnl, fall back to price-based calc
    if realized_pnl is not None and realized_pnl != 0:
        computed_pnl_pct = round(realized_pnl / amount_usdt * 100, 4)
        computed_pnl_usdt = round(realized_pnl, 4)
    else:
        # Fallback: price-based calculation
        if direction.upper() == 'SHORT':
            computed_pnl_pct = round((entry_px - hl_exit_px) / entry_px * 100, 4)
        else:
            computed_pnl_pct = round((hl_exit_px - entry_px) / entry_px * 100, 4)
        computed_pnl_usdt = round(computed_pnl_pct / 100 * amount_usdt, 4)

    is_win = float(computed_pnl_pct or 0) > 0

    # ── Position closed event log ───────────────────────────────────────────────
    try:
        log_event(EVENT_POSITION_CLOSED, {'token': token, 'close_reason': reason})
    except Exception:
        pass

    conn = get_db_connection()
    if conn is None:
        return
    try:
        cur = conn.cursor()
        cur.execute("""
            UPDATE trades SET status='closed', exit_price=%s,
                pnl_pct=%s, pnl_usdt=%s,
                close_time=NOW(), close_reason=%s, exit_reason=%s,
                last_updated=NOW(), updated_at=NOW(),
                is_guardian_close=TRUE, guardian_reason=%s,
                hype_realized_pnl_usdt=%s, hype_realized_pnl_pct=%s
            WHERE id=%s AND status='open'
        """, (hl_exit_px, computed_pnl_pct, computed_pnl_usdt,
              reason, reason, reason,
              realized_pnl if realized_pnl else None,
              computed_pnl_pct if realized_pnl else None,
              trade_id))
        if cur.rowcount == 0:
            log(f'  Dedup: orphan trade #{trade_id} ({token}) already closed, skipping', 'WARN')
            conn.rollback()
        else:
            conn.commit()
            log(f'  Closed orphan trade #{trade_id}: {token} {direction} exit={hl_exit_px:.6f} '
                f'pnl={computed_pnl_pct:+.4f}% {"WIN" if is_win else "LOSS"}', 'PASS')
        cur.close()
        conn.close()

        # ── Signal outcome recording + self-correction ────────────────────────
        _record_trade_outcome(token, direction.upper(), computed_pnl_pct,
                              computed_pnl_usdt, trade_id)

    except Exception as e:
        try:
            conn.rollback()
            conn.close()
        except:
            pass
        log(f'  _close_orphan_paper_trade_by_id error: {e}', 'FAIL')
    # FIX (2026-04-01): Clear reconciled state when position is closed on HL.
    # This allows the token to be re-reconciled if a new position opens.
    # BUG-15 fix: move inside try block so it's actually called (was after return).
    _clear_reconciled_token(token)


def _record_trade_outcome(token, direction, pnl_pct, pnl_usdt, trade_id):
    """
    Record trade outcome to signal_outcomes + self-correct on loss.
    Called whenever any trade closes (guardian or position_manager).
    """
    is_win = float(pnl_pct or 0) > 0

    # ── Record to signal_outcomes (SQLite) ─────────────────────────────────
    try:
        import sqlite3
        conn_s = sqlite3.connect('/root/.hermes/data/signals_hermes_runtime.db')
        cur_s = conn_s.cursor()
        # Dedup: check if we already recorded this exact outcome recently
        # (same token, direction, pnl — protects against the function being
        # called twice for the same trade close in the same sync cycle)
        cur_s.execute("""
            SELECT id FROM signal_outcomes
            WHERE token=? AND direction=? AND ABS(pnl_pct - ?) < 0.0001
            AND created_at > datetime('now', '-5 minutes')
        """, (token.upper(), direction.upper(), pnl_pct))
        if cur_s.fetchone():
            log(f'  Signal outcome dedup: {token} {direction} already recorded recently, skipping', 'WARN')
            conn_s.close()
            return
        # BUG-24 fix: include trade_id column so outcomes can be joined back to brain.trades.
        cur_s.execute("""
            INSERT INTO signal_outcomes (token, direction, signal_type, is_win, pnl_pct, pnl_usdt, confidence, trade_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (token.upper(), direction.upper(), 'decider',
              1 if is_win else 0, pnl_pct, pnl_usdt, None, trade_id))
        conn_s.commit()
        conn_s.close()
        log(f'  Signal outcome: {token} {direction} -> {"WIN" if is_win else "LOSS"} '
            f'(pnl={pnl_pct:+.4f}%)', 'PASS')
    except Exception as sig_err:
        log(f'  Signal outcome record error: {sig_err}', 'WARN')

    # ── Self-correction on loss ───────────────────────────────────────────
    if not is_win:
        opposite = 'LONG' if direction.upper() == 'SHORT' else 'SHORT'
        try:
            from signal_schema import set_cooldown
            set_cooldown(token.upper(), opposite, minutes=60,
                         reason=f'flip_after_loss_{direction.lower()}')
            log(f'  FLIP: {token} {direction} lost -> {opposite} cooldown (60min)', 'INFO')
        except Exception as cd_err:
            log(f'  Flip cooldown error: {cd_err}', 'WARN')

        # Record penalty to trade_patterns via UPSERT (incrementing sample_count each time)
        try:
            import psycopg2 as _pg2
            conn_b = _pg2.connect(**BRAIN_DB_DICT)
            cur_b = conn_b.cursor()
            # Look up original signal confidence to compute penalty
            cur_b.execute("""
                SELECT signal, confidence FROM trades
                WHERE token=%s AND direction=%s AND server='Hermes'
                ORDER BY id DESC LIMIT 1
            """, (token.upper(), direction.upper()))
            row = cur_b.fetchone()
            cur_b.close()
            conf = float(row[1] or 50) if row else 50
            penalty = min(15, conf * 0.3)
            # psycopg2 JSONB accepts Python dict directly — no json.dumps() needed.
            # ON CONFLICT (token, side, regime, pattern_name): increments sample_count.
            # Also upserts adjustment so the latest penalty is always stored.
            cur_b2 = conn_b.cursor()
            cur_b2.execute("""
                INSERT INTO trade_patterns
                    (token, side, regime, pattern_name, confidence, adjustment, sample_count)
                VALUES (UPPER(%s), UPPER(%s), 'unknown', 'wrong_direction_signal',
                        0.5, (%s), 1)
                ON CONFLICT (token, side, regime, pattern_name)
                DO UPDATE SET
                    confidence = GREATEST(trade_patterns.confidence, EXCLUDED.confidence),
                    adjustment = EXCLUDED.adjustment,
                    sample_count = trade_patterns.sample_count + 1,
                    last_seen = NOW()
            """, (token.upper(), direction.upper(),
                  _pg2.extras.Json({'confidence_adj': -penalty, 'sl_mult': 0.9})))
            conn_b.commit()
            cur_b2.close()
            conn_b.close()
            log(f'  PENALTY: {token} {direction} future signals -{penalty:.1f}pts '
                f'(conf {conf:.0f}->{max(0,conf-penalty):.0f})', 'INFO')
        except Exception as pen_err:
            log(f'  Penalty record error: {pen_err}', 'WARN')


# ─── Main Sync Cycle ──────────────────────────────────────────────────────────

def _sweep_blocklist_trades(prices):
    """
    Step 9 (2026-04-05): Sweep all open paper trades and close any on SHORT or LONG blacklist.
    This is the last line of defense against external systems writing blocklisted tokens.
    Only closes paper=true trades — live trades get real HL fill data.
    """
    if DRY:
        log('[DRY] _sweep_blocklist_trades: would check all open paper trades against SHORT/LONG blacklist')
        return 0

    conn = get_db_connection()
    if conn is None:
        return 0

    closed = 0
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT id, token, direction, entry_price, leverage
            FROM trades
            WHERE status = 'open'
              AND paper = TRUE
              AND exchange = 'Hyperliquid'
        """)
        for (trade_id, token, direction, entry_px, lev) in cur.fetchall():
            ht = token.upper()
            blocked_short = direction.upper() == 'SHORT' and ht in SHORT_BLACKLIST
            blocked_long = direction.upper() == 'LONG' and ht in LONG_BLACKLIST
            if not (blocked_short or blocked_long):
                continue

            # Determine direction-appropriate close reason
            reason = 'HOTSET_BLOCKED_SHORT' if blocked_short else 'HOTSET_BLOCKED_LONG'
            exit_price = prices.get(ht) or prices.get(token) or entry_px or 0

            trade_id_str = str(trade_id)
            if trade_id_str in _CLOSED_THIS_CYCLE:
                continue

            _close_paper_trade_db(trade_id, token, exit_price, reason)
            _CLOSED_THIS_CYCLE.add(trade_id_str)
            _save_closed_set()
            closed += 1
            log(f'  [BLOCKLIST SWEEP] {token} {direction} (#{trade_id}) — closed: {reason}', 'WARN')

        cur.close()
        conn.close()
    except Exception as e:
        log(f'_sweep_blocklist_trades error: {e}', 'FAIL')
        try:
            cur.close()
            conn.close()
        except:
            pass

    return closed


# ─── TP/SL Reconciliation ────────────────────────────────────────────────────

# Per-token cooldown: prevents the guardian from hammering HL with TP/SL updates
# Key = token.upper(), Value = Unix timestamp of last TP/SL reconcile
_TPSL_RECONCILE_COOLDOWN = {}   # module-level, persists across sync cycles
_TPSL_COOLDOWN_SEC = 30          # 30-second cooldown per token

# In-memory state for TP/SL reconciles this cycle (per-token, not cross-token)
_TPSL_MOVED_THIS_CYCLE = {}      # token.upper() -> {'tp': bool, 'sl': bool}


def _check_and_close_breached_trades(hl_pos: dict, prices: dict, db_trades: list) -> int:
    """
    Step 11 (2026-04-08): Plan B breach detector — fires when HL TP/SL placement fails.

    For each open HL position with a DB trade:
      - Checks if current price has crossed the DB stop_loss (SL breach) OR target (TP breach)
      - LONG: breached if curr < SL  OR curr > TP
      - SHORT: breached if curr > SL OR curr < TP
      - If breached → fires close_position_hl (market close on HL) + closes DB trade

    Returns count of positions closed due to breach.

    This is the fallback when HL trigger orders are rejected (PENDLE/MET) or as redundant
    safety net even when HL TP/SL exists (guardian catches breaches in ~60s vs HL's instant trigger).
    """
    if DRY:
        log('[DRY] _check_and_close_breached_trades: would check and close breached trades', 'WARN')
        return 0

    # Build token -> db_trade lookup
    db_by_token = {t['token'].upper(): t for t in db_trades if t.get('status') == 'open'}

    breach_closed = 0
    conn = get_db_connection()
    if conn is None:
        return 0

    for coin, pos_data in hl_pos.items():
        tok = coin.upper()
        if tok not in db_by_token:
            continue

        # Skip if already closed this cycle (dedup)
        if tok in _CLOSED_HL_COINS:
            continue

        entry_px = float(pos_data.get('entry_px', 0))
        direction = pos_data.get('direction', 'LONG')
        sz = float(pos_data.get('size', 0))
        if entry_px == 0 or sz == 0:
            continue

        db_trade = db_by_token[tok]
        trade_id = db_trade.get('id')
        sl = db_trade.get('stop_loss') or 0
        tp = db_trade.get('target') or 0
        curr = prices.get(coin, 0)
        if curr == 0:
            continue

        # Determine breach
        breached = False
        breach_reason = None
        if direction == 'LONG':
            if sl > 0 and curr <= sl:
                breached = True
                breach_reason = 'breach_SL'
            elif tp > 0 and curr >= tp:
                breached = True
                breach_reason = 'breach_TP'
        else:  # SHORT
            if sl > 0 and curr >= sl:
                breached = True
                breach_reason = 'breach_SL'
            elif tp > 0 and curr <= tp:
                breached = True
                breach_reason = 'breach_TP'

        if not breached:
            continue

        log(f'  🚨 {coin} BREACH DETECTED ({direction}): {breach_reason} — '
            f'entry={entry_px}, curr={curr:.6f}, SL={sl:.6f}, TP={tp:.6f}', 'WARN')

        # Mark coin as closed BEFORE closing to prevent race conditions
        _CLOSED_HL_COINS.add(tok)

        # Phase-3 fix: add trade_id to dedup set and persist BEFORE calling HL.
        # This prevents duplicate closes if this process crashes after HL call
        # but before the DB update below.
        if trade_id:
            _CLOSED_THIS_CYCLE.add(str(trade_id))
            _save_closed_set()

        # File lock to prevent this exact close from racing with another guardian cycle
        lock_path = f'/tmp/hermes-close-lock-{token}.lock'
        lock_fd = os.open(lock_path, os.O_CREAT | os.O_RDWR, 0o644)
        try:
            fcntl.flock(lock_fd, fcntl.LOCK_EX)  # blocking lock
        finally:
            os.close(lock_fd)

        # Fire market close on HL
        success = close_position_hl(coin, breach_reason)
        if not success:
            _CLOSED_HL_COINS.discard(tok)  # Remove on failure, allow retry next cycle
            log(f'  ❌ {coin} breach close failed — will retry next cycle', 'FAIL')
            continue

        # Wait for HL fills to appear (close_position_hl returns immediately, fills take time)
        time.sleep(6)

        # Close DB paper trade using actual HL fill price
        try:
            from hyperliquid_exchange import get_trade_history
            close_start_ms = int(time.time() * 1000) - 300000
            hl_exit_px, realized_pnl = _poll_hl_fills_for_close(tok, close_start_ms)

            amount_usdt = db_trade.get('amount_usdt', 50.0)
            lev = db_trade.get('leverage', 1)

            if realized_pnl is not None and realized_pnl != 0:
                computed_pnl_pct = round(realized_pnl / amount_usdt * 100, 4)
                computed_pnl_usdt = round(realized_pnl, 4)
            elif hl_exit_px > 0:
                if direction.upper() == 'SHORT':
                    computed_pnl_pct = round((entry_px - hl_exit_px) / entry_px * 100, 4)
                else:
                    computed_pnl_pct = round((hl_exit_px - entry_px) / entry_px * 100, 4)
                computed_pnl_usdt = round(computed_pnl_pct / 100 * amount_usdt, 4)
            else:
                # No fill data — close at current price as estimate
                if direction.upper() == 'SHORT':
                    computed_pnl_pct = round((entry_px - curr) / entry_px * 100, 4)
                else:
                    computed_pnl_pct = round((curr - entry_px) / entry_px * 100, 4)
                computed_pnl_usdt = round(computed_pnl_pct / 100 * amount_usdt, 4)
                hl_exit_px = curr

            if trade_id:
                cur = conn.cursor()
                cur.execute("""
                    UPDATE trades SET
                        status='closed',
                        close_reason=%s,
                        exit_reason=%s,
                        guardian_closed=TRUE,
                        hl_exit_price=%s,
                        pnl_pct=%s,
                        pnl_usdt=%s,
                        realized_pnl=%s
                    WHERE id=%s
                """, (
                    breach_reason,
                    breach_reason,
                    hl_exit_px,
                    computed_pnl_pct,
                    computed_pnl_usdt,
                    computed_pnl_usdt if realized_pnl is not None else 0,
                    trade_id
                ))
                conn.commit()
                cur.close()
                _CLOSED_THIS_CYCLE.add(str(trade_id))
                log(f'  ✅ {coin} DB trade #{trade_id} closed — {breach_reason}, '
                    f'exit={hl_exit_px:.6f}, pnl={computed_pnl_pct:.2f}%', 'PASS')
        except Exception as e:
            log(f'  ❌ {coin} DB trade close error: {e}', 'FAIL')
            _CLOSED_HL_COINS.discard(tok)

        breach_closed += 1
        time.sleep(3)

    conn.close()
    return breach_closed


def _is_tpsl_cooldown_active(token: str) -> bool:
    """Return True if token is in 30s cooldown since last reconcile_tp_sl."""
    tok = token.upper()
    if tok not in _TPSL_RECONCILE_COOLDOWN:
        return False
    elapsed = time.time() - _TPSL_RECONCILE_COOLDOWN[tok]
    return elapsed < _TPSL_COOLDOWN_SEC


def _set_tpsl_cooldown(token: str):
    """Mark token as having just been reconciled (start 30s cooldown)."""
    _TPSL_RECONCILE_COOLDOWN[token.upper()] = time.time()


def _should_move_sl(entry_px: float, direction: str, ideal_sl: float, current_sl: float) -> bool:
    """
    Decide if SL should be moved to ideal_sl from current_sl.
    Only move in the FAVORABLE direction:
      - LONG:  favorable = moving SL HIGHER (closer to entry = less risk, tighter stop)
               BUT actually we want to protect profits → move SL UP (higher = better for LONG)
               Wait: for LONG, SL price < entry. Moving SL UP means price goes up (toward entry).
               Favorable for LONG = SL moves higher (further from entry, gives trade more room)
               No wait: for profit protection, you move SL UP (to lock in more profit)
               Actually: for LONG, favorable = SL moving higher (away from entry = lock in more profit
               before being stopped out)
      - SHORT: favorable = moving SL LOWER (closer to entry for SHORT)

    Actually re-reading: "moves TP/SL only in favorable direction" means:
    - Long: SL should only move UP (higher price, more protection/profit lock-in)
           TP should only move UP (higher price, more profit)
    - Short: SL should only move DOWN (lower price, more protection/profit lock-in)
             TP should only move DOWN (lower price, more profit)

    Wait, let me think again more carefully:
    - For LONG: entry_px is the base. SL is below entry. TP is above entry.
      - SL moving DOWN (lower) = worse (wider, further from entry) — NOT favorable
      - SL moving UP (higher) = better (tighter stop, closer to entry) OR profit lock-in?
      Actually: SL at $90 with entry at $100. SL moving to $95 = better (stops closer to entry).
      So for LONG: favorable SL = moving UP (higher price, closer to entry or lock-in)
      TP at $110 with entry $100. TP moving to $115 = better (more profit).
      So for LONG: favorable TP = moving UP (higher price, more profit)

    - For SHORT: entry_px is the base. SL is above entry. TP is below entry.
      - SL moving UP (higher) = worse (wider, further from entry)
      - SL moving DOWN (lower) = better (closer to entry or lock-in)
      - TP moving DOWN (lower) = better (more profit)
      - TP moving UP (higher) = worse (less profit)

    So:
      LONG:  favorable = SL moves UP (higher), TP moves UP (higher)
      SHORT: favorable = SL moves DOWN (lower), TP moves DOWN (lower)
    """
    if current_sl is None or current_sl == 0:
        return True  # No existing SL, always set

    if direction.upper() == 'LONG':
        # For LONG: favorable = SL moves UP (higher price = better protection)
        return ideal_sl > current_sl
    else:  # SHORT
        # For SHORT: favorable = SL moves DOWN (lower price = better protection)
        return ideal_sl < current_sl


def _should_move_tp(entry_px: float, direction: str, ideal_tp: float, current_tp: float) -> bool:
    """Same logic for TP."""
    if current_tp is None or current_tp == 0:
        return True

    if direction.upper() == 'LONG':
        # For LONG: favorable = TP moves UP (higher price = more profit)
        return ideal_tp > current_tp
    else:  # SHORT
        # For SHORT: favorable = TP moves DOWN (lower price = more profit)
        return ideal_tp < current_tp


def _place_or_replace_tp(coin: str, direction: str, new_tp_price: float, size: float) -> dict:
    """
    Place a new TP order if none exists, or replace the existing TP order.
    Returns {"success": True} on success, {"success": False, "error": ...} on failure.
    """
    from hyperliquid_exchange import (
        place_tp, replace_tp, _find_open_trigger_order, _hl_price_decimals, _hl_tick_round
    )
    from hyperliquid_exchange import get_exchange
    import hyperliquid_exchange as hl_ex
    _exchange = hl_ex.get_exchange()

    tp_oid, tp_cloid, existing_tp_sz, existing_tp_px = _find_open_trigger_order(coin, "tp")

    price_decimals = _hl_price_decimals(coin)
    tp_rounded = _hl_tick_round(new_tp_price, price_decimals)

    if tp_oid is None:
        # No existing TP — place a new one
        return place_tp(coin, direction, tp_rounded, size)
    else:
        # Existing TP found — replace it
        return replace_tp(coin, direction, tp_rounded, size)


def reconcile_tp_sl(hl_pos: dict, prices: dict, db_trades: list):
    """
    Step 10 (2026-04-08): Reconcile ATR-based SL for open HL positions.

    For each open HL position with a corresponding paper DB trade:
      1. Skip if token is in 30s cooldown (per-token)
      2. Compute ideal SL using ATR-based logic (ATR distance from current_price, not entry_price)
         - Uses current_price from prices dict for ATR% calculation (Bug 3 fix)
      3. Skip only if the new SL is within 1 tick size of current (Bug 4 fix — no favorable-move gate)
      4. Send SL update to HL via replace_sl() — TP is left untouched
      5. After any successful SL update, set per-token cooldown (30s)
      6. Always persist ATR SL/TP to DB (source of truth for the web dashboard)

    Returns:
      moved (int): number of SL updates successfully sent to HL
      failed (int): number of SL updates that failed
      failed_coins (list): list of (coin, error_reason) tuples for each failure
    """
    conn = get_db_connection()
    if conn is None:
        log('[DEBUG] reconcile_tp_sl: conn is None, returning 0')
        return 0

    if DRY:
        log('[DRY] reconcile_tp_sl: would reconcile TP/SL for open positions', 'WARN')
        return 0

    moved = 0
    failed = 0
    failed_coins = []  # (coin, error_reason)

    try:
        # Build token -> db_trade lookup for quick access
        db_by_token = {t['token'].upper(): t for t in db_trades if t.get('status') == 'open'}
        log(f'  [DEBUG] Step10: {len(db_by_token)} tokens in db_by_token: {list(db_by_token.keys())}')

        for coin, pos_data in hl_pos.items():
            entry_px = float(pos_data.get('entry_px', 0))
            sz = float(pos_data.get('size', 0))
            direction = pos_data.get('direction', 'LONG')

            if entry_px == 0 or sz == 0:
                continue

            # Skip if in cooldown
            if _is_tpsl_cooldown_active(coin):
                log(f'  ⏳ {coin} TP/SL: in cooldown, skipping')
                continue

            # Skip SKIP_COINS — no longer skipping any coins; all get ATR-based SL via place_tp_sl_batch
            # (previously skipped: AAVE, MORPHO, ASTER, PAXG, AVNT — now all supported)
            pass

            # Check if we have a DB trade for this token
            tok = coin.upper()
            if tok not in db_by_token:
                continue

            db_trade = db_by_token[tok]
            current_sl = db_trade.get('stop_loss') or 0
            current_tp = db_trade.get('target') or 0

            log(f'  [DEBUG] {coin}: checking TP/SL (sz={sz} dir={direction} entry={entry_px})')

            # ── BUG-FIX (Bug 3): Use current_price (from prices dict) for ATR calculation ──
            # This replaces entry_price which was incorrectly used before.
            current_price = prices.get(tok, entry_px)

            # ── Compute ideal TP/SL using same ATR-based logic as _compute_dynamic_sl ──
            # Import the function from decider-run's scope (both use same constants)
            from decider_run import _compute_dynamic_sl

            # Use sl_pct_fallback=0.010 (1.0%) as baseline if ATR unavailable
            sl_pct_fallback = 0.010
            try:
                # BUG-FIX: pass current_price as 4th arg (was entry_px)
                ideal_sl = _compute_dynamic_sl(tok, direction.upper(), entry_px, current_price, sl_pct_fallback)
            except Exception as e:
                # Fallback to fixed % SL
                if direction.upper() == 'LONG':
                    ideal_sl = current_price * (1 - sl_pct_fallback)
                else:
                    ideal_sl = current_price * (1 + sl_pct_fallback)
                log(f'  [WARN] {coin} ATR-based SL failed ({e}), using fixed {sl_pct_fallback*100:.1f}%')

            # ── Trailing SL: enforce one-way movement ──
            # SHORT: SL only moves UP (numerically higher) to lock in profit
            # LONG:  SL only moves DOWN (numerically lower) to lock in profit
            if current_sl > 0:
                if direction.upper() == 'SHORT':
                    ideal_sl = max(ideal_sl, current_sl)
                else:  # LONG
                    ideal_sl = min(ideal_sl, current_sl)

            # ── Compute ideal TP using ATR (same logic as _compute_dynamic_tp) ──
            from decider_run import _compute_dynamic_tp
            tp_pct_fallback = 0.015
            try:
                # BUG-FIX: pass current_price as 4th arg (was entry_px)
                ideal_tp = _compute_dynamic_tp(tok, direction.upper(), entry_px, current_price, tp_pct_fallback)
            except Exception as e:
                # Fallback to fixed % TP
                if direction.upper() == 'LONG':
                    ideal_tp = current_price * (1 + tp_pct_fallback)
                else:
                    ideal_tp = current_price * (1 - tp_pct_fallback)
                log(f'  [WARN] {coin} ATR-based TP failed ({e}), using fixed {tp_pct_fallback*100:.1f}%')

            # ── BUG-FIX (Bug 4): Remove favorable-move gate — only skip if negligible change ──
            # Only skip if the new SL/TP is within 1 tick size of the current one
            tick_decimals = _hl_price_decimals(tok)
            tick_size = 10 ** (-tick_decimals)
            sl_changed = abs(ideal_sl - current_sl) > tick_size if current_sl > 0 else True
            tp_changed = abs(ideal_tp - current_tp) > tick_size if current_tp > 0 else True

            if not sl_changed and not tp_changed:
                log(f'  ✅ {coin} TP/SL: no move needed (ideal_sl={ideal_sl:.6f} current_sl={current_sl:.6f} | ideal_tp={ideal_tp:.6f} current_tp={current_tp:.6f})')
                continue

            # ── Build order size from HL position size ──
            # Size in hyperliquid is in coin units (sz from hl_pos)
            order_size = abs(sz)

            # ── PERSIST ATR SL TO DB FIRST (before replace_sl) ──────────────────────────
            # Step 3 (HL→DB reconcile) runs BEFORE Step 10 in every cycle and would
            # overwrite our ATR value with HL's stale SL. By writing here BEFORE calling
            # replace_sl, we ensure the DB already has the correct ATR value when Step 3
            # would overwrite it. This guarantees the dashboard shows ATR SL even if
            # HL rate-limits or rejects the replace_sl call.
            try:
                _conn = get_db_connection()
                if _conn:
                    _cur = _conn.cursor()
                    _cur.execute("""
                        UPDATE trades SET stop_loss=%s, target=%s WHERE id=%s
                    """, (ideal_sl, ideal_tp, db_trade.get('id')))
                    _conn.commit()
                    _cur.close()
                    _conn.close()
            except Exception as _db_err:
                log(f'  [WARN] {coin} ATR DB persist failed: {_db_err}')

            # ── SL-only: use replace_sl to update SL on HL (TP stays as-is from HL) ──
            try:
                result = replace_sl(tok, direction.upper(), ideal_sl, order_size)
                if isinstance(result, dict) and result.get('success'):
                    log(f'  🔄 {coin} SL updated on HL: SL={ideal_sl:.6f}', 'PASS')
                    moved += 1
                    _set_tpsl_cooldown(tok)
                else:
                    error_msg = result.get('error', 'unknown') if isinstance(result, dict) else str(result)
                    hint = result.get('hint', '') if isinstance(result, dict) else ''
                    log(f'  ❌ {coin} SL replace failed: {error_msg}{f" | {hint}" if hint else ""}', 'FAIL')
                    failed += 1
                    failed_coins.append((coin, error_msg))
            except Exception as e:
                log(f'  ❌ {coin} SL replace exception: {e}', 'FAIL')
                failed += 1
                failed_coins.append((coin, str(e)))

            # ── TP update: send TP to HL if it's missing or stale ─────────────────
            # FIX (2026-04-14): reconcile_tp_sl only sent SL to HL, never TP.
            # This caused positions like XRP (no TP on HL) to have no TP protection.
            # Now check if TP needs to be placed, and place it if missing.
            if ideal_tp > 0:
                tp_result = _place_or_replace_tp(
                    tok, direction.upper(), ideal_tp, order_size)
                if isinstance(tp_result, dict) and tp_result.get('success'):
                    log(f'  🎯 {coin} TP updated on HL: TP={ideal_tp:.6f}', 'PASS')
                elif tp_result and not tp_result.get('success'):
                    tp_err = tp_result.get('error', 'unknown')
                    log(f'  ⚠️ {coin} TP update failed: {tp_err}', 'WARN')
                else:
                    log(f'  ⚠️ {coin} TP update returned unexpected result: {tp_result}', 'WARN')

            # ── DB persistence: ALWAYS write ATR-computed values to DB ────────────────
            # The DB is the source of truth for the web dashboard. Even if HL API
            # fails (e.g. 'Main order cannot be trigger order' or 'Invalid TP/SL price'),
            # we must persist the correct ATR SL/TP so the dashboard shows accurate values.
            # HL can be re-synced later; the DB must always reflect the ATR formula.
            try:
                conn_upd = get_db_connection()
                if conn_upd:
                    cur_upd = conn_upd.cursor()
                    cur_upd.execute("""
                        UPDATE trades SET stop_loss=%s, target=%s WHERE id=%s
                    """, (ideal_sl, ideal_tp, db_trade.get('id')))
                    conn_upd.commit()
                    cur_upd.close()
                    conn_upd.close()
                    log(f'  💾 {coin} DB ATR TP/SL persisted: SL={ideal_sl:.6f} TP={ideal_tp:.6f}')
            except Exception as db_e:
                log(f'  ❌ {coin} DB ATR update failed: {db_e}', 'FAIL')

    except Exception as e:
        log(f'reconcile_tp_sl error: {e}', 'FAIL')
        import traceback; traceback.print_exc()
    finally:
        try:
            conn.close()
        except:
            pass

    # FIX (2026-04-14): After updating ATR SL/TP in DB, update trades.json immediately
    # so the web dashboard shows the correct values without waiting for the next
    # pipeline run (which runs every 60s). Guardian runs every 30s so this ensures
    # the dashboard is never more than 30s stale on ATR values.
    _update_trades_json_atr(db_by_token)

    return moved, failed, failed_coins


def _update_trades_json_atr(db_by_token: dict):
    """
    Update SL/TP values in trades.json for the tokens that were just ATR-updated.
    This is a lightweight targeted update — only touches the open trades array.
    Reads current trades.json, updates matching tokens, writes back atomically.
    """
    import sqlite3
    TRADES_JSON = '/var/www/hermes/data/trades.json'
    PRICE_DB = '/root/.hermes/data/signals_hermes.db'

    try:
        with open(TRADES_JSON) as f:
            data = json.load(f)
    except Exception as e:
        log(f'  [WARN] trades.json update skipped: {e}')
        return

    # Build token -> db_trade lookup for quick access
    if not db_by_token:
        return

    try:
        # Get current prices for all tokens
        conn_p = sqlite3.connect(PRICE_DB, timeout=3)
        cur_p = conn_p.cursor()
        prices = {}
        for tok in db_by_token.keys():
            cur_p.execute(
                'SELECT price FROM price_history WHERE token=? ORDER BY timestamp DESC LIMIT 1',
                (tok,))
            row = cur_p.fetchone()
            prices[tok] = float(row[0]) if row else None
        conn_p.close()
    except Exception as e:
        log(f'  [WARN] trades.json price fetch failed: {e}')
        return

    updated = 0
    for tok, db_trade in db_by_token.items():
        # Find matching open trade in trades.json
        for jt in data.get('open', []):
            if jt.get('token', '').upper() == tok:
                entry_px = float(db_trade.get('entry_price') or 0)
                direction = db_trade.get('direction', '')
                current_px = prices.get(tok, entry_px) or entry_px
                sl = float(db_trade.get('stop_loss') or 0)
                tp = float(db_trade.get('target') or 0)

                # Recalculate PnL from ATR values
                if entry_px > 0 and current_px > 0:
                    if direction.upper() == 'SHORT':
                        pnl_pct = round((entry_px - current_px) / entry_px * 100, 2)
                    else:
                        pnl_pct = round((current_px - entry_px) / entry_px * 100, 2)
                    amt = float(db_trade.get('amount_usdt') or 50)
                    pnl_usdt = round(pnl_pct / 100 * amt, 2)
                else:
                    pnl_pct = 0
                    pnl_usdt = 0

                jt['sl'] = round(sl, 6)
                jt['tp'] = round(tp, 6)
                jt['current'] = round(current_px, 6)
                jt['pnl_pct'] = pnl_pct
                jt['pnl_usdt'] = pnl_usdt
                updated += 1
                break

    try:
        lock_path = TRADES_JSON + '.lock'
        with open(lock_path, 'w') as lf:
            fcntl.flock(lf.fileno(), fcntl.LOCK_EX)
            with open(TRADES_JSON, 'w') as f:
                json.dump(data, f, indent=2)
            fcntl.flock(lf.fileno(), fcntl.LOCK_UN)
        log(f'  [WARN] trades.json ATR update: {updated} trades updated')
    except Exception as e:
        log(f'  [WARN] trades.json write failed: {e}')


def sync():
    """Run one full sync cycle."""
    global _CLOSED_THIS_CYCLE, _CLOSED_HL_COINS
    _CLOSED_THIS_CYCLE.clear()
    _CLOSED_HL_COINS.clear()
    _save_closed_set()  # BUG-4: persist cleared state
    log(f'── Sync cycle ──')

    # Step 1: Get HL positions (retry on rate-limit → empty dict)
    # If HL is rate-limited and returns {}, we risk closing real positions as orphans.
    # Retry with backoff before accepting an empty position set.
    hl_pos = {}
    for attempt in range(4):
        try:
            hl_pos = get_open_hype_positions_curl()
            if hl_pos:
                break  # Got real positions
            if attempt < 3:
                wait = 5 * (2 ** attempt)
                log(f'HL returned empty (rate-limited), retrying in {wait}s... ({attempt+1}/4)', 'WARN')
                time.sleep(wait)
        except Exception as e:
            log(f'HL fetch error: {e}', 'WARN')
            if attempt < 3:
                time.sleep(5 * (2 ** attempt))
    if not hl_pos:
        log('HL still returning empty after 4 retries — skipping this cycle', 'WARN')
        return

    # Step 2: Get current prices from shared cache (written by price_collector)
    prices = {}
    try:
        import hype_cache as hc
        mids = hc.get_allMids()
        prices = {k: float(v) for k, v in mids.items()}
    except Exception as e:
        log(f'Failed to fetch prices: {e}', 'WARN')

    # Step 3: Get paper DB open trades
    try:
        db_trades = get_db_open_trades()
    except Exception as e:
        log(f'Failed to fetch DB trades: {e}', 'FAIL')
        return

    # ── Guardian cycle checkpoint ───────────────────────────────────────────────
    try:
        checkpoint_write('guardian_cycle', {'workflow_state': 'IDLE', 'open_trade_count': len(db_trades)})
    except Exception:
        pass

    hl_tokens=set(hl_pos.keys())
    db_tokens={t['token'] for t in db_trades}

    orphans = sorted(hl_tokens - db_tokens)       # on HL, not in DB
    missing = sorted(db_tokens - hl_tokens)      # in DB, not on HL

    log(f'HL: {len(hl_tokens)} positions | DB: {len(db_tokens)} open trades')
    log(f'Orphans (HL only):  {orphans or "none"}')
    log(f'Missing (DB only): {missing or "none"}')

    # Step 4: Reconcile HL→Paper (update existing, create orphans before closing)
    reconcile_hype_to_paper(hl_pos, prices)

    # Step 5: Sync PnL from HL
    sync_pnl_from_hype(prices)

    # Step 6: Close orphan HL positions (paper trade was already created by reconcile_hype_to_paper)
    # IMPORTANT: close the existing orphan paper trade directly by ID using the actual
    # HL exit price. Do NOT call record_closed_trade() — that INSERTS a new row which
    # duplicates the orphan paper trade that reconcile_hype_to_paper already created.
    # Token set is tracked so Step 7-8 skip these tokens.
    if orphans:
        log(f'Closing {len(orphans)} orphan HL position(s)...', 'WARN')
        for coin in orphans:
            _CLOSED_HL_COINS.add(coin.upper())
            p = hl_pos.get(coin, {})
            entry_px = float(p.get('entry_px', 0))
            direction = p.get('direction', 'LONG')
            lev = float(p.get('leverage', 1)) or 1

            success = close_position_hl(coin, 'guardian_orphan')
            if success:
                time.sleep(6)  # Wait for fills to appear

                # Find the orphan paper trade that reconcile_hype_to_paper created
                # and close it directly with the actual HL exit price.
                # Skip if already closed this cycle (dedup).
                conn_orphan = get_db_connection()
                if conn_orphan:
                    cur_orphan = conn_orphan.cursor()
                    cur_orphan.execute(
                        "SELECT id FROM trades WHERE token=%s AND status='open' "
                        "AND exchange='Hyperliquid' LIMIT 1",
                        (coin.upper(),))
                    orphan_row = cur_orphan.fetchone()
                    if orphan_row:
                        orphan_id = orphan_row[0]
                        if orphan_id in _CLOSED_THIS_CYCLE:
                            log(f'  Dedup: orphan trade #{orphan_id} already closed, skipping', 'WARN')
                        else:
                            _CLOSED_THIS_CYCLE.add(orphan_id)
                            _save_closed_set()  # BUG-4: persist orphan close
                            _close_orphan_paper_trade_by_id(
                                orphan_id, coin, direction, entry_px, lev,
                                'guardian_orphan'
                            )
                    cur_orphan.close()
                    conn_orphan.close()
            time.sleep(3)

    # Step 7: Close orphan paper trades (mirror paper→HL or close)
    if missing:
        log(f'Syncing {len(missing)} paper-only trade(s)...', 'WARN')
        close_orphan_paper_trades(hl_pos, prices)

    # Step 8: Close remaining "missing" DB trades ONLY if they weren't externally closed.
    # Bug fix (2026-04-02): T manually closed STABLE. Without guardian_closed flag,
    # guardian detected it as "missing from HL" and closed ALL other DB trades in cascade.
    # Safeguard: only close if guardian_closed=FALSE and the trade wasn't manually closed.
    #
    # FIX (2026-04-13): 429 rate-limit false positives.
    # When HL returns 429, real positions are invisible for 1 cycle. If guardian closes
    # DB trades as "HL_CLOSED" based on a single invisible cycle, real positions are lost.
    # Fix: track tokens missing from HL across consecutive cycles. Only close a paper=False
    # trade as HL_CLOSED after 2+ consecutive missing cycles. Single 429 = wait for 2nd cycle.
    if missing:
        # Load missing tracking state
        missing_state = _load_missing_tracking()
        now_ts = time.strftime('%Y-%m-%d %H:%M:%S')

        # Update tracking: increment cycle count for missing tokens, clear for present tokens
        for tok_missing in missing:
            tok_upper = tok_missing.upper()
            if tok_upper in missing_state:
                missing_state[tok_upper]['cycles'] += 1
                log(f'  Missing tracking: {tok_upper} now {missing_state[tok_upper]["cycles"]} cycles', 'WARN')
            else:
                missing_state[tok_upper] = {'cycles': 1, 'first_seen': now_ts}
                log(f'  Missing tracking: {tok_upper} first miss at {now_ts}', 'WARN')

        # Clear tracking for tokens that ARE on HL this cycle
        all_db_tokens = {t['token'].upper() for t in db_trades}
        for tok_on_hl in (all_db_tokens & set(hl_tokens)):
            if tok_on_hl in missing_state:
                log(f'  Missing tracking: {tok_on_hl} is back on HL — clearing', 'INFO')
                del missing_state[tok_on_hl]

        # Persist updated tracking state
        _save_missing_tracking(missing_state)

        conn_guard = get_db_connection()
        if conn_guard:
            try:
                cur_guard = conn_guard.cursor()
                # Pre-fetch which trades are guardian_closed
                cur_guard.execute("""
                    SELECT id, token FROM trades
                    WHERE status='open' AND exchange='Hyperliquid'
                    AND guardian_closed=FALSE
                """)
                safe_to_close = {str(r[0]): r[1] for r in cur_guard.fetchall()}
                cur_guard.close()
                conn_guard.close()
            except Exception:
                safe_to_close = {}

            for t in db_trades:
                tok = t['token'].upper()
                trade_id = t['id']

                if tok in _CLOSED_HL_COINS:
                    continue  # Already closed in Step 6
                if tok not in [x.upper() for x in missing]:
                    continue  # Not actually missing

                # BUG-FIX: guardian_closed logic was INVERTED.
                # guardian_closed=FALSE  → externally closed by T/cut-loser → skip (don't re-close)
                # guardian_closed=TRUE   → guardian set flag but close failed (stale) → attempt close
                # safe_to_close = guardian_closed=FALSE trades → skip these
                # NOT in safe_to_close = guardian_closed=TRUE → stale flag, try to close
                # FIX (2026-04-02): paper=f trades are LIVE trades — never skip them.
                # They MUST be closed when missing from HL, regardless of guardian_closed flag.
                # FIX (2026-04-09): Paper trades missing from HL are NOT expected —
                # they mean HL closed the position (via TP/SL or otherwise) and the
                # DB must be updated. Previously this block skipped paper trades,
                # leaving phantom open positions in DB and breaking the pipeline.
                #
                # Logic:
                #  - Paper=True, missing from HL → HL closed it → close DB with TP/SL reason
                #  - Paper=False, guardian_closed=FALSE → externally closed → skip (don't re-close)
                #  - Paper=False, guardian_closed=TRUE  → stale orphan → close as MANUAL_CLOSE
                if t.get('paper') == True:
                    # Paper=True trades are mirror-only. Missing from HL = HL closed it via TP/SL.
                    # Close DB immediately to keep paper trail in sync.
                    try:
                        # Get TP/SL from DB to determine close_reason
                        conn_trade = get_db_connection()
                        if conn_trade:
                            cur_trade = conn_trade.cursor()
                            cur_trade.execute(
                                "SELECT stop_loss, target, direction FROM trades WHERE id=%s",
                                (trade_id,))
                            row_trade = cur_trade.fetchone()
                            cur_trade.close()
                            conn_trade.close()
                            sl = float(row_trade[0]) if row_trade and row_trade[0] else 0
                            tp = float(row_trade[1]) if row_trade and row_trade[1] else 0
                            direction = row_trade[2] if row_trade else ''
                            hl_entry_price = float(row_trade[3]) if row_trade and row_trade[3] else None
                        else:
                            sl = tp = 0
                            direction = t.get('direction', '')
                            hl_entry_price = None

                        fallback_price = prices.get(tok) or prices.get(t['token']) or t.get('entry_price') or 0
                        exit_price = _get_hl_exit_price(tok, fallback_price)

                        # FIX (2026-04-14): Same logic as second Step 8 path.
                        # Only close with HL_* reason if HL confirmed the position existed.
                        has_hl_confirmation = bool(hl_entry_price)

                        if not has_hl_confirmation:
                            close_reason = 'PHANTOM_CLOSE'
                        else:
                            if tp > 0 and sl > 0:
                                if direction.upper() == 'LONG':
                                    if exit_price >= tp:
                                        close_reason = 'HL_TP_CLOSED'
                                    elif exit_price <= sl:
                                        close_reason = 'HL_SL_CLOSED'
                                    else:
                                        close_reason = 'HL_CLOSED'
                                else:  # SHORT
                                    if exit_price <= tp:
                                        close_reason = 'HL_TP_CLOSED'
                                    elif exit_price >= sl:
                                        close_reason = 'HL_SL_CLOSED'
                                    else:
                                        close_reason = 'HL_CLOSED'
                            else:
                                close_reason = 'HL_CLOSED'

                        log(f'  Step8 closing {tok} #{trade_id}: exit={exit_price} reason={close_reason} hl_confirmed={has_hl_confirmation}', 'INFO')

                        # Mark guardian_closed BEFORE closing to prevent double-close
                        conn_upd = get_db_connection()
                        if conn_upd:
                            cur_upd = conn_upd.cursor()
                            cur_upd.execute(
                                "UPDATE trades SET guardian_closed=TRUE WHERE id=%s",
                                (trade_id,))
                            conn_upd.commit()
                            cur_upd.close()
                            conn_upd.close()

                        _close_paper_trade_db(trade_id, tok, exit_price, close_reason)
                    except Exception as e:
                        log(f'  DB close failed for paper {tok}: {e}', 'FAIL')
                    continue

                if str(trade_id) in safe_to_close:
                    # FIX (2026-04-09): Trade missing from HL with guardian_closed=FALSE.
                    # Previously skipped as "externally closed". But this includes HL TP/SL closes
                    # (NIL, AAVE, CFX, LAYER) where the user didn't manually close — HL did.
                    # Determine close_reason from TP/SL in DB, then close with HL_CLOSED reason.
                    #
                    # FIX (2026-04-13): 429 rate-limit false positives.
                    # paper=False trades are LIVE trades. If HL returns 429, we should NOT close
                    # them as HL_CLOSED based on a single invisible cycle. Only close after 2+
                    # consecutive missing cycles (to survive 1-cycle 429 without losing the trade).
                    missing_cycles = missing_state.get(tok, {}).get('cycles', 0)
                    if missing_cycles < 2:
                        log(f'  Step8 SKIP {tok} #{trade_id}: missing only {missing_cycles} cycle(s) — waiting for 2nd miss before closing (possible 429)', 'WARN')
                        continue
                    try:
                        conn_trade = get_db_connection()
                        if conn_trade:
                            cur_trade = conn_trade.cursor()
                            cur_trade.execute(
                                "SELECT stop_loss, target, direction, hl_entry_price FROM trades WHERE id=%s",
                                (trade_id,))
                            row_trade = cur_trade.fetchone()
                            cur_trade.close()
                            conn_trade.close()
                            sl = float(row_trade[0]) if row_trade and row_trade[0] else 0
                            tp = float(row_trade[1]) if row_trade and row_trade[1] else 0
                            direction = row_trade[2] if row_trade else t.get('direction', '')
                            hl_entry_price = float(row_trade[3]) if row_trade and row_trade[3] else None
                        else:
                            sl = tp = 0
                            direction = t.get('direction', '')
                            hl_entry_price = None

                        fallback_price = prices.get(tok) or prices.get(t['token']) or t.get('entry_price') or 0
                        exit_price = _get_hl_exit_price(tok, fallback_price)
                        if not exit_price or exit_price <= 0:
                            raise ValueError(f"No valid exit price for {tok} trade #{trade_id}: fallback={fallback_price}")

                        # FIX (2026-04-14): Only close paper=False trades as HL_CLOSED if HL
                        # actually confirmed the position (hl_entry_price IS NOT NULL).
                        # If hl_entry_price IS NULL, the HL mirror likely failed (rate limit,
                        # balance, blacklist, etc.) and this is a PHANTOM paper trade — close
                        # it as PHANTOM_CLOSE instead of HL_CLOSED.
                        has_hl_confirmation = bool(hl_entry_price)

                        if not has_hl_confirmation:
                            # PHANTOM: HL mirror never succeeded — close without HL fill
                            close_reason = 'PHANTOM_CLOSE'
                            log(f'  Step8 {tok} #{trade_id}: PHANTOM (no HL confirmation, never reached HL) — closing as phantom', 'WARN')
                        else:
                            # HL confirmed — use TP/SL logic to determine close reason
                            if tp > 0 and sl > 0 and direction:
                                if direction.upper() == 'LONG':
                                    if exit_price >= tp:
                                        close_reason = 'HL_TP_CLOSED'
                                    elif exit_price <= sl:
                                        close_reason = 'HL_SL_CLOSED'
                                    else:
                                        close_reason = 'HL_CLOSED'
                                else:  # SHORT
                                    if exit_price <= tp:
                                        close_reason = 'HL_TP_CLOSED'
                                    elif exit_price >= sl:
                                        close_reason = 'HL_SL_CLOSED'
                                    else:
                                        close_reason = 'HL_CLOSED'
                            else:
                                close_reason = 'HL_CLOSED'

                        log(f'  Step8 closing {tok} #{trade_id}: exit={exit_price} reason={close_reason}', 'INFO')

                        # Mark guardian_closed BEFORE closing to prevent double-close
                        conn_upd = get_db_connection()
                        if conn_upd:
                            cur_upd = conn_upd.cursor()
                            cur_upd.execute(
                                "UPDATE trades SET guardian_closed=TRUE WHERE id=%s",
                                (trade_id,))
                            conn_upd.commit()
                            cur_upd.close()
                            conn_upd.close()

                        _close_paper_trade_db(trade_id, tok, exit_price, close_reason)
                    except Exception as e:
                        log(f'  DB close failed for {tok}: {e}', 'FAIL')
                    continue

                # guardian_closed=TRUE but trade is missing from HL — stale orphan, close now
                log(f'  Step8 closing {tok} #{trade_id}: guardian_closed=TRUE but missing from HL — closing stale orphan', 'WARN')

                try:
                    fallback_price = prices.get(tok) or prices.get(t['token']) or t.get('entry_price') or 0
                    exit_price = _get_hl_exit_price(tok, fallback_price)
                    if not exit_price or exit_price <= 0:
                        raise ValueError(f"No valid exit price for stale orphan {tok} trade #{trade_id}: fallback={fallback_price}")

                    # Mark as guardian_closed BEFORE closing to prevent double-close
                    conn_upd = get_db_connection()
                    if conn_upd:
                        cur_upd = conn_upd.cursor()
                        cur_upd.execute(
                            "UPDATE trades SET guardian_closed=TRUE WHERE id=%s",
                            (trade_id,))
                        conn_upd.commit()
                        cur_upd.close()
                        conn_upd.close()

                    _close_paper_trade_db(trade_id, tok, exit_price, 'MANUAL_CLOSE')
                except Exception as e:
                    log(f'  DB close failed for {tok}: {e}', 'FAIL')

            # Step 9: SWEEP SHORT/LONG BLACKLIST — close any paper trades on the directional blacklist.
    # External systems (e.g. OpenClaw) can write directly to brain.trades, bypassing
    # signal_gen.py blacklist checks. This is the last line of defense: any paper trade
            # on SHORT_BLACKLIST or LONG_BLACKLIST gets closed regardless
    # of how it was created. Only closes paper=true trades — live trades use HL fills.
    if True:  # always run, even when live trading is OFF
        sweep_closed = _sweep_blocklist_trades(prices)
        if sweep_closed > 0:
            log(f'Step9 blocklist sweep: closed {sweep_closed} paper trades on SHORT/LONG blacklist')

    # Step 10: Reconcile ATR-based SL — move only in favorable direction, per-token 30s cooldown
    if db_trades:
        log(f'[DEBUG] Step10 called with {len(db_trades)} db_trades, {len(hl_pos)} hl_pos')
        tpsl_moved, tpsl_failed, tpsl_failed_coins = reconcile_tp_sl(hl_pos, prices, db_trades)
        log(f'[DEBUG] Step10 result: moved={tpsl_moved} failed={tpsl_failed}')
        if tpsl_moved > 0:
            log(f'Step10 SL reconcile: updated {tpsl_moved} token(s) on HL')
        if tpsl_failed > 0:
            failed_list = ', '.join([f'{c} ({e})' for c, e in tpsl_failed_coins])
            log(f'Step10 SL reconcile FAILED ({tpsl_failed}): {failed_list}', 'FAIL')

    # Step 11 (2026-04-08): Plan B — Internal breach detector
    # Runs if HL TP/SL placement failed (PENDLE/MET still missing) or as redundant safety net.
    # Checks if current price has crossed SL or TP for any open HL position.
    # If breached → fires market close on HL (Plan A backup) + closes DB trade.
    breach_closed = _check_and_close_breached_trades(hl_pos, prices, db_trades)
    if breach_closed > 0:
        log(f'Step11 breach detector: closed {breach_closed} position(s) — TP/SL backup')

    log(f'── Sync done ──')


def main():
    global DRY

    parser = argparse.ArgumentParser(description='HL sync guardian daemon')
    parser.add_argument('--dry', action='store_true', help='Dry-run mode (no closes/records)')
    parser.add_argument('--interval', type=int, default=60, help='Seconds between checks (default: 60)')
    args = parser.parse_args()

    DRY = args.dry

    mode = 'DRY RUN' if DRY else 'LIVE SYNC'
    log(f'hl-sync-guardian starting — {mode}', 'INFO')
    log(f'PID: {os.getpid()}', 'INFO')

    # Module-level counter — persists across loop iterations
    global _failure_count

    # ── Checkpoint recovery on startup ─────────────────────────────────────────
    try:
        recovered = detect_incomplete_run()
        if recovered:
            log_event(EVENT_CHECKPOINT_RECOVERY, {'recovered': recovered})
            log(f'[CHECKPOINT] Recovered from incomplete run: {recovered}', 'WARN')
    except Exception:
        pass

    while True:
        # ── VmSize context window monitoring ──────────────────────────────
        try:
            import resource
            rss_mb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024
            if rss_mb > 1024:
                log(f'FATAL: VmSize {rss_mb:.0f}MB > 1GB — context window risk. Exiting.', 'FAIL')
                sys.exit(1)
            elif rss_mb > 500:
                log(f'VmSize warning: {rss_mb:.0f}MB (>{500}MB threshold)', 'WARN')
        except Exception as vm_err:
            pass  # Non-critical

        # ── Pending orphan close retry ─────────────────────────────────────────────
        # If any orphan closes failed last cycle (market_close returned None),
        # retry them immediately before the normal sync cycle.
        pending = _load_pending_retry()
        if pending:
            log(f'Retrying {len(pending)} pending orphan close(s): {sorted(pending)}', 'WARN')
            for token in sorted(pending):
                trade_id = _get_reconciled_trade_id(token)
                if not trade_id:
                    log(f'  {token}: no reconciled trade_id — clearing pending retry', 'WARN')
                    _clear_pending_retry([token])
                    continue
                try:
                    import hype_cache as hc
                    mids = hc.get_allMids()
                    prices = {k: float(v) for k, v in mids.items()}
                except Exception:
                    prices = {}
                curr_price = prices.get(token, 0)
                result = close_position_hl(token, 'pending_retry')
                if result:
                    time.sleep(6)
                    _close_orphan_paper_trade_by_id(
                        trade_id, token, 'LONG', curr_price, 1, 'guardian_orphan_retry'
                    )
                    _clear_pending_retry([token])
                    log(f'  {token}: pending retry succeeded', 'PASS')
                else:
                    log(f'  {token}: pending retry still failing — will retry again next cycle', 'WARN')
            # Refresh HL state after retries
            try:
                hl_pos_retry = get_open_hype_positions_curl()
                if hl_pos_retry:
                    log(f'HL state refreshed after retry: {len(hl_pos_retry)} positions', 'INFO')
            except Exception:
                pass

        # ── PHANTOM_CLOSE exit-price backfill ──────────────────────────────────────
        # FIX (2026-04-14): PHANTOM_CLOSE trades have exit_price=0 because HL fills
        # hadn't propagated when the guardian first closed them. Now that we have
        # _get_fills_cached with a 5-min cache, subsequent guardian cycles can find
        # the real HL fill prices without making extra API calls.
        # Only retry trades where: close_reason=PHANTOM_CLOSE AND exit_price=0.
        _retry_phantom_close_fills()

        try:
            sync()
            _failure_count = 0  # Reset on success
        except Exception as e:
            _failure_count += 1
            import traceback; traceback.print_exc()
            log(f'Sync cycle error #{_failure_count}: {e}', 'FAIL')
            if _failure_count >= MAX_CONSECUTIVE_FAILURES:
                log(f'FATAL: {_failure_count} consecutive failures — exiting', 'FAIL')
                sys.exit(1)

        log(f'Sleeping {INTERVAL}s...', 'INFO')
        time.sleep(INTERVAL)


if __name__ == '__main__':
    main()
