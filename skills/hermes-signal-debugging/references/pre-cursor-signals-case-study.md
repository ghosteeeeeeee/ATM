# EIGEN Pre-Pump Signal Failure — Case Study
**Date:** 2026-05-05
**Symptom:** All signals caught EIGEN after the pump was already underway. Zero pre-cursor signals.

---

## The Move

```
5m candle timeline:
18:30 | V=173.9K | rng=0.60% | ← FIRST unusual volume spike (EIGEN avg ~20-30K)
18:55 | V=45.8K  | rng=0.65% | above avg volume, tight range
19:00 | V=100.8K | rng=0.54% | 4-5x normal volume, compressed range  
19:10 | V=91.5K  | rng=0.59% | sustained volume build
19:20 | V=257.5K | rng=1.08% | ← PUMP — 1.08% range + massive volume
19:30 | V=153.7K | rng=0.59% | continuation to 0.1882 (+15% from pre-pump low)
```

Pre-pump compression zone: **0.1837–0.1850** for ~45 minutes. Price was BELOW EMA(300).

---

## Why Each Signal Missed the Early Move

### `pct-hermes+` — Fires at WRONG TIME
- Measures: price position relative to session range
- Problem: fires when price is already at top of range — by the time it fires, the pump candle has already moved
- Fires: 21:00 candle when price already at 0.2082 (top of the move)

### `accel-300+` — Never Even Triggered
- Requires: price ABOVE EMA(300) with growing gap (gap is GROWING over 3 bars)
- Problem: EIGEN was BELOW EMA(300) during the entire accumulation phase
- The signal measures "breakout above EMA" momentum — incompatible with pre-pump accumulation

### `gap-300+` — Same Problem
- Fires: on cross ABOVE EMA300
- EIGEN crossed above EMA300 only AFTER the pump started (~21:00), not during accumulation

### `hzscore+` — Wrong Timeframe
- Measures: how far price has deviated from recent average (z-score)
- Problem: z-score is LOW during accumulation (price is grinding sideways, not deviating)
- z-score only spikes AFTER the pump is already underway

### `vel-hermes+` — Wrong Direction
- Pure acceleration signal — measures bar-to-bar momentum
- 0% WR, correctly blocked

### `macd_1m` (per-token tuned) — Fires In-Flight
- Fires on histogram crossover — by the time MACD crosses, the move has started
- Would have caught the pump at 19:20, but only if direction aligned with the pre-existing position

---

## The Core Problem: Signal Taxonomy

All existing signals fall into one of two categories:

### In-Flight Signals (detect momentum already underway)
- `pct-hermes+` — fires at price peak
- `accel-300+` — fires when gap above EMA is growing  
- `gap-300+` — fires on EMA cross
- `hzscore+` — fires when z-score is already high
- `macd_1m` — fires on MACD histogram cross
- `vel-hermes+` — fires on bar momentum

**These all require the move to already be happening.**

### Pre-Cursor Signals (detect accumulation before move)
- NONE currently exist in the Hermes signal library

**The tell that was available 30-40 minutes early:**
```
Volume 8-10x normal
Price range compressed (< 0.6% per 5m bar)
Price grinding sideways in a defined range (0.1837-0.1850)
```

This is the classic "smart money accumulating" pattern — large orders absorbed, price held down.

---

## New Signal Concepts

### 1. VOLRANGE_DIV — Volume/Range Divergence (Highest Priority)
**File:** `/root/.hermes/scripts/signals/volrange_div.py` (NOT YET CREATED)

```
Fire LONG when ALL of:
  - volume_ratio > 4.0x  (cur_vol / 20-bar avg vol)
  - range_ratio < 0.5x   (cur_range% / 20-bar avg range%)
  - 3+ consecutive bars of compression
  - price breaks above compression high with volume confirmation

Data: candles_5m in candles.db — no HL API calls
Lead time: 30-40 minutes before pump
```

### 2. BBWqueeze — Bollinger Band Width Compression
Fire when BBW(20,2) < 20th percentile AND candle breaks compression high.

### 3. VOLACCUM — Consecutive Above-Average Volume Bars
Fire when 4+ consecutive bars have volume > 2x avg while price stays in < 0.5% range.

### 4. EMARIBBON_FLAT — EMA Ribbon Compression
Fire when fast EMAs (3,5,8,10) and slow EMAs (30,35,40) converge within 0.3% for 10+ bars.

---

## Debugging Rule: Pre-Cursor vs In-Flight

When T says "signals caught it after the party ended" or "wrong side of the move":
1. Check if the signal is IN-FLIGHT type — if so, it's architecturally unable to catch pre-cursor patterns
2. Look for VOLUME buildup while price RANGE contracts — the classic accumulation signature
3. Implement a pre-cursor signal (volrange_div is the strongest candidate)

---

## Files Modified
- `/root/.hermes/plans/eigen-pre-pump-signal.md` — full plan/spec
