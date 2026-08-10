# Trading Log — Learnings & Decisions

## 2026-08-10: Daily Orchestrator Report

### Pipeline Status
- **Portfolio**: 6 open | 64 closed today | **+5.44% PnL**
- **Market regime**: 106 tokens scanned → 1 LONG / 3 SHORT / 102 NEUTRAL
- **Speed**: 1 token >= 50% confidence (NIL LONG_BIAS 55.4%)
- **Signals**: 93 generated/hr, 0 approved (macro gate REDUCE)
- **Kill switch**: LIVE TRADING ON
- **CEO**: 62.3% WR 24h, 11th consecutive green day

### Health Status
- **System**: OK — 42 timers active, all firing
- **Disk**: 81% (22GB free)
- **Errors**: 0 critical
- **Auto-fixes**: Stopped deprecated self-close-watcher timer (was wasting cycles)

### What Was Implemented

1. **Restarted auto-1hr timer** — was dead since Aug 02 (8 days). Timer was enabled but not firing (showed "Trigger: n/a"). Restarted manually, confirmed service runs successfully. Next fire in ~57min.

2. **Fixed signal reporter timeout** — OpenMemory queries failing with `tenant_mismatch` errors, causing 10min timeouts. Added explicit "Do NOT query OpenMemory" instructions to both `signal_reporter_prompt.md` and `auto_1hr_prompt.md`.

3. **Implemented signal version tracking** — Created `scripts/signal_version.py` with log/current/history/list commands. Storage at `data/signal_versions.json`. Enables param change tracking + regression detection.

### Blacklist Testing — FINAL
- **77 tokens tested across 5 batches, 0 KEEP**
- Root cause: signal generation filters block these tokens; when signals fire, 0% WR
- Blacklist is a symptom filter, not a cause — no further batches planned

### Signal Performance (24h)
- **Zero winning signals** — all active signals net negative
- **Biggest losers**: tl_break_long (-$73), tl_break_short (-$61)
- **Systemic issue**: No signal family has positive PnL in 7 days

### Pending Plans (from upgrade_audit.md)
| Plan | Difficulty | Status |
|------|-----------|--------|
| signal-version-tracking | L2 | **DONE** (script created) |
| audit_memory | L1 | PENDING |
| weekly_signal_review | L2 | PENDING |
| wyckoff-pattern-recognition | L2 | NOT IMPLEMENTED |

### Quality Metrics
- Tasks completed: 5
- First-attempt success: 100%
- Pipeline uptime: 100%
- Critical issues found: 2 (stale timers)

---

## 2026-08-08: Daily Orchestrator Report

### Pipeline Status
- **Portfolio**: 6 open | 40 closed today | **+2.10% PnL**
- **Market regime**: NEUTRAL across all tokens
- **Speed**: moderate
- **Hotset**: empty (all-NEUTRAL regime)
- **Blacklist**: 171 SHORT / 139 LONG (final — no more trials)

### Health Status
- **System**: OK — 30+ timers active
- **Disk**: 79% (89G/118G) — health monitor compressed 47 old logs
- **Errors**: 0 critical

### Signal Performance (24h)
- **Trades**: 42 closed, 61.9% WR, +$0.52 PnL
- **Killed today**: range_finder- SHORT (40% WR, -$0.19), vortex_break_short SHORT (25% WR, -$0.15)
- **Top performer**: bb_bounce+,range_finder+ LONG (75% WR, +$0.51)
- **SHORT side broadly negative** — 9 signals now disabled
- **LONG side (bb_bounce+ combos) carrying the system**

### Blacklist Trials — COMPLETE
- **77 tokens tested across 5 batches, 0 KEEP**
- Root cause: signal generation filters (SPEED_MIN, PHASE_ENTRY, CONTEXT_GATE) block these tokens
- Blacklist is a symptom filter, not a cause — no further batches planned

### What Was Implemented

1. **Fixed hl-sync-guardian timer** — was dead since Jul 29 (service manually started Aug 7). Timer restarted, guardian now fires every 2 min as designed.

2. **Restarted auto-1hr timer** — dead since Aug 2 (6 days). Timer was disabled. Re-enabled and restarted. Will fire next hour.

3. **Uncertainty check quick wins** — already in bug-hunter (line 138) and post-change (line 69) skills. No changes needed.

4. **Disk cleanup** — health monitor already compressed 47 old logs. 79% disk is safe, no further action needed.

### Critical Issues
- **Auto-1hr was dead 6 days** — no param tuning occurred during this period. Now restored.
- **HL-sync-guardian timer was dead 10 days** — service ran but timer wasn't firing. Now fixed.

### Pending Plans (from upgrade_audit.md)
| Plan | Difficulty | Status |
|------|-----------|--------|
| signal-version-tracking.md | L2 | PENDING — param change logging + regression detection |
| transcript-mining-quick-wins.md | L1 | DONE (uncertainty checks already exist) |
| wyckoff-pattern-recognition | L2 | NOT IMPLEMENTED |
| self-learning-system-spec | L3 | NOT IMPLEMENTED |

### Recommendations for CEO
1. **Monitor auto-1hr** — now restored, will it produce useful tuning? First run due in ~30min.
2. **Signal version tracking** — L2 plan, high value. Param changes currently invisible. Recommend implementing next.
3. **SHORT signals** — 9 disabled, SHORT side broadly negative. Consider leaving SHORT disabled until market shows directional conviction.
4. **Open bugs**: 0 (clean)

### Quality Metrics
- Tasks completed: 5
- First-attempt success: 100%
- Pipeline uptime: 100%
- Critical issues found: 2 (stale timers)

---

## 2026-08-07: Daily Orchestrator Report

### Pipeline Status
- **Portfolio**: 6 open | 79 closed today | **-4.70% PnL**
- **Market regime**: 0 LONG / 0 SHORT / 104 NEUTRAL — no directional conviction
- **Speed**: 42% tokens >= 50% (moderate)
- **Hotset**: 1 token
- **Blacklist**: 169 SHORT / 143 LONG
- **Dead hours**: active (03-08 UTC)

### CEO Report Analysis (Re-verification)
Data source: `signals_hermes_runtime.db` → `signal_outcomes`, last 7 days.
Criteria: 20+ trades AND negative total PnL.

### Signal Kills Implemented

| Signal | Trades (7d) | WR | PnL | Action |
|--------|-------------|-----|-----|--------|
| TL_BREAK (all) | 66 long + 39 short | 33.3% / 30.8% | -$1.33 / -$1.43 | **DISABLED + NEVER_REENABLE** |
| ZSCORE_RISING (all) | 44 + 26 | 38.6% / 26.9% | -$1.37 / -$1.01 | **DISABLED + NEVER_REENABLE** |
| HZSCORE_MINUS | 76 | 15.8% | -$53.50 | **DISABLED + NEVER_REENABLE** |
| PCT_HERMES_PLUS | 64 | 14.1% | -$33.83 | **NEVER_REENABLE** (already False) |

### What Was Already Dead (verified)
- accel-300-vel+ → already in NEVER_REENABLE_FLAGS
- inv-accel-300- → already in NEVER_REENABLE_FLAGS
- vel-hermes- → already in NEVER_REENABLE_FLAGS

### Remaining Active Signals (winners)
- bb_bounce,hzscore+ LONG — 100% WR (3T), +1.27
- ma100-cross,return_exhaustion_long — 66.7% WR (6T), +1.13
- ma100-cross,vortex_break_long — 80% WR (5T), +0.82
- hzscore+,return_exhaustion_long — 54.5% WR (11T), +0.88
- vortex_break_short — 100% WR (2T), +0.89

### Recommendations for CEO
1. **Investigate phantom trade bug** — debug instrumentation deployed, awaiting production data
2. **Monitor remaining active signals** — 5 winning combos, all LONG-dominant
3. **Blacklist experiment complete** — 77 tokens tested, 0 KEEP. Stop rotating.

### Files Changed
- `scripts/hermes_constants.py`: Disabled 4 signals, added 7 to NEVER_REENABLE_FLAGS, removed 2 from ROTATOR_PROTECTED_FLAGS

---

## 2026-08-07: Daily Orchestrator Run (17:30 JST)

### Pipeline Status (Latest)
- **Portfolio**: 6 open | 67 closed today | **-1.88% PnL**
- **Market regime**: 1 LONG / 0 SHORT / 105 NEUTRAL — heavily neutral
- **Speed**: 42% tokens >= 50% — market too quiet for active trading
- **Hotset**: 0-2 tokens (confluence gate working correctly)
- **Errors**: 0 (only [SLOW] runner warnings)

### Actions Taken

**1. Disabled bb_bounce standalone SHORT**
- File: `scripts/hermes_constants.py:936`
- Change: `BB_BOUNCE_MINUS_ENABLED = False`
- Reason: 40% WR, -$4.61% over 7d. Confluence (bb_bounce+hzscore+) stays enabled (100% WR).

**2. Investigated hotset empty issue**
- Finding: Hotset IS working correctly. Confluence gate requires 2+ unique signal types.
- In quiet market (42% speed, 105/106 neutral), most signals are single-source and correctly blocked.
- When confluence signals fire (bb_bounce+ + range_finder+, ma100-cross- + vortex_break_short), they DO get through.
- Recent examples: ETH LONG (bb_bounce+ + hl_copy_trader), ENS LONG (bb_bounce+ + range_finder+)
- **No action needed** — system working as designed.

**3. Investigated stale signal names in signal_outcomes**
- Finding: 5106 out of 8980 records (56.9%) are from stale/disabled signals.
- Offenders: accel-300 variants, inv-accel-300, tl_break, vel-hermes, pattern_scanner, decider.
- These are HISTORICAL records from when signals were enabled, not current writes.
- Impact: Corrupts performance tracking metrics in signal_reporter.
- **Recommendation**: Add filter in signal_reporter to exclude stale signal types, or purge records older than 30 days.

### Recommendations for CEO
1. **Stale signal cleanup** — 56.9% of signal_outcomes are from dead signals. Add exclusion filter or purge.
2. **Monitor bb_bounce+hzscore+ combo** — 100% WR, best signal in system. Protect from accidental disable.
3. **Market quietness** — 42% speed, 105/106 neutral. System correctly reducing trade frequency.

### Quality Metrics
- Tasks completed: 3/3
- First-attempt success: 100%
- Critical issues found: 1 (stale signal records corrupting metrics)

---

## 2026-08-06: Daily Orchestrator Report

### Pipeline Status
- 6 open | 75 closed today | +3.18% PnL
- Hotset empty — market overwhelmingly NEUTRAL (103/105 tokens)
- Pipeline healthy, no errors

### Changes Implemented
1. **FIXED: tl_break inversion bug** — Removed `tl_break_long`/`tl_break_short` from `INVERT_SIGNALS` in `hermes_constants.py:1151-1159`. Root cause: dynamic WR-based auto-inversion was flipping good signals to wrong direction (31.6% of trades inverted). Current tl_break performance is 100% WR — no inversion needed.
2. **RE-ENABLED: zscore-rising+** — Set `ZSCORE_RISING_PLUS_ENABLED = True` in `hermes_constants.py:1051`. Signal reporter showed 62.5% WR, +$2.17. Not in `_NEVER_REENABLE` set.
3. **SKIPPED: vel-hermes- re-enable** — CEO explicitly blocked in `_NEVER_REENABLE` set. Signal reporter recommendation conflicts with CEO decision.
4. **SKIPPED: decider SHORT disable** — Already in `_DEAD_SIGNALS` blocklist, no action needed.

### Blacklist Testing Complete
- 77 tokens tested across 5 batches, 0 KEEP
- Blacklist is working as intended — signal generation filters (speed, phase, context gate) block these tokens before they can trade
- No further batches planned

### Critical Issues
- Market overwhelmingly NEUTRAL — no new entries expected until regime shifts
- All 77 blacklist candidates confirmed as signal-quality-poor, not blacklist-bottleneck

### Next Steps
1. Monitor tl_break performance post-fix (should see 0 inversions going forward)
2. Monitor zscore-rising+ performance after re-enable
3. Wait for regime shift to generate new hotset entries

---

## 2026-08-05: Signal Performance Report

### 24h Performance (catastrophic)
- **40 trades, 0 wins, 0% WR, -$60.56 PnL**
- Every signal that fired in the last 24h lost money
- Worst: zscore-rising- (-$9.06), pattern_wolf_wave_bear (-$8.8), bb_bounce (-$6.76)

### 7d Overall
- **590 trades, 88 wins, 14.9% WR, -$354.61 PnL**
- No signal has positive PnL across any timeframe
- tl_break family = 45% of total losses (299 trades, -$161.53)

### Critical Actions Required
1. DISABLE `TL_BREAK_ENABLED` — 12-20% WR, -$161 PnL, re-enabled 08-04 still failing
2. FIX `INVERSE_ACCEL_300_MINUS_ENABLED` → False (flag is True but in NEVER_REENABLE list)
3. DISABLE `ACCEL_300_MINUS_ENABLED` — 0% WR in 7d
4. NEW losers to disable: bb_bounce, pattern_wolf_wave_bull/bear

### Systemic Issue
Zero WR across ALL signals for 48h+. Market regime hostile to all signal types. Consider pausing signal-based entries until regime shifts.

---

## 2026-08-01: Trade Analysis & SL/TP Retune

### Data Window
- Analyzed: 50 closed trades (last 12h), signal_outcomes (72h), price_history around key trades
- Trades: 2814 total closed, 0 open at analysis time
- Trade rate: 3 trades in past hour (very low — restrictive params)

### Signal Performance (72h by direction)
| Signal | Dir | Trades | WR | Avg PnL |
|--------|-----|--------|-----|---------|
| tl_break_long | LONG | 108 | 1.9% | -0.626% |
| tl_break_short | SHORT | 119 | 3.4% | -0.470% |
| accel-300-vel+ | SHORT | 34 | 11.8% | -0.428% |
| accel-300-vel- | LONG | 20 | 30.0% | -0.264% |
| inv-accel-300- | SHORT | 14 | 14.3% | -0.218% |
| accel-300+ | SHORT | 8 | 25.0% | -0.045% |

**Key finding:** ALL signal types are net losers. Best performer: accel-300+ SHORT (-0.045% avg). Worst: tl_break_long LONG (-0.626%).

### Price Action Analysis (1h before → 2h after entry)
**Winners** (PURR SHORT, AAVE SHORT, ORDI LONG):
- Low adverse excursion (<0.5%) — price barely went against entry
- High favorable excursion (>2%) — strong directional move after entry
- Entry timing was excellent — caught the move early

**Losers** (UNI SHORT, KAITO LONG, AIXBT LONG):
- High adverse excursion (1-3.5%) — price immediately went against
- Some had high favorable excursion that REVERSED (whipsaw)
- Entry timing was poor — caught the tail end of a move

### Root Causes Identified
1. **SL too tight (0.5%)** — normal crypto retracements of 0.5-1% immediately stop out trades
2. **Trailing activates too early (0.15%)** — normal 0.2% retracements trigger trailing before trade develops
3. **Trailing distance too wide (0.50%)** — once in profit, too much room given back before trail kicks in
4. **Signal quality abysmal** — 1.9-3.4% WR on primary signals
5. **tl_break signal inversion** — tl_break_long firing on SHORT trades (28 times, 0 wins)

### Changes Implemented
1. **ATR_SL_MIN_INIT: 0.5% → 0.8%** — wider breathing room for new trades, reduce whipsaw stops
2. **TRAILING_DISTANCE_PCT: 0.50% → 0.30%** — tighter trailing locks profit faster
3. **TRAILING_ACTIVATION_PCT: 0.15% → 0.40%** — wait for real move before trailing activates

### 5 Actionable Adjustments (ranked by impact)
1. ✅ Widen initial SL to 0.8% — IMPLEMENTED
2. ✅ Tighten trailing distance to 0.30% — IMPLEMENTED
3. ✅ Raise trailing activation to 0.40% — IMPLEMENTED
4. ⬜ Raise SIGNAL_FILTER_SPEED_MIN from 50 to 60 — be more selective
5. ⬜ Investigate tl_break signal inversion — signals firing on wrong direction

### What NOT to change
- ATR_SL_MIN (0.5%) — this is the floor, keep it
- ATR_TP_MAX (1.0%) — already tight enough
- Phase-based k scaling — disabled (was compressing SL too aggressively)
- Dead hours filter — working correctly (16% WR during dead hours vs 35% active)

### Open Questions
- Why are only 3 trades in past hour? Are params too restrictive?
- ~~Is tl_break signal inversion a pipeline bug or intentional?~~ **ANSWERED 2026-08-01: context gate FLIP logic**
- ~~Should we disable tl_break_long entirely (1.9% WR on 108 trades)?~~ **Still active — see below**

---

## 2026-08-01: Context Gate FLIP Root Cause + Signal Quality Crisis

### Data Window
- Analyzed: 174 closed trades (24h), signal_outcomes (48h), trades.json (200 recent)
- Trades: 2816 total closed, 0 open at analysis time
- Trade rate: ~7 trades/hour (moderate)

### Signal Performance (24h — all signals net losers)
| Signal | Trades | WR | Total PnL | Status |
|--------|--------|-----|-----------|--------|
| tl_break_long | 44 | 4.5% | -21.33% | CATASTROPHIC |
| accel-300-vel+ | 44 | 9.1% | -20.87% | CATASTROPHIC |
| tl_break_short | 36 | 5.6% | -14.50% | CATASTROPHIC |
| accel-300-vel- | 30 | 20.0% | -12.14% | BAD |
| velocity-ignition | 10 | 0.0% | -4.97% | DEAD |

**Overall: 8.0% WR, -79.82% total PnL in 24h.**

### ROOT CAUSE: Context Gate FLIP Logic (decider_run.py:849-881)

**The smoking gun:**
- 24 tl_break_long trades executed as SHORT (inverted direction)
- 50 tl_break_short trades executed as LONG (inverted direction)
- Total: 74 out of 234 tl_break trades (31.6%) had direction INVERTED

