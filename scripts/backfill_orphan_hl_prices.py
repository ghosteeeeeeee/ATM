#!/usr/bin/env python3
"""
Backfill orphan_recovery trades with HL ground-truth prices.
For each orphan_recovery trade in brain.trades:
  1. Query HL get_trade_history() between open_time and close_time
  2. Compute wavg entry/exit from actual fills
  3. Get realized_pnl from close fills (side="B", closed_pnl field)
  4. UPDATE DB with hl_entry_price, hl_exit_price, hype_pnl_usdt, hype_pnl_pct
  5. Mark close_reason = 'orphan_recovery_backfilled'
  6. Print before/after for verification
"""
import sys
import time
import psycopg2
sys.path.insert(0, '/root/.hermes/scripts')

from hyperliquid_exchange import get_trade_history, get_exchange

DB_KWARGS = {
    'host': 'localhost',
    'port': 5432,
    'database': 'brain',
    'user': 'postgres',
    'password': 'brain123',
}

TOKENS = ['KAITO', 'WLFI', 'FARTCOIN', 'SKR', 'RENDER', 'MELANIA', 'POLYX', 'NIL', 'ZEC', 'FTT']

def ms(dt) -> int:
    """Convert datetime string or object to Unix milliseconds."""
    if isinstance(dt, str):
        dt = dt.replace(' ', 'T') if 'T' not in dt else dt
        from datetime import datetime
        dt = datetime.fromisoformat(dt)
    return int(dt.timestamp() * 1000)

def wavg_price(fills):
    """Compute size-weighted average price from a list of fill dicts."""
    if not fills:
        return 0.0
    total_sz = sum(f['sz'] for f in fills)
    if total_sz == 0:
        return 0.0
    return sum(f['px'] * f['sz'] for f in fills) / total_sz

def fetch_hl_prices(token: str, start_ms: int, end_ms: int):
    """
    Fetch fills for token between start_ms and end_ms.
    Returns dict with entry_price, exit_price, realized_pnl, open_fills, close_fills.
    """
    # Poll up to 3 times with 2s delay to handle fill delay
    fills = []
    for attempt in range(3):
        raw = get_trade_history(start_ms, end_ms)
        token_fills = [f for f in raw if f['coin'].upper() == token.upper()]
        if token_fills:
            fills = token_fills
            break
        if attempt < 2:
            print(f"  [attempt {attempt+1}/3] No fills yet for {token}, waiting 2s...")
            time.sleep(2)
        else:
            fills = token_fills

    if not fills:
        print(f"  WARNING: No fills found for {token} between {start_ms} and {end_ms}")
        return None

    open_fills  = [f for f in fills if f['side'] == 'A']
    close_fills = [f for f in fills if f['side'] == 'B']

    entry_price  = wavg_price(open_fills)
    exit_price   = wavg_price(close_fills)
    realized_pnl = sum(f['closed_pnl'] for f in close_fills)

    print(f"  HL fills: {len(fills)} total, {len(open_fills)} open, {len(close_fills)} close")
    print(f"  entry={entry_price:.8f}, exit={exit_price:.8f}, realized_pnl={realized_pnl:.6f} USDT")

    return {
        'entry_price':  entry_price,
        'exit_price':   exit_price,
        'realized_pnl': realized_pnl,
        'open_fills':   open_fills,
        'close_fills':  close_fills,
    }

