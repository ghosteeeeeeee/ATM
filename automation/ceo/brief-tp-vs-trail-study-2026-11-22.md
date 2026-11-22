# BRIEF: T orders a shadow study — TP (take-profit) instead of trailing-SL (2026-11-22)

## T's words (verbatim intent)
"Run a shadow study that sees if P&L improves if we go for a **TP (instead of trailing SL)
approach.**"
→ Design + register + (build if cheap) the counterfactual: what would the book have earned
exiting at targets vs the current trailing stack? T's intuition has SOME data behind it —
the study must be honest about the mixed prior art below.

## Parent's fresh exit landscape (PG, 11-22 04:44Z — trust, spot-check)
**14d exit mix (reason, n, WR, net-of-fee):**
- `profit-monster-trail` 73 · 95.9% · **+$3.64** (the winning engine)
- `atr_sl_hit` 32 · 0% · **−$3.85** · `hard_max_loss` 26 · 0% · −$3.01 · `manual_sl_hit` 22 · 0% · −$2.43
  (SL/stop family = the bleed)
- `mfe_exit` 16 · 93.8% · +$0.69
- **`manual_tp_hit` 10 · 80% · +$1.87** ← T's TP intuition: the second-best net in the window
  (note: manual = your own targets, n small)
- `prearm_lock` (new, enforced 11-20) 10 · 10% · −$0.20 (fires on losers, locks at BE — early)
- `hard_tp` 1 · +$0.21 · `manual_trail_hit` 5 · 80% · +$0.31 · `trail_arm_timeout` 3 · −$0.04

## Prior art (DO NOT re-derive — reconcile with it)
1. **`data/jup_exit_sim.json` (jup, n=98):** pm_trail sim +97.88 (100% WR) vs pm_actual −30.52
   vs **rr2_cfg / rr3_cfg (R:R targets = TP approach) −272.02** (41.2% WR, 56 timeouts) —
   TP-as-fixed-R:R was WORST for jup. atr_cfg −157, atr_norm −101.
2. **ride_it (the live TP engine):** RIDE_IT_ENABLED=True (:5524) serving volume-buildup etc.;
   atr_trend trial passed Bonferroni (p=3.9e-9) but **sign-reverses on the full book
   (n=38,349, p=0.0009)** — MoE (2026-11-19) explicitly ruled DO NOT roll out beyond atr_trend.
3. **MoE panel dissents in force:** no regime-matching, no notional caps, no new signals
   without evidence; ride_it generalization banned on current evidence.
4. Registry already has `reentry-study` (11-21) and queued giveback-profile items — the TP
   study must not duplicate them (re-entry = re-buy after exit; this study = TP as THE exit).

## What to design and register
1. **The study spec (registry entry `tp-vs-trail-shadow`, kind=shadow, deadline you set —
   suggest 12-06 for n):** define precisely:
   - **Population:** which signals/cohorts (all? stop-family bleed sources? the 8-source
     stop-tighten scope? profit-monster-trail cohort as control?) — justify the choice so
     n reaches the bar in the window.
   - **TP definition(s):** what variants are tested — fixed % target, ATR-multiple target,
     R:R-based (the jup-sim loser), MFE-based (trail-to-target)? Pick the2-3 worth testing
     and state why (each variant's hypothesis).
   - **Counterfactual engine:** entry = same fill, walk1m/5m candles, exit = first touch of
     TP vs the ACTUAL exit (and a trail-replay arm for the same trades = controlled
     comparison), fees in, token-day dedup where applicable, units guard (#193: pnl_usdt =
     price_move × notional; never mix leveraged pnl_pct).
   - **Bar:** e.g. TP-arm net ≥ trail-arm net + $1.00/14d AND fk ≤20% AND OOS halves same
     sign AND WR not down >5pp — set the numbers yourself, but they must be pre-registered
     BEFORE any result is seen.
   - **Where it lives:** reuse `scripts/jup_exit_sim.py` machinery (it already replays exit
     stacks — extend its arm set rather than writing a new simulator) OR `shadow_tag_join`
     pattern if signal-level; state which and why.
2. **Honest framing for T:** the prior TP evidence is MIXED (manual_tp +$1.87/10 vs
   jup rr-sims −272) — the study's job is to settle WHICH TP form, if any, beats the trail
   on a controlled same-trade comparison — not to confirm the hypothesis.
3. **Deliver:** the registry entry (full spec), whether a build is needed today (and if so,
   dispatch it log-only with gates) or whether existing sim machinery covers it, and what T
   should see at the read.
Constraints: no blanket kills, protected flags (PM_TRAIL_*), net-of-fees, token-day dedup,
flag polarity, speed mandate; rides the standing payoff program (stop-tighten/prearm/win-capture)
without colliding with their 11-21/11-22/11-24 reads.
