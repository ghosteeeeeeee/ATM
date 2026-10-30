# Shadow Redundancy Deep Dive v2 — Which Gates/Filters Are Redundant?

**Date:** 2026-10-30 · **Window:** 2026-10-04 → 10-30 (26 days) · **Status:** CORRECTED PER OWN-CONCLUSIONS VERDICT — READY FOR EXTERNAL AUDIT · **Config changes:** NONE
**Correction ledger:** v1 (commit 7262794c) was ruled NOT fit for external hand-off by the independent own-conclusions auditor (`brain/verdicts/2026-10-30_shadow-redundancy-own-conclusions.md`, commit 5ed3bcf8): arithmetic faithful (20/20 export rows verified, engine no-lookahead confirmed), but inference/framing/provenance required fixes. This v2 implements all four correction classes. Every v1→v2 delta is listed in §7.

## 0. External audit package

| File | Contents |
|---|---|
| `analysis/shadow_redundancy_deepdive_v2_2026-10-30.py` | v2 engine — single script, re-runnable, includes capture-audit, cluster tests, expiry recompute, t5 |
| `analysis/shadow_redundancy_deepdive_v2.out` | v2 raw output (all numbers below, verbatim) |
| `analysis/exports/v2_gate_events.tsv` | Every event (n=59,436 enriched) + metrics + provenance flag |
| `analysis/exports/v2_gate_summary.tsv` | Per-gate table incl. cluster p-values |
| `analysis/exports/v2_expiry_summary.tsv` | Singles vs multi-source expiry recompute |
| Source DBs | `brain/gate_shadow.db`, `brain/expiry_shadow.db`, `brain/t5_shadow.db`; candles `/root/.hermes/data/candles.db`; PG brain.trades |
| Verification trail | v1 report+engine in git (7262794c); own-conclusions verdict (5ed3bcf8) with its own /tmp/audit engine; prior engine cross-validation `audit/gate_counterfactual_verify.md` |

## 1. Provenance and coverage (C5 — corrected)

**Event frame = fresh reparse of the SURVIVING raw log (Oct 10 20:49 → Oct 30, 455MB, current recorder regexes incl. the Oct-22 compactor-form `:?` fix) ∪ gate_shadow.db rows from Oct 4–10 20:49 (marked `db-only` — raw archives no longer exist on disk; those 12,483 events are UNVERIFIABLE against raw logs).** v1's claim that `pipeline.log.*.gz` archives were package material was wrong and is retracted.

**Recorder capture audit (DB rows vs reparse ground truth, overlap window):**

| gate | capture % | | gate | capture % |
|---|---|---|---|---|
| VOL-GATE-BYPASS | 99 | | LONG-NEUTRAL-CHOP | 86 |
| CONTINUUM-BULL | 96 | | CONTINUUM-BLOCK | 83 |
| CONFLUENCE-GATE-BLOCK | 93 | | LONG-NEUTRAL | 81 |
| SHORT-CONTINUUM | 93 | | BTC-CHOP-GATE | 80 |
| PUMP-CHAIN-SHORT-HIGH | 92 | | LONG-RSI-CEILING | 53 |
| PUMP-CHAIN-RSI-MAX | 91 | | SHORT-BB-DEAD-ZONE2 | 52 |
| CTX-GATE | 91 | | OVERSOLD-SHORT | 60 |
| PUMP-CHAIN-HIGH | 98 | | SHORT-RSI-HARD-FLOOR | **43** |
| | | | LONG-RSI-BLOCK | **38** |
| | | | SPIKE-FILTER | **37** |
| | | | LONG-MIDBAND | **33** |

The Oct-11/12 recorder outage (~4,500 deduped events) and the pre-Oct-22 regex blindness (~4,600 more) are **recovered by the reparse** in this frame. Gates below ~60% capture in the DB had their v1 first-seen dates and populations distorted — v2 first-seen/eps come from the reparse frame. The "10-22 cohort" caveat applies to DB-only cross-references, not to this frame. Headline gates all ≥80% capture.