def main():
    print("=" * 60)
    print("ORPHAN RECOVERY BACKFILL — HL Ground Truth Prices")
    print("=" * 60)

    conn = psycopg2.connect(**DB_KWARGS)
    cur = conn.cursor()

    for token in TOKENS:
        # Fetch all trades for this token with orphan_recovery close_reason
        cur.execute("""
            SELECT id, token, direction, entry_price, exit_price,
                   pnl_pct, pnl_usdt, hype_pnl_usdt, hype_pnl_pct,
                   open_time, close_time, close_reason,
                   hl_entry_price, hl_exit_price
            FROM trades
            WHERE token = %s
              AND close_reason = 'orphan_recovery'
              AND status = 'closed'
            ORDER BY close_time
        """, (token,))
        rows = cur.fetchall()

        if not rows:
            print(f"\n[{token}] No orphan_recovery trades found — skipping")
            continue

        for row in rows:
            (trade_id, tok, direction, entry_price, exit_price,
             pnl_pct, pnl_usdt, hype_pnl_usdt, hype_pnl_pct,
             open_time, close_time, close_reason,
             hl_entry_price, hl_exit_price) = row

            print(f"\n{'─'*60}")
            print(f"[{tok}] id={trade_id}  direction={direction}")
            print(f"  BEFORE: entry={entry_price}, exit={exit_price}, "
                  f"pnl_pct={pnl_pct}, hype_pnl={hype_pnl_usdt}")

            # Query HL for fills
            start_ms = ms(open_time) - 3600000 if open_time else 0  # go back 1h to catch edge cases
            end_ms   = ms(close_time) + 120000  # add 2min buffer

            hl_data = fetch_hl_prices(token, start_ms, end_ms)
            if hl_data is None:
                print(f"  SKIPPING {tok} id={trade_id} — no HL fills found")
                continue

            entry_px  = hl_data['entry_price']
            exit_px   = hl_data['exit_price']
            real_pnl  = hl_data['realized_pnl']

            # Use signal entry_price if HL has no open fills (pre-mirror positions)
            calc_entry_px = entry_px if entry_px > 0 else float(entry_price)

            # Compute hype_pnl_pct from actual exit price and entry price
            # Use amount_usdt from DB if available; default to 50
            cur.execute("SELECT amount_usdt FROM trades WHERE id = %s", (trade_id,))
            amt_row = cur.fetchone()
            amount  = float(amt_row[0]) if amt_row and amt_row[0] else 50.0

            if calc_entry_px > 0 and exit_px > 0:
                if direction == 'SHORT':
                    hype_pnl_pct_raw = ((calc_entry_px - exit_px) / calc_entry_px) * 100
                else:
                    hype_pnl_pct_raw = ((exit_px - calc_entry_px) / calc_entry_px) * 100
            else:
                hype_pnl_pct_raw = 0.0

            # Use actual realized_pnl from HL if available, otherwise compute
            if real_pnl != 0 and abs(real_pnl) > 0.0001:
                hype_pnl_usdt_val = real_pnl
            else:
                hype_pnl_usdt_val = round(amount * hype_pnl_pct_raw / 100, 4)

            print(f"  AFTER:  hl_entry={entry_px:.8f}, hl_exit={exit_px:.8f}, "
                  f"hype_pnl_usdt={hype_pnl_usdt_val:.6f}, hype_pnl_pct={hype_pnl_pct_raw:.4f}")

            # UPDATE DB — use calc_entry_px (HL entry or signal fallback)
            cur.execute("""
                UPDATE trades
                SET hl_entry_price  = %s,
                    hl_exit_price   = %s,
                    hype_pnl_usdt    = %s,
                    hype_pnl_pct     = %s,
                    pnl_pct          = %s,
                    pnl_usdt         = %s,
                    exit_price       = %s,
                    close_reason     = 'orphan_recovery_backfilled',
                    last_updated     = NOW(),
                    updated_at       = NOW()
                WHERE id = %s
            """, (
                calc_entry_px, exit_px,
                hype_pnl_usdt_val, hype_pnl_pct_raw,
                hype_pnl_pct_raw, hype_pnl_usdt_val,
                exit_px,
                trade_id
            ))
            conn.commit()
            print(f"  DB UPDATED for id={trade_id}")

    # Summary
    print(f"\n{'='*60}")
    print("BACKFILL COMPLETE — Verifying all trades:")
    print("=" * 60)
    cur.execute("""
        SELECT id, token, direction, entry_price, hl_entry_price,
               exit_price, hl_exit_price,
               pnl_pct, hype_pnl_usdt, hype_pnl_pct, close_reason
        FROM trades
        WHERE token IN %s
          AND close_reason = 'orphan_recovery_backfilled'
        ORDER BY token
    """, tuple(TOKENS))
    rows = cur.fetchall()
    print(f"{'id':>5} {'token':<10} {'direction':<8} {'entry_price':>15} {'hl_entry_price':>16} "
          f"{'hl_exit_price':>16} {'hype_pnl_usdt':>14} {'hype_pnl_pct':>12}  close_reason")
    print("-" * 120)
    for r in rows:
        print(f"{r[0]:>5} {r[1]:<10} {r[2]:<8} {r[3]:>15.8f} {str(r[4]):>16} "
              f"{str(r[5]):>16} {str(r[7]):>14} {str(r[8]):>12}  {r[10]}")

    cur.close()
    conn.close()
    print(f"\nDone. {len(rows)} trades backfilled.")

if __name__ == '__main__':
    main()
