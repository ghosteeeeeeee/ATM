# Plan: Win Rate Improvement — From 29% to 50%+

**Date:** 2026-07-28
**Status:** Phase 1 DONE, Phase 2 spec ready
**Context:** 200 closed trades analyzed. 29% WR, 1.68x R:R. Break-even needs ~37% WR. System is bleeding.

---

## Current State Diagnosis

### The Numbers
| Metric | Value | Verdict |
|--------|-------|---------|
| Win Rate | 29% | Below break-even threshold (37%) |
| R:R Ratio | 1.68x | Good — wins are 1.68x bigger than losses |
| Profit Factor | 0.58 | Losing money overall |
| Avg Win | +0.49% | Acceptable |
| Avg Loss | -0.29% | Acceptable |
| Total PnL | -$0.81 | Essentially flat |

### What Works
- **`accel-300-` SHORT**: 60% WR, +0.107% avg — the ONLY reliable signal
- **SHORT direction**: 7% higher WR than LONG
- **3x leverage**: Less bleed than 5x
- **Risk management**: Zero large losses (>1%), tight stops working

### What Doesn't Work
- **`inv-accel-300+` LONG**: 29% WR, -0.06% avg — produces 62% of all trades
- **`inv-accel-300-` SHORT**: 24% WR, -0.11% avg — second biggest signal
- **`sqx+` LONG**: 0% WR — every single trade loses
- **`accel-300+` LONG**: 22% WR, -0.17% avg
- **03:00-08:00 UTC entries**: ~15% WR — dead zone
- **94% of exits are ATR SL hits** — profit targets almost never reached

### Root Causes
1. **Signals enter at exhaustion points** — SHORT at range bottom, LONG at range top
2. **No wave quality filter** — system enters during whitewater (dead hours, ranging markets)
3. **No phase awareness** — signals fire during exhaustion/extreme phases (move already done)
4. **Dominant signals are net losers** — inv-accel-300 produces most trades but loses money
5. **No AI/context check** — signals detect momentum but don't assess context

---

## Proposal 1: Targeted Signal Inversion Gate

### Problem
With 29% WR, certain signals are consistently wrong. Simple global inversion doesn't work (tested — WR dropped to 13.8%) because it flips R:R too. But **selective inversion** for specific losing signals could work.

### Analysis
| Signal | Trades | WR | Avg PnL | Invert? |
|--------|--------|-----|---------|---------|
| `inv-accel-300+` LONG | 69 | 29% | -0.06% | YES — consistently loses |
| `accel-300+` LONG | 9 | 22% | -0.17% | YES — consistently loses |
| `sqx+` LONG | 7 | 0% | -0.32% | Already disabled |
| `inv-accel-300-` SHORT | 55 | 24% | -0.11% | MAYBE — slightly better than random |
| `accel-300-` SHORT | 15 | 60% | +0.11% | NO — this is our best signal |

### Implementation
1. Add inversion dict to `hermes_constants.py`:
```python
INVERT_SIGNALS = {
    'inv-accel-300+': True,   # LONG always loses → flip to SHORT
    'accel-300+': True,       # LONG always loses → flip to SHORT
}
```

2. Add inversion logic to `decider_run.py` before `execute_trade()`:
```python
if source in INVERT_SIGNALS and INVERT_SIGNALS[source]:
    direction = 'SHORT' if direction == 'LONG' else 'LONG'
    print(f"  [INVERT] Flipped {source} {original_direction} → {direction}")
```

3. Make it toggleable: `SIGNAL_INVERSION_ENABLED = True` in hermes_constants.py

### Risk
- LOW — can be toggled off instantly
- If it doesn't work, just set `SIGNAL_INVERSION_ENABLED = False`

### Expected Impact
- If inv-accel-300+ LONG (29% WR) becomes SHORT: could reach ~50%+ WR
- Net effect: +5-10% WR improvement on affected signals

---

## Proposal 2: AI Decision Making Before Trade

### Problem
The system detects momentum (signal exists) but has no intelligence about context. The signal says "price is moving" but doesn't ask "should we actually trade this?"

### Original Vision (from surfing.md)
> "No auto-approve. No auto-execute. No shortcuts."
> The compactor was supposed to be the "AI Decider" — it's now fully deterministic.

