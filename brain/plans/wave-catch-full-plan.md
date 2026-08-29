# Wave Catch System — Full Plan

**Created:** 2026-08-28
**Status:** Phase 1 APPROVED (Medium Priority)
**CEO Decision:** 2026-08-28 (276th run)
**MoE Confidence:** 0.35/1.00 (LOW)

---

## Executive Summary

The wave catch system aims to enter on pre-wave support_resistance LONG signals and ride multi-day uptrend waves (+20-100%) with 3.0% trailing stops. The MoE panel found the edge is REAL but UNPROVEN, with critical blockers in risk architecture, regime suppression, and survivorship bias.

**CEO Decision:** Approve Phase 1 backtest only. System crisis is signal starvation (ZERO backbone), not new strategy.

---

## The Opportunity

### What We Found (Aug 17-22 Wave)

9 coins moved +20-100% over 5 days:

| Coin | Peak Return | Pre-Wave Signal | Signal Price | Potential |
|------|-------------|-----------------|--------------|-----------|
| ENA | +100.5% | support_resistance Aug 17 | 0.08296 | +100.0% |
| IOTA | +50.7% | support_resistance Aug 17 | 0.03179 | +55.2% |
| ARB | +45.4% | r2_trend_long Aug 17 | 0.07472 | +46.4% |
| DOGE | +43.6% | r2_trend_long Aug 18 | 0.07026 | +43.5% |
| CC | +36.0% | support_resistance Aug 19 | 0.08991 | +38.1% |
| GMT | +33.3% | support_resistance Aug 19 | 0.00590 | +33.9% |
| DYDX | +31.6% | r2_trend_long Aug 17 | 0.10142 | +32.5% |
| COMP | +19.6% | r2_trend_long Aug 19 | 17.744 | +17.9% |
| BANANA | +21.8% | support_resistance Aug 19 | 3.642 | +21.4% |

### The Core Insight

**ALL 28 pre-wave support_resistance LONG signals eventually won.** The problem is NOT signal quality — it's stop management.

---

## Surfing Philosophy (From `brain/surfing.md`)

Trading is like surfing. You can't force a wave — you read it, position yourself, and let it carry you.

### The Three Axes of a Wave Catch

| Surf Element | Wave Catch Equivalent | Key Question |
|---|---|---|
| **Wave direction** | Regime (LONG/SHORT) | Are we riding with the tide? |
| **Wave speed** | Token velocity + z-score | Is the wave building or collapsing? |
| **Wave shape** | Compression → breakout | Clean wall vs whitewater? |

### The 4 Quadrants (Z-Score + Speed)

From `surfing.md` — the key insight for wave detection:

| Z-Score | Speed | Acceleration | Interpretation | Action |
|---|---|---|---|---|
| Near 0 | Low | Flat | Range-bound, no wave | Sit out, don't paddle |
| **Negative (oversold)** | **HIGH** | **Positive** | **Wave building UP — bottom picked** | **Paddle for LONG** |
| Negative (oversold) | LOW | Positive | Wave building but slow | Wait, too early |
| Positive (overbought) | HIGH | Negative | Wave cresting — top in | Take SHORT, grab rail |
| Positive (overbought) | LOW | Negative | Wave collapsing from high | Exit LONGs |
| Near 0 | HIGH | Positive | Mid-range explosion building | Confirm with confluence |

**For wave catching, we want:** Z-Score moving from negative toward 0 + Speed increasing + Acceleration positive = "Wave building UP"

---

## ZScore Wave Detection Component

**Concept:** Use z-score to detect when a coin is transitioning from consolidation (compression) to trend (expansion).

### How ZScore Finds Pumps

From `surfing.md`:
- **Z-Score = (current_price - 20h_mean) / 20h_std**
- Negative z-score = price is low relative to history (potential bottom)
- When z-score crosses from negative to positive with speed = wave starting

### ZScore Wave Catch Signals

| Signal | What It Detects | When to Use |
|--------|-----------------|-------------|
| `zscore_pump_long` | z > threshold = upward momentum | Ride the wave once confirmed |
| `zscore_rising_long` | z-score crossing threshold + velocity aligning | Catch the wave at onset |
| `hzscore_long` | Histogram z-score reversal | Detect momentum shift |

### The Compression → Expansion Pattern

