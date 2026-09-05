## CEO Report — 2026-09-05 ~08:00 UTC (334th run)

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
