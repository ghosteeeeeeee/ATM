# Independent Adversarial Verification — Gate Counterfactual Audit (2026-10-08)

**Auditor:** independent verification pass (mimo agent), everything re-derived from raw artifacts.
**Artifacts under audit:** `analysis/gate_counterfactual_audit_2026-10-08.py` / `.out`
**My code (independent re-implementation, written from scratch):** `audit/gc_verify_scripts/`
(`parse_events.py` → `engine.py` → `stats_a-d.py`, plus `repro_audit.py` which re-runs *both* audit versions' regexes verbatim). Intermediate data: `/tmp/gaudit/`.
**Window:** pipeline.log 2026-10-02 20:24 → 2026-10-08 23:01 UTC · candles.db `candles_5m` · brain.trades (PostgreSQL).

> **VERSION STATUS:** v1 (48,287 lines / 38 gates / 5,427 episodes, 23:09 build) → v2 (parser-fixed, UNSIGNED baseline — the intermediate whose numbers were briefly relayed) → **v3 = the on-disk artifact (script 23:30, .out 23:31): 74,806 lines / 49 gate names / 8,061 episodes / 7,818 covered, direction-signed baseline at both call sites. v3 is CURRENT and is what §A verifies.** My original v1 kills caused the v2 parser fix and the v3 baseline fix; §A.3 confirms v3 cross-validates against my independent implementation, and §A.9 verifies the new pooled/MWU claims and rules on the three explicit determinations. §B retains the v1 record for provenance.

---

# §A. VERIFICATION AGAINST v3 (CURRENT ON-DISK AUDIT)

## A.0 Version trail — the relayed numbers were v2-intermediate, v3 on disk is correct

The second update relayed (as "v2") the numbers CONFLUENCE-GATE-BLOCK "+0.193, p=0.104", PENALTY-BLOCK "+0.837, p=0.046 (blocks-winners direction)", SLOPE-FILTER "+1.768, p=0.011", CONTINUUM-BULL "+0.225, p=0.358". **Those are v2-intermediate values (fixed parser, OLD unsigned baseline) and do not appear in the current on-disk `.out` (v3, mtime 23:31).** v3 says:

| gate | relayed v2-intermediate | on-disk v3 `.out` (23:31) | my independent direction-signed number |
|---|---|---|---|
| CONFLUENCE-GATE-BLOCK | 856 eps, **+0.193, p=0.104** | 856 eps, **−0.097, p=0.011** | 874 eps, −0.058, p=0.020 |
| PENALTY-BLOCK | 153 eps, **+0.837, p=0.046** | 154 eps, **+0.316, p=0.336** | 155 eps, +0.306, p=0.364 |
| SLOPE-FILTER | 110 eps, **+1.768, p=0.011** | 110 eps, **+0.544, p=0.008** | 112 eps, +0.542, p=0.007 |
| CONTINUUM-BULL | 245 eps, **+0.225, p=0.358** | 246 eps, **−0.097, p=0.993** | 246 eps, −0.081, p=0.862 |

The v2 values ≈ my unsigned-baseline numbers (+0.263 / +0.829 / +1.841 / +0.205) — i.e. they still carried the short-drift bias. The on-disk v3 `.out` was regenerated with the direction-sign baseline fix (script lines 228–235) and matches my direction-signed numbers almost exactly. **The v3 artifact is the citable one.**

## A.1 Claim 1 (counts) — CORRECTED, now reconciled exactly

| quantity | v3 | my independent parse | reconciliation |
|---|---|---|---|
| raw block lines | 74,806 | 75,824 | **1,018 = 819 one-char-token "W" lines (v3 regex still `[A-Z0-9]{2,12}`) + 196 lines of 6 gates v3 still misses + ~41 RR-ENGINE scope naming** |
| gate names | 49 | 55 | v3 misses CONF-FILTER-PRESERVE (83 lines), CONFLICT-RESCUE-BLOCK (52, 🔄 emoji absent), LOSERS-BLOCK (42, 🗑️ emoji absent), PRESERVE-MERGE/LOCK/CHOP-BLOCK (8/6/5, colon-glued `TOK:LONG` format) |
| episodes (60-min gap) | 8,061 | 8,226 | **165 = ~84 W-token episodes + 74 episodes of the 6 missing gates + ~7 misc — exact** |
| episodes w/ coverage | 7,818 | 7,979 | same deltas |

Per-gate line counts match to **exactly the W-line count** on every shared gate (CONFLUENCE 236 = its W-lines; LONG-NEUTRAL 187 = its W-lines; SHORT-CONTINUUM 39 = its W-lines; …). v3's soft-multiplier exclusions are correct: TIDE/RR PENALTY/SLOPE-OVERRIDE/OPP-PENALTY multipliers are out, RR HARD BLOCK / "denied" / "skip" blocks are in. **The v3 parser is sound; remaining loss ≈ 1.4 % of lines, non-systematic — no verdict affected** (the one substantive residual: CONF-FILTER-PRESERVE, 52 eps, which my run measures as a genuine WORKS gate: direction-signed −0.67, p=0.006, significant under all five baselines).

## A.2 Claim 2 (method) — CONFIRMED, fixes verified correct

v3 adopted the direction-signed baseline: `excess = sgn × (raw_fwd − market_mean)`, applied at both call sites (episodes, lines 228–235; passed trades, lines 290–292). I verified the code — algebraically identical to my `exn_4h` field. Two cosmetic leftovers: docstring line 14 and footnote line 65 still describe the OLD formula ("signed − market"); and the in-code comment "market fell −0.20 %/4h" is at the aggressive end of a composition-dependent quantity (my measurements: −0.149 %/4h over the 84 episode-token set, −0.047 %/4h over the top-gate token set, **+0.105 %/4h over all 182 tokens** — the drift level, hence every excess level, moves with cross-section composition; gate-level effects move ≤0.10 %).

## A.3 Claim 2/4 — CROSS-VALIDATION: v3 table vs my independent engine

Joining all 39 machine-parseable rows of the v3 per-gate table with my independently computed direction-signed numbers: **zero gates differ by more than 0.10 %; most agree within ±0.02 %; Wilcoxon p-values nearly identical (exact to 3 decimals on PHANTOM-WRITE 0.306/0.306, SHORT-RSI-CEILING 0.635/0.635, EXEC-BLOCK 0.850/0.850, CHASE-BLOCK 0.249/0.249, HOT-SET 0.557/0.557; within ±0.005 elsewhere: LONG-RSI-BLOCK 0.010/0.009, SHORT-RSI-FLOOR 0.041/0.042, SLOPE-FILTER 0.008/0.007, PUMP-CHAIN-VEL-SHORT 0.070/0.070, BTC-CHOP-GATE 0.000/0.000, …).** Two fully separate implementations (my per-gate explicit-pattern parser + numpy engine vs their shape-classifier + in-loop baseline) now agree on the entire table. Largest residual deltas: SPIKE-FILTER −0.095, VOL-GATE-BYPASS −0.067 (sign differs, both p>0.28, n≈186), CONFLUENCE-GATE-BLOCK −0.039 — all explained by W-token episodes and cross-section composition.

## A.4 Claim 3 (headline) — CONFIRMED against v3

- Passed side: v3 **+0.188 / +0.032** (mean/med ex4h, direction-signed) vs my **+0.186 / +0.046** ✓.
- Blocked side (v3 scope, dedup by token+dir+bucket): **+0.006 mean / −0.016 med** (my compute on v3's 49-gate set).
- The pooled/MWU numbers quoted in the v3 update are **not present in the on-disk `.out`** (the script still computes no MWU despite docstring line 17) — verified ad hoc in §A.9: all reproduce.
- **Headline verdict stands unchanged: statistically indeterminate, and structurally underpowered** (passed-side bootstrap CI ±0.37 %; only selection ≳0.4 %/trade would be detectable). The attack-H caveats also stand: 78 % of passed trades had a same-token+direction blocked episode within ±30 min; passed = 82 % LONG vs blocked = 50 % LONG.

## A.5 Claim 4 — per-gate verdicts as they now stand on the v3 artifact

| gate | v3 eps | v3 ex4h (direction-signed) | v3 p | final verdict |
|---|---|---|---|---|
| SHORT-CONTINUUM | 1,054 | −0.028 | 0.016 | NO EDGE (statistically detectable, economically zero: ≤0.03 %/trade) |
| CONFLUENCE-GATE-BLOCK | 856 | −0.097 | 0.011 | NO ECONOMIC EDGE (significant but −0.1 %; OOS flips +0.10/−0.20) |
| LONG-RSI-BLOCK | 627 | −0.028 | 0.010 | NO ECONOMIC EDGE (rank-skew; permutation p=0.685 on mean) |
| LONG-NEUTRAL | 549 | +0.038 | 0.465 | NO EDGE ✓ |
| CONTINUUM-BLOCK | 513 | +0.054 | 0.241 | NO EDGE ✓ (deployed Oct 3) |
| RR-ENGINE (hard blocks) | 406 | +0.155 | 0.568 | NO EDGE (runner-kill 31.5 % vs market 22.5 % — keep watching) |
| PUMP-CHAIN-SHORT-RSI-MIN | 401 | −0.048 | 0.673 | NO EDGE ✓ |
| SHORT-NEUTRAL | 382 | −0.166 | 0.397 | NO EDGE ✓ |
| HALL-SHAME | 288 | +0.026 | 0.550 | NO EDGE ✓ robust |
| LONG-RSI-CEILING | 251 | +0.175 | 0.430 | NO EDGE ✓ |
| CONTINUUM-BULL | 246 | −0.097 | 0.993 | NO EDGE ✓ (deployed Oct 5) |
| BTC-CHOP-GATE | 238 | **−0.381** | **0.000** | **WORKS ✓** (only robust verdict; OOS halves −0.61/+0.16 still flip) |
| SHORT-RSI-FLOOR | 211 | +0.213 | 0.041 | WEAK "BLOCKS WINNERS" — not Bonferroni-significant (α≈0.0011 over 46 gates); halves same-sign (+0.01/+0.28); still code-change-confounded (2bb04d9e mid-window) |
| VOL-GATE-BYPASS | 186 | −0.054 | 0.283 | NO EDGE ✓ (deployed Oct 6) |
| PUMP-CHAIN-RSI-MAX | 184 | +0.172 | 0.947 | NO EDGE ✓ |
| OVERSOLD-SHORT | 178 | **+0.037** | **0.509** | **NO EDGE — v1 "blocks winners (+1.176, p<0.001)" is retracted by v3 itself** |
| CTX-GATE | 163 | −0.013 | 0.598 | NO EDGE ✓ |
| PENALTY-BLOCK | 154 | +0.316 | 0.336 | NO EDGE (the v2-intermediate "+0.837 blocks-winners" was the unsigned-baseline artifact; deployed Oct 6) |
| BTC-CRASH | 146 | +0.335 | 0.392 | NO EDGE ✓ (only 15 solo eps; overlap 1.7) |
| PUMP-CHAIN-SHORT-HIGH | 124 | −0.228 | 0.763 | NO EDGE ✓ |
| SPIKE-FILTER | 111 | +0.265 | 0.309 | NO EDGE ✓ |
| SLOPE-FILTER | 110 | **+0.544** | **0.008** | **BLOCKS WINNERS (strongest candidate)** — significant under all 5 baselines (§B N4), monotone 30m→8h, runner-kill 59.1 % vs direction-matched market 23.6 %. Still not Bonferroni-significant in isolation; needs longer-window confirmation before acting |
| PUMP-CHAIN-VEL-SHORT | 59 | +0.358 | 0.070 | NO EDGE (v1 claim dead: not significant under corrected baseline) |
| CHOP | 30 | −0.189 | 0.524 | NO EDGE — v1 "works" retracted |
| CHASE-BLOCK | 37 | −0.511 | 0.249 | no verdict (n.s., n=37) |
| CONF-FILTER-PRESERVE | *absent from v3* | (−0.67, p=0.006, my run) | — | **v3 still misses this WORKS gate** (colon-glued format) |

Bonferroni note: v3's footer "VERDICT KEY: ex-mean > 0 → BLOCKS WINNERS" applies no significance requirement; over 46 gates α≈0.0011, so under strict family-wise control **no positive verdict survives** (SLOPE-FILTER p=0.008 and SHORT-RSI-FLOOR p=0.041 fail; BTC-CHOP-GATE's negative p<0.001 passes). The docstring's promised Bonferroni adjustment is not implemented.

## A.6 Claim 5 (MFE) — unchanged by v3, still CORRECTED

v3 did not touch the market MFE reference. My direction-matched reference stands: **market LONG MFE(4h) 1.42 % mean, 22.0 % ≥2 %; SHORT 1.52 % / 23.6 %** (their claimed "1.51 % / 16 %" matches neither). v3's per-gate mfe>2 % column cross-validates with mine (SLOPE-FILTER 59.1 vs my 59.8; SHORT-RSI-FLOOR 38.4/38.4; PUMP-CHAIN-RSI-MAX 37.5/37.5; HALL-SHAME 28.8/28.8). Corrected "runner-kill" excesses: PUMP-CHAIN-RSI-MAX +15.5 pts, SHORT-RSI-FLOOR +14.8, PUMP-CHAIN-SHORT-HIGH +12.7, **SLOPE-FILTER +36.2**, RR-ENGINE +9.4, HALL-SHAME only +6.3 (their +12.7 was inflated by the 16 % reference).

## A.7 Robustness verdicts (attacks C/D/F/I/J) — unchanged, now on v3 numbers

- **D (baseline):** fixed in v3; my 5-baseline matrix (§B.3) remains the robustness reference. Verdicts that are robust under v3: all NO-EDGE calls, BTC-CHOP-GATE WORKS, SLOPE-FILTER harmful-direction. Baseline-dependent (do not act): CONFLUENCE-GATE-BLOCK sign (+0.29 unsigned vs −0.10 signed), CONTINUUM-BLOCK, PENALTY-BLOCK.
- **C (horizons):** no 30m-vs-4h sign reversal under the corrected baseline anywhere; OVERSOLD-SHORT flat ≈0 at all horizons; BTC-CHOP monotone −0.04/−0.10/−0.41/−0.45.
- **F (coalescing):** 30/60/120-min gaps leave every verdict unchanged (headline +0.119/+0.158/+0.160 unsigned; neutral −0.011/+0.004/+0.009).
- **I (ties):** zero ties/zeros in all excess series; Wilcoxon valid; permutation cross-checks agree.
- **J (regime):** v3 halves flip sign for **10 of 22** gates with ≥10 eps per half (v1: 14/22) — improved by the baseline fix but still ~45 %; mid-window gate-code changes (SHORT_CONTINUUM_SCORE_MAX 40→60, SHORT-RSI-FLOOR override restore, LONG RSI 70→85, SHORT_RSI_HARD_FLOOR 25→45) remain unmodelled. **No per-gate verdict from this 6-day window is out-of-sample evidence.**
- **A/B/E/G:** unchanged — timestamps UTC-verified; entry rule lookahead-free (lag-1 moves ≤0.06 %); solo counts now agree (v3 SC solo 693 vs mine 674; LONG-NEUTRAL 247 vs 252 — the overlap correction landed); coverage: TESTTOKEN correctly censored, GRASS feed broken, XAI 160-min gap — no verdict affected.

## A.8 What remains wrong in v3 (residual findings)

1. Token "W" still dropped (~864 lines / ~84 eps) — regex `[A-Z0-9]{2,12}`.
2. CONF-FILTER-PRESERVE still missed (colon-glued `TOK:LONG`); my run says it **works** (−0.67, p=0.006). CONFLICT-RESCUE-BLOCK (🔄), LOSERS-BLOCK (🗑️), PRESERVE-MERGE/LOCK/CHOP-BLOCK still missed (~110 lines).
3. Direction-level blocks remain unverifiable/unlisted: WARNING "BTC momentum blocks SHORT" (1,348 lines), DIRECTION-LOCK (425), VOL-FLOOR (1,247), VOL-GATE-v2 SKIP (724), HOTSET-FILTER direction-less variant (205).
4. Docstring + table footnote still document the old baseline; VERDICT KEY lacks significance requirement; the on-disk `.out` still contains no pooled/MWU/Bonferroni block (those were computed ad hoc — verified by me in §A.9).
5. Claim-5 MFE market reference (16 %) still wrong upstream in whatever produced that claim.
6. All §B methodological findings stand: 78 % passed-trade toggle rate, 82-vs-50 % direction mix, single-regime window, mid-window code changes.

## A.9 Pooled-statistics verification + rulings on the three explicit determinations

### A.9.1 Pooled v3 numbers — independently reproduced

Their ad-hoc pooled figures (not in the `.out`): blocked n=7,818 mean +0.012 % med −0.010 %; passed n=130 mean +0.188 % med +0.032 %; MWU two-sided p=0.518, one-sided p=0.259, permutation p≈0.139. My reproduction on v3 scope (49 gate names, 1-char tokens excluded, direction-signed excess):

| quantity | their v3 | mine (independent) |
|---|---|---|
| blocked n (non-dedup) | 7,818 | 7,815 |
| blocked mean / med | +0.012 / −0.010 | **+0.0114 / −0.0178** |
| passed mean / med | +0.188 / +0.032 | **+0.186 / +0.046** |
| MWU two-sided | 0.518 | **0.5285** (non-dedup) / **0.5162** (dedup by token+dir+bucket, n=6,603) |
| MWU one-sided (blocked < passed) | 0.259 | **0.2642 / 0.2581** |
| label-permutation, diff of means, one-sided | ≈0.139 | **0.1438** (20k perms; two-sided 0.2907) |

All reproduce within Monte-Carlo/implementation noise. Extra views, all null: Welch t p=0.228; Cliff's δ −0.035; blocked dedup mean −0.002 %. **The pooled passed≈blocked null is CONFIRMED** — with the standing power caveat (passed-side CI ±0.37 %/trade; only selection ≳0.4 % detectable) and the standing selection caveats (78 % toggle rate within ±30 min; 82 % vs 50 % LONG mix; SHORT-side-only hint p=0.08 on n=24).

### A.9.2 Ruling on determination (1): "BTC-CHOP-GATE is the sole robust edge gate" — **CONFIRMED, with two footnotes**

- v3: −0.381, p<0.0001 (their claim). My independent value: −0.405, Wilcoxon **p=1.14e-04** — same order; passes Bonferroni over 46 gates (α≈0.0011) either way. **It is the only gate in the v3 table that survives family-wise correction in any direction.**
- Robustness (my 5-baseline matrix): significant negative under **all five** baselines (audit −0.530*, direction-signed −0.405*, median-baseline −0.377*, BTC-baseline −0.517*, raw −0.616*); horizon-monotone (−0.04/−0.10/−0.41/−0.45 at 30m/1h/4h/8h); survives 5-min entry lag (−0.51), solo-only (−0.99 audit / −0.66 signed), and all coalescing gaps (−0.83/−0.53/−0.47 at 30/60/120 min). Runner-kill 7.5 % vs market 22.7 % — it blocks almost nothing that runs.
- Footnote 1 — OOS: v3's own halves flip (−0.613 / +0.163); per-day mixed. The verdict is a window-average property driven by the Oct 2–5 chop regime.
- Footnote 2 — "sole" holds **within v3's gate table**. Two caveats: (a) three other gates are nominally negative but economically zero and OOS-unstable (CONFLUENCE −0.097 p=0.011, LONG-RSI-BLOCK −0.028 p=0.010, SHORT-CONTINUUM −0.028 p=0.016 — all ≤0.10 %/trade); (b) the gate v3 still misses, **CONF-FILTER-PRESERVE (52 eps), is a second "works" candidate** in my run (−0.67, p=0.006, negative under all five baselines) — it fails Bonferroni too, but it belongs in the next round.

### A.9.3 Ruling on determination (2): "the pooled passed≈blocked null" — **CONFIRMED** (see A.9.1)

### A.9.4 Ruling on determination (3): "SLOPE-FILTER is the sole nominal blocks-winners gate" — **CONFIRMED as strongest / KILLED as sole**

Census of nominally significant (Wilcoxon p<0.05) direction-signed excess across my 55-gate universe:

- **Positive (blocks-winners direction): SLOPE-FILTER (+0.542, p=0.007, n=112) AND SHORT-RSI-FLOOR (+0.216, p=0.042, n=211).** SLOPE-FILTER is therefore the sole p<0.01 positive gate but **not** the sole nominal one — SHORT-RSI-FLOOR is also nominally positive (v3's own table: +0.213, p=0.041), with the caveats already logged (fails Bonferroni; halves same-sign +0.01/+0.28 but the gate's code changed mid-window, commit 2bb04d9e; n1=50/n2=161).
- Negative (works direction): BTC-CHOP-GATE (p=1.1e-4), CONF-FILTER-PRESERVE (p=0.006, absent from v3), LONG-RSI-BLOCK (p=0.009), CONFLUENCE (p=0.020), SHORT-CONTINUUM (p=0.019), PUMP-CHAIN-RSI-MIN (p=0.046, n=39) — only BTC-CHOP-GATE survives Bonferroni and only it has non-trivial magnitude.
- SLOPE-FILTER's case in full: significant under **all five** baselines (audit +1.841*, signed +0.542*, median +0.471*, BTC +1.028*, raw +1.191*); horizon-consistent (+0.60/+1.75/+1.95 audit-formula at 30m/1h/8h, signed 4h +0.54); OOS halves **both positive** (+0.44 / +0.67 — one of the few gates that does not flip); runner-kill **59.1 % vs direction-matched market 23.6 %** (the largest in the stack); it blocks shorts against a +0.05 %/5m slope, i.e. it fades exactly the mean-reversion shorts that kept paying in this window. Standing caveats: n=110, single regime, p=0.008 > Bonferroni α≈0.0011, and it is a momentum-conditioned gate whose "harm" is regime-defined (in a genuine uptrend its blocks should be correct — its own design assumption). **Verdict: strongest blocks-winners candidate; confirm across ≥4 weeks before touching it.**

---

# §B. RETAINED v1 RECORD (superseded, kept for provenance)

**v1 bottom line (23:09 build) — the audit this section killed:**

1. v1's arithmetic was exactly reproducible (48,287 / 38 / 5,427 / 83 tokens) but its substring pre-filter (`'BLOCKED' or 'blocked' in line`) missed **27,537 real block lines / ~17 gates** — including CONFLUENCE-GATE-BLOCK (12,558 lines, the #2 gate), CONTINUUM-BLOCK ("blocking"), CONTINUUM-BULL ("denied"), RR-ENGINE "RR HARD BLOCK" (no D), VOL-GATE-BYPASS ("denied"), PENALTY-BLOCK, SLOPE-FILTER ("skip"), CHASE-BLOCK, CONF-FILTER-PRESERVE, token "W" (864 lines), and all direction-level gates.
2. v1's excess formula was asymmetric for shorts (`signed − market` for both directions) — in this falling window every SHORT episode got ~+0.30 % free excess, manufacturing the three "BLOCKS WINNERS" verdicts and most OOS flips.
3. v1 headline (passed +0.310/+0.018 vs blocked +0.169/−0.093, claimed "MWU p=0.45" — a number that appeared nowhere in its artifacts) → my v1 reproduction: passed +0.308/+0.022, blocked +0.159/−0.096, MWU p=0.499, Cliff's δ −0.035 — indeterminate confirmed, but underpowered by construction.
4. v1 kills: OVERSOLD-SHORT (+1.176→neutral +0.045, p=0.46), PUMP-CHAIN-VEL-SHORT (+1.709→+0.37, p=0.07), SHORT-RSI-FLOOR (+1.153, own p=0.083 never significant→neutral +0.216), CHOP "works" (−0.909→neutral −0.18, p=0.57). v1 survivors: BTC-CHOP-GATE works (robust under all 5 baselines/horizons/lag/solo); nine NO-EDGE verdicts (economically zero under every baseline); OOS instability (14/22 flips); MFE reference corrected to 22.0 %/23.6 %; new harmful-gate candidate SLOPE-FILTER; new WORKS-gate CONF-FILTER-PRESERVE; 78 % passed-trade toggle rate; passed 82 % LONG vs blocked 50 %.
5. v1 methodological findings (all still valid): episode coalescing robust at 30/60/120 min; entry rule lookahead-free; timestamps UTC; ties moot; coverage gaps (GRASS broken feed, XAI 160-min gap, TESTTOKEN dev noise); EXEC-RSI-HARD-FLOOR misnamed (mostly stale-candle fail-closed); baseline composition moves drift level from −0.15 to +0.11 %/4h.

**Full v1 per-gate, 5-baseline, solo, OOS, coverage tables:** unchanged in the earlier revision of this file's structure; the authoritative current numbers are §A + `stats_b/c/d.py` outputs in `/tmp/gaudit/`.

---

## Recommendations (updated for v3)

1. **v3 is now trustworthy arithmetic** — cross-validated gate-by-gate against an independent implementation (max Δ 0.10 %). Its per-gate table may be cited; the relayed intermediate numbers may not.
2. Do not remove or unblock any gate on this window's evidence. Only **BTC-CHOP-GATE (works)** and **SLOPE-FILTER (harmful-direction)** are worth carrying forward as hypotheses; both need ≥4 weeks spanning up- and down-regimes and code-version-aware splits.
3. Finish v3's job: fix the `[A-Z0-9]{2,12}` token regex (W), handle colon-glued `TOK:LONG` and 🔄/🗑️ emoji, decide explicitly how direction-level gates (VOL-FLOOR, DIRECTION-LOCK, WARNING) will be evaluated or declared out of scope, update the docstring/footnote to the direction-signed formula, implement the promised MWU + Bonferroni, and correct the MFE market reference (22.0 %/23.6 %, not 16 %).
4. Treat the 78 % toggle rate as a design finding: gates firing on continuous thresholds flip minute-to-minute; future audits should evaluate threshold *margins* (e.g., blocked-at-RSI-39.9 vs passed-at-40.1), not just gate on/off counterfactuals.
5. Remove TESTTOKEN log noise; fix the GRASS candle feed.

*Reproduction: `python3 audit/gc_verify_scripts/repro_audit.py` (v1 parse, exact) · import the audit module (v3) and call `parse_log()` for the v3 census · `parse_events.py` → `engine.py` → `stats_a-d.py` (my pipeline; ~10 min; scipy/numpy + psql access).*
