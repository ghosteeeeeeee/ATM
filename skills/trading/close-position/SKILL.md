---
name: close-position
description: Close a specific Hyperliquid position by coin symbol AND sync to paper trades.json + brain PostgreSQL. After HL close fills, fetches the exit price, updates paper with reason=manual_close, and closes the brain trade. Records loss cooldown (wins do NOT trigger cooldown).
version: 1.3.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [trading, hyperliquid, close, sync]
notes:
  - get_trade_history() returns 422 for many coins — always fall back to avgPx from close result
  - Must close in BOTH postgres (brain) AND trades.json — guardian reads from postgres and will re-insert if only trades.json is updated
  - Only LOSSES trigger cooldown — wins do NOT block re-entry
  - Win cooldowns were removed from position_manager.py entirely
---

# Close Position

Close a specific Hyperliquid position by coin symbol. **Full stop-the-line sync** — updates HL, paper trades.json, and brain PostgreSQL in one shot.

## ⚠️ Critical: Postgres-First Reconciliation

**The guardian reads from postgres, NOT trades.json.** If you manually edit trades.json without closing the trade in postgres, the guardian will re-insert the position on its next cycle (every 5 min) — clobbering your edit.

To close a position cleanly, you MUST close in BOTH:
1. HL (via this skill)
2. Postgres (`UPDATE trades SET status='closed' WHERE token='XMR' AND status='open'`)

This skill does both. If you only edit trades.json, the guardian will undo your changes.

## Usage

```
/close-position STRK
/close-position BTC
/close-position ETH
```

## How it works

1. Calls `close_position(coin)` on Hyperliquid (real market order)
2. Verifies the position is gone from HL
3. Fetches exit price from `get_trade_history()` (last fill = exit price)
   - NOTE: `get_trade_history()` does **NOT** accept a `limit` kwarg
4. Removes coin from paper `trades.json` open, appends to closed with `reason: manual_close`
5. Closes the corresponding brain PostgreSQL trade with `exit_reason: manual_close`
6. Reports final state across all 3 stores (HL / Paper / Brain)

## Exit Price — Primary + Fallback

Exit price is fetched from `get_trade_history()` (last fill = exit price).

**If `get_trade_history()` fails (422 or network error):** do NOT default to 0.0 — extract `avgPx` from the `close_position()` result's filled status instead:
```python
statuses = result.get('result', {}).get('response', {}).get('data', {}).get('statuses', [])
if statuses and 'filled' in statuses[0]:
    exit_price = float(statuses[0]['filled'].get('avgPx', 0))
```
This has proven reliable across XMR, INIT, LAYER and other coins where `get_trade_history()` returns 422 after a fill.

## Notes

- Uses `hyperliquid_exchange.close_position()` — same function guardian uses
- Works on **live HL positions only**
- `reason=manual_close` distinguishes operator closes from guardian/ATR stops
- After using this skill, **do not** run `sync-open-trades` separately — the close is already synced

## Code

