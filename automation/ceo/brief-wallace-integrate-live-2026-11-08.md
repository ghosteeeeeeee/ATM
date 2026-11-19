# BRIEF: Integrate all mining — promote biggest winners LIVE now, stagger the rest via shadow (2026-11-08)

## Operator directive (carried as authorization)

The session operator instructs, verbatim: **"integrate these learnings into our system. We should
add some to shadow mode and the potential biggest winning points should go live right now.
Everything should be built and double checked (bug-hunter etc.). Any staggered future builds should
be automated using the automatic-implementation skill. Let's become profitable."**

This brief carries that authorization for **exactly what YOU determine qualifies as a biggest
winner with evidence in hand**. Anything you judge NOT to have sufficient evidence does NOT go
live — it goes shadow with a pre-registered bar. If a CEO_PROTECTED_FLAGS/constant edit is needed
for a live promotion, state the exact flag + old → new value in your ruling and record that the
operator authorized it this session; if your guardrails reject the edit, report `ok_after_reject`
style rather than routing around them. Revenue context: 7d 154T −$1.89 55.8% WR (your last run's
PG read) — profitability is the frame.

## Mining set to integrate (5 videos, all committed under `brain/transcript-mining/`)

1. `this-algo-strategy-has-only-3-rules-and-62-win-rate.md` — Connors 7d breakout; exposure-adjusted returns; ATR(20)×2 stop benchmark. You ruled exposure tracking + ATR benchmark do-now in an earlier session.
2. `i-gave-jev-control-of-a-trading-bot.md` / `i-turned-jev-ai-into-a-247-stock-trader.md` — architecture vindications; HL key audit (DONE, PASS-w/caveats); session/hour-of-day analysis; decision-stream dashboard (K, deferred).
3. `how-to-actually-build-an-ai-trading-bot-with-claude.md` — ALPHA course; drove the current batch (A locked test ✅, M rule loop ✅, H freq shadow ✅ live, B neighbor sweep IN FLIGHT as fresh subagent dispatched from your 173238Z checkpoint, I kill-lines + J exposure-budget authorized this week with bars already set).
4. `wall-st-trader-10yr-track-record-michael-wallace.md` — **NEW this session.** Key items:
   - **S1 STREAK ANALYSIS (quick win, read-only):** per signal source — max consecutive losses, WR after 1st/2nd/3rd consecutive loss, and first-win-after-streak MFE vs baseline. Directly adjudicates whether our LOSS_COOLDOWN_* (streaks→block) has data behind it or whether Wallace's opposite claim (odds IMPROVE after streaks) holds on our data. THE PATTERN discipline mandatory: n, p-values, OOS window, reproduce cmd. Feeds a possible LOSS_COOLDOWN calibration ruling (constants = T/operator gate).
   - **S2 EVENT-COMPLETION EXITS for mean-reversion sources:** exit when the reversion event resolves (z normalizes / reversion candle completes), not when price says so — his point: once the statistical window is met, trailing past it degrades odds. Candidate for bb_bounce/return_exhaustion/zscore family. Analysis of MFE-past-reversion first, then shadow.
   - **S3 NULL TEST per source:** check existing winrate-calculator skill first — reuse, don't rebuild.
   - **SKIP (ruled out):** Martingale sizing (first record streak = ruin; crypto has no bounded-streak floor; DRAWDOWN/KELLY reduce-after-loss stays), long-only bias, no-stop 1-day exits.
   - **Known-flaw rule for anything streak-based:** historical max streak is in-sample, never a hard bound — any promoted logic needs measured streak distribution with tail headroom.

## Questions — rule and DO

1. **LIVE NOW:** name the single biggest-winner candidate(s) with evidence already in hand across the whole mining set (candidates include: S1-derived LOSS_COOLDOWN recalibration IF the analysis this run proves our direction is wrong; ATR(20)×2 benchmark IF it beats our ATR_SL range on real data; anything else you judge proven). For each: exact file/flag, old→new, the evidence (numbers you or a subagent actually ran this session), and the revert path. **Independent verification before any live flip is mandatory** — separate verifier (own-conclusions or bug_hunter) reads the numbers cold; your own run is not sufficient (repo rule).
2. **SHADOW NOW:** which remaining items enter shadow this run, each with pre-registered bar (existing bars for H/I/J unchanged). **Use the `automatic-implementation` skill's staggered shadow→enforce pattern for every staged build** so collection→enforce is automated with an explicit approval gate — invoke the skill, follow its instructions.
3. **BUILD ORDER + DISPATCH:** dispatch implementation to fresh single-goal subagents this run (S1 analysis first — it gates the rest). S2/S3 analysis next if budget allows; report what didn't fit with its next slot. Do NOT collide with the in-flight B neighbor-sweep subagent (`scripts/neighbor_step_sweep.py` — do not touch that file or its result path `checkpoints/20261108T173238Z-result-1.md`).
4. **VERIFICATION CONTRACT (non-negotiable, per operator):** every build = code review subagent + **bug_hunter last**, commit per unit, no uncommitted leftovers; every LIVE promotion additionally = independent cold read of the evidence. State in your ruling which checks ran and their results — failures reported, never hidden.
5. **AUTOMATION WIRING:** any staggered build you set up must be wired so its shadow collection runs on its own (systemd timer, never cron) and the enforce decision surfaces to a CEO run on the pre-registered date — not dependent on a human remembering.

## Constraints

- `hermes_constants.py` existing values: operator authorization rides only with items you rule LIVE under Q1; everything else = new flags as False/zero-behavior or standalone scripts (your established pattern).
- H timer untouched; stop-tighten eval deadline 11-14 untouched; B subagent files untouched.
- Search before building — signal-lab/signal-backtest/winrate-calculator skills exist; no duplicates.
- Session lock + checkpoint-before-edit discipline as always; fresh subagents only, never resumed/compacted.

## Deliverable

Checkpoint with the ruling table: LIVE-now items (exact change + evidence + verifier result) /
SHADOW items (bar + automatic-implementation wiring) / build dispatch results (commits) / what
queued for next run. Report like a P&L: what changes, why, how it makes us money.
