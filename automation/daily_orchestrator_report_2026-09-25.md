# Daily Orchestrator Report — 2026-09-25

## PIPELINE STATUS
- **24h:** 18T, 44.4% WR, -$1.07 (DB-verified)
- **7d:** 212T, 43.4% WR, -$2.02
- **14d:** 427T, 47.8% WR, -$3.73
- **Open:** 1
- **ATR_SL hit rate:** 61.8% 7d (CRITICAL)

## TEAM ACTIVITY
- **signal_reporter (05:09 UTC):** No kills — no signals met all3 24h kill criteria. pump-chain- SHORT 58.3% WR -$0.42 on watch (R:R issue). Found volatility_regime column mismatch bug. No inversions.
- **health_monitor (05:45 UTC):** System OK. hl_sync flagged as CRITICAL (false alarm — log rotated to .gz).
- **auto_1hr (05:18 UTC):** hl_sync false alarm. No kill candidates. FAVORITES: DEMOTE FIL/FOGO/SYRUP, PROMOTE CASHCAT. LOSERS: ADD KAS/AZTEC/CAKE.
- **auto_1hr (06:11 UTC):** No changes needed. No kill candidates, no overtrading.

## ANALYSIS
1. **hl_sync false alarm** — Service `hermes-hl-sync-guardian.service` is active and running. Log file rotated to `.log.gz`. Health check looks for uncompressed file. Not a real issue.
2. **ATR_SL hit rate 61.8%** — Structural issue. 131/212 exits via ATR stop loss in 7d. Needs CEO decision on ATR_SL_MIN adjustment.
3. **SHORT_RSI_FLOOR potential leak** — 2 pump-chain- SHORT trades on Sep 24 (16:16, 21:46) had detection-time RSI<50 (41.66, 47.06) yet executed after the SHORT_RSI_FLOOR=50 hard block fix. Both small wins ($0.03). Root cause unclear — may be timing issue with fix deployment or `signal_metadata` not propagating correctly to hotset.
4. **pump-chain- V5_SHORT trades aging out** — 11T in 24h all from Sep 24 (pre-disable). Disable working.
5. **Signal diversity** — Only pump-chain+ LONG and volume-breakout-long+ carry system in NEUTRAL.

## IMPLEMENTED TODAY
No code changes — monitoring mode.

## CRITICAL ISSUES
1. ATR_SL hit rate 61.8% 7d — needs CEO decision
2. SHORT_RSI_FLOOR potential leak — 2 trades RSI<50 executed post-fix

## NEXT STEPS
1. Monitor ATR_SL hit rate — if stays above 60%, escalate to CEO
2. Investigate SHORT_RSI_FLOOR leak — check if `signal_metadata` propagates to hotset correctly
3. Signal diversity — need new NEUTRAL signals
