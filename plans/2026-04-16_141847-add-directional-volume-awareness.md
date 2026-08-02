# Plan: Directional Volume Corroboration

## Goal
Make volume signal-aware — confirm LONG signals with buy-volume, SHORT signals with sell-volume.
Reject or de-weight signals where volume flows in the wrong direction (price rising on heavy sell-volume = distribution = bad for longs).

---

## Core Insight

For any candle, we can infer dominant direction from the close-vs-open relationship:

| Candle Color | Close vs Open | Interpretation | Valid for |
|---|---|---|---|
| Green (close > open) | Bullish | Buy-volume dominant | LONG confirmation |
| Red (close < open) | Bearish | Sell-volume dominant | SHORT confirmation |
| Doji (close ≈ open) | Neutral | Mixed / indecision | Neither |

Then a simple **directional volume** score:

```
directional_vol = volume × sign(close - open)   # positive = buy-vol, negative = sell-vol
```

Or for more precision, use the body size as a weighting factor:

```
buy_volume_approx  = volume × max(0, (close - open) / (high - low))   # 0 if red candle
sell_volume_approx = volume × max(0, (open - close) / (high - low))    # 0 if green candle
```

---

## Proposed Algorithm: `get_directional_volume_ratio(token, direction, lookback=20)`

```
1. Fetch last `lookback` 1m candles from Binance
2. For each candle:
     body = close - open
     if body > 0: buy_vol += volume
     else:        sell_vol += volume
3. avg_buy_vol  = mean of buy_vols across lookback-1 historical candles
   avg_sell_vol = mean of sell_vols across lookback-1 historical candles
4. current_buy_vol  = buy_vol from most recent candle
   current_sell_vol = sell_vol from most recent candle
5. For LONG:  ratio = current_buy_vol  / avg_buy_vol
   For SHORT: ratio = current_sell_vol / avg_sell_vol
6. Return ratio + direction confirmation
```

**Interpretation:**

| Ratio | Meaning | Action |
|---|---|---|
| > 2.0x | Strong directional volume surge | +15 confidence |
| 1.5x–2.0x | Moderate surge | +10 confidence |
| 0.8x–1.5x | Normal | +0 (neutral) |
| < 0.5x | Quiet / weak | -5 confidence |
| BUY vol collapsing on a LONG signal | Distribution | -15 or skip |

---

## Implementation: New File `volume_filter.py`

```python
# volume_filter.py
import requests

BINANCE_1M = "https://api.binance.com/api/v3/klines"

def get_directional_vol(token: str, direction: str, lookback: int = 20) -> dict:
    """
    Returns directional volume analysis for token.

    direction: 'LONG' or 'SHORT'
    Returns: {
        'buy_ratio': float,   # current buy-vol / avg buy-vol
        'sell_ratio': float,  # current sell-vol / avg sell-vol
        'confirm': str,       # 'strong', 'moderate', 'neutral', 'weak', 'contrarian'
        'delta': int,         # confidence delta (+15, +10, 0, -5, -15)
    }
    """
    url = f"{BINANCE_1M}?symbol={token}USDT&interval=1m&limit={lookback + 1}"
    resp = requests.get(url, timeout=5)
    candles = resp.json()

    current = candles[-1]   # most recent (index -1 = oldest if sorted asc)
    history = candles[:-1]  # lookback excludes current

    def _directional_vol(candles_list):
        buy_vols, sell_vols = [], []
        for c in candles_list:
            vol  = float(c[5])
            open_, close_ = float(c[1]), float(c[4])
            body = close_ - open_
            if body > 0:
                buy_vols.append(vol)
            elif body < 0:
                sell_vols.append(vol)
        return buy_vols, sell_vols

    curr_buy, curr_sell = _directional_vol([current])
    curr_buy  = curr_buy[0]  if curr_buy  else 0.0
    curr_sell = curr_sell[0] if curr_sell else 0.0

    all_buy, all_sell = _directional_vol(history)
    avg_buy  = sum(all_buy)  / len(all_buy)  if all_buy  else 1.0
    avg_sell = sum(all_sell) / len(all_sell) if all_sell else 1.0

    buy_ratio  = curr_buy  / avg_buy
    sell_ratio = curr_sell / avg_sell

    if direction == 'LONG':
        ratio    = buy_ratio
        opp_ratio = sell_ratio
        if buy_ratio > 2.0 and sell_ratio < 0.5:
            confirm, delta = 'strong',    +15
        elif buy_ratio > 1.5:
            confirm, delta = 'moderate',  +10
        elif buy_ratio < 0.5:
            confirm, delta = 'weak',       -5
        elif sell_ratio > 2.0:
            confirm, delta = 'contrarian', -15  # heavy sell-vol while expecting LONG
        else:
            confirm, delta = 'neutral',    0
    else:  # SHORT
        ratio    = sell_ratio
        opp_ratio = buy_ratio
        if sell_ratio > 2.0 and buy_ratio < 0.5:
            confirm, delta = 'strong',     +15
        elif sell_ratio > 1.5:
            confirm, delta = 'moderate',   +10
        elif sell_ratio < 0.5:
            confirm, delta = 'weak',        -5
        elif buy_ratio > 2.0:
            confirm, delta = 'contrarian',  -15  # heavy buy-vol while expecting SHORT
        else:
            confirm, delta = 'neutral',     0

    return {
        'buy_ratio':  round(buy_ratio,  2),
        'sell_ratio': round(sell_ratio, 2),
        'confirm': confirm,
        'delta': delta,
        'curr_buy_vol':  round(curr_buy,  4),
        'curr_sell_vol': round(curr_sell, 4),
        'avg_buy_vol':   round(avg_buy,   4),
        'avg_sell_vol':  round(avg_sell,  4),
    }
```

