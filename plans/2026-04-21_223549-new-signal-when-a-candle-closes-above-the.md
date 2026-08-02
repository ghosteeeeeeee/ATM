# Plan: MA300 + Candle-Confirmation Signal (EMA, signal_gen integration)

## Updated Design (T confirmed 2026-04-21)

- **MA type**: EMA(300)
- **Integration**: called/imported inside `signal_gen.py`
- **Order**: backtest FIRST, evaluate, then implement
- **Timeframe**: 1m candles from `candles.db`

---

## Signal Logic

**LONG** fires when:
1. Candle[i] closes above EMA(300)
2. Candle[i+1] opens AND closes above candle[i]'s body high (max of open, close)

**SHORT** fires when:
1. Candle[i] closes below EMA(300)
2. Candle[i+1] opens AND closes below candle[i]'s body low (min of open, close)

**Entry**: at candle[i+1] close price (non-repainting — both candles confirmed before entry)
**SL floor**: 0.75% | **TP floor**: 1.0%

Signal name: `ma300_candle` | Source tag: `ma300-confirm{N}` (N = bars since confirmation)

---

## Step 1 — Backtest FIRST

### `scripts/backtest_ma300_candle_confirm.py`

Backtester mirroring `backtest_ma_cross.py`:

```
- Load 1m candles for all tokens (min 3000 candles)
- EMA(300) warmup: need 300 candles before first valid candle[i]
- Signal fires at candle[i+1] close (after confirmation)
- Default: SL=0.75%, TP=1.0%
- Sweep SL/TP combos: (0.5,0.75), (0.75,1.0), (0.75,1.5), (1.0,1.5)
- Exit: TP / SL / reverse signal / end-of-data
- Report: win rate, avg P&L, signal count, per-token WR, top combos
```

**Run command**: `python3 scripts/backbacktest_ma300_candle_confirm.py --top 50`

Metrics to evaluate before implementing:
- Win rate > 50%?
- Total P&L positive?
- Per-token WR distribution (any tokens consistently good/bad?)
- Signal frequency (too sparse? too noisy?)

---

## Step 2 — Implement signal scanner

### `scripts/ma300_candle_confirm_signals.py`

Core detection. Key components:

**EMA calculation** — reuse `_ema()` and `_ema_series()` from `ma_cross_signals.py` (copy or import)

```python
# Constants
EMA300_PERIOD         = 300
MA300CANDLE_SIGNAL_TYPE = 'ma300_candle'
MA300CANDLE_SOURCE_PREFIX = 'ma300'
MA300CANDLE_LOOKBACK  = 350   # 300 warmup + 2 for detection + buffer
MA300CANDLE_COOLDOWN  = 15     # minutes between signals per token+direction
MA300CANDLE_MIN_CONF  = 50
MA300CANDLE_MAX_CONF  = 88
MA300CANDLE_BASE_CONF = 65

def detect_ma300_candle(token, candles, price) -> Optional[dict]:
    # candles: oldest-first from candles.db
    # price: current price (candles[-1]['close'])
    closes = [c['close'] for c in candles]
    ema300_series = _ema_series(closes, EMA300_PERIOD)

    # Valid from index 299 onward
    for i in range(EMA300_PERIOD - 1, len(candles) - 2):
        c_i     = candles[i]
        c_next  = candles[i + 1]

        ema_val = ema300_series[i]
        if ema_val is None:
            continue

        body_high_i = max(c_i['open'], c_i['close'])
        body_low_i  = min(c_i['open'], c_i['close'])

        # LONG
        if c_i['close'] > ema_val:
            if c_next['open'] > body_high_i and c_next['close'] > body_high_i:
                # compute confidence, bars_since, source
                ...

        # SHORT
        elif c_i['close'] < ema_val:
            if c_next['open'] < body_low_i and c_next['close'] < body_low_i:
                ...
```

**Confidence scoring:**
- Base: 65
- +10 if body_next > 1.5× body_i (explosive candle)
- +8 if |close_i - ema_val| / price > 1.5% (strong MA separation)
- Cap 88, floor 50

**Output dict:**
```python
{
    'direction':  'LONG' or 'SHORT',
    'confidence': int,
    'source':     'ma300-confirm{N}',
    'bars_since': int,
    'value':      float(confidence),
}
```

### `scripts/run_ma300_candle_confirm_signals.py`

Standalone runner (for manual testing / cron). Mirrors `run_ma_cross_signals.py`:
- Fetches latest prices from candles.db
- Filters blacklists, open positions, cooldowns
- Calls `scan_ma300_candle_signals(filtered)`
- Writes cooldowns via `signal_schema.record_cooldown_start()`

---

## Step 3 — Integrate into signal_gen.py

Add to `STEPS_EVERY_MIN` in `run_pipeline.py` or call directly from `signal_gen.py`:

**Option A** — call from `signal_gen.py` directly (recommended):
```python
# In signal_gen.py, after other scanners:
try:
    from ma300_candle_confirm_signals import scan_ma300_candle_signals
    prices = get_live_prices()  # reuse existing price fetch
    scan_ma300_candle_signals(prices)
except ImportError:
    pass
```

**Option B** — add `run_ma300_candle_confirm_signals` to `STEPS_EVERY_MIN` in `run_pipeline.py`.

TBD — confirm which approach with T.

---

## Step 4 — Add to hermes_constants.py

```python
MA300CANDLE_COOLDOWN_MINUTES = 15
MA300CANDLE_BLACKLIST = {}  # start empty
```

---

## Files to Create

1. `scripts/backtest_ma300_candle_confirm.py` — backtester (RUN FIRST)
2. `scripts/ma300_candle_confirm_signals.py` — core signal detector
3. `scripts/run_ma300_candle_confirm_signals.py` — standalone runner

## Files to Modify

4. `hermes_constants.py` — add MA300CANDLE constants
5. `signal_gen.py` or `run_pipeline.py` — add integration (TBD: A or B)

---

## Validation

1. `python3 scripts/backtest_ma300_candle_confirm.py --top 50` — evaluate win rate, P&L
2. `python3 scripts/run_ma300_candle_confirm_signals.py` — manual emit
3. Check `signals_hermes_runtime.db` for `signal_type='ma300_candle'`
4. Verify cooldown blocks duplicate signals
5. Verify appears in hot-set

---

## Open Questions for T

1. **Integration approach**: Call from `signal_gen.py` directly (A) or add to pipeline steps (B)?
2. **Any tokens to blacklist** specifically for this signal?
3. **Backtest SL/TP**: want to sweep more combos than listed above?
