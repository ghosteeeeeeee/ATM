# INDEPENDENT VERDICT — retest-fade-system-plan (own-conclusions)

**Auditor:** agent-1 (fresh eyes, no priming — read plan + skills + code from scratch, wrote own scripts in /tmp)
**Date:** 2026-11-20 05:0x UTC | **Target:** `/root/.hermes/plans/2026-11-20_retest-fade-system-plan.md`
**Data:** `/root/.hermes/data/candles.db` (live, still being written — sums drift slightly between runs)
**Scripts:** `/tmp/study1.py`, `/tmp/study1_grid.py`, `/tmp/study2.py`, `/tmp/study2_search.py`, `/tmp/study34.py`, `/tmp/sweep.py`, `/tmp/deep.py`

Data facts established first (queried directly):

| table | min ts | max ts | BTC bars |
|---|---|---|---|
| candles_1m | 2025-02-09 | 2026-11-20 04:31 | (full) |
| candles_5m | **2026-10-21 04:25** | 2026-11-20 04:30 | 8,642 |
| candles_15m | **2026-08-22 04:45** | 2026-11-20 04:30 | 8,640 |
| candles_1h/4h | 2026-08-22 | 2026-11-20 | — |

→ 15m starts Aug22 (plan's disclosure ✓). **5m only exists from Oct-21 — the plan does not disclose this**; any 5m OOS/walk-forward (G1) is impossible, there are only 30 days of 5m.

---

## === INDEPENDENT VERDICT ===

### Claim 1 — Study 1 as-armed: 0/9 win, −33.93% margin
**Verdict: AGREE** | Confidence: **HIGH**
Evidence: walked all 9 `status='error'` BTC ladder shorts (ts>1794990000) on BTC 1m from first trigger-cross, entry=trigger, SL/TP as armed in `pending_orders.json`. Result **0/9 exit at SL, sum = −33.93% @10x** — identical to the plan. Also =Σ stop distances 3.393%×10 (0.252/0.585/0.332/0.395/0.429/0.272/0.295/0.439/0.395 → the plan's "0.25–0.58%" ✓). 5m walk gives the same −33.93%.
Notes: the 9 ids are `btc-auto-ladder-*` (keeper-derived ✓); RSI rejections 11.93…41.26 = plan's "11.9–41.3" ✓; 7 knife(<35) + 2 HARD_FLOOR(45) ✓; `state['…']['status']=='error'` is terminal in `trade_watchdog._monitor_pending_orders_impl:1402` and `_ladder_keeper._unfired` counts `error` as consumed → **burn confirmed on both paths**.

### Claim 2 — Study 1 stops-ignored: 8/9, +112.55%
**Verdict: PARTIAL** | Confidence: **MEDIUM-HIGH**
Evidence: stops-ignored with a fixed 1.5% target, mark-to-end at data end → **+112.6%** (plan +112.55 — match to 0.05pp; small drift = live DB). But the count does not reproduce: **6/9 reach the 1.5% target, 3/9 still open at data end and all three in profit** → 6 resolved wins, 9/9 favourable — never 8/9. No variant (armed TP vs 1.5%, 1m vs 5m, cross-start vs reject-start, exclude-open vs mark) yields 8/9 with +112.5.
Notes: the sum is the reproducible part; "8/9" looks like a miscount of the open marks.

### Claim 3 — Study 1 1.2% structure stop: 4/9, −5.53%
**Verdict: DISAGREE** | Confidence: **HIGH** (on non-reproducibility)
Evidence: full recipe grid (1m/5m × start@cross/start@reject × stop{armed,0.4…3.0%,none} × TP{armed,1.5%} × wick/close-exit) — **no cell gives 4/9 −5.53%**. Nearest: 1.2% stop + 1.5% TP = **5/9, +84.8%** (5 TP, 1 stop, 3 open all in profit); 1.2% stop + armed TP = 2/9, +19.2%; 0.8% stop = 3/9, −3.0%.
Notes: this matters — the row is cited as proof that "no fixed tight stop reliably survives". In fact a **1.2% stop survives 8/9** (only rung-5's MAE 2.89% exceeds it) and nets strongly positive. The wider-stop variant is *better* than the plan reports, which strengthens, not weakens, spec #3.

### Claim 4 — MAE range 0.26–2.89%
**Verdict: AGREE** | Confidence: **HIGH**
Evidence: my 1m walk gives min MAE **0.26%** (as-armed) and max MAE **2.89%** (stops-ignored, rung 62278) — exactly the quoted range.

### Claim 5 — Study 2 down-window table (16/11/2 +169.2 | 19/6/4 +219.7 | 18/4/5 +197.3 | 18/3/6 +208.2, n=29)
**Verdict: PARTIAL** | Confidence: **HIGH** that it is not reproducible as specified; **MEDIUM** that the direction is right
Evidence:
- With the stated rules (±3 bars, prominence 0.25%, ≥6-bar spacing, zone 0.997, entry at zone / confirm at 0.99×level, stop at level, target entry×0.985, first-touch) I get **n=40–46** (not 29) and sums **+270…+450** (not +169…+220).
- Grid search over 24 swing recipes × 4 cells scored **max 7/16** against the table — win/stop *splits* come close (16/10/0, 19/6/1, 18/4/4) but no recipe reproduces all four sums.
- n=29 itself is reachable under ~70 different parameterizations (half 2–5 × gap 6–14 × 2 prominence definitions) — i.e. **the stated rules under-determine the detector**.
- Direction is robust: FADE0.8 and CONFIRM0.4 in Nov18→20 are positive in **24/24 recipes** (median +276/+250 vs plan +220/+197 — plan sits at the low end).
- Internal: FADE rows sum to 29 ✓; CONFIRM rows sum to 27 (18+4+5, 18+3+6) — consistent only if 2 of 29 touches never pull back to 0.99×level (undocumented).

### Claim 6 — "5 consecutive stops Nov18 19:35 → Nov19 06:05" (+ "7 straight before")
**Verdict: PARTIAL** | Confidence: **MEDIUM-HIGH**
Evidence: my FADE0.4 outcome sequence contains a stop-run that **starts at exactly 11-18 19:35 and runs through 11-19 06:05 (and 06:35)**, and **exactly 7 consecutive TPs precede it** (05:35→13:35) — both boundaries and the "7 straight" reproduce. But I count **10 stops inside 19:35→06:05 (12 in the full run), not 5**; FADE0.4 has 11 stops total in the whole window, so "5 consecutive" is a subset that only appears under an unpublished, stricter detector (n=29 vs my 46).

### Claim 7 — Study 3 rally Nov16–17 FADE0.8 = −27.5%
**Verdict: DISAGREE** | Confidence: **HIGH**
Evidence: 36 parameterizations (2 prominence definitions × half{3,4,5} × gap{6,10,14} × valley{10,20}) — **FADE0.8 is WINNING in 36/36**, including the recipes that hit the plan's own **n=21** exactly (14 TP / 7 stop → ≈ +154% margin, not −27.5%). Widest sweep (24 recipes): sum range **+52 … +163, positive 24/24**.

### Claim 8 — Study 3 rally CONFIRM0.4 = −160.8%, 0 winners of 13; snap FADE0.8 = −18.4%
**Verdict: PARTIAL** | Confidence: **MEDIUM-HIGH**
Evidence: rally CONFIRM0.4 loses in **32/36 recipes** (sum −124…+9, median −33) → direction ✓, magnitude ✗. But **n is never 13 (min 21)** and **0-winner recipes: 0/36** (min 10 winners). Snap Nov17 FADE0.8: positive in 23/24 recipes (plan −18.4) → ✗.

### Claim 9 — Study 4 LONG mirror table (BULL +372/+296/+123/+50, n=369; rally +447…; Oct −80/−190/−204/−282, n=141; Nov −245/−463/−698/−936, n=117)
**Verdict: PARTIAL** | Confidence: **MEDIUM**
Evidence (15m, same rules, entry 1.003×swing-low, stop at level, target ×1.015):
- **n is 30–60% higher than the plan's** (548 vs 369; 321 vs 228; 227 vs 141; 155 vs 117) — same detector under-determination as Study 2. No single recipe matches all five targets.
- Signs: bull FADE ✓ (+615 vs +372), rally ✓ (+441/+427 vs +447/+436), Nov control ✓ (−290/−683/−796/−1101 vs −245/−463/−698/−936), Oct CONFIRM ✓ (−794/−926).
- **Two sign flips:** BULL CONFIRM0.4 → **−352** (plan +123) and Oct FADE0.4 → **+174** (plan −80). Across 24 recipes Oct FADE0.4 is positive **24/24** → the plan's "Oct kills every variant" does not reproduce for FADE; BULL CONFIRM is positive only 9/24 (median −30).
- Internal check of the plan's own numbers: 369 = 228+141 ✓, 117 = Nov ✓.

### Claim 10 — "Rally payoff math: ~49% hit-rate × (+15 / −7) = 2.14:1 → EV+ despite 113 stops"
**Verdict: DISAGREE (internally inconsistent)** | Confidence: **HIGH**
Evidence: 15/7 = 2.14 ✓ and the +15/−7 pair *does* match the LONG FADE0.4 geometry (entry 1.003L, stop 0.996L → 0.698% → −6.98 margin ✓). But 0.49×15 − 0.51×7 = **+3.78% margin/trade → ×369 = +1,395%**, while the table says **+372%** (= +1.01% margin/trade = +0.101% price). A 49% hit rate at +15/−7 cannot produce the table (it would need ~77 winners and 113 stops → ≈ +840%). The paragraph's inputs come from a sample that is not in the plan.

### Claim 11 — "fade-the-retest is two-sided and regime-aligned"
**Verdict: PARTIAL** | Confidence: **MEDIUM-HIGH**
Two-sided ✓ (short down-window positive 24/24; long bull FADE positive 24/24). Regime-aligned only for **CONFIRM** (rally/bull CONFIRM weak-or-negative 22/24 & 15/24, chop/bear CONFIRM negative 24/24 & 24/24, down CONFIRM positive 24/24). For **FADE the claim fails in my runs**: rally and Oct FADE are positive in every recipe.

### Claim 12 — "the regime gate is the money component"
**Verdict: PARTIAL / lean DISAGREE** | Confidence: **MEDIUM**
In my re-runs the money components, in order of size, are: (a) **execution model** — the system allows ONE BTC position (brain dup-guard + serial/stacking guard), and under flat-only execution the sums collapse to **9–38% of ideal** and two control cells **flip sign** (rally CONFIRM0.4 −124 → +17; Nov FADE0.4 −291 → +57); (b) **costs** (below); (c) trend direction — real, but only for CONFIRM. For FADE the gate would *remove* profitable trades in my data.

### Claim 13 — "reclaim-of-trigger stops are a guaranteed-retest-stop"
**Verdict: AGREE** | Confidence: **MEDIUM-HIGH**
Mechanism is sound: the keeper's reclaim SL (sl1h + 0.6·ATR15) sat 0.25–0.58% above trigger while every one of the 9 trades saw a bounce ≥ that before any TP (MAE 0.26–2.89%). "Guaranteed" is in-sample wording — the mechanism (stop inside the retest's own wick envelope) is what §11-1 already says about first-break entries.

### Claim 14 — "the BANANA gates were accidentally right for the 9 rejections"
**Verdict: PARTIAL** | Confidence: **HIGH**
Right *relative to the stops actually armed* (avoided −33.93% margin). Not right *relative to the plan's own spec*: level stops would have been **+85%** (1.2% stop) or **+112.6%** (no stop) in my walk, and direction was right 9/9-ish. So the gates avoided a bad stop geometry at the cost of the trade — they were "accidentally correct" only because the armed stops were defective. Worth stating the counterfactual both ways; as written the sentence over-credits the gates.

### Claim 15 — Data availability: "15m starts 2026-08-22 (their Aug 16 unavailable)"
**Verdict: AGREE** | Confidence: **HIGH**
min(ts) candles_15m = 1787373900 = **2026-08-22 04:45 UTC** (1h/4h same day). Add: **5m starts 2026-10-21** (undisclosed in the plan).

### Claim 16 — Spec #6 reach-gap: "59,940 counted armed while 1,990pts away blocked all nearer shorts"
**Verdict: AGREE — still LIVE** | Confidence: **HIGH**
Current book: `btc-ceo-short-60000`, trigger **59,940**, `status=None` (unfired), BTC 61,516, ATR1h 739 → 3·ATR1h = 2,216, reach_lo = 59,299 → **in reach, short_ready = True → keeper derives nothing**. Distance now 1,576 (price moved; the plan's 1,990 at their snapshot is consistent). Note F-6's reach bound (`d01fe7ab`, 2026-11-13) already shipped and does **not** fix this case — spec #6 needs a *new* rule (nearest-unfired / tighter bound), not a re-proposal of F-6.

### Claim 17 — "the no-burn rework is the only safety-adjacent piece"
**Verdict: DISAGREE** | Confidence: **HIGH**
At least two others are equally safety-adjacent: (i) **spec #6 changes keeper arming** — the exact code bug_hunter has already audited twice (`bug-hunter-ladder-keeper-2026-11-13`, closures); (ii) **exit ownership** — the plan keeps structure-lag+BE-cap exits while its evidence assumes a 1.5% target that closes (see SPEC SOUNDNESS B1); changing/bypassing `structure_governed` is precisely the F-1 class and F-1 is still open (`bug-hunter-tp-gate-lagv3-2026-11-15` F-1: −34.5pp live / −17pp replay). The plan's own §5.4 hedges ("the only safety-adjacent piece + the full entry path").

---

## Standing verdicts that constrain this plan (read directly)

- **F-1 (HIGH, OPEN)** — `bug-hunter-tp-gate-lagv3-2026-11-15` / `bug-hunter-be-cap-f6-2026-11-15`: for managed+stop trades `structure_governed()` **suppresses the TP hit** (`position_manager.py:643-658`, `hit = None`) — "the target is validation-only; the trailing structure stop is the profit-taker". Verified in code: `MANAGED_TAGS = ('ai-trader-manual','ai-trader-pending','ai-trader-auto')` → **every keeper/pending fade trade is in this class**. Cost quantified: −34.5pp (#16915), −17pp (#16913).
- **Reach-gap (OPEN, live)** — see Claim 16.
- **F-9 (LOW, open)** — `_arm_real_leg` writes `pending_orders.json` **without** the flock; any new fade armer must take `pending_orders.json.lock` or lose arms.
- **F-8 (MED, doc)** — SKILL rule 13's short-side text is stale vs shipped keeper code (24h-low vs sl15/sl1h) — a hand-deriving agent can "correct" the code backwards.
- **Fill/resting** — `bug-hunter-tp-gate-lagv3` A(ii): **zero resting HL orders**; all exits are local, quote-derived fills (so "fill leak" is a local-sim artefact class, and F-7 candle drift 1m vs 15m is still open).

---

## GAPS RANKED

### BLOCKER (must change before code)
1. **Exit-model mismatch (evidence vs doctrine).** Studies 1–4 all bank a fixed 1.5% target; shipped doctrine *suppresses that exit* for managed+stop trades (`position_manager.py:643-658`). Spec #3.7 keeps structure-lag+BE-cap exits. So the tabulated payoffs (+15%/win) are not what production realises. Fix: either re-run every study through the real exit engine (lag trail + BE-cap + structure break, TP validation-only), or explicitly carve fade trades out of `structure_governed` — which needs bug_hunter + CEO sign-off because that is F-1.
2. **Entry style is contradictory.** §3.2 ships "failed retest only" (= CONFIRM, pullback ≤0.99/≥1.01), but the headline evidence (FADE rows, "FADE captures more legs", Study-4's best cells, the payoff paragraph) is FADE. Worse, §3.3's own sizing ("margin risk ≈ −11%/−7% @10x") is the **FADE** geometry (entry 0.997L, stop 1.004/1.008L → 0.70/1.10%); CONFIRM's stated entry gives **−14.1%/−18.2% margin**. Pick one style; the numbers must follow it.
3. **Reproducibility.** The plan says "all reproducible from candles.db" but ships no script, and the stated swing rules under-determine the detector (70+ parameterizations; 24-recipe grid search scores ≤7/16 on Study 2; 5 of 5 Study-4 n targets unmatched). Without the script there is no OOS re-run (G1/G2 cannot be executed).
4. **Execution model.** Tables assume unlimited concurrent BTC positions; the machine allows one (dup-guard + serial + one-rung-per-cycle). Flat-only re-run: **9–38% of the ideal sum, and two control cells flip sign**. Every table must be re-reported under the real constraint (fade rungs queue behind keeper rungs — that behaviour is not modelled at all).
5. **Cost floor kills the LONG mirror.** Round-trip taker = 0.09% (HL maker 0.015/taker 0.045, `hermes_constants.py:4637`). Per-trade average edge: down-window shorts **+0.59…+0.88%** (robust) vs Study-4 longs **+0.11% (FADE0.4), +0.06% (FADE0.8), +0.03% (CONFIRM)** → fees eat 80–300% of the edge before any slippage (G3's own fill-leak range is 0.1–0.5%/event). The CEO's actual request (longs on bullish data) is cost-negative as tabulated.

### SHOULD-HAVE
6. Fix/drop **Study-1 row B** (4/9 −5.53% unreproducible; a 1.2% stop survives 8/9).
7. Fix **"8/9"** (I get 6 resolved wins / 9 favourable) and the **payoff paragraph** (49%/113 stops don't reconcile with +372%).
8. **Fix the level lookahead**: a ±3-bar swing is only confirmable 15 min after its bar, but touches occur **1 bar** after the swing bar. Enforcing confirmability: BULL FADE0.4 **+615 → +160 (delay 3) → −9 (delay 6)**; down FADE0.4 +316 → +256 → +219. The long-mirror profit is largely a lookahead artifact; the short down-window survives (partly).
9. **n-independence**: 46 signals/48h in one decline with runs of 7–12 identical outcomes; top-3 half-day blocks = 29% of PnL; effective independent units ≈ 2–3 trend phases, not 29/46/369. Report episodes + block CIs, not signal counts.
10. **Regime-gate evidence is circular**: gate = live structure states, but the evidence for it = hand-picked calendar windows labelled by outcome (Nov18-20 "down", Nov16-17 "rally", Oct "chop"). Label the *same* windows with the shipped `structure_detail` states at entry time and re-measure.
11. **Fix Study-3 rally FADE0.8 (−27.5%)** — contradicted 36/36; it is load-bearing for "regime gate is the money component".
12. **No-burn error taxonomy**: `brain.py` exits 1 both for money-gate rejections (`:1752`) and for other failures; `_execute_pending_order_impl` burns on any non-success. Spec must name the contract (distinct exit code for `REJECTED`, e.g. rc=3) — otherwise it is string-parsing `❌ REJECTED:` or it re-burns real failures / double-fires HL outages. Preserve F1 fail-closed semantics (corrupt state → refuse).
13. **Stop authority at t0 vs after entry**: spec #3 (level±0.8%) vs keeper reclaim (`slX+0.6·ATR15`, was 0.25–0.58%) vs `_lag_stop` (moves it every cycle, BE-capped). State precedence explicitly — today three actors write the same stop.
14. **F-9**: fade armer must flock `pending_orders.json`.
15. **G1 restated**: no 5m history before Oct-21 → walk-forward only on 15m; say so.

### NICE
16. Disclose 5m starts Oct-21 (plan discloses 15m Aug22 only).
17. Same-level dedup: Study-1 armed **63025 twice** (9 rungs ≈ 6 distinct levels, one decline) — n is not 9 independent trials.
18. Zone sensitivity: 0.997 (0.3%) is narrower than a typical 5m bar range, so "touch" ≈ "every swing high gets touched" (46 touches/45 distinct levels) — sweep 0.99–0.999.
19. Table arithmetic: document why CONFIRM rows sum to 27 under "n=29".
20. Keep `bug_hunter` on the reach rule (#6) too — it changes arming.

---

## SPEC SOUNDNESS (§3, six components)

| # | Component | Verdict |
|---|---|---|
| 1 | Levels (±3 bars / 0.25% / ≥6 bars) | **Underspecified** — "prominence" has ≥2 readings (peak−max(valley) vs peak−min(flanks)) and neither reproduces the tables; also **two level definitions coexist**: entries use this fractal, the gate + `_lag_stop` use `structure_analysis`'s 0.6×ATR14 zigzag. Say which feeds what. |
| 2 | Entry (failed retest only) | **Contradictory** with the evidence base (FADE) and with §3.3's own margin numbers; "no-burn re-cross-wait equivalent" is undefined. |
| 3 | Stops at the level (0.8%/0.4%) | Numbers internally consistent **only for FADE** (−11/−7 @10x); for CONFIRM the same text means −14/−18 @10x. Conflicts with the keeper's reclaim formula. G4 (sizing vs HL $11 floor) still open. |
| 4 | Regime gate (1h+4h structure) | Mechanically fine (uses existing `structure_detail`, closed-bar data, no lookahead), but **the evidence for it is calendar-circular** and partly contradicted (rally/Oct FADE positive in 24/24). |
| 5 | No-burn on rejection | Rightly flagged safety-adjacent; **under-specified**: no error taxonomy / exit-code contract; must not weaken F1 fail-closed state handling or the one-shot double-fire protections. |
| 6 | Reach-gap | **Real and live** (verified: 59,940 rung, 1,576pts, in-reach today). Needs a new rule — F-6's 3·ATR1h already shipped and does not exclude it. |
| 7 | Interactions (G7/G8) | G7/G8 are named but the **TP-suppression contradiction is not** — that is the biggest integration risk. Also: fade rungs and keeper rungs share one config, one flock, one position, one serial slot. |

**Is no-burn the only bug_hunter-mandatory piece?** No — spec #6 (arming) and any change to exit/TP ownership belong in the same round.

---

## MINIMAL BULLETPROOF V0.5

Ship nothing that trades. One committed harness + one honest table:

1. **`scripts/backtest_retest_fade.py`** — pins the detector (exact params + prominence definition), Studies 1–4, first-touch, no survivorship, and prints each table with **four columns**: *as-simulated* / *confirmable-levels only (swing+3 bars)* / *flat-only execution* / *net of 0.09% RT fees + 0.1% slip*. That single table settles claims 5, 8, 9, 10, 11, 12.
2. **Correct the three unreproducible rows** before anything else: Study-1 B (4/9 −5.53%), Study-3 rally FADE (−27.5%), and the payoff paragraph (49%/113 stops).
3. **Resolve the exit question first** (blocker 1): either re-run through the real exit engine, or get an explicit CEO/bug_hunter ruling that fade trades keep a real TP (i.e. carve out of `structure_governed`). Everything else in §3 depends on it.
4. **One entry style + one stop authority + the no-burn rc contract + the reach rule** written into §3 (blockers 2, 12; should-haves 13, 6…).
5. Then shadow (entries OFF, counterfactuals logged), bug_hunter on *no-burn + reach rule + entry path*, CEO approval — exactly the plan's §5 order, but with the tables regenerated under (1).

**Bottom line:** the plan's *diagnosis* is right (reclaim stops are a guaranteed retest-stop; the gates burned 9 rungs; the direction was right; reach-gap is live; regime matters for CONFIRM). Its *evidence* is not yet code-grade: 3 of ~15 headline numbers do not reproduce, the long-mirror profit is lookahead- and cost-negative, and the payoff model contradicts the shipped exit doctrine. Fix the five blockers and v0.5 is defensible.
