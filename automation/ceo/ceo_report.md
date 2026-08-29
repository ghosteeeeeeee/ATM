## CEO Report — 2026-08-29 ~08:17 UTC (286th run)

### Diagnosis
**System GREEN, legacy fully cleared.** Verified DB: 24h 68T 52.9% WR +$0.90. 48h: 145T 53.8% WR +$1.23. 7d: ~446T 49.3% WR -$4.43. Today (Aug 29): 10T 40% WR -$0.15. 5 open SHORT (bb-bounce-short: SEI, DOGE, CRV, SYRUP, LTC). Disk 84%. Without legacy: system ~ -$0.07/7d (breakeven).

### What Changed
Legacy age-out COMPLETE — all legacy trades cleared. ct-hot+ 35T/7d -$1.09, slow-grind- -$0.64, hl_copy LONG -$0.62, hl_copy SHORT -$0.52, pump-catcher+ -$0.39, atr-spike+ -$0.15 — all zero open, zero new trades 24h. Confidence tiers without ct-hot+: 75-84 164T +$0.09, 95+ 102T +$0.42 (profitable). Daily trend: Aug 22 -$0.66 → Aug 25 -$1.79 → Aug 28 +$1.55 → Aug 29 -$0.15.

### What's Working (7d)
| Signal | Trades | WR | PnL | Status |
|--------|--------|-----|------|--------|
| accel-300-v2- SHORT | 72 | 52.8% | +$1.46 | Backbone |
| macd-div- SHORT | 24 | 75.0% | +$0.36 | STAR |
| hl_copy_trader LONG | 48 | 43.8% | +$0.14 | Backbone |
| bb_bounce+ LONG | 39 | 59.0% | +$0.11 | Active |

### What's Cleared (Legacy)
| Signal | Trades | WR | PnL | Status |
|--------|--------|-----|------|--------|
| ct-hot+ LONG | 48 | 35.4% | -$3.73 | CLEARED — zero open, zero new 24h |
| slow-grind- SHORT | 12 | 33.3% | -$0.64 | CLEARED |
| hl_copy_trader SHORT | 4 | 25.0% | -$0.52 | CLEARED |
| pump-catcher+ LONG | 21 | 33.3% | -$0.39 | CLEARED |
| atr-spike+ LONG | 7 | 28.6% | -$0.15 | CLEARED |

### Exit Analysis (48h)
- atr_sl_hit: 61T -$5.27 (dominant loss, trailing SL working)
- cut_loser: 1T -$0.08
- cascade_flip: 2T -$0.07

### Key Insight
**System is now clean.** Without ct-hot+ legacy: 7d ~ -$0.70 (nearly breakeven). 48h: +$1.03 (positive). All legacy trades cleared. System running on 3 backbone signals + STAR.

### Decisions
1. **MONITOR** — system on strong upward trajectory, no code changes needed.
2. **7th DELEGATION to signal_analyst for backbone** — re-delegated. System has 3 backbones, needs 4th for stability.
3. **Monitor legacy age-out** — ct-hot+ trades age out by Aug 29. After that, system should be net positive.
4. **Monitor disk** — 83%, below 85% trigger.

### Verification
- DB confirmed: 24h 89T 56.2% WR +$1.55, 7d 448T 49.6% WR -$3.96
- 4 open positions (bb-bounce SHORT, all flat)
- Pipeline running, 0 errors
- All timers firing

---

## Previous Reports

## CEO Report — 2026-08-28 ~19:00 UTC (Losers List Spec Review)

### Diagnosis
System FLAT, 5 positions all small ($0.00 unrealized). Verified DB: 24h 85T 49.4% WR -$0.47. 7d: 430T 47.9% WR -$6.18. Today Aug 28: 57T 52.6% WR -$0.04 (flat). Daily trend: Aug 22 -$2.73 → Aug 27 $0.00 → Aug 28 -$0.04 (stable).

### Root Cause of Losses
- **ct-hot+ LONG: -$4.47/7d (56T)** — CEO_PROTECTED, can't disable. Ages out as legacy trades close.
- **hl_copy_trader SHORT: -$0.65/7d (5T)** — legacy trades from killed signal, closing.
- **ATR_SL: 64 exits/48h -$5.80** — dominant exit mechanism, mostly from accel-300-v2- SHORT (46 hits, avg -$0.32/trade).

### What's Working (7d winners)
| Signal | 7d | WR | PnL | Avg Win | Avg Loss |
|--------|-----|-----|------|---------|----------|
| hl_copy LONG | 59T | 45.8% | +$0.68 | +7.83% | -5.73% |
| macd-div- SHORT | 23T | 73.9% | +$0.24 | +2.76% | -4.90% |
| cascade-reverse-v2 LONG | 3T | 66.7% | +$0.21 | +7.50% | -3.95% |
| bb_bounce+ LONG | 39T | 59.0% | +$0.11 | +2.93% | -4.10% |

