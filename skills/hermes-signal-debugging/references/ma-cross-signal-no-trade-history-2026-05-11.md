# ma_cross Signal — Enabled but Zero Trade History (2026-05-11)

## Problem
ma_cross signal fires correctly (golden/death crosses detected), `MA_CROSS_ENABLED = True` in hermes_constants, `SIGNAL_SOURCE_BLACKLIST = {}` (empty), but **zero ma_cross trades ever executed** across all 33 archive files and live trades.json.

## Signal Logic (signals/ma_cross.py)
- 10 EMA crosses ABOVE 200 EMA → LONG (golden cross)
- 10 EMA crosses BELOW 200 EMA → SHORT (death cross)
- Confidence = 65 base + sep_bonus (up to +15) + recency_bonus (up to +10)
- Lookback: 250 candles (needs 210 for warmup)
- Cooldown: 15 min per token+direction
- Data source: price_history table in signals_hermes.db (1m candles, updated every minute)

## Execution Path (traced)
1. `signals_runner.py` (every 1 min) → `signals.__init__.py` → `run_all_signals()`
2. `signals/__init__.py:307` → module `ma_cross` → function `scan_ma_cross_signals()`
3. `scan_ma_cross_signals()` (ma_cross.py:226) → `add_signal()` via `signal_schema`
4. `signal_schema.add_signal()` (line 536) → checks `MA_CROSS_ENABLED` → if False, returns None

## Why No Trades?
Signal IS enabled and fires. The issue is likely:
- **Confidence too low** — base 65 needs co-signals to survive compactor
- **Compactor regime penalty** — NEUTRAL tokens get 0.5x score multiplier
- **Never survived compaction** — zero ma_cross signals ever entered hot-set
- Alternative: was previously blacklisted in SIGNAL_SOURCE_BLACKLIST (comment at hermes_constants.py:140 notes longs were "catastrophic")

## Live Crosses (2026-05-11 05:21 UTC)
```
TOTAL: 86 crosses | SHORTS: 17 | LONGS: 69

SHORT (death crosses):
  IO      conf=72 bars=3  sep=0.140%
  MEGA   conf=71 bars=4  sep=0.036%
  ATOM   conf=65 bars=39 sep=0.249%
  CRV    conf=65 bars=38 sep=0.322%
  DOGE   conf=65 bars=36 sep=0.077%
  INJ    conf=65 bars=47 sep=0.278%
  TRX    conf=65 bars=41 sep=0.037%
  XRP    conf=65 bars=35 sep=0.064%
```

## Debugging Checklist for "Signal Fires But Never Executes"
```python
# Step 1: Verify enabled flag
from hermes_constants import MA_CROSS_ENABLED
print(f"MA_CROSS_ENABLED: {MA_CROSS_ENABLED}")

# Step 2: Check blacklist
from hermes_constants import SIGNAL_SOURCE_BLACKLIST
print(f"SIGNAL_SOURCE_BLACKLIST: {SIGNAL_SOURCE_BLACKLIST}")

# Step 3: Verify signal reaches add_signal (run the scanner)
from signals.ma_cross import scan_ma_cross_signals, detect_ma_cross, _get_candles_1m
from signal_schema import get_all_latest_prices
prices = get_all_latest_prices()
candles = _get_candles_1m('ATOM', lookback=250)
sig = detect_ma_cross('ATOM', candles, prices['ATOM']['price'])

# Step 4: Check add_signal returned a signal ID (not None)
from signal_schema import add_signal
sid = add_signal(token='ATOM', direction='SHORT', signal_type='ma_cross',
                 source='ma-death39', confidence=65, value=65.0,
                 price=prices['ATOM']['price'])

# Step 5: Check if it survived into hotset.json
# (run the compaction and check hotset.json)

# Step 6: Check archive for any historical ma_cross trades
# (search all trades_archive_*.json for 'ma-' in source)
```

## Key Files
- `/root/.hermes/scripts/signals/ma_cross.py` — signal logic (lines 76-175 for detect, 226-275 for scan)
- `/root/.hermes/scripts/hermes_constants.py:389` — `MA_CROSS_ENABLED = True`
- `/root/.hermes/scripts/signal_schema.py:536` — Layer 2 kill-switch check
- `/root/.hermes/scripts/signals/__init__.py:97` — registry import, line 198 in SIGNAL_REGISTRY

## Conclusion
ma_cross is **operational, not disabled**. It fires correctly on 1m candles. Zero trade history means it was either (a) blocked before reaching hot-set, or (b) never survived compaction. The death cross SHORT signals (ATOM, CRV, DOGE, INJ, TRX, XRP etc.) are available for backtesting or paper trading if T wants to validate profitability.