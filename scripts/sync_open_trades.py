#!/usr/bin/env python3
"""
Sync Open Trades — Reconcile paper open positions against live Hyperliquid positions.

Replaces the referenced sync_open_trades.py that was never created.

Logic:
  1. Load open paper trades from brain DB
  2. Load open HL positions via get_open_hype_positions_curl()
  3. Find tokens in paper but NOT on HL  → close as orphaned paper entry
  4. Find tokens on HL but NOT in paper → orphan HL position:
     a. If a CLOSED paper trade exists for that token: skip (already reconciled)
     b. If an open paper trade exists: REUSE that trade ID — update entry/direction/leverage, then close both
     c. Otherwise: create a new paper trade, close it (both with same new ID)

Safety:
  - Default is DRY — must pass --apply to execute closes
  - Every action is logged before it runs
  - Idempotent: already-closed trades are skipped
  - In-memory dedup set prevents double-closing same trade in one run

Usage:
  python3 sync_open_trades.py          # dry-run
  python3 sync_open_trades.py --apply  # live — close orphaned paper entries
"""

import sys, os, time, argparse

# ── Paths & DB ────────────────────────────────────────────────────────────────
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _secrets import BRAIN_DB_DICT
import psycopg2

# ── HL API ────────────────────────────────────────────────────────────────────
from hyperliquid_exchange import get_open_hype_positions_curl, get_exchange

# ── Cooldown helpers (duplicated from guardian to avoid cross-service imports) ──
from hermes_constants import LOSS_COOLDOWN_FILE, LOSS_COOLDOWN_BASE, LOSS_COOLDOWN_MAX
from hermes_file_lock import FileLock
import json as _json

from hermes_log import log
def _load_cooldowns() -> dict:
    try:
        with open(LOSS_COOLDOWN_FILE) as f:
            return _json.load(f)
    except Exception:
        return {}

def _save_cooldowns(data: dict) -> None:
    try:
        with FileLock('loss_cooldowns'):
            with open(LOSS_COOLDOWN_FILE, 'w') as f:
                _json.dump(data, f, indent=2)
    except Exception as e:
        print(f"[_save_cooldowns] FAILED: {e}")

def _is_loss_cooldown_active(token: str, direction: str) -> bool:
    key = f"{token.upper()}:{direction.upper()}"
    data = _load_cooldowns()
    entry = data.get(key)
    if not entry:
        return False
    expiry = entry.get('expires', 0) if isinstance(entry, dict) else entry
    return expiry > time.time()

def _record_loss_cooldown(token: str, direction: str) -> None:
    """Record a loss cooldown for token+direction. Guards against duplicates."""
    import time as _time
    if _is_loss_cooldown_active(token, direction):
        return
    key = f"{token.upper()}:{direction.upper()}"
    data = _load_cooldowns()
    existing = data.get(key, {})
    if existing.get('reason') == 'loss':
        return  # pipeline already wrote it
    entry = data.get(key)
    if entry is None:
        streak = 1
    elif isinstance(entry, dict):
        streak = entry.get('streak', 0) + 1
    else:
        streak = 1
    hours = min(LOSS_COOLDOWN_BASE * (2 ** (streak - 1)), LOSS_COOLDOWN_MAX)
    expiry = _time.time() + (hours * 3600)
    data[key] = {'expires': expiry, 'streak': streak, 'hours': hours, 'reason': 'sync'}
    _save_cooldowns(data)
    print(f"  [SYNC] LOSS COOLDOWN: {token} {direction} streak={streak} blocked for {hours:.1f}h")

# ── Constants ─────────────────────────────────────────────────────────────────
CLOSE_SLIPPAGE = 0.005   # 0.5% slippage for market closes
DRY = True               # Default to safe mode
_CLOSED_THIS_RUN = set() # In-memory dedup for this run


# ── Logging ──────────────────────────────────────────────────────────────────
def get_db_connection():
    try:
        return psycopg2.connect(**BRAIN_DB_DICT)
    except Exception as e:
        log(f'DB connection failed: {e}', 'FAIL')
        return None


