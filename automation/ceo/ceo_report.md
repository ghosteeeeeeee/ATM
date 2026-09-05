## CEO Report — 2026-09-05 ~17:00 UTC — Position Replacement Engine Review

### Verdict: **DEFER**

### Why Not Build

**Three reasons to defer:**

**1. R:R is broken — fixing the engine beats swapping positions.**
Current R:R ratio 0.73 (avg_win $0.111 vs avg_loss $0.152). The replacement engine *compares* R:R but doesn't *fix* it. Swapping a 0.5 R:R position for a 0.75 R:R position still loses money — just slower. The PM_TRAIL_DISTANCE_PCT widening (0.40→0.50%) deployed today needs 20+ trades to verify. If R:R reaches 0.80+, the system becomes profitable without any replacement logic.

**2. Signal starvation makes replacement irrelevant.**
System has 1 profitable backbone (bb-bounce-v2-long+, 80% WR). Replacement requires *multiple* strong signals competing for capital. Right now, if bb-bounce fires, it's the only good option — there's nothing better to swap in. Build the SHORT backbone first, then replacement has something to compare.

**3. Fee drag + complexity vs. marginal alpha.**
At 0.06% round-trip, 2 swaps/hour = 0.12%/hour in fees. In a system making +$0.019/trade, that's 6+ trades of profit eaten per hour of churning. The complexity of integrating with position_manager, cut_loser, btc_crash_filter, AND trailing stops — for a system that's barely positive — is backwards.

### Open Questions — CEO Answers

| # | Question | Answer |
|---|----------|--------|
| 1 | Same-direction swaps? | **No.** Replace LONG YGG with LONG SOL = fees for marginal improvement. Only allow cross-direction swaps (LONG→SHORT or SHORT→LONG) when R:R improvement > 2x. |
| 2 | Track R:R decline over time? | **No, premature.** Track it only after the replacement engine is live. Add `rr_history` field but don't use it for decisions yet — adds complexity for zero proven benefit. |
| 3 | Trailing stop interaction? | **Close at current price, not trail floor.** The trail floor is already a "last resort" exit. If we're replacing, we want the *current* R:R, not the floor R:R. |
| 4 | Right replacement multiplier? | **1.5x is wrong.** Use 2.0x (100% better). At 1.5x, a 0.5 R:R position gets replaced by a 0.75 R:R — still losing. At 2.0x, 0.5→1.0 is breakeven, 0.5→1.5+ is actually profitable. |

### What to Build Instead (Priority Order)

1. **Directional Cap (65%)** — highest-impact mechanical fix, prevents regime-transition bleed
2. **SHORT backbone signal** — system 100% LONG-dependent, SHORT has 0 active signals
3. **Verify PM_TRAIL fix** — 31 trades at old distance, need 20+ at new 0.50%
4. **Then** build replacement engine — by then we'll have 2+ backbones, working R:R, and data to prove the concept

### Biggest Risks of Building Now

- **Complexity trap.** Integration with position_manager (3339 lines), cut_loser, btc_crash_filter, AND trailing stops = 4+ integration points to test and maintain. A bug in the swap logic = closed position + failed re-entry = lost capital.
- **Premature optimization.** The system isn't profitable enough to benefit from position selection. Fix R:R and add signals first.
- **Churning in flat markets.** In NEUTRAL regime (current), R:R estimates are unreliable. Swapping based on noisy R:R = random churn = fee bleed.

---

## CEO Report — 2026-09-05 ~16:00 UTC

### Diagnosis

**84% LONG concentration is the vulnerability.** When the tide turns, all positions bleed simultaneously. Existing protections (Directional Outcome, Weather Vane, LONG_NEUTRAL_BLOCK) are all REACTIVE — they fire after damage starts. The 4-phase cycle (LONG dominance → breakdown → oscillation → SHORT dominance) means the system always bleeds during transitions.

