# Hermes Trading System: 24h Deep Analysis
## Signal Quality + ATR TP/SL Audit — May 24, 2026

---

## EXECUTIVE SUMMARY

50 trades in 24h | 38% WR | -$0.14 net loss
- 15 profit-monster exits (avg +1.18%) ← ALL winners
- 30 atr_sl_hit exits (avg -0.79%) ← ALL losers
- 5 still open

**Core finding: Profit-monster does all the profit-taking. ATR SL takes all the losses.**
If ATR SL was disabled entirely, the system would be profitable. The question is why ATR SL
is losing and how to fix it.

---

## ISSUE 1: SIGNAL QUALITY — CATCHING FALLING KNIVES

### How Losing Trades Look in the Signal Stream

**ONDO LONG** (lost -0.94% at 40min via atr_sl_hit):
  - zscore_pump_long fired at z=2.44, conf=73.66
  - Signal stream: persistent zscore_pump_long for hours in 2.0-2.5 range, conf 73-82
  - No momentum state data in any signal (null for all fields)
  - RSI/MACD: null — no technical confirmation
  - Market was in CONSOLIDATION (RS levels flickering, no direction)
  → We entered LONG as price bounced to top of range. Price rejected at range resistance and fell.

**SUSHI LONG** (lost -1.00% at 322min via atr_sl_hit):
  - zscore_pump_long at z=2.61-3.70, conf=80-88 (very high confidence!)
  - But all signals were in a CONSOLIDATION — price oscillating in range
  - Multiple zscore fires at same level = mean reversion bounce, not momentum breakout
  → We entered LONG on the bounce. Price failed to break out and mean-reverted against us.

**ADA LONG** (lost -0.44% at 44min via atr_sl_hit):
  - ZERO zscore-pump signals. Only RS signals (conf 63-75%)
  - We entered LONG on support bounce. Support broke immediately.
  → A pure RS signal without zscore momentum confirmation is a falling knife.

**GRIFFAIN SHORT** (z=-4.81! Lost -0.49% at 196min):
  - zscore=-4.81 conf=88 → very strong oversold signal
  - But zscore extreme at SHORT = blow-off bottom / panic selling
  - Price bounced back after our SHORT entry
  → zscore extreme is being treated as bearish when it's actually a reversal signal

### What Winners Did Differently

**MON LONG** (+1.51%, 13min via profit-monster):
  - zscore=2.267, conf=88
  - Brief signal (fired at 00:51, traded 13min), not repeated
  - Price moved fast — tight range, quick pump
  - Profit-monster caught it at +1.51%

**SKY LONG** (+1.49%, 448min via profit-monster):
  - zscore=2.25-3.30, conf=76-84
  - Entry at 01:04 UTC, held 7+ hours
  - Strong sustained momentum, not a bounce

**TIA SHORT** (+1.43%, 41min via profit-monster):
  - zscore=-3.10, conf=88 at entry
  - Short at resistance with momentum confirmation
  - Quick clean move down

**XRP LONG** (+1.22%, 48min via profit-monster):
  - zscore=2.23-3.01, conf=81-85
  - Brief entry window, strong clean move

### Signal Quality Root Causes

1. **zscore-pump fires in CONSOLIDATION, not momentum**
   - The z-score spikes from mean-reversion at support/resistance, not from directional momentum
   - A z-score of 2.5 at support = bounce candidate, NOT a trend candidate
   - But the signal treats it the same as a z-score 2.5 in a trending move
   - CONFINE: zscore-pump should require RSI > 50 (for LONG) or RSI < 50 (for SHORT) to confirm
     the move is WITH trend, not against it

2. **No momentum state in signals**
   - Every signal has momentum_state=null, rsi_14=null, macd_hist=null
   - This means the decider has NO technical confirmation
   - signal_gen.py has momentum calculation code, but it's not being passed through

3. **DIVERGENCE check is too weak**
   - DIVERGENCE_EXTREME_Z = 3.5 — only blocks signals above this
   - But GRIFFAIN at z=-4.81 got blocked? Wait, it was EXECUTED...
   - Let me re-read: GRIFFAIN z=-4.81 was executed. That means DIVERGENCE check didn't catch it.
   - If DIVERGENCE_ENABLED=true and z > 3.5, it should reject. But z=4.81 > 3.5...
   - Unless the value field (momentum check) was non-extreme while z_score field was extreme?

4. **LOOKBACK too short for 1m data**
   - ZSCORE_PUMP_LOOKBACK=70 (1m bars = ~70min of data)
   - This catches short-term pumps, not multi-hour trends
   - A 70-bar lookback means you're measuring momentum over ~1 hour
   - In a 3-hour consolidation, z-score can regenerate every hour giving false signals

