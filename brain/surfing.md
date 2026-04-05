# Surfing: The Hermes Trading Metaphor

## Core Analogy

Trading is like surfing. You can't force a wave — you read it, position yourself, and let it carry you.

| Surf Element | Hermes Equivalent | Notes |
|---|---|---|
| **Wave direction** | `regime` (LONG/SHORT) | Are you riding with or against the tide? |
| **Wave speed** | `token velocity` (SPEED FEATURE) | How fast is the wave actually moving? |
| **Your position in the lineup** | `signal source quality` | Hot-set = sitting where the good waves break |
| **Timing the paddle** | `entry signal precision` | Too early/late = wipeout |
| **Board size** | `leverage / position size` | Right tool for the conditions |
| **Wave shape** | `signal quality / confluence` | Clean wall vs chaos |
| **Wind and tide** | `funding rates, open interest` | Shapers of whether a move has structure |
| **Ocean floor** | `support/resistance, orderbook depth` | Determines if a wave has a floor or drops to zero |
| **Reading the sets** | `patience / regime conviction` | Wait for the real swell, don't chase every ripple |

---

## The Three Axes of a Trade

### 1. Direction — `regime`
LONG or SHORT. Driven by BTC/ETH 4h z-score.
- regime = LONG → prefer long signals, filter opposing
- regime = SHORT → prefer short signals, filter opposing
- Regime tells you **which shore to face**

### 2. Speed — `token_speeds` (SPEED FEATURE)
How fast is this token moving relative to the universe?

```
price_velocity_5m  = (current_price - 1hr_ago) / 1hr_ago * 100   [% change]
price_acceleration = rate of change of velocity                      [momentum of momentum]
speed_percentile   = rank of |vel_5m| vs all tokens in universe   [0-100]
is_stale           = vel_5m < 0.2% AND vel_15m < 0.2%              [flat for 3+ hours]
```

**Why it matters:** A wave can be moving toward you (right direction) but be too slow to carry you anywhere. Speed tells you if the wave has energy.

**Speed thresholds:**
- `speed_percentile >= 80` → hot movers, speed bonus applies
- `speed_percentile >= 70` → 5% easier entry threshold
- `speed_percentile < 20` → blocked unless very strong signal (conf >= 80)
- `is_stale = True` → flat for 3+ hours, candidate for stale winner/loser exit

### 3. Quality — `hot-set signals only`
Every new position MUST come from the hot-set. No jumping the line.

**The hot-set is the lineup.** Signals come from:
1. Compaction survivors (scored by AI decider)
2. Speed-boosted (percentile >= 80 → +15% score boost)
3. Confluence-multiplied (multiple signal types agreeing)
4. Direction-filtered (must match current regime)

**No auto-approve. No auto-execute. No shortcuts.**
If a signal is not in the hot-set, it does not get executed. Period.

---

## Wave-Turn Detection: Z-Score + Speed

This is the key insight. These two indicators together tell you if a wave is building or collapsing:

```
Z-Score  = (current_price - 20h_mean) / 20h_std
           → How far price has drifted from recent average
           → Negative = price is low relative to history (potential bottom)
           → Positive = price is high relative to history (potential top)

Speed    = price_velocity_5m
           → How fast price is moving RIGHT NOW

Accel    = price_acceleration
           → Is velocity increasing or decreasing?
```

### The 4 Quadrants:

| Z-Score | Speed | Acceleration | Interpretation | Action |
|---|---|---|---|---|
| Near 0 | Low | Flat | Range-bound, no wave | Sit out, don't paddle |
| Negative (oversold) | HIGH | Positive | Wave building UP — bottom picked | Paddle for LONG |
| Negative (oversold) | LOW | Positive | Wave building but slow | Wait, too early |
| Positive (overbought) | HIGH | Negative | Wave cresting — top in | Take SHORT, grab rail |
| Positive (overbought) | LOW | Negative | Wave collapsing from high | Exit LONGs |
| Near 0 | HIGH | Positive | Mid-range explosion building | Confirm with confluence |

