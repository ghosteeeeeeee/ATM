# accel-300 LOOKBACK + STALE Interaction (Jun 6 2026)

## The Counterintuitive Formula

```
Detection window starts at: PERIOD + LOOKBACK
was_below_recently check range: i - LOOKBACK to i
```

**Smaller LOOKBACK = wider detection window (starts earlier).**
**Larger LOOKBACK = narrower window (starts later).**

This is documented but still confusing in practice.

## How LOOKBACK=250 Breaks the Signal

With `PERIOD=300`, `LOOKBACK=250`:
- Detection starts at bar 550 (of 700 total)
- Cross for most tokens is at bar 330-450
- bars_since_cross at window start = 550-441 = 109
- ACCEL_300_STALE_BARS=25 → ALL bars rejected as stale

With original `LOOKBACK=30`:
- Detection starts at bar 330
- Same cross at 441
- bars_since_cross = 441-330 = 111 (still > 25!)
- BUT if cross was at ~320-325, bars_since = 5-10 and passes

**The signal only fires when the cross is very recent (within STALE_BARS of window start).**
With any realistic LOOKBACK, the cross is too old.

## Root Cause: Stale Data is Primary Blocker

All 81 fresh tokens (price_age < 3h) fail at the stale filter:

| Filter | Tokens Blocked |
|--------|----------------|
| gap (abs too large) | dominant blocker |
| growth (too small) | secondary |
| stale (bars_since > 25) | ALL remaining |

For PURR:
- cross_bar = 421
- detection start = 550 (LOOKBACK=250)
- bars_since at start = 129
- Every bar in detection window has bars_since 109-257
- All > STALE_BARS=25 → ALL blocked

## Why Historical Worked But Current Doesn't

Historical SHORT trades: 155 trades, 51.6% WR. These fired when:
- LOOKBACK was smaller (30 or similar)
- Market had recent crosses within STALE_BARS of detection window start
- The combination of parameters happened to align

Current market: crosses are 100-250 bars old. The parameters cannot capture them.

## The Fix

Two options:

**Option A — Accept the limitation**: Wait for a token with a cross within STALE_BARS bars of now. No parameter change needed. Signal fires rarely but correctly.

**Option B — Raise STALE_BARS**:
```
ACCEL_300_STALE_BARS = 300  # was 25
```
This makes STALE_BARS so high it effectively disables staleness filtering.
But it also means old crosses (250+ bars) are accepted, which may introduce noise.

**Option C — Lower LOOKBACK**:
```
ACCEL_300_LOOKBACK = 30  # was 250
```
Detection starts at bar 330. If cross is at 325, bars_since=5 and passes.
But this requires a very recent cross — market must have crossed within last ~30 bars.

## MIN_GAP_PCT_SHORT is a MAXIMUM (confirmed Jun 6)

Code: `if abs(gap_pcts[i]) < gap_min: continue`

| Gap | abs(gap) | Passes MIN=0.15? | Quality |
|-----|----------|-------------------|---------|
| -4.39% (XLM) | 4.39% | NO — rejected | BEST momentum |
| -0.05% (chop) | 0.05% | YES — passes | NO trend |

Raising MIN_GAP_PCT_SHORT to 0.50 or 1.0 lets deep gaps through.
Or change logic to `gap_pct < -gap_min` (LONG) / `gap_pct > gap_min` (SHORT).

## Current Constants (Jun 6 2026)

```
ACCEL_300_LOOKBACK = 250
ACCEL_300_STALE_BARS = 25
MIN_GAP_PCT_SHORT = 0.10
ACCEL_300_REGIME_SLOPE_PCT = 0.003
```

## 96h Trade Results (Jun 6 2026)

From trades.json (200 closed, all from past 96h):

| Signal | Trades | Win Rate | Avg PnL |
|--------|--------|----------|---------|
| accel-300-,rs-s-broken SHORT | 138 | 52.9% | +19.18% |
| accel-300+ LONG (all RS variants) | 53 | 9.4% | -58.0% |
| All other SHORTs | 9 | 55.6% | +22.2% |

**Net effect of LONGs: -58% × 53 = -3,074% in losses that destroy SHORT gains.**

The system is a net winner ONLY if LONGs are blocked.

## Recommended Actions

1. **Block accel-300+ LONG entirely** — killswitch via `ACCEL_300_PLUS_ENABLED = False`
2. **Raise MIN_GAP_PCT_SHORT** to 0.50+ to accept deep gaps
3. **Do NOT lower LOOKBACK** — it breaks the was_below_recently logic differently
4. **Accept 0 signals** until market produces a fresh cross within STALE_BARS of detection start
