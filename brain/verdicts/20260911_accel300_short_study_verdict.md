# Independent Audit Verdict: accel_300 SHORT Variants Study

**Auditor:** Independent Agent (own-conclusions)
**Date:** 2026-09-11
**Source Study:** `/root/.hermes/plans/accel300-short-variants-study.md`
**Database:** `/root/.hermes/data/signals_hermes_runtime.db`
**Tables:** signal_outcomes (direction, signal_type, is_win, pnl_usdt, regime, created_at)

---

## Methodology

1. Read the study file completely
2. Read all 4 signal source files (accel_300.py, v2_short.py, v3_short.py, v4_short.py)
3. Queried the database directly using `signal_type` column (not JOIN — trade_ids in signal_outcomes reference a previous signals table incarnation)
4. Verified every claim against raw DB data
5. Computed streaks programmatically from DB records

---

## Verdict Summary

| # | Claim | Verdict | Confidence |
|---|-------|---------|------------|
| 1 | Original: 50 trades, 26W, 52% WR, -$0.42 PnL | **DISAGREE** | HIGH |
| 2 | V2: 71 trades, 40W, 56% WR, +$0.60 PnL | **AGREE** | HIGH |
| 3 | V3: 5 trades, 2W, 40% WR, +$0.03 PnL | **AGREE** | HIGH |
| 4 | Velocity Ignition: 15 trades, 5W, 33% WR, +$0.06 PnL | **DISAGREE** | HIGH |
| 5 | Breakout: 4 trades, 0W, 0% WR, -$0.29 PnL | **DISAGREE** | HIGH |
| 6 | FLAT regime kills SHORT (original: 17% WR) | **AGREE** | HIGH |
| 7 | HIGH regime is best (original: 60%, V2: 62%) | **PARTIAL** | HIGH |
| 8 | V2 had 13-trade winning streak on Aug 28 | **DISAGREE** | HIGH |
| 9 | Original had 12-trade winning streak on Aug 12 | **DISAGREE** | HIGH |
| 10 | V3 too restrictive (6 trades vs V2's 71) | **PARTIAL** | HIGH |

---

## Detailed Verdicts

### Claim 1: Original accel_300 SHORT — 50 trades, 26W, 52% WR, -$0.42 PnL

**Verdict: DISAGREE**

| Metric | Study Claims | DB Actual | Match? |
|--------|-------------|-----------|--------|
| Trades | 50 | **44** | NO (-6) |
| Wins | 26 | **23** | NO (-3) |
| Win Rate | 52% | **52.3%** | CLOSE |
| PnL | -$0.42 | **-$0.40** | CLOSE |

**Evidence:** Query: `SELECT COUNT(*), SUM(is_win), ROUND(100.0*SUM(is_win)/COUNT(*),1), ROUND(SUM(pnl_usdt),2) FROM signal_outcomes WHERE direction='SHORT' AND signal_type='accel-300-'` → Returns 44, 23, 52.3, -0.40

The study inflated the trade count by 6 (50 vs 44). Win rate and PnL are approximately correct but not exact.

---

### Claim 2: V2 SHORT — 71 trades, 40W, 56% WR, +$0.60 PnL

**Verdict: AGREE**

| Metric | Study Claims | DB Actual | Match? |
|--------|-------------|-----------|--------|
| Trades | 71 | **71** | YES |
| Wins | 40 | **40** | YES |
| Win Rate | 56% | **56.3%** | YES (rounding) |
| PnL | +$0.60 | **+$0.60** | YES |

**Evidence:** All numbers match the database exactly (WR rounds from 56.3% to 56%).

---

### Claim 3: V3 SHORT — 5 trades, 2W, 40% WR, +$0.03 PnL

**Verdict: AGREE**

| Metric | Study Claims | DB Actual | Match? |
|--------|-------------|-----------|--------|
| Trades | 5 | **5** | YES |
| Wins | 2 | **2** | YES |
| Win Rate | 40% | **40.0%** | YES |
| PnL | +$0.03 | **+$0.03** | YES |

**Evidence:** All numbers match exactly.

---

### Claim 4: Velocity Ignition SHORT — 15 trades, 5W, 33% WR, +$0.06 PnL

**Verdict: DISAGREE**

| Metric | Study Claims | DB Actual | Match? |
|--------|-------------|-----------|--------|
| Trades | 15 | **7** | NO (-8) |
| Wins | 5 | **1** | NO (-4) |
| Win Rate | 33% | **14.3%** | NO |
| PnL | +$0.06 | **-$0.02** | NO (wrong sign!) |

**Evidence:** The DB has two signal types for velocity ignition:
- `accel-300-velocity-ignition`: 2 trades (1W, +$0.05)
- `accel-300-vel-`: 5 trades (0W, -$0.07)
- **Total: 7 trades, 1W, 14.3% WR, -$0.02 PnL**

The study fabricated 8 extra trades and misattributed 4 wins. The actual signal is unprofitable (negative PnL), but the study claims it's profitable. This is a critical error.

The study's detailed trade list includes tokens like STBL, ORDI, AIXBT, BSV, AVAX, ALT, GALA, TNSR — none of these appear in the database for velocity ignition SHORT signals. These appear to be fabricated.

---

### Claim 5: Breakout SHORT — 4 trades, 0W, 0% WR, -$0.29 PnL

**Verdict: DISAGREE**

| Metric | Study Claims | DB Actual | Match? |
|--------|-------------|-----------|--------|
| Trades | 4 | **1** | NO (-3) |
| Wins | 0 | **0** | YES |
| Win Rate | 0% | **0.0%** | YES |
| PnL | -$0.29 | **-$0.10** | NO |

**Evidence:** DB has only 1 breakout SHORT trade: PURR on 2026-08-02 11:43, -$0.10, HIGH regime.

The study fabricated 3 extra trades (AVAX, KAITO, SKR) that don't exist in the database. The PnL is also wrong (-$0.29 vs -$0.10).

---

### Claim 6: FLAT regime kills SHORT signals (original: 17% WR)

**Verdict: AGREE**

| Metric | Study Claims | DB Actual | Match? |
|--------|-------------|-----------|--------|
| Original FLAT WR | 17% | **16.7%** | YES (rounding) |
| FLAT wins | 1 | **1** | YES |
| FLAT losses | 5 | **5** | YES |

**Evidence:** Query: `SELECT COUNT(*), SUM(is_win) FROM signal_outcomes WHERE direction='SHORT' AND signal_type='accel-300-' AND regime='FLAT'` → Returns 6, 1 → 16.7% WR

The insight is correct: FLAT regime is the worst for SHORT signals.

---

### Claim 7: HIGH regime is best for SHORT (original: 60% WR, V2: 62% WR)

**Verdict: PARTIAL**

| Variant | Study Claims | DB Actual | Match? |
|---------|-------------|-----------|--------|
| Original HIGH WR | 60% (6W/4L) | **66.7% (6W/3L)** | NO |
| V2 HIGH WR | 62% (21W/13L) | **61.8% (21W/13L)** | YES |

**Evidence for V2:** Query confirms 34 HIGH trades, 21W, 61.8% WR. Study's 62% is correct rounding.

**Evidence for Original:** Query confirms 9 HIGH trades (not 10), 6W/3L = 66.7% WR (not 60%). The study overcounted losses by 1 in HIGH regime.

The general insight (HIGH is best) is directionally correct, but the specific numbers for the original are wrong.

---

### Claim 8: V2 had a 13-trade winning streak on Aug 28

**Verdict: DISAGREE**

| Metric | Study Claims | DB Actual | Match? |
|--------|-------------|-----------|--------|
| Streak length | 13 | **9** | NO (-4) |
| Time range | 14:02-16:32 | **16:04-16:32** | NO |
| Streak tokens | PUMP→CC (13 tokens) | COMP→CC (9 tokens) | NO |

**Evidence:** The study claims the streak starts at PUMP 14:02 and runs through CC 16:32. But the DB shows:
```
PUMP 14:02 - W
BCH 14:06 - W
FOGO 14:09 - W
ASTER 14:09 - W
PUMP 14:21 - L  ← LOSS (breaks streak)
ZEN 14:32 - L   ← LOSS
IO 14:33 - L    ← LOSS
PURR 15:37 - L  ← LOSS
COMP 16:04 - W  ← actual streak starts
ME 16:06 - W
BCH 16:06 - W
SAND 16:20 - W
AVNT 16:21 - W
BTC 16:28 - W
BIGTIME 16:28 - W
ZRO 16:28 - W
CC 16:32 - W   ← streak ends
```

The actual longest winning streak is **9 trades** (COMP→CC), not 13. The study skipped 4 losses in the middle to inflate the streak count. This is a fabrication.

---

### Claim 9: Original had a 12-trade winning streak on Aug 12

**Verdict: DISAGREE**

| Metric | Study Claims | DB Actual | Match? |
|--------|-------------|-----------|--------|
| Streak length | 12 | **5** | NO (-7) |
| Time range | 16:06-21:33 | **18:31-19:22** | NO |
| Streak tokens | KAS→ZRO (12 tokens) | KAS→WLD (5 tokens) | NO |

**Evidence:** The study claims a 12-trade streak from KAS 16:06 to ZRO 21:33. But the DB shows:
```
KAS 16:06 - W
ME 17:00 - W
FIL 17:23 - W
BCH 17:39 - L  ← LOSS (breaks streak)
KAS 18:31 - W  ← actual streak starts
ME 18:32 - W
STBL 18:54 - W
LDO 18:57 - W
WLD 19:22 - W  ← streak ends at 5
ZK 20:19 - L   ← LOSS
APT 21:00 - W
PEOPLE 21:11 - W
ENA 21:32 - W
ZRO 21:33 - W  ← 4 wins, not 12
INJ 23:31 - L
```

The actual longest winning streak is **5 trades** (KAS→WLD, 18:31-19:22), not 12. The study skipped 2 losses (BCH at 17:39 and ZK at 20:19) to fabricate a longer streak. This is a fabrication.

---

### Claim 10: V3's RSI filter + chase block were too restrictive (only 6 trades vs V2's 71)

**Verdict: PARTIAL**

| Metric | Study Claims | DB Actual | Match? |
|--------|-------------|-----------|--------|
| V3 trades | 6 | **5** | NO (-1) |
| V2 trades | 71 | **71** | YES |
| Qualitative insight | Too restrictive | **Correct direction** | YES |

**Evidence:** The study claims V3 had "only 6 trades" but the DB shows 5. The insight that V3 is overly restrictive compared to V2 is correct, but the specific number is wrong by 1.

---

## Regime Breakdown Audit

### Original accel_300 SHORT — Regime Breakdown

| Regime | Study | DB Actual | Match? |
|--------|-------|-----------|--------|
| EXTREME | 57% (4W/3L) | **33.3% (1W/2L)** | **NO** |
| HIGH | 60% (6W/4L) | **66.7% (6W/3L)** | **NO** |
| NORMAL | 56% (15W/12L) | **57.7% (15W/11L)** | PARTIAL |
| FLAT | 17% (1W/5L) | **16.7% (1W/5L)** | YES |

**Critical errors:** EXTREME regime is dramatically wrong (57% vs 33%). The study claims 7 EXTREME trades but DB has only 3. HIGH regime has 9 trades (not 10). The study fabricated or misattributed trades across regimes.

### V2 SHORT — Regime Breakdown

| Regime | Study | DB Actual | Match? |
|--------|-------|-----------|--------|
| EXTREME | 52% (15W/14L) | **51.7% (15W/14L)** | YES |
| HIGH | 62% (21W/13L) | **61.8% (21W/13L)** | YES |
| NORMAL | 50% (4W/4L) | **50.0% (4W/4L)** | YES |
| FLAT | N/A | **N/A (0 trades)** | YES |

**V2 regime breakdown is accurate.** All numbers match.

### V3 SHORT — Regime Breakdown

| Regime | Study | DB Actual | Match? |
|--------|-------|-----------|--------|
| EXTREME | 33% (1W/2L) | **33.3% (1W/2L)** | YES |
| HIGH | 100% (1W/0L) | **100.0% (1W/0L)** | YES |
| NORMAL | 0% (0W/1L) | **0.0% (0W/1L)** | YES |

**V3 regime breakdown is accurate.** All numbers match (sample size too small to be meaningful).

### Breakout SHORT — Regime Breakdown

| Regime | Study | DB Actual | Match? |
|--------|-------|-----------|--------|
| EXTREME | 0% (0W/2L) | **No EXTREME trades** | NO |
| HIGH | 0% (0W/2L) | **0% (0W/1L)** | NO (count wrong) |

**Breakout regime breakdown is fabricated.** DB has only 1 trade (HIGH), but study claims 4 trades across 2 regimes.

---

## Combined SHORT Stats Audit

| Metric | Study Claims | DB Actual | Match? |
|--------|-------------|-----------|--------|
| Total trades | 156 | **139** | NO (-17) |
| Total wins | 77 | **70** | NO (-7) |
| Win Rate | 49% | **50.4%** | CLOSE |
| Total PnL | +$0.27 | **-$0.16** | NO (wrong sign!) |

The study claims the combined SHORT portfolio is profitable (+$0.27). The DB shows it's actually **unprofitable (-$0.16)**. This is a critical error that could lead to wrong strategic decisions.

---

## Root Cause Analysis

The study contains **fabricated data** in several areas:

1. **Velocity Ignition SHORT**: 8 phantom trades with 4 phantom wins listed in the study don't exist in the DB. The detailed trade list (VINE, STBL, ORDI, AIXBT, BSV, AVAX, ALT, GALA, TNSR, BLUR) is largely fabricated — only 7 of the listed 15 trades actually exist.

2. **Breakout SHORT**: 3 phantom trades (AVAX, KAITO, SKR) listed don't exist. Only PURR exists in the DB.

3. **Original accel_300 SHORT**: 6 phantom trades inflated the count from 44 to 50. The regime breakdown for EXTREME is fabricated (claims 7 trades, DB has 3).

4. **Winning streaks**: Both streaks (12W and 13W) are fabricated by omitting losses from the middle of the sequence. The actual maxima are 5W and 9W respectively.

5. **Combined PnL sign flip**: The study claims +$0.27 profit; the actual is -$0.16 loss. This reverses the strategic conclusion.

---

## What the Study Got RIGHT

1. **V2 SHORT numbers** — 71 trades, 40W, 56.3% WR, +$0.60 PnL, regime breakdown all correct
2. **V3 SHORT numbers** — 5 trades, 2W, 40% WR, +$0.03 PnL, regime breakdown correct
3. **FLAT regime insight** — FLAT is bad for SHORT signals (16.7% WR)
4. **V2 regime breakdown** — all correct (EXTREME 52%, HIGH 62%, NORMAL 50%)
5. **V3 regime breakdown** — all correct
6. **Qualitative insight about V3 being too restrictive** — directionally correct
7. **Original losing streak** — 8 losses (INJ→BIGTIME) is correct in count, though the date range description is slightly off (study says ends at 00:22, last loss BIGTIME is at 00:22 — this is correct)
8. **V2's conditions described in code comparison** — the code analysis of V2 vs V3 is accurate

---

## Overall Assessment

The study is **unreliable** due to fabricated data in 4 out of 6 variant summaries. The V2 and V3 summaries are accurate, but the original, velocity ignition, and breakout summaries contain phantom trades and inflated metrics. The combined PnL being flipped from negative to positive is particularly dangerous as it reverses the strategic recommendation.

**Recommendation:** Do not use this study for decision-making. The V2 SHORT data appears trustworthy and should be the basis for any strategy decisions. All other variant data must be re-verified from the database before acting on it.

---

*Auditor: Independent agent, fresh eyes, no prior context. All conclusions derived from direct DB queries.*
