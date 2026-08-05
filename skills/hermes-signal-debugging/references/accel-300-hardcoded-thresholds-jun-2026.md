# accel-300 Hardcoded Thresholds — Debug Log

## 2026-06-06 AM Session

### 1. ACCEL_300_REGIME_SLOPE_PCT was hardcoded

The regime slope threshold (0.015) was **hardcoded** at `signals/accel_300.py` lines 410/413:
```python
if slope_pct <= 0.015 and direction == 'LONG':
if slope_pct >= -0.015 and direction == 'SHORT':
```

**Fix**: Added `ACCEL_300_REGIME_SLOPE_PCT = 0.008` to `hermes_constants.py` (line 478) and wired it into the import/use in accel_300.py.

### 2. ACCEL_300_STALE_BARS also hardcoded

Hardcoded at `signals/accel_300.py` line 291: `if bars_since_cross > 20:`

**Fix**: Added `ACCEL_300_STALE_BARS = 25` to `hermes_constants.py` (line 479) and wired it in.

### 3. CLI section used non-existent candles_1m table

Lines 554-579 in accel_300.py queried `candles_1m` with columns `ts, close` — table doesn't exist.

**Fix**: Patched to use `price_history` with `timestamp, price` columns.

### 4. Debug Pattern for accel_300

When `accel_300.run()` returns 0 signals, trace each token manually:
```python
from signals.accel_300 import _get_1m_prices, detect_accel_300
prices = _get_1m_prices(token)  # returns list of dicts: [{'timestamp': ..., 'price': ...}]
result = detect_accel_300(token, prices)
```

`_get_1m_prices` returns dicts, NOT tuples — common mistake to try `for ts, price in prices`.

---

## 2026-06-06 PM Session — Gap Threshold is a MAXIMUM (Critical)

### The Core Bug

`MIN_GAP_PCT_SHORT` and `MIN_GAP_PCT_LONG` are implemented as **maximums**, not minimums:
```python
if direction == 'SHORT' and abs(gap_pcts[i]) < MIN_GAP_PCT_SHORT:  # reject
if direction == 'LONG' and gap_pcts[i] < MIN_GAP_PCT_LONG:          # reject
```

For SHORT: `abs(-0.25) = 0.25` is NOT `< 0.15` → rejected. This blocks the **strongest** SHORT momentum (XLM -4.39%, FET -3.11%, MORPHO -0.25%) and only passes shallow 0% to -0.15% dips — exactly the choppy conditions we're trying to avoid.

For LONG: cross at +0.05% (valid trend start) is rejected as "too shallow" — must be between 0% and +0.20%.

### Current Constants (post-session tweaks)
```
MIN_GAP_PCT_LONG            = 0.20   # max, blocks valid trend-start crosses
MIN_GAP_PCT_SHORT           = 0.15   # max, blocks steep momentum drops
ACCEL_300_REGIME_SLOPE_PCT  = 0.008
ACCEL_300_STALE_BARS        = 25
ACCEL_300_PERSISTENCE_BARS  = 4
ACCEL_300_MIN_GAP_GROWTH     = 0.05
LOOKBACK                    = 300    # hardcoded in accel_300.py
```

### Full Universe Filter Breakdown (87 tokens checked)
```
gap:        3158   ← DOMINANT BLOCKER
growth:      536
stale:       204
chop:        124
other:        80
persistent:   28
no_data:      18
expansion:     2
```

### Tokens With Crosses in 300-Bar Window (7 total — all LONG, all fail gap)
```
NOT     LONG  regime=+0.082%  cg=+0.016%  bars=1   need +0.20% → FAIL gap
STRK    LONG  regime=+0.075%  cg=+0.042%  bars=1   need +0.20% → FAIL gap
ASTER   LONG  regime=+0.193%  cg=+0.088%  bars=3   need +0.20% → FAIL gap
ZORA    LONG  regime=+0.087%  cg=+0.013%  bars=3   need +0.20% → FAIL gap
ORDI    LONG  regime=+0.065%  cg=+0.025%  bars=21  need +0.20% → FAIL gap
PEOPLE  LONG  regime=+0.078%  cg=+0.098%  bars=21  need +0.20% → FAIL gap
CAKE    LONG  regime=+0.045%  cg=+0.017%  bars=25  need +0.20% → FAIL gap
```

### Live Trading vs Dry-Run Disconnect
In live trading (96h window, 200 trades):
- accel-300- SHORT: 155 trades, 51.6% WR, avg +0.18% — working correctly
- accel-300+ LONG: 45 trades, 22.2% WR, avg -0.41% — catastrophic, all required RS confirmation

The dry-run lookback window captures a different time slice than live trading. The system CAN find signals in live — the 0 dry-run signals is a separate problem from the live win rate issue.

### Fix Options in hermes_constants

1. **Lower `MIN_GAP_PCT_LONG`** from 0.20 to 0.10 or 0.12 — cross gap just needs to confirm price is above EMA

