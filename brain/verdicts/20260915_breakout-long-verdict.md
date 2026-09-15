# Independent Verdict: Breakout-Long+ Loser Analysis

**Auditor:** Independent (fresh-eyes, no priming)
**Date:** 2026-09-15
**Source files reviewed:**
- `/root/.hermes/brain/analysis/breakout-long-losers-analysis.md`
- `/root/.hermes/scripts/signals/breakout_long.py`
- `/root/.hermes/scripts/hermes_constants.py` (lines 2081-2094)
- PostgreSQL `trades` table — 13 breakout-long+ trades queried directly

---

## Claim 1: "XPL winner had RSI 46.6, BB 0.97, wave accelerating"

**Verdict: AGREE**
**Confidence: HIGH**

| Field | Claimed | Actual (DB) | Match? |
|-------|---------|-------------|--------|
| RSI | 46.6 | 46.6 | ✅ Exact |
| BB position | 0.97 | 0.9665 | ✅ Rounded correctly |
| Wave phase | accelerating | accelerating | ✅ Exact |
| BTC regime | TRANSITIONING→BULL | TRANSITIONING (btc_score=91.3) | ⚠️ Partial — DB shows only "TRANSITIONING", the "→BULL" is editorial interpretation of the high btc_score |

**Evidence:** Trade ID 15369, PnL +11.27%, entry 0.0803, exit 0.0821. Signal metadata confirms all values.

---

## Claim 2: "IMX loser had RSI 71.4, BB 0.77, wave falling"

**Verdict: AGREE**
**Confidence: HIGH**

| Field | Claimed | Actual (DB) | Match? |
|-------|---------|-------------|--------|
| RSI | 71.4 | 71.43 | ✅ Rounded correctly |
| BB position | 0.77 | 0.7676 | ✅ Rounded correctly |
| Wave phase | falling | falling | ✅ Exact |
| BTC regime | RANGING | RANGING (btc_score=19.4) | ✅ Exact |

**Evidence:** Trade ID 15416, PnL -11.07%, entry 0.1238, exit 0.1210. Signal metadata confirms all values.

---

## Claim 3: "ZEN loser had RSI 49.4, BB 0.77, wave falling"

**Verdict: AGREE**
**Confidence: HIGH**

| Field | Claimed | Actual (DB) | Match? |
|-------|---------|-------------|--------|
| RSI | 49.4 | 49.4 | ✅ Exact |
| BB position | 0.77 | 0.7725 | ✅ Rounded correctly |
| Wave phase | falling | falling | ✅ Exact |
| BTC regime | BULL_TREND | BULL_TREND (btc_score=98.6) | ✅ Exact |

**Evidence:** Trade ID 15419, PnL -8.84%, entry 6.3791, exit 6.2663. Signal metadata confirms all values.

---

## Claim 4: "ACE loser had RSI 73.3, BB 0.28, wave accelerating"

**Verdict: AGREE**
**Confidence: HIGH**

| Field | Claimed | Actual (DB) | Match? |
|-------|---------|-------------|--------|
| RSI | 73.3 | 73.33 | ✅ Rounded correctly |
| BB position | 0.28 | 0.2762 | ✅ Rounded correctly |
| Wave phase | accelerating | accelerating | ✅ Exact |
| BTC regime | TRANSITIONING | TRANSITIONING (btc_score=47.5) | ✅ Exact |

**Evidence:** Trade ID 15384, PnL -3.94%, entry 0.1522, exit 0.1502. Signal metadata confirms all values.

**Additional note:** ACE has z_score = -0.8953 (negative) while going LONG. Price was BELOW its mean — this is an unusual entry for a breakout long and suggests the signal fired at a poor price level.

---

## Claim 5: "RSI_MAX=70 would block IMX and ACE"

**Verdict: AGREE**
**Confidence: HIGH**

**Evidence:**
- IMX: RSI 71.43 > 70 → BLOCKED ✅
- ACE: RSI 73.33 > 70 → BLOCKED ✅
- XPL: RSI 46.6 < 70 → PASSES ✅
- ZEN: RSI 49.4 < 70 → PASSES ✅

**Impact on all 13 breakout-long+ trades:**
- BANANA (WIN, RSI 84.76) → Would also be blocked ⚠️
- CRV (WIN, RSI 87.72) → Would also be blocked ⚠️

