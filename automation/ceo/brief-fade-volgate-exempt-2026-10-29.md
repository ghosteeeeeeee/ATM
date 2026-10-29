# CONSULT: RC1 label — direction-aware fade exemption at APPROVAL (vol-gate 0.0)

**Budget ~20-30 min; print by ~minute 20. This is a LABEL round on a pre-registered
decision — the precondition you set is now met. Deliverable: verdict + implementation
label (CEO-APPROVED-TO-FLIP / KILL / shadow-first variant) + anything to bind.**

## Context (your own words, consult 20261029T173906Z + autopsy follow-up)

> "exempt contrarian-live sources from the EXTREME 0.0 override — but only after
> re-running the fade OOS split by regime... Never enable without the split."

Autopsy (subagent 893bb816) established RC1 = the real conversion blocker: ~90% of
fade signals die at APPROVAL where `signal_compactor` (no inversion logic) evaluates
the STORED SHORT + '-' source sign; the biggest killer `('EXTREME','pump-chain-'):0.0`
took ~183 signals. The exec-stage exemption shipped shadow on 10-29; this consult is
the approval-stage unlock.

## The split you ordered (delivered — subagent 5434f9ac, exact reproduction)

- Cohort = the exact "226/350" base (`contrarian_outcome_join`, reproduced to the digit).
- Regime re-derived via the live gate's own 1h-ATR path; **96.4% agreement** vs
  PG-stamped regimes on 110 live trades.
- **EXTREME: n=226, 152W/74L = 67.3% WR (CI 60.9–73.0) — ABOVE the 64.6% overall**;
  EXTREME holds 64.6% of the cohort. NORMAL 60.2% (n=103), HIGH 63.2% (n=19), FLAT n=2.
- **Not stale-regime**: 95.6% of the 590 log-clustered kill-events were genuinely
  EXTREME at detect (the gate reads EXTREME correctly — it keys on the wrong thing).
- **Independent corroboration**: the 83 tombstoned kills replayed at true detection
  prices = 60.8% EXTREME (n=79); combined **200/305 = 65.6%**.
- **Both sides of the premise true**: pump-chain- SHORT EXTREME 30d = 28.4% WR −$1.14
  (the bleed the 0.0 targeted is real); pump-chain+ LONG EXTREME = 43.8% +$3.01 (the
  family keeps its habitat). The source-sign 0.0 kills the profitable direction with
  the bleeding one.
- Caveats on record: 37.3% of shadow rows dropped by a writer bug (BUG-069, filed;
  proxy-backfill proven biased — the hole is *unmeasured*, not collapse); shadow
  outcome = ±0.40% touch rule, no $; live fade evidence n=1 (−$0.06).

## The decision

**Label the RC1 exemption: direction-aware `0.0` override exemption for post-fade
LONG entries** — i.e., at the compactor's vol-gate-override check (and its sibling
direction-keyed approval checks — RSI floor sites check SHORT floors on would-be
LONGs, 4 kills), evaluate the EFFECTIVE direction (flipped when `_contrarian_live_hit`)
instead of the stored one. Keep intact: the SHORT-EXTREME bleed block, the HIGH hard
block (n=19 too thin), all exec-stage gates, and the 7d enforce bar on the exec
exemption (≥15 fills & ≥+$1.00, deadline 11-10).

Questions:
1. **Verdict + shape**: approve as-is? Or a different mechanism (e.g., exempt only
   the `('EXTREME','pump-chain-')` key vs a general effective-direction rule for
   contrarian sources at approval)? Scope discipline matters — the general rule also
   touches the 4 RSI-floor kills (tiny n) and future direction-keyed gates.
2. **Phase**: ship live immediately (the gate is semantically wrong — keyed on sign,
   not direction; the exec stage + enforce bar remain the live test) OR a shadow
   variant at approval too (log would-pass, still block, N days). The automatic-
   implementation SOP says shadow-first for NEW gates; this is the removal of a
   mis-keyed kill on an already-OOS-approved signal — your call which doctrine binds.
3. **Bind anything else**: does the ±0.40%-touch outcome (no $) plus n=1 live fill
   suffice for your bar, or do you want a bigger pre-label sample (and from where —
   the BUG-069 holes make "more shadow" slow)?
4. **BUG-069**: filed (MEDIUM) — skip-write when price falsy; confirm no backfill
   (proxy biased).

## Guardrails
READ-ONLY round; T's standing "proceed if CEO signed off" covers implementation once
you label. No blanket changes: HIGH block, SHORT bleed, knife<35, protected flags,
trial pair all stay.
