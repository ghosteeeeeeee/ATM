## CEO Report — 2026-08-11 18:50 UTC

### Diagnosis
System signal-starved. Pipeline generatesbb_bounce+ signals butsignal_analyst blocks ALL (MIN_SCORE=60, bb_bounce+ scores 50 in NEUTRAL regime). 24h: 26T -$0.50 (38.5% WR — RED). 7d: 372T +$0.26 (51.9% WR — barely positive, declining from +$0.62 peak Aug9). System idle 45min+. 3 open (2 hzscore+ LONG, 1 ht_sig4 paper). Daily trend: Aug9 +$0.62 → Aug10 -$0.10 → Aug11 -$0.46 (declining).

### Root Cause
Quality gate too aggressive for NEUTRAL regime. MIN_SCORE=60 blocks allbb_bounce+ signals (score50: trend=0 rsi=0 wr=25 time=10 blacklist=15). REDUCE mode adds 50% sizing penalty. Double filter = zero signal flow.

### Fix Applied
Lowered MIN_SCORE from60 to55 in signal_analyst.py. Lets partial-trend-alignment signals through (trend=15 needed). Still filters garbage (score <55 blocked). Minimal, reversible.

### Verification
Monitor 24h: if signal flow resumes AND WR >=45% → fix working. If WR <40% → revert MIN_SCORE to60. Stars7d intact: bb_bounce+,range_finder+ LONG 53T +$0.71 58.5%, bb-bounce-short,hzscore- SHORT 17T +$0.12 58.8%, hzscore+,mover+ LONG 5T +$0.17 80%. SL at1.0% correct. Disk81%. Pipeline healthy.

---

## CEO Report — 2026-08-12 Autopilot Improvements Review

### Overall Assessment
**PHASE 1: YES (with adjustments). PHASE 2-5: MODIFY. PHASE 6: DEFER.** The plan is solid control theory mapped to trading, but the system is currently idle (signal starvation) — adding more filters before fixing signal flow is counterproductive. Prioritize safety limits and signal starvation fix first.

### Verified Numbers (DB)
- **24h**: 28T, -$0.63, 32.1% WR (RED)
- **7d**: 371T, +$0.24, 51.8% WR (barely positive, declining)
- **SHORT 7d**: 129T, -$1.00, 49.6% WR (bleeding)
- **LONG 7d**: 242T, +$1.24, 52.9% WR (profitable)
- **Open**: 4 trades
- **Pipeline**: IDLE (0 signals in compaction, 24h+ no trades)
- **Cost driver**: atr_sl_hit 37T, -$1.73 (48h dominant)

---

### Per-Phase Verdicts

#### Phase 1: Safety Limits — **YES (with calibration)**
**Reasoning:** The system already has partial safety (MAX_OPEN_POSITIONS=6, LOSS_COOLDOWN, DRAWDOWN tiers). But missing hard daily trade cap and circuit breaker. Current state: 28T/24h, 49.6% SHORT WR bleeding.

| Sub-Phase | Verdict | Notes |
|-----------|---------|-------|
| 1.1 Position limit 5 | YES | Current is 6 — reduce by 1, trivial |
| 1.2 Daily trade cap 8 | MODIFY → 12 | 8 is too tight for current volume (28T/24h). Set 12 as initial, tune down |
| 1.3 Max loss 2%/trade | YES | Matches CUT_LOSER_MAX_PCT=-3.0 and ATR_SL_MAX=2.5%. Tighten CUT_LOSER to -2.0% |
| 1.4 Daily drawdown 5% | YES | Already have DRAWDOWN_TIER_1=5% at 0.5x. Add hard circuit breaker (stop all) at 5% |
| 1.5 Post-loss cooldown 2h | MODIFY | Existing LOSS_COOLDOWN_BASE=20min with exponential is sufficient. 2h flat is too aggressive — keep existing system |

**Action:** Add `max_daily_trades=12` and `daily_drawdown_circuit_breaker=0.05` to hermes_constants.py. Tighten CUT_LOSER_MAX_PCT from -3.0 to -2.0.

#### Phase 2: Dead Zone — **MODIFY (deploy after signal starvation fixed)**
**Reasoning:** System is currently generating 0 signals. Adding more filters will make starvation worse. Deploy AFTER signal flow is restored.

| Sub-Phase | Verdict | Notes |
|-----------|---------|-------|
| 2.1 Price dead zone 1.5% | YES | Good noise filter, but 1.5% may be too wide for low-vol tokens. Start at 1.0% |
| 2.2 RSI 35-65 filter | MODIFY → 40-60 | 35-65 blocks too many valid signals. Narrow to 40-60 (stricter neutral zone) |
| 2.3 Volume 1.3x | YES | Volume confirmation is standard, 1.3x is reasonable |

**Action:** DEFER until signal starvation is fixed. Then deploy with 1.0% price dead zone, RSI 40-60, volume 1.3x.

#### Phase 3: Adaptive Thresholds — **YES**
**Reasoning:** REGIME_ENABLED=True already exists. Regime detection runs. But thresholds are fixed (CONFIDENCE_THRESHOLD=0.75 implied). Mapping regime to threshold/size/stop is the natural next step.

