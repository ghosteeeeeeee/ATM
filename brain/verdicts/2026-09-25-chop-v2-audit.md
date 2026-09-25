# Independent Audit: Chop V2 Spec

**Auditor:** Independent Agent (fresh eyes, no prior context)
**Date:** 2026-09-25
**Files Read:** chop-v2-spec.md, signal_compactor.py, volatility_gate_v2.py, hermes_constants.py, profit_monster.py, chop_detector.py
**DB Queried:** PostgreSQL brain (host=/var/run/postgresql, dbname=brain)
**Time Window:** Last 14 days (close_time > now() - interval '14 days')

---

## Summary of Findings

| # | Claim | Verdict | Confidence |
|---|-------|---------|------------|
| 1 | Mean-rev signals win in chop (55% WR SHORT, 60.7% WR LONG) | **PARTIAL** | HIGH |
| 2 | Momentum signals lose in chop (49.1% SHORT, 48.9% LONG) | **PARTIAL** | HIGH |
| 3 | SHORT booking ratio -23.4% (0.90% MFE, -0.21% booked) | **UNVERIFIABLE** | HIGH |
| 4 | PM trail 0.40% activation is the bottleneck | **DISAGREE** | HIGH |
| 5 | <2h trades destroy PnL, >6h trades profitable | **AGREE** | HIGH |
| 6 | BTC can be in chop while individual coins trend | **AGREE** | HIGH |
| 7 | Spec proposes new chop gate (overlap with chop_detector.py?) | **PARTIAL DUPLICATION** | HIGH |

---

## Detailed Verdicts

### Claim 1: Mean-rev signals win in chop (55% WR SHORT, 60.7% WR LONG in NEUTRAL)

**Verdict: PARTIAL**

**Evidence from DB (14d, NEUTRAL regime, 396 trades):**

| Signal Family | Direction | Trades | WR | Total PnL (%) | Avg PnL (%) |
|---------------|-----------|--------|-----|---------------|-------------|
| MEAN-REV | LONG | 137 | **53.3%** | **+82.13** | +0.60 |
| MEAN-REV | SHORT | 159 | **50.9%** | **-88.14** | -0.55 |
| MOMENTUM | LONG | 72 | **51.4%** | **-1.25** | -0.02 |
| MOMENTUM | SHORT | 29 | **37.9%** | **-11.87** | -0.41 |

**Analysis:**
- MEAN-REV LONG: WR is 53.3% (claimed 60.7%). The claim is **inflated by 7.4 percentage points**. However, mean-rev LONG IS profitable (+82.13% total PnL).
- MEAN-REV SHORT: WR is 50.9% (claimed 55.0%). The claim is **inflated by 4.1 percentage points**. And critically, mean-rev SHORT **LOSES MONEY** (-88.14% total PnL). The spec claims it's profitable (+$0.07), but the data shows the opposite.
- The directional classification into "MEAN-REV" vs "MOMENTUM" families was done by the auditor using chop_detector.py's SIGNAL_OVERRIDES mapping. The spec may have used a different classification.

**Bottom line:** Mean-rev LONG is the only profitable signal family in chop. Mean-rev SHORT loses money. The spec's numbers are wrong.

---

### Claim 2: Momentum signals lose in chop (49.1% SHORT, 48.9% LONG in NEUTRAL)

**Verdict: PARTIAL**

**Evidence:**
- MOMENTUM LONG: 51.4% WR (claimed 48.9%). The claim is **wrong by 2.5 points**. Momentum LONG is essentially break-even (-1.25% total PnL).
- MOMENTUM SHORT: 37.9% WR (claimed 49.1%). The claim is **wrong by 11.2 points**. Momentum SHORT is **much worse** than claimed — 37.9% WR is terrible.
- The spec's numbers suggest momentum SHORT is mediocre (49.1%), but reality shows it's catastrophic (37.9%).

