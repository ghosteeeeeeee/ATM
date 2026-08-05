# SHORT ATR TP/SL Discrepancy — 2026-05-18

## Symptom

SNX SHORT and ADA LONG show different TP% magnitudes from the same ATR source:

| Trade | Dir | Entry | TP | TP% from entry | ATR% (approx) | Expected TP% (k_tp×ATR) |
|-------|-----|-------|----|---------|------|------|
| ADA | LONG | $0.2510 | $0.2548 | +1.8% | ~0.70% | +0.875% |
| SNX | SHORT | $0.3034 | $0.2964 | +2.6% | ~0.70% | +0.875% |

Both trades have similar ATR (~0.70%), both should use k_tp=1.25 → TP% ≈ 0.875%.
ADA is using a 1.5% TP floor (ATR_TP_MIN) — correct.
SNX is using ~2.6% — NOT the ATR floor, NOT 1.25×ATR — appears to use a different constant.

## Root Cause Hypothesis

**SHORT TP path in `compute_atr_sl_tp()` uses wrong sign or wrong constant.**

For SHORT, TP should be:
```
new_tp = round(ref_price * (1 - eff_tp_pct), 8)   # ref_price = lowest_price
```

If the SHORT TP is accidentally computed as:
```
new_tp = round(ref_price * (1 + some_default_pct), 8)   # WRONG: + instead of -
```

Then `some_default_pct` must be ≈ 0.026 to produce TP=$0.2964 from ref_price=$0.3034:
```
0.3034 * (1 + 0.026) = 0.2964   ← this is GOING THE WRONG DIRECTION
```

But if the formula had a sign flip:
```
new_tp = round(entry * (1 - 0.026), 8) = 0.2964   ← CORRECT direction
```

This suggests the SHORT TP is using a **hardcoded fallback** (TP_PCT_FALLBACK or similar) rather than the ATR-computed `k_tp × ATR`.

## Pending Investigation

- Confirm whether SHORT TP path in `tpsl_utils.py` is bypassing `hermes_constants` for TP
- Trace actual constant used for SNX SHORT TP% ≈ 2.6%
- Check if `TP_PCT_FALLBACK = 0.08` (8%) or `SL_PCT_FALLBACK = 0.015` (1.5%) is leaking into SHORT TP via a wrong variable or wrong branch
- Compare with LONG TP path to identify asymmetry

## Key Diagnostic

```bash
# Check TPSL pipeline log for SNX SHORT
grep "SNX" /root/.hermes/logs/pipeline.log | grep -E "ATR|TPSL|PERSIST" | tail -20

# Check what TP% was written to DB
psql "host=/var/run/postgresql dbname=brain user=postgres password=Brain123" \
  -c "SELECT token, direction, entry_price, target, stop_loss FROM trades WHERE token='SNX' AND status='open';"
```

## Related Files

- `tpsl_utils.py` — `compute_atr_sl_tp()` SHORT TP branch (around line 400+)
- `hermes_constants.py` — `TP_PCT_FALLBACK=0.08`, `ATR_TP_MIN=0.015`, `ATR_TP_K_MULT=1.25`
