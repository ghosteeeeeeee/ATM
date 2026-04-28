---
name: zscore-pump-backtest
description: Correct backtest methodology for zscore_pump_hunter — critical candle timeframe matching with live system. Catches the lookback/TF mismatch bug.
triggers:
  - zscore pump backtest
  - chandelier ATR backtest
  - zscore_pump_hunter backtest
  - testing ATR stops on zscore
---

# ZScore Pump Backtest — Methodology

## Context
Backtesting Chandelier ATR for zscore_pump_hunter.py requires matching the LIVE system's candle timeframe. A critical bug was discovered mid-analysis: the backtest was running on 1h candles with lookback values that meant something completely different than in live trading.

## The Critical Bug: Timeframe/Lookback Mismatch

**Live system** (`zscore_pump_hunter.py`):
- Uses `candles_1m` (1-minute candles) for price data
- Lookback=10 means 10 **minutes** of price history
- Lookback=58 means 58 **minutes**

**Wrong approach** (what was initially tested):
- Running backtest on 1h candles
- Lookback=10 interpreted as 10 **hours** — 60x longer
- This produced "200 hour average holds" and +178% net returns that were completely unrealistic

**Correct approach**:
- Backtest must run on the SAME candle timeframe the live system uses
- If live uses 1m candles → backtest on 1m candles
- The lookback number stays the same; the TIME it represents changes based on candle TF

## Confirmed Exit Strategy (2026-04-20)

ZS cross-0 with 20% ROC deceleration dimming — `cross_zero_d20`:
- **+1,714% net, 28.6% WR, 1.64 PF** across 156 tokens
- Exit when ZS crosses 0 OR ROC has dimmed 20% from peak (whichever comes first)
- T approved: "zscore crosses 0 in 30 candles might be ok for now"
- This is the IMPLEMENTED exit in `check_and_close_positions()`

### Exit Strategy Comparison (156 tokens, 1m candles)

| Strategy | Net% | WinRate | PF | AvgBars |
|----------|------|---------|-----|---------|
| **cross_zero_d20** | **+1,714** | 28.6% | **1.64** | varies |
| cross_zero_d30 | +1,660 | 28.7% | 1.63 | varies |
| cross_zero (plain ZS→0) | +874 | 27.8% | 1.45 | 13 bars |
| accel_exit_N3 (ROC<0 only) | -897 | 31.0% | 0.96 | — |
| accel_exit_N5 (ROC<0 only) | -811 | 32.8% | 1.03 | — |
| roc_dim_20 (ROC dim only) | -4 | 31.9% | 0.29 | — |

**Key finding**: Acceleration-only exits (ROC<0, ZS still same direction) all lose money badly. The market doesn't respect "ZS still positive but momentum turning" as a valid exit signal. ZS crossing 0 is the actual edge. The 20% ROC dimmer just helps exit earlier before full mean-reversion completes.

### Top Performer Tokens by cross_zero (156-token sweep)
ZEC +796%, ME +86%, EIGEN +86%, KAITO +85%, MEME +85%, BLUR +84%

## Pre-existing Bug Found by ai-engineer (2026-04-20)

`mirror_open()` was being called with WRONG keyword arguments in `execute_zscore_trade()`:
```python
# WRONG (pre-existing bug):
res = mirror_open(coin=token.upper(), is_long=(direction=='LONG'), sz=size, tp_pct=2.0, sl_pct=3.0)
# Actual signature: mirror_open(token, direction, entry_price, leverage=None)
```
This meant **no live trades EVER fired from zscore_pump_hunter.py** — the call would crash on TypeError before reaching the exchange.

**Fixed to**:
```python
res = mirror_open(token=token.upper(), direction=direction, entry_price=entry_price)
```

## Previous Findings ( Chandler ATR — superseded by ZS cross-0 exit)

