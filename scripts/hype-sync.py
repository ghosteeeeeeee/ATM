#!/usr/bin/env python3
"""
hype-sync.py — Reconcile brain DB positions with live Hyperliquid positions.

Usage:
  python3 hype-sync.py --dry       # show what would happen (default)
  python3 hype-sync.py --apply    # actually mirror missing trades

What it does:
  1. Get open positions from brain DB (paper + live)
  2. Get actual open positions from Hyperliquid
  3. For each brain position not on HL → mirror_open
  4. For each HL position not in brain  → mirror_close + brain.close_trade (ground-truth PnL)
  5. Log everything with clear PASS/FAIL/INFO tags
"""
import sys, argparse, time
sys.path.insert(0, '/root/.hermes/scripts')
from hyperliquid_exchange import (
    mirror_open, mirror_close, is_live_trading_enabled,
    get_open_hype_positions_curl, is_delisted, get_tradeable_tokens,
    get_realized_pnl
)
import psycopg2

DRY = True  # overridden by --dry / --apply

DB = {'host': '/var/run/postgresql', 'database': 'brain', 'user': 'postgres'}


def log(msg, tag="INFO"):
    ts = time.strftime("%H:%M:%S")
    print(f"[{ts}] [{tag}] {msg}")


def get_brain_positions():
    """Get all live (non-paper) open positions from brain DB."""
    conn = psycopg2.connect(**DB)
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT token, direction, entry_price, leverage, server, paper
            FROM trades
            WHERE status = 'open'
              AND paper = FALSE
              AND server = 'Hermes'
            ORDER BY token
        """)
        rows = cur.fetchall()
        return [{'token': r[0], 'direction': r[1], 'entry_price': r[2],
                 'leverage': r[3], 'server': r[4], 'paper': r[5]} for r in rows]
    except Exception as e:
        log(f"Failed to query brain trades: {e}", "FAIL")
        return []
    finally:
        conn.close()


def get_brain_trade_by_token(token: str):
    """Get open brain trade ID for a token (needed to close it)."""
    conn = psycopg2.connect(**DB)
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT id, entry_price, direction, open_time
            FROM trades
            WHERE token = %s AND status = 'open' AND paper = FALSE
            LIMIT 1
        """, (token,))
        row = cur.fetchone()
        return row  # (id, entry_price, direction, open_time) or None
    finally:
        conn.close()


def close_brain_trade(trade_id: int, exit_price: float, realized_pnl: float):
    """Close a brain trade with HL ground-truth PnL (called after mirror_close)."""
    # Import brain close_trade inline to avoid circular imports
    import os
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from brain import close_trade as brain_close_trade
    try:
        brain_close_trade(trade_id, exit_price, realized_pnl)
        log(f"  brain.close_trade({trade_id}) updated — exit={exit_price:.6f} pnl={realized_pnl:+.4f}", "PASS")
    except Exception as e:
        log(f"  brain.close_trade({trade_id}) FAILED — {e}", "FAIL")


def get_hype_positions():
    """Get live HL positions. Returns {} on failure."""
    try:
        return get_open_hype_positions_curl()
    except Exception as e:
        log(f"Failed to fetch HL positions: {e}", "WARN")
        return {}


def sync_opens(brain_positions, hype_positions):
    """Mirror any brain positions missing from HL."""
    hype_tokens = set(hype_positions.keys())
    tradeable = get_tradeable_tokens()
    opened = skipped = delisted = 0

    for pos in brain_positions:
        token = pos['token']

        if is_delisted(token):
            log(f"  {token}: DELISTED on HL — cannot mirror", "WARN")
            delisted += 1
            continue

        if token in hype_tokens:
            skipped += 1
            continue

        tag = "DRY" if DRY else "SYNC"
        log(f"  {token}: missing on HL → {tag} {pos['direction']} @ ${pos['entry_price']:.4f} lev={pos['leverage']}x", "WARN")

        if DRY:
            opened += 1
            continue

        try:
            result = mirror_open(
                token, pos["direction"].upper(),
                float(pos["entry_price"]),
                leverage=int(pos["leverage"])
            )
            if result.get("success"):
                log(f"  {token}: ✅ mirror_open SUCCESS — HL fill=${result.get('hl_entry_price'):.6f}", "PASS")
            else:
                log(f"  {token}: ❌ mirror_open FAILED — {result.get('message')}", "FAIL")
        except Exception as e:
            log(f"  {token}: ❌ mirror_open EXCEPTION — {e}", "FAIL")

        opened += 1
        time.sleep(1)

    return opened, skipped, delisted


