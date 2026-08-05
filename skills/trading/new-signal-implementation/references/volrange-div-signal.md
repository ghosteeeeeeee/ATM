# Pre-Cursor Signal Design: volrange_div
**Signal:** Volume/Range Divergence — detect accumulation before a move starts
**Status:** NOT YET IMPLEMENTED — planned from EIGEN case study (2026-05-05)
**File to create:** `/root/.hermes/scripts/signals/volrange_div.py`

---

## The EIGEN Pattern That Motivated This

```
5m candle timeline (May 5, 2026):
18:30 | V=173.9K | rng=0.60% | ← FIRST unusual volume spike (EIGEN avg ~20-30K)
18:55 | V=45.8K  | rng=0.65% | above avg volume, tight range
19:00 | V=100.8K | rng=0.54% | 4-5x normal volume, compressed range  
19:10 | V=91.5K  | rng=0.59% | sustained volume build
19:20 | V=257.5K | rng=1.08% | ← PUMP — 1.08% range + massive volume (+15% in 45min)
```

**Lead time potential: 30-40 minutes before pump was detectable.**

Price ranged 0.1837–0.1850 for ~45 minutes before pumping. Classic "smart money accumulating" — large orders absorbed, price held in tight range.

---

## Core Concept: Pre-Cursor vs In-Flight Signals

All existing signals are **in-flight** — they measure momentum that only exists AFTER a move starts:
- `pct-hermes+` — fires at price peak (already at top of range)
- `accel-300+` — requires price above EMA(300) with growing gap
- `gap-300+` — fires on EMA cross (no cross until after pump starts)
- `hzscore+` — fires when z-score is already high (low during accumulation)
- `macd_1m` — fires on histogram cross (after momentum is visible)

**Pre-cursor signals** detect the setup BEFORE the move: volume building into a compressed range.

---

## Signal Logic: volrange_div

### State Machine

```
State: NORMAL
  → If 3+ consecutive bars with volume_ratio > 2.0x AND range_ratio < 0.7x
  → transition to COMPRESSING

State: COMPRESSING  
  → If price breaks above compression_high AND volume_ratio > 3.0x
  → FIRE LONG, transition to NORMAL
  → If price breaks below compression_low AND volume_ratio > 3.0x
  → FIRE SHORT, transition to NORMAL
  → If 8 bars pass without breakout → transition to NORMAL (failed setup)
  → Update compression high/low with each bar

State: NORMAL (after fire)
  → cooldown of 8 bars before new compression can be tracked
```

### Detection Parameters

```python
VOL_RATIO_COMPRESS = 2.0   # volume must be 2x avg to count as "building"
RANGE_RATIO_COMPRESS = 0.7  # range must be < 0.7x avg to count as compressed
COMPRESS_BARS = 3            # 3+ consecutive bars required
VOL_RATIO_BREAK = 3.0       # breakout volume must be 3x avg
RANGE_RATIO_BREAK = 0.5     # breakout range must be < 0.5x avg (compressed)
BREAK_PCT = 0.3             # close must break above compression high by 0.3%
COOLDOWN_BARS = 8
LOOKBACK_5M = 50
MIN_VOL_USD = 20_000        # minimum USD volume to qualify
```

### Data Source
- `candles_5m` in `candles.db` — no HL API calls
- Price from `price_history` in `signals_hermes.db` for current price

### Confidence Scoring
```python
base_conf = 70
volume_bonus = min((vol_ratio - 3.0) * 5, 15)   # +5 per extra x volume
range_bonus = min((0.7 - range_ratio) * 30, 10)   # tighter range = bonus
compression_len_bonus = min((compress_bars - 3) * 3, 6)  # longer compression = bonus
confidence = min(base_conf + volume_bonus + range_bonus + compression_len_bonus, 92)
```

---

## Implementation Checklist

- [ ] Create `/root/.hermes/scripts/signals/volrange_div.py`
- [ ] Add to `signals/__init__.py` registry
- [ ] Add to `signal_compactor.py` SOURCE_WEIGHTS with weight 1.0 (conservative start)
- [ ] Write backtest script — validate on 30+ days of 5m data
- [ ] Test on EIGEN and other known pump events
- [ ] Tune: volume_ratio thresholds, range_ratio thresholds, compression bars

---

## Backtest Methodology

**IMPORTANT: Use survival analysis (exit on reverse signal), NOT fixed TP/SL.**
See `new-signal-implementation.md` §4 for full backtest methodology.

Test on: EIGEN, and 10+ other tokens with known pump events (>10% in <2h).
Verify lead time — signal must fire BEFORE the pump candle, not during or after.

---

## Related
- Plan: `/root/.hermes/plans/eigen-pre-pump-signal.md`
- Case study: `references/pre-cursor-signals-case-study.md` (in `hermes-signal-debugging`)
