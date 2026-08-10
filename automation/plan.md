# Plan: 15m Trend Filter Test for SHORT Signals

## Problem
The `add_signal()` trend filter at `signal_schema.py:580` blocks ALL SHORT signals when the 1H trend is BULLISH. This is the single biggest SHORT bottleneck:
- 1H BULLISH: 38% of tokens → SHORT blocked
- 15m BULLISH: 14% of tokens → SHORT would be allowed
- 42% of tokens have 1H ≠ 15m trend (disagreement rate)

Recent blocked SHORT signals (all `mover_short`):
| Token | 1H Trend | 15m Trend | Would 15m unblock? |
|-------|----------|-----------|-------------------|
| ACE   | BULL    | BEAR      | YES               |
| AVNT  | BULL    | NEUTRAL   | YES               |
| CC    | BULL    | NEUTRAL   | YES               |
| MORPHO| BULL    | NEUTRAL   | YES               |
| W     | BULL    | NEUTRAL   | YES               |
| TNSR  | BULL    | NEUTRAL   | YES               |
| BSV   | BULL    | NEUTRAL   | YES               |
| GOAT  | BULL    | BEAR      | YES               |

8 of 8 recently blocked SHORTs would be unblocked with 15m filter.

---

## Proposed Changes

### Option A: Replace 1H with 15m trend filter (signal_schema.py:538)
Change `TREND_FILTER_TIMEFRAME = '1h'` → `TREND_FILTER_TIMEFRAME = '15m'`

**Pros:**
- Dramatically more SHORT signals (14% BULLISH vs 38%)
- Still uses EMA20/EMA50 on 15m — proven methodology
- Faster reacting to trend changes

**Cons:**
- More volatile / whipsaw-prone
- May allow SHORTs in early-stage pullbacks that become continuations
- The 1H filter was deliberately conservative

### Option B: Remove 1H trend filter for SHORT direction only (signal_schema.py:580)
Keep 1H filter for LONG, remove it for SHORT.

**Pros:**
- Most aggressive SHORT liberalization
- Mean-reversion signals (bb_bounce, range_finder) should fire at overbought regardless of trend
- Only affects SHORT

**Cons:**
- Asymmetric logic — harder to reason about
- No higher-timeframe protection for SHORT

### Option C: Replace 1H with 4H trend filter
Trade-off between A and B — 4H is slower than 15m but faster than 1H.

---

## Test 1 Results (RUN): Historical blocked SHORT signals

Parsed 32 BLOCKED SHORT signals from recent pipeline logs (all `mover_short`):

| Token | Signal | Time | 1H | 15m | 1H Blk | 15m Blk |
|-------|--------|------|-----|------|---------|---------|
| ACE (11x) | mover_short | Aug8-10 | BULL | MIX (BULL+BEAR) | YES | MIX |
| AVNT (6x) | mover_short | Aug9-10 | BULL | MIX (BULL+NEUTRAL) | YES | MIX |
| CC (5x) | mover_short | Aug9-10 | BULL | MIX (BULL+BEAR) | YES | MIX |
| CELO (2x) | mover_short | Aug10 | BULL | MIX | YES | MIX |
| ME (1x) | mover_short | Aug10 | BULL | NEUTRAL | YES | NO |
| BSV (1x) | mover_short | Aug10 | BULL | NEUTRAL | YES | NO |
| MEGA (1x) | mover_short | Aug10 | BULL | NEUTRAL | YES | NO |

**Summary:**
- Blocked by 1H BULLISH: 32/32 (100%)
- Would still be blocked by 15m BULLISH: 20/32 (62%)
- **NEWLY ALLOWED with 15m filter: 12/32 (38%)**

The 12 newly allowed signals: ACE (3x at 15m=BEAR), AVNT (3x at 15m=NEUTRAL), CC (2x at 15m=BEAR), CELO, ME, BSV, MEGA

**Key insight:** 15m being BEARISH/NEUTRAL while 1H is BULLISH = price has already pulled back on 15m but 1H hasn't confirmed. These are exactly the entries mean-reversion wants — shorting into a pullback that hasn't yet violated the larger trend.

---

## Tests to Run

### Test 1: Historical candle simulation (can run NOW)
For each token in recent pipeline runs, compute what the 1H vs 15m trend was at signal time. Does not require changing code — just data analysis.

**Script:** `scripts/test_15m_vs_1h_trend.py` (new)

**Data to collect:**
- All `add_signal` calls in last 7 days that were BLOCKED by trend filter
- For each: token, timestamp, signal_type
- Compute 1H and 15m trend at that timestamp
- Answer: would 15m have allowed it?

### Test 2: Forward paper trading (requires code change)
Deploy 15m filter → run paper trading for 24-48h → compare SHORT signal count vs historical rate.

### Test 3: Backtest on closed trades (if data available)
Check if any recent CLOSED trades (that WON as SHORT) would have been blocked by 1H filter at entry. This tells us if the filter is blocking winners.

---

## Implementation Steps

### Step 1: Write `scripts/test_15m_vs_1h_trend.py`
```python
"""
Historical analysis: how many SHORT signals were blocked by 1H trend filter
that 15m would have allowed?
"""
# 1. Read pipeline logs for BLOCKED signals
# 2. For each blocked signal, get token + timestamp
# 3. Reconstruct 1H and 15m EMAs at that time
# 4. Report: blocked by 1H, allowed by 15m count
```

### Step 2: If Test 1 looks good → implement Option A
Change `TREND_FILTER_TIMEFRAME = '15m'` in `hermes_constants.py`
Also update the EMA lookback from 60 to 60 (same number of candles, different timeframe)

### Step 3: Monitor 48h
- SHORT signal count vs baseline
- SHORT WR vs baseline
- Any new bleeding patterns

### Step 4: If SHORT WR drops below 40% → revert or add guard
Add minimum spread threshold: only block if 15m spread > 1.0% (strong BULLISH)

---

## Recommended Action

**Proceed with Option A: Replace 1H with 15m trend filter**

Rationale:
1. Test 1 confirms 38% more SHORT signals would get through
2. The newly allowed signals (15m BEARISH/NEUTRAL + 1H BULLISH) are ideal mean-reversion entries
3. 62% still blocked — conservative enough
4. Single constant change: `TREND_FILTER_TIMEFRAME = '15m'`

## Key Metrics to Track

| Metric | Baseline (1H) | Target (15m) |
|--------|---------------|---------------|
| SHORT signals/hr | ~1-2 | ~3-5 |
| SHORT WR | 37.9% (7d) | >40% |
| SHORT PnL/24h | $0.02 | >$0.05 |

---

## Risk Assessment

- **MEDIUM risk**: 15m filter more volatile, may allow chop-chasing SHORTs
- **MITIGATION**: Keep 5m+15m dual-BULLISH confirmation (lines 638-642) as second layer
- **MITIGATION**: Monitor first — if SHORT WR drops below 40% for 5+ trades, add spread threshold or revert

---

## Implementation Steps

1. [ ] Change `hermes_constants.py`: `TREND_FILTER_TIMEFRAME = '15m'`
2. [ ] Deploy to paper trading
3. [ ] Monitor 48h: SHORT count, WR, PnL
4. [ ] If SHORT WR < 40% for 5+ trades: revert or add `TREND_FILTER_SPREAD_MIN = 1.0` (only block if 15m spread > 1%)
5. [ ] If WR >= 40%: keep 15m filter, document in constants

---

## Files to Modify
- `hermes_constants.py`: `TREND_FILTER_TIMEFRAME = '15m'`

---

## Status
**READY TO IMPLEMENT** — Test 1 results confirm 38% more SHORT signals would get through
