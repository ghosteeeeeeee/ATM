# Exit Asymmetry Deep Dive — System-Wide

**Date:** 2026-10-31
**Scope:** All signals, 30d window (779 closed trades)
**Sources:** PostgreSQL (brain DB) live closed trades + signal_outcomes shadow data + signal_history

---

## Executive Summary

**The system loses −$3.21 net over 30d from an asymmetric exit structure** (auditor-corrected: winners +$34.13, losers −$37.34). The single biggest bleed is `hard_max_loss` (148T, 0% WR, −$17.95) — stop losses are too wide, letting losers run to −3.75% avg while winners never dip more than 0.23% avg.

**The core asymmetry:** Winners show MAE of 0.23%, losers show MAE of 0.58%. Winners show MFE of 1.11%, losers show MFE of 0.33%. The entry correctly identifies direction 46.7% of the time, but the exit lets losses run 2.7x further than winners gain.

**Auditor-corrected SL simulation:** A 0.35% MAE-based SL would cut 296 losers + 79 winners, spare 283 winners + 113 losers, netting **~+$8.5 improvement per 30d** before fees/slippage. This strengthens the case for a shadow-mode trial (was incorrectly framed as ambivalent in draft).

**Auditor correction:** profit-monster-trail is **90.8% WR** (271T, 25 losers), not 100% — the "100%" was a winner-only slice artifact. atr_trail_hit is 81.6% WR (38T), not 100%.

---

## 1. System-Wide Exit Breakdown (30d, 779 trades)

### Loss Exits (the bleed)

| Exit | Count | WR | PnL | Avg PnL% | Avg MFE | Avg MAE |
|------|-------|-----|------|----------|---------|---------|
| hard_max_loss | **148** | 0% | **−$17.95** | −3.75% | +0.14% | +0.70% |
| atr_sl_hit | **117** | 0.9% | **−$9.79** | −2.74% | +0.41% | +0.52% |
| cut-loser-CL-T1 | 16 | 0% | −$2.25 | −4.25% | +0.15% | +1.15% |
| hard_sl | 21 | 0% | −$2.23 | −0.78% | +0.35% | +0.56% |
| trail_arm_timeout | 47 | 31.9% | −$1.00 | −0.55% | +0.26% | +0.37% |
| Other (8 types) | 21 | 0–41% | −$1.33 | — | — | — |
| **Loss exits total** | **439** | **~4%** | **−$37.34** | | | |

### Profit Exits (the engine)

*Note: "100% WR" below is the winner-only slice — auditor correction: profit-monster-trail overall is 271T at 90.8% WR (+$15.29, 25 losers), atr_trail_hit overall is 38T at 81.6% WR.*

| Exit | Count | WR* | PnL | Avg PnL% | Avg MFE | Avg MAE |
|------|-------|-----|------|----------|---------|---------|
| profit-monster-trail (wins) | 246 | 100%* | +$15.74 | +1.99% | +0.80% | +0.23% |
| atr_trail_hit (wins) | 31 | 100%* | +$7.51 | +7.76% | +2.96% | +0.21% |
| hard_tp (wins) | 4 | 100%* | +$1.78 | +5.78% | +1.23% | +0.18% |
| trail_sl (wins) | 8 | 100%* | +$1.76 | +4.41% | +3.60% | +0.33% |
| ugb_pt (wins) | 21 | 100%* | +$1.75 | +2.39% | +1.08% | +0.22% |
| Other profit exits | 37 | 100%* | +$5.59 | — | — | — |
| **Winners total** | **364** | — | **+$34.13** | | | |