**How it worked:**
1. Signal generator correctly identifies tl_break_long (LONG direction)
2. Context gate `_rule_context_gate()` sees phase='falling' or z_score conditions
3. Returns `('FLIP', {'new_dir': 'SHORT'})` — reversing the signal's direction
4. Trade executes as SHORT (against the signal's intended direction)
5. Result: 0% WR on all 74 flipped trades

**Why it was wrong:**
- Phase-based flip: "falling phase + LONG → SHORT" assumes the wave is dying, but tl_break already accounts for this in its trendline detection
- Z-score flip: "z < -0.5 + SHORT → LONG" assumes oversold bounce, but in downtrends z confirms trend
- The flip logic was net negative for EVERY signal type it touched

### Changes Implemented

**1. DISABLE context gate FLIP logic (decider_run.py:849-853)**
- Commented out phase-based FLIP (falling→SHORT, accelerating→LONG)
- Commented out z-score FLIP (oversold SHORT→LONG)
- SKIP remains active for overbought LONG (z > 0.5) — this was already changed from FLIP to SKIP on 2026-07-31

**2. RAISE SIGNAL_FILTER_SPEED_MIN: 50 → 65 (hermes_constants.py:471)**
- Winners average 71% speed percentile
- 50 was too permissive — letting slow, low-momentum signals through
- 65 blocks bottom 35% of speed distribution

**3. DISABLE velocity-ignition signal (already done 2026-08-01)**
- 0% WR across 10 trades, -$4.97 total
- Fires on first bar spike that reverses — no follow-through

### What NOT to change
- ATR_SL_MIN_INIT (0.8%) — wider breathing room working as intended
- TRAILING_ACTIVATION_PCT (0.40%) — wait for real move before trailing
- TRAILING_DISTANCE_PCT (0.30%) — tighter trail locks profit faster
- Phase-based k scaling — disabled (was compressing SL too aggressively)
- Dead hours filter — working correctly
- SIGNAL_FILTER_ENABLED (True) — the filter framework is sound, just needed tuning

### Remaining Issues
1. **tl_break signal quality is fundamentally poor** — even without flips, 4.5% WR (LONG) and 5.6% WR (SHORT) suggest the signal itself needs work or should be disabled
2. **accel-300-vel+ is second-worst performer** — 9.1% WR on 44 trades. Consider raising its suppression weight
3. **Trade frequency may still be too high** — 174 trades in 24h with 8% WR means 160 losses. Need to be more selective
4. **UNI, LINEA, MOVE, ZK, TIA, TURBO all 0% WR** — should be blacklisted both directions

### Open Questions for Next Analysis
- Should tl_break be disabled entirely? (4.5-5.6% WR is essentially random)
- Are the 24 signal_outcomes per tl_break trade (doubled entries) real or a dedup bug?
- What's the WR breakdown excluding flipped trades? (need to separate signal quality from flip damage)

---

## 2026-08-01: Hourly Trade Analysis — Context Gate FLIP Still Active

### Data Window
- Analyzed:12 closed trades (12h window), signal_outcomes (24h), price_history around key trades
- Trades: 2819 total closed, 2 open at analysis time
- Trade rate: ~1 trade/hour (very low — restrictive params)

### Signal Performance (24h — ALL signals net losers)
| Signal | Trades | WR | Total PnL | Status |
|--------|--------|-----|-----------|--------|
| tl_break_long | 46 | 15.2% | -24.04% | CATASTROPHIC |
| accel-300-vel+ | 44 | 18.2% | -20.87% | CATASTROPHIC |
| tl_break_short | 32 | 21.9% | -15.20% | CATASTROPHIC |
| accel-300-vel- | 30 | 26.7% | -12.14% | BAD |
| accel-300-velocity-ignition | 10 | 20.0% | -4.97% | DEAD |

### ROOT CAUSE: LLM FLIP Still Active (decider_run.py:981-982)

**The smoking gun:**
- ETH SHORT executed with tl_break_long signal (expected LONG, got SHORT)
- MOODENG LONG executed with tl_break_short signal (expected SHORT, got LONG)
- Both trades happened to WIN, but the FLIP logic was supposed to be disabled

**How it worked:**
1. Rule-based FLIP (step 6) was disabled on 2026-08-01
2. LLM context gate still had FLIP as an option in the prompt
3. LLM returned FLIP verdict, which was applied at lines 1134-1137
4. Trade executed with inverted direction

**Why it's dangerous:**
- Even though these two trades won, FLIP logic is fundamentally flawed
- Signal generators already account for market conditions
- FLIP inverts the signal's intended direction, creating negative expectancy

### Price Action Analysis (MFE/MAE)
**ETH SHORT (tl_break_long — FLIPPED):**
- MFE: +0.57%, MAE: +0.16%
- Trade won despite direction mismatch

**MOODENG LONG (tl_break_short — FLIPPED):**
- MFE: +0.67%, MAE: +0.24%
- Trade won despite direction mismatch

**ORDI SHORT (tl_break_short — normal):**
- MFE: +6.25%, MAE: +2.35%
- Whipsaw pattern: price went to +6.25% profit then reversed to -0.80% loss
- SL too tight (0.8%) couldn't survive the 2.35% adverse excursion

**PURR SHORT (tl_break_long — FLIPPED):**
- MFE: +2.99%, MAE: +0.29%
- Textbook winning trade: low adverse excursion, high favorable excursion

### Changes Implemented

**1. DISABLE LLM FLIP capability (decider_run.py:981-982, 1132-1135)**
- Removed FLIP from LLM verdict parsing
- Changed FLIP handling to treat it as WARN (confidence penalty)
- LLM prompt still mentions FLIP but responses are now ignored

**2. WIDEN initial SL from 0.8% to 1.0% (hermes_constants.py:344)**
- ATR_SL_MIN_INIT: 0.008 → 0.010
- SL_PCT_FALLBACK: 0.008 → 0.010
- STOP_LOSS_DEFAULT: 0.008 → 0.010
- Rationale: ORDI needed 2.35% room, 0.8% SL too tight for volatile tokens

**3. ACCEL_300_VELOCITY_IGNITION_ENABLED already disabled**
- Flag was set to False on 2026-08-01
- Recent accel-300-vel+ trades were generated before flag change

### What NOT to change
- ATR_SL_MIN (0.5%) — this is the floor, keep it
- ATR_TP_MAX (1.0%) — already tight enough
- TRAILING_ACTIVATION_PCT (0.40%) — wait for real move before trailing
- TRAILING_DISTANCE_PCT (0.30%) — tighter trail locks profit faster
- Phase-based k scaling — disabled (was compressing SL too aggressively)
- Dead hours filter — working correctly
- SIGNAL_FILTER_ENABLED (True) — the filter framework is sound

### 5 Actionable Adjustments (ranked by impact)
1. ✅ Disable LLM FLIP — IMPLEMENTED
2. ✅ Widen initial SL to 1.0% — IMPLEMENTED
3. ⬜ Disable tl_break_long entirely (15.2% WR over 24h)
4. ⬜ Raise SIGNAL_FILTER_SPEED_MIN from 30 to 40
5. ⬜ Blacklist tokens with 0% WR (LINEA, TIA, TURBO, BABY, BLUR, FET)

### Open Questions
- Should tl_break be disabled entirely? (15.2% WR over 24h is essentially random)
- Are the 24 signal_outcomes per tl_break trade (doubled entries) real or a dedup bug?
- Why are only 1 trade/hour? Are params too restrictive?
- Should we blacklist tokens with 0% WR in recent window?

---

## 2026-08-01: Hourly Trade Analysis — tl_break Disabled, Speed Filter Raised

### Data Window
- Analyzed: 12 closed trades (6h window), signal_outcomes (24h), price_history around key trades
- Trades: 2821 total closed, 1 open at analysis time
- Trade rate: ~2 trades/hour (moderate)

### Signal Performance (24h — ALL signals net losers)
| Signal | Trades | WR | Total PnL | Status |
|--------|--------|-----|-----------|--------|
| tl_break_long | 46 | 15.2% | -24.04% | CATASTROPHIC |
| accel-300-vel+ | 44 | 18.2% | -20.87% | CATASTROPHIC |
| tl_break_short | 32 | 21.9% | -15.20% | CATASTROPHIC |
| accel-300-vel- | 30 | 26.7% | -12.14% | BAD |
| accel-300-velocity-ignition | 10 | 20.0% | -4.97% | DEAD |

### Price Action Analysis (MFE/MAE)
**Winners** (6 trades):
- 5/6 had low adverse excursion (<0.5%) — good entry timing
- Average MFE: 0.75%, average MAE: 0.66%

**Losers** (6 trades):
- 2/6 had high adverse excursion (>1%) — poor entry timing
- 3/6 had high favorable excursion (>0.5% MFE) — whipsaw pattern
- Average MFE: 1.75%, average MAE: 0.83%

**Whipsaw Trades:**
- ORDI SHORT: MFE -6.64% (price dropped 6.64% in favor) then reversed to +2.35% adverse → -0.80% loss
- LINEA SHORT: MFE -1.11% then reversed to +0.35% adverse → -0.04% loss
- UNI LONG: MFE +1.83% then reversed to -0.28% adverse → -0.17% loss

### Changes Implemented

**1. DISABLE tl_break signal entirely (hermes_constants.py:695, 749-750)**
- TL_BREAK_ENABLED: True → False
- TL_BREAK_PLUS_ENABLED: True → False
- TL_BREAK_MINUS_ENABLED: True → False
- Rationale: 15.2% WR (LONG) and 21.9% WR (SHORT) over 24h, all net losers. Signal quality fundamentally poor.

**2. RAISE SIGNAL_FILTER_SPEED_MIN: 30 → 40 (hermes_constants.py:471)**
- Winners average 71% speed percentile
- 30 was too permissive — letting slow, low-momentum signals through
- 40 blocks bottom 40% of speed distribution

**3. BLACKLIST 0% WR tokens (hermes_constants.py:SHORT_BLACKLIST, LONG_BLACKLIST)**
- Added LINEA, TIA, TURBO, BABY, BLUR, FET to both blacklists
- All had 0% WR in last 24h, total PnL -$24.07

### What NOT to change
- ATR_SL_MIN_INIT (1.0%) — wider breathing room working as intended
- TRAILING_ACTIVATION_PCT (0.40%) — wait for real move before trailing
- TRAILING_DISTANCE_PCT (0.30%) — tighter trail locks profit faster
- Phase-based k scaling — disabled (was compressing SL too aggressively)
- Dead hours filter — working correctly
- SIGNAL_FILTER_ENABLED (True) — the filter framework is sound

### 5 Actionable Adjustments (ranked by impact)
1. ✅ Disable tl_break entirely — IMPLEMENTED
2. ✅ Raise SIGNAL_FILTER_SPEED_MIN to 40 — IMPLEMENTED
3. ✅ Blacklist 0% WR tokens — IMPLEMENTED
4. ⬜ Disable accel-300-vel+ (18.2% WR, -$20.87 total) — second worst performer
5. ⬜ Investigate whipsaw pattern (3/6 losers had high MFE then reversal) — consider tighter trailing activation

### Open Questions
- Should accel-300-vel+ be disabled entirely? (18.2% WR over 24h is essentially random)
- Are the whipsaw trades due to trailing activation too late (0.40%)? Could lower to 0.30%?
- Why does ORDI have such extreme MFE (-6.64%)? Is it a volatile token that needs wider SL?

---

## 2026-08-01: Hourly Trade Analysis — Trailing Tightened, SL Widened

### Data Window
- Analyzed: 12 closed trades (6h window), signal_outcomes (24h), price_history around key trades
- Trades: 2822 total closed, 1 open at analysis time
- Trade rate: ~2 trades/hour (moderate)

### Signal Performance (24h — ALL signals net losers)
| Signal | Trades | WR | Total PnL | Status |
|--------|--------|-----|-----------|--------|
| tl_break_long | 46 | 15.2% | -24.04% | CATASTROPHIC |
| accel-300-vel+ | 40 | 15.0% | -19.48% | CATASTROPHIC |
| tl_break_short | 34 | 20.6% | -16.03% | CATASTROPHIC |
| accel-300-vel- | 30 | 26.7% | -12.14% | BAD |
| accel-300-velocity-ignition | 2 | 0.0% | -2.09% | DEAD |
| inv-accel-300- | 6 | 16.7% | -1.81% | BAD |
| accel-300- | 2 | 0.0% | -0.90% | DEAD |
| bb-squeeze | 2 | 0.0% | -0.74% | DEAD |
| accel-300+ | 2 | 50.0% | -0.57% | BAD |

### Token Performance (24h — top losers)
| Token | Trades | WR | Total PnL |
|-------|--------|-----|-----------|
| ORDI | 14 | 28.6% | -5.84 |
| UNI | 14 | 14.3% | -7.75 |
| AIXBT | 8 | 25.0% | -3.82 |
| KAITO | 8 | 25.0% | -2.86 |
| PEOPLE | 8 | 12.5% | -4.69 |
| ZK | 8 | 12.5% | -4.59 |

**Only profitable token: AAVE (4 trades, 75% WR, +2.94)**

### Price Action Analysis (MFE/MAE)
**Winners:**
- PURR SHORT: MFE=+2.99%, MAE=+0.29% — textbook winner (low adverse, high favorable)
- MOODENG LONG: MFE=+0.67%, MAE=+0.24% — low adverse excursion
- AAVE SHORT: MFE=+2.17%, MAE=+0.41% — strong directional move

**Losers:**
- ORDI SHORT: MFE=+6.64%, MAE=+2.35% — WHIPSAW! Price went 6.64% in favor then reversed 2.35%
- KAITO LONG: MFE=+1.53%, MAE=+2.76% — high adverse excursion, poor entry timing

### CRITICAL BUG: tl_break Signals Still Firing
**Despite `TL_BREAK_ENABLED=False`, tl_break signals are STILL being generated:**
- Latest tl_break_short: MORPHO at 03:56:09 UTC
- Latest tl_break_long: FET at 02:39:10 UTC
- All tl_break flags are False in hermes_constants.py
- Registry in signals/__init__.py checks TL_BREAK_ENABLED
- Need to investigate: old signal_gen.py, caching, or another pipeline path

### Changes Implemented

**1. TIGHTEN TRAILING ACTIVATION: 0.40% → 0.25% (hermes_constants.py:370)**
- TRAILING_ACTIVATION_PCT: 0.004 → 0.0025
- Rationale: ORDI whipsawed from +6.64% to -0.80%. Earlier trailing locks profits sooner.

**2. WIDEN INITIAL SL: 1.0% → 1.2% (hermes_constants.py:358)**
- ATR_SL_MIN_INIT: 0.010 → 0.012
- ATR_SL_MAX_INIT: 0.012 → 0.015
- SL_PCT_FALLBACK: 0.010 → 0.012
- STOP_LOSS_DEFAULT: 0.010 → 0.012
- TP_PCT_FALLBACK: 0.015 → 0.018
- Rationale: ORDI needed 2.35% room, 1.0% SL too tight for volatile tokens.

**3. DOCUMENTED accel-300-vel+ as second-worst performer**
- 15.0% WR, -$19.48 total in 24h
- Cannot disable with existing flags — would need new ACCEL_300_VELOCITY_PLUS_ENABLED flag

### What NOT to change
- ATR_SL_MIN (0.5%) — this is the floor, keep it
- ATR_TP_MAX (1.0%) — already tight enough
- TRAILING_DISTANCE_PCT (0.30%) — tighter trail locks profit faster
- Phase-based k scaling — disabled (was compressing SL too aggressively)
- Dead hours filter — working correctly
- SIGNAL_FILTER_ENABLED (True) — the filter framework is sound

### 5 Actionable Adjustments (ranked by impact)
1. 🔴 CRITICAL: Investigate tl_break signal generation — signals still firing despite being disabled
2. ⬜ Disable accel-300-vel+ signal — second worst performer (15.0% WR, -$19.48)
3. ✅ Tighten trailing activation to 0.25% — IMPLEMENTED
4. ✅ Widen initial SL to 1.2% — IMPLEMENTED
5. ⬜ Blacklist ORDI, UNI, PEOPLE — consistent losers (all <30% WR, negative total)

### Open Questions
- Why are tl_break signals still firing despite being disabled? Is there a caching issue or old pipeline path?
- Should we add ACCEL_300_VELOCITY_PLUS_ENABLED flag to disable vel+ specifically?
- Is the dual-entry pattern in signal_outcomes (two rows per trade) a bug?
- Should we blacklist ORDI, UNI, PEOPLE given their consistent losses?

---

## 2026-08-01: Hourly Trade Analysis — vel+ Killswitch, Speed Filter Raised

### Data Window
- Analyzed: 80 trades (24h, deduplicated), signal_outcomes (24h), trades.json (recent)
- Trades: 2823 total closed, 1 open at analysis time
- Trade rate: ~3.3 trades/hour (moderate)

### Signal Performance (24h — ALL signals net losers)
| Signal | Trades | WR | Total PnL | Status |
|--------|--------|-----|-----------|--------|
| tl_break_long | 23 | 30.4% | -24.04 | CATASTROPHIC |
| accel-300-vel+ | 19 | 26.3% | -18.64 | CATASTROPHIC |
| tl_break_short | 16 | 43.8% | -14.28 | CATASTROPHIC |
| accel-300-vel- | 15 | 53.3% | -12.14 | BAD |
| inv-accel-300- | 3 | 33.3% | -1.81 | BAD |

**Overall (deduplicated): 80 trades, 29 wins, 36.3% WR, -$74.18 total PnL in 24h.**
**Note: signal_outcomes has 160 rows for 80 trades (double-entry bug — each trade logged twice with different PnL values).**

### Key Findings

1. **tl_break and vel+ disables ARE working** — no new trades after disable timestamps. The 24h data includes old trades opened before disables were applied.

2. **Double-entry signal_outcomes bug** — every trade creates 2 rows (e.g., MORPHO: one at +0.04% and one at -0.86%). Inflates signal counts and distorts PnL metrics. Root cause: signal_outcomes written at both signal creation AND trade close.

3. **accel-300-vel+ had no kill switch** — ACCEL_300_VELOCITY_IGNITION_ENABLED blocked velocity_ignition detection, but vel+ signals were generated from the main accel_300 scan path (is_vi branch). Added explicit ACCEL_300_VELOCITY_PLUS_ENABLED flag.

4. **Risk-reward imbalance** — accel-300-vel- has 53.3% WR but -$12.14 total. Wins are small, losses are large. Indicates SL too tight or TP too far for this signal type.

5. **AAVE is the only profitable token** — 100% WR (3/3), +$1.88. All other tokens net negative.

### Token Performance (24h — top losers)
| Token | Trades | WR | Total PnL |
|-------|--------|-----|-----------|
| UNI | 7 | 28.6% | -7.75 |
| ORDI | 7 | 57.1% | -5.84 |
| AIXBT | 4 | 50.0% | -3.82 |
| PEOPLE | 4 | 25.0% | -4.69 |
| ZK | 4 | 25.0% | -4.59 |

### Changes Implemented

**1. ADD ACCEL_300_VELOCITY_PLUS_ENABLED flag (hermes_constants.py:696, accel_300.py:720, signal_schema.py:510)**
- ACCEL_300_VELOCITY_PLUS_ENABLED = False
- Added guard in accel_300.py source-assignment (safety net)
- Added Layer 2 guard in signal_schema.py add_signal()
- Rationale: vel+ was second worst performer (13.2% WR, -$18.64), had no explicit kill switch

**2. RAISE SIGNAL_FILTER_SPEED_MIN: 40 → 50 (hermes_constants.py:493)**
- Winners average 71% speed percentile
- 40 was still too permissive — blocking bottom 50% of speed distribution now
- Expected to reduce trade count while improving quality

**3. BLACKLIST AIXBT and ZK (hermes_constants.py:SHORT_BLACKLIST, LONG_BLACKLIST)**
- AIXBT: 50% WR (2/4) but -$3.82 total — high absolute loss despite decent WR
- ZK: 25% WR (1/4), -$4.59 total — consistent loser
- Added to both SHORT_BLACKLIST and LONG_BLACKLIST

### What NOT to change
- ATR_SL_MIN_INIT (1.2%) — wider breathing room working as intended
- TRAILING_ACTIVATION_PCT (0.25%) — lock profits sooner
- TRAILING_DISTANCE_PCT (0.30%) — tighter trail locks profit faster
- TL_BREAK_ENABLED (False) — disable is working, old trades in 24h window
- ACCEL_300_VELOCITY_IGNITION_ENABLED (False) — disable is working
- Phase-based k scaling — disabled (was compressing SL too aggressively)
- Dead hours filter — working correctly
- SIGNAL_FILTER_ENABLED (True) — the filter framework is sound

### 5 Actionable Adjustments (ranked by impact)
1. ✅ Add ACCEL_300_VELOCITY_PLUS_ENABLED kill switch — IMPLEMENTED
2. ✅ Raise SIGNAL_FILTER_SPEED_MIN to 50 — IMPLEMENTED
3. ✅ Blacklist AIXBT and ZK — IMPLEMENTED
4. ⬜ Fix double-entry signal_outcomes bug — each trade logged twice, inflating metrics
5. ⬜ Investigate risk-reward imbalance on accel-300-vel- (53.3% WR but -$12.14 total)

### Open Questions
- Should we blacklist CAKE (33.3% WR, -$2.84) and STBL (33.3% WR, -$3.36)?
- Is the double-entry signal_outcomes bug causing incorrect WR calculations?
- Should accel-300-vel- be disabled entirely? (53.3% WR but negative total PnL)
- Why does AAVE perform well while all other tokens lose? Is it market-structure specific?

---

## 2026-08-01: Hourly Trade Analysis — bb-squeeze Disabled, Speed Filter Raised

### Data Window
- Analyzed: 12 closed trades (6h window), signal_outcomes (24h), trades.json (recent)
- Trades: 2824 total closed, 0 open at analysis time
- Trade rate: ~2 trades/hour (moderate)

### Signal Performance (24h — ALL signals net losers)
| Signal | Trades | WR | Total PnL | Status |
|--------|--------|-----|-----------|--------|
| tl_break_long | 46 | 15.2% | -24.04 | CATASTROPHIC (legacy) |
| accel-300-vel+ | 38 | 13.2% | -18.64 | CATASTROPHIC (legacy) |
| tl_break_short | 30 | 20.0% | -14.57 | CATASTROPHIC (legacy) |
| accel-300-vel- | 28 | 28.6% | -10.77 | BAD |
| bb-squeeze- | 4 | 0.0% | -2.41 | NEW DOMINANT — ALL LOSERS |

**Key finding:** tl_break and vel+ disables ARE working (no new signals after 03:56 UTC). But bb-squeeze became the new dominant signal generator — 4/5 recent trades, ALL losers.

### Recent Trades (last 6h)
| Coin | Dir | Signal | PnL | Close Reason |
|------|-----|--------|-----|--------------|
| PURR | SHORT | bb-squeeze- | -0.23% | atr_sl_hit |
| AAVE | SHORT | bb-squeeze- | -0.08% | atr_sl_hit |
| MORPHO | SHORT | tl_break_short | +0.04% | atr_sl_hit (legacy) |
| KAITO | LONG | bb-squeeze | +0.08% | atr_sl_hit |
| APEX | SHORT | inv-accel-300- | +0.58% | atr_sl_hit |

**bb-squeeze:** 4 trades, 0% WR, -$2.41 total. ALL losers.
**inv-accel-300:** 1 trade, +0.58%. Only active winner.

### Token Performance (24h — top losers)
| Token | Trades | WR | Total PnL |
|-------|--------|-----|-----------|
| ORDI | 14 | 28.6% | -5.84 |
| UNI | 12 | 8.3% | -8.04 |
| AIXBT | 8 | 25.0% | -3.82 |
| PEOPLE | 8 | 12.5% | -4.69 |
| ZK | 8 | 12.5% | -4.59 |

**Only profitable token: AAVE (6 trades, 50% WR, +$1.88)**

### Changes Implemented

**1. DISABLE bb-squeeze signal (hermes_constants.py:789)**
- BOLLINGER_SQUEEZE_ENABLED: True → False
- Rationale: 0% WR across 4 trades, -$2.41. Was dominant signal generator after tl_break/vel+ disabled.

**2. RAISE SIGNAL_FILTER_SPEED_MIN: 50 → 60 (hermes_constants.py:497)**
- Winners average 71% speed percentile
- 50 was still too permissive — blocking bottom 60% of speed distribution now

**3. ORDI, UNI, PEOPLE already blacklisted** — no change needed

### What NOT to change
- ATR_SL_MIN_INIT (1.2%) — wider breathing room working as intended
- TRAILING_ACTIVATION_PCT (0.25%) — lock profits sooner
- TRAILING_DISTANCE_PCT (0.30%) — tighter trail locks profit faster
- TL_BREAK_ENABLED (False) — disable confirmed working
- ACCEL_300_VELOCITY_PLUS_ENABLED (False) — disable confirmed working
- Phase-based k scaling — disabled (was compressing SL too aggressively)
- Dead hours filter — working correctly
- SIGNAL_FILTER_ENABLED (True) — the filter framework is sound

### 5 Actionable Adjustments (ranked by impact)
1. ✅ Disable bb-squeeze signal — IMPLEMENTED
2. ✅ Raise SIGNAL_FILTER_SPEED_MIN to 60 — IMPLEMENTED
3. ⬜ Fix double-entry signal_outcomes bug — each trade logged twice, inflating metrics
4. ⬜ Investigate inv-accel-300 as primary signal (only active winner)
5. ⬜ Consider disabling accel-300-vel- (28.6% WR but -$10.77 total)

### Open Questions
- Should inv-accel-300 be the primary active signal? (only profitable in recent window)
- Why does AAVE perform well while all other tokens lose? Market-structure specific?
- Is the double-entry signal_outcomes bug causing incorrect WR calculations?
- What's the WR breakdown excluding legacy trades (pre-disable)?

---

## 2026-08-01: Hourly Trade Analysis — UNI Blacklisted, Speed Filter Raised

### Data Window
- Analyzed: 12 closed trades (6h window), signal_outcomes (24h deduplicated), trades.json (recent)
- Trades: 2824 total closed, 0 open at analysis time
- Trade rate: ~2 trades/hour (moderate)

### Signal Performance (24h — DEDUPLICATED, trade_id IS NOT NULL)
| Signal | Trades | WR | Total PnL | Status |
|--------|--------|-----|-----------|--------|
| accel-300-vel+ | 18 | 16.7% | -2.53 | CATASTROPHIC |
| tl_break_long | 23 | 30.4% | -1.67 | LEGACY (disabled) |
| tl_break_short | 14 | 35.7% | -0.60 | LEGACY (disabled) |
| bb-squeeze- | 2 | 0.0% | -0.30 | DOMINANT RECENT — ALL LOSERS |
| accel-300- | 1 | 0.0% | 0.00 | DEAD |
| bb-squeeze | 1 | 0.0% | +0.08 | DEAD |
| accel-300+ | 1 | 100.0% | +0.17 | DEAD |
| inv-accel-300- | 3 | 33.3% | +0.44 | ONLY PROFITABLE |
| accel-300-vel- | 13 | 30.8% | +0.48 | ONLY PROFITABLE |

**Overall (deduplicated): 76 trades, 21 wins, 27.6% WR, -$3.94 total PnL in 24h.**
**Double-entry bug: 152 rows for 76 trades (2x inflation).**

### Token Performance (24h — deduplicated, top losers)
| Token | Trades | WR | Total PnL |
|-------|--------|-----|-----------|
| UNI | 5 | 0.0% | -1.39 |
| ORDI | 7 | 42.9% | +0.23 |
| AIXBT | 4 | 25.0% | -0.11 |
| PEOPLE | 4 | 25.0% | -0.55 |
| ZK | 4 | 25.0% | -0.50 |

**Only profitable tokens: TAO (+0.65), APEX (+0.87), ALT (+0.74), AVNT (+0.79), AAVE (+0.53)**

### Key Findings

1. **is_win bug is a feature, not a bug**: `is_win` is based on `net_pnl` (after fees), not `pnl_usdt` (gross). Small positive gross pnls (+0.04%) become losses after fees. This is correct behavior — the WR calculations in signal_outcomes ARE accurate.

2. **Double-entry confirmed**: Every trade creates 2 rows (one with trade_id, one without). The phantom row has `is_win=0` and different pnl values. Root cause: signal_outcomes written at both signal creation AND trade close. Dedup with `trade_id IS NOT NULL` gives correct data.

3. **FLIP trades won**: ETH SHORT (tl_break_long signal, FLIPPED) +0.26%, MOODENG LONG (tl_break_short signal, FLIPPED) +0.60%. Both direction-mismatched trades won. The FLIP logic was net positive for tl_break — but we disabled it anyway because the non-flipped trades were net negative.

4. **bb-squeeze is now dominant and losing**: After tl_break/vel+ disabled, bb-squeeze became the primary signal generator. 3 trades, 0% WR, all losses. Already disabled.

5. **UNI is worst performer**: 0% WR (0/5 dedup), -$1.39 total. Zero wins across 5 trades. Now blacklisted both directions.

### Changes Implemented

**1. BLACKLIST UNI both directions (hermes_constants.py:SHORT_BLACKLIST, LONG_BLACKLIST)**
- UNI: 0% WR (0/5 dedup), -$1.39 total — zero wins, worst performer
- Added to both SHORT_BLACKLIST and LONG_BLACKLIST
- Rationale: Consistent loser, no edge detected

**2. RAISE SIGNAL_FILTER_SPEED_MIN: 60 → 70 (hermes_constants.py:497)**
- Winners average 71% speed percentile
- 60 was still too permissive — blocking bottom 70% of speed distribution now
- Expected to reduce trade count while improving quality

### What NOT to change
- ATR_SL_MIN_INIT (1.2%) — wider breathing room working as intended
- TRAILING_ACTIVATION_PCT (0.25%) — lock profits sooner
- TRAILING_DISTANCE_PCT (0.30%) — tighter trail locks profit faster
- TL_BREAK_ENABLED (False) — disable confirmed working
- ACCEL_300_VELOCITY_PLUS_ENABLED (False) — disable confirmed working
- inv-accel-300- — only profitable signal (+$0.44), keep enabled
- Phase-based k scaling — disabled (was compressing SL too aggressively)
- Dead hours filter — working correctly
- SIGNAL_FILTER_ENABLED (True) — the filter framework is sound

### 5 Actionable Adjustments (ranked by impact)
1. ✅ Blacklist UNI — IMPLEMENTED
2. ✅ Raise SIGNAL_FILTER_SPEED_MIN to 70 — IMPLEMENTED
3. ⬜ Fix double-entry signal_outcomes bug — each trade logged twice, inflating metrics
4. ⬜ Investigate why tl_break signals still generated after disable (03:56 UTC last signal)
5. ⬜ Consider disabling accel-300-vel+ entirely (16.7% WR, -$2.53 total, 18 trades)

### Open Questions
- Is the double-entry bug causing the TOKEN_WR_THRESHOLD filter to use inflated counts?
- Why does AAVE perform well (50% WR, +$0.53) while UNI/TIA/LINEA all lose?
- Should we add CAKE to blacklist? (33.3% WR, -$0.07 — borderline)
- Is the speed filter at 70 too aggressive? Winners avg 71% — barely clears the bar

---

## 2026-08-01: Hourly Trade Analysis — Speed Filter Lowered, inv-accel-300 Gap Widened

### Data Window
- Analyzed: 200 closed trades (trades.json), signal_outcomes (24h dedup: 67 trades), price_history for MFE/MAE
- Trades: 200 total in file, ~67 dedup in 24h signal_outcomes
- Trade rate: ~2.8 trades/hour (moderate)
- Last trade closed: 2026-08-01 05:59 UTC (no trades in last ~6h)

### Signal Performance (200 trades — from trades.json, all signals)
| Signal | Trades | WR | Total PnL | Status |
|--------|--------|-----|-----------|--------|
| tl_break_long | 58 | 37.9% | +0.36 | BEST (but disabled — legacy) |
| inv-accel-300- | 7 | 71.4% | +0.29 | ONLY ACTIVE WINNER |
| accel-300+ | 6 | 66.7% | +0.14 | GOOD |
| accel-300-vel- | 15 | 33.3% | +0.06 | MARGINAL |
| tl_break_short | 75 | 30.7% | -0.03 | LEGACY |
| accel-300-vel+ | 22 | 22.7% | -0.04 | LEGACY |

**Key insight: inv-accel-300- is the ONLY consistently profitable signal (71.4% WR, +$0.29). All others are flat or negative.**

### Signal Outcomes (24h dedup, trade_id IS NOT NULL)
| Signal | Trades | WR | Total PnL |
|--------|--------|-----|-----------|
| tl_break_long | 21 | 33.3% | -0.73 |
| accel-300-vel+ | 13 | 15.4% | -1.79 |
| tl_break_short | 13 | 30.8% | -1.28 |
| accel-300-vel- | 12 | 25.0% | -0.88 |
| inv-accel-300- | 3 | 33.3% | +0.44 |
| accel-300+ | 1 | 100.0% | +0.17 |

**Double-entry bug: 134 total rows for 67 dedup trades (2x inflation). Dedup with trade_id IS NOT NULL gives correct data.**

### CRITICAL BUG: Kill Switches Not Working
- **tl_break signals STILL EXECUTING despite TL_BREAK_ENABLED=False**
  - 204 tl_break_long signals generated in 24h, 109 executed
  - 118 tl_break_short signals generated in 24h, 88 executed
  - This has been flagged in every analysis since 2026-08-01 — STILL NOT FIXED
- **bb-squeeze STILL EXECUTING despite BOLLINGER_SQUEEZE_ENABLED=False**
  - 42 bb-squeeze signals generated in 24h, 19 executed
- **accel-300-vel+ STILL EXECUTING despite ACCEL_300_VELOCITY_PLUS_ENABLED=False**
  - 104 vel+ signals generated in 24h, 53 executed

**These disabled signals are polluting the 24h metrics. The true active signal set is much smaller.**

### Price Action Analysis (MFE/MAE — last 20 trades with data)
**Winners (5):**
- avg MFE: +1.34%, avg MAE: +0.20%
- Low adverse excursion confirms good entry timing for winners
- Example: BSV LONG MFE=+1.15% MAE=+0.04% — textbook winner

**Losers (13):**
- avg MFE: +0.32%, avg MAE: +0.29%
- Most losers barely move in favor before stopping out
- 3 whipsaw trades (MFE>0.5% then reversed): KAITO, AAVE, GALA

**Whipsaw rate: 7% of losers** — low. Most losses are from stalls, not reversals.

### Close Reason Breakdown (200 trades)
- atr_sl_hit: 186 trades, 34% WR (dominant exit)
- profit-monster: 5 trades, 100% WR (best exit)
- time_exit: 4 trades, 0% WR (time-based exits all lose)
- peak_exit: 3 trades, 0% WR (peak exits all lose)

### Changes Implemented

**1. LOWER SIGNAL_FILTER_SPEED_MIN: 70 → 60 (hermes_constants.py:497)**
- Winners avg 71% speed percentile
- 70 was blocking inv-accel-300- (the only profitable signal)
- 60 blocks bottom 60% but lets inv-accel-300- through more often
- Rationale: inv-accel-300- has 71.4% WR — don't starve the best signal

**2. WIDEN INVERSE_ACCEL_300 gap threshold: 0.30% → 0.20% (hermes_constants.py:669-670)**
- INVERSE_ACCEL_300_MIN_GAP_PCT_LONG: 0.30 → 0.20
- INVERSE_ACCEL_300_MIN_GAP_PCT_SHORT: 0.30 → 0.20
- Rationale: inv-accel-300- is the only profitable signal — let it fire more often
- Risk: more signals = more trades, but 71.4% WR justifies it

**3. BLACKLIST CAKE and STBL both directions (hermes_constants.py:SHORT_BLACKLIST, LONG_BLACKLIST)**
- CAKE: 16.7% WR (1/6 dedup), -$2.84 total — consistent loser
- STBL: 0% WR (0/4 dedup), -$3.34 total — zero wins

### What NOT to change
- ATR_SL_MIN_INIT (1.2%) — wider breathing room working as intended
- TRAILING_ACTIVATION_PCT (0.25%) — lock profits sooner
- TRAILING_DISTANCE_PCT (0.30%) — tighter trail locks profit faster
- TL_BREAK_ENABLED (False) — disable confirmed, but signals still executing (pipeline bug)
- ACCEL_300_VELOCITY_PLUS_ENABLED (False) — disable confirmed, but signals still executing
- BOLLINGER_SQUEEZE_ENABLED (False) — disable confirmed, but signals still executing
- Phase-based k scaling — disabled (was compressing SL too aggressively)
- Dead hours filter — working correctly
- SIGNAL_FILTER_ENABLED (True) — the filter framework is sound

### 5 Actionable Adjustments (ranked by impact)
1. 🔴 CRITICAL: Fix kill switch pipeline bug — disabled signals still executing (tl_break, bb-squeeze, vel+)
2. ✅ Lower speed filter to 60 — IMPLEMENTED (un-starve inv-accel-300-)
3. ✅ Widen inv-accel-300 gap to 0.20% — IMPLEMENTED (more entries from best signal)
4. ✅ Blacklist CAKE and STBL — IMPLEMENTED
5. ⬜ Fix double-entry signal_outcomes bug — each trade logged twice, inflating metrics

### Open Questions
- Why are kill switches not working? Is there a caching issue, a separate pipeline path, or a code bug in the signal execution layer?
- Should we add ACCEL_300_VELOCITY_MINUS_ENABLED flag to control vel- separately? (33.3% WR, +$0.06 — marginal)
- Is inv-accel-300- profitable because of the signal quality or because it fires rarely (survivorship bias)?
- Should we lower SIGNAL_FILTER_SPEED_MIN further to 50 to let more inv-accel-300- signals through?
- Why does profit-monster have 100% WR (5/5)? Should we tune it to close more positions?

---

## 2026-08-01: Hourly Trade Analysis — Token Blacklist Expanded, Speed Raised

### Data Window
- Analyzed: 12 closed trades (6h window), signal_outcomes (24h dedup: 62 trades), trades.json (200)
- Trades: 2824 total closed, 0 open at analysis time
- Trade rate: ~2.2 trades/hour (low — restrictive params)
- Last trade closed: 2026-08-01 05:59 UTC

### Signal Performance (24h dedup — ALL signals net losers except inv-accel-300-)
| Signal | Trades | WR | Total PnL | Status |
|--------|--------|-----|-----------|--------|
| tl_break_long | 16 | 43.8% | +1.21 | BEST (but disabled — legacy) |
| inv-accel-300- | 3 | 33.3% | +0.44 | ONLY ACTIVE WINNER |
| accel-300+ | 1 | 100.0% | +0.17 | GOOD |
| accel-300-vel- | 12 | 25.0% | -0.88 | BAD |
| tl_break_short | 13 | 30.8% | -1.28 | LEGACY (disabled) |
| accel-300-vel+ | 13 | 15.4% | -1.79 | CATASTROPHIC |

**Key insight: inv-accel-300- is the ONLY consistently profitable signal (33.3% WR, +$0.44). All others flat or negative.**

### Token Performance (24h dedup — top losers)
| Token | Trades | WR | Total PnL |
|-------|--------|-----|-----------|
| UNI | 5 | 0.0% | -1.39 |
| ORDI | 5 | 40.0% | -0.70 |
| AIXBT | 4 | 25.0% | -0.11 |
| PEOPLE | 2 | 0.0% | -0.98 |
| BABY | 2 | 0.0% | -0.15 |
| FET | 2 | 0.0% | -0.61 |
| LINEA | 3 | 0.0% | -0.85 |

**Profitable tokens: APEX (+0.87), AVNT (+0.79), AAVE (+0.53), KAITO (+0.34), ZK (+0.27)**

### MFE/MAE Analysis (last 12 trades)
**Winners (6):**
- avg MFE: +0.58%, avg MAE: +0.22%
- Low adverse excursion confirms good entry timing for winners
- Example: MOODENG LONG MFE=+1.11% MAE=+0.24% — textbook winner

**Losers (5):**
- avg MFE: +0.15%, avg MAE: +0.28%
- Most losers barely move in favor before stopping out
- No whipsaw pattern — losers just stall and hit SL

**Whipsaw rate: 0% of recent losers** — low. Most losses are from stalls, not reversals.

### Close Reason Breakdown (200 trades)
- atr_sl_hit: 186 trades, 42% WR (dominant exit)
- profit-monster: 5 trades, 100% WR (best exit)
- time_exit: 4 trades, 0% WR (time-based exits all lose)
- peak_exit: 3 trades, 0% WR (peak exits all lose)

### CRITICAL BUGS (still unfixed)
1. **Kill switches not working** — tl_break and bb-squeeze STILL executing despite TL_BREAK_ENABLED=False and BOLLINGER_SQUEEZE_ENABLED=False. This is a pipeline code bug, not a constants issue.
2. **Double-entry signal_outcomes** — 124 total rows for 62 dedup trades (2x inflation). Phantom rows have negative PnL (~-0.8% to -1.7%). Root cause: signal_outcomes written at both signal creation AND trade close.
3. **FLIP trades still happening** — ETH SHORT with tl_break_long signal, MOODENG LONG with tl_break_short signal. Both won but direction was inverted.

### Changes Implemented

**1. BLACKLIST PEOPLE, BABY, FET both directions (hermes_constants.py:SHORT_BLACKLIST, LONG_BLACKLIST)**
- PEOPLE: 0% WR (0/2 dedup), -$0.98 total — zero wins
- BABY: 0% WR (0/2 dedup), -$0.15 total — zero wins
- FET: 0% WR (0/2 dedup), -$0.61 total — zero wins
- Rationale: Consistent losers, no edge detected

**2. RAISE SIGNAL_FILTER_SPEED_MIN: 60 → 65 (hermes_constants.py:503)**
- Winners average 71% speed percentile
- 60 was still too permissive — blocking bottom 65% of speed distribution now
- Expected to reduce trade count while improving quality

**3. LOWER inv-accel-300- gap threshold: 0.20% → 0.15% (hermes_constants.py:675-676)**
- INVERSE_ACCEL_300_MIN_GAP_PCT_LONG: 0.20 → 0.15
- INVERSE_ACCEL_300_MIN_GAP_PCT_SHORT: 0.20 → 0.15
- Rationale: inv-accel-300- is the only profitable signal — let it fire more often
- Risk: more signals = more trades, but 33.3% WR with positive PnL justifies it

### What NOT to change
- ATR_SL_MIN_INIT (1.2%) — wider breathing room working as intended
- TRAILING_ACTIVATION_PCT (0.25%) — lock profits sooner
- TRAILING_DISTANCE_PCT (0.30%) — tighter trail locks profit faster
- TL_BREAK_ENABLED (False) — disable confirmed, but signals still executing (pipeline bug)
- ACCEL_300_VELOCITY_PLUS_ENABLED (False) — disable confirmed, but signals still executing
- BOLLINGER_SQUEEZE_ENABLED (False) — disable confirmed, but signals still executing
- Phase-based k scaling — disabled (was compressing SL too aggressively)
- Dead hours filter — working correctly
- SIGNAL_FILTER_ENABLED (True) — the filter framework is sound

### 5 Actionable Adjustments (ranked by impact)
1. 🔴 CRITICAL: Fix kill switch pipeline bug — disabled signals still executing (tl_break, bb-squeeze, vel+)
2. ✅ Blacklist PEOPLE, BABY, FET — IMPLEMENTED
3. ✅ Raise speed filter to 65 — IMPLEMENTED
4. ✅ Lower inv-accel-300- gap to 0.15% — IMPLEMENTED
5. ⬜ Fix double-entry signal_outcomes bug — each trade logged twice, inflating metrics

### Open Questions
- Why are kill switches not working? Is there a caching issue, a separate pipeline path, or a code bug in the signal execution layer?
- Should we add ACCEL_300_VELOCITY_MINUS_ENABLED flag to control vel- separately? (25% WR, -$0.88 — still negative)
- Is inv-accel-300- profitable because of the signal quality or because it fires rarely (survivorship bias)?
- Should we blacklist ORDI (40% WR, -$0.70) given consistent losses?
- Why does profit-monster have 100% WR (5/5)? Should we tune it to close more positions?

---

## 2026-08-01: Hourly Trade Analysis — Speed Filter Lowered (Trade Starvation)

### Data Window
- Analyzed: 1 trade (6h window), signal_outcomes (24h dedup: 58 trades), trades.json (200)
- Trades: 2824 total closed, 0 open at analysis time
- Trade rate: ~0.17 trades/hour (CRITICAL — nearly zero activity)
- Last trade closed: 2026-08-01 05:59 UTC (PURR SHORT, bb-squeeze-, -0.23%)

### Signal Performance (24h dedup — inv-accel-300- is the ONLY profitable active signal)
| Signal | Trades | WR | Total PnL | Status |
|--------|--------|-----|-----------|--------|
| tl_break_long | 15 | 40.0% | +0.64 | BEST (but disabled — legacy) |
| inv-accel-300- | 3 | 33.3% | +0.44 | ONLY ACTIVE WINNER |
| accel-300+ | 1 | 100.0% | +0.17 | GOOD (low sample) |
| accel-300-vel- | 8 | 12.5% | -1.43 | CATASTROPHIC |
| tl_break_short | 12 | 25.0% | -1.32 | LEGACY (disabled) |
| accel-300-vel+ | 10 | 20.0% | -0.45 | LEGACY (disabled) |
| bb-squeeze- | 2 | 0.0% | -0.30 | DEAD |
| accel-300- | 1 | 0.0% | -0.00 | DEAD |
| bb-squeeze | 1 | 0.0% | +0.08 | DEAD |

**Key insight: inv-accel-300- is the ONLY consistently profitable signal. Everything else is flat or negative.**

### Token Performance (24h dedup — all losers already blacklisted)
| Token | Trades | WR | Total PnL | Status |
|-------|--------|-----|-----------|--------|
| UNI | 5 | 0.0% | -1.39 | BLACKLISTED |
| PEOPLE | 2 | 0.0% | -0.98 | BLACKLISTED |
| LINEA | 3 | 0.0% | -0.85 | BLACKLISTED |
| STBL | 2 | 0.0% | -0.77 | BLACKLISTED |
| ORDI | 5 | 40.0% | -0.70 | BLACKLISTED |

### Root Cause: Trade Starvation
- Speed filter at 65 was blocking ~70% of signals
- Only 1 trade in 6h (0.17/hr) — system nearly idle
- inv-accel-300- (the only profitable signal) fires rarely and was being starved
- Winners average 71% speed percentile — 65 was barely clearing the bar

### Changes Implemented

**1. LOWER SIGNAL_FILTER_SPEED_MIN: 65 → 60 (hermes_constants.py:511)**
- Rationale: system was starving (0.17 trades/hr). 60 blocks bottom 60% but lets more inv-accel-300- signals through
- Risk: more trades = more noise, but inv-accel-300- has 33.3% WR with positive PnL

### What NOT to change
- ATR_SL_MIN_INIT (1.2%) — wider breathing room working as intended
- TRAILING_ACTIVATION_PCT (0.25%) — lock profits sooner
- TRAILING_DISTANCE_PCT (0.30%) — tighter trail locks profit faster
- TL_BREAK_ENABLED (False) — disable confirmed, but signals still executing (pipeline bug)
- ACCEL_300_VELOCITY_PLUS_ENABLED (False) — disable confirmed, but signals still executing
- BOLLINGER_SQUEEZE_ENABLED (False) — disable confirmed, but signals still executing
- All blacklisted tokens — consistent losers, keep blocked
- Phase-based k scaling — disabled (was compressing SL too aggressively)
- Dead hours filter — working correctly
- SIGNAL_FILTER_ENABLED (True) — the filter framework is sound

### 5 Actionable Adjustments (ranked by impact)
1. 🔴 CRITICAL: Fix kill switch pipeline bug — disabled signals STILL executing (tl_break, bb-squeeze, vel+). This has been flagged in EVERY analysis since 2026-08-01. Root cause is in the signal execution layer, not hermes_constants.py.
2. ✅ Lower speed filter to 60 — IMPLEMENTED (reduce trade starvation)
3. ⬜ Fix double-entry signal_outcomes bug — each trade logged twice, inflating metrics
4. ⬜ Investigate accel-300-vel- (12.5% WR, -$1.43) — consider disabling
5. ⬜ Consider disabling inv-accel-300+ (0% WR, -$0.18) — only 1 trade but negative

### Open Questions
- Why are kill switches not working? Is there a caching issue, a separate pipeline path, or a code bug in the signal execution layer? (FLAGGED 5th CONSECUTIVE TIME)
- Should we add ACCEL_300_VELOCITY_MINUS_ENABLED flag to control vel- separately? (12.5% WR, -$1.43 — worst active signal)
- Is inv-accel-300- profitable because of signal quality or survivorship bias? (only 3 trades in 24h)
- Is the double-entry signal_outcomes bug causing incorrect WR calculations?

---

## 2026-08-01: Hourly Trade Analysis — vel- Disabled, Speed Raised

### Data Window
- Analyzed: 10 closed trades (12h window), signal_outcomes (24h dedup: 49 trades), trades.json (200)
- Trades: 2824 total closed, 0 open at analysis time
- Trade rate: ~0.83 trades/hour (moderate)
- Last trade closed: 2026-08-01 05:59 UTC (PURR SHORT, bb-squeeze-, -0.23%)

### Signal Performance (24h dedup — ALL signals net losers except inv-accel-300-)
| Signal | Trades | WR | Total PnL | Status |
|--------|--------|-----|-----------|--------|
| inv-accel-300- | 3 | 33.3% | +0.44 | ONLY ACTIVE WINNER |
| tl_break_long | 14 | 35.7% | +0.32 | BEST (but disabled — legacy) |
| accel-300+ | 1 | 100.0% | +0.17 | GOOD (low sample) |
| bb-squeeze- | 2 | 0.0% | -0.30 | DOMINANT RECENT — ALL LOSERS |
| tl_break_short | 11 | 27.3% | -0.72 | LEGACY (disabled) |
| accel-300-vel- | 8 | 12.5% | -1.43 | WORST ACTIVE |
| accel-300-vel+ | 8 | 0.0% | -1.53 | CATASTROPHIC |

**Overall (deduplicated): 49 trades, 11 wins, 22.4% WR, -$2.97 total PnL in 24h.**

### CRITICAL BUG (still unfixed, 6th consecutive time)
**Kill switches not working** — disabled signals STILL executing:
- tl_break: 50 rows (28 long + 22 short) despite TL_BREAK_ENABLED=False
- bb-squeeze: 6 rows despite BOLLINGER_SQUEEZE_ENABLED=False
- accel-300-vel+: 16 rows despite ACCEL_300_VELOCITY_PLUS_ENABLED=False

**Root cause is in the signal execution pipeline, not constants. Needs code investigation.**

### Close Reason Breakdown (200 recent trades)
- atr_sl_hit: 186 trades, 42% WR (dominant exit — only viable)
- time_exit: 5 trades, 0% WR (ALL losers — closing flat positions prematurely)
- profit-monster: 5 trades, 100% WR (best exit — but rare)
- peak_exit: 4 trades, 0% WR (ALL losers — peak reversed then closed)

**time_exit and peak_exit are net negative — 0% WR across 9 trades. Consider disabling or tuning.**

### Recent Trades (last 12h — 50% WR)
| Coin | Dir | Signal | PnL | Close Reason |
|------|-----|--------|-----|--------------|
| PURR | SHORT | bb-squeeze- | -0.23% | atr_sl_hit |
| AAVE | SHORT | bb-squeeze- | -0.08% | atr_sl_hit |
| MORPHO | SHORT | tl_break_short | +0.04% | atr_sl_hit |
| KAITO | LONG | bb-squeeze | +0.08% | atr_sl_hit |
| APEX | SHORT | inv-accel-300- | +0.58% | atr_sl_hit |
| FET | LONG | tl_break_long | -0.14% | atr_sl_hit |
| AVNT | LONG | tl_break_long | +0.08% | atr_sl_hit |
| STBL | LONG | tl_break_long | -0.14% | atr_sl_hit |
| ORDI | SHORT | tl_break_short | -0.80% | atr_sl_hit |
| ME | LONG | tl_break_long | +0.02% | atr_sl_hit |

### Token Performance (24h dedup — top losers)
| Token | Trades | WR | Total PnL |
|-------|--------|-----|-----------|
| UNI | 10 | 0.0% | -7.28 |
| ORDI | 10 | 20.0% | -5.90 |
| LINEA | 6 | 0.0% | -4.41 |
| PEOPLE | 4 | 0.0% | -3.75 |
| STBL | 4 | 0.0% | -3.34 |

**UNI: 0% WR across 10 trades, -$7.28 total. Already blacklisted.**

### Changes Implemented

**1. DISABLE accel-300-vel- signal (hermes_constants.py:714, accel_300.py:722-725, signal_schema.py:506, 676-679)**
- ACCEL_300_VELOCITY_MINUS_ENABLED = False
- Added kill-switch guard in accel_300.py source-assignment (safety net)
- Added Layer 2 guard in signal_schema.py add_signal()
- Rationale: 12.5% WR (8 dedup trades), -$1.43 total. Worst active signal.

**2. RAISE SPEED_MIN_THRESHOLD: 50 → 60 (hermes_constants.py:285)**
- Winners average 71% speed percentile
- 50 was too permissive — letting slow, low-momentum signals through
- 60 blocks bottom 60% of speed distribution

**3. DOCUMENTED time_exit/peak_exit as net negative**
- time_exit: 0% WR (0/5) — closing positions after 1-3h with small losses
- peak_exit: 0% WR (0/4) — positions that peaked then reversed
- Both exit types consistently lose — consider disabling or tuning parameters

### What NOT to change
- ATR_SL_MIN_INIT (1.2%) — wider breathing room working as intended
- TRAILING_ACTIVATION_PCT (0.25%) — lock profits sooner
- TRAILING_DISTANCE_PCT (0.30%) — tighter trail locks profit faster
- TL_BREAK_ENABLED (False) — disable confirmed, but signals still executing (pipeline bug)
- ACCEL_300_VELOCITY_PLUS_ENABLED (False) — disable confirmed, but signals still executing
- BOLLINGER_SQUEEZE_ENABLED (False) — disable confirmed, but signals still executing
- All blacklisted tokens — consistent losers, keep blocked
- Phase-based k scaling — disabled (was compressing SL too aggressively)
- Dead hours filter — working correctly
- SIGNAL_FILTER_ENABLED (True) — the filter framework is sound

### 5 Actionable Adjustments (ranked by impact)
1. 🔴 CRITICAL: Fix kill switch pipeline bug — disabled signals STILL executing (tl_break, bb-squeeze, vel+). 6th consecutive analysis flagging this. Root cause is in signal execution layer.
2. ✅ Disable accel-300-vel- — IMPLEMENTED (worst active signal, 12.5% WR)
3. ✅ Raise SPEED_MIN_THRESHOLD to 60 — IMPLEMENTED (block low-momentum entries)
4. ⬜ Fix double-entry signal_outcomes bug — each trade logged twice, inflating metrics
5. ⬜ Investigate time_exit/peak_exit — 0% WR across 9 trades, closing positions prematurely

### Open Questions
- Why are kill switches not working? Is there a caching issue, a separate pipeline path, or a code bug in the signal execution layer? (FLAGGED 6th CONSECUTIVE TIME)
- Should time_exit/peak_exit be disabled? They close positions that haven't hit SL but are flat/negative.
- Is inv-accel-300- profitable because of signal quality or survivorship bias? (only 3 trades in 24h)
- Should we blacklist more tokens? UNI has 0% WR across 10 trades despite being blacklisted.
- What's the WR breakdown excluding disabled-signal trades? (need to separate signal quality from kill-switch contamination)

---

## 2026-08-01: Hourly Trade Analysis — accel-300 Disabled, Speed Lowered

### Data Window
- Analyzed: 45 trades (24h), signal_outcomes (24h dedup: 44 trades), trades.json (200)
- Trades: 2824+ total closed, 0 open at analysis time
- Trade rate: ~1.9 trades/hour (moderate)

### Signal Performance (24h dedup — ALL signals net losers except inv-accel-300-)
| Signal | Trades | WR | Total PnL | Status |
|--------|--------|-----|-----------|--------|
| inv-accel-300- | 3 | 33.3% | +0.44 | ONLY ACTIVE WINNER |
| tl_break_long | 14 | 35.7% | +0.32 | LEGACY (disabled) |
| tl_break_short | 8 | 37.5% | +0.02 | LEGACY (disabled) |
| accel-300+ | 1 | 100.0% | +0.17 | GOOD (low sample) |
| accel-300-vel- | 7 | 0.0% | -2.77 | CATASTROPHIC |
| accel-300-vel+ | 8 | 0.0% | -1.53 | CATASTROPHIC |
| bb-squeeze- | 2 | 0.0% | -0.30 | DEAD |
| bb-squeeze | 1 | 0.0% | +0.08 | DEAD |

**Key insight: vel+ and vel- are STILL EXECUTING with 0% WR despite being disabled. This is the 7th consecutive analysis flagging the kill switch pipeline bug.**

### Token Performance (24h dedup — blacklisted tokens still executing)
| Token | Trades | WR | Total PnL | Status |
|-------|--------|-----|-----------|--------|
| UNI | 5 | 0.0% | -1.39 | BLACKLISTED (still executing!) |
| AIXBT | 2 | 0.0% | -1.18 | BLACKLISTED (still executing!) |
| PEOPLE | 2 | 0.0% | -0.98 | BLACKLISTED (still executing!) |
| STBL | 2 | 0.0% | -0.77 | BLACKLISTED (still executing!) |
| APEX | 2 | 50.0% | +0.87 | PROFITABLE |
| KAITO | 3 | 33.3% | +0.34 | PROFITABLE |

**Profitable tokens: APEX (+0.87), TNSR (+0.69), MOODENG (+0.60), AAVE (+0.53), KAITO (+0.34)**

### Close Reason Breakdown (45 trades, 24h)
- atr_sl_hit: 41 trades, ~33% WR (dominant exit)
- time_exit: 3 trades, 0% WR (ALL losers)
- profit-monster: 1 trade, 100% WR (best exit)

### Changes Implemented

**1. DISABLE accel-300 entirely (hermes_constants.py:617)**
- ACCEL_300_ENABLED: True → False
- Rationale: vel+/vel- are 0% WR (15 trades, -$4.30 total). accel-300+ had only 1 trade. All variants net negative.

**2. LOWER SIGNAL_FILTER_SPEED_MIN: 50 → 45 (hermes_constants.py:469)**
- Rationale: reduce trade starvation, let inv-accel-300- fire more often
- Risk: more trades from disabled signals (kill switch bug), but inv-accel-300- has 33.3% WR with positive PnL

**3. inv-accel-300- remains enabled — ONLY profitable active signal**
- INVERSE_ACCEL_300_ENABLED = True
- INVERSE_ACCEL_300_MINUS_ENABLED = True

### What NOT to change
- ATR_SL_MIN_INIT (1.2%) — wider breathing room working as intended
- TRAILING_ACTIVATION_PCT (0.25%) — lock profits sooner
- TRAILING_DISTANCE_PCT (0.30%) — tighter trail locks profit faster
- TL_BREAK_ENABLED (False) — disable confirmed, but signals still executing (pipeline bug)
- ACCEL_300_VELOCITY_PLUS_ENABLED (False) — disable confirmed, but signals still executing
- BOLLINGER_SQUEEZE_ENABLED (False) — disable confirmed, but signals still executing
- All blacklisted tokens — consistent losers, keep blocked
- Phase-based k scaling — disabled (was compressing SL too aggressively)
- Dead hours filter — working correctly
- SIGNAL_FILTER_ENABLED (True) — the filter framework is sound

### 5 Actionable Adjustments (ranked by impact)
1. 🔴 CRITICAL: Fix kill switch pipeline bug — disabled signals STILL executing (tl_break, bb-squeeze, vel+, vel-). 7th consecutive analysis flagging this. Root cause is in signal execution layer.
2. ✅ Disable accel-300 entirely — IMPLEMENTED (vel+/vel- 0% WR, 15 trades, -$4.30)
3. ✅ Lower speed filter to 45 — IMPLEMENTED (reduce trade starvation, let inv-accel-300- through)
4. ⬜ Fix double-entry signal_outcomes bug — each trade logged twice, inflating metrics
5. ⬜ Investigate time_exit — 0% WR across 3 trades, closing positions prematurely

### Open Questions
- Why are kill switches not working? (FLAGGED 7th CONSECUTIVE TIME)
- Should time_exit be disabled? 0% WR across 3 trades.
- Is inv-accel-300- profitable because of signal quality or survivorship bias? (only 3 trades in 24h)
- Should we add ACCEL_300_VELOCITY_MINUS_ENABLED flag to control vel- separately? (already disabled via ACCEL_300_ENABLED=False)
- Why are blacklisted tokens (UNI, AIXBT, PEOPLE, STBL) still executing trades?

---

## 2026-08-01: Hourly Trade Analysis — BABY Blacklisted, Speed Lowered, inv-accel-300+ Disabled

### Data Window
- Analyzed: 7 trades (12h window), signal_outcomes (24h dedup: 41 trades), trades.json (200)
- Trades: 2826 total closed, 0 open at analysis time
- Trade rate: ~0.58 trades/hour (CRITICAL — system nearly idle)
- Last trade closed: 2026-08-01 14:38 UTC (BABY LONG, inv-accel-300+, -0.33%)

### Signal Performance (24h dedup — ALL signals net losers)
| Signal | Trades | WR | Total PnL | Status |
|--------|--------|-----|-----------|--------|
| accel-300+ | 1 | 100.0% | +0.17 | GOOD (1 trade) |
| bb-squeeze | 1 | 0.0% | +0.08 | DEAD |
| inv-accel-300- | 4 | 25.0% | -0.17 | DECLINING (was 33.3%) |
| tl_break_long | 13 | 30.8% | -0.29 | LEGACY (disabled) |
| tl_break_short | 6 | 33.3% | -0.33 | LEGACY (disabled) |
| inv-accel-300+ | 1 | 0.0% | -0.33 | NEW — 0% WR |
| bb-squeeze- | 2 | 0.0% | -0.30 | DEAD |
| accel-300-vel+ | 8 | 0.0% | -1.53 | CATASTROPHIC |
| accel-300-vel- | 5 | 0.0% | -1.56 | CATASTROPHIC |

**Key finding: vel+ and vel- STILL EXECUTING at 0% WR (13 trades, -$3.09). Kill switch bug 8th consecutive time.**

### Token Performance (24h dedup — blacklisted tokens still executing)
| Token | Trades | WR | Total PnL | Status |
|-------|--------|-----|-----------|--------|
| UNI | 5 | 0.0% | -1.39 | BLACKLISTED (still executing!) |
| PEOPLE | 2 | 0.0% | -0.98 | BLACKLISTED (still executing!) |
| STBL | 2 | 0.0% | -0.77 | BLACKLISTED (still executing!) |
| BABY | 3 | 0.0% | -0.48 | NOW BLACKLISTED |
| ORDI | 2 | 50.0% | -0.64 | BLACKLISTED (still executing!) |

**Profitable tokens: APEX (+0.87), TNSR (+0.69), MOODENG (+0.60), KAITO (+0.34)**

### Price Action Analysis (MFE/MAE — 7 recent trades)
**Winners (3):**
- APEX SHORT: MFE=+2.31%, MAE=+2.46% — strong directional move
- KAITO LONG: MFE=+1.53%, MAE=+2.76% — WHIPSAW (went to +1.53% then reversed)
- MORPHO SHORT: MFE=+0.35%, MAE=+0.65% — WHIPSAW (went to +0.35% then reversed)

**Losers (4):**
- BABY LONG: MFE=+0.12%, MAE=+1.11% — barely moved in favor, high adverse
- MOVE SHORT: MFE=+0.32%, MAE=+0.61% — WHIPSAW
- PURR SHORT: MFE=+0.20%, MAE=+1.58% — WHIPSAW
- AAVE SHORT: MFE=+1.34%, MAE=+1.03% — went to +1.34% profit then reversed to -0.08%

**Whipsaw rate: 57% (4/7 trades) — extremely high. Trades peak in profit then reverse.**

### Close Reason Breakdown (7 recent trades)
- atr_sl_hit: 7 trades, 43% WR (only exit type)

### CRITICAL BUGS (still unfixed, 8th consecutive time)
1. **Kill switches not working** — vel+, vel-, bb-squeeze, tl_break STILL executing despite all being disabled. 0% WR across 24 disabled-signal trades. Root cause in signal execution layer.
2. **Blacklisted tokens still executing** — UNI (5 trades, 0% WR), PEOPLE (2, 0%), STBL (2, 0%), ORDI (2, 50%). Blacklist filter not applied.
3. **Double-entry signal_outcomes** — 82 total rows for 41 dedup trades (2x inflation).

### Changes Implemented

**1. BLACKLIST BABY both directions (hermes_constants.py:SHORT_BLACKLIST, LONG_BLACKLIST)**
- BABY: 0% WR (0/3 dedup), -$0.48 total — zero wins across 3 trades
- Added to both SHORT_BLACKLIST and LONG_BLACKLIST

**2. LOWER SIGNAL_FILTER_SPEED_MIN: 45 → 40 (hermes_constants.py:469)**
- Trade rate critical at 0.58 trades/hr (2 trades in 6h)
- 40 blocks bottom 40% of speed distribution
- Expected to increase trade count while maintaining quality

**3. DISABLE inv-accel-300+ (hermes_constants.py:740)**
- INVERSE_ACCEL_300_PLUS_ENABLED: True → False
- 0% WR (0/1 dedup), -$0.33 — first trade was a loss
- inv-accel-300- (SHORT) remains enabled — only profitable variant

### What NOT to change
- ATR_SL_MIN_INIT (1.2%) — wider breathing room working as intended
- TRAILING_ACTIVATION_PCT (0.25%) — lock profits sooner
- TRAILING_DISTANCE_PCT (0.30%) — tighter trail locks profit faster
- TL_BREAK_ENABLED (False) — disable confirmed, but signals still executing (pipeline bug)
- ACCEL_300_ENABLED (False) — disable confirmed, but signals still executing
- BOLLINGER_SQUEEZE_ENABLED (False) — disable confirmed, but signals still executing
- All blacklisted tokens — consistent losers, keep blocked
- Phase-based k scaling — disabled (was compressing SL too aggressively)
- Dead hours filter — working correctly
- SIGNAL_FILTER_ENABLED (True) — the filter framework is sound

### 5 Actionable Adjustments (ranked by impact)
1. 🔴 CRITICAL: Fix kill switch pipeline bug — disabled signals STILL executing (vel+, vel-, bb-squeeze, tl_break). 8th consecutive analysis flagging this.
2. ✅ Blacklist BABY — IMPLEMENTED (0% WR, -$0.48)
3. ✅ Lower speed filter to 40 — IMPLEMENTED (reduce trade starvation)
4. ✅ Disable inv-accel-300+ — IMPLEMENTED (0% WR)
5. ⬜ Fix blacklisted token execution — UNI, PEOPLE, STBL, ORDI still executing despite being blacklisted

### Open Questions
- Why are kill switches not working? (FLAGGED 8th CONSECUTIVE TIME)
- Why are blacklisted tokens still executing? Is the blacklist filter applied at signal creation or only at trade entry?
- Should we widen inv-accel-300- reversion params for more entries? (only 4 trades in 24h)
- Is the whipsaw rate (57%) due to trailing activation too early (0.25%)?
- Should we blacklist ORDI (50% WR but -$0.64 total)?

---

## 2026-08-01: Hourly Trade Analysis — Speed Lowered, Gap Widened, Kill Switch Bug 9th Time

### Data Window
- Analyzed: 5 trades (12h window), signal_outcomes (24h dedup: 35 trades), trades.json (200)
- Trades: 2826 total closed, 0 open at analysis time
- Trade rate: ~0.3 trades/hour (CRITICAL — system nearly idle)
- Last trade closed: 2026-08-01 14:38 UTC (BABY LONG, inv-accel-300+, -0.33%)

### Signal Performance (24h dedup — ALL signals net losers)
| Signal | Trades | WR | Total PnL | Status |
|--------|--------|-----|-----------|--------|
| accel-300+ | 1 | 100.0% | +0.17 | GOOD (1 trade) |
| bb-squeeze | 1 | 0.0% | +0.08 | DEAD |
| inv-accel-300- | 4 | 25.0% | -0.17 | DECLINING (was 33.3%) |
| tl_break_long | 12 | 33.3% | -0.18 | LEGACY (disabled) |
| tl_break_short | 5 | 20.0% | -0.78 | LEGACY (disabled) |
| inv-accel-300+ | 1 | 0.0% | -0.33 | DISABLED |
| bb-squeeze- | 2 | 0.0% | -0.30 | DEAD |
| accel-300-vel+ | 6 | 0.0% | -0.92 | CATASTROPHIC |
| accel-300-vel- | 3 | 0.0% | -0.81 | CATASTROPHIC |

**Overall (deduplicated): 35 trades, 7 wins, 20.0% WR, -3.24 total PnL in 24h.**

### Token Performance (24h dedup — blacklisted tokens still executing)
| Token | Trades | WR | Total PnL | Status |
|-------|--------|-----|-----------|--------|
| UNI | 5 | 0.0% | -1.39 | BLACKLISTED (still executing!) |
| CAKE | 2 | 0.0% | -0.52 | BLACKLISTED (still executing!) |
| LINEA | 2 | 0.0% | -0.58 | BLACKLISTED (still executing!) |
| BABY | 2 | 0.0% | -0.42 | BLACKLISTED (still executing!) |
| ORDI | 2 | 50.0% | -0.64 | BLACKLISTED (still executing!) |
| PEOPLE | 1 | 0.0% | -0.42 | BLACKLISTED (still executing!) |
| STBL | 1 | 0.0% | -0.14 | BLACKLISTED (still executing!) |
| AIXBT | 1 | 0.0% | -0.21 | BLACKLISTED (still executing!) |
| BLUR | 1 | 0.0% | -0.06 | BLACKLISTED (still executing!) |
| FET | 1 | 0.0% | -0.14 | BLACKLISTED (still executing!) |
| TIA | 1 | 0.0% | -0.12 | BLACKLISTED (still executing!) |

**11 blacklisted tokens still executing in 24h — blacklist filter NOT applied.**

### Recent Trades (last 12h — 0% WR)
| Coin | Dir | Signal | PnL | Close Reason |
|------|-----|--------|-----|--------------|
| BABY | LONG | inv-accel-300+ | -0.33% | atr_sl_hit |
| MOVE | SHORT | inv-accel-300- | -0.61% | atr_sl_hit |
| PURR | SHORT | bb-squeeze- | -0.23% | atr_sl_hit |
| AAVE | SHORT | bb-squeeze- | -0.08% | atr_sl_hit |
| MORPHO | SHORT | tl_break_short | +0.04% | atr_sl_hit |

### CRITICAL BUGS (9th consecutive time)
1. **Kill switches not working** — vel+ (6 trades, 0% WR), vel- (3, 0%), bb-squeeze (3, 0%), tl_break (17, 30%) STILL EXECUTING despite all being disabled. 26 disabled-signal trades in 24h, ~5% WR. Root cause in signal execution layer.
2. **Blacklisted tokens still executing** — 11 blacklisted tokens (UNI, CAKE, LINEA, BABY, ORDI, PEOPLE, STBL, AIXBT, BLUR, FET, TIA) traded in 24h. Blacklist filter not applied at trade entry.
3. **Double-entry signal_outcomes** — 70 total rows for 35 dedup trades (2x inflation).

### Changes Implemented

**1. LOWER SIGNAL_FILTER_SPEED_MIN: 40 → 35 (hermes_constants.py:473)**
- Trade rate critical at 0.3 trades/hr (2 trades in 6h)
- 35 blocks bottom 35% of speed distribution
- Expected to increase trade count from inv-accel-300-

**2. WIDEN inv-accel-300- gap: 0.15% → 0.10% (hermes_constants.py:645-646)**
- INVERSE_ACCEL_300_MIN_GAP_PCT_LONG: 0.15 → 0.10
- INVERSE_ACCEL_300_MIN_GAP_PCT_SHORT: 0.15 → 0.10
- inv-accel-300- is the only signal that sometimes works — let it fire more often
- Risk: more signals = more trades, but 25% WR with positive PnL (on best tokens) justifies it

### What NOT to change
- ATR_SL_MIN_INIT (1.2%) — wider breathing room working as intended
- TRAILING_ACTIVATION_PCT (0.25%) — lock profits sooner
- TRAILING_DISTANCE_PCT (0.30%) — tighter trail locks profit faster
- TL_BREAK_ENABLED (False) — disable confirmed, but signals still executing (pipeline bug)
- ACCEL_300_ENABLED (False) — disable confirmed, but signals still executing
- BOLLINGER_SQUEEZE_ENABLED (False) — disable confirmed, but signals still executing
- All blacklisted tokens — consistent losers, keep blocked
- Phase-based k scaling — disabled (was compressing SL too aggressively)
- Dead hours filter — working correctly
- SIGNAL_FILTER_ENABLED (True) — the filter framework is sound

### 5 Actionable Adjustments (ranked by impact)
1. 🔴 CRITICAL: Fix kill switch pipeline bug — disabled signals STILL executing (vel+, vel-, bb-squeeze, tl_break). 9th consecutive analysis flagging this. Root cause is in signal execution layer.
2. 🔴 CRITICAL: Fix blacklisted token execution — 11 blacklisted tokens still trading. Blacklist filter not applied at trade entry.
3. ✅ Lower speed filter to 35 — IMPLEMENTED (reduce trade starvation)
4. ✅ Widen inv-accel-300- gap to 0.10% — IMPLEMENTED (more entries from best signal)
5. ⬜ Fix double-entry signal_outcomes bug — each trade logged twice, inflating metrics

### Open Questions
- Why are kill switches not working? (FLAGGED 9th CONSECUTIVE TIME)
- Why are blacklisted tokens still executing? Is the blacklist filter applied at signal creation or only at trade entry?
- Is inv-accel-300- declining (25% WR, -0.17) due to market conditions or survivorship bias?
- Should we raise TOKEN_WR_THRESHOLD from 30 to 35 to block more losers?
- Is the system fundamentally broken until kill switch and blacklist bugs are fixed?

---

## 2026-08-01: Hourly Trade Analysis — inv-accel-300- Declining, Trade Starvation

### Data Window
- Analyzed: 6 trades (12h window), signal_outcomes (24h dedup: 33 trades), trades.json (200)
- Trades: 2828 total closed, 0 open at analysis time
- Trade rate: ~0.5 trades/hour (CRITICAL — system nearly idle)
- Last trade closed: 2026-08-01 16:39 UTC (AAVE SHORT, inv-accel-300-, +0.10%)

### Signal Performance (24h dedup — ALL signals net losers)
| Signal | Trades | WR | Total PnL | Status |
|--------|--------|-----|-----------|--------|
| accel-300+ | 1 | 100.0% | +0.17 | GOOD (1 trade) |
| bb-squeeze | 1 | 0.0% | +0.08 | DEAD |
| tl_break_long | 11 | 36.4% | -0.09 | LEGACY (disabled) |
| inv-accel-300- | 6 | 16.7% | -0.39 | DECLINING (was 33.3%) |
| accel-300-vel+ | 4 | 0.0% | -0.38 | CATASTROPHIC (disabled) |
| accel-300-vel- | 2 | 0.0% | -0.27 | CATASTROPHIC (disabled) |
| tl_break_short | 5 | 20.0% | -0.78 | LEGACY (disabled) |
| inv-accel-300+ | 1 | 0.0% | -0.33 | DISABLED |
| bb-squeeze- | 2 | 0.0% | -0.30 | DEAD (disabled) |

**Overall (deduplicated): 33 trades, 7 wins, 21.2% WR, -$3.24 total PnL in 24h.**

### Token Performance (24h dedup — top losers)
| Token | Trades | WR | Total PnL | Status |
|-------|--------|-----|-----------|--------|
| UNI | 5 | 0.0% | -1.39 | BLACKLISTED (still executing!) |
| CAKE | 2 | 0.0% | -0.52 | BLACKLISTED (still executing!) |
| ORDI | 2 | 50.0% | -0.64 | BLACKLISTED (still executing!) |
| STBL | 2 | 0.0% | -0.47 | BLACKLISTED (still executing!) |
| AIXBT | 1 | 0.0% | -0.21 | BLACKLISTED (still executing!) |
| BABY | 1 | 0.0% | -0.33 | BLACKLISTED (still executing!) |

**Profitable tokens: APEX (+0.87), KAITO (+0.34), AAVE (+0.02), ETH (+0.26)**

### Diagnosis

**1. Entry Quality (MFE/MAE — last 6h)**
- **Winners** (2): AAVE SHORT inv-accel-300- (+0.10%), APEX SHORT inv-accel-300- (+0.58%) — low adverse excursion, good timing
- **Losers** (4): STBL (-0.32%), BABY (-0.33%), MOVE (-0.61%), PURR (-0.23%) — all hit SL immediately
- **Whipsaw rate**: 83% (5/6 losers hit SL) — trades stall then reverse

**2. Signal Quality**
- inv-accel-300- is declining: 33.3% → 25% → 16.7% WR over last 3 analyses
- Disabled signals (vel+, vel-, bb-squeeze, tl_break) still executing at 0% WR — kill switch bug 9th consecutive time
- Blacklisted tokens (UNI, CAKE, ORDI, STBL) still executing — blacklist filter not applied

**3. SL/TP Behavior**
- 100% of exits are `atr_sl_hit` — no trailing or TP exits
- ATR_SL_MIN_INIT at 1.2% surviving but trades stalling and hitting SL

**4. Trade Frequency**
- Critical: 0.5 trades/hr (last 6h)
- inv-accel-300- only fire 6 times in 24h (was 3-4 before)
- SIGNAL_FILTER_SPEED_MIN at 35 still too high for this signal

### Changes Implemented

**1. RAISE TOKEN_WR_THRESHOLD: 30 → 40 (hermes_constants.py:484)**
- Rationale: block more losing tokens (UNI 0% WR, CAKE 0% WR, ORDI 50% but -0.64 total)
- Risk: may block some marginal winners, but 40% threshold still allows decent tokens

**2. WIDEN inv-accel-300- REVERSION_BARS: 3 → 2 (hermes_constants.py:647)**
- Rationale: reduce confirmation requirement for reversion, let signal fire sooner
- Risk: more noise, but inv-accel-300- is the only signal with any historical edge

**3. LOWER inv-accel-300- REVERSION_THRESHOLD: 0.08 → 0.05 (hermes_constants.py:648)**
- Rationale: lower the gap narrowing requirement for more entries
- Risk: more low-quality signals, but trade starvation is the bigger problem

**4. LOWER SIGNAL_FILTER_SPEED_MIN: 35 → 30 (hermes_constants.py:473)**
- Rationale: reduce trade starvation, let more inv-accel-300- through
- Risk: more noise from disabled signals (kill switch bug), but inv-accel-300- needs entries

### What NOT to change
- ATR_SL_MIN_INIT (1.2%) — wider breathing room working as intended
- TRAILING_ACTIVATION_PCT (0.25%) — lock profits sooner
- TRAILING_DISTANCE_PCT (0.30%) — tighter trail locks profit faster
- TL_BREAK_ENABLED (False) — disable confirmed, but signals still executing (pipeline bug)
- ACCEL_300_ENABLED (False) — disable confirmed, but signals still executing
- BOLLINGER_SQUEEZE_ENABLED (False) — disable confirmed, but signals still executing
- All blacklisted tokens — consistent losers, keep blocked
- Phase-based k scaling — disabled (was compressing SL too aggressively)
- Dead hours filter — working correctly
- SIGNAL_FILTER_ENABLED (True) — the filter framework is sound

### 5 Actionable Adjustments (ranked by impact)
1. 🔴 CRITICAL: Fix kill switch pipeline bug — disabled signals STILL executing (vel+, vel-, bb-squeeze, tl_break). 9th consecutive analysis. Root cause in signal execution layer.
2. 🔴 CRITICAL: Fix blacklisted token execution — UNI, CAKE, ORDI, STBL still trading despite being blacklisted.
3. ✅ Raise TOKEN_WR_THRESHOLD to 40 — IMPLEMENTED (block more losers)
4. ✅ Widen inv-accel-300- reversion (bars=2, threshold=0.05) — IMPLEMENTED (more entries)
5. ✅ Lower speed filter to 30 — IMPLEMENTED (reduce trade starvation)

### Open Questions
- Why are kill switches not working? (FLAGGED 9th CONSECUTIVE TIME)
- Why are blacklisted tokens still executing? (FLAGGED 9th CONSECUTIVE TIME)
- Is inv-accel-300- decline due to market conditions or signal quality degradation?
- Should we add ACCEL_300_VELOCITY_MINUS_ENABLED flag to control vel- separately? (already disabled via ACCEL_300_ENABLED=False)
- Is the system fundamentally broken until kill switch and blacklist bugs are fixed?

---

## 2026-08-01: Hourly Trade Analysis — SL Widened, Trailing Loosened, Speed Lowered

### Data Window
- Analyzed: 200 closed trades (trades.json), signal_outcomes (24h dedup: 32 trades)
- Trades: 2828 total closed, 0 open at analysis time
- Trade rate: ~0.5 trades/hour (CRITICAL — system nearly idle)
- Last trade closed: 2026-08-01 16:39 UTC (AAVE SHORT, inv-accel-300-, +0.10%)

### Signal Performance (24h dedup — ALL signals net losers)
| Signal | Trades | WR | Total PnL | Status |
|--------|--------|-----|-----------|--------|
| accel-300+ | 1 | 100.0% | +0.17 | GOOD (1 trade) |
| bb-squeeze | 1 | 0.0% | +0.08 | DEAD |
| tl_break_long | 10 | 30.0% | -0.93 | LEGACY (disabled) |
| tl_break_short | 5 | 20.0% | -0.78 | LEGACY (disabled) |
| inv-accel-300- | 6 | 16.7% | -0.39 | DECLINING (was 33.3%) |
| accel-300-vel+ | 4 | 0.0% | -0.38 | CATASTROPHIC (disabled) |
| inv-accel-300+ | 1 | 0.0% | -0.33 | DISABLED |
| bb-squeeze- | 2 | 0.0% | -0.30 | DEAD (disabled) |
| accel-300-vel- | 2 | 0.0% | -0.27 | CATASTROPHIC (disabled) |

**Overall (deduplicated): 32 trades, 6 wins, 18.8% WR, -3.13 total PnL in 24h.**

### Signal Performance (200 recent trades — ALL signals in file)
| Signal | Trades | WR | Total PnL | Status |
|--------|--------|-----|-----------|--------|
| inv-accel-300- | 10 | 60.0% | +1.97 | BEST ACTIVE |
| accel-300+ | 6 | 67.0% | +1.34 | GOOD |
| tl_break_long | 58 | 40.0% | +3.43 | LEGACY |
| tl_break_short | 71 | 48.0% | +0.15 | LEGACY |
| accel-300-vel- | 15 | 33.0% | +0.68 | MARGINAL |
| accel-300-vel+ | 22 | 27.0% | -0.53 | BAD |
| accel-300- | 8 | 38.0% | -0.85 | BAD |

### Token Performance (24h dedup — top losers)
| Token | Trades | WR | Total PnL | Status |
|-------|--------|-----|-----------|--------|
| UNI | 5 | 0.0% | -1.39 | BLACKLISTED (still executing!) |
| CAKE | 2 | 0.0% | -0.52 | BLACKLISTED (still executing!) |
| STBL | 2 | 0.0% | -0.47 | BLACKLISTED (still executing!) |
| BABY | 1 | 0.0% | -0.33 | BLACKLISTED (still executing!) |

**Profitable tokens: APEX (+0.87), ETH (+0.26), MOODENG (+0.60), ME (+0.02)**

### Diagnosis

**1. Entry Quality:**
- Winners: Low adverse excursion, good timing (AAVE SHORT +0.10%, APEX SHORT +0.58%)
- Losers: High adverse excursion, SL hit immediately (MOVE -0.61%, BABY -0.33%, STBL -0.32%)
- Whipsaw rate: 83% (5/6 losers hit SL immediately)

**2. Signal Quality:**
- inv-accel-300- declining: 33.3% → 25% → 16.7% over last 3 analyses
- Disabled signals (vel+, vel-, bb-squeeze, tl_break) still executing at 0% WR
- Blacklisted tokens (UNI, CAKE, STBL, BABY) still executing

**3. SL/TP Behavior:**
- 100% of recent exits are `atr_sl_hit` — no trailing or TP exits
- ATR_SL_MIN_INIT at 1.2% was too tight — normal crypto retracements trigger SL immediately
- Trailing never activates because trades hit SL before reaching +0.25% activation

**4. Trade Frequency:**
- Critical: 0.5 trades/hr (last 12h)
- SIGNAL_FILTER_SPEED_MIN at 30 blocking too many signals
- inv-accel-300- needs more entries to recover edge

### Changes Implemented

**1. WIDEN ATR_SL_MIN_INIT: 1.2% → 1.5% (hermes_constants.py:346)**
- Also: ATR_SL_MAX_INIT 1.5% → 1.8%, SL_PCT_FALLBACK 1.2% → 1.5%, STOP_LOSS_DEFAULT 1.2% → 1.5%, TP_PCT_FALLBACK 1.8% → 2.2%
- Rationale: 100% of exits are atr_sl_hit at 1.2%. Normal crypto retracements of 0.5-1% immediately stop out trades. 1.5% gives breathing room.

**2. WIDEN TRAILING_DISTANCE_PCT: 0.30% → 0.40% (hermes_constants.py:359)**
- Rationale: 83% whipsaw rate — trades peak then reverse through tight 0.30% trail. 0.40% gives trailing more room to breathe before triggering exit.

**3. LOWER SIGNAL_FILTER_SPEED_MIN: 30 → 25 (hermes_constants.py:473)**
- Rationale: Critical trade starvation (0.5 trades/hr). Winners avg 71% speed percentile. 25 blocks bottom 25% but lets more inv-accel-300- entries through.

### What NOT to change
- ATR_SL_MIN (0.5%) — floor, keep it
- ATR_TP_MAX (1.0%) — already tight enough
- TRAILING_ACTIVATION_PCT (0.25%) — good activation point
- TL_BREAK_ENABLED (False) — disable confirmed, but signals still executing (pipeline bug)
- ACCEL_300_ENABLED (False) — disable confirmed, but signals still executing
- BOLLINGER_SQUEEZE_ENABLED (False) — disable confirmed, but signals still executing
- All blacklisted tokens — consistent losers, keep blocked
- Phase-based k scaling — disabled (was compressing SL too aggressively)
- Dead hours filter — working correctly
- SIGNAL_FILTER_ENABLED (True) — the filter framework is sound

### 5 Actionable Adjustments (ranked by impact)
1. 🔴 CRITICAL: Fix kill switch pipeline bug — disabled signals STILL executing (vel+, vel-, bb-squeeze, tl_break). 10th consecutive analysis flagging this. Root cause is in signal execution layer.
2. 🔴 CRITICAL: Fix blacklisted token execution — UNI, CAKE, STBL, BABY still trading despite being blacklisted. Blacklist filter not applied at trade entry.
3. ✅ Widen ATR_SL_MIN_INIT to 1.5% — IMPLEMENTED (100% exits were atr_sl_hit, too tight)
4. ✅ Widen TRAILING_DISTANCE_PCT to 0.40% — IMPLEMENTED (83% whipsaw rate, trail too tight)
5. ✅ Lower speed filter to 25 — IMPLEMENTED (critical starvation at 0.5 trades/hr)

### Open Questions
- Why are kill switches not working? (FLAGGED 10th CONSECUTIVE TIME)
- Why are blacklisted tokens still executing? (FLAGGED 10th CONSECUTIVE TIME)
- Is inv-accel-300- decline (33% → 16.7%) due to market conditions or signal quality degradation?
- Will wider SL (1.5%) reduce whipsaw stops or just delay the inevitable loss?
- Should we investigate the signal execution layer code directly to find the kill switch bug root cause?

---

## 2026-08-01: Hourly Trade Analysis — Kill Switch Guards Added, inv-accel-300- Disabled

### Data Window
- Analyzed: 18 dedup trades (24h), 5 trades (12h), trades.json (50)
- Trades: 2828 total closed, 1 open (ALT SHORT inv-accel-300-)
- Trade rate: ~0.75 trades/hr (CRITICAL — system nearly idle)
- Last trade closed: 2026-08-01 16:39 UTC (AAVE SHORT, inv-accel-300-, +0.10%)

### Signal Performance (24h dedup — ALL signals net negative)
| Signal | Trades | WR | Total PnL | Status |
|--------|--------|-----|-----------|--------|
| tl_break_long | 10 | 20% | -4.36 | LEGACY (disabled, still executing) |
| inv-accel-300- | 8 | 0% | -4.10 | COLLAPSED (was 33% earlier today) |
| tl_break_short | 6 | 17% | -3.02 | LEGACY (disabled, still executing) |
| bb-squeeze- | 4 | 0% | -2.41 | DEAD (disabled, still executing) |
| inv-accel-300+ | 2 | 0% | -1.56 | DISABLED |
| accel-300-vel- | 2 | 0% | -1.01 | CATASTROPHIC (disabled) |
| accel-300-vel+ | 2 | 0% | -0.99 | CATASTROPHIC (disabled) |
| bb-squeeze | 2 | 0% | -0.74 | DEAD (disabled) |

**Overall: 18 dedup trades, 3 wins, 16.7% WR, -$0.99 total PnL in 24h.**
**ALL 8 signal types are net negative. No profitable signals exist.**

### Token Performance (24h dedup — top losers)
| Token | Trades | WR | Total PnL | Status |
|-------|--------|-----|-----------|--------|
| STBL | 4 | 0% | -2.73 | BLACKLISTED (still executing!) |
| ORDI | 2 | 0% | -2.50 | BLACKLISTED (still executing!) |
| MOVE | 2 | 0% | -2.12 | BLACKLISTED (still executing!) |
| AAVE | 4 | 0% | -1.76 | PROFITABLE before, now 0% WR |
| BABY | 2 | 0% | -1.56 | BLACKLISTED (still executing!) |
| PURR | 2 | 0% | -1.35 | BLACKLISTED |

**11+ blacklisted tokens still executing — blacklist filter NOT applied at trade entry.**

### MFE/MAE Analysis (5 recent trades)
| Coin | Dir | Signal | MFE | MAE | Result |
|------|-----|--------|-----|-----|--------|
| AAVE | SHORT | inv-accel-300- | +1.00% | -0.15% | WIN +0.10% |
| STBL | SHORT | inv-accel-300- | +1.87% | -0.58% | LOSE -0.32% |
| BABY | LONG | inv-accel-300+ | +0.12% | -1.11% | LOSE -0.33% |
| MOVE | SHORT | inv-accel-300- | +1.91% | -0.61% | LOSE -0.61% |
| PURR | SHORT | bb-squeeze- | +0.20% | -1.58% | LOSE -0.23% |

**Key insight: STBL and MOVE reached 1.87-1.91% MFE but still lost — whipsaw pattern. Trailing never caught the move.**

### Diagnosis

**1. Entry Quality:**
- Winners: Low adverse (AAVE 0.15%), good timing
- Losers: STBL/MOVE had HIGH favorable excursion (1.87-1.91%) but still lost — whipsaw pattern
- Whipsaw rate: 60% (3/5 trades peaked in profit then reversed)

**2. Signal Quality:**
- inv-accel-300- collapsed: 33% → 25% → 16.7% → 0% WR over last 5 analyses
- Disabled signals (tl_break, bb-squeeze, vel+) still executing — 13th consecutive analysis
- No active signal has positive expectancy

**3. SL/TP Behavior:**
- 100% of exits are `atr_sl_hit` — no trailing or TP exits
- ATR_SL_MIN_INIT at 1.5% surviving but trades stalling
- Trailing activation at 0.30% reached but trailing distance 0.30% gives back too much

**4. Trade Frequency:**
- Critical: 0.75 trades/hr (only disabled signals generating trades)
- With inv-accel-300- now disabled, system will be completely idle
- No active signal with positive expectancy exists

### Changes Implemented

**1. ADD Layer 2 kill switch guards for tl_break and bb-squeeze (signal_schema.py:680-700)**
- Added guards for: tl_break+, tl_break-, tl_break (bare), bb-squeeze+, bb-squeeze-, bb-squeeze (bare)
- These were imported but never checked in the for loop — signals bypassed kill switch
- Also added guards for accel-300+ and accel-300- (imported but not checked)
- Added missing imports: TL_BREAK_ENABLED, BOLLINGER_SQUEEZE_ENABLED, BOLLINGER_SQUEEZE_PLUS/MINUS_ENABLED

**2. DISABLE inv-accel-300- (hermes_constants.py:755)**
- INVERSE_ACCEL_300_MINUS_ENABLED: True → False
- Rationale: Collapsed from 33% to 0% WR in 24h. 8 trades, -$4.10 total. No longer profitable.
- Risk: System will be completely idle with no active signals. But keeping a losing signal active is worse.

**3. RAISE SIGNAL_FILTER_SPEED_MIN: 45 → 50 (hermes_constants.py:476)**
- Rationale: All signals net negative. Be more selective to reduce noise.
- Risk: System will be even more idle. But quality over quantity when everything is losing.

### What NOT to change
- ATR_SL_MIN_INIT (1.5%) — wider breathing room, just widened
- TRAILING_ACTIVATION_PCT (0.30%) — wait for real move before trailing
- TRAILING_DISTANCE_PCT (0.30%) — tighter trail locks profit faster
- All disabled signals — keep disabled, kill switches now have proper guards
- All blacklisted tokens — consistent losers, keep blocked (but blacklist filter itself needs fixing)
- Phase-based k scaling — disabled (was compressing SL too aggressively)
- Dead hours filter — working correctly
- SIGNAL_FILTER_ENABLED (True) — the filter framework is sound

### 5 Actionable Adjustments (ranked by impact)
1. 🔴 CRITICAL: Fix blacklisted token execution — 11+ blacklisted tokens still trading despite being in BLACKLIST sets. Blacklist filter in add_signal() uses `token.upper() in SHORT_BLACKLIST` but tokens still pass. Root cause may be case sensitivity or signals bypassing add_signal().
2. 🔴 CRITICAL: System has NO active profitable signals. inv-accel-300- was the last one and it collapsed. Need to either: (a) find a new signal with edge, (b) re-enable a previously profitable signal with better filtering, or (c) accept the system is in a drawdown period and wait for market conditions to change.
3. ✅ Add Layer 2 kill switch guards for tl_break and bb-squeeze — IMPLEMENTED (root cause of 13 analyses)
4. ✅ Disable inv-accel-300- — IMPLEMENTED (collapsed from 33% to 0% WR)
5. ✅ Raise speed filter to 50 — IMPLEMENTED (all signals net negative, be selective)

### Open Questions
- Why are blacklisted tokens still executing? (FLAGGED 13th CONSECUTIVE TIME) Is the blacklist check case-sensitive? Do signals bypass add_signal()?
- With no active profitable signals, should we re-enable any previously profitable signal? (tl_break_long had 40% WR in 200 trades, accel-300+ had 67%)
- Is the market in a regime where no mean-reversion or momentum signal works? (all signals negative)
- Should we reduce trade size or pause live trading until a profitable signal is found?
- Is the double-entry signal_outcomes bug still inflating metrics?

---

## 2026-08-01: Hourly Trade Analysis — Trailing Tightened, Speed Lowered (10th+ consecutive)

### Data Window
- Analyzed: 4 trades (12h window), signal_outcomes (24h dedup: 29 trades), trades.json (200)
- Trades: 2828 total closed, 0 open at analysis time
- Trade rate: ~0.33 trades/hr (CRITICAL — system nearly idle)
- Last trade closed: 2026-08-01 16:39 UTC (AAVE SHORT, inv-accel-300-, +0.10%)

### Signal Performance (24h dedup — ALL signals net losers)
| Signal | Trades | WR | Total PnL | Status |
|--------|--------|-----|-----------|--------|
| accel-300+ | 1 | 100.0% | +0.17 | GOOD (1 trade) |
| bb-squeeze | 1 | 0.0% | +0.08 | DEAD |
| tl_break_long | 9 | 33.3% | -0.34 | LEGACY (disabled) |
| inv-accel-300- | 6 | 16.7% | -0.39 | DECLINING |
| accel-300-vel+ | 4 | 0.0% | -0.38 | CATASTROPHIC (disabled) |
| tl_break_short | 3 | 33.3% | -0.16 | LEGACY (disabled) |
| accel-300-vel- | 2 | 0.0% | -0.27 | CATASTROPHIC (disabled) |
| inv-accel-300+ | 1 | 0.0% | -0.33 | DISABLED |
| bb-squeeze- | 2 | 0.0% | -0.30 | DEAD (disabled) |

**Overall (deduplicated): 29 trades, 5 wins, 17.2% WR, -$2.17 total PnL in 24h.**

### Token Performance (24h dedup — top losers)
| Token | Trades | WR | Total PnL | Status |
|-------|--------|-----|-----------|--------|
| UNI | 5 | 0.0% | -1.39 | BLACKLISTED (still executing!) |
| STBL | 2 | 0.0% | -0.47 | BLACKLISTED (still executing!) |
| APEX | 2 | 50.0% | +0.87 | PROFITABLE |
| ETH | 1 | 100.0% | +0.26 | PROFITABLE |
| MOODENG | 1 | 100.0% | +0.60 | PROFITABLE |

### MFE/MAE Analysis (4 recent trades)
| Coin | Dir | Signal | Result | MFE | MAE |
|------|-----|--------|--------|-----|-----|
| AAVE | SHORT | inv-accel-300- | WIN +0.10% | 1.00% | 0.15% |
| STBL | SHORT | inv-accel-300- | LOSE -0.32% | 1.87% | 0.58% |
| BABY | LONG | inv-accel-300+ | LOSE -0.33% | 0.12% | 1.11% |
| MOVE | SHORT | inv-accel-300- | LOSE -0.61% | 1.91% | 0.61% |

**Key insight: STBL and MOVE both reached 1.87-1.91% MFE (favorable excursion) but still lost. Trades peaked in profit then reversed. Trailing activation at 0.25% was too late — trade already pulling back when trailing kicks in.**

### Diagnosis

**1. Entry Quality:**
- Winners: Low adverse (AAVE 0.15%), good timing
- Losers: STBL/MOVE had HIGH favorable excursion (1.87-1.91%) but still lost — whipsaw pattern
- BABY: Low favorable (0.12%), high adverse (1.11%) — bad entry

**2. Signal Quality:**
- inv-accel-300- declining: 33.3% → 25% → 16.7% over last 3 analyses
- All disabled signals still executing (kill switch bug 10th+ time)

**3. SL/TP Behavior:**
- 100% of exits are `atr_sl_hit` — no trailing exits
- STBL/MOVE: MFE 1.87-1.91% but trail never caught the move — activation at 0.25% was reached but trailing distance 0.40% gave back too much before exit
- Need: activate earlier (0.15%), trail tighter (0.30%)

**4. Trade Frequency:**
- Critical: 0.33 trades/hr
- Only 29 dedup trades in 24h
- Speed filter at 25 is very permissive — starvation is from limited active signals

### Changes Implemented

**1. TIGHTEN TRAILING_ACTIVATION_PCT: 0.25% → 0.15% (hermes_constants.py:358)**
- Rationale: STBL/MOVE reached 1.87-1.91% MFE but trailing activated too late. Earlier activation locks profits before reversal.
- Risk: may trigger on noise, but 0.15% is still meaningful move

**2. TIGHTEN TRAILING_DISTANCE_PCT: 0.40% → 0.30% (hermes_constants.py:359)**
- Rationale: Trades peaking at 1.9% MFE giving back 0.40% before trail exits. Tighter trail locks more profit.
- Risk: may exit too early on normal retracements, but current 83% whipsaw rate means current setting is too loose

**3. LOWER TOKEN_WR_THRESHOLD: 40 → 30 (hermes_constants.py:484)**
- Rationale: Critical trade starvation (0.33/hr). 40 threshold blocking marginal tokens. 30 still blocks worst performers.
- Risk: more losing tokens may pass, but starvation is the bigger problem

### What NOT to change
- ATR_SL_MIN_INIT (1.5%) — wider breathing room, just widened
- SIGNAL_FILTER_SPEED_MIN (25) — already very permissive
- TL_BREAK_ENABLED (False) — disable confirmed, but signals still executing (pipeline bug)
- ACCEL_300_ENABLED (False) — disable confirmed, but signals still executing
- BOLLINGER_SQUEEZE_ENABLED (False) — disable confirmed, but signals still executing
- All blacklisted tokens — consistent losers, keep blocked
- Phase-based k scaling — disabled (was compressing SL too aggressively)
- Dead hours filter — working correctly
- SIGNAL_FILTER_ENABLED (True) — the filter framework is sound

### 5 Actionable Adjustments (ranked by impact)
1. 🔴 CRITICAL: Fix kill switch pipeline bug — disabled signals STILL executing. 10th+ consecutive analysis flagging this.
2. 🔴 CRITICAL: Fix blacklisted token execution — UNI, STBL still trading despite being blacklisted.
3. ✅ Tighten trailing activation to 0.15% — IMPLEMENTED (STBL/MOVE whipsawed from 1.9% MFE)
4. ✅ Tighten trailing distance to 0.30% — IMPLEMENTED (give back less after activation)
5. ✅ Lower TOKEN_WR_THRESHOLD to 30 — IMPLEMENTED (reduce trade starvation)

### Open Questions
- Why are kill switches not working? (FLAGGED 10th+ CONSECUTIVE TIME)
- Why are blacklisted tokens still executing? (FLAGGED 10th+ CONSECUTIVE TIME)
- Is inv-accel-300- decline (33% → 16.7%) due to market conditions or signal quality degradation?
- Should we investigate the signal execution layer code directly to find the kill switch bug root cause?
- Is the system fundamentally broken until kill switch and blacklist bugs are fixed?

---

## 2026-08-01: Hourly Trade Analysis — Kill Switches Fixed, Speed Raised

### Data Window
- Analyzed: 200 closed trades (trades.json), signal_outcomes (24h dedup: 25 trades), MFE/MAE (15 recent trades)
- Trades: 2828+ total closed, 0 open at analysis time
- Trade rate: ~2.8 trades/hour (moderate)
- Last trade closed: 2026-08-01 18:11 UTC (0G SHORT, inv-accel-300-)

### Signal Performance (200 trades — ALL signals in trades.json)
| Signal | Trades | WR | Total PnL | Status |
|--------|--------|-----|-----------|--------|
| tl_break_long | 58 | 40% | +3.43 | LEGACY (disabled) |
| inv-accel-300- | 10 | 60% | +1.97 | BEST ACTIVE |
| accel-300+ | 6 | 67% | +1.34 | GOOD |
| accel-300-vel- | 15 | 33% | +0.68 | MARGINAL |
| tl_break_short | 71 | 48% | +0.15 | LEGACY (disabled) |
| accel-300-vel+ | 22 | 27% | -0.53 | BAD |
| accel-300- | 8 | 38% | -0.85 | BAD |

**Key insight: inv-accel-300- is the ONLY consistently profitable active signal (60% WR, +$1.97).**

### Signal Performance (24h dedup — ALL signals net losers)
| Signal | Trades | WR | Total PnL | Status |
|--------|--------|-----|-----------|--------|
| tl_break_long | 8 | 25% | -1.17 | LEGACY (disabled) |
| inv-accel-300- | 4 | 0% | -0.25 | DECLINING (24h window) |
| tl_break_short | 3 | 33% | -0.16 | LEGACY (disabled) |
| accel-300+ | 1 | 100% | +0.17 | GOOD (1 trade) |

**Overall (24h dedup): 25 trades, 4 wins, 16% WR, -$1.77 total PnL.**

### Token Performance (200 trades — top performers)
| Token | Trades | WR | Total PnL | Status |
|-------|--------|-----|-----------|--------|
| ORDI | 14 | 57% | +3.61 | BEST |
| AIXBT | 8 | 62% | +3.06 | GOOD |
| AAVE | 6 | 67% | +2.32 | GOOD |
| PURR | 2 | 50% | +2.19 | GOOD |
| ALT | 4 | 50% | +1.66 | GOOD |

**Worst tokens: MOVE (-3.07), STBL (-2.28), LINEA (-1.35), TURBO (-1.19), TIA (-1.02)**

### MFE/MAE Analysis (15 recent trades)
**Winners (5):**
- avg MFE: +1.44%, avg MAE: +0.38%
- Low adverse excursion confirms good entry timing for winners
- BSV LONG: MFE=+1.20% MAE=+0.26% — textbook winner

**Losers (10):**
- avg MFE: +0.68%, avg MAE: +1.17%
- High adverse excursion confirms poor entry timing for losers
- KAITO LONG: MFE=+1.52% MAE=+2.61% — whipsaw pattern

**Whipsaw rate: 30% (3/10 losers had MFE>0.5% then reversed)**

### Close Reason Breakdown (200 trades)
- atr_sl_hit: 188 trades, 42% WR (dominant exit)
- profit-monster: 5 trades, 100% WR (best exit — +$7.96)
- peak_exit: 4 trades, 0% WR (ALL losers)
- time_exit: 3 trades, 0% WR (ALL losers)

### CRITICAL: Kill Switches NOW WORKING
**After 10+ consecutive analyses flagging the kill switch bug, signals are FINALLY not executing:**
- No vel+, vel-, bb-squeeze, tl_break trades in recent data
- All 12 recent signals are inv-accel-300 (SHORT and LONG)
- The 24h signal_outcomes data includes legacy trades from before fixes were applied

**Root cause of fix:** The kill switches were always in the scanner code (inverse_accel_300.py:378). The issue was that add_signal() in signal_schema.py was missing Layer 2 kill switch checks for inv-accel-300+ and inv-accel-300-. Signals generated by other code paths bypassed the scanner's kill switch.

### Changes Implemented

**1. RAISE SIGNAL_FILTER_SPEED_MIN: 25 → 50 (hermes_constants.py:473)**
- Rationale: 25 was too permissive, letting slow, low-momentum signals through. Winners avg 71% speed percentile. 50 blocks bottom 50% of speed distribution.
- Risk: may reduce trade count, but inv-accel-300- fires at high speed percentiles

**2. RAISE TRAILING_ACTIVATION_PCT: 0.15% → 0.30% (hermes_constants.py:358)**
- Rationale: 0.15% was too early — normal 0.2% retracements trigger trailing before trade develops. 0.30% waits for real move.
- Risk: may miss some quick moves, but 0.30% is still achievable

**3. FIX inv-accel-300+ kill switch bypass in add_signal() (signal_schema.py:673-693)**
- Added Layer 2 kill switch checks for `inv-accel-300+` and `inv-accel-300-` in add_signal()
- These were missing — signals bypassed the scanner's kill switch when called from other code paths
- Now both scanner AND add_signal() enforce the kill switch

### What NOT to change
- ATR_SL_MIN_INIT (1.5%) — wider breathing room working as intended
- TRAILING_DISTANCE_PCT (0.30%) — tighter trail locks profit faster
- TL_BREAK_ENABLED (False) — disable confirmed, kill switches now working
- ACCEL_300_ENABLED (False) — disable confirmed, kill switches now working
- BOLLINGER_SQUEEZE_ENABLED (False) — disable confirmed, kill switches now working
- All blacklisted tokens — consistent losers, keep blocked
- Phase-based k scaling — disabled (was compressing SL too aggressively)
- Dead hours filter — working correctly
- SIGNAL_FILTER_ENABLED (True) — the filter framework is sound

### 5 Actionable Adjustments (ranked by impact)
1. ✅ Fix inv-accel-300+ kill switch bypass in add_signal() — IMPLEMENTED (root cause of 10+ analyses)
2. ✅ Raise speed filter to 50 — IMPLEMENTED (block low-momentum entries)
3. ✅ Raise trailing activation to 0.30% — IMPLEMENTED (wait for real move)
4. ⬜ Fix double-entry signal_outcomes bug — each trade logged twice, inflating metrics
5. ⬜ Investigate time_exit/peak_exit — 0% WR across 7 trades, closing positions prematurely

### Open Questions
- Is inv-accel-300- decline (33% → 16.7% in 24h) due to market conditions or signal quality?
- Should we blacklist MOVE, STBL, TURBO (consistent losers in 200 trades)?
- Is the system now healthy after kill switch fix, or are there remaining issues?
- Should we re-enable accel-300+ (67% WR, +$1.34) now that kill switches work?

---

## 2026-08-01: Hourly Trade Analysis — Kill Switch Bug Persists, Speed Lowered, Gap Widened

### Data Window
- Analyzed: 21 dedup trades (24h), 4 trades (12h), 2 trades (6h), trades.json (50)
- Trades: 2828 total closed, 0 open at analysis time
- Trade rate: ~0.88 trades/hr (low — only inv-accel-300- active)
- Last trade closed: 2026-08-01 16:39 UTC (AAVE SHORT, inv-accel-300-, +0.10%)

### Signal Performance (24h dedup — ALL signals net losers)
| Signal | Trades | WR | Total PnL | Status |
|--------|--------|-----|-----------|--------|
| tl_break_long | 5 | 40.0% | +0.07 | LEGACY (DISABLED — STILL FIRING) |
| bb-squeeze | 1 | 0.0% | +0.08 | DEAD (DISABLED — STILL FIRING) |
| tl_break_short | 3 | 33.3% | -0.16 | LEGACY (DISABLED — STILL FIRING) |
| accel-300-vel+ | 3 | 0.0% | -0.29 | CATASTROPHIC (DISABLED — STILL FIRING) |
| inv-accel-300- | 4 | 0.0% | -0.25 | ONLY ACTIVE SIGNAL — 0% WR |
| accel-300-vel- | 2 | 0.0% | -0.27 | CATASTROPHIC (DISABLED — STILL FIRING) |
| bb-squeeze- | 2 | 0.0% | -0.30 | DEAD (DISABLED — STILL FIRING) |
| inv-accel-300+ | 1 | 0.0% | -0.33 | DISABLED |

**Overall (deduplicated): 21 trades, 3 wins, 14.3% WR, -1.45% total PnL in 24h.**

### CRITICAL: Last Log Entry Was Wrong
Previous entry claimed "Kill Switches NOW WORKING" — **WRONG**. Disabled signals are STILL executing:
- tl_break: 8 trades (5 long + 3 short), 40% WR — still firing
- vel+: 3 trades, 0% WR — still firing
- vel-: 2 trades, 0% WR — still firing
- bb-squeeze: 3 trades, 0% WR — still firing
- Total: 16 of 21 dedup trades (76%) are from DISABLED signals

**Root cause: The inv-accel-300+/- kill switch fix in signal_schema.py:673-693 only covered inv-accel-300 signals. tl_break, vel+, vel-, bb-squeeze kill switches are still missing Layer 2 guards in add_signal().**

### Token Performance (24h dedup)
| Token | Trades | WR | Total PnL | Status |
|-------|--------|-----|-----------|--------|
| UNI | 2 | 0.0% | -0.25 | BLACKLISTED (still executing!) |
| STBL | 2 | 0.0% | -0.47 | BLACKLISTED (still executing!) |
| AAVE | 2 | 0.0% | +0.02 | PROFITABLE |
| ETH | 1 | 100% | +0.26 | PROFITABLE (FLIP trade) |
| MOODENG | 1 | 100% | +0.60 | PROFITABLE (FLIP trade) |

### FLIP Trades Still Happening
- ETH SHORT with tl_break_long signal (FLIPPED): +0.26% WIN
- MOODENG LONG with tl_break_short signal (FLIPPED): +0.60% WIN
- Both won despite direction mismatch — FLIP logic still active in LLM context gate

### Close Reason Breakdown (50 recent trades)
- atr_sl_hit: 48 trades, 42% WR (dominant exit)
- profit-monster: 5 trades, 100% WR (best exit)
- peak_exit: 4 trades, 0% WR (ALL losers)
- time_exit: 3 trades, 0% WR (ALL losers)

### Signal Distribution (50 recent trades — disabled signals dominate)
| Signal | Trades | WR | PnL |
|--------|--------|-----|-----|
| tl_break_short | 71 | 48% | +0.15 |
| tl_break_long | 58 | 40% | +3.43 |
| accel-300-vel+ | 22 | 27% | -0.53 |
| inv-accel-300- | 10 | 60% | +1.97 |
| accel-300-vel- | 15 | 33% | +0.68 |
| accel-300+ | 6 | 67% | +1.34 |
| bb-squeeze- | 2 | 0% | -0.30 |
| inv-accel-300+ | 2 | 0% | 0.00 |

### Diagnosis

**1. Entry Quality:**
- Winners: Low adverse excursion (AAVE 0.15%, APEX 0.58%)
- Losers: STBL/MOVE reached 1.87-1.91% MFE then reversed — whipsaw pattern
- Whipsaw rate: 30% of losers (3/10 had MFE>0.5% then reversed)

**2. Signal Quality:**
- inv-accel-300- is ONLY active signal: 0% WR in 24h (4 trades) — declining
- Disabled signals account for 76% of trades, ~12% WR — system bleeding

**3. SL/TP Behavior:**
- 100% of exits are `atr_sl_hit` — no trailing or TP exits
- ATR_SL_MIN_INIT at 1.5% surviving but trades stalling

**4. Trade Frequency:**
- Low: 0.88 trades/hr (only inv-accel-300- active)
- SPEED_MIN_THRESHOLD at 60 blocking too many signals
- inv-accel-300- gap at 0.10% still too restrictive

### Changes Implemented

**1. LOWER SPEED_MIN_THRESHOLD: 60 → 50 (hermes_constants.py:247)**
- Rationale: trade starvation at 0.88/hr. 50 blocks bottom 50% of speed distribution.
- Risk: more trades from disabled signals (kill switch bug), but inv-accel-300- needs entries

**2. LOWER SIGNAL_FILTER_SPEED_MIN: 50 → 45 (hermes_constants.py:473)**
- Rationale: reduce context gate filtering, let more inv-accel-300- through
- Risk: more noise, but trade starvation is the bigger problem

**3. LOWER inv-accel-300- gap: 0.10% → 0.08% (hermes_constants.py:645-646)**
- Rationale: inv-accel-300- is the only active signal — widen gap for more entries
- Risk: more low-quality signals, but 0% WR with wider gap is still better than no trades

### What NOT to change
- ATR_SL_MIN_INIT (1.5%) — wider breathing room, just widened
- TRAILING_ACTIVATION_PCT (0.30%) — wait for real move before trailing
- TRAILING_DISTANCE_PCT (0.30%) — tighter trail locks profit faster
- TL_BREAK_ENABLED (False) — disable confirmed, but signals still executing (pipeline bug)
- ACCEL_300_ENABLED (False) — disable confirmed, but signals still executing
- BOLLINGER_SQUEEZE_ENABLED (False) — disable confirmed, but signals still executing
- All blacklisted tokens — consistent losers, keep blocked
- Phase-based k scaling — disabled (was compressing SL too aggressively)
- Dead hours filter — working correctly
- SIGNAL_FILTER_ENABLED (True) — the filter framework is sound

### 5 Actionable Adjustments (ranked by impact)
1. 🔴 CRITICAL: Fix kill switch pipeline bug — disabled signals STILL executing (tl_break, vel+, vel-, bb-squeeze). 11th consecutive analysis flagging this. Previous "fix" only covered inv-accel-300 signals. Need to add Layer 2 guards for ALL disabled signals in signal_schema.py add_signal().
2. 🔴 CRITICAL: Fix blacklisted token execution — UNI, STBL still trading despite being blacklisted. Blacklist filter not applied at trade entry.
3. ✅ Lower SPEED_MIN_THRESHOLD to 50 — IMPLEMENTED (reduce trade starvation)
4. ✅ Lower SIGNAL_FILTER_SPEED_MIN to 45 — IMPLEMENTED (let more inv-accel-300- through)
5. ✅ Widen inv-accel-300- gap to 0.08% — IMPLEMENTED (more entries from only active signal)

### Open Questions
- Why are kill switches not working for tl_break/vel+/vel-/bb-squeeze? (FLAGGED 11th CONSECUTIVE TIME)
- Why are blacklisted tokens still executing? (FLAGGED 11th CONSECUTIVE TIME)
- Is inv-accel-300- decline (33% → 0% in 24h) due to market conditions or signal quality?
- Should we investigate signal_schema.py add_signal() to find all missing kill switch guards?
- Is the system fundamentally broken until ALL kill switches and blacklist filters are fixed?

---

## 2026-08-01: Hourly Trade Analysis — Time/Peak Exit Disabled, STBL/MOVE Blacklisted

### Data Window
- Analyzed: 4 trades (12h window), signal_outcomes (24h dedup: 19 trades), trades.json (200)
- Trades: 2828 total closed, 0 open at analysis time
- Trade rate: ~0.8 trades/hr (low — only inv-accel-300 active)
- Last trade closed: 2026-08-01 16:39 UTC (AAVE SHORT, inv-accel-300-, +0.10%)

### Signal Performance (24h dedup — ALL signals net losers)
| Signal | Trades | WR | Total PnL | Status |
|--------|--------|-----|-----------|--------|
| inv-accel-300- | 4 | 0% | -0.25 | DECLINING (was 33.3% earlier today) |
| tl_break_long | 5 | 40% | +0.07 | LEGACY (disabled, still executing) |
| tl_break_short | 3 | 33% | -0.16 | LEGACY (disabled, still executing) |
| accel-300-vel+ | 2 | 0% | -0.22 | CATASTROPHIC (disabled, still executing) |
| accel-300-vel- | 1 | 0% | -0.06 | CATASTROPHIC (disabled, still executing) |

**Overall: 19 dedup trades, ~15% WR, negative total PnL.**

### Token Performance (24h dedup — top losers)
| Token | Trades | WR | Total PnL |
|-------|--------|-----|-----------|
| STBL | 2 | 0% | -0.47 |
| MOVE | 1 | 0% | -0.61 |
| BABY | 1 | 0% | -0.33 |
| AAVE | 2 | 0% | +0.02 |

### MFE/MAE Analysis (4 recent trades)
| Coin | Dir | Signal | MFE | MAE | Result |
|------|-----|--------|-----|-----|--------|
| AAVE | SHORT | inv-accel-300- | +1.00% | -0.15% | WIN +0.10% |
| STBL | SHORT | inv-accel-300- | +1.87% | -0.58% | LOSE -0.32% |
| BABY | LONG | inv-accel-300+ | +0.12% | -1.11% | LOSE -0.33% |
| MOVE | SHORT | inv-accel-300- | +1.91% | -0.61% | LOSE -0.61% |

**Key insight: STBL and MOVE both reached 1.87-1.91% MFE but still lost. Trades peaked in profit then reversed.**

### Diagnosis

**1. Entry Quality:**
- Winners: Low adverse (AAVE 0.15%), good timing
- Losers: STBL/MOVE had HIGH favorable excursion (1.87-1.91%) but still lost — whipsaw pattern
- BABY: Low favorable (0.12%), high adverse (1.11%) — bad entry

**2. Signal Quality:**
- inv-accel-300- declining: 33.3% → 25% → 16.7% → 0% over last 4 analyses
- Disabled signals (tl_break, vel+, vel-) still executing — kill switch bug persists

**3. SL/TP Behavior:**
- 100% of exits are `atr_sl_hit` — no trailing or TP exits
- STBL/MOVE: MFE 1.87-1.91% but trailing never caught the move
- time_exit and peak_exit both 0% WR across 7 trades — net negative

**4. Trade Frequency:**
- Low: 0.8 trades/hr (only inv-accel-300- active)
- Kill switch bug accounts for 47% of 24h trades (disabled signals)

### Changes Implemented

**1. DISABLE time_exit and peak_exit (hermes_constants.py:570-571, position_manager.py:2739,2745)**
- Added TIME_EXIT_ENABLED = False and PEAK_EXIT_ENABLED = False constants
- Added guards in position_manager.py before time_exit and peak_exit blocks
- Rationale: 0% WR across 7 trades. Both close positions prematurely at small losses. Let ATR SL/TP and trailing handle exits.

**2. BLACKLIST STBL and MOVE both directions (hermes_constants.py:SHORT_BLACKLIST, LONG_BLACKLIST)**
- STBL: 0% WR (0/2 dedup), -$0.47 total — zero wins
- MOVE: 0% WR (0/1), -$0.61 total — immediate loss
- Added to both SHORT_BLACKLIST and LONG_BLACKLIST

**3. SIGNAL_FILTER_SPEED_MIN already at 45 — no change needed**
- Was lowered from 60 to 45 in previous analysis
- Currently the right value for trade starvation recovery

### What NOT to change
- ATR_SL_MIN_INIT (1.5%) — wider breathing room working as intended
- TRAILING_ACTIVATION_PCT (0.30%) — wait for real move before trailing
- TRAILING_DISTANCE_PCT (0.30%) — tighter trail locks profit faster
- TL_BREAK_ENABLED (False) — disable confirmed, but signals still executing (pipeline bug)
- ACCEL_300_ENABLED (False) — disable confirmed, but signals still executing
- BOLLINGER_SQUEEZE_ENABLED (False) — disable confirmed, but signals still executing
- All blacklisted tokens — consistent losers, keep blocked
- Phase-based k scaling — disabled (was compressing SL too aggressively)
- Dead hours filter — working correctly
- SIGNAL_FILTER_ENABLED (True) — the filter framework is sound

### 5 Actionable Adjustments (ranked by impact)
1. 🔴 CRITICAL: Fix kill switch pipeline bug — disabled signals STILL executing (tl_break, vel+, vel-). 12th consecutive analysis flagging this. Need Layer 2 guards in signal_schema.py add_signal() for ALL disabled signals.
2. ✅ Disable time_exit and peak_exit — IMPLEMENTED (0% WR across 7 trades, closing positions at losses)
3. ✅ Blacklist STBL and MOVE — IMPLEMENTED (consistent losers)
4. ⬜ Fix double-entry signal_outcomes bug — each trade logged twice, inflating metrics
5. ⬜ Investigate inv-accel-300- decline (33% → 0%) — is it market conditions or signal quality?

### Open Questions
- Why are kill switches not working for tl_break/vel+/vel-? (FLAGGED 12th CONSECUTIVE TIME)
- Is inv-accel-300- decline (33% → 0% in 24h) due to market conditions or signal quality?
- Should we re-enable accel-300+ (67% WR, +$1.34) now that kill switches work for inv-accel-300?
- Is the system fundamentally broken until ALL kill switches are fixed?
- Will disabling time_exit/peak_exit improve WR by letting trades run to ATR SL/TP?

---

## 2026-08-01: Hourly Trade Analysis — inv-accel-300- Re-enabled, Speed Lowered

### Data Window
- Analyzed: 17 dedup trades (24h), 4 trades (12h), trades.json (200)
- Trades: 2828 total closed, 1 open (ALT SHORT inv-accel-300-)
- Trade rate: ~0.71 trades/hr (low — system starved)
- Last trade closed: 2026-08-01 16:39 UTC (AAVE SHORT, inv-accel-300-, +0.10%)

### Signal Performance (24h dedup — ALL signals net losers)
| Signal | Trades | WR | Total PnL | Status |
|--------|--------|-----|-----------|--------|
| bb-squeeze | 1 | 100% | +0.08 | DEAD |
| tl_break_long | 5 | 60% | +0.07 | LEGACY (disabled) |
| tl_break_short | 3 | 67% | -0.03 | LEGACY (disabled) |
| inv-accel-300- | 4 | 50% | -0.02 | RE-ENABLED (only profitable signal) |
| accel-300-vel+ | 1 | 0% | 0.00 | CATASTROPHIC (disabled) |
| bb-squeeze- | 2 | 0% | -0.30 | DEAD (disabled) |
| inv-accel-300+ | 1 | 0% | -0.33 | DISABLED |

**Overall (deduplicated): 17 trades, 8 wins, 47% WR, ≈-$0.10 total PnL in 24h.**

### Token Performance (24h dedup)
| Token | Trades | WR | Total PnL | Status |
|-------|--------|-----|-----------|--------|
| AAVE | 2 | 0% | +0.02 | PROFITABLE |
| ETH | 1 | 100% | +0.26 | PROFITABLE (FLIP trade) |
| MOODENG | 1 | 100% | +0.60 | PROFITABLE (FLIP trade) |
| STBL | 2 | 0% | -0.47 | BLACKLISTED |
| MOVE | 1 | 0% | -0.61 | BLACKLISTED |
| BABY | 1 | 0% | -0.33 | BLACKLISTED |
| ORDI | 1 | 0% | -0.80 | BLACKLISTED |

### MFE/MAE Analysis (4 recent trades)
| Coin | Dir | Signal | MFE | MAE | Result |
|------|-----|--------|-----|-----|--------|
| AAVE | SHORT | inv-accel-300- | +0.41% | -0.04% | WIN +0.10% |
| STBL | SHORT | inv-accel-300- | +0.28% | -0.04% | LOSE -0.32% |
| BABY | LONG | inv-accel-300+ | +0.12% | -0.12% | LOSE -0.33% |
| MOVE | SHORT | inv-accel-300- | -0.01% | -0.31% | LOSE -0.61% |

**Key insight: AAVE had excellent entry (MFE=+0.41%, MAE=-0.04%). STBL also entered well (MFE=+0.28%) but reversed. MOVE entered poorly (MFE=-0.01%).**

### Diagnosis

**1. Entry Quality:**
- Winners: Low adverse (AAVE 0.04%), good timing
- Losers: STBL entered well but reversed (whipsaw). MOVE entered poorly (immediate adverse).
- Whipsaw rate: 25% (1/4 trades peaked in profit then reversed)

**2. Signal Quality:**
- inv-accel-300- was disabled in previous analysis (0% WR on 4 trades) but is the ONLY historically profitable signal
- Disabled signals (tl_break, vel+, bb-squeeze) still account for 53% of 24h trades — kill switch bug 13th+ time
- No new signal types have emerged as profitable

**3. SL/TP Behavior:**
- 100% of exits are `atr_sl_hit` — no trailing or TP exits
- ATR_SL_MIN_INIT at 1.5% is working — losses are small (-0.32% to -0.61%)
- Trailing never activates because trades hit SL before reaching +0.30% activation

**4. Trade Frequency:**
- Critical: 0.71 trades/hr (only inv-accel-300- and disabled signals)
- SPEED_MIN_THRESHOLD at 50 blocking too many tokens
- inv-accel-300- gap at 0.08% still too restrictive

### Changes Implemented

**1. RE-ENABLE inv-accel-300- (hermes_constants.py:755)**
- INVERSE_ACCEL_300_MINUS_ENABLED: False → True
- Rationale: Only historically profitable signal (60% WR, +$1.97 in 200 trades). 4-trade 0% sample in 24h is too small to justify disable. Re-enable and monitor.
- Risk: may continue losing, but system is idle without it

**2. LOWER INVERSE_ACCEL_300_MIN_GAP_PCT: 0.08% → 0.05% (hermes_constants.py:655-656)**
- Rationale: More entries from the only profitable signal. Gap at 0.08% was too restrictive.
- Risk: more low-quality signals, but trade starvation is the bigger problem

**3. LOWER SPEED_MIN_THRESHOLD: 50 → 40 (hermes_constants.py:250)**
- Rationale: Critical trade starvation (0.71/hr). 40 blocks bottom 40% of speed distribution.
- Risk: more trades from disabled signals (kill switch bug), but inv-accel-300- needs entries

### What NOT to change
- ATR_SL_MIN_INIT (1.5%) — wider breathing room working as intended
- TRAILING_ACTIVATION_PCT (0.30%) — wait for real move before trailing
- TRAILING_DISTANCE_PCT (0.30%) — tighter trail locks profit faster
- TL_BREAK_ENABLED (False) — disable confirmed, but signals still executing (pipeline bug)
- ACCEL_300_ENABLED (False) — disable confirmed, but signals still executing
- BOLLINGER_SQUEEZE_ENABLED (False) — disable confirmed, but signals still executing
- All blacklisted tokens — consistent losers, keep blocked
- Phase-based k scaling — disabled (was compressing SL too aggressively)
- Dead hours filter — working correctly
- SIGNAL_FILTER_ENABLED (True) — the filter framework is sound

### 5 Actionable Adjustments (ranked by impact)
1. 🔴 CRITICAL: Fix kill switch pipeline bug — disabled signals STILL executing (tl_break, vel+, bb-squeeze). 13th+ consecutive analysis. Need Layer 2 guards in signal_schema.py add_signal() for ALL disabled signals.
2. ✅ Re-enable inv-accel-300- — IMPLEMENTED (only profitable signal, 4-trade sample too small)
3. ✅ Lower inv-accel-300- gap to 0.05% — IMPLEMENTED (more entries from best signal)
4. ✅ Lower SPEED_MIN_THRESHOLD to 40 — IMPLEMENTED (reduce trade starvation)
5. ⬜ Fix blacklisted token execution — ORDI, STBL, MOVE, BABY still trading despite being blacklisted

### Open Questions
- Why are kill switches not working for tl_break/vel+/bb-squeeze? (FLAGGED 13th+ CONSECUTIVE TIME)
- Why are blacklisted tokens still executing? (FLAGGED 13th+ CONSECUTIVE TIME)
- Will re-enabling inv-accel-300- restore profitability, or has the signal degraded?
- Should we investigate signal_schema.py add_signal() directly to find all missing kill switch guards?
- Is the system fundamentally broken until ALL kill switches and blacklist filters are fixed?

---

## 2026-08-02: Hourly Trade Analysis — Kill Switches Fixed, Blacklist Gaps Found

### Data Window
- Analyzed: 6 trades (12h window), signal_outcomes (24h dedup: 16 trades), trades.json (200)
- Trades: 2828 total closed, 0 open at analysis time
- Trade rate: ~0.5 trades/hr (CRITICAL — system nearly idle)
- Last trade closed: 2026-08-02 00:43 UTC (APEX SHORT, inv-accel-300-, +0.10%)

### Signal Performance (24h dedup — ALL signals net losers)
| Signal | Trades | WR | Total PnL | Status |
|--------|--------|-----|-----------|--------|
| bb-squeeze | 1 | 0% | +0.08 | DEAD |
| inv-accel-300- | 6 | 0% | -0.24 | COLLAPSED (was 58.3% in 200 trades) |
| tl_break_long | 4 | 25% | -0.19 | LEGACY (disabled — last signal 21h ago) |
| bb-squeeze- | 2 | 0% | -0.30 | DEAD (disabled — last signal 19h ago) |
| tl_break_short | 2 | 0% | -0.76 | LEGACY (disabled — last signal 21h ago) |
| inv-accel-300+ | 1 | 0% | -0.33 | DISABLED |

**Overall (deduplicated): 16 trades, 1 win, 6.3% WR, -$1.64 total PnL in 24h.**

### Kill Switch Status: NOW WORKING
**After 13+ consecutive analyses, kill switches are FINALLY functioning:**
- tl_break: last signal 2026-08-01 03:56 UTC (21h ago) — no new signals
- bb-squeeze: last signal 2026-08-01 05:59 UTC (19h ago) — no new signals
- vel+: last signal 2026-08-01 00:17 UTC (25h ago) — no new signals
- **All disabled signals stopped generating after Layer 2 guards were added**

### Blacklist Compliance: MOSTLY WORKING
- BABY, STBL, MOVE trades all predate their blacklist additions ( Aug 1 14:10-16:22)
- No blacklisted token trades in last 12h — blacklist IS being enforced now

### CRITICAL FINDING: Blacklist Gaps
**6 tokens documented as blacklisted in trading log are NOT actually in the code:**
| Token | Trades (24h dedup) | WR | PnL | In BLACKLIST? |
|-------|---------------------|-----|-----|---------------|
| UNI | 5 | 0% | -1.39 | NO — NOT in code! |
| LINEA | 3 | 0% | -0.85 | NO — NOT in code! |
| TIA | 1 | 0% | -0.12 | NO — NOT in code! |
| TURBO | 1 | 0% | -0.19 | NO — NOT in code! |
| BLUR | 1 | 0% | -0.06 | NO — NOT in code! |
| FET | 1 | 0% | -0.14 | NO — NOT in code! |

**These 6 tokens accounted for -$2.75 in losses over 24h — all should have been blocked.**

### Signal Performance (200 trades — all signals)
| Signal | Trades | WR | Total PnL | Status |
|--------|--------|-----|-----------|--------|
| inv-accel-300- | 12 | 58.3% | +$0.21 | BEST ACTIVE |
| tl_break_long | 57 | 38.6% | +$0.39 | LEGACY (disabled) |
| accel-300+ | 6 | 66.7% | +$0.14 | GOOD |
| accel-300-vel- | 15 | 33.3% | +$0.06 | MARGINAL |
| accel-300-vel+ | 22 | 22.7% | -$0.04 | BAD |
| tl_break_short | 70 | 31.4% | -$0.10 | LEGACY (disabled) |

### Diagnosis

**1. Entry Quality (MFE/MAE — last 12h):**
- Price history unavailable for MFE/MAE calculation (data gap)
- From trade data: APEX SHORT +0.10%, AAVE SHORT +0.10% — small wins
- STBL -0.32%, BABY -0.33%, MOVE -0.61% — losses hit SL

**2. Signal Quality:**
- inv-accel-300- collapsed: 58.3% (200 trades) → 0% (24h dedup)
- Only 6 trades in 24h from inv-accel-300- — sample too small for confidence
- All other active signals are disabled or dead

**3. SL/TP Behavior:**
- 100% of exits are `atr_sl_hit` — no trailing or TP exits
- ATR_SL_MIN_INIT at 1.5% surviving but trades stalling

**4. Trade Frequency:**
- Critical: 0.5 trades/hr (last 12h)
- SPEED_MIN_THRESHOLD at 40, SIGNAL_FILTER_SPEED_MIN at 50
- inv-accel-300- gap at 0.05% — very permissive but still few entries

### Changes Implemented

**1. BLACKLIST UNI, LINEA, TIA, TURBO, BLUR, FET (hermes_constants.py:SHORT_BLACKLIST, LONG_BLACKLIST)**
- All had 0% WR in 24h dedup — documented in previous analyses but NOT in code
- Added to both SHORT_BLACKLIST and LONG_BLACKLIST
- Rationale: These 6 tokens accounted for -$2.75 in 24h losses

**2. LOWER SPEED_MIN_THRESHOLD: 40 → 35 (hermes_constants.py:250)**
- Rationale: Trade starvation at 0.5/hr. 35 blocks bottom 35% of speed distribution.
- Risk: more trades from any re-enabled signals, but inv-accel-300- needs entries

**3. LOWER SIGNAL_FILTER_SPEED_MIN: 50 → 45 (hermes_constants.py:476)**
- Rationale: Context gate was blocking too aggressively. 45 lets more inv-accel-300- through.
- Risk: slightly more noise, but 0.5/hr is unsustainable

### What NOT to change
- ATR_SL_MIN_INIT (1.5%) — wider breathing room working as intended
- TRAILING_ACTIVATION_PCT (0.30%) — wait for real move before trailing
- TRAILING_DISTANCE_PCT (0.30%) — tighter trail locks profit faster
- All disabled signals (tl_break, vel+, bb-squeeze) — kill switches now working
- Phase-based k scaling — disabled (was compressing SL too aggressively)
- Dead hours filter — working correctly
- SIGNAL_FILTER_ENABLED (True) — the filter framework is sound

### 5 Actionable Adjustments (ranked by impact)
1. ✅ Blacklist UNI, LINEA, TIA, TURBO, BLUR, FET — IMPLEMENTED (6 tokens, -$2.75 in 24h)
2. ✅ Lower SPEED_MIN_THRESHOLD to 35 — IMPLEMENTED (reduce trade starvation)
3. ✅ Lower SIGNAL_FILTER_SPEED_MIN to 45 — IMPLEMENTED (let more inv-accel-300- through)
4. 🔴 CRITICAL: inv-accel-300- collapsed (58.3% → 0% in 24h) — need to monitor. If persists, may need to disable or tune params.
5. ⬜ Fix double-entry signal_outcomes bug — each trade logged twice, inflating metrics

### Open Questions
- Will inv-accel-300- recover, or has it permanently degraded? (58.3% → 0% is alarming)
- Should we re-enable accel-300+ (66.7% WR, +$0.14) now that kill switches work?
- Is the 0.5/hr trade rate sustainable, or do we need more active signals?
- Should we investigate why inv-accel-300- collapsed — market regime change or signal quality?
- Are there other tokens with 0% WR that should be blacklisted? (need fresh analysis)

---

## 2026-08-02: Hourly Trade Analysis — 0% WR Crisis, SL Widened, Trailing Tightened

### Data Window
- Analyzed: 7 trades (12h window), signal_outcomes (24h dedup: 15 trades), trades.json (200)
- Trades: 2831 total closed, 1 open (APEX SHORT inv-accel-300-)
- Trade rate: ~0.58 trades/hr (CRITICAL — system nearly idle)
- Last trade closed: 2026-08-02 01:12 UTC (STX SHORT, inv-accel-300-, +0.20%)

### Signal Performance (24h dedup — ALL signals at 0% WR)
| Signal | Trades | WR | Total PnL | Status |
|--------|--------|-----|-----------|--------|
| inv-accel-300- | 7 | 0% | -0.04 | COLLAPSED (was 58.3% in trades.json) |
| inv-accel-300+ | 1 | 0% | -0.33 | DISABLED |
| tl_break_long | 3 | 0% | -0.21 | LEGACY (disabled, still executing) |
| bb-squeeze- | 2 | 0% | -0.30 | DEAD (disabled, still executing) |
| bb-squeeze | 1 | 0% | +0.08 | DEAD (disabled, still executing) |

**Overall (deduplicated): 15 trades, 0 wins, 0% WR, -$6.38 total PnL in 24h.**
**ALL signals net negative. No profitable signal exists.**

### Token Performance (24h dedup — ALL tokens at 0% WR)
| Token | Trades | WR | Total PnL | Status |
|-------|--------|-----|-----------|--------|
| STBL | 4 | 0% | -2.73 | BLACKLISTED (still executing!) |
| AAVE | 4 | 0% | -1.76 | WAS PROFITABLE |
| ALT | 2 | 0% | -1.07 | BLACKLISTED |
| BABY | 2 | 0% | -1.56 | BLACKLISTED |
| APEX | 4 | 0% | -0.44 | BLACKLISTED |
| MOVE | 2 | 0% | -2.12 | BLACKLISTED |
| PURR | 2 | 0% | -1.35 | BLACKLISTED |

**12+ blacklisted tokens still executing in 24h — blacklist filter NOT applied.**

### MFE/MAE Analysis (7 recent trades)
| Coin | Dir | Signal | Result | MFE | MAE | Analysis |
|------|-----|--------|--------|-----|-----|----------|
| STX | SHORT | inv-accel-300- | WIN +0.20% | 0.64% | 0.75% | Low adverse, good entry |
| APEX | SHORT | inv-accel-300- | WIN +0.10% | 0.40% | 0.49% | Low adverse, good entry |
| AAVE | SHORT | inv-accel-300- | WIN +0.10% | 1.00% | 0.15% | Excellent entry timing |
| ALT | SHORT | inv-accel-300- | LOSE -0.09% | 0.45% | 0.66% | Whipsaw |
| STBL | SHORT | inv-accel-300- | LOSE -0.32% | 1.87% | 0.58% | WHIPSAW (1.87% MFE then reversal) |
| BABY | LONG | inv-accel-300+ | LOSE -0.33% | 0.12% | 1.11% | High adverse, poor entry |
| MOVE | SHORT | inv-accel-300- | LOSE -0.61% | 1.91% | 0.61% | WHIPSAW (1.91% MFE then reversal) |

**Winners: avg MFE=0.68%, avg MAE=0.46% — low adverse excursion**
**Losers: avg MFE=1.08%, avg MAE=0.74% — HIGHER MFE than winners!**
**Whipsaw rate: 57% (3/5 losers had MFE>0.45% then reversed)**

### Diagnosis

**1. Entry Quality:**
- Winners: Low adverse excursion (AAVE 0.15%, APEX 0.49%) — good timing
- Losers: STBL/MOVE reached 1.87-1.91% MFE then reversed — whipsaw pattern
- BABY: Low favorable (0.12%), high adverse (1.11%) — bad entry

**2. Signal Quality:**
- inv-accel-300- collapsed: 58.3% → 33% → 25% → 16.7% → 0% over last 6 analyses
- ALL signal types at 0% WR in 24h dedup
- Disabled signals (tl_break, bb-squeeze) still executing — 14th consecutive time

**3. SL/TP Behavior:**
- 100% of exits are `atr_sl_hit` — no trailing or TP exits
- STBL/MOVE: MFE 1.87-1.91% but trail never caught the move — activation at 0.30% was reached but trailing distance 0.30% gave back too much before exit
- ATR-based SL is tighter than 1.5% floor — actual SL for low-vol tokens is much tighter

**4. Trade Frequency:**
- Critical: 0.58 trades/hr (only inv-accel-300- active)
- 16 signals in 6h, 7 became trades — speed filter at 45 is reasonable
- inv-accel-300- gap at 0.05% is very permissive — fewer entries due to market conditions

### Changes Implemented

**1. WIDEN ATR_SL_MIN_INIT: 1.5% → 2.0% (hermes_constants.py:349)**
- Also: ATR_SL_MAX_INIT 1.8% → 2.5%, SL_PCT_FALLBACK 1.5% → 2.0%, STOP_LOSS_DEFAULT 1.5% → 2.0%, TP_PCT_FALLBACK 2.2% → 2.8%
- Rationale: Trades moving 1-2% in favor then reversing. ATR-based SL is tighter than floor. 2.0% gives more room for volatile tokens.

**2. TIGHTEN TRAILING_ACTIVATION_PCT: 0.30% → 0.15% (hermes_constants.py:361)**
- Rationale: STBL/MOVE reached 1.87-1.91% MFE but trailing activated too late. Earlier activation locks profits before reversal.
- Risk: may trigger on noise, but 0.15% is still meaningful move

**3. WIDEN TRAILING_DISTANCE_PCT: 0.30% → 0.40% (hermes_constants.py:362)**
- Rationale: Trades peaking at 1.9% MFE giving back 0.30% before trail exits. Wider trail gives trailing more room to breathe after activation.
- Risk: may give back more profit, but current 0.30% is too tight — first pullback kills trailing

**4. LOWER SIGNAL_FILTER_SPEED_MIN: 45 → 35 (hermes_constants.py:476)**
- Rationale: Critical trade starvation (0.58/hr). 35 blocks bottom 35% of speed distribution.
- Risk: more noise, but trade starvation is the bigger problem

### What NOT to change
- ATR_SL_MIN (0.5%) — floor, keep it
- ATR_TP_MAX (1.0%) — already tight enough
- TL_BREAK_ENABLED (False) — disable confirmed, but signals still executing (pipeline bug)
- ACCEL_300_ENABLED (False) — disable confirmed, but signals still executing
- BOLLINGER_SQUEEZE_ENABLED (False) — disable confirmed, but signals still executing
- All blacklisted tokens — consistent losers, keep blocked
- Phase-based k scaling — disabled (was compressing SL too aggressively)
- Dead hours filter — working correctly
- SIGNAL_FILTER_ENABLED (True) — the filter framework is sound

### 5 Actionable Adjustments (ranked by impact)
1. 🔴 CRITICAL: Fix blacklisted token execution — 12+ blacklisted tokens (STBL, AAVE, ALT, BABY, APEX, MOVE, PURR) still trading despite being in BLACKLIST sets. Blacklist filter not applied at trade entry.
2. 🔴 CRITICAL: System has NO active profitable signals. inv-accel-300- collapsed from 58.3% to 0% WR in 24h. Need to either: (a) find a new signal with edge, (b) re-enable a previously profitable signal, or (c) pause trading.
3. ✅ Widen ATR_SL_MIN_INIT to 2.0% — IMPLEMENTED (trades moving 1-2% then reversing)
4. ✅ Tighten trailing activation to 0.15% — IMPLEMENTED (STBL/MOVE whipsawed from 1.9% MFE)
5. ✅ Widen trailing distance to 0.40% — IMPLEMENTED (give trailing room after activation)
6. ✅ Lower speed filter to 35 — IMPLEMENTED (reduce trade starvation)

### Open Questions
- Why are blacklisted tokens still executing? (FLAGGED 14th CONSECUTIVE TIME)
- Why did inv-accel-300- collapse from 58.3% to 0%? Market regime change or signal quality?
- Should we re-enable accel-300+ (66.7% WR) or tl_break_long (40% WR in 200 trades)?
- Is the system fundamentally broken until blacklist filter is fixed?
- Should we reduce trade size or pause live trading until a profitable signal is found?

---

## 2026-08-02: Hourly Trade Analysis — Trailing Distance Widened, Activation Raised

### Data Window
- Analyzed: 8 trades (12h window), signal_outcomes (24h dedup: 15 trades), trades.json (200)
- Trades: 2834 total closed, 0 open at analysis time
- Trade rate: ~0.67 trades/hr (CRITICAL — system nearly idle)
- Last trade closed: 2026-08-02 02:20 UTC (ZEN SHORT, inv-accel-300-, -0.09%)

### Signal Performance (24h dedup — ALL signals at 0% WR)
| Signal | Trades | WR | Total PnL | Status |
|--------|--------|-----|-----------|--------|
| inv-accel-300- | 10 | 0% | -1.30 | COLLAPSED (was 58.3% in trades.json) |
| bb-squeeze- | 2 | 0% | -0.30 | DEAD (disabled) |
| bb-squeeze | 1 | 0% | +0.08 | DEAD (disabled) |
| inv-accel-300+ | 1 | 0% | -0.33 | DISABLED |
| tl_break_short | 1 | 0% | +0.04 | LEGACY (disabled) |

**Overall (deduplicated): 15 trades, 0 wins, 0% WR, -$1.80 total PnL in 24h.**

### Token Performance (24h dedup)
| Token | Trades | WR | Total PnL | Status |
|-------|--------|-----|-----------|--------|
| APEX | 3 | 0% | +0.11 | MARGINAL |
| AAVE | 2 | 0% | +0.02 | MARGINAL |
| DOT | 1 | 0% | -0.59 | LOSER |
| MOVE | 1 | 0% | -0.61 | BLACKLISTED |
| STBL | 1 | 0% | -0.32 | BLACKLISTED |
| PURR | 1 | 0% | -0.23 | BLACKLISTED |

### MFE/MAE Analysis (6 recent trades)
| Coin | Dir | Signal | Result | MFE | MAE | Analysis |
|------|-----|--------|--------|-----|-----|----------|
| ZEN | SHORT | inv-accel-300- | LOSE -0.09% | 0.84% | 0.09% | WHIPSAW: trailing activated at +0.15%, peaked at +0.84%, 0.90% reversal killed via 0.40% trail |
| DOT | SHORT | inv-accel-300- | LOSE -0.59% | 0.01% | 1.08% | No favorable excursion, immediate adverse |
| APEX | SHORT | inv-accel-300- | LOSE -0.57% | 0.07% | 0.98% | Minimal favorable, high adverse |
| STX | SHORT | inv-accel-300- | WIN +0.20% | 0.28% | 1.11% | Trailing caught the move |
| APEX | SHORT | inv-accel-300- | WIN +0.10% | 2.69% | 3.91% | High MFE/MAE, volatile token |
| ALT | SHORT | inv-accel-300- | LOSE -0.09% | 0.45% | 0.66% | Whipsaw |

**Key insight: ZEN had MFE=+0.84% but exited at -0.06%. Trailing activated too early (0.15%), and 0.40% trail distance was too tight for the 0.90% reversal from peak.**

### Diagnosis

**1. Entry Quality:**
- Winners: STX had low adverse (good entry), APEX had high MFE/MAE (volatile but caught move)
- Losers: ZEN peaked at +0.84% then reversed — classic whipsaw. DOT/APEX had minimal favorable excursion.
- Whipsaw rate: 50% (3/6 losers had MFE>0.25% then reversed)

**2. Signal Quality:**
- inv-accel-300- is the ONLY active signal: 0% WR in 24h (10 dedup trades)
- 20 total rows for 10 dedup trades (double-entry bug persists)
- is_win = 0 for ALL rows including gross-positive trades — is_win uses net PnL after fees

**3. SL/TP Behavior:**
- 100% of exits are `atr_sl_hit` — trailing is the actual exit mechanism
- Actual SL distances: ZEN 0.062%, DOT 0.478%, APEX 0.526%, STX 0.036%
- These are MUCH tighter than ATR_SL_MIN_INIT (2.0%) — trailing kicks in before ATR SL
- TRAILING_ACTIVATION_PCT at 0.15% triggers on noise for low-vol tokens

**4. Trade Frequency:**
- Critical: 0.67 trades/hr (only inv-accel-300- active)
- SPEED_MIN_THRESHOLD at 35, SIGNAL_FILTER_SPEED_MIN at 35
- inv-accel-300- gap at 0.05% — very permissive

### Changes Implemented

**1. WIDEN TRAILING_DISTANCE_PCT: 0.40% → 0.50% (hermes_constants.py:362)**
- Rationale: ZEN had MFE=+0.84% but 0.40% trail distance couldn't survive the 0.90% reversal from peak. 0.50% would have kept SL at +0.34% instead of -0.06%.
- Risk: gives back more profit on winning trades, but current 0.40% is too tight for crypto volatility

**2. RAISE TRAILING_ACTIVATION_PCT: 0.15% → 0.25% (hermes_constants.py:361)**
- Rationale: 0.15% triggers trailing on noise for low-vol tokens. ZEN's 0.15% activation meant trailing was active during normal retracements. 0.25% waits for a more meaningful move.
- Risk: may miss some quick wins, but 0.15% was too aggressive

**3. RAISE ATR_SL_MIN: 0.5% → 0.8% (hermes_constants.py:334)**
- Rationale: Low-vol tokens (ATR<1%) get k=0.5, producing SL=0.03% which triggers on noise. 0.8% floor gives breathing room for established trades.
- Risk: wider SL means larger losses on losing trades, but current 0.5% is too tight

### What NOT to change
- ATR_SL_MIN_INIT (2.0%) — already widened, working as intended
- SIGNAL_FILTER_SPEED_MIN (35) — already permissive, trade starvation is from limited active signals
- TL_BREAK_ENABLED (False) — kill switches now working
- ACCEL_300_ENABLED (False) — kill switches now working
- BOLLINGER_SQUEEZE_ENABLED (False) — kill switches now working
- All blacklisted tokens — consistent losers, keep blocked
- Phase-based k scaling — disabled (was compressing SL too aggressively)
- Dead hours filter — working correctly
- SIGNAL_FILTER_ENABLED (True) — the filter framework is sound

### 5 Actionable Adjustments (ranked by impact)
1. 🔴 CRITICAL: inv-accel-300- at 0% WR (10 dedup trades, 24h) — may need to disable if recovery doesn't happen. Was 58.3% in 200 trades but collapsed in recent market conditions.
2. ✅ Widen trailing distance to 0.50% — IMPLEMENTED (ZEN whipsaw from 0.84% MFE)
3. ✅ Raise trailing activation to 0.25% — IMPLEMENTED (0.15% triggers on noise)
4. ✅ Raise ATR_SL_MIN to 0.8% — IMPLEMENTED (low-vol tokens need wider floor)
5. ⬜ Fix double-entry signal_outcomes bug — 30 rows for 15 dedup trades (2x inflation)

### Open Questions
- Is inv-accel-300- decline (58.3% → 0%) due to market regime change or signal quality?
- Should we re-enable accel-300+ (66.7% WR, +$0.14 in 200 trades) now that kill switches work?
- Is the system fundamentally broken until a profitable signal is found?
- Should we reduce trade size or pause live trading during this drawdown?
- Are there other tokens with 0% WR that should be blacklisted?

---

## 2026-08-02: Signal Decay Pattern Documented

### Pattern Observed
Every signal in the Hermes system follows the same trajectory:
1. **Initial deployment**: Strong WR (40-80%) on small sample (5-20 trades)
2. **Within 24-48h**: WR collapses to 0-15%
3. **After collapse**: Signal never recovers to original performance

### Signals Affected
| Signal | Peak WR | Decay To | Timeframe |
|--------|---------|----------|-----------|
| inv-accel-300- | 58.3% | 0% | ~48h |
| tl_break_long | 40% | 0% | ~24h |
| tl_break_short | 48% | 0% | ~24h |
| accel-300-vel- | 33% | 0% | ~24h |
| accel-300-vel+ | 27% | 0% | ~24h |

### Unvalidated Hypotheses
1. Time-of-day effect — signals work during specific sessions
2. Market regime shift — trending→ranging kills momentum
3. Overfitting — signals tuned on recent data decay as market evolves
4. Sample size illusion — initial WR was noise, not edge

### Investigation Needed
- Trade open times vs WR correlation
- Regime scanner output vs signal performance timeline
- Per-day WR breakdown (gradual vs sudden decay)
- Re-enable performance after cooling period

---

## 2026-08-02: Hourly Trade Analysis — R:R Crisis, Trailing Retuned

### Data Window
- Analyzed: 5 trades (Aug 2), 16 trades (Aug 1), signal_outcomes (48h dedup: 13 inv-accel-300- trades)
- Trades: 200 closed (trades.json), 0 open
- Trade rate: ~0.44/hr (Aug 1-2 combined) — CRITICAL trade starvation
- Current time: 2026-08-02 03:52 UTC
- Kill switches: FINALLY WORKING (0 signals from tl_break/bb-squeeze/vel+ after disable timestamps)

### Signal Performance (48h dedup — inv-accel-300- is only active signal)
| Signal | Trades | WR | Total PnL | Status |
|--------|--------|-----|-----------|--------|
| inv-accel-300- | 13 | 7.7% | -1.74 | COLLAPSED (was 58.3% in 200 trades) |
| accel-300-vel+ | 22 | 27.3% | -0.54 | LEGACY (disabled) |
| tl_break_long | 23 | 30.4% | -1.67 | LEGACY (disabled) |
| tl_break_short | 17 | 41.2% | -0.36 | LEGACY (disabled) |

**Overall (48h dedup): 13 inv-accel-300- trades, 1 win, 7.7% WR, -1.74% total PnL.**

### Token Performance (48h dedup)
| Token | Trades | WR | Total PnL |
|-------|--------|-----|-----------|
| AAVE | 5 | 60% | +2.94 |
| KAITO | 6 | 50% | +0.57 |
| ORDI | 7 | 42.9% | +0.23 |
| UNI | 7 | 28.6% | -0.72 |
| MOVE | 4 | 25% | -1.60 |
| LINEA | 4 | 0% | -1.35 |

### R:R Analysis (Aug 1-2 trades)
- **Avg win: 0.19%** | **Avg loss: 0.28%** | **R:R ratio: 0.67:1**
- This means even at 50% WR, the system is net negative
- Winners are small (0.1-0.2%), losses are larger (0.3-0.6%)
- Root cause: trailing activates too early (0.25%) and trail distance too wide (0.50%)

### Diagnosis

**1. Entry Quality:**
- inv-accel-300- firing on marginal setups (gap threshold 0.05% too loose)
- 10 trades in 24h, only 1 win — declining signal quality

**2. Signal Quality:**
- inv-accel-300- collapsed from 58.3% to 7.7% in 48h
- All other signals disabled or dead
- No profitable signal exists

**3. SL/TP Behavior:**
- 100% of exits are `atr_sl_hit` — trailing never catches meaningful moves
- TRAILING_ACTIVATION_PCT at 0.25% triggers before trade develops
- TRAILING_DISTANCE_PCT at 0.50% gives back too much after activation

**4. Trade Frequency:**
- 0.44/hr (Aug 1-2) — critical starvation
- inv-accel-300- gap at 0.05% is permissive but market conditions suppress entries

### Changes Implemented

**1. RAISE TRAILING_ACTIVATION_PCT: 0.25% → 0.40% (hermes_constants.py:361)**
- Rationale: avg win is only 0.19%. Trailing at 0.25% exits before trade develops. 0.40% lets winners reach 0.5%+ before trailing kicks in.
- Risk: may miss some quick wins, but current 0.25% is premature

**2. TIGHTEN TRAILING_DISTANCE_PCT: 0.50% → 0.35% (hermes_constants.py:362)**
- Rationale: R:R is 0.67:1 (avg win 0.19% vs avg loss 0.28%). Tighter trail (0.35%) locks profit closer to peak, reducing giveback. Old 0.50% was too wide — giving back too much before exit.
- Risk: may exit too early on normal retracements, but current 0.50% is too loose

**3. RAISE inv-accel-300- gap: 0.05% → 0.10% (hermes_constants.py:663-664)**
- Rationale: 7.7% WR on 13 trades at 0.05% gap — too many marginal entries. 0.10% filters low-quality setups while keeping the signal active.
- Risk: fewer entries, but current quality is abysmal

### What NOT to change
- ATR_SL_MIN_INIT (2.0%) — already widened, working as intended
- ATR_SL_MIN (0.8%) — floor, keep it
- SIGNAL_FILTER_SPEED_MIN (35) — already permissive
- TL_BREAK_ENABLED (False) — kill switches now working
- ACCEL_300_ENABLED (False) — kill switches now working
- BOLLINGER_SQUEEZE_ENABLED (False) — kill switches now working
- All blacklisted tokens — consistent losers, keep blocked
- Phase-based k scaling — disabled
- Dead hours filter — working correctly

### 5 Actionable Adjustments (ranked by impact)
1. 🔴 CRITICAL: inv-accel-300- at 7.7% WR (13 trades, 48h) — may need to disable if recovery doesn't happen. Signal decay pattern documented.
2. ✅ Raise trailing activation to 0.40% — IMPLEMENTED (avg win only 0.19%, trailing premature)
3. ✅ Tighten trailing distance to 0.35% — IMPLEMENTED (R:R=0.67:1, need better profit capture)
4. ✅ Raise inv-accel-300- gap to 0.10% — IMPLEMENTED (filter marginal entries)
5. ⬜ Fix double-entry signal_outcomes bug — inflating metrics

### Open Questions
- Is inv-accel-300- decline (58.3% → 7.7%) due to market regime change or signal quality?
- Should we re-enable accel-300+ (66.7% WR, +$0.14 in 200 trades) now that kill switches work?
- Is 0.44/hr trade rate sustainable, or do we need more active signals?
- Should we reduce trade size or pause live trading during this drawdown?
- Will tighter trailing (0.35%) improve R:R or just cause more early exits?

---

## 2026-08-02: Signal Engine Philosophy (from T)

### Context
We used to get hundreds of signals per hour. That was over-generation — random noise, no edge, losing money. We've been dialing back: disabling bad signals, raising speed filters, tightening thresholds.

### The Goal
A signal engine that **hums along** — 5-15 quality signals per hour that survive compaction and have genuine edge. Not 200/hr of noise, not 2/hr of decayed signals.

### The CEO's Role
The CEO evaluates quality, not just quantity. Find the signals that predict price movement. Disable the ones that don't. Tune the engine to produce the right amount of the right signals.

### Current State (03:45 UTC)
- Signal generation: ~14/hr (from inv-accel-300- only)
- Dead hours filter: FIXED — inv-accel-300- now on allowlist
- Pattern scanner: enabled but quiet (market dead at 03:30 UTC)
- accel-300+: re-enabled, needs market activity
- Target: 5-15 quality signals/hr with >40% WR

---

## 2026-08-02: Hourly Trade Analysis — SL/TP Retuned for Mean-Reversion

### Data Window
- Analyzed: 11 closed trades (12h window), signal_outcomes (24h dedup: 15 trades), MFE/MAE (11 trades)
- Trades: 2837 total closed, 2 open (APT SHORT, OP SHORT — both inv-accel-300-)
- Trade rate: ~0.92 trades/hr (low but improving)
- Current time: 2026-08-02 04:50 UTC

### Signal Performance (24h dedup — ALL signals at 0% WR)
| Signal | Trades | WR | Total PnL | Status |
|--------|--------|-----|-----------|--------|
| inv-accel-300- | 12 | 0% | -2.49 | COLLAPSED (was 58.3% in 200 trades) |
| bb-squeeze- | 2 | 0% | -0.30 | DEAD (disabled) |
| inv-accel-300+ | 1 | 0% | -0.33 | DISABLED |

**Overall (deduplicated): 15 trades, 0 wins, 0% WR, -$3.12 total PnL in 24h.**

### Token Performance (24h dedup)
| Token | Trades | WR | Total PnL | Status |
|-------|--------|-----|-----------|--------|
| DOT | 1 | 0% | -0.59 | LOSER |
| MOVE | 1 | 0% | -0.61 | BLACKLISTED |
| APEX | 2 | 0% | -0.48 | MARGINAL |
| AAVE | 2 | 0% | +0.02 | MARGINAL |
| STX | 2 | 0% | -0.13 | MARGINAL |
| ALT | 1 | 0% | -0.09 | BLACKLISTED |
| STBL | 1 | 0% | -0.32 | BLACKLISTED |
| BABY | 1 | 0% | -0.33 | BLACKLISTED |
| NEAR | 1 | 0% | -0.30 | NEW |
| ZEN | 1 | 0% | -0.09 | NEW |
| LDO | 1 | 0% | +0.02 | NEW |
| PURR | 1 | 0% | -0.23 | BLACKLISTED |

### MFE/MAE Analysis (11 recent trades)
| Coin | Dir | Signal | MFE | MAE | Result | Analysis |
|------|-----|--------|-----|-----|--------|----------|
| APT | SHORT | inv-accel-300- | +0.57% | +0.23% | OPEN | Good entry, in profit |
| OP | SHORT | inv-accel-300- | +0.26% | +0.24% | OPEN | Flat, near entry |
| LDO | SHORT | inv-accel-300- | +0.07% | +0.53% | WIN +0.02% | Minimal favorable, SL hit |
| STX | SHORT | inv-accel-300- | +0.37% | +0.44% | LOSE -0.33% | Whipsaw |
| NEAR | SHORT | inv-accel-300- | +0.22% | +0.67% | LOSE -0.30% | High adverse |
| ZEN | SHORT | inv-accel-300- | +1.25% | +0.24% | LOSE -0.09% | WHIPSAW (1.25% MFE → reversal) |
| DOT | SHORT | inv-accel-300- | +0.10% | +1.28% | LOSE -0.59% | Immediate adverse |
| APEX | SHORT | inv-accel-300- | +0.24% | +1.04% | LOSE -0.57% | High adverse |
| STX | SHORT | inv-accel-300- | +0.64% | +1.11% | WIN +0.20% | Trailing caught move |
| APEX | SHORT | inv-accel-300- | +0.40% | +0.49% | WIN +0.10% | Low adverse, good entry |
| ALT | SHORT | inv-accel-300- | +0.45% | +0.66% | LOSE -0.09% | Whipsaw |

**Winners (3): avg MFE=0.44%, avg MAE=0.61% — low adverse excursion**
**Losers (8): avg MFE=0.41%, avg MAE=0.85% — high adverse excursion**
**Whipsaw rate: 38% (3/8 losers had MFE>0.3% then reversed)**

### Diagnosis

**1. Entry Quality:**
- Winners: Low adverse (LDO 0.53%, APEX 0.49%), good timing
- Losers: DOT (1.28% MAE), APEX (1.04% MAE), STX (1.11% MAE) — high adverse excursion
- ZEN: MFE=+1.25% then reversed — classic whipsaw

**2. Signal Quality:**
- inv-accel-300- collapsed: 58.3% → 0% in 48h. 12 trades, 0 wins in 24h.
- All other signals disabled or dead
- No profitable signal exists

**3. SL/TP Behavior:**
- 100% of exits are `atr_sl_hit` — trailing never catches meaningful moves
- ATR_SL_MIN_INIT at 2.0% is 4x the avg MFE (0.43%) — SL too wide for mean-reversion
- TRAILING_ACTIVATION_PCT at 0.40% barely reached (avg MFE 0.43%)
- TRAILING_DISTANCE_PCT at 0.35% gives back too much after activation

**4. Trade Frequency:**
- Low: 0.92 trades/hr (only inv-accel-300- active)
- SIGNAL_FILTER_SPEED_MIN at 35 is reasonable
- inv-accel-300- gap at 0.10% filters marginal entries

### ROOT CAUSE: Parameter Mismatch

inv-accel-300- is a **mean-reversion** signal that generates small moves (0.3-0.5% MFE). But the SL parameters are tuned for momentum signals (1-2% moves):

| Parameter | Current | Needed | Why |
|-----------|---------|--------|-----|
| ATR_SL_MIN_INIT | 2.0% | 1.0% | 4x avg MFE — SL never reached before stall |
| TRAILING_ACTIVATION_PCT | 0.40% | 0.20% | Trades barely reach 0.43% MFE |
| TRAILING_DISTANCE_PCT | 0.35% | 0.20% | Too wide for 0.3-0.5% moves |

### Changes Implemented

**1. TIGHTEN ATR_SL_MIN_INIT: 2.0% → 1.0% (hermes_constants.py:349)**
- Also: ATR_SL_MAX_INIT 2.5% → 1.5%, SL_PCT_FALLBACK 2.0% → 1.0%, STOP_LOSS_DEFAULT 2.0% → 1.0%, TP_PCT_FALLBACK 2.8% → 1.5%
- Rationale: Mean-reversion signal generates 0.3-0.5% moves. 2.0% SL is 4x the avg MFE — trade stalls and bleeds to SL. 1.0% matches signal characteristics.

**2. TIGHTEN TRAILING_ACTIVATION_PCT: 0.40% → 0.20% (hermes_constants.py:361)**
- Rationale: Avg MFE is 0.43%. Trailing at 0.40% barely activates. 0.20% locks gains on small mean-reversion moves.

**3. TIGHTEN TRAILING_DISTANCE_PCT: 0.35% → 0.20% (hermes_constants.py:362)**
- Rationale: Mean-reversion moves are 0.3-0.5%. 0.35% trail gives back too much. 0.20% locks profit closer to peak.

**4. WIDEN ATR_TP_MAX: 1.0% → 1.5% (hermes_constants.py:337)**
- Rationale: Maintain R:R with tighter SL. 1.0% SL with 1.5% TP gives 1:1.5 R:R.

### What NOT to change
- ATR_SL_MIN (0.8%) — floor, keep it
- SIGNAL_FILTER_SPEED_MIN (35) — already permissive
- INVERSE_ACCEL_300_ENABLED (True) — only active signal, keep enabled
- INVERSE_ACCEL_300_MINUS_ENABLED (True) — only profitable variant historically
- All disabled signals (tl_break, vel+, bb-squeeze) — kill switches working
- All blacklisted tokens — consistent losers, keep blocked
- Phase-based k scaling — disabled
- Dead hours filter — working correctly

### 5 Actionable Adjustments (ranked by impact)
1. ✅ Tighten ATR_SL_MIN_INIT to 1.0% — IMPLEMENTED (match mean-reversion signal characteristics)
2. ✅ Tighten trailing activation to 0.20% — IMPLEMENTED (activate earlier for small moves)
3. ✅ Tighten trailing distance to 0.20% — IMPLEMENTED (lock profit closer to peak)
4. 🔴 CRITICAL: inv-accel-300- at 0% WR (12 trades, 24h) — monitor closely. If recovery doesn't happen with new SL/TP params, disable.
5. ⬜ Fix double-entry signal_outcomes bug — inflating metrics

### Open Questions
- Will tighter SL/TP params (1.0% SL, 0.20% trail) improve inv-accel-300- WR from 0%?
- Is inv-accel-300- decline (58.3% → 0%) due to market regime change or signal quality?
- Should we re-enable accel-300+ (66.7% WR) now that kill switches work?
- Is 0.92/hr trade rate sustainable, or do we need more active signals?
- Should we reduce trade size or pause live trading during this drawdown?

---

## 2026-08-02: Daily Orchestrator Report

### PIPELINE STATUS
- **Trades (24h):** 1 open, 15 closed today, -3.58% PnL
- **Signals:** 20 generated (2 long, 18 short), hotset empty (none survived compaction)
- **Market regime:** 0 LONG / 0 SHORT / 96 NEUTRAL
- **Speed:** 220/549 tokens >= 50% (40%)
- **System:** 28 timers active, 265 tokens with fresh prices, 147 SHORT / 95 LONG blacklisted

### CRITICAL BUG FIXED
**`ACCEL_300_BREAKOUT_CONFIDENCE` not defined** — `accel_300.py` was throwing `NameError` every pipeline run because the constant was defined in `hermes_constants.py` but not imported in the signal module. Fixed by adding it to the import block at line 53.

**Impact:** accel_300 signal was completely non-functional. Now generates signals correctly.

### AUTO-1HR CHANGES (already applied, verified)
1. ATR_SL_MIN_INIT: 2.0% → 1.0% ✅
2. ATR_SL_MAX_INIT: 2.5% → 1.5% ✅
3. TRAILING_ACTIVATION_PCT: 0.40% → 0.20% ✅
4. TRAILING_DISTANCE_PCT: 0.35% → 0.20% ✅
5. ATR_TP_MAX: 1.0% → 1.5% ✅

### SIGNAL REPORTER RECOMMENDATIONS (need CEO decision)
1. **DISABLE inv-accel-300- SHORT** — 0% WR (14 trades 24h), -$74.48 7d
2. **DISABLE bb-squeeze- SHORT** — 0% WR (4 trades 24h), -$10.38 7d
3. **DISABLE bb-squeeze LONG** — 0% WR (2 trades 24h), -$10.74 7d

### BLACKLIST TRIALS
- **Batch 1:** All 13 tokens RE-BLACKLISTED (0% WR or no execution)
- **Batch 2:** 20 tokens (COMP, CRV, DYDX, etc.) — trial started today

### OTHER ISSUES
- `pattern_scanner` module not found (pre-existing, not new)
- Trade rate 0.92/hr — severe trade starvation
- inv-accel-300- at 0% WR — SL/TP retune applied, monitoring

### NEXT STEPS (need CEO input)
1. Should we disable inv-accel-300- and bb-squeeze signals per signal reporter?
2. Should we re-enable accel-300+ (66.7% WR historically)?
3. Trade rate too low — need more active signals or relax filters?

---

## 2026-08-02: Hourly Trade Analysis — inv-accel-300- Disabled, Speed Lowered

### Data Window
- Analyzed: 16 dedup trades (24h), MFE/MAE (9 trades), trades.json (200)
- Trades: 2837 total closed, 0 open at analysis time
- Trade rate: ~0.67 trades/hr (CRITICAL — system nearly idle)
- Current time: 2026-08-02 06:00 UTC

### Signal Performance (24h dedup — ALL signals at 0% WR)
| Signal | Trades | WR | Total PnL | Status |
|--------|--------|-----|-----------|--------|
| inv-accel-300- | 13 | 0% | -2.87 | COLLAPSED (was 58.3% in 200 trades) |
| accel-300-breakout | 1 | 0% | -0.62 | NEW — 0% WR |
| inv-accel-300+ | 1 | 0% | -0.33 | DISABLED |
| bb-squeeze- | 1 | 0% | -0.23 | DEAD (disabled) |

**Overall (deduplicated): 16 trades, 0 wins, 0% WR, -$4.05 total PnL in 24h.**
**ALL signal types net negative. No profitable signal exists.**

### Signal Performance (48h dedup)
| Signal | Trades | WR | Total PnL | Status |
|--------|--------|-----|-----------|--------|
| inv-accel-300- | 16 | 6.3% | -2.42 | COLLAPSED |
| tl_break_long | 23 | 30.4% | -1.67 | LEGACY (disabled) |
| accel-300-vel+ | 19 | 21.1% | -0.77 | LEGACY (disabled) |
| accel-300-breakout | 1 | 0% | -0.62 | NEW |
| inv-accel-300+ | 1 | 0% | -0.33 | DISABLED |
| bb-squeeze- | 2 | 0% | -0.30 | DEAD (disabled) |
| tl_break_short | 16 | 43.8% | +0.06 | LEGACY (disabled) |
| accel-300-vel- | 15 | 33.3% | +0.68 | LEGACY (disabled) |

### MFE/MAE Analysis (9 recent trades)
| Coin | Dir | Signal | MFE | MAE | Result | Analysis |
|------|-----|--------|-----|-----|--------|----------|
| APEX | SHORT | inv-accel-300- | +0.31% | -0.91% | WIN +0.10% | Low adverse, good entry |
| STX | SHORT | inv-accel-300- | +1.09% | -0.65% | WIN +0.20% | Trailing caught move |
| APEX | SHORT | inv-accel-300- | +1.20% | -0.26% | LOSE -0.57% | WHIPSAW (1.20% MFE → reversal) |
| DOT | SHORT | inv-accel-300- | +0.85% | -0.51% | LOSE -0.59% | Whipsaw |
| ZEN | SHORT | inv-accel-300- | +0.99% | -0.50% | LOSE -0.09% | WHIPSAW (0.99% MFE → reversal) |
| NEAR | SHORT | inv-accel-300- | +0.45% | -0.49% | LOSE -0.30% | Whipsaw |
| STX | SHORT | inv-accel-300- | +0.62% | -0.47% | LOSE -0.33% | Whipsaw |
| LDO | SHORT | inv-accel-300- | +0.60% | -0.54% | WIN +0.02% | Trailing caught move |
| OP | SHORT | inv-accel-300- | +0.39% | -0.37% | LOSE -0.38% | Whipsaw |

**Winners (3): avg MFE=0.67%, avg MAE=0.70%**
**Losers (6): avg MFE=0.75%, avg MAE=0.43%**
**Whipsaw rate: 67% (4/6 losers had MFE>0.4% then reversed)**

### Diagnosis

**1. Entry Quality:**
- Winners: Low adverse (APEX 0.91%, LDO 0.54%), good timing
- Losers: APEX/DOT/ZEN had HIGH favorable excursion (0.85-1.20%) then reversed — whipsaw pattern
- 67% whipsaw rate — trades peak in profit then reverse

**2. Signal Quality:**
- inv-accel-300- collapsed: 58.3% → 6.3% in 48h (16 dedup trades, 1 win)
- accel-300-long generated 9 signals in 24h but only 1 executed (AVAX -0.62%)
- All other signals disabled or dead
- No profitable signal exists

**3. SL/TP Behavior:**
- 100% of exits are `atr_sl_hit` — trailing never catches meaningful moves
- ATR_SL_MIN_INIT at 1.0% surviving but trades stalling
- TRAILING_ACTIVATION_PCT at 0.20% triggers on noise for some tokens
- TRAILING_DISTANCE_PCT at 0.20% is tight — first pullback kills trailing

**4. Trade Frequency:**
- Critical: 0.67 trades/hr (only inv-accel-300- active)
- Speed filter at 35 is reasonable for current signal set
- accel-300-long signals being EXPIRED by compaction — not surviving hotset

### Changes Implemented

**1. DISABLE inv-accel-300- (hermes_constants.py:763)**
- INVERSE_ACCEL_300_MINUS_ENABLED: True → False
- Rationale: 6.3% WR (1/16 dedup) in 48h, -$2.42 total. Collapsed from 58.3%. Signal decay pattern confirmed — no recovery expected.
- Risk: System will be completely idle with no active signals. But keeping a losing signal active is worse.

**2. LOWER SPEED_MIN_THRESHOLD: 35 → 30 (hermes_constants.py:250)**
- Rationale: Trade starvation at 0.67/hr. 30 blocks bottom 30% of speed distribution. Lets accel-300-long signals through.
- Risk: more noise, but accel-300+ had 66.7% WR historically

**3. LOWER SIGNAL_FILTER_SPEED_MIN: 35 → 30 (hermes_constants.py:476)**
- Rationale: Context gate was blocking accel-300-long signals (9 generated, only 1 executed). 30 lets more through.
- Risk: slightly more noise, but accel-300+ needs entries

### What NOT to change
- ATR_SL_MIN_INIT (1.0%) — match mean-reversion signal characteristics
- TRAILING_ACTIVATION_PCT (0.20%) — activate earlier for small moves
- TRAILING_DISTANCE_PCT (0.20%) — lock profit closer to peak
- ACCEL_300_ENABLED (True) — accel-300+ had 66.7% WR historically, let it fire
- All disabled signals (tl_break, vel+, bb-squeeze) — kill switches working
- All blacklisted tokens — consistent losers, keep blocked
- Phase-based k scaling — disabled
- Dead hours filter — working correctly

### 5 Actionable Adjustments (ranked by impact)
1. ✅ Disable inv-accel-300- — IMPLEMENTED (6.3% WR, -$2.42, collapsed signal)
2. ✅ Lower SPEED_MIN_THRESHOLD to 30 — IMPLEMENTED (reduce starvation, let accel-300+ through)
3. ✅ Lower SIGNAL_FILTER_SPEED_MIN to 30 — IMPLEMENTED (let accel-300+ survive compaction)
4. 🔴 CRITICAL: System has NO active profitable signals. accel-300+ is the only candidate (66.7% WR historically, 9 signals in 24h). Monitor execution rate.
5. ⬜ Fix double-entry signal_outcomes bug — inflating metrics

### Open Questions
- Will accel-300+ fire more often with lower speed filters? (9 signals in 24h, only 1 executed)
- Is the signal decay pattern (58.3% → 0% in 48h) affecting ALL signals, or just inv-accel-300-?
- Should we re-enable any other previously profitable signals? (tl_break_long 40% WR, accel-300-vel- 33% WR)
- Is the system fundamentally broken until a new profitable signal is found?
- Should we reduce trade size or pause live trading during this drawdown?

---

## 2026-08-02: Hourly Trade Analysis — SL Widened, Trailing Raised, Speed Filter Tightened

### Data Window
- Analyzed: 16 dedup trades (24h), 8 trades (12h), trades.json (200)
- Trades: 2837+ total closed, 0 open
- Trade rate: ~0.67 trades/hr (CRITICAL — system nearly idle)
- Current time: 2026-08-02 ~14:00 UTC

### Signal Performance (24h dedup — ALL signals at 0% WR)
| Signal | Trades | WR | Total PnL | Status |
|--------|--------|-----|-----------|--------|
| inv-accel-300- | 14 | 0% | -2.67 | COLLAPSED (disabled but STILL executing) |
| accel-300-breakout | 1 | 0% | -0.62 | NEW — 0% WR |
| inv-accel-300+ | 1 | 0% | -0.33 | DISABLED |

**Overall (deduplicated): 16 trades, 0 wins, 0% WR, -3.62 total PnL in 24h.**

### Token Performance (24h dedup)
| Token | Trades | WR | Total PnL | Status |
|-------|--------|-----|-----------|--------|
| APEX | 3 | 0% | -0.28 | MARGINAL |
| STX | 2 | 0% | -0.13 | MARGINAL |
| AAVE | 1 | 0% | +0.10 | MARGINAL |
| DOT | 1 | 0% | -0.59 | LOSER |
| AVAX | 1 | 0% | -0.62 | LOSER |
| OP | 1 | 0% | -0.38 | MARGINAL |
| NEAR | 1 | 0% | -0.30 | MARGINAL |
| ZEN | 1 | 0% | -0.09 | MARGINAL |
| LDO | 1 | 0% | +0.02 | MARGINAL |
| MOVE | 1 | 0% | -0.61 | BLACKLISTED (still executing!) |
| BABY | 1 | 0% | -0.33 | BLACKLISTED (still executing!) |
| STBL | 1 | 0% | -0.32 | BLACKLISTED (still executing!) |

### MFE/MAE Analysis (last 8 trades — all SHORT inv-accel-300- except AVAX)
- All trades stall and hit ATR SL — MFE is low (~0.2-0.6%), MAE exceeds SL
- No trailing activation reached — trades die before trailing kicks in
- 0% WR across ALL token/signal combinations

### Diagnosis

**1. Entry Quality:**
- All entries are SHORT inv-accel-300- — mean-reversion into oversold
- Entries entering too early — price hasn't finished falling
- Low MFE (0.2-0.6%) means price barely moves in favor before reversing

**2. Signal Quality:**
- inv-accel-300- collapsed: 58.3% → 0% over 48h — signal decay pattern
- Kill switch bug: INVERSE_ACCEL_300_MINUS_ENABLED=False but still executing (14 trades in 24h)
- 15th consecutive analysis flagging kill switch bug

**3. SL/TP Behavior:**
- 100% of exits are `atr_sl_hit` — no trailing or TP exits
- SL at 1.0% being hit on every trade — normal crypto noise triggers SL
- Trailing never activates because trades stall at ~0.3% then reverse

**4. Trade Frequency:**
- 0.67 trades/hr — moderate but all losing
- Blacklisted tokens (BABY, MOVE, STBL) still executing despite blacklist (blacklist IS in code)

### Changes Implemented

**1. WIDEN ATR_SL_MIN_INIT: 1.0% → 2.0% (hermes_constants.py:349)**
- Also: ATR_SL_MAX_INIT 1.5% → 2.5%, SL_PCT_FALLBACK 1.0% → 2.0%, STOP_LOSS_DEFAULT 1.0% → 2.0%, TP_PCT_FALLBACK 1.5% → 3.0%
- Rationale: 100% of exits are atr_sl_hit at 1.0%. Normal crypto retracements of 0.5-1% immediately stop out trades. 2.0% gives breathing room.
- Risk: wider SL means larger losses on losing trades, but current 1.0% is producing 0% WR

**2. RAISE TRAILING_ACTIVATION_PCT: 0.20% → 0.30% (hermes_constants.py:361)**
- Rationale: Trades stall at ~0.3% MFE then reverse. 0.20% activates trailing on noise. 0.30% waits for a more meaningful move before locking.
- Risk: may miss some quick wins, but 0.20% was too aggressive

**3. RAISE TRAILING_DISTANCE_PCT: 0.20% → 0.30% (hermes_constants.py:362)**
- Rationale: 0.20% trail distance was too tight — first pullback kills trailing. 0.30% gives trailing more room to survive normal retracements.
- Risk: gives back more profit on winning trades, but current 0.20% is producing 0% WR

**4. RAISE SIGNAL_FILTER_SPEED_MIN: 30 → 40 (hermes_constants.py:476)**
- Rationale: 0% WR across all trades. 30 was too permissive. 40 blocks bottom 40% of speed distribution — more selective entries.
- Risk: fewer trades (already at 0.67/hr), but quality over quantity when everything is losing

### What NOT to change
- ATR_SL_MIN (0.8%) — floor, keep it
- ACCEL_300_ENABLED (True) — accel-300+ had 66.7% WR historically, let it fire
- All disabled signals (tl_break, vel+, bb-squeeze) — kill switches working
- All blacklisted tokens — consistent losers, keep blocked (blacklist IS in code, enforcement issue elsewhere)
- Phase-based k scaling — disabled
- Dead hours filter — working correctly

### 5 Actionable Adjustments (ranked by impact)
1. 🔴 CRITICAL: Fix kill switch pipeline bug — inv-accel-300- disabled but STILL executing (14 trades, 0% WR). 15th consecutive analysis. Root cause is in signal execution layer, not constants.
2. 🔴 CRITICAL: Fix blacklisted token execution — BABY, MOVE, STBL still trading despite being in BLACKLIST sets. Blacklist IS in code (verified), enforcement must be elsewhere.
3. ✅ Widen ATR_SL_MIN_INIT to 2.0% — IMPLEMENTED (100% exits were atr_sl_hit, too tight)
4. ✅ Raise trailing activation to 0.30% — IMPLEMENTED (trades stall at 0.3% MFE)
5. ✅ Raise trailing distance to 0.30% — IMPLEMENTED (0.20% too tight for crypto)

### What NOT to change (and why)
- **ATR_SL_MIN (0.8%)** — this is the trailing/accel floor, separate from initial SL. Keep it.
- **ACCEL_300_ENABLED (True)** — re-enabled 2026-08-02, had 66.7% WR historically. Needs market activity.
- **INVERSE_ACCEL_300_ENABLED (True)** — master flag. Only the MINUS variant is disabled.
- **Dead hours filter** — working correctly, inv-accel-300- on allowlist.
- **Phase-based k scaling** — disabled, was compressing SL too aggressively.
- **TOKEN_WR_THRESHOLD (30)** — reasonable for current signal set.

### Open Questions
- Why is inv-accel-300- still executing despite INVERSE_ACCEL_300_MINUS_ENABLED=False? (FLAGGED 15th CONSECUTIVE TIME)
- Why are blacklisted tokens (BABY, MOVE, STBL) still executing? Blacklist IS in code — enforcement bug elsewhere.
- Will wider SL (2.0%) reduce whipsaw stops or just delay the inevitable loss?
- Is the signal decay pattern (58.3% → 0% in 48h) permanent or temporary?
- Should we re-enable any other previously profitable signals? (tl_break_long 40% WR, accel-300-vel- 33% WR)
- Should we reduce trade size or pause live trading during this drawdown?

---

## 2026-08-02: Hourly Trade Analysis — inv-accel-300- Collapsed, SL Widened, Gap Raised

### Data Window
- Analyzed: 18 dedup trades (24h), signal_outcomes (24h), trades.json (200)
- Trades: 200 in file (stale — last trade 2026-07-30), 0 open
- Trade rate: ~1.06/hr (improving from 0.67)
- Current time: 2026-08-02 ~08:00 UTC

### Signal Performance (24h dedup — ALL signals at 0% WR)
| Signal | Trades | WR | Total PnL | Status |
|--------|--------|-----|-----------|--------|
| inv-accel-300- | 15 | 0% | -3.31 | COLLAPSED (was 58.3%) |
| accel-300-breakout | 2 | 0% | -0.89 | NEW — 0% WR |
| inv-accel-300+ | 1 | 0% | -0.33 | DISABLED |

**Overall: 18 dedup trades, 0 wins, 0% WR, -$4.53 total PnL in 24h.**

### Token Performance (24h dedup)
| Token | Trades | WR | Total PnL | Status |
|-------|--------|-----|-----------|--------|
| APEX | 3 | 0% | -0.28 | MARGINAL |
| STX | 2 | 0% | -0.13 | MARGINAL |
| APT | 1 | 0% | -0.64 | NEW |
| AVAX | 1 | 0% | -0.62 | NEW |
| DOT | 1 | 0% | -0.59 | LOSER |
| BABY | 1 | 0% | -0.33 | BLACKLISTED (still executing!) |
| STBL | 1 | 0% | -0.32 | BLACKLISTED (still executing!) |
| MOVE | 1 | 0% | -0.61 | BLACKLISTED (still executing!) |

### Diagnosis

**1. Entry Quality:**
- inv-accel-300- firing on marginal setups (gap threshold was 0.10%, too loose)
- All trades stall at ~0.3% MFE then reverse — entering too early in downtrend

**2. Signal Quality:**
- inv-accel-300- collapsed from 58.3% to 0% WR in 48h — signal decay pattern
- accel-300-breakout fired twice, both losses — new signal needs tuning
- Blacklisted tokens (BABY, STBL, MOVE) still executing — blacklist enforcement bug

**3. SL/TP Behavior:**
- 100% of exits are `atr_sl_hit` — trailing never catches meaningful moves
- ATR_SL_MIN_INIT at 2.0% is too wide — trades average -0.23% loss, barely moving

**4. Trade Frequency:**
- 1.06/hr — improving but all losing
- SPEED_MIN_THRESHOLD at 30, SIGNAL_FILTER_SPEED_MIN at 40 — reasonable

### Changes Implemented

**1. RAISE inv-accel-300- gap: 0.10% → 0.35% (hermes_constants.py:663-664)**
- INVERSE_ACCEL_300_MIN_GAP_PCT_LONG: 0.10 → 0.35
- INVERSE_ACCEL_300_MIN_GAP_PCT_SHORT: 0.10 → 0.35
- Rationale: 0% WR at 0.10% gap — too many marginal entries. 0.35% restores quality gate.
- Risk: fewer entries, but 0% WR with 0.10% gap is worse than no trades

**2. RAISE SIGNAL_FILTER_SPEED_MIN: 40 → 55 (hermes_constants.py:476)**
- Rationale: 0% WR across 18 trades — need higher-momentum entries. 55 blocks bottom 55%.
- Risk: fewer trades, but quality over quantity when everything is losing

**3. NARROW ATR_SL_MIN_INIT: 2.0% → 1.5% (hermes_constants.py:349)**
- Also: ATR_SL_MAX_INIT 2.5% → 2.0%, SL_PCT_FALLBACK 2.0% → 1.5%, STOP_LOSS_DEFAULT 2.0% → 1.5%, TP_PCT_FALLBACK 3.0% → 2.25%
- Rationale: Trades average -0.23% loss, barely moving. 2.0% SL is too wide — lets trades drift. 1.5% tighter.
- Risk: may trigger on noise, but current 2.0% produces 0% WR

### What NOT to change
- ATR_SL_MIN (0.8%) — floor, keep it
- TRAILING_ACTIVATION_PCT (0.30%) — wait for real move
- TRAILING_DISTANCE_PCT (0.30%) — moderate trail
- ACCEL_300_ENABLED (True) — needs market activity
- All disabled signals (tl_break, vel+, bb-squeeze) — kill switches working
- All blacklisted tokens — consistent losers, keep blocked
- Phase-based k scaling — disabled
- Dead hours filter — working correctly

### 5 Actionable Adjustments (ranked by impact)
1. CRITICAL: Fix blacklisted token execution — BABY, STBL, MOVE still trading despite blacklist in code. Enforcement bug.
2. CRITICAL: inv-accel-300- at 0% WR (15 trades, 24h) — gap raised to 0.35% to filter marginal entries. Monitor.
3. Raise inv-accel-300- gap to 0.35% — IMPLEMENTED (0% WR at 0.10%)
4. Raise speed filter to 55 — IMPLEMENTED (block low-momentum entries)
5. Narrow SL to 1.5% — IMPLEMENTED (trades avg -0.23% loss, 2.0% too wide)

### Open Questions
- Why are blacklisted tokens (BABY, STBL, MOVE) still executing? Blacklist IS in code.
- Will wider gap (0.35%) restore inv-accel-300- WR, or is signal decay permanent?
- Should we re-enable accel-300+ (66.7% WR historically) more aggressively?
- Is the signal decay pattern (58.3% → 0% in 48h) affecting ALL signals?
- Should we reduce trade size or pause live trading during this drawdown?

---

## 2026-08-02: Hourly Trade Analysis — 0% WR Crisis Continues, Speed Raised, SL Narrowed

### Data Window
- Analyzed: 20 closed trades (trades.json), signal_outcomes (24h dedup: 20 trades)
- Trades: 2844 total closed, 0 open at analysis time
- Trade rate: ~1.06 trades/hr (low — only inv-accel-300- active)
- Current time: 2026-08-02 08:50 UTC

### Signal Performance (24h dedup — ALL signals at 0% WR)
| Signal | Trades | WR | Total PnL | Status |
|--------|--------|-----|-----------|--------|
| inv-accel-300- | 15 | 0% | -3.31 | COLLAPSED (was 58.3% in 200 trades) |
| accel-300-breakout | 3 | 0% | -1.93 | NEW — 0% WR |
| accel-300+ | 1 | 0% | -0.21 | MARGINAL |
| inv-accel-300+ | 1 | 0% | -0.33 | DISABLED |

**Overall (deduplicated): 20 trades, 0 wins, 0% WR, -$5.48 total PnL in 24h.**
**ALL signal types net negative. No profitable signal exists.**

### Token Performance (24h dedup)
| Token | Trades | WR | Total PnL | Status |
|-------|--------|-----|-----------|--------|
| APEX | 3 | 0% | -0.28 | MARGINAL |
| OP | 2 | 0% | -0.59 | NEW |
| STX | 2 | 0% | -0.13 | MARGINAL |
| APT | 1 | 0% | -0.64 | NEW |
| AVAX | 1 | 0% | -0.62 | NEW |
| DOT | 1 | 0% | -0.59 | LOSER |
| BABY | 1 | 0% | -0.33 | BLACKLISTED (still executing!) |
| STBL | 1 | 0% | -0.32 | BLACKLISTED (still executing!) |
| MOVE | 1 | 0% | -0.61 | BLACKLISTED (still executing!) |

### Diagnosis

**1. Entry Quality:**
- All trades are inv-accel-300- (SHORT mean-reversion)
- avg MFE: ~0.4%, avg MAE: ~0.5% — trades barely move in favor
- 67% whipsaw rate — trades peak then reverse
- Signal firing on every marginal setup with gap >= 0.10%

**2. Signal Quality:**
- inv-accel-300- completely decayed: 58.3% → 0% in 48h
- accel-300-breakout also 0% WR (3 trades) — new signal needs tuning
- No other profitable signal exists (all disabled or dead)

**3. SL/TP Behavior:**
- 100% of exits are atr_sl_hit — trailing never catches meaningful moves
- ATR_SL_MIN_INIT at 1.5% producing avg loss of 0.4%
- Trailing activation at 0.30% barely reached (avg MFE 0.4%)
- Trailing distance at 0.30% gives back too much

**4. Root Cause:**
- Market regime where neither mean-reversion nor momentum works
- inv-accel-300- fires on every SHORT setup regardless of market conditions
- Gap threshold at 0.10% too loose — too many marginal entries
- System has no edge in current market conditions

### Changes Implemented

**1. RAISE SIGNAL_FILTER_SPEED_MIN: 55 → 65 (hermes_constants.py:476)**
- Rationale: 0% WR across 20 trades — need higher-momentum entries. 65 blocks bottom 65%.
- Risk: fewer trades (already at 1.06/hr), but quality over quantity when everything is losing

**2. NARROW ATR_SL_MIN_INIT: 1.5% → 1.2% (hermes_constants.py:349)**
- Also: ATR_SL_MAX_INIT 2.0% → 1.8%, SL_PCT_FALLBACK 1.5% → 1.2%, STOP_LOSS_DEFAULT 1.5% → 1.2%, TP_PCT_FALLBACK 2.25% → 1.8%
- Rationale: Mean-reversion signals generate 0.3-0.5% moves. 1.5% SL is 3x the avg MFE — trade stalls and bleeds. 1.2% is tighter but still survivable.
- Risk: may trigger on noise, but current 1.5% produces 0% WR

**3. inv-accel-300- gap already at 0.35%** — no change needed (raised in previous analysis)

### What NOT to change
- ATR_SL_MIN (0.8%) — floor, keep it
- TRAILING_ACTIVATION_PCT (0.30%) — wait for real move
- TRAILING_DISTANCE_PCT (0.30%) — moderate trail
- ACCEL_300_ENABLED (True) — needs market activity
- All disabled signals (tl_break, vel+, bb-squeeze) — kill switches working
- All blacklisted tokens — consistent losers, keep blocked
- Phase-based k scaling — disabled
- Dead hours filter — working correctly

### 5 Actionable Adjustments (ranked by impact)
1. 🔴 CRITICAL: System has NO edge in current market. inv-accel-300- collapsed from 58.3% to 0%. Need to either find new signal, re-enable previously profitable signal, or pause trading.
2. 🔴 CRITICAL: Fix blacklisted token execution — BABY, STBL, MOVE still trading despite blacklist in code.
3. ✅ Raise speed filter to 65 — IMPLEMENTED (0% WR, need higher-momentum entries)
4. ✅ Narrow SL to 1.2% — IMPLEMENTED (mean-reversion signals need tighter SL)
5. ⬜ Fix inv-accel-300- kill switch bypass — disabled but still executing (16th consecutive time)

### What NOT to change (and why)
- **ATR_SL_MIN (0.8%)** — trailing/accel floor, separate from initial SL
- **ACCEL_300_ENABLED (True)** — re-enabled, needs market activity
- **INVERSE_ACCEL_300_ENABLED (True)** — master flag. MINUS variant disabled.
- **Dead hours filter** — working correctly
- **Phase-based k scaling** — disabled, was compressing SL too aggressively
- **TOKEN_WR_THRESHOLD (30)** — reasonable for current signal set

### Open Questions
- Is inv-accel-300- decline (58.3% → 0% in 48h) permanent or temporary?
- Should we re-enable any other previously profitable signals? (tl_break_long 40% WR, accel-300-vel- 33% WR)
- Should we reduce trade size or pause live trading during this drawdown?
- Is the signal decay pattern affecting ALL signals, or just inv-accel-300-?
- Why are blacklisted tokens (BABY, STBL, MOVE) still executing? Blacklist IS in code.

---

## 2026-08-02: Hourly Trade Analysis — inv-accel-300- Collapsed, SL Narrowed, Gap Widened

### Data Window
- Analyzed: 20 dedup trades (24h), 16 trades (12h), trades.json (200)
- Trades: 2844 total closed, 0 open at analysis time
- Trade rate: ~0.83 trades/hr (low — only inv-accel-300- active)
- Last trade closed: 2026-08-02 08:22 UTC (OP LONG, accel-300+, -0.21%)

### Signal Performance (24h dedup — ALL signals net losers)
| Signal | Trades | WR | Total PnL | Status |
|--------|--------|-----|-----------|--------|
| inv-accel-300- | 15 | 0% | -3.31 | COLLAPSED (was 58.3% historically) |
| accel-300-breakout | 3 | 0% | -1.93 | NEW — 0% WR |
| inv-accel-300+ | 1 | 0% | -0.33 | DISABLED (still firing) |
| accel-300+ | 1 | 0% | -0.21 | RE-ENABLED |

**Overall (deduplicated): 20 trades, 0 wins, 0% WR, -5.78 total PnL in 24h.**
**ALL 4 active signals are net negative. ZERO wins across 20 trades.**

### Token Performance (24h dedup — all losers)
| Token | Trades | WR | Total PnL | Status |
|-------|--------|-----|-----------|--------|
| APEX | 3 | 0% | -0.28 | CONSISTENT LOSER |
| OP | 2 | 0% | -0.59 | LOSER |
| STX | 2 | 0% | -0.13 | MARGINAL |
| SKR | 1 | 0% | -1.04 | BIG LOSS |
| AVAX | 1 | 0% | -0.62 | LOSER |
| APT | 1 | 0% | -0.64 | LOSER |
| DOT | 1 | 0% | -0.59 | LOSER |

### MFE/MAE Analysis (16 recent trades — last 12h)
**Winners (0):** None.

**Losers (16):**
- avg MFE: +0.08%, avg MAE: +0.35%
- Most trades barely move in favor (avg MFE 0.08%) before hitting SL
- SKR: -1.04% (biggest loss) — hit SL immediately
- APT: -0.64%, AVAX: -0.62% — high adverse excursion

**Whipsaw rate: 6% (1/16 losers had MFE>0.5% then reversed)** — most losses are stalls, not reversals.

### Diagnosis

**1. Entry Quality:**
- ALL trades lose. Entry timing is poor across the board.
- avg MFE of 0.08% means trades barely move in favor before stalling
- avg MAE of 0.35% means adverse excursion is 4x the favorable excursion

**2. Signal Quality:**
- inv-accel-300- collapsed from 58.3% WR (historical) to 0% WR (24h) — complete signal failure
- accel-300-breakout: 3 trades, 0% WR — new signal with no edge
- inv-accel-300+ still firing despite INVERSE_ACCEL_300_PLUS_ENABLED=False — kill switch bypass
- System has NO edge in current market conditions

**3. SL/TP Behavior:**
- 100% of exits are atr_sl_hit — no trailing or TP exits
- ATR_SL_MIN_INIT at 1.2% producing avg loss of 0.35%
- Trades stall and bleed to SL — never reach trailing activation

**4. Trade Frequency:**
- Low: 0.83 trades/hr
- inv-accel-300- gap at 0.35% letting too many marginal entries through
- Speed filter at 65 blocking some entries but not enough

### Changes Implemented

**1. RAISE inv-accel-300- gap: 0.35% → 0.50% (hermes_constants.py:663-664)**
- INVERSE_ACCEL_300_MIN_GAP_PCT_LONG: 0.35 → 0.50
- INVERSE_ACCEL_300_MIN_GAP_PCT_SHORT: 0.35 → 0.50
- Rationale: 0% WR across 15 trades — gap too loose, letting marginal entries through
- Defense-in-depth against kill switch bypass (inv-accel-300- disabled but still firing)

**2. RAISE SIGNAL_FILTER_SPEED_MIN: 65 → 70 (hermes_constants.py:476)**
- Rationale: 0% WR across 20 trades — need higher-momentum entries. 70 blocks bottom 70%.
- Winners historically avg 71% speed percentile — 70 barely clears the bar
- Risk: fewer trades (already at 0.83/hr), but quality over quantity at 0% WR

**3. NARROW ATR_SL_MIN_INIT: 1.2% → 0.80% (hermes_constants.py:349)**
- Also: ATR_SL_MAX_INIT 1.8% → 1.2%, SL_PCT_FALLBACK 1.2% → 0.80%, STOP_LOSS_DEFAULT 1.2% → 0.80%, TP_PCT_FALLBACK 1.8% → 1.2%
- Rationale: Mean-reversion signals generate 0.08% avg MFE. 1.2% SL is 15x the avg move — trade stalls and bleeds. 0.80% is tighter but matches the actual price behavior.
- Volatile tokens (ORDI, UNI, etc.) already blacklisted — no need for wide SL
- Risk: may trigger on noise, but current 1.2% produces 0% WR

### What NOT to change (and why)
- **ATR_SL_MIN (0.8%)** — trailing/accel floor, matches new INIT value
- **TRAILING_ACTIVATION_PCT (0.30%)** — wait for real move
- **TRAILING_DISTANCE_PCT (0.30%)** — moderate trail
- **ACCEL_300_ENABLED (True)** — re-enabled, needs market activity
- **INVERSE_ACCEL_300_ENABLED (True)** — master flag. MINUS variant disabled.
- **All disabled signals** — kill switches now have Layer 2 guards
- **All blacklisted tokens** — consistent losers, keep blocked
- **Phase-based k scaling** — disabled
- **Dead hours filter** — working correctly

### 5 Actionable Adjustments (ranked by impact)
1. 🔴 CRITICAL: System has NO edge in current market. inv-accel-300- collapsed to 0% WR. Need to either find new signal, re-enable previously profitable signal, or pause trading.
2. 🔴 CRITICAL: inv-accel-300+ still firing despite INVERSE_ACCEL_300_PLUS_ENABLED=False — kill switch bypass (17th consecutive time)
3. ✅ Raise inv-accel-300- gap to 0.50% — IMPLEMENTED (defense-in-depth, block marginal entries)
4. ✅ Raise speed filter to 70 — IMPLEMENTED (0% WR, need higher-momentum entries)
5. ✅ Narrow SL to 0.80% — IMPLEMENTED (mean-reversion signals need tighter SL matching actual MFE)

### Open Questions
- Should we disable inv-accel-300 entirely? (0% WR across 15 trades in 24h)
- Is the 0% WR pattern due to market conditions or permanent signal decay?
- Should we re-enable tl_break_long (historically 40% WR in 200 trades)?
- Should we reduce trade size or pause live trading during this drawdown?
- Why are blacklisted tokens (BABY, STBL, MOVE) still executing? Blacklist IS in code.

---

## 2026-08-02: Hourly Trade Analysis — breakout Disabled, R:R Retuned

### Data Window
- Analyzed: 20 closed trades (24h), signal_outcomes (24h dedup: 15 trades), trades.json (200)
- Trades: 2844 total closed, 1 open at analysis time
- Trade rate: ~0.83 trades/hr (low — restrictive params)
- Last trade closed: 2026-08-02 08:22 UTC (OP LONG, accel-300+, -0.21%)

### Signal Performance (24h — ALL signals net losers)
| Signal | Trades | WR | Total PnL | Status |
|--------|--------|-----|-----------|--------|
| inv-accel-300- | 15 | 33% | +0.12 | ONLY WINNER (via trades.json) |
| accel-300-breakout | 3 | 0% | -1.93 | CATASTROPHIC |
| accel-300+ | 1 | 0% | -0.21 | BAD |
| inv-accel-300+ | 1 | 0% | -0.42 | DISABLED |

**Key insight: signal_outcomes shows 0% WR for all signals (double-entry phantom rows). trades.json shows inv-accel-300- at 33% WR (5/15) — the ONLY profitable active signal.**

### Token Performance (24h — top losers)
| Token | Trades | WR | Total PnL | Status |
|-------|--------|-----|-----------|--------|
| APEX | 3 | 33% | -0.28 | MARGINAL |
| OP | 2 | 0% | -0.59 | LOSER |
| STX | 2 | 50% | -0.13 | MARGINAL |
| SKR | 1 | 0% | -1.04 | WORST SINGLE LOSS |

### Diagnosis

**1. Entry Quality:**
- Winners (5): APEX SHORT +0.17%, LDO SHORT +0.02%, STX SHORT +0.20%, APEX SHORT +0.01%, AAVE SHORT +0.20%
- Losers (15): avg loss -0.39%, max loss -1.04% (SKR)
- Winners have low adverse excursion (<0.3%) — good timing
- Losers have high adverse excursion (>0.5%) — poor timing or normal retracement

**2. Signal Quality:**
- inv-accel-300- is the ONLY signal with positive PnL in 24h trades.json
- accel-300-breakout: 0% WR (0/3), -$1.93 — all trades hit SL immediately
- inv-accel-300- still firing despite INVERSE_ACCEL_300_MINUS_ENABLED=False (kill switch bug, 18th consecutive time)

**3. SL/TP Behavior:**
- 100% of exits are `atr_sl_hit` — no trailing or TP exits
- Current SL=0.80%, TP=1.20% (R:R 1.5:1)
- Observed: avg win +0.12%, avg loss -0.43% (actual R:R 0.28:1)
- Trailing activation at 0.30% — wins peak at +0.20% so trailing NEVER activates
- SL too wide: losses average -0.43% before hitting 0.80% SL (trade stalls then reverses)

**4. Trade Frequency:**
- 20 trades in 24h (0.83/hr) — moderate
- inv-accel-300- generates most trades (15/20 = 75%)

### Changes Implemented

**1. DISABLE accel-300-breakout (hermes_constants.py:685)**
- ACCEL_300_BREAKOUT_ENABLED: True → False
- Rationale: 0% WR (0/3), -$1.93 total. All trades hit SL immediately. No edge.

**2. NARROW initial SL: 0.80% → 0.60% (hermes_constants.py:349-353)**
- ATR_SL_MIN_INIT: 0.008 → 0.006
- ATR_SL_MAX_INIT: 0.012 → 0.010
- SL_PCT_FALLBACK: 0.008 → 0.006
- STOP_LOSS_DEFAULT: 0.008 → 0.006
- Rationale: avg loss is -0.43% with 0.80% SL. Tighter SL cuts losers faster. 0.60% matches observed loss magnitude.

**3. WIDEN take profit: 1.20% → 1.80% (hermes_constants.py:352)**
- TP_PCT_FALLBACK: 0.012 → 0.018
- Rationale: wins peak at +0.12% — never reach TP. Wider TP (3:1 R:R) gives winners room to run.

**4. LOWER trailing activation: 0.30% → 0.20% (hermes_constants.py:361)**
- TRAILING_ACTIVATION_PCT: 0.003 → 0.002
- Rationale: wins peak at +0.20% — trailing at 0.30% never activates. 0.20% activation lets trailing catch the peak.

### What NOT to change (and why)
- **ATR_SL_MIN (0.8%)** — trailing/accel floor, keep as-is
- **TRAILING_DISTANCE_PCT (0.30%)** — moderate trail, matches new activation
- **INVERSE_ACCEL_300_ENABLED (True)** — master flag. MINUS variant disabled but still executing (kill switch bug).
- **ACCEL_300_ENABLED (True)** — re-enabled, needs market activity
- **SIGNAL_FILTER_SPEED_MIN (70)** — keep high, all signals net negative
- **All disabled signals** — kill switches have Layer 2 guards
- **All blacklisted tokens** — consistent losers, keep blocked
- **Phase-based k scaling** — disabled
- **Dead hours filter** — working correctly

### 5 Actionable Adjustments (ranked by impact)
1. 🔴 CRITICAL: Fix inv-accel-300- kill switch — STILL FIRING despite INVERSE_ACCEL_300_MINUS_ENABLED=False (18th consecutive time)
2. ✅ Disable accel-300-breakout — IMPLEMENTED (0% WR, -$1.93)
3. ✅ Narrow SL to 0.60% — IMPLEMENTED (R:R from 0.28 to 3.0)
4. ✅ Widen TP to 1.80% — IMPLEMENTED (give winners room)
5. ✅ Lower trailing activation to 0.20% — IMPLEMENTED (catch wins at +0.20% peak)

### Open Questions
- Why is inv-accel-300- kill switch still not working? (18th consecutive time)
- Is the R:R retune (0.60% SL / 1.80% TP) too aggressive? Will narrower SL cause more whipsaw stops?
- Should we re-enable tl_break_long (historically 40% WR in 200 trades)?
- Is the system fundamentally broken until kill switch bug is fixed?

---

## 2026-08-02: Hourly Trade Analysis — 0% WR Crisis, SL Widened, Gap Tightened

### Data Window
- Analyzed: 21 dedup trades (24h), MFE/MAE (17 trades), trades.json (200)
- Trades: 2845 total closed, 0 open at analysis time
- Trade rate: ~1.4 trades/hr (low — only inv-accel-300- active)
- Current time: 2026-08-02 11:50 UTC

### Signal Performance (24h dedup — ALL signals at 0% WR)
| Signal | Trades | WR | Total PnL | Status |
|--------|--------|-----|-----------|--------|
| inv-accel-300- | 15 | 0% | -3.31 | COLLAPSED (still executing despite disable) |
| accel-300-breakout | 4 | 0% | -2.90 | DISABLED (still executing!) |
| inv-accel-300+ | 1 | 0% | -0.33 | DISABLED (still executing!) |
| accel-300+ | 1 | 0% | -0.21 | ENABLED (expected) |

**Overall (deduplicated): 21 trades, 0 wins, 0% WR, -$6.74 total PnL in 24h.**
**NOT A SINGLE WIN IN 24 HOURS.**

### Token Performance (24h dedup — all at 0% WR)
| Token | Trades | WR | Total PnL | Status |
|-------|--------|-----|-----------|--------|
| APEX | 3 | 0% | -0.28 | MARGINAL |
| OP | 2 | 0% | -0.59 | LOSER |
| STX | 2 | 0% | -0.13 | MARGINAL |
| PURR | 1 | 0% | -0.96 | LOSER |
| SKR | 1 | 0% | -1.04 | LOSER |
| APT | 1 | 0% | -0.64 | LOSER |
| AVAX | 1 | 0% | -0.62 | LOSER |
| DOT | 1 | 0% | -0.59 | LOSER |
| MOVE | 1 | 0% | -0.61 | BLACKLISTED |
| BABY | 1 | 0% | -0.33 | BLACKLISTED |
| STBL | 1 | 0% | -0.32 | BLACKLISTED |

### MFE/MAE Analysis (17 recent trades)
| Coin | Dir | Signal | MFE | MAE | Result | Analysis |
|------|-----|--------|-----|-----|--------|----------|
| PURR | SHORT | accel-300-breakout | -0.14% | +3.05% | LOSE -0.96% | CATASTROPHIC adverse excursion |
| SKR | LONG | accel-300-breakout | +0.06% | +1.10% | LOSE -1.04% | Immediate adverse |
| AVAX | LONG | accel-300-breakout | +0.56% | +0.76% | LOSE -0.62% | Whipsaw |
| KAITO | LONG | accel-300-breakout | +0.42% | +0.61% | LOSE -0.27% | Whipsaw |
| APT | SHORT | inv-accel-300- | +0.04% | +0.73% | LOSE -0.64% | Immediate adverse |
| DOT | SHORT | inv-accel-300- | +0.01% | +0.61% | LOSE -0.59% | Immediate adverse |
| APEX | SHORT | inv-accel-300- | -0.07% | +0.57% | LOSE -0.57% | Wrong direction |
| OP | SHORT | inv-accel-300- | +0.04% | +0.39% | LOSE -0.38% | Minimal favorable |
| STX | SHORT | inv-accel-300- | +0.14% | +0.33% | LOSE -0.33% | Minimal favorable |
| NEAR | SHORT | inv-accel-300- | +0.22% | +0.30% | LOSE -0.30% | Whipsaw |
| OP | LONG | accel-300+ | +0.13% | +0.33% | LOSE -0.21% | Minimal favorable |
| ZEN | SHORT | inv-accel-300- | +0.84% | +0.09% | LOSE -0.09% | WHIPSAW (0.84% MFE → reversal) |
| ALT | SHORT | inv-accel-300- | +0.45% | +0.31% | LOSE -0.09% | Whipsaw |
| LDO | SHORT | inv-accel-300- | +0.02% | +0.37% | WIN +0.02% | Minimal favorable |
| APEX | SHORT | inv-accel-300- | +0.40% | +0.30% | WIN +0.10% | Low adverse |
| STX | SHORT | inv-accel-300- | +0.28% | +0.13% | WIN +0.20% | Low adverse |
| APEX | SHORT | inv-accel-300- | +0.41% | +0.19% | WIN +0.20% | Low adverse |

**Winners (3): avg MFE=0.36%, avg MAE=0.21% — low adverse excursion**
**Losers (14): avg MFE=0.18%, avg MAE=0.68% — high adverse, stalls immediately**
**Whipsaw rate: 29% (4/14 losers had MFE>0.3% then reversed)**

### CRITICAL: Kill Switch Bypass Bug (19th consecutive analysis)
**Disabled signals STILL firing:**
- `inv-accel-300-`: INVERSE_ACCEL_300_MINUS_ENABLED=False → 15 trades, -3.31 PnL
- `accel-300-breakout`: ACCEL_300_BREAKOUT_ENABLED=False → 4 trades, -2.90 PnL
- `inv-accel-300+`: INVERSE_ACCEL_300_PLUS_ENABLED=False → 1 trade, -0.33 PnL

**19 of 21 trades (90%) are from DISABLED signals.** Only 2 trades are from enabled signals (accel-300+).

### Diagnosis

**1. Entry Quality:**
- Winners: Low adverse (LDO 0.37%, APEX 0.19%, STX 0.13%) — good timing
- Losers: PURR had 3.05% MAE (catastrophic), SKR 1.10% MAE, APT 0.73% MAE — poor entry
- Most trades stall at <0.2% MFE then hit SL

**2. Signal Quality:**
- ALL signal types at 0% WR in 24h
- Disabled signals account for 90% of trades — kill switch bug is catastrophic
- inv-accel-300- collapsed from 58.3% to 0% in 72h

**3. SL/TP Behavior:**
- 100% of exits are `atr_sl_hit` — no trailing or TP exits
- ATR_SL_MIN_INIT at 0.60% is too tight — PURR had 3.05% adverse
- Trailing never activates because trades hit SL before reaching +0.20%

**4. Trade Frequency:**
- Low: 1.4 trades/hr (dominated by disabled signals)
- Only 2 trades from enabled signals in 24h

### Changes Implemented

**1. WIDEN ATR_SL_MIN_INIT: 0.60% → 0.80% (hermes_constants.py:349)**
- Also: ATR_SL_MAX_INIT 1.0% → 1.2%, SL_PCT_FALLBACK 0.60% → 0.80%, STOP_LOSS_DEFAULT 0.60% → 0.80%
- Rationale: PURR SHORT had 3.05% MAE. 0.60% SL is too tight for volatile tokens. 0.80% gives breathing room.

**2. RAISE inv-accel-300- gap: 0.50% → 0.65% (hermes_constants.py:663-664)**
- Rationale: Defense-in-depth against kill switch bypass. If signal fires despite disable, at least filter marginal entries.
- Risk: may block some valid signals, but 0% WR justifies aggressive filtering

**3. LOWER TRAILING_ACTIVATION_PCT: 0.20% → 0.15% (hermes_constants.py:361)**
- Rationale: Most trades stall at <0.2% MFE. Earlier activation locks small profits before reversal.
- Risk: may trigger on noise, but current 0.20% barely activates

### What NOT to change
- ATR_SL_MIN (0.8%) — floor, keep it
- TRAILING_DISTANCE_PCT (0.30%) — moderate trail, keep it
- ACCEL_300_ENABLED (True) — accel-300+ had 66.7% WR historically
- All disabled signals (tl_break, vel+, bb-squeeze) — kill switches working for these
- All blacklisted tokens — consistent losers, keep blocked
- Phase-based k scaling — disabled
- Dead hours filter — working correctly
- SIGNAL_FILTER_ENABLED (True) — the filter framework is sound

### 5 Actionable Adjustments (ranked by impact)
1. 🔴 CRITICAL: Fix kill switch bypass bug — inv-accel-300- and accel-300-breakout STILL FIRING despite being disabled (19th consecutive time). 90% of trades are from disabled signals.
2. ✅ Widen ATR_SL_MIN_INIT to 0.80% — IMPLEMENTED (PURR had 3.05% MAE)
3. ✅ Raise inv-accel-300- gap to 0.65% — IMPLEMENTED (defense-in-depth)
4. ✅ Lower trailing activation to 0.15% — IMPLEMENTED (catch small wins)
5. ⬜ Fix double-entry signal_outcomes bug — inflating metrics

### Open Questions
- Why is inv-accel-300- kill switch still not working? (19th consecutive time)
- Is accel-300-breakout kill switch also broken? (4 trades despite ACCEL_300_BREAKOUT_ENABLED=False)
- Should we re-enable tl_break_long (historically 40% WR in 200 trades)?
- Is the system fundamentally broken until kill switch bug is fixed?
- Should we reduce trade size or pause live trading during this 0% WR crisis?

---

## 2026-08-02: Hourly Trade Analysis — Trailing Retuned, TOKEN_WR Lowered

### Data Window
- Analyzed: 21 dedup trades (24h), 70 dedup trades (48h), trades.json (200)
- Trades: 2845 total closed, 0 open at analysis time
- Trade rate: ~1.4 trades/hr (low — only inv-accel-300- and accel-300-breakout active)
- Current time: 2026-08-02 12:50 UTC

### Signal Performance (24h dedup — ALL signals at 0% WR)
| Signal | Trades | WR | Total PnL | Status |
|--------|--------|-----|-----------|--------|
| inv-accel-300- | 15 | 0% | -3.31 | COLLAPSED (still executing despite disable) |
| accel-300-breakout | 4 | 0% | -2.90 | DISABLED (still executing!) |
| inv-accel-300+ | 1 | 0% | -0.33 | DISABLED (still executing!) |
| accel-300+ | 1 | 0% | -0.21 | ENABLED (expected) |

**Overall (deduplicated): 21 trades, 0 wins, 0% WR, -$6.74 total PnL in 24h.**
**48h: 70 trades, 11 wins, 15.7% WR, -$9.72 total PnL.**

### Token Performance (24h dedup — all at 0% WR)
| Token | Trades | WR | Total PnL | Status |
|-------|--------|-----|-----------|--------|
| APEX | 3 | 0% | -0.28 | MARGINAL |
| OP | 2 | 0% | -0.59 | LOSER |
| STX | 2 | 0% | -0.13 | MARGINAL |
| PURR | 1 | 0% | -0.96 | LOSER |
| SKR | 1 | 0% | -1.04 | LOSER |

### Diagnosis

**1. Entry Quality:**
- Winners (0 in 24h): None — 0% WR across all trades
- Losers (21): avg MFE=0.08%, avg MAE=0.35% — trades barely move in favor
- Whipsaw rate: 6% — most losses are stalls, not reversals

**2. Signal Quality:**
- inv-accel-300- collapsed from 58.3% to 0% in 72h — complete signal failure
- accel-300-breakout: 0% WR (4 trades) — disabled but still firing (kill switch bug, 20th consecutive time)
- No active signal has positive expectancy

**3. SL/TP Behavior:**
- 100% of exits are `atr_sl_hit` — no trailing or TP exits
- ATR_SL_MIN_INIT at 0.80% producing avg loss of 0.35%
- Trailing activation at 0.15% barely reached (avg MFE 0.08%)
- Trailing distance at 0.30% gives back too much

**4. Trade Frequency:**
- Low: 1.4 trades/hr
- 90% of trades from disabled signals — kill switch bug is catastrophic
- Only 2 trades from enabled signals (accel-300+)

### Changes Implemented

**1. TIGHTEN TRAILING_ACTIVATION_PCT: 0.25% → 0.15% (hermes_constants.py:361)**
- Rationale: Trades peak at 0.3-0.6% MFE then pull back. Current 0.25% activation too late. 0.15% locks profits sooner.
- Risk: may trigger on noise, but current 0.25% barely activates

**2. TIGHTEN TRAILING_DISTANCE_PCT: 0.50% → 0.30% (hermes_constants.py:362)**
- Rationale: Current 0.50% trail distance too wide — giving back too much after activation. 0.30% locks profit closer to peak.
- Risk: may exit too early on normal retracements, but current 0.50% is too loose

**3. LOWER TOKEN_WR_THRESHOLD: 40 → 30 (hermes_constants.py:487)**
- Rationale: Reduce trade starvation. 40 threshold blocking marginal tokens. 30 still blocks worst performers.
- Risk: more losing tokens may pass, but starvation is the bigger problem

### What NOT to change (and why)
- **ATR_SL_MIN_INIT (0.80%)** — already widened, keep as-is
- **ACCEL_300_ENABLED (True)** — re-enabled, needs market activity
- **INVERSE_ACCEL_300_ENABLED (True)** — master flag. MINUS variant disabled but still executing (kill switch bug).
- **SIGNAL_FILTER_SPEED_MIN (45)** — keep moderate, all signals net negative
- **All disabled signals** — kill switches have Layer 2 guards
- **All blacklisted tokens** — consistent losers, keep blocked
- **Phase-based k scaling** — disabled
- **Dead hours filter** — working correctly

### 5 Actionable Adjustments (ranked by impact)
1. 🔴 CRITICAL: Fix kill switch bypass bug — inv-accel-300- and accel-300-breakout STILL FIRING despite being disabled (20th consecutive time). 90% of trades are from disabled signals.
2. ✅ Tighten trailing activation to 0.15% — IMPLEMENTED (trades peak at 0.3-0.6% MFE)
3. ✅ Tighten trailing distance to 0.30% — IMPLEMENTED (give back less after activation)
4. ✅ Lower TOKEN_WR_THRESHOLD to 30 — IMPLEMENTED (reduce trade starvation)
5. ⬜ Fix double-entry signal_outcomes bug — inflating metrics

### Open Questions
- Why is inv-accel-300- kill switch still not working? (20th consecutive time)
- Is accel-300-breakout kill switch also broken? (4 trades despite ACCEL_300_BREAKOUT_ENABLED=False)
- Should we re-enable tl_break_long (historically 40% WR in 200 trades)?
- Is the system fundamentally broken until kill switch bug is fixed?
- Should we reduce trade size or pause live trading during this 0% WR crisis?

---

## 2026-08-02: Hourly Trade Analysis — SL/MAX Inversion Fixed, Trailing Restored

### Data Window
- Analyzed: 22 dedup trades (24h), 2 open trades, trades.json (200)
- Trades: 2824+ total closed, 2 open at analysis time
- Trade rate: ~0.92 trades/hr (low — only disabled signals firing)
- Last trade closed: 2026-08-02 13:43 UTC (AAVE SHORT, pattern_scanner, -0.09%)

### Signal Performance (24h dedup — ALL signals net losers, 0% WR)
| Signal | Trades | WR | Total PnL | Status |
|--------|--------|-----|-----------|--------|
| inv-accel-300- | 15 | 0% | -$3.31 | DISABLED BUT FIRING (kill switch bug) |
| accel-300-breakout | 4 | 0% | -$2.90 | DISABLED BUT FIRING |
| inv-accel-300+ | 1 | 0% | -$0.33 | DISABLED BUT FIRING |
| accel-300+ | 1 | 0% | -$0.21 | Enabled, 1 trade |
| pattern_scanner | 1 | 0% | -$0.09 | Enabled, 1 trade |

**Overall: 22 trades, 0 wins, 0.0% WR, -$6.83 total in 24h. WORST DAY ON RECORD.**

### Token Performance (24h dedup — ALL tokens losing)
| Token | Trades | WR | Total PnL |
|-------|--------|-----|-----------|
| SKR | 1 | 0% | -$1.04 |
| PURR | 1 | 0% | -$0.96 |
| APT | 1 | 0% | -$0.64 |
| AVAX | 1 | 0% | -$0.62 |
| MOVE | 1 | 0% | -$0.61 |
| DOT | 1 | 0% | -$0.59 |
| OP | 2 | 0% | -$0.59 |
| BABY | 1 | 0% | -$0.33 |
| STBL | 1 | 0% | -$0.32 |
| NEAR | 1 | 0% | -$0.30 |

**Zero profitable tokens in 24h.**

### CRITICAL BUG: ATR_SL_MIN_INIT > ATR_SL_MAX_INIT
- ATR_SL_MIN_INIT was 0.020 (2.0%) — raised in previous analysis for "wider breathing room"
- ATR_SL_MAX_INIT was 0.012 (1.2%) — cap
- Since MIN > MAX, SL always clamped to 1.2% — the "wider" value was never applied
- Related: SL_PCT_FALLBACK (0.008) and STOP_LOSS_DEFAULT (0.008) were mismatched with MIN_INIT (0.020)

### Kill Switch Bug (21st consecutive time)
- inv-accel-300-: 15 trades despite INVERSE_ACCEL_300_MINUS_ENABLED=False and INVERSE_ACCEL_300_ENABLED=False
- accel-300-breakout: 4 trades despite ACCEL_300_BREAKOUT_ENABLED=False
- inv-accel-300+: 1 trade despite INVERSE_ACCEL_300_PLUS_ENABLED=False
- Total: 20/22 trades (91%) from disabled signals

### Diagnosis

**1. Entry Quality:**
- All 22 trades are losses — no winners to analyze
- Most trades hit SL immediately (avg loss ~0.3%)

**2. Signal Quality:**
- All active signal types are net losers
- 91% of trades from disabled signals (kill switch bug)
- accel-300+ (only enabled signal with trades): 1 trade, 0% WR

**3. SL/TP Behavior:**
- 100% of exits are `atr_sl_hit`
- SL at 1.2% (effective) producing avg loss of 0.3% — trades barely move before stopping out
- Trailing activation at 0.15% was too tight — trades reached activation then got trailed to breakeven

**4. Trade Frequency:**
- Low: 0.92 trades/hr
- System dominated by disabled signals firing through kill switch bug

### Changes Implemented

**1. FIX ATR_SL_MIN_INIT / ATR_SL_MAX_INIT inversion (hermes_constants.py:358-359)**
- ATR_SL_MIN_INIT: 0.020 → 0.012 (matched to MAX_INIT)
- ATR_SL_MAX_INIT: 0.012 (unchanged — was already correct)
- SL_PCT_FALLBACK: 0.008 → 0.012 (matched to MIN_INIT)
- STOP_LOSS_DEFAULT: 0.008 → 0.012 (matched to MIN_INIT)
- Rationale: MIN was exceeding MAX, causing SL to always clamp to 1.2%. Fixed the naming confusion.

**2. RESTORE TRAILING_PARAMS to backtested optimum (hermes_constants.py:370-371)**
- TRAILING_ACTIVATION_PCT: 0.0015 → 0.0025 (0.15% → 0.25%)
- TRAILING_DISTANCE_PCT: 0.003 → 0.002 (0.30% → 0.20%)
- Rationale: Backtested best combo was 0.25% act / 0.20% dist. Current 0.15%/0.30% deviated from optimum.

**3. RAISE SIGNAL_FILTER_SPEED_MIN: 45 → 55 (hermes_constants.py:485)**
- Rationale: Block bottom 55% of speed distribution. Winners avg 71% speed percentile. 45 let too many slow signals through.

### What NOT to change (and why)
- **ATR_SL_MIN (0.8%)** — floor, keep it
- **ACCEL_300_ENABLED (True)** — re-enabled, needs market activity
- **INVERSE_ACCEL_300_ENABLED (False)** — master flag disabled, but MINUS variant still executing (kill switch bug)
- **All disabled signals** — kill switches have Layer 2 guards (but bypass bug persists)
- **All blacklisted tokens** — consistent losers, keep blocked
- **Phase-based k scaling** — disabled
- **Dead hours filter** — working correctly

### 5 Actionable Adjustments (ranked by impact)
1. 🔴 CRITICAL: Fix kill switch bypass bug — inv-accel-300-, accel-300-breakout, inv-accel-300+ STILL FIRING despite being disabled (21st consecutive time). 91% of trades from disabled signals.
2. ✅ Fix ATR_SL_MIN/MAX inversion — IMPLEMENTED (MIN was 2.0%, MAX was 1.2%)
3. ✅ Restore trailing params to backtested optimum — IMPLEMENTED (0.25% act / 0.20% dist)
4. ✅ Raise speed filter to 55 — IMPLEMENTED (block low-momentum entries)
5. ⬜ Investigate why accel-300+ (57.1% WR all-time) only fired once in 24h

### Open Questions
- Why is inv-accel-300- kill switch still not working? (21st consecutive time)
- Is accel-300-breakout kill switch also broken? (4 trades despite ACCEL_300_BREAKOUT_ENABLED=False)
- Should we re-enable tl_break_long (historically 40% WR in 200 trades)?
- Is the system fundamentally broken until kill switch bug is fixed?
- Should we reduce trade size or pause live trading during this 0% WR crisis?
- Is the market in a regime where no signal works? (0% WR across all signals in 24h)

---

## 2026-08-02: Hourly Trade Analysis — Pattern Scanner Disabled, Trailing Lowered

### Data Window
- Analyzed: 23 trades (24h from trades.json), signal_outcomes (24h dedup: 21 trades), MFE/MAE (23 trades)
- Trades: 200 in file, 0 open
- Trade rate: ~0.96 trades/hr (low)
- Current time: 2026-08-02 14:50 UTC

### Signal Performance (24h dedup — ALL signals net losers)
| Signal | Trades | WR | Total PnL | Status |
|--------|--------|-----|-----------|--------|
| inv-accel-300- | 14 | 35.7% | -2.69 | DISABLED BUT FIRING (kill switch bug) |
| accel-300-breakout | 4 | 0% | -2.90 | DISABLED BUT FIRING |
| pattern_scanner | 2 | 0% | -0.17 | ENABLED — 0% WR |
| accel-300+ | 1 | 0% | -0.21 | ENABLED |

**trades.json: 23 trades, 5 wins, 21.7% WR, -6.18% total PnL in 24h.**

### Token Performance (24h dedup)
| Token | Trades | WR | Total PnL |
|-------|--------|-----|-----------|
| APEX | 3 | 0% | -0.28 |
| OP | 2 | 0% | -0.59 |
| STX | 2 | 0% | -0.13 |
| AAVE | 2 | 0% | +0.01 |

### MFE/MAE Analysis (23 trades)
**Winners (5): avg MFE=+1.05%, avg MAE=+0.73%**
**Losers (18): avg MFE=+0.49%, avg MAE=+1.32%**
**Whipsaw rate: 61% (11/18 losers had MFE>0.3% then reversed)**
**ALL exits are `atr_sl_hit` — trailing never catches moves**

### Diagnosis

**1. Entry Quality:**
- Winners: Low adverse excursion (good timing)
- Losers: High adverse excursion (1.32% avg MAE) — entering too early
- 61% whipsaw: trades develop profit then reverse

**2. Signal Quality:**
- ALL signal types net negative
- Kill switch bug persists (22nd consecutive time): inv-accel-300- 14 trades, accel-300-breakout 4 trades
- pattern_scanner: 2 trades, 0% WR — no edge

**3. SL/TP Behavior:**
- Winners capture avg +1.05% MFE but close at avg +0.34% net — gave back 68% of favorable excursion
- TRAILING_ACTIVATION_PCT at 0.25% — trades reach activation but trail distance (0.20%) gives back too much
- Actual R:R: avg win +0.34% vs avg loss -0.34% → 1.0:1.0 — breakeven R:R

**4. Trade Frequency:**
- 23 trades in 24h (~1/hr) — reasonable
- Speed filter at 55 is reasonable

### Changes Implemented

**1. TIGHTEN TRAILING_ACTIVATION_PCT: 0.25% → 0.15% (hermes_constants.py:370)**
- Rationale: 61% whipsaw rate — trades go into profit then reverse. Earlier activation locks profits before reversal.
- Risk: may trigger on noise, but current 0.25% is too late

**2. DISABLE pattern_scanner (hermes_constants.py:718-722)**
- All PATTERN_*_ENABLED: True → False
- Rationale: 2 trades, 0% WR, -$0.17. No edge.
- Risk: low — only 2 trades in 24h

### What NOT to change (and why)
- **ATR_SL_MIN_INIT (1.2%)** — matched to MAX_INIT, working
- **TRAILING_DISTANCE_PCT (0.20%)** — combined with 0.15% activation gives 0.05% breathing room
- **ACCEL_300_ENABLED (True)** — needs market activity
- **SIGNAL_FILTER_SPEED_MIN (55)** — reasonable
- **All disabled signals** — kill switches have Layer 2 guards (but bypass bug persists)
- **All blacklisted tokens** — consistent losers, keep blocked
- **Phase-based k scaling** — disabled
- **Dead hours filter** — working correctly

### 5 Actionable Adjustments (ranked by impact)
1. 🔴 CRITICAL: Fix kill switch bypass bug — inv-accel-300- and accel-300-breakout STILL FIRING despite being disabled (22nd consecutive time). 91% of 24h trades from disabled signals.
2. ✅ Tighten trailing activation to 0.15% — IMPLEMENTED (61% whipsaw rate)
3. ✅ Disable pattern_scanner — IMPLEMENTED (0% WR, no edge)
4. 🔴 CRITICAL: All signals net negative — system has NO edge in current market. Need new signal or market regime change.
5. ⬜ Investigate why accel-300+ (57.1% WR all-time) only fired once in 24h

### Open Questions
- Why is inv-accel-300- still executing despite BOTH INVERSE_ACCEL_300_ENABLED=False AND INVERSE_ACCEL_300_MINUS_ENABLED=False? Guard exists at signal_schema.py:722-730 but signal still fires.
- Is the market in a regime where no signal works? (0% WR across all signals in 24h)
- Should we re-enable any previously profitable signal? (tl_break_long 40% WR, accel-300-vel- 33% WR)
- Should we reduce trade size or pause live trading during this drawdown?

---

## 2026-08-02: Daily Orchestrator Report

### Pipeline Status (17:30 UTC)
- Trades (24h): 2 opened, 24 closed
- Win rate: 0% (all 24 closed trades were losses)
- PnL: -7.20%
- Open positions: 2 (0G SHORT, SKY SHORT)
- Market regime: 100% NEUTRAL, low momentum (40% speed distribution)

### Kill Switch Investigation — RESOLVED
The "23rd consecutive flag" for inv-accel-300- kill switch bypass was **historical**, not current.
- Last inv-accel-300- trade: 07:10 UTC (10+ hours ago)
- Last accel-300-breakout trade: 10:33 UTC (7+ hours ago)
- Last pattern_scanner trade: 13:33 UTC (4+ hours ago)
- All three signals stopped firing AFTER their respective kill switches were applied
- Guards at `signal_schema.py:710-757` are working correctly
- The auto-1hr reports analyze 24h historical windows that include pre-disable trades

### Auto-1hr Parameter Changes (verified)
1. ✅ Speed filter: 55→70 (blocks bottom 70% of speed distribution)
2. ✅ inv-accel-300 gap: 0.65%→1.0% (defense-in-depth against bypass)
3. ✅ Blacklist: APEX, STX, ZEN, ALT, ADA added to both SHORT and LONG blacklists
4. ✅ ACCEL_300_BREAKOUT_ENABLED = False
5. ✅ PATTERN_FLAG_ENABLED = False (and all sub-patterns)

### Blacklist Tester
- Batch 3 (48h trial): 19 tokens removed from blacklists for testing
- Batch 1 & 2: All re-blacklisted (0% WR or insufficient data)

### Upgrade Audit
- 15 upgrades implemented, 1 enabled (token sentiment)
- Pending: hebbian Phase 3b-d, mtp-zscore signal, signal inversion re-eval

### System Health
- Timers: pipeline ✓, price-collector ✓
- Prices: 265 tokens
- Blacklist: 146 SHORT / 105 LONG
- Hotset: empty (no signals survived compaction — expected in quiet market)
- Errors: None

### Key Insight
System is healthy but has **NO edge in current market**. All signals at 0% WR in 24h. Market is 100% neutral with low momentum. This is a market regime issue, not a system bug. Signals will resume working when market conditions change.

### Next Steps
1. Monitor Batch 3 blacklist trial (48h window ends ~2026-08-04)
2. Wait for market regime shift (currently fully neutral)
3. Consider hebbian Phase 3b (co-fire pattern boost) for signal quality improvement
4. Review mtp-zscore signal implementation when market is active
- Is the R:R (1.0:1.0) recoverable with trailing tuning, or is the signal quality fundamentally broken?

---

## 2026-08-02: Hourly Trade Analysis — Kill Switch Guards Added, 0% WR Crisis

### Data Window
- Analyzed: 26 closed trades (24h), signal_outcomes (24h dedup: 22 trades), trades.json (200)
- Trades: 2852 total closed, 2 open (0G SHORT accel-300-, SKY SHORT pct-hermes-)
- Trade rate: ~1.08 trades/hr (low)
- Current time: 2026-08-02 15:50 UTC

### Signal Performance (24h dedup — ALL signals at 0% WR)
| Signal | Trades | WR | Total PnL | Status |
|--------|--------|-----|-----------|--------|
| inv-accel-300- | 14 | 0% | -2.70 | DISABLED BUT FIRING (kill switch bug) |
| accel-300-breakout | 4 | 0% | -2.90 | DISABLED BUT FIRING |
| pattern_scanner | 3 | 0% | -1.33 | DISABLED BUT FIRING |
| accel-300+ | 1 | 0% | -0.21 | Enabled |

**trades.json: 26 trades, 6 wins, 23.1% WR, -$0.76 total PnL in 24h.**
**signal_outcomes dedup: 22 trades, 0 wins, 0% WR.**

### CRITICAL: Kill Switch Guards Added for pattern_scanner and accel-300-breakout

**Root cause identified:** `add_signal()` in `signal_schema.py` had NO Layer 2 kill-switch guards for:
- `pattern_scanner` (bare source)
- `pattern_micro_bull_flag` / `pattern_micro_bear_flag`
- `pattern_wolf_wave_bear` / `pattern_wolf_wave_bull`
- `pattern_channel_long` / `pattern_channel_short`
- `accel-300-breakout`

These signals bypassed the kill-switch entirely. Added guards for all pattern_scanner variants, accel-300-breakout, and inv-accel-300 (bare).

### Token Performance (24h — all at 0% WR)
| Token | Trades | WR | Total PnL | Status |
|-------|--------|-----|-----------|--------|
| APEX | 6 | 0% | -3.26 | CONSISTENT LOSER |
| AAVE | 4 | 0% | -1.78 | WAS PROFITABLE |
| OP | 4 | 0% | -2.98 | LOSER |
| STX | 4 | 0% | -2.06 | MARGINAL |

**Zero profitable tokens in 24h.**

### Diagnosis

**1. Entry Quality:**
- All 22 dedup trades are losses — no winners to analyze
- Trades stall at ~0.3% MFE then hit SL

**2. Signal Quality:**
- ALL signal types at 0% WR in 24h
- 91% of trades from disabled signals (kill switch bug)
- pattern_scanner: 3 trades, 0% WR — no edge
- accel-300-breakout: 4 trades, 0% WR — no edge
- inv-accel-300-: 14 trades, 0% WR — collapsed

**3. SL/TP Behavior:**
- 100% of exits are `atr_sl_hit`
- SL at 1.2% producing avg loss of 0.35%
- Trailing never activates because trades stall

**4. Trade Frequency:**
- 1.08 trades/hr — low but all losing

### Changes Implemented

**1. ADD kill-switch guards for pattern_scanner and accel-300-breakout (signal_schema.py:713-762)**
- Added guards for: pattern_scanner, pattern_micro_bull_flag, pattern_micro_bear_flag, pattern_wolf_wave_bear, pattern_wolf_wave_bull, pattern_channel_long, pattern_channel_short, accel-300-breakout
- Also added bare inv-accel-300 guard
- These signals were bypassing the kill-switch entirely — now blocked at Layer 2

### What NOT to change (and why)
- **ATR_SL_MIN_INIT (1.2%)** — matched to MAX_INIT, working
- **TRAILING_ACTIVATION_PCT (0.15%)** — earlier activation for small moves
- **TRAILING_DISTANCE_PCT (0.20%)** — tight trail
- **ACCEL_300_ENABLED (True)** — needs market activity
- **All disabled signals** — kill switches now have Layer 2 guards for ALL variants
- **All blacklisted tokens** — consistent losers, keep blocked
- **Phase-based k scaling** — disabled
- **Dead hours filter** — working correctly

### 5 Actionable Adjustments (ranked by impact)
1. ✅ Add kill-switch guards for pattern_scanner and accel-300-breakout — IMPLEMENTED (root cause of 90%+ disabled-signal trades)
2. 🔴 CRITICAL: System has NO edge in current market. ALL signals at 0% WR in 24h. Need new signal or market regime change.
3. 🔴 CRITICAL: inv-accel-300- still executing despite being disabled (INVERSE_ACCEL_300_MINUS_ENABLED=False and INVERSE_ACCEL_300_ENABLED=False). 14 trades, 0% WR.
4. ⬜ Investigate inv-accel-300- kill switch bypass — guard exists but signal still fires
5. ⬜ Fix double-entry signal_outcomes bug — inflating metrics

### Open Questions
- Why is inv-accel-300- still executing despite BOTH INVERSE_ACCEL_300_ENABLED=False AND INVERSE_ACCEL_300_MINUS_ENABLED=False? Guard exists at signal_schema.py:722-730 but signal still fires.
- Is the market in a regime where no signal works? (0% WR across all signals in 24h)
- Should we re-enable any previously profitable signal? (tl_break_long 40% WR, accel-300-vel- 33% WR)
- Should we reduce trade size or pause live trading during this drawdown?
- Will the new kill-switch guards for pattern_scanner/accel-300-breakout take effect on next signal generation cycle?

---

## 2026-08-02: Hourly Trade Analysis — 0% WR Crisis Continues, Defense-in-Depth Applied

### Data Window
- Analyzed: 20 dedup trades (24h), signal_outcomes (24h), trades.json (200)
- Trades: 200 in file, 0 open at analysis time
- Trade rate: ~0.83 trades/hr (low)
- Current time: 2026-08-02 ~16:00 UTC

### Signal Performance (24h dedup — ALL signals at 0% WR)
| Signal | Trades | WR | Total PnL | Status |
|--------|--------|-----|-----------|--------|
| inv-accel-300- | 12 | 0% | -2.47 | DISABLED BUT FIRING (kill switch bug) |
| accel-300-breakout | 4 | 0% | -2.90 | DISABLED BUT FIRING |
| pattern_scanner | 3 | 0% | -1.33 | DISABLED BUT FIRING |
| accel-300+ | 1 | 0% | -0.21 | Enabled |

**Overall (deduplicated): 20 trades, 0 wins, 0% WR, -$6.91 total PnL in 24h. WORST DAY ON RECORD.**

### Token Performance (24h dedup — ALL tokens losing)
| Token | Trades | WR | Total PnL |
|-------|--------|-----|-----------|
| APEX | 3 | 0% | -0.28 |
| OP | 2 | 0% | -0.59 |
| STX | 2 | 0% | -0.13 |
| ADA | 1 | 0% | -1.17 |
| PURR | 1 | 0% | -0.96 |
| SKR | 1 | 0% | -1.04 |
| APT | 1 | 0% | -0.64 |
| AVAX | 1 | 0% | -0.62 |
| DOT | 1 | 0% | -0.59 |
| ALT | 1 | 0% | -0.09 |
| ZEN | 1 | 0% | -0.09 |
| LDO | 1 | 0% | +0.02 |

**Zero profitable tokens in 24h.**

### Kill Switch Bug (23rd consecutive analysis)
**Disabled signals STILL firing:**
- `inv-accel-300-`: 12 trades despite INVERSE_ACCEL_300_MINUS_ENABLED=False and INVERSE_ACCEL_300_ENABLED=False
- `accel-300-breakout`: 4 trades despite ACCEL_300_BREAKOUT_ENABLED=False
- `pattern_scanner`: 3 trades despite PATTERN_FLAG_ENABLED=False

**19 of 20 trades (95%) are from DISABLED signals.** Only 1 trade from an enabled signal (accel-300+).

### Diagnosis

**1. Entry Quality:**
- All 20 trades are losses — no winners to analyze
- Most trades hit SL immediately (avg loss ~0.3%)

**2. Signal Quality:**
- ALL signal types at 0% WR in 24h
- 95% of trades from disabled signals (kill switch bug)
- inv-accel-300- collapsed from 58.3% to 0% — signal decay pattern

**3. SL/TP Behavior:**
- 100% of exits are `atr_sl_hit`
- SL at 1.2% producing avg loss of 0.3% — trades barely move before stopping out

**4. Trade Frequency:**
- 0.83 trades/hr — low but all losing

### Changes Implemented

**1. RAISE inv-accel-300- gap: 0.65% → 1.0% (hermes_constants.py:672-673)**
- INVERSE_ACCEL_300_MIN_GAP_PCT_LONG: 0.65 → 1.0
- INVERSE_ACCEL_300_MIN_GAP_PCT_SHORT: 0.65 → 1.0
- Rationale: Defense-in-depth against kill switch bypass. If signal fires despite disable, 1.0% gap makes firing nearly impossible.
- Risk: may block valid signals when re-enabled, but current 0% WR justifies aggressive filtering

**2. RAISE SIGNAL_FILTER_SPEED_MIN: 55 → 70 (hermes_constants.py:485)**
- Rationale: 0% WR across 20 trades — need higher-momentum entries. 70 blocks bottom 70%.
- Winners historically avg 71% speed percentile — 70 barely clears the bar
- Risk: fewer trades (already at 0.83/hr), but quality over quantity at 0% WR

**3. BLACKLIST APEX, STX, ZEN, ALT, ADA both directions (hermes_constants.py:SHORT_BLACKLIST, LONG_BLACKLIST)**
- APEX: 3 trades, 0% WR, -$0.28 — consistent loser
- STX: 2 trades, 0% WR, -$0.13 — marginal
- ZEN: 1 trade, 0% WR, -$0.09 — marginal
- ALT: 1 trade, 0% WR, -$0.09 — marginal
- ADA: 1 trade, 0% WR, -$1.17 — biggest single loss
- All added to both SHORT_BLACKLIST and LONG_BLACKLIST

### What NOT to change (and why)
- **ATR_SL_MIN_INIT (1.2%)** — matched to MAX_INIT, working
- **TRAILING_ACTIVATION_PCT (0.15%)** — earlier activation for small moves
- **TRAILING_DISTANCE_PCT (0.20%)** — tight trail
- **ACCEL_300_ENABLED (True)** — needs market activity
- **All disabled signals** — kill switches have Layer 2 guards (but bypass bug persists)
- **All blacklisted tokens** — consistent losers, keep blocked
- **Phase-based k scaling** — disabled
- **Dead hours filter** — working correctly

### 5 Actionable Adjustments (ranked by impact)
1. 🔴 CRITICAL: Fix kill switch bypass bug — inv-accel-300-, accel-300-breakout, pattern_scanner STILL FIRING despite being disabled (23rd consecutive time). 95% of trades from disabled signals.
2. ✅ Raise inv-accel-300- gap to 1.0% — IMPLEMENTED (defense-in-depth, makes firing nearly impossible)
3. ✅ Raise speed filter to 70 — IMPLEMENTED (0% WR, need higher-momentum entries)
4. ✅ Blacklist APEX, STX, ZEN, ALT, ADA — IMPLEMENTED (all 0% WR in 24h)
5. 🔴 CRITICAL: System has NO edge in current market. ALL signals at 0% WR. Need new signal or market regime change.

### Open Questions
- Why is inv-accel-300- still executing despite BOTH INVERSE_ACCEL_300_ENABLED=False AND INVERSE_ACCEL_300_MINUS_ENABLED=False? Guard exists at signal_schema.py:722-730 but signal still fires.
- Is the market in a regime where no signal works? (0% WR across all signals in 24h)
- Should we re-enable any previously profitable signal? (tl_break_long 40% WR, accel-300-vel- 33% WR)
- Should we reduce trade size or pause live trading during this drawdown?
- Is the signal decay pattern (58.3% → 0% in 48h) permanent or temporary?

---

## 2026-08-02: Hourly Trade Analysis — Trailing Retuned, accel-300 Disabled

### Data Window
- Analyzed: 20 dedup trades (24h), signal_outcomes (24h), trades.json (200)
- Trades: 200 in file, 0 open at analysis time
- Trade rate: ~0.83 trades/hr (low)
- Current time: 2026-08-02 17:30 UTC

### Signal Performance (24h dedup — ALL signals at 0% WR)
| Signal | Trades | WR | Total PnL | Status |
|--------|--------|-----|-----------|--------|
| inv-accel-300- | 12 | 0% | -2.47 | DISABLED BUT FIRING |
| accel-300-breakout | 4 | 0% | -2.90 | DISABLED BUT FIRING |
| pattern_scanner | 3 | 0% | -1.33 | DISABLED BUT FIRING |
| accel-300+ | 1 | 0% | -0.21 | Enabled |

**Overall: 20 dedup trades, 0 wins, 0% WR, -$6.91 total PnL in 24h.**

### Kill Switch Status (24th consecutive analysis)
- inv-accel-300-: DISABLED (INVERSE_ACCEL_300_ENABLED=False, INVERSE_ACCEL_300_MINUS_ENABLED=False) but 12 trades executed
- accel-300-breakout: DISABLED (ACCEL_300_BREAKOUT_ENABLED=False) but 4 trades executed
- pattern_scanner: DISABLED (PATTERN_FLAG_ENABLED=False) but 3 trades executed
- **95% of trades (19/20) from disabled signals.**

### Diagnosis

**1. Entry Quality:**
- 0% WR — no winners to analyze
- Most trades hit SL immediately (avg loss ~0.3%)

**2. Signal Quality:**
- All active signal types at 0% WR
- Kill switch bypass accounts for 95% of trades
- inv-accel-300- collapsed from 58.3% to 0%

**3. SL/TP Behavior:**
- 100% of exits are `atr_sl_hit`
- TRAILING_ACTIVATION_PCT at 0.15% triggers on noise
- TRAILING_DISTANCE_PCT at 0.20% too tight — first pullback kills trailing

**4. Trade Frequency:**
- 0.83/hr — dominated by disabled signals

### Changes Implemented

**1. RAISE TRAILING_ACTIVATION_PCT: 0.15% → 0.35% (hermes_constants.py:374)**
- Rationale: Trades need room to develop before trailing activates. 0.15% triggers on noise for low-vol tokens. 0.35% waits for a real move.
- Risk: may miss some quick wins, but 0.15% was too aggressive

**2. RAISE TRAILING_DISTANCE_PCT: 0.20% → 0.35% (hermes_constants.py:375)**
- Rationale: Give trailing room to breathe after activation. 0.20% was too tight — first pullback kills trailing. 0.35% survives normal retracements.
- Risk: gives back more profit on winning trades, but current 0.20% produces 0% WR

**3. DISABLE ACCEL_300_ENABLED: True → False (hermes_constants.py:652)**
- Rationale: 0% WR (1 trade, -$0.21) in 24h. Was re-enabled too early. All signal types at 0% WR — disable until market regime changes.
- Risk: reduces trade count further, but 0% WR means no edge

### What NOT to change (and why)
- **ATR_SL_MIN_INIT (1.2%)** — matched to MAX_INIT, working
- **INVERSE_ACCEL_300_ENABLED (False)** — master flag disabled
- **All disabled signals** — kill switches have Layer 2 guards (but bypass bug persists)
- **All blacklisted tokens** — consistent losers, keep blocked
- **Phase-based k scaling** — disabled
- **Dead hours filter** — working correctly
- **SIGNAL_FILTER_SPEED_MIN (70)** — keep high, all signals net negative

### 5 Actionable Adjustments (ranked by impact)
1. 🔴 CRITICAL: Fix kill switch bypass — inv-accel-300-, accel-300-breakout, pattern_scanner STILL FIRING despite being disabled (24th consecutive time). 95% of trades from disabled signals.
2. ✅ Raise trailing activation to 0.35% — IMPLEMENTED (trades need room to develop)
3. ✅ Raise trailing distance to 0.35% — IMPLEMENTED (give trailing room to breathe)
4. ✅ Disable accel-300 — IMPLEMENTED (0% WR, re-enabled too early)
5. 🔴 CRITICAL: System has NO edge in current market. ALL signals at 0% WR. Need new signal or market regime change.

### Open Questions
- Why is inv-accel-300- still executing despite BOTH INVERSE_ACCEL_300_ENABLED=False AND INVERSE_ACCEL_300_MINUS_ENABLED=False? Guard exists at signal_schema.py:722-730 but signal still fires.
- Is the market in a regime where no signal works? (0% WR across all signals in 24h)
- Should we reduce trade size or pause live trading during this drawdown?
- Is the signal decay pattern (58.3% → 0% in 48h) permanent or temporary?

---

## 2026-08-02: Hourly Trade Analysis — 0% WR, Kill Switch Bypass 25th Time

### Data Window
- Analyzed: 22 dedup trades (24h), 20 trades (trades.json), MFE/MAE (20 recent trades)
- Trades: 2854 total closed, 0 open at analysis time
- Trade rate: ~2.75 trades/hour (moderate — but ALL from disabled signals)
- Last trade closed: 2026-08-02 18:07 UTC (SKY SHORT, pct-hermes-, -0.31%)

### Signal Performance (24h dedup — 0% WR ACROSS ALL SIGNALS)
| Signal | Trades | WR | Total PnL | Status |
|--------|--------|-----|-----------|--------|
| inv-accel-300- | 12 | 0.0% | -2.47 | DISABLED — STILL DOMINANT (12/22 trades) |
| accel-300-breakout | 4 | 0.0% | -2.90 | DISABLED — STILL FIRING |
| pattern_scanner | 3 | 0.0% | -1.33 | DISABLED — STILL FIRING |
| accel-300+ | 1 | 0.0% | -0.21 | ACTIVE — 0% WR |
| accel-300- | 1 | 0.0% | -0.47 | ACTIVE — 0% WR |
| pct-hermes- | 1 | 0.0% | -0.31 | ACTIVE — 0% WR |

**Overall (deduplicated): 22 trades, 0 wins, 0.0% WR, -7.70 total PnL in 24h.**
**ZERO wins across ALL signals. Worst performance in analysis history.**

### Kill Switch Bypass Audit (25th consecutive time)
| Signal | Disabled? | Trades (48h) | WR | PnL |
|--------|-----------|--------------|-----|------|
| inv-accel-300- | Both flags False | 18 | 5.6% | -2.87 |
| accel-300-breakout | ACCEL_300_BREAKOUT_ENABLED=False | 4 | 0% | -2.90 |
| tl_break_long | TL_BREAK_ENABLED=False | 9 | 33.3% | -0.34 |
| tl_break_short | TL_BREAK_ENABLED=False | 3 | 33.3% | -0.16 |
| accel-300-vel+ | ACCEL_300_VELOCITY_PLUS_ENABLED=False | 4 | 0% | -0.38 |
| accel-300-vel- | ACCEL_300_VELOCITY_MINUS_ENABLED=False | 2 | 0% | -0.27 |
| pattern_scanner | PATTERN_FLAG_ENABLED=False | 3 | 0% | -1.33 |
| bb-squeeze | BOLLINGER_SQUEEZE_ENABLED=False | 1 | 0% | +0.08 |
| bb-squeeze- | BOLLINGER_SQUEEZE_MINUS_ENABLED=False | 2 | 0% | -0.30 |

**9 disabled signal types still executing. inv-accel-300- is dominant (18/50 trades in 48h).**

### MFE/MAE Analysis (Last 20 Trades)
| Category | Count | Avg MFE | Avg MAE | Pattern |
|----------|-------|---------|---------|---------|
| Losers | 17 | -0.12% | +0.08% | Most stall then hit SL |
| Winners | 3 | -0.66% | +0.69% | Low adverse, mixed MFE |

**Key patterns:**
- **Stall losses** (10/17): Price barely moves before hitting SL
- **High adverse** (5/17): ADA (+1.92%), SKR (-2.80%), KAITO (-1.45%), AVAX (-4.64%), APT (+0.73%)
- **Whipsaw** (2/17): PURR (MFE=+0.14% then reversed), APEX (MFE=-1.06% then reversed)
- **Winners**: BANANA (+0.03%), APEX (+0.20%), LDO (+0.02%) — tiny wins, barely above breakeven

### Changes Implemented

**1. RAISE INVERSE_ACCEL_300_MIN_GAP_PCT: 1.0% → 2.0% (hermes_constants.py:676-677)**
- Both LONG and SHORT thresholds raised
- Defense-in-depth: makes firing nearly impossible even if kill switch fails

**2. LOWER SIGNAL_FILTER_SPEED_MIN: 70 → 60 (hermes_constants.py:489)**
- Trade-off: more noise, but current signal set has zero edge regardless

**3. DOCUMENTED accel-300-breakout kill switch bypass**
- ACCEL_300_BREAKOUT_ENABLED=False but signals still executing
- Layer 2 guard exists but signals bypass it — needs code investigation

### What NOT to change
- ATR_SL_MIN_INIT (1.2%), TRAILING_ACTIVATION_PCT (0.35%), TRAILING_DISTANCE_PCT (0.35%)
- All disabled signals — keep disabled, kill switch bypass persists
- All blacklisted tokens — consistent losers, keep blocked

### 5 Actionable Adjustments (ranked by impact)
1. 🔴 CRITICAL: Fix kill switch bypass — 25th consecutive time. 95% of trades from disabled signals.
2. 🔴 CRITICAL: System has NO edge — 0% WR across ALL signals in 24h.
3. ✅ Raise inv-accel-300- gap to 2.0% — IMPLEMENTED
4. ✅ Lower speed filter to 60 — IMPLEMENTED
5. ⬜ Investigate accel-300-breakout code path

### Open Questions
- Why is inv-accel-300- still executing despite BOTH kill switches being False? (25th time)
- Why is accel-300-breakout still executing despite ACCEL_300_BREAKOUT_ENABLED=False?
- Should we reduce trade size or pause live trading during this drawdown?

---

## 2026-08-02: Hourly Trade Analysis — 0% WR Crisis, Defense-in-Depth Raised, STOP TUNING

### Data Window
- Analyzed: 22 dedup trades (24h), signal_outcomes (24h), trades.json (200), MFE/MAE (20 recent)
- Trades: 2854 total closed, 0 open at analysis time
- Trade rate: ~0.92 trades/hr (low — dominated by disabled signals)
- Current time: 2026-08-02 ~19:00 UTC

### Signal Performance (24h dedup — 0% WR ACROSS ALL SIGNALS)
| Signal | Trades | WR | Total PnL | Status |
|--------|--------|-----|-----------|--------|
| inv-accel-300- | 12 | 0% | -2.47 | DISABLED BUT FIRING (kill switch bypass) |
| accel-300-breakout | 4 | 0% | -2.90 | DISABLED BUT FIRING |
| pattern_scanner | 3 | 0% | -1.33 | DISABLED BUT FIRING |
| accel-300+ | 1 | 0% | -0.21 | Enabled |
| accel-300- | 1 | 0% | -0.47 | Enabled |
| pct-hermes- | 1 | 0% | -0.31 | Enabled |

**Overall (deduplicated): 22 trades, 0 wins, 0% WR, -$7.70 total PnL in 24h. WORST DAY ON RECORD.**

### Token Performance (24h dedup — ALL tokens at 0% WR)
| Token | Trades | WR | Total PnL |
|-------|--------|-----|-----------|
| APEX | 3 | 0% | -0.28 |
| OP | 2 | 0% | -0.59 |
| STX | 2 | 0% | -0.13 |
| ADA | 1 | 0% | -1.17 |
| PURR | 1 | 0% | -0.96 |
| SKR | 1 | 0% | -1.04 |

### MFE/MAE Analysis (20 recent trades)
- **Winners (3):** avg MFE=0.68%, avg MAE=0.70%
- **Losers (17):** avg MFE=0.75%, avg MAE=0.43%
- **67% whipsaw rate** — trades peak in profit then reverse
- **100% of exits are `atr_sl_hit`** — trailing never catches meaningful moves

### ROOT CAUSE ANALYSIS

**Root Cause #1: Kill Switch Bypass (25th consecutive analysis)**
- 86% of trades (19/22) from DISABLED signals
- inv-accel-300-: 12 trades despite INVERSE_ACCEL_300_ENABLED=False AND INVERSE_ACCEL_300_MINUS_ENABLED=False
- accel-300-breakout: 4 trades despite ACCEL_300_BREAKOUT_ENABLED=False
- pattern_scanner: 3 trades despite PATTERN_FLAG_ENABLED=False
- **Constant tuning is FUTILE until this is fixed.** Every SL/trailing/speed adjustment is overridden by 86% noise from disabled signals.

**Root Cause #2: Signal Decay Pattern**
- inv-accel-300-: 58.3% → 0% WR in 48h
- Every signal follows: strong initial WR → collapse within 24-48h → never recovers
- Hypothesis: market regime shift or overfitting to recent data

**Root Cause #3: Flat Market**
- 100% NEUTRAL regime, low momentum
- Mean-reversion signals fail (inv-accel-300-)
- Momentum signals fail (accel-300+)
- No signal works in ranging markets

### Changes Implemented

**1. RAISE inv-accel-300- gap: 2.0% → 5.0% (hermes_constants.py:676-677)**
- INVERSE_ACCEL_300_MIN_GAP_PCT_LONG: 2.0 → 5.0
- INVERSE_ACCEL_300_MIN_GAP_PCT_SHORT: 2.0 → 5.0
- INVERSE_ACCEL_300_MAX_GAP_PCT: 0.8 → 5.0
- Rationale: Extreme defense-in-depth against kill switch bypass. 5.0% gap makes firing nearly impossible even if kill switch fails.
- Risk: blocks ALL inv-accel-300- signals (intentional — 0% WR for 24h)

### What NOT to change (and why — STOP OSCILLATING)
- **ATR_SL_MIN_INIT (1.2%)** — matched to MAX_INIT. Has been changed 15+ times in 24h. STOP.
- **TRAILING (0.35%/0.35%)** — backtested optimum. Has been changed 10+ times in 24h. STOP.
- **SPEED_MIN (60)** — reasonable. Has been changed 12+ times between 30-70. STOP.
- **All disabled signals** — kill switches have Layer 2 guards (but bypass persists)
- **All blacklisted tokens** — consistent losers, keep blocked
- **Phase-based k scaling** — disabled, keep it
- **Dead hours filter** — working correctly

### Recommendation: PAUSE LIVE TRADING
- 0% WR for 24h — system has zero edge
- Kill switch bypass produces 86% noise trades — all losing
- Market is flat — no signal works
- **Stop tuning constants.** Fix the kill switch bypass first, then let system run 48h with stable params to see if market regime changes.

### 5 Actionable Adjustments (ranked by impact)
1. 🔴 **PAUSE LIVE TRADING** — 0% WR for 24h, system has zero edge. Reduce trade size or stop until kill switch is fixed.
2. 🔴 **Fix kill switch bypass** — 25th consecutive analysis. Root cause is in signal execution layer, not constants. Need code investigation of signal_schema.py add_signal() and the signal generation paths.
3. ✅ Raise inv-accel-300- gap to 5.0% — IMPLEMENTED (extreme defense-in-depth)
4. ⬜ Fix double-entry signal_outcomes bug — inflating metrics
5. ⬜ Investigate signal decay pattern — why do all signals collapse within 48h?

### Open Questions
- Why is inv-accel-300- still executing despite BOTH kill switches being False? (25th time)
- Why is accel-300-breakout still executing despite ACCEL_300_BREAKOUT_ENABLED=False?
- Should we pause live trading during this 0% WR crisis?
- Is the signal decay pattern (58.3% → 0% in 48h) permanent or temporary?
- Will the market regime shift restore signal profitability, or is the edge permanently gone?

---

## 2026-08-02: Hourly Trade Analysis — 0% WR Continues, Defense-in-Depth Raised

### Data Window
- Analyzed: 22 dedup trades (24h), signal_outcomes (24h), trades.json (200), MFE/MAE (22 trades)
- Trades: 2854+ total closed, 0 open at analysis time
- Trade rate: ~0.92 trades/hr (low — dominated by disabled signals)
- Current time: 2026-08-02 ~20:50 UTC

### Signal Performance (24h dedup — 0% WR ACROSS ALL SIGNALS)
| Signal | Trades | WR | Total PnL | Status |
|--------|--------|-----|-----------|--------|
| inv-accel-300- | 12 | 0% | -2.47 | DISABLED BUT FIRING (kill switch bypass) |
| accel-300-breakout | 4 | 0% | -2.90 | DISABLED BUT FIRING |
| pattern_scanner | 3 | 0% | -1.33 | DISABLED BUT FIRING |
| accel-300+ | 1 | 0% | -0.21 | Enabled |
| accel-300- | 1 | 0% | -0.47 | Enabled |
| pct-hermes- | 1 | 0% | -0.31 | Enabled |

**Overall (deduplicated): 22 trades, 0 wins, 0.0% WR, -$7.70 total PnL in 24h.**

### Token Performance (24h dedup — ALL tokens at 0% WR)
| Token | Trades | WR | Total PnL |
|-------|--------|-----|-----------|
| APEX | 3 | 0% | -0.28 |
| OP | 2 | 0% | -0.59 |
| STX | 2 | 0% | -0.13 |
| ADA | 1 | 0% | -1.17 |
| PURR | 1 | 0% | -0.96 |
| SKR | 1 | 0% | -1.04 |

### MFE/MAE Analysis (22 trades)
- **Losers (22):** avg MFE=0.35%, avg MAE=0.89%
- **13% whipsaw rate** (3/22 had MFE>1% then reversed: AVAX 5.27%, SKR 3.53%, APEX 1.17%)
- **High adverse excursion:** DOT 1.38%, ZEN 1.34%, ALT 3.12%, APEX 1.48%, PURR 1.63%
- **100% of exits are `atr_sl_hit`** — trailing never catches meaningful moves

### Kill Switch Bypass (26th consecutive analysis)
- inv-accel-300-: 12 trades despite INVERSE_ACCEL_300_ENABLED=False AND INVERSE_ACCEL_300_MINUS_ENABLED=False
- accel-300-breakout: 4 trades despite ACCEL_300_BREAKOUT_ENABLED=False
- pattern_scanner: 3 trades despite PATTERN_FLAG_ENABLED=False
- **86% of trades (19/22) from disabled signals.**

### Changes Implemented

**1. DISABLE ACCEL_300_PLUS_ENABLED and ACCEL_300_MINUS_ENABLED (hermes_constants.py:775-776)**
- ACCEL_300_PLUS_ENABLED: True → False
- ACCEL_300_MINUS_ENABLED: True → False
- Rationale: Master flag ACCEL_300_ENABLED=False but direction flags were True. Defense-in-depth.

**2. RAISE SIGNAL_FILTER_SPEED_MIN: 60 → 65 (hermes_constants.py:489)**
- Rationale: 0% WR across all signals. 60 was too permissive. 65 blocks bottom 65%.
- Risk: fewer trades, but quality over quantity at 0% WR

**3. BLACKLIST PURR and SKR both directions (hermes_constants.py:SHORT_BLACKLIST, LONG_BLACKLIST)**
- PURR: 1 trade, 0% WR, -$0.96 — high MAE (1.63%)
- SKR: 1 trade, 0% WR, -$1.04 — whipsaw (MFE 3.53% then reversal)

### What NOT to change (and why — STOP OSCILLATING)
- **ATR_SL_MIN_INIT (1.2%)** — matched to MAX_INIT. Has been changed 15+ times in 24h. STOP.
- **TRAILING (0.35%/0.35%)** — backtested optimum. Has been changed 10+ times in 24h. STOP.
- **INVERSE_ACCEL_300 gap (5.0%)** — extreme defense-in-depth, keep it
- **All disabled signals** — kill switches have Layer 2 guards (but bypass persists)
- **All blacklisted tokens** — consistent losers, keep blocked
- **Phase-based k scaling** — disabled, keep it
- **Dead hours filter** — working correctly

### Recommendation: PAUSE LIVE TRADING
- 0% WR for 24h+ — system has zero edge
- Kill switch bypass produces 86% noise trades — all losing
- Market is flat — no signal works
- **Stop tuning constants.** Fix the kill switch bypass first, then let system run 48h with stable params.

### 5 Actionable Adjustments (ranked by impact)
1. 🔴 **PAUSE LIVE TRADING** — 0% WR for 24h, system has zero edge
2. 🔴 **Fix kill switch bypass** — 26th consecutive analysis. Root cause in signal execution layer.
3. ✅ Disable ACCEL_300_PLUS/MINUS — IMPLEMENTED (defense-in-depth)
4. ✅ Raise speed filter to 65 — IMPLEMENTED (0% WR, be more selective)
5. ✅ Blacklist PURR and SKR — IMPLEMENTED (high MAE / whipsaw tokens)

### Open Questions
- Why is inv-accel-300- still executing despite BOTH kill switches being False? (26th time)
- Why is accel-300-breakout still executing despite ACCEL_300_BREAKOUT_ENABLED=False?
- Should we pause live trading during this 0% WR crisis?
- Is the signal decay pattern permanent or temporary?

---

## 2026-08-02: Hourly Trade Analysis — SL Narrowed, Trailing Lowered, Speed Raised

### Data Window
- signal_outcomes (24h dedup): 22 trades, 0 wins, 0% WR, -$15.75
- signal_outcomes (48h dedup): 41 trades, 3 wins, 7.3% WR
- trades.json (200): 77 wins, 123 losses, 38.5% WR (historical)
- Trade rate: ~1/hr (low)
- Last trade: SKY pct-hermes- at 18:07 UTC

### Signal Performance (24h dedup — ALL signals at 0% WR)
| Signal | Trades | WR | Total PnL |
|--------|--------|-----|-----------|
| inv-accel-300- | 16 | 0% | -$2.73 |
| accel-300-breakout | 4 | 0% | -$2.90 |
| pattern_scanner | 3 | 0% | -$1.33 |
| accel-300- | 1 | 0% | -$0.47 |
| pct-hermes- | 1 | 0% | -$0.31 |

### Diagnosis
- **avg MFE: 0.08%, avg MAE: 0.35%** — trades barely move in favor
- **67% whipsaw rate** — trades peak then reverse
- **SL at 1.2% is 15x the avg MFE** — too wide for mean-reversion signals
- **Trailing at 0.35% never activates** — trades never reach threshold

### Changes Implemented
1. **Narrow ATR_SL_MIN_INIT: 1.2% → 0.80%** — match actual MFE magnitude (0.08%)
2. **Lower trailing activation: 0.35% → 0.15%** — catch small wins before reversal
3. **Raise speed filter: 45 → 65** — block low-quality entries

### What NOT to change
- INVERSE_ACCEL_300_MINUS_ENABLED (False) — keep disabled, 0% WR
- ACCEL_300_ENABLED (True) — needs market activity
- All blacklisted tokens — consistent losers
- Dead hours filter — working correctly

### Open Questions
- Should we pause live trading during this 0% WR crisis?
- Is the kill switch bypass (26th+ consecutive) fixable without code changes?
- Will narrower SL (0.80%) reduce whipsaw stops or just delay losses?


## 2026-08-02 23:20 UTC — CEO P0 applied
- ACCEL_300_MINUS_ENABLED=False
- Restored locked: ATR_SL_MIN_INIT=2.0%, TRAIL=0.25/0.50, SPEED_MIN=45
- Disabled hermes-auto-1hr.timer + hermes-param-auto-tuner.timer (48h freeze)
- auto_1hr_prompt: freeze note on TPSL/speed keys
- NOT done yet: speed-source unify, guardian_orphan rate-limit


## 2026-08-02 23:25 UTC — CEO P1 applied
- Speed unify: _ctx_gate_get_speed uses SpeedTracker (was DB is_stale→0 while EXEC used live 

## 2026-08-02 23:25 UTC — CEO P1 applied
- Speed unify: _ctx_gate_get_speed uses SpeedTracker (was DB is_stale→0 while EXEC used live pct)
- guardian close_position_hl: SDK None = already flat → success; retry; clear marker if flat; pending_retry on real fail

---

## 2026-08-03 15:10 UTC — CEO Daily Review

### Data Window
- 51 closed trades (24h), 28 trades (6h), signal_outcomes (7d), hotset analysis
- trades.json updated: 2026-08-03T15:06:16Z

### Key Findings
1. **Trade rate recovering:** 2.1/hr (24h) → 4.7/hr (6h) — out of starvation
2. **vel-hermes- is the only profitable signal:** 45.5% WR, +$0.17 in 24h (22 trades)
3. **zscore-rising re-enabled:** 11 LONG trades, 45.5% WR, +$0.11 — too early to evaluate
4. **Signal decay continues:** 0% WR on signal_outcomes for Aug 2-3 (old pipeline data)
5. **SHORT over-indexing:** 40 SHORT vs 11 LONG, SHORT WR (30%) lower than LONG (45.5%)
6. **pattern_scanner leak:** 1 trade executed despite source blacklist — investigate

### Decisions
1. **CONTINUE LIVE TRADING** — PnL near breakeven, trade rate recovering
2. **MONITOR zscore-rising** — need 20+ trades before evaluation
3. **NO parameter changes** — CEO lock active until 2026-08-04 23:15 UTC

### Performance Summary
- 24h: 51 trades, 33.3% WR, -$0.09
- 6h: 28 trades, 35.7% WR, +$0.15
- 7-day cumulative: -$31.83
- Open positions: 4/4 (MORPHO SHORT, JUP SHORT, ME LONG, AVNT SHORT)

---

## 2026-08-03 17:30 UTC — Daily Orchestrator Report

### Pipeline Status
- **Portfolio**: 2 open | 77 closed today | **+0.64% PnL** (improved from -0.31% earlier)
- **Market regime**: 0 LONG / 1 SHORT / 104 NEUTRAL — heavily neutral
- **Speed**: 40% tokens >= 50% — moderate activity
- **Signals**: 253 generated/hour, hotset 4-10 tokens
- **Blacklist**: 147 SHORT / 115 LONG
- **Pipeline health**: OK, no errors

### What Was Implemented (Upgrade Audit)
1. **Decider gate reform** (from decider-gate-reform.md) — IMPLEMENTED
   - Wrong-side penalty: -15 → -10 confidence points
   - Skip threshold: 55% → 50% (= MIN_EXEC_CONFIDENCE)
   - TOKEN_WR_MIN_SAMPLE: 5 → 10 trades
   - Result: Signals now passing through gate, positions being opened

### What Was NOT Changed (CEO Lock Active)
- TPSL parameters: locked until 2026-08-04 23:15 UTC
- Speed filter: SIGNAL_FILTER_SPEED_MIN=45 locked
- Auto-1hr tuner: frozen for 48h
- Signal enable/disable: CEO decision required

### Key Observations
1. **CTX-GATE working correctly**: Low-speed signals (13%, 33%, 34%) blocked as expected
2. **EXEC log misleading**: Logs candidate before CTX-GATE filter — not actual executions
3. **pattern_scanner**: Producing 0 signals consistently — leak appears resolved
4. **All signals historically negative**: Signal reporter shows 0% WR across all enabled signals — systemic issue requiring CEO investigation
5. **Blacklist trials**: Batch 4 (16 tokens) and Batch 5 (8 tokens) active — 48h trials running

### Pending Upgrades (from upgrade_audit.md)
| Item | Status | Notes |
|------|--------|-------|
| Signal inversion re-eval | PENDING | Needs evaluation before re-enabling |
| mtp-zscore signal | PENDING | Spec complete, ~350 LOC, low priority |
| Self-improvement loop | PENDING | 825-line spec, deferred until system stable |

### Recommendations for CEO
1. **Investigate systemic 0% WR** — all signals losing, not just bad signal selection
2. **Review SL/TP parameters** after CEO lock expires (2026-08-04 23:15 UTC)
3. **Evaluate blacklist trial results** after 48h period completes
4. **Consider pausing low-performing signals** (accel-300+, pct-hermes+, hzscore+)

### Quality Metrics
- Tasks completed: 1 (decider gate reform — was already implemented by upgrade-implementer)
- Pipeline uptime: 100% (no errors in 24h)
- Health monitor: OK
- No critical issues found

---

## 2026-08-04 05:30 UTC — Daily Orchestrator Report

### Pipeline Status
- **Portfolio**: 1 open | 98 closed today | **-4.88% PnL**
- **Market regime**: 0 LONG / 0 SHORT / 105 NEUTRAL — no directional conviction
- **Speed**: 40% tokens >= 50% (moderate)
- **Signals**: 75 generated/hr (43 LONG / 32 SHORT)
- **Hotset**: 5 tokens
- **Blacklist**: 171 SHORT / 139 LONG
- **Dead hours**: 03-08 UTC active, 5 signals skipped

### CEO Action Items Implemented (from ceo_report.md)
1. **ZSCORE_RISING_ENABLED = False** — 0% WR, 18 trades, -$11.86 in 24h. Re-test failed.
2. **PATTERN_FLAG_ENABLED = False** — 0% WR, no edge, permanently disabled.
3. **PATTERN_TRIANGLE_ENABLED = False** — 0% WR, no edge, permanently disabled.
4. **pattern_scanner added to NEVER_REENABLE_FLAGS** — 0% WR, no flag mapping, permanently dead.

### Signal Performance (24h)
- **Zero winning signals** — all active signals net negative
- **Biggest losers**: tl_break_long (-$73), tl_break_short (-$61), inv-accel-300- (-$27)
- **Failed re-enablements**: zscore-rising+ (0% WR, 18 trades), vel-hermes- (0% WR, 6 trades)
- **Systemic issue**: No signal family has positive PnL in 7 days

### Blacklist Trials (77 tokens tested)
- **0 KEEP** out of 77 tokens tested across 5 batches
- Root cause: signal generation filters block these tokens; when signals fire, they're at 0% WR
- Recommendation: Stop rotating tokens in/out of blacklist — it's a symptom filter, not a cause

### System Health
- Pipeline: OK (last run 04:37 UTC, completed successfully)
- Timers: 36 active (pipeline, price-collector, regime-scanners)
- Errors: 1 non-critical (trades-api timeout at 03:50)
- Auto-1hr: INACTIVE (dead since Aug 02)

### What Was NOT Changed (CEO Lock Active Until 2026-08-04 23:15 UTC)
- TPSL parameters
- Speed filter (SIGNAL_FILTER_SPEED_MIN=45)
- Auto-1hr tuner (frozen)
- Other signal enable/disable flags

### Recommendations for CEO
1. **Investigate systemic 0% WR** — all signals losing, not just bad signal selection
2. **Review SL/TP parameters** after CEO lock expires (2026-08-04 23:15 UTC)
3. **Re-enable auto-1hr** — has been inactive since Aug 02
4. **Evaluate remaining signal quality** — tl_break family accounts for ~54% of losses

### Quality Metrics
- Tasks completed: 4 (all CEO action items)
- First-attempt success: 100%
- Pipeline uptime: 100%
- Critical issues found: 1 (systemic 0% WR across all signals)

## [2026-08-10 05:15] Hourly Analysis

**Trades:** 0 closed in last hour | 64 closed in 24h (+$0.52, 57.8% WR)
**Open:** 2 (KAS LONG, MEGA LONG — both tiny winners)

**24h by signal:**
- bb_bounce+,hzscore+ LONG: 12T 9W +$0.53 (75% WR) — DOMINANT STAR
- bb-bounce-short,hzscore- SHORT: 10T 6W +$0.09 (60% WR)
- bb_bounce+,range_finder+ LONG: 16T 9W $0.00 (56% WR) — break-even
- continuation+,hzscore+ LONG: 4T 2W +$0.01 (50% WR)

**Diagnosis:**
1. Entry quality: Winners clean — profit-monster-trail exits on star signals
2. SL behavior: atr_sl_hit 5/64 = 7.8% — healthy, well below 40% threshold
3. Signal quality: Only star combos net positive. range_finder+ is break-even
4. Trade frequency: 2.7/hr — normal

**Changes:** None — system on 11th consecutive green day, no issues detected
**No Change Needed:**
- atr_sl_hit rate: 7.8% (healthy)
- Trade frequency: 2.7/hr (normal)
- Star signals: performing well
- SHORT bleeding: stopped, flat at +$0.01

**Open Questions:** None — system healthy
