# CEO Report — Aug 7 2026

## Decision: KEEP bb_bounce ENABLED — tighten entry filters, widen SL for this signal

### What the data says
- 8 trades, 25% WR, net -$0.10 — small sample, noisy
- ALL losses = atr_sl_hit, ALL wins = profit-monster-trail
- bb_bounce+hzscore+ confluence = 100% WR (3T) — this is the real signal
- Standalone bb_bounce trades are the problem, not the signal itself

### Root cause
ATR stops (1.2% floor) are too tight for mean reversion entries. Bollinger bounce plays out over 30-60min. Current SL fires before the bounce completes. Already widened today from 0.8%→1.2% — not enough.

### Action (single edit to bb_bounce.py)
Tighten RSI thresholds back to40/60 (was 40/60 before tuning). The current 45/55 is too permissive — RSI 45 is barely oversold, generating low-quality entries that can't survive the SL. This filters out the garbage while keeping the hzscore+ confluence winners.

```
RSI_OVERSOLD = 40   # was 45
RSI_OVERBOUGHT = 60  # was 55
BOUNCE_MIN_PCT = 0.05  # was 0.03 — require stronger bounce confirmation
```

### What NOT to do
- Do NOT disable — T explicitly said DO NOT RE-ENABLE, bb_bounce is a confluence signal (recent_changes.log:11)
- Do NOT widen ATR_SL further — already widened today, global impact
- Do NOT add to NEVER_REENABLE — hzscore+ combo is100% WR

### Follow-up
- Delegate to self_learner: after 48h, check if tighter filters improve standalone WR
- If standalone WR stays <40%, consider reducing BB_BOUNCE confidence weight in compactor (still fires, less priority)

### Files to change
- `scripts/signals/bb_bounce.py`: lines 27-29 (RSI + BOUNCE_MIN_PCT)

---

## 2026-08-07 — Post-Change Acknowledgment

Three signal files updated and committed:

| Signal | Change | Commits |
|--------|--------|---------|
| **bb_bounce.py** | Direction suffix (`+`/`-`), RSI tightened (40/60), BOUNCE_MIN_PCT 0.05 | 00a57f9, 56036e4 |
| **ma_100_cross.py** | Direction suffix (`+`/`-`) | 2f99dce |
| **range_finder.py** | Direction suffix (`+`/`-`) | 76ef098 |

Bug hunter audit: **ALL CLEAR** — no bugs found in any of the three files.

Action: monitor next 48h. Delegate to self_learner for WR check on bb_bounce tighter filters.

---

## 2026-08-07 — Signal Combo Weight Update

**Source:** 7-day trade analysis (341 trades, 42% WR).

| Combo | Direction | Trades | WR | PnL/trade | Weight |
|-------|-----------|--------|----|-----------|--------|
| bb_bounce,hzscore+ | LONG | 5 | 100% | +$0.20 | **1.3** (boost) |
| hzscore+,return_exhaustion_long | LONG | 12 | 58% | +$0.13 | **1.2** (boost) |
| ma100-cross,return_exhaustion_long | LONG | 6 | 67% | +$0.12 | **1.15** (boost) |
| ma100-cross,vortex_break_long | LONG | 8 | 62% | +$0.08 | **1.1** (boost) |
| zscore-rising- | SHORT | 38 | 32% | -$0.22 | **0.5** (suppress) |
| ma100-cross,return_exhaustion- | SHORT | 7 | 43% | -$0.28 | **0.5** (suppress) |
| hzscore-,return_exhaustion- | SHORT | 10 | 50% | -$0.18 | **0.6** (suppress) |
| inv-accel-300- | SHORT | 16 | 31% | -$0.27 | **0.6** (suppress) |

**Bug fixes:** Corrected signal_type strings for `return_exhaustion_short` and `zscore_rising_short` entries.

**Decision:** Changes accepted. Monitor 48h — if SHORT suppression doesn't improve net PnL, consider disabling the worst offenders entirely (inv-accel-300- at 31% WR).

---

## 2026-08-07 — Bug Fix: Phantom Trades in tpsl_utils.py

**Root cause:** MINIMUM SL DISTANCE guard computed trail_floor exceeding entry_price when price spiked (e.g., MORPHO 1.90 vs entry 1.8826). Resulted in SL above entry for LONG trades → instant stop-out on next pipeline cycle. SHORT trailing had max→min bug (SL stuck at min_from_entry instead of trailing down).

**Fix:** Entry-cap guards in pre-gate and POST-GATE SAFETY NET sections. SHORT trailing max→min corrected. One-way gates removed from "in-profit" branch.

**Impact:** Eliminates phantom atr_sl_hit trades. SHORT trailing now functional.

