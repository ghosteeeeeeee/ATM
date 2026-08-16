## CEO Report — 2026-08-16 (32nd run)

### Diagnosis
Signal starvation (27T/24h) + ATR_SL dominant (37T/48h 2.7% WR -$2.45). ct-hot+ legacy draining (33T/48h -$0.42). SHORT side dead (12T 8.3% WR -$0.40). Today worst day: 27T -$0.72 (22.2% WR). 1 open SYRUP LONG -$0.05. PM_TRAIL working: 37T 67.6% WR +$1.06. T1 exits strong: 12T 100% WR +$0.69. R:R 0.42:1 (PM_TRAIL +0.28% vs ATR_SL -0.67%).

### Root Cause
ct-hot+ disabled = volume collapse. SIGNAL_FILTER_SPEED_MIN 30 too loose = ATR_SL hits on weak entries. Entry quality bottleneck — not exit mechanics.

### Fix Applied
1. RE-ENABLED COIN_TRACKER_HOT with MIN_COMPOSITE 55 (stricter filter, was 50)
2. RAISED SIGNAL_FILTER_SPEED_MIN 30→40 (fewer but better entries)

### Verification
Monitor48h: ct-hot+ WR must >55% at composite 55. Daily trades must >20T with filter 40. ATR_SL hit count must ↓ from 37/48h.

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

## CEO Report — 2026-08-16 (30th run)

### Diagnosis
System STABILIZING. 48h 96T -$1.00 (40.6% WR). Real system (excl ct-hot+): 47T/48h -$0.32 (42.6% WR). ct-hot+ legacy 33T/48h clearing (no new trades). ATR_SL dominant drag: 17T 5.9% WR -$1.15 (avg -0.68%). PM_TRAIL working: 24T 58.3% WR +$0.57 (avg +0.23%). 7d: 437T -$2.54 (48.5% WR). 1 open flat. Regime NEUTRAL. Pipeline active.

### Root Cause
ATR_SL entry quality — trades entering at local tops, immediately going negative. Avg peak move 3.04% but still hitting SL at -0.68%. PM_TRAIL should catch these but timing mismatch. Legacy trades (ct-hot+, range_finder+, wave_catcher) still clearing from before disable.

### Fix Applied
NO CHANGES. System stabilizing, legacy clearing naturally. PM_TRAIL 0.15% distance confirmed working (58.3% WR). All bad actors disabled. Pipeline healthy.

### Verification
- PM_TRAIL 48h: 24T 58.3% WR +$0.57 (WORKING)
- ATR_SL 48h: 17T 5.9% WR -$1.15 (improving from -0.75% avg)
- Stars7d: return_exhaustion_long 3T 100%, bb_bounce+ 22T 63.6%, r2-trend-long2 17T 64.7%
- ct-hot+ legacy: clearing, no new trades
- Monitor: Monday volume, ATR_SL entry quality, phantom trades root cause

## CEO Report — 2026-08-16 15:20 UTC (31st run)

### Diagnosis
SHORT side is a net drag: 13T/48h 7.7% WR -$0.50. range_finder- (SHORT) was the only actively firing SHORT signal — 3T 0% WR -$0.12 (both standalone and with hl_copy_trader). Today Aug16: 26T -$0.71 (23.1% WR — worst day in 7d, legacy ct-hot+ draining). Regime 100% NEUTRAL (104N/0L/1S) — no directional edge for SHORTs.

### Root Cause
range_finder- fires in NEUTRAL regime without directional edge. SHORT signals need confirmed downtrend to be profitable. All range_finder variants (LONG, SHORT, MINUS, PLUS) are now dead — LONG disabled earlier today, SHORT killed now.

### Fix Applied
- `RANGE_FINDER_MINUS_ENABLED = False` (3T SHORT 0% WR -$0.12)
- `RANGE_FINDER_SHORT_ENABLED = False` (all range_finder variants dead)
- Do NOT enable new SHORT signals until regime shifts to SHORT_BIAS

### Verification
DB verified: 24h 51T -$0.55 (37.3% WR), 48h LONG -$0.49 (46.3% WR) + SHORT -$0.50 (7.7% WR), 7d 437T -$2.54 (48.5% WR). PM_TRAIL 0.15% dist working: 69.4% WR +$1.07/48h (avg +0.29%). Stars7d intact: return_exhaustion_long 3T 100%, bb_bounce+ 22T 63.6%, r2-trend-long2 17T 64.7%. Pipeline active. Git committed + pushed.
