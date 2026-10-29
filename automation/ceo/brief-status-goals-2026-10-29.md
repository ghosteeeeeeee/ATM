# CONSULT: Status check — goals, winrate, shadow usage, winner/loser control

**Budget ~30 min; print your full answer by ~minute 22. Re-verify everything; file:line
for code claims. Deliverable: status verdict first (one line per question), then the
ranked top-3 actions with CEO-APPROVED-TO-FLIP / KEEP / KILL labels — implementation
follows right after. Plain numbers over comfort.**

## T's questions (verbatim, 2026-10-29 ~13:50 UTC)

> "what's the update, look at the last 100 trades, are we meeting our goals? (0.3%
> daily profitability)? is our winrate any better, are we using our shadow data. are
> our losers in control or still over shadowing winners"

Note: T states the goal as **0.3% daily** — `vacation_mode.json` still carries
`daily_growth_target: 0.01` (1%). Reconcile (which is authoritative? propose the file
change if 0.3% is).

## Verified grounding (re-verify; correct me plainly)

**Last 100 closed:** WR **56.0%** (up from 55.0% on 10-28) — net **−$1.20** (WORSE than
−$0.19 then). avg win **+$0.0482** vs avg loss **−$0.0975** → **losers 2.0× winners**
(was 1.38× on 10-28 — asymmetry WIDENED). By side: LONG 71T −$0.11 (57.7%), SHORT 29T
−$1.09 (51.7%). Best win +$0.22 (STABLE bb-squeeze+), worst loss −$0.31 (BLUR
hard_max_loss). Exit census last-2d: PM-trail +$0.77/14, ugb_pt +$0.20/7 (avg +0.030),
atr_sl −$0.91/7, CL-T1 −$0.58/4, arm-timeout −$0.03/6.

**Daily PnL (6d):** 10-23 +0.32 · 10-24 +0.39 · 10-25 +0.32 · **10-26 −1.17 (39.3% WR,
the crash day)** · 10-27 +0.62 (76.5% WR — reckoning day) · 10-28 −0.83 · 10-29 −0.09
so far (7T, 71.4% WR). 7d = −$0.41; **since-reckoning (10-27 00:00): 52T −$0.30 at
WR 63.5%** — best WR era ever, still red.
Balance: last known ~$50 (verify from HL yourself) → 0.3%/day ≈ $0.15/day; 7d run-rate
≈ −$0.06/day → **shortfall ≈ $0.21/day**.

**Live now:** 1 open — BTC SHORT (13:18, +0.23% at 13:43). 24h: 19 closed, −$0.07
(Portfolio log). Recent wins: CHIP LONG +2.80 (12:41 — check if it was a
[CONTRARIAN-LIVE] pc- fade), YGG SHORT +1.12, SPX +0.88; recent ROI-% losers: VIRTUAL
−5.75, NXPC −3.65 (≈ −1.1% price = CL-T1 band).

**Shadow → action conversion since the 10-27 reckoning:**
- Contrarian pc- fade LIVE: 78 [CONTRARIAN-LIVE] lines (real fires incl. CHIP/CAKE) —
  verify its outcomes (fills, WR, PnL since deploy; the CHIP +2.80 may be one).
- UGB_PT 0.45: 7 ugb_pt exits since, avg +$0.030 ✓ positive.
- Cooldown cut (policy refusals no longer poison cooldowns) + tombstones truthful —
  ship-list evidence: NXPC SHORT entered 04:27 post-fix; verify SHORT fills since.
- Coupled trial running (CUT_LOSER −6 / ATR_SL_MAX 4%): bound-check (any HML exits?
  MED-3 T1-binding note in data/shadow_disposition.json).
- Gates killed per dispositions (tc/mom timers disabled, TEMPORAL off, oscillator
  archived, mirrors removed, accel concept dropped).
- **Registry: 22 entries (8 done, 14 open with deadlines 11-03/11-07/11-10);
  the weekly disposition runner has NEVER RUN (next fire Mon 11-02 08:15)** — the
  automated loop T demanded ("a cadence that isn't scheduled is a wish") hasn't ticked
  once; verdicts so far were manual consults. Decide: keep weekly or run DAILY while
  the 11-03 deadline cluster approaches?

## Questions

1. **Update + goals:** are we on track for 0.3%/day? Decompose the gap (WR × size ×
   frequency × exit quality) with numbers; reconcile 0.3% vs the file's 1%; state the
   binding constraint today and the one lever that closes the most $/day.
2. **Winrate:** 44% (pre-10-13 era) → 55% (10-28) → 56% (last100) → **63.5%
   since-reckoning** — is the improvement real (statistically) or cohort luck? Does it
   survive the 10-26-crash-day exclusion? Verdict on "is our winrate any better".
3. **Shadow data usage:** conversion table above — is the system now USEING its shadow
   data (flips shipped: contrarian, UGB, cooldown evidence, trial; kills executed)?
   What's still collecting-but-not-deciding (14 open registry entries — pull any
   forward given 11-03 cluster)? Should the disposition runner run daily during the
   deadline window? Is ANY collector still ahead of its decision?
4. **Losers vs winners:** 2.0× asymmetry in last100 vs 1.01× aggregate — is this
   structural (which exit rules clip winners: ugb0.45 effect measured, PM-trail
   protected, SOFT_TRAIL/timeouts) or cohort (crash-day losers aging in)? Where does
   the avg-win shrinkage (0.0665 → 0.0482) come from — exit mix or entry mix?
   Deliver the single change that most improves the ratio without unclipping losers.
5. **What NOT to touch** (protected flags, knife<35, 10-24 floors, trial pair
   auto-revert rules, family blocks).

## Guardrails

- READ-ONLY; you label, we implement right after (constants changes ride the
  vacation_mode.json waiver/review-queue; anything new needs an explicit scope line).
- No blanket kills; no comfort framing — if the update is bad, say bad; if good, show
  the number that makes it good.
- Speed: T is checking in between trades.
