---
name: fake-dump-short-signal
description: Detect "fake dump" short opportunities — RSI crashes from overbought to oversold, bounces, then real crash. Empirical analysis across 130+ coins, 179 big dumps.
tags: [short, rsi, volume-spike, fake-dump, mean-reversion, dump-pattern]
triggers:
  - fake dump short
  - dump pattern detection
  - big short opportunity
  - RSI crash bounce short
  - volume spike short
---

# Fake Dump Short Signal — Detection & Backtest

## Pattern Description

"Fake dump" = a sharp initial drop that looks like capitulation but is actually the WARNING shot, not the final move. Price stabilizes, bounces, then collapses for real.

**Textbook case: BOME Apr 19, 2026**
- 16:00-16:20: Parabolic pump +14%, RSI 84-91 (overbought), vol 63x avg
- 16:21-17:00: First "dump" — price -23%, RSI 84→15 (looks catastrophic)
- 17:00-17:05: Stabilizes at bottom, RSI recovers 39-48 (the BOUNCE)
- 17:05-17:10: REAL crash begins — -30% from peak
- Pattern complete in ~65 minutes

**ACE Apr 18, 2026** (same pattern, compressed):
- 05:34-07:07: Grinding down, RSI 7 (extreme), vol 4-20x
- 07:08-08:03: Brief bounce (RSI recovers), then -25% crash

## Signal Types

### TYPE A — Dead Cat Bounce Short (BOME pattern)
- Preceded by parabolic pump to RSI >80
- RSI CRASHES from >60 to <30 in <30 min (first "dump")
- Price stabilizes, RSI recovers to 35-65
- **Entry: SHORT when RSI bounces to 40-60 zone after fake dump**
- **Stop: RSI crosses back above 65, or first candle closes green**
- **TP: 1-2% (fast), SL: 0.5% max**

### TYPE B — Continuation Breakdown Short (most common: 128/179 cases)
- RSI already elevated (>50) at dump start — no fake dump, just breakdown
- Price below SMA20 confirmed
- Volume spike >10x avg
- **Entry: SHORT on vol spike + RSI >50 + price below SMA20**
- **Stop: RSI reclaims 50, or first candle reverses**
- **TP: 1-2%, SL: 0.5-0.75%**

## Empirical Findings (179 big dumps >15% in 1h, 30 days, 130+ coins)

| Signal | % of Dumps That Had It |
|--------|----------------------|
| Volume spike >5x avg | **100%** (universal) |
| Price below SMA20 | ~95% |
| RSI overbought (>70) at some point | ~35% |
| RSI deeply oversold (<30) at some point | ~60% |

**Key finding**: Volume spike is the ONLY universal precursor. RSI overbought is NOT required (most dumps happen from elevated RSI, not overbought).

## Volume Spike Detection (Universal — 100% of dumps)

```python
# From candles.db (1m candles), compute rolling 60-bar avg volume
avg_vol = np.mean(vols[-60:])
vol_ratio = current_vol / avg_vol

if vol_ratio > 10 and close < sma20:
    # VOLUME CONFIRMATION: price below SMA + vol spike
    # Direction depends on RSI zone:
    #   RSI > 60 → likely continuation dump, SHORT
    #   RSI < 40 → could be bounce, wait for RSI recovery entry
```

## Fake Dump Detection Algorithm

```python
def detect_fake_dump(closes, rsis, vols, lookback=60):
    """
    Detect fake dump pattern:
    1. RSI was >60 (overbought) 30 min ago
    2. RSI crashed to <30 in last 15 candles (the fake dump)
    3. RSI now recovering (35 < RSI < 65) — BOUNCE phase
    4. Volume elevated (>3x avg) during the crash
    
    Returns: signal_type ('fake_dump', 'breakdown', None)
    """
    if lookback < 45:
        return None
    
    rsi_then = rsi_at(closes, lookback - 30, lookback - 15)
    rsi_crash = np.min(rsi_at(closes, lookback - 15, lookback))
    rsi_now = rsi_at(closes, lookback - 5, lookback)
    
    vol_avg = np.mean(vols[-60:])
    vol_during_crash = np.max(vols[lookback-15:lookback])
    
    if rsi_then > 60 and rsi_crash < 30 and 35 <= rsi_now <= 65 and vol_during_crash > 3 * vol_avg:
        return 'fake_dump'
    elif rsi_now > 50 and vol_during_crash > 10 * vol_avg:
        return 'breakdown'
    return None
```

## Entry/Exit Rules (T's Philosophy)

From memory: T's philosophy is "first candle against us we're out, book profit fast"
- SL floor: 0.5% (never more than 0.75%)
- TP floor: 1% (never less than 0.75%, never more than 2%)
- Entry confirmation: wait for RSI bounce confirmation (don't fade the initial crash)
- Exit on first candle that closes against direction

## Related Findings

- RSI IN the signal HURTS performance (from rsi-backtest skill): WR drops 50%→39%, avg PnL goes negative
- z-score mean reversion (zscore_pump) is for bounces, not for fake dump shorts
- MA cross 8/50 SHORT: already works well for continuation breakdown shorts
- Volume spike detection as PRIMARY signal is what's missing from Hermes

## Post-Gap Entry SL Behavior (XRP Apr 27, 2026 — empirical)

When `gap-300-` fires on a gap-down entry, the ATR SL defaults to its floor (0.50%). This is often too tight.

**Case study: XRP SHORT, trade 7849**
- Entry: 1.3841 (gap-down, `gap-300-` signal)
- SL: 1.39102 (0.50% above entry — the ATR floor)
- TP: 1.37372 (0.75% below entry)
- Exit: 1.39185 at 15:35 EDT — **SL hit** (price bounced 0.57% after the gap-down dump)
- Duration: ~12 minutes
- Result: -0.56% loss

**What happened in the candles:**
```
15:15  High: 1.3977, Low: 1.3842, Close: 1.3893  ← GAP DUMP
15:20  High: 1.3921, Low: 1.3836, Close: 1.3847  ← Entry zone
15:25  High: 1.3868, Low: 1.3843, Close: 1.3868
15:30  High: 1.3909, Low: 1.3875, Close: 1.3903
15:35  High: 1.3919, Low: 1.3907, Close: 1.3911  ← SL fires (1.39102)
```

After a gap-dump, the market routinely bounces 0.5-0.7% before resuming the trend. The 0.50% SL floor gets hit by the bounce itself, not by the trend resuming.

**Rule of thumb for gap-down entries:**
- After a >1% gap-down candle, expect a 0.5-0.7% retracement bounce before continuation
- If using ATR SL at floor (0.50%), the bounce will likely trigger it
- Consider wider SL floor (0.75%) for gap-down entries specifically, or wait for bounce to exhaust before entry

## Files

- `/root/.hermes/data/candles.db` — 1m candles, 130+ coins (candles_1m table)
- Companion: `rsi-backtest` skill — RSI degrades signal quality
- Companion: `zscore-pump-backtest` skill — z-score mean reversion exits

## Implementation Suggestion

Add to signal_gen.py or create new signal:

```python
# New signal type: 'fake_dump' or 'vol_spike_short'
# Fire when:
#   vol_ratio > 10x avg AND price < sma20 AND 40 < RSI < 65
#   OR: RSI bounced from <30 to 40-60 after fake dump
# Direction: SHORT only (never LONG this pattern)
# Regime: bear market / risk-off (test with market regime filter)
```
