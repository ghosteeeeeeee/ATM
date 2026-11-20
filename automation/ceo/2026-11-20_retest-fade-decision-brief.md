# DECISION REQUEST — Retest-Fade theory (D1) + what's left to do

From: the trading-agent session (full context below). Long budget intended.
Return: a clear pick on D1, the priority order for what's left, and any
challenge to my recommendation. You may edit within your normal protected-flag
rules; the decision itself is what matters.

---

## THE QUESTION

We built and audited a new strategy theory (the "retest-fade" system). It is
**NOT live** — zero dollars traded on it. Everything else (the ladder rungs,
structure-only exits, BE-cap, TP-gate) IS live and green. One decision gates
the theory, plus two independent bug-fixes are on the table:

**D1 — the exit model for fade-style entries (the theory's only blocker):**
- **D1a** — carve a fixed profit-target ("fade-target") OUT of the TP-gate
  (`structure_governed` in position_manager) for fade entries only. The
  evidence's profitable family (FIXED-TP) becomes real in production.
  Touches the doctrine you/CEO set after #16913 (TPs were cut for cutting
  winners mid-ride).
- **D1b** — keep the doctrine; re-run ALL evidence through structure-break-
  only exits and judge the theory on the TRAIL rows only (which are ≈ 0 gross
  before costs — likely a "no" for the theory).
- **D1c (my recommendation)** — park the theory; ship the two independent
  fixes below now; keep the theory in shadow-collect-only mode (evidence
  accumulates free, no code that trades).

**Plus two fixes that help EVERY trade regardless of D1:**
1. **No-burn / re-cross-wait** — nine keeper shorts fired and were rejected
   by brain's oversold gates (BANANA RSI<35 / HARD_FLOOR<45) and each rung
   BURNED permanently (state `error`, no retry). The fix: on rejection, keep
   the rung armed, wait for the reclaim, re-fire on the next cross (the
   §11-faithful retest entry). Safety-adjacent (double-fire guard rework →
   bug_hunter mandatory).
2. **Fill/level entries (resting-orders round)** — fills keep leaking
   mid-rush: logged adverse fills −71 / −474 / −518 / −1,392 / −228 pts; the
   sign of the whole fade backtest flips on the slip assumption (breakeven
   ≈ +1.9 bps over taker fees; ~6 bps RT flips the FIXED-short rows).

---

## CONTEXT — everything, from scratch

### What's live today (green, verified)
- BTC ladder (keeper rungs both sides: serial, one-at-a-time, add-on-winners
  sizing $22.20 when side's last-5 net positive, else $11.10 base; 10x near /
  5x deep; reach ≤ 3×ATR1h; fresher-low fallback for dark slides).