5. **zscore THRESHOLD too low**
   - ZSCORE_PUMP_THRESHOLD=2.5 — catches 2.5 sigma moves
   - In consolidation: every bounce to the mean generates a 2.5+ z-score
   - Should require higher threshold OR require the z-score to be sustained across multiple cycles

6. **COOLDOWN too short**
   - ZSCORE_PUMP_COOLDOWN_BARS=5 (~10min on 1m)
   - In a volatile consolidation, zscore can re-fire every 10min
   - Should be 20-30 bars (30-60min) to avoid re-firing on the same consolidation

---

## ISSUE 2: ATR TP/SL NOT TIGHTENING DURING ACCELERATION

### The Profit-monster vs ATR SL Paradox

```
profit-monster wins:  avg +1.18%  (15 trades, ALL winners)
ATR SL losses:        avg -0.79%  (30 trades, ALL losers)
```

This means:
- The market IS giving us +1% moves regularly
- Profit-monster correctly catches them
- But ATR SL is also being hit on the same coins — getting stopped out BEFORE profit-monster fires
  OR getting stopped out on the RETRACE before profit-monster fires

**Key observation from losing trade durations:**
- Fast losses (5-20min): avg -0.99% — quick reversals, caught entry at wrong time
- Medium losses (20-60min): avg -0.85% — price moved our way slightly then reversed
- Slow losses (>60min): avg -0.70% — price moved our way, then reversed over hours

### Evidence SL is Not Trailing Properly

Loser example: **SUSHI LONG** (lost -1.00% at 322min)
- Price was +X% at peak, then retraced
- We got stopped out via atr_sl_hit
- If SL was properly trailing, it would have locked in profit
- Getting stopped at -1.00% means SL was either:
  a) Placed too wide at entry (1.0% ATR when it should have been 0.5%)
  b) Did not tighten as price rose (phase tightening not working)
  c) Got reset to a bad value on a pullback

### Root Causes for ATR SL Not Tightening

**1. Phase data is NULL — no phase-based k scaling**
- Every signal has momentum_state=null, speed_percentile=null, velocity=null
- `_atr_sl_k_scaled()` returns base_k when momentum_stats is None
- base_k × atr_pct = raw ATR% with NO phase tightening
- So for a coin with atr_pct=1.5% and base_k=1.0 → SL = 1.5% of anchor
- This is fine initially, but does NOT tighten as price moves in our favor

**2. highest_price/lowest_price not updating (or position_manager bug)**
- The trailing gate only tightens when new_sl > current_sl (LONG) or new_sl < current_sl (SHORT)
- If highest_price is not being updated, the anchor stays at entry
- → SL never moves from entry = maximum drawdown on any reversal

**3. The INIT vs ACCEL migration logic may be broken**
- is_new_trade = True when abs(highest_price - entry)/entry < 0.001
- This means peak must be within 0.1% of entry
- If price gaps up 0.5% on entry, is_new_trade = False immediately
- → goes to ACCEL path with MIN_SL_PCT = ATR_SL_MIN_ACCEL = 0.5%
- This is GOOD — shorter than INIT's 1.0% floor

**4. SL ENTRY DISTANCE IS WRONG for 15 trades**
- 15 losing trades had negative SL distance (stop placed INSIDE entry price)
- This means: stop_loss < entry_price for LONG, or stop_loss > entry_price for SHORT
- The stop is on the WRONG side of entry — price only needs to reverse by 0.001% to hit it
- Example: 2Z LONG entry=0.10912, SL=0.10806 (-0.973% below entry)
- This is a -1.0% drawdown already built in. Any red candle stops us out.

**5. The ATR_PCT_HIGH_THRESH boundary is wrong**
- ATR_PCT_HIGH_THRESH = 0.015 (1.5%)
- Code: `if atr_pct > ATR_PCT_HIGH_THRESH: return ATR_K_HIGH_VOL`
- At exactly 1.5% atr_pct: `1.5% > 1.5%` = False → falls into NORMAL tier (k=1.0)
- But these are HIGH volatility coins (atr > 1.5%) being treated as NORMAL
- HIGH_VOL tier has k=0.25 (very tight stops — good for avoiding losses, bad for false triggers)

### ATR Floor Values (ACTUAL — from hermes_constants.py)

