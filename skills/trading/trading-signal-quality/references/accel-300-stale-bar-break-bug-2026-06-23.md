# accel-300 Stale-Bar `break` Bug (2026-06-23)

## Symptom (User-Reported)

> "regularly long trades where the price is below the EMA300, and the reverse
> shorts when the price is above the EMA300, both those conditions should not
> be allowed according to the logic the signal was designed for"

User saw accel_300_long signals fire and HL open LONG trades while the price
was on the wrong side of EMA300, and the mirror SHORT case. Per-trade
direction was inverted relative to the signal's stated intent.

## Measured Impact

Out of **3,537 accel_300 signals emitted on 2026-06-23**, **1,112 (31%) had
direction INVERTED vs. price-vs-EMA at signal time**. Verified by:

1. Querying `signals_hermes_runtime.db` for all `accel_300_long` /
   `accel_300_short` rows from 2026-06-23.
2. For each signal, replicating the detection logic against `signals_hermes.db`
   price_history to find which bar `i` the production code would have returned.
3. Comparing bar `i`'s gap to the LATEST bar's gap at signal time.

Many signals had signal bars **300+ minutes stale** (hit the
ACCEL_300_STALE_LOOKBACK=400 ceiling).

## Root Cause (Single Line)

File: `/root/.hermes/scripts/signals/accel_300.py`

Line 267:
```python
for i in range(PERIOD + LOOKBACK, len(closes) - 1):
```

Line 619:
```python
signal_bar = {...}
break
```

The detection loop walks forward through all 700+ bars of price history.
`break` exits on the FIRST bar that passes all gates. Going forward, the
first match is the **OLDEST** qualifying bar in the dataset — not the most
recent.

The comment at lines 608-610 is self-contradictory:
```
# Found a qualifying bar — save its state and break to return the MOST RECENT.
# Scanning forward keeps the last (most recent) match.
```
"break on first match going forward" returns the FIRST (oldest) match. The
claim "scanning forward keeps the last match" is wrong.

## Mechanism (Step by Step)

1. Scanner runs every minute, pulls 700 bars of 1m prices.
2. Detection walks all 700 bars, looking for ANY bar where all 10 conditions
   pass (min gap, persistence, cross exists, cross-back check, gap growth,
   gap expansion, marginal accel, regime slope, stale gap decay, chop filter).
3. First qualifying bar going forward is returned. For most tokens this is
   a bar from **hours ago** (e.g., 18:51 when scan runs at 20:47).
4. Signal row written with `direction = LONG/SHORT` based on bar `i`'s
   price-vs-EMA. AT BAR `i`, the direction is correct.
5. Signal row's `price` field comes from the SCANNER's prices_dict
   (`price = data.get('price')`, line 660) — the LIVE current price, NOT
   bar `i`'s price.
6. By the time signal_compactor → guardian → HL opens the trade, the LIVE
   price has often already reversed through the EMA.
7. Trade opens LONG with price below EMA300, or SHORT with price above
   EMA300 — the user-visible symptom.

## Why the Original Audit Missed It

The first audit (2026-06-23) built a docstring-vs-implementation matrix
and verified every gate was wired correctly. It missed this bug because:

- Every gate IS technically correct.
- The bug is in the SCAN PATTERN (forward + break-on-first), not in any gate.
- The semantic "return the most recent" is in the COMMENT, not enforced by
  the code structure.

The audit added a CRITICAL "Condition 1 no-op for SHORT" finding from the
docstring/implementation matrix, but that was a separate bug — the user's
actual symptom (31% directional inversion) wasn't visible until live signals
were traced against bar-level state.

**Lesson: code audits must trace live signals, not just verify gates are wired.**
See `references/signal-code-audit-methodology.md` step 7.

## Reproduction Recipe

```python
import sqlite3
from datetime import datetime, timezone

def find_first_qualifying_bar(token, direction, prices, ema_series):
    """Replicate production logic: scan forward, break on FIRST match."""
    PERIOD, PERSISTENCE_BARS = 300, 2
    LOOKBACK, LOOKBACK_SHORT = 30, 500
    MIN_GAP_LONG, MIN_GAP_SHORT = 0.20, 0.25
    MIN_GROWTH, MIN_GROWTH_SHORT = 0.05, 0.07
    STALE_BARS, STALE_BARS_SHORT = 60, 55
    STALE_LOOKBACK, MARGINAL_ACCEL_BARS = 400, 3
    REGIME_SLOPE_PCT, SLOPE_WINDOW = 0.003, 20
    CROSS_LOOKBACK = 100
    n = len(prices)
    closes = prices
    gap_pcts = [None]*n
    for i in range(n):
        if ema_series[i] is None or ema_series[i] == 0: continue
        gap_pcts[i] = (closes[i]-ema_series[i])/ema_series[i]*100
    # ... full replica of accel_300.py detection (omitted here, see actual file)
    # The key: for i in range(PERIOD + LOOKBACK, n - 1): ... break on first match

# Then compare: signal_bar_idx vs latest_idx, signal_bar gap vs latest gap
```

## The Fix (Option 1A)

Replace line 267 of `/root/.hermes/scripts/signals/accel_300.py`:

```python
# BEFORE
for i in range(PERIOD + LOOKBACK, len(closes) - 1):

# AFTER
for i in range(len(closes) - 2, PERIOD + LOOKBACK - 1, -1):
```

Walking backward, first match = MOST RECENT qualifying bar. The staleness
check at line 534 (`bars_from_latest > ACCEL_300_STALE_LOOKBACK`) and the
stale-gap-decay check at line 575 (using `newest_idx = len(closes) - 2`)
remain consistent — `len-2` is the highest index the backward scan can
reach on its first iteration, which is exactly the bar used for the
stale-gap-decay comparison.

## Belt-and-Suspenders Tightening

Also recommended: tighten `ACCEL_300_STALE_LOOKBACK` from 400 (≈6.7 hours)
to ~15 (15 minutes). Even with Option 1A, allowing signals more than 15
minutes old is too permissive given the comment in the file:
"signal must fire within tight window of latest bar."

If MIN_GAP_EXPANSION / cross-back checks cause any of the gates to skip
on the most recent bars, this tightening will surface those cases as
"no signal" rather than letting the code reach back to an old bar.

## Related

- `references/signal-code-audit-methodology.md` — step 7 (live-signal trace)
- `references/accel-300-root-cause-jun-2026.md` — earlier mean-reversion
  trap finding (separate bug, also accel-300)
- `references/accel-300-lookback-stale-jun-2026.md` — earlier
  LOOKBACK/STALE_BARS interaction analysis (different stale axis)
