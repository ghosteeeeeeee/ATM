# Ghost Trade: zscore_pump z≈0 Signal (2026-05-17)

## Symptom
ETHFI LONG opened @ $0.3877, closed in ~30 seconds at SL, PnL ~0%.
Display showed: `z-score=0.000` — exactly zero.

## Root Cause
`zscore_pump` computes z_score as `(current_price - ema300) / ema300_std`. When price is exactly at the EMA300 mean, z=0.0.

A z_score of exactly 0.0 means:
- No directional bias — price is statistically at the mean
- The signal barely qualified (probably `MIN_ZSCORE=0` threshold lets it through)
- The trade direction has NO momentum conviction behind it
- Any adverse move immediately hits the SL

This is different from `z_score=None` which is a merge bug (RS signal overwriting z_score during merge).

## The Fix
Consider adding a minimum z_score threshold for zscore_pump signals in decider:

In `signals/zscore_pump.py` or `decider_run.py`, reject signals where `abs(z_score) < 0.3` or so:
```python
# Require minimum conviction
if abs(sig['z_score']) < 0.3:
    logger.warning(f"{tok}: z_score={sig['z_score']:.3f} below threshold, skipping")
    continue
```

Or in `signal_compactor`, flag low-conviction signals in `signals.json`:
```json
{
  "token": "ETHFI",
  "zscore": 0.0,  // zero conviction — display should warn
  "low_conviction": true
}
```

## Key Distinction

| z_score value | Meaning | Action |
|---|---|---|
| `z_score > 0.5` | Strong directional bias | Normal SL placement |
| `0 < z_score < 0.3` | Weak, near-mean | Warn in display or reject |
| `z_score ≈ 0.0` | No conviction, random walk | Reject or flag |
| `z_score = None` | Merge bug (RS overwrites) | Fix signal_schema.py UPDATE |

## ETHFI Trade Chain
1. `rs-s42, rs-s98` → support resistance signals, no z_score
2. `zscore-pump+` → z_score=0.0 for ETHFI (price at mean)
3. Merged: `rs-s42,rs-s98,zscore-pump+` → z_score=None (merge bug overwrote 0.0)
4. Trade opened @ $0.3877, SL placed via pump-mode (1.5%), hit in ~30s
5. Display showed `z-score=0.000` in the trade row

The display `z-score=0.000` and the DB `z_score=None` are two separate issues:
- Display: the `signals.json` zscore field reads from hotset entry which has no z_score
- DB: the merged signal's z_score was overwritten to NULL by RS signal during merge