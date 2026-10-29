# CONSULT: "btc is dumping, where are the shorts" — the 2026-10-29 dump chain

**Budget ~30 min; print your full answer by ~minute 22. Re-verify everything yourself;
file:line for code claims. Deliverable: verdict first, then a labeled action list
(COO-APPROVED-TO-FLIP / KEEP / DESIGN-PICK / KILL) — implementation follows right after.**

## T's message (verbatim, 2026-10-29 ~02:33 UTC)

> "btc is dumping, where are the shorts"

When asked which lever (quick cooldown fix vs CEO design round on compaction), T replied:
> "ask the ceo, use the shared ceo-comm skill, give a long timeout"

So both items are yours to rule.

## Verified grounding (re-verify; correct me plainly where wrong)

**Market:** BTC −1.83% in 3h (81,358 → 79,867, low 79,809) with the **01:00 candle
−1,086 points** (81,106 → 80,020). Continuum now: RECOVERY / BEAR / BELOW, age ~6s.
**0 open positions** (last close 01:11 — the BTC LONG died at dump start);
**last SHORT fill = 2026-10-28 14:25** (HBAR −5.25% ROI = ~−1.05% price ≈ the CL-T1
−1.0% band; recent shorts: USELESS +0.90, RESOLV +1.77, FOGO −3.53, BABY −5.34) —
**zero shorts filled during tonight's dump.**

**The chain (last 90 min unless noted):**
1. **53 SHORT signals EXPIRED `compaction_stale_10min`** — never reached approval;
   `Approval rate: 0/3` every minute of the window. Recurring: 10-27 = 393 LONG /
   870 SHORT expiries (2.2× SHORT starvation). The 10-24 consult's conflict-rescue
   fix (vol-floor) did NOT cover tonight's 53 — determine what is actually causing
   them to sit PENDING (confluence never arriving? conflict demotion? hotset only
   carrying blocked candidates? approval-denominator mechanics?).
2. **Knife did its job:** 3 exec attempts died at `RSI knife floor 28.7/29.1/29.x`
   (deep oversold after the cascade) — BANANA doctrine, NO change expected here.
   State that explicitly so it's not re-litigated.
3. **Cooldown poisoning (our design flaw):** WLFI SHORT is the perfect candidate —
   conf 78.9, EVERY gate green (`SHORT-NEUTRAL-BYPASS` bear, `CONFLUENCE-GATE-PASS`,
   `BTC-CHOP-3H` pass, `TREND-ALIGN 1.40×`, `TIDE 1.2×`, signal-analyst PASS) —
   and it is locked `hotset failure cooldown (2 failures)` until ~03:01. The 2
   failures were *exec-policy refusals* (knife/band) made while RSI was <35 — they
   flow through the trade-failed branch (`_record_hotset_failure`, the BUG-049 site
   we deliberately KEPT in UNCLOG-2 #2). Result: refusals that are correct at the
   time lock the token out exactly when RSI recovers into the admissible [35,45)
   band. **Rule the scope precisely: which failure reasons must NOT count toward the
   cooldown (policy refusals: knife/hard/soft floor, midband, similar-setup, vol
   regime) vs which MUST (genuine brain/HL execution failures, notional, API) —
   give the exact cut, and whether 2-policy-refusals-in-a-row needs ANY throttle.**
4. **Working, do not touch (cite if you disagree):** unclog band admits = **70 today**
   (`allowed at approval`); spike filter = **0 SHORT blocks / 448 bypassed**
   (RECOVERY+BEAR bypass works); bear exemption armed (continuum BEAR fresh);
   knife <35 intact.
5. **Family blocks** (EXTREME vol-gate ×126, confluence 2-source ×100,
   pump-chain-HIGH ×98): already ruled KEEP in the 10-28 excuses-audit with data —
   confirm or overturn with NEW evidence only.

## Questions

1. **Design pick for the compaction starvation (the 53):** option space with pros/cons
   + your pick: (a) extend staleness 10→N min, (b) pre-approve/conditional hotset
   admission before confluence completes, (c) hotset slot/denominator mechanics
   (0/3 = blocked candidates occupying slots — BSV-class issue from 10-27), (d) route
   single-source bear-bypass signals through a faster lane, (e) something else you
   trace from the data. First diagnose WHY tonight's 53 sat PENDING (query the
   signals table + compactor logs for that window) — the fix follows the cause.
2. **Cooldown cut:** exact policy (listed above) + implementation site + revert.
3. **Any label from the chain** I missed (e.g., the HBAR/BABY −5.25/−5.34 ROI losers
   = CL-T1 −1.0% band: does that interact with the live coupled trial's MED-3 note —
   T1 binds before HML? Include in the trial's 11-03 read if so).
4. **What NOT to touch.**

## Guardrails

- READ-ONLY; you label, we implement right after (vacation waiver scope: any
  constants change needs an explicit line in vacation_mode.json unclog_waiver).
- No blanket kills; knife <35 stays dead; protected flags untouched; family blocks
  keep their data-backed rulings unless NEW data.
- Speed matters to T (he's watching a live dump): lead with the cooldown cut and the
  compaction pick — those are the two that put shorts back in this move.
