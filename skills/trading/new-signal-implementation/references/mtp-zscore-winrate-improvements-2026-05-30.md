# mtp-zscore Win-Rate Improvements — 2026-05-30

## Current State

- mtp_zscore fires on 3,456 signals (2,001 LONG, 1,455 SHORT) in signals_hermes_runtime.db
- Has NO divergence protection — unlike zscore_pump which has `_check_divergence()` (lines 93–168)
- zscore_pump divergence gate rejects: z spiked to +3.5+ then falling 5+ bars while price made new highs = reversal trap
- mtp_zscore philosophy: structural trend-following, ride momentum, no mean-reversion, no divergence gate

## Root Cause of Lower Win-Rate

mtp_zscore catches the structural trend correctly but ALSO catches the reversal at the top when z collapses from extreme. zscore_pump's divergence gate avoids these reversal traps. Adding divergence to mtp_zscore would undermine its structural character.

**The right fixes are:**

### 1. Raise Z_MIN bounds (biggest impact — fewer but higher-quality signals)

```
Z_SHORT_Z_MIN = 2.0    # was 1.5 — only fire when short-term momentum is mature
Z_MID_Z_MIN   = 2.0    # was 1.5
Z_LONG_Z_MIN  = 1.5    # keep structural period more sensitive (it has the widest lookback)
```

Current Z_MIN=1.5 on all 3 periods fires on marginal trends. Z_MIN=2.0 requires actual momentum conviction.

### 2. Scale confidence by z-score magnitude

zscore_pump does: `conf_bonus = min(15, (z_abs - threshold) * 5)` — stronger z = higher confidence.
mtp_zscore uses flat 80+5=85 for all signals regardless of z magnitude.

```python
# In scan_mtp_zscore_signals(), compute confidence as:
z_magnitude = abs(sig['z_score'])
conf_bonus = min(10, (z_magnitude - 2.0) * 3)  # stronger z = up to +10 conf
confidence = min(95, MTP_ZSCORE_BASE_CONF + MTP_ZSCORE_CONF_BONUS + conf_bonus)
```

This gives the signal_compactor better signal selection info.

### 3. Extend LB_LONG to 200–300 bars

150 bars on 1m = 150 minutes = 2.5 hours. For "structural" trend detection, this is short.
Extended lookback catches bigger-picture moves:

```
MTP_ZSCORE_LB_LONG = 200   # was 150 — structural, not just multi-hour
```

### 4. Consider shortening cooldown

mtp_zscore: 20 bars (~20 min). zscore_pump: 10 bars (~10 min).
Shorter cooldown lets winners run when the structural trend continues.

## What NOT To Do

- Do NOT add divergence gate to mtp_zscore — that changes its character from structural trend-following to momentum confirmation and defeats the multi-TF design purpose
- Do NOT raise Z_MAX — extended trends hitting z=5-8 are correctly riding momentum; capping too low causes rejection paradox (the exact problem zscore_pump tuning solved)
- Do NOT require 2/3 instead of 3/3 — weakening the agreement requirement dilutes the structural conviction signal

## Constants Summary

```python
# hermes_constants.py — proposed changes
Z_SHORT_Z_MIN  = 2.0    # was 1.5
Z_MID_Z_MIN    = 2.0    # was 1.5
Z_LONG_Z_MIN   = 1.5    # keep at 1.5 (structural period should be more sensitive)
MTP_ZSCORE_LB_LONG = 200   # was 150
# mtp_zscore.py — confidence scaling
# Add z_magnitude conf_bonus in scan_mtp_zscore_signals()
```

## Verification

```bash
# After changes, verify signals still fire (dry run)
cd /root/.hermes/scripts && python3 signals/mtp_zscore.py --dry

# Check signal count vs before
sqlite3 /root/.hermes/data/signals_hermes_runtime.db \
  "SELECT signal_type, direction, COUNT(*) as cnt FROM signals \
   WHERE source IN ('mtp-zscore+','mtp-zscore-') GROUP BY signal_type, direction;"
```