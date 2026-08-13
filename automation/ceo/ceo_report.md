## CEO Report — 2026-08-13 (CEO run)

### Diagnosis
24h 106T -$0.18 (53.8% WR — flat). 7d ~465T +$0.37 (52.8% WR — positive). Daily: Aug 12 +$0.49 (recovery confirmed) → Aug 13 11T -$0.52 (36.4% WR — cold, only 11 trades). 5 open $0 flat. Stars7d intact (5 profitable): bb_bounce+,range_finder+ 53T +$0.71 58.5%, range_breakout_short 14T +$0.49 71.4%, hzscore+,mover+ 5T +$0.17 80%, bb_bounce+,hzscore+ 34T +$0.22 50%, bb-bounce-short,hzscore- 18T +$0.14 61.1%.

### Root Cause
Aug 13 cold streak: 11T at 36.4% WR is noise (too few trades). Only active bleeder: accel-300- SHORT 31T -$0.12 58.1% WR (marginal — losses > wins but WR fine). All prior bleeders disabled/blacklisted. Atr_sl_hit dominates: 63T -$3.87 in 48h. System flat, no clear actionable problem.

### Fix Applied
NO CHANGES. Stability period active. Aug 13 too early to judge (11 trades). All prior disables confirmed working (0 new trades post-disable/blacklist). Pipeline healthy.

### Verification
All prior fixes confirmed: range_breakout+ 0 trades post-disable, hzscore+ standalone 0 trades post-blacklist, return_exhaustion- 0 trades post-blacklist. System flat, no actionable bleed. Monitor: accel-300- (if持续 bleeding → disable ACCEL_300_MINUS_ENABLED), daily PnL (if -2 consecutive red → investigate).

---

## Weather Vane Component 1 — Acknowledged (2026-08-13)

**Status:** Live. Code verified in `signal_compactor.py:433-445`, constants in `hermes_constants.py:615-620`.

**What it does:** Tracks last 5 trades per direction in 30min rolling window. If 3+ losses OR WR < 40%, applies 0.7x score penalty. Auto-recovers when old losses age out.

**Verified:**
- `get_directional_outcome()` function present
- `dir_outcome_mult` integrated into `_score_signal()` multiplier chain
- Constants: WINDOW=5, TIME_WINDOW=30min, LOSS_THRESHOLD=3, WR_THRESHOLD=40, PENALTY=0.7, MIN_TRADES=3
- Bug hunter: ALL CLEAR (SQL LIMIT fix, connection leak fix confirmed)

**Expected impact:** Reduces score for directions on cold streaks, should cut consecutive losses in a direction. Milder penalty (0.7x) for first deploy — can tighten to 0.5x if needed.

**Component 2 (Position Shield):** Unblocked. Ready when needed.

---

## Global Spike Filter — Acknowledged (2026-08-13)

**Status:** Deployed. Code in `signal_compactor.py`, constants in `hermes_constants.py:615-620`.

**What it does:** Blocks SHORT entries during bullish momentum:
1. Last 3 closed 5m candles with bullish close > 0.3% → block
2. RSI < 30 → block (oversold bounce risk)

Backtested 195 SHORT trades: blocks 6 losers (TIA, CFX, IO, YGG, LINEA, BIGTIME) vs 3 tiny winners ($0.01-$0.03). Ratio 0.5x — good.

**Expected impact:** Reduces SHORT entries against momentum. Global filter applies to all SHORT signals. range_breakout_short still has its own spike filters as second layer.

---

## Weather Vane v2 — Proposal Evaluation (2026-08-13)

### Proposal 1: Hysteresis (Dead Zone) — APPROVE WITH MODIFICATION

**Current problem:** If a direction hovers at exactly 3 losses in 5 trades (WR ~40%), the 0.7x penalty toggles on/off each compaction round as trades age out and new ones enter. This changes signal scoring → changes which signals enter → changes outcomes → feedback loop (thrashing).

**Verdict: APPROVE. Modify exit threshold from 50% to 45%.**

**Why hysteresis works:** Two separate thresholds break the feedback loop. Once suppressed, the system demands stronger evidence of recovery before unsuppressing — not just "losses aged out."