| Sub-Phase | Verdict | Notes |
|-----------|---------|-------|
| 3.1 Regime→threshold | YES | BULL=0.70, SIDEWAYS=0.80, BEAR=0.85, VOLATILE=0.90 — reasonable |
| 3.2 Regime→position size | YES | BULL=1.0, SIDEWAYS=0.75, BEAR=0.50, VOLATILE=0.25 — aligns with existing DRAWDOWN tiers |
| 3.3 Regime→stop distance | MODIFY | Existing ATR-based stops already adapt to volatility. Adding regime layer is redundant — use ATR system instead |
| 3.4 Regime wiring | YES | market_regime.json already exists, executor already reads it |

**Action:** Implement 3.1 and 3.2. Skip 3.3 (ATR already handles this). Wire into signal-executor.py.

#### Phase 4: Dampening — **MODIFY**
**Reasoning:** Re-entry after exit is a real problem (bb_bounce+,hzscore+ daily declining from 80% to 25% WR). But 4h cooldown is arbitrary.

| Sub-Phase | Verdict | Notes |
|-----------|---------|-------|
| 4.1 Post-exit dampening 4h | MODIFY → 2h | 4h is too long in fast market. 2h matches existing cooldown philosophy. 50% confidence reduction on re-entry is good |
| 4.2 Consecutive loss dampening (3) | YES | 3 consecutive losses doubling threshold is sound. Reset after 24h is reasonable |
| 4.3 Signal count anti-boost | YES | Repeated signals adding confidence is backwards. Cap at +5% max is correct fix |

**Action:** Implement 4.2 and 4.3 immediately (they fix existing bugs). Defer 4.1 to Phase 2 deployment.

#### Phase 5: Watchdog — **YES (highest priority after safety)**
**Reasoning:** Pipeline is currently IDLE with no operational visibility. A watchdog would have caught this 24h ago.

| Sub-Phase | Verdict | Notes |
|-----------|---------|-------|
| 5.1 Stale signal alert (30min) | YES — CRITICAL | System idle 24h+ with no alert. This is the highest-value change |
| 5.2 Execution failure watchdog | YES | Freqtrade API unreachable detection is basic ops hygiene |
| 5.3 Stale signal rejection (5 bars) | YES | Prevents acting on old signals. accel_300 already has stale checks but other signals don't |

**Action:** Implement 5.1 immediately. 5.2 and 5.3 can follow in Phase 2.

#### Phase 6: Wiring — **DEFER**
**Reasoning:** Integration is the final step after phases 1-5 are individually tested. Don't wire until components work.

**Action:** Defer until phases 1-5 are deployed and verified.

---

### Priority Reorder

| Priority | Phase | Why |
|----------|-------|-----|
| **1** | Phase 5.1 (Watchdog) | System idle 24h with no alert — highest operational risk |
| **2** | Phase 1 (Safety Limits) | Hard limits prevent blowup, quick to implement |
| **3** | Phase 4.2-4.3 (Dampening bugs) | Fixes existing anti-boost bug and consecutive loss handling |
| **4** | Phase 3.1-3.2 (Adaptive thresholds) | Regime-aware sizing, natural extension of existing REGIME_ENABLED |
| **5** | Phase 2 (Dead Zones) | Deploy AFTER signal starvation is fixed |
| **6** | Phase 6 (Wiring) | Last, after components tested |

### Additional Recommendations

1. **Fix signal starvation first.** The compactor producing 0 signals is the #1 problem. Adding filters (Phase 2) before fixing flow is wrong. The standalone bypass fix (Aug 12 14:30) should restore flow — verify.

2. **SHORT regime filter.** SHORT 7d -$1.00 on 129T. In NEUTRAL regime, SHORT should be blocked or heavily reduced. This is more impactful than dead zones.

3. **atr_sl_hit is the dominant cost driver** (37T, -$1.73/48h). The autopilot plan doesn't address SL width — but the existing ATR system already handles this. The issue is entry quality, not SL width.

4. **bb_bounce+,hzscore+ LONG daily declining** (Aug 9 80% → Aug 11 25%). Phase 4.2 (consecutive loss dampening) would help here. 7d still 48.5% WR — not dead, but cooling.

### Risk Warnings

- **Over-filtering risk:** Adding dead zones + adaptive thresholds + dampening simultaneously could starve the system further. Deploy incrementally with 24h evaluation windows.
- **Regime detection quality:** brain.py INSERT missing regime column on ALL 370 trades. Regime-adaptive features need clean regime data to work. Fix data quality first.
- **SHORT bleeding:** -$1.00/7d on SHORT. Phase 3 regime mapping helps, but the real fix is disabling SHORT in NEUTRAL/BEAR or adding regime gate to SHORT signals specifically.
- **Pipeline is inactive:** systemctl shows hermes-pipeline inactive. This is the most urgent issue — nothing else matters if the pipeline isn't running.

### Verification
- DB queried directly via psql — numbers match kanban
- Pipeline health: INACTIVE (systemctl)
- Constants file reviewed: 1408 lines, all safety params confirmed
- Signal logic review: accel_300 SHORT sign-inverted bug confirmed (not currently firing — disabled)
- Open trades: 4 (3 hzscore+ LONG, 1 ht_sig4 paper)
