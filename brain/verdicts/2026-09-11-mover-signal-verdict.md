# Mover Signal Verdict — Sep 11, 2026

**Auditor:** Independent (fresh eyes, no prior analysis assumed)
**Date:** 2026-09-11
**Subject:** LDO mover+ trade at 16:57 UTC — noise or real move?

---

## Executive Summary

**The user is correct: the 16:57 signal was noise.** The mover signal's filters (RSI, BB position, proximity) are fundamentally misaligned with its purpose as a momentum detector. They block the signal during actual moves and only allow it after the move is over.

---

## The Trade

| Field | Value |
|-------|-------|
| Token | LDO |
| Signal | mover+ (LONG) |
| Signal time | 2026-09-11 16:57:38 UTC |
| Trade open | 2026-09-11 16:57:38 UTC |
| Trade close | 2026-09-11 17:08:01 UTC |
| Entry price | 0.38129 |
| Exit price | 0.38198 |
| PnL | $0.02 (essentially flat) |
| Confidence | 99 |

The trade held for ~10 minutes and made $0.02. This is not a real move — it's noise that happened to not lose money.

---

## What Actually Happened on Sep 11

### The Real Moves

**Move 1 (12:25–12:35):** Price surged from 0.3677 to 0.3771 (+2.6%) in 10 minutes on 475k volume.
- At 12:30: velocity = +2.56%, RSI = 83.1, BB = 1.39
- **BLOCKED:** RSI > 70, BB > 0.85

**Move 2 (13:40–14:00):** Price surged from 0.3745 to 0.3896 (+4.0%) in 20 minutes.
- At 13:45: velocity = +1.06%, RSI = 56.4, BB = 0.91, proximity = 0.0%
- **BLOCKED:** BB > 0.85, proximity < 0.5%
- At 13:55: velocity = +2.78%, RSI = 72.2, BB = 1.16
- **BLOCKED:** RSI > 70, BB > 0.85

### The Signal Time (16:55–16:57)

- Price: 0.38212 (dead flat after the moves)
- Velocity: +1.76% (residual from the earlier moves, not a new move)
- RSI: 50.5 (cooled down)
- BB: 0.72 (cooled down)
- Proximity: 0.59% (just barely above threshold)
- **ALL FILTERS PASS** → Signal fires

But there's no momentum left. The price drifted sideways from 0.382 to 0.382 for the next 10 minutes.

---

## Root Cause Analysis

### 1. RSI Filter (MOVER_RSI_MAX=70) — THE PRIMARY BLOCKER

The RSI filter is designed to avoid "overbought" entries. But for a momentum signal, this is backwards:

- **During a real move:** RSI spikes to 70–90 → BLOCKED
- **After the move ends:** RSI cools to 40–60 → ALLOWED

This creates a catch-22: the signal can only fire when there's no momentum left.

**Evidence:** Both big moves (12:30 and 13:55) had RSI > 70 and were blocked. The signal only fired at 16:57 when RSI was 50.5 — but by then, the move was over.

### 2. BB Position Filter (MOVER_BB_POSITION_MAX=0.85) — SECONDARY BLOCKER

Same problem as RSI. Strong moves push price above the upper Bollinger Band:

- At 12:30: BB = 1.39 (way above 0.85) → BLOCKED
- At 13:45: BB = 0.91 (above 0.85) → BLOCKED
- At 16:57: BB = 0.72 (below 0.85) → ALLOWED

The BB filter is a mean-reversion filter, not a momentum filter.

### 3. Proximity Filter (MOVER_PROXIMITY_PCT=0.5%) — TERTIARY BLOCKER

This prevents entering within 0.5% of the recent high. During a strong move, the price IS at the recent high:

- At 13:45: price was at the exact recent high (distance = 0.0%) → BLOCKED
- At 16:57: price had pulled back 0.59% from the high → ALLOWED

For momentum, entering near highs is expected and correct.

### 4. Velocity Calculation — CORRECT BUT MISUSED

The velocity calculation itself is fine:
- Uses 12 candles (1h window) of 5m data
- Measures % change from start to end
- Returns (velocity_pct, direction)

