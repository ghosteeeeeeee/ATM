# BTC Wave Pattern Surfer — Catch the Repeatable Macro Move

**Created:** 2026-09-04 00:10 UTC
**Status:** Spec — needs signal implementation
**Priority:** HIGH — this is the new primary BTC strategy

---

## The Pattern (Sep 3, 2026 — First Observed)

BTC printed a **+5.10% move** (77,340 → 81,270) in a clean, repeatable structure:

### Phase Breakdown

| Phase | Time (UTC) | Duration | Price Move | Volume | What Happens |
|-------|-----------|----------|------------|--------|-------------|
| **1. Chop/Coil** | 01:00-10:00 | 9 hours | Range: 76,968-78,183 | Low (20-60 BTC/5min) | Price oscillates around EMA300, multiple failed crosses. The "paddling" zone — you're waiting, not riding. |
| **2. The Cross** | 11:04 | 1 min | 77,752 (crosses EMA300) | Still low | **THE PADDLE MOMENT.** Price crosses above EMA300 and holds. This is when you start paying attention. |
| **3. Slow Build** | 11:04-12:30 | 86 min | +0.66% | Gradual increase | Price drifts higher above EMA300. Volume slowly builds. The wave is forming but hasn't broken yet. |
| **4. Volume Explosion** | 12:30-15:00 | 2.5 hours | +3.2% | 20 → 757 BTC/5min (**38x**) | **THE WAVE.** Volume goes parabolic. Price rips. This is the meat of the move. |
| **5. Grind/Digest** | 15:00-17:00 | 2 hours | +0.25% | Decreasing | Price holds gains, volume drops. Move is over. |
| **6. Consolidation** | 17:00+ | - | Sideways | Normal | Normal trading resumes. |

### Key Numbers

- **Total move:** +5.10% ($3,930 on BTC)
- **Wave portion (cross → peak):** +4.60% in ~4 hours
- **Volume spike:** 38x increase from baseline
- **EMA300 distance at peak:** +1.31% above
- **Time above EMA300:** 677 minutes (11+ hours) — the longest continuous stretch of the day

---

## The Surfing Analogy (From surfing.md)

This maps perfectly to the surfing framework:

| Surf Element | This Pattern |
|---|---|
| **Wave direction** | LONG — price crosses and holds above EMA300 |
| **Paddling** | The 11:04 cross — you start paddling when price confirms above EMA300 |
| **Catching the wave** | Volume confirmation at 12:30 — the wave has energy now |
| **Riding the face** | 12:30-15:00 — the parabolic volume + price expansion |
| **Wiping out / exiting** | 15:00+ — volume drops, price grinds sideways, time to take profit |

### The Critical Insight

**You don't enter at the bottom. You enter when the trend CONFIRMS.**

The EMA300 crossover at 11:04 is the paddle moment. But the real entry should be when volume confirms the trend — around 12:30 when the first volume spike hits. That's when the wave has energy.

If you entered at the cross (77,752) and rode to the peak (81,370): **+4.65%**
If you entered at volume confirmation (78,265) and rode to the peak: **+3.97%**
Both are massive. The cross gives you早 entry; volume confirmation gives you conviction.

---

## Detection Criteria (Signal Spec)

### Primary Signal: EMA300 Crossover + Volume Surge

```
TRIGGER CONDITIONS:
1. BTC 1m close crosses ABOVE EMA300
2. Price stays above EMA300 for 5+ consecutive minutes (not a fake-out)
3. Volume begins increasing (5min rolling avg > 1.5x of 1hr rolling avg)

CONFIRMATION (optional but improves timing):
4. 30-min rolling price acceleration turns positive
5. Volume spike: 5min bucket > 2x previous 5min bucket

ENTRY:
- LONG BTC (or BTC-perp with leverage)
- Entry at confirmation of cross + volume (Phase 3)
- Size: Full position (this is a high-conviction setup)

EXIT:
- Volume drops below 50% of peak for 15+ minutes
- OR price drops below EMA300
- OR trailing stop activates (1% trail from peak)
- OR 12 hours elapsed since cross (time-based exit)
```

### Anti-Fake-Out Filters

The Sep 3 data shows multiple failed crosses before the real one:
- 00:01-00:06: 5 min above → fail
- 01:07-02:04: 57 min above → fail
- 02:05-02:07: 2 min above → fail
- 02:10-05:17: 187 min above → fail (longest false positive)
- 05:50-07:50: 120 min above → fail
- 08:00-09:28: 88 min above → fail
- 10:52-10:54: 2 min above → fail
- 10:55-10:58: 3 min above → fail
- 10:59-11:03: 4 min above → fail
- **11:04-22:21: 677 min above → THE REAL ONE**

**The real wave was 7x longer than the longest false positive (187 min vs 677 min).**

Key differentiator: **Volume.** During the false crosses, volume stayed flat. During the real wave, volume exploded 38x. The signal should require:
1. Duration above EMA300 > 60 minutes (filter out the 2-5 min noise)
2. Volume increasing during the above-EMA period
3. 30-min price acceleration turning positive

---

## Implementation Plan

### Step 1: BTC EMA300 Crossover Detector
- New script: `scripts/btc_wave_detector.py`
- Monitors BTC 1m candles in real-time
- Detects EMA300 crossover events
- Tracks duration above EMA300
- Monitors volume acceleration

### Step 2: Volume Confirmation Signal
- When crossover holds for 60+ min AND volume begins increasing
- Emit a `BTC_WAVE_START` signal to the signal DB
- Signal carries: direction (LONG), confidence (based on volume surge magnitude), entry price

### Step 3: Integration with Signal Pipeline
- `BTC_WAVE_START` flows through signal_compactor → hotset → decider_run
- Position sizing: full size (high conviction)
- Entry: market order on confirmation
- Exit: trailing stop + time-based exit

### Step 4: Wave Phase Tracker
- Track which phase we're in (cross → build → explosion → digest)
- Adjust exit behavior based on phase
- During explosion phase: hold tight, don't trail too tight
- During digest phase: tighten stops, prepare to exit

---

## Data References

- **1m candles:** `/root/.hermes/data/btc_1m_sep3_2026.json` (full Sep 3 dataset)
- **Candle DB:** `/root/.hermes/data/candles.db` → `candles_1m` table
- **Surfing philosophy:** `/root/.hermes/brain/surfing.md`
- **EMA300 constants:** `hermes_constants.py` — existing EMA300 infrastructure

---

## Why This Matters

This is a **repeatable pattern** that will happen over and over. As candles get bigger (4h, 1d), the same structure plays out at different scales. The key is:

1. **Patience** — wait for the EMA300 cross, don't chase the chop
2. **Confirmation** — volume tells you the wave has energy
3. **Ride the face** — once confirmed, hold through the explosion phase
4. **Exit on exhaustion** — when volume drops, the wave is over

This is the highest-conviction setup in the system. Every other signal is a ripple; this is a tsunami. We need to catch it every single time.

---

## Next Steps

1. [ ] Build `btc_wave_detector.py` — real-time EMA300 cross monitor
2. [ ] Add BTC_WAVE_START signal type to signal_schema.py
3. [ ] Add wave detection parameters to hermes_constants.py
4. [ ] Backtest on historical BTC 1m data (how often does this pattern occur?)
5. [ ] Test with paper trading before going live
6. [ ] Update surfing.md with this new pattern
