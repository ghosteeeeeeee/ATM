# Signal Quality Lessons — June 9, 2026

## RS Touch Count Hard Cap — Don't Speculate, Trust the Data

**RS_TOUCH_HARD_CAP=150 was raised to 180** on the basis that "151-180 range has some validity."
This was speculation. The authoritative data: 120-1380 touches = 0% WR.
Result: UNI (152), ADA (164), ORDI (154) — all passed the 180 cap, all lost.
**Never raise RS_TOUCH_HARD_CAP above the data. Cap at 120.**

The cap only blocks NEW signals going forward. Old signals in the DB already have
high touch counts (created before the cap was lowered) and will still execute if they
pass other gates. This is why the same tokens (UNI, ADA, ORDI) kept appearing.

## rs-r-broken LONG — The Missing Killswitch

**RS_BROKEN_SHORT_ENABLED=False** (kills rs-s-broken SHORT) was already in place.
But there was **NO killswitch for rs-r-broken LONG**.

rs-r-broken path: price breaks through resistance level → system fires LONG expecting
a bounce at the broken level. Counter-trend trap. BLUR (-0.52%) and BRETT (-1.03%)
both lost on this path.

**Fix:** `RS_BROKEN_RESISTANCE_LONG_ENABLED=False` added to hermes_constants.py.
Also added to rs.py imports and the broken resistance LONG block at line 633.
When killswitch fires: `nearest_resistance = None` AND `cand_signal = None`
The explicit `cand_signal = None` is required to avoid LSP possibly-unbound error
at the signal update line (675).

## Two-Path Kill-Switch Architecture

Both broken-level paths need independent killswitches:

| Path | Signal | Direction | Killswitch Constant | Default |
|------|--------|-----------|---------------------|---------|
| rs-s-broken | Support broken → fires SHORT | SHORT | `RS_BROKEN_SHORT_ENABLED` | True (enabled) |
| rs-r-broken | Resistance broken → fires LONG | LONG | `RS_BROKEN_RESISTANCE_LONG_ENABLED` | True (enabled) |

When adding a killswitch to a broken-level path in rs.py:
1. Add constant to hermes_constants.py with clear comment
2. Add to rs.py imports (line ~48-51)
3. Wrap the signal generation block: `if not KILLSWITCH: nearest_xxx = None; cand_signal = None`
4. Set `cand_signal = None` explicitly (not just `nearest_xxx = None`) to avoid unbound variable at signal update

## Accel-300 Standalone Bypass Is Fundamentally Broken

**ACCEL_300_STANDALONE_BYPASS_CONFIDENCE=70** was set to allow strong pure accel-300
signals to bypass confluence. But accel-300 fires at conf=70 exactly (capped).
So threshold <=70 passes ALL pure accel-300 signals. Threshold >70 passes NONE.
**The concept is broken at the architecture level. Pure accel-300 has ~40% WR — firing
all of them through a bypass created losses.**

ACCEL_300_STANDALONE_BYPASS_ENABLED=False (reverted).
If a standalone bypass is ever needed again: use a different metric (e.g., gap_pct
threshold, not confidence), not conf.

## Confluence Gate — No Exceptions

The confluence gate (signal_compactor.py lines 571-589) requires 2+ unique signal types.
Every attempt to bypass it (standalone bypass, loosened thresholds) has caused losses.
**Signals must always have confluence. Period.**

## Key Parameters (hermes_constants.py)

```
RS_TOUCH_HARD_CAP                = 120   # block touch >= 121
RS_DECIDER_MIN_TOUCHES           = 80    # decider min touch
RS_BROKEN_SHORT_ENABLED          = False # kills rs-s-broken SHORT
RS_BROKEN_RESISTANCE_LONG_ENABLED = False # kills rs-r-broken LONG (2026-06-09)
ACCEL_300_STANDALONE_BYPASS_ENABLED = False
ACCEL_300_MIN_GAP_PCT_LONG       = 0.20
ACCEL_300_MIN_GAP_PCT_SHORT      = 0.25
ACCEL_300_MIN_GAP_GROWTH_SHORT   = 0.07
ACCEL_300_STALE_BARS             = 60    # LONG stale threshold
ACCEL_300_STALE_BARS_SHORT       = 55    # SHORT stale threshold
CONFLUENCE_REQUIRED               = True
```

## Winning Signal Patterns (from 11 trades, June 9)

| Signal | Result | Key Factor |
|--------|--------|-----------|
| accel-300+,rs-s136 (CAKE LONG) | WIN +0.97% | touch=136 (below cap), proven support |
| accel-300-,rs-r106 (2Z SHORT) | WIN +1.12% | touch=106 (low, proven) |
| accel-300+,rs-s16 (AAVE LONG) | WIN +0.85% | touch=16 (fresh level) |
| accel-300-,rs-r76 (2Z SHORT) | WIN +0.98% | touch=76 (low, proven) |

Losing signals: all had either broken-level paths (BLUR/BRETT rs-r-broken),
high touch counts >=120 (UNI/ADA/ORDI), or low touch counts that weren't proven (AAVE rs-s44).

## If WR Still Below 75% After These Fixes

Next surgical parameter changes (in order):
1. `RS_DECIDER_MIN_TOUCHES = 80` → raise to `100` (decider requires higher touch)
2. `RS_DECIDER_CONF_FLOOR = 60` → raise to `65` (block low-confidence trades)
3. `ACCEL_300_MIN_GAP_PCT_SHORT = 0.25` → raise to `0.30` (stricter SHORT accel)
4. `ACCEL_300_MIN_GAP_GROWTH_SHORT = 0.07` → raise to `0.10` (stricter SHORT momentum)

Wait one cycle between changes. Never change multiple parameters simultaneously.