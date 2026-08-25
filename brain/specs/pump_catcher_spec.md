# Pump Catcher Signal — Spec

## Problem
We missed the HBAR 6% pump (0.0793 → 0.0843) on Aug 25 because:
1. All momentum signals are disabled (velocity_ignition, zscore_pump)
2. Existing pump_hunter.py is a REVERSION strategy (fades spikes)
3. Volume data is all zeros — any vol-based detection is dead
4. fast_momentum needs 240 min of data — too slow for early entry

## Goal
Catch the FIRST 0.5-1.0% explosive move in a new direction and ride it for 2-4%.
Entry window: within 2-5 bars of the first explosive candle.
Target: 2-4% profit (the meat of the move, not the whole thing).

## Design: Repurpose pump_hunter.py

### What to Keep
- Position management infrastructure (JSON tracking, DB records, HL execution)
- Exit monitoring (check_pump_exits, sync_hl_positions)
- Token universe scanning (get_tradeable_tokens)
- The overall scan_and_fire() loop structure

### What to Change

#### 1. Detection: Price-Based Momentum (not volume-based)

**Current (broken):**
```python
vol_ratio > 4.0 AND |body_pct| > 3.5%  # volume is always 0 → never fires
```

**New: Multi-Signal Momentum Detection**

```python
def detect_pump_momentum(candles, prices_1m):
    """
    Detect early-stage momentum breakout.
    
    Fires when ALL of these are true:
    1. Price velocity: >0.5% move in 3-5 bars (1m timeframe)
    2. Acceleration: current 3-bar velocity > prior 3-bar velocity
    3. Trend alignment: price above EMA20 (computed from prices_1m)
    4. No exhaustion: RSI < 75 (not overbought yet)
    5. Fresh move: no similar signal in last 10 bars (dedup)
    
    Returns: {direction: 'LONG', entry_price, target, stop, confidence}
    """
```

**Why this works for HBAR:**
- At 02:17, price moved +0.52% in 1 bar → velocity fires
- At 02:18, price moved +0.76% in 1 bar → acceleration confirms
- Price was above EMA20 (trend aligned)
- RSI was ~55 (not overbought)
- No recent signal (fresh move)

#### 2. Direction: LONG Only (Momentum, Not Reversion)

**Current:** Always LONG reversion (fade the spike)
**New:** Always LONG momentum (ride the spike)

Rationale: We want to catch pumps, not fade them. The reversion strategy was backtested on15m data with 89% WR, but that's for mean-reversion on 3.5%+ spikes. Our target is catching 0.5-1.0% initial moves that become 2-4% trends.

#### 3. TP/SL: Asymmetric (Ride Winners, Cut Losers)

**Current:**
- TP: 100% reversion (back to prev_close)
- SL: 150% impulse

**New:**
- TP: 3.0% from entry (ride the trend)
- SL: 1.0% from entry (tight stop, cut losers fast)
- Trailing stop: activate at +1.5%, trail by 0.8%

Rationale: We want 3:1 R/R on momentum trades. The HBAR move was 6.3% peak — a 3% TP would have captured half the move.

#### 4. Confidence Scoring

```python
confidence = 60  # base
+ 5 if velocity > 0.8% in 3 bars (strong move)
+ 5 if acceleration > 0 (momentum building)
+ 5 if price > EMA50 (higher timeframe alignment)
+ 5 if RSI between 40-65 (sweet spot, not overbought/oversold)
+ 5 if speed_percentile > 70 (top mover)
# Cap at 88
```

#### 5. Cooldown & Dedup

- Minimum 10 bars between signals per token (same as fast_momentum)
- Maximum 3 concurrent positions (conservative)
- Skip if token already has an open position (any signal type)

### Implementation Plan

1. **Create `scripts/signals/pump_catcher.py`** — new signal in the registry
   - Uses price_history (1m) for detection — same as accel_300
   - No volume dependency
   - Generates signals into signals_hermes_runtime.db
   - Goes through signal_compactor → hotset → guardian → HL

2. **Add to signal registry** in `scripts/signals/__init__.py`
   - Fast signal (runs every minute)
   - Enabled via `PUMP_CATCHER_ENABLED` in hermes_constants.py

3. **Parameters in hermes_constants.py:**
   ```python
   PUMP_CATCHER_ENABLED = True
   PUMP_CATCHER_PLUS_ENABLED = True
   PUMP_CATCHER_MINUS_ENABLED = False  # LONG only initially
   PUMP_CATCHER_VELOCITY_MIN = 0.5     # min % move in 3 bars
   PUMP_CATCHER_ACCEL_MIN = 0.0        # min acceleration (velocity must be increasing)
   PUMP_CATCHER_TREND_EMA = 20         # EMA period for trend filter
   PUMP_CATCHER_RSI_MAX = 75           # max RSI (not overbought)
   PUMP_CATCHER_RSI_MIN = 30           # min RSI (not oversold)
   PUMP_CATCHER_TP_PCT = 3.0           # take profit at 3%
   PUMP_CATCHER_SL_PCT = 1.0           # stop loss at 1%
   PUMP_CATCHER_TRAILING_ACTIVATE = 1.5  # activate trailing at +1.5%
   PUMP_CATCHER_TRAILING_DISTANCE = 0.8  # trail by 0.8%
   PUMP_CATCHER_COOLDOWN_BARS = 10     # bars between signals
   PUMP_CATCHER_MAX_POSITIONS = 3      # max concurrent
   PUMP_CATCHER_CONFIDENCE_BASE = 60
   PUMP_CATCHER_CONFIDENCE_CAP = 88
   ```

4. **Backtest validation:**
   - Run against HBAR Aug 25 data → should fire at 02:17-02:18
   - Run against full 30-day dataset → measure WR, avg P&L, max drawdown
   - Target: >55% WR, >1.5% avg P&L, <3% max drawdown

### Files to Create/Modify

| File | Action | Purpose |
|------|--------|---------|
| `scripts/signals/pump_catcher.py` | CREATE | New momentum signal |
| `scripts/signals/__init__.py` | MODIFY | Add to registry |
| `scripts/hermes_constants.py` | MODIFY | Add parameters |
| `brain/specs/pump_catcher_spec.md` | CREATE | This spec |

### Risk Considerations

1. **False breakouts**: Price spikes 0.5% then reverses → SL hit at -1%
   - Mitigation: Require acceleration (not just velocity) to confirm momentum
   - Mitigation: Tight 1% SL limits damage

2. **Overfitting**: Parameters tuned to HBAR specifically
   - Mitigation: Backtest across 20+ tokens, not just HBAR
   - Mitigation: Use conservative defaults, let tuner optimize later

3. **Execution speed**: Signal fires but HL fill is late
   - Mitigation: This goes through the normal signal pipeline (not standalone like pump_hunter)
   - Mitigation: Signal compactor + guardian handle execution timing

### Success Metrics

After 7 days of live paper trading:
- Signal fires on ≥3 genuine momentum moves (not false breakouts)
- Win rate ≥ 55%
- Average winning trade ≥ 2%
- Average losing trade ≤ -1% (SL working)
- No more than 2 consecutive losses