2. **Raise `MIN_GAP_PCT_SHORT`** to 0.50+ OR change logic to `gap_pct < -threshold` (reject only shallow/flat, accept steep drops)

3. **Increase `LOOKBACK`** from 300 to 400 or 450 — current window too short, misses earlier crosses

4. **Add `ACCEL_300_MIN_CROSS_GAP`** as separate loose check (0.05%) from trailing gap (0.20%)

### Debug Pattern for Zero Signals
1. List all tokens with crosses in 300-bar window — if list is empty, increase LOOKBACK
2. Print regime slope, direction, cross gap (cg), bars_since_cross for each
3. If all failing on gap → threshold too tight → check MIN_GAP_PCT values
4. Check `price_history` staleness — 18 tokens skipped due to stale data
5. Run: `cd /root/.hermes/scripts && PYTHONPATH=/root/.hermes/scripts python3 signals/accel_300.py --dry`

---

## 2026-06-06 Late PM — Regime Filter Blocking (Critical Finding)

### The Blocking Gate: Regime Filter (lines 390-418)

CC is the best candidate — passes ALL upstream gates (gap, persistence, growth, chop, marginal, expansion, staleness gate at detection bar) but `detect_accel_300` returns None. The regime filter is the final blocker.

**CC trace at detection bar 624:**
- gap=-0.575, pers=True, growth=0.051 (PASS), chop=False, marginal=PASS, expansion=N/A (SHORT), stale bx=14<=25 PASS
- Staleness gate (lines 372-388): newest bar 698 confirms SHORT (gap=-1.019 < -0.10) — PASSES
- **Regime filter (lines 390-418): BLOCKS SHORT**

**Why regime blocks CC:**
```python
# Line 415 — regime filter for SHORT:
if slope_pct >= -ACCEL_300_REGIME_SLOPE_PCT:  # slope_pct >= -0.008
    return None  # blocked as NEUTRAL
```

CC's regime slope from 20-row price_history query: **slope_pct = -0.000060 (-0.0060%/bar)**
- -0.000060 >= -0.008 → True → SHORT blocked as NEUTRAL
- The market is technically slightly bearish (-0.006%/bar) but not bearish enough to pass the -0.008 threshold

### Root Cause: Threshold Polarity Confusion

`ACCEL_300_REGIME_SLOPE_PCT = 0.008` means:
- LONG fires when slope_pct > +0.008 (bullish market required)
- SHORT fires when slope_pct < -0.008 (bearish market required)

A slope of -0.00006 is closer to 0 than -0.008, so it's classified as NEUTRAL — not bearish enough for SHORT.

### All 11 Crossed Coins Are Stale

After LOOKBACK=250 was set, 11 coins had crosses in the lookback window:
```
HYPER(81), TRX(83), CAKE(87), STX(94), MNT(104),
KNEIRO(142), KPEPE(142), KSHIB(144), KBONK(146), KFLOKI(146), CC(149 bars ago)
```
ALL have bars_since_cross > ACCEL_300_STALE_BARS=25 → stale-blocked even if regime passed.

### LOOKBACK Constant Was Being Ignored

**Bug**: accel_300.py line 70 had `LOOKBACK = 30` hardcoded — did NOT import or use `ACCEL_300_LOOKBACK` from hermes_constants. Only `ACCEL_300_REGIME_SLOPE_PCT` and `ACCEL_300_STALE_BARS` were wired in.

**Fix applied**: Patched accel_300.py lines 55-62 to add `ACCEL_300_LOOKBACK` to the import list, and line 70 to use `LOOKBACK = ACCEL_300_LOOKBACK`.

### Current Constants (post-session)
```
ACCEL_300_LOOKBACK           = 250   # was 20, was hardcoded 30 in signal
ACCEL_300_REGIME_SLOPE_PCT  = 0.008
ACCEL_300_STALE_BARS        = 25
MIN_GAP_PCT_LONG             = 0.15
MIN_GAP_PCT_SHORT            = 0.10
ACCEL_300_MIN_GAP_GROWTH     = 0.05
ACCEL_300_PERSISTENCE_BARS   = 4
```

### Regime Filter Fix Options

1. **Lower ACCEL_300_REGIME_SLOPE_PCT to 0.005 or 0.004** — lets near-neutral slopes through (slope of -0.00006 would pass at -0.005)
2. **Raise ACCEL_300_REGIME_SLOPE_PCT to 0.015** — only pass tokens with genuinely strong trends; CC (-0.006%/bar) is too weak
3. **Raise ACCEL_300_STALE_BARS to 200+** — all 11 crossed coins have bars_ago 81-149, need threshold >= 149 to capture CC

### Debug Pattern for Regime Filter (lines 390-418)

To manually check a token's regime slope:
```python
import sqlite3, statistics
token = 'CC'
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
print(f"slope_pct = {slope_pct:.6f} ({slope_pct*100:.4f}%/bar)")
print(f"SHORT blocked if slope_pct >= -0.008: {slope_pct >= -0.008}")
```
