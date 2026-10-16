---
name: manual-trade-override
description: Use when the CEO wants to manually open a trade bypassing signal gates. Triggers on "open X manually", "force trade", "manual override", "open X now". ONLY use when CEO is present and explicitly requests it.
---

# Manual Trade Override

Open trades directly on Hyperliquid, bypassing signal gates. **ONLY use when CEO is present and explicitly requests it.**

## When to Use

- CEO says "open X manually" or "force trade X"
- Signal gates are blocking a trade the CEO wants
- Testing/debugging trade execution
- Market conditions require immediate action

## When NOT to Use

- Automated trading (watchdog/pipeline handles this)
- When CEO is not present
- Without explicit CEO confirmation

## Command

```bash
cd /root/.hermes/scripts && python3 brain.py trade add COIN DIRECTION AMOUNT ENTRY --real --signal ai-trader-manual --strategy ai-trader --confidence 70 --leverage 5 --sl STOP_LOSS --target TAKE_PROFIT
```

## Parameters

| Parameter | Required | Description | Example |
|-----------|----------|-------------|---------|
| `COIN` | ✅ | Token symbol (uppercase) | `GRASS` |
| `DIRECTION` | ✅ | `long` or `short` | `long` |
| `AMOUNT` | ✅ | USDT amount (before leverage) | `11.10` |
| `ENTRY` | ✅ | Current market price | `0.86897` |
| `--real` | ✅ | Real trade (not paper) | `--real` |
| `--signal` | ✅ | Signal source tag | `ai-trader-manual` |
| `--strategy` | ✅ | Strategy name | `ai-trader` |
| `--confidence` | ✅ | Confidence 0-100 | `70` |
| `--leverage` | ✅ | Leverage 1-10 | `5` |
| `--sl` | ✅ | Stop loss price | `0.8437` |
| `--target` | ✅ | Take profit price | `0.8853` |

## Pre-Trade Checklist

**ALWAYS run the precheck before opening:**
```bash
cd /root/.hermes/scripts && python3 ai_trader_precheck.py COIN DIRECTION
```

Even for manual trades, the RR engine and exit management will manage the position. The precheck tells you:
- RR engine verdict (will exit management work?)
- RSI position (avoid extremes)
- Volatility (is there room for SL/TP?)
- 30d winrate (is this coin a known loser?)

## Example: Open GRASS LONG

```bash
# 1. Precheck
cd /root/.hermes/scripts && python3 ai_trader_precheck.py GRASS LONG

# 2. Get current price
python3 -c "
import sqlite3
conn = sqlite3.connect('/root/.hermes/data/candles.db')
cur = conn.cursor()
cur.execute('SELECT close FROM candles_5m WHERE token=\"GRASS\" ORDER BY ts DESC LIMIT 1')
print(cur.fetchone()[0])
conn.close()
"

# 3. Open trade (example: $11 USDT, 5x leverage, SL 3% below, TP 4% above)
python3 brain.py trade add GRASS long 11.10 0.86897 --real \
    --signal ai-trader-manual --strategy ai-trader --confidence 70 \
    --leverage 5 --sl 0.8437 --target 0.8853
```

## What Happens After Opening

1. **Trade opens on Hyperliquid** — mirrored position
2. **PostgreSQL records trade** — `signal='ai-trader-manual'`, `atr_managed=False`
3. **Dashboard shows trade** — via trades.json (updated every minute)
4. **Exit management activates** — `ai-trader` prefix matches `SIGNAL_EXIT_CONFIG` → `rr_engine`
5. **Position manager manages** — trailing stops, ATR SL/TP, guardian protection

## Exit Management

Manual trades use the same exit management as AI trader signals:
- **RR Engine exit** — structural S/R based SL/TP
- **Trailing stops** — activated at profit threshold
- **Guardian protection** — loss limits, staleness checks

The `ai-trader` prefix in the signal tag (`ai-trader-manual`) matches the exit config automatically.

## Setting Manual SL (Breakeven Protection)

After opening a trade, you can move SL to breakeven to make it risk-free:

```bash
python3 -c "
import sys; sys.path.insert(0, '/root/.hermes/scripts')
import psycopg2
from _secrets import BRAIN_DB_DICT
conn = psycopg2.connect(**BRAIN_DB_DICT)
cur = conn.cursor()
cur.execute('UPDATE trades SET stop_loss = %s WHERE id = %s AND status = %s', (NEW_SL, TRADE_ID, 'open'))
conn.commit()
conn.close()
print('SL moved to', NEW_SL)
"
```

**Manual SL is protected** — the RR engine will NOT overwrite it because:
1. **CAS write** — TRAIL_SL only updates if SL hasn't changed since read
2. **Breakeven guard** — engine won't trail past breakeven (SL >= entry for LONG)
3. **entry_price=0 check** — skips trail if entry price is invalid
4. **Status check** — won't update closed trades

**When to set manual SL:**
- Trade is in profit and you want to make it risk-free
- You have a specific level in mind (support/resistance)
- You want to override the engine's SL for any reason

**The engine respects your SL** but will still trail it UPWARD (tighter) as price moves in your favor.

## Verification

After opening, verify the trade:
```bash
# Check PostgreSQL
python3 -c "
import sys; sys.path.insert(0, '/root/.hermes/scripts')
import psycopg2
conn = psycopg2.connect('host=/var/run/postgresql dbname=brain user=postgres')
cur = conn.cursor()
cur.execute('SELECT id, token, direction, entry_price, signal, status FROM trades WHERE token=\"COIN\" AND status=\"open\" ORDER BY id DESC LIMIT 1')
for row in cur.fetchall():
    print(f'#{row[0]} {row[1]} {row[2]} entry={row[3]} signal={row[4]} status={row[5]}')
conn.close()
"
```

## Safety Notes

- **This bypasses signal gates** — the trade will open even if RSI, RR engine, or other filters would normally block it
- **Exit management still applies** — the trade will be managed by rr_engine after opening
- **Use appropriate position sizing** — manual trades should be same size as signal trades ($11-20 USDT)
- **Log the reason** — include why you're overriding in the `--signal` or notes

## Related Skills

- `signal-lab` — for testing signal logic
- `signal-backtest` — for backtesting before manual entry
- `trade-analysis` — for analyzing trade outcomes
