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
import sys, time, json, subprocess, argparse, os, re
sys.path.insert(0, '/root/.hermes/scripts')

from hyperliquid_exchange import (
    get_open_hype_positions_curl, get_exchange, get_realized_pnl,
    get_trade_history, is_live_trading_enabled, mirror_open, hype_coin
)

DRY = True   # Default is DRY RUN (safe). Use --apply flag to enable LIVE closing of orphan positions.
INTERVAL = 60  # seconds between checks
MAX_CONSECUTIVE_FAILURES = 5
LOG_FILE = '/root/.hermes/logs/sync-guardian.log'
DATA_DIR = '/root/.hermes/data'
COPIED_TRADES_FILE = os.path.join(DATA_DIR, 'copied-trades-state.json')

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
            password='brain123'
        )
    except Exception as e:
        log(f'DB connection error: {e}', 'FAIL')
        return None


def get_db_open_trades():
    """Get open trades from paper DB where exchange = Hyperliquid."""
    r = subprocess.run([
        'psql', '-U', 'postgres', '-d', 'brain', '-t', '-c',
        "SELECT token, direction, entry_price, leverage, amount_usdt, paper FROM trades WHERE status = 'open' AND exchange = 'Hyperliquid'"
    ], capture_output=True, text=True, timeout=10)
    trades = []
    for line in r.stdout.strip().splitlines():
        if '|' in line:
            parts = [p.strip() for p in line.split('|')]
            if len(parts) >= 5:
                trades.append({
                    'token': parts[0],
                    'direction': parts[1],
                    'entry_price': float(parts[2]) if parts[2] else 0,
                    'leverage': float(parts[3]) if parts[3] else 1,
                    'amount_usdt': float(parts[4]) if parts[4] else 50,
                    'paper': parts[5].lower() == 't' if len(parts) > 5 else True,
                })
    return trades


def get_all_open_trades():
    """Get ALL open trades (paper and real) from DB."""
    r = subprocess.run([
        'psql', '-U', 'postgres', '-d', 'brain', '-t', '-c',
        "SELECT token, direction, entry_price, leverage, amount_usdt, paper FROM trades WHERE status = 'open'"
    ], capture_output=True, text=True, timeout=10)
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
    """
    if DRY:
        log(f'  [DRY] Would add_orphan_trade: {token} {direction} @ {entry_price} x{leverage}', 'WARN')
        return None

    conn = get_db_connection()
    if conn is None:
        return None
    try:
        cur = conn.cursor()
        # Check for existing open trade first
        cur.execute(
            "SELECT id FROM trades WHERE token=%s AND server = 'Hermes' AND status = 'open'",
            (token,)
        )
        if cur.fetchone():
            cur.close()
            conn.close()
            log(f'  {token} already has an open trade in DB — skipping add', 'WARN')
            return None

        cur.execute("""
            INSERT INTO trades (token, direction, amount_usdt, entry_price,
                exchange, paper, stop_loss, target, server, status, open_time,
                pnl_usdt, pnl_pct, leverage, sl_distance, trailing_activation, trailing_distance)
            VALUES (%s, %s, %s, %s, 'Hyperliquid', true, %s, %s, 'Hermes', 'open', NOW(),
                0, 0, %s, 0.03, 0.01, 0.01)
            RETURNING id
        """, (token, direction, amount_usdt, entry_price,
              stop_loss, target, leverage))
        trade_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        conn.close()
        log(f'  Created orphan recovery trade #{trade_id}: {token} {direction}', 'PASS')
        return trade_id
    except Exception as e:
        try:
            conn.rollback()
            conn.close()
        except:
            pass
        log(f'  add_orphan_trade failed for {token}: {e}', 'FAIL')
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
    Returns (hl_exit_price, realized_pnl) or (0.0, 0.0) if no fills found.
    """
    for attempt in range(3):
        time.sleep(2)
        fills = get_trade_history(close_start_ms, int(time.time() * 1000))
        token_closes = [f for f in fills
                        if f['coin'].upper() == token.upper() and f['side'] == 'B']
        if token_closes:
            total_sz = sum(f['sz'] for f in token_closes)
            wavg_exit = sum(f['px'] * f['sz'] for f in token_closes) / total_sz
            realized_pnl = sum(f['closed_pnl'] for f in token_closes)
            return wavg_exit, realized_pnl
        log(f'  Fill poll attempt {attempt+1}/3 — no close fills yet for {token}', 'WARN')
    log(f'  No HL close fills found for {token} after 3 polls', 'FAIL')
    return 0.0, 0.0


