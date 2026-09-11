# MoE Verdict: BTC Timing Guard

**Date:** 2026-09-11
**Question:** Should we implement per-signal-type BTC momentum thresholds to prevent chasing entries?
**Experts:** Signal Analyst, Risk Manager, Regime Analyst (Statistician pending)

---

## Consensus: NO-GO (3/3 experts agree)

| Expert | Verdict | Key Reason |
|--------|---------|------------|
| Signal Analyst | REVISE | 2 of 6 thresholds good, 1 inverted (accel-300), 1 redundant (pump-chain) |
| Risk Manager | NO-GO | System already has 9+ BTC filters, hotset EMPTY, R:R is exit problem |
| Regime Analyst | NO-GO | Thresholds create blackout zones 54% of time, adversarial with Layer 7 |

**Dissent:** Signal Analyst says pullback-entry thresholds are "sound logic" — would keep if implemented alone.

---

## Key Findings

### 1. The System Is Already Over-Filtered

The system has 9+ BTC/momentum filter layers. Adding a 10th creates "death by a thousand cuts":

| Layer | Threshold | What It Blocks |
|-------|-----------|---------------|
| BTC_CHOP_GATE | \|30m\| < 0.20% | Momentum signals when BTC flat |
| BTC_MOMENTUM_FILTER | 30m ±0.12% | Counter-trend entries |
| TIDE | 3h ±0.1% | Directional penalty |
| DIRECTIONAL_BIAS | momentum_state | Counter-trend penalty |
| ALT_BTC_DIVERGENCE | alt vs BTC | Divergent entries |
| CHOP_DETECTOR | 4 inputs | Momentum in chop |
| SHORT_VEL_FILTER | token vel | SHORT when token rising |
| SPIKE_FILTER | 5m candle | After large moves |
| PUMP_CHAIN_VEL_FILTER | token 30m vel | Wrong direction |

**Result:** pump-chain has 344 signals/day but only 3 execute (99.1% blocked). pullback-entry has 126 signals/day, 0 execute (100% blocked). The hotset is EMPTY.

### 2. Blackout Zones

When BTC moves > +0.3% in 30m:
- Layer 7 blocks SHORT (BTC rising)
- Proposed threshold blocks LONG (BTC already up)
- **Result: BOTH directions blocked = complete blackout**

This happens ~54% of the time in trending markets. The system would be dead during exactly when it should be most active.

### 3. The Real Problem Is Exits, Not Entries

| Metric | Current | Target |
|--------|---------|--------|
| Win Rate | 48% | 55%+ |
| R:R | 0.755 | 1.0+ |
| Avg Win | +3.38% | +4.0%+ |
| Avg Loss | -4.48% | -3.0% |

**No amount of entry filtering changes the exit structure.** A trade that enters at the "perfect" BTC moment still loses -4.48% when the stop gets hit. The R:R problem is:
- ATR_SL at 1.2% but trades bleed to -4.48% (slippage + gap risk)
- PM_TRAIL at 0.20% too tight — winners trailed out early (+3.38% avg)
- CUT_LOSER barely fires (trades bleed past it)

### 4. The accel-300-v4-short- Threshold Is Inverted

The proposed threshold (block SHORT when BTC < -0.15%) would block the signal during the strongest downtrends — exactly when it should fire. The existing Layer 7 already correctly blocks SHORT when BTC is RISING.

---

## What To Do Instead

### Priority 1: Fix the R:R (Exit Problem)

| Action | What | Expected Impact |
|--------|------|-----------------|
| Widen PM_TRAIL | 0.20% → 0.35% distance | Winners run to +4-5% instead of +3.38% |
| Tighten CUT_LOSER | -3.0% → -2.5% hard stop | Losses capped at -2.5% instead of -4.48% |
| Audit ATR_SL slippage | Why do 1.2% SLs become -4.48% losses? | Find the leak |

### Priority 2: Reduce Filter Overlap

| Action | What | Expected Impact |
|--------|------|-----------------|
| Audit filter stack | Map which filters block the same signals | Remove redundant layers |
| Relax CHOP_GATE | 0.20% → 0.10% | More signals reach execution |
| Remove redundant filters | TIDE + DIRECTIONAL_BIAS + BTC_MOMENTUM all check BTC | Consolidate to 1 |

### Priority 3: Add Visibility

| Action | What | Expected Impact |
|--------|------|-----------------|
| Filter audit dashboard | Track how many signals each filter blocks | See which filters do real work |
| Entry quality tracker | Log BTC state at entry vs exit | Verify if BTC timing actually matters |

---

## Revised Plan: Exit Optimization (Not Entry Filtering)

Instead of adding more entry filters, fix the exit structure:

```python
# New constants (replacing timing guard)
PM_TRAIL_DISTANCE_PCT = 0.0035    # 0.35% (was 0.20%) — let winners run
CUT_LOSER_HARD_STOP = 0.025       # 2.5% (was 3.0%) — cap losses tighter
```

**Expected impact:**
- Avg win: +3.38% → +4.5% (wider trail)
- Avg loss: -4.48% → -2.5% (tighter stop)
- R:R: 0.755 → 1.80 (massive improvement)
- Breakeven WR: 57% → 36% (system becomes profitable at 48% WR)

---

## MoE Decision

**DO NOT implement BTC timing guard.** Instead:

1. **Fix R:R first** (PM_TRAIL + CUT_LOSER adjustments)
2. **Audit filter overlap** (reduce from 9+ layers to 5-6)
3. **Add filter audit dashboard** (visibility into what's being blocked)
4. **Then** consider per-signal thresholds only if data shows clear chasing pattern after filter reduction

**Confidence:** HIGH (3/3 experts agree, strong data support)
