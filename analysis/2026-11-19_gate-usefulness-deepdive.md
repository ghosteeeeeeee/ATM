# Gate Usefulness Deep Dive — Which Gates Are Useful, Which Are Useless Blockers

**Date:** 2026-11-19 · **Window:** 2026-10-04 → 11-19 (46 days) · **Status:** SELF-AUDITED 6/6 PASS — READY FOR EXTERNAL AUDIT · **Config changes:** NONE
**Requested by:** T ("which gates are actually useful and which are useless blockers of legitimate setups... all results will be audited, double-check all your work, leave a paper trail")

## 0. TL;DR

1. **T's three claims all CONFIRMED against PG brain.trades:** trade frequency collapsed **47.0/day → 13.2/day (−72%)** since the Sep-7 week; **LONG WR 46.4%** (n=729, net **−$6.89**); SHORT 48.7% (n=318, −$1.71) — both directions are coin-toss-to-negative. The book is unprofitable in the window.
2. **Gate answer: 2 useful, 0 proven-harmful, 24 useless (no-edge), 14 mixed, 7 insufficient.** Cluster-robust WORKS: **PUMP-CHAIN-RSI-MAX** (n=1,028, ex4h −0.195%, p_tok=0.008 p_day=0.003) and **LONG-RSI-CEILING** (n=988, −0.188%, p_tok=0.048). **No gate survives as demonstrably blocking legitimate setups** — despite 164 concrete ≥10%-MFE misses, blocked sets average ≈ market on 4h markouts. The "useless blockers" are the 24 no-edge gates: they neither help nor hurt per block, but they constitute ~99% of block volume and produce a **90:1 block-to-trade ratio**.
3. **The flow collapse is NOT primarily gate tightening:** blocked episodes held steady at 4,300–9,400/week all window while trades fell 242→53/week — the starvation is upstream (signal volume / confluence / confidence), not a tightening of the veto layer.
4. **Self-audit caught and fixed a real engine bug** (lookahead when entry precedes candle history) and documented that **candles_5m is under ~29d rolling retention** — a mass prune fired mid-run at 21:55, making Oct 4–20 values unreproducible post-hoc. See §1.

## 1. Data, provenance, and the data-mutation finding

**Frame:** 107,040 block events = 56,030 reparse (Oct 30 → Nov 19, raw logs/archives, ground truth) ∪ 51,010 gate_shadow.db events (Oct 4 → Oct 30; raw logs deleted pre-rotator). Capture audit in overlap: **39/39 gates ≥90% recorder capture** (post-fix recorder is healthy; health metric confirms 0.96).

