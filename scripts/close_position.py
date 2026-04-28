#!/usr/bin/env python3
"""
Close a single HL position by coin and sync to paper + brain.
Usage: python3 close_position.py <COIN>
Example: python3 close_position.py STRK
"""
import sys, json, time, psycopg2
from datetime import datetime

sys.path.insert(0, '/root/.hermes/scripts')
from hyperliquid_exchange import close_position, get_open_hype_positions_curl, get_trade_history

PAPER_JSON = "/var/www/hermes/data/trades.json"
BRAIN_DB   = {'host': '/var/run/postgresql', 'database': 'brain', 'user': 'postgres'}

def log(msg, tag="INFO"):
    print(f"[{time.strftime('%H:%M:%S')}] [{tag}] {msg}")

def get_exit_price(coin):
    """Get the most recent fill price for a coin from HL trade history.
    NOTE: get_trade_history() does NOT accept a `limit` kwarg.
    Returns (exit_price, side) or (None, None).
    """
    try:
        fills = get_trade_history(coin)
        if fills:
            last = fills[-1]
            return float(last["price"]), last.get("side", "sell")
    except Exception as e:
        log(f"Could not get HL fill price: {e}", "WARN")
    return None, None

def close_paper(coin, direction, entry, exit_price):
    """Remove coin from paper open, append to closed with reason=manual_close."""
    with open(PAPER_JSON) as f:
        data = json.load(f)
    data["open"] = [p for p in data["open"] if p.get("coin") != coin]
    data.setdefault("closed", []).append({
        "coin":       coin,
        "direction":  direction,
        "entry":      entry,
        "exit":       exit_price or 0.0,
        "pnl_pct":    0.0,
        "pnl_usdt":   0.0,
        "closed_at":  datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f"),
        "reason":     "manual_close",
    })
    data["open_count"]   = len(data["open"])
    data["closed_count"] = len(data.get("closed", []))
    data["updated"] = datetime.now().isoformat() + "Z"
    with open(PAPER_JSON, "w") as f:
        json.dump(data, f, indent=2)
    log(f"Paper: closed {coin} ({direction}) entry={entry} exit={exit_price}", "PASS")