### The NIL Trade: Wrong-Side Entry

**What happened:**

```
Apr 2 20:00-20:11  NIL was in a SHORT regime (z = -1.276 → falling)
  → All LONG signals expired (correct: regime filter working)
  → SHORT mtf_macd signals fired at conf=54, z=-1.276, momentum=falling

Apr 2 20:11  SHORT signal triggered
  → Entry fill: UNKNOWN (not in fills data — executed via mirror or closed before fills logged)
  → z-score at signal: -0.882 (price below 20h mean)
  → price_velocity_5m: essentially flat (-0.1%)

Apr 2 20:11-20:20  Price kept grinding DOWN
  → Actual bottom: 0.034699 at 20:20 (9 minutes AFTER the SHORT signal!)
  → SHORT signal fired 9 min too late — caught the bottom

Apr 2 20:20 → Apr 3 01:00  NIL rallied from 0.03470 → 0.03554 (+2.4%)
  → SHORT was underwater
  → Momentum shifted from "falling" to recovering
```

**The problem:** The regime said SHORT, but:
1. Price was already at the bottom of its range (z=-0.88)
2. Speed was near zero — no energy in the wave
3. Acceleration was about to flip positive — the wave was about to turn

**What SPEED would have caught:**
```
is_stale = True (vel_5m < 0.2% AND vel_15m < 0.2%)
→ NIL was flat for 3+ hours before the signal
→ A flat wave right at the bottom of its range
→ Not a clean SHORT — it was a mean-reversion trap
```

**The fix (SPEED FEATURE):**
- Before executing any SHORT signal, check `is_stale`
- If `is_stale AND z_score < 0` → this is a counter-trend signal, not a trend signal
- Counter-trend signals in a regime of the opposite direction = high probability of failure
- With SPEED: a stale flat token near the bottom of its range with regime=SHORT should have the signal BLOCKED

---

## The 0G Trade: Ranging vs Trending — The Mean Reversion Trap

**What happened:**

```
Mar 22 11:15  0G LONG signal fires
  → confidence: confluence=70 + mtf_macd=94.5 (very high)
  → z-score: -1.179 (near bottom of range)
  → momentum_state: None (not trending)
  → regime at time: LONG

Mar 22 11:00-12:00  0G price was 0.514-0.520
  → Entry fill: 0.51255 (LONG A, 21 sz)
  → Price was already near the high of the day

Mar 22 → Apr 3  0G price drifted: 0.52 → 0.51 → 0.035 (crashed)
  → The "confluence" was a fake-out
  → z=-1.179 was the LOWER band of a volatile range
  → When z-score says "oversold" in a ranging market, it means
    "price is temporarily low" — not "a wave is building"
```

**The problem:** z-score in a ranging market is a mean-reversion signal, not a trend signal. The system interpreted "near the bottom of the range" as "momentum building for a_LONG move" — but in ranging conditions, z-score reversals often just mean "price snapped back to the middle" and then continues drifting.

**The z-score vs trend distinction:**

| Condition | Z-Score Meaning | What To Do |
|---|---|---|
| Strong regime (consistent direction) | Trend confirmation | Z-score extremes = entries with trend |
| Weak/no regime (ranging) | Mean reversion | Z-score extremes = exits, not entries |
| Mixed signals | Regime uncertain | Reduce size, wait for clarity |

**The confluence was misleading:**
- `mtf_macd` (94.5% confidence) was reading MACD weakening across timeframes
- In a trending market, weakening MACD = trend ending = reversal coming
- In a ranging market, MACD just oscillates — it's noise

---

## The Pipeline: How a Wave Gets Ridden

