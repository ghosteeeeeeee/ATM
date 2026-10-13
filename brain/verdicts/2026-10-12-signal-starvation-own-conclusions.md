# Independent Verdict: Signal Starvation Plan
Date: 2026-10-12
Auditor: own-conclusions (fresh eyes, no priming)

All numbers below were produced by running actual SQL against PostgreSQL (`dbname=brain`), reading actual code, and grepping actual pipeline logs in this session. Nothing is from memory or from the plan's own claims.

---

## Actual Data Findings

### Q1 — Trade frequency and WR by day (last 14 days, closed trades, n=362)

| Day | Trades | Wins | WR% | PnL |
|---|---|---|---|---|
| 2026-09-29 | 44 | 20 | 45.5 | -0.78 |
| 2026-09-30 | 14 | 7 | 50.0 | 0.00 |
| 2026-10-01 | 29 | 13 | 44.8 | +0.36 |
| 2026-10-02 | 53 | 32 | 60.4 | +1.06 |
| 2026-10-03 | 33 | 18 | 54.5 | -0.08 |
| 2026-10-04 | 37 | 23 | 62.2 | +0.01 |
| 2026-10-05 | 31 | 15 | 48.4 | -1.33 |
| 2026-10-06 | 10 | 5 | 50.0 | +0.30 |
| 2026-10-07 | 13 | 3 | 23.1 | +0.83 |
| 2026-10-08 | 11 | 4 | 36.4 | -0.22 |
| 2026-10-09 | 23 | 10 | 43.5 | +0.17 |
| 2026-10-10 | 29 | 10 | 34.5 | -0.88 |
| 2026-10-11 | 13 | 7 | 53.8 | +1.18 |
| 2026-10-12 | 22 | 8 | 36.4 | -0.23 |

**Aggregates (computed from the rows above):**
- Sep 29–Oct 5 ("before tight filters"): 241 trades / 7d = **34.4/day**, 128 wins = **53.1% WR**, total **-$0.76** (avg day **-$0.11**)
- Oct 6–12 ("after tight filters"): 121 trades / 7d = **17.3/day**, 47 wins = **38.8% WR**, total **+$1.15** (avg day **+$0.16**)

**The single most important fact the plan omits: total PnL flipped from NEGATIVE to POSITIVE after the tight filters went in.** Fewer trades, lower WR, but better money. Per-trade PnL went from -$0.003 to +$0.0095 (3x improvement). The plan treats the frequency drop as damage to be undone; the PnL data says the filter change was, so far, an improvement.

14d direction split: **LONG 288T, 50.3% WR, +$2.50** | **SHORT 74T, 39.2% WR, -$2.11**. The system's SHORT book is the loss engine; the LONG book pays for it.

### Q2/Q3/Q4 — SHORT performance by entry RSI band (14d)

- **RSI < 45 (the blocked band):** 29T, 12W (41.4% WR), **-$1.15**, avg -$0.0397
- **RSI 45–65 (the band that passes):** 38T, 15W (39.5% WR), **+$0.22**, avg +$0.0058

Pre/post the Oct-7 hard-floor raise (25→45): pre-Oct-7 RSI<45 shorts = 27T, 10W, **-$1.70**; post-Oct-7 only 2T slipped through (+$0.55, n far too small to mean anything). I.e., **the cohort the floor now blocks was losing money at -$1.70/week before the floor stopped it.**

30d nested window: RSI<45 = 99T 40.4%WR **-$3.66**; 45–65 = 120T 45%WR **-$0.58**; ≥65 = 25T -$0.82. (Note: even the "passing" band is negative on 30d — all SHORT bands bleed; the floor merely blocks the worst one.)
90d nested window: RSI<45 = 449T 45.0%WR **-$6.61** (worst band); 45–65 = 260T -$2.04; ≥65 = 706T -$1.22.