On 1m with short lookbacks (10-58 bars):
- Fixed SL hits 0% — price reverses before ever touching it
- Z-score mean-reversion IS the actual exit (now confirmed + implemented)
- Chandelier ATR provides no benefit over zs_only on 1m

## T's Philosophy
- "first candle against us we're out, book profit fast"
- "established momentum, will continue to ride"
- "zscore crosses 0 in 30 candles might be ok for now" → APPROVED the cross_zero_d20 exit

## Going Live: What Was Broken and Fixed (2026-04-20)

### 1. mirror_open Wrong Args (live trades never fired)
`execute_zscore_trade()` called `mirror_open` with wrong kwargs — no live trades ever executed.
```python
# WRONG:
res = mirror_open(coin=token.upper(), is_long=(direction=='LONG'), sz=size, tp_pct=2.0, sl_pct=3.0)
# CORRECT (signature: mirror_open(token, direction, entry_price, leverage=None)):
res = mirror_open(token=token.upper(), direction=direction, entry_price=entry_price)
```

### 2. Guardian/Position Manager Exclusion Pattern
When adding a self-managed signal type, you MUST exclude it from guardian and position_manager SQL queries. The guardian (`hl-sync-guardian.py`) and `position_manager.py` both query the brain DB and skip `pump_hunter` signals. Add new signals to both files:

```sql
-- pattern: use NOT IN, not != (allows adding multiple signals cleanly)
WHERE signal NOT IN ('pump_hunter', 'zscore_pump')
```

Files with exclusions (all 3 queries in each):
- `/root/.hermes/scripts/hl-sync-guardian.py` — lines 589, 616, 1032
- `/root/.hermes/scripts/position_manager.py` — lines 278, 302, 326

### 3. Dry-Run Tracking Bug
`execute_zscore_trade()` returns `{'success': True, 'dry': True}` in dry mode. The scan loop was checking `if result.get('success')` — this fires in dry too, adding phantom positions to the JSON every minute via the systemd timer.
```python
# WRONG:
if result.get('success'):
    add_zs_position(...)
# CORRECT:
if result.get('success') and not result.get('dry'):
    add_zs_position(...)
```

### 4. TP/SL Monitoring — No HL Orders Were Ever Sent
`mirror_open` places market orders only. There is no TP/SL attached. The old `check_and_close_positions` looked for positions "gone from HL" — but they never auto-close since no TP/SL was ever placed. Fixed by monitoring price vs stored `stop_price`/`tp_price` directly.

```python
def check_and_close_positions():
    # 1. ZS cross-0 exit (always runs)
    curr_z = _get_zscore_at_bar(token, lookback)
    should_exit = (direction == 'LONG' and curr_z <= 0) or (direction == 'SHORT' and curr_z >= 0)

    # 2. Price-based SL/TP (always runs)
    tp_hit = (direction == 'LONG' and curr_price >= tp_price) or \
             (direction == 'SHORT' and curr_price <= tp_price)
    sl_hit = (direction == 'LONG' and curr_price <= stop_price) or \
             (direction == 'SHORT' and curr_price >= stop_price)
```

### 5. Positions File Location
Two different files:
- `/var/www/hermes/data/pump_hunter_positions.json` — **zscore_pump_hunter writes here** (4KB, live)
- `/root/.hermes/data/pump_hunter_positions.json` — stale, wrong file

Use `--close` flag to clear: `python3 zscore_pump_hunter.py --close`

## Files
- `/tmp/chandelier_correct.py` — CORRECT backtest (matches live TF)
- `/tmp/chandelier_tf.py` — older version with TF mismatch
- `/root/.hermes/scripts/zscore_pump_hunter.py` — live system
- `/root/.hermes/scripts/hl-sync-guardian.py` — guardian (excludes pump_hunter/zscore_pump)
- `/root/.hermes/scripts/position_manager.py` — position manager (same exclusions)
- `/root/.hermes/data/candles.db` — has candles_1m, candles_15m, candles_1m