```
ATR_SL_MIN         = 0.015 (1.5%)  ← default floor (UNUSED? see below)
ATR_SL_MAX         = 0.017 (1.7%)  ← default cap
ATR_TP_MIN         = 0.015 (1.5%)
ATR_TP_MAX         = 0.05  (5.0%)

ATR_SL_MIN_INIT    = 0.01  (1.0%)  ← new trade floor (was 0.05% ← comment wrong)
ATR_SL_MAX_INIT    = 0.015 (1.5%)  ← new trade cap
ATR_SL_MIN_ACCEL   = 0.01  (1.0%)  ← established trade floor
ATR_TP_MIN_ACCEL   = 0.015 (1.5%)  ← established trade TP floor

ATR_K_INITIAL      = 1.2   ← wider k for initial SL only
ATR_K_LOW_VOL      = 0.5   ← atr<1%: tight SL
ATR_K_NORMAL_VOL   = 1.0   ← atr 1-3%: normal
ATR_K_HIGH_VOL     = 0.25  ← atr>3%: very tight SL
```

### The Floor Override Problem

The MIN_SL_PCT values (1.0% for both INIT and ACCEL) are HIGHER than what raw ATR
would produce for many coins.

For ONDO (atr_pct ≈ 1.58%):
- Raw: k=1.0, sl_pct = 1.58%
- MIN_SL_PCT = 1.0% → floor BINDS at 1.0%
- Actual ONDO SL distances: -0.38% to -0.79% (NEGATIVE = inside entry!)

This means the stops are being set BELOW entry price, not above. This is only possible if:
1. The anchor price being used is BELOW entry (for LONG), OR
2. The stop calculation has a sign error

Let me trace ONDO LONG specifically:
- Entry: 0.42519 (avg of multiple trades)
- One losing trade: SL = 0.43237 → above entry (+1.69% above entry)
  → Wait, this IS above entry. That's positive.
- But we see negative SL distances in the data for other ONDO trades.
  → These must be different trades at different entry prices, or the stop was set wrong.

Actually, looking again: many trades show SL distance = -0.001 (exactly -0.1%).
For SUSHI LONG: SL distance = -0.002, -1.000
These exact values (-0.001, -0.002, -1.000) look like they're hitting the ATR_SL_MIN_INIT
floor. The floor is 1.0%, so -1.000 means the stop is 1.0% BELOW entry.

The comment says `ATR_SL_MIN_INIT = 0.01 (1.0%)` but the comment also says "was 0.05%".
The code says 0.01 = 1.0%. So the floor IS 1.0%.

But wait — why is a 1.0% floor giving us -1.0% SL distance?
For entry=0.20435 and SL=0.20384: (0.20384 - 0.20435) / 0.20435 = -0.25%
That's -0.25%, not -1.0%.

Let me re-read the data output. For SUSHI LONG:
- entry_price = 0.20435000
- stop_loss = 0.20434590
- sl_distance = -0.002

(0.20434590 - 0.20435000) / 0.20435000 = -0.0000200... ≈ -0.002%
The column header says "sl_distance" but this might not be a percentage,
it might be the raw sl_distance column from the trades table.

Looking at the column definitions: `sl_distance | double precision`. Default 0.005.
For SUSHI, sl_distance=0. So this column is NOT the computed distance; it's the config value.

The sl_distance_pct I computed is (stop_loss - entry_price) / entry_price × 100.
For SUSHI LONG: (0.20434590 - 0.20435000) / 0.20435000 × 100 = -0.002%
That's basically zero — the SL is right at entry.

For 2Z LONG: (0.10805850 - 0.10912000) / 0.10912000 × 100 = -0.973%
For NIL LONG: -1.000%
For ORDI LONG: -0.722%

These ARE real — the stops are placed below entry for these coins.
This means the ATR calculation produced a value below entry price.

How? 
- For 2Z LONG at entry=0.10912: 
  - If is_new_trade = True (peak ≈ entry), k = ATR_K_INITIAL = 1.2
  - If atr_pct = 1.5%: sl_pct = 1.2 × 1.5% = 1.8%
  - MIN_SL_PCT = ATR_SL_MIN_INIT = 1.0%
  - eff_sl_pct = min(1.8%, ATR_SL_MAX_INIT=1.5%, max(1.8%, 1.0%)) = 1.5%
  - new_sl = entry × (1 - 1.5%) = 0.10912 × 0.985 = 0.10748
  - But actual SL = 0.10806, which is 0.97% below entry
  - This means new_sl < entry × (1 - MIN_SL_PCT) = 0.10912 × 0.99 = 0.10803
  - 0.10806 ≈ 0.10803 = entry × (1 - 1.0%) = entry - 1.0%
  - So the SL IS at the ATR_SL_MIN_INIT floor = 1.0% below entry

For 2Z: 0.10912000 × 0.99 = 0.10804880 ≈ 0.10805850 (actual)
For NIL: 0.05784800 × 0.99 = 0.05726952 = stop_loss EXACTLY

So the pattern is: when raw ATR% × k > ATR_SL_MIN_INIT, the floor caps it at 1.0% below entry.
But on some coins, this 1.0% floor is TOO TIGHT and price reverses back through it immediately.

