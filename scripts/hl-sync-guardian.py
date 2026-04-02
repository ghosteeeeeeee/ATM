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

# Non-HL tokens that appear in HL data but are not tradeable (phantom positions)
HL_TOKEN_BLOCKLIST = frozenset({'PANDORA', 'JELLY', 'FRIEND', 'FTM', 'CANTO', 'MANTA',
    'LOOM', 'BONK', 'WIF', 'PYTH', 'JTO', 'RAY', 'SRM', 'MNGO', 'APTOS',
    'SAGE', 'SAMO', 'DUST', 'HNT', 'STABLE', 'STBL'})

def _is_token_tradeable(token: str) -> bool:
    """Check if token is on HL blocklist (non-tradeable phantom tokens)."""
    if token.upper() in HL_TOKEN_BLOCKLIST:
        return False
    # Also verify via HL API
    try:
        mids = exchange.info.all_mids()
        if token not in mids:
            return False
    except:
        pass
    return True


# ── Process lock: prevent multiple guardian instances ───────────────────────
_LOCK_FILE = '/tmp/hermes-guardian.lock'
_lock_fd = os.open(_LOCK_FILE, os.O_CREAT | os.O_RDWR, 0o644)
try:
    fcntl.flock(_lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
except (IOError, OSError):
    print("[FATAL] Guardian already running — exiting")
    os.close(_lock_fd)
    sys.exit(1)
sys.path.insert(0, '/root/.hermes/scripts')

from ab_utils import get_cached_ab_variant
from hyperliquid_exchange import (
    get_open_hype_positions_curl, get_exchange, get_realized_pnl,
    get_trade_history, is_live_trading_enabled, mirror_open, hype_coin
)

import json  # for json.dumps in penalty recording

DRY = False  # Default is LIVE. Use --dry flag (not --apply) for dry-run mode.
# NOTE: systemd service runs WITHOUT --apply by default — set DRY=False here to enable guardian closes.
# Override with --apply flag if you need temporary dry-run without changing this file.
INTERVAL = 60  # seconds between checks
MAX_CONSECUTIVE_FAILURES = 5
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
    """Persist reconciled state to disk."""
    try:
        with open(_RECONCILED_STATE_FILE, 'w') as f:
            json.dump(state, f)
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

# Deduplication: track trade IDs closed this cycle to prevent duplicate closes.
# Both record_closed_trade() (Step 6) and _close_paper_trade_db() (Steps 7-8)
# may fire for the same trade. Once a trade_id is closed this cycle, skip re-closes.
_CLOSED_THIS_CYCLE = set()
_CLOSED_HL_TOKENS = set()  # tokens where HL position was closed this cycle

# Ensure data dir exists
os.makedirs(DATA_DIR, exist_ok=True)


def log(msg, level='INFO'):
    ts = time.strftime('%Y-%m-%d %H:%M:%S')
    line = f'[{ts}] [{level}] {msg}'
    print(line)
    try:
        with open(LOG_FILE, 'a') as f:
            f.write(line + '\n')
    except:
        pass


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
    with open(COPIED_TRADES_FILE, 'w') as f:
        json.dump(state, f)


# ─── DB Helpers ────────────────────────────────────────────────────────────────

def get_db_connection():
    """Get a psycopg2 connection to the brain DB."""
    import psycopg2
    try:
        return psycopg2.connect(
            host='/var/run/postgresql',
            dbname='brain',
            user='postgres',
            password='Brain123'
        )
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
        result = exchange.market_close(coin=coin, slippage=0.01)
        statuses = result.get('response', {}).get('data', {}).get('statuses', [])
        for s in statuses:
            if 'error' in s:
                log(f'  ❌ {coin}: {s["error"]}', 'FAIL')
                return False
        log(f'  ✅ {coin} closed ({reason})', 'PASS')
        return True
    except Exception as e:
        log(f'  ❌ {coin}: EXCEPTION {e}', 'FAIL')
        return False


def _poll_hl_fills_for_close(token: str, close_start_ms: int):
    """
    Poll get_trade_history() up to 3 times with 2s delay to get actual HL fill data
    for a recently-closed position.
    Returns (hl_exit_price, realized_pnl) or (0.0, None) if no fills found.
    Returns (wavg_exit, float) for breakeven or losing/winning trades.
    """
    for attempt in range(3):
        time.sleep(2)
        fills = get_trade_history(close_start_ms, int(time.time() * 1000))
        token_closes=[f for f in fills
                        if f['coin'].upper() == token.upper() and f['side'] == 'B']
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
    Polls trade history up to 3 times with 2s delay.
    Returns the weighted-average close-fill price, or fallback if no fills found.
    Only considers side='B' (close) fills — not entry fills (side='A').
    """
    for attempt in range(3):
        time.sleep(2)
        try:
            fills = get_trade_history(int(time.time() * 1000) - 120_000, int(time.time() * 1000))
            # Only use close fills (side='B'), not entry fills (side='A')
            token_closes = [f for f in fills
                           if f['coin'].upper() == token.upper() and f.get('side') == 'B']
            if token_closes:
                total_sz = sum(f['sz'] for f in token_closes)
                wavg = sum(f['px'] * f['sz'] for f in token_closes) / total_sz
                log(f'  HL exit price for {token}: {wavg:.4f} (from {len(token_closes)} close fills)')
                return wavg
        except Exception as e:
            log(f'  HL fill poll attempt {attempt+1} failed for {token}: {e}', 'WARN')
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
                trade_id = add_orphan_trade(
                    coin, direction, amount_usdt, hl_entry, lev, sl_price, tp_price
                )
                if trade_id:
                    _mark_hl_reconciled(coin, trade_id, hl_entry, direction)

                # KEY FIX: Actually close the orphan HL position after creating the paper trade.
                # Previously, add_orphan_trade() was called but the HL position was never closed.
                # This left real money at risk on Hyperliquid.
                if trade_id and not DRY:
                    close_result = close_position_hl(coin, f"orphan_recovery_trade_{trade_id}")
                    if close_result:
                        log(f'  Orphan {coin} HL position closed via market order', 'PASS')
                        _CLOSED_HL_TOKENS.add(coin.upper())  # Prevent Step 6 double-close
                    else:
                        log(f'  ⚠️ Orphan {coin} created in DB (trade #{trade_id}) but HL close failed', 'WARN')

                # If we created the paper trade, mark it as copied so we don't try to mirror it again
                if trade_id and not DRY:
                    copied_state = get_copied_trades()
                    copied_state['copied'].append(str(trade_id))
                    save_copied_trades(copied_state)
                    log(f'  Orphan {coin} marked as copied (trade #{trade_id})', 'WARN')
                elif DRY:
                    log(f'  [DRY] Would mark orphan {coin} as copied', 'WARN')

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
    if not flip_cfg:
        return

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

            # Verify token is tradeable on HL before opening
            try:
                mids_check = exchange.info.all_mids()
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
                    lev, amount, 'unknown', 'unknown', 'unknown',
                    -2.0, -4.0, trail_act_val, trail_dist_val,
                    variant_id, trade_id
                ))

                # Mark guardian_closed so Step 8 won't re-process this trade
                cur.execute("""
                    UPDATE trades SET status='closed', close_reason='flipped',
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
                    pnl_usdt = round(unrealized_pnl, 4)
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
                            hype_pnl_usdt = %s, hype_pnl_pct = %s,
                            current_price = %s
                        WHERE id = %s
                    """, (pnl_usdt, pnl_pct, pnl_usdt, pnl_pct,
                          prices.get(token, entry) if prices else entry,
                          trade_id))

                    # Check flip trade triggers (A/B tested: soft SL arm / hard SL flip)
                    _check_and_execute_flip(
                        {'id': trade_id, 'token': token, 'direction': direction,
                         'leverage': lev, 'amount_usdt': amount},
                        pnl_pct, prices)

                    updated += 1
                    # Cut-loser: emergency exit at -10% loss
                    # This runs AFTER flip check, so flip has priority over hard cut
                    # ── Cut-loser: BUG-2/3/28 fix ────────────────────────────────────────
                    # IMPORTANT: close_position() sends order but does NOT wait for fill.
                    # BUG-2 old: marked DB closed BEFORE HL confirmed fill. Fix: wait first.
                    # BUG-3: flip order placed without verifying close succeeded. Fix: verify.
                    # BUG-28: no retry on failure. Fix: retry once, then alert.
                    CUT_LOSER_THRESHOLD = -5.0
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
                                        "close_reason='cut_loser', exit_reason='cut_loser_pnl' "
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
            intel.get('regime_4h'),
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

        # Get ALL paper trades (not just top) to check for closes
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
                    # Retry up to 3 times with 5s delay.
                    registered = False
                    for retry in range(3):
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
                        _close_paper_trade_db(trade_id, token, prices.get(token, entry), 'hl_position_missing')
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
                _close_paper_trade_db(trade_id, token, curr_price, 'max_positions')
                closed_count += 1
                continue

            # Mirror paper trade to HL
            if not DRY and is_live_trading_enabled():
                try:
                    ht = hype_coin(token)
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
    Calculates pnl_usdt and pnl_pct from entry_price stored in DB."""
    if DRY:
        log(f'  [DRY] Would close paper trade #{trade_id} ({reason})', 'WARN')
        return
    if trade_id in _CLOSED_THIS_CYCLE:
        log(f'  Dedup: trade #{trade_id} already closed this cycle, skipping', 'WARN')
        return
    _CLOSED_THIS_CYCLE.add(trade_id)

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
        if not entry_price or not exit_price or exit_price <= 0:
            log(f'  Skipping trade #{trade_id} ({token}): missing entry/exit price', 'WARN')
            cur.close(); conn.close()
            return

        amount_usdt = float(amount_usdt or 50)
        leverage = float(leverage or 1)

        # ── Try HL ground truth first ───────────────────────────────────
        hype_pnl_usdt = None
        try:
            from hyperliquid_exchange import get_trade_history
            close_start_ms = int(time.time() * 1000) - 120_000
            fills = get_trade_history(close_start_ms, int(time.time() * 1000))
            token_fills = [f for f in fills if f['coin'].upper() == token.upper()]
            close_fills = [f for f in token_fills if f['side'] == 'B']
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

    # Poll HL for the close fill
    close_start_ms = int(_time.time() * 1000) - 120000
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
        cur_s.execute("""
            INSERT INTO signal_outcomes (token, direction, signal_type, is_win, pnl_pct, pnl_usdt, confidence)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (token.upper(), direction.upper(), 'decider',
              1 if is_win else 0, pnl_pct, pnl_usdt, None))
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
            conn_b = _pg2.connect(host='/var/run/postgresql', dbname='brain',
                                  user='postgres',            password='Brain123')
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

def sync():
    """Run one full sync cycle."""
    global _CLOSED_THIS_CYCLE, _CLOSED_HL_TOKENS
    _CLOSED_THIS_CYCLE.clear()
    _CLOSED_HL_TOKENS.clear()
    log(f'── Sync cycle ──')

    # Step 1: Get HL positions
    try:
        hl_pos = get_open_hype_positions_curl()
    except Exception as e:
        log(f'Failed to fetch HL positions: {e}', 'FAIL')
        return

    # Step 2: Get current prices
    prices = {}
    try:
        exchange = get_exchange()
        mids = exchange.info.all_mids()
        prices = {k: float(v) for k, v in mids.items()}
    except Exception as e:
        log(f'Failed to fetch prices: {e}', 'WARN')

    # Step 3: Get paper DB open trades
    try:
        db_trades = get_db_open_trades()
    except Exception as e:
        log(f'Failed to fetch DB trades: {e}', 'FAIL')
        return

    hl_tokens = set(hl_pos.keys())
    db_tokens = {t['token'] for t in db_trades}

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
            _CLOSED_HL_TOKENS.add(coin.upper())
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
    if missing:
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

                if tok in _CLOSED_HL_TOKENS:
                    continue  # Already closed in Step 6
                if tok not in [x.upper() for x in missing]:
                    continue  # Not actually missing

                # BUG-1 fix: Clarify the guardian_closed logic.
                # guardian_closed=FALSE  -> externally closed (T or cut-loser). safe_to_close = TRUE. Skip.
                # guardian_closed=TRUE   -> guardian itself closed this trade. safe_to_close = FALSE. Re-close OK.
                # safe_to_close contains IDs with guardian_closed=FALSE (externally closed = skip).
                if str(trade_id) not in safe_to_close:
                    log(f'  Step8 SKIP {tok} #{trade_id}: externally closed (guardian_closed=TRUE — already closed)', 'WARN')
                    continue

                try:
                    fallback_price = prices.get(tok) or prices.get(t['token']) or t.get('entry_price') or 0
                    exit_price = _get_hl_exit_price(tok, fallback_price)

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

                    _close_paper_trade_db(trade_id, tok, exit_price, 'guardian_missing')
                except Exception as e:
                    log(f'  DB close failed for {tok}: {e}', 'FAIL')

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
    _failure_count = 0

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