The problem is that by the time velocity exceeds 1.0% AND all filters pass, the move is already over. The filters are anti-correlated with the signal's purpose.

---

## Filter Pass/Fail Timeline (Sep 11)

| Time | Vel% | RSI | BB | Prox | Would Fire? | Notes |
|------|------|-----|-----|------|-------------|-------|
| 12:25 | +1.02 | 74.2 | 1.00 | — | NO | RSI blocked |
| 12:30 | +2.56 | 83.1 | 1.39 | — | NO | RSI + BB blocked |
| 12:35 | +3.51 | 87.0 | 1.35 | — | NO | RSI + BB blocked |
| 13:40 | -0.13 | 54.1 | 0.64 | 1.03 | NO | Velocity too low |
| 13:45 | +1.06 | 56.4 | 0.91 | 0.00 | NO | BB + proximity blocked |
| 13:50 | +1.22 | 67.4 | 1.03 | 0.00 | NO | BB + proximity blocked |
| 13:55 | +2.78 | 72.2 | 1.16 | 0.00 | NO | RSI + BB + proximity blocked |
| 14:00 | +4.14 | 71.4 | 1.13 | 0.00 | NO | RSI + BB + proximity blocked |
| 16:55 | +1.76 | 50.5 | 0.72 | 0.59 | **YES** | All pass — but move is over |

---

## Answer to User's Questions

### Is the RSI filter actually the problem?
**YES.** The RSI filter is the primary blocker. During both real moves, RSI exceeded 70 and blocked the signal. The signal only fires after RSI cools down, which means the momentum is gone.

### Is the velocity calculation correct?
**YES.** The calculation is mathematically correct. The issue is that the velocity window (1h) and the filters are misaligned. By the time velocity is high enough to pass, the filters block it.

### Is the 1h window appropriate?
**PARTIALLY.** A 1h window is reasonable for detecting moves, but it's too slow for fast-moving coins. The signal needs to detect the move WITHIN the first 15–30 minutes, not after an hour. Consider:
- Shorter window (6 candles = 30min) for faster detection
- Or use acceleration (velocity change) instead of absolute velocity

### What would you recommend to fix this?

**Option A: Relax the filters for momentum signals**
- Set MOVER_RSI_MAX to 85 or 90 (only block extreme overbought)
- Set MOVER_BB_POSITION_MAX to 1.0 (remove BB filter entirely)
- Set MOVER_PROXIMITY_PCT to 0.1 (allow entering near highs)

**Option B: Use acceleration as primary signal**
- Instead of requiring velocity > 1%, require velocity to be INCREASING
- Fire when acceleration > 0 AND volume is above average
- Use RSI/BB only as exit filters, not entry filters

**Option C: Dual-mode signal**
- Mode 1 (momentum): Fire during strong moves with relaxed filters
- Mode 2 (pullback): Fire after pullbacks with strict filters (current behavior)
- Let the user choose which mode to use

**Recommended:** Option A (simplest, lowest risk). The current filters were designed for mean-reversion signals, not momentum. Relaxing them fixes the fundamental mismatch.

---

## Additional Finding: BB Position Discrepancy

The signal metadata records `bb_position: 0.9371` but the mover.py's own `compute_bb_position()` returns `0.7229` for the same timestamp. This is because:
- **mover.py** computes BB from 5m candle closes (period=20, stddev=2.0)
- **signal_schema._enrich_indicators()** computes BB from 1-minute price history using a z-score formula

These are different calculations. The metadata's BB position is not what the mover signal uses for its filter check. This is not a bug, but it's confusing for debugging.

---

## Conclusion

The mover signal is **structurally broken** for catching momentum moves. Its filters are designed for mean-reversion (buy the dip), but its purpose is momentum (ride the wave). The signal only fires after the move is over, when all filters have cooled down. This produces noise signals like the LDO trade at 16:57.

**Severity:** High — the signal is not achieving its stated purpose.
**Fix complexity:** Low — relaxing 3 constants in hermes_constants.py.
**Risk of fix:** Low — relaxed filters may produce more false signals, but they'll at least catch real moves.
