# accel-300 Full Debug Reference — All Sessions Combined

## Session1: Hardcoded Thresholds (2026-06-06 AM)

### Bugs Found
1. `ACCEL_300_REGIME_SLOPE_PCT` hardcoded at lines 410/413 as 0.015
2. `ACCEL_300_STALE_BARS` hardcoded at line 291 as 20
3. CLI section queried non-existent `candles_1m` table

### Fixes Applied
- Added `ACCEL_300_REGIME_SLOPE_PCT = 0.008` to hermes_constants.py
- Added `ACCEL_300_STALE_BARS = 25` to hermes_constants.py
- Patched accel_300.py to use `price_history` table with `timestamp, price` columns

### Current Constants (post-session)
```
ACCEL_300_REGIME_SLOPE_PCT = 0.008
ACCEL_300_STALE_BARS = 25
ACCEL_300_PERSISTENCE_BARS = 4
ACCEL_300_MIN_GAP_GROWTH   = 0.05
MIN_GAP_PCT_LONG           = 0.20
MIN_GAP_PCT_SHORT          = 0.15
```

---

## Session 2: Gap Threshold is a MAXIMUM (2026-06-06 PM)

### The Core Bug
`MIN_GAP_PCT_SHORT` and `MIN_GAP_PCT_LONG` are implemented as **maximums**, not minimums:
```python
if direction == 'SHORT' and abs(gap_pcts[i]) < MIN_GAP_PCT_SHORT:  # reject
```
This blocks the **strongest** SHORT momentum and only passes shallow dips.

### Full Universe Filter Breakdown (87 tokens)
```
gap:      3158  ← DOMINANT BLOCKER
growth:    536
stale:     204
chop:      124
other:      80
persistent:  28
no_data:     18
expansion:    2
```

### Tokens With Crosses (all LONG, all fail gap)
NOT, STRK, ASTER, ZORA, ORDI, PEOPLE, CAKE — all fail MIN_GAP_PCT_LONG=0.20

---

## Session 3: Regime Filter Blocking (2026-06-06 Late PM)

### CC Blocked by Regime Filter
CC passes ALL upstream gates but regime filter blocks at line 415:
```python
if slope_pct >= -ACCEL_300_REGIME_SLOPE_PCT:  # slope_pct >= -0.008
    return None
```
CC slope = -0.000060%/bar — closer to 0 than -0.008 → classified NEUTRAL.

### All 11 Crossed Coins Are Stale
HYPER(81), TRX(83), CAKE(87), STX(94), MNT(104), KNEIRO(142), KPEPE(142), KSHIB(144), KBONK(146), KFLOKI(146), CC(149)
ALL have bars_since_cross > STALE_BARS=25.

### LOOKBACK Constant Was Being Ignored
Line 70 had `LOOKBACK = 30` hardcoded — did NOT import `ACCEL_300_LOOKBACK` from hermes_constants.

### Fix Applied
Patched accel_300.py lines 55-62 to import and use `ACCEL_300_LOOKBACK`.

---

## Session 4: Market Chop Not a Bug (2026-06-06 Late PM)

### Finding
accel-300 returning 0 signals in trending market — market is mid-pullback after initial move, not a signal bug. The signal fires at START of trending moves. During consolidation, gap_growth and marginal_accel fail correctly.

### Win Rate Reality
- accel-300 LONG: 9.4% WR, -58% avg return — CATASTROPHIC
- accel-300 SHORT: 51.6% WR, +0.18% avg — working correctly
- rs-s-broken SHORT: 52.9% WR — working

**accel-300 LONG is the problem, not the 0-signal state.**

---

## Session 5: STALE_LOOKBACK=10 Blocks All Detection (2026-06-08)

### Root Cause
STALE_LOOKBACK=10 is mathematically incompatible with LOOKBACK_1M=700:
- Detection starts at PERIOD(300) + LOOKBACK(30) = bar 330
- bars_from_latest at i=330 = 700-1-330 = **369**
- STALE_LOOKBACK=10 requires bars_from_latest <= 10
- Result: only bar i=689 (last 10 bars) can fire

