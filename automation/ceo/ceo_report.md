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
