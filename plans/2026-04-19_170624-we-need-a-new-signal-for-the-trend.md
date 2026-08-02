# Plan: "Trend Is Your Friend" Signal

## Slug
`trend-is-your-friend`

## Goal

Design and implement a new signal — `trend-is-your-friend` — that detects when a trending move is losing steam and likely to reverse. The thesis: trade with the trend while it's healthy, exit and fade when multiple indicators confirm exhaustion.

---

## Context / Assumptions

- Current signal set: `mtf_zscore`, `percentile_rank`, `velocity`, `hwave`, `momentum`, `pattern_micro_flag`, `fast_momentum`, `wave_turn`
- `wave_turn` fires on short-term speed + acceleration flips (5m z-score + acceleration)
- `trend-is-your-friend` should be **different**: longer-term trend breakdown, not just short-term velocity
- Core thesis: "don't fight the tape, but exit when the tape tires"

**What "trend-is-your-friend" means:**
- Price making higher highs but momentum/velocity making lower highs (divergence)
- Volume fading on the latest push
- Multi-timeframe alignment breaking (e.g., 4H trending but 15m diverging)
- Bollinger Band walk-extreme + contraction next bar
- ADX peaking then falling during continued price movement

---

## Proposed Approach

### Signal Philosophy
- **Direction**: Counter-trend (exit long / exit short, optionally flip)
- **Trigger**: Combination of 2+ exhaustion indicators firing together (confluence)
- **Timeframe**: 4H primary, 1H confirmation
- **Confidence**: Higher = more indicators agree

### Indicator Stack (any 2+ fires signal)

| Indicator | What it measures | Bullish exhaustion | Bearish exhaustion |
|---|---|---|---|
| **Price/Momentum Divergence** | Price vs RSI/MACD histogram | Price↑ momentum↓ | Price↓ momentum↑ |
| **Volume Fade** | Volume on latest push vs 20MA | Volume declining on up bars | Volume declining on down bars |
| **Bollinger Band Extension** | Price outside 2σ, next bar inside | Close inside BB after extreme | Close inside BB after extreme |
| **RSI Extreme + Roll Over** | RSI > 70 LONG, < 30 SHORT | RSI > 70 → declining | RSI < 30 → rising |
| **MA Alignment Break** | 5/10/20 MA stack direction | All pointing up → mixed | All pointing down → mixed |
| **ADX Peak + Price Continue** | ADX was high (>25), now falling while price keeps going | ADX falling + price up = exhausted rally | ADX falling + price down = exhausted sell |

### Entry vs Exit Mode
- **As exit signal** (primary): close existing position when trend exhausts
- **As flip signal** (optional): after close, inject counter-signal with high confidence

---

## Step-by-Step Plan

### Step 1: Create `trend_is_your_friend` detector function in `signal_gen.py`

Location: new section in `signal_gen.py`, near the existing `detect_wave_turn()` or as a standalone function.

Function signature:
```python
def detect_trend_is_your_friend(token: str, direction: str) -> dict:
    """
    Returns dict with keys:
      - firing: bool
      - confidence: int (60-95)
      - reasons: list[str]  # which indicators fired
      - direction: str  # 'LONG' or 'SHORT' (the position we want to close)
      - value: float
      - z_score: float
    """
```

### Step 2: Implement each exhaustion indicator

Each as a sub-function inside `detect_trend_is_your_friend`. Use 4H candles as primary, 1H for confirmation.

### Step 3: Wire into `signal_gen.py` main loop

Call `detect_trend_is_your_friend()` for each token with an open position (check against open trades from position_manager or trades.json).

If firing:
- Log the signal with direction = opposite of current position
- confidence = 60 + (20 * num_indicators_firing) — max 95
- Signal type = `trend_is_your_friend`

### Step 4: Add to `ai_decider.py` scoring

Add `trend_is_your_friend` to the signal type scoring — high confidence threshold since it's confluence-based. Should auto-approve at confidence >= 80 (3+ indicators).

### Step 5: Add counter-signal injection

After `trend_is_your_friend` fires and closes a position, inject a counter-signal (opposite direction) with:
- signal_type = `trend_is_your_friend`
- confidence = same as exit confidence
- source = `trend_is_your_friend,momentum`
- z_score_tier = `trend_is_your_friend`

### Step 6: Add blacklist/blacklist handling

- `SHORT_BLACKLIST`: tokens where trend exhaustion should NOT trigger SHORT exits (e.g., already in a downtrend — don't fade it further)
- `LONG_BLACKLIST`: tokens where trend exhaustion should NOT trigger LONG exits

### Step 7: Unit test with historical candles

Run backtest on 30 days of 15m/4H data, 50+ tokens. Verify:
- Signal fires at sensible points (not too early, not too late)
- Win rate on counter-fade trades after exhaustion
- No false positives in strong trending markets (should wait for real exhaustion)

---

## Files Likely to Change

| File | Change |
|---|---|
| `/root/.hermes/scripts/signal_gen.py` | Add `detect_trend_is_your_friend()` function + wire into main loop |
| `/root/.hermes/scripts/ai_decider.py` | Add `trend_is_your_friend` scoring / auto-approval threshold |
| `/root/.hermes/scripts/position_manager.py` | Optional: wire as exit check (like wave_turn) |
| `/root/.hermes/scripts/hermes_constants.py` | Add `trend_is_your_friend` to SHORT_BLACKLIST / LONG_BLACKLIST if needed |
| `/root/.hermes/brain/trading.md` | Document new signal design |

---

## Tests / Validation

1. Run `python3 signal_gen.py --dry` and check `signals_hermes_runtime.db` for `trend_is_your_friend` signals
2. Verify signal confidence reflects number of indicators firing
3. Check that `trend_is_your_friend` signals are not blocking each other in signal_schema
4. Smoke test: `python3 smoke_test.py --target signal_gen.py`
5. Backtest: run against historical candles for 30 days, compare vs buy-and-hold

---

## Risks / Tradeoffs / Open Questions

1. **Risk**: Trend exhaustion signals can be early in strong trends — consider requiring 3+ indicators vs 2
2. **Tradeoff**: More indicators = higher confidence but fewer signals. Need to tune minimum threshold.
3. **Open question**: Should `trend_is_your_friend` fire on **both** exit AND flip, or only exit? T should decide.
4. **Open question**: Does this replace or augment `wave_turn`? `wave_turn` is short-term (5m); `trend_is_your_friend` is longer-term (4H). They target different regimes — likely both keep.
5. **ADX data**: Need to verify ADX is available in the candle data or needs to be computed from raw OHLCV
6. **Volume data**: Need to verify volume is populated in the candle DB for all tokens

---

## Backtest Metric Targets (post-implementation)

| Metric | Target |
|---|---|
| Win rate on counter-fade after exhaustion | > 55% |
| Avg trade duration | < 4 hours |
| Signal frequency | ~3-5/day across portfolio |
| False positive rate (exhaustion in healthy trend) | < 20% |