Caveat for honesty: these windows are nested, not independent, and no single band reaches conventional significance on its own (n=47 bear/RSI<45 over 90d, avg -$0.034, |t| < 1). What IS robust: the sign is negative in every window, in both meta-RSI (constants comments) and entry-RSI (my queries) framings, and the entire 90d SHORT book is -$9.87 across 1,415 trades.

### Q5 — SHORT trades during bear structure (BEAR_TREND / RANGING_BEAR, 14d)

33T, 12W (36.4% WR), **-$0.10**. Cross-tab:
- BEAR_TREND RSI<45: 16T, 8W (50% WR), **-$0.29**
- BEAR_TREND RSI 45–65: 15T, 3W (20% WR), +$0.23
- RANGING_BEAR RSI<45: 1T, +$0.03

90d extension (my own addition): **bear-regime SHORT with RSI<45 = 47T, 21W (44.7% WR), -$1.58, avg -$0.034.** This is *precisely* the trade the plan's P0 #1 wants to re-enable ("in confirmed bear structure oversold = continuation"). The system's own executed history says that trade loses in bear structure too. The premise is not supported.

### Q6/Q7 — oversold-bounce LONGs

- Last 14d: 8T, 4W, +$0.02
- **All-time (since signal inception 2026-10-06): 8T, 4W, +$0.02** — the signal is 6 days old, n=8 ever
- By regime (all-time): BULL_TREND 3T -$0.06, RANGING 3T -$0.07, **BEAR_TREND 1T +$0.23**, TRANSITIONING 1T -$0.08

Log verification (2026-10-12 23:25): JUP, PURR, NXPC, WLFI LONGs with `source='oversold-bounce+'` were indeed killed by `CONTINUUM-BLOCK … BTC bearish structure`. The mechanism is real; the evidence that exempting it makes money is **n=8 total, net ~zero, one bear trade ever.**

### Q8 — final_confidence metadata

Present in `_signal_metadata`. Executed trades (last 3d) show final_confidence 42.5 → 242.3 (scores exceed 100 via boosts; "out of 100" framing in the plan is wrong but harmless). Corroborates that scores are being computed and stored, but executed trades are by construction the survivors — this cannot measure the blocked cohort's scores; the pipeline log SCORE-FLOOR lines do that instead.

### Log forensics (pipeline.log, 2026-10-12)

