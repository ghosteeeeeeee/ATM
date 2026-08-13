## CEO Report — 2026-08-13 (Spec Review: Progressive Context Shaping)

### Verdict: NOT APPROVED — Over-engineering, revisit if drift is validated

**The spec solves a problem we don't have.** Hermes already has 6 overlapping context/state files: AGENTS.md (stable rules), orchestrator_prompt.md (execution context), ceo_prompt.md (strategy), OpenMemory (cross-session memory), ceo_kanban.md (decision history), ceo_report.md (session summaries). Adding a 7th file (CURRENT.md) is complexity, not simplicity.

### What's wrong

1. **No validated problem.** The spec claims "agents drift on stale context" but provides no evidence. The orchestrator already has 218 lines of structured phases. The CEO prompt already reads kanban at session start. Where's the actual drift?

2. **OpenMemory already does this.** The `openmemory_openmemory_store/query` system is literally "cross-session context for agents." CURRENT.md is a markdown reimplementation of what OpenMemory already provides, but worse (no search, no salience, manual maintenance).

3. **CURRENT.md is unfocused.** It mixes 6 concerns: active goal, decisions, limitations, backlog, guardrails, stop conditions. That's not "short, live, readable in <30s" — it's a mini-AGENTS.md.

4. **YouTube transcript ≠ system requirements.** This was mined from "Three OpenAI Engineers Shipped A Million Lines." That's a different scale, different architecture, different problem. Applying their solution without validating we have their problem is cargo-cult engineering.

5. **Maintenance burden.** Who updates CURRENT.md? If agents do, it becomes stale like the orchestrator prompt it's supposed to fix. If humans do, it's one more file to maintain. The spec doesn't answer this.

### What's right

- The4-layer mental model (stable/current/map/history) is useful as a diagnostic lens, not as an implementation plan.
- Recording signal deprecation *reasons* (not just state) is genuinely good. That should be a standalone improvement to `signal_lifecycle.py`, not bundled into this spec.
- The context map idea (where signals live, how to test) is useful as a one-time documentation effort, not a living file.

### What to do instead

1. **Don't create CURRENT.md.** Use OpenMemory for cross-session state. Use kanban for decisions. Use ceo_report.md for session summaries. These already work.
2. **Extract the good parts as standalone changes:**
   - Add deprecation reasons to `signal_lifecycle.py` (small, useful)
   - Add a signal context map as a one-time doc (not a living file)
3. **If drift is actually observed** (agents repeating work, missing context), then and only then revisit. But measure first — grep CEO reports for "repeated" decisions or "missed" context.
4. **Don't modify orchestrator_prompt.md or ceo_prompt.md** for this. Those files are already long enough. Adding CURRENT.md references adds complexity without fixing root causes.

### CURRENT.md focus issues

The current CURRENT.md is 56 lines — already over the 50-line "graveyard" stop condition it sets for itself. The "System Improvement Backlog" section (lines 23-38) is a duplicate of what should be in a separate planning file, not in the "current state" document. The "What NOT To Do" section (lines 39-45) duplicates AGENTS.md behavioral directives. This file is trying to be everything, which means it's nothing.

---

## CEO Report — 2026-08-13 (Latest)

### Diagnosis
24h: 105T, -$0.44 PnL, 52.4% WR — RED day. Aug 13 only 17T at35.3% WR (tiny sample). 7d: 460T +$0.3853.0% WR — barely positive, holding.

### Root Cause
Cold streak, not systemic. Aug 12 recovered to +$0.4957% WR, Aug 13 is just 17 trades with bad distribution. accel-300- SHORT remains marginal: 35T -$0.1757.1% WR but R:R unfavorable (avg_win $0.05 vs avg_loss $0.08). atr_sl_hit 65T -$4.07 dominates cost — trailing stop compensating but not enough.

### Fix Applied
NO CHANGES. Stability period active. System flat, stars intact, no clear bleeding point to fix.

### Verification
Stars7d intact: bb_bounce+,range_finder+ +$0.71, range_breakout_short +$0.43, hzscore+,mover+ +$0.17, bb_bounce+,hzscore+ +$0.22, bb-bounce-short,hzscore- +$0.14. All previously disabled/blacklisted signals confirmed. Pipeline healthy, 6 open -$0.16 flat.

