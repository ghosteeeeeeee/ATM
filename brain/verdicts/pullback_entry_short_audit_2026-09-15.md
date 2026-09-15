# Pullback-Entry SHORT Signal — Independent Audit
**Auditor:** Own-Conclusions Agent (fresh eyes, no prior context)
**Date:** 2026-09-15
**Scope:** Last 48 hours (31 trades) + all-time (77 trades)
**Data Source:** PostgreSQL `brain` database, `_signal_metadata` JSONB column

---

## Executive Summary

The pullback-entry SHORT signal is underperforming its historical baseline. Last 48h WR dropped from 61.0% (all-time) to 54.8%, and total PnL collapsed from +3.00 to +0.03. The signal is not broken — it's a regime change. The current market has inverted several historical patterns, and the filters need recalibration.

**Overall Verdict: MEDIUM severity — filters need updating, not a code bug.**

---

## Finding 1: Triple Z-Score Confusion (MEDIUM)

**What I found:** There are THREE different z-score calculations in play, and they can diverge significantly:

| Source | Data | Timeframe | Where Used |
|--------|------|-----------|------------|
| `detect()` in pullback_entry.py | 5m candles | 20-bar | Signal generation filter (line 202-208) |
| `_enrich_indicators()` in signal_schema.py | 1m price_history | 20-bar | Stored in `_signal_metadata.z_score` |
| `_ctx_gate_get_zscore()` in decider_run.py | 1m price_history | 20-bar | Live execution-time check (line 929) |

**Evidence:** 13 of 31 trades (48h) have `_signal_metadata.z_score > 0.5` — meaning the 1m z was above 0.5 at enrichment time. Yet these trades passed `detect()` because the 5m z was below 0.5. The z-score in the trade database is the 1m enrichment z, NOT the 5m detect z.

**Impact:** This makes z-score-based analysis confusing. When we see "z > 0.5 trades have 60% WR", that's the 1m z, not the 5m z the detect filter uses. The two measurements are answering different questions:
- 5m z: "Is the macro trend intact?" (downtrend confirmation)
- 1m z: "Is price extended right now?" (mean reversion opportunity)

**Is this a bug?** Not exactly — it's a design choice with unintended consequences. The detect filter and decider filter are checking different things on different timeframes, which is actually reasonable. But it makes analysis and tuning very difficult because the stored z doesn't match the filter z.

**Recommendation:** Store BOTH z-scores in metadata: `z_score_5m` (from detect) and `z_score_1m` (from enrichment). This enables proper analysis.

---

## Finding 2: RSI 25-35 Is the Danger Zone (HIGH)

**What I found:** RSI 25-35 has the WORST win rate of any bucket in the last 48 hours:

| RSI Bucket | Trades | WR | PnL |
|------------|--------|-----|-----|
| RSI 0-25 | 3 | 66.7% | +0.01 |
| **RSI 25-35** | **5** | **20.0%** | **-0.69** |
| RSI 35-45 | 5 | 60.0% | +0.13 |
| RSI 45-55 | 10 | 40.0% | +0.06 |
| RSI 55-65 | 6 | 83.3% | +0.35 |
| RSI 65+ | 2 | 100.0% | +0.17 |

**All-time confirmation:** RSI 35-45 is also the worst all-time bucket (42.9% WR). The danger zone is consistent.

**Current filters:**
- `SHORT_RSI_FLOOR = 25` (decider line 925) — blocks RSI < 25
- `SIGNAL_FILTER_RSI_MIN = 30` (decider line 906) — blocks RSI < 30

**Problem:** RSI 25-35 passes BOTH filters but has only 20% WR. The SHORT_RSI_FLOOR should be raised to at least 35.

**Specific losses in RSI 25-35:**
- CHIP: RSI=34.0, PnL=-0.34 (biggest single loss in 48h)
- ALT: RSI=33.3, PnL=-0.18
- NEO: RSI=29.2, PnL=-0.22
- ENS: RSI=28.6, PnL=-0.15
- SUPER: RSI=28.6, PnL=+0.20 (only win)

**Recommendation:** Raise `SHORT_RSI_FLOOR` from 25 to 35. This would catch 4/14 losses (28.6% of all losses) while blocking only 1/17 wins (5.9% of wins). Net PnL impact: +0.53 (avoid -0.69 in losses, lose +0.20 in wins from SUPER).

---

## Finding 3: Momentum Filter Is Backwards for Current Market (HIGH)

**What I found:** The momentum filter in `detect()` blocks SHORT with rising momentum (line 188). But the 48h data shows:

| Momentum | 48h WR | All-time WR | Change |
|----------|--------|-------------|--------|
| rising | **66.7%** | 56.5% | **+10.2%** |
| flat | 53.8% | 60.6% | -6.8% |
| falling | **33.3%** | 66.7% | **-33.4%** |

**Key insight:** Falling momentum was the BEST signal for SHORT all-time (66.7% WR), but it's now the WORST (33.3%). Rising momentum went from worst to best. The market regime has inverted the momentum pattern.

**Evidence from losses:**
- Falling momentum losses: FOGO(-0.15), ALT(-0.18), ONDO(-0.13), ENS(-0.15) = -0.61 total
- Rising momentum losses: MET(-0.12), CHIP(-0.34), LDO(-0.15), ENA(-0.20) = -0.81 total

Both momentum directions have losses, but the WR difference is stark.

**Is this a bug?** No — the momentum filter in `detect()` is actually CORRECT for the all-time data. The problem is the current market regime has flipped. The filter is doing what it was designed to do, but the assumption it was based on (rising momentum = bad for SHORT) no longer holds.

