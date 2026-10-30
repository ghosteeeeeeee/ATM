# Shadow Redundancy Deep Dive — Which Gates/Filters Are Redundant?

**Date:** 2026-10-30 · **Window:** 2026-10-04 → 10-30 (26 days) · **Status:** READY FOR EXTERNAL AUDIT · **Config changes:** NONE
**Prepared by:** hermes-agent (analysis session) · **Requested by:** T

## 0. External audit package

| File | Contents |
|---|---|
| `analysis/shadow_redundancy_deepdive_2026-10-30.py` | Complete engine — one file, re-runnable, no live-path imports |
| `analysis/shadow_redundancy_deepdive_2026-10-30.out` | Full output (this report's numbers, verbatim) |
| `analysis/exports/gate_events_enriched.tsv` | Every shadow event (n=50,478) + computed fwd/excess/MFE/regime (5.7MB) |
| `analysis/exports/gate_summary.tsv` | Per-gate summary table |
| `analysis/exports/expiry_summary.tsv` | Confluence-expiry answer by confidence band |
| `brain/gate_shadow.db` / `brain/expiry_shadow.db` / `brain/t5_shadow.db` | Source shadow DBs (recorders: `scripts/gate_shadow.py`, `scripts/expiry_shadow.py`, `scripts/t5_shadow.py`) |
| Prior verification | `audit/gate_counterfactual_verify.md` (independent cross-validation of the engine, <0.10% agreement), `brain/verdicts/2026-10-12_deadlock-gate-verify.md` |

Engine provenance: the forward-return method is the one independently cross-validated in the Oct-8 audit (entry = OPEN of first 5m candle ≥ block_ts, no lookahead; direction-signed excess = sgn × (fwd − cross-sectional mean); the unsigned-baseline variant was killed by audit and is NOT used here).

## 1. Data inventory

| Source | Events | Window | Closure method |
|---|---|---|---|
| gate_shadow.db | 50,478 (49,904 with forward data; 23,015 coalesced episodes; 50 gates) | Oct 4 → Oct 30 | **Audited candle engine** (strong) + built-in follow-on-trade join (weak, kept for triangulation) |
| expiry_shadow.db | 28,634 (27,685 closed) | Sep 24 → Oct 30 | D3 engine (same direction-signed method) |
| t5_shadow.db | 42,002 decisions (961 with pnl closures) | Oct 4 → Oct 30 | cell-admission join (weak coverage — 2%) |

Coverage caveats (auditor must weigh):
1. **gate_shadow parser sees only 🚫🔒🚧🌊-emoji gates with blocked/denied wording.** Invisible: RR-ENGINE (🎯, ~400 eps/6d in the Oct-8 audit), CHASE-BLOCK, CONF-FILTER-PRESERVE, CONFLICT-RESCUE (🔄), LOSERS-BLOCK (🗑️), and all direction-level gates (VOL-FLOOR, WARNING BTC-momentum, DIRECTION-LOCK, VOL-GATE-v2 — ~3,800 lines/6d with no token+dir). The D4 BLOCKED-format tranche (Oct 9) improved visibility for six families mid-window.
2. **Oct 11 gap** — log-rotation window (recorder dead Oct 10 20:48 → rotation fix; 124 events on Oct 12 only).
3. **Renames reset first-seen:** CONTINUUM-BLOCK/BULL show first-seen 10-09 in shadow (code rework), not their true age. HALL-SHAME enforcement ended ~Oct 12 (replaced by Reputation Phase 2, commit 4b1371ce) — its 316 episodes are historical only.
4. Regime mix: 70–90% of blocks per gate are chop-regime (|BTC 30m vel| < 0.3%). Trend-regime n is small per gate (50–700).

## 2. Headline findings

**F1 — Exactly one gate survives Bonferroni over 26 days: PUMP-CHAIN-RSI-MAX works.**
n=1,010 episodes, excess_4h −0.127% (blocked signals went on to underperform market), p<0.0001, solo 81% (fires alone — real marginal value), runner-kill 34.2% vs ~22% market baseline. Consistent direction in both halves (−0.028/−0.226). This is the strongest working gate in the system.

**F2 — Three gates are FULLY REDUNDANT (no edge AND almost never fire alone):**
| gate | eps | ex4h | p | solo% |
|---|---|---|---|---|
| CONTINUUM-BLOCK | 1,639 | −0.033% | 0.003 | **18%** |
| CONTINUUM-BULL | 1,586 | +0.004% | 0.002 | **19%** |
| PRESERVE-SPIKE-BLOCK | 225 | −0.027% | 0.293 | 25% |

The BTC-structure pair (BLOCK/BULL) blocks ~3,200 episodes/26d at market-average outcomes, and in **81–82% of episodes another gate was already blocking the same token+direction within ±10min**. Removing them would change very little flow and costs nothing measurable. (Note: neither survives Bonferroni as *different from zero* — p=0.002–0.003 vs threshold 0.001 — i.e., they are not even reliably "slightly helpful"; their effects are economically zero either way.)

**F3 — The confluence-by-expiry filter (the system's largest) PROTECTS at every confidence band — D3 question answered: NO.**
28,634 expired signals, strong closures: conf 60–69 ex4h **−0.210%** (n=750) · 70–79 −0.035% (n=12,940) · 80–89 −0.024% (n=13,872) · 90+ −0.019% (n=80). **The high-confidence singles the confluence wall kills (avg conf 80.5) underperform market slightly at every band.** The confluence requirement is not costing edge — it's mildly protective. This closes the D3 instrumentation question opened Oct 9.

**F4 — Aggregate gate economics at live sizing: mildly protective, small.**
Sum over all gates × blocked excess × $15 notional = **−$67 refused opportunity over 26 days** (negative = gates refused entries that would have lost). At current sizing everything is near the noise floor; the number matters directionally, not as PnL.

**F5 — The shadow's own weak closer is coin-flip quality.** Sign agreement between gate_shadow's built-in follow-on-trade closure and the audited candle engine: **52%** on 2,873 dual-closed episodes. Per-gate weak-pnl vs strong-excess disagree in sign for 5/12 top gates. The built-in closer should not be used for decisions; the audited engine (or the extended closer from CEO D1) is required.

**F6 — BTC-CHOP-GATE's edge did NOT replicate.** Sole Bonferroni survivor of the Oct 2–8 audit (ex4h −0.38%); over 26 days: **+0.103% (p=0.49), positive (blocks winners direction) in both halves** (+0.071/+0.133). Honest OOS update: the gate's edge was regime-specific to the early-October chop→dump window, not durable.

**F7 — SLOPE-FILTER harm replicates for the third time.** +0.244% excess (blocked signals beat market), p=0.0015 (just above Bonferroni 0.001), **OOS-stable both halves (+0.297/+0.212)**, runner-kill 39.8% vs ~22% market, solo 46%. Consistent across: 6-day audit, auditor's 5-baseline matrix, and now 26-day shadow. Strongest harm candidate; remains monitor-only per CEO D2 guardrail until the Nov 6 readout.

**F8 — LONG-NEUTRAL-CHOP (the patch-spiral gate) is a wash, not the catastrophe feared.** Over its full life (n=1,042): ex4h −0.001% — exactly zero. In-chop +0.058 (mildly blocks winners), in-trend −0.253 (mildly protective). The verifier's "likely counterproductive vs chop-LONG best cohort" hypothesis is **not confirmed at 26d scale** — it's economically neutral. Keep measuring; no removal urgency.

## 3. Per-gate table (top 25 by episodes; full table in .out and gate_summary.tsv)

| gate | first | eps | solo% | ex4h mean | wr | p | verdict class |
|---|---|---|---|---|---|---|---|
| CONFLUENCE-GATE-BLOCK | 10-04 | 3,889 | 69% | −0.036% | 50% | 0.46 | no edge, high solo (keep — protects per F3) |
| SHORT-CONTINUUM | 10-04 | 1,897 | 58% | −0.054% | 55% | 0.036 | no edge (nominal) |
| CONTINUUM-BLOCK | 10-09 | 1,639 | **18%** | −0.033% | 47% | 0.003 | **FULLY REDUNDANT** |
| CONTINUUM-BULL | 10-09 | 1,586 | **19%** | +0.004% | 55% | 0.002 | **FULLY REDUNDANT** |
| LONG-NEUTRAL | 10-04 | 1,446 | 44% | +0.013% | 49% | 0.23 | no edge |
| SHORT-NEUTRAL | 10-04 | 1,424 | 44% | +0.011% | 53% | 0.047 | no edge (nominal) |
| CTX-GATE (LLM) | 10-04 | 1,380 | 70% | −0.081% | 47% | 0.057 | no edge (nominal protective) |
| PUMP-CHAIN-SHORT-HIGH | 10-07 | 1,156 | 90% | −0.059% | 52% | 0.47 | no edge |
| LONG-NEUTRAL-CHOP | 10-12 | 1,042 | 40% | −0.001% | 48% | 0.15 | **wash (F8)** |
| PUMP-CHAIN-RSI-MAX | 10-04 | 1,010 | 81% | **−0.127%** | 38% | **<0.0001** | **WORKS (F1)** |
| VOL-GATE-BYPASS | 10-09 | 980 | 76% | +0.018% | 51% | 0.70 | no edge |
| SHORT-RSI-HARD-FLOOR | 10-22 | 734 | 66% | +0.012% | 53% | 0.21 | no edge at 26d (chop-specific bleed not visible in markout) |
| BTC-CHOP-GATE | 10-04 | 449 | 41% | +0.103% | 54% | 0.49 | **edge NOT replicated (F6)** |
| OVERSOLD-SHORT | 10-22 | 388 | 32% | +0.161% | 56% | 0.012 | harm candidate (nominal) |
| PUMP-CHAIN-SHORT-RSI-MIN | 10-04 | 349 | 75% | −0.087% | 49% | 0.70 | no edge |
| HALL-SHAME | 10-04 | 316 | 77% | +0.092% | 46% | 0.35 | no edge (enforcement ended ~10-12) |
| PUMP-CHAIN-HIGH | 10-21 | 306 | 77% | −0.115% | 41% | 0.029 | nominal protective |
| LONG-RSI-CEILING | 10-22 | 288 | 51% | −0.250% | 43% | 0.018 | nominal protective |
| SLOPE-FILTER | 10-09 | 254 | 46% | **+0.244%** | 61% | 0.0015 | **harm, 3rd replication (F7)** |
| SPIKE-FILTER | 10-22 | 247 | 48% | −0.275% | 43% | 0.008 | nominal protective |
| PRESERVE-SPIKE-BLOCK | 10-05 | 225 | 25% | −0.027% | 52% | 0.29 | **FULLY REDUNDANT** |
| PENALTY-BLOCK | 10-09 | 202 | 65% | −0.077% | 46% | 0.17 | no edge |
| LONG-RSI-BLOCK | 10-22 | 181 | 33% | +0.057% | 47% | 0.60 | no edge |
| HOT-SET | 10-04 | 167 | 30% | +0.083% | 51% | 0.50 | no edge |
| EXEC-RSI-DETECT-FLOOR | 10-13 | 148 | 21% | +0.124% | 58% | 0.069 | no edge, functionally redundant |

## 4. Redundancy summary (the answer)

Of 50 recorded gates (44 with n≥16):
- **1 has durable edge:** PUMP-CHAIN-RSI-MAX.
- **3 are fully redundant** (no edge + ≤25% solo): CONTINUUM-BLOCK, CONTINUUM-BULL, PRESERVE-SPIKE-BLOCK — together ~3,450 blocked episodes/26d that changed nothing.
- **~20 are economically redundant with meaningful solo share** (removal would change signal flow but at ~market-average outcomes — the "78% no edge" finding from the 6-day audit holds at 26 days).
- **2 harm candidates (nominal, not Bonferroni):** SLOPE-FILTER (3rd replication, OOS-stable) and OVERSOLD-SHORT.
- **1 previously-claimed worker failed OOS:** BTC-CHOP-GATE.
- **The largest filter (confluence-expiry, 28k events) works** — protects at every confidence band; the D3 "are we killing 80-conf singles with edge?" question is answered NO.
- Aggregate effect at live sizing: −$67/26d refused opportunity — the stack is mildly protective, not harmful, but per-gate economics are dominated by noise; the architecture finding from the earlier audits (vetoes are absolute, scoring is cumulative) remains the structural issue this data cannot settle — that needs the R1 exit-stack shadow closer (CEO D1).

## 5. Regime-stability caveat

Per-gate OOS (Oct 4–17 vs 17–30) sign flips: 9/25 top gates flip. Trend-regime n is small (50–700 per gate). All verdicts above are 26-day-window properties. The Nov 6 re-audit decision gate stands: no gate removals on this report alone; the three FULLY REDUNDANT gates are the priority verification targets there (their removal is the cleanest test of the redundancy thesis — predicted flow change ≈ zero).

## 6. t5_shadow note (third source, weak coverage)

42,002 cell-admission decisions, but only 961 (2%) have pnl closures: WOULD_SKIP (n=8,522, 167 closed) avg −0.035% — skipped cells mildly negative; WOULD_TRADE (n=1,577, 85 closed) avg −0.003% — flat. Directionally consistent with "cell system mildly protective" but coverage too thin for verdicts. Recommend closing more t5 decisions or retiring the stream in favor of the extended gate_shadow closer (CEO D1).
