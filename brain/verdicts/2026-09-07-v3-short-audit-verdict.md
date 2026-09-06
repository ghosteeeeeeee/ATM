# Independent Audit Verdict: accel_300_v3_short Filters
**Date:** 2026-09-07  
**Auditor:** Independent verification agent  
**Files read:** accel_300_v3_short.py, accel_300_v2_short.py, hermes_constants.py (lines 1680-1707), decider_run.py (lines 3130-3284)  
**Data source:** signals_hermes_runtime.db (signal_outcomes, signals, token_speeds)

---

## Raw Data: v3_short Trade Outcomes

| Token | Win/Loss | PnL% | RSI | z_tier | z_score | Signal→Exec Gap | Confidence |
|-------|----------|------|-----|--------|---------|-----------------|------------|
| MET | WIN | +0.304% | 47.94 | neutral | +0.2784 | 477 min (7.95h) | 77.6% |
| INJ | WIN | +1.1027% | 32.35 | extreme_low | -2.5987 | 283 min (4.72h) | 80.0% |
| ENA | LOSS | -0.5463% | 21.2 | low | -1.4607 | 65.7 min | 78.0% |
| ZORA | LOSS | -1.6133% | 30.52 | neutral | -0.9145 | 117.1 min | 86.0% |
| CRV | LOSS | -0.8958% | 35.21 | neutral | -0.8753 | 9.0 min | 84.0% |
| W | LOSS | -1.6009% | 16.67 | extreme_low | -2.0473 | 41.2 min | 77.0% |

**Summary:** 2W/4L = 33% WR, total PnL = -3.24%

## Raw Data: v2_short Trade Outcomes

| Token | Win/Loss | PnL% | Confidence |
|-------|----------|------|------------|
| PUMP | WIN | +1.5614% | 88.0% |
| STX | WIN | +0.004% | 87.0% |
| XPL | WIN | +1.1346% | 88.0% |
| STX(2) | WIN | +1.2656% | 84.0% |
| NEAR | LOSS | -1.0105% | 84.0% |
| ENS | LOSS | -0.8251% | 69.0% |
| PURR | LOSS | -0.0357% | 84.0% |
| JUP | LOSS | -1.4123% | 69.0% |
| AVNT | LOSS | -0.8429% | 73.0% |
| MET | LOSS | -0.8448% | 84.0% |
| ZRO | LOSS | -0.8443% | 82.0% |

**Summary:** 4W/7L = 36% WR, total PnL = -2.05%

---

## Claim-by-Claim Verdict

### Claim 1: "All 4 v3_short losers were stale entries (price moved 0.4-1.2% against us)"
**Verdict: DISAGREE**  
**Evidence:**
- **ENA**: Signal rsi=21.2 at 03:30, executed at 04:36 (65.7 min gap). The issue was RSI oversold, NOT price move. The constants comment says ENA moved +0.4%, but +0.4% < 0.5% threshold, so the price_move filter would NOT have caught ENA. ENA was caught by RSI_MIN=25 (21.2 < 25).
- **ZORA**: Signal at 01:48, executed at 03:45 (117 min gap). This IS a stale entry (2 hours old). Would be caught by staleness filter (117 > 10 min).
- **CRV**: Signal at 00:27, executed at 00:36 (9 min gap). Only 9 minutes — within the 10-min staleness window! NOT caught by staleness. Claim says price_move +0.76% catches it, but I cannot independently verify the price_move percentage without historical price data at execution time.
- **W**: Signal rsi=16.67 at 15:02, executed at 15:43 (41 min gap). The primary issue was RSI oversold (16.67 < 25), NOT staleness. W was also stale (41 min), but RSI is the cleaner explanation.

**Confidence: HIGH** — Only ZORA was clearly stale. ENA and W were RSI-caught, not staleness-caught. CRV's staleness is debatable (9 min gap, within 10-min window).

---

### Claim 2: "V2's #1 success predictor is SPEED (winners avg 71.7%, losers avg 53.2%)"
**Verdict: DISAGREE**  
**Evidence:**
The current `token_speeds` table shows (note: this is current data, NOT historical at trade time):

**V2 Winners (current speed):**
- PUMP: 82.1%, STX: 41.3%, XPL: 11.4%, STX(2): 41.3%
- Average: 44.0%

**V2 Losers (current speed):**
- NEAR: 86.4%, ENS: 54.9%, PURR: 97.3%, JUP: 98.9%, AVNT: 48.4%, MET: 98.4%, ZRO: 84.2%
- Average: 81.2%