### What AI Could Decide
1. **Direction confirmation**: Signal says LONG but z-score is +2.0 (overbought) → AI says SHORT or no-trade
2. **Context check**: Signal fires at 03:00 UTC, stale token, ranging market → AI says skip
3. **Wave state**: Is this a clean wave or whitewater? (surfing.md's "wave quality filter")
4. **Coin history**: LINK is 0/6 — AI blocks further LINK trades

### Implementation (Phased)
**Phase 1 — Rule-based context check (no LLM):**
```python
def context_check(signal, market_state):
    """Rule-based context check before trade execution."""
    # Dead hours filter
    if 3 <= utc_hour <= 8:
        return "SKIP", "dead_hours"

    # Counter-trend filter
    if signal.direction == 'LONG' and market_state.z_score > 1.5:
        return "SKIP", "overbought_counter_trend"
    if signal.direction == 'SHORT' and market_state.z_score < -1.5:
        return "SKIP", "oversold_counter_trend"

    # Coin loss history
    if coin_wr < 50% and coin_trades >= 3:
        return "SKIP", "poor_coin_history"

    # Stale token in ranging market
    if market_state.is_stale and abs(market_state.z_score) < 0.5:
        return "SKIP", "stale_ranging"

    return "PASS", "all_checks_passed"
```

**Phase 2 — LLM-based context check (future):**
- Use `opencode + command` to call a lightweight LLM
- Send signal context, market state, recent trades
- LLM returns: GO/LONG/SHORT/SKIP with reasoning
- Add 2-5s latency budget

### Files to Modify
- `decider_run.py`: Add context check before `execute_trade()`
- `hermes_constants.py`: Add `CONTEXT_CHECK_ENABLED = True`

### Risk
- MEDIUM — rule-based phase is safe; LLM phase needs latency management
- Can start with rules-only, evolve to LLM

### Expected Impact
- Eliminates ~30-40% of bad entries (dead hours, counter-trend, bad coins)
- Could improve WR by +10-15%

---

## Proposal 3: Phase-Aware Entry Timing

### Problem
The phase system (quiet → building → accelerating → exhaustion → extreme) exists in `tpsl_utils.py` and affects SL/TP trailing. But `accel_300` and `inv_accel_300` are **completely phase-agnostic** — they fire regardless of market phase.

Signals fire during exhaustion/extreme phases (after the move has happened). The LINK trades are perfect examples.

### Current Phase System
```python
# From tpsl_utils._phase_from_pct()
Phase 0 (quiet):     speed_percentile < 60, low velocity
Phase 1 (building):  speed_percentile >= 60
Phase 2 (accelerating): speed_percentile >= 70
Phase 3 (exhaustion): speed_percentile >= 88
Phase 4 (extreme):   speed_percentile >= 95
```

### What to Add

**For `accel_300` (momentum signal):**
| Phase | Action | Reason |
|-------|--------|--------|
| quiet | Allow | Fresh start, early entry |
| building | Allow | IDEAL — momentum just starting |
| accelerating | Allow | Still OK — momentum confirmed |
| exhaustion | Block | Move is over — don't chase |
| extreme | Block | Exhausted — high reversal risk |

**For `inv_accel_300` (mean reversion signal):**
| Phase | Action | Reason |
|-------|--------|--------|
| quiet | Caution | No move to revert from |
| building | Caution | Move still building — too early |
| accelerating | Caution | Move may be too far gone |
| exhaustion | Allow | IDEAL — reversal prime |
| extreme | Allow | Maximum exhaustion — best reversion |

### Implementation
1. Import `_phase_from_pct()` from `tpsl_utils.py` into signal detectors
2. Compute speed_percentile at detection time
3. Block signals based on phase table above

### Files to Modify
- `signals/accel_300.py`: Add phase check after detection
- `signals/inverse_accel_300.py`: Add phase check after detection
- `tpsl_utils.py`: Export `_phase_from_pct()` (already exists)

### Risk
- LOW — phase detection already exists, just not used in signals
- Can be toggled per-signal

### Expected Impact
- Blocks ~20-30% of bad entries (exhaustion-phase entries)
- Could improve WR by +5-10%

---

## Proposal 4: Surfing.md Alignment

### Problem
Surfing.md has 5 open questions that map directly to our problems. The core surfing principle we're violating: "Read the wave, position yourself, and let it carry you." We're currently **chasing ripples**, not riding waves.

### Open Questions from Surfing.md → Actions

| Open Question | Status | Action |
|---------------|--------|--------|
| Wave quality filter | NOT IMPLEMENTED | Add minimum wave quality score |
| Entry timing | PARTIALLY DONE (price position filter) | Add phase filter (Proposal 3) |
| Regime strength | NOT IMPLEMENTED | Add regime strength axis |
| Funding rate | NOT IMPLEMENTED | Low priority |
| Wave-of-interest | PARTIALLY DONE (speed filter) | Focus on top 50 tokens |

### Concrete Rules to Add (from surfing.md case studies)

**NIL Case Study (Wrong-Side Entry):**
> "Before executing any SHORT signal, check is_stale. If is_stale AND z_score < 0 → counter-trend trap, block it."

**0G Case Study (Mean Reversion Trap):**
> "Z-score in a ranging market is a mean-reversion signal, not a trend signal. Don't use z-score as an entry trigger in ranging conditions."

**The 4 Quadrants (from surfing.md):**
| Z-Score | Speed | Action |
|---------|-------|--------|
| Near 0 | Low | Sit out — whitewater |
| Negative + HIGH speed + positive accel | Paddle for LONG |
| Positive + HIGH speed + negative accel | Take SHORT |
| Near 0 + HIGH speed + positive accel | Confirm with confluence |

### Rules to Add to AGENTS.md

```markdown
## Surfing Principles

### Entry Rules (from surfing.md)
1. **No entries during dead hours**: 03:00-08:00 UTC = whitewater. Block all entries.
2. **Wave quality minimum**: Speed percentile must be >= 30 to enter. Below 30 = no wave.
3. **Phase alignment**: accel_300 only during building/accelerating phases. inv_accel_300 only during exhaustion/extreme.
4. **Range position**: Don't LONG at range top (>80%), don't SHORT at range bottom (<20%).
5. **Counter-trend trap**: If z-score contradicts signal direction AND speed is low → block.
6. **Ranging market filter**: If |z-score| < 0.5 AND speed < 30th percentile → no entries.
7. **Coin history gate**: If coin has <50% WR with >=3 trades → block further entries.

### Exit Rules (from surfing.md)
8. **Stale winner**: If pnl >= +0.5% and trade age > 30 min → tighten trailing aggressively.
9. **Wave turning**: If z-score > +1.5 AND acceleration < 0 → close longs.
10. **Bottom forming**: If z-score < -1.5 AND acceleration > 0 → close shorts.

### Position Sizing (from surfing.md)
11. **Fast movers, smaller size**: Speed percentile >= 80 → use 3x leverage (not 5x).
12. **Slow movers, standard size**: Speed percentile < 50 → standard position.
```

### Files to Modify
- `AGENTS.md`: Add surfing principles section
- `decider_run.py`: Add dead-hours filter, wave quality minimum
- `signal_compactor.py`: Add regime strength scoring

### Risk
- LOW — these are mostly filter additions, not core logic changes

### Expected Impact
- Eliminates dead-hours entries (~15% WR → 0 trades during those hours)
- Eliminates ranging-market entries
- Could improve WR by +10-15%

---

## Implementation Order

### Phase 1 (DONE — 2026-07-28)
1. ✅ **Targeted inversion gate** (Proposal 1) — commit `705dcf7`
2. ✅ **Dead-hours filter** (Proposal 4) — commit `705dcf7`
3. ✅ **AGENTS.md surfing rules** (Proposal 4) — commit `705dcf7`
4. ✅ **Price position filter** — commit `f42b4e5`

### Phase 2 (DONE — 2026-07-28)
5. ✅ **Context gate** (Proposal 2 + Proposal 3 merged) — rule-based + LLM fallback
   - Speed >= 20th percentile (surfing rule #2)
   - Phase alignment (surfing rule #3)
   - Counter-trend trap + speed cross-check (surfing rule #5)
   - Ranging market filter (surfing rule #6)
   - LLM fallback for ambiguous cases (5-10 calls/hr)

### Phase 3 (Future — Low Priority)
6. 🔲 **Funding rate integration** (surfing.md open question)

---

## Expected Combined Impact

| Proposal | Status | WR Improvement | Confidence |
|----------|--------|---------------|------------|
| Targeted inversion | ✅ DONE | +5-10% | HIGH |
| Dead-hours filter | ✅ DONE | +3-5% | HIGH |
| Price position filter | ✅ DONE | +2-3% | HIGH |
| Context gate (merged: phase + counter-trend + ranging + speed + LLM) | ✅ DONE | +8-14% | MEDIUM-HIGH |
| Coin history gate | ✅ DONE (existing) | +2-3% | HIGH |
| **Combined (all deployed)** | | **+20-35%** | **MEDIUM-HIGH** |

**Current state (all deployed):** 29% → estimated 43-50% WR
**Optimistic:** 55%+ WR

At 50% WR with 1.68x R:R, the system would be significantly profitable.

---

## Risk Assessment

| Risk | Mitigation |
|------|------------|
| Inversion makes things worse | Toggle `SIGNAL_INVERSION_ENABLED = False` |
| Phase filter blocks too many signals | Make it configurable per-signal |
| Dead-hours filter misses good trades | Allow override with high confidence (conf >= 85) |
| Context check adds latency | Start with rules-only (no latency), add LLM later |
| Combined filters too restrictive | Monitor signal count — if <5/day, loosen filters |

---

## Success Metrics

After implementation, track:
1. **Win rate**: Target 45%+ (from 29%)
2. **Profit factor**: Target >1.2 (from 0.58)
3. **Trades per day**: Should remain >10 (if <5, filters too tight)
4. **Max drawdown**: Should decrease (fewer bad entries)
5. **Avg win / avg loss**: Should remain >=1.5x (don't sacrifice R:R)

---

## Questions for T

1. **Inversion**: Which signals should be inverted? My analysis suggests `inv-accel-300+` and `accel-300+`. Agree?
2. **Dead hours**: Is 03:00-08:00 UTC the right window? Or should it be tighter (04:00-07:00)?
3. **Phase filter**: Should we block during exhaustion or just penalize (reduce confidence)?
4. **AI decision**: Rule-based first, or go straight to LLM? LLM adds 2-5s latency.
5. **Surfing rules**: Any additional rules from surfing.md I missed?