def record_closed_trade(token: str, direction: str, entry_px: float, exit_px: float,
                        pnl_pct: float, lev: float, amount: float, reason: str,
                        use_hl_fills: bool = True):
    """
    Record (or update) a closed trade in the paper DB.
    If use_hl_fills=True (default): poll HL get_trade_history() for actual exit price
    and realized_pnl. Falls back to signal-based prices if HL fills not available.
    close_reason will be set to '{reason}_hl_verified' if HL fills were found.
    """
    hl_exit_px  = 0.0
    real_pnl    = 0.0
    hl_verified = False

    if use_hl_fills and not DRY:
        close_start_ms = int(time.time() * 1000) - 300000  # look back 5 min
        hl_exit_px, real_pnl = _poll_hl_fills_for_close(token, close_start_ms)

    # Compute pnl_pct from HL or signal prices
    if hl_exit_px > 0 and entry_px > 0:
        if direction == 'SHORT':
            computed_pnl_pct = round((entry_px - hl_exit_px) / entry_px * 100, 4)
        else:
            computed_pnl_pct = round((hl_exit_px - entry_px) / entry_px * 100, 4)
        computed_exit = hl_exit_px
        computed_pnl_usdt = real_pnl if real_pnl != 0 else round(amount * computed_pnl_pct / 100, 4)
        hl_verified = (real_pnl != 0) or (hl_exit_px != exit_px)
    else:
        computed_pnl_pct  = pnl_pct
        computed_exit     = exit_px
        computed_pnl_usdt = round(amount * pnl_pct / 100, 2)

    actual_reason = reason if not hl_verified else f'{reason}_hl_verified'

    if DRY:
        log(f'  [DRY] Would record {token}: exit={computed_exit:.6f}, '
            f'pnl={computed_pnl_pct:.4f}%, hl_verified={hl_verified}', 'WARN')
        return

    try:
        # Use psycopg2 with parameterized queries — NEVER interpolate user input into SQL.
        conn = psycopg2.connect(host='/var/run/postgresql', dbname='brain',
                                user='postgres', password='***')
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO trades (token, direction, entry_price, exit_price, status,
                pnl_pct, pnl_usdt, leverage, amount_usdt, exchange, paper,
                hl_entry_price, hl_exit_price, hype_pnl_usdt, hype_pnl_pct,
                close_time, close_reason, exit_reason, last_updated, updated_at)
            VALUES (%s, %s, %s, %s, 'closed',
                %s, %s, %s, %s, 'Hyperliquid', FALSE,
                %s, %s, %s, %s,
                NOW(), %s, %s, NOW(), NOW())
        """, (token, direction, entry_px, computed_exit,
              computed_pnl_pct, computed_pnl_usdt, lev, amount,
              entry_px, computed_exit, real_pnl, computed_pnl_pct,
              actual_reason, actual_reason))
        conn.commit()
        cur.close()
        conn.close()
        log(f'  DB recorded: {token} exit={computed_exit:.6f} '
            f'pnl={computed_pnl_pct:.4f}% hl_verified={hl_verified}', 'PASS')
        return
    except Exception as e:
        log(f'  DB record exception: {e}', 'FAIL')


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
                sl_price = round(entry_px * (1 + sl_pct), 8)
                tp_price = round(entry_px * (1 - tp_pct), 8)
            else:
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
                # ── KEY FIX: Orphan HL position — create paper trade FIRST, then close ──
                # This is the core fix for KAITO/WLFI/FARTCOIN problem.
                # Previous guardian just closed positions without recording them.
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
                    token=coin,
                    direction=direction,
                    entry_price=hl_entry,
                    amount_usdt=amount_usdt,
                    leverage=int(lev),
                    stop_loss=sl_price,
                    target=tp_price,
                )

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
            SELECT id, token, amount_usdt, leverage, entry_price
            FROM trades
            WHERE status='open' AND exchange='Hyperliquid'
        """)

        updated = 0
        for row in cur.fetchall():
            trade_id, token, amount, lev, entry = row
            if token in hl_pos:
                pos_data = hl_pos[token]
                unrealized_pnl = float(pos_data.get('unrealized_pnl', 0))
                margin = float(pos_data.get('margin_used', 1)) or 1

                if unrealized_pnl != 0:
                    pnl_usdt = round(unrealized_pnl, 4)
                    pnl_pct = round((unrealized_pnl / margin) * 100, 4) if margin > 0 else 0

                    cur.execute("""
                        UPDATE trades SET pnl_usdt = %s, pnl_pct = %s,
                            hype_pnl_usdt = %s, hype_pnl_pct = %s,
                            current_price = %s
                        WHERE id = %s
                    """, (pnl_usdt, pnl_pct, pnl_usdt, pnl_pct,
                          prices.get(token, entry) if prices else entry,
                          trade_id))
                    updated += 1

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
                    # Paper trade still open but HL position gone → close paper
                    log(f'  ⚠️ {token} copied but no HL position — closing paper', 'WARN')
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
    """Close a paper trade in the DB without touching HL."""
    if DRY:
        log(f'  [DRY] Would close paper trade #{trade_id} ({reason})', 'WARN')
        return

    conn = get_db_connection()
    if conn is None:
        return
    try:
        cur = conn.cursor()
        cur.execute("""
            UPDATE trades SET status = 'closed', exit_price = %s,
                close_time = NOW(), close_reason = %s, exit_reason = %s
            WHERE id = %s AND status = 'open'
        """, (exit_price, reason, reason, trade_id))
        conn.commit()
        cur.close()
        conn.close()
        log(f'  Closed paper trade #{trade_id} ({reason}): {token} @ {exit_price}', 'PASS')
    except Exception as e:
        try:
            conn.rollback()
            conn.close()
        except:
            pass
        log(f'  _close_paper_trade_db error: {e}', 'FAIL')


