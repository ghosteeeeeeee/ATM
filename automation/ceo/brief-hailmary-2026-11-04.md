# BRIEF: T — HAIL MARY REQUEST + shutdown risk (2026-11-04, ceo-comm long timeout)

## T's words (verbatim intent)
"Still more of the same on the trades. BTC is making giant swings — volatility is our life
force and we're sitting with barely any trades (at least profitable ones). Giant dump and
giant pump, nothing for us to show for it. Still net negative, bleeding every second trade.
Very disappointed. **Check your shadow calendar — see if there's anything you can use for a
hail Mary (many studies were due on the 4th Nov onwards).** Gonna have to shut down
operations soon — seems like a giant waste of time thinking you could help figure this out.
Months of work and maybe one profitable day."

→ Two deliverables: (1) HAIL-MARY TRIAGE of the shadow calendar — what is RIPE NOW
(bars already met, evidence already in hand) that we can act on TODAY instead of waiting
for 11-10/11-14/11-17 deadlines; (2) a blunt shutdown-risk assessment: trajectory, fastest
path to a profitable day, what would have to be true to keep going. No comfort.

## State (verified — trust)
**Performance:** 24h 41 closed net −$0.80 (fees in); 7d net −$5.71; 30d net ≈ −$16.9;
metrics verifier 0/7 at last run (goal-704ed65e); ~19 opens in last 12h = fills exist but
are thin and negative. Book has bled 6 straight days. ONE profitable day in the visible
recent record (10-31 +0.05).

**Shipped TODAY (all gated: review SHIP + bug_hunter SHIP, pushed a76ee44d):**
stop-tighten 0.75% ENFORCE (HML = 46% of 30d losses, was structurally inert at 1.0) ·
Cap C jup fill cap 1/6h (jup was 64-72% of fills) · LONG-bypass block in SHORT_BIAS
(worst cell 94T −$0.65; 20 real blocks day one) · amplifier bb-squeeze+/warrior ± weights
+ vol-gate HIGH allowlist · SHORT_RSI_CEILING 65→75 (yesterday). First proofs: clamps
writing at all sites, Cap C skipping, bypass blocks firing, ratio 4.3:1 → 2.4:1.

**Volatility context:** T says BTC printing giant dump AND giant pump swings — i.e. the
exact regime the philosophy calls home (every pump a LONG, every dump a SHORT), yet fills
are thin. Prior findings that constrain: confluence 2-source requirement, RSI floors,
SHORT-REGIME-GATE score-kill, pc-short-high/vol-gate blocks (all KEEP-ruled on data),
jup cap now limiting the former volume engine, chop/neutral blocks. The tension: we
throttled volume (jup cap, quality gates) while the tape got louder.

## THE SHADOW CALENDAR — 40 OPEN entries due 11-05 → 11-21 (act-on list for hail-mary)
Already-ripe candidates (bar may be met NOW — verify and act today):
- `jup-trail-shadow-1xatr` (11-17): bar "40 closed jup trades — ALREADY MET (97 as of 11-03)"; evaluate = replay would-armed trades → if positive, act today.
- `watch-contrarian-live` (11-10): bar ≥1 real fade trade MET (11+); remaining = Z-FLIP conversion check → can close early with verdict.
- `amplify-grind-breakout-deploy` (11-14): "shadow_trader: grind-breakout- n=26 WR 92.3% avg +1.56 = #1 source; live 30d only X" — if live gap is admission, this is a deploy candidate TODAY.
- `trial-wider-sl` / `trial-extended-time` (11-07): both bars FAILING hard (37.7% vs 55; −15.7pp vs +5) → default = KILL both, freeing machinery/conf — early kill is itself a hail-mary (stop funding dead trials).
- `harvest-ship-2026-11-04` (11-07): 4 metrics; read at 48h (11-06 ~04:00Z) — revert failures early if clearly failing by then.
- `fade-btc-crash-postflip` + `ichimoku-bypass-lowjoin-ticket` (11-05, i.e. NOW): both due TODAY — fade crash data already computed (dump-tape fade LONGs +$0.32 n=12 → KEEP); ichimoku join measurement or ticket execution.
Biggest potential unlocks (enforce-flips if shadow bars hit early — with T's speed mandate,
can these be pre-read on accumulated data?):
- `bear-single-source-shadow` (11-10): enforce = single-source shorts in SHORT_BIAS/BEAR — the biggest admission unlock; shadow lines already firing (16+).
- `volgate-short-exempt-shadow` + `maxxed-short-exempt-shadow` (11-17): short admission in vol.
- `storm-confl-waiver` (11-12): 3-storm bar — the tape IS violent now; storm packets may be accumulating fast.
- `rsi-ceiling-75-live` (11-10): revert rule check — if 65-75 band working, keep.
- `amplify-winner-cell-mult-150` (11-14): size winners up if cells positive.
- `amplify-stop-tighten-probe-080` + `stop-tighten-enforce-eval` (11-14): read stop-tighten's first days.
Others due: momentum-cache/capture/candle audits + timer-cadence (11-06), volmom, jup-yolo-regime, zombie-purge (11-09), mfe-cut/fade-ctx/winner-cell/conf-parity (11-10), pc+-weight-kill (11-13), atrtrail-clip + amplify-jup-short-walk (11-14), join-builder (11-16), reentry-study (11-21).