def get_open_paper_trades():
    """Return dict: token_upper -> {id, direction, entry_price, leverage, amount_usdt, ...}"""
    conn = get_db_connection()
    if conn is None:
        return {}
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT id, token, direction, entry_price, leverage, amount_usdt,
                   stop_loss, target, hl_entry_price
            FROM trades
            WHERE server IN ('Hermes', 'Hermes-Dallas') AND status = 'open'
        """)
        rows = cur.fetchall()
        cur.close(); conn.close()
        return {r[1].upper(): dict(zip(
            ['id','token','direction','entry_price','leverage','amount_usdt',
             'stop_loss','target','hl_entry_price'], r)) for r in rows}
    except Exception as e:
        log(f'Failed to load open paper trades: {e}', 'FAIL')
        return {}


def get_open_hl_positions():
    """Return dict: coin_upper -> {coin, size, entry_px, unrealized_pnl, ...}"""
    try:
        raw = get_open_hype_positions_curl()
    except Exception as e:
        log(f'Failed to fetch HL positions: {e}', 'FAIL')
        return {}
    if not raw:
        return {}
    # raw is a dict: {'BTC': {'size': ..., 'direction': ..., ...}, ...}
    out = {}
    for coin, pos in raw.items():
        if coin and isinstance(pos, dict):
            pos['coin'] = coin   # inject coin name into the dict
            out[coin.upper()] = pos
    return out


def find_existing_open_trade(token: str):
    """Return existing open trade ID for token, or None."""
    conn = get_db_connection()
    if conn is None:
        return None
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT id FROM trades WHERE token=%s AND server IN ('Hermes','Hermes-Dallas') AND status='open' LIMIT 1",
            (token,))
        row = cur.fetchone()
        cur.close(); conn.close()
        return row[0] if row else None
    except:
        return None


def find_recent_closed_trade(token: str, within_minutes=30):
    """Return most recent closed trade for token within N minutes (orphan already reconciled)."""
    conn = get_db_connection()
    if conn is None:
        return None
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT id, close_reason, close_time FROM trades
            WHERE token=%s AND server IN ('Hermes','Hermes-Dallas') AND status='closed'
              AND close_time > NOW() - INTERVAL '%s minutes'
            ORDER BY close_time DESC LIMIT 1
        """, (token, within_minutes))
        row = cur.fetchone()
        cur.close(); conn.close()
        return row if row else None
    except:
        return None


def close_paper_trade_db(trade_id: int, token: str, exit_price: float, reason: str):
    """
    Close a paper trade in DB without touching HL.
    Calculates PnL from stored entry_price.
    Idempotent — skips if already closed.
    DUPLICATE PROTECTION: checks _CLOSED_THIS_RUN and DB status='open' before closing.
    """
    if trade_id in _CLOSED_THIS_RUN:
        log(f'  Dedup: trade #{trade_id} already closed this run, skipping', 'WARN')
        return True
    if DRY:
        log(f'  [DRY] Would close paper trade #{trade_id} ({token})', 'WARN')
        return True

    conn = get_db_connection()
    if conn is None:
        return False
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT entry_price, direction, amount_usdt, leverage FROM trades WHERE id=%s AND status='open'",
            (trade_id,))
        row = cur.fetchone()
        if not row:
            log(f'  Dedup: trade #{trade_id} ({token}) already closed, skipping', 'WARN')
            cur.close(); conn.close()
            return True

        entry_price, direction, amount_usdt, leverage = row
        ep_f = float(entry_price)
        ex_f = float(exit_price)
        amt  = float(amount_usdt)

        if ep_f > 0 and ex_f > 0:
            pnl_pct  = round((ep_f - ex_f) / ep_f * 100, 4) if direction == 'SHORT' \
                      else round((ex_f - ep_f) / ep_f * 100, 4)
            pnl_usdt = round(pnl_pct / 100 * amt, 4)
        else:
            pnl_pct = 0.0; pnl_usdt = 0.0

        cur.execute("""
            UPDATE trades SET
                status='closed', exit_price=%s, pnl_pct=%s, pnl_usdt=%s,
                close_reason=%s, close_time=NOW()
            WHERE id=%s AND status='open'
        """, (ex_f, pnl_pct, pnl_usdt, reason, trade_id))
        conn.commit()
        # ── Loss cooldown: record if this was a losing trade ──────────────────
        # FIX (2026-04-28): This function was closing trades without recording
        # loss cooldowns, allowing immediate re-entry after orphan/paper closes.
        if pnl_usdt < 0:
            _record_loss_cooldown(token, direction)
        cur.close(); conn.close()
        _CLOSED_THIS_RUN.add(trade_id)
        log(f'  Closed paper trade #{trade_id} ({token}) — {direction} ep={ep_f} ex={ex_f} pnl={pnl_usdt} ({reason})', 'PASS')
        return True
    except Exception as e:
        log(f'  Failed to close paper trade #{trade_id}: {e}', 'FAIL')
        try:
            conn.rollback()
            conn.close()
        except:
            pass
        return False


