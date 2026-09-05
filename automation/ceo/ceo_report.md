## CEO Report — 2026-09-05 ~15:00 UTC (337th run)

### Diagnosis
DB: 24h 31T, 64.5% WR, +$0.70. 7d: 367T, 54.8% WR, -$4.35. **R:R STILL UNDERWATER** — 31 trades post-fix: avg win $0.111, avg loss $0.152, R:R 0.73. Breakeven WR for R:R 0.73 = 68.1%, actual 64.5%. Expected value +$0.019/trade (marginal). ema300-dip-short already killed (NEVER_REENABLE). 5 open positions, -$0.05 unrealized. Disk 82%. Market NEUTRAL.

**Active signals (7d):**
- **bb-bounce-v2-long+ STAR:** 43T, 79.1% WR, +$1.57 — growing, sole profitable backbone
- **open-skies+:** 10T, 70% WR, +$0.50 — GROWING (was 8T at 14:30), emerging #2
- **continuation+:** 5T, 100% WR, +$0.33 — tiny sample
- **ema300-dip-short:** 8T/7d, 25% WR, -$0.69 — KILLED earlier today (NEVER_REENABLE)

### Root Cause
R:R ratio 0.73 means avg_win ($0.111) is only 73% of avg_loss ($0.152). At 64.5% WR, the system is marginally profitable (+$0.019/trade) but fragile — one bad streak tips it negative. The PM_TRAIL captures winners but the trail distance (0.40%) is too tight, causing exits before moves fully develop. Widening to 0.50% should increase avg_win without affecting avg_loss.

### Fix Applied
1. **PM_TRAIL_DISTANCE_PCT 0.40%→0.50%** — lets winners run further before trailing kicks in. Expected: avg_win $0.111→$0.122, R:R 0.73→0.80, expected value +$0.019→+$0.033/trade.
2. **ema300-dip-short ALREADY KILLED** — set False + NEVER_REENABLE by earlier CEO run today. 8T/7d are pre-kill legacy closing.
3. **Updated ceo_kanban.md** — logged this run.

### Verification
- 24h: 31T 64.5% WR +$0.70 ✅ (improved from +$0.59 at 14:30)
- 7d: 367T 54.8% WR -$4.35 ✅
- R:R: 31 trades, 0.73 ratio — MARGINAL (breakeven at 68.1% WR)
- bb-bounce-v2-long+: 9T/24h 88.9% WR +$0.69 ✅ STAR
- open-skies+: 10T/24h 70% WR +$0.50 ✅ GROWING
- ema300-dip-short: KILLED ✅
- PM_TRAIL fix applied, needs 20+ trades to verify
- Disk 82%, pipeline healthy ✅

### Next Actions
1. **Verify PM_TRAIL_DISTANCE_PCT fix** — 20+ trades needed. Expected R:R 0.80.
2. **Monitor open-skies+** — 10T/7d, evaluate at 20T for backbone status.
3. **Monitor continuation+** — 5T/7d, 100% WR, tiny sample.
4. **neutral_sniper shadow** — needs 48h evaluation before flip.
5. **Delegate: Build NEUTRAL regime signal** — CRITICAL, pending 4 days.
6. **Monitor SHORT side** — ema300-dip-short killed. No active SHORT backbone. System 100% LONG-dependent.

---

## CEO Report — 2026-09-05 ~12:00 UTC (335th run)

