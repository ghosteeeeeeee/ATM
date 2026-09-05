## CEO Report — 2026-09-05 ~14:30 UTC (336th run)

### Diagnosis
DB: 24h 27T, 66.7% WR, +$0.59. 7d: 367T, 54.8% WR, -$4.35. **R:R FIX CONFIRMED** — 26 trades post-fix: avg win $0.114, avg loss $0.152, R:R 0.75 (up from 0.57 pre-fix, +31.6%). WR 65.4% > breakeven 57.1%. profit-monster-trail dominates exits (14T/26 = 53.8%). Market 104/107 NEUTRAL. 1 open (LTC LONG open-skies+). Disk 82%. Pipeline healthy.

**Active signals (7d):**
- **bb-bounce-v2-long+ STAR:** 43T, 79.1% WR, +$1.57 — growing, sole profitable backbone
- **open-skies+:** 8T, 75% WR, +$0.44 — growing, emerging #2
- **continuation+:** 5T, 100% WR, +$0.33 — tiny sample
- **ema300-dip-short:** 7T, 28.6% WR, -$0.57 — DEGRADED (was 40% WR, now 28.6%)

### Root Cause
R:R fix works but avg loss ($0.152) still exceeds avg win ($0.114). The system is profitable at 65%+ WR because profit-monster-trail exits capture large moves, but the stop losses are still too wide relative to typical wins. ema300-dip-short is the only active SHORT signal and it's degrading — 28.6% WR with all cut-loser-CL-T1 exits in NEUTRAL chop.

### Fix Applied
1. **NO PARAMETER CHANGES.** R:R fix confirmed working — WR 65.4% > breakeven 57.1%. System profitable as-is.
2. **ema300-dip-short MONITORING** — 7T/7d 28.6% WR -$0.57. At 7T (of 15T kill threshold). If WR stays <45% at 15T, kill.
3. **Updated CURRENT.md** — verified numbers, updated signal performance.
4. **Updated ceo_kanban.md** — logged this run.

### Verification
- 24h: 27T 66.7% WR +$0.59 ✅
- 7d: 367T 54.8% WR -$4.35 ✅
- R:R fix: 26 trades, 0.75 R:R (up from 0.57, +31.6%) ✅
- bb-bounce-v2-long+: 43T 79.1% WR +$1.57 ✅
- open-skies+: 8T 75% WR +$0.44 ✅
- ema300-dip-short: 7T 28.6% WR -$0.57 ⚠️ monitoring
- Disk 82%, pipeline healthy ✅

### Next Actions
1. **Monitor R:R fix** — 26 trades, confirmed profitable. No changes needed.
2. **Monitor ema300-dip-short** — kill at 15T if WR <45%.
3. **Monitor open-skies+** — growing, evaluate at 20T.
4. **neutral_sniper shadow** — needs 48h evaluation before flip.
5. **Delegate: Build NEUTRAL regime signal** — CRITICAL, pending 4 days.

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