```
Phase 1: COMPRESSION (z-score near 0, low volatility)
  → ATR shrinking, bollinger bands tightening
  → Price oscillating around 20h mean
  → Speed low, acceleration flat
  → ACTION: Watch, don't enter

Phase 2: ACCUMULATION (z-score slightly negative, volume building)
  → Smart money accumulating
  → Price testing support repeatedly
  → Speed starting to increase
  → ACTION: Prepare to enter

Phase 3: BREAKOUT (z-score crosses 0, speed spikes)
  → Wave confirmed
  → Volume expanding
  → Acceleration positive
  → ACTION: Enter LONG

Phase 4: TREND (z-score positive, speed sustained)
  → Wave riding
  → Higher highs, higher lows
  → ACTION: Trail stop, add position

Phase 5: BLOWOFF (z-score extreme positive, speed declining)
  → Wave exhausted
  → Volume spike on reversal
  → ACTION: Exit, take profit
```

### ZScore Entry Rules

```python
# Wave Catch ZScore Entry Conditions
WAVE_CATCH_ZSCORE_ENTRY = {
    'z_cross_threshold': 0.0,      # z-score crosses from negative to positive
    'z_min_at_cross': -0.5,        # must have been below -0.5 before crossing
    'speed_min_percentile': 50,    # fish must be moving
    'accel_must_be': 'positive',   # velocity must be increasing
    'rsi_range': (30, 70),         # not overbought or oversold
    'volume_ratio': 1.2,           # volume must be 1.2x average
}
```

---

## Retroactive Scanning: Spot Compressions in Hindsight

**Concept:** Instead of waiting for signals to fire, actively scan for compression patterns and prepare entries.

### The Problem with Forward-Only Scanning

Current system: Wait for signal → Evaluate → Enter
- Problem: By the time signal fires, wave may have already started
- Problem: Misses the compression phase where entry is optimal

### Retroactive Scanning Approach

**Step 1: Identify Compressions (Hindsight)**
```python
# Scan for ATR compression over last 48-72 hours
def detect_compression(candles_15m, lookback_hours=72):
    """
    Find periods where:
    1. ATR has been declining for N periods
    2. Bollinger bands are tightening
    3. Price is oscillating around a mean
    4. Volume is declining (calm before storm)
    """
    # Return: compression_start, compression_end, support_level, resistance_level
```

**Step 2: Monitor for Breakout (Real-Time)**
```python
# Once compression detected, watch for breakout
def monitor_breakout(compression, current_price, current_volume):
    """
    Trigger when:
    1. Price breaks above resistance_level
    2. Volume expands (1.5x average)
    3. ATR starts expanding
    4. Z-score crosses from negative to positive
    """
    # Return: breakout_confirmed, entry_price, stop_level
```

**Step 3: Enter on Confirmation (Not Too Late)**
```python
# Enter AFTER breakout confirmed, not during compression
WAVE_CATCH_RETROACTIVE_ENTRY = {
    'compression_min_hours': 48,      # minimum compression duration
    'breakout_volume_ratio': 1.5,     # volume must spike on breakout
    'breakout_atr_expansion': 1.2,    # ATR must expand 20%
    'z_score_cross': True,            # z-score must cross 0
    'confirmation_candles': 2,        # wait 2 candles (30min) to confirm
}
```

### Why "Not Too Late" Matters

From `surfing.md`:
> "Timing the paddle — too early/late = wipeout"

The sweet spot is:
- **Too early:** During compression (price still ranging, no momentum)
- **Sweet spot:** On breakout confirmation (1-2 candles after break, z-score crossing 0)
- **Too late:** After +10% move (z-score already positive, speed declining)

### Retroactive Scan Output

```json
{
  "token": "ENA",
  "compression_start": "2026-08-15 00:00",
  "compression_end": "2026-08-17 12:00",
  "compression_hours": 60,
  "support_level": 0.08200,
  "resistance_level": 0.08400,
  "breakout_detected": "2026-08-17 13:00",
  "entry_price": 0.08450,
  "stop_level": 0.08200,
  "risk_pct": 3.0,
  "z_score_at_entry": 0.15,
  "speed_percentile": 72,
  "wave_potential": "+100%"
}
```

---

## Wave Catch Signal Stack (Integrated)

### Entry Signal Combination

```
Primary:   support_resistance (structural support)
Confirm:   zscore_rising (z-score crossing threshold)
Filter:    r2_trend_long (trend confirmation)
Volume:    Volume expanding > 1.2x average
Regime:    4h regime = NEUTRAL or LONG_BIAS (not SHORT_BIAS)
```

### The Wave Catch Sequence

```
1. RETROACTIVE SCAN: Detect compression (ATR shrinking, BB tightening)
2. MONITOR: Watch for breakout (price > resistance, volume expanding)
3. CONFIRM: Z-score crosses 0, speed percentile > 50, acceleration positive
4. ENTER: support_resistance fires at breakout level
5. TRAIL: 3.0% initial → 2.5% at +5% → 2.0% at +10%
6. EXIT: Blowoff signal (RSI > 80, volume spike, z-score > 2.0)
```

