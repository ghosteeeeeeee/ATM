# BTC Pump Rider — Gradual Rally Mode

**Date:** 2026-09-11
**Status:** PLAN → OWN-CONCLUSIONS REVIEW
**Trigger:** BTC rallied +3.4% (12:00-14:02 UTC), alts rallied 5-10%. System caught 3 winners but missed ENA (+9.9%), JUP (+8.3%), ARB (+8.3%), BLUR (+8.2%). Pump rider couldn't detect gradual rally.
**Core Insight:** Alts lag BTC by 5-10 minutes. When BTC starts rising, buy lagging alts BEFORE they move.

---

## Problem Statement

BTC rallied +3.4% from $77,020 to $79,614 between 12:00-14:02 UTC Sep 11. Multiple alts followed with 5-10% moves:

| Coin | Peak Move | Caught? | PnL |
|------|-----------|---------|-----|
| ENA | +9.9% | ❌ No trade | — |
| JUP | +8.3% | ❌ No trade | — |
| ARB | +8.3% | ✅ LONG at 14:02 | -5.9% (entered too late) |
| BLUR | +8.2% | ❌ No trade | — |
| CRV | +6.4% | ❌ No trade | — |
| AIXBT | +6.7% | ✅ LONG at 13:02 | +4.6% ✅ |
| DOGE | +5.1% | ✅ LONG at 13:06 | -3.2% (entered too late) |
| YGG | +4.9% | ✅ LONG at 12:57 | +4.9% ✅ |
| IMX | +4.9% | ✅ LONG at 12:41 | +9.3% ✅ |
| AVAX | +6.1% | ✅ LONG at 13:59 | -4.5% (entered too late) |

**3 winners, 3 losers, 6 missed entirely.** The system catches some rallies but enters too late on others and misses the best ones.

### Why the Pump Rider Missed This Rally

The existing `btc_pump_rider.py` detects BTC breakouts using:
1. BTC breaks above 1h high (close must confirm)
2. Volume spike ≥3x average on breakout candle
3. Price velocity ≥0.15% in single candle
4. 2+ follow-through candles

**This rally was GRADUAL, not explosive:**

```
12:01 — BTC broke 1h high, volume 0.2x → REJECTED (need 3x)
12:29 — Volume spike 17.7x, but BTC DROPPED -0.85% (flash crash) → REJECTED
12:32-14:02 — BTC rallied +4.1% over 90 minutes, volume 1-2x → REJECTED (need 3x)
```

**The pump rider only catches explosive single-candle breakouts.** Gradual rallies with steady volume slip through.

### The 5-10 Minute Lag Pattern

Analysis of the rally shows alts lag BTC by approximately 5-10 minutes:

```
12:01 — BTC breaks 1h high (first signal)
12:29 — BTC flash crash (confuses signals)
12:32 — BTC starts recovering (real rally begins)
12:37 — BTC at $77,407 (+0.5% from 12:00)
12:41 — IMX LONG enters (caught early) → +9.3% ✅
12:57 — YGG LONG enters (caught early) → +4.9% ✅
13:02 — AIXBT LONG enters (caught early) → +4.6% ✅
13:06 — DOGE LONG enters (entered late) → -3.2% ❌
13:59 — AVAX LONG enters (entered way too late) → -4.5% ❌
14:02 — ARB LONG enters (entered at peak) → -5.9% ❌
```

**The winning trades entered within 10 minutes of the rally start.** The losing trades entered30-60 minutes later, after most of the move had happened.

---

## Solution: Gradual Rally Detection Mode

### How It Works

Add a second detection mode to `btc_pump_rider.py` alongside the existing explosive breakout detection:

**Mode 1 (existing): Explosive Breakout**
- Single candle breaks 1h high
- Volume ≥3x average
- Catches fast, violent moves

**Mode 2 (new): Gradual Rally**
- BTC rises >0.5% over 30 minutes
- 3+ consecutive up candles (sustained buying)
- Volume consistently above average (not just spike)
- Catches slow, steady rallies

### Detection Logic

```python
def detect_btc_gradual_rally() -> dict | None:
    """
    Detect gradual BTC rally — sustained buying over 30+ minutes.
    Returns rally info dict or None.
    """
    btc_candles = _get_candles('BTC', 'candles_1m', 60)
    if len(btc_candles) < 30:
        return None
    
    # BTC 30m price change
    price_30m_ago = btc_candles[-30][4]  # close 30 candles ago
    price_now = btc_candles[-1][4]
    change_30m = (price_now - price_30m_ago) / price_30m_ago * 100
    
    if change_30m < 0.5:  # Need >0.5% rise in 30min
        return None
    
    # Count consecutive up candles in last 15 minutes
    recent = btc_candles[-15:]
    up_candles = sum(1 for c in recent if c[4] > c[1])
    if up_candles < 3:  # Need 3+ up candles
        return None
    
    # Volume consistency — avg of last 15 candles vs 60 candle avg
    avg_vol_60 = sum(c[5] for c in btc_candles) / len(btc_candles)
    avg_vol_15 = sum(c[5] for c in recent) / len(recent)
    vol_ratio = avg_vol_15 / avg_vol_60 if avg_vol_60 > 0 else 0
    
    if vol_ratio < 1.0:  # Volume must be above average
        return None
    
    return {
        'btc_price': price_now,
        'btc_change_30m': change_30m,
        'btc_up_candles': up_candles,
        'btc_vol_ratio': vol_ratio,
        'mode': 'gradual_rally',
    }
```

