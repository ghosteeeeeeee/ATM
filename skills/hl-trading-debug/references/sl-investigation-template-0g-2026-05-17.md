# 0G SHORT SL Investigation — 2026-05-17

## The Problem

0G SHORT: entry=$0.49609, current=$0.49558, actual SL=$0.503663 (+1.53% from entry)
ATR (15m): $0.00123 = **0.248%** of entry price — extremely low volatility

## Expected vs Actual SL

| Source | SL | Distance from Entry |
|--------|----|---------------------|
| Expected (ATR math with MIN_SL_PCT=0.70% floor) | $0.499-$0.500 | +0.60-0.70% |
| Actual | $0.503663 | **+1.53%** |
| Gap | +0.4-0.5% | unexplained |

## Key Finding: ATR-Based SL Is Sensitive to ATR Source

For ATR%=0.248% (very low volatility):
- k=1.0 (NORMAL tier, below 1% threshold)
- sl_pct = k × ATR% = 0.248% — below MIN_SL_PCT floors
- Established trade floor: **0.70%** → expected SL = $0.499-$0.500

The actual SL ($0.503663) implies **1.5%+ SL distance** — this is only possible if:
1. Entry-time ATR was significantly higher (e.g., 1h candles, older period)
2. SL was set by a different code path (pump-mode fixed %, brain.py Step 5, etc.)
3. Position_manager trailing hasn't corrected it

## Investigation Steps Used

```python
# 1. Get current ATR for token
from atr_cache import get_atr
atr = get_atr('0G', interval='15m')  # primary
atr_1h = get_atr('0G', interval='1h')  # fallback

# 2. Check what tpsl_utils computes with current data
from tpsl_utils import compute_atr_sl_tp
result = compute_atr_sl_tp(
    token='0G', direction='SHORT',
    entry_price=0.49609, current_price=0.49558,
    highest_price=0.0, lowest_price=0.0,  # no peak/low stored
    pnl_pct=0.001, current_sl=0.0, current_tp=0.0,
    momentum_stats=None, speed_percentile=50.0
)
print(result['new_sl'], result['eff_sl_pct'], result['k'])

# 3. Check trades.json for current SL
import json
with open('/var/www/hermes/data/trades.json') as f:
    data = json.load(f)
for t in data['open']:
    if t['coin'] == '0G':
        print(t['sl'], t['tp'], t['opened'])

# 4. Check ATR cache file for stale values
cat /root/.hermes/data/atr_cache.json | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('0G',{}))"

# 5. Check what anchor price was used in trailing
# Look for TPSL log entries in pipeline.log:
grep "0G.*SHORT" /var/www/hermes/data/pipeline.log | tail -20
```

## Architecture Note: SL Set at Entry vs Trailing Updates

- `tpsl_utils.compute_atr_sl_tp()` is the **sole authority** for ATR-based SL/TP
- SL is computed fresh each cycle by `position_manager._collect_atr_updates()`
- But if `current_sl > 0`, the trailing gate only tightens (SHORT: new_sl < current_sl accepted)
- If initial SL was set too wide by a different mechanism (pump-mode, brain.py Step 5), trailing can't tighten it back — only a force-update can

## The Real Fix for This Trade

Force recompute via `force_atr_update.py` or wait for guardian's next cycle to apply ATR update. The SL should be $0.499-$0.500 not $0.503663.

## Lesson

When investigating unexpected SL/TP values:
1. Compute expected SL from current ATR + floors — this is your baseline
2. If actual ≠ expected, either: (a) initial SL was set by different mechanism, or (b) trailing hasn't run yet
3. Check ATR cache for staleness — old ATR gives wrong SL
4. Check if `current_sl > 0` means trailing gate is blocking tighten
5. For pump-mode trades: brain.py Step 5 may have set SL before position_manager could override