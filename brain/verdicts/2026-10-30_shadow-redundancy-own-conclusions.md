# Independent Audit — Shadow Redundancy Deep Dive (2026-10-30)

**Auditor:** independent (own-conclusions) · **Date:** 2026-10-30 · **Report under audit:** `analysis/2026-10-30_shadow-redundancy-deepdive.md`
**Method:** read every file from scratch; wrote an independent parser/engine in `/tmp/audit/` (build_features.py + analyze*.py) that imports NOTHING from the audited engine; recomputed from raw DBs (gate_shadow.db, expiry_shadow.db, t5_shadow.db, candles.db, PostgreSQL brain.trades) and reparsed 453MB of raw pipeline.log with the recorder's own regexes.

**Headline of this audit:** the audited engine's arithmetic is faithful — I reproduce its per-gate table from its own export to ±0.0001% and the exports verify 20/20 against raw candles. The problems are in **inference and framing**, not in the arithmetic: no clustering correction anywhere (p-values are pseudo-replicated), the runner-kill baseline is mismatched, F3's mechanism claim is wrong for the actual population it claims about, the first-seen column is a recorder artifact for ~15 gates, and F5's n is inflated 13× by trade reuse.

Key independent numbers (all recomputed by me):
- Export verified: 20/20 rows f4h/MFE/excess match raw candles; per-event excess vs export over all 49,904 events: mean|Δ|=8.6e-5 (export is 4-dp rounded). Episodes computed from the export alone reproduce the report exactly (CONTINUUM-BLOCK −0.0332, PUMP-CHAIN-RSI-MAX −0.1272, BTC-CHOP +0.1032, SLOPE +0.2437, PRESERVE −0.0273).
- Engine attacks: entry rule has NO lookahead (entry = next 5m candle open after the log line; max drift 6 min over all 50k events); SHORT sign convention is correct; self-inclusion in the market baseline is negligible (excl-self variant changes means <0.001pp).
- Market-wide MFE≥2% in 4h: **long 25.4% / short 21.9%** (the "~22%" claim ≈ the short side).
- Cluster-robust inference (t over per-token means / per-day means) is far weaker than the Wilcoxon p the report uses, for every significant claim.
- Recorder fidelity vs raw log (Oct 10 20:49 → Oct 30, deduped with recorder's own rules): log=47,548 vs DB=39,437. Missed: **Oct 11: 1,981 (DB: 0); Oct 12: 2,517; plus ~4,600 more Oct 13–22** because the compactor-form regex fix (`:?`) shipped ~Oct 22 (code comment: "previously ZERO compactor block lines matched"). Oct 23–29 recorded **exactly** (0 diff). `pipeline.log.*.gz` archives no longer exist → Oct 4–10 events (~10.3k) cannot be re-verified against raw logs.
- Live book (PostgreSQL, closed, paper='f', Oct 4–30): 637–638 trades, WR 44%, net −$5.35, median notional $11.10.

=== INDEPENDENT VERDICT ===
Claim: F1
Verdict: PARTIAL
Evidence: Replicated: n=1,002–1,010 episodes, excess_4h **−0.130%** (report −0.127), Wilcoxon p=3.5e-8, solo **80.8%** (±10min; 88.9% at ±5min, 73.3% at ±20min — robust), OOS halves −0.028/−0.231 (same sign). BUT: (i) significance is test-dependent — ordinary t-test p=**0.069**, day-clustered t (n=25 day means) p=**0.069**, token-clustered t (47 tokens) p=0.012; the p<0.0001 comes from Wilcoxon/sign tests on 1,002 episodes that are neither independent across tokens nor across days (worst days 10-25 −1.05, 10-29 −0.74; best +0.54). (ii) Baseline-sensitive: cross-mean −0.130, cross-**median** −0.046, **BTC baseline −0.010** (≈zero). The "edge" is mostly "blocked pump-chains underperformed the right-skewed cross-sectional mean." (iii) Runner-kill baseline mismatched: observed MFE≥2% share 34.7% (episode) / 37.2% (event) vs the claimed "~22% market" — but market-wide LONG runner share is 25.4% and the gate's **own tokens' unconditional** rates average **32.1%** (CHIP 51.7%, ALT 45.4%, GRASS 51.3%...). The honest runner-kill differential is ≈ +5pp, not +12pp. (iv) Effect concentrated in second half (half-1 ≈ −0.03, economically zero); 92% of events captured in log (good).
Confidence: HIGH
Notes: Direction (protective, blocked longs underperform) is real and the gate is the best candidate in the stack; "durable edge, p<0.0001, runner-kill 34.2 vs 22" overstates statistical strength and mismatches the runner baseline. Fix the baseline (per-token) and report cluster-robust p before calling it durable.

=== INDEPENDENT VERDICT ===
Claim: F2
Verdict: PARTIAL
Evidence: Economic-zero is robust: CONTINUUM-BLOCK n=1,630 mean −0.016→−0.033 (episode-construction dependent at the live edge), CONTINUUM-BULL +0.004, PRESERVE-SPIKE-BLOCK −0.027; cluster-robust p all >0.1; t-tests all >0.5; sign stable across 30/60/120-min coalescing (BULL flips to −0.005 at 120min — i.e., pure noise). Functional redundancy: CONTINUUM-BLOCK solo **17.73%**, CONTINUUM-BULL **18.55%** (2.48% vs raw events!) — robustly low. But **PRESERVE-SPIKE-BLOCK solo = 24.66%**, i.e., 0.34pp below the <25% cutoff: at a ±5min solo window it is 26.9% and it is NOT functionally redundant; at ±20min 19.7%. Also the "economically redundant" class mixes a statistical gate (p≥Bonferroni 0.001) with an economic one: CONTINUUM-BULL at 30-min coalescing has p=0.0006 < Bonferroni → the machinery would label a +0.0003% effect "HAS EDGE". "Removes changes little flow": agree for BULL/BLOCK (81–82% co-blocked, 15.5–2.5% solo vs raw events); PSB removal would pass ~56 episodes/26d.
Confidence: HIGH
Notes: Conclusion (three gates can go at ~zero cost) is supported; the "FULLY REDUNDANT" label is knife-edge for PSB and the p-threshold criterion is arbitrary — present these as "no detectable economic effect, solo≤19-25%" rather than a bright-line class.

=== INDEPENDENT VERDICT ===
Claim: F3
Verdict: PARTIAL
Evidence: Recomputed all 28k expiry events from candles (stored excess is not reproducible: 4,782/27,729 rows differ >0.01pp from current candles, 201 differ >1pp — e.g., SAGA 09-25 stored −29.35% vs fresh −3.88%). Fresh band means: 60-69 **−0.211** (n=772) ✓, 70-79 −0.037 (13,107) ✓, 80-89 −0.018 (13,922) ~✓ (report −0.024), **90+ +0.142 (n=84)** — report says −0.019; the "protects at EVERY band" fails at 90+ (noise-level either way). Two deeper problems: (i) **mechanism misattributed** — splitting by source count: conf≥80 **single-source** excess = **+0.0016%** (n≈14k; 80-89 single EXPIRED −0.012, single SKIPPED **+0.048**); the negative band means are carried by MULTI-source rows (80-89 multi: −0.08/−0.21; overall multi −0.132). "The high-confidence singles the confluence wall kills underperform market at every band" is arithmetically false for the singles themselves. (ii) **No clustering correction**: token-clustered p = 0.11/0.67/0.07/0.32 (60-69/70-79/80-89/90+), day-clustered p all >0.23; effective n ≈ 354/2,820/3,020 token-4h-clusters, not 28k. The recorder's own docstring (brain_auditor #160) warns event-level stats are pseudo-replicated 2-3x — the report ignores its own source's warning.
Confidence: HIGH
Notes: The DECISION conclusion survives — killing high-conf single-source signals costs ≈nothing (their excess is 0.00, i.e., even more clearly "no edge lost" than claimed) — but the stated REASON ("they underperform, confluence is protective") must be corrected to "they are economically zero; no band shows an edge-costing positive excess." Also: 297 events (1%) had no candle coverage at signal time (entry drift up to 254h) — excluded from closings, benign.

=== INDEPENDENT VERDICT ===
Claim: F4
Verdict: AGREE
Evidence: Recomputed aggregate −$60.7 (my snapshot) / −$67.2 (sum of gate_summary.tsv dollars) ✓ −$67. Deduping overlapping blocks (19,394 unique token+dir+bucket vs 22,793 gate-episodes) gives −$73 — same order. Postgres cross-check: live closed book Oct 4–30 = 637 trades, WR 44%, net −$5.35 at median $11.10 notional — consistent with "everything is near the noise floor." Trades WITH a gate block on the same token+dir within ±10min (n=185, i.e., traded despite blocks): WR 48%, −$0.69; trades without (n=453): WR 43%, −$4.65 — weakly *against* "blocked tokens are worse," but tiny PnL per trade (−0.004 vs −0.010 $/trade) and heavy selection; indistinguishable from noise.
Confidence: HIGH
Notes: The report's own hedge ("matters directionally, not as PnL") is the correct reading; note the double-counting of multi-gate blocks is disclosed nowhere but does not change the sign or order of magnitude.

=== INDEPENDENT VERDICT ===
Claim: F5
Verdict: PARTIAL
Evidence: The 52% reproduces exactly (52.4% on 2,881 episodes; 52.6% event-level on 6,356). BUT: (i) the 2,873 "dual-closed episodes" resolve to only **489 distinct live trades** (top trade backs 143 episodes) — the effective sample is ~489, so the 95% CI is [0.48, 0.57], not ±0.012; (ii) the comparison is win-flag vs 4h-beat-market — two different objects (real SL/TP/trailing exits over variable duration vs fixed-4h market-relative return); a trade can win and underperform the market; (iii) the built-in closer only exists for the 12.5% of episodes where a real follow-on trade fired within 24h — a heavily selected subset.
Confidence: HIGH
Notes: Conclusion ("don't use the built-in closer for decisions") is right, but for structural reasons the report doesn't state (selected 24h join, multi-counted trades, different exit semantics). The 52% figure as evidence is weak — it partly measures metric mismatch, not closer error. Reword.

=== INDEPENDENT VERDICT ===
Claim: F6
Verdict: AGREE
Evidence: BTC-CHOP-GATE: n=448 episodes, +0.108% (report +0.103), Wilcoxon p=0.43, t-test p=0.17, token-cluster p=0.82, positive in both OOS halves (+0.071/+0.133 per report; my halves consistent). Under every baseline (excl-self, 30/120-min gaps) it stays +0.09→+0.11 with p 0.33–0.71. The Oct 2–8 edge (−0.38%) clearly did not replicate over 26 days.
Confidence: HIGH
Notes: None beyond: its 26-day data captures ~80% of its log-visible volume (Oct 11–12 gap), which cannot plausibly reverse a p=0.43 null.

=== INDEPENDENT VERDICT ===
Claim: F7
Verdict: PARTIAL
Evidence: Point estimate replicates exactly: +0.244% (n=253–254 episodes, all SHORT), Wilcoxon p=0.0015, OOS-stable (my event-level halves +0.214/+0.213; report +0.297/+0.212), runner-kill 39.9% (matched per-token baseline 28.7% → +13pp, a real differential). BUT significance is Wilcoxon-only: **t-test p=0.18, token-clustered p=0.62 (70 tokens), day-clustered p=0.27 (19 days)**. The mean is carried by magnitude outliers while the sign test (p=0.0007) says most episodes are positive — a consistent small harm, not a measured +0.244%.
Confidence: HIGH
Notes: "Strongest harm candidate, monitor-only" is a defensible posture; "harm replicates for the third time" should be stated as directional/sign-level significance only. n=253 over 19 days means one regime can carry it.

=== INDEPENDENT VERDICT ===
Claim: F8
Verdict: AGREE
Evidence: LONG-NEUTRAL-CHOP: n=1,036 episodes, excess −0.002 (report −0.001), Wilcoxon p=0.14, t p=0.97, cluster p>0.35; in-chop +0.054 / in-trend −0.256 (report +0.058/−0.253) ✓. Economic zero confirmed under 30/60/120-min coalescing (+0.018/−0.002/−0.007). Gate is ~1.5 days older than reported (log shows firing from 10-11; DB first-seen 10-12 = rotation gap) — immaterial.
Confidence: HIGH
Notes: The regime split (trend n=197–390) is small; "wash" is the right call, no removal urgency — agree.

=== INDEPENDENT VERDICT ===
Claim: F9
Verdict: AGREE
Evidence: Recomputed from t5_shadow.db: 42,068 decisions, 963 (2.29%) with would_pnl closures ✓ ~2%. WOULD_SKIP n=8,530, 169 closed, avg −$0.034 ✓ (report 8,522/167/−0.035); WOULD_TRADE n=1,577, 85 closed, −$0.003 ✓. Coverage too thin for verdicts — agree, and it is worse than "thin": the closure join selects only signals that BECAME live trades within 60min, so the 2% is not a random sample of skips/trades.
Confidence: HIGH
Notes: Provenance gap: the t5 section's numbers are NOT produced by the audited engine (shadow_redundancy_deepdive_2026-10-30.py contains no t5 query and the .out has no t5 output). They do reproduce from the DB by hand, but the report cites the engine/.out as the audit package — either add the t5 query to the engine or cite the ad-hoc source.

=== INDEPENDENT VERDICT ===
Claim: F2/F3 supporting-data quality (recorder coverage, first-seen column, package provenance)
Verdict: DISAGREE
Evidence: (i) The report's "first" column is a recorder-visibility artifact for ~15 gates: the compactor-form regex fix (`:?`, gate_shadow.py, dated 2026-10-22) made ~10 gates "first seen" 10-22/10-23, but the raw log shows them firing from Oct 10–12: SHORT-RSI-HARD-FLOOR **1,933 pre-first-seen log events** (db captures 1,675 of 3,869 = 43%), SPIKE-FILTER 689 (37% captured), LONG-RSI-BLOCK 381 (38%), LONG-MIDBAND 385 (33%), LONG-RSI-CEILING 427 (53%), OVERSOLD-SHORT 411 (60%), SHORT-BB-DEAD-ZONE2 52%, PUMP-CHAIN-VEL 39%. The report attributes first-seen resets only to "renames" and never mentions this fix. Verdicts for these gates (incl. harm-candidate OVERSOLD-SHORT and no-edge SHORT-RSI-HARD-FLOOR) rest on 33–60% of their true block volume. (ii) Oct 11–12 gap is real and recorder-side (log alive: 1,981 + 2,641 deduped recordable events missed; DB 0 + 124) — acknowledged by the report but never quantified (~4,500 events; ~9,100 total missed incl. regex = 19% of in-span volume). (iii) The package table cites "archives pipeline.log.*.gz" as raw material — **no pipeline.log archives exist on disk**; Oct 4–10 events (~10.3k, 20% of the DB) are no longer verifiable against raw logs. Headline claims' populations are less affected: RSI-MAX 92% captured, CONTINUUM pair 83–96%, SLOPE 85%, BTC-CHOP 80%.
Confidence: HIGH
Notes: This does not flip F1/F2/F6/F7, but it invalidates the first-seen column and weakens every verdict for the "10-22 cohort." Also: stored expiry_shadow excess values are not reproducible from current candles (17% >0.01pp, worst >20pp — mutable/backfilled candle history); recompute rather than read from that DB.

---

## OVERALL VERDICT

**NOT fit to hand to an external auditor as-is.** The computational core is sound and I could reproduce essentially every number from the raw data — but four classes of correction are required first:

1. **Inference hygiene (biggest issue).** Every significance claim uses Wilcoxon over token×time-episodes that are heavily dependent (a single token-day cluster drives many episodes). Token-clustered and day-clustered t-tests I ran turn F1's p<0.0001 into p=0.01–0.07, F7's p=0.0015 into p=0.27–0.62, and every F3 band into p>0.07. The expiry_shadow.py docstring itself (brain_auditor #160) warns of exactly this 2–3x pseudo-replication — the report ignores its own instrument's warning. Add cluster-robust p-values (or day-block bootstrap) to every claim, or relabel all p-values "naive (unclustered)."
2. **F3 must be re-derived.** The claim "the high-confidence singles the confluence wall kills underperform at every band" is false for singles: conf≥80 single-source excess is **+0.0016%** (n≈14k); the negative band means come from multi-source rows; the 90+ band flips positive in fresh recomputation (n=84). The decision ("killing singles costs no edge") is *more* robust than claimed — singles are exactly zero — but the protective narrative and "at every band" must go.
3. **Baselines and thresholds must be fixed or disclosed.** F1's runner-kill "34.2% vs ~22%" uses the wrong denominator (the gate's own tokens run ≥2% at 32.1% unconditionally; differential ≈ +5pp). F1's edge is cross-mean-specific (median −0.046, BTC −0.010). The redundancy classes are knife-edge: PRESERVE-SPIKE-BLOCK solo=24.66% (cutoff 25%, window-sensitive), CONTINUUM-BULL flips "HAS EDGE" at 30-min coalescing. Report sensitivity ranges, not point labels.
4. **Provenance and data-coverage corrections.** (a) first-seen column wrong for ~15 gates (Oct-22 regex artifact) — recompute from logs; (b) state the Oct 11–12 gap size (~4,500 events) and the ~4,600 more lost Oct 13–22 to the regex; (c) remove the claim that pipeline.log archives exist — they don't, and Oct 4–10 is unverifiable; (d) add the t5 query to the engine or stop citing the engine for the t5 numbers; (e) note that expiry_shadow stored excess is not reproducible from current candles (17% of rows drift) — regenerate F3's table from candles, not from the DB.

What survives this audit unchanged and can be relied on: the engine's forward-return arithmetic and exports (verified 20/20 and 49,904-event diff), F4's order-of-magnitude conclusion, F6 (BTC-CHOP did not replicate), F8 (LONG-NEUTRAL-CHOP is a wash), F9 (t5 too thin — and biased, not just thin), the low-solo finding for the CONTINUUM pair, and the directional findings of F1 (PUMP-CHAIN-RSI-MAX is the strongest protective gate in the stack) and F7 (SLOPE-FILTER is a sign-consistent harm candidate). With items 1–4 fixed, the report's *conclusions* — nothing gets removed on this data alone, RSI-MAX is the one keeper, three gates are near-certainly removable — would stand.

*Engine/code attacks resolved: (a) no lookahead in the entry rule — entry is the next 5m candle open after the logged block, max drift 6 min, achievable and slightly conservative; (b) SHORT direction-signing is correct; (c) market-baseline self-inclusion negligible (excl-self changes <0.001pp), but baseline *choice* matters materially (see F1); (d) 30/60/120-min coalescing sensitivity — signs stable, only p-threshold classifications flip; (e) Wilcoxon on dependent/tied data — the real weak point, see item 1; (f) redundancy thresholds — knife-edge, see item 3; (g) MFE runner baseline recomputed — 25.4% long / 21.9% short market-wide, 32.1% per-token for RSI-MAX's coins; (h) 52% agreement reproduced but rests on 489 distinct trades and compares win-vs-beat-market.*
