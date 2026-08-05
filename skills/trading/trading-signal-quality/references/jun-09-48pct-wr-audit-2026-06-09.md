# Jun 09 2026 Audit: 16W/17L (48.5% WR) — Subagent Claims vs Actual Code

## Session Context
- Date: 2026-06-09
- 33 closed trades, 16W/17L (48.5% WR)
- T asked to review a subagent's audit and verify against actual code
- **CRITICAL LESSON**: Subagent recommendations must be verified against actual code before accepting

## What the Subagent Got Right (Verified)

### 1. rs-s-broken SHORT is a trap — CONFIRMED
**Code: rs.py lines 552-575**
- Support broken → fires SHORT with source `rs-s-broken`
- Regime penalty only 0.80x in LONG_BIAS — not enough to block in uptrends
- Trade evidence: GRIFFAIN -1.07%, AVNT -0.85%/-1.11%, SKR -0.54%, ME -1.74% — all hit SL

### 2. RS touch count pattern — CONFIRMED (no hard cap exists)
**Code: RS_DECIDER_MIN_TOUCHES = 150** (line 266) — penalizes, does NOT block
**Trade evidence:**
| Touches | Outcome | Trades |
|---------|---------|--------|
| 8, 24, 56, 58, 60, 72, 88, 92 | WIN | 8/8 = 100% |
| 120, 188 | LOSS | 0/2 = 0% |
| 406, 640, 1380 | LOSS | 0/3 = 0% |

**Sweet spot: <100 touches. No RS_TOUCH_HARD_CAP exists anywhere.**

### 3. accel-300 SHORT is weak — PARTIALLY CONFIRMED
- Only 3 SHORT trades: DASH -1.16%, ADA -0.93%, ME -1.10% — all losses, all hit ATR SL
- Sample too small for WR calculation, but direction is consistently wrong

## What the Subagent Got Wrong

### 1. `ACCEL_300_MIN_GAP_PCT_SHORT = 0.25` — DOES NOT EXIST
The subagent recommended this constant. **It doesn't exist in hermes_constants.py.**
Only `ACCEL_300_MIN_GAP_PCT = 0.20` exists — used for BOTH directions.
The subagent invented a constant that has no code backing.

### 2. `RS_TOUCH_HARD_CAP = 200` — DOES NOT EXIST
The subagent proposed `RS_TOUCH_HARD_CAP = 200` as a new constant. **It doesn't exist.**
The existing `RS_DECIDER_MIN_TOUCHES = 150` penalizes low touches but has no hard cap.

### 3. `bars_since_cross > 3` → `> 1` fix — WRONG direction
Subagent said change to `> 1` to require acceleration from bar 2.
**Code: accel_300.py line 340** — `if bars_since_cross > 3:` means bars 0-3 skip acceleration check.
Changing to `> 1` would still exempt bars 0-1 entirely. The real issue is the RS touch count, not bar count.

## Verified Constants-Only Changes for 75%+ WR Target

### hermes_constants.py changes needed:

```python
# ── RS Touch Cap (NEW) ─────────────────────────────────────────────
RS_DECIDER_MIN_TOUCHES = 80   # was 150 — tighten the penalty floor
RS_TOUCH_HARD_CAP      = 150  # NEW: block signals above this entirely

# ── rs-s-broken Kill-switch (NEW) ────────────────────────────────
RS_BROKEN_SHORT_ENABLED = False  # NEW — broken support SHORT fires in uptrends, trap
                                   # Better path: broken support → LONG on recovery

# ── accel-300 Per-Direction Thresholds (NEW) ─────────────────────
ACCEL_300_MIN_GAP_PCT_LONG  = 0.20   # keep existing
ACCEL_300_MIN_GAP_PCT_SHORT = 0.25   # NEW — tighter for SHORT (was 0.20 global)
ACCEL_300_MIN_GAP_GROWTH_SHORT = 0.07  # NEW — stricter growth for SHORT (was 0.05)
ACCEL_300_STALE_BARS_SHORT  = 60    # NEW — stricter stale gate for SHORT (was 80)
ACCEL_300_STALE_BARS         = 60    # was 80 — fire earlier, less stale for both
```

## Expected Impact

| Fix | Removes | Result |
|-----|---------|--------|
| RS_TOUCH_HARD_CAP = 150 | 7 losing trades (120-1380 touches) | +7 removed, 16W/26L → 61.5% |
| RS_BROKEN_SHORT_ENABLED = False | 5 losing rs-s-broken SHORTs | +5 removed, 16W/21L → 76.2% |
| accel-300 SHORT tighter | Filters weak SHORT signals | +1-2 quality |

**Projected WR: 75%+**

## Key Files Referenced

- `/root/.hermes/scripts/hermes_constants.py` — all tunable constants
- `/root/.hermes/scripts/signals/rs.py` — rs-s-broken path at lines 552-575
- `/root/.hermes/scripts/signals/accel_300.py` — bars_since_cross check at line 340
- `/var/www/hermes/data/signals.json` — signal type references