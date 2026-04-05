#!/usr/bin/env python3
"""
Backfill hype_pnl_usdt and hype_pnl_pct for closed trades using HL /my_trades.
HL API: side="A" = Open fill, side="B" = Close fill (has realized closedPnl)

Usage: python3 scripts/backfill_hl_pnl.py
"""
import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from hyperliquid_exchange import get_trade_history
from datetime import datetime, timedelta

import psycopg2
DB = {
    'host': 'localhost', 'port': 5432, 'database': 'brain',
    'user': 'postgres', 'password': 'brain123'
}

WINDOW_DAYS = 30  # extend window to catch older closed positions


def get_closed_trades_without_hl_pnl():
    conn = psycopg2.connect(**DB)
    cur = conn.cursor()
    cur.execute("""
        SELECT id, token, direction, entry_price, exit_price, pnl_usdt, pnl_pct,
               created_at, open_time
        FROM trades
        WHERE status = 'closed'
          AND (hype_pnl_pct IS NULL OR hype_pnl_pct = 0.0)
        ORDER BY created_at DESC
    """)
    rows = cur.fetchall()
    cols = [d[0] for d in cur.description]
    conn.close()
    return [dict(zip(cols, r)) for r in rows]


def get_hl_close_fill(token: str, start_time_ms: int, end_time_ms: int = None) -> dict:
    """
    Get the most recent HL close fill (side=B) for a token after start_time_ms.
    Returns {"realized_pnl": float, "exit_price": float, "sz": float, "time_ms": int}
    or None if no close fill found.
    """
    if end_time_ms is None:
        end_time_ms = int(time.time() * 1000)
    fills = get_trade_history(start_time_ms, end_time_ms)
    close_fills = [f for f in fills
                   if f['coin'].upper() == token.upper() and f['side'] == 'B']
    if not close_fills:
        return None
    # Most recent close fill
    return max(close_fills, key=lambda x: x['time_ms'])


def update_trade(trade_id, exit_price, pnl_usdt, pnl_pct, hype_pnl_usdt, hype_pnl_pct):
    conn = psycopg2.connect(**DB)
    cur = conn.cursor()
    cur.execute("""
        UPDATE trades SET
            exit_price     = %s,
            pnl_usdt       = %s,
            pnl_pct        = %s,
            hype_pnl_usdt  = %s,
            hype_pnl_pct   = %s
        WHERE id = %s
    """, (exit_price, pnl_usdt, pnl_pct, hype_pnl_usdt, hype_pnl_pct, trade_id))
    conn.commit()
    cur.close()
    conn.close()


def backfill():
    trades = get_closed_trades_without_hl_pnl()
    print(f"Found {len(trades)} closed trades without HL PnL")

    if not trades:
        print("Nothing to backfill.")
        return

    updated = 0
    skipped = 0

    for t in trades:
        trade_id    = t['id']
        token       = t['token']
        direction   = t['direction']
        open_time   = t['open_time']
        brain_entry = float(t['entry_price'] or 0)
        brain_exit  = float(t['exit_price'] or 0)
        brain_pnl   = float(t['pnl_usdt'] or 0)

        # Estimate amount_usdt from signal PnL if available
        if t['pnl_pct'] and float(t['pnl_pct']) != 0:
            amount_usdt = abs(brain_pnl / (float(t['pnl_pct']) / 100))
        else:
            amount_usdt = 50.0

        # Convert open_time to ms
        if open_time:
            if isinstance(open_time, str):
                dt = datetime.fromisoformat(open_time.replace('Z', '+00:00'))
            else:
                dt = open_time
            start_ms = int(dt.timestamp() * 1000)
        else:
            start_ms = int((datetime.now() - timedelta(days=WINDOW_DAYS)).timestamp() * 1000)

        end_ms = start_ms + 86400 * WINDOW_DAYS * 1000

        # Query HL with retry (empty fills can mean rate-limit or genuinely no data)
        hl = None
        for attempt in range(4):
            fills = get_trade_history(start_ms, end_ms)
            close_fills = [f for f in fills
                           if f['coin'].upper() == token.upper() and f['side'] == 'B']
            if close_fills:
                hl = max(close_fills, key=lambda x: x['time_ms'])
                break
            elif not fills:
                wait = 2 ** attempt + 1
                print(f"  No fills for {token} (attempt {attempt+1}/4), retrying in {wait}s...")
                time.sleep(wait)
            else:
                break

        if not hl:
            print(f"[{trade_id}] {token} {direction} — no HL close fill (may be older than {WINDOW_DAYS}d)")
            skipped += 1
            continue

        # Calculate hype_pnl_pct from closed_pnl (HL gives this on side=B fills)
        hype_pnl_pct = (hl['closed_pnl'] / amount_usdt * 100) if amount_usdt else 0

        print(f"[{trade_id}] {token} {direction}")
        print(f"  brain:  entry={brain_entry:.6f}  exit={brain_exit:.6f}  "
              f"pnl={brain_pnl:+.4f} ({t['pnl_pct']:+.2f}%)")
        print(f"  HL:     exit={hl['px']:.6f}  realized={hl['closed_pnl']:+.4f}  "
              f"sz={hl['sz']}  @ {datetime.fromtimestamp(hl['time_ms']/1000).strftime('%m-%d %H:%M')}")

        update_trade(trade_id, hl['px'],
                     hl['closed_pnl'], hype_pnl_pct,
                     hl['closed_pnl'], hype_pnl_pct)
        print(f"  → hype_pnl_pct={hype_pnl_pct:+.2f}%")

        # Brief pause between trades to avoid rate limits
        time.sleep(0.5)
        updated += 1

    print(f"\nDone: {updated} updated, {skipped} no-HL-data")


if __name__ == '__main__':
    backfill()