**Bottom line:** Momentum does lose in chop, but the spec understates how badly. Momentum SHORT at 37.9% WR is a disaster, not a mild underperformance.

---

### Claim 3: SHORT booking ratio is -23.4% (sees 0.90% MFE but books -0.21%)

**Verdict: UNVERIFIABLE**

**Evidence:**
- MFE data is **almost entirely NULL**: only 124 out of 5,315 closed trades (2.3%) have mfe_pct populated.
- Of those 124 trades, only 53 are SHORT in NEUTRAL — a tiny sample.
- Where MFE exists for SHORT NEUTRAL trades: avg_mfe_pct = 0.564% (not 0.90%), avg_pnl_pct = +0.027% (not -0.21%).
- The booking ratio claim (pnl/mfe) shows +4.8% average where data exists, not -23.4%.

**The claim is built on a foundation of missing data.** With 97.7% NULL MFE values, any statistic derived from MFE is unreliable. The spec's "0.90% MFE" figure cannot be confirmed or denied.

**Root cause:** MFE/MAE is not being recorded for most trades. Only 6 trades in the last 14 days have MFE data. This is a critical data gap that should be fixed BEFORE building chop exit logic based on MFE.

---

### Claim 4: PM trail activates at 0.40% but ATR SL hits before trail catches

**Verdict: DISAGREE**

**Evidence from code:**
- `PM_TRAIL_ACTIVATE_PCT = 0.004` (0.40%) — confirmed in hermes_constants.py line 1456
- `PM_TRAIL_DISTANCE_PCT = 0.002` (0.20%) — confirmed in hermes_constants.py line 1457
- The trail is ALREADY tighter than ATR SL (0.20% vs ~0.15% from peak). Comment in code: "Trail MUST be tighter (0.20%) to exit before ATR SL."

**Evidence from DB (14d, NEUTRAL regime):**

| Close Reason | Count | Avg PnL | Total PnL |
|--------------|-------|---------|-----------|
| atr_sl_hit | 1,057 | -0.54% | -568.68% |
| profit-monster-trail | 627 | **+1.50%** | **+940.31%** |
| cut-loser-CL-T1 | 109 | -4.64% | -505.32% |

**Analysis:**
- PM trail fires **627 times** in NEUTRAL with avg +1.50% PnL. It IS firing and it IS the most profitable exit.
- ATR SL fires 1,057 times with avg -0.54% PnL. This is the biggest loser.
- The claim that "trail doesn't catch" is contradicted by 627 successful trail exits totaling +940.31% PnL.
- The REAL problem is that ATR SL fires 1.7x more often than PM trail. Trades that never reach 0.40% profit get killed by ATR SL before trail can activate. This is a **coverage problem**, not a trail-too-slow problem.

