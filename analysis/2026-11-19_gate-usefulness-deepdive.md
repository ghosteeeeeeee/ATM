# Gate Usefulness Deep Dive — Which Gates Are Useful, Which Are Useless Blockers

**Date:** 2026-11-19/20 · **Window:** 2026-10-04 → 11-19 (46 days) · **Status:** CORRECTED PER OWN-CONCLUSIONS VERDICT — SELF-AUDITED 6/6 PASS — READY FOR EXTERNAL AUDIT · **Config changes:** NONE
**Requested by:** T. **Verification trail:** own-conclusions verdict `brain/verdicts/2026-11-19-gate-usefulness-own-conclusions.md` (8 claims: 3 AGREE, 5 PARTIAL → all defects corrected in this revision; correction ledger §10). Lineage: `audit/gate_counterfactual_verify.md`, `brain/verdicts/2026-10-12_deadlock-gate-verify.md`, `brain/verdicts/2026-10-30_shadow-redundancy-own-conclusions.md`.

## 0. TL;DR

1. **T's three claims all CONFIRMED** (own-conclusions C1 AGREE, recomputed from PG): frequency **47.0/day → 13.2/day (−72%)** since the Sep-7 week; **LONG 729T, WR 46.4%, net −$6.89**; SHORT 318T, 48.7%, −$1.71. Unprofitable in both directions.
2. **Gate answer over 46 days (56 gates, cluster-robust): 2 useful, 0 proven-harmful, 27 no-edge, 20 mixed, rest insufficient.** WORKS: **PUMP-CHAIN-RSI-MAX** (n=1,027, ex4h −0.190%, p_tok=0.012 p_day=0.005) and **LONG-RSI-CEILING** (n=989, −0.188%, p_tok=0.049). BLOCKS-SETUPS = 0 under the reference baseline — **but this is power-limited: median MDE = 0.227% at n≥400, so a gate harming at +0.15%/block would be undetectable** (§4b). The useless blockers are the **27 no-edge gates = 82.4% of episodes / 85.8% of events** of block volume (corrected from the v1 report's "99%").
3. **The funnel:** blocked episodes ran **4.3k–9.4k/week all window while trades halved twice (242→53/week)**; block:trade worsened 21:1 → **93.5:1**. This is *consistent with* upstream starvation (signal volume/confluence/confidence) but **not proven**: gate-mix shifted (TV 0.12–0.36/wk), a pass-proxy fell 4.5%→1.0%, early weeks are known-undercounted (pre-Oct-22 recorder capture 33–60% for several gates), and the signal-side denominator was never measured (§9).
4. **Self-audit found and fixed a real engine bug** (lookahead when entry precedes candle history; guard added, 24,699 events dropped) and, per the verdict, this revision fixes five more defects: two-run splice, the 99% figure, the missing RR-ENGINE gate (3,402 events, 56-gate frame now), undisclosed baseline/power/survivorship limits, and a wrong prune narrative (§1, §10).

## 1. Data, provenance, and the data-mutation finding (corrected per verdict C7)

**Frame:** 109,003 events = 57,993 reparse (Oct 30 → Nov 19, raw logs + archives, ground truth) ∪ 51,010 gate_shadow.db (Oct 4 → Oct 30; raw logs deleted pre-rotator). **56 gates** after the emoji expansion (C2 fix: the original 4-emoji parser hid RR-ENGINE's 3,402 events, BTC-CRASH 1,232, CHASE-BLOCK, CONFLICT-RESCUE-BLOCK and colon-glued gates; capture audit now lists all 54 overlap gates without an r<20 filter — 8 gates show db=0 because the recorder's own regex lacks their emojis, disclosed not hidden).

**⚠ F-DATA-1 (candles_5m mutability — narrative corrected):** `candles_5m` is under **30-day rolling retention maintained by routine incremental prunes** (collector journal: 514 boundary prunes on Nov 19 alone, 100–284 rows each; **no single mass delete** — my v1 report's "mass prune at 21:55" claim is retracted). `MIN(ts)` is a moving target equal to last_closed−30d (the auditor watched it move during its audit). Consequences, as corrected:
- Because the 30d cap has been in code since Oct 4, **history was already capped at my run time** — so *all* 24,699 events with entry older than the horizon were **lookahead-contaminated at run time** (v1's "computed from complete data, now unreproducible" is wrong; v1's "11 tokens/~564 fingerprint" was an artifact — events falling in the narrow post-boundary window made tokens look "varied"; the true contaminated population ≈ all 24,699).
- **Engine bug (real):** `fwd_metrics` had no entry-before-history guard — it silently measured forward returns from the first available candle (up to 17 days late). **Fixed:** `rows[0][0] > entry_ts + 300 → None` (the +300s matches the recorder's 5-min bucket convention — auditor confirmed the guard is correct). 24,699 events dropped (reproduced: 24,716 an hour later as the horizon moved); enriched 106,357 → **83,593**.
- The fingerprint evidence was destroyed by the drop → **unverifiable; stated as such**. This root cause also explains the prior auditor's "17% of expiry_shadow stored values don't reproduce."
- **Paper-trail implication:** `exports/nov19_gate_events.tsv` is the immutable snapshot of record; re-runs are stable only within the 30d retention window. Auditors should re-verify *method* (A3/A6) on retained data rather than expect bit-identical regeneration of expired rows.

## 2. Self-audit — independent second path, 6/6 PASS (re-run after every correction round)

`gate_usefulness_selfaudit_2026-11-19.py` → `.md`: **A1** independent re-coalescing of the export matches summary per-gate n+means · **A2** raw-log-line existence (reparse rows) + forward returns via a different code path · **A3** excess via independent SQL baseline to 4dp · **A4** live-book second SQL + pnl sign consistency (19 "mismatches" = all $0.00 scratches, 0 real) · **A5** zero duplicate keys in the 83,593-row export · **A6** big-miss MFEs vs raw candles. **All PASS on the final build.** (Three bugs in the self-audit itself were found and fixed during the process — A1's None-filter count, A2's wrong archive paths, A2's data-mutation gating — plus two engine bugs found *by* the audit chain: the lookahead guard and a case-sensitivity regression in the round-3 emoji expansion that briefly dropped BTC-CHOP-GATE to a biased 210-episode subset; run-4 restored n=869/+0.047.)

## 3. The funnel — C-1 (frequency collapse), corrected per verdict C3

Full-frame episodes (blocks need no forward data; the v1 splice that zeroed early weeks is fixed):

| week | blocked eps | trades | block:trade |
|---|---|---|---|
| 2026-09-28 | 423* | 36 | 11.8 |
| 2026-10-05 | 5,480 | 127 | 43.1 |
| 2026-10-12 | 4,285 | 201 | 21.3 |
| 2026-10-19 | 6,387 | 128 | 49.9 |
| 2026-10-26 | 9,442 | 242 | 39.0 |
| 2026-11-02 | 7,112 | 149 | 47.7 |
| 2026-11-09 | 7,960 | 111 | 71.7 |
| 2026-11-16 | 4,953 | 53 | **93.5** |

*recorder starts Oct 4; early weeks also undercounted (pre-Oct-22 capture 33–60% for several gates).

**Interpretation (softened per verdict):** absolute block volume held roughly steady while trades halved twice — *consistent with* upstream starvation rather than gate tightening, but NOT established: the gate mix shifted week-to-week (total-variation 0.12–0.36/wk), a pass-rate proxy fell 4.5%→1.0% over the window, and **the signal-side denominator (emissions per week) was never measured**. Establishing the starvation root cause requires the signal-volume/confluence-expiry/confidence-floor time series (§9).

## 4. Per-gate usefulness (56 gates, cluster-robust)

Method: 60-min episodes; excess = direction-signed fwd4h − cross-sectional market mean (reference baseline); Wilcoxon (naive) + token-clustered and day-clustered t-tests; Bonferroni p<0.0009; class claims require ≥1 cluster p<0.05. Kill rates vs the gate's own tokens' unconditional MFE rates.

**WORKS (2)** — reference baseline, cluster-robust:
- **PUMP-CHAIN-RSI-MAX** n=1,027, −0.190%, p_w<0.0001, p_tok=0.012, p_day=0.005, kill5 8% vs own 5%
- **LONG-RSI-CEILING** n=989, −0.188%, p_w=0.0003, p_tok=0.049, kill5 4% vs own 3%

**BLOCKS-SETUPS (0) under the reference baseline — with a power caveat (§4b).**

**NO-EDGE (27) — the useless blockers, 82.4% of episodes / 85.8% of events:** CONFLUENCE-GATE-BLOCK (3,436, −0.063), CONTINUUM-BLOCK (2,831, +0.016), CONTINUUM-BULL (2,362, −0.033), SHORT-RSI-HARD-FLOOR (2,194, −0.005), LONG-NEUTRAL-CHOP (1,915, +0.059 — still a wash), LONG-NEUTRAL (1,791), SHORT-NEUTRAL (1,637), OVERSOLD-SHORT (1,446), **RR-ENGINE (1,416, −0.048 — new in frame)**, PUMP-CHAIN-SHORT-HIGH (1,236), **BTC-CRASH (1,232, −0.011 — new)**, CTX-GATE (1,107), SHORT-CONTINUUM (1,093), PUMP-CHAIN-HIGH (966), LONG-RSI-BLOCK (921), BTC-CHOP-GATE (869, +0.047 — non-replication holds), SHORT-REGIME-GATE, EXEC-BLOCK, SHORT-BB-DEAD-ZONE/2, LONG-MIDBAND, SHORT-RSI-CEILING, EXEC-RSI-HARD-FLOOR, HOT-SET, VEL-FILTER, LONG-BYPASS-SHORT-BIAS-BLOCK, CHASE-BLOCK (24).

**MIXED/NS (20)** — directionally interesting, not robust: **VOL-GATE-BYPASS** (+0.117, **p_day=0.015**, best harm candidate — but see survivorship note), **SPIKE-FILTER** (−0.157, p_tok=0.008 — probable worker), SLOPE-FILTER (+0.130, cluster-ns, direction consistent across 4 studies), PUMP-CHAIN-VEL (−0.347, p_day=0.045, post-deadband), EXEC-RSI-DETECT-FLOOR, CHOP, LONG-HIGH-70, MAXXED-BLOCK (kill5 extreme, n small), CONFLICT-RESCUE-BLOCK (n=19, +0.410, p_day=0.027 — too small), et al.

### 4b. Power / MDE (verdict C4-power)

MDE ≈ 4.4 × SE(day-means), 80% power: gates n≥400 have **median MDE = 0.227%** (best: SHORT-RSI-HARD-FLOOR/CONTINUUM-BLOCK 0.116%; CONFLUENCE 0.218%). **Therefore BLOCKS-SETUPS=0 means "no gate harms by ≥~0.23%/block detectably" — a +0.15% harmful gate at n=400 would be invisible.** The zero-blocks conclusion is a detection-limit statement, not proof of absence.

### 4c. Baseline sensitivity (verdict C4)

| baseline | WORKS | BLOCKS-SETUPS |
|---|---|---|
| cross-mean (reference) | PUMP-CHAIN-RSI-MAX, LONG-RSI-CEILING | none |
| median | PUMP-CHAIN-RSI-MAX only | none |
| BTC | SHORT-RSI-HARD-FLOOR, LONG-HIGH-70 | SHORT-REGIME-GATE (+0.118), LONG-BYPASS-SHORT-BIAS-BLOCK (+0.639) |

**PUMP-CHAIN-RSI-MAX is the only gate robust across all three baselines.** LONG-RSI-CEILING's WORKS status is cross-mean/median-dependent; under the BTC baseline a different pair flips. All BLOCKS-SETUPS appearances are baseline-specific — disclosed, not claimed.

### 4d. Survivorship (verdict C4)

The pre-history guard dropped 6 gates at 100% (1,772 events) and differentially thinned early-October samples. Restoring Oct 4–20 from the Oct-30 v2 export (own-conclusions computation): **16/52 gates change class; WORKS=2 and BLOCKS-SETUPS=0 hold either way; VOL-GATE-BYPASS's harm-candidate status flips to NO-EDGE** with the early period restored — its harm candidacy is period-dependent and should not be acted on independently of the R1 dollar-closer.

## 5. Missing big moves — C-3 (AGREE)

**164 blocked episodes printed dir-MFE ≥10% in 4h** (0.5% of 34,231 enriched episodes). Top casualties in `exports/nov19_bigmisses.tsv`: SOPH 10-30 LONG +37.9% (fwd +33.3, VOL-GATE-BYPASS); BLUR 10-30 LONG +32.9% (four gates: CONTINUUM-BLOCK, SPIKE-FILTER, LONG-RSI-BLOCK, LONG-NEUTRAL-CHOP); NXPC 11-09 +29.6% (three gates); CASHCAT 11-16 +22.1% (four gates incl. EXEC-BLOCK); IMX 11-13 +28.7% MFE but fwd −2.4% (faded — would need the trail to exit green). Per-gate kill10−own10 differentials: MAXXED-BLOCK extreme (+5.6pp pre-guard, n shrank), PUMP-CHAIN-VEL-SHORT +1.5pp, PUMP-CHAIN-RSI-MIN +1.0pp, SLOPE-FILTER +0.9pp, VOL-GATE-BYPASS +0.5pp (n=1,231). The WORKS gates also kill above their base rate (RSI-MAX kill5 8% vs own 5%) — that is what working costs.

## 6. Robustness (C6 AGREE)

Coalescing 30/120min flips 1–2 of top-20 signs; OOS (Oct 4→Nov 1 vs Nov 1→19) flips 9/20; the WORKS pair holds same-sign both halves. Method lineage: the forward-return engine independently cross-validated in `audit/gate_counterfactual_verify.md`, now with the §1 guard.

## 7. The answer (corrected)

1. **Useful (keep):** PUMP-CHAIN-RSI-MAX — the only gate robust to baseline choice; LONG-RSI-CEILING (reference/median baselines); probable workers pending Bonferroni: SPIKE-FILTER, PUMP-CHAIN-VEL (post-deadband).
2. **Useless blockers:** the 27 no-edge gates — **82.4% of episode volume** — neither help nor hurt per block. Removal case = efficiency/functional redundancy (the Oct-30 audit put the CONTINUUM pair at solo 13–17%), NOT recovered PnL; blocked ≈ market means removal changes flow at ≈ zero markout cost. Nov-6-queue logic extends; decisions need the R1 dollar-closer.
3. **Not shown to be the cause of unprofitability:** blocked ≈ passed ≈ market (standing p≈0.5); the detection limit (§4b) means small harm can't be excluded, but nothing ≥0.23%/block exists. Long WR 46.4%/−$6.89 is entry+exit-engine quality the gates neither created nor prevented.
4. **Harm candidates — watch, don't act:** VOL-GATE-BYPASS (p_day=0.015 but period-dependent per §4d), SLOPE-FILTER (direction-consistent, 4 studies, cluster-ns), MAXXED-BLOCK (tail-kill, n=44), CONFLICT-RESCUE-BLOCK (n=19).
5. **Concrete misses exist** (164 episodes ≥10% MFE; three four-gate cases) but do not generalize; tail questions need the R1 extended closer ($-denominated, still unbuilt).

## 8. What this cannot settle

4h candle markouts ≠ realized PnL under the live exit stack (R1); harm < MDE (0.23% at n≥400) is undetectable at this window; the starvation root cause needs the signal-side denominator (§3/§9); db-only Oct 4–30 raw lines are deleted (rotator retains going forward); 30d candle retention makes expired-window values non-regenerable (exports are the snapshot of record).

## 9. Next analysis if T wants the frequency-collapse root cause

Signal emissions/week (the missing denominator), confluence-expiry rates/week (expiry_shadow has 63k events), confidence-floor rejection counts/week — all derivable from existing data; none collected in this study.

## 10. Correction ledger (v1 → this revision, per the own-conclusions verdict)

| # | v1 defect | correction |
|---|---|---|
| 1 | Two-run splice: §3 funnel and §5 kill-differentials cited pre-guard numbers the committed engine couldn't produce | funnel rebuilt from full frame in-engine; kill differentials re-sourced from run-4 .out (e.g. RSI-MIN +1.0→+6.7pp class of fixes) |
| 2 | "~99% of block volume" | **82.4% episodes / 85.8% events** (95% only counting all non-WORKS) |
| 3 | RR-ENGINE (3,402 events/1,415 eps) invisible; capture audit hid gates behind r<20 | emoji set expanded (+🎯⏱️🛡️🚨⚠️🔄🗑️) with gate/marker classification; 47→56 gates; capture audit lists all 54 overlap gates |
| 4 | Undisclosed guard survivorship | §4d: 6 gates 100% dropped (1,772 events); 16/52 class changes on early-period restore; WORKS=2/BLOCKS=0 stable; VOL-GATE-BYPASS flips |
| 5 | Undisclosed baseline sensitivity | §4c table: only RSI-MAX robust across all three baselines |
| 6 | BLOCKS-SETUPS=0 stated without power | §4b: median MDE 0.227% (n≥400); +0.15% harm undetectable |
| 7 | C3 "starvation is upstream" overclaimed | §3 softened: consistent-not-proven; gate-mix TV 0.12–0.36/wk; pass-proxy 4.5%→1.0%; early-week undercount; signal denominator unmeasured |
| 8 | C7 "mass prune at 21:55 / computed from complete data / 11-token fingerprint" | §1 retracted: routine incremental 30d retention (journal: 514 prunes, ≤284 rows); history always capped → all 24,699 were lookahead at run; fingerprint artifact + now unverifiable; guard correct, drop count reproduces |
| 9 | — | New: case-sensitivity regression caught by run-3 diff (BTC-CHOP 868→210 biased subset) fixed in run 4 |

## 11. Paper trail

`analysis/gate_usefulness_deepdive_2026-11-19.py` (engine, all fixes inline with provenance comments) · `.out` (run-4 verbatim) · `analysis/gate_usefulness_selfaudit_2026-11-19.py` + `.md` (6/6 PASS) · `exports/nov19_gate_events.tsv` (83,593 rows — snapshot of record), `nov19_gate_summary.tsv` (cluster p + MDE + 3-baseline means), `nov19_weekly_funnel.tsv` (full-frame), `nov19_bigmisses.tsv` (164) · verdict `brain/verdicts/2026-11-19-gate-usefulness-own-conclusions.md` · auditor working code `/tmp/oc_nov19/`.
Reproduce: `python3 analysis/gate_usefulness_deepdive_2026-11-19.py && python3 analysis/gate_usefulness_selfaudit_2026-11-19.py`. Known limits: §8.