Note: BANANA and CRV are combo trades (accel_300_v2_long + volume_breakout_long+). The RSI filter would prevent the breakout_long component from firing, but the accel_300_v2_long signal might still execute independently. Whether the combo still triggers depends on minimum signal count requirements.

---

## Claim 6: "BB_POSITION_MIN=0.85 would block IMX, ZEN, ACE"

**Verdict: AGREE**
**Confidence: HIGH**

**Evidence:**
- IMX: BB 0.7676 < 0.85 → BLOCKED ✅
- ZEN: BB 0.7725 < 0.85 → BLOCKED ✅
- ACE: BB 0.2762 < 0.85 → BLOCKED ✅
- XPL: BB 0.9665 > 0.85 → PASSES ✅

**Impact on all 13 breakout-long+ trades:**
- 11 of 13 trades would be blocked by this filter alone. Only XPL (0.9665) and SUSHI-2nd (0.9869) have BB > 0.85.
- Winners that would be blocked: BANANA (0.8321), CRV (0.8278), MET (0.5513), BIGTIME (0.729), SUSHI-2nd (0.9869 is fine, but wave=falling blocks it)

---

## Claim 7: "WAVE_PHASE_BLOCK='falling' would block IMX and ZEN"

**Verdict: AGREE**
**Confidence: HIGH**

**Evidence:**
- IMX: wave=falling → BLOCKED ✅
- ZEN: wave=falling → BLOCKED ✅
- XPL: wave=accelerating → PASSES ✅
- ACE: wave=accelerating → PASSES (but blocked by RSI and BB filters)

**Impact on all 13 breakout-long+ trades:**
- 7 trades have wave=falling: BANANA, ONDO, MET, SUSHI-2nd, SOL, IMX, ZEN
- Would block 2 additional winners: BANANA (+0.84%), SUSHI-2nd (+0.75%), MET (+0.63%)
- Note: SUSHI-2nd passes RSI and BB filters but is blocked by wave=falling

---

## Claim 8: "XPL would still pass all filters"

**Verdict: AGREE**
**Confidence: HIGH**

**Evidence (all three core filters):**
- RSI 46.6 < 70 → ✅ PASS
- BB 0.9665 > 0.85 → ✅ PASS
- Wave accelerating ≠ falling → ✅ PASS

XPL passes all three recommended filters. No issue here.

---

## Claim 9: "The signal code doesn't check RSI, BB position, or wave phase"

**Verdict: AGREE**
**Confidence: HIGH**

**Evidence from `breakout_long.py`:**
The `detect_breakout_long()` function checks:
1. ATR(14) compression (ATR < 0.5% of price)
2. Price breakout above range high (by 0.3%)
3. Volume spike (2x average for Path A, 3x for Path B)
4. Candle strength (close > high * 0.997)
5. EMA300 confirmation (Path B only)

It does **NOT** compute or check:
- RSI
- Bollinger Band position
- Wave phase
- BTC regime
- Momentum state

The RSI, BB position, wave phase, and BTC regime values in `_signal_metadata` are populated by a separate enrichment step (likely `signal_compactor.py`), not by `breakout_long.py`. The detection code is purely volume/ATR/price-structure based.

---

## CRITICAL FINDING: Analysis Summary Table Has Errors

The analysis document's "Expected Impact" table contains **three errors**:

### Error 1: "Trades Blocked: 0 → 2 (IMX, ZEN)"

**Actual: 3 trades blocked (IMX, ZEN, ACE)**

ACE (RSI=73.33 > 70) would be blocked by RSI_MAX=70. The analysis correctly notes this in the RSI filter section ("Would have blocked IMX and ACE"), but the summary table omits ACE from the blocked count.

### Error 2: "Win Rate: 33.3% → ~66.7% (2W/1L)"

**Actual: 100% (1W/0L) for pure breakout-long+ trades**

After applying all three core filters, only XPL passes. IMX, ZEN, and ACE are all blocked. There is no remaining "1L" trade — ACE is blocked by both RSI_MAX and BB_POSITION_MIN. The projected win rate is 100%, not 66.7%.

### Error 3: "Worst Trade: -11.07% → -3.94% (ACE only)"

**Actual: ACE would be blocked — no remaining losing trades**

Since ACE is blocked by RSI_MAX=70 (73.33 > 70) AND BB_POSITION_MIN=0.85 (0.2762 < 0.85), it would not trade. The only remaining trade is XPL (+11.27%). The "worst trade" of -3.94% is incorrect — that trade would not occur.

### Root cause of errors

The analysis appears to have evaluated each filter **independently** in the individual sections (which is correct), but then compiled the summary as if only the WAVE_PHASE filter was applied (blocking IMX and ZEN) while ignoring that RSI_MAX and BB_POSITION_MIN also block ACE.

---

## ADDITIONAL FINDING: Impact on Combo Trades Not Addressed

The analysis only considers 4 "pure" breakout-long+ trades. However, 9 other trades use `volume_breakout_long` or `volume-breakout-long+` as a **secondary signal in a combo**. The filters in `breakout_long.py` would prevent the breakout_long component from firing for ALL 13 trades, not just the 4 pure ones.

**Winners that would be affected by combo disruption:**

| Token | PnL | Strategy | Blocked by | Would combo still fire? |
|-------|-----|----------|------------|------------------------|
| BANANA | +0.84% | accel_300_v2_long + volume-breakout-long+ | RSI + BB + wave | Unknown — depends on min signal count |
| CRV | +15.61% | accel_300_v2_long + volume-breakout-long+ | RSI + BB | Unknown — depends on min signal count |
| MET | +0.63% | rs_s + volume-breakout-long+ | BB + wave | Unknown — depends on min signal count |
| SUSHI-2nd | +0.75% | rs_s + volume-breakout-long+ | wave | Unknown — depends on min signal count |
| BIGTIME | +3.95% | trend_purity+ + volume-breakout-long+ | BB | Unknown — depends on min signal count |

If the pipeline requires 2+ signals to execute a trade, suppressing the breakout_long component would prevent these combos from firing, losing **+21.78%** in potential gains from 5 winning trades.

**This risk is completely unaddressed in the analysis.**

---

## ADDITIONAL FINDING: Patterns the Analysis Missed

### 1. Negative z_score on ACE (LONG trade)
ACE had z_score = -0.8953 while entering a LONG position. This means price was below its statistical mean — a poor location for a breakout long entry. A z_score filter (e.g., require z_score > 0 for LONG) could be an additional quality filter.

### 2. `is_stale` field
Three trades had is_stale=true: SUSHI-1st (LOSS), BANANA (WIN), SOL (LOSS). Staleness doesn't cleanly predict outcome, but it's worth noting that the pipeline executed stale signals.

### 3. BTC regime is not a reliable filter
- BULL_TREND: BIGTIME (WIN), ZEN (LOSS) — mixed
- TRANSITIONING: XPL (WIN), ACE (LOSS) — mixed
- RANGING: IMX (LOSS) — only one data point

### 4. momentum_state vs wave_phase divergence
Several trades have conflicting momentum_state and wave_phase values:
- IMX: momentum_state=rising but wave_phase=falling
- SUSHI-2nd: momentum_state=rising but wave_phase=falling
- ZEN: momentum_state=rising but wave_phase=falling

This suggests these metrics measure different things and should not be used interchangeably.

### 5. SUGGESTED ADDITIONAL FILTER: momentum_score
Losers tend to have lower momentum_scores:
- XPL (WIN): 37.1
- IMX (LOSS): 29.0
- ZEN (LOSS): 33.9
- ACE (LOSS): 27.6

A MOMENTUM_SCORE_MIN=30 filter could provide additional protection, though the sample size is small.

---

## OVERALL VERDICT

| Aspect | Assessment |
|--------|------------|
| Trade-level data accuracy | ✅ ALL 9 specific claims verified correct |
| Filter logic correctness | ✅ Filters would block the 3 pure losers |
| XPL survival | ✅ XPL passes all filters |
| Code gap identification | ✅ Correctly identified missing RSI/BB/wave checks |
| Summary table accuracy | ❌ THREE errors (wrong block count, wrong win rate, wrong worst trade) |
| Combo trade impact | ❌ NOT ADDRESSED — could lose 5 winning trades |
| Additional patterns | ⚠️ Missed z_score, is_stale, momentum divergence patterns |

**Bottom line:** The individual trade analysis and filter recommendations are sound. The proposed RSI_MAX=70, BB_POSITION_MIN=0.85, and WAVE_PHASE_BLOCK='falling' filters would correctly block all 3 pure breakout-long+ losers without affecting the winner (XPL). However, the summary projections are wrong (ACE would also be blocked), and the analysis completely ignores the impact on combo trades where breakout_long is a secondary signal. Before implementing these filters, the team should verify whether combo trades would still execute without the breakout_long component.