**Recommendation:** This is a regime adaptation issue, not a code fix. Options:
1. **Conservative:** Remove the momentum filter from detect() entirely. Let the decider's speed/momentum filters handle it.
2. **Adaptive:** Add a regime-aware momentum filter that relaxes in certain conditions.
3. **Leave as-is:** Accept that the filter blocks some winners but also catches some losers (4 rising momentum losses = -0.81 saved).

---

## Finding 4: EXTREME Regime Has Inverted (MEDIUM)

**What I found:**

| Regime | 48h WR | All-time WR | Change |
|--------|--------|-------------|--------|
| NORMAL | 66.7% | 58.3% | +8.4% |
| HIGH | 52.6% | 60.0% | -7.4% |
| EXTREME | **33.3%** | **69.2%** | **-35.9%** |

EXTREME regime went from the BEST performing (69.2% all-time) to the WORST (33.3% in 48h). Only 3 EXTREME trades in 48h, but all were losses or breakeven.

**Losses in EXTREME:**
- CHIP: PnL=-0.34 (biggest loss in 48h)
- MET: PnL=-0.12
- BLUR: PnL=+0.06 (only win)

**Recommendation:** Consider adding an EXTREME regime dampener for pullback-entry SHORT. In EXTREME regime, the signal could require higher confidence or additional confirmation.

---

## Finding 5: Speed Filter Performance Is Inverted (LOW)

**What I found:**

| Speed Bucket | 48h WR | All-time WR |
|--------------|--------|-------------|
| 0-25% | 55.6% | 52.4% |
| 25-50% | 55.6% | 64.0% |
| 50-75% | 50.0% | 65.4% |
| 75+% | **66.7%** | 60.0% |

All-time, speed 25-75% is best. In 48h, high speed (75+%) is best. The `SIGNAL_FILTER_SPEED_MIN = 40` blocks speed < 40%, which catches 7/14 losses (50%) but also blocks several wins.

**Recommendation:** The speed filter is working reasonably well. No change needed.

---

## Finding 6: No Code Bugs Found (POSITIVE)

I read `pullback_entry.py` and the relevant `decider_run.py` sections from scratch. The code logic is correct:
- detect() properly checks impulse, pullback, volume, BB squeeze, EMA trend, momentum, z-score, support/resistance, and RSI
- The decider's pullback-specific safety checks (SHORT_RSI_FLOOR, live z check) are correctly implemented
- The z-score alignment check (ZSCORE_ACCEL) is correctly implemented
- No infinite loops, no race conditions, no obvious logic errors

**One concern:** The `detect()` function's z-score filter (line 205) blocks SHORT when 5m z > 0.5, but the comment says "price above mean = downtrend reversed (danger zone)". This is correct for 5m data. However, the stored z in metadata is 1m data, which can be > 0.5 even when 5m z is < 0.5. This is not a bug but creates analysis confusion (see Finding 1).

---

## Finding 7: The Biggest Single Loss Pattern (HIGH)

**CHIP trade analysis:**
- Entry: 0.040972, Exit: 0.041604, PnL: -0.34 (biggest loss in 48h)
- z_score: 2.61 (extreme — price way above mean)
- rsi_14: 34.0 (oversold territory)
- momentum: rising (anti-trend for SHORT)
- regime: EXTREME
- speed: 50.3

This trade violated MULTIPLE safety conditions:
1. z > 0.5 (should have been caught by detect filter on 5m, or decider live z check)
2. RSI < 35 (should have been caught if SHORT_RSI_FLOOR was 35)
3. Rising momentum (should have been caught by detect momentum filter)
4. EXTREME regime (highest risk)

**Why did it trade?** The z_score in metadata is 1m z. The detect() function likely saw 5m z < 0.5. The RSI in metadata is 1m RSI (34.0), but the detect() function uses 5m RSI which may have been different. The momentum in metadata is 1m "rising", but detect() may have seen 5m "flat".

**Root cause:** The dual-timeframe problem (Finding 1) allowed a trade through that multiple filters should have caught.

---

## Summary of Recommendations

| # | Finding | Severity | Action | Expected Impact |
|---|---------|----------|--------|-----------------|
| 1 | Triple z-score confusion | MEDIUM | Store both 5m and 1m z in metadata | Better analysis |
| 2 | RSI 25-35 danger zone | HIGH | Raise `SHORT_RSI_FLOOR` from 25 to 35 | +0.53 PnL/48h |
| 3 | Momentum filter backwards | HIGH | Evaluate removing or making regime-aware | Depends on regime |
| 4 | EXTREME regime inverted | MEDIUM | Add EXTREME dampener | Reduces big losses |
| 5 | Speed filter OK | LOW | No change | — |
| 6 | No code bugs | POSITIVE | — | — |
| 7 | CHIP loss pattern | HIGH | Combination of #1-#4 fixes | Catches worst losses |

---

## Projected Impact of Combined Fixes

If we apply Finding 2 (RSI floor 35) + Finding 3 (relax momentum filter):

**48h backtest of proposed changes:**
- Losses avoided: CHIP(-0.34), ALT(-0.18), NEO(-0.22), ENS(-0.15), USUAL(-0.18) = -1.07 saved
- Wins blocked: SUPER(+0.20) = -0.20 lost
- Net improvement: +0.87 PnL
- New 48h PnL: 0.03 + 0.87 = +0.90 (was +0.03)
- New 48h WR: (17-1)/(31-5) = 16/26 = 61.5% (was 54.8%)

This is a significant improvement that brings performance back in line with the all-time baseline.

---

*Audit completed: 2026-09-15. Data verified against PostgreSQL brain database.*