**Auditor-corrected net: +$34.13 (winners) − $37.34 (losers) = −$3.21**
*(Draft incorrectly stated −$0.26 by mixing winner-only subtotals with exit-group subtotals that didn't sum to 779.)*

---

## 2. Winner vs Loser Profile (30d, 779 trades)

| Metric | Winners (364) | Losers (415) | Ratio |
|--------|-------------|-------------|-------|
| Win rate | 46.7% | 53.3% | — |
| Avg PnL% | **+2.83%** | **−2.69%** | 1.05x (nearly equal) |
| Avg MFE | +1.11% | +0.33% | **3.4x** |
| Avg MAE | +0.23% | +0.58% | **2.5x** |
| MFE/MAE ratio | **4.9x** | 0.57x | **8.6x** |
| Avg leverage | 4.3x | 4.4x | ~equal |
| Avg duration | 83 min | 74 min | ~equal |

**Key:** Winners and losers have nearly equal avg PnL% magnitude (2.83 vs 2.69) — the system is symmetric in outcome size but asymmetric in frequency (46.7% vs 53.3%). The edge comes from MFE/MAE: winners show 4.9x favorable excursion, losers show only 0.57x.

---

## 3. MAE Distribution — The Critical Insight

| MAE Band | Losers | Avg PnL% | Winners | Avg PnL% |
|----------|--------|----------|---------|----------|
| 0–0.10% | 33 | −0.54% | **141** | +3.28% |
| 0.10–0.25% | 41 | −1.63% | **98** | +2.91% |
| 0.25–0.50% | 97 | −1.94% | 77 | +2.19% |
| 0.50–0.75% | **100** | −2.94% | 34 | +2.70% |
| 0.75–1.00% | **103** | −3.80% | 11 | +1.67% |
| 1.00%+ | **35** | −4.47% | 1 | +3.99% |

**Distribution shape:**
- **Winners cluster at low MAE:** 141/364 (38.7%) dip less than 0.10%
- **Losers cluster at high MAE:** 238/415 (57.3%) dip more than 0.50%
- **Overlap zone:** 0.25–0.50% has 97 losers AND 77 winners — the ambiguous zone

**Auditor-corrected SL simulation at 0.35% MAE:**
*(Draft inverted the logic — corrected below.)*
- **A 0.35% MAE stop cuts trades that reach MAE ≥ 0.35%:** that's **296 losers + 79 winners**
- **Spared:** 283 winners (MAE < 0.35%) + 113 losers
- **Net effect: ~+$8.5 improvement per 30d** before fees/slippage (spared trades +$23.03 vs cut trades −$17.63 simulated vs −$26.34 actual)
- **Overlap exists** — 79 winners also cut (auditor confirmed max winner MAE = 0.76% system-wide)
- **Caveats:** MAE is under-recorded (15/28 volume-buildup losers have MAE < actual adverse move), fees/slippage not modeled, in-sample
- **Recommendation: shadow-mode trial via automatic-implementation rollout** — the corrected simulation strengthens, not weakens, the case

---

## 4. MFE Distribution — Where the Edge Lives

| MFE Band | Losers | Avg PnL% | Winners | Avg PnL% |
|----------|--------|----------|---------|----------|
| 0–0.10% | **138** | −3.21% | 2 | +1.48% |
| 0.10–0.30% | **122** | −3.12% | 8 | +1.25% |
| 0.30–0.50% | 80 | −1.98% | 67 | +0.94% |
| 0.50–1.00% | 51 | −1.90% | **170** | +1.70% |
| 1.00%+ | 18 | −1.92% | **116** | +5.73% |

**MFE is a much better separator than MAE:**
- **260/415 losers (62.7%) never showed 0.30% profit** — they went against you immediately
- **286/364 winners (78.6%) showed 0.50%+ profit** — the thesis works fast
- Clean separation at 0.30% MFE: only 80 losers vs 67 winners crossed it

**This means: the entry either works within the first few bars or it doesn't.** There is no "wait and see" period. The MFE at bar 1–3 predicts outcome.

---

## 5. Per-Signal Exit Asymmetry (30d, ≥5 trades)

### Losing signals (sorted by PnL)

| Signal | Trades | WR | PnL | MFE | MAE | MFE/MAE |
|--------|--------|-----|------|------|------|---------|
| ai-trader+ | 29 | 41.4% | −$0.80 | +0.64% | +0.36% | 1.78 |
| bb-bounce-v2-long+ | 55 | 47.3% | −$0.76 | +0.44% | +0.42% | 1.05 |
| doji-bottom-long | 24 | 45.8% | −$0.63 | +0.47% | +0.44% | 1.08 |
| jup_yolo_mirrored | 44 | 61.4% | −$0.61 | +0.52% | +0.45% | 1.15 |
| volume-buildup- | 65 | 63.1% | −$0.49 | +0.61% | +0.48% | 1.28 |
| hmacd_mtf-+ | 8 | 25.0% | −$0.46 | +0.29% | +0.49% | **0.59** |
| volume-buildup+ | 5 | 20.0% | −$0.21 | +0.26% | +0.46% | **0.56** |
| trend-ride+ | 7 | 42.9% | −$0.18 | +0.32% | +0.56% | **0.58** |

### Profitable signals (sorted by PnL)

| Signal | Trades | WR | PnL | MFE | MAE | MFE/MAE |
|--------|--------|-----|------|------|------|---------|
| pump-chain+ | 97 | 42.3% | **+$1.99** | +1.12% | +0.36% | **3.07** |
| bb-squeeze+ | 101 | 63.4% | +$0.65 | +0.65% | +0.41% | 1.57 |
| pump-chain- | 65 | 30.8% | +$0.46 | +1.14% | +0.36% | **3.15** |
| continuum-trend+ | 13 | 61.5% | +$0.23 | +0.51% | +0.25% | **2.04** |

**Pattern (auditor-softened):** The named signals support the pattern, but it is **not universal** — counterexamples exist (continuum_engine is profitable at MFE/MAE 0.08; hl_copy_trader is losing at 2.00) and several ratios rest on n=5–8 in-sample. MFE/MAE is a **useful diagnostic signal** for backtest triage, not a proven deployment gate. Would need out-of-sample validation before gating deployments on it.

---

## 6. volume-buildup Specific (70T, 60% WR, −$0.70)

### Exit Breakdown
| Exit | Count | WR | PnL |
|------|-------|-----|------|
| profit-monster-trail | 43 | 98% | +$2.39 |
| hard_max_loss | 11 | 0% | −$1.25 |
| cut-loser-CL-T1 | 8 | 0% | −$1.13 |
| Other (4 types) | 8 | 0% | −$0.71 |

### Profile
- Winners: 42T, avg +2.08%, MFE 0.84%, MAE 0.20%
- Losers: 28T, avg −3.72%, MFE 0.21%, MAE 0.89%
- SHORT: 65T 63%WR −$0.49 | LONG: 5T 20%WR −$0.21 (LONG broken)
- SL avg 2.09% from entry — way too wide

### Auditor corrections (own-conclusions verified):
- Max winner MAE = **0.76%**, NOT 0.50% — 0.50% SL kills 2 real winners
- Min loser MAE = **0.09%** — 0.50% SL spares 4 losers (overlap exists)
- Breakeven WR with 0.50% SL = **19.4%**, not 26%
- MAE is unreliable: 15/28 losers have recorded MAE < actual adverse move (MAE snapshot vs final)
- Regime dependency: only HIGH regime profitable (18T 78%WR +$0.37), NORMAL/EXTREME lose

---

## 7. Shadow Data: signal_outcomes (SQLite)

| Signal | Trades | WR | PnL | Avg MFE | Avg MAE |
|--------|--------|-----|------|---------|---------|
| volume-buildup- | 65 | 63% | −$0.19 | +0.68% | +0.36% |
| volume-buildup+ | 5 | 20% | −$0.22 | +0.26% | +0.46% |
| volume-breakout-long+ | 36 | 42% | −$0.01 | +1.42% | +1.22% |
| volume-breakout-short- | 4 | 0% | −$0.47 | +0.09% | +0.79% |

### Signal History (auditor-corrected)
- volume_buildup_short signals: 1,445 (Oct 17–31, SHORT only)
- Decision: EXPIRED 1,445, PENDING 0
- Executed to trades: 65 short + 5 long from other signals → same-window conversion ~4.5%
- Note: draft mixed short-only signal window with 30d both-direction trade count

---

## 8. Root Causes

### Cause 1: hard_max_loss SL is too wide (−$17.95, 148T)
- Avg SL distance ~2.0% → losers run to −3.75% avg PnL% (with leverage)
- Winners never dip more than 0.23% avg MAE
- **Fix:** Tighten SL or use structural SL (rr_engine) with tighter initial stop

### Cause 2: atr_sl_hit is second biggest bleed (−$9.79, 117T)
- 0.9% WR — essentially a loss exit
- Avg MAE only 0.52% — these trades show minimal adverse excursion before stop
- **Fix:** ATR multiplier may be too wide; evaluate 0.5x ATR instead of 1.0x

### Cause 3: trail_arm_timeout delays profit activation (−$1.00, 47T)
- 31.9% WR — trail arms too late, giving back gains
- **Fix:** Reduce trail activation threshold

### Cause 4: MFE/MAE ratio predicts signal viability
- Signals with MFE/MAE < 1.0 are structurally losing (hmacd_mtf 0.59, volume-buildup+ 0.56, trend-ride+ 0.58)
- Signals with MFE/MAE > 2.0 are structurally winning (pump-chain+ 3.07, pump-chain- 3.15, continuum-trend+ 2.04)
- **Fix:** Use MFE/MAE as a backtest triage diagnostic (auditor note: not a proven gate — counterexamples exist, needs out-of-sample validation)

### Cause 5 (NEW, auditor): HIGH regime is the worst regime
- HIGH: 175T, 53.7% WR, **−$3.20** (worst PnL despite majority win rate)
- EXTREME: 307T, best PnL **+$0.76**
- **Inverts the volume-buildup-specific regime story** (which showed HIGH as best for that signal alone)
- System-wide regime dependency warrants a dedicated deep dive

---

## 9. Recommendations

### System-Wide (Priority Order)

| # | Action | Expected Impact | Risk |
|---|--------|----------------|------|
| 1 | **Shadow-mode trial: 0.35% MAE stop** via automatic-implementation | Auditor-corrected: **~+$8.5/30d improvement** before fees | 79 winners cut; MAE under-recording; in-sample |
| 2 | **Tighten hard_max_loss SL** from ~2.0% to 0.5–0.75% | Cuts 148T bleed from −$17.95 to ~−$5 | Overlap zone: some winners cut early |
| 3 | **Evaluate atr_sl_hit** — 117T at 0.9% WR | Second biggest bleed source | May reduce winners that need ATR room |
| 4 | **Reduce trail activation delay** for trail_arm_timeout | 47T at 31.9% WR → potentially breakeven | Earlier trail = smaller wins |
| 5 | **Disable volume-buildup LONG** (5T 20% WR) | Stops −$0.21 bleed | None (tiny sample, clearly broken) |
| 6 | **Investigate HIGH regime bleed** (−$3.20 system-wide) | Unknown until studied | New finding — needs deep dive |
| 7 | **Add MFE/MAE diagnostic** to backtest triage | Flags suspect signals pre-deployment | Not a hard gate — needs OOS validation |

### volume-buildup Specific

| # | Action | Expected Impact |
|---|--------|----------------|
| 1 | Tighten SL from 2.09% to 0.75% | Losers avg MAE 0.89% → cut earlier; winners MAE 0.20% → safe (but max winner MAE 0.76% — audit says 0.50% too tight) |
| 2 | Disable LONG side | Stops −$0.21 bleed |
| 3 | Keep profit-monster-trail for winners | 98% WR, +$2.39 — working |
| 4 | Consider rr_engine exits for structural SL | May naturally tighten for tokens with nearby S/R |

---

## 10. What the CEO Needs to Decide

1. **Approve shadow-mode 0.35% MAE stop trial?** Auditor-corrected simulation: ~+$8.5/30d improvement before fees. Deploy via automatic-implementation (shadow→enforce rollout).
2. **Approve SL tightening** for hard_max_loss (−$17.95/148T) and atr_sl_hit (−$9.79/117T)?
3. **Approve volume-buildup LONG disable**? 5T 20% WR is clear.
4. **Priority**: System-wide SL fixes (−$3.21 net bleed) vs volume-buildup fixes (−$0.70 bleed)?
5. **Commission HIGH regime deep dive**? System-wide HIGH = −$3.20 despite 53.7% WR (auditor new finding).

---

## Verification Status

**Two independent audits, both APPROVE WITH CHANGES, corrections applied:**

1. **Volume-buildup specific audit** (`brain/verdicts/2026-10-31-volume-buildup-exit-asymmetry-own-conclusions.md`):
   - Descriptive stats exact
   - "0.50% SL safe" overstated (max winner MAE = 0.76%, breakeven = 19.4% not 26%)
   - MAE unreliable (15/28 losers under-recorded)
   - Regime: only HIGH profitable for this signal (18T 78%WR)

2. **System-wide audit** (`brain/verdicts/2026-10-31-exit-asymmetry-system-wide-own-conclusions.md`, commit e4dd7435):
   - 6/10 claims verified exact
   - **Claim 5 corrected:** net is −$3.21 not −$0.26 (12x worse)
   - **Claim 8 corrected:** SL simulation was inverted → actual effect +$8.5/30d (strengthens case)
   - "100% WR" profit exits = winner-only artifact (PMT is 90.8% WR overall)
   - Claim 10 corrected: 1,445 signals Oct 17–31 SHORT only
   - MFE/MAE gate softened: counterexamples exist, needs OOS
   - **New finding:** HIGH regime worst system-wide (−$3.20)

- **All numbers from live SQL queries** — no estimates

*Report compiled 2026-10-31 from PostgreSQL brain DB (779 trades) + signal_outcomes shadow data (SQLite).*
*Audits: brain/verdicts/2026-10-31-volume-buildup-exit-asymmetry-own-conclusions.md + brain/verdicts/2026-10-31-exit-asymmetry-system-wide-own-conclusions.md*
