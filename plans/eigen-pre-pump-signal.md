# EIGEN Pre-Pump Signal — Research Spec
**Date:** 2026-05-05
**Status:** RESEARCH COMPLETE — READY TO IMPLEMENT

---

## What Happened

EIGEN pumped ~15% in ~45 minutes on May 5, 2026.

```
5m candle timeline:
18:30 | V=173.9K | rng=0.60% | ← FIRST unusual volume spike, price compressed
18:55 | V=45.8K  | rng=0.65% | ← above avg volume, tight range
19:00 | V=100.8K | rng=0.54% | ← 4-5x normal volume, compressed range  
19:10 | V=91.5K  | rng=0.59% | ← sustained volume build
19:20 | V=257.5K | rng=1.08% | ← PUMP — 1.08% range + massive volume
19:30 | V=153.7K | rng=0.59% | ← continuation to 0.1882
```

Pre-pump compression zone: **0.1837–0.1850** for ~45 minutes.

Price was BELOW EMA(300) during accumulation — so breakout signals that measure gap-above-EMA (accel-300, gap-300) would NOT have fired early.

---

## Why Existing Signals Failed

| Signal | Problem |
|--------|---------|
| `pct-hermes+` | Measures position at top of range — fires AFTER move starts |
| `pct-hermes-` | Catches knives — 0% WR, blocked |
| `accel-300+` | Requires price above EMA(300) with growing gap — EIGEN was BELOW EMA during accumulation |
| `gap-300+` | Fires on cross above EMA300 — no cross until after pump starts |
| `hzscore+` | Needs high z-score — z-score is low during accumulation |
| `vel-hermes+` | 0% WR, blocked |
| `macd_1m` | Fires on histogram cross — fires after momentum is already visible |

**Root cause:** All existing signals measure things that happen AFTER a move starts.
No signal detects the *pre-cursor pattern*: smart money accumulating in a compressed range.

---

## Signal Concepts (Priority Order)

### 1. VOLRANGE_DIV — HIGHEST POTENTIAL ✓
**Concept:** Volume SPIKES while price range CONTRACTS.
Classic "smart money accumulation" pattern — large orders absorbed, price held down.

```
Fire LONG when ALL of:
  - volume_ratio > 4.0x  (current vol / 20-bar avg vol)
  - range_ratio < 0.5x   (current range% / 20-bar avg range%)
  - price break above compression high on volume confirmation
```

**Early detection window:** 30-40 minutes before pump

**Data source:** `ohlcv_1m` in `signals_hermes.db` (HL-sourced volume — NOT candles.db which is Binance with 0.0 volume)

> **CRITICAL:** candles.db candles_1m/candles_5m tables have 0.0 volume for EIGEN because EIGEN isn't actively traded on Binance. The real volume is in `signals_hermes.db`'s `ohlcv_1m` table, which is sourced from Hyperliquid. All volume-based signals must read from `ohlcv_1m`, NOT from candles.db.

**File:** `/root/.hermes/scripts/signals/volrange_div.py`

---

### 2. BBWqueeze — MEDIUM POTENTIAL
**Concept:** Bollinger Band width contracts to multi-hour low → squeeze precedes expansion.

```
Fire when:
  - BBW(20,2) < 20th percentile of 50-bar rolling window
  - Candle breaks compression high with volume > 2x avg
```

**Early detection window:** 20-30 minutes before pump

---

### 3. VOLACCUM — MEDIUM POTENTIAL
**Concept:** 4+ consecutive bars above-average volume while price stays in tight range.

```
Fire when ALL of:
  - 4+ consecutive 5m bars with volume > 2x 20-bar avg
  - Total range of those 4 bars < 0.5%
  - Price breaks above compression high on next bar
```

**Early detection window:** 20-30 minutes before pump

---

### 4. EMARIBBON_FLAT — LOWER POTENTIAL
**Concept:** Fast EMAs (3,5,8,10) and slow EMAs (30,35,40) converge to tight spread for 10+ bars → breakout imminent.

`guppy.py` already does the cross detection — this adds the *pre-breakout compression* component.

---

## Implementation Plan

### Phase 1: volrange_div.py (Priority)
1. Create `/root/.hermes/scripts/signals/volrange_div.py`
2. Read OHLCV from `ohlcv_1m` table in `signals_hermes.db` (HL-sourced, has real volume)
3. For each token in prices_dict:
   - Fetch last 25 1m bars from `ohlcv_1m`
   - Aggregate into 5m bars for the rolling window (or work at 1m resolution)
   - Compute rolling avg volume and avg range% (bar range = high-low)
   - Current bar: volume_ratio = cur_vol / avg_vol, range_ratio = cur_range% / avg_range%
   - Track compression state: 3+ consecutive bars with range_ratio < 0.7x AND volume_ratio > 2x
   - Fire signal when compression breaks to upside with volume > 3x avg
4. Write via `signal_schema.add_signal()`
5. Add to `signals/__init__.py` registry
6. Add to `signal_compactor.py` SOURCE_WEIGHTS with conservative weight (1.0 initially)

### Phase 2: Backtesting
- Run against 30+ days of 5m candle data
- Validate on EIGEN and other known pump events
- Tune volume_ratio threshold and range_ratio threshold

### Phase 3: Integration
- Require confluence with structural support check (price within 1 ATR of HH/HL level)
- Add to hot-set scoring pipeline

---

## Files to Modify/Create

| File | Action |
|------|--------|
| `/root/.hermes/scripts/signals/volrange_div.py` | CREATE |
| `/root/.hermes/scripts/signals/__init__.py` | MODIFY — add registry entry |
| `/root/.hermes/scripts/signal_compactor.py` | MODIFY — add SOURCE_WEIGHTS entry |
| `/root/.hermes/scripts/signal_gen.py` | MODIFY — add scan call |

---

## Key Parameters (Starting Values — to be tuned)

```
VOL_RATIO_FIRE     = 3.0   # volume must be 3x avg to qualify
RANGE_RATIO_FIRE   = 0.5   # range must be < 0.5x avg (compressed)
COMPRESS_BARS      = 3     # 3+ consecutive compressed bars required
BREAK_PCT          = 0.3   # close must break above compression high by this %
MIN_VOL            = 20_000 # minimum USD volume to qualify
COOLDOWN_BARS      = 8     # bars between fires
LOOKBACK_5M        = 50    # 5m bars to fetch
```
