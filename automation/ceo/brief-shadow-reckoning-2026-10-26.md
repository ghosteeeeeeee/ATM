# CONSULT: The shadow era is not moving the needle — reckoning

**Budget ~30 min; print your full answer by ~minute 22. Every number re-queried by you;
file:line for code claims. Format: verdict first, then a ranked SHADOW-RECKONING table
with explicit CEO-APPROVED-TO-FLIP / KILL / KEEP labels + a learning-loop fix. This is
the strategic layer — items from the 10-22 (unclog) and 10-24 (short-starved) consults
are already shipped; do not re-approve stale ones.**

## T's message (verbatim, 2026-10-26 ~21:30 UTC)

> "we have been collecting 100x shadow data, needle has not moved. goals are not met.
> still net negative. losers bigger than winners. same mistakes still being made, the
> system is not learning/improving at all with 100x more data"

## Reports to read first (the substance T wants presented)

- `reports/20261026-mfe-mae-8h-verdict.md` — MFE/MAE over 8h, last 100 trades (amended).
- `reports/20261026-mfe-mae-8h-last100.md` — raw output + method appendix.
- `brain/verdicts/20261026-mfe-mae-8h-own-conclusions.md` — independent audit
  (AGREE 7 / PARTIAL 4 / DISAGREE 0; amendments applied).
Key conclusions from them: **74% of exits are followed by a bigger move** (median foregone
1.83pp); stopped-loser tail (18/42 would have been ≥+1%); for MFE≥0.8% trades the MAE to
survive is p50 0.57% / p75 1.17% / p90 1.62% price; at 5x HML (0.8% price) kills 13–14/64
before the peak — survivable **36–51/64**; peaks arrive p50 **~4.6h** (time-based exits
structurally can't reach them); coupled CUT_LOSER −4%→≈−6% + wider-SL shadow trial is
supported by the data and was deferred by you post-SL-sweep; new BUG-065 (HML vol-floor
dead code since the Oct-10 cap).

## Verified grounding — the needle (re-verify; correct me plainly where wrong)

**Performance (PostgreSQL brain):**
| Window | n | PnL | WR | avg win | avg loss |
|---|---:|---:|---:|---:|---:|
| 7d | 144 | **−$1.20** | 44.4% | +0.075 | −0.080 |
| 30d | 732 | **−$3.17** | 44.0% | +0.104 | −0.098 |
| **since shadow era (open > 10-13)** | 342 | **−$4.96** | **38.6%** | — | — |

Weekly: 09-28 **+$0.37** · 10-05 **+$0.25** · **10-12 −$3.61** · 10-19 −$0.45 · 10-26 −$1.13.
→ **The two pre-shadow weeks were positive; every week since 10-12 is negative.** WR is
the dominant term (38.6% since 10-13); avg loss ≈ avg win at 7d (0.080 vs 0.075 — "losers
bigger than winners" is directionally true this week but win-rate collapse is the bigger
factor; verify and state which term actually drives the −$4.96).
Goal: vacation_mode `daily_growth_target = 0.01` (1%/day) — currently the sign is wrong.

**Shadow inventory (the "100x"):**
- 15 shadow flags/modes in `hermes_constants.py`; 6 shadow systemd timers
  (t5, shadow-trader, expiry, mom-filter, tc, contrarian-monitor, gate-shadow cycle).
- `brain/gate_shadow.db` = **40,211** recorded blocks · oscillator_shadow.json 24,598 lines
  (stale since 10-01) · rr_shadow_audit 1,655 (stale 10-04) · wyckoff 342 ·
  floor_admit_shadow 1,461 · contrarian 754 events + summary · relative_regime flips 71%.
- `SHADOW_BYPASS_SIGNALS` registry: 16 signals (Stage A 5 / B 4 / C 7) — T directive
  10-21 "simulate disabled signals in shadow".
- Since 10-13: **97 shadow-related commits vs ~8 flip/enforce commits → conversion ≈ 8%.**
  Examples of never-flipped: TEMPORAL_CONFLUENCE_SHADOW (18 all-time log lines, dry),
  RR_ENGINE_SHADOW (log-only), REP_SHADOW_MODE, CHASE_RATIO_SHADOW, acceleration-threshold
  (no counterfactual stream at all — 10-24 consult found "insufficient evidence" streams).

## Questions

1. **Why doesn't shadow data convert to improvement?** Audit EVERY shadow stream
   (flags in constants, timers, jsonl/db files, shadow_bypass registry, gate_shadow,
   shadow_trader): for each — events collected, age, does it even join to outcomes, and
   a disposition **FLIP (exact value) / KILL / KEEP-until (date + threshold)**. The 8%
   conversion is the disease; name the systemic cause (no disposition deadline? outcome
   joins missing? flips require T and T is away? streams too dry?) and the mechanism fix
   (e.g., every stream gets a decision deadline + auto-escalation to kanban; streams
   unable to join outcomes get KILLed to stop collection cost).
2. **"Same mistakes still being made"** — mine the evidence: `automation/bugs.json` (65
   entries — count reopened/recurrence classes), `brain/verdicts/` (repeated findings),
   brain_auditor daily commit messages since 10-13, stale-comment class (BUG-065, the
   10-24 LOSERS/Waiver findings). What is recurring, why does daily auditing not stop it,
   and what one mechanism would (e.g., pre-commit stale-comment/pattern linter, kill
   switch for repeat classes)?
3. **Root-cause the −$4.96**: decompose since 10-13 by exit reason, direction, signal,
   regime — which bleed class dominates now (HML? trails? WR?) and which of your deferred
   items (coupled CUT_LOSER+SL trial, MoE fixes #1-3 from 10-13 plan, momentum-gate
   rejected-with-data 10-24) addresses it. Rank by $ impact and say which need only your
   label vs T approval.
4. **Are the goals reachable?** At ~$50 balance, 1%/day ≈ $15/day; realized is ≈ −$0.70/day
   (30d). What is the binding constraint — WR (38.6–44%), position size (size-reduce 0.5×,
   $11 floor), opportunity count (fills/day), or exit structure (MFE/MAE report: winners
   cut early, p50 peak at 4.6h unreachable)? Give the single highest-leverage lever and a
   measurable 7-day target that is NOT vanity.
5. **Deliverables:** (a) SHADOW-RECKONING disposition table with CEO-approved labels;
   (b) learning-loop mechanism fix (data→decision deadlines); (c) top-3 causes of the
   negative streak with ranked $ fixes; (d) what NOT to touch.

## Guardrails

- READ-ONLY — you label; implementation happens after (waiver scope: vacation_mode.json
  unclog_waiver still governs constants changes; anything outside it needs T explicitly).
- No blanket regime/time kills; knife RSI<35 stays dead; protected flags untouched.
- Verify every number yourself; if the framing of T's message is wrong on any term
  (e.g., losers-vs-winners asymmetry), say so with data — plain talk beats comfort.
- Distinguish: shadow-broken vs shadow-working-but-unflipped vs goals-miscalibrated.