### Verified Numbers (DB)
- **7d:** 362 trades, 55.5% WR, -$3.95
- **LONG:** 265T, 57.4% WR, -$1.62
- **SHORT:** 97T, 47.4% WR, -$2.33
- **Today (Sep 5):** LONG 27T 77.8% WR +$1.55 | SHORT 5T 0% WR -$0.74
- **Open positions:** 4 LONG, 1 SHORT (80% LONG)

### Root Cause

The system loads up on the winning direction. LONG works → more LONG signals fire → more LONG positions open → 84% concentration. When regime shifts, ALL LONG positions bleed at once. No mechanical cap exists — only reactive penalties that fire too late.

### Strategic Recommendation: DIRECTIONAL CAP (highest-impact single change)

**Build a DIRECTIONAL CAP — max 65% of open positions in one direction.**

**Why 65% (not 60%):**
- Current LONG is 80% (4/5 open). 60% would have blocked 2 recent winners.
- 65% = 2 out of 3 positions max in one direction. Still allows conviction but prevents monoculture.
- When you hit the cap, you can only open the OTHER direction (or wait for closes).

**Implementation (lazy version):**
```python
# hermes_constants.py
DIRECTIONAL_CAP_ENABLED = True
DIRECTIONAL_CAP_MAX_PCT = 65  # max % of open positions in one direction

# position_manager.py — enforce_max_positions() or new function
def enforce_directional_cap(direction: str) -> bool:
    """Return True if opening this direction won't exceed cap."""
    if not DIRECTIONAL_CAP_ENABLED:
        return True
    long_count = count_open_positions('LONG')
    short_count = count_open_positions('SHORT')
    total = long_count + short_count
    if total == 0:
        return True
    if direction.upper() == 'LONG':
        return (long_count / total) * 100 < DIRECTIONAL_CAP_MAX_PCT
    else:
        return (short_count / total) * 100 < DIRECTIONAL_CAP_MAX_PCT
```

**Why this beats the alternatives:**

| Option | Verdict |
|--------|---------|
| Directional Cap (65%) | **BUILD THIS.** Simple, mechanical, prevents monoculture. Enforced at open time. |
| Regime-adaptive signals | Complex, requires accurate regime detection (currently unreliable). Future work. |
| Transition detection | Reactive by nature. Can't predict when tide turns. |
| Harder LONG_NEUTRAL_BLOCK | Already deployed. Doesn't prevent concentration during LONG_BIAS. |

### What This Prevents

1. **Regime transition bleed:** When LONG stops working, system can't have 80% LONG exposure.
2. **Simultaneous drawdown:** Cap limits how many positions can bleed at once in the same direction.
3. **Opportunity forcing:** When LONG is capped, the system MUST look for SHORT setups — building the SHORT backbone the system currently lacks.

### Execution

1. **Add `DIRECTIONAL_CAP_ENABLED` and `DIRECTIONAL_CAP_MAX_PCT` to hermes_constants.py**
2. **Add `enforce_directional_cap()` to position_manager.py**
3. **Call from signal_compactor.py before executing any trade**
4. **Log when cap blocks a trade** — so we can measure impact

**Expected impact:** Reduces maximum simultaneous directional exposure from ~80% to 65%. During regime transitions, limits giveback by 15-20%. Forces diversification into SHORT signals.

### Also: SHORT Backbone is CRITICAL

The cap alone won't fix the SHORT side. SHORT has 0% WR today, no active backbone signal. **Delegate to signal_analyst: build a SHORT backbone signal.** The cap creates the NEED for SHORT signals; we need to build the SUPPLY.

### Next Actions

1. **BUILD directional cap** — highest-impact mechanical fix
2. **DELEGATE SHORT signal build** — system 100% LONG-dependent
3. **Monitor PM_TRAIL_DISTANCE_PCT** — 31 trades at old distance, need 20+ at 0.50%
4. **Monitor neutral_sniper** — shadow mode, 5 SHORT signals in test