### Monitor
- accel-300- SHORT: disable ACCEL_300_MINUS_ENABLED if PnL drops below -$0.30
- SHORT7d: add regime filter if total drops below -$1.50
- Daily: investigate if 2 consecutive red days after today

---

## CEO Report — 2026-08-15 (Z-Score + Acceleration Filter — Deployed)

**DEPLOYED.** Z-Score + Acceleration alignment filter now live in `decider_run.py:762-772`. Hard block: LONG z>0.5+accel>0.005, SHORT z<-0.5+accel<-0.005. Bug hunter: ALL CLEAR. No trading changes.

Goal: +2-4% WR by blocking ~23.8% WR misaligned trades. Monitor 48h for false positive rate. If >10% of valid signals blocked, tighten thresholds.

---

## CEO Report — 2026-08-15 (Z-Score + Acceleration Filter — Pipeline Placement)

### Verdict: Separate gate in `rule_based_context_gate()`. NOT part of volatility_gate.py.

**Why separate?** volatility_gate answers "which signals work in which ATR regime?" (FLAT/NORMAL/HIGH/EXTREME → signal mapping). Z-Score+Acceleration answers "is the direction aligned with momentum?" (z>0 + accel>0 → SHORT aligned, LONG misaligned). Different questions, different data, different pipeline positions. Merging conflates two orthogonal concerns.

