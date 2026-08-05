# SL Tightness Analysis — 2026-05-07

## Source Data
- trades.json: 200 closed trades, 68 wins (34% WR), $30.95 total PnL
- All 126 `atr_sl_hit` losses analyzed using 1m candles from `candles.db`
- 71/126 RIGHT_SIG (price moved in signal direction), 55/126 WRONG_DIR

## Finding: SL is too tight, cutting right-signal winners

| Metric | Value |
|--------|-------|
| Avg worst adverse excursion (right-sig losses) | **0.334%** |
| Avg max favorable move (right-sig losses) | **0.107%** |
| Would survive 0.50% SL | 60/71 (85%) |
| Would survive 0.75% SL | 68/71 (96%) |
| Would survive 1.00% SL | 70/71 (99%) |

The avg right-sig worst move (0.334%) is 3× larger than avg max favorable (0.107%).
Price spikes in our favor by +0.10%, then whips back 0.33% and hits the tight SL.

## Recommendation

1. **Widen SL floor from 0.20% → 0.50%** — gives 85% survival on right-sig trades
2. **Trailing SL** — activate at +0.15% profit (1.5× avg max_fav), lock in winners before spike-reverse
3. Current ATR_SL_MIN_ACCEL=0.20% is too tight — most ATR-based k multipliers land around 0.25-0.40%

## SL survival table (right-signal losses only)

| SL distance | Trades saved | % saved |
|-------------|-------------|---------|
| 0.20% (current) | 0/71 | 0% |
| 0.50% | 60/71 | 85% |
| 0.75% | 68/71 | 96% |
| 1.00% | 70/71 | 99% |

## Analysis query (run against candles.db)

```python
import sqlite3
from datetime import datetime
cconn = sqlite3.connect('/root/.hermes/data/candles.db')
cc = cconn.cursor()
cc.execute("SELECT ts, close FROM candles_1m WHERE token=? AND ts>=? AND ts<=? ORDER BY ts",
           (coin, entry_ts - 60, exit_ts + 300))
bars = cc.fetchall()
prices = [b[1] for b in bars]
# direction-aware worst/favorable:
if direction == 'SHORT':
    worst = max(prices[1:-1])   # highest high (bad for SHORT)
    max_fav = (entry - min(prices[1:-1])) / entry * 100
    worst_move = (worst - entry) / entry * 100
else:
    worst = min(prices[1:-1])   # lowest low (bad for LONG)
    max_fav = (max(prices[1:-1]) - entry) / entry * 100
    worst_move = (entry - worst) / entry * 100
```

## Key files
- `position_manager.py` `_atr_sl_k_scaled()` — ATR adaptive SL computation
- `hl-sync-guardian.py` Step 4 — ATR SL/TP breach monitoring
- `/var/www/hermes/data/candles.db` — 1m close prices for post-exit analysis
- `/var/www/hermes/data/trades.json` — closed trade record (check `close_reason`, `pnl_pct`)