```
Signal Generation (signal_gen.py)
    │
    ├─ SPEED FILTER: speed_percentile < 20 → blocked (no paddle on flat water)
    ├─ SPEED BOOST:   speed_percentile >= 70 → entry threshold × 0.95 (easier)
    └─ Signals written to signals DB

         ▼

AI Decider / Compaction (ai_decider.py)
    │
    ├─ Score = recency + confidence + confluence + speed_score
    ├─ Speed score: (speed_percentile / 100) × 0.10
    └─ Keep top 20 survivors → HOT SET

         ▼

Hot Set (decider-run.py)
    │
    ├─ speed_percentile >= 80 → +15% effective confidence boost
    ├─ Direction must match regime
    └─ Execution order: fastest movers first

         ▼

Position Manager (position_manager.py)
    │
    ├─ STALE WINNER EXIT: pnl >= +1%, is_stale 15+ min → book profit
    ├─ STALE LOSER EXIT:   pnl <= -1%, is_stale 30+ min → cut loss
    └─ Trailing stops: activate at 1% profit, 0.5% buffer, floor at 0.2%

         ▼

Hyperliquid Execution
    │
    └─ 10 max positions, 10X-20X leverage
```

---

## The Rules (What We Do Now)

### Entry Rules
1. **Every entry comes from the hot-set** — no exceptions, no shortcuts
2. **Speed filter:** `speed_percentile < 20` → blocked unless `conf >= 80` or `|vel_5m| > 1.0%`
3. **Speed boost:** `speed_percentile >= 70` → entry threshold 5% easier
4. **No stale entries:** If `is_stale AND z_score < 0` (in SHORT regime) or `is_stale AND z_score > 0` (in LONG regime) → this is a counter-trend trap, block it
5. **Z-score in ranging markets:** If regime is weak/mixed, don't use z-score as an entry trigger — use it as an exit signal instead

### Exit Rules
6. **Stale winner:** `pnl >= +1% AND is_stale 15+ min` → take the profit, find a faster wave
7. **Stale loser:** `pnl <= -1% AND is_stale 30+ min` → cut it, it's a dead position
8. **Wave turning:** If `z_score > +1.5 AND acceleration < 0` (top forming) → close longs
9. **Wave building:** If `z_score < -1.5 AND acceleration > 0` (bottom forming) → close shorts

### Position Sizing
10. **Fast movers, small size:** High speed = higher risk of reversal, use smaller positions
11. **Slow movers, larger size:** Low speed = stable wave, can size up slightly
12. **Max 10 positions** — spread across different wave speeds

---

## What "Wave Turning" Looks Like in Data

When SPEED + Z-Score both agree, the turn is high conviction:

```
TOP FORMING (bearish turn):
  z_score:    +2.0 (price far above mean)
  vel_5m:     declining from +0.5% to +0.1%  (wave losing energy)
  accel:      negative (velocity itself is slowing)
  → Action: Close longs, prepare for SHORT

BOTTOM FORMING (bullish turn):
  z_score:    -1.8 (price far below mean)
  vel_5m:     rising from -0.3% to +0.2%  (wave building)
  accel:      positive (velocity accelerating upward)
  → Action: Close shorts, look for LONG entry

RANGE-BOUND (no trade):
  z_score:    near 0
  vel_5m:     low, oscillating
  accel:      flipping signs
  → Action: Sit out. This isn't a wave — it's whitewater.
```

---

## Open Questions / Next Builds

- [ ] **Wave quality filter:** How to distinguish clean consistent swell from chaotic whitewater? Need an `hma_slope` or `trend_strength` metric beyond just velocity.
- [ ] **Entry timing:** Speed tells us a wave exists. But WHERE in the wave are we? Early (ideal), mid (still OK), late (about to close out). Need to add position-in-wave detection.
- [ ] **Regime strength signal:** Currently regime is binary LONG/SHORT. Should have a STRONG/WEAK axis — strong regime = z-score extremes are entries, weak regime = z-score extremes are exits.
- [ ] **Funding rate integration:** Add funding rate as "wind direction" — negative funding = tailwind for SHORTs, positive = tailwind for LONGs.
- [ ] **Wave-of-interest filter:** Instead of tracking all 536 tokens, focus on the top 50 that are: (a) in the current regime direction, (b) speed_percentile > 50, (c) not is_stale. These are the waves worth watching.