### From `surfing.md` — The Pipeline (Updated for Wave Catch)

```
Retroactive Scanner (NEW)
    │
    ├─ Detect compression patterns (48-72h ATR decline)
    ├─ Identify support/resistance levels
    └─ Queue tokens for monitoring

         ▼

Signal Generation (signal_gen.py)
    │
    ├─ ZSCORE FILTER: z-score must be crossing 0 (not already positive)
    ├─ SPEED FILTER: speed_percentile >= 50 (wave has energy)
    ├─ VOLUME FILTER: volume > 1.2x average (real participation)
    └─ Signals written to signals DB

         ▼

Wave-Catch Compactor (NEW)
    │
    ├─ Score = z_score_cross + speed + volume + compression_quality
    ├─ Compression quality: longer compression = higher score
    └─ Keep top 5 wave-catch candidates

         ▼

Wave-Catch Risk Module (NEW)
    │
    ├─ Entry: breakout confirmed (2 candles after break)
    ├─ Stop: 3.0% from entry (not standard ATR stop)
    ├─ Trail: 2.5% at +5%, 2.0% at +10%
    ├─ Exit: blowoff signal (RSI > 80, z > 2.0)
    └─ Bypasses: Cut Loser, Profit Monster, MAE Guard

         ▼

Hyperliquid Execution
    │
    └─ Max 4 wave-catch positions, 3x-5x leverage
```

---

## MoE Panel Results

### Expert Verdicts

| Expert | Weight | Verdict | Key Finding |
|--------|--------|---------|-------------|
| Signal Analyst | 0.25 | HIGH quality | RS logic sound, needs standalone bypass for wave catching |
| Risk Manager | 0.30 | MEDIUM-HIGH risk | 3 existing systems would kill positions before 3% stop works |
| Statistician | 0.25 | INSUFFICIENT data | 1285 signals, 0 outcomes. Survivorship bias invalidates "100% win rate" |
| Regime Analyst | 0.20 | SKIP scanners | signal_compactor penalizes NEUTRAL by 50%, suppressing entries |

### Critical Blockers Found

#### Blocker 1: Survivorship Bias (Statistician)
- **1285** support_resistance LONG signals fired Aug 14-22
- **ZERO** have recorded outcomes (none were actually traded)
- The "28/28 wins" are signals we CHOSE after the fact as "pre-wave"
- Real win rate: UNKNOWN (need to backtest ALL 1285 signals)
- Effective sample: n=8 (independent coins), not n=28
- Confidence interval: 63-100% (wide due to small sample)

#### Blocker 2: Risk Architecture Conflicts (Risk Manager)
Three existing systems would kill wave-catch positions:

| System | Current Behavior | Conflict |
|--------|-----------------|----------|
| **Cut Loser** | Exits at -1.0% to -2.0% | Kills BEFORE 3% stop can work |
| **Profit Monster** | Closes at +1-2% | Kills winners BEFORE wave captures +17-30% |
| **MAE Guard** | Exits at 3.0% | FIGHTS with 3.0% trailing stop |

**Result:** Without a dedicated wave-catch risk module, the wider stops are meaningless.

#### Blocker 3: Regime Suppression (Regime Analyst)
- All 8 wave-catch coins were NEUTRAL regime pre-wave
- signal_compactor applies **50% penalty** to NEUTRAL regime signals
- This SUPPRESSES the very entries that capture +27-100% moves
- Current regime scanners detect trends AFTER they start (+7-19%), not before

#### Blocker 4: Sample Too Small (Statistician)
- n=28 signals, but effective n=8 (independent coins)
- Multiple signals on same coin during same event = pseudo-replication
- Need 90+ days across 20+ coins for statistical validity

---

## Trailing Stop Analysis (Verified)

| Coin | Entry | 1.0% | 2.0% | 3.0% | 4.0% | 5.0% |
|------|-------|------|------|------|------|------|
| GMT | 0.005898 | -1.0% (08/19) | +2.7% (08/19) | **+29.9% (08/22)** | +28.5% (08/22) | +27.2% (08/22) |
| DYDX | 0.10165 | +0.6% (08/19) | +2.6% (08/19) | **+18.1% (08/21)** | +16.9% (08/21) | +15.6% (08/21) |
| COMP | 17.744 | -0.6% (08/19) | +0.5% (08/19) | +6.5% (08/20) | +5.4% (08/21) | **+12.0% (08/22)** |
| BANANA | 3.642 | -0.8% (08/19) | -1.8% (08/19) | **+17.7% (08/22)** | +16.5% (08/22) | +15.3% (08/22) |
| CC | 0.08991 | +0.2% (08/19) | +9.0% (08/19) | +10.3% (08/20) | +12.1% (08/20) | +10.9% (08/20) |