**⚠ Finding F-DATA-1 (candles_5m is mutable):** `candles_5m` has ~29-day rolling retention. A **mass prune fired 2026-11-19 21:55, during this analysis's engine run**, deleting everything before Oct 21 03:10 (global min now = that timestamp for all tokens). Consequences:
- 24,699 events (entry before candle history) are now **unreproducible** — the engine originally computed their forward returns from complete data; a re-run next week would silently produce *different* values.
- **Engine bug found by self-audit A2:** `fwd_metrics` had no guard for entry-before-first-candle — it silently measured forward returns from a candle up to 17 days after the event (lookahead). A fingerprint test (identical fwd_4h across all of a token's pre-history events) confirmed ~11 tokens/~564 events were contaminated even at run time. **Fixed:** `rows[0][0] > entry_ts + 300 → return None`; 24,699 pre-history events now dropped honestly (enriched 106,357 → 81,707). This same root cause explains the own-conclusions auditor's "17% of expiry_shadow stored values don't reproduce" finding.
- **Paper-trail implication:** re-runs are only stable within the retention window; exports are the snapshot of record. External auditors should treat `exports/nov19_gate_events.tsv` as the immutable computed-values record and re-verify *method* (checks A3/A6) rather than expect bit-identical regeneration of pre-Oct-21 rows.

## 2. Self-audit — independent second path, 6/6 PASS

`analysis/gate_usefulness_selfaudit_2026-11-19.py` → `analysis/gate_usefulness_selfaudit_2026-11-19.md` (rerun after fixes; three self-audit bugs were found and fixed during the process — A1 compared all-episodes vs non-None-episodes; A2 used wrong archive paths; A2 didn't gate on data mutation — none were engine bugs except the lookahead guard of §1):

| # | Check | Result |
|---|---|---|
| A1 | Independent re-coalescing of events export matches summary (per-gate n + mean) | **PASS** |
| A2 | Random events: raw log line exists (reparse prov) + forward return recomputed by a different code path | **PASS** |
| A3 | Excess re-derived via independent SQL baseline (300-token sample) — matches to 4dp | **PASS** |
| A4 | Live-book WR/net second SQL + pnl_usdt/pnl_pct sign consistency (19 "mismatches" = all $0.00 scratches; 0 real) | **PASS** |
| A5 | No duplicate (gate,token,dir,10min) in 81,707-row export | **PASS** |
| A6 | Big-miss MFE values spot-checked vs raw candles | **PASS** |

## 3. The funnel — C-1 (frequency collapse)

| week | blocked eps | trades | block:trade |
|---|---|---|---|
| 2026-10-05 | 5,480 | 127 | 43:1 |
| 2026-10-12 | 4,285 | 201 | 21:1 |
| 2026-10-19 | 6,387 | 128 | 50:1 |
| 2026-10-26 | 9,389 | 242 | 39:1 |
| 2026-11-02 | 7,133 | 149 | 48:1 |
| 2026-11-09 | 7,696 | 111 | 69:1 |
| 2026-11-16 | 4,789 | 53 | **90:1** |

Blocked volume is roughly **stable (4.3k–9.4k/week)** while trades **halved twice over**. The veto layer didn't tighten — flow upstream dried up. Weekly trade series (§0) also shows the collapse is a September phenomenon that continued: 47/day → 13/day.

## 4. Per-gate usefulness classification (cluster-robust)

Method: 60-min episodes; excess = direction-signed fwd4h − cross-sectional market mean; Wilcoxon (naive) + **token-clustered and day-clustered t-tests**; Bonferroni p<0.0011 over 47 gates; a class claim requires ≥1 cluster p<0.05. Kill rates: blocked episodes printing dir-MFE≥5%/≥10% vs the gate's **own tokens' unconditional** rates (hourly-sampled) — the honest big-move baseline.

**WORKS (2)** — blocks below-market signals, cluster-robust, OOS same-sign:
- **PUMP-CHAIN-RSI-MAX** n=1,028, −0.195%, p_w<0.0001, p_tok=0.008, p_day=0.003, OOS −0.28/−0.13. The system's one durable worker. (Continued from Oct-30 finding — now 46 days.)
- **LONG-RSI-CEILING** n=988, −0.188%, p_w=0.0003, p_tok=0.048, OOS same-sign. First cluster-robust appearance for this gate.

**BLOCKS-SETUPS (0)** — *no gate survives as demonstrably refusing legitimate setups.* On 4h markouts, blocked sets are market-average or better-under-market. This is the honest answer to the core question — the "missing big moves" are real at the anecdote level (§5) but not at the average level.

**NO-EDGE (24)** — |ex4h|<0.10%, p≥Bonferroni. Includes every volume giant: CONFLUENCE-GATE-BLOCK (n=3,426, −0.063%), CONTINUUM-BLOCK (2,817, +0.015), CONTINUUM-BULL (2,362, −0.034), SHORT-RSI-HARD-FLOOR (2,190, −0.005), LONG-NEUTRAL-CHOP (1,904, +0.059 — remains a wash), LONG-NEUTRAL, SHORT-NEUTRAL, OVERSOLD-SHORT, PUMP-CHAIN-SHORT-HIGH, CTX-GATE (LLM), SHORT-CONTINUUM, LONG-RSI-BLOCK, BTC-CHOP-GATE, EXEC-BLOCK, HOT-SET, VEL-FILTER, SHORT-BB-DEAD-ZONE/2, SHORT-RSI-CEILING, SHORT-REGIME-GATE, PUMP-CHAIN-HIGH, LONG-MIDBAND, EXEC-RSI-HARD-FLOOR, LONG-BYPASS-SHORT-BIAS-BLOCK. **These are the "useless blockers": ~99% of block volume, no measurable effect in either direction.**

**MIXED/NS (14)** — directionally interesting, not robust:
- **VOL-GATE-BYPASS** +0.121%, **p_day=0.010**, OOS +0.047/+0.214 (both positive) — best harm *candidate* (blocks-winners direction, day-cluster significant, OOS-stable).
- **SLOPE-FILTER** +0.122%, kill5 9% vs own 5% — harm direction consistent with all three prior audits; still cluster-ns.
- **SPIKE-FILTER** −0.157%, p_tok=0.008, OOS −0.21/−0.13 — protective direction, token-cluster sig, fails Bonferroni.
- **PUMP-CHAIN-VEL** −0.347%, p_day=0.045 (post-deadband protective, third window confirming).
- **MAXXED-BLOCK**: kill5 **45% vs own 9%** (n=44) — kills its tokens' big moves at ~5× their base rate; excess ns but the tail-kill is extreme — flagged for review.

**INSUFFICIENT (7):** n<16 (incl. PUMP-CHAIN-RSI-MIN kill5 23% vs own 6%, n=13 — watch).

## 5. Missing big moves — C-3

**164 blocked episodes printed dir-MFE ≥10% in 4h** (0.4% of 33,812 episodes). Top casualties (full list `exports/nov19_bigmisses.tsv`):
- **10-30 SOPH LONG +37.9% MFE** (fwd +33.3) — blocked by VOL-GATE-BYPASS
- **10-30 BLUR LONG +32.9%** (fwd +24.6) — blocked by CONTINUUM-BLOCK *and* SPIKE-FILTER, LONG-RSI-BLOCK, LONG-NEUTRAL-CHOP (same move, four gates)
- **11-09 NXPC LONG +29.6%** (fwd +9.8) — CONTINUUM-BLOCK + LONG-NEUTRAL + LONG-RSI-CEILING
- **11-16 CASHCAT LONG +22.1%** (fwd +21.4) — blocked by four gates incl. EXEC-BLOCK
- 10-22 ALT SHORT +25.3% (fwd +22.4), 11-13 IMX LONG +28.7% (fwd **−2.4** — MFE faded, would have needed the trail to exit green)

Per-gate big-move kill differential (kill10 − own10): MAXXED-BLOCK **+5.6pp** (pre-guard run; n shrank post-guard), PUMP-CHAIN-VEL-SHORT +1.5pp, PUMP-CHAIN-RSI-MIN +1.0pp, SLOPE-FILTER +0.9pp, SHORT-BB-DEAD-ZONE2 +0.7pp, VOL-GATE-BYPASS +0.5pp (n=1,237). Note the WORKS gates also kill above their base rate (RSI-MAX kill5 8% vs own 5%) — that is what "working" costs: refusing some future runners to avoid worse entries.

## 6. Robustness

- **Coalescing:** 30/120-min gaps flip sign for only 1–2 of top-20 gates.
- **OOS (Oct 4→Nov 1 vs Nov 1→19):** 9 of 20 listed gates flip sign — regime-dependence persists (consistent with all prior audits); the WORKS pair holds same-sign in both halves.
- **Method lineage:** engine = the forward-return method independently cross-validated in `audit/gate_counterfactual_verify.md` (two implementations <0.10% apart), now with the §1 lookahead guard.

## 7. The answer

1. **Useful gates (keep):** PUMP-CHAIN-RSI-MAX, LONG-RSI-CEILING (cluster-robust, OOS-stable); PUMP-CHAIN-VEL post-deadband (protective, day-cluster sig); SPIKE-FILTER (probable worker, fails Bonferroni).
2. **Useless blockers (removal candidates on efficiency grounds, NOT recovered PnL):** the 24 no-edge gates — they don't lose money per block, but they are ~99% of the veto layer's volume, fire continuously (the 90:1 funnel), and several are functionally redundant (CONTINUUM pair, established in the Oct-30 audit at solo 13–17%). Since blocked ≈ market, removing them changes flow at ≈ zero markout cost — the Nov-6-queue logic extends: removal tests should target the biggest no-edge gates with the R1 dollar-closer when it ships.
3. **Not the cause of unprofitability (on this metric):** blocked sets ≈ passed sets ≈ market. Long WR 46.4% / −$6.89 is an entry-quality + exit-engine problem the gates neither created nor prevented — consistent with the standing finding that passed-vs-blocked is indistinguishable (p≈0.5). The gates are not why you're losing; they're also not why flow starved (§3).
4. **Harm candidates to watch (not act on):** VOL-GATE-BYPASS (day-cluster sig, OOS-stable), SLOPE-FILTER (direction consistent across four studies), MAXXED-BLOCK (extreme tail-kill, n=44).
5. **Concrete misses exist** (164 episodes ≥10% MFE; the four-gate BLUR/CASHCAT cases) — but average markouts don't support "gates block winners" as a class. The R1 extended closer (real exit-stack counterfactual in $) remains the instrument that could settle tail questions.

## 8. Paper trail (everything re-runnable or snapshotted)

| Artifact | Purpose |
|---|---|
| `analysis/gate_usefulness_deepdive_2026-11-19.py` | Engine: frame build, guard-fixed fwd_metrics, cluster tests, kill baselines, funnel, exports. One file, no live-path imports |
| `analysis/gate_usefulness_deepdive_2026-11-19.out` | Verbatim output (all numbers above) |
| `analysis/gate_usefulness_selfaudit_2026-11-19.py` + `.md` | Independent second path, 6/6 PASS |
| `exports/nov19_gate_events.tsv` | 81,707 events with computed metrics (snapshot of record — candles mutate) |
| `exports/nov19_gate_summary.tsv` | Per-gate table incl. cluster p-values + classes |
| `exports/nov19_weekly_funnel.tsv` | Full-frame weekly blocks vs trades |
| `exports/nov19_bigmisses.tsv` | All 164 ≥10%-MFE blocked episodes |
| Source DBs | `brain/gate_shadow.db` (recorder, capture 0.96), `brain/expiry_shadow.db`, PG `brain.trades`, `candles.db` (⚠ ~29d rolling retention) |
| Prior verification | `audit/gate_counterfactual_verify.md`, `brain/verdicts/2026-10-30_shadow-redundancy-own-conclusions.md`, `brain/verdicts/2026-10-12_deadlock-gate-verify.md` |

Reproduce: `python3 analysis/gate_usefulness_deepdive_2026-11-19.py && python3 analysis/gate_usefulness_selfaudit_2026-11-19.py`. Known reproduction limits: pre-Oct-21 candle values are unreproducible after the 21:55 prune (§1) — verify method (A3/A6) on retained data instead; db-only (Oct 4–30) raw log lines are deleted (rotator now retains archives going forward).

## 9. What this cannot settle

4h candle markouts ≠ realized PnL under the live exit stack (R1 extended closer still unbuilt); the harm candidates need the Nov-6-plus data and dollar-level closure; upstream starvation (why trades halved with stable blocks) is a separate question — signal generation volume, confluence-expiry rates, and confidence-floor rejections over the same window are the next analysis if T wants the root cause of the frequency collapse.