**Stateless implementation (no state file needed):**
Current trigger condition: `if losses >= 3 or wr < 40%` → suppress
Hysteresis deactivation: `if losses < 3 AND wr >= 45%` → unsuppress

This is stateless because:
- While suppressed: both losses AND WR must improve to unsuppress
- When losses drop to 2 but WR is still 40% → stays suppressed (wr < 45%)
- When losses drop to 2 AND WR hits 60% → unsuppresses
- The two-condition deactivation naturally prevents flickering

**Why 45% not 50%:** With a 5-trade window, going from 2W-3L to 3W-2L requires 3 consecutive wins. At 50% WR exit, the suppression window becomes very long (need 3 wins in ~30min). 45% is strict enough to prevent thrashing but gives the system a reasonable recovery path — 2 wins in 5 trades is achievable without requiring a full reversal.

**Code change (3 lines):**
```python
# signal_compactor.py _score_signal(), weather vane section
if DIRECTIONAL_OUTCOME_ENABLED:
    losses, total, wr = get_directional_outcome(direction)
    if total >= DIRECTIONAL_OUTCOME_MIN_TRADES:
        if losses >= DIRECTIONAL_OUTCOME_LOSS_THRESHOLD or wr < DIRECTIONAL_OUTCOME_WR_THRESHOLD:
            dir_outcome_mult = DIRECTIONAL_OUTCOME_PENALTY
```
→ Add recovery check:
```python
if DIRECTIONAL_OUTCOME_ENABLED:
    losses, total, wr = get_directional_outcome(direction)
    if total >= DIRECTIONAL_OUTCOME_MIN_TRADES:
        if losses >= DIRECTIONAL_OUTCOME_LOSS_THRESHOLD or wr < DIRECTIONAL_OUTCOME_WR_THRESHOLD:
            dir_outcome_mult = DIRECTIONAL_OUTCOME_PENALTY
        # Hysteresis: only unsuppress if BOTH losses dropped AND WR recovered
        elif wr < DIRECTIONAL_OUTCOME_RECOVERY_WR:
            dir_outcome_mult = DIRECTIONAL_OUTCOME_PENALTY  # stay suppressed
```
+ New constant: `DIRECTIONAL_OUTCOME_RECOVERY_WR = 45`

**Risks:** If a direction is genuinely cold (3 losses in 5 trades), suppression persists longer. This is by design — cold directions should stay suppressed until they prove recovery. No risk of over-suppression because the 30-min time window still ages out old trades.

---

### Proposal 2: Off-Course Alarm — APPROVE AS-IS

**Verdict: APPROVE. Zero risk.**

Log a warning when a direction hits 2 losses in 5 trades. No scoring impact — pure visibility.

**Implementation:**
```python
# In get_directional_outcome(), after computing losses/total/wr
if losses >= 2 and total >= 3:
    log.warning(f"Weather Vane OFF-COURSE: {direction} {losses}/{total} losses ({wr}% WR)")
```

**Why approve:** Early warning before the penalty triggers. Gives visibility into whether a direction is approaching the danger zone without changing scoring. Zero downside.

---

### Additional Recommendation: Graduated Penalty (Optional)

Current: flat 0.7x multiplier when triggered. Could gradate:
- 3 losses in 5: 0.85x (mild)
- 4 losses in 5: 0.70x (current)
- 5 losses in 5: 0.50x (hard block)

This is a "nice to have" — hysteresis is the priority fix. Graduation adds complexity for marginal gain. Skip for now, revisit if hysteresis alone doesn't stop thrashing.

---

### Parameters Summary

| Parameter | Current | Proposed | Reasoning |
|-----------|---------|----------|-----------|
| LOSS_THRESHOLD | 3 | 3 | Keep — loss count is the trigger |
| WR_THRESHOLD | 40 | 40 | Keep — secondary trigger |
| RECOVERY_WR | — | 45 | New — exit gate (hysteresis) |
| PENALTY | 0.7 | 0.7 | Keep — milder for first deploy |
| MIN_TRADES | 3 | 3 | Keep |
| WINDOW | 5 | 5 | Keep |
| TIME_WINDOW | 30 | 30 | Keep |