## 2. Method v2

- Forward-return engine: unchanged from the independently cross-validated reference (entry = OPEN of first 5m candle ≥ block ts — auditor confirmed NO lookahead, max drift 6min; direction-signed excess = sgn × (fwd − cross-sectional mean); median and BTC baselines also computed per event).
- **Cluster-robust inference (C1):** every gate reports Wilcoxon (naive) plus token-clustered and day-clustered one-sample t-tests on cluster means. A claim is called robust only if at least one cluster p < 0.05 alongside p_w < Bonferroni (0.001).
- Episodes = 60-min coalescing; sensitivity at 30/120-min and solo windows ±5/±10/±15min (C4).
- Runner-kill baseline fixed (C3): each gate's blocked MFE≥2% share vs **its own tokens' unconditional** MFE≥2% share (hourly-sampled buckets over the window), not the market-wide share.

## 3. Headline findings (cluster-robust)

**H1 — Exactly two gates have cluster-robust edge; both protective.**
- **PUMP-CHAIN-RSI-MAX**: n=1,087, ex4h −0.136%, p_w<0.0001, **p_tok=0.011, p_day=0.040**, solo 76%, OOS same-sign (−0.085/−0.224). Runner differential honest version: blocked 35.1% vs own-token unconditional 27.9% = **+7.2pp** (v1's "+34.2 vs ~22 market" retracted). Edge is cross-mean-specific: median baseline −0.051 (same sign, ~1/3 size); the claim is "protective under the reference baseline", not baseline-independent.
- **PUMP-CHAIN-VEL (post-deadband)**: n=144, ex4h **−0.549%**, p_w=0.0010, p_day=0.015 (p_tok=0.074), solo 42%. The deadband shipped Oct 14 (`PUMP_CHAIN_VEL_30M_MIN=−0.3`); since then the gate blocks only genuine decliners and that population underperforms market strongly. **The deadband reform self-validated**: noise-band blocks are gone; what remains works.

**H2 — NO cluster-robust harm exists.** v1's SLOPE-FILTER "3rd replication" (+0.244%, p=0.0015) becomes +0.342% with p_w=0.0003 but **cluster-ns (p_tok=0.30, p_day=0.20)** — relabeled sign-consistent harm *candidate*, not demonstrated. OVERSOLD-SHORT (+0.152%, OOS-stable +0.171/+0.141) is likewise nominal/cluster-ns. Under honest inference, **no gate in 26 days demonstrably blocks winners.**

**H3 — 26 gates are NO-EDGE** (|ex4h|<0.10%, p_w≥Bonferroni) — including every volume giant: CONFLUENCE-GATE-BLOCK (n=4,120, −0.040%), SHORT-CONTINUUM (1,962, −0.063%), LONG-NEUTRAL (1,690, −0.009%), **SHORT-RSI-HARD-FLOOR (1,625, −0.012%)**, SHORT-NEUTRAL (1,497, +0.029%), CTX-GATE (1,451, −0.088%), PUMP-CHAIN-SHORT-HIGH (1,229, −0.065%), **LONG-NEUTRAL-CHOP (1,200, +0.014%)** — the patch-spiral gate remains a wash at full life.

**H4 — Fully-redundant class holds with stronger data.** CONTINUUM-BLOCK solo **13%** (16%/12% at ±5/±15min — robustly low), CONTINUUM-BULL **17%** (21%/17%), PRESERVE-SPIKE-BLOCK **19%** (v1's knife-edge 24.66% resolved by the larger reparse frame). Economic effects all |−0.04|<0.10. These three fire on ~3,900 episodes/26d that almost always duplicate another gate's block. Removal predicted ≈ zero flow change — the cleanest Nov 6 test.

**H5 — F3 corrected: confluence-expired SINGLES are exactly zero, not negative.** Fresh recompute from candles (stored expiry_shadow excess was 17% non-reproducible — not used): singles 70-79 −0.034% (n=12,791), 80-89 **−0.0003%** (n=11,944), 90+ **+0.085%** (n=79, flips positive); multi-source rows carry all the negativity (−0.13 to −0.14). Pooled conf≥70 singles: −0.0175% (n=24,814). "Protects at every band" is retracted. The decision it supported is unchanged and stronger: **killing high-conf singles costs nothing measurable — they are exactly zero.**

**H6 — BTC-CHOP-GATE non-replication stands**: +0.133%, positive both halves (+0.080/+0.204).

**H7 — t5_shadow (now in-engine, C6)**: 2.3% closure coverage, and per the auditor the closure join is selected (only signals that became live trades) — not usable for verdicts; keep as a candidate for retirement or redesign with the R1 extended closer.

## 4. Per-gate table (top 18 by episodes; full table in .out / v2_gate_summary.tsv)

| gate | eps | solo10 | ex4h | p_w | p_tok | p_day | ex_med | mfe2 vs own | class |
|---|---|---|---|---|---|---|---|---|---|
| CONFLUENCE-GATE-BLOCK | 4,120 | 68% | −0.040 | 0.204 | 0.930 | 0.324 | −0.067 | 22.5 vs 23.9 | NO-EDGE |
| CONTINUUM-BLOCK | 1,984 | **13%** | −0.043 | 0.0001 | 0.030 | 0.251 | +0.003 | 20.0 vs 20.3 | **FULLY REDUNDANT** |
| SHORT-CONTINUUM | 1,962 | 57% | −0.063 | 0.024 | 0.059 | 0.370 | −0.166 | 20.9 vs 25.1 | NO-EDGE (nominal) |
| LONG-NEUTRAL | 1,690 | 40% | −0.009 | 0.037 | 0.186 | 0.456 | +0.045 | 17.2 vs 20.5 | NO-EDGE |
| CONTINUUM-BULL | 1,650 | **17%** | +0.009 | 0.0008 | 0.593 | 0.830 | −0.079 | 14.5 vs 22.5 | **FULLY REDUNDANT** |
| SHORT-RSI-HARD-FLOOR | 1,625 | 73% | −0.012 | 0.491 | 0.415 | 0.932 | −0.041 | 32.2 vs 25.2 | NO-EDGE |
| SHORT-NEUTRAL | 1,497 | 43% | +0.029 | 0.017 | 0.315 | 0.353 | −0.047 | 18.0 vs 21.8 | NO-EDGE |
| CTX-GATE | 1,451 | 60% | −0.088 | 0.037 | 0.062 | 0.036 | −0.046 | 32.6 vs 27.5 | NO-EDGE |
| PUMP-CHAIN-SHORT-HIGH | 1,229 | 88% | −0.065 | 0.556 | 0.300 | 0.537 | −0.120 | 29.0 vs 24.9 | NO-EDGE |
| LONG-NEUTRAL-CHOP | 1,200 | 36% | +0.014 | 0.068 | 0.348 | 0.992 | +0.068 | 22.5 vs 21.2 | NO-EDGE (wash) |
| PUMP-CHAIN-RSI-MAX | 1,087 | 76% | **−0.136** | **<0.0001** | **0.011** | **0.040** | −0.051 | 35.1 vs 27.9 | **WORKS** |
| VOL-GATE-BYPASS | 993 | 75% | +0.021 | 0.716 | 0.485 | 0.762 | +0.038 | 37.2 vs 31.7 | NO-EDGE |
| SPIKE-FILTER | 660 | 44% | −0.123 | 0.028 | 0.138 | 0.056 | −0.085 | 37.4 vs 27.4 | nominal |
| OVERSOLD-SHORT | 649 | 31% | +0.152 | 0.003 | 0.188 | 0.045 | +0.103 | 23.0 vs 23.6 | harm-cand. (cluster-ns) |
| LONG-RSI-CEILING | 552 | 49% | −0.192 | 0.002 | 0.427 | 0.396 | −0.112 | 34.1 vs 25.4 | nominal |
| BTC-CHOP-GATE | 511 | 37% | +0.133 | 0.316 | 0.456 | 0.126 | +0.150 | 18.4 vs 21.2 | NO-EDGE (non-repl.) |
| PUMP-CHAIN-VEL (post-DB) | 144 | 42% | **−0.549** | **0.0010** | 0.074 | **0.015** | −0.478 | 36.8 vs 30.6 | **WORKS** |
| SLOPE-FILTER | 287 | 39% | +0.342 | 0.0003 | 0.299 | 0.204 | +0.263 | 41.5 vs 31.5 | harm-cand. (cluster-ns) |

Sensitivity (C4): no sign flips for any top gate across 30/60/120-min coalescing; one knife-edge flag — LONG-RSI-BLOCK solo is window-sensitive (56%/28%/26% at ±5/±10/±15min).

## 5. The answer (redundancy classes, corrected)

- **2 cluster-robust workers**: PUMP-CHAIN-RSI-MAX, PUMP-CHAIN-VEL (post-deadband).
- **0 demonstrated harmful gates** (v1's SLOPE-FILTER/RSI-family harm claims downgrade to candidates — cluster-ns).
- **3 fully redundant**: CONTINUUM-BLOCK, CONTINUUM-BULL, PRESERVE-SPIKE-BLOCK — no edge + solo ≤19% robust across windows. Priority removal tests at Nov 6.
- **~24 no-edge gates** with meaningful solo share: removal would change flow at ~market-average outcomes — the "78% no edge" architecture finding holds at 26 days under cluster-robust standards.
- **Confluence-expired singles: exactly zero** — the wall neither costs nor protects on singles; its multi-source blocks skew negative.
- Aggregate dollarization unchanged in order of magnitude (v1's −$67/26d; AGREE per auditor; v2 frame not re-dollarized — flag for external auditor).

## 6. What this cannot settle (unchanged from v1 + auditor)

4h candle markouts ≠ realized PnL under the live exit stack (the R1 extended closer, CEO D1, is still the missing instrument for dollar-denominated decisions); trend-regime n per gate is small (regime splits in .out); single 26-day span; DB-only Oct 4–10 tail unverifiable.

## 7. Correction ledger (v1 → v2)

| # | v1 claim | v2 correction |
|---|---|---|
| 1 | Wilcoxon p as primary inference | Cluster p added everywhere; claims require cluster support. Kills: SLOPE-FILTER "3rd replication" (p_tok=0.30), all F3 band significance |
| 2 | F3 "protects at every band; singles underperform" | FALSE for singles: 80-89 −0.0003%, 90+ +0.085%; multi-source carries negativity. Decision unchanged (singles = zero) |
| 3 | F1 runner "+34.2% vs ~22% market" | Own-token baseline: 35.1% vs 27.9% (+7.2pp). Median baseline −0.051 (baseline-specific disclosed) |
| 4 | Bright-line redundancy classes | Sensitivity ranges added; PRESERVE-SPIKE solo resolved 24.66%→19% with reparse frame; knife-edge flags emitted |
| 5 | first-seen + archives + capture | Reparse-based frame; capture audit table; archives retracted (gone); db-only tail flagged UNVERIFIABLE; Oct 11–12 + Oct 13–22 gaps quantified and recovered |
| 6 | t5 cited ad hoc | t5 queries in-engine (C6) |
| 7 | expiry from stored DB values | Recomputed from candles (17% stored drift) |
| 8 | — | NEW: PUMP-CHAIN-VEL post-deadband cluster-robust WORKS (deadband shipped Oct 14, self-validated) |