## Questions for you
1. **Hail-Mary list, ranked:** for each ripe item — ACT TODAY (enforce/close/kill) vs wait. Name exact actions with file/flag and metric. Prefer acting on already-earned evidence over waiting for calendar dates (T's speed mandate).
2. **Volatility harvest:** given giant both-way swings, which of the KEEP-ruled admission gates is actually throttling fills in THIS regime (measure: last 48h block counts by gate on qualifying signals) — and which relaxation is justified NOW by accumulated shadow lines (e.g. bear-single-source pre-read)? What is the fastest config path from "giant swings" to "fills that pay"?
3. **Frequency vs quality:** fills are thin (19 opens/12h) after jup cap + quality gates — is the system now UNDER-trading the best regime it has? Quantify: fills/day before vs after today's ships, and what a volatility-aligned target frequency should be.
4. **Shutdown-risk assessment (blunt):** 6 straight negative days, ~−$0.80/day net on thin volume, one profitable day in view. State: (a) how many more days like this before the numbers make shutdown rational; (b) the single fastest credible path to a profitable day THIS WEEK given what shipped today and what's ripe; (c) what we'd have to see by 11-07/11-10 to justify continuing vs folding. If the honest answer includes "some capital-preserving action" (size down, pause), say it with numbers.
5. Deliver: an EXECUTE-TODAY list (hail Mary) + the keep/fold decision framework with dated checkpoints.

## APPENDIX — your previous run (rc=124, incomplete: 58 tool calls, NO verdict text) burned its
## whole budget re-querying. Everything material is pre-seeded below. HARD RULE for this run:
## **maximum ~10 confirmatory queries, then WRITE THE VERDICT.** Prefer deciding over digging.

### Pre-seeded numbers (verified by the parent session — trust these)
- Book: 24h 41 closed net −$0.80 | 7d −$5.71 | 30d ≈ −$16.9 | 6 straight red days | ~19 opens/12h.
  Verifier 0/7 (goal-704ed65e): jup rolling-50 64% (48h 72%), HML 7d 34/−$4.83, ratio 2.4:1 (was 4.3:1),
  fleet WR 51.4% (14d), net72h −$3.33.
- Shipped today (gated SHIP+SHIP, pushed): stop-tighten 0.75 ENFORCE (HML=46% of 30d losses; live clamps
  proven at decider_open/pm/guardian), Cap C jup 1 fill/6h (290 SKIPs), LONG-BYPASS-SHORT-BIAS block
  (20 real blocks day one), amplifier bb-squeeze 1.3 / warrior ±1.6 + vol-gate HIGH allowlist,
  SHORT_RSI_CEILING 75 (yesterday). Ratio already moved 4.3→2.4:1.
- Calendar: 40 OPEN entries due 11-05→11-21 (full list in the brief above). Ripe-now set: jup-trail-1xatr
  (bar MET, 97 trades), watch-contrarian (bar MET, 11+ fades), grind-breakout-deploy (#1 source
  n=26 92.3% +1.56), trial-wider-sl + trial-extended-time (both FAILING → early KILL due 11-07),
  fade-btc-crash-postflip + ichimoku ticket (DUE TODAY 11-05; fade dump-tape computed: +$0.32 n=12 KEEP),
  harvest-ship metrics read 11-06 04:00Z. Enforce-flip candidates: bear-single-source (11-10, shadow
  lines already firing), volgate/maxxed (11-17), storm-confl-waiver (11-12, violent tape = storm bar
  filling), rsi-ceiling revert check (11-10), winner-cell-150 (11-14).
- Last-run artifacts: brain/analysis/HARVEST_INDEX_2026-11-04.md (6 artifacts: fleet net-of-fees
  19/22 cells negative; HML 46% of losses; backstop overlap; fade dump-tape +; HML reclaim 46% never
  reclaim; jup entry-split NULL — no entry filter exists).
- Prior verdicts in force: admission funnel NOT working (longs admitted 4.3x); every major short gate's
  fwd counterfactual costly EXCEPT floor-45 (protective) & pc-high (net-saving after fees); fade KEEP;
  "old winners phased out" REFUTED (all kills data-backed); entry-quality route closed (3 audits).
