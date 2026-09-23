# Independent Verdict: Pump-Chain SHORT Signal Filter Performance
**Audit Date:** 2026-09-23
**Auditor:** Independent agent (fresh read, no prior analysis)
**Data Source:** PostgreSQL brain DB, query `signal LIKE 'pump-chain-%' AND direction = 'SHORT'`

---

## Raw Data Summary

| Metric | Value |
|--------|-------|
| Total SHORT trades | 63 |
| Breakeven (PnL=$0) | 3 (CC, JUP, APT) |
| Active trades | 60 |
| Wins | 36 |
| Losses | 24 |
| Baseline WR | 60.0% |
| Baseline PnL | $+0.25 |

**Metadata distribution:**
- wave_phase: accelerating(24), bottoming(7), decelerating(6), falling(25), neutral(1)
- momentum_state: falling(40), flat(18), rising(5)
- bb_position range: -0.255 to 0.622
- speed_percentile range: 1.2 to 99.4

---

## Claim-by-Claim Verification

### Claim 1: "Filter: accel+rising OR falling+BB>0.4 catches 4/26 losses with 0/35 wins killed, improving WR from 57.4% to 61.4%"

**Verdict: DISAGREE**

**Evidence:**
- My baseline: 36 wins, 24 losses (60.0% WR), total 60 active trades
- Claim baseline: 35 wins, 26 losses (57.4% WR) — **this doesn't match current DB state**
- Filter catches: 4 losses ✅ (BCH -$0.12, INJ -$0.27, ARB -$0.13, ENA -$0.16) ✅
- Filter kills: **1 win** ❌ (ALGO +$0.19, phase=falling/mom=rising/bb=0.622)
  - ALGO matches `falling+BB>0.4` (phase=falling, bb=0.622 > 0.4) ✅
  - **Claim of "0 wins killed" is FALSE**
- Remaining PnL: $+0.74 (not $+0.24 as claimed)
- Remaining WR: 35/55 = 63.6%

**Why ALGO gets caught:** ALGO has phase=falling, momentum=rising, BB=0.622. The `falling+BB>0.4` condition matches because 0.622 > 0.4, regardless of momentum_state.

**Confidence: HIGH** — Direct DB query, exact filter logic applied.

---

### Claim 2: "The 4 caught losses are: BCH -$0.12 (falling/flat/BB=0.401), INJ -$0.27 (accelerating/rising/BB=0.453), ARB -$0.13 (accelerating/rising/BB=0.353), ENA -$0.16 (falling/flat/BB=0.419)"

**Verdict: AGREE**

**Evidence:**
- BCH: phase=falling, mom=flat, bb=0.4008, pnl=$-0.12 ✅ (rounds to 0.401)
- INJ: phase=accelerating, mom=rising, bb=0.453, pnl=$-0.27 ✅
- ARB: phase=accelerating, mom=rising, bb=0.3526, pnl=$-0.13 ✅ (rounds to 0.353)
- ENA: phase=falling, mom=flat, bb=0.4192, pnl=$-0.16 ✅ (rounds to 0.419)

**Confidence: HIGH** — All 4 trades verified with exact DB values.

---

### Claim 3: "Remaining PnL stays at +$0.24 (same as baseline)"

**Verdict: DISAGREE**

**Evidence:**
- Baseline PnL (all 60 active): $+0.25
- Remaining PnL after filter (55 trades): $+0.74
- The difference ($+0.49) = the PnL of caught losses ($-0.68) + killed wins ($+0.19) = -$0.49 net removed
- $+0.25 - (-$0.68 + $+0.19) = $+0.25 + $0.49 = $+0.74

**The claimed "$+0.24 same as baseline" is mathematically impossible** — if you remove 4 losses worth $-0.68, remaining PnL MUST increase by $0.68 (minus any killed wins).

**Confidence: HIGH** — Mathematical verification.

---

### Claim 4: "accel+flat catches 4 losses but kills 2 wins (APT +$0.11, ENA +$0.13)"

**Verdict: DISAGREE (partially)**