### ema300 NoneType Crash
Cross-bar search `closes[j-1] >= ema300[j-1]` crashes when `ema300[j-1]` is None during warmup. Fixed with `ema300[j-1] is not None` guard.

### CHOP Parameters Not Loosened
- `ACCEL_300_CHOP_AVG_GAP_PCT=0.90` — comment says "loosen to 0.50" but never changed
- `ACCEL_300_CHOP_CROSS_GAP_PCT=0.22` — comment says "loosen to 0.10" but never changed

---

## Session 6: Chop Filter vs Early Entry (2026-06-08 Late)

### AVNT SHORT — Textbook Early Entry
- Cross at 21:26 UTC, gap = -0.11% (barely through EMA)
- 2 bars later: -0.53%
- Final: -1.72% (30 min after cross)
- gap expansion ratio: **120x**

AVNT fails chop because cross gap0.014% < CHOP_CROSS_GAP_PCT=0.22.

### Param Impact Matrix
| Config | STALE_BARS | STALE_LOOKBACK | CHOP_AVG | CHOP_CROSS | Signals |
|--------|-----------|---------------|---------|---------|---------|
| current | 10 | 10 | 0.90 | 0.22 | 0 |
| stale_only | 80 | 400 | 0.90 | 0.22 | 0 |
| loose_chop | 80 | 400 | 0.50 | 0.10 | 32 |
| no_chop | 80 | 400 | 0.05 | 0.01 | 172 |

### Recommended Fixes
| Param | Current | Proposed |
|-------|---------|----------|
| `ACCEL_300_STALE_BARS` | 10 | 80 |
| `ACCEL_300_STALE_LOOKBACK` | 10 | 400 |
| `ACCEL_300_CHOP_AVG_GAP_PCT` | 0.90 | 0.05 |
| `ACCEL_300_CHOP_CROSS_GAP_PCT` | 0.22 | 0.01 |

---

## Debug Patterns

### Pattern 1: Zero Signals — Trace Each Gate
```python
from signals.accel_300 import _get_1m_prices, detect_accel_300
prices = _get_1m_prices(token)  # returns list of dicts: [{'timestamp':..., 'price':...}]
result = detect_accel_300(token, prices)
```

### Pattern 2: Regime Slope Manual Check
```python
import sqlite3, statistics
conn = sqlite3.connect('/root/.hermes/data/signals_hermes.db', timeout=10)
rows = conn.execute(
    "SELECT price FROM price_history WHERE token=? ORDER BY timestamp DESC LIMIT 20",
    (token.upper(),)
).fetchall()
closes_20 = [r[0] for r in reversed(rows)]
n = len(closes_20)
mean_x = (n - 1) / 2.0
mean_y = statistics.mean(closes_20)
cov = sum((i - mean_x) * (closes_20[i] - mean_y) for i in range(n))
var_x = sum((i - mean_x) ** 2 for i in range(n))
slope_pct = (cov / var_x) / mean_y if mean_y > 0 else 0
print(f"slope_pct = {slope_pct*100:.4f}%/bar")
```

### Pattern 3: Full Param Impact Test
```python
configs = [
    ("current",    10,  10,  0.90, 0.22),
    ("stale_only", 80, 400, 0.90, 0.22),
    ("loose_chop", 80, 400, 0.50, 0.10),
    ("no_chop",    80, 400, 0.05, 0.01),
]
# Count signals per config to measure gate impact
```

### Pattern 4: Gate-by-Gate Trace
```
G1 stale_bar: bars_since_cross >= STALE_BARS → BLOCK
G2 stale_lookback: bars_from_latest > STALE_LOOKBACK → BLOCK
G3 gap_expansion: gap grew by MIN_GAP_EXPANSION since cross → PASS
G4 marginal: dl (log diff) vs dp (price diff) check
G5 regime_slope: price slope in SLOPE_WINDOW must be <= -REGIME_SLOPE_PCT (SHORT)
G6 stale_gap_decay: abs(now_gap) >= STALE_GAP_DECAY_THRESHOLD * abs(signal_gap)
G7 chop: 3 sub-checks (cross_gap, ema_angle, avg_gap) — any True → BLOCK
```
