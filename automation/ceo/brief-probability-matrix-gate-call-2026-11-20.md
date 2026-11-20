# BRIEF: Probability-matrix P0 gate STOP — PARK or ITERATE? (2026-11-20)

## Context (full arc, all verified — artifacts named so you can spot-check)

**Origin**: 5-video transcript mining → Thorp/Kassouf *Beat the Market* distilled
(`brain/summaries/beat-the-market-thorp-kassouf.md`, skill `book_beat_the_market`) → the
"probability matrix" idea (fit conditional expectation, price = Σ payoff × P, bounds first) →
prior-art survey (`brain/context/probability-matrix-context.md`, `1d59afbc`: `cell_stats.py` IS the
normal-price-curve analog, live in `_score_signal`; **zero EV code anywhere**; confidence documented
anti-predictive).

**Spec**: `brain/plans/probability-matrix-spec.md` v1.1 (`4fe2153a`→`77cf42c0`). Own-conclusions
audit v1.0 → PROCEED-WITH-CHANGES (`brain/verdicts/2026-11-19-probability-matrix-spec-verdict.md`,
`10eb95ff`), all 9 required changes applied (churn-aware rolling folds, ev-honesty, 0-win no-fail-open,
hardened bars). Phases: P0 study (read-only) → P1 shadow (pre-registered bar) → P2 enforce
(one-line flag, CEO-gated). **n_min=15 must never be loosened to chase coverage (spec §4d/§9).**

**P0 executed end-to-end** (build `037ea1ce` → code review PASS-WITH-FIXES → 11/11 fixes
`631f9289` → **bug_hunter PASS** `370117c8`: 11/11 verified, gate byte-identically reproduced,
**fail-open-to-PASS hunt clean** across 9 failure modes, independent recompute from raw trades
matched every number). Tool: `scripts/probability_matrix.py` (`calibrate`/`report`/`--selfcheck`,
21 asserts), report `brain/analysis/probability-matrix-calibration.md`, bughunt
`brain/analysis/probability-matrix-p0-bughunt.md`. **Zero trading-path files; hermes_constants
untouched.** Reproduce: `python3 scripts/probability_matrix.py calibrate`.

## THE GATE RESULT (pre-registered 4 limbs, final post-fix numbers)

Window: anchored 90d (2026-08-22→11-20), 2,780 closed trades, 5 rolling folds train30d→test7d.

| Limb | Verdict | Numbers |
|---|---|---|
| (a) discrimination | **FAIL** | top-2 p-decile WR 49.0% (n=51) vs bottom-2 28.0% (n=50), Δ+21.0pp — but CR1 p=0.208, **G=4** (small-G indicative; bug_hunter's proper two-sample test p=0.087 — FAIL holds either way) |
| (b) beats confidence | **INCONCLUSIVE** | intersection 198/813 = **24.4% < 30% floor** → not claimable by rule. Point estimates on intersection: Brier(p)=0.2465 vs Brier(conf)=0.3798 (p looks far better, withheld honestly) |
| (c) beats coin | **FAIL** | Brier(p)=0.2522 vs 0.2500, Δ+0.0012, CI [−0.0081,+0.0104], p=0.759 — **cell WR does not predict next-period outcomes OOS** |
| (d) coverage disclosure | **PASS** | per-fold published, worst 19.0% ≥ 10% floor |

**GATE = STOP (1/4). Consequences per spec: NO P1 shadow, NO confidence replacement, n_min
untouched.** Memory stored; nothing runs anywhere.

## Root constraints (measured, not hypothesized)

1. **Signal churn**: pooled OOS coverage 30.9% — labels like `jup_yolo_mirrored` went 0→168 trades
   within the window; train cells don't exist in test. Clean 60/30 split was even worse: 7.1%.
2. **Cluster thinness**: covered OOS trades span only **G=4–6 distinct signals** → cluster-robust
   inference is indicative only. Limb (a)'s shape (Δ+21pp, proper p=0.087) is suggestive but
   unclaimable at this sample.
3. **Confidence is the weakest predictor measured** (0.3798 Brier ≈ badly miscalibrated) — but limb
   (b)'s coverage floor prevents the replacement claim.

## The decision you're being asked to make

**A. PARK** — record the honest negative result; tool stays for cheap re-runs; revisit when the
signal set naturally matures (kill-lines 12-03 / H bar 11-22 cycles will keep producing data).
Cost: zero. Risk: none. Gain: none now; the STOP itself protects credibility.

**B. ITERATE with fresh pre-registered bars** (you must specify the bars BEFORE the run). Honest
candidate iterations, each with tradeoffs — you pick which, if any:
   - **B1: Longer window** (`--days 180/270` or full history ~4,851+ trades). More n, more folds —
     BUT older data has *different* labels (even more churn backward in time); needs a stated
     mapping policy (mature-labels-only subset? base-source grouping?).
   - **B2: Mature-label subset** — only signals with ≥60d history (directly tests the book's
     "fit on known instruments"; kills churn by construction; shrinks universe).
   - **B3: Coarser cells** (e.g., base signal family instead of full combo label) → more trades
     per cell AND more clusters (attacks G=4 directly); costs resolution; must be specified
     exactly (family mapping rule) before running.
   - Note: any iteration re-runs the SAME verified tool — build cost ≈ ruling cost. Any pass of
     the 4 limbs still goes through P1 shadow + your approval before anything touches live.
   - The spec forbids loosening n_min/coverage floors to force a pass — iterations change the
     *data design*, never the bars.

**C. KILL the line** — archive spec + tool as closed experiment; no revisit scheduled.

## Questions — state the ruling

1. **A, B, or C?** If B: which variant(s) (B1/B2/B3 or a combination), the exact window/mapping
   policy, and the pre-registered limbs (unchanged 4, or any amendment you explicitly state now —
   BEFORE any run).
2. If B: sequencing — direct dispatch now, or queue behind current in-flight work (H bar review
   11-22, stop-tighten eval 11-21, kill-line enforce 12-03)?
3. Anything to record for the eventual P2 path already (so a future pass doesn't re-litigate scope)?

Constraints on your ruling: operator standing order = "biggest winners go live right now" was
already consumed as: only evidence-proven items flip (ATR_SL_MIN attempt FAILED verification and
did not ship). Same standard applies here — a PASS gets you shadow, never an instant live flip.
Protocol for any change: same build→review→bug_hunter chain; independent verification before any
future enforce.

State the ruling as: DECISION + exact parameters (if B) + pre-registered bars + sequencing +
one-line rationale.