def sync_closes(hype_positions, brain_positions):
    """
    Close any HL positions that aren't in brain DB (paper protection).
    After mirror_close succeeds, queries HL for realized PnL and calls brain.close_trade.
    """
    brain_tokens = {p['token'] for p in brain_positions}
    closed = 0

    for token, pos in hype_positions.items():
        if token in brain_tokens:
            continue

        direction = pos.get("direction", "UNKNOWN")
        tag = "DRY" if DRY else "SYNC"
        log(f"  {token}: on HL but not in brain → {tag} CLOSE {direction}", "WARN")

        if DRY:
            closed += 1
            continue

        try:
            # Step 1: mirror_close on HL
            result = mirror_close(token)
            if not result.get("success"):
                log(f"  {token}: ❌ mirror_close FAILED — {result.get('message')}", "FAIL")
                continue

            log(f"  {token}: ✅ mirror_close SUCCESS on HL", "PASS")

            # Step 2: Get HL exit price and realized PnL
            from datetime import datetime
            open_time = pos.get("open_time")
            if open_time:
                if isinstance(open_time, str):
                    dt = datetime.fromisoformat(open_time.replace('Z', '+00:00'))
                else:
                    dt = open_time
                start_ms = int(dt.timestamp() * 1000)
            else:
                start_ms = int((datetime.now().timestamp() - 86400 * 3) * 1000)

            hl_data = get_realized_pnl(token.upper(), start_ms)
            exit_price = hl_data.get("exit_price") or 0
            realized_pnl = hl_data.get("realized_pnl") or 0

            log(f"  {token}: HL realized pnl={realized_pnl:+.4f} exit={exit_price:.6f}", "INFO")

            # Step 3: Find and close the brain trade
            brain_trade = get_brain_trade_by_token(token)
            if brain_trade:
                trade_id = brain_trade[0]
                close_brain_trade(trade_id, exit_price, realized_pnl)
            else:
                log(f"  {token}: no brain trade found to close", "WARN")

        except Exception as e:
            log(f"  {token}: ❌ sync_closes EXCEPTION — {e}", "FAIL")

        closed += 1
        time.sleep(1)

    return closed


def main():
    global DRY
    parser = argparse.ArgumentParser(description="Sync brain positions with Hyperliquid")
    parser.add_argument("--dry", action="store_true", default=True,
                        help="Dry run (default — shows what would happen)")
    parser.add_argument("--apply", action="store_true",
                        help="Actually execute mirror trades")
    parser.add_argument("--opens-only", action="store_true")
    parser.add_argument("--closes-only", action="store_true")
    args = parser.parse_args()
    DRY = not args.apply

    mode = "DRY RUN" if DRY else "LIVE SYNC"
    live = is_live_trading_enabled()
    log(f"hype-sync — {mode} | Live trading: {'ON' if live else 'OFF'}", "INFO")

    if not live:
        log("Live trading is DISABLED — opens will be blocked by hyperliquid_exchange", "WARN")

    brain_pos = get_brain_positions()
    log(f"Brain live positions: {len(brain_pos)}", "INFO")
    for p in brain_pos:
        log(f"  [{p['server']}] {p['token']} {p['direction']} @ ${float(p['entry_price']):.4f} lev={p['leverage']}x", "INFO")

    hype_pos = get_hype_positions()
    log(f"HL open positions: {len(hype_pos)}", "INFO")
    for token, p in hype_pos.items():
        log(f"  {token} {p.get('direction')} ${p.get('entry_price')} lev={p.get('leverage')}x", "INFO")

    opens_ok = closes_ok = 0
    if not args.closes_only:
        log("--- Checking missing HL opens ---", "INFO")
        opened, skipped, delisted = sync_opens(brain_pos, hype_pos)
        log(f"Opens: {skipped} already on HL | {delisted} delisted | {opened - skipped} to mirror", "INFO")

    if not args.opens_only:
        log("--- Checking unexpected HL closes ---", "INFO")
        closed = sync_closes(hype_pos, brain_pos)
        closes_ok = closed
        tag = "WARN" if closed else "INFO"
        log(f"Closes: {closed} closed {('(should be 0 — investigate)' if closed else '')}", tag)

    if DRY:
        log("DRY RUN complete — re-run with --apply to execute", "WARN")
    else:
        log(f"SYNC complete — {opens_ok} opened, {closes_ok} closed", "PASS")


if __name__ == "__main__":
    main()