**Where?** New rule in `rule_based_context_gate()` in `decider_run.py` — the execution-path gate that already checks z-score, speed, momentum, acceleration. Position: after speed check (#1) and before FLIP territory (#3). ~15 lines.

**Why not signal_compactor scoring?** signal_compactor `_score_signal()` applies soft multipliers (regime_mult 1.5x/0.5x). Z-Score+Acceleration is a hard directional alignment check — misaligned trades have 23.8% WR. Soft penalty doesn't cut it. Hard block in context gate = right layer.

**Interaction concerns:**
- Overlap with existing `SIGNAL_FILTER` (speed/momentum/RSI/z checks in context gate): Z-Score+Acceleration is distinct — checks directional alignment of z AND accel together, not individual thresholds. No double-penalization.
- Overlap with `regime_mult` in signal_compactor: regime_mult is regime-level (LONG_BIAS/SHORT_BIAS), Z-Score+Acceleration is token-level z+accel alignment. Different granularity.
- Interaction with context gate FLIP: FLIP already handles z>1.0 LONG / z<-1.0 SHORT. Z-Score+Acceleration catches the more specific case where z+accel direction conflicts with trade direction.

### Implementation spec

New rule after speed check in `rule_based_context_gate()`:

```python
# Z-Score + Acceleration Alignment
# surfing.md backtest: aligned (z>0 + accel>0 for SHORT) = 76.4% WR
#                       misaligned (z>0 + accel>0 for LONG) = 23.8% WR
# This catches trades where price is extended AND accelerating AGAINST us.
if z_score is not None and accel is not None:
    # LONG + z positive + accel positive = price above mean and rising = chasing
    if direction == 'LONG' and z_score > 0.5 and accel > 0.005:
        return ('SKIP', f'misaligned LONG: z={z_score:.2f} accel={accel:+.4f} (price extended, accelerating away)')
    # SHORT + z negative + accel negative = price below mean and falling = chasing
    if direction == 'SHORT' and z_score < -0.5 and accel < -0.005:
        return ('SKIP', f'misaligned SHORT: z={z_score:.2f} accel={accel:+.4f} (price extended, accelerating away)')
```

**Thresholds:** z>0.5 / z<-0.5 (conservative — not extreme), accel>0.005 / accel<-0.005 (meaningful acceleration, not noise).

### Risk assessment
- **Low risk.** Pure additive gate — can't break existing logic. Fail-open (only blocks, never forces).
- **Expected impact:** Eliminates ~5-10% of trades (the misaligned ones with 23.8% WR). Net WR improvement: +2-4%.
- **Revert: remove the rule or set CONTEXT_GATE_ENABLED=False.**

### Measurable Goal
| Metric | Current | Target | Deadline |
|--------|---------|--------|----------|
| Misaligned trade WR | ~24% | 0 (blocked) | Immediate |
| Overall WR | 52.8% | 55%+ | 72h |

### Verification
After deployment, query DB for blocked trades:
```sql
SELECT COUNT(*) FROM trades WHERE status='closed' AND close_time > NOW() - INTERVAL '48 hours'
  AND signal_metadata LIKE '%misaligned%';
```
If misaligned trades still appearing → threshold too loose, tighten z to 0.3 / accel to 0.003.

### Recommendation
**APPROVE.** Implement as new rule in `rule_based_context_gate()`. No volatility_gate changes needed. Ship it.

---

## CEO Report — 2026-08-13 (Weather Vane v3 — Predictive Methods)

### DB-Verified Numbers
24h: 107T -$0.52, 52.3% WR (flat). 7d: ~464T +$0.37, 53.0% WR (barely positive). Stars7d intact.

### Method 1: Consecutive Loss Counter — **APPROVED, HIGHEST PRIORITY**
DB backtest (14d) validates this HARD:
- After 3+ consecutive losses: 444 trades, **37.8% WR**, **-$2.44 total PnL**
- Normal trades: 402 trades, **51.5% WR**, **+$1.60 total PnL**
- **14-point WR gap. $4.04 PnL spread.** This is the strongest predictive signal in the dataset.
- Real bleeders: BSV SHORT (7/10 losses), AXS LONG (6/9), AAVE SHORT (5/8)

**Implementation:** New `get_consecutive_losses(token, direction)` function querying `signal_outcomes` per token+direction. Apply as multiplier in `_score_signal()`. Hard block at 5+ consecutive, soft penalty at 3-4.

**Risk:** Low. All data already in signal_outcomes table. ~30 lines of code. Integrates into existing `_score_signal()` flow alongside existing directional outcome tracker.

**Circuit breaker:** If >30% of signals penalized in 24h → auto-disable (prevents over-suppression during choppy markets).

### Method 5: Entry Price vs Range — **APPROVED, SECOND PRIORITY**
Catches chasing: LONG at 90th percentile = buying the top, SHORT at 10th = selling the bottom.

**Data issue:** `candles_1h` is in SQLite (RUNTIME_DB), not PostgreSQL. Query needs to use `sqlite3.connect(RUNTIME_DB)` not PostgreSQL.

**Implementation:** New `check_price_extreme(token, direction, price)` function querying SQLite candles. ~25 lines. Apply as 0.75x penalty at extremes.

### Method 2: Volume Spikes — **DEFERRED**
Sound concept but needs candle volume data from SQLite. More complex to integrate correctly. Can add after Methods 1+5 proven.

### Method 4: Time-of-Day — **REJECTED**
Insufficient sample sizes per hour. Current trade volume (~15/hr) means <10 trades per hour bucket. Noise dominates signal. Revisit when volume 3x+.

### Implementation Order
1. Method 1 (consecutive losses) — implement NOW, deploy after 14d backtest
2. Method 5 (price extremes) — implement NEXT, deploy with Method 1
3. Method 2 (volume spikes) — LATER, after Methods 1+5 validated
4. Method 4 (time-of-day) — NOT NOW

### Target
Combined effect of Methods 1+5: reduce LONG bleed by $0.50-1.00/week (from ~$0.50 to break-even). Expected WR improvement: +2-3% on penalized trades.

---

## CEO Report — 2026-08-13 (CEO Run)

### Diagnosis
24h: 105T -$0.36, 53.3% WR (flat). 7d: 464T +$0.33, 53.0% WR (barely positive). Aug 13: 15T -$0.57, 40% WR — cold but only 15 trades (too early to act). Stars7d intact: bb_bounce+,range_finder+ $0.71, range_breakout_short $0.49, hzscore+,mover+ $0.17, bb_bounce+,hzscore+ $0.22, bb-bounce-short,hzscore- $0.14.

### Root Cause
No single bleed source. accel-300- SHORT is the only active bleeder (35T -$0.17, 57.1% WR — WR fine, losses slightly larger than wins). All previously identified bleeders (range_breakout+, trend_momentum, hzscore+ standalone, return_exhaustion- combos) already disabled/blacklisted. atr_sl_hit dominates cost at -$3.91 (48h). Today's cold reading is low volume, not a new problem.

### Fix Applied
NO CHANGES — stability period. System flat, no clear actionable bleed.

### Monitor
- Daily PnL: if -2 consecutive red days → investigate
- accel-300- SHORT: if持续 bleeding past -$0.50 → disable ACCEL_300_MINUS_ENABLED
- 6 open trades at -$0.19 — normal

---

## CEO Report — 2026-08-13 (Weather Vane v3 Evaluation)

### Verdict: MODIFY — Concept approved, implementation has a critical flaw

**The insight is sound.** Signal volume IS a leading indicator. When the market turns bullish, SHORT signal generators fire less often and with lower confidence — this happens BEFORE losses accumulate. The 3-layer architecture (volume → confidence → loss cluster) is the right order of operations.

**But the baseline calculation will cause constant false positives.**

### Evidence

SHORT signal volume from the last 48h:
- Range: 16/hour (02:00) to 386/hour (19:00) — **24x natural swing**
- 24h average: ~126/hour
- Normal low-activity hour: 16-50 signals (60-87% below average)

The spec uses a 24h rolling baseline. Comparing a 2-hour window to this average during any quiet period (3-6 AM, post-session lulls) will trivially exceed the 50% threshold. Example: 02:00 has 16 SHORT signals vs 126 baseline = **87% drop → CONSTANT TRIGGER**.

This is noise, not signal.

### Required Changes

| Item | Spec Says | Should Be | Why |
|------|-----------|-----------|-----|
| Baseline | 24h rolling avg | Same-hour yesterday (or 7-day same-hour avg) | Eliminates time-of-day false positives |
| Threshold | 50% drop | 65% drop | After time-of-day fix, 65% filters real regime shifts from normal variance |
| Min baseline | 10 signals/hr | 20 signals/hr | 10 is too low — single token batch can spike 15 signals in one hour |
| Cache | 5min TTL | 15min TTL | Hourly aggregation doesn't need 5min refresh; saves DB reads |

### What's Good (keep as-is)

- **Confidence trend layer** — delta of -4.3 observed (close to -5.0 threshold, would fire appropriately, not constantly)
- **Minimum penalty wins** — correct. Predictive 0.8x fires before reactive 0.7x. If both fire, stronger penalty applies.
- **Milder predictive penalties** — 0.8x vs 0.7x reactive. Correct graduation.
- **Existing v2 fallback intact** — Layer 3 unchanged, safety net preserved.

### Risk If Unchanged

False positives during quiet hours would apply 0.8x penalty to SHORT signals at 2-5 AM. This is low-stakes (few trades execute at those hours) but it's a correctness issue that undermines trust in the system. Fix it before deploying.

### Decision

**APPROVE with modifications.** Implementer should:
1. Change baseline to same-hour-yesterday (query: signals WHERE direction=X AND created_at BETWEEN yesterday_hour_start AND yesterday_hour_end)
2. Raise threshold to 0.65
3. Raise min baseline to 20
4. Backtest 7d before deploying live
5. Add a 30-minute cooldown after trigger fires (prevents thrashing on hour boundaries)

No rush — system is in stability period. Target: implement + backtest by end of day, deploy tomorrow if backtest confirms.

---

## CEO Report — 2026-08-13 (Previous)

### Diagnosis
System flat — 24h 104T -$0.10 (53.8% WR), 7d 463T +$0.37 (52.8% WR). Recovery confirmed: Aug 9 +$0.62 peak → Aug 11 -$0.33 (worst) → Aug 12 +$0.49. Today Aug 13 cold streak: 11T -$0.52 (36.4% WR) — too early to act, only 11 trades.

### Stars7d (all intact)
- bb_bounce+,range_finder+ LONG: 53T +$0.71 58.5%
- range_breakout_short: 14T +$0.49 71.4%
- hzscore+,mover+ LONG: 5T +$0.17 80%
- bb-bounce-short,hzscore- SHORT: 18T +$0.14 61.1%
- bb_bounce+,hzscore+ LONG: 34T +$0.22 50%

### 24h Bleeders (no action needed)
- range_breakout+ LONG: 8T -$0.41 25% WR — DISABLED
- hzscore+ standalone LONG: 4T -$0.14 25% WR — BLACKLISTED
- accel-300- SHORT: 31T -$0.12 58.1% WR — marginal, not kill threshold

### Cost Drivers48h
- atr_sl_hit: 63T -$3.87 (dominant, trail compensating ~$2.64)
- cut-loser-CL-T1: 4T -$0.42

### Fix Applied
No changes. Stability period active, system flat, no clear bleed source to fix.

### Verification
Pipeline healthy (all timers active). 6 open trades flat. Weather Vane v2 deployed (hysteresis + off-course alarm). Previous fixes confirmed working.

### Monitor
- Daily PnL: if -2 consecutive red days → investigate
- accel-300- SHORT: if持续 bleeding → disable ACCEL_300_MINUS_ENABLED
- SHORT7d: currently -$0.50 — below -$1.50 regime filter threshold

### Weather Vane v2 — Complete
Bug fix: velocity_mult defaulted to 1.0 (no-op) when velocity tiers disabled → fixed to DIRECTIONAL_OUTCOME_PENALTY (0.7x). Proposals 3-4 (velocity tiers, integral) already live. Proposals 5-6 (gain scheduling, watchdog) YAGNI. All layers active: hysteresis, off-course alarm, velocity tiers, integral. No trading changes.

---

## CEO Report — 2026-08-15 (Latest Run)

### Diagnosis
Verified DB: 24h 103T -$0.08 (54.4% WR — flat), 7d 460T +$0.38 (53.0% WR — barely positive). Stars intact: bb_bounce+,range_finder+ 53T +$0.71 58.5%, range_breakout_short 14T +$0.49 71.4%, bb_bounce+,hzscore+ 34T +$0.22 50%, hzscore+,mover+ 5T +$0.17 80%, bb-bounce-short,hzscore- 18T +$0.14 61.1%.

### Root Cause
No active bleeding source. All prior bleeders disabled/blacklisted (range_breakout+, trend_momentum, hzscore+ standalone, return_exhaustion-). accel-300- SHORT 31T -$0.12 (58.1% WR — marginal, losses > wins but WR acceptable). Cost driver: atr_sl_hit 63T -$3.87 (dominant).

### Fix Applied
NO CHANGES — system flat, no actionable problem, stability period active.

### Verification
Aug 12 recovery confirmed (+$0.49, 57.0% WR). Aug 13 11T -$0.52 (36.4% WR — cold streak, only 11 trades, too early to act). 6 open $0 flat. Pipeline healthy.

### Monitor
- Daily PnL: if -2 consecutive red days → investigate
- accel-300- SHORT: if持续 bleeding → disable ACCEL_300_MINUS_ENABLED
- SHORT7d: currently improving, below -$1.50 threshold

---

## CEO Report — 2026-08-13 (Weather Vane v3 Evaluation)

### Verdict: APPROVE WITH MODIFICATIONS

**Core insight is sound.** Structure shifts (HH_HL↔LH_LL) indicate uncertainty, and uncertainty kills trades. The data is direction-symmetric: shifts hurt LONG AND SHORT. This is a volatility filter, not a directional call.

### Concerns

1. **Sample sizes too small.** 20 SHORT shifted trades and 37 LONG shifted trades are not statistically significant. Need 14-day backtest with 100+ shifted trades per direction before deploying live.

2. **"N → HH_HL" is not a shift — it's emergence.** The spec conflates emerging structure (N → HH_HL) with actual shifts (HH_HL → LH_LL). These are different things. The backtest shows emerging bullish (N → HH_HL) hurts LONG (37% WR, -$0.62) — but that's because LONG entries during emerging bullish are chasing, not because structure is uncertain. Separate these cases.

3. **Suppression is too blunt.** 57/391 trades (15%) suppressed for ~$1.33/week net benefit (saves $19 losses, loses $17.67 wins). Use soft penalty (0.7x-0.8x) instead of hard suppression — preserves high-confidence trades while penalizing uncertainty.

### Required Changes

| Item | Spec Says | Should Be | Why |
|------|-----------|-----------|-----|
| Filter type | Hard suppression (continue) | Soft penalty (0.75x mult) | Preserves high-confidence trades during shifts |
| Emerging structure | Treated same as shift | Separate category — no penalty | N→HH_HL is not HH_HL→LH_LL |
| Backtest | 7 days | 14 days, 100+ shifted trades each | 20/37 trades is not significant |
| Circuit breaker | None | Disable if >20% signals suppressed in 24h | Prevents over-filtering in choppy markets |
| Min swings | 8 | 10 | 8 is too few for reliable structure classification |

### Implementation Path

1. Add `STRUCTURE_SHIFT_ENABLED`, `STRUCTURE_SHIFT_PENALTY=0.75`, `STRUCTURE_SHIFT_WINDOW=50`, `STRUCTURE_SHIFT_MIN_SWINGS=10` to `hermes_constants.py`
2. Add `check_structure_shift(token)` to `signal_compactor.py` — returns penalty multiplier, not bool
3. Apply as soft penalty in `_score_signal()`, not hard block in HOTSET-FILTER
4. Backtest 14 days before live deploy
5. Add circuit breaker: if >20% of signals penalized in any 24h window → auto-disable STRUCTURE_SHIFT_ENABLED

### Decision

**APPROVE with modifications.** Implement soft penalty version, backtest 14 days, deploy only if backtest shows >$2/week improvement. No rush — system flat, stability period active.

---

## CEO Report — 2026-08-13 (Accel-300- Param Tuning)

### Decision: APPROVE Option A (F_slope_001)

**Change `ACCEL_300_REGIME_SLOPE_PCT` from `0.0005` to `0.001` in `hermes_constants.py`.**

### DB-Verified Numbers
- 24h: 107T -$0.52, 52.3% WR (flat/slight red)
- 7d accel-300- SHORT: 35T -$0.17, 57.1% WR (marginal — WR fine, losses > wins)
- Exit: 15/16 losses via `atr_sl_hit`, 1 via `cut_loser_-1.01%`

### Why Option A
- **Single param change** — minimal risk, easy to revert
- Backtest: +0.05% PnL, +0.6% WR over 8 days (310 trades)
- Only -8 trades vs baseline — doesn't over-filter
- Best PnL of all tested combos

### Why Not Option B or C
- **Option B (M_conservative)**: -45 trades, slightly lower PnL. More aggressive filtering not needed — 57% WR is fine, issue is loss magnitude not signal quality.
- **Option C (fix execution)**: Valid finding — NXPC/ETC were winners in backtest, so execution (stale price, ATR miscalc) is the real problem. But that's a separate investigation. Don't block a +EV param change on an unrelated fix.

### Risks
- Backtest is 8 days / 310 trades — small sample. Monitor 48h post-change.
- If WR drops below 35% or PnL goes negative after 48h, revert to 0.0005.

### Verification
- Will confirm param applied via `grep` after edit
- Monitor accel-300- WR and PnL in next 2 CEO runs
- If execution issues persist after param change, open separate investigation for ATR SL calculation

---

## CEO Report — 2026-08-13 (Stability Period)

### Diagnosis
7d PnL dropped +$0.38→+$0.16. Today (Aug13) 17T -$0.73 35.3%WR — ugly but tiny sample. 5 open all accel-300- SHORT. Pipeline running, volatility gate blocking entries (5/6 positions).

### DB-Verified Numbers
- 24h: 107T -$0.52, 52.3% WR (RED)
- 7d: 465T +$0.16, 52.7% WR (barely positive, down from +$0.38)
- LONG 24h: 19T -$0.61, 31.6% WR (bad, tiny sample)
- SHORT 24h: 88T +$0.09, 56.8% WR (profitable)
- SHORT 7d: 198T -$0.92, 53.0% WR (bleeding — losses > wins despite decent WR)
- Stars7d intact: bb_bounce+,range_finder+ 53T +$0.71 58.5%, range_breakout_short 15T +$0.43 66.7%, hzscore+,mover+ 5T +$0.17 80%, bb_bounce+,hzscore+ 34T +$0.22 50%, bb-bounce-short,hzscore- 18T +$0.14 61.1%
- accel-300- SHORT: 35T -$0.17, 57.1% WR, avg_win $0.05, avg_loss $0.08 (R:R unfavorable — losses 60% larger than wins)
- Cost drivers48h: atr_sl_hit 65T -$4.07 (dominant)
- 5 open (all accel-300- SHORT, $0 flat)

### Root Cause
SHORT7d bleeding from R:R asymmetry across multiple signals. accel-300- has 57.1% WR but avg_loss >> avg_win. range_breakout- also contributing -$0.12. No single kill candidate — distributed bleed. Today's cold streak (17T, 35.3% WR) is regime noise, not signal failure.

### Fix Applied
NO CHANGES. Stability period active. System flat (7d +$0.16). Stars intact. accel-300- marginal but not broken (57.1% WR, historically star). Overreacting destabilizes.

### Monitor
- daily PnL: if -2 consecutive red days → investigate
- accel-300-: if持续 bleeding → disable ACCEL_300_MINUS_ENABLED
- SHORT7d: if -$1.50+ → consider regime filter

---

## CEO Report — 2026-08-15 (Z-Score+Accel Thresholds Refactor — Noted)

**Acknowledged.** Thresholds for Z-Score+Acceleration alignment filter hardcoded in `decider_run.py` (0.5, 0.005) moved to `hermes_constants.py` as `ZSCORE_ACCEL_Z_THRESHOLD` and `ZSCORE_ACCEL_ACCEL_THRESHOLD`. Named constants imported by `decider_run.py`. Bug hunter: ALL CLEAR. No trading changes — single source of truth refactor only.

---

## CEO Report — 2026-08-15 (Weather Vane v4 — Tide Detection)

### Verdict: APPROVED WITH MODIFICATIONS

**Correlations are strong.** 839 trades, 14 days. 22-point WR gap (57.1% vs 35.2%) is the largest single-signal gap in our backtests. SHORT win rate as tide indicator is clean: >55% = bearish (SHORTs winning), <45% = bullish (SHORTs losing). BTC z-score adds confirmation but less standalone signal.

**Risks identified:**
1. **Backward-looking SHORT WR.** It reflects *recent outcomes*, not *future direction*. By the time SHORT WR hits 55%, the bearish move may already be priced in. Lag = missed entries on the best trades.
2. **Data gap: BTC 1h candles.** Only 18 available (need 20 for z-score). Minor — works at 18 with `if len(closes) < 10: return 0.0` fallback. But if price_collector stalls, z-score degrades to 0.0 (neutral). Acceptable fail-open.
3. **Feedback loop.** Suppressing LONGs during "bearish tide" reduces LONG volume → SHORT WR stays high → suppression persists. In a ranging market this could lock us out of LONG entries for hours. Circuit breaker needed.
4. **Dead zone 45-55%.** Neither condition fires → no suppression. This is correct (neutral = trade both), but means tide detection is binary: full suppression or nothing. No gradient.

### Modifications Required

| # | Change | Reason |
|---|--------|--------|
| 1 | **Soft penalty 0.7x** (not hard SKIP) | Aligns with Weather Vane v3 precedent. Hard blocks too blunt — 22-point gap is strong but 839 trades is still modest. |
| 2 | **Circuit breaker**: if >25% of signals penalized in 24h, auto-disable TIDE_ENABLED | Prevents feedback-loop lockout in ranging markets |
| 3 | **Minimum SHORT trade count: 10** (not 5) | 5 trades is noise. Need 10+ for WR to be meaningful. Spec says "if len(short_rows) < 5: return 1.0" — change to 10. |
| 4 | **Fallback: z-score uses closes[-1] if <20 candles** | Currently returns 0.0 (neutral). Better: use available candles (min 10 per existing code). Already handled. |

### Data Freshness Assessment

| Data | Source | Fresh? | Notes |
|------|--------|--------|-------|
| SHORT win rate | signal_outcomes (SQLite) | YES — 194 SHORT trades in 7d | Real-time |
| BTC z-score | candles_1h (candles.db) | YES — 18 candles available | Needs price_collector running |
| PostgreSQL trades | brain DB | YES — 103 trades in 24h | Real-time |

No data freshness blockers. Both sources are actively populated.

### Integration (2 files only)

1. `hermes_constants.py` — add 6 TIDE_* params (~8 lines)
2. `signal_compactor.py` — add `get_tide_penalty()` + `_get_btc_z_score()` (~40 lines), integrate into `_score_signal()` (~3 lines)

### Expected Impact

- **Target**: +2-4% WR on counter-tide trades
- **Risk**: Low — soft penalty (0.7x) means counter-tide trades still fire, just ranked lower
- **Revert**: `TIDE_ENABLED = False` (one-line toggle)

### Priorities After Approval

1. Implement tide detection (30 min)
2. Monitor 48h — verify SHORT WR window behaves as expected
3. Circuit breaker: add auto-disable if feedback loop detected
4. If tide detection shows <1% WR improvement after 7d → disable (YAGNI)
