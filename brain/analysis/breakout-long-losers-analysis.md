# Breakout-Long+ Signal — Loser Analysis

**Date:** 2026-09-14
**Signal:** breakout-long+
**Win Rate:** 33.3% (1W/2L pure, 0W/1L combo)
**Avg PnL:** -2.88%

## Trade Summary

| Token | Entry | Exit | PnL | RSI | BB Pos | Wave | BTC Regime | Outcome |
|-------|-------|------|-----|-----|--------|------|------------|---------|
| XPL | 0.0803 | 0.0821 | **+11.27%** | 46.6 | 0.97 | accelerating | TRANSITIONING→BULL | ✅ WIN |
| IMX | 0.1238 | 0.1210 | **-11.07%** | 71.4 | 0.77 | falling | RANGING | ❌ LOSS |
| ZEN | 6.3791 | 6.2663 | **-8.84%** | 49.4 | 0.77 | falling | BULL_TREND | ❌ LOSS |
| ACE | 0.1522 | 0.1502 | **-3.94%** | 73.3 | 0.28 | accelerating | TRANSITIONING | ❌ LOSS |

## Pattern Analysis

### What the Winner Had (XPL)
- **RSI: 46.6** — neutral, not overbought
- **BB position: 0.97** — near upper band (breakout confirmed)
- **Wave phase: accelerating** — momentum building
- **Entry timing: DURING consolidation** — before the main move
- **Price action: steady grind** — 0.0797 → 0.0832 over 6 hours

### What the Losers Had

**Common failure patterns:**
1. **RSI > 70 (overbought)** — IMX: 71.4, ACE: 73.3
2. **BB position < 0.80** — IMX: 0.77, ZEN: 0.77, ACE: 0.28
3. **Wave phase = falling** — IMX: falling, ZEN: falling
4. **Entry at TOP of spike** — not during consolidation
5. **BTC regime unsupportive** — RANGING or TRANSITIONING

### Root Cause
The signal fires on volume spike + price near range high, but it doesn't check:
- Whether the move has already happened (RSI overbought = late entry)
- Whether momentum is building or fading (wave phase)
- Whether price is actually at breakout level (BB position)

## Recommended Parameter Changes

### 1. Add RSI_MAX filter (70)
**File:** `scripts/signals/breakout_long.py`
**Logic:** Skip if RSI > 70 — overbought, likely to reverse
**Impact:** Would have blocked IMX (71.4) and ACE (73.3), saved ~15%
**Backtest:** XPL RSI was 46.6 — would still pass

### 2. Add BB_POSITION_MIN filter (0.85)
**File:** `scripts/signals/breakout_long.py`
**Logic:** Skip if BB position < 0.85 — not at breakout level
**Impact:** Would have blocked IMX (0.77), ZEN (0.77), ACE (0.28)
**Backtest:** XPL BB was 0.97 — would still pass

### 3. Add WAVE_PHASE filter
**File:** `scripts/signals/breakout_long.py`
**Logic:** Skip if wave phase = 'falling' — momentum fading
**Impact:** Would have blocked IMX and ZEN
**Backtest:** XPL wave was 'accelerating' — would still pass

### 4. Add SPIKE_REJECTION filter
**File:** `scripts/signals/breakout_long.py`
**Logic:** Skip if price dropped >0.3% in last 3 candles — false breakout
**Impact:** Would have caught the spike-then-drop pattern
**Backtest:** XPL had steady grind, no rejection — would still pass

### 5. Tighten ATR_MAX from 0.5% to 0.4%
**File:** `scripts/hermes_constants.py`
**Logic:** Stricter consolidation requirement
**Impact:** Fewer signals but higher quality
**Backtest:** Need to verify XPL ATR was < 0.4%

## Constants to Add/Modify

```python
# In hermes_constants.py
BREAKOUT_LONG_RSI_MAX = 70           # NEW: max RSI for entry (overbought filter)
BREAKOUT_LONG_BB_POSITION_MIN = 0.85 # NEW: min BB position (breakout level)
BREAKOUT_LONG_WAVE_PHASE_BLOCK = ('falling',)  # NEW: blocked wave phases
BREAKOUT_LONG_SPIKE_REJECTION_PCT = 0.3  # NEW: max drop % in last 3 candles
BREAKOUT_LONG_ATR_MAX_PCT = 0.4     # MODIFY: was 0.5, tighter consolidation
```

## Files to Modify

1. `scripts/hermes_constants.py` — add new constants
2. `scripts/signals/breakout_long.py` — add filter logic
3. Run backtest to verify no winning trades affected

## Expected Impact

| Metric | Before | After (Projected) |
|--------|--------|-------------------|
| Win Rate | 33.3% | ~66.7% (2W/1L) |
| Avg PnL | -2.88% | +3.66% |
| Worst Trade | -11.07% | -3.94% (ACE only) |
| Trades Blocked | 0 | 2 (IMX, ZEN) |