- **SHORT-RSI-HARD-FLOOR:** 2,284 block lines on Oct 12, **64 unique tokens** blocked at some point during the day. In the plan's cited window (22:40–23:30): **26 unique tokens** blocked (ADA, AIXBT, ALGO, ALT, ARB, BTC, CFX, CHIP, ETC, GOAT, GRASS, ICP, IMX, INJ, IO, LDO, MNT, ONDO, PURR, SAGA, SAND, USUAL, WCT, XPL, YGG, ZORA) — re-logged every minute. The floor is by far the dominant SHORT blocker; the plan's "7 of 11" *understates* its reach.
- **CONTINUUM-BLOCK:** 66 unique LONGs blocked on Oct 12; in the 22:40–23:30 window: WLFI(9), NXPC(9), JUP(9), PURR(7), TRX(3), BTC(2), HYPE(1) — matches the plan's named examples exactly.
- **SCORE-FLOOR:** products 0.0032–0.2997 observed, all floored to 0.3. Products **decay every cycle** (BTC SHORT: 0.2997→0.2680→0.2365→0.2049→0.1735→…→0.0201; staleness_mult shrinking as signals sit) — the crush deepens the longer a signal waits, a dynamic the plan misses. The plan's exact claimed values (INJ 0.0160, BTC 0.0070, JUP 0.0131) **do not appear verbatim** in the log, though same-magnitude values do.
- **RR-ENGINE on Oct 12 (4,935 graded evaluations):** mult=0.85 → 1,951 (39.5%); 0.70 → 1,575 (31.9%); **0.00 hard block → 1,296 (26.3%)**; 1.15 → 108 (2.2%); 1.30 → 5 (0.1%). During the dump, ~71% of evaluations get C/D-grade penalties, 26% hard-kill, ~2% boosted. The "grade C/D during dumps" observation is correct.
- **PENDING expiry:** verified in `signals_hermes_runtime.db`: created→expired spans of 10m16s, 10m22s, 10m33s, 10m43s (e.g., BTC SHORT created 23:57:28 → EXPIRED 00:08:01). "~11 min" confirmed (≈5–6 min before/around first cycles + the >5-min PENDING window). 1,125 EXPIRED in 3 days vs ~46 executions — starvation is massive and real. Crucially, the expired dump-window SHORTs (BTC, CFX, COMP, DOT, GMT, APT, LINK, HYPER…) are the *same tokens* the RSI floor blocked at approval.
- **HALL-SHAME:** 548 blocks on Oct 12, but **last occurrence 17:52:00 Oct 12 — zero on Oct 13.** `REP_SHADOW_MODE` was flipped to False ("FLIPPED TO LIVE 2026-10-12", hermes_constants:3711). In the live path (signal_compactor.py:1717–1726) the new reputation system applies a *multiplier* — reputation.py:536 explicitly says "apply HALL-SHAME multiplier (not hard block)". The old hard block lives only inside the `_REP_SHADOW` branch (signal_compactor.py:1701–1713). **Root cause #4 targets code that stopped hard-blocking the same day the plan was written.**
- **BB dead zone:** SHORT_BB_DEAD_ZONE2 = [0.35, 0.55] confirmed (hermes_constants:965–966); SYRUP blocked 10× in the window at that filter. Claim verified.

---

## Claim Verification

### Claim 1: "Frequency dropped ~31/day→~16/day, WR ~55%→~41%"
**Verdict: PARTIAL (direction right, framing wrong, key fact omitted)**
Actual: 34.4/day→17.3/day; 53.1%→38.8%. Plan's ~31/~16/~55/~41 are within rounding of reality. BUT the plan omits that PnL flipped **-$0.76 → +$1.15** over the same split. A "frequency drop with WR drop AND profit rise" is not evidence of broken filters — it is evidence of filters working. No causal analysis (regime shift vs filter change) is offered by the plan either way; I offer none beyond noting both windows' raw numbers.

### Claim 2: "7 of 11 SHORT signals blocked by SHORT-RSI-HARD-FLOOR"
**Verdict: PARTIAL (mechanism verified, count understated / not reproducible as stated)**
Actual: 26 unique tokens were blocked by this filter in the 22:40–23:30 window; 64 unique tokens across Oct 12. I could not reproduce a "11 SHORT signals, 7 blocked" cohort — the block footprint is larger than claimed. The floor is unambiguously the dominant SHORT blocker.

### Claim 3: "SHORT-RSI-HARD-FLOOR prevents shorting during dumps" (implying this is a bug)
**Verdict: AGREE on mechanism, DISAGREE on the implied conclusion**
Actual: the floor does block oversold shorts during dumps (verified in code: decider_run.py:2035–2037 "no bearish override", compactor line 3981, and logs). But the data says the blocked trades LOSE: RSI<45 SHORT -$1.15 (14d) / -$3.66 (30d) / -$6.61 (90d, worst band); bear-regime RSI<45 SHORT -$0.29 (14d) / -$1.58 (90d, n=47). The floor, raised 25→45 on Oct 7 (constants:905), coincided with the PnL flip to positive. Claimed "7 blocked at RSI 24–35 = missed winners" is unsupported — historically that cohort returns -$0.04/trade.
Note also: the plan proposes mirroring the SHORT_RSI_CEILING bear exemption (verified at decider_run.py:2048–2077, not at "lines 1959-1979" as the plan states — line refs stale), but that exemption applies to a band (65–75) whose SHORTs are also negative on 14d (-$0.73 combined) — the mirror precedent is not a good one.