**Evidence:**
- accel+flat catches: **3 losses** (not 4): APT -$0.11, HYPER -$0.14, GOAT -$0.30
- accel+flat kills: **2 wins** ✅: APT +$0.11, ENA +$0.13
- The claimed 4th caught loss doesn't exist in current DB

**Confidence: HIGH** — Direct filter application.

---

### Claim 5: "Adding speed>80 kills 6 wins including $+0.50 BLUR — not worth it"

**Verdict: DISAGREE (partially)**

**Evidence:**
- speed>80 kills: **5 wins** (not 6): BLUR +$0.50, APT +$0.11, GRASS +$0.06, GMT +$0.22, ACE +$0.01, ACE +$0.22
- Wait — that's 6. Let me recount: BLUR, APT, GRASS, GMT, ACE, ACE = **6 wins killed** ✅
- Actually correct: 6 wins killed ($+1.12 total)
- But it also catches 10 losses ($-1.51) — net benefit is negative (-$0.39)
- BLUR +$0.50 is indeed the biggest single kill

**Verdict revised: AGREE** — speed>80 kills 6 wins including BLUR +$0.50.

**Confidence: HIGH**

---

## Best Zero-Kill Filters Found

| Filter | Catches | Caught PnL | Remaining PnL | Rem WR |
|--------|---------|------------|---------------|--------|
| **accel+rising** | 2 losses | -$0.40 | $+0.65 | 62.1% |
| accel+bb>0.3 | 2 losses | -$0.40 | $+0.65 | 62.1% |
| accel+bb>0.4 | 1 loss | -$0.27 | $+0.52 | 61.0% |
| falling+flat+bb>0.3 | 2 losses | -$0.28 | $+0.53 | 62.1% |
| falling+flat+bb>0.4 | 2 losses | -$0.28 | $+0.53 | 62.1% |

**Best overall: `accel+rising`** — catches INJ -$0.27 and ARB -$0.13, zero kills, $+0.65 remaining PnL.

---

## Recommended Filter

**Primary: `accel+rising`** (AND condition)
- Catches 2 losses (INJ -$0.27, ARB -$0.13) = $-0.40
- Zero wins killed
- Remaining: 58 trades, 36W/22L, WR 62.1%, PnL $+0.65

**If you want to catch more losses, add `falling+flat+bb>0.4` as a second condition:**
- Catches: BCH -$0.12, ENA -$0.16 (additional $-0.28)
- Zero additional kills
- Combined catches: 4 losses ($-0.68)
- Remaining: 56 trades, 36W/20L, WR 64.3%, PnL $+0.93

**Do NOT use the claimed OR filter** — it kills ALGO +$0.19 due to falling+BB>0.4 matching.

---

## Summary Table

| Claim | Verdict | Key Issue |
|-------|---------|-----------|
| 1. Filter catches 4/26 losses, 0/35 wins killed | **DISAGREE** | Kills 1 win (ALGO +$0.19); baseline counts wrong |
| 2. Specific 4 losses listed | **AGREE** | All match DB exactly |
| 3. Remaining PnL = $+0.24 | **DISAGREE** | Actual is $+0.74 (math proves it) |
| 4. accel+flat catches 4, kills 2 | **PARTIAL** | Catches 3 (not 4), kills 2 ✅ |
| 5. speed>80 kills 6 wins including BLUR | **AGREE** | Confirmed 6 kills, BLUR +$0.50 biggest |

---

## Verdict Confidence

| Aspect | Confidence | Reason |
|--------|------------|--------|
| Baseline stats | HIGH | Direct DB query, 63 trades found |
| Filter catch/kill counts | HIGH | Exact filter logic applied to each trade |
| PnL calculations | HIGH | Summed from individual trade PnL |
| Metadata accuracy | HIGH | Extracted from `_signal_metadata` JSONB |
| Claim matching | HIGH | Direct comparison of claimed vs actual |

**Overall Confidence: HIGH** — All numbers derived from fresh DB query, no prior analysis trusted.
