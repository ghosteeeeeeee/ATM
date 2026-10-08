# Independent Verification Report — pump_exit "Dead-Money Time Exit" Concern Claim

**Auditor:** independent verification agent (adversarial, from-scratch re-implementation)
**Date:** 2026-10-08 (night)
**Target claim:** reconstruction of a LIVE exit rule (pump_exit dead-money component) "killed 6 home runs, net cost −$2.60"
**Data:** PostgreSQL `brain.trades` (paper=false, source of truth) + `/root/.hermes/data/candles.db` (candles_5m/1m, is_closed=1)
**Scripts (all in `/root/.hermes/audit/`, read-only against DBs):**
- `dm_verify_replay.py` — clean replay engine (conditions evaluated at bar CLOSE, trades truncated at actual close)
- `dm_verify_variants.py` — methodology matrix (bar-alignment × censor-grace) + dead-money forensics
- `dm_verify_deploy.py` — was the engine even operating Sep 13–20?
- `dm_verify_1m.py` — 1-minute-granularity replay of the 6 kills (attack vector b)
- `dm_verify_final.py` — era split, claim-config reproduction, premise counts, MFE check
- Artifacts: `dm_verify_results.json`, `dm_verify_variants.json`, `dm_verify_1m.json`

---

## BOTTOM LINE

**Verdict: (ii) Concern overstated — file with major caveats.**

The **design-level concern is real and robust**: a clean, methodologically sound replay independently reproduces the negative economics (29 fires, −$2.64, the same 6 home-run kills), and every proposed parameter fix still kills 3–6 home runs. **But the historical framing of the claim is wrong on a fatal point the original analysis missed: the dead-money time exit was dead code in production until 2026-09-21 15:05.** A datetime TypeError was silently swallowed by `except Exception: pass` for its first 8 days of existence. **All 6 "home-run kills" (Sep 9–20) predate the rule ever being able to fire.** In the 17 days the rule actually worked (Sep 21 → Oct 8), it fired 10× in scope, killed zero home runs, and its realized economics are roughly neutral-to-slightly-positive (+$0.66 at exit; post-exit drift median +0.19%).

The claim's headline numbers (36 fires / −$2.60 / 7-of-10 validation) are internally reproducible — but only under a configuration with a **5-minute lookahead** and a **300 s post-close grace window** that generates **6–7 impossible fires on already-closed trades**; 4 of its 7 "validation" hits are circular. The correct in-force denominator for the rule's premise test is 47 trades (not 147).

**Recommended framing to CEO:** "latent design risk — the 2h/+2% time exit reliably cuts future home runs whenever evaluation is live (proven by clean replay); current realized impact ≈ $0 because the rule only became operational Sep 21 and has killed no HR since" — NOT "the rule cost us 6 home runs."

| # | Claim | Verdict |
|---|-------|---------|
| 1 | Scope 147 trades, 13 home runs | **AGREE** (exact) |
| 2 | 36 fires; 7/10 validation; −$2.60 | **PARTIAL** — reproducible only with lookahead+post-close grace; clean engine: 29 fires / 3-of-10 genuine validation / −$2.64 |
| 3 | 6 home-run kills | **AGREE (numbers) / DISAGREE (framing)** — same 6 kills reproduced 3 ways, but ALL predate the functioning rule |
| 4 | −$2.60 split, 21/36, weeks | **AGREE (structure & weeks exact; ±$0.12 bucketing)** — but 100% of the negative sits in the pre-fix era |
| 5 | Premise: below +2% at 2h is normal | **PARTIAL** — conclusion holds for the correct population (86% of the 47 that reach 2h); counts 116/88 use already-closed trades; "5–7% vs 8.8%" HR rates are artifacts |
| 6 | Fix variants all still fail | **AGREE** (all four reproduced in kind; disable = +$2.64) |
| 7 | Post-fire drift ≈ neutral | **AGREE** (8/9/9, median +0.19% vs claimed +0.16%) |
| 8 | 11 SHORT dead-money exits predate reroute | **AGREE** (reroute commit Sep 29 14:53 > Sep 22–24 opens) |