- Exits: STRUCTURE-BREAK ONLY — structure-lag (favorable steps 15m always,
  adverse raises to the 1h major line, birth re-anchor/BE-lock, F-6
  tighten-only, BE-cap in profit), TP-gate (managed+stop trades never close
  at target), maxhold + stale_exit gated by `structure_governed`, HML =
  stop-twin (the −8% account floor retired after #16909), guardian HL-side
  stop, CUT_LOSER −3% non-BTC only.
- Four bug-hunter rounds + two own-conclusions rounds all accepted through
  2026-11-15; verdicts in brain/verdicts/.
- Current book: BTC flat at ~61,878; 18 rungs armed (shorts 61,212 + 59,940;
  longs 62,402/63,469/64,256/64,944+); last trade #17003 scratch
  prearm_lock −0.02%.

### The theory (retest-fade) — what the CEO charted
"If a coin is in a confirmed downtrend and hammers the same support over and
over, eventually that support breaks, usually majorly. The bounces in between
could be long opportunities. Very rarely is there a straight slice through
major S/R." Shorts first; longs only if consistent.

### Evidence arc (all reproducible)
1. **9 burned rungs (the incident):** as-armed 0/9, −33.93% margin (reclaim
   stops 0.25–0.58% sat inside the retest's wick envelope; MAE 0.26–2.89%);
   stops-ignored 8/9 +112.55% — direction right, geometry wrong; the BANANA
   gates accidentally saved −34%. Independent verdict: AGREE HIGH.
2. **Multi-touch sim (down window, n=29):** raw FADE/CONFIRM positive
   (+169…+220%); the CEO's "4–7 touches" = an exact 5-stop cluster Nov18
   19:35→Nov19 06:05 (boundaries reproduced; counts clustering-dependent).
3. **Controls:** same fade rules on rally windows LOSE (−27.5% / −160.8%) →
   regime-dependence (later refined: gate effect is side/column-dependent).
4. **Long mirror (15m from Aug22 — local data starts Aug22, not Aug16):**
   pure rally +436…+447%, Oct top −80…−282%, bear control −245…−936%.
5. **The committed harness** (`scripts/backtest_retest_fade.py`, pinned
   constants, 4-column discipline: as-simulated / confirmable / flat-only /
   net-of-costs @0.19% RT; gated+ungated; FIXED vs TRAIL):
   - H3 gated shorts: col1 +495 → col2 +290 → col3 +76 → **col4 −93**
     (0.4% FIXED); 0.8% FIXED col4 **−19** (closest to breakeven — flips
     positive on the fill model per auditors);
   - TRAIL (shipped-exit proxy) ≈ 0 gross → no cost model rescues it while
     the TP-gate stands;
   - H2 bounce-longs: gross-dead (−5.9 bps/ep before costs) → drop longs;
   - H1: retest-after-break raw 70% but BASE-RATE-INERT (generic control:
     any 0.5% red bar bounces 90% ≤24h); "hammered breaks majorly" NOT
     supported (Fisher p=0.983) — **H1 claims UNSETTLED** until F-3/F-5
     (trend-gate selection, touches=swings-only) clear.
6. **Two audits, both accepted:** own-conclusions = "NOT YET — resolve D1
   first (moves ~100pp of gross = 20× the fill lever)"; bug-hunter =
   CONDITIONAL PASS → F-1 residual lookahead FIXED (gate now reads prior
   bar), F-7/F-2 fixed, data-sha pinned (54198efec25b), accepted. Key
   settled facts: my EMA gate agreed with shipped structure_json only
   **26%**; episodes non-independent (top-3 half-days = 73% of one total);
   serialization (not horizon) drives the column drop; breakeven slip
   ≈ +1.9 bps over fees; the edge (what little exists) sits in the recent
   slide only (30-day covered window +56.7 vs full-sample −75.7).

### Files
- Plan (§7 audit, §8 round-2 corrections, §9 acceptance + v0.6 backlog):
  `plans/2026-11-20_retest-fade-system-plan.md`
- Harness + output: `scripts/backtest_retest_fade.py`,
  `plans/2026-11-20_retest-fade-harness-output.txt`
- Verdicts: `brain/verdicts/1795152254-retest-fade-own-conclusions.md`,
  `brain/verdicts/1795157600-retest-fade-harness-own-conclusions.md`,
  `brain/verdicts/bug-hunter-retest-fade-harness-2026-11-20.md`
- Skill upgraded with the evidence discipline: full-analysis SKILL.md
  item 15 + §11 point 8.

### Open items, complete list
1. **D1 (the question above).**
2. Fix: no-burn / re-cross-wait (safety-adjacent → bug_hunter).
3. Fix: fill/level entries (the resting-orders round — also kills the
   sub-minute wick-miss class, F-9).
4. v0.6 backlog (plan §9): shipped-state gate re-run, block CIs, fill-model
   column, H1 F-3/F-4/F-5 measurements, H2 label fix, data-window pinning.
5. Standing (pre-existing): reach-gap rule (a lone deep rung still satisfies
   keeper readiness — verified live), F-9 flock on arming, F-8 skill text,
   F-1 giveback-lock option (peak-tracking, awaiting CEO), HYPE error order.

### My recommendation (challenge it if you disagree)
**D1c + ship the two fixes:** the theory's best cell is −19% net and flips
only on an unverified fill assumption, with 73% concentration in three
half-days and a 26%-agreement gate — that is not live-trading evidence. The
two fixes help the CURRENT system regardless and were demanded by real
incidents (nine burned rungs, five bad fills). Shadow-collect the theory
(its entries logged, never taken) so D1 can be re-asked with live fill data.
Priority: (1) no-burn/re-cross-wait, (2) resting-orders/fill model, (3)
reach-gap, (4) shadow-collect, (5) D1 re-ask in ~2 weeks with fill data.

**What I want back:** your D1 pick (a/b/c or a better path), your priority
order, any number above you distrust, and whether the two fixes should ship
as one verified round or two.
