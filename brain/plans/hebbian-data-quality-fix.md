# Plan: Fix Hebbian Gate Data Quality

**Created:** 2026-08-08
**Status:** PENDING
**Priority:** HIGH

## Problem

The Hebbian memory gate in `decider_run.py` makes auto-approve/auto-reject decisions based on token-specific WR estimates from `brain.db`. These estimates are unreliable:

1. **Tiny samples** — Most token+signal combos have n=1-8 trades. Hebbian uses these to estimate WR, which is statistically meaningless.
2. **Wrong predictions** — Actual WR diverges significantly from Hebbian estimates:
   - `accel-300-,rs-s-broken`: Hebbian says 24.6% (n=8), actual is 48.3% (n=1025) — off by -23.7%
   - `inv-accel-300-`: Hebbian says 59.9% (n=5), actual is 32.7% (n=98) — off by +27.2%
   - `tl_break_long`: Hebbian says 100% (n=1), actual is 38.3% (n=94) — off by +61.7%
3. **Missing data** — 7 signals in runtime signal_outcomes are NOT in Hebbian trade_log
4. **Old naming** — Hebbian was seeded from session logs with different signal naming conventions. 839 signals in Hebbian don't match current signal_outcomes.

## Current Architecture

```
signal fires → add_signal() → MC gate (signal_type level)
    → context gate → Hebbian lookup (token+signal level)
        → auto-approve/reject based on WR thresholds
```

- MC gate: runs at `add_signal()` time, blocks by signal_type+direction
- Hebbian gate: runs at context_gate time, blocks by token+signal combo

## Proposed Fixes

### Fix 1: Backfill signal_outcomes into Hebbian trade_log

Feed all586 rows from `signal_outcomes` (with trade_id) into Hebbian `trade_log`. This ensures:
- All current signals have Hebbian data
- Token+signal combos have more samples
- Direction-agnostic fallback has more data

**Script:** `backfill_hebbian_outcomes.py` (exists but may need updating)

### Fix 2: Increase min-n thresholds

Current thresholds in `decider_run.py`:
- `HEBBIAN_BOOST_MIN_N = 5` (soft boost)
- `HEBBIAN_PENALTY_MIN_N = 5` (soft penalty)
- `HEBBIAN_AUTO_MIN_N = 5` (auto-approve/reject)

**Proposed:** Increase to n≥15 for auto decisions, n≥10 for soft advisories. Small samples should not trigger auto-approve/reject.

### Fix 3: Add composite score weight validation

The composite score uses hardcoded weights:
```python
score = 0.4*wr + 0.3*exit + 0.2*token + 0.1*combo
```

These weights were never backtested. Options:
- A) Backtest optimal weights on historical data
- B) Use equal weights (0.25 each) until validated
- C) Remove composite scoring until data quality improves

### Fix 4: Improve direction-agnostic fallback

Current fallback in `hebbian_trade_boost()`:
```python
direction = 'LONG' if '+' in signal else 'SHORT' if '-' in signal else None
result = engine.decayed_wr_estimate(direction, signal)
```

This fails for signals without +/- suffix. Better approach:
- Use the `direction` parameter from the signal (not inferred from name)
- Query `trade_log WHERE signal = ? AND direction = ?` directly

### Fix 5: Add staleness detection

If the last trade for a token+signal combo is >7 days old, the WR estimate may be stale. Add a staleness check:
- If last trade >7 days old, reduce confidence in the estimate
- If last trade >30 days old, treat as no data

## Files to Change

| File | Change |
|------|--------|
| `scripts/backfill_hebbian_outcomes.py` | Update to pull from signal_outcomes |
| `scripts/decider_run.py` | Increase min-n thresholds, fix direction fallback |
| `scripts/hebbian_engine.py` | Add staleness check, fix direction query |

## Success Criteria

- All signal_outcomes with trade_id have corresponding Hebbian trade_log entries
- Auto-approve/reject only triggers with n≥15
- Hebbian WR estimates are within 10% of actual WR for signals with n≥20
- No false auto-approves for signals with n<10

## Risk

- Increasing min-n thresholds means the Hebbian gate fires less often
- This is acceptable — fewer decisions based on bad data is better than many decisions based on noise
- The MC gate and other filters still protect against bad signals