---

## Integration Points

### Option 1: In `signal_schema.py` `add_signal()` — before DB insert
Most surgical. Add directional volume check for every signal at entry:

```python
# In add_signal(), after SOURCE_KILL_SWITCH check, before DB insert:
if delta != 'neutral':  # only adjust, don't veto
    confidence = max(1, confidence + delta)
```

**Problem:** This adds a Binance API call to every signal, on every pipeline cycle. If 50 signals fire per cycle, that's 50 Binance calls. Manageable but not free.

**Better:** Only check on the FIRST signal for a token+direction (not on every re-confirmation).

### Option 2: In `macd_rules.py` — when generating the signal
Can incorporate volume direction into the signal's base confidence before it even reaches `add_signal()`. More natural integration — signal generation already has token+direction context.

### Option 3: In `ai_decider.py` — last gate before trade execution
Most expensive (uses AI decision) but highest value — AI can weigh volume against other factors.

**Recommendation:** Option 2 + Option 1 hybrid. Check volume in macd_rules when generating. `add_signal()` in signal_schema as a safety net.

---

## Step-by-Step Plan

1. **Create `/root/.hermes/scripts/volume_filter.py`** with `get_directional_vol(token, direction, lookback=20)` function
2. **Add to `hermes_constants.py`**:
   - `VOLUME_CONFIRM_THRESHOLD = 1.5` (moderate)
   - `VOLUME_SURGE_THRESHOLD = 2.0` (strong)
   - `VOLUME_CONTRARIAN_THRESHOLD = 2.0` (opposite direction heavy = skip)
   - `VOLUME_LOOKBACK = 20`
3. **Wire into `macd_rules.py`**: call `get_directional_vol()` in `get_macd_signal()` or equivalent, add `volume_delta` to confidence before returning signal
4. **Add safety net in `signal_schema.py`**: `add_signal()` calls `get_directional_vol()` as a fallback (even if macd_rules didn't call it)
5. **Test**: Backtest last 100 signals, compare volume-confirmed vs non-confirmed outcomes
6. **Tune thresholds**: Start conservative (2.0x surge = +10, contrarian = skip), adjust based on backtest results

---

## Files to Change

| File | Change |
|------|--------|
| **NEW**: `/root/.hermes/scripts/volume_filter.py` | Directional volume functions |
| `/root/.hermes/scripts/hermes_constants.py` | Add volume thresholds |
| `/root/.hermes/scripts/macd_rules.py` | Call `get_directional_vol()` in signal generation |
| `/root/.hermes/scripts/signal_schema.py` | Safety-net volume check in `add_signal()` |

---

## Key Distinction from Non-Directional

| Non-Directional | Directional (this plan) |
|---|---|
| volume > 2x avg | direction-aware: buy-vol > 2x avg AND sell-vol < 0.5x avg |
| Confirms momentum exists | Confirms momentum has **fuel** in the right direction |
| Can be fooled by distribution days | Rejects distribution (price up + heavy sell-vol = trap) |

---

## Risk: Binance ≠ Hyperliquid

Binance is more liquid than HL perpetuals. A volume surge on Binance may not mean the same on HL. Mitigation:
- Use as a **confidence adjuster** (-15 to +15), not a hard kill switch
- If Binance shows strong directional volume and HL doesn't confirm, that's a red flag worth noting
- Backtest before production to see if it adds alpha or noise