---

## CODE-FACT VERIFICATION (all confirmed by reading code + git)

- `position_manager.py` 2791–2950: pump_exit = 3×ATR (1h candles) trailing SL + momentum exit (`< PUMP_EXIT_MOMENTUM_VEL (−0.5)` on 2 consecutive closed 5m intervals) + time exit (`hold_hours > 2.0` STRICT, `profit < 2.0` STRICT, newest-closed-5m-pair velocity adverse; LONG: (c[0]−c[1])/c[1] < 0 with c[0] newest). Momentum is checked BEFORE the time exit in the same cycle. Confirmed as described in the claim context.
- `hermes_constants.py` 1654+: `pump-chain+ → pump_exit`, `pump-chain- → rr_engine`, `pump_chain+ → pump_exit`, `pump_chain- → rr_engine`, `pump_chain (bare) → pump_exit`. Version stem-matching (`_key_stem = key.rstrip('+-')`) routes `pump-chain-v5 → pump_exit` via the `pump-chain+` key. Confirmed.
- Reroute `pump-chain- → rr_engine` landed **2026-09-29 14:53 UTC** (commit e905e34), i.e. after Sep 22–24. Before that (Sep 13 cc9423e → Sep 29) pump-chain- used pump_exit. **Claim 8's premise holds.**
- `PUMP_CHAIN_V5_ENABLED = False` since 2026-10-08 17:53 (commit 5f6364d). Confirmed; current live scope = pump-chain+ LONG. In-scope population is 100% LONG (147/147).

---

## CLAIM-BY-CLAIM

### Claim 1 — Scope population: **AGREE (exact)**
`paper=false AND status='closed' AND (strategy LIKE '%pump-chain+%' OR '%pump_chain+%' OR ='pump_chain')` → **147 trades**, all LONG (142 plain `Hermes-pump-chain+` + 5 compound/v5-tinged strings). **13 home runs (pnl_pct ≥ 10)**, tokens and values match the claim one-for-one: GRASS 30.8, INJ 12.5, FOGO 18.7, AVAX(15518) 23.6, JUP(15520) 21.1, AVAX(15547) 45.7, ETC 13.5, ADA 23.1, JUP(15570) 13.6, CASHCAT 11.6, ME 12.0, CRV 42.3, IMX 10.8.

### Claim 2 — Replay fires / validation: **PARTIAL**
The claim's exact numbers (36 fires, −$2.60, 7-of-10 dead-money overlap) are reproducible — but **only** with the configuration `align=open, grace=300s`:

| config | fires | impossible (post-close) | net Δ | dead-money overlap |
|---|---|---|---|---|
| close-aligned, censored at actual close (clean) | **29** | 0 | **−$2.64** | **3** (genuine) |
| open-aligned (= claim), censored | 30 | 0 | −$2.56 | 3 |
| open-aligned (= claim), grace 300 s | **36** | **6** | **−$2.60** | **7** ← claim's numbers |
| close-aligned, grace 240 s | 36 | 7 | −$2.63 | 7 |
| any config, no censoring | 89–91 | 59–62 | −$7.8 | 10 (all circular) |