### Claim 4: "Score crush: 25 multipliers stack multiplicatively, products 0.01–0.20"
**Verdict: PARTIAL (mechanism verified; counts and quoted values slightly off)**
Actual: 24 multipliers in `_mult_product` (signal_compactor.py:2109–2114), plus rr_mult applied outside = 25 factors total — plan's "25" counts the RR mult, fair. Observed products in logs: 0.0032–0.2997 (plan's "0.01–0.20" is the right order of magnitude). Claimed specific values INJ 0.0160 / BTC 0.0070 / JUP 0.0131 not found verbatim; same-magnitude products (JUP LONG 0.0382, CFX 0.0032, BTC decaying to 0.0201) confirm the phenomenon. Products decay cycle-over-cycle (staleness), making crush time-dependent — worse than the plan describes.

### Claim 5: "RR engine is exempt from the 0.3 floor" (signal_compactor.py:2131)
**Verdict: AGREE**
Verified: `final_score = score * _mult_adjusted * rr_mult` at line 2131, with BUG-12 comment at 2107–2108.

### Claim 6: "CONTINUUM-BLOCK kills oversold-bounce LONGs in bear structure"
**Verdict: AGREE on mechanism, DISAGREE on recommendation basis**
Actual: mechanism verified in log (JUP/PURR/NXPC/WLFI/TRX oversold-bounce+ LONGs blocked at 23:25 by "BTC bearish structure", signal_compactor.py:2784; pump-chain IS exempt via `_btc_exempt` at line 2672 — plan correct). But the recommendation ("mean-reversion that works during bear structure — buying dips") rests on **8 trades ever, +$0.02 net, exactly 1 bear-regime trade (+$0.23)**. That is not evidence; it is an assertion.

