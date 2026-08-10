## CEO Report — 2026-08-10 — URGENT: SL Bug

### Diagnosis

5 open trades have SL at exactly 1.2% (`ATR_SL_MIN` floor). User reports: "these SL should not be possible, we just adjusted the SL a little while ago."

| Coin | Dir | Entry | Current | PnL% | SL Distance |
|------|-----|-------|---------|------|-------------|
| CELO | LONG | $0.0640 | $0.0639 | -0.50% | -1.20% |
| LINK | LONG | $8.2736 | $8.2335 | -0.52% | -1.25% |
| MORPHO | LONG | $1.9444 | $1.9264 | -0.75% | -1.27% |
| BSV | SHORT | $14.3510 | $14.3500 | -0.06% | +1.20% |
| XRP | SHORT | $1.0184 | ~$1.018 | +0.01% | +0.21% |

### Root Cause

**Code forces 1.2% minimum SL for trades in loss.** In `tpsl_utils.py:530-531`:
```python
new_sl = min(new_sl, round(entry_f * (1 - ATR_SL_MIN), 8))
```

This enforces `ATR_SL_MIN = 0.012` (1.2%) as an absolute floor for all trades in loss, regardless of any manual SL adjustment. The trailing logic overrides manual changes back to 1.2%.

### Fix Options

1. **Tighten `ATR_SL_MIN`** in `hermes_constants.py` (e.g., from 0.012 to 0.005) — affects all trades globally
2. **Add manual SL override support** — allow DB `sl_distance` to override the computed value when manually set
3. **Check if user's adjustment was meant for trailing distance** — recent commit `3f2effe` tightened `TRAILING_DISTANCE_PCT` from 0.7% to 0.3%, but that only affects trades IN PROFIT, not trades in loss

### Recommendation

Clarify what the user adjusted:
- If they tightened `ATR_SL_MIN`: verify the value persisted in `hermes_constants.py`
- If they want manual SL overrides: need code change to respect manual adjustments
- If they expected trailing to tighten: trailing only works on trades in profit (these are in loss)

### Verification
All 5 trades show `sl_distance = 0.012` in DB. This is the `ATR_SL_MIN` floor being enforced by tpsl_utils.py trailing logic.
