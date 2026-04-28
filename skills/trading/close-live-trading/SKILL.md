---
name: close-live-trading
description: |
  Emergency shutdown: disable live trading and cleanly close ALL open Hyperliquid
  positions. Closes on HL (real market orders), then syncs paper trades.json and
  brain PostgreSQL. Monitors for 5 minutes post-close to confirm no new positions.
  Use when switching to paper-only or before any risky system changes.
version: 1.0.0
author: Hermes Agent
license: MIT
tags: [trading, hyperliquid, emergency, shutdown]
---

# Close Live Trading

Emergency shutdown: disable live trading and cleanly close ALL open Hyperliquid positions.

## What it does

1. **Flag OFF** — sets `live_trading: false` in `/var/www/hermes/data/hype_live_trading.json`
2. **Detect** — fetches all open HL positions via `get_open_hype_positions_curl()`
3. **HL close** — calls `close_position.py` for each coin (real HL market orders)
4. **Paper sync** — closes stale entries in `trades.json` (handles concurrent corruption)
5. **Brain sync** — closes stale entries in brain PostgreSQL
6. **Monitor** — polls HL every 60s for 5 minutes, confirms zero new positions

## Usage

```
/close-live-trading
```

## Exit Prices

HL `close_position()` returns `avgPx` in the fill result — use this as exit price
when `get_trade_history()` returns 422 (common for many coins).

PnL is computed direction-aware:
- LONG: `(exit - entry) / entry * 100`
- SHORT: `(entry - exit) / entry * 100`

## Loss Cooldowns

Only losses trigger cooldowns (`set_loss_cooldown()`). Wins do NOT block re-entry.

## Edge Case: trades.json Concurrent Corruption

If multiple `close_position.py` scripts run in parallel, concurrent writes can corrupt
`trades.json` (JSONDecodeError: `Expecting ',' delimiter`). When this happens:
- HL close already succeeded — positions are gone from HL
- Close remaining coins in brain directly via SQL
- Rewrite paper from scratch using only the non-corrupted data
- Skip the rewrite if paper is already valid

## Verification Checklist

```
HL open:      []
Paper open:   []
Brain open:   []
```

## Code

