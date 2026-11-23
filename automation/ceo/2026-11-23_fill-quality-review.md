# DECISION BRIEF — entry/exit relaxation review (the CEO's pending question, 2026-11-23)

From: lead agent. To: CEO automation (deep — decide + edit).
Context: T (03:0x): "you either got wicked in again into a bounce (rungs
need to be relaxed further), or exited too early (same, SL levels need
to be relaxed further), don't make any changes right now, revisit on
your next hourly run to see what ended up happening." This is the
dissection from that run (03:20). NO changes were made in between.

## The evidence (executed: 17 ai-trader-pending fills, last 72h, PG + local candles)

**Entry leak (fill vs the rung trigger, matched by fire-time):**
- mean **−193pts adverse** (min −812, max +404), **8/17 fills >200pts adverse**
- **BUT the leak does not predict the outcome:** the big adverse-leak
  fills NET POSITIVE as a group (+$0.37 over the adverse>200 set) —
  #17014 (−592pt leak) is the BIGGEST WINNER (+$0.50), #17016 (−359)
  +$0.196, while #17026 (−803) lost only −$0.02. A max-fill-distance
  guard would have refused the best trades of the window.
- Corollary: the earlier "fill-leak guard" question (T: "accept the
  leak") — the data says accept it again: the deep fills are the
  deep-runs' entries.

**Exit follow-through (price 60min after the exit vs the exit):**
- **10 SAVED / 7 PREMATURE** — the exits were correct in 59% of cases;
  the saved class NETS +$0.216, the premature class −$0.092.
- The 72h pending book overall: **net +$0.12 with fees** (positive).
- The premature class's composition: **3 of the 7 are already fixed by
  the shipped redesign** (#17013 mfe_exit → now off for ladder trades;
  #17026/#17027 BE-cap-at-birth → now needs a 2.5% peak to arm; the
  prearm micro-locks retired) — the residual premature class = 4
  (#17005, #17049, #17050, #17052: manual_sl/trail micro-exits), and
  it shares NO exit-type signature with the saved class (both classes
  contain manual_sl_hit and manual_trail_hit) — no clean selector.
- The 03:05 case T pasted (#17058): entry 333pts below its trigger
  (the leak), exit at the structure stop — and price has since risen
  to 61,667, i.e. **the exit saved ~760pts more** — this trade is a
  "saved", not a premature.

## The question for T

Given (a) the 72h book is net positive, (b) the leak correlates
positively with the biggest winners, (c) the premature class is
partly already eliminated by the redesign, and (d) the residual has no
clean selector — should we:

1. **Ratify "wait for the 2026-11-29 7-day gate"** (my lean) — the
   gate's metrics (never-ran share, BE-at-birth kills, closes/day,
   heat-binding) measure exactly this question on post-redesign data;
   the reverts are one-liners if a metric degrades.
2. **Relax the entries anyway** despite (b): specify the lever —
   a max-fill-distance guard (with the cost: it refuses the
   #17014-class winners), or fill-at-level resting orders (the parked
   resting-orders round), or something else.
3. **Relax the SLs anyway** despite (c)/(d): specify the lever —
   widen the structure stops (cost: the saved10's +$0.216 shrinks),
   or loosen the trail's micro-steps (the residual4's class), or
   something else.
4. Your own shape.

Reply with the ruling (or "wait for the gate") and the lead agent
implements/verifies per the standing process.
