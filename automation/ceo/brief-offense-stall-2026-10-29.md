# CONSULT: T's indictment — "surprised you haven't figured this out yet"

**Budget ~30 min; print your full answer by ~minute 22. Re-verify everything. This is a
STRATEGIC round, not a tactical one. Deliverable: (a) an honest diagnosis of why the
system hasn't evolved its winners, (b) the OFFENSE plan — tweak / clone / amplify —
with CEO-APPROVED-TO-FLIP labels and $/day math, (c) what automation changes make
offense self-running instead of consultant-driven. Numbers over comfort.**

## T's message (verbatim, 2026-10-29 ~15:10 UTC)

> "I'm honestly very surprised you haven't figured this out yet, with the amount of
> signal data (entry, exit, all in shadow + 6000 live trades) we have coming in right
> now, and the level of automation we have going on already. I'm honestly surprised you
> haven't started tweaking the signals that work, finding more like them, are just
> generally knocking it out of the ballpark. We're still grinding in the same place,
> big losses, wipe out any winning streak, still net negative. Very surprised"

T is not asking for another gate. He's asking why, with ~5,900+ trades of primary data,
full shadow telemetry, and a heavy automation stack (MoE weekly, self_learner,
brain_auditor, disposition runner), the system still **grinds in place**: big losses eat
winning streaks, still net negative. The missing thing he names: an OFFENSE loop —
tweak what works, find more like it, amplify, compound.

## Verified grounding (re-verify; correct me plainly)

**30d signal ranking (PG, closed, n≥10 — 726 trades / 69 distinct signals):**
| signal | n | WR% | net$ | avg$ |
|---|---|---|---|---|
| pump-chain+ | 88 | 42.0 | **+1.91** | 0.0217 |
| volume-breakout-long+ | 21 | 28.6 | +0.74 | 0.0352 |
| r2v2-long3 | 23 | 65.2 | +0.69 | 0.0300 |
| bb-squeeze+ | 100 | 64.0 | +0.65 | 0.0065 |
| ai-trader-manual | 15 | 46.7 | +0.34 | — |
| **pump-chain-** | **72** | **27.8** | **−0.95** | — |
| ai-trader+ | 29 | 41.4 | −0.80 | — |
| bb-bounce-v2-long+ | 58 | 46.6 | −0.73 | — |
| doji-bottom-long | 26 | 50.0 | −0.58 | — |
| continuation+ | 10 | 40.0 | −0.43 | — |

**Winner profiles (14d closed, n≥5 cells):** bb-squeeze+ NORMAL 20T 100%WR +1.30 ·
pump-chain+ EXTREME 12T 100% +0.72 · volume-buildout- HIGH 10T 100% +0.70 ·
bb-bounce-v2-long+ NORMAL 10T 100% +0.55 (verify: pre-block aging vs leakage past the
10-26 NORMAL regime-block) · volume-buildout- EXTREME/NORMAL cells also clean.
The **same family** (pump-chain) is simultaneously our biggest winner (+$1.91) and our
biggest loser (−$0.95 @ 27.8% WR) — and the ONE offense mechanism shipped for it
(CONTRARIAN-LIVE fade, CEO-OOS 64.7%) has logged ~39 flips → **1 live fill** (BIGTIME
−0.06). Its kill-table investigation is running right now (subagent) — design around
its landing.

**State:** balance **$24.43** (0.3% goal = $0.073/day, canon'd today); 7d run-rate
−$0.091/day; last100: WR 56%, net −$1.20, aw 0.0482 / al −0.0886 (1.84× against us);
payoff ratio 0.52 → breakeven WR 65.8% at that payoff (running 62.3% era-WR).
9 of 14 open registry entries deadline 11-03; daily disposition timer now live.

## Questions

1. **The honest diagnosis (answer like T is reading it):** why has OFFENSE stalled while
   defense shipped? Candidate causes to confirm/reject with evidence: (a) every
   positive change pays a tax stack (14d shadow + waiver + CEO consult + T sign-off +
   review + bug_hunter) while every kill ships in one auditor run — check the kill vs
   flip throughput since 10-13 (97 shadow commits vs ~8 flips before, what now);
   (b) no owner/mechanism for "find more like the winners" (MoE/self_learner/auditor
   are all disposition-oriented — name the missing piece);
   (c) parameter-level tuning never ran on the winners (pump-chain+ internals, bb-squeeze
   depths, r2v2 params — has ANY winning cell ever been widened?);
   (d) winners are structurally capped (UGB/PM/timeout exits, uniform $11-16 notional)
   so even a 62% WR can't compound; (e) something else you find in the data.
2. **The offense plan (labels + $/day):** using the ranking above — (i) TWEAK: which
   winning signal's parameters get widened (and what shadow-first evidence each tweak
   needs — cite the candle/trade window you used); (ii) CLONE: the find-more-like-them
   mechanism — mine signals/gate_shadow/shadow_trades + candle counterfactuals for
   setups that share the winners' profile but fire rarely or are blocked (name the
   exact query family + what automation runs it weekly); (iii) AMPLIFY: what makes
   winners bigger without unclipping losers (UGB-0.45 n=8/10 on track; size/notional
   floor; confidence multipliers — respect CEO_PROTECTED_FLAGS and T's no-blanket rule);
   (iv) CONVERT the fade (39 flips → make them fills — the investigation lands soon;
   this is simultaneously the biggest bleed fix AND the biggest edge unlock).
3. **The math to net positive:** current shortfall ≈ $0.16/day to the 0.3% goal.
   Rank the offense actions by $/day contribution with your own estimates + the
   measurement that proves each one (registry entry per action, deadline, threshold).
4. **Make offense self-running:** what automation change stops offense from being a
   consultant-driven event? Options to rule on: a weekly "winner-amplification" eval
   parallel to MoE-kill; auto-clone pipeline (shadow-first by construction, staggered
   via automatic-implementation skill); a flip-throughput budget (e.g., N shadow→live
   conversions per week) so the tax stack stops making defense the path of least
   resistance. Pick ONE mechanism with the smallest new surface.
5. **What NOT to touch** (protected flags, knife<35, 10-24 floors, trial pair + revert
   rules, family blocks with negative evidence — but note which family blocks have gone
   STALE by now and are candidates for re-examination with fresh data).

## Guardrails

- READ-ONLY; you label, T/I implement right after.
- Philosophy stands: every pump LONG, every dump SHORT, no blanket kills — the offense
  plan must ROUTE winners bigger and better, not silence risk.
- If the honest answer is "the governance stack itself is the bottleneck", say that
  plainly and propose how to fix it without weakening the guardrails that caught
  BUG-068, the inverted flags, and the BANANA class.
