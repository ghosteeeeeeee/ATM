# CONSULT: "Sounds like excuses" — last 100 closed, winner vs LOSER SIZE

**Budget ~30 min; print your full answer by ~minute 22. Re-verify everything yourself;
file:line for code claims. This is a confrontation of OUR OWN framing — answer like T is
reading over your shoulder. Deliverable: verdict first, then a NO-EXCUSES action list
with CEO-APPROVED-TO-FLIP / KILL / KEEP labels (implementation follows immediately).**

## T's message (verbatim, 2026-10-28 ~02:30 UTC)

> "sounds like excuses again. look at the last 100 closed trades, we're still getting
> our asses kicked (look at the size of the winners and losers)"

Context: hours earlier the session's answer to "btc is pumping, where are the trades"
was largely "these gates are by-design/data-backed" (plus one genuine bug, BUG-068:
brain_auditor #188 inverted CHASE_RATIO_SHADOW at 19:50 on 10-27, live-blocked FOGO
conf-133 ×10, fixed/restored to log-only at 21:55, bugs.json #068, kanban correction
filed). T is rejecting the by-design framing as excuses. Test that claim honestly.

## Verified grounding (re-verify; correct me plainly where wrong)

**Last 100 closed trades (PostgreSQL brain, ordered by close_time DESC):**
- Net **−$0.19** at **WR 55.0%** — winning record, negative money.
- **avg win +0.0665 vs avg loss −0.0917 → losers 1.38× bigger than winners.**
  Breakeven WR at these sizes = **58.0%** (actual 55.0). **This contradicts the
  2026-10-27 consult's "losers are more frequent, not bigger" (since-10-13 aggregate
  avg win +0.085 > loss −0.077) — over the RECENT window the size asymmetry flipped.
  Say which window says what and why.**
- LONG 62T −$0.20 (53.2% WR, avg win 0.0633 / avg loss −0.0848) ·
  SHORT 38T +$0.01 (57.9%, 0.0714 / −0.1040) — SHORT makes money only because of WR.
- Best 5 wins: +0.34/+0.25/+0.22/+0.19/+0.16 (CFX pump-chain-, MET volume-buildup-,
  STABLE bb-squeeze+ ×2, FOGO pump-chain+). Worst 5 losses: −0.31/−0.21/−0.19/−0.17/−0.17
  (BLUR pump-chain+, DOT continuation+, PURR hh-hl+, LTC/ALT volume-buildup-).
- Loss-exit census (last100): hard_max_loss 8 = −$1.18 (single worst −0.31),
  atr_sl_hit 9 = −$1.01, cut-loser-CL-T1 4 = −$0.45, hard_sl 4 = −$0.42,
  trail_arm_timeout 13 = −$0.34, stale/manual = −0.28. **Losing exits = −$3.63;
  the 55 winners must overcome that and don't.**
- Position sizes uniform micro: avg $12.3 notional (11.1–22.1) — size is NOT the
  asymmetry; PnL per trade is.
- One position open: BTC LONG @80,950 (since 10-27 21:54, −0.04% when checked).

## Questions

1. **Anatomy of "asses kicked" at 55% WR:** decompose the −$0.19 (exit-reason ×
   direction × regime × signal; pre/post the 10-27 15:27 coupled-trial deploy —
   CUT_LOSER −6 + ATR_SL_MAX 4% has been live ~11h of this window: did it work, bind
   early (cut_loser T1 −1.0% price / SOFT_TRAIL interaction, registered in
   data/shadow_disposition.json MED-3 note), or backfire?). Is the dominant term
   (a) winners clipped early by exits, (b) losers riding to caps, (c) entry quality?
   **The MFE/MAE report (reports/20261026-mfe-mae-8h-verdict.md, audited AGREE 7/PARTIAL 4)
   says 74% of exits were followed by a bigger move and winners gave up tails —
   reconcile that with the 10-27 claim "exits can't flip the sign, WR is binding":
   WR is now 55% and money is still negative, so SIZE must carry the gap — quantify
   exactly what exit/entry changes recover the −$0.19 → positive at 55%.**
2. **Excuse audit (explicit):** for each of today's "by-design/data-backed" blockers,
   rule EXCUSE vs LEGITIMATE with counterfactual $: (i) bb-squeeze+ NORMAL-only
   (30d HIGH −$0.26/40T but 60% WR), (ii) pump-chain LONG HIGH block (37% WR),
   (iii) similar-setup WR<30 hard block (CC n=7 WR=14%), (iv) preserve-merge lets
   vol-blocked signals reach EXEC (approval/exec contradiction — wasted cycles; is
   this protecting us or laundering the block list?), (v) blacklisted BSV holding a
   hotset slot at sc=98/r5 (approval denominator 0/3 pollution), (vi) 10-min
   compaction expiry (27 LONG signals died waiting on 10-27). T's claim: the gate
   census is being used as a shield. Where is he RIGHT?
3. **Winner-size ceiling:** winners are capped by profit-monster-trail / ugb_pt
   giveback (0.30%) / SOFT_TRAIL / time exits — while losers reach hard caps. What
   is the measured cost of the winner-clipping exits in THIS window (n and $), and
   which single change makes winners bigger without unclipping losers?
4. **The one change:** rank by $ impact and effort what closes the 55%-WR-but-negative
   gap THIS WEEK (labels: APPROVED-TO-FLIP / KILL / KEEP / needs-T). Include whether
   anything from the 10-27 reckoning (coupled trial verdict early, mid-band eval,
   disposition deadlines) should be pulled forward because of this window.
5. **What NOT to touch** (protected flags, knife<35, 10-24 short floors, waiver bands).

## Guardrails

- READ-ONLY; you label, we implement right after.
- No blanket regime/time kills; no constants outside an explicit T-waived scope.
- Plain talk: if our earlier claims ("losers not bigger", "exits near-optimal",
  "by-design") were wrong or window-dependent, say so with numbers — T has called
  this "excuses" twice and deserves a straight answer either way.
