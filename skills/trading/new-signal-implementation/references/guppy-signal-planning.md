# Guppy MMA Signal — Design Document

## Signal Overview

Daryl Guppy's Multiple Moving Average (MMA) uses two groups of EMAs to capture the tension between retail momentum (fast group) and institutional flow (slow group).

### Groups

| Group | Periods | Source | Interpretation |
|-------|---------|--------|----------------|
| Fast  | 3, 5, 8, 10, 12, 15 | Short-term retail/speculative | Responds quickly, noisy |
| Slow  | 30, 35, 40, 45, 50, 60 | Long-term institutional | Slow, durable trend confirmation |

**Key insight:** When the fast group compresses into a tight bundle and then diverges from the slow group, it signals a trend has begun. The slow group provides institutional confirmation — a fast-group cross without slow-group alignment is noise.

---

## Signal Trigger Conditions

### Entry Signals

**LONG:**
- Fast group crosses ABOVE slow group (all 6 fast EMAs > all 6 slow EMAs)
- OR: Fast group and slow group both ascending AND fast group above slow group
- Confidence boosted when: fast-group bundle is tight (low internal dispersion)

**SHORT:**
- Fast group crosses BELOW slow group (all 6 fast EMAs < all 6 slow EMAs)
- OR: Fast group and slow group both descending AND fast group below slow group

### Squeeze Detection (Pre-Entry Flag)

Guppy's original approach — detect when ALL 12 EMAs compress into a narrow band, then wait for the breakout direction:

```
SQUEEZE = all 6 fast within X% of each other
      AND all 6 slow within X% of each other
      AND fast/slow bundles are close to each other
```

Breakout direction: whichever group breaks the squeeze first determines direction (or require confirmed direction before entry).

### Exit Signals (Guppy Group Flip)

- LONG exit: Fast group flips below slow group, OR any 3+ fast EMAs cross below the midpoint of slow group
- SHORT exit: Fast group flips above slow group, OR any 3+ fast EMAs cross above midpoint of slow group
- Stop: Price closes outside fast-group extreme by ATR threshold

---

## Confidence Scoring

```python
SEPARATION_BONUS  = abs(fast_avg - slow_avg) / slow_avg * 100  # % separation
SLOPE_COHERENCE   = count of same-sign slopes in group / 6      # 0-1
SQUEEZE_PENALTY   = 1.0 if squeeze else 1.0                     # no penalty

confidence = 50 + SEPARATION_BONUS * 10 + SLOPE_COHERENCE * 30
confidence = min(95, confidence)
```

---

## Suggested Backtest Parameters

```python
SHORT_GROUP      = [3, 5, 8, 10, 12, 15]
LONG_GROUP       = [30, 35, 40, 45, 50, 60]
SEP_THRESHOLD    = 0.5   # % separation to confirm trend (min gap)
SQUEEZE_ATR_PCT  = 0.3  # all EMAs within 0.3% of each other = squeeze
MIN_SLOPE_COHERENCE = 0.5  # ≥3/6 same-sign slopes = coherent group
EXIT_ATR_MULT    = 1.5   # Guppy-specific exit: price beyond fast EMA extremes
COOLDOWN_MIN     = 15
```

---

## ATR Exit vs Guardian's Standard Exit

**Critical issue:** The Guardian applies its own ATR(14)×1.5 trailing stop to ALL positions regardless of entry signal. A Guppy-specific ATR exit (using the fast-group extremes as the stop reference) would conflict with the Guardian's generic ATR trailing.

See `references/guppy-signal-exit-routing.md` for the four solution paths and implications for signal design.

---

## Files to Create

```
scripts/guppy_signals.py          # detection engine
scripts/run_guppy_signals.py       # systemd runner
scripts/backtest_guppy.py          # validation
```

## Files to Modify

```
scripts/signal_compactor.py        # add SIGNAL_SOURCE_WEIGHTS entry
```

## Signal Naming

- `signal_type`: `guppy_long`, `guppy_short`
- `source`: `guppy+{conf}`, `guppy-{conf}` (e.g., `guppy+73`)
