## CEO Report — 2026-08-16 (42nd run)

### Diagnosis
ct-hot+ is the ONLY drag on the system. Today: 12T, 25% WR, -$0.49 (100% of daily loss). ALL 11 ct-hot+ trades in NEUTRAL regime — signal fires on coin_tracker setups with barely-passing composite in flat markets. Non-ct-hot system: 28T, -$0.09 (flat/healthy). PM_TRAIL carrying system: 43T/48h, 69.8% WR, +$1.22. ATR_SL dominant exit: 39T/48h, 2.6% WR, -$2.42 (ct-hot+ = 18/39 = 46% of all stops).

### Root Cause
MIN_COMPOSITE 70 insufficient filter for NEUTRAL regime. ct-hot+ fires on coin_tracker setups with composite just above threshold, but flat markets produce immediate ATR_SL exits.

### Fix Applied
RAISED MIN_COMPOSITE 70→75. Targets <5 ct-hot+ trades/24h while maintaining >20T daily trades. Pipeline restarted.

### Verification
Monitor 24h: ct-hot+ trade count (should drop from 12→<5), daily trades (must stay >20T), PM_TRAIL WR (must hold >65%), overall PnL (should improve from -$0.58/day).