```python
#!/usr/bin/env python3
"""
close_live_trading.py — Emergency shutdown of all live HL positions.
"""
import sys, json, time, subprocess
from datetime import datetime

sys.path.insert(0, '/root/.hermes/scripts')
from hyperliquid_exchange import get_open_hype_positions_curl, close_position
import psycopg2

PAPER_JSON = "/var/www/hermes/data/trades.json"
LIVE_FLAG  = "/var/www/hermes/data/hype_live_trading.json"
BRAIN_DB   = {'host': '/var/run/postgresql', 'database': 'brain', 'user': 'postgres'}

def log(msg, tag="INFO"):
    print(f"[{time.strftime('%H:%M:%S')}] [{tag}] {msg}")

def set_live_off():
    with open(LIVE_FLAG, 'w') as f:
        json.dump({"live_trading": False, "reason": "emergency-close", "ts": int(time.time())}, f)
    log("live_trading flag OFF")

def get_open():
    pos = get_open_hype_positions_curl()
    return pos  # {COIN: {size, direction, entry_px, unrealized_pnl, leverage}}

def close_one(coin):
    """Close single coin on HL, return (success, avgPx or None)."""
    try:
        result = close_position(coin)
        if result.get("success"):
            statuses = result.get("result", {}).get("response", {}).get("data", {}).get("statuses", [])
            avg_px = None
            if statuses and "filled" in statuses[0]:
                avg_px = float(statuses[0]["filled"].get("avgPx", 0))
            log(f"HL close {coin}: avgPx={avg_px}", "PASS")
            return True, avg_px
    except Exception as e:
        log(f"HL close {coin} failed: {e}", "FAIL")
    return False, None

def paper_sync(coin, direction, entry, exit_px):
    """Close coin in paper trades.json."""
    with open(PAPER_JSON) as f:
        data = json.load(f)
    data["open"] = [p for p in data["open"] if p.get("coin") != coin]
    pnl_pct = 0.0
    if direction == "LONG":
        pnl_pct = round((exit_px - entry) / entry * 100, 4) if entry else 0.0
    else:
        pnl_pct = round((entry - exit_px) / entry * 100, 4) if entry else 0.0
    data.setdefault("closed", []).append({
        "coin": coin, "direction": direction, "entry": entry, "exit": exit_px or 0.0,
        "pnl_pct": pnl_pct, "pnl_usdt": 0.0,
        "closed_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f"),
        "reason": "manual_close",
    })
    data["open_count"]   = len(data["open"])
    data["closed_count"] = len(data.get("closed", []))
    data["updated"] = datetime.now().isoformat() + "Z"
    with open(PAPER_JSON, "w") as f:
        json.dump(data, f, indent=2)
    log(f"Paper closed {coin} ({direction}) entry={entry} exit={exit_px} pnl%={pnl_pct}", "PASS")

def brain_sync(coin, direction, entry, exit_px):
    """Close coin in brain PostgreSQL."""
    conn = psycopg2.connect(**BRAIN_DB)
    try:
        cur = conn.cursor()
        pnl_pct = 0.0
        if direction == "LONG":
            pnl_pct = round((exit_px - entry) / entry * 100, 4) if entry else 0.0
        else:
            pnl_pct = round((entry - exit_px) / entry * 100, 4) if entry else 0.0
        cur.execute("""
            UPDATE trades SET
              status='closed', close_time=NOW(), exit_price=%s,
              pnl_usdt=0, pnl_pct=%s, exit_reason='manual_close',
              close_reason='manual_close', updated_at=NOW()
            WHERE token=%s AND status='open' AND exchange='Hyperliquid'
        """, (exit_px or 0.0, pnl_pct, coin))
        conn.commit()
        log(f"Brain closed {coin} ({direction}) pnl%={pnl_pct} [{cur.rowcount} row(s)]", "PASS")
    finally:
        conn.close()

def verify_clean():
    """Return (hl_ok, paper_ok, brain_ok)."""
    # HL
    hl = get_open_hype_positions_curl()
    hl_ok = len(hl) == 0
    # Paper
    with open(PAPER_JSON) as f:
        paper = json.load(f)
    paper_ok = len([p for p in paper.get("open", []) if p.get("exchange","").lower()=="hyperliquid"]) == 0
    # Brain
    conn = psycopg2.connect(**BRAIN_DB)
    cur = conn.cursor()
    cur.execute("SELECT token FROM trades WHERE status='open' AND exchange='Hyperliquid'")
    brain_ok = len(cur.fetchall()) == 0
    conn.close()
    return hl_ok, paper_ok, brain_ok

def monitor(interval=60, cycles=5):
    """Poll HL for new positions."""
    for i in range(1, cycles+1):
        log(f"Monitor check {i}/{cycles}")
        hl = get_open_hype_positions_curl()
        if hl:
            log(f"WARNING: new positions appeared: {list(hl.keys())}", "WARN")
        else:
            log("No new positions")
        if i < cycles:
            time.sleep(interval)

def main():
    # 1. Flag off
    set_live_off()

    # 2. Get positions
    pos = get_open()
    coins = list(pos.keys())
    log(f"Open positions: {coins}")
    if not coins:
        log("No open positions — monitoring only")
        monitor()
        return

    # 3. Close all on HL (sequential to avoid rate-limit storms)
    exits = {}  # coin -> avgPx
    for coin in coins:
        ok, avg = close_one(coin)
        if ok:
            exits[coin] = avg
        time.sleep(1)  # rate-limit breathing room

    # 4. Verify HL empty
    hl = get_open_hype_positions_curl()
    if hl:
        log(f"WARNING: HL still has positions: {list(hl.keys())}", "WARN")
    else:
        log("HL confirmed empty")

    # 5. Sync paper + brain
    for coin, avg_px in exits.items():
        info = pos[coin]
        paper_sync(coin, info["direction"], info["entry_px"], avg_px)
        brain_sync(coin, info["direction"], info["entry_px"], avg_px)

    # 6. Final verification
    hl_ok, paper_ok, brain_ok = verify_clean()
    log(f"Final — HL: {'OK' if hl_ok else 'FAIL'}, Paper: {'OK' if paper_ok else 'FAIL'}, Brain: {'OK' if brain_ok else 'FAIL'}")

    # 7. Monitor
    monitor()

if __name__ == "__main__":
    main()
```

## Related Skills

- `close-position` — close a single position
- `clear-all` — full state reset
- `sync-open-trades` — reconcile open positions