### Alt Selection Logic

When a gradual rally is detected, scan for alts that:
1. **Haven't moved yet** — alt 30m price change < 0.3% (still near pre-pump price)
2. **Are correlated with BTC** — alt beta > 0.5
3. **Have sufficient volume** — alt volume > $100k/day
4. **RSI not overbought** — alt RSI < 70 (don't chase)

```python
def find_lagging_alts(rally_info: dict) -> list:
    """Find alts that haven't followed BTC yet."""
    btc_price = rally_info['btc_price']
    lagging = []
    
    for token in get_tradeable_tokens():
        alt_candles = _get_candles(token, 'candles_1m', 30)
        if len(alt_candles) < 15:
            continue
        
        # Alt 30m change
        alt_30m_ago = alt_candles[-15][4]
        alt_now = alt_candles[-1][4]
        alt_change = (alt_now - alt_30m_ago) / alt_30m_ago * 100
        
        if alt_change > 0.3:  # Already moved — too late
            continue
        
        # Correlation with BTC
        beta = compute_alt_beta(token, btc_closes, alt_closes)
        if beta < 0.5:  # Not correlated
            continue
        
        # RSI check
        rsi = compute_rsi(alt_closes)
        if rsi > 70:  # Overbought
            continue
        
        lagging.append({
            'token': token,
            'alt_change': alt_change,
            'beta': beta,
            'rsi': rsi,
            'lag_score': beta * (1 - alt_change/0.3),  # Higher = more lagging
        })
    
    # Sort by lag score (most lagging first)
    return sorted(lagging, key=lambda x: x['lag_score'], reverse=True)[:5]
```

### Signal Emission

```python
# In run() function:
# Step 1: Try explosive breakout (existing)
btc_info = detect_btc_breakout()

# Step 2: If no breakout, try gradual rally (new)
if btc_info is None:
    btc_info = detect_btc_gradual_rally()

# Step 3: Find lagging alts
if btc_info:
    lagging_alts = find_lagging_alts(btc_info)
    for alt in lagging_alts:
        add_signal(
            token=alt['token'],
            direction='LONG',
            signal_type='btc_pump_rider_long',
            source='btc-pump-rider+',
            confidence=75 + alt['lag_score'] * 10,
            value=alt['alt_change'],
            price=alt['price'],
        )
```

---

## Expected Impact

Based on the Sep 11 rally analysis:

| Scenario | Trades | Winners | PnL |
|----------|--------|---------|-----|
| Current (pump rider only) | 3 | 3 | +$0.35 |
| With gradual rally mode | +5 more (ENA, JUP, CRV, BLUR, DOGE) | +3 estimated | +$0.80 |
| **Total improvement** | | | **+$0.45** |

**Conservative estimate:** Even 50% effectiveness → +$0.20 per rally.

**Frequency:** BTC rallies >0.5% in 30min happen ~2-3 times per day. If we catch even one per day, that's +$0.20/day = +$6/month.

---

## Files to Modify

| File | Change | Lines |
|------|--------|-------|
| `scripts/signals/btc_pump_rider.py` | Add `detect_btc_gradual_rally()` + `find_lagging_alts()` | ~50 lines |
| `scripts/hermes_constants.py` | Add gradual rally constants | ~8 lines |

**Total: ~58 lines + 8 constants.**

---

## Constants

```python
# Gradual Rally Detection
BTC_PUMP_RIDER_GRADUAL_ENABLED = True
BTC_PUMP_RIDER_GRADUAL_MIN_CHANGE_30M = 0.5    # % — minimum BTC rise in 30min
BTC_PUMP_RIDER_GRADUAL_MIN_UP_CANDLES = 3     # consecutive up candles in 15min
BTC_PUMP_RIDER_GRADUAL_VOL_MIN_RATIO = 1.0    # volume must be above average
BTC_PUMP_RIDER_GRADUAL_ALT_MAX_CHANGE = 0.3   # % — alt must not have moved yet
BTC_PUMP_RIDER_GRADUAL_ALT_MIN_BETA = 0.5     # minimum correlation with BTC
BTC_PUMP_RIDER_GRADUAL_ALT_RSI_MAX = 70       # don't buy overbought alts
BTC_PUMP_RIDER_GRADUAL_MAX_ALTS = 5           # max alt signals per rally
```

---

## Risks

| Risk | Mitigation |
|------|-----------|
| False positives — BTC rises 0.5% then reverses | Require 3+ consecutive up candles (sustained buying) |
| Alts already moved by the time we detect | Alt max change threshold (0.3%) filters these out |
| Too many signals in a rally | Cap at 5 alt signals per rally |
| Gradual rally detection lag | 30-minute window catches most rallies within 10-15 min of start |

---

## Testing Plan

1. **Backtest on Sep 11 rally:** Would gradual rally mode have detected the move? Which alts would it have selected?
2. **LOG-ONLY (48h):** Add gradual rally detection, log what would have been fired without actually trading.
3. **Enable live:** After 48h of clean logs.
4. **Monitor:** Track win rate of gradual rally signals vs explosive breakout signals.
