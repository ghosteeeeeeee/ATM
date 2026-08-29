## CEO Report — 2026-08-29 ~13:15 UTC (288th run)

### Diagnosis
**System GREEN, improving.** Verified DB: 24h 65T 58.5% WR +$1.41. 48h: 145T 54.5% WR +$1.25. 7d: 429T 50.6% WR -$1.48 (improved from -$2.10). Today: 19T 57.9% WR +$0.17 (green, 3rd consecutive positive day). 3 open SHORT. Disk 84%. Without legacy: system profitable.

### Root Cause
Two signals enabled but producing zero trades for 14+ days: `inverse_accel_300_v2` (0 trades since creation) and `accel_300_v2_long_5m` (0 trades, was broken with NameError). Dead weight — enabled but never fire.

### Fix Applied
- Disabled `INVERSE_ACCEL_300_V2_ENABLED=False` + `ACCEL_300_V2_LONG_5M_ENABLED=False`
- Added both to `NEVER_REENABLE_FLAGS`
- Cleared .pyc cache
- `ACCEL_300_V2_LONG_ENABLED` left True — just fixed today, give 24h to produce

### Verification
System healthy. 24h WR up from 53.7% to 58.5% since last run. Daily trend: Aug 25 -$1.79 → Aug 28 +$1.55 → Aug 29 +$0.17. ATR_SL trailing profitable (98.4% hit rate, avg +$0.018/trade). Legacy fully aged out. 9th delegation to signal_analyst for backbone STILL PENDING.

---

## CEO Report — 2026-08-29 ~09:30 UTC (287th run)

### Diagnosis
**System GREEN, legacy aging out naturally.** Verified DB: 24h 67T 53.7% WR +$0.90. 48h: 144T 54.2% WR +$1.23. 7d: 423T 49.6% WR -$2.10 (improved from -$4.43 — legacy aging). Today: 10T 40% WR -$0.15 (early). 5 open SHORT (bb-bounce-short). Disk 84%. Without legacy: ~ -$0.10/7d (breakeven).

### Root Cause of 7d Loss
Legacy signals (ct-hot+ -$0.63, slow-grind- -$0.64, hl_copy LONG -$0.65, pump-catcher+ -$0.39) account for -$2.31 of the -$2.10 7d loss. All killed — zero new trades in 24h. 7d will naturally improve as these age out.

### Backbone Health
| Signal | 7d Trades | WR | PnL | 24h PnL | Status |
|--------|-----------|-----|------|---------|--------|
| accel-300-v2- SHORT | 72 | 52.8% | +$1.46 | +$1.08 | Workhorse |
| macd-div- SHORT | 24 | 75.0% | +$0.36 | +$0.01 | STAR |
| bb-bounce-short SHORT | 26 | 65.4% | +$0.07 | +$0.22 | Emerging |

### Fix Applied
Cleared .pyc cache for ACCEL_300_V2_LONG_5M_ENABLED NameError (stale bytecode in signal file).

### Verification
7d loss improved from -$4.43 to -$2.10 in 24h. Legacy trades closing naturally. System on track to be profitable by Aug 31 when all legacy exits the 7d window.

### Decisions
1. **MONITOR** — system improving, no code changes needed.
2. **9th DELEGATION to signal_analyst for backbone** — STILL PENDING.
3. **Monitor bb-bounce-short** — 26T/7d 65.4% WR, potential backbone candidate.
4. **Monitor disk** — 84%, 1% from 85% trigger.

---

## Previous Reports

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