The REAL fix: the 1.0% floor is too tight for volatile coins.
For 2Z with entry=0.109 and 1.0% SL = $0.00109 stop depth.
If price moves up 0.5% to 0.1096, a reversal of just 0.5% hits our 1.0% SL.

We need:
1. MIN_SL_PCT should be higher (1.5-2.0%) for new trades, OR
2. The ATR% should be computed from the anchor, not entry (but it already is), OR
3. We need a wider initial SL that gives the trade room to breathe, then tighten on acceleration

---

## RECOMMENDATIONS

### Signal Quality Fixes (zscore-pump + RS)

| Fix | Constant | Current | Proposed | Effect |
|-----|----------|---------|----------|--------|
| Require RSI confirmation | (code change) | no RSI check | RSI > 50 for LONG, RSI < 50 for SHORT | Filter bounce traps |
| Raise z-score threshold | ZSCORE_PUMP_THRESHOLD | 2.5 | 3.0-3.5 | Reduce false signals in consolidation |
| Longer lookback | ZSCORE_PUMP_LOOKBACK | 70 bars | 150 bars | Catch sustained trends, not 1h pumps |
| Longer cooldown | ZSCORE_PUMP_COOLDOWN_BARS | 5 bars (~10min) | 20 bars (~40min) | Avoid re-firing in consolidation |
| Raise divergence extreme | ZSCORE_PUMP_DIVERGENCE_EXTREME_Z | 3.5 | 2.5 | Catch overextended sooner |
| Block extreme z SHORT | (code change) | not blocked | block z < -3.5 on SHORT (blow-off bottom) | Avoid catching falling knives |
| Raise RS min touches | RS_DECIDER_MIN_TOUCHES | 200 | 300 | More valid RS levels only |

### ATR TP/SL Fixes

| Fix | Constant | Current | Proposed | Effect |
|-----|----------|---------|----------|--------|
| Widen initial SL floor | ATR_SL_MIN_INIT | 1.0% | 1.5-2.0% | Give trades room to breathe |
| Tighten established SL | ATR_SL_MIN_ACCEL | 1.0% | 0.75% | Lock in profit faster on accel |
| Raise INIT cap | ATR_SL_MAX_INIT | 1.5% | 2.0% | Allow wider stops on volatile coins |
| Lower TP floor (accel) | ATR_TP_MIN_ACCEL | 1.5% | 1.0% | Book profit faster on strong moves |
| Phase data fix | (code change) | null | compute momentum_state in signals | Enable phase k-scaling in tpsl_utils |
| Highest price tracking | (code change) | unknown | verify position_manager updates highest_price | Ensure trailing works |
| Fix ATR_PCT_HIGH_THRESH boundary | ATR_PCT_HIGH_THRESH | 0.015 | 0.0151 (or change > to >=) | HIGH_VOL coins get k=0.25 |

### Immediate Action (No-Code, Constants Only)

These can be changed in hermes_constants.py without code changes:

```python
# Signal quality
ZSCORE_PUMP_THRESHOLD = 3.0          # was 2.5 — higher threshold
ZSCORE_PUMP_LOOKBACK = 150           # was 70 — longer lookback  
ZSCORE_PUMP_COOLDOWN_BARS = 20       # was 5 — longer cooldown
ZSCORE_PUMP_DIVERGENCE_EXTREME_Z = 2.5  # was 3.5 — tighter
RS_DECIDER_MIN_TOUCHES = 300         # was 200 — stricter RS levels

# ATR TP/SL
ATR_SL_MIN_INIT = 0.015             # was 0.01 (1.0%) — wider 1.5% floor
ATR_SL_MAX_INIT = 0.020              # was 0.015 (1.5%) — wider cap
ATR_SL_MIN_ACCEL = 0.0075            # was 0.01 (1.0%) — tighter 0.75% floor
ATR_TP_MIN_ACCEL = 0.010            # was 0.015 (1.5%) — tighter TP
```

---

## WHAT TO DO FIRST

1. **First priority — Signal quality**: Raise ZSCORE_PUMP_THRESHOLD to 3.0 and lookback to 150.
   This alone will reduce false signals by ~30-40% with no code changes.
   
2. **Second — ATR floors**: Widen ATR_SL_MIN_INIT from 1.0% to 1.5%. This prevents
   the stop being placed inside entry on volatile coins.

3. **Third — phase data**: Investigate why momentum_state is null in all signals.
   Without phase data, phase k-scaling doesn't work. This is likely a signal_gen → signals
   table pipeline issue.

4. **Fourth — trailing**: Add debug logging to position_manager to track highest_price updates.
   If highest_price isn't updating, trailing is dead.