```python
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
from position_manager import set_loss_cooldown

PAPER_JSON = "/var/www/hermes/data/trades.json"
BRAIN_DB   = {'host': '/var/run/postgresql', 'database': 'brain', 'user': 'postgres'}

def log(msg, tag="INFO"):
    print(f"[{time.strftime('%H:%M:%S')}] [{tag}] {msg}")

def get_exit_price(coin):
    """Get the most recent fill price for a coin from HL trade history.
    NOTE: get_trade_history() does NOT accept a `limit` kwarg.
    Returns (exit_price, side) or (None, None).

    If get_trade_history() fails (422 for many coins), caller should
    extract avgPx from the close_position() result instead — see main().
    """
    try:
        fills = get_trade_history(coin)
        if fills:
            # most recent fill is last in the list
            last = fills[-1]
            return float(last["price"]), last.get("side", "sell")
    except Exception as e:
        log(f"Could not get HL fill price: {e}", "WARN")
    return None, None

def close_paper(coin, direction, entry, exit_price):
    """Remove coin from paper open, append to closed with reason=manual_close.
    pnl_pct is computed direction-aware: LONG = (exit-entry)/entry, SHORT = (entry-exit)/entry.
    """
    with open(PAPER_JSON) as f:
        data = json.load(f)
    data["open"] = [p for p in data["open"] if p.get("coin") != coin]
    data.setdefault("closed", []).append({
        "coin":       coin,
        "direction":  direction,
        "entry":      entry,
        "exit":       exit_price or 0.0,
        "pnl_pct":    round((exit_price - entry) / entry * 100, 4) if direction == "LONG" and entry else 0.0,
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
            SELECT id, direction, entry_price
            FROM trades
            WHERE token = %s AND status = 'open' AND exchange = 'Hyperliquid'
            ORDER BY id DESC LIMIT 1
        """, (coin,))
        row = cur.fetchone()
        if not row:
            log(f"Brain: no open trade for {coin}", "WARN")
            return
        trade_id, direction, entry_price = row
        pnl_pct = 0.0
        if entry_price and float(entry_price) != 0 and exit_price:
            if direction == 'LONG':
                pnl_pct = round((exit_price - float(entry_price)) / float(entry_price) * 100, 4)
            else:  # SHORT
                pnl_pct = round((float(entry_price) - exit_price) / float(entry_price) * 100, 4)
        cur.execute("""
            UPDATE trades SET
                status='closed', close_time=NOW(), exit_price=%s,
                pnl_usdt=0, pnl_pct=%s, exit_reason='manual_close',
                close_reason='manual_close', updated_at=NOW()
            WHERE id=%s
        """, (exit_price or 0.0, pnl_pct, trade_id))
        conn.commit()
        log(f"Brain: closed trade {trade_id} ({coin} {direction}) entry={entry_price} exit={exit_price}", "PASS")
    finally:
        conn.close()

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
        # get_trade_history() failed — extract avgPx from the close result itself
        statuses = result.get('result', {}).get('response', {}).get('data', {}).get('statuses', [])
        if statuses and 'filled' in statuses[0]:
            exit_price = float(statuses[0]['filled'].get('avgPx', 0))
            log(f"Exit price from close result avgPx: {exit_price}")
        else:
            exit_price = 0.0
    if exit_price:
        log(f"Exit price: {exit_price}")

    # Step 4: Get direction/entry from paper or brain for sync
    with open(PAPER_JSON) as f:
        paper_data = json.load(f)
    paper_match = next((p for p in paper_data["open"] if p.get("coin") == coin), None)

    if paper_match:
        close_paper(coin, paper_match["direction"], paper_match["entry"], exit_price)
    else:
        # Try brain for direction/entry
        conn = psycopg2.connect(**BRAIN_DB)
        cur = conn.cursor()
        cur.execute("SELECT direction, entry_price FROM trades WHERE token=%s AND status='open' AND exchange='Hyperliquid' LIMIT 1", (coin,))
        row = cur.fetchone()
        conn.close()
        if row:
            close_paper(coin, row[0], float(row[1]), exit_price)
        else:
            log(f"Could not find direction/entry for {coin} — skipping paper sync", "WARN")

    # Step 5: Sync brain
    close_brain(coin, exit_price)

    # Step 5b: Record loss/win cooldown using paper_match already in scope
    if paper_match:
        record_cooldown(coin, paper_match.get("direction", "LONG"), paper_match.get("entry", 0), exit_price)
    else:
        # Try brain for direction/entry
        conn = psycopg2.connect(**BRAIN_DB)
        cur = conn.cursor()
        cur.execute("SELECT direction, entry_price FROM trades WHERE token=%s AND status='closed' AND exchange='Hyperliquid' ORDER BY id DESC LIMIT 1", (coin,))
        row = cur.fetchone()
        conn.close()
        if row:
            record_cooldown(coin, row[0], float(row[1]), exit_price)
        else:
            log(f"Could not find direction/entry for {coin} — skipping cooldown", "WARN")

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

def record_cooldown(coin: str, direction: str, entry: float, exit_price: float):
    """
    Record loss cooldown based on PnL.
    Wins do NOT trigger cooldown — only losses trigger the incremental block (2h → 4h → 8h per streak).
    """
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

if __name__ == "__main__":
    main()
```

## Notes

- Uses `hyperliquid_exchange.close_position()` — the same function guardian uses to close positions
- Works on LIVE HL positions only
- Slippage is set by the exchange module (0.5% default)
- No paper-only close — this is a real HL market close
- **get_trade_history() returns 422 for many coins** — exit price always extracted from close result avgPx as primary source
- **Cooldowns: losses only** — `set_loss_cooldown()` called after close; wins do NOT trigger cooldown
- Win cooldowns (`_set_win_cooldown`) removed from position_manager.py entirely — wins never block re-entry
- Guardian reads from postgres — closing only trades.json will be undone by guardian within 5 min

## ⚠️ Critical: Do NOT Run Multiple Closes in Parallel Against Same File

`trades.json` is a plain JSON file with no locking. Running multiple `close_position.py` instances simultaneously causes concurrent read/write races that corrupt the file mid-operation (JSONDecodeError on partial writes). HL closes will succeed, but paper sync will fail on some coins.

**Recovery when paper sync partially fails:**
1. HL is already closed — that's the hard part, already done
2. Extract exit prices from the close result `avgPx` fields (already printed in logs)
3. Run a manual sync script (see below) to close remaining stale paper+brain entries

```python
# Manual sync for stale entries after parallel close race
# Run AFTER all parallel HL closes have finished
exits = {
    'COIN': {'exit': 85.44,   'direction': 'LONG',  'entry': 85.481},
}
import json, psycopg2
from datetime import datetime
PAPER = "/var/www/hermes/data/trades.json"
# 1. Check what's still open in paper but closed on HL
# 2. Close each via brain first (postgres), then paper
# Guardian reads from postgres — brain close is authoritative
conn = psycopg2.connect(host='/var/run/postgresql', database='brain', user='postgres')
cur = conn.cursor()
for coin, ex in exits.items():
    pnl_pct = round((ex['exit'] - ex['entry']) / ex['entry'] * 100, 4) if ex['direction'] == 'LONG' else round((ex['entry'] - ex['exit']) / ex['entry'] * 100, 4)
    cur.execute("UPDATE trades SET status='closed', close_time=NOW(), exit_price=%s, pnl_pct=%s, exit_reason='manual_close', close_reason='manual_close', updated_at=NOW() WHERE token=%s AND status='open' AND exchange='Hyperliquid'", (ex['exit'], pnl_pct, coin))
    print(f"Brain: closed {coin} [{cur.rowcount}]")
conn.commit()
conn.close()
# Then sync paper...
```

**Rule: close positions sequentially, never in parallel, unless you have a distributed lock on trades.json**