**Key insight:** 3.0% trailing stop is the sweet spot for most coins. All stops were eventually hit at the blowoff — the goal is to capture the wave, not avoid the blowoff.

---

## CEO Decision (2026-08-28)

**APPROVE Phase 1 (backtest) — Priority: MEDIUM**

### Rationale
1. System crisis is signal starvation (ZERO backbone), not new strategy
2. MoE is right — n=8 is not actionable. Backtest costs nothing
3. Bypassing 3 risk systems is dangerous without proof of edge
4. NEUTRAL regime suppression is the real blocker — fix confluence scoring first

### Order of Operations
1. **Backbone signal** (already delegated — must produce)
2. **Confluence scoring fix** (reduce NEUTRAL penalty from 50% to 25%)
3. **Wave catch backtest** (delegate to signal_analyst)
4. **Only then:** Phase 2 risk module

---

## Implementation Plan

### Phase 1: Validate the Edge (APPROVED — DO FIRST)

**Goal:** Find the REAL win rate of support_resistance LONG signals + zscore component

**Task:** Backtest ALL 1285 support_resistance LONG signals (Aug 14-22) WITH zscore filter

**Steps:**
1. Query trades table for support_resistance LONG signals with outcomes
2. For signals without recorded outcomes, fetch historical price data (5m candles)
3. Simulate entry at signal time, track price for 72h
4. **Add zscore filter:** Only count signals where z-score was crossing 0 at entry
5. Calculate: WR, avg win%, avg loss%, R:R, max drawdown
6. Break down by: regime (NEUTRAL vs LONG_BIAS), coin, confidence tier, z-score state
7. **Compare:** RS-only WR vs RS+zscore WR (does zscore improve selection?)
8. Return: full statistical report with confidence intervals

**Decision gate:** If backtest WR > 55% with 50+ outcomes → approve Phase 2. Otherwise, kill proposal.

**Owner:** signal_analyst
**Deadline:** This week

### Phase 2: Build Infrastructure (BLOCKED until Phase 1 proves edge)

**Goal:** Build retroactive scanner + wave-catch risk module

**Component A: Retroactive Compression Scanner**
```python
# Scan for ATR compression patterns
def scan_compressions(candles_15m, lookback_hours=72):
    """
    Detect:
    1. ATR declining for N periods (compression)
    2. Bollinger bands tightening (volatility squeeze)
    3. Price oscillating around mean (z-score near 0)
    4. Volume declining (calm before storm)
    
    Return: compression_start, support_level, resistance_level, quality_score
    """
```

**Component B: Breakout Monitor**
```python
# Watch compressed tokens for breakout
def monitor_breakout(compression, current_price, current_volume, z_score):
    """
    Trigger when:
    1. Price breaks above resistance_level
    2. Volume expands (1.5x average)
    3. ATR starts expanding
    4. Z-score crosses from negative to positive
    
    Return: breakout_confirmed, entry_price, stop_level
    """
```

**Component C: Wave-Catch Risk Module**
```
Wave-Catch Risk Module:
├── Entry: breakout confirmed (2 candles after break + zscore cross)
├── Initial stop: 3.0% from entry
├── Tightening: 2.5% at +5%, 2.0% at +10%
├── Exit: Blowoff signal (RSI > 80, z-score > 2.0, volume spike)
├── Bypasses: Cut Loser, Profit Monster, MAE Guard
└── Max positions: 4 concurrent
```

**Owner:** signal_analyst + CEO
**Status:** BLOCKED

### Phase 3: Paper Trading (BLOCKED until Phase 2 approved)

**Goal:** Validate retroactive scanner + zscore filter in real-time

**Steps:**
1. Run retroactive scanner on all tracked tokens
2. Log compressions detected (not just signals that fire)
3. Track breakout detections vs actual moves
4. **Key metric:** What % of detected compressions actually break out?
5. Compare zscore-filtered entries vs raw entries
6. Shadow mode for 2 weeks (log without trading)

**Gate:** >55% WR with 50+ signals → enable live

**Owner:** signal_analyst
**Status:** BLOCKED

### Phase 4: Deploy (BLOCKED until Phase 3 passes)

**Goal:** Go live with small position sizes

**Steps:**
1. Start with 50% position sizing
2. Monitor for 1 week
3. If stable, increase to 100%
4. Continuous monitoring

**Owner:** signal_analyst
**Status:** BLOCKED

