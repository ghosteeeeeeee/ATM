# bb_bounce_v3_long — Signal Development Brief

## Goal
Build a high-winrate bb_bounce LONG signal. **Every trade should be a winner.**

## Current Performance (all bb_bounce LONG variants combined)
- **133 trades, 66.2% WR, +$1.64 total**
- Best variant: `bb_bounce_v2_long` — 73T, 74.0% WR, +$2.08

## What Works (replicate)
1. **profit-monster-trail exits**: 78T, 97.4% WR, +$5.94 — this is the money maker
2. **NORMAL regime**: 72.7% WR, +$0.81 — best regime
3. **HIGH regime**: 64.4% WR, +$0.52 — solid
4. **RSI 30-50 at entry**: Winners tend to enter when RSI is recovering from oversold, not chasing
5. **BB position 0.2-0.5**: Near lower band but not at extremes
6. **Negative/low speed**: Price not falling hard when entering

## What Doesn't Work (avoid)
1. **cut-loser-CL-T1 exits**: 12T, 0% WR, -$1.92 — ALL losses, premature exits
2. **atr_sl_hit exits**: 38T, 28.9% WR, -$2.20 — SL too tight or bad entry
3. **stale=True trades**: Many losses have stale=True — entering on stale signals = bad
4. **Extreme RSI entries**: ATOM entered at RSI=8.79 (oversold = catching falling knife)
5. **EXTREME regime**: 58.6% WR, -$0.01 — weakest regime, break-even
6. **BB position > 0.8**: Entering near upper band = chasing, not bouncing

## Entry Conditions (from trade data analysis)

### Winners typically have:
- RSI: 30-50 (recovering from oversold, not extreme)
- BB position: 0.15-0.50 (near lower band, bouncing)
- Speed: negative to slightly positive (not falling hard)
- Stale: False (fresh signals work better)
- Regime: NORMAL or HIGH (not EXTREME)

### Losers typically have:
- RSI: <20 or >60 (extreme conditions)
- BB position: >0.6 or <0.1 (too far from band)
- Speed: highly negative (falling knife)
- Stale: True (old signals lose)
- Regime: EXTREME (whipsaw-prone)

## V2 Parameters (current)
```python
BB_TOUCH_PCT = 0.15    # Price within 0.15% of lower BB
BB_WIDTH_MAX = 2.5     # BB width < 2.5%
RSI_MIN = 35           # RSI > 35 (bounce confirmed)
BOUNCE_MIN_PCT = 0.10  # Bounce strength >= 0.10%
VEL_MIN = -0.01        # 15m velocity > -0.01%
MOM_MIN = 0            # 30m momentum > 0
VOL_MAX = 0.5          # Volatility < 0.5%
MIN_AGE_SEC = 600      # 10 min candle age
```

## V3 Requirements

### New Filters (based on loss analysis):
1. **RSI band filter**: RSI must be 25-55 (not extreme oversold or overbought)
2. **Stale filter**: Block stale=True signals (or require tighter conditions)
3. **Speed filter**: 15m speed > -0.5% (not free-falling)
4. **BB position band**: BB position must be 0.10-0.65 (not chasing)
5. **Regime-aware confidence**: Lower confidence in EXTREME (0.7x), boost in NORMAL (1.1x)

### Improved Entry Logic:
1. Price must be within BB_TOUCH_PCT of lower BB (existing)
2. **RSI recovery**: RSI must be rising (current RSI > RSI 3 bars ago)
3. **Momentum confirmation**: 3 consecutive green candles or positive momentum
4. **Volume confirmation**: Volume > 1.2x average (bounce confirmed by volume)
5. **No extreme conditions**: Skip if RSI <20 or >65, or speed < -1%

### Regime-Specific Tuning:
- **NORMAL**: Full confidence, all filters active (best regime)
- **HIGH**: Full confidence, relax speed filter slightly
- **EXTREME**: 0.7x confidence, require RSI 35-50 (tighter band)
- **FLAT**: Full confidence, require volume confirmation

## Testing Requirements
1. **Backtest on all 133 historical trades** — must improve on 74% WR
2. **Check: would v3 filters have blocked any of the 88 winners?**
   - If >5% of winners blocked = too aggressive
3. **Check: would v3 filters have caught the 41 losers?**
   - Target: catch >60% of losers without blocking winners
4. **Shadow mode first** — run for 48h before enabling live

## Files to Reference
- Current signal: `scripts/signals/bb_bounce_v2_long.py`
- Parameters: `scripts/hermes_constants.py` (BB_BOUNCE_V2_* constants)
- Trade data: PostgreSQL `brain` database, `trades` table
- Signal registry: `scripts/signals/__init__.py`

## Success Criteria
- **Target**: 78%+ WR with 50+ trades
- **No trade should be a loser** — if it's going to lose, don't enter
- **Better R:R** — wins should be bigger than losses
- **Regime-aware** — adapt to market conditions