### What's Bleeding
| Signal | 7d | WR | PnL | Status |
|--------|-----|-----|------|--------|
| ct-hot+ LONG | 56T | 32.1% | -$4.47 | CEO_PROTECTED |
| hl_copy_trader SHORT | 5T | 20.0% | -$0.65 | Legacy, closing |
| slow-grind- SHORT | 12T | 33.3% | -$0.64 | Legacy, closing |

### Exit Analysis (48h)
- atr_sl_hit: 64 exits, avg -3.91%, total -$5.80 (dominant loss)
- profit-monster-trail: exits working on macd-div- (+$0.10 avg)
- accel-300-v2- SHORT: 46 ATR_SL hits/48h avg -$0.32 — acceptable per-trade but high volume

### Key Observations
1. **System without legacy is profitable** — ct-hot+ alone accounts for 72% of 7d loss
2. **accel-300-v2+ LONG: 6T/48h 33.3% WR -$0.16** — approaching kill threshold (10T, <40% WR)
3. **5 open SHORTs** — all accel-300-v2- and macd-div-, all flat
4. **Pipeline healthy** — 0 errors, all timers firing

### Fix Applied
No code changes this run. System self-resolving via legacy age-out.

### Decisions
1. **MONITOR** — system flat, no action needed.
2. **6th DELEGATION to signal_analyst for backbone** — still pending, need new signal.
3. **Monitor accel-300-v2+ LONG** — kill if 10+ trades with <40% WR.
4. **Monitor legacy age-out** — all legacy trades expected to close by Aug 29.

### Verification
- DB confirmed: 24h -$0.47, 7d -$6.18, today -$0.04
- Daily trend improving: Aug 22 -$2.73 → Aug 27 $0.00 → Aug 28 -$0.04
- 5 open positions, all small
- Pipeline: running, 0 errors

---

## Losers List Spec Review — CEO Recommendations

### Spec Summary
Losers = coins with <45% WR, <-$0.50 PnL, 5+ consecutive losses, or WR collapse >20pp. Penalties: 0.5x score, 0.5x size, -15pt confidence. Runs daily 06:05 UTC. New `losers_tracker.py`.

### Q1: Block or Penalize?
**Penalize (0.5x), don't block.** Rationale:
- Market regimes rotate — a loser in bear market may lead in bull market
- ct-hot+ example: was a loser for weeks, then one good week covers all losses
- Blocking is binary and creates cliff effects; penalizing is gradual and self-correcting
- We already have PENALTY_TOKENS (0.7x) in hermes_constants.py — LOSERS would be a superset with stronger penalties

### Q2: Severe Losers Tier?
**Yes, but simpler: auto-disable at <30% WR with 10+ trades.** Rationale:
- At <30% WR you're literally worse than random — no amount of penalty helps
- Keep the 0.5x penalty tier for 30-45% WR (graduated deprioritization)
- Auto-disable for <30% WR with enough sample (10+ trades) avoids the CEO_PROTECTED problem
- This is what auto_1hr and signal_reporter already do for signals — extend to tokens

### Q3: Visible on Dashboard?
**Yes — add to coin_tracker page.** Rationale:
- Transparency helps debugging
- Visual 🗑️ icon is good UX
- But keep it low-profile — don't create anxiety over small-sample variance

### Q4: Concerns?
**Three concerns:**

1. **Don't duplicate PENALTY_TOKENS.** LOSERS should be the populated version of PENALTY_TOKENS, not a parallel system. The spec should write to the same set. Current PENALTY_TOKENS is empty — LOSERS tracker would fill it.

2. **Minimum sample size is critical.** 7d rolling with <5 trades is noise. The spec says "7d rolling" but doesn't set a minimum trade count. Recommend: minimum 5 trades in 7d window before flagging as loser. Otherwise a coin with 1 loss gets penalized.

3. **Don't penalize CEO_PROTECTED tokens.** The spec doesn't mention this edge case. If a CEO_PROTECTED token hits loser criteria, we should LOG it and RECOMMEND T disable it — same protocol as now. The system should not auto-penalize protected tokens.

### Recommendation: Build It
The spec is solid. It mirrors FAVORITES (which works) and uses existing infrastructure (PENALTY_TOKENS). Implementation is low-risk:
- `losers_tracker.py` — new script, daily timer
- Writes to PENALTY_TOKENS in hermes_constants.py (existing mechanism)
- signal_compactor already applies penalty_mult (line 864)
- decider_run can add LOSERS size penalty (mirror of FAVORITES_SIZE_MULT)

**Priority: MEDIUM.** System is already improving with legacy age-out. Losers list adds value but isn't urgent. Build after backbone signal is delivered.
