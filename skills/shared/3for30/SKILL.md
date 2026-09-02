---
name: 3for30
description: Monitor open trades every 3 minutes for 30 minutes. Tracks PnL, SL/TP proximity, and v3 signal state. Use when user says "follow every 3 mins", "3for30", "monitor trades", or "track position".
---

# 3for30 — Trade Monitor (3min x 30min)

Monitor open trades every 3 minutes for 30 minutes (10 rounds). Tracks PnL, SL/TP proximity, and v3 signal health.

## Usage

When invoked, run this script in the background:

```python
import sys, os, sqlite3, time
from datetime import datetime
sys.path.insert(0, '/root/.hermes/scripts')
from paths import STATIC_DB
from signal_schema import get_all_latest_prices
from signals.accel_300_v3_long import _ema_series, _rsi, detect_accel_300_v3_long

# TRADES = list of open positions to track
# Each: {'token': 'X', 'entry': 0.0, 'sl': 0.0, 'tp': 0.0, 'size': 11.1, 'lev': 3}
```

## Output Format

```
--- Round N/10 (HH:MM:SS) ---
  TOKEN    STATUS   $PRICE    pnl=+X.XX% $+X.XX | SL X.XX% TP X.XX%
           gap=X.XX% rsi=X.X pull=X.XX reexp=X.XX move30=X.XX sig=YES/NO
```

## Status Codes

- `GREEN` — in profit
- `RED` — in loss
- `SL HIT` — stop loss triggered
- `TP HIT` — take profit triggered

## What to Watch For

1. **SL proximity** — if SL distance < 0.3%, trade is at risk
2. **RSI overbought** — RSI > 68 at peak = likely reversal
3. **Gap narrowing** — gap shrinking = momentum fading
4. **Reexp negative** — bounce failed, exit signal
5. **New signals** — check if v3 fires again on same token

## After 30 Minutes

Summarize:
- Final PnL for each trade
- Which filters worked / didn't work
- Any patterns for signal tuning