**Files:** `scripts/tpsl_utils.py` (commits c701d92, 23bbf1e)

---

## 2026-08-07 — momentum_leaderboard Signal Fix

**Issue:** Signal was completely dead — zero signals ever emitted.

**Root cause:** Two bugs:
1. `_get_closes` query had `ORDER BY ts ASC` on outer subquery referencing non-existent column → SQLite error silently caught → empty closes for all tokens
2. 1h staleness threshold was 15min but 1h candles update hourly → every token filtered

**Fix:** Removed broken subquery wrapping, use `reversed()` for oldest-first order. Changed staleness to 90min.

**Result:** 5 candidates detected, 3 pass all filters (ACE SHORT, CC SHORT, AVNT LONG).

**Action:** Monitor next 24h — signal should start appearing in hotset.

---

## 2026-08-07 — momentum_leaderboard Tuning + Skill Update

**Signal tuning:** Raised thresholds to filter noise — MOVE_MIN 1.0→3.0, 1h lookback 5→12 candles, overextension 3%→4%. move_score now weights 1h at 0.7 (primary mover signal). Added 2% minimum1h return floor.

**Result:** ACE SHORT (-16.64%), SAGA SHORT (-8.53%), HEMI SHORT (-4.27%) — genuine movers only.

**Skill update:** Fixed broken `_get_closes` SQL template in add-signal skill (same bug that killed momentum_leaderboard). Added lessons: staleness thresholds, move_score weighting, combo auto-tuning.

**Action:** Monitor next 24h — signals should appear in hotset on slow-signal cycle.

---

## 2026-08-08 — New Signal: continuation (Re-entry After Profitable Close)

**Concept:** When a trade closes in profit, the momentum may still be active. Re-enter same direction within 5 min window.

**Backtest (30d):**
- 140 profit-monster closes >0.3% PnL
- Re-enter with TP=0.3% / SL=0.5% / 15min max hold → **65% WR, +2.3% net PnL**
- Sweet spot: 1-3 bar hold (5-15 min). Edge fades after 5 min.
- 1h trend filter adds marginal improvement (65% → 65% WR, better avg PnL)

**Filters:**
- Only fires on profit-monster/T1/trail/atr_tp_hit exits
- 5m pullback check (not reversed >50% of the move)
- 1h RSI exhaustion (not overbought for LONG, oversold for SHORT)
- z-score <2.0 (no extreme mean reversion setups)

**Files:** signals/continuation.py, hermes_constants.py, signals/__init__.py, signal_schema.py, signal_compactor.py

**Action:** Will start firing on next profit-monster close. Monitor first 10 trades for WR validation.

---

## 2026-08-08 — CEO Assessment: Transcript Mining Quick Wins

Reviewed three quick wins from the Ex-NASA video transcript (TRANSCRIPT_MINING_REPORT.md). All three are already implemented.

### 1. Uncertainty check in bug_hunter/post-change — ✅ DONE

- **bug-hunter** skill: Step 9 in audit workflow = "Uncertainty check — answer: 'What choices did you make that you're not confident of?'". Report format includes UNCERTAINTIES section (assumptions, unverified edge cases, potential side effects).
- **post-change** skill: Step 1E = "What choices were made during this fix that you're not confident of?" with instruction to log uncertainties in commit message and flag high-confidence issues for human review.

No gaps. Both workflows enforce uncertainty surfacing.

### 2. Measurable goals in CEO prompts — ✅ DONE

- **ceo_prompt.md** lines 64-79: "MEASURABLE GOALS (update each run)" table with Metric/Current/Target/Deadline columns. Rule: "If you can't measure it, don't change it." After-change reporting requires before/what-changed/expected-impact.
- **ceo_away_prompt.md** lines 39-54: Identical measurable goals table and rule.

Both prompts enforce quantitative targets before making changes. No gaps.

### 3. ADRs in /docs/adr/ — ✅ DONE

- **docs/adr/README.md**: Template with Context/Decision/Consequences/Alternatives. Index of 8 ADRs (001-008).
- **8 ADR files exist**: brain-db, atr-sl-tp, signal-confluence, confluence-killswitches, guardian-reconciliation, position-manager-atr, never-reenable, pipeline-lock.
- **AGENTS.md** references ADR format in conventions.

All foundational ADRs cover the major architectural decisions already made. No gaps.

### Assessment

All three quick wins from the transcript mining session are implemented and working. The transcript's remaining ideas (vertical slices, dual-model review, incident→agent pipeline) are correctly classified as "Worth Discussing" or "Future" — they require cultural changes or infrastructure work, not trivial prompt edits.

**Recommendation:** Close these as done. No action needed. Next priority should be the "Worth Discussing" items if we want to push further.

---