Findings:
- **The original engine evaluates conditions at the bar's OPEN using that bar's CLOSE data — a 5-minute lookahead.** Proof: under open-alignment every kill number matches the claim exactly (GRASS 2.02 h/+0.65 %/−0.11 %, FOGO 2.11/+0.53/−0.01, AVAX 2.21/+1.21/−0.56, JUP 2.19/+1.59/−0.15, ETC 2.12/−0.43/−0.22, ADA 2.11/−0.15/−0.26); close-aligned gives the same trades one bar later/earlier.
- **6 of the 36 fires are impossible trades**: the position was already closed when the "fire" occurred (post-close by 0.4–24.5 min, using candles that closed up to 5 min after the trade was gone).
- **The "7 of 10 validation" is largely circular**: 4 of the 7 overlap trades (ENS, LDO, IMX, GMT#15918) were "predicted" only with post-close data. Genuine pre-close predictions: **3/10** (GMX 15588, AZTEC 15591, DOT 15982) — exactly what the clean engine gets.
- Under the clean engine the structure holds: 29 fires, −$2.64, 15 winners/14 losers, same 6 kills. **Direction robust; headline numbers methodology-flawed.**

### Claim 3 — 6 home-run kills: **AGREE on numbers, DISAGREE on framing (fatal context)**
The same 6 kills reproduce under my clean engine and at 1-minute granularity (values within one bar of the claim):

| id | token | clean fire | 1m fire | profit at fire | actual | gave up (clean) |
|---|---|---|---|---|---|---|
| 15126 | GRASS | 2.11 h | 2.008 h | +0.65 % | +30.8 % / $+1.57, atr_sl_hit | $1.46 |
| 15493 | FOGO | 2.19 h | 2.008 h | +0.53 % | +18.7 % / $+0.69, atr_sl_hit | $0.63 |
| 15518 | AVAX | 2.29 h | 2.292 h | +1.21 % | +23.6 % / $+0.53, atr_sl_hit | $0.40 |
| 15520 | JUP | 2.27 h | 2.005 h | +1.59 % | +21.1 % / $+0.47, atr_sl_hit | $0.29 |
| 15565 | ETC | 2.04 h | 2.040 h | −0.26 % | +13.5 % / $+0.30, atr_sl_hit | $0.33 |
| 15567 | ADA | 2.02 h | 2.022 h | −0.05 % | +23.1 % / $+0.52, atr_sl_hit | $0.54 |

But the fatal context the original analysis missed:

- **The time exit was dead code from its commit (Sep 13, cc9423e) until commit 8c09684b landed Sep 21 ~15:05.** Pre-fix line: `entry_dt = datetime.fromisoformat(open_time_str.replace('+00:00', ''))` — `open_time_str` is a **datetime object** from Postgres → `TypeError` every cycle → swallowed by the surrounding `except Exception: pass`. **First `pump_exit_dead_money` exit ever recorded: 2026-09-21 15:05:52** (26 s before the fix commit — file saved before commit, pipeline runs every minute).
- **The momentum component was also inoperative through Sep 20**: IMX 15549 had a momentum-qualifying moment at 1.71 h (Sep 20 01:10) and still exited `atr_sl_hit` at 01:15; first `pump_exit_momentum` exit ever: Sep 21 02:01 (HEMI).
- **Empirical confirmation**: 22 in-scope trades had time-exit-qualifying moments while open between Sep 13 and Sep 21 15:05 — **zero** fired. All 6 kills are among them. All 6 trades actually exited via `atr_sl_hit` (ratcheted trail) 1.6–6.1 h after the replayed fire.
- **All 13 home runs' closes: 11 of 13 closed before Sep 21; the 3 that closed after (ME, CRV, IMX) did NOT fire in replay** (ME 3.73 h hold and CRV 3.07 h stayed ≥ +2 % or velocity-positive; IMX held 0.48 h). **In the era the rule actually worked, it killed zero home runs.**
- "Velocity clause did NOT save any of them": **AGREE** — all 6 had adverse newest-pair velocity at fire under every engine variant.

### Claim 4 — Rule economics: **AGREE (structure), with era correction**
Under the claim's own configuration: 21/36 fires ended positive ✓; fires by **entry** ISO week {37:6, 38:23, 39:2, 40:4, 41:1} → **23/36 in week 38 exact** ✓; weeks 40+41 = **5** ✓; net −$2.60 ✓. Winner/loser split: mine $−3.89 / +$1.29 vs claimed −$4.01 / +$1.41 (±$0.12 bucketing of a zero-pnl trade; immaterial).

**Era correction (the number that matters):**

| era | fires | net Δ | kills |
|---|---|---|---|
| rule broken (closes before Sep 21 15:05) | 26 | **−$2.67** | **all 6** |
| rule working (after) | 3 | **+$0.03** | **0** |

100 % of the concern's economics — and every home-run kill — sits in the window when the rule could not fire. Realized behavior while working: 10 live fires, PnL at exit **+$0.66 total**, none home runs (largest: ENS +9.1 %, LDO +9.5 % pnl_pct — exited positive), post-exit drift median +0.19 % (claim 7) → roughly break-even.

### Claim 5 — Premise test: **PARTIAL**
- **Correct population**: only **47/147 trades were still open at 2 h** (SQL hold-time check; 43/37 have candle data within ±5 min of the 2 h point). The rule can only act on those.
- Of the trades that reach 2 h: **37/43 = 86 % (floor alignment) / 30/37 = 81 % (ceil) are below +2 %** — the claim's qualitative "below +2 % is the NORMAL state" **holds strongly within the relevant population**.
- The claim's counts (116 or 88 of 147) come from evaluating price at wall-clock 2 h **for trades that had already closed** (~100 trades). I reproduce ~110/97 (floor) and ~108/92 (ceil) with that (flawed) method — confirming their method, not its validity.
- **HR-rate framing flips**: within the 47 survivors, the below-threshold subset produced 7 HRs → **18.9 %** (floor) / 20 % (ceil) HR rate vs a 16.3 % survivor baseline — versus the claim's "5–7 % vs 8.8 %". The correct statement: below-2 %-at-2h has essentially **no negative predictive value among trades the rule sees** (all 7 surviving HRs were below +2 % at 2 h). The claim's conclusion direction survives; its stated rates do not.

### Claim 6 — Fix variants: **AGREE (all reproduced in kind; clean engine)**
| variant | mine (clean) | claim | kills (mine = claim) |
|---|---|---|---|
| profit < 0 at 2 h | 18 fires, −$1.60 | 20, −$1.79 | 3: GRASS/ETC/ADA ✓ |
| hold to 3 h | 20 fires, −$1.68 | 21, −$1.88 | 4 (GRASS/FOGO/ETC/ADA) ✓ |
| exempt if ever ≥ +2 % | 29 fires, −$2.64 | —, −$2.61 | still all 6 ✓ |
| exempt if ever ≥ +1 % | 22 fires, −$1.92 | 24, −$1.89 | 4 ✓ |
| require 2 consecutive adverse intervals (my extra test) | 27 fires, **−$2.89** | — | **still all 6** (fires later, gives up more) |
| disable time exit | +$2.64 vs current | +$2.60 | 0 |

**No cheap parameter fix eliminates home-run kills** — the strongest surviving support for the concern. (All of these economics also belong to the pre-fix era; in the working era every variant is ≈ neutral.) The "exempt ≥ +2 %" variant's futility is confirmed: the killed HRs never exceeded +2 % before the 2 h mark (max-profit at fire: GRASS +0.65, FOGO +0.53, AVAX +1.21, JUP +1.59, ETC −0.26→max ~+0.1, ADA ~+0.1 — none ≥ 2 %).

### Claim 7 — Post-fire drift: **AGREE**
All 26 `pump_exit_dead_money` exits (paper=false): direction-aware drift from exit_price to the 1 h-later 5m close (30 min minimum coverage): **8 recovered > +0.3 %, 9 continued < −0.3 %, 9 flat, median +0.19 %** (claim: ~8/~9/~9/~+0.16 %). After the rule exits, prices neither collapse nor moon — confirmed. (My first run had a tuple-unpack bug producing 2e10 % medians; fixed and re-verified.)

### Claim 8 — Historical SHORT scope: **AGREE**
- **11** `pump_exit_dead_money` exits on strategy exactly `Hermes-pump-chain-`, opened **Sep 22–24** ✓ (plus 2 on compound `pump-chain-,rs-r6x` labels and 3 on `pump-chain-v5` — the "11" is the exact-label subset; 13/14 SHORT-family total).
- Reroute `pump-chain- → rr_engine` commit e905e34: **2026-09-29 14:53 UTC — after Sep 24** ✓. The claim holds. (Caveat: pipeline runs every minute, so deploy lag ≈ 0; also all these fires post-date the Sep 21 datetime fix, consistent.)

---

## ATTACK VECTORS

**a. Censoring bias — claim's engine fails this, mine holds.**
My clean engine truncates each trade at its actual close; `all_exits_after_fire=True` (min lag +0.01 h) by construction and verified. The claim's configuration (open-align + 300 s grace) contains **6 impossible fires** (post-close by 0.4–24.5 min) — including 4 of its 7 "validation" hits. For the 6 kills the comparison is fair under any config: all actual exits (`atr_sl_hit` trail ratchets) came 1.6–6.1 h **after** the fire, so "exit at fire vs actual later exit" is the correct counterfactual (the ATR trail depends only on price, so it would have evolved identically). Non-kill fires: 27/36 rode to `atr_sl_hit`, 1 `profit-monster`/trail family, 1 `rr_engine_support_br`, 1 momentum, 7 genuine dead-money — all post-fire exits exist, none pre-fire.

**b. 1-minute timing fidelity — kills survive, mostly worse for the rule.**
All 6 kills fire at 1m resolution on `candles_1m` with the live engine's actual inputs (1m price + newest closed 5m pair): GRASS 2.008 h/+0.648 %, FOGO 2.008/+0.417, AVAX 2.292/+1.207, JUP 2.005/+1.205, ETC 2.040/−0.264, ADA 2.022/−0.052. **Five of six fire EARLIER than the 5m replay** (JUP ~13 min earlier, at the first minute past 2 h). The adverse 5m pair holds for the full 5-minute interval, and the position_manager cycle is 120 s (`run_pipeline.py` STEPS throttle) — a 2-minute cycle cannot miss a 5-minute window. Timing approximation rescues **nothing**.

**c. Velocity-at-fire robustness — fresh flips, not sustained downtrends, but robust anyway.**
Every kill fired on a **fresh flip**: previous interval positive in 6/6 (GRASS +0.17, FOGO +0.08, AVAX +0.91, JUP +0.48, ETC +0.46, ADA +0.39). Next interval: negative in 4/6 (GRASS −0.21, FOGO −0.05, AVAX −0.33, JUP −0.12), positive in 2/6 (ETC +0.06, ADA +0.16 — single-bar adverse islands). **However**, velocity-fluke-sensitivity does not create escapes: the exit commits at the first adverse-pair evaluation with profit < 2 %, which is deterministic at the 5m close (and at 1m — the pair changes discretely at bar closes). 0/6 would escape under a live 1m cycle. The kills' real fragility axis is the **profit** distance from 2 % (JUP +1.59 %, AVAX +1.21 % are within 1 % of the threshold) — and even those fire at 1m.

**d. Pseudo-replication — the claim's premise here is factually wrong.**
The 6 kills are **6 distinct tokens**; "AVAX×2 and JUP×2" refers to the 13-HR list, not the kills (only one AVAX and one JUP was killed). But clustering is still real: **5/6 kills in ISO week 38**, and entries pair up — {ETC, ADA} opened **2 minutes apart** (Sep 20 09:12/09:13), {AVAX, JUP} the same Sep 19 morning — so the 6 represent roughly **4 independent episodes** (GRASS-alone, FOGO-alone, AVAX+JUP, ETC+ADA), 3 within a ~36 h span, and all from the same broken-rule era. Effective n for "the rule kills HRs" is ≈ 4 episodes × (a period when the rule wasn't running).

**e. Second-order effects — bounded, and they favor the rule.**
Of the 36 claim-config fires: **zero actual exits were `hard_max_loss` / `cut-loser` family** (27 `atr_sl_hit`, 1 `rr_engine_support_br`, 1 `pump_exit_momentum`, 7 `pump_exit_dead_money`). The dead-money exit **never preempted a loss-kill** — no trade would have been HML'd later anyway (HML/cut-loser fires fast on dumping trades that die before 2 h). The dead-money rule actually **saved $+1.29 (clean: +$1.22) on eventual losers** while giving up −$3.89 on winners. Opportunity cost (capital locked longer without the exit) is not modeled; bounded by the fact that non-kill fires' actual exits happened 1.6–6.1 h later and netted positive on losers. Post-Oct-7 HML (`CUT_LOSER_PNL=−1.5` account, `HML_VOL_ATR_MULT`) touches only the 5 week-40/41 fires — none loss-family.

**f. Contribution concentration — yes, the entire concern is 6 trades.**
Top-5 negative contributors (clean engine): GRASS −$1.46, FOGO −$0.63, ADA −$0.53, AVAX −$0.40, ETC −$0.33 → **−$3.41 vs net −$2.64** (all six kills sum −$3.64; the other 23 fires net **+$1.01**). The −$2.60 headline is entirely the 6 pre-fix-era kills; on ordinary trades the replayed rule is a **net saver**.

**g. Momentum-exit preemption — non-issue (0 trades), with a twist.**
**0/29** clean fires (0/36 claim-config) had a momentum-qualifying moment (2 consecutive intervals < −0.5 %) before the replayed fire — the momentum exit fires on crashes, the time exit on gentle fades; disjoint regimes. Net delta unchanged excluding them. **Twist**: in the pre-fix era the momentum exit was itself inoperative (IMX 15549 counterexample, first momentum exit ever Sep 21 02:01), so pre-Sep-21 neither pump-exit component ran — replaying either against that era is anachronistic.

---

## FATAL FLAWS (in the claim as presented)

1. **All 6 "home-run kills" predate the functioning rule.** The dead-money time exit was dead code Sep 13 → Sep 21 15:05 (datetime TypeError swallowed by `except: pass`; fixed in 8c09684b; first ever fire 2026-09-21 15:05:52). The momentum exit was inoperative through Sep 20 as well. 22 in-scope trades had qualifying moments in that window; zero fired. Presenting these as "the rule killed 6 home runs" is historically false — they are counterfactual kills of a rule that was not running. **The realized kill count of the rule is 0.**
2. **The replay engine has a 5-minute lookahead and post-close impossible trades.** Conditions are evaluated at bar OPEN with bar CLOSE data (exactly reproduces the claim's per-trade numbers), plus a ~300 s post-close grace producing 6 fires on already-closed positions. The "7-of-10 validation" drops to a genuine **3-of-10** under a sound engine. (The direction and magnitude survive the fix — but the validation claim as stated is circular.)
3. **The premise statistic uses the wrong population.** "116 (or 88) of 147 below +2 % at 2 h" measures ~100 already-closed trades at wall-clock 2 h. The rule sees only the 47 that survive to 2 h; within those, below-threshold is 81–86 % (premise conclusion survives) but the stated HR rates (5–7 % vs 8.8 %) are denominator artifacts — the correct within-survivor comparison is 18.9 % vs 16.3 %, i.e. below-threshold-at-2h does not identify losers.

**What is NOT flawed:** the clean replay independently reproduces 29 fires / −$2.64 / the same 6 kills; the 1m replay confirms all kills; every fix variant still kills 3–6 HRs; claim 7 and claim 8 verify; the rule (now working) demonstrably fires on ~86 % of 2-h survivors that are below +2 % — so future HR kills are a live risk whenever a home run is slow to start.

---

## SIDEWIDE FINDINGS (see something, say something)

1. **`pump-chain-v5` SHORTS bypass the Sep 29 rr_engine reroute (medium).** `_match_exit_config` stem-matching routes `pump-chain-v5 → pump_exit` regardless of direction; the Sep 22–24 reroute only changed the `pump-chain-`/`pump_chain-` keys. `PUMP_CHAIN_V5_SHORT` stays True (regime-routed), so v5 SHORT trades still get pump_exit (ATR-trail) — the exact exposure ("CASHCAT lost 6.4 % with pump_exit") the reroute was made to remove. 3 v5 dead-money exits exist. Worth confirming this is intended.
2. **BUG-030 momentum loop "fix" (Oct 8) is a runtime no-op (low).** With `LIMIT momentum_candles+1` (window = 3 closes = 2 intervals) and exit requiring 2 consecutive, the old newest-first and new oldest-first loops have identical truth conditions (exhaustive 4-case check). The stale-momentum bug it describes can only manifest with a larger window.
3. **GRASS pnl data inconsistency (low).** pnl_usdt $1.57 vs pnl_pct/leverage × amount_usdt implied $1.71 (only inconsistent trade among the 13 HRs; others match to the cent). Possible fee-netting or HL backfill; worth a data-hygiene check.
4. **`except Exception: pass` around the entire time-exit block (medium, structural)** is what hid the dead code for 8 days. A counter/log for swallowed exceptions in exit blocks would have surfaced this on day 1.

---

## OVERALL RECOMMENDATION

**(ii) Concern overstated — file with major caveats.**

File to the CEO as a **latent design risk**, not a realized loss:
- **Real risk (verified 3 ways):** the 2 h / +2 % dead-money exit, when actually evaluating, cuts home runs that are slow to start — 6/13 historical HRs had qualifying fire moments, no parameter fix in the claim's set prevents 3–6 kills, and 1m fidelity makes fires earlier, not later.
- **Realized impact to date: ≈ $0.** The rule was dead code until Sep 21 15:05; in its 17 working days it fired 10× in scope, killed no HR, netted +$0.66 at exit with +0.19 % median post-exit drift.
- **Required corrections to the claim before filing:** drop "the rule killed 6 home runs" (replace with "counterfactual under idealized evaluation"); drop the 7-of-10 validation (genuine: 3-of-10); drop the 116/88-of-147 premise counts (use 47-trade denominator); disclose the lookahead engine.
- **Actionable options for CEO** (note: I tested an extra "require 2 consecutive adverse intervals" fix — it FAILS, still kills all 6 at −$2.89 because it fires later on the same slow-then-rally trades; there is apparently **no parameter tweak inside this rule's frame that saves home runs**, because home runs are below +2 % at 2 h *by construction*):
  (1) **Disable the time exit entirely** (keep momentum exit + 3×ATR trail): +$2.64 in replay vs current; the only cost is forgoing the +$1.29 saved on eventual losers, and era-2 realized data (10 fires ≈ +$0.66, drift +0.19 %) suggests the working rule's true contribution is ≈ neutral anyway. This is the only variant that reaches 0 kills.
  (2) **Profit gate to < 0 %**: halves fires (18) and dollars (−$1.60) but keeps 3 kills — partial mitigation only.
  (3) **Accept-and-monitor**: keep the rule for capital velocity but log every fire with MFE context and re-audit when the in-scope fire count doubles (currently 10 live fires in 17 days).
  (4) **Fix the operational gaps that made this analysis necessary**: instrument swallowed `except: pass` in exit blocks (8 days of silent dead code); fix the v5-SHORT routing bypass; require replay-vs-live divergence reporting (29 idealized vs 10 live fires) whenever exit rules are audited.
- If the concern is filed without these corrections, it repeats the exact failure pattern documented in AGENTS.md (selection-on-outcome + wrong denominator + unreproducible "validation"), and the auditor-visible contradictions (kills predate the rule) would sink it.

*All numbers in this report come from the scripts listed above, re-runnable read-only against the live DBs.*