def close_brain(coin, exit_price):
    """Close the open brain trade for coin with reason=manual_close."""
    conn = psycopg2.connect(**BRAIN_DB)
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT id, direction, entry_price, amount_usdt
            FROM trades
            WHERE token = %s AND status = 'open' AND exchange = 'Hyperliquid'
            ORDER BY id DESC LIMIT 1
        """, (coin,))
        row = cur.fetchone()
        if not row:
            log(f"Brain: no open trade for {coin}", "WARN")
            return
        trade_id, direction, entry_price, amount_usdt_raw = row
        amount = float(amount_usdt_raw or 50.0)
        pnl_pct = 0.0
        if entry_price and float(entry_price) != 0 and exit_price:
            pnl_pct = round((exit_price - float(entry_price)) / float(entry_price) * 100, 4)
        # BUG-FIX (2026-04-19): pnl_usdt was hardcoded to 0 — manual_close trades
        # showed exit prices that differed from entry but pnl=0.00 was recorded.
        # Fix: compute pnl_usdt from entry/exit/amount and direction-aware formula.
        pnl_usdt_calc = 0.0
        if entry_price and float(entry_price) != 0 and exit_price:
            if direction == 'LONG':
                pnl_usdt_calc = round((exit_price - float(entry_price)) / float(entry_price) * amount, 4)
            else:
                pnl_usdt_calc = round((float(entry_price) - exit_price) / float(entry_price) * amount, 4)
        cur.execute("""
            UPDATE trades SET
                status='closed', close_time=NOW(), exit_price=%s,
                pnl_usdt=%s, pnl_pct=%s, exit_reason='manual_close',
                close_reason='manual_close', updated_at=NOW()
            WHERE id=%s
        """, (exit_price or 0.0, pnl_usdt_calc, pnl_pct, trade_id))
        conn.commit()
        log(f"Brain: closed trade {trade_id} ({coin} {direction}) entry={entry_price} exit={exit_price}", "PASS")
    finally:
        conn.close()

def record_cooldown(coin: str, direction: str, entry: float, exit_price: float):
    """Record loss cooldown based on PnL. Wins do NOT trigger cooldown."""
    try:
        from position_manager import set_loss_cooldown
    except ImportError:
        log("position_manager.set_loss_cooldown not available, skipping cooldown", "WARN")
        return
    if not entry or not exit_price or exit_price == 0:
        return
    if direction == 'LONG':
        pnl_pct = (exit_price - entry) / entry * 100
    else:
        pnl_pct = (entry - exit_price) / entry * 100
    if pnl_pct < 0:
        set_loss_cooldown(coin, direction)
        log(f"Cooldown: {coin} {direction} LOSS — loss cooldown recorded")
    else:
        log(f"Cooldown: {coin} {direction} WIN/BREAK — no cooldown (wins don't block)")

def main():
    if len(sys.argv) < 2:
        coin = input("Coin to close: ").strip().upper()
    else:
        coin = sys.argv[1].strip().upper()

    if not coin:
        print("No coin specified.")
        sys.exit(1)

    log(f"Closing {coin} on HL...")

    # Step 1: Close on HL
    result = close_position(coin)
    if result.get("success"):
        log(f"HL close: {result}", "PASS")
    else:
        log(f"HL close failed: {result}", "FAIL")
        sys.exit(1)

    # Step 2: Verify HL position gone
    hype = get_open_hype_positions_curl()
    if coin in hype:
        log(f"FAIL: {coin} STILL OPEN on HL", "FAIL")
        sys.exit(1)
    log(f"HL: {coin} confirmed closed ✓")

    # Step 3: Get exit price — try get_trade_history first, fallback to avgPx from close result
    exit_price, side = get_exit_price(coin)
    if not exit_price:
        statuses = result.get('result', {}).get('response', {}).get('data', {}).get('statuses', [])
        if statuses and 'filled' in statuses[0]:
            exit_price = float(statuses[0]['filled'].get('avgPx', 0))
            log(f"Exit price from close result avgPx: {exit_price}")
    if not exit_price:
        log(f"Could not fetch HL fill — using 0.0", "WARN")
        exit_price = 0.0
    else:
        log(f"Exit price: {exit_price}")

    # Step 4: Get direction/entry from paper for sync
    with open(PAPER_JSON) as f:
        paper_data = json.load(f)
    paper_match = next((p for p in paper_data["open"] if p.get("coin") == coin), None)

    if paper_match:
        close_paper(coin, paper_match["direction"], paper_match["entry"], exit_price)
        record_cooldown(coin, paper_match.get("direction", "LONG"), paper_match.get("entry", 0), exit_price)
    else:
        # Try brain for direction/entry
        conn = psycopg2.connect(**BRAIN_DB)
        cur = conn.cursor()
        cur.execute("SELECT direction, entry_price FROM trades WHERE token=%s AND status='open' AND exchange='Hyperliquid' LIMIT 1", (coin,))
        row = cur.fetchone()
        conn.close()
        if row:
            close_paper(coin, row[0], float(row[1]), exit_price)
            record_cooldown(coin, row[0], float(row[1]), exit_price)
        else:
            log(f"Could not find direction/entry for {coin} — skipping paper sync", "WARN")

    # Step 5: Sync brain
    close_brain(coin, exit_price)

    # Step 6: Final verification
    hype2 = get_open_hype_positions_curl()
    with open(PAPER_JSON) as f:
        final = json.load(f)
    paper_open = sorted([p["coin"] for p in final["open"] if p.get("exchange","").lower()=="hyperliquid"])
    conn = psycopg2.connect(**BRAIN_DB)
    cur = conn.cursor()
    cur.execute("SELECT token FROM trades WHERE status='open' AND exchange='Hyperliquid' ORDER BY token")
    brain_open = sorted([r[0] for r in cur.fetchall()])
    conn.close()
    log(f"Final — HL:    {sorted(hype2.keys())}")
    log(f"Final — Paper: {paper_open}")
    log(f"Final — Brain: {brain_open}")

if __name__ == "__main__":
    main()