---

## Wave Quality Score (For Future Use)

**Pre-trade filter:**

Score = (HH/HL consistency × 0.3) + (Trend purity × 0.3) + (Pullback frequency × 0.2) + (Volume trend × 0.2)

- HH/HL consistency: % of 4h blocks with both HH and HL
- Trend purity: R² of price vs time over 3 days
- Pullback frequency: Number of >2% pullbacks per day
- Volume trend: Slope of volume over the wave

**Minimum score to trade:** 0.6

---

## Coin Selection (For Future Use)

### Best Wave Catch Candidates (Aug 19-22)

| Coin | Grade | Pre-Wave Signal | Peak Return |
|------|-------|-----------------|-------------|
| IOTA | A+ | support_resistance Aug 17 | +55.2% |
| ENA | A | support_resistance Aug 17 | +100.0% |
| ARB | A | r2_trend_long Aug 17 | +46.4% |
| DOGE | B+ | r2_trend_long Aug 18 | +43.5% |

### Tradeable with Wider Stops

| Coin | Grade | Pre-Wave Signal | Peak Return |
|------|-------|-----------------|-------------|
| DYDX | B+ | r2_trend_long Aug 17 | +32.5% |
| GMT | B+ | support_resistance Aug 19 | +33.9% |
| BANANA | B+ | support_resistance Aug 19 | +21.4% |
| CC | A | support_resistance Aug 19 | +38.1% |

### Skip

| Coin | Why |
|------|-----|
| COMP | Too jagged, 3% trail only captures +6.5% |

---

## Signal Analyst Recommendations (For Future Use)

### support_resistance Signal Modifications

1. **Add to STANDALONE_BYPASS_SIGNALS** — allow RS to fire without co-signal for wave catching
2. **Add explicit LONG weight** — boost RS LONG to 1.2 (currently default 1.0)
3. **Allow confidence range** — RS_MIN_CONFIDENCE = 75, RS_MAX_CONFIDENCE = 88 (currently hardcoded to 88)
4. **Fix regime timeframe mismatch** — RS uses 5m regime, wave catch needs 4h

### Regime Detector Modifications

1. **Lower thresholds** — slope > 0.10, r2 > 0.30 (currently slope > 0.35, r2 > 0.50)
2. **Longer lookback** — 24-30 4h candles (4-5 days, not 6)
3. **Don't penalize wave-catch signals in NEUTRAL** — reduce penalty from 50% to 25%

---

## Risk Management (For Future Use)

### Wave-Catch Risk Module Design

```python
# Bypass lists for wave-catch positions
WAVE_CATCH_BYPASS_SIGNALS = ['support_resistance', 'r2_trend_long']
WAVE_CATCH_MAX_POSITIONS = 4
WAVE_CATCH_INITIAL_STOP = 3.0  # %
WAVE_CATCH_TIGHTENING = {
    5.0: 2.5,   # At +5%, tighten to 2.5%
    10.0: 2.0,  # At +10%, tighten to 2.0%
}
WAVE_CATCH_MAE_THRESHOLD = 4.0  # % (higher than standard 3.0%)
```

### BTC Stability Gate

```python
# Block wave-catch entries when BTC is falling
BTC_MOMENTUM_THRESHOLD = -0.15  # % per 30m
```

### Position Limits

```python
# Cap concurrent wave-catch positions
WAVE_CATCH_MAX_CONCURRENT = 4
WAVE_CATCH_CORRELATION_LIMIT = 2  # Max 2 from same sector
```

---

## Files

| File | Purpose |
|------|---------|
| `brain/plans/wave-catch-plan.md` | Updated plan with audit corrections |
| `brain/plans/wave-catch-full-plan.md` | This file (comprehensive plan) |
| `brain/moe-log/2026-08-28-wave-catch-system.md` | MoE decision log |
| `brain/verdicts/wave-catch-audit-20260828.md` | Audit v1 |
| `brain/verdicts/wave-catch-audit-v2-20260828.md` | Audit v2 |
| `automation/ceo/ceo_report.md` | CEO decision report |
| `automation/ceo/ceo_action_plan.md` | CEO action items |

---

## Audit Trail

| Version | Date | Key Changes |
|---------|------|-------------|
| v1 | 2026-08-28 | Initial plan |
| v2 | 2026-08-28 | Corrected signal entries (audit v1) |
| v3 | 2026-08-28 | Corrected core problem: stop management (audit v2) |
| v4 | 2026-08-28 | MoE panel + CEO decision: Phase 1 backtest approved |
| **v5** | **2026-08-28** | **Added: zscore component, retroactive scanning, surfing philosophy** |
