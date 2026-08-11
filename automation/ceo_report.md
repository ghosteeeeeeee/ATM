## CEO Report — 2026-08-12 07:00 UTC

### Diagnosis
SL eval window complete (05:20 Aug 11 → 05:20 Aug 12). Verified DB: 24h 33T, -$0.96, 27.3% WR (RED). 7d 368T, +$0.16, 51.6% WR (barely positive, declining from +$0.45). Daily: Aug 9 +$0.62 (peak), Aug 10 -$0.10, Aug 11 -$0.56 (31.3% WR — worst in week), today partial low volume. Trend: declining since Aug 9 peak.

### Root Cause
1. **SL at 1.2% not improving outcomes** — SL eval window completed, 24h still RED (27.3% WR). atr_sl_hit 19/33 exits (57.6% — elevated). System-wide losses across almost every token (W -$0.25, MEGA -$0.23, ETH -$0.16). This is NEUTRAL regime + mean-reversion getting chopped.
2. **Regime field NULL on ALL trades** — regime not written to trades table (brain.py INSERT missing regime column). Known data quality issue from Aug 10. Without regime data, regime-based filtering and analysis is blind.
3. **trend_momentum_near_sma+ paper test failed** — 0% WR, 3T, -$0.35. Zero wins. Disabled.

### Fix Applied
1. **DISABLED trend_momentum_near_sma+** — TREND_MOMENTUM_NEAR_SMA_ENABLED=False, TREND_MOMENTUM_NEAR_SMA_PLUS_ENABLED=False. Paper test with0% WR, no reason to keep firing.
2. **NO SL param changes** — 7d still positive (+$0.16). SL revert from 0.5% to 1.2% was correct (0.5% caused 64.7% SL hit rate). Current SL at 1.2% is correct; issue is market regime, not SL.

### What NOT to change
- SL params (1.2% min, 2.5% max — correct, 0.5% was worse)
- Trailing distance (0.60%)
- bb_bounce+,range_finder+ (53T +$0.71, 58.5% WR 7d — star)
- bb_bounce+,hzscore+ (33T +$0.20, 48.5% WR 7d — cold streak, not dead)
- SHORT trend filter (15m — working, SHORT profitable 7d)

### Known Issues
- regime field NULL on all trades (data quality, needs brain.py INSERT fix)
- smoke test failing (cosmetic, non-critical, 4+ days)
- Disk 82%

### Verification
Pipeline running, all timers active. 1 open position. Next review: 24h for SL hit rate trend and regime fix progress.
