# Jun 2026 Signal Quality Audit (48.5% WR → 75%+ target)

## Dataset: 33 trades, 2026-06-09

## Problems Found

### P1: rs-s-broken SHORT — 29% WR (2W/5L)
**Pattern:** Support broken → fire SHORT. But in uptrends, broken support just means price left it behind. Shorting the "break" is fighting momentum.
**Evidence:**
- GRIFFAIN SHORT -1.07%, AVNT SHORT -0.85%/-1.11%, SKR SHORT -0.54%, ME SHORT -1.74% — all hit SL
- ONDO SHORT +0.92% and ME SHORT +1.12% were wins but small
**Fix:** `RS_BROKEN_SHORT_ENABLED = False` — kill-switch at rs.py line ~564.
When `False`, broken support sets `nearest_support = None` instead of firing SHORT.
Applied at BOTH signal generation (rs.py) AND decider_run.py (execution gate).

### P2: RS Touch Count — sweet spot 8-92, hard cap >150
**Pattern:**
| Touches | WR | Trades |
|---------|----|--------|
| 8-92    | 100% | 8/8 |
| 120-188 | 0%   | 0/2 |
| 290-1380| 0%   | 0/6 |
High-touch levels are exhausted/trampled — price sails past them.
**Fix:** `RS_TOUCH_HARD_CAP = 150` — hard block when touch_count > 150.
Applied at BOTH rs.py (nearest_support/resistance = None) AND decider_run.py (hard cap check before min_touches comparison).

Also: `RS_DECIDER_MIN_TOUCHES = 80` (was 150) — penalty floor tightened.

### P3: accel-300 SHORT — 40% WR (2W/3L, no broken)
**Pattern:** All 3 non-broken SHORT losses hit ATR SL — momentum was fading.
**Fix:** Per-direction thresholds:
- `ACCEL_300_MIN_GAP_PCT_SHORT = 0.25` (LONG=0.20)
- `ACCEL_300_MIN_GAP_GROWTH_SHORT = 0.07` (LONG=0.05)
- `ACCEL_300_STALE_BARS_SHORT = 55` (LONG=60)

### P4: accel-300+ LONG — 55% WR but stale entries
**Pattern:** Losses on MON (406t), LINEA (406t), AAVE (344t) — all had high-touch RS levels.
Fix: `ACCEL_300_STALE_BARS = 60` (was 80). Bars_since_cross uses per-direction.

### P5: Regime filtering — 20% haircut not enough
Counter-regime trades at 60% regime conf getting through.
Fix: The RS_TOUCH_HARD_CAP and RS_BROKEN_SHORT_ENABLED naturally filter the worst counter-regime trades.

## All Constants Added to hermes_constants.py

```
RS_DECIDER_MIN_TOUCHES         = 80    # was 150
RS_TOUCH_HARD_CAP              = 150   # NEW
RS_BROKEN_SHORT_ENABLED        = False # NEW
RS_ATR_DIST_FALLBACK           = 999   # NEW
ACCEL_300_MIN_GAP_PCT_LONG     = 0.20  # NEW (explicit)
ACCEL_300_MIN_GAP_PCT_SHORT    = 0.25  # NEW
ACCEL_300_MIN_GAP_GROWTH_SHORT = 0.07  # NEW
ACCEL_300_STALE_BARS           = 60    # was 80
ACCEL_300_STALE_BARS_SHORT     = 55    # NEW
ACCEL_300_MARGINAL_ACCEL_BARS  = 3     # NEW (replaces hardcoded 3)
ACCEL_300_BARS_UNKNOWN         = 999   # NEW (replaces hardcoded 999)
ACCEL_300_BAR_GAP_THRESH_SEC   = 150  # NEW (replaces hardcoded 150)
```

## Hardcoded Values Replaced

| Value | Location | Constant |
|-------|----------|----------|
| `3` | accel_300.py line 352 | `ACCEL_300_MARGINAL_ACCEL_BARS` |
| `999` | accel_300.py line 320 | `ACCEL_300_BARS_UNKNOWN` |
| `150` | accel_300.py line 148 | `ACCEL_300_BAR_GAP_THRESH_SEC` |
| `999` | rs.py lines 550, 617 | `RS_ATR_DIST_FALLBACK` |

## Import Pattern (3-layer)

Every constant used in signal logic must be imported at BOTH module level AND inside the detection function:

```python
# Module level (accel_300.py lines 61-70):
from hermes_constants import (
    ACCEL_300_MIN_GAP_PCT_SHORT, ACCEL_300_STALE_BARS_SHORT,
    ACCEL_300_MARGINAL_ACCEL_BARS, ACCEL_300_BARS_UNKNOWN, ...
)
MARGINAL_ACCEL_BARS = ACCEL_300_MARGINAL_ACCEL_BARS  # local alias

# Inside detect_accel_300() function (lines 183-197):
from hermes_constants import (
    ACCEL_300_PERIOD, ACCEL_300_MIN_GAP_PCT_SHORT, ...
    ACCEL_300_MARGINAL_ACCEL_BARS, ACCEL_300_BARS_UNKNOWN, ...
)
```

## Subagent Audit Lesson

Subagent recommended `ACCEL_300_MIN_GAP_PCT_SHORT = 0.25` but this constant **did not exist** in hermes_constants.py. The subagent was reading from documentation, not actual code. Always `grep -n "ACCEL_300_MIN_GAP_PCT_SHORT" /root/.hermes/scripts/hermes_constants.py` before accepting recommendations. Verify constants exist before patching.