With current data, it's the **OPPOSITE** of the claim: losers have HIGHER speed (81.2%) vs winners (44.0%). The claim states winners avg 71.7% and losers avg 53.2%, which contradicts the data.

**CRITICAL CAVEAT:** The `token_speeds` table is a current snapshot, not historical. Speed values at trade time may have been different. However, the claim cannot be verified with available data, and the current data actively contradicts it. No historical speed data exists in the database.

**Confidence: MEDIUM** — Data contradicts the claim, but historical speed data is unavailable.

---

### Claim 3: "The z_tier filter (z >= -1.0) was removed because it blocked MET (a winner with z=+0.28)"
**Verdict: DISAGREE (partially)**  
**Evidence:**
1. **The constant exists but is DEAD CODE.** `ACCEL_300_V3_SHORT_Z_TIER_MIN = 'low'` is defined in hermes_constants.py line 1705, but is **never imported or used** anywhere in the codebase (verified by grep across all /root/.hermes/scripts/).

2. **The claim mischaracterizes the filter.** The constant is about `z_score_tier` (a categorical tier: extreme_low/low/neutral/high), NOT a z_score threshold of -1.0. The constant value is `'low'`, not `-1.0`.

3. **MET's actual data:** z_score=+0.2784, z_tier='neutral'. If the filter enforced `z_tier >= 'low'`, it would reject 'neutral' (since 'neutral' > 'low' in typical tier ordering). But this is speculation since the filter was never implemented.

4. **The claim says "z >= -1.0 blocked MET"** — This is wrong. MET's z_score was +0.28, which would PASS a z >= -1.0 filter. The claim confuses z_score (continuous) with z_tier (categorical).

**Confidence: HIGH** — The z_tier filter is dead code. The claim mischaracterizes both what the filter was and why it would block MET.

---

### Claim 4: "RSI_MIN=25 catches W (rsi=16.7) and ENA (rsi=21.2)"
**Verdict: AGREE**  
**Evidence:**
- W's signal rsi_14 = 16.67. The detector at line 367: `if rsi < V3_SHORT_RSI_MIN: return None` where RSI_MIN=25. 16.67 < 25 → BLOCKED ✓
- ENA's signal rsi_14 = 21.2. 21.2 < 25 → BLOCKED ✓
- Both values are from the signals table at the time closest to execution.

**Confidence: HIGH** — Mathematically certain.

---

### Claim 5: "Price move > 0.5% catches ZORA (+1.2%), CRV (+0.76%), W (+0.64%)"
**Verdict: PARTIAL**  
**Evidence:**
- The `ACCEL_300_V3_SHORT_MAX_ENTRY_MOVE = 0.5` filter IS implemented in decider_run.py lines 3242-3256. It compares signal price to current price at execution time.
- **ZORA**: 117 min gap. Price move claim of +1.2% is plausible but I cannot independently verify without historical price data. Would also be caught by staleness (117 > 10 min).
- **CRV**: 9 min gap. Price move claim of +0.76% is plausible. This is the ONLY filter that would catch CRV (9 min < 10 min staleness window, rsi=35.21 > 25).
- **W**: Price move claim of +0.64%. Would ALSO be caught by RSI_MIN=25 (rsi=16.67 < 25), so price_move is redundant for W.
- **Constants comment error**: Line 1706 says "catches ENA +0.4%" but +0.4% < 0.5% threshold. ENA would NOT be caught by price_move filter.

**Confidence: MEDIUM** — Cannot independently verify the price_move percentages without historical price snapshots at execution time.

---

### Claim 6: "If filters had been in place: 2W/0L = 100% WR for v3"
**Verdict: DISAGREE**  
**Evidence:**
This claim is **mathematically wrong** because the staleness filter would also block the winning trades:

| Token | Outcome | Blocked by RSI? | Blocked by price_move? | Blocked by staleness? |
|-------|---------|-----------------|----------------------|---------------------|
| MET | WIN | No (rsi=47.9) | Unknown | **YES (477 min >> 10 min)** |
| INJ | WIN | No (rsi=32.4) | Unknown | **YES (283 min >> 10 min)** |
| ENA | LOSS | YES (rsi=21.2) | No (+0.4% < 0.5%) | Yes (65.7 min) |
| ZORA | LOSS | No (rsi=30.5) | Unknown (+1.2%) | YES (117 min) |
| CRV | LOSS | No (rsi=35.2) | Unknown (+0.76%) | No (9 min < 10 min) |
| W | LOSS | YES (rsi=16.7) | Unknown (+0.64%) | Yes (41.2 min) |