def close_hl_position(coin: str, reason: str) -> bool:
    """Close a real position on Hyperliquid. Returns True on success."""
    if DRY:
        log(f'  [DRY] Would close HL {coin} ({reason})', 'WARN')
        return True
    try:
        exchange = get_exchange()
        result = exchange.market_close(coin=coin, slippage=CLOSE_SLIPPAGE)
        if result is None:
            log(f'  HL close {coin}: returned None (rate-limited?)', 'FAIL')
            return False
        if isinstance(result, dict):
            resp = result.get('response')
            if isinstance(resp, dict):
                statuses = resp.get('data', {}).get('statuses', [])
                for s in statuses:
                    if isinstance(s, dict) and 'error' in s:
                        log(f'  HL close {coin}: {s["error"]}', 'FAIL')
                        return False
        log(f'  Closed HL position {coin} ({reason})', 'PASS')
        return True
    except Exception as e:
        log(f'  HL close {coin} exception: {e}', 'FAIL')
        return False


def add_orphan_recovery_trade(token: str, direction: str, entry_price: float,
                               amount_usdt: float, leverage: int) -> int:
    """
    Create a paper trade for orphan HL recovery.
    ATOMIC: INSERT only if no open trade exists for this token.
    Returns new trade_id or None if creation skipped/failed.
    """
    if DRY:
        log(f'  [DRY] Would create orphan recovery trade: {token} {direction} @ {entry_price} x{leverage}', 'WARN')
        return None

    conn = get_db_connection()
    if conn is None:
        return None
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO trades (token, direction, amount_usdt, entry_price, hl_entry_price,
                exchange, paper, server, status, open_time,
                pnl_usdt, pnl_pct, leverage, sl_distance,
                guardian_closed, is_guardian_close)
            SELECT %s, %s, %s, %s, %s, 'Hyperliquid', true, 'Hermes', 'open', NOW(),
                   0, 0, %s, 0.03, TRUE, TRUE
            WHERE NOT EXISTS (
                SELECT 1 FROM trades WHERE token=%s AND server IN ('Hermes','Hermes-Dallas') AND status='open'
            )
            RETURNING id
        """, (token, direction, amount_usdt, entry_price, entry_price,
              leverage, token))
        row = cur.fetchone()
        if row is None:
            cur.close(); conn.close()
            log(f'  {token} already has an open trade — skipping add', 'WARN')
            return None
        trade_id = row[0]
        conn.commit()
        cur.close(); conn.close()
        log(f'  Created orphan recovery trade #{trade_id}: {token} {direction} @ {entry_price} x{leverage}', 'PASS')
        # Record entry features (RSI, MACD, etc.)
        try:
            from hl_sync_guardian import record_entry_features
            record_entry_features(int(trade_id), token.upper())
        except Exception as _feat_err:
            log(f'  Feature record failed for {token}: {_feat_err}', 'WARN')
        return trade_id
    except Exception as e:
        log(f'  add_orphan_recovery_trade failed for {token}: {e}', 'FAIL')
        try:
            conn.rollback(); conn.close()
        except:
            pass
        return None


# ── Core sync logic ───────────────────────────────────────────────────────────
def sync_open_trades():
    """
    Main reconciliation loop.

    Paper-only tokens  → close orphaned paper entries (no HL position to close)
    HL-only tokens     → orphan HL position:
      - If closed paper trade exists recently: skip (already reconciled)
      - If open paper trade exists: REUSE its ID — update entry/direction/leverage, close BOTH
      - Else: create new paper trade, close BOTH (same ID)
    """
    paper = get_open_paper_trades()
    hl    = get_open_hl_positions()

    paper_tokens = set(paper.keys())
    hl_tokens    = set(hl.keys())

    orphan_paper = paper_tokens - hl_tokens   # in paper, not on HL
    orphan_hl    = hl_tokens    - paper_tokens # on HL, not in paper
    matched       = paper_tokens & hl_tokens  # both have it — consistent

    log(f'Open paper: {len(paper)} | HL positions: {len(hl)} | Matched: {len(matched)} | Orphaned paper: {len(orphan_paper)} | Orphaned HL: {len(orphan_hl)}')

    # ── 1. Close orphaned paper entries ───────────────────────────────────────
    for token in sorted(orphan_paper):
        info = paper[token]
        tid  = info['id']
        entry = info['entry_price']
        if entry is None:
            entry = 0.0
        log(f'Paper-only: {token} (trade #{tid}) — no HL position, closing as ORPHAN_PAPER')
        ok = close_paper_trade_db(tid, token, float(entry), 'ORPHAN_PAPER')
        if not ok:
            log(f'  Failed to close orphaned paper trade #{tid}', 'FAIL')

    # ── 2. Handle orphaned HL positions ────────────────────────────────────────
    for coin in sorted(orphan_hl):
        info       = hl[coin]
        entry_px   = float(info.get('entry_px', 0) or 0)
        unreal_pnl = float(info.get('unrealized_pnl', 0) or 0)
        size       = float(info.get('size', 0) or 0)
        direction  = info.get('direction', 'LONG')  # already 'LONG' or 'SHORT' from HL
        lev        = int(abs(float(info.get('leverage', 1) or 1)))

        # 2a. Check for recently closed paper trade → already reconciled
        recent = find_recent_closed_trade(coin, within_minutes=60)
        if recent:
            log(f'Orphan HL {coin}: recent closed paper trade #{recent[0]} ({recent[1]}) — skipping, already reconciled', 'WARN')
            continue

        # 2b. Check for existing open paper trade → REUSE its ID
        existing_id = find_existing_open_trade(coin)
        if existing_id:
            log(f'Orphan HL {coin}: existing paper trade #{existing_id} — REUSE ID, update entry/direction/leverage, close both')
            # Update existing trade with current HL entry/direction/leverage
            if not DRY:
                conn = get_db_connection()
                if conn:
                    try:
                        cur = conn.cursor()
                        cur.execute("""
                            UPDATE trades SET entry_price=%s, direction=%s, leverage=%s,
                                hl_entry_price=%s, amount_usdt=%s
                            WHERE id=%s AND status='open'
                        """, (entry_px, direction, lev, entry_px, abs(unreal_pnl) if unreal_pnl else 10.0, existing_id))
                        conn.commit()
                        cur.close(); conn.close()
                        log(f'  Updated trade #{existing_id}: ep={entry_px} dir={direction} lev={lev}', 'PASS')
                    except Exception as upd_err:
                        log(f'  Failed to update existing trade #{existing_id}: {upd_err}', 'WARN')
            # Close HL position first (eliminates real-money risk)
            close_ok = close_hl_position(coin, f'reuse_trade_{existing_id}')
            if close_ok and not DRY:
                time.sleep(6)  # Wait for HL fill to settle
            # Close paper trade using the SAME existing ID
            close_paper_trade_db(existing_id, coin, entry_px, 'ORPHAN_PAPER')
            continue

        # 2c. No existing paper trade → create new one, then close BOTH
        log(f'Orphan HL {coin}: no existing paper trade — creating orphan recovery trade')
        trade_id = add_orphan_recovery_trade(
            token    = coin,
            direction= direction,
            entry_price = entry_px,
            amount_usdt = max(abs(unreal_pnl), 10.0) if unreal_pnl else 10.0,
            leverage = lev
        )
        if trade_id is None:
            # Race: another process created it between check and insert
            existing_id = find_existing_open_trade(coin)
            if existing_id:
                log(f'  Race resolved: using existing trade #{existing_id}')
                trade_id = existing_id
            else:
                log(f'  Could not create or find paper trade for {coin} — skipping', 'WARN')
                continue

        # Close HL position first
        close_ok = close_hl_position(coin, f'orphan_recovery_trade_{trade_id}')
        if close_ok and not DRY:
            time.sleep(6)  # Wait for HL fill to settle
        # Close paper trade using the SAME new ID
        close_paper_trade_db(trade_id, coin, entry_px, 'ORPHAN_PAPER')

    log('Sync complete.')


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Sync open paper trades with HL positions')
    parser.add_argument('--apply', action='store_true', help='Execute closes (default is dry-run)')
    args = parser.parse_args()

    if args.apply:
        DRY = False
        log('=== LIVE MODE — will close orphaned positions ===', 'WARN')
    else:
        log('=== DRY RUN — no changes will be made (use --apply to execute) ===', 'WARN')

    sync_open_trades()
