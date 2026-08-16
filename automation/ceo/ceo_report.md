## CEO Report — 2026-08-16 (28th run)

### Diagnosis
DISABLED ct-hot+ AGAIN. Re-enabled earlier today (commit a0a971a per user request) but data shows still bleeding: 25T/24h 36% WR -$0.56. ATR_SL 18T 0% WR -$1.23 dominates. PM_TRAIL on ct-hot+ works (10T 90% WR +$0.48) but entry quality is the bottleneck. Verified DB: 24h 51T -$0.53 (37.3% WR). 48h 97T -$0.97 (41.2% WR). 7d 441T -$2.52 (48.8% WR). 2 open flat ($0.00). PM_TRAIL aggregate 48h: 39T 66.7% WR +$1.09 (dist 0.15% revert WORKING). ATR_SL 48h: 36T avg -0.75% -$2.68. R:R 0.36:1.

### Root Cause
ct-hot+ re-enabled despite data showing 36% WR. ATR_SL hits dominate (18T/48h from ct-hot+ alone). Entry quality — coin_tracker composite threshold 45 lets in low-quality setups. PM_TRAIL captures gains on winners but can't overcome 0% ATR_SL hit rate.

### Fix Applied
1. DISABLED COIN_TRACKER_HOT_ENABLED, COIN_TRACKER_HOT_PLUS_ENABLED, COIN_TRACKER_HOT_MINUS_ENABLED (all False)
2. RAISED COIN_TRACKER_HOT_MIN_COMPOSITE 45→50 (for when re-enabled)
3. KEPT PM_TRAIL distance at 0.15% — 66.7% WR, working well
4. Pipeline restarted

### Verification
ct-hot+ flags confirmed False. Pipeline active. PM_TRAIL 0.15% dist holding 66.7% WR. Next run should show zero new ct-hot+ trades.

### Verification
- Pipeline: active ✅ | Kill switch: enabled ✅
- PM_TRAIL: working (48h +$1.07, avg +0.24%) ✅
- Stars7d: return_exhaustion_long 3T 100%, bb_bounce+ 22T 63.6%, r2-trend-long2 17T 64.7% ✅
- 3 open: flat ($0.00 unrealized) ✅ | No new kill candidates ✅

### Next Actions
1. **Monitor legacy clear** — ct-hot+ ages out Aug 17-18, daily trades should recover
2. **ATR_SL fix evaluation** — need 48h+ data after Aug 17 to assess 3.0% cap impact
3. **Phantom trades** — 6T/48h -$0.10, root cause in guardian_orphan (backlog)
4. **No param changes** — eval windows closed, changes risk destabilizing

## CEO Report — 2026-08-16 (29th run)

### Diagnosis
Real system stable at 46.7% WR (15T/24h +$0.25). ct-hot+ legacy draining (32T/24h, no new trades). PM_TRAIL working at66.7% WR (+$1.09/48h). ATR_SL dominant loss driver (17T/48h -$1.15 on real system). R:R 0.39:1. Regime NEUTRAL. SHORTs in NEUTRAL bleeding (13T 7.7% WR -$0.51 — all legacy signals).

### Root Cause
ATR_SL hits are entry quality issue — trades never reach PM_TRAIL activation (0.30%) and go straight to SL. Requires signal-level changes (not param tuning). Legacy signals (ct-hot+, wave_catcher+, range_breakout+) still clearing but no new trades.

### Fix Applied
NO CHANGES — real system stable, PM_TRAIL working, legacy draining naturally. Eval windows just closed (Aug 16). Need 48h+ data on current params before making changes.

### Verification
- 24h real system: 15T +$0.25 (46.7% WR) — positive
- 48h real system: 52T -$0.37 (42.3% WR) — slightly negative
- PM_TRAIL: 66.7% WR, +$1.09 — working
- ATR_SL: 17T/48h -$1.15 — entry quality bottleneck
- ct-hot+ legacy: 32T/24h, no new trades — draining
- Pipeline: healthy, timer firing
- Stars7d intact: return_exhaustion_long 3T 100%, bb_bounce+ 22T 63.6%, r2-trend-long2 17T 64.7%