If ALL 3 filters had been in place:
- **MET** (WIN) → BLOCKED by staleness (477 min)
- **INJ** (WIN) → BLOCKED by staleness (283 min)
- **ENA** (LOSS) → BLOCKED by RSI
- **ZORA** (LOSS) → BLOCKED by staleness
- **CRV** (LOSS) → BLOCKED by price_move (if +0.76% claim is true)
- **W** (LOSS) → BLOCKED by RSI

**Result: 0 trades executed, not 2W/0L.** The claim cherry-picks which filters apply to which trades.

**CAVEAT:** The staleness filter uses `entry_origin_ts` first, which might differ from `created_at`. If MET and INJ had recent `entry_origin_ts` values (e.g., from re-validation), the staleness check might have passed. But I have no data to confirm this — the signal_outcomes table doesn't store `entry_origin_ts`.

**Confidence: HIGH** — The 10-min staleness gap is 477 min for MET and 283 min for INJ. These would be blocked unless `entry_origin_ts` overrides are in play.

---

### Claim 7: "V3 is re-enabled with these filters and should perform better than v2"
**Verdict: PARTIAL**  
**Evidence:**
- **Re-enabled:** Confirmed. `ACCEL_300_V3_SHORT_ENABLED = True` at line 1682.
- **Filters in place:** RSI_MIN=25 (in signal detector), staleness 10-min (in decider_run.py), price_move 0.5% (in decider_run.py). All three are active code.
- **"Should perform better than v2":** This is a prediction, not a verifiable fact. V2 has 36% WR on 11 trades. V3 with filters would have had 0 trades on the historical data (see Claim 6). On 6 trades, even 100% WR is statistically insignificant (small sample size).
- **The filters are real and functional**, but the analysis supporting them is flawed (Claim 6 is wrong).

**Confidence: MEDIUM** — The infrastructure is correct, but the performance prediction is unsupported.

---

## Additional Findings

### BUG: `ACCEL_300_V3_SHORT_Z_TIER_MIN` is dead code
The constant `ACCEL_300_V3_SHORT_Z_TIER_MIN = 'low'` (line 1705) is defined but never imported or used anywhere. It should either be implemented or removed to avoid confusion.

### BUG: Constants comment error on ENA
Line 1706 says the price_move filter "catches ENA +0.4%" but +0.4% < 0.5% threshold. ENA would NOT be caught by this filter. ENA is caught by RSI_MIN=25 instead.

### OBSERVATION: MET's extreme staleness
MET's signal-to-execution gap is 477 minutes (nearly 8 hours). This is extreme and suggests the signal was sitting in a queue for a very long time before execution. This warrants investigation into the compactor/execution pipeline.

### OBSERVATION: CRV's z_tier='neutral' is borderline
CRV's last signal before execution had z_tier='neutral'. If the dead z_tier filter were implemented, it might have caught CRV differently. But the current filters (price_move + staleness) should handle it.

### BUG: Silent failure in price_move filter
The price_move check in decider_run.py (lines 3257-3258) catches exceptions and logs a warning but does NOT block the trade:
```python
except Exception as e:
    log(f'  [WARN] price move check failed: {e}', 'WARN')
```
If the price_move calculation fails, the trade proceeds anyway. This should be fail-closed (block on error), not fail-open.

---

## Summary Table

| Claim | Verdict | Key Issue |
|-------|---------|-----------|
| 1. All 4 losers were stale | DISAGREE | Only ZORA was clearly stale. ENA/W were RSI-caused, CRV borderline. |
| 2. SPEED predicts v2 success | DISAGREE | Current data shows OPPOSITE (losers avg 81.2% vs winners 44.0%). No historical data to verify. |
| 3. z_tier filter removed for MET | DISAGREE | z_tier filter is dead code. Claim mischaracterizes the filter type. |
| 4. RSI_MIN=25 catches W and ENA | AGREE | Mathematically certain: 16.67 < 25 and 21.2 < 25. |
| 5. price_move > 0.5% catches ZORA/CRV/W | PARTIAL | Cannot verify price_move percentages. Constants comment has ENA error. |
| 6. Filters → 2W/0L = 100% WR | DISAGREE | Staleness would also block MET (477 min) and INJ (283 min). Result would be 0 trades. |
| 7. V3 re-enabled, should beat v2 | PARTIAL | Re-enabled confirmed. Performance prediction unsupported by flawed analysis. |