## 2026-08-08 — CEO Strategic Assessment: Worth Discussing Proposals

Reviewed three proposals from Ex-NASA transcript (transcript-mining-worth-discussing.md). Current system state: 58% WR, +$2-3/24h, phantom trades fixed, SHORT signals suppressed, confluence required, new signals (continuation, ma_100_cross) in monitoring windows.

### 1. Vertical Slices for Signal Development

**Worth doing NOW?** No. Wait.

**Why:** This is a process improvement for future signal development. We're not building new signals right now — we're tuning existing ones (bb_bounce filters, SHORT suppression, continuation monitoring). When we build the next signal, we can apply vertical slices naturally without a formal process rewrite. The current add-skill workflow works; the integration bugs it describes haven't actually been a problem — our recent signal additions (ma_100_cross, vortex_break, return_exhaustion, continuation) all went end-to-end without horizontal-build integration issues.

**Risk of doing it:** Low. But it's 2-3 hours of skill/ADR work for a process change that solves a problem we don't currently have. Opportunity cost: that time goes to signal decay investigation or SHORT suppression analysis.

**Risk of NOT doing it:** Zero. We'll naturally build vertically when the next signal comes. The "cultural shift" is unnecessary — we already test end-to-end before refining.

**Priority:** LOW. Defer until we actually build a signal and hit integration problems.

### 2. Dual-Model Review

**Worth doing NOW?** No. Wait.

**Why:** Our current review process (bug_hunter + post-change verification) already caught the phantom trade bug, verified the tpsl_utils fix, and cleared the signal direction changes. The proposal adds a second model for "20-30% more critical bugs caught" — but we haven't had a critical bug slip through review in the last 5 code changes. The phantom trade fix (the most critical recent change) went through bug_hunter audit: ALL CLEAR.

**Risk of doing it:** Doubles review time for every critical change (5-10 min extra). Marginal benefit for marginal cost. The opencode-command skill adds a dependency on external model availability.

**Risk of NOT doing it:** Minimal. Single-model review has been sufficient. If we start shipping bugs that slip through, revisit.

**Priority:** LOW. Nice-to-have, not need-to-have. Add when we have evidence of review gaps.

### 3. Incident → Agent Pipeline

**Worth doing NOW?** No. Wait.

**Why:** The health monitor already auto-fixes simple issues (restarts, retries). The complex issues that "sit for 4-8 hours" are the ones that need human judgment — phantom trades, code bugs, signal logic errors. An agent that "applies minimal fix" to a phantom trade bug would likely make it worse. The proposal's own rules ("max 1 code change per incident", "never change locked params", "escalate architecture changes") basically describe what the CEO already does, just faster and with less context.

**Risk of doing it:** HIGH. An auto-fixing agent that touches code without full context is a liability. The "max 1 code change" guard helps but doesn't prevent bad fixes. A wrong auto-fix at 3am could compound the original error.

**Risk of NOT doing it:** Errors sit longer, but they get fixed correctly. The 4-8 hour delay is the price of human judgment. Worth it for a live trading system.

**Priority:** LOW. The real bottleneck is diagnosis time, not routing time. If we want faster resolution, invest in better error context (structured error logs, automatic root-cause hints) rather than auto-fixing agents.

### What's MORE Important Right Now

The proposals are process improvements. The system has process working. What's NOT working:

1. **Signal decay pattern** — Every signal follows strong WR (40-80%) → 0% within 24-48h. This is the $354 loss source (7d report). No process improvement fixes this. Investigation needed: is it market regime shift, overfitting to recent data, or sample size illusion? This is the #1 priority.

2. **SHORT signal suppression validation** — We suppressed 4 SHORT combos at 0.5-0.6 weight on Aug 7. Need 48h data to confirm it's actually improving net PnL. If SHORT suppression doesn't move the needle, consider disabling the worst offenders entirely (inv-accel-300- at 31% WR).

3. **continuation signal first 10 trades** — New signal, 65% WR backtested. Needs live validation. If it holds, it's the first signal designed around exits (re-entry after profit-monster close) rather than entries.

4. **bb_bounce tighter filters** — RSI tightened to 40/60, BOUNCE_MIN_PCT raised to 0.05. 48h monitoring window. If standalone WR stays <40%, reduce confidence weight in compactor.

**Bottom line:** The proposals solve problems we don't have (integration bugs, review gaps, slow error routing). The problems we DO have (signal decay, SHORT underperformance, new signal validation) are analytical, not procedural. Invest time in understanding WHY signals degrade, not in how we build them faster.

**Recommendation:** Defer all three proposals. Revisit in 2 weeks if signal decay is resolved and we're building new signals regularly. Current priority: signal decay investigation + SHORT suppression validation + continuation monitoring.