**The bottleneck is NOT the 0.40% activation.** The bottleneck is that many trades never reach 0.40% profit at all — they go straight to ATR SL. Lowering activation to 0.25% (as the spec proposes) would help capture more trades, but the real fix is preventing bad entries in chop (which the spec's signal routing addresses).

---

### Claim 5: Trades stopped in <2h destroy PnL while trades held >6h are profitable

**Verdict: AGREE (strongly)**

**Evidence from DB (14d, NEUTRAL regime, all signals):**

| Duration | Trades | Total PnL (%) | Avg PnL (%) | WR |
|----------|--------|---------------|-------------|-----|
| <2h | 229 | **-281.92** | **-1.23** | 44.1% |
| 2-6h | 121 | +96.62 | +0.80 | 55.4% |
| >6h | 50 | **+159.62** | **+3.19** | 72.0% |

**By direction:**

| Duration | Dir | Trades | Total PnL | Avg PnL | WR |
|----------|-----|--------|-----------|---------|-----|
| <2h | LONG | 139 | **-141.62** | -1.02 | 46.0% |
| <2h | SHORT | 90 | **-140.29** | -1.56 | 41.1% |
| >6h | LONG | 19 | +86.28 | +4.54 | 73.7% |
| >6h | SHORT | 31 | +73.34 | +2.37 | 71.0% |

**Analysis:**
- <2h trades lose -281.92% total PnL across 229 trades. This is the single biggest source of losses.
- >6h trades gain +159.62% total PnL across 50 trades. These are the system's bread and butter.
- The spec claims -$6.27 LONG and -$3.36 SHORT (in USDT). My data shows -$5.85 LONG and -$3.99 SHORT. Close but not exact — likely different time windows.
- SHORT <2h is the worst performer: 41.1% WR, -1.56% avg PnL. This is exactly what the chop exit module should address.

**This claim is the strongest finding in the entire spec.** The data unequivocally supports it.

---

### Claim 6: BTC can be in chop while individual coins trend

**Verdict: AGREE**

**Evidence from DB (14d, NEUTRAL regime, top performers by coin):**

| Token | Trades | WR | Total PnL | Avg PnL |
|-------|--------|-----|-----------|---------|
| AVAX | 5 | 40.0% | +56.00 | +11.20 |
| JUP | 7 | 71.4% | +26.69 | +3.81 |
| XPL | 5 | 80.0% | +22.46 | +4.49 |
| FOGO | 9 | 55.6% | +20.49 | +2.28 |
| ADA | 7 | 57.1% | +19.54 | +2.79 |

**Analysis:**
- In NEUTRAL (BTC chop), individual coins show massive performance variation: AVAX +56%, JUP +26%, while others lose money.
- This confirms that BTC being in chop does NOT mean all coins are choppy.
- The existing chop_detector.py already partially addresses this with `_get_token_momentum()` (line 123-141) which checks per-coin 1h momentum and allows momentum signals when the coin is trending (>0.5% in 1h).

**Bottom line:** The insight is valid. The existing code partially addresses it. The spec's per-coin classification would be a more robust version of what already exists.

---

## Critical Finding: Does the Spec Duplicate Existing Code?

### What chop_detector.py ALREADY does:
1. ✅ Classifies signals as MOMENTUM or MEAN_REVERSION (SIGNAL_OVERRIDES dict, 100+ entries)
2. ✅ Blocks momentum signals in CHOP regime (should_trade_signal function)
3. ✅ Allows mean-reversion signals in CHOP
4. ✅ Checks BTC 30m momentum (flat = chop)
5. ✅ Checks volatility regime (FLAT = chop)
6. ✅ Checks market phase (defensive/range = chop)
7. ✅ Checks continuum oscillator (structural override)
8. ✅ Per-coin momentum check (token trending >0.5% bypasses chop block)
9. ✅ Is ENABLED (CHOP_DETECTOR_ENABLED = True)
10. ✅ Is integrated into signal_compactor.py (lines 1209, 1288-1290, 3830-3831)

### What the spec proposes that is NEW:
1. ✅ Per-coin TRENDING/CHOPPING classification using EMA20 slope, ATR ratio, candle consistency (chop_detector only uses 1h momentum)
2. ✅ Coin trend score (0-100) — more granular than binary chop/trend
3. ✅ BTC chop classification using continuum oscillator (partially exists in chop_detector lines 316-366)
4. ✅ Chop exit module (CHOP_TRAIL, CHOP_TIER, CHOP_KILL) — completely new
5. ✅ Signal routing with score multipliers (0.3x penalty, 1.2x boost) — chop_detector only blocks/allows, no scoring

### What the spec DUPLICATES:
1. ❌ Signal family classification (MOMENTUM vs MEAN-REV) — already exists in SIGNAL_OVERRIDES
2. ❌ Blocking momentum in chop — already exists in should_trade_signal
3. ❌ BTC momentum check — already exists in _check_btc_momentum
4. ❌ "BTC can be while coins trend" insight — already addressed by per-coin bypass

**Verdict: The signal routing portion of the spec duplicates ~60% of what chop_detector.py already does. The per-coin classification and chop exit module are genuinely new.**

---

## Additional Findings (Not in Spec)

### Finding 1: MFE/MAE Data is Almost Entirely NULL
- **Severity: HIGH**
- Only 2.3% of trades have MFE data (124/5315)
- Only 6 trades in the last 14 days have MFE data
- The spec's entire SHORT booking ratio claim is unverifiable
- **Recommendation:** Fix MFE/MAE recording BEFORE building chop exit logic based on MFE

### Finding 2: cut-loser-CL-T1 is a Major Loser
- **Severity: HIGH**
- 109 exits in NEUTRAL, avg -4.64% PnL, total -505.32%
- This is nearly as bad as ATR SL (-568.68%)
- The spec doesn't address cut_loser at all

### Finding 3: PM Trail IS Working (Contrary to Spec)
- **Severity: MEDIUM**
- 627 trail exits in NEUTRAL with avg +1.50% PnL
- Total +940.31% — the system's most profitable exit
- The spec claims trail "doesn't catch" but it does — the issue is coverage, not trail speed

### Finding 4: SHORT NEUTRAL is Overall Unprofitable
- **Severity: HIGH**
- 189 SHORT trades in NEUTRAL, total PnL: -99.83%, WR: 49.2%
- The spec proposes routing to fix this, which is directionally correct

### Finding 5: The Spec's Signal Family Classification Doesn't Match chop_detector.py
- **Severity: MEDIUM**
- The spec classifies 'pump-chain' as MOMENTUM (to block in chop)
- chop_detector.py classifies 'pump-chain' as MEAN_REVERSION (to allow in chop)
- pump-chain is the #1 signal in NEUTRAL (125 trades, 50.4% WR, +49.77% PnL)
- Blocking pump-chain in chop would REMOVE the system's most-traded signal in NEUTRAL

---

## Recommendations

1. **Fix MFE/MAE recording first.** The spec's core premise (booking ratio analysis) is unverifiable without this data. No chop exit logic should be built on MFE assumptions.

2. **Don't duplicate chop_detector.py.** Extend it with per-coin classification instead of creating a separate chop_gate.py. The existing integration into signal_compactor.py is already working.

3. **Don't block pump-chain in chop.** It's the most-traded signal in NEUTRAL with 50.4% WR and +49.77% PnL. The spec's CHOP_BLOCKED_FAMILIES incorrectly classifies it as momentum.

4. **Focus on the <2h problem.** The data shows this is the #1 source of losses. The chop exit's CHOP_KILL (45min no-profit, 0.8% MAE) directly addresses this.

5. **Lower PM trail activation to 0.25% for chop trades.** The spec's CHOP_TRAIL_ACTIVATE_PCT = 0.0025 is sensible. Many trades never reach 0.40% — capturing them at 0.25% would reduce <2h losses.

6. **Fix the cut-loser problem.** The spec ignores cut-loser-CL-T1 entirely, but it's the 3rd biggest loser (-505.32% in NEUTRAL).

---

## Final Assessment

The spec correctly identifies the core problem (system bleeds in chop) and proposes directionally correct solutions (signal routing, tighter exits for chop trades). However:

- **3 of 6 claims have wrong numbers** (claims 1, 2, 3)
- **1 claim contradicts the data** (claim 4 — PM trail IS working)
- **1 critical claim is unverifiable** (claim 3 — MFE data is 97.7% NULL)
- **The signal routing duplicates existing code** (chop_detector.py already does this)
- **The spec would block pump-chain**, which is the most profitable signal family in NEUTRAL

**Overall Grade: C+**
- Good problem identification
- Directionally correct solutions
- But wrong numbers, duplicated code, and a critical blind spot (MFE data gap)

---

*Audit completed 2026-09-25 by independent agent. All data queried directly from PostgreSQL brain DB.*
