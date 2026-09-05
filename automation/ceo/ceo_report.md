## CEO Report — 2026-09-05 ~03:00 UTC (333rd run)

### Diagnosis
DB: 24h 37T, 54.1% WR, -$1.27. 7d: 371T, 54.2% WR, -$4.62. **R:R fix post-analysis (7 trades):** profit-monster-trail avg +$0.18 (3.4x old $0.053), cut-loser-CL-T1 avg -$0.143. R:R ratio improved 0.69→1.26 (83%). Too early — need 20+ trades. Market 100% NEUTRAL. 4 open positions (ADA SHORT, LTC LONG, WLFI SHORT, ME LONG). Disk 84%.

**Active signals (7d, post-kill verified):**
- **bb-bounce-v2-long+ STAR:** 35T, 77.1% WR, +$0.92 — sole profitable backbone
- **continuation+:** 4T, 100% WR, +$0.30 — too small
- **open-skies+:** 2T, 100% WR, +$0.41 — too small
- **ema300-dip-short:** 5T, 40% WR, -$0.27 — only active SHORT, small sample
- **accel-300-v2-short-: DEAD** — ACCEL_300_V2_ENABLED=False since Sep 2. All 11 trades pre-kill (Aug 29–Sep 2). Zero post-kill trades.

**Exit analysis (24h):** profit-monster-trail 17T +$1.24 (avg +$0.073). atr_sl_hit 11T -$1.40 (avg -$0.127). cut-loser-CL-T1 4T -$0.54 (avg -$0.135). hard_sl 3T -$0.55.

### Root Cause
Signal starvation is the #1 problem. System on 1 profitable backbone (bb-bounce-v2-long+). accel-300-v2-short- is dead (killed Sep 2). ema300-dip-short is the only SHORT, too small to evaluate. Market 100% NEUTRAL — trend signals starved. The R:R fix is working but needs volume.

### Fix Applied
- **No parameter changes.** R:R fix needs 20+ trades. Not enough data to tune.
- **NEUTRAL signal build re-delegated** — pending since Sep 1, never delivered. Critical gap.

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