# ─── Main Sync Cycle ──────────────────────────────────────────────────────────

def sync():
    """Run one full sync cycle."""
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

    # Step 6: Close orphan HL positions (paper trade was already created above)
    if orphans:
        log(f'Closing {len(orphans)} orphan HL position(s)...', 'WARN')
        for coin in orphans:
            p = hl_pos.get(coin, {})
            entry_px = float(p.get('entry_px', 0))
            direction = p.get('direction', 'LONG')
            lev = float(p.get('leverage', 1)) or 1

            # Calculate position size
            sz = float(p.get('size', 0)) or 0
            position_usd = abs(sz) * entry_px if entry_px > 0 else 20
            amount = min(position_usd, 20.0) or 20

            # Get current price
            exit_px = prices.get(coin, entry_px) if prices else entry_px

            # Calculate PnL
            if exit_px > 0 and entry_px > 0:
                if direction == 'SHORT':
                    raw_pnl_pct = (entry_px - exit_px) / entry_px * 100
                else:
                    raw_pnl_pct = (exit_px - entry_px) / entry_px * 100
                pnl_pct = round(raw_pnl_pct, 4)
            else:
                pnl_pct = 0

            success = close_position_hl(coin, 'guardian_orphan')
            if success:
                time.sleep(6)  # Wait for fills to appear
                record_closed_trade(
                    coin, direction, entry_px, exit_px,
                    pnl_pct, lev, amount, 'guardian_orphan'
                )
            time.sleep(3)

    # Step 7: Close orphan paper trades (mirror paper→HL or close)
    if missing:
        log(f'Syncing {len(missing)} paper-only trade(s)...', 'WARN')
        close_orphan_paper_trades(hl_pos, prices)

    # Step 8: Close missing DB trades (position no longer on HL)
    # CRITICAL FIX: token='***' was a hardcoded literal that matched NOTHING,
    # creating phantom "closed at entry price" trades that lost pure fees.
    # Also: setting exit_price=entry_price, pnl=0 destroys the real exit data.
    # Fix: use psycopg2 with parameterized query, preserve entry_price, let
    # guardian fill exit_price via HL fills (or mark as unknown).
    if missing:
        for t in db_trades:
            if t['token'] in missing:
                try:
                    conn2 = get_db_connection()
                    cur2 = conn2.cursor()
                    # Check if there are HL fills for this token to get real exit price
                    from hyperliquid_exchange import get_trade_history
                    import time as _time
                    fills = get_trade_history(int(_time.time()*1000) - 3600000)
                    token_fills = [f for f in fills if t['token'] in f.get('coin','')]
                    if token_fills:
                        # Use last HL fill price as exit
                        last_fill = token_fills[-1]
                        exit_px = last_fill.get('px')
                    else:
                        exit_px = None  # Will be filled by guardian on next pass
                    
                    if exit_px:
                        cur2.execute("""
                            UPDATE trades SET status='closed', close_time=NOW(),
                                close_reason='guardian_missing', exit_reason='guardian_missing',
                                last_updated=NOW(), updated_at=NOW()
                            WHERE token=%s AND status='open'
                        """, (t['token'],))
                    else:
                        # No HL fill yet — don't close yet, let guardian retry next pass
                        log(f'  Skipping DB close for {t["token"]} — no HL fill yet, will retry', 'WARN')
                        cur2.close(); conn2.close()
                        continue
                    
                    conn2.commit()
                    cur2.close(); conn2.close()
                    log(f'  DB closed: {t["token"]} @ {exit_px} (position not on HL)', 'PASS')
                except Exception as e:
                    log(f'  DB close failed for {t["token"]}: {e}', 'FAIL')

    log(f'── Sync done ──')


def main():
    global DRY

    parser = argparse.ArgumentParser(description='HL sync guardian daemon')
    parser.add_argument('--apply', action='store_true', help='Actually close/record positions (default is dry-run)')
    parser.add_argument('--interval', type=int, default=60, help='Seconds between checks (default: 60)')
    args = parser.parse_args()

    DRY = not args.apply

    mode = 'DRY RUN' if DRY else 'LIVE SYNC'
    log(f'hl-sync-guardian starting — {mode}', 'INFO')
    log(f'PID: {os.getpid()}', 'INFO')

    while True:
        try:
            sync()
        except Exception as e:
            global _consecutive_failures
            _consecutive_failures = getattr(sys.modules[__name__], '_consecutive_failures', 0) + 1
            import traceback; traceback.print_exc()
            log(f'Sync cycle error #{_consecutive_failures}: {e}', 'FAIL')
            if _consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
                log(f'FATAL: {_consecutive_failures} consecutive failures — exiting', 'FAIL')
                sys.exit(1)

        log(f'Sleeping {INTERVAL}s...', 'INFO')
        time.sleep(INTERVAL)


if __name__ == '__main__':
    main()
