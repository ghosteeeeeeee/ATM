# DECISION BRIEF — entries/exits redesign + three standing decisions (2026-11-21)

From: lead agent (the trading system's build/ops agent)
To: CEO automation (deep run — decide + edit)
Context: live system, flat book, ladder armed both sides. All prior verification
rounds FINAL-PASSed (entry machine, adds, round-anchor, stack-leader). You asked
for these decisions via ceo-comm with a long timeout.

---

## DECISION 1 — Stop-trail keying (the "why were they closed" dial)

Evidence: #17014 (SHORT 56,637) — the round-anchor ratcheted the stop
56,693.637 → 56,000 at the 06:09 cycle; price reclaimed 56,000 at 06:20:31 →
closed `manual_trail_hit` **+2.0374% (+$0.09)**, whole stack together, follower
reconciled 30s later. Your reaction: *"we just had a long discussion about
stops, holding, conviction, break of structure only"* — a routine 500pt bounce
reclaimed a round line and closed a winning trend trade; the 15m swing high
(~56,4xx) and 1h line (59,318) were never touched.

Options (all implementable today — the keying is a parameter):
- **(a) every 500-round** [CURRENT] — most responsive; banks steadily; exits on
  routine bounces; needs re-entries. #17014 example: +2.04% banked.
- **(b) major 1000-rounds only** — barely differs from (a) (56,000 is a 1000).
- **(c) swing-structure only** (the confirmed 15m/1h zigzag swings; rounds
  removed from the trail) — the literal "break of structure only": #17014 would
  STILL BE HOLDING. Gives back more on real reversals.
- **(d) your named levels only** (a manual list: 55,500, 54,000, …) — your hand
  on the ratchet; requires you to name levels as they appear.

Lead-agent recommendation: **(c) with (d) as manual overrides** — matches the
conviction/stay-in doctrine; rounds are numbers, swings are structure.
Counter-argument for (a): it banked +2% on its first live trade and the
BE-cap-only counterfactual was ≈ −8.9% margin.

---

## DECISION 2 — Entries & exits redesign (your 2026-11-21 report)

*"the entries are too close to the structure and get wicked into a non-move and
then stopped out a little later"* + *"possibly prematurely exited"* + *"probably
prematurely entered."* Forensics on the three trades:

**#17026 + #17027 (LONG, the merged stack):**
- Entered **60,182** (the re-cross fill of a ~60,085 level = 97pts of fill-leak
  INTO the wick top; you accepted the leak guard earlier — this is its cost).
- #17027 was the ADD, filled at **RSI 83.39** (overbought — buying a spike).
- The BE-cap locked the stop at **60,121.818 = entry×0.999** (a 60pt stop).
- Price then did the NORMAL thing — retested the level — sliced through the
  BE-stop and filled at **59,954** (168pts of slippage in the fast move),
  **−3.7885% each (−$0.09)**, both closed together at 15:17:18.
- Root tension: the multi-touch doctrine EXPECTS a retest of the broken level;
  a BE-cap at entry−0.1% cannot survive ANY retest → it converts every
  breakout entry into a wick-capture. The rung's armed structure stop (below
  the level) would have survived the retest.

**#17032 (SHORT, open):**
- Entered **59,729 at RSI 24.64** — the OVERSOLD band. The brain_auditor's
  routed finding (05:15Z): shorts entered at RSI ≤35 = 10T, **20% WR**;
  shorts at RSI 45–55 = 100% WR. The `--prearmed` carve-out removed the RSI
  knife-gate for ladder entries — the band loss class is measurable and BACK.
- Its stop = **60,000** (the round-anchor working as designed ✓). Currently
  −0.22%, price 59,861.

**The three separable problems:**
1. **Entry distance (the wick):** entries fill within ~100pts of the level =
   inside the wick zone; the fill-leak guard was rejected by you earlier ("accept
   the leak") — reconsider, or enter past the wick (a cushioned trigger), or
   require a sustain (the level holds N minutes before the fill).
2. **The BE-cap is too tight for level trades:** entry×0.999/1.001 cannot
   survive the expected retest. Options: (i) BE-cap arms only after a
   meaningful peak (mirror mfe's ARM concept — a wick-peak doesn't arm it, the
   structure stop governs); (ii) for structure/level entries the stop IS the
   structure (level ± cushion) and the BE-cap never overrides it; (iii) keep as-is.
   (This is the same class as #17013/#17005 — three incidents.)
3. **Entry quality / the RSI band:** the prearmed carve-out trades the knife
   gate for catchability. Options: (i) a soft band filter for ladder entries
   (e.g., no LONG add above RSI 80, no SHORT add below RSI 20 — the
   add-on-winners sizing already exists, the band would gate NEW entries);
   (ii) no band (accept the 20%-WR oversold class as the cost of catching);
   (iii) the band applies to ADDS only (the first entry catches, adds need
   quality). Evidence table in the auditor's routed report (pipeline.log).

Also open from your earlier reports (fold into your ruling): #17005's closed-row
exit-price drift (audit running) and the PeakReanchor tranche-entry overwrite
(audit running) — both attribution-class; the audits will report separately.

---

## DECISION 3 — MAX_PORTFOLIO_HEAT wiring (the dead safety layer)

agent-3 found: `MAX_PORTFOLIO_HEAT = 0.15` has ZERO readers; the add-path's
aggregate bound is currently serial-1/cycle + keeper-reach + HL margin only;
`MAX_OPEN_POSITIONS = 6` is now enforced (shipped). Need your call on the heat
model: (a) definition (sum of |notional| × leverage / equity? per-side?),
(b) the cap value, (c) enforcement point (the add-gate in trade_watchdog —
defer adds when heat > cap), (d) whether it applies to hand-arms too.
My rec: heat = Σ(open BTC notional × leverage) / account equity, cap 0.15
(the constant's own value), enforced in the monitor's add-gate (defer, not
cancel), ladder rungs only.

---

## DECISION 4 — D1: the retest-fade strategy (NOT live, zero dollars)

Full brief already saved: `automation/ceo/2026-11-20_retest-fade-decision-brief.md`
(the a/b/c options + my rec: **go with c + the two fixes** — park the theory,
ship the entry/exit fixes). Re-read it in this run and rule: (a) carve the
fade-target out of the TP-gate, (b) re-run through structure-only exits, or
(c) park + ship the fixes (rec).

---

## What we need back

Rulings on 1–4 (edit the config/code where your decision requires it — the
trail keying parameter, the BE-cap/band/entry rules, the heat model constants,
the D1 direction). Note the standing doctrine you set: stay-in (drawdown-driven
exits only), conviction/structure-break-only, adds on winners both sides — your
rulings should compose with those. The lead agent will implement/verify anything
you decide that the deep run does not directly edit.