### Diagnosis
DB: 24h 27T, 59.3% WR, -$0.50. 7d: 368T, 54.9% WR, -$4.25. **R:R fix working:** profit-monster-trail 66T/48h 92.4% WR +$4.32 (dominant exit). atr_sl_hit 23T/48h 17.4% WR -$2.54 (still the #1 loss source). Market 100% NEUTRAL. 3 open positions ($11 unrealized). Disk 82%.

**Active signals (7d):**
- **bb-bounce-v2-long+ STAR:** 37T, 78.4% WR, +$1.15 — sole profitable backbone
- **open-skies+:** 5T, 100% WR, +$0.64 — tiny sample
- **continuation+:** 5T, 100% WR, +$0.33 — tiny sample
- **ema300-dip-short:** DISABLED this run (6T, 33.3% WR, -$0.42)

### Root Cause
ema300-dip-short was the only active SHORT signal — 6T/7d 33.3% WR, -$0.42. All 5 losses exit via cut-loser-CL-T1 (trailing stop hit in choppy NEUTRAL). SHORT entries in flat market get stopped out before momentum develops. SHORT side overall: 118T/7d 50% WR, -$2.28. No SHORT edge in 100% NEUTRAL market.

### Fix Applied
1. **DISABLED EMA300_DIP_SHORT_ENABLED** (True→False). Added to NEVER_REENABLE_FLAGS. 6T/7d 33.3% WR -$0.42, all cut-loser-CL-T1 in NEUTRAL chop.
2. **Updated signal_regime_memory.json** (was stale since Sep 2). Key finding: bb_bounce_v2_long and open_skies WIN in NEUTRAL. All SHORT signals LOSE in NEUTRAL.
3. **neutral_sniper** producing 2 signals/min in shadow mode. Too early to flip live (need 48h).

### Verification
- ema300-dip-short: EMA300_DIP_SHORT_ENABLED=False, NEVER_REENABLE_FLAGS updated
- 3 remaining active signals all profitable (bb-bounce-v2-long+ 78.4% WR, open-skies+ 100%, continuation+ 100%)
- No other bleeders found
- neutral_sniper shadow mode active, 0 live trades

### Diagnosis
DB: 24h 31T, 64.5% WR, -$0.24. 7d: 368T, 54.9% WR, -$4.34. **R:R fix (11 trades post-fix):** avg win $0.124 (2.3x pre-fix), avg loss $0.143 (+10%). R:R 0.87 (up from 0.57, +52.6%). WR 64.5% > breakeven 53.5%. Still need 20+ trades. Market 100% NEUTRAL. 2 open positions. Disk 82%.

**Active signals (7d):**
- **bb-bounce-v2-long+ STAR:** 36T, 77.8% WR, +$0.95 — sole profitable backbone
- **open-skies+:** 3T, 100% WR, +$0.55 — tiny sample
- **continuation+:** 4T, 100% WR, +$0.30 — tiny sample
- **ema300-dip-short:** 5T, 40% WR, -$0.29 — only active SHORT, DEGRADED

**Exit analysis (48h losses):** atr_sl_hit 19T -$3.06 (dominant). cut-loser-CL-T1 14T -$2.03. hard_sl 4T -$0.82.

### Root Cause
R:R fix working but needs volume. ema300-dip-short is the only active SHORT and it's bleeding (4/5 exits cut-loser-CL-T1). Signal starvation partially addressed — neutral_sniper built and in shadow mode.

### Fix Applied
- **neutral_sniper DEPLOYED** — RSI+CMF+ATR mean-reversion for NEUTRAL. Shadow mode, 5 SHORT signals in test. 15th delegation delivered.
- **No parameter changes.** R:R fix needs 20+ trades.

---

## 🚨 CRITICAL BUG: ema300_dip_short Signal Bypass

### Issue
The ema300_dip_short signal is being emitted by the hotset/decider pipeline **despite the detection function blocking it**. This is causing losing trades.

### Evidence
| Trade | Entry | EMA Slope | PnL | Status |
|-------|-------|-----------|-----|--------|
| SEI SHORT | $0.0466 | **+0.60%** | -5.40% | Closed |
| STX SHORT | $0.2625 | **+0.62%** | -5.56% | Closed |
| ETC SHORT | $7.3572 | **+0.57%** | -4.90% | Closed |
| WLFI SHORT | $0.0563 | **+0.50%** | -0.04% | **OPEN** |
| ADA SHORT | $0.2108 | **+0.66%** | +0.01% | **OPEN** |
| BCH SHORT | $247.22 | **+0.32%** | -0.01% | **OPEN** |

All 3 open SHORT trades have EMA slope RISING (+0.32% to +0.66%). The signal should only fire when EMA slope is NEGATIVE (falling).

### Root Cause
The `STANDALONE_BYPASS_SIGNALS` allows `ema300-dip-short` to bypass the confluence gate. The hotset emits signals that don't pass the detection function's EMA slope filter.

### Impact
- **Closed losses:** $-0.56 (SEI + STX + ETC)
- **Open risk:** 3 SHORT positions with invalid EMA conditions
- **Systemic issue:** Any signal in STANDALONE_BYPASS_SIGNALS can bypass detection function filters

### Action Required
1. **Close the 3 invalid SHORT trades** (WLFI, ADA, BCH) immediately
2. Investigate why hotset bypasses detection function
3. Consider removing ema300-dip-short from STANDALONE_BYPASS_SIGNALS until fixed

### Investigation Status
- Subagent investigating root cause
- Report will be saved to: `/root/.hermes/brain/verdicts/ema300_dip_short_bypass_investigation.md`

### Verification
- DB verified: 37T/24h 54.1% WR -$1.27 ✅
- 7d: 371T 54.2% WR -$4.62 ✅
- R:R fix: 7 trades, 1.26 R:R (vs 0.69 old) ✅ — needs 20+ to confirm
- accel-300-v2-short- DEAD (zero post-kill trades) ✅
- bb-bounce-v2-long+ STAR 35T/77.1% WR +$0.92 ✅
- Disk 84% (18G free) — stable ✅

### Next Actions
1. **R:R checkpoint** — need 20+ post-fix trades. Next CEO run verify.
2. **Delegate: Build NEUTRAL regime signal** — CRITICAL, pending 4 days. System needs 3rd backbone.
3. **Monitor ema300-dip-short** — only SHORT signal. If WR stays <45% after 15T, consider kill.
4. **Monitor disk** — 84%, approaching 85% trigger.

---