### Claim 7: "HALL-SHAME blocks tokens with 30d WR < 55%"
**Verdict: PARTIAL (was true; now stale)**
Actual: the hard block exists (signal_compactor.py:1701–1713, threshold 55%, min-sample 15 trades which the plan omits) and fired 548× on Oct 12 (DOT 28.6%, CHIP 44.4% — plan's "CHIP 33.3%" doesn't match the log's 44.4%). **But REP_SHADOW_MODE flipped live 2026-10-12; last HALL-SHAME block was 17:52 that day; the live path now applies a reputation multiplier, not a block.** The proposed "momentum exemption" modifies a filter that no longer hard-blocks.

### Claim 8: "BB dead zone [0.35, 0.55] blocks SHORTs"
**Verdict: AGREE**
Verified: SHORT_BB_DEAD_ZONE2_MIN/MAX = 0.35/0.55 (hermes_constants:965–966); SYRUP blocked repeatedly in the dump window. (Also SHORT_BB_DEAD_ZONE1 = [0.70, 0.85] exists at 961–962 — the plan only discusses zone 2.)

### Claim 9: "PENDING signals sit ~11 min then expire"
**Verdict: AGREE on timing, DISAGREE on the plan's causal story**
Actual: created→EXPIRED spans of ~10.5–11 min verified in the signals DB; expiry rule is ">5 min PENDING" (log + code comment at 5322). But the plan's root cause — "score crush empties the hotset → PENDING can't be approved" — is **architecturally false**: the hotset is a *relative top-10 slice* (`scored[:10]` at 3611; `hotset_final[:10]` at 5188). A top-10 of a non-empty list is never empty, no matter how low the scores. The dump-window PENDING SHORTs expired because they were **hard-filtered out of hotset_final (RSI floor at 3981, etc.)** and/or died at decider confidence gates — not because their scores were low in absolute terms.

---

## Critical Analysis of Recommendations

### Is "Option A: remove RR exemption from the floor" the right fix? — **No, and for different reasons than the plan's critics might guess.**

**Direction of effect (refuting the "would make scores lower" worry):** Under current code, final = score × max(prod, 0.3) × rr_mult. Option A is final = score × max(prod × rr_mult, 0.3). For the dump-window cohort (prod < 0.3, rr ∈ {0.70, 0.85} for ~71% of evaluations), Option A **raises** scores: 88 × 0.3 × 0.85 = 22.4 → 88 × 0.3 = 26.4 (+18%; +43% for rr=0.70). It lowers scores only for the rare boosted setups (rr 1.15/1.30, ~2.3% of evaluations) — silently deleting the RR engine's *rewards* and equalizing grade-A structures with grade-C ones whenever prod < 0.3. Information destruction, but not a score crusher.

**Futility (the finding the plan misses entirely):** The decider applies the score floor a **second time, on the raw product**: `PENALTY-GATE` (decider_run.py:3478–3492) computes exec_conf = final_confidence × max(penalty_product, 0.3) and blocks below MIN_EXEC_CONFIDENCE = 40. I simulated the full chain (base 88, prod 0.10–0.29, rr 0.70–1.30): **every crushed signal stays blocked at exec (exec_conf 5.5–10.3, all < 40), with or without Option A.** A heavily-penalized signal needs final_confidence ≥ 133 to survive the decider gate under the 0.3 floor. Option A moves exec confidence from 6.7 to 7.9 — irrelevant. The plan's headline promise ("fixes score crush, populates hotset") delivers ~0 additional trades from this cohort while (a) weakening RR-boost differentiation and (b) leaving the RR engine's 26.3% hard-blocks (grade F / R:R<0.7) untouched — those are the biggest RR kill-switch, and neither the plan nor Option A addresses them.

**The only place Option A plausibly helps:** absolute-score gates upstream — e.g., SHORT-REGIME-GATE (signal_compactor.py:2002, conf ≥ 75 in NORMAL vol; BTC SHORT was blocked at conf=74, a 1-point miss that an rr=0.85 penalty likely caused). Even then, the rescued signal immediately meets the next wall: the dump SHORTs blocked at compactor would still die at the approval-time RSI floor (3981) or the decider's exec floor. Fixing one link in a chain of three blockers does not release the trade.

**Risk assessment of each P0:**
- **P0 #1 (RSI floor bear exemption, 45→25):** re-opens the single most reliably negative cohort in the book (bear RSI<45 SHORT: -$1.58/90d; all-window sign consistent; the Oct-7 raise coincided with the PnL flip to positive). Would also need decider_run.py:2035 AND compactor 3981 AND SHORT_RSI_FLOOR (45) at 2042 all changed — lowering HARD_FLOOR alone changes nothing because EXEC-RSI-FLOOR blocks at the same 45. **The plan underestimates the code surface: two constants, three check sites.**
- **P0 #2 (RR exemption removal):** low direct harm, near-zero direct benefit, real subtle harm (boost erasure). If the goal is the SHORT-REGIME-GATE cohort, the surgical fix is a targeted threshold change or gate-specific handling — not a global floor semantics change.
- **P1 #3 (oversold-bounce CONTINUUM exemption):** n=8 all-time cannot justify it. Also collides with the just-shipped brain_auditor 2026-10-11 CONTINUUM tightening (lines 2735–2743, DECLINING+LEAN_BULL flicker fix) — re-opening bypasses on a block that was tightened yesterday is a filter-collision risk.
- **P1 #4 (HALL-SHAME momentum exemption):** moot — HALL-SHAME stopped hard-blocking when REP went live Oct 12. Delete this item or re-scope it as "review REP multiplier behavior".
- **P2 #5 (BB dead zone narrowing):** untested assertion; no band analysis offered. Fine as shadow-mode experiment, no data behind it yet.

**What the plan gets structurally wrong:** the causal chain "score crush → empty hotset → PENDING starvation" is false (hotset is relative top-10; starvation is hard-filter driven). Consequently three of six "root causes" are mis-prioritized: the actual kill chain for the dump-window cohort is (1) SHORT-RSI-HARD-FLOOR at approval + exec, (2) hard filters removing top-10 entries (CONTINUUM, REP, BB zones, spike/velocity), (3) decider PENALTY-GATE double-floor, (4) RR hard-blocks (26% of evaluations). Score crush on the compactor side is a minor entry in that list.

**Missing from the plan (auditor additions):**
1. **PnL flipped positive after the filters.** Any change must be justified against +$0.16/day, not against trade count.
2. **SHORTs lose, LONGs win** (-$2.11 vs +$2.50 over 14d). Both P0s increase SHORT flow. The philosophy "every dump is a SHORT" is an ideology the data currently contradicts.
3. **Decider double-floor** — the true exec-stage score crush, unmentioned.
4. **staleness_mult decay** makes products shrink every minute — signals are structurally time-starved regardless of floors.
5. **All nested-window caveats** — 14d ⊂ 30d ⊂ 90d are not independent samples; n=8 oversold-bounce and n=47 bear-oversold-shorts are individually under-powered (the latter's |t| < 1). Honest conclusion: no positive-EV case exists for unblocking, and the burden of proof lies with the unblock, not the block.
6. **REP live flip (Oct 12)** makes root cause #4 stale on arrival.

**If anything in this plan should ship, it is shadow-mode counterfactuals, not the exemptions.** The governance section already specifies shadow-first; the auditor recommends keeping that and *dropping the P0 enablement targets* until shadow data shows a positive counterfactual edge.

---

## Overall Assessment

# REJECT (as written)

Reasoning:
1. The plan's core premise — "filters broke, restore frequency" — is contradicted by its own system's data: PnL went from -$0.76 to +$1.15 in the same split the plan cites. The plan measures the wrong success variable (count/WR instead of PnL).
2. P0 #1 (unblock oversold shorts in bear structure) re-opens a cohort that loses in every window measured (14d/30d/90d, bear-specific 90d n=47, -$1.58). No statistical case is made for the exemption; the evidence points the other way.
3. P0 #2 (remove RR exemption) is built on a false causal chain (score crush cannot empty a relative top-10 hotset) and is nearly futile at the exec stage because the decider PENALTY-GATE re-floors the raw product — simulated result: zero crushed signals cross MIN_EXEC_CONFIDENCE=40 with or without the change, while RR boosts get erased.
4. Root cause #4 (HALL-SHAME) was already retired by the REP live flip hours before the plan's window; the plan audits a ghost.
5. Root cause #5's causal story (score crush → PENDING expiry) is architecturally wrong; the PENDING deaths are hard-filter deaths.
6. Sample sizes the plan leans on (n=8 oversold-bounce, "7 of 11" that doesn't reproduce — actual 26 tokens in window) fail the repo's own standing bar (AGENTS.md "THE PATTERN": significance, out-of-sample, collision checks).

**Salvage list (what a v2 plan could legitimately contain):**
- Shadow-mode counterfactual logging for every proposed exemption (RSI floor, CONTINUUM oversold-bounce, BB zone) — 7 days, as the plan's governance already requires. Ship the *measurement*, not the exemptions.
- Fix or explicitly design around the **decider PENALTY-GATE double-floor** if score flow is the goal; consider whether final_confidence should be pre-gate or post-gate consistently.
- Investigate why **SHORTs bleed -$2.11/14d** while LONGs earn +$2.50 — the frequency problem may be a *direction allocation* problem.
- Address **staleness_mult decay** (time-starvation) as its own root cause.
- Delete item #4 (HALL-SHAME) as moot; re-scope as "audit REP multiplier post-flip".
- Do NOT touch SHORT_RSI_HARD_FLOOR without (a) bear-band shadow data showing positive counterfactual PnL, and (b) a plan for all three check sites (compactor 3981, decider 2035 HARD_FLOOR, decider 2042 SHORT_RSI_FLOOR — lowering only one changes nothing